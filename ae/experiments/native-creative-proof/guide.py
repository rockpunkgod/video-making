"""Fixed Scratch VO and native Premiere assembly for this one synthetic AE proof."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from video_contracts import read,sha,write
from scripts.voice_delivery import asset,validate as validate_delivery
from premiere_production.mcp import PremiereMcpClient
from premiere_production.student_voice import inspect_rendered_voice
from run import current,file_sha,research_output,canvas_duration,voice_slots


def fixed_clips(request,source):
    """Reuse every original recording exactly; presentation may change its slot."""
    slots=voice_slots(request);clips={c['id']:c for c in source['clips']}
    if len(clips)!=len(source['clips']) or set(clips)!={v['id'] for v in slots}:
        raise ValueError('Fixed synthetic guide requires every exact original voice ID')
    return [(clips[slot['id']],slot) for slot in slots]


def validate_placement(request,voices):
    slots=voice_slots(request)
    if len(voices)!=len(slots):raise ValueError('Do not add or remove fixed voice slots')
    previous=0
    for voice,slot in zip(voices,slots):
        if (any(type(voice[k]) not in (int,float) or not math.isfinite(voice[k]) for k in ('start','end','duration'))
                or voice['id']!=slot['id'] or voice['text']!=slot['text']
                or voice['text_sha']!=sha(slot['text']) or voice['start']!=slot['start']
                or voice['listening_review']!='PENDING'
                or not previous<=voice['start']<voice['end']<=canvas_duration(request)
                or abs(voice['end']-voice['start']-voice['duration'])>1e-8
                or any(abs(v*24-round(v*24))>1e-6 for v in (voice['start'],voice['end']))):
            raise ValueError('Fixed guide identity, whole-clip duration or placement changed')
        previous=voice['end']


def prepare(revision,delivery,output):
    request=current(revision);delivery=Path(delivery).resolve();source=validate_delivery(delivery)
    pairs=fixed_clips(request,source)
    output=research_output(output);output.mkdir(parents=True,exist_ok=False);voices=[]
    for clip,slot in pairs:
        transcript=asset(delivery.parent,clip['transcript']).read_text(encoding='utf-8-sig')
        if transcript!=slot['text']:raise ValueError('Do not rewrite the fixed guide')
        target=output/(clip['id']+'.wav')
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(asset(delivery.parent,clip['audio'])),
            '-ar','48000','-ac','1','-c:a','pcm_s16le','-f','s16le','pipe:1'])
        original=len(pcm)//2;frames=math.ceil(original/2000)*2000
        with wave.open(str(target),'wb') as media:
            media.setparams((1,2,48000,frames,'NONE','not compressed'))
            media.writeframes(pcm+b'\0'*(2*(frames-original)))
        if abs(slot['start']*24-round(slot['start']*24))>1e-6:
            raise ValueError('Place the whole clip on a video-frame boundary')
        voices.append({'id':clip['id'],'path':str(target),'sha256':file_sha(target),
            'source_sha256':clip['audio_sha256'],'text':transcript,'text_sha':sha(transcript),
            'start':slot['start'],'end':slot['start']+frames/48000,'duration':frames/48000,
            'padding_samples':frames-original,'sample_rate':48000,'channels':1,
            'listening_review':'PENDING'})
    validate_placement(request,voices)
    plan={'kind':'synthetic_fixed_scratch_guide','spec_sha':request['spec_sha'],
        'source_delivery':str(delivery),'delivery_sha':file_sha(delivery),
        'generation_receipt_sha':file_sha(delivery.parent/'generation.json'),
        'voices':voices,'music':None,'sfx':None,'listening_review':'PENDING',
        'final_voice_accepted':False,'sample_delivery_allowed':False,'public_render_ready':False}
    plan['guide_sha']=sha(plan);write(output/'guide-plan.json',plan);return plan


def preflight(revision,output):
    request=current(revision);plan=read(output/'guide-plan.json');picture=read(revision/'render-receipt-B.json')
    if (plan['guide_sha']!=sha({k:v for k,v in plan.items() if k!='guide_sha'})
            or plan['spec_sha']!=request['spec_sha'] or picture['spec_sha']!=request['spec_sha']
            or picture['variant']!='B' or picture['audio'] is not False
            or picture['production_eligible'] is not False or picture['public_render_ready'] is not False
            or plan['final_voice_accepted'] is not False or plan['public_render_ready'] is not False
            or plan['sample_delivery_allowed'] is not False or plan['listening_review']!='PENDING'
            or len(plan['voices'])!=len(request['scene']['voice'])
            or file_sha(plan['source_delivery'])!=plan['delivery_sha']
            or file_sha(Path(plan['source_delivery']).parent/'generation.json')!=plan['generation_receipt_sha']
            or file_sha(picture['project'])!=picture['project_sha256']
            or file_sha(picture['output'])!=picture['output_sha256']):
        raise ValueError('Frozen native picture or fixed guide changed')
    validate_placement(request,plan['voices'])
    source=validate_delivery(plan['source_delivery'])
    for voice,(clip,slot) in zip(plan['voices'],fixed_clips(request,source)):
        with wave.open(voice['path'],'rb') as media:
            pcm=(media.getnchannels(),media.getsampwidth(),media.getframerate(),media.getnframes()/media.getframerate())
        if (file_sha(voice['path'])!=voice['sha256'] or voice['source_sha256']!=clip['audio_sha256']
                or pcm[:3]!=(1,2,48000) or abs(pcm[3]-voice['duration'])>1/48000):
            raise ValueError('Fixed guide identity or placement changed')
    return picture,plan


def client():
    from run import ROOT
    c=PremiereMcpClient('http://127.0.0.1:11489/mcp',
        (ROOT/'local-data/v9.1/mcp-token.txt').read_text().strip());c.initialize();return c


def timeline(c,revision,output):
    duration=canvas_duration(current(revision))
    picture,plan=preflight(revision,output);identity=read(output/'pr-identity.json')
    info=c.call('get_project_info');state=c.call('get_active_sequence');settings=c.call('get_sequence_settings')
    if (Path(info['path']).resolve()!=output/'NATIVE_GUIDE.prproj' or state['id']!=identity['sequence_id']
            or abs(state['end']-duration)>1e-6 or state.get('pagination',{}).get('truncated')
            or [settings[k] for k in ('frameSizeHorizontal','frameSizeVertical','timebase','audioSampleRateHz')]
            !=[1920,1080,'10584000000',48000]):raise ValueError('Native guide sequence changed')
    videos=[v for t in state['videoTracks'] for v in t['clips']]
    sounds=[v for t in state['audioTracks'] for v in t['clips']]
    if len(videos)!=1 or len(sounds)!=len(plan['voices']):raise ValueError('Guide must remain a single continuous picture')
    items=c.call('list_project_items')
    items=items['items'] if isinstance(items,dict) else items
    for path,node in identity['item_ids'].items():
        matches=[i for i in items if i.get('nodeId')==node]
        if len(matches)!=1 or Path(matches[0].get('mediaPath','')).resolve()!=Path(path).resolve():
            raise ValueError('Native source path was replaced')
    expected=[(picture['output'],0,duration)]+[(v['path'],v['start'],v['end']) for v in plan['voices']]
    for actual,(path,start,end) in zip(videos+sounds,expected):
        if (actual['name']!=Path(path).name or abs(actual['start']-start)>1/48000
                or abs(actual['end']-end)>1/48000):raise ValueError('Do not cut picture or truncate guide')
        props=c.call('get_clip_properties',{'node_id':actual['nodeId']})
        if abs(props['inPoint'])>1/48000 or abs(props['outPoint']-(end-start))>1/48000:
            raise ValueError('Unexpected native source trim')
    write(output/'native-pr-audit.json',{'timeline':state,'settings':settings,'project':info,
        'guide_sha':plan['guide_sha'],'picture_sha':picture['output_sha256'],'public_render_ready':False})
    return state


def assemble(revision,output):
    from run import ROOT
    picture,plan=preflight(revision,output);project=output/'NATIVE_GUIDE.prproj'
    if project.exists():raise FileExistsError('Preserve native guide projects')
    c=client();before=c.call('get_project_info');prior=Path(before['path']);prior_sha=file_sha(prior)
    backup=output/'prior-project-byte-backup.prproj';shutil.copy2(prior,backup)
    write(output/'prior-project-binding.json',{'path':str(prior),'sha256':prior_sha,'byte_backup':str(backup)})
    log=[]
    def mutate(name,args):
        preflight(revision,output);write(output/'pending-pr-mutation.json',{'tool':name,'arguments':args})
        result=c.call(name,args,timeout=120);log.append({'tool':name,'arguments':args,'result':result})
        write(output/'pr-edit-receipts.json',log);return result
    mutate('create_project',{'path':str(project)})
    if file_sha(prior)!=prior_sha:raise ValueError('Prior Premiere bytes changed; inspect and reconcile')
    mutate('create_sequence',{'name':'SYNTHETIC_NATIVE_FIXED_GUIDE',
        'preset_path':str(ROOT/'local-data/v9.1/pr-config/CINEMATIC_1080p24.sqpreset')})
    paths=[picture['output']]+[v['path'] for v in plan['voices']]
    mutate('import_media',{'file_paths':paths,'suppress_ui':True})
    data=c.call('list_project_items');entries=data['items'] if isinstance(data,dict) else data
    ids={}
    for path in paths:
        hits=[i for i in entries if i.get('mediaPath') and Path(i['mediaPath']).resolve()==Path(path).resolve()]
        if len(hits)!=1:raise ValueError('Ambiguous imported guide source')
        ids[path]=hits[0]['nodeId']
    write(output/'pr-identity.json',{'sequence_id':c.call('get_active_sequence')['id'],'item_ids':ids})
    mutate('overwrite_clip',{'item_id':ids[picture['output']],'start_seconds':0,'track_index':0})
    for voice in plan['voices']:
        mutate('overwrite_clip',{'item_id':ids[voice['path']],'start_seconds':voice['start'],
            'track_index':0,'audio_track_index':0})
    mutate('save_project',{});return timeline(c,revision,output)


def export(revision,output):
    from run import ROOT
    c=client();timeline(c,revision,output);picture,plan=preflight(revision,output)
    duration=canvas_duration(current(revision))
    target=output/'B_FIXED_GUIDE.mp4'
    if target.exists():raise FileExistsError('Preserve native guide renders')
    preset=ROOT/'local-data/v9.1/g01-r2/premiere/INTERNAL_H264_CAPTION_CANDIDATE_2.epr'
    if file_sha(preset)!='b528a68080fa043fcb387eedfd643f4e30d90368c4ef38a2e7f39c8061e1e76a':
        raise ValueError('Existing native export preset changed')
    native=c.call('export_sequence',{'output_path':str(target),'preset_path':str(preset),
        'range':'entire','overwrite':False,'timeout_minutes':8},timeout=510)
    write(output/'native-pr-export.json',native)
    timeline(c,revision,output)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format',
        '-of','json',str(target)],encoding='utf-8'))
    video=[s for s in info['streams'] if s['codec_type']=='video']
    audio=[s for s in info['streams'] if s['codec_type']=='audio']
    if (len(video)!=1 or len(audio)!=1 or video[0]['width']!=1920 or video[0]['height']!=1080
            or video[0]['r_frame_rate']!='24/1' or int(audio[0]['sample_rate'])!=48000
            or abs(float(video[0]['duration'])-duration)>1/24):
        raise ValueError('Native encoded guide does not match its sequence')
    write(output/'encoded-media.json',info)
    subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    signal=inspect_rendered_voice(target,plan);write(output/'encoded-voice-presence.json',signal)
    write(output/'guide-receipt.json',{'output':str(target),'output_sha256':file_sha(target),
        'project':str(output/'NATIVE_GUIDE.prproj'),'project_sha256':file_sha(output/'NATIVE_GUIDE.prproj'),
        'picture_sha':picture['output_sha256'],'guide_sha':plan['guide_sha'],
        'engine':'native_Premiere_export','listening_review':'PENDING','human_viewing_review':'PENDING',
        'final_voice_accepted':False,'sample_delivery_allowed':False,'public_render_ready':False})
    return str(target)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('prepare','assemble','export','audit'))
    p.add_argument('revision');p.add_argument('output');p.add_argument('--delivery');args=p.parse_args()
    revision=research_output(args.revision);output=research_output(args.output)
    if args.operation=='prepare':result=prepare(revision,args.delivery,output)
    elif args.operation=='audit':result=timeline(client(),revision,output)
    else:result=globals()[args.operation](revision,output)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
