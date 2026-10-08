"""Existing voice-delivery/v1 and native Premiere, for this one research film."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

from run import ROOT, LOCAL, current, local, file_sha, voice_slots
from video_contracts import read, sha, write
from scripts.voice_delivery import validate as validate_delivery, asset
from premiere_production.mcp import PremiereMcpClient
from premiere_production.student_voice import inspect_rendered_voice
from premiere_production.music import recording_manifest, gain_envelope, verify_gain_keys


def client():
    c=PremiereMcpClient('http://127.0.0.1:11489/mcp',(ROOT/'local-data/v9.1/mcp-token.txt').read_text().strip())
    c.initialize();return c


def validate_voices(request, voices):
    slots=voice_slots(request);last=0
    if len(voices)!=len(slots):raise ValueError('Every frozen guide beat must survive')
    for v,s in zip(voices,slots):
        if (v['id']!=s['id'] or v['text']!=s['text'] or v['text_sha']!=sha(s['text'])
                or v['listening_review']!='PENDING' or v['start']!=s['start']
                or type(v['duration']) not in (int,float) or not math.isfinite(v['duration'])
                or not last<=v['start']<v['end']<=request['duration']
                or abs(v['end']-v['start']-v['duration'])>1e-8
                or any(abs(t*24-round(t*24))>1e-6 for t in (v['start'],v['end']))):
            raise ValueError('Keep exact words, full samples, PENDING reviews and frame placement')
        last=v['end']


def prepare(revision, delivery, output, music_source=None):
    r=current(revision)
    if r['phase']!='full':raise ValueError('Only the complete dual film gets guided narration')
    delivery=Path(delivery).resolve();source=validate_delivery(delivery);clips={c['id']:c for c in source['clips']}
    if set(clips)!={v['id'] for v in voice_slots(r)}:raise ValueError('Use only the five existing frozen guide beats')
    output=local(output);output.mkdir(parents=True,exist_ok=False);voices=[]
    for s in voice_slots(r):
        c=clips[s['id']];text=asset(delivery.parent,c['transcript']).read_text(encoding='utf-8-sig')
        if text!=s['text']:raise ValueError('Frozen synthetic guide changed')
        path=output/(s['id']+'.wav')
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(asset(delivery.parent,c['audio'])),
            '-ar','48000','-ac','1','-c:a','pcm_s16le','-f','s16le','pipe:1'])
        samples=len(pcm)//2;padded=math.ceil(samples/2000)*2000
        with wave.open(str(path),'wb') as f:
            f.setparams((1,2,48000,padded,'NONE','not compressed'));f.writeframes(pcm+b'\0'*(2*(padded-samples)))
        voices.append({'id':s['id'],'text':text,'text_sha':sha(text),'path':str(path),'sha256':file_sha(path),
            'source_sha':c['audio_sha256'],'start':s['start'],'end':s['start']+padded/48000,
            'duration':padded/48000,'sample_rate':48000,'channels':1,'added_silent_samples':padded-samples,
            'listening_review':'PENDING'})
    validate_voices(r,voices);music=None
    if music_source:
        path=Path(music_source).resolve();recording=recording_manifest(path,title='Nocturne No. 6 in G Minor, Op. 15, No. 3',
            composer='Frédéric Chopin',performer='Arthur Rubinstein',source='User-provided local recording')
        target=output/'CHOPIN_SCRATCH.wav'
        subprocess.run(['ffmpeg','-v','error','-n','-ss','8','-i',str(path),'-t',str(r['duration']),
            '-ar','48000','-ac','2','-c:a','pcm_s16le',str(target)],check=True)
        if file_sha(path)!=recording['file_sha']:raise ValueError('Do not change the original recording')
        # The source stays unmastered. Premiere owns these small duck/fade keys.
        anchors=[(0,-70),(.8,-30),(12.4,-30),(15.5,-35),(38.8,-35),(40,-42),(44.5,-42),(46.45,-70)]
        music=dict(recording,path=str(target),sha256=file_sha(target),source_path=str(path),source_in=8,
            audio_track_index=1,gain_keys=gain_envelope(anchors,r['duration'],steps=2))
    plan={'kind':'synthetic_relay_audio_editorial','spec_sha':r['spec_sha'],'trajectory_sha':r['trajectory_sha'],
        'source_delivery':str(delivery),'delivery_sha':file_sha(delivery),'generation_sha':file_sha(delivery.parent/'generation.json'),
        'voices':voices,'music':music,'listening_review':'PENDING','final_voice_accepted':False,
        'sample_delivery_allowed':False,'production_eligible':False,'public_render_ready':False}
    plan['plan_sha']=sha(plan);write(output/'audio-plan.json',plan);return plan


def preflight(revision, output):
    r=current(revision);p=read(output/'audio-plan.json');picture=read(revision/'render-receipt.json')
    if (r['phase']!='full' or p['plan_sha']!=sha({k:v for k,v in p.items() if k!='plan_sha'})
            or p['spec_sha']!=r['spec_sha'] or picture['spec_sha']!=r['spec_sha']
            or picture['phase']!='full' or not picture['native']['done']
            or file_sha(picture['output'])!=picture['output_sha'] or file_sha(picture['project'])!=picture['project_sha']
            or file_sha(p['source_delivery'])!=p['delivery_sha']
            or file_sha(Path(p['source_delivery']).parent/'generation.json')!=p['generation_sha']
            or any(p[k] is not False for k in ('final_voice_accepted','sample_delivery_allowed','production_eligible','public_render_ready'))):
        raise ValueError('Frozen native picture or audio delivery changed')
    validate_voices(r,p['voices']);delivery=validate_delivery(p['source_delivery']);sources={x['id']:x for x in delivery['clips']}
    for v in p['voices']:
        with wave.open(v['path'],'rb') as f:
            measured=(f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes()/f.getframerate())
        if (file_sha(v['path'])!=v['sha256'] or sources[v['id']]['audio_sha256']!=v['source_sha']
                or measured[:3]!=(1,2,48000) or abs(measured[3]-v['duration'])>1/48000):
            raise ValueError('Bound voice data or whole-clip duration changed')
    if p['music'] and (file_sha(p['music']['path'])!=p['music']['sha256']
            or file_sha(p['music']['source_path'])!=p['music']['file_sha']):raise ValueError('Bound scratch recording changed')
    return r,p,picture


def native_audit(c, revision, output):
    r,p,pic=preflight(revision,output);identity=read(output/'pr-identity.json')
    project=c.call('get_project_info');seq=c.call('get_active_sequence');settings=c.call('get_sequence_settings')
    if (Path(project['path']).resolve()!=output/'METHOD_RELAY.prproj' or seq['id']!=identity['sequence_id']
            or seq.get('pagination',{}).get('truncated') or abs(seq['end']-r['duration'])>1e-6
            or [settings[k] for k in ('frameSizeHorizontal','frameSizeVertical','timebase','audioSampleRateHz')]
            !=[1920,1080,'10584000000',48000]):raise ValueError('Wrong native project, sequence or format')
    video=[v for t in seq['videoTracks'] for v in t['clips']];sounds=[v for t in seq['audioTracks'] for v in t['clips']]
    expected=[(pic['output'],0,r['duration'])]+[(v['path'],v['start'],v['end']) for v in p['voices']]
    if p['music']:expected.append((p['music']['path'],0,r['duration']))
    if len(video)!=1 or len(sounds)!=len(expected)-1:raise ValueError('No cuts, time stretch or missing audio')
    entries=c.call('list_project_items');entries=entries['items'] if isinstance(entries,dict) else entries
    for path,node in identity['item_ids'].items():
        hits=[x for x in entries if x.get('nodeId')==node and x.get('mediaPath') and Path(x['mediaPath']).resolve()==Path(path).resolve()]
        if len(hits)!=1:raise ValueError('Imported source identity changed')
    for actual,(path,start,end) in zip(video+sounds,expected):
        if actual['name']!=Path(path).name or abs(actual['start']-start)>1/48000 or abs(actual['end']-end)>1/48000:
            raise ValueError('Native clip placement differs from the exact editorial plan')
        props=c.call('get_clip_properties',{'node_id':actual['nodeId']})
        if abs(props['inPoint'])>1/48000 or abs(props['outPoint']-(end-start))>1/48000:
            raise ValueError('Native timeline cropped a voice or picture')
    if p['music']:
        m=read(output/'music-property-binding.json');actual=c.call('get_keyframes',m['query'])
        verify_gain_keys(actual,p['music']['gain_keys']);write(output/'native-music-audit.json',actual)
    state={'project':project,'sequence':seq,'settings':settings,'picture_sha':pic['output_sha'],
        'plan_sha':p['plan_sha'],'listening_review':'PENDING','public_render_ready':False}
    write(output/'native-pr-audit.json',state);return state


def assemble(revision, output):
    r,p,pic=preflight(revision,output);c=client();prior=c.call('get_project_info');old=Path(prior['path']);old_sha=file_sha(old)
    # Open a byte copy before create_project can save its current session.
    session=output/'SESSION_START.prproj'
    if session.exists():raise FileExistsError('Preserve earlier editorial sessions')
    shutil.copy2(old,session);c.call('open_project',{'path':str(session)})
    if Path(c.call('get_project_info')['path']).resolve()!=session or file_sha(old)!=old_sha:
        raise ValueError('Premiere isolation did not preserve old project bytes')
    write(output/'pr-isolation.json',{'prior':prior,'old_sha':old_sha,'isolated':str(session)})
    log=[]
    def mutate(name,args):
        preflight(revision,output);write(output/'pending-pr-mutation.json',{'tool':name,'arguments':args})
        result=c.call(name,args,timeout=120);log.append({'tool':name,'arguments':args,'result':result});write(output/'pr-edit-receipts.json',log);return result
    target=output/'METHOD_RELAY.prproj'
    if target.exists():raise FileExistsError('Preserve editable projects')
    mutate('create_project',{'path':str(target)})
    mutate('create_sequence',{'name':'SYNTHETIC_METHOD_RELAY_DUAL_PASS','preset_path':str(ROOT/'local-data/v9.1/pr-config/CINEMATIC_1080p24.sqpreset')})
    paths=[pic['output']]+[v['path'] for v in p['voices']]+([p['music']['path']] if p['music'] else [])
    mutate('import_media',{'file_paths':paths,'suppress_ui':True})
    data=c.call('list_project_items');data=data['items'] if isinstance(data,dict) else data;ids={}
    for path in paths:
        hits=[x for x in data if x.get('mediaPath') and Path(x['mediaPath']).resolve()==Path(path).resolve()]
        if len(hits)!=1:raise ValueError('Ambiguous imported source')
        ids[path]=hits[0]['nodeId']
    write(output/'pr-identity.json',{'sequence_id':c.call('get_active_sequence')['id'],'item_ids':ids})
    mutate('overwrite_clip',{'item_id':ids[pic['output']],'start_seconds':0,'track_index':0})
    for v in p['voices']:mutate('overwrite_clip',{'item_id':ids[v['path']],'start_seconds':v['start'],'track_index':0,'audio_track_index':0})
    if p['music']:
        mutate('overwrite_clip',{'item_id':ids[p['music']['path']],'start_seconds':0,'track_index':0,'audio_track_index':1})
        sequence=c.call('get_active_sequence');music_node=sequence['audioTracks'][1]['clips'][0]['nodeId']
        properties=c.call('get_clip_properties',{'node_id':music_node});write(output/'music-native-properties.json',properties)
        effects=properties.get('effects',[]);level=None
        for effect in effects:
            if effect.get('matchName')!='Internal Volume Stereo':continue
            parameters=c.call('get_effect_properties',{'node_id':music_node,'effect_name':effect['displayName']})
            write(output/'music-effect-properties.json',parameters)
            for parameter in parameters.get('properties',[]):
                if parameter.get('displayName') in ('级别','Level') and parameter.get('keyframesSupported'):
                    level={'effect_name':effect['displayName'],'property_name':parameter['displayName']}
        if level is None:raise ValueError('Read native volume names before writing automation')
        query={'node_id':music_node,**level};write(output/'music-property-binding.json',{'query':query})
        for k in p['music']['gain_keys']:
            applied=mutate('add_keyframe',dict(query,time_seconds=k['time_seconds'],value=10**((k['level_db']-15)/20)))
            if not applied.get('stored') or applied.get('keyframesOutsideVisibleRange'):raise ValueError('Music key was not stored')
    mutate('save_project',{})
    if file_sha(old)!=old_sha:raise ValueError('Historical Premiere bytes changed')
    return native_audit(c,revision,output)


def export(revision, output):
    c=client();native_audit(c,revision,output);r,p,pic=preflight(revision,output)
    target=output/'METHOD_RELAY_DUAL_PASS.mp4'
    if target.exists():raise FileExistsError('Never overwrite a previous movie')
    preset=ROOT/'local-data/v9.1/g01-r2/premiere/INTERNAL_H264_CAPTION_CANDIDATE_2.epr'
    if file_sha(preset)!='b528a68080fa043fcb387eedfd643f4e30d90368c4ef38a2e7f39c8061e1e76a':raise ValueError('Existing export preset changed')
    args={'output_path':str(target),'preset_path':str(preset),'range':'entire','overwrite':False,'timeout_minutes':8}
    write(output/'pr-export-request.json',args);native=c.call('export_sequence',args,timeout=510);write(output/'native-pr-export.json',native)
    native_audit(c,revision,output)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target)],encoding='utf-8'))
    video=[s for s in info['streams'] if s['codec_type']=='video'];audio=[s for s in info['streams'] if s['codec_type']=='audio']
    if (len(video)!=1 or len(audio)!=1 or video[0]['width']!=1920 or video[0]['height']!=1080
            or video[0]['r_frame_rate']!='24/1' or int(audio[0]['sample_rate'])!=48000
            or abs(float(video[0]['duration'])-r['duration'])>1/24):raise ValueError('Actual encoded delivery differs from the native timeline')
    write(output/'encoded-media.json',info);subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    write(output/'voice-presence.json',inspect_rendered_voice(target,p))
    receipt={'engine':'native_Premiere_export','output':str(target),'output_sha':file_sha(target),
        'project':str(output/'METHOD_RELAY.prproj'),'project_sha':file_sha(output/'METHOD_RELAY.prproj'),
        'picture_sha':pic['output_sha'],'plan_sha':p['plan_sha'],'listening_review':'PENDING','human_viewing_review':'PENDING',
        'final_voice_accepted':False,'sample_delivery_allowed':False,'production_eligible':False,'public_render_ready':False}
    write(output/'delivery-receipt.json',receipt);return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('prepare','assemble','audit','export'))
    p.add_argument('revision');p.add_argument('output');p.add_argument('--delivery');p.add_argument('--music')
    a=p.parse_args();revision=local(a.revision);output=local(a.output)
    if a.operation=='prepare':result=prepare(revision,a.delivery,output,a.music)
    elif a.operation=='audit':result=native_audit(client(),revision,output)
    else:result=globals()[a.operation](revision,output)
    print(json.dumps({'operation':a.operation,'receipt_saved':str(output)},ensure_ascii=True))


if __name__=='__main__':main()
