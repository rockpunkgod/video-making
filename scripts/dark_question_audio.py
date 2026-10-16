"""Exact existing WAV placement, voice-only Premiere edit list and review mux."""
import argparse
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from premiere_production.episode_audio import interchange
from scripts.voice_delivery import sha256
from video_contracts import read, write


def voice_only(plan):
    if plan['fps'] != 24 or plan['duration_frames'] != 1680:
        raise ValueError('Expected the 70-second / 24fps review')
    samples=np.zeros(1680*2000,dtype='<i2');previous=0;placements=[]
    for v in plan['voices']:
        if sha256(v['path'])!=v['audio_sha256']:raise ValueError('Original WAV changed')
        with wave.open(v['path'],'rb') as src:
            if (src.getframerate(),src.getnchannels(),src.getsampwidth())!=(48000,1,2):
                raise ValueError('Expected unchanged PCM16 mono 48kHz WAV')
            raw=src.readframes(src.getnframes());data=np.frombuffer(raw,dtype='<i2')
        start=v['start_frame']*2000;end=start+len(data)
        if start<previous or end!=v['end_frame']*2000 or end>len(samples):
            raise ValueError('Overlap, truncation or unaligned voice')
        samples[start:end]=data;previous=end
        placements.append(dict(id=v['id'],start_frame=v['start_frame'],end_frame=v['end_frame'],
            audio_sha256=v['audio_sha256'],sample_exact=True))
    return samples,placements


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('revision',type=Path);cli.add_argument('--mux',action='store_true')
    a=cli.parse_args();out=a.revision.resolve();plan=read(out/'PLAN.json')
    samples,placements=voice_only(plan);audio=out/'VOICE_ONLY_48K.wav';picture=out/'PICTURE_1080.mp4'
    if not a.mux:
        if audio.exists():raise FileExistsError(audio)
        with wave.open(str(audio),'wb') as target:
            target.setparams((1,2,48000,0,'NONE','not compressed'));target.writeframes(samples.tobytes())
        interchange(plan,picture,{},out/'QUESTION_PREMIERE.xml',include_original_cues=False)
        write(out/'VOICE_TIMELINE_RECEIPT.json',dict(placements=placements,music=False,sfx=False,
            time_stretch=False,gain_change=False,transcript_change=False,audio_sha256=sha256(audio),
            listening_review='PENDING',public_render_ready=False))
        return
    with wave.open(str(audio),'rb') as media:
        if media.readframes(media.getnframes())!=samples.tobytes():raise ValueError('Reference mix changed')
    dest=out/'QUESTION_REVIEW_1080.mp4'
    if dest.exists():raise FileExistsError(dest)
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([exe,'-hide_banner','-nostdin','-n','-i',str(picture),'-i',str(audio),
        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','320k','-movflags','+faststart',str(dest)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    # Decode the delivered AAC and compare each actual voice window, not metadata alone.
    raw=subprocess.run([exe,'-v','error','-i',str(dest),'-map','0:a:0','-f','s16le','-ac','1','-ar','48000','-'],capture_output=True,check=True).stdout
    decoded=np.frombuffer(raw,dtype='<i2').astype(float);checks=[]
    for v in plan['voices']:
        start=v['start_frame']*2000;end=v['end_frame']*2000
        x=samples[start:end].astype(float);y=decoded[start:end]
        if len(y)!=len(x):raise ValueError('Encoded audio truncated')
        corr=float(np.corrcoef(x,y)[0,1]);rms=float(np.sqrt(np.mean(y*y)))
        if not corr>.98 or not rms>10:raise ValueError('Encoded voice absent or wrongly timed')
        checks.append(dict(id=v['id'],correlation=corr,rms_pcm16=rms))
    write(out/'ENCODED_VOICE_AUDIT.json',dict(checks=checks,sha256=sha256(dest),
        mode='native_AE_picture_exact_voice_reference_mux',listening_review='PENDING',public_render_ready=False))
    print(str(dest))


if __name__=='__main__':main()
