"""Ordered whole-interval frame inspection; never substitutes for human playback."""
import argparse
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw
from run import file_sha, research_output
from video_contracts import write


def review(movie, output, fps=4):
    movie=research_output(movie);output=research_output(output)
    if not 1<=fps<=24:raise ValueError('Inspection rate must be 1–24 fps')
    output.mkdir(parents=True,exist_ok=False)
    subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf',f'fps={fps},scale=640:360',
        str(output/'frame-%04d.png')],check=True)
    frames=sorted(output.glob('frame-*.png'));sheets=[]
    for base in range(0,len(frames),8):
        sheet=Image.new('RGB',(1280,4*386),'#eeeae3');draw=ImageDraw.Draw(sheet)
        for j,path in enumerate(frames[base:base+8]):
            x=(j%2)*640;y=(j//2)*386
            with Image.open(path) as frame:sheet.paste(frame,(x,y))
            draw.text((x+10,y+364),f'{(base+j)/fps:.3f}s',fill='#243530')
        target=output/f'motion-{base//8+1:02d}.jpg';sheet.save(target,quality=92);sheets.append(target.name)
    manifest={'movie_sha256':file_sha(movie),'fps':fps,'frames':len(frames),
        'sheets':sheets,'coverage':'whole_interval_ordered_frames',
        'limitation':'Sampling can miss sub-frame artifacts; not real-time playback or human taste approval.',
        'human_viewing_review':'PENDING'}
    write(output/'review-input.json',manifest);return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('movie');p.add_argument('output')
    p.add_argument('--fps',type=int,default=4);args=p.parse_args()
    print(review(args.movie,args.output,args.fps))
