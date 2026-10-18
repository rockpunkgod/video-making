var I=TRIAL_INPUT,N=BASELINE_NATIVE,c=app.project.itemByID(N.B_source),a=app.project.itemByID(N.A_source),full=I.full_question;
if(c.width!==3840||c.height!==2160||c.frameRate!==24)throw Error('Wrong native source');
var audit={word_focus:[],reading_windows:[],query_handoffs:[]},ink=[.09,.13,.16],blue=[.10,.37,.57],orange=[.69,.27,.06];
var s5='function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}';
// Restore the parent camera outside the original bounded trial. The same
// accepted B motion remains inside it; offset continuity decays after its end.
var cam=c.layer('READING_CAMERA'),focus=c.layer('READING_FOCUS');
function bindOutside(prop,ref,inside,endValue){var t0=I.clip_start,te=I.last_source_time;prop.expression=s5+'var o='+ref+';if(time<'+t0+'){o;}else if(time<'+(t0+.5)+'){o*(1-s((time-'+t0+')/.5))+('+inside+')*s((time-'+t0+')/.5);}else if(time<='+te+'){'+inside+';}else{o+('+JSON.stringify(endValue)+'-'+ref.replace(/valueAtTime\(time\)/g,'valueAtTime('+te+')')+')*(1-s((time-'+te+')/.5));}';}
var ref='comp('+JSON.stringify(a.name)+').layer("READING_CAMERA")';
bindOutside(cam.transform.position,ref+'.transform.position.valueAtTime(time)','thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0])+thisComp.layer("MQ_CAMERA_OFFSET").transform.position',cam.transform.position.valueAtTime(I.last_source_time,false));
bindOutside(cam.transform.pointOfInterest,ref+'.transform.pointOfInterest.valueAtTime(time)','thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0])',cam.transform.pointOfInterest.valueAtTime(I.last_source_time,false));
bindOutside(focus.transform.position,'comp('+JSON.stringify(a.name)+').layer("READING_FOCUS").transform.position.valueAtTime(time)','thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0])',focus.transform.position.valueAtTime(I.last_source_time,false));
var aperture=cam.cameraOption.aperture;aperture.expression=s5+'var o='+ref+'.cameraOption.aperture.valueAtTime(time);time<'+I.clip_start+'?o:time<='+I.last_source_time+'?value:o+(10-'+ref+'.cameraOption.aperture.valueAtTime('+I.last_source_time+'))*(1-s((time-'+I.last_source_time+')/.5));';
var query=c.layer('CARRIED_QUERY_SC09L'),prior=query.transform.position.expression;query.transform.position.expression='if(time<'+I.clip_start+'){comp('+JSON.stringify(a.name)+').layer("CARRIED_QUERY_SC09L").transform.position.valueAtTime(time);}else{'+prior+'}';
var prior=query.transform.scale.expression;query.transform.scale.expression='if(time<'+I.clip_start+'){comp('+JSON.stringify(a.name)+').layer("CARRIED_QUERY_SC09L").transform.scale.valueAtTime(time);}else{'+prior+'}';
// Only superseded search animators are removed from this owned copy.
for(var j=1;j<=c.numLayers;j++){
 var l=c.layer(j);if(l.name.indexOf('camp-source-')!==0)continue;
 var aa=l.property('ADBE Text Properties').property('ADBE Text Animators');
 for(var k=aa.numProperties;k>=1;k--){var name=aa.property(k).name;if(name.indexOf('READ_FOCUS_')===0||name.indexOf('RF_CHUNK_reading_line_')===0||name.indexOf('RF_CHUNK_keyword_hit')===0||name.indexOf('MQ_READING_')===0)aa.property(k).remove();}
 var op=l.transform.opacity;op.expression='time<'+I.clip_start+'||time>'+I.last_source_time+'?comp('+JSON.stringify(a.name)+').layer('+JSON.stringify(l.name)+').transform.opacity.valueAtTime(time):value;';
}
function measuredRows(e){var out=[];
 for(var j=1;j<=c.numLayers;j++){var l=c.layer(j);if(l.name.indexOf('camp-source-')!==0)continue;var b=JSON.parse(l.comment);if(b.start>=e.end||b.end<=e.start)continue;var d=l.property('Source Text').valueAtTime(0,false);
  for(var k=0;k<d.composedLineCount;k++){var range=d.composedLineRange(k,k+1),lo=b.start+range.characterStart,hi=b.start+range.characterEnd;if(lo>=e.end||hi<=e.start)continue;out.push({block:{layer:l,start:b.start},start:lo,end:hi,line:k});}}
 out.sort(function(a,b){return a.start-b.start;});return out;}
for(var j=0;j<full.scenes.length;j++){var s=full.scenes[j];for(var k=0;k<s.reading_events.length;k++){var e=s.reading_events[k];cmReadingSequence(measuredRows(e),e,s.id,audit,ink,blue,orange,s.id==='SC09L'&&e.start===416?I.reading_focus.chunks:null);}}
var hand=cmQueryHandoff(c,query,c.layer('camp_QUESTION'),c.layer('QUERY_READING_MARGIN_SC09L'),{scene:'SC09L',return_start:158.708333333333,end:I.locator_scene.end,origin:JSON.parse(query.comment).origin,span:I.locator_scene.locator.stem_span},audit,ink);
var wrapped=app.project.items.addComp('MQ_B_COMPLETE_QUESTION_4K24',3840,2160,1,full.frames/24,24);wrapped.bgColor=c.bgColor;wrapped.layers.addSolid(c.bgColor,'ORIGINAL_CANVAS',3840,2160,1,wrapped.duration);var l=wrapped.layers.add(c);l.timeRemapEnabled=true;var remap=l.property('ADBE Time Remapping');while(remap.numKeys>1)remap.removeKey(remap.numKeys);remap.setValueAtTime(0,full.start);remap.setValueAtTime(full.end-full.start,full.end-1/24);remap.setValueAtTime((full.end-full.start)-1/24,full.end-1/24);remap.setInterpolationTypeAtKey(1,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);remap.setInterpolationTypeAtKey(2,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.HOLD);remap.setInterpolationTypeAtKey(3,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);l.outPoint=wrapped.duration;
for(var j=0;j<full.voices.length;j++){var voice=full.voices[j],footage=null;for(var k=1;k<=app.project.numItems;k++){var item=app.project.item(k);if(item instanceof FootageItem&&item.file&&item.file.fsName===new File(voice.voice.path).fsName){footage=item;break;}}if(!footage)footage=app.project.importFile(new ImportOptions(new File(voice.voice.path)));var audio=wrapped.layers.add(footage);audio.startTime=voice.voice_start-full.start;audio.inPoint=audio.startTime;audio.outPoint=voice.voice_end-full.start;}
wrapped.comment=JSON.stringify({source_start:full.start,last_source_time:full.end-1/24,complete_takes:full.voices.length,copy_unchanged:true,terminal:'D after all four authorized decisions',human_review:'PENDING'});
N.project=I.native_project;N.full_question_comp=wrapped.id;N.full_question_frames=full.frames;N.coverage=audit;N.human_review='PENDING';N.rig.production_integrated='shared phrase focus and query handoff; original B curves retained';
var file=new File(PATCH_RECEIPT);file.encoding='UTF-8';file.open('w');file.write(JSON.stringify(N));file.close();app.project.save();return N;
