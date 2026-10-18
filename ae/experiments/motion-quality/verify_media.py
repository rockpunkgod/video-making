"""Check actual encoded pictures and make review artifacts from those bytes."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from run import read, write, sha256, base
probe=base.probe
from premiere_production.lossless_handoff import packet_binding

def verify(folder):
    p=Path(folder);i=read(p/'TRIAL_INPUT.json');n=read(p/'NATIVE_IDENTITY.json');out=p/'review';out.mkdir(exist_ok=True);total=i['clip_frames']
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);pcm={};result={'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'variants':{},'human_motion_review':'PENDING','human_listening_review':'PENDING'}
    for v in ('A','B'):
        media=Path(read(p/f'RENDER_{v}.json')['output']);picture=p/'media'/f'{v}_NATIVE_PICTURE.mp4';pr=probe(media)
        video=next(s for s in pr['streams'] if s['codec_type']=='video')
        assert [video['width'],video['height'],video['r_frame_rate'],int(video['nb_read_frames'])]==[3840,2160,'24/1',total]
        fr=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(media)]))['frames']
        pts=np.array([float(x['best_effort_timestamp_time']) for x in fr]);assert len(pts)==total and np.max(np.abs(pts-np.arange(total)/24))<1e-5
        assert packet_binding(media,'v:0')==packet_binding(picture,'v:0')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(media),'-f','null','-'],check=True)
        pcm[v]=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-map','0:a:0','-ac','1','-ar','48000','-f','s16le','-']),dtype='<i2')
        cap=cv2.VideoCapture(str(media));frames=out/('frames-'+v);frames.mkdir(exist_ok=True);motion=[];prev=None;k=0
        while True:
            ok,bgr=cap.read()
            if not ok:break
            small=cv2.resize(bgr,(960,540));cv2.imwrite(str(frames/f'{k:04}.jpg'),small,[cv2.IMWRITE_JPEG_QUALITY,93]);gray=cv2.cvtColor(cv2.resize(bgr,(480,270)),cv2.COLOR_BGR2GRAY)
            motion.append({'frame':k,'time':k/24,'mean_abs_change':float(np.mean(cv2.absdiff(prev,gray))) if prev is not None else 0,'dark_pixel_fraction':float(np.mean(gray<8))})
            prev=gray;k+=1
        cap.release();assert k==total and max(x['dark_pixel_fraction'] for x in motion)<.25
        with (out/f'{v}_FRAME_CONTINUITY.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=motion[0].keys());writer.writeheader();writer.writerows(motion)
        indices=[0,16,39,72,112,139,176,191,238,270,306,330,376,400,425,452,486,515,557,600,634,700,752,total-1]
        grid=Image.new('RGB',(1920,6*294),'#eeeae2');d=ImageDraw.Draw(grid)
        for j,frame in enumerate(indices):
            x=j%4*480;y=j//4*294;grid.paste(Image.open(frames/f'{frame:04}.jpg').resize((480,270)),(x,y+24));d.text((x+8,y+2),f'{v}  {frame/24:.3f}s  | frame {frame}',font=font,fill='#172128')
        grid.save(out/f'{v}_ENCODED_CONTACT.jpg',quality=93)
        # Every frame in two action handoffs, not just static endpoints.
        for first,last,label in [(60,83,'chunk-search'),(410,433,'camera-handoff'),(500,523,'extraction'),(546,569,'settle'),(745,768,'return'),(768,791,'source-handoff')]:
            grid=Image.new('RGB',(1920,4*204),'#eeeae2');d=ImageDraw.Draw(grid)
            for j,frame in enumerate(range(first,last+1)):
                x=j%6*320;y=j//6*204;grid.paste(Image.open(frames/f'{frame:04}.jpg').resize((320,180)),(x,y+24));d.text((x+6,y+2),f'{v}  f{frame}  {frame/24:.3f}s',font=font,fill='#172128')
            grid.save(out/f'{v}_EVERY_FRAME_{label}.jpg',quality=93)
        result['variants'][v]={'file':str(media),'sha256':sha256(media),'width':3840,'height':2160,'fps':24,'frames':total,'duration':total/24,'frame_timestamps':'PASS','full_decode':'PASS','video_packets_identical_to_native_picture':True,'all_frames_scanned':total,'black_frame_check':'PASS','duplicate_frame_pairs':sum(x['mean_abs_change']<.001 for x in motion[1:]),'duplicate_frame_note':'Expected native reading/result holds; not automatically a frame-drop failure'}
    assert np.array_equal(pcm['A'],pcm['B'])
    takes=[]
    for take in i['voices']:
        with wave.open(take['voice']['path'],'rb') as w:
            raw=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float);assert w.getframerate()==48000 and w.getnchannels()==1
        offset=round((take['voice_start']-i['clip_start'])*48000);clip=pcm['A'][offset:offset+len(raw)].astype(float)
        correlation=float(np.corrcoef(raw,clip)[0,1]);assert correlation>.99
        takes.append({'id':take['id'],'text':take['text'],'correlation':correlation,'offset_samples':offset,'take_samples':len(raw)})
    result['audio']={'decoded_A_B_identical':True,'decoded_pcm_sha256':hashlib.sha256(pcm['A'].tobytes()).hexdigest(),'complete_takes':takes,'speed_change':False,'cut':False,'listening_judgement':'PENDING'}
    # A sequential, labelled review copy; the two native 4K originals above
    # stay untouched and remain the measured technical comparison.
    comparison=p/'media'/'AB_MOTION_QUALITY_COMPARE_4K24.mp4'
    if not comparison.exists():
        fontpath='C\\:/Windows/Fonts/arial.ttf'
        filters=f"[0:v]drawtext=fontfile='{fontpath}':text='A  CURRENT':x=w-tw-90:y=60:fontsize=42:fontcolor=0x374247:box=1:boxcolor=white@0.86:boxborderw=16[v0];[1:v]drawtext=fontfile='{fontpath}':text='B  MOTION':x=w-tw-90:y=60:fontsize=42:fontcolor=0x374247:box=1:boxcolor=white@0.86:boxborderw=16[v1];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]"
        subprocess.run(['ffmpeg','-v','error','-n','-i',result['variants']['A']['file'],'-i',result['variants']['B']['file'],'-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','24','-c:a','aac','-b:a','256k','-movflags','+faststart',str(comparison)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(comparison),'-f','null','-'],check=True)
    cp=probe(comparison);cv=next(s for s in cp['streams'] if s['codec_type']=='video')
    assert [cv['width'],cv['height'],cv['r_frame_rate'],int(cv['nb_read_frames'])]==[3840,2160,'24/1',total*2]
    result['comparison']={'path':str(comparison),'sha256':sha256(comparison),'format':cp,'purpose':'labelled sequential review; native A/B originals are independently available'}
    write(p/'MEDIA_QA.json',result);return result

if __name__=='__main__':
    r=verify(sys.argv[1]);print(json.dumps({'frames':{v:x['frames'] for v,x in r['variants'].items()},'audio':r['audio'],'comparison':r['comparison']['path']},ensure_ascii=False))
