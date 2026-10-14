"""Minimal original cues and an exact voice reference mix for P4 internal review."""
import argparse
import math
from pathlib import Path
import wave
import xml.etree.ElementTree as ET

import numpy as np
from scripts.voice_delivery import sha256
from video_contracts import read, write


def wav(path,data):
    if Path(path).exists():raise FileExistsError('Preserve existing audio')
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000)
        out.writeframes(np.rint(np.clip(data,-1,32767/32768)*32768).astype('<i2').tobytes())


def prepare_audio(plan,output):
    out=Path(output).resolve(); out.mkdir(parents=True,exist_ok=False)
    n=plan['duration_frames']*2000
    voice=np.zeros(n);sfx=np.zeros(n);transitions=np.zeros(n)
    for v in plan['voices']:
        if sha256(v['path'])!=v['audio_sha256']:raise ValueError('Source voice changed')
        with wave.open(v['path'],'rb') as media:
            if (media.getframerate(),media.getnchannels(),media.getsampwidth())!=(48000,1,2):raise ValueError('Unexpected WAV profile')
            raw=media.readframes(media.getnframes());samples=np.frombuffer(raw,dtype='<i2').astype(float)/32768
        a=v['start_frame']*2000;b=a+len(samples)
        if b!=v['end_frame']*2000 or b>n:raise ValueError('Voice would be truncated or retimed')
        voice[a:b]=samples
    events=[]
    for row in plan['scenes']:
        if row['kind']=='evidence':at=row['start_frame']+round(1.05*24)
        elif row['kind']=='comparison' and row['effect']=='eliminate':at=row['start_frame']+row['decision_frame']
        else:continue
        # Original procedural dry cue; no external recordings, licences or melody borrowed.
        time=np.arange(2400)/48000;rng=np.random.default_rng(at)
        cue=(.045*rng.standard_normal(len(time))+.025*np.sin(2*np.pi*840*time))*np.exp(-time*130)
        cue*=np.minimum(time/.002,1)
        start=at*2000;end=min(n,start+len(cue));sfx[start:end]+=cue[:end-start]
        events.append(dict(frame=at,kind=row['kind'],scene_id=row['id']))
    # Sparse two-tone transition sound, used only on memory cards. No teaching bed.
    for row in plan['scenes']:
        if row['kind']!='recall':continue
        length=min((row['end_frame']-row['start_frame'])*2000,96000)
        time=np.arange(length)/48000
        notes=sum(.012*np.sin(2*np.pi*f*time)*np.exp(-time*2.8) for f in (523.251,783.991))
        notes*=np.minimum(time/.01,1)
        a=row['start_frame']*2000;transitions[a:a+length]+=notes
    for name,data in [('VOICE_REFERENCE.wav',voice),('SFX_ORIGINAL.wav',sfx),('TRANSITIONS_ORIGINAL.wav',transitions),('REVIEW_MIX.wav',voice+sfx+transitions)]:wav(out/name,data)
    receipt=dict(schema='episode-audio/v1',sample_rate=48000,duration=plan['duration'],frames=plan['duration_frames'],
        voice_samples_changed=False,voice_time_stretch=False,voice_count=len(plan['voices']),
        cues=events,transition_sound='original_procedural_two_tone_not_Chopin',
        source_recording_license='no_third_party_audio_samples',
        files={p.name:dict(path=str(p),sha256=sha256(p)) for p in out.glob('*.wav')},
        listening_review='PENDING',public_render_ready=False)
    write(out/'AUDIO_RECEIPT.json',receipt);return receipt


def interchange(plan,picture,audio,path):
    """Native Premiere-importable edit list; source WAVs stay as 19 separate clips."""
    root=ET.Element('xmeml',version='5');sequence=ET.SubElement(root,'sequence',id='p4-internal')
    def leaf(node,key,value):ET.SubElement(node,key).text=str(value)
    def rate(node):r=ET.SubElement(node,'rate');leaf(r,'timebase',24);leaf(r,'ntsc','FALSE')
    leaf(sequence,'name','P4_INTERNAL_REVIEW');leaf(sequence,'duration',plan['duration_frames']);rate(sequence)
    media=ET.SubElement(sequence,'media');video=ET.SubElement(media,'video');format=ET.SubElement(video,'format');sample=ET.SubElement(format,'samplecharacteristics');rate(sample)
    for k,v in [('width',1920),('height',1080),('anamorphic','FALSE'),('pixelaspectratio','square'),('fielddominance','none')]:leaf(sample,k,v)
    sound=ET.SubElement(media,'audio');leaf(sound,'numOutputChannels',2)
    def clip(track,id,path,start,end,kind):
        node=ET.SubElement(track,'clipitem',id=id);leaf(node,'name',Path(path).name);leaf(node,'enabled','TRUE');leaf(node,'duration',end-start);rate(node)
        for k,v in [('start',start),('end',end),('in',0),('out',end-start)]:leaf(node,k,v)
        f=ET.SubElement(node,'file',id='file-'+id);leaf(f,'name',Path(path).name);leaf(f,'pathurl',Path(path).resolve().as_uri());rate(f);leaf(f,'duration',end-start)
        fm=ET.SubElement(f,'media');section=ET.SubElement(fm,kind);sc=ET.SubElement(section,'samplecharacteristics')
        if kind=='audio':leaf(sc,'depth',16);leaf(sc,'samplerate',48000);leaf(section,'channelcount',1)
        else:
            rate(sc);leaf(sc,'width',1920);leaf(sc,'height',1080);leaf(sc,'pixelaspectratio','square');leaf(sc,'fielddominance','none')
        st=ET.SubElement(node,'sourcetrack');leaf(st,'mediatype',kind);leaf(st,'trackindex',1)
    clip(ET.SubElement(video,'track'),'picture',picture,0,plan['duration_frames'],'video')
    track=ET.SubElement(sound,'track')
    for v in plan['voices']:clip(track,v['id'],v['path'],v['start_frame'],v['end_frame'],'audio')
    for i,name in enumerate(('SFX_ORIGINAL.wav','TRANSITIONS_ORIGINAL.wav')):
        clip(ET.SubElement(sound,'track'),'original-'+str(i),audio['files'][name]['path'],0,plan['duration_frames'],'audio')
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--picture',type=Path,required=True)
    a=p.parse_args();plan=read(a.plan);audio=prepare_audio(plan,a.output);interchange(plan,a.picture,audio,a.output/'P4_PREMIERE.xml')


if __name__=='__main__':main()
