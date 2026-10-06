"""Local assembly of verified native scenes and frozen narration; internal only.

ASR supplies approximate timing anchors, never subtitle wording. The caption
projection and final media require listening/editorial review before publication.
"""
from difflib import SequenceMatcher
from pathlib import Path
import re
import subprocess
import wave
from video_contracts import read, write, sha
from creative_os.hero import file_sha
from .passage_video import validate_plan


def normalized_chars(text):
    return [(i,c.lower()) for i,c in enumerate(text) if c.isalnum()]


def timing_centres(text, diagnostic, duration):
    """Estimate authored character centres from ASR without changing wording."""
    authored=normalized_chars(text)
    spoken=[]
    for row in diagnostic['rows']:
        for word in row['words']:
            chars=normalized_chars(word['word'])
            for j,(_,c) in enumerate(chars):
                spoken.append((c,word['start']+(j+.5)*(word['end']-word['start'])/len(chars)))
    if not authored or not spoken: raise ValueError('Nonempty authored copy and ASR anchors required')
    matcher=SequenceMatcher(None,''.join(c for _,c in authored),''.join(c for c,_ in spoken),autojunk=False)
    anchors={}
    for block in matcher.get_matching_blocks():
        for j in range(block.size): anchors[block.a+j]=spoken[block.b+j][1]
    if len(anchors)<max(2,len(authored)*.25): raise ValueError('Too few ASR anchors for estimated captions')
    # Boundary anchors make interpolation total, including foreign words misheard by ASR.
    anchors[-1]=0.;anchors[len(authored)]=duration
    ordered=sorted(anchors);centres={}
    for a,b in zip(ordered,ordered[1:]):
        for i in range(max(0,a),min(b+1,len(authored))):
            centres[i]=anchors[a]+(anchors[b]-anchors[a])*(i-a)/(b-a)
    return authored,centres


def caption_cues(text, diagnostic, duration, max_chars=27):
    """Preserve exact characters; interpolate only unmatched ASR timing gaps."""
    authored,centres=timing_centres(text,diagnostic,duration)
    pieces=re.findall(r'.*?[，。！？；,!?;：:]|.+$',text,re.S)
    chunks=[];pending=''
    for piece in pieces:
        if pending and len(pending)+len(piece)>max_chars:chunks.append(pending);pending=''
        while len(piece)>max_chars:
            if pending:chunks.append(pending);pending=''
            chunks.append(piece[:max_chars]);piece=piece[max_chars:]
        pending+=piece
    if pending:chunks.append(pending)
    if ''.join(chunks)!=text:raise ValueError('Subtitle copy mutation')
    cues=[];offset=0
    for chunk in chunks:
        indices=[i for i,(position,_) in enumerate(authored) if offset<=position<offset+len(chunk)]
        if not indices:raise ValueError('Caption contains only punctuation')
        start=0. if indices[0]==0 else (centres[indices[0]-1]+centres[indices[0]])/2
        last=indices[-1];end=duration if last==len(authored)-1 else (centres[last]+centres[last+1])/2
        if end<=start:raise ValueError('Nonpositive caption interval')
        cues.append({'start':start,'end':end,'text':chunk});offset+=len(chunk)
    return cues


