"""Consume one explicit copy correction from the normal voice/align/prepare chain."""
import json,sys
from pathlib import Path
from run import Trial,read,write,sha256,HERE

def main(folder,copy_folder):
    t=Trial(folder);p=t.folder;source=Path(copy_folder).resolve();plan=read(source/'AV_PLAN.json');i=t.i;n=read(p/'NATIVE_IDENTITY.json')
    if (p/'FINAL_COPY_COMPLETE.json').exists():raise FileExistsError('Inspect completed copy patch')
    old=next(v for v in i['full_question']['voices'] if v['id']=='SC14_1')
    new=next(v for v in plan['segments'] if v['id']=='SC14_1');scene=next(s for s in plan['scenes'] if s['id']=='SC14')
    if new['text']!='四项检查完，选D。':raise ValueError('Exact user correction required')
    for s in i['full_question']['scenes']:
        if s['id']!='SC14' and s!=next(x for x in plan['scenes'] if x['id']==s['id']):raise ValueError('Unrelated scene timing changed')
    cues=[q for q in plan['cues'] if q['segment']=='SC14_1']
    payload={'old':old,'new':new,'scene':scene,'cues':cues,'source_comp':n['B_source'],'wrapper':n['full_question_comp'],'start':i['full_question']['start'],'old_event':next(s for s in i['full_question']['scenes'] if s['id']=='SC14')['event_time']}
    code='var I='+json.dumps(payload,ensure_ascii=False)+';'+r'''
var c=app.project.itemByID(I.source_comp),w=app.project.itemByID(I.wrapper),captions=[],audio=[];
for(var j=1;j<=c.numLayers;j++)if(c.layer(j).name.indexOf('CAPTION_SC14_1_')===0)captions.push(c.layer(j));
if(captions.length!==I.cues.length)throw Error('Caption identity changed');
captions.sort(function(a,b){return a.inPoint-b.inPoint;});
for(var j=0;j<captions.length;j++){var l=captions[j],cue=I.cues[j],d=l.property('Source Text').value;d.text=cue.display_lines.join('\r');l.property('Source Text').setValue(d);l.name='CAPTION_'+cue.id;l.inPoint=cue.start;l.outPoint=cue.end;l.comment=JSON.stringify({kind:'audio_aligned_exact_caption',segment:cue.segment,text:cue.text,start:cue.start,end:cue.end});}
for(var j=1;j<=w.numLayers;j++){var l=w.layer(j);if(l.source instanceof FootageItem&&l.source.file&&l.source.file.fsName===new File(I.old.voice.path).fsName)audio.push(l);}
if(audio.length!==1)throw Error('Expected exactly one complete final voice take');var footage=app.project.importFile(new ImportOptions(new File(I.new.voice.path)));audio[0].replaceSource(footage,false);audio[0].startTime=I.new.voice_start-I.start;audio[0].inPoint=audio[0].startTime;audio[0].outPoint=I.new.voice_end-I.start;
for(var j=0;j<4;j++){var l=c.layer('camp_OPTION_'+'ABCD'.charAt(j)),p=l.property('Source Text'),key=p.nearestKeyIndex(I.old_event);if(Math.abs(p.keyTime(key)-I.old_event)>.001)throw Error('Original final judgment key missing');var d=p.keyValue(key);p.removeKey(key);p.setValueAtTime(I.scene.event_time,d);key=p.nearestKeyIndex(I.scene.event_time);p.setInterpolationTypeAtKey(key,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}
c.layer('FINAL_camp').inPoint=I.scene.event_time;
var duration=I.scene.end-I.start+1;w.duration=duration;
for(var j=1;j<=w.numLayers;j++){var l=w.layer(j);if(l.source instanceof CompItem){var p=l.property('ADBE Time Remapping');while(p.numKeys>1)p.removeKey(p.numKeys);p.setValueAtTime(I.scene.end-I.start-1/24,I.scene.end-1/24);p.setValueAtTime(I.scene.end-I.start,I.scene.end-1/24);p.setInterpolationTypeAtKey(1,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);p.setInterpolationTypeAtKey(2,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.HOLD);p.setInterpolationTypeAtKey(3,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);l.outPoint=duration;}else if(l.name==='ORIGINAL_CANVAS')l.outPoint=duration;}
w.comment=JSON.stringify({source_start:I.start,last_source_time:I.scene.end-1/24,complete_takes:13,copy_revision:'四项检查完，选D。',human_review:'PENDING'});app.project.save();return {duration:duration,frames:Math.round(duration*24),event:I.scene.event_time,cues:I.cues,voice:I.new};
'''
    write(p/'BEFORE_FINAL_COPY_NATIVE_IDENTITY.json',n)
    r=t.mutate('Synchronize exact final sentence, complete voice and captions',lambda:t.h.js(code,'Update final sentence'))
    i['full_question']['end']=scene['end'];i['full_question']['frames']=r['frames'];i['full_question']['scenes'][-1]=scene
    i['full_question']['voices']=[new if v['id']=='SC14_1' else v for v in i['full_question']['voices']]
    i['copy_revision']={'folder':str(source),'plan_sha256':sha256(source/'AV_PLAN.json'),'changed_take':'SC14_1','exact_text':new['text']}
    write(p/'TRIAL_INPUT.json',i);t.i=i;n['full_question_frames']=r['frames'];n['input_sha256']=sha256(p/'TRIAL_INPUT.json');n['code_binding']=t.binding();n['final_copy']=i['copy_revision'];write(p/'NATIVE_IDENTITY.json',n)
    write(p/'FINAL_COPY_COMPLETE.json',{'result':r,'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'human_listening_review':'PENDING','asr_limit':'Unprompted small-model ASR did not reliably resolve the final English letter; forced alignment is not pronunciation approval.'})
    print(json.dumps(r,ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
