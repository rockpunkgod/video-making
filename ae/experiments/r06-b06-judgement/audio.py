"""Reuse exact frozen takes; recompute excerpt clocks without time stretching."""
import argparse
from copy import deepcopy
from pathlib import Path
import wave
import numpy as np

from produce import current, local, read, write, file_sha, sha, FPS


def pcm(path):
    with wave.open(str(path),'rb') as stream:
        if stream.getframerate()!=48000 or stream.getsampwidth()!=2:
            raise ValueError('Existing 48 kHz PCM16 source required')
        channels=stream.getnchannels()
        return np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').reshape(-1,channels).copy()


def save(path, values):
    if path.exists():raise FileExistsError('Preserve the previous audio revision')
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(values.shape[1]);stream.setsampwidth(2);stream.setframerate(48000)
        stream.writeframes(values.astype('<i2').tobytes())


def srt_time(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def prepare(folder):
    production,spec=current(folder);out=folder/'audio';out.mkdir(exist_ok=True)
    if (folder/'AV_PLAN.json').exists():raise FileExistsError('Existing bounded audio plan')
    root=Path(production['baseline_folder']).parent/'title-task-episode-r1'
    original=read(root/'editorial/AUDIO_EDITORIAL.json')
    if file_sha(original['music']['path'])!=original['music']['sha256']:
        raise ValueError('Frozen music bed changed')
    for source in original['sources']:
        if file_sha(source['path'])!=source['sha256']:
            raise ValueError('Frozen music recording changed')
    for v in production['voices']:
        transcript=Path(v['path']).with_suffix('.txt')
        if sha(transcript.read_text(encoding='utf-8'))!=v['transcript_sha'] or file_sha(v['path'])!=v['sha256']:
            raise ValueError('Exact voice/transcript binding changed')
        if len(pcm(v['path']))!=round(v['duration']*48000):
            raise ValueError('Complete take sample count changed')
    old_bounds=production['bounds']['old_context'];new_bounds=production['bounds']['new_context']
    old_start,old_end=[round(f/FPS*48000) for f in old_bounds]
    old_music=pcm(original['music']['path'])[old_start:old_end]
    # The existing second recording is already in progress in B05. Continue the
    # recording through the extra observation time; never repeat/stretch music.
    source=pcm(root/'editorial/MUSIC_SOURCE_1.wav')
    source_start=round((new_bounds[0]/FPS-original['music']['transition']+.5)*48000)
    count=round((new_bounds[1]-new_bounds[0])/FPS*48000)
    raw=source[source_start:source_start+count].astype(np.float32)/32768
    if len(raw)!=count:raise ValueError('Existing music recording does not cover the new excerpt')
    gain=np.full(count,.035,np.float32);start=new_bounds[0]/FPS
    for v in production['voices']:
        a=max(0,round((v['start']-start-.12)*48000));b=min(count,round((v['end']-start+.2)*48000));gain[a:b]=.012
    for event in spec['events']:
        a=max(0,round((event['decision_start']-start)*48000));b=min(count,round((event['decision_end']+.3-start)*48000))
        if a<b:gain[a:b]=.006
    knots=np.arange(0,count,4800);gain=np.interp(np.arange(count),knots,gain[knots])
    new_music=np.round(raw*gain[:,None]*32768).astype('<i2')
    save(out/'OLD_CONTEXT_MUSIC.wav',old_music);save(out/'NEW_CONTEXT_MUSIC.wav',new_music)
    captions=read(Path(production['baseline_folder'])/'CAPTIONS.json')
    variants={}
    for label,bound_key in [('OLD_B06_FULL','old_pure'),('NEW_B06_FULL','new_pure'),
                           ('OLD_CONTEXT_VISUAL','old_context'),('NEW_CONTEXT_VISUAL','new_context'),
                           ('OLD_CONTEXT_FULL','old_context'),('NEW_CONTEXT_FULL','new_context')]:
        new=label.startswith('NEW');bounds=production['bounds'][bound_key];a,b=[x/FPS for x in bounds]
        context_start=(new_bounds if new else old_bounds)[0]/FPS
        selected=[]
        for voice in production['voices']:
            v=deepcopy(voice);v['start']=voice['start'] if new else voice['original_start'];v['end']=voice['end'] if new else voice['original_end']
            if v['end']<=a or v['start']>=b:continue
            if not a<=v['start']<v['end']<=b:raise ValueError('Excerpt would truncate a frozen take')
            if label.endswith('_VISUAL'):continue
            v['start']-=a;v['end']-=a;v['native_name']=Path(v['path']).name;selected.append(v)
        music=out/(('NEW' if new else 'OLD')+'_CONTEXT_MUSIC.wav')
        if 'B06_FULL' in label:
            samples=pcm(music)[round((a-context_start)*48000):round((b-context_start)*48000)]
            music=out/(label+'_MUSIC.wav');save(music,samples)
        rows=[]
        for row in captions:
            if row['clip_id'] not in {v['id'] for v in selected}:continue
            value=deepcopy(row)
            offset=production['insert']['frames']/FPS if new and row['start']>=production['insert']['original_frame']/FPS else 0
            value['start']+=offset-a;value['end']+=offset-a
            if not 0<=value['start']<value['end']<=b-a:raise ValueError('Caption escapes its complete take excerpt')
            rows.append(value)
        subtitle=out/(label+'.srt')
        subtitle.write_text('\n\n'.join(f"{i+1}\n{srt_time(r['start'])} --> {srt_time(r['end'])}\n{r['display_text']}" for i,r in enumerate(rows))+'\n',encoding='utf-8')
        variants[label]={'frames':bounds[1]-bounds[0],'duration':b-a,'source_frames':bounds,'voices':selected,
            'music':{'path':str(music),'sha256':file_sha(music),'duration':b-a,'rights':'UNKNOWN_INTERNAL_ONLY'},
            'captions':rows,'srt_path':str(subtitle),'srt_sha':file_sha(subtitle),
            'vo_mode':'NONE_FOR_UNEXPLAINED_VISUAL_CONTROL' if label.endswith('_VISUAL') else 'ALL_COMPLETE_BOUND_TAKES',
            'voice_stretched':False,'voice_truncated':False,'listening_review':'PENDING','public_render_ready':False}
    plan={'kind':'bounded_b06_av_plan','production_sha':production['production_sha'],'sample_rate':48000,'fps':24,
        'variants':variants,'existing_music_sources':original['sources'],'new_music_pcm_source_sha':file_sha(root/'editorial/MUSIC_SOURCE_1.wav'),
        'music_retiming':'Continuous recording excerpt with reauthored ducking; no loop or time stretch',
        'clock_mapping':{'kind':'TIMING_RELATION_NOT_PIXEL_IDENTITY','original_insert_frame':production['insert']['original_frame'],
                         'inserted_observation_frames':production['insert']['frames'],'source_context_start_frame':old_bounds[0]},
        'native_timeline_verification':'PENDING','human_visual_review':'PENDING','human_listening_review':'PENDING','public_render_ready':False}
    plan['av_plan_sha']=sha(plan);write(folder/'AV_PLAN.json',plan)
    return {'variants':len(variants),'complete_voice_slots':sum(len(v['voices']) for v in variants.values()),'new_pure_seconds':variants['NEW_B06_FULL']['duration']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder');args=parser.parse_args();print(prepare(local(args.folder)))