def ass_time(seconds):
    cs=round(seconds*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'


def write_ass(path,cues,offset=.4):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Bound,Passage Caption,50,&H00303524,&H00303524,&H00F2F8FA,&H00F2F8FA,0,0,0,0,100,100,0,0,1,0,0,2,150,150,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    rows=[]
    for c in cues:
        if any(x in c['text'] for x in ('{','}','\\','\n','\r')):
            raise ValueError('Unsupported ASS control characters in frozen copy')
        rows.append(f"Dialogue: 0,{ass_time(c['start']+offset)},{ass_time(c['end']+offset)},Bound,,0,0,0,,{c['text']}")
    Path(path).write_text(header+'\n'.join(rows)+'\n',encoding='utf-8-sig')


def verified_head(scene,receipt):
    # Style probes use 24 seconds; duration is resolved only after voice recording.
    style={k:v for k,v in scene.items() if k not in ('start','duration','voice','voice_start','timing_kind')}
    style['duration']=24
    if (receipt['scene_sha']!=sha(style) or receipt['segment_sha']!=scene['segment_sha']
            or receipt['static_hold_verified'] is not True
            or file_sha(receipt['video'])!=receipt['video_sha']
            or file_sha(receipt['hold_frame'])!=receipt['hold_sha']):
        raise ValueError('Native motion or verified hold changed')
    if receipt.get('reuse_proof'):
        proof=receipt['reuse_proof']
        if file_sha(proof['receipt'])!=proof['receipt_sha']:
            raise ValueError('Original native reuse receipt changed')


def assemble(plan,bundle,status_path,heads_root,voice_root,output,caption_font,motion=None,direction=None):
    output=Path(output).resolve()
    validate_plan(plan,bundle,read(status_path))
    if direction is not None:
        from .passage_director import validate_direction
        validate_direction(direction,plan,bundle)
        if motion is None: raise ValueError('Directed presentation needs its phrase clock')
    if motion is not None:
        from .passage_motion import validate_motion
        validate_motion(motion,plan,voice_root)
    if caption_font['family']!='Passage Caption' or file_sha(caption_font['font'])!=caption_font['font_sha']:
        raise ValueError('Frozen regular caption font required')
    output.mkdir(parents=True,exist_ok=True)
    clips=[];captions=[]
    for scene in plan['scenes']:
        validate_plan(plan,bundle,read(status_path))
        sid=scene['segment_id'];head=read(Path(heads_root)/sid/'receipt.json');verified_head(scene,head)
        if head.get('direction_sha') != (direction['direction_sha'] if direction else None):
            raise ValueError('Native direction is missing or stale')
        if head.get('reuse_proof') and head['reuse_proof']['scene_direction_sha']!=sha(direction['scenes'][sid]):
            raise ValueError('Reused head no longer has identical visible nodes')
        diagnostic=read(Path(voice_root)/sid/'asr.json')
        if diagnostic['audio_sha']!=scene['voice']['sha256']:raise ValueError('Stale ASR diagnostic')
        cues=caption_cues(scene['voice']['text'],diagnostic,scene['voice']['duration'])
        folder=output/sid;receipt=folder/'receipt.json'
        events=motion['scenes'][sid] if motion is not None else []
        if motion is not None and head.get('presentation_sha')!=motion['presentation_sha']:
            raise ValueError('Motion retiming requires its exact native presentation')
        binding=sha({'plan':plan['plan_sha'],'scene':sid,'head':head,'cues':cues,'caption_font':caption_font,'motion':events})
        if receipt.exists():
            prior=read(receipt)
            if prior['input_sha']!=binding or file_sha(prior['path'])!=prior['sha256']:
                raise ValueError('Existing assembled clip changed')
            clips.append(prior);captions.extend(prior['captions']);continue
        if folder.exists():raise ValueError('Uncertain assembly exists; reconcile first')
        folder.mkdir();write_ass(folder/'bound.ass',cues,scene['voice_start'])
        # Local font directory prevents DirectWrite resolving a variable font to Thin.
        import shutil
        (folder/'fonts').mkdir();shutil.copyfile(caption_font['font'],folder/'fonts/regular.ttf')
        dest=folder/'scene.mp4';frames=round(scene['duration']*24)
        from .passage_motion import time_expression
        clock=time_expression(events)
        native_end=(events[-1]['native_start']+.5+1/24 if events else .5+1/24) if motion is not None else 4
        subprocess.run(['ffmpeg','-v','error','-n','-threads','2','-i',head['video'],
            '-vf',f"trim=end={native_end},setpts='{clock}',fps=24,tpad=stop_mode=clone:stop_duration={scene['duration']},subtitles=bound.ass:fontsdir=fonts",
            '-frames:v',str(frames),'-an','-c:v','libx264','-threads','2','-preset','veryfast',
            '-crf','17','-pix_fmt','yuv420p','-r','24',str(dest)],cwd=folder,check=True)
        global_cues=[dict(c,start=c['start']+scene['start']+scene['voice_start'],
                          end=c['end']+scene['start']+scene['voice_start'],segment_id=sid) for c in cues]
        record={'input_sha':binding,'path':str(dest),'sha256':file_sha(dest),'frames':frames,
            'captions':global_cues,'caption_timing':'ASR_anchored_interpolation_estimate',
            'caption_copy_sha':sha(scene['voice']['text']),'ass_sha':file_sha(folder/'bound.ass'),'caption_font_sha':caption_font['font_sha'],
            'motion_events':events,'presentation_sha':head.get('presentation_sha'),
            'independent_listening_review':False,'public_render_ready':False}
        write(receipt,record);clips.append(record);captions.extend(global_cues)
        print('Assembled',sid,scene['duration'],flush=True)
    validate_plan(plan,bundle,read(status_path))
    silent=output/'visual.mp4';master_voice=output/'voice.wav'
    if silent.exists() or master_voice.exists():raise ValueError('Preserve existing final assembly')
    # Relative paths in a generated concat list avoid shell/path escaping entirely.
    (output/'concat.txt').write_text(''.join("file '"+s['segment_id']+"/scene.mp4'\n" for s in plan['scenes']),encoding='utf-8')
    subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','1','-i','concat.txt',
        '-c','copy','-movflags','+faststart',str(silent)],cwd=output,check=True)
    with wave.open(str(master_voice),'wb') as target:
        target.setparams((1,2,48000,0,'NONE','not compressed'));written=0
        for scene in plan['scenes']:
            start=round((scene['start']+scene['voice_start'])*48000)
            if start<written:raise ValueError('Voice overlap')
            target.writeframes(b'\0'*(2*(start-written)))
            with wave.open(scene['voice']['path'],'rb') as source:
                if (source.getnchannels(),source.getsampwidth(),source.getframerate())!=(1,2,48000):
                    raise ValueError('Unexpected voice format')
                data=source.readframes(source.getnframes());target.writeframes(data)
            written=start+len(data)//2
        target.writeframes(b'\0'*(2*(round(plan['canvas']['duration']*48000)-written)))
    write(output/'captions.json',{'copy_sha':plan['copy_sha'],'cues':captions,'timing_is_estimated':True})
    result={'plan_sha':plan['plan_sha'],'visual':str(silent),'visual_sha':file_sha(silent),
        'direction_sha':direction['direction_sha'] if direction else None,
        'voice':str(master_voice),'voice_sha':file_sha(master_voice),'clips':clips,
        'public_render_ready':False,'teaching_release':'HOLD','source_display_release':'HOLD','editorial_release':'HOLD'}
    write(output/'assembly.json',result);return result
