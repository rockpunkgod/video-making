"""One user-selected local music bed below frozen narration. No music generation."""
import argparse
from pathlib import Path
import subprocess
from video_contracts import read,write
from creative_os.hero import file_sha
from creative_os.passage_video import validate_plan
from scripts.generate_anchored_passage_voice import measure


def mix(request):
    plan=read(request['plan']);bundle=read(request['bundle']);validate_plan(plan,bundle,read(request['status']))
    if file_sha(request['music'])!=request['music_sha'] or file_sha(request['voice'])!=request['voice_sha']:
        raise ValueError('Music or voice source changed')
    out=Path(request['output']).resolve()
    if out.exists():raise ValueError('Preserve previous mix')
    out.mkdir(parents=True);duration=plan['canvas']['duration'];sequence=None
    if request.get('sequence_plan'):
        from creative_os.passage_sequence import validate_sequence
        sequence=read(request['sequence_plan']);validate_sequence(sequence,plan,bundle,read(request['status']))
        duration=sequence['canvas']['duration']
    # A gentle overlap of the same recording maintains a continuous bed if needed.
    # The input must be at least 20 s; this renderer supports at most one repeat.
    import json
    music_duration=float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'format=duration','-of','json',request['music']],encoding='utf-8'))['format']['duration'])
    if music_duration<20 or duration>2*music_duration-6:raise ValueError('Music length outside one-repeat contract')
    prefix='[0:a]'
    if duration>music_duration:
        prefix='[0:a]asplit=2[x][y];[x][y]acrossfade=d=6:c1=tri:c2=tri,'
    else:prefix+='anull,'
    # loudnorm supports TP >= -9; normalize there, then apply a fixed -9 dB bed gain.
    filters=prefix+f'atrim=duration={duration},loudnorm=I=-22:TP=-9:LRA=5,volume=-9dB,afade=t=in:d=3,afade=t=out:st={duration-4}:d=4[m]'
    subprocess.run(['ffmpeg','-v','error','-n','-i',request['music'],'-filter_complex',filters,'-map','[m]',
        '-ar','48000','-ac','2','-c:a','pcm_s16le',str(out/'music.wav')],check=True)
    subprocess.run(['ffmpeg','-v','error','-n','-i',request['voice'],'-i',str(out/'music.wav'),'-filter_complex',
        '[0:a]pan=stereo|c0=c0|c1=c0[v];[v][1:a]amix=inputs=2:normalize=0:duration=longest[m]',
        '-map','[m]','-ar','48000','-c:a','pcm_s16le',str(out/'mix.wav')],check=True)
    measurement=measure(out/'mix.wav')
    if float(measurement['input_tp'])>=-1:raise ValueError('Mix needs peak correction; keep failed candidate for inspection')
    validate_plan(plan,bundle,read(request['status']))
    receipt={'plan_sha':plan['plan_sha'],'voice_sha':request['voice_sha'],'mix':str(out/'mix.wav'),
        'sequence_sha':sequence['sequence_sha'] if sequence else None,
        'mix_sha':file_sha(out/'mix.wav'),'music':request['music'],'music_sha':request['music_sha'],
        'music_measurement':measure(out/'music.wav'),'measurement':measurement,'music_target_lufs':-31,
        'music_loop_overlap_seconds':6 if duration>music_duration else 0,
        'music_release':'UNCONFIRMED_INTERNAL_ONLY','public_render_ready':False}
    write(out/'receipt.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request');a=p.parse_args();mix(read(a.request))
