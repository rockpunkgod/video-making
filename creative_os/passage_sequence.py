"""Show the untouched frozen task before consuming its reviewed explanation."""
import math
import wave
import subprocess
from pathlib import Path
from video_contracts import read,write,sha
from .hero import file_sha
from .passage_video import validate_plan,wrap


def question_first(plan,bundle,status,passage_seconds=12,question_seconds=8):
    validate_plan(plan,bundle,status)
    if not (8<=passage_seconds<=60 and 6<=question_seconds<=30):
        raise ValueError('Explicit, bounded original-task preview times required')
    from PIL import ImageFont
    p=bundle['payload'];cards={};entries=[];at=0
    def add(entry,duration):
        nonlocal at
        duration=math.ceil(duration*24)/24
        entries.append(dict(entry,start=at,duration=duration));at+=duration
    def node(name,value,x,y,width,size,ref,english=False):
        font=ImageFont.truetype(plan['fonts']['english' if english else 'chinese'],size)
        if not english:
            try:font.set_variation_by_name(b'Regular')
            except (AttributeError,OSError):pass
        text=wrap(value,font,width);height=len(text.splitlines())*size*1.24
        if y+height>1000 or font.getlength(max(text.splitlines(),key=font.getlength))>width+1:
            raise ValueError('Original task needs another readable page')
        return dict(name=name,text=text,x=x,y=y,w=width,h=height,size=size,
                    font='Georgia' if english else 'NotoSansSC-Regular',origin=ref)
    lines=wrap(p['passage'],ImageFont.truetype(plan['fonts']['english'],32),800).splitlines()
    for index in range(0,len(lines),42):
        page=lines[index:index+42];half=math.ceil(len(page)/2);cid='original-passage-'+str(index//42+1)
        nodes=[node('HEADER','2025 全国一卷 · 阅读 D · 原题',110,48,1700,28,'editorial_label')]
        for col,part in enumerate((page[:half],page[half:])):
            if part:nodes.append(node('PASSAGE_'+str(col),'\n'.join(part),110+900*col,145,800,32,'/payload/passage',True))
        cards[cid]=dict(kind='original_passage',nodes=nodes,pause_hint=True)
        add({'kind':'original','card_id':cid},passage_seconds)
    shown=[]
    for scene in plan['scenes']:
        qid=scene['question_id']
        if qid not in shown:
            question=next(q for q in p['questions'] if q['question_id']==qid);qi=p['questions'].index(question)
            cid='original-question-'+str(question['number'])
            nodes=[node('HEADER',scene['heading'],110,48,1700,26,'scene.heading'),
                   node('QUESTION',question['stem'],110,104,1700,38,'/payload/questions/'+str(qi)+'/stem')]
            for i,(letter,text) in enumerate(question['options'].items()):
                nodes.append(node('OPTION_'+letter,letter+'  '+text,170,330+i*134,1520,42,
                                  '/payload/questions/'+str(qi)+'/options/'+letter))
            cards[cid]=dict(kind='original_question',question_id=qid,nodes=nodes,pause_hint=True)
            add({'kind':'original','card_id':cid,'question_id':qid},question_seconds);shown.append(qid)
        elif entries[-1].get('question_id')!=qid:
            raise ValueError('Question groups must be contiguous; no implicit reordering')
        add({'kind':'explanation','segment_id':scene['segment_id'],'question_id':qid,
             'source_start':scene['start'],'segment_sha':scene['segment_sha']},scene['duration'])
    result=dict(version='0.1.0',kind='question_first_passage',base_plan_sha=plan['plan_sha'],
                lesson_binding_sha=bundle['semantic_binding_sha'],cards=cards,entries=entries,
                preview_seconds={'passage':passage_seconds,'question':question_seconds},
                canvas=dict(plan['canvas'],duration=at),public_render_ready=False,
                preview_is_full_reading_time=False)
    result['sequence_sha']=sha(result);return result


def validate_sequence(sequence,plan,bundle,status):
    expected=question_first(plan,bundle,status,sequence['preview_seconds']['passage'],sequence['preview_seconds']['question'])
    if sequence!=expected:raise ValueError('Original-task order, copy or timing changed')


def assemble_question_first(sequence,plan,bundle,status_path,base_assembly,card_receipts,output):
    """Reuse exact explanation pixels/captions; insert neutral native original cards."""
    validate_sequence(sequence,plan,bundle,read(status_path))
    if base_assembly['plan_sha']!=plan['plan_sha']:raise ValueError('Wrong explanation assembly')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous original-first assembly')
    output.mkdir(parents=True);clips=[];captions=[];voices=[]
    for entry in sequence['entries']:
        if entry['kind']=='original':
            cid=entry['card_id'];receipt=card_receipts[cid]
            if (receipt['card_sha']!=sha(sequence['cards'][cid]) or receipt['sequence_sha']!=sequence['sequence_sha']
                    or file_sha(receipt['frame'])!=receipt['frame_sha']):raise ValueError('Original card changed')
            clip=output/(cid+'.mp4')
            subprocess.run(['ffmpeg','-v','error','-n','-loop','1','-framerate','24','-i',receipt['frame'],
                '-frames:v',str(round(entry['duration']*24)),'-an','-c:v','libx264','-threads','2',
                '-preset','veryfast','-crf','17','-pix_fmt','yuv420p',str(clip)],check=True)
        else:
            scene=next(s for s in plan['scenes'] if s['segment_id']==entry['segment_id'])
            original=base_assembly['clips'][plan['scenes'].index(scene)];clip=Path(original['path'])
            if file_sha(clip)!=original['sha256']:raise ValueError('Explanation pixels changed')
            shift=entry['start']-scene['start']
            captions.extend(dict(c,start=c['start']+shift,end=c['end']+shift) for c in original['captions'])
            voices.append((entry['start']+scene['voice_start'],scene['voice']))
        clips.append(dict(entry,path=str(clip),sha256=file_sha(clip)))
    # ffconcat quote escaping is file syntax, never shell interpolation.
    def quote(path):return "'"+str(path).replace('\\','/').replace("'","'\\''")+"'"
    (output/'concat.txt').write_text(''.join('file '+quote(c['path'])+'\n' for c in clips),encoding='utf-8')
    visual=output/'question-first-visual.mp4'
    subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(output/'concat.txt'),
                    '-c','copy','-movflags','+faststart',str(visual)],check=True)
    voice=output/'question-first-voice.wav'
    with wave.open(str(voice),'wb') as target:
        target.setparams((1,2,48000,0,'NONE','not compressed'));written=0
        for start,item in voices:
            frame=round(start*48000)
            if frame<written or file_sha(item['path'])!=item['sha256']:raise ValueError('Shifted voice changed or overlaps')
            target.writeframes(b'\0'*(2*(frame-written)))
            with wave.open(item['path'],'rb') as source:
                if (source.getnchannels(),source.getsampwidth(),source.getframerate())!=(1,2,48000):raise ValueError('Voice format changed')
                data=source.readframes(source.getnframes())
            target.writeframes(data);written=frame+len(data)//2
        target.writeframes(b'\0'*(2*(round(sequence['canvas']['duration']*48000)-written)))
    validate_sequence(sequence,plan,bundle,read(status_path))
    write(output/'captions.json',{'copy_sha':plan['copy_sha'],'cues':captions,'timing_is_estimated':True})
    result=dict(plan_sha=plan['plan_sha'],sequence_sha=sequence['sequence_sha'],visual=str(visual),visual_sha=file_sha(visual),
                voice=str(voice),voice_sha=file_sha(voice),clips=clips,public_render_ready=False)
    write(output/'assembly.json',result);return result
