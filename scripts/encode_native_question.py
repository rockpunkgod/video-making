"""Encode validated native lossless frames without changing their timing or composition."""
import argparse
import json
from pathlib import Path
import subprocess
import re

import imageio_ffmpeg
from PIL import Image
from scripts.voice_delivery import sha256
from video_contracts import read, write


def validate_frames(folder, count):
    expected=[f'frame_{i:04d}.tif' for i in range(count)]
    actual=sorted(p.name for p in folder.glob('*.tif'))
    if actual!=expected:raise ValueError('Native frame sequence is incomplete or contains extra frames')
    for name in expected:
        with Image.open(folder/name) as image:
            if image.size!=(1920,1080):raise ValueError('Native review resolution changed')
    return expected


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('revision',type=Path)
    cli.add_argument('--output-name',default='PICTURE_1080.mp4')
    args=cli.parse_args();out=args.revision.resolve();plan=read(out/'PLAN.json')
    if not (out/'FRAMES_DONE.txt').exists():raise ValueError('Native render not complete')
    names=validate_frames(out/'native-frames',plan['duration_frames'])
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.mp4',args.output_name):raise ValueError('Use a local media basename')
    dest=out/args.output_name
    if dest.exists():raise FileExistsError('Preserve previous picture')
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-nostdin','-n','-framerate',str(plan['fps']),
        '-start_number','0','-i',str(out/'native-frames/frame_%04d.tif'),'-frames:v',str(len(names)),
        '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    with (out/'ENCODE_LOG.txt').open('w',encoding='utf-8') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    receipt_name='PICTURE_RECEIPT.json' if args.output_name=='PICTURE_1080.mp4' else dest.with_suffix('.picture.json').name
    write(out/receipt_name,dict(native_frames=len(names),fps=plan['fps'],resolution=[1920,1080],
        duration=plan['duration'],audio=False,picture_sha256=sha256(dest),
        composition_changed=False,timing_changed=False,public_render_ready=False))
    print(json.dumps(dict(picture=str(dest)),ensure_ascii=True))


if __name__=='__main__':main()
