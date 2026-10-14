"""Two-pass delivery loudness after native Premiere export; video is stream-copied."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import shutil
import math


def ffmpeg():
    found=shutil.which('ffmpeg')
    if found:return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def measure(path):
    result=subprocess.run([ffmpeg(),'-hide_banner','-i',str(path),'-vn','-af',
        'loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
    blocks=re.findall(r'\{\s*"input_i".*?\}',result.stderr,re.S)
    if not blocks:raise ValueError('No loudness measurement')
    return json.loads(blocks[-1])


def normalize(source,destination,duration_seconds=None):
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Preserve old delivery')
    if duration_seconds is not None and (type(duration_seconds) not in (int,float)
            or not math.isfinite(duration_seconds) or duration_seconds<=0):
        raise ValueError('Finite positive bound sequence duration required')
    first=measure(source)
    af=('loudnorm=I=-14:TP=-1.2:LRA=11:linear=true:print_format=json:'+':'.join(
        f'{key}={first[value]}' for key,value in [('measured_I','input_i'),('measured_TP','input_tp'),
        ('measured_LRA','input_lra'),('measured_thresh','input_thresh'),('offset','target_offset')]))
    # The caller has already checked all voice slots end within this sequence.
    # Remove normalizer-added tail padding; never retime the video or stretch voice.
    if duration_seconds is not None:af+=f',atrim=duration={duration_seconds},asetpts=PTS-STARTPTS'
    subprocess.run([ffmpeg(),'-v','error','-n','-i',str(source),'-map','0:v:0','-map','0:a:0',
        '-c:v','copy','-af',af,'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(destination)],check=True)
    final=measure(destination)
    if not -15<=float(final['input_i'])<=-13 or float(final['input_tp'])>-1:
        raise ValueError('Encoded delivery loudness outside target; keep output for inspection')
    report=dict(before=first,after=final,video_stream_copied=True,voice_time_stretch=False,
                duration_bound=duration_seconds,public_render_ready=False)
    destination.with_suffix('.loudness.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--duration-seconds',type=float,help='Bound sequence duration after voice-slot end validation')
    a=p.parse_args();r=normalize(a.source,a.destination,a.duration_seconds);print(json.dumps(r['after']))
