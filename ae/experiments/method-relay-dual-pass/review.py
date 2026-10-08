"""Ordered frame inspection of the actual movie, with exact source frame ordinals."""
import argparse
import math
import subprocess
from PIL import Image, ImageDraw
from run import local, file_sha
from video_contracts import write


def review(movie, output, fps=2, windows=None):
    movie=local(movie);output=local(output)
    if fps not in (1,2,3,4,6,8,12,24):raise ValueError('Sample at a divisor of the native 24 fps')
    total=int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=nb_frames','-of','default=nw=1:nk=1',str(movie)]))
    windows=windows or [(0,total/24)]
    if any(not 0<=a<b<=total/24 for a,b in windows):raise ValueError('Read the actual complete interval')
    ordinals=[i for i in range(0,total,24//fps) if any(a<=i/24<b for a,b in windows)]
    clauses=[f'between(n,{math.ceil(a*24)},{math.ceil(b*24)-1})' for a,b in windows]
    select='('+ '+'.join(clauses)+f')*not(mod(n,{24//fps}))'
    output.mkdir(parents=True,exist_ok=False)
    subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf',f"select='{select}',scale=640:360",
        '-fps_mode','vfr',str(output/'frame-%04d.png')],check=True)
    frames=sorted(output.glob('frame-*.png'))
    if len(frames)!=len(ordinals):raise ValueError('Frame inspection lost native ordinals')
    sheets=[]
    for base in range(0,len(frames),8):
        sheet=Image.new('RGB',(1280,1544),'#eeeae3');draw=ImageDraw.Draw(sheet)
        for j,path in enumerate(frames[base:base+8]):
            x=(j%2)*640;y=(j//2)*386
            with Image.open(path) as frame:sheet.paste(frame,(x,y))
            draw.text((x+10,y+364),f'frame {ordinals[base+j]} / {ordinals[base+j]/24:.3f}s',fill='#243530')
        name=f'motion-{base//8+1:02d}.jpg';sheet.save(output/name,quality=92);sheets.append(name)
    result={'movie_sha256':file_sha(movie),'fps':fps,'source_frame_ordinals':ordinals,'windows':windows,
        'frames':len(frames),'sheets':sheets,'scope':'ordered_rendered_frame_inspection_not_human_playback',
        'human_viewing_review':'PENDING','public_render_ready':False}
    write(output/'review-input.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('movie');p.add_argument('output')
    p.add_argument('--fps',type=int,default=2);p.add_argument('--window',nargs=2,type=float,action='append')
    a=p.parse_args();result=review(a.movie,a.output,a.fps,a.window)
    print({'frames':result['frames'],'sheets':len(result['sheets'])})
