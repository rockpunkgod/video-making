"""Hash-bound silent locating comparisons and literal native-frame excerpts."""
import argparse
import subprocess
import shutil
from pathlib import Path
import acquisition_ab
import locating_render
import run as relay
from video_contracts import read,write,sha


def prepare(config,baseline,baseline_sha,output):
    patch=locating_render.current(config)
    source=relay.local(config['output']);receipt=read(source/'render-receipt.json')
    baseline=relay.local(baseline);out=relay.local(output)
    old_request=read(baseline.parent/'request.json')
    if (old_request['spec_sha']!=patch['base_spec_sha']
            or relay.file_sha(baseline)!=baseline_sha
            or receipt['patch_sha']!=patch['patch_sha']
            or receipt['native_canvas']!=[3840,2160,24]
            or receipt['frame_manifest_sha']!=sha(read(source/'native-frame-shas.json'))
            or relay.file_sha(source/'GUIDED_B.mp4')!=receipt['movie']['sha256']):
        raise ValueError('Same original request and completed native B required')
    first,last=config['frames'];out.mkdir(exist_ok=False,parents=True)
    movies={}
    for label,path in [('A',baseline),('B',source/'GUIDED_B.mp4')]:
        target=out/('GUIDED_'+label+'.mp4');shutil.copy2(path,target)
        movies[label]=acquisition_ab.verify_movie(target,last-first,3840,2160)
    ranges={'SCAN':patch['frame_range'],
            'ACQUIRE_TO_LIFT':[patch['plan']['clock']['events'][-1]['activation'][0],last]
            if patch['plan']['handoff'] else patch['frame_range']}
    for label,(start,end) in ranges.items():
        if not first<=start<end<=last:raise ValueError('Excerpt outside native render')
        movies[label]=acquisition_ab.encode_frames(source/'native-frames',start,end-start,
                    out/(label+'.mp4'),3840,2160)
    events=patch['plan']['clock']['events']
    if events:
        e=events[min(1,len(events)-1)];start=e['activation'][0]-4
        end=(e.get('retirement') or [e['recognition'][1],e['recognition'][1]+9])[1]+4
        start=max(first,start);end=min(last,end)
        short=out/'RECOGNITION.mp4'
        movies['RECOGNITION']=acquisition_ab.encode_frames(source/'native-frames',start,end-start,short,3840,2160)
        loop=out/'RECOGNITION_LOOP.mp4'
        subprocess.run(['ffmpeg','-v','error','-n','-stream_loop','2','-i',str(short),'-an','-c','copy',str(loop)],check=True)
        movies['RECOGNITION_LOOP']=acquisition_ab.verify_movie(loop,(end-start)*3,3840,2160)
        ranges['RECOGNITION']=[start,end]
    # Comparison canvas is 4K; each panel is explicitly downscaled to 1080p.
    # Standalone native A/B and excerpts retain their full original 4K pixels.
    target=out/'AB_GUIDED_4K.mp4'
    subprocess.run(['ffmpeg','-v','error','-n','-threads','1','-i',movies['A']['path'],
        '-threads','1','-i',movies['B']['path'],'-filter_complex_threads','1','-filter_complex',
        '[0:v]scale=1920:1080,pad=1920:2160:0:540:color=0xf8f7f2[a];'
        '[1:v]scale=1920:1080,pad=1920:2160:0:540:color=0xf8f7f2[b];[a][b]hstack=inputs=2[v]',
        '-map','[v]','-frames:v',str(last-first),'-an','-c:v','libx264','-threads','4',
        '-crf','16','-pix_fmt','yuv420p',str(target)],check=True)
    movies['AB']=acquisition_ab.verify_movie(target,last-first,3840,2160)
    result={'kind':'locating_trace_silent_comparison','trace_sha':patch['plan']['trace_sha'],
        'patch_sha':patch['patch_sha'],'baseline_spec_sha':old_request['spec_sha'],
        'ranges':ranges,'movies':movies,'comparison_layout':'A left / B right; 4K canvas, 1080p panels',
        'baseline_review':'NEEDS_REVISION; no approval inherited',
        'loop_policy':'three literal repeats at real speed; reset is an editorial cut',
        'human_visual_review':'PENDING','listening_review':'DEFERRED_BY_USER',
        'public_render_ready':False,'integrated_full_film':False}
    write(out/'comparison-receipt.json',result)
    write(out/'human-review.json',{'reviewer':None,'movie_sha':movies['B']['sha256'],
        'trace_sha':patch['plan']['trace_sha'],'status':'PENDING','feedback':None,
        'questions':['Does scanning resemble attention while solving?',
            'Is approach to the next candidate natural?', 'Is deceleration appropriately timed?',
            'Does the brief fill feel like recognizing a word?', 'Does search resume smoothly?',
            'Are same-line and cross-line camera movements natural?',
            'Does the camera support attention without showing off?',
            'Does acquisition settle clearly?', 'Is acquisition-to-lift continuous?',
            'Does B reduce uniform motion and stutter compared with A?'],
        'scope':'locating picture only','public_render_ready':False})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('render_config');p.add_argument('baseline')
    p.add_argument('baseline_sha');p.add_argument('output');a=p.parse_args()
    result=prepare(read(a.render_config),a.baseline,a.baseline_sha,a.output)
    print({'outputs':list(result['movies']),'human_visual_review':'PENDING'})
