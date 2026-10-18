var file=new File(INPUT);file.encoding='UTF-8';file.open('r');var I=JSON.parse(file.read());file.close();
if(app.project.dirty||app.project.renderQueue.rendering||app.project.renderQueue.numItems)throw Error('Expected clean idle host');
if(app.project.file.fsName!==new File(I.parent_aep).fsName||new File(I.native_project).exists)throw Error('Inspect parent/project identity');
var original=app.project.itemByID(I.native_master_id);
if(original.width!==3840||original.height!==2160||original.frameRate!==24)throw Error('Expected original 4K24');
var A=original.duplicate();A.name='MQ_A_ORIGINAL_SOURCE_4K24';var B=original.duplicate();B.name='MQ_B_NATIVE_CURVES_SOURCE_4K24';
var s=I.source_scene,loc=I.locator_scene,t0=I.clip_start,te=I.last_source_time,z=[0,0,0];
var rig={native_curves:[],curves:[],chunks:[],phase_notes:[],production_integrated:false,source_scenes:[loc.id,s.id]};
var cam=B.layer('READING_CAMERA'),focus=B.layer('READING_FOCUS'),lift=B.layer('SOURCE_LIFT_SC10'),choice=B.layer('CANDIDATE_FLIGHT_SC10'),source=B.layer('camp-source-781'),extract=B.layer('EXTRACT_SC10_camp-source-781'),query=B.layer('CARRIED_QUERY_SC09L');
function pos(l,t){return l.transform.position.valueAtTime(t,false);}
function aim(t){return cam.transform.pointOfInterest.valueAtTime(t,false);}
function makeNull(name){var l=B.layers.addNull();l.name=name;l.threeDLayer=true;l.enabled=false;l.transform.anchorPoint.setValue(z);l.transform.position.setValue(z);return l;}
var startAim=aim(t0),scan1=aim(149.416666666667),scan2=aim(153.625),hit=aim(155.25),question=aim(s.oriented),readAim=aim(s.source_arrive),stage=aim(s.settled),returnAim=aim(te);
var queryScreen=mqProject(pos(query,t0),cam,t0),queryOrigin=pos(query,160.666666666667),queryScale=query.transform.scale.valueAtTime(t0,false);
var sourceOrigin=pos(lift,s.extract_start),sourceDest=pos(lift,s.settled),choiceOrigin=pos(choice,s.candidate_start),choiceDest=pos(choice,s.settled);
var cameraRig=makeNull('MQ_CAMERA_RIG'),target=makeNull('MQ_CAMERA_AIM'),offset=makeNull('MQ_CAMERA_OFFSET');
target.parent=cameraRig;offset.parent=cameraRig;cam.parent=cameraRig;focus.parent=cameraRig;
mqKeyed(target.transform.position,[
 mqRow(t0,startAim,70,25,25,'directional_search'),
 mqRow(149.416666666667,scan1,85,25,25,'continue_through_paragraph'),
 mqRow(153.625,scan2,90,25,35,'approach_hit'),
 mqRow(155.25,hit,0,72,33,'identify_and_read'),
 mqRow(158.708333333333,hit,0,33,24,'prepare_next_view'),
 mqRow(s.oriented,question,0,72,33,'read_original_option'),
 mqRow(s.candidate_start,question,0,33,22,'carry_departure'),
 mqRow(165.625,[12650,readAim[1]-70,-110],260,36,36,'continuous_handoff'),
 mqRow(s.source_arrive,readAim,0,76,33,'recognize_source'),
 mqRow(s.extract_start-.25,readAim,0,33,22,'camera_prepares_extraction'),
 mqRow(s.settled-.25,stage,0,76,33,'camera_settles_before_text'),
 mqRow(s.return_start-.125,stage,0,33,22,'prepare_return'),
 mqRow(te-.125,returnAim,0,78,33,'return_reading_hold'),
 mqRow(te,returnAim,0,33,33,'original_source_handoff')
],rig,'camera_attention');
mqKeyed(offset.transform.position,[
 mqRow(t0,[0,-185,-1550],0,33,33,'fixed_pitch_search'),
 mqRow(158.708333333333,[0,-185,-1550],0,33,30,'pitch_release'),
 mqRow(s.oriented-.25,[0,0,-1550],0,70,33,'question_axis'),
 mqRow(s.candidate_start,[0,0,-1550],0,33,28,'approach_axis'),
 mqRow(s.source_arrive,[0,-185,-1550],0,70,33,'reading_axis'),
 mqRow(s.extract_start-.25,[0,-185,-1550],0,33,28,'extraction_axis'),
 mqRow(s.settled-.25,[-120,-65,-1600],0,70,33,'comparison_axis'),
 mqRow(s.return_start-.125,[-120,-65,-1600],0,33,25,'return_axis'),
 mqRow(te-.125,[-80,-30,-1550],0,75,33,'original_axis'),
 mqRow(te,[-80,-30,-1550],0,33,33,'hold')
],rig,'camera_offset');
cam.transform.pointOfInterest.expression='thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0]);';
cam.transform.position.expression='thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0])+thisComp.layer("MQ_CAMERA_OFFSET").transform.position;';
focus.transform.position.expression='thisComp.layer("MQ_CAMERA_AIM").toWorld([0,0,0]);';
var qscreen=makeNull('MQ_QUERY_SCREEN');qscreen.transform.position.setValue(queryScreen);
var qexpr=mqScreenExpression(qscreen.name),qend=160.666666666667;
query.transform.position.expression=qexpr.replace(/;$/,';').replace(/c\+f\*d\+r\*\(\(q\[0\]-thisComp.width\/2\)\*d\/z\)\+u\*\(\(q\[1\]-thisComp.height\/2\)\*d\/z\);$/,'var carry=c+f*d+r*((q[0]-thisComp.width/2)*d/z)+u*((q[1]-thisComp.height/2)*d/z);var a=Math.max(0,Math.min(1,(time-158.708333333333)/('+qend+'-158.708333333333)));a=a*a*a*(a*(6*a-15)+10);carry*(1-a)+'+JSON.stringify(queryOrigin)+'*a;');
rfCurve(query.transform.scale,[[t0,queryScale,z],[158.708333333333,queryScale,z],[qend,[100,100,100],z]],rig,'query_return_scale');
// The same native option follows a visible foreground route; it still exits
// only when the already-authorized elimination event is reached.
var carrier=makeNull('MQ_OPTION_SCREEN'),screen0=mqProject(choiceOrigin,cam,s.candidate_start),screen1=mqProject(choiceDest,cam,s.settled);
mqKeyed(carrier.transform.position,[mqRow(s.candidate_start,screen0,0,33,20,'carry'),mqRow(s.candidate_arrive,screen1,0,76,33,'align'),mqRow(s.event_time,screen1,0,33,33,'hold_until_existing_judgment')],rig,'option_carry');
var ce=mqScreenExpression(carrier.name);choice.transform.position.expression='if(time>='+s.event_time+'){value;}else{'+ce+'}';
var orientation=rfSmoothExpression([[s.candidate_start,z,z],[s.candidate_start+.75,[0,3,0],z],[s.candidate_arrive-.125,z,z],[s.event_time,z,z]]);
choice.transform.orientation.expression='if(time>='+s.event_time+'){value;}else{'+orientation+'}';
mqKeyed(lift.transform.position,[
 mqRow(s.extract_start,sourceOrigin,0,33,20,'extract_departure'),
 mqRow(s.extract_start+.90,[sourceOrigin[0]+8,sourceOrigin[1]+4,-250],180,28,38,'decisive_depth_travel'),
 mqRow(s.settled-4/24,sourceDest,0,76,33,'position_settled'),
 mqRow(s.return_start,sourceDest,0,33,22,'return_departure'),
 mqRow(te-5/24,sourceOrigin,0,80,33,'position_returned'),
 mqRow(te,sourceOrigin,0,33,33,'source_handoff')
],rig,'source_extract_and_return');
mqKeyed(lift.transform.orientation,[
 mqRow(s.extract_start,z,0,33,33,'still'),mqRow(s.extract_start+4/24,z,0,33,25,'delayed_turn'),
 mqRow(s.extract_start+.9,[1,0,0],0,55,42,'turn'),mqRow(s.settled,z,0,70,33,'follow_through_settles'),
 mqRow(s.return_start,z,0,33,28,'return_turn'),mqRow(s.return_start+.6,[.8,0,0],0,55,45,'turn_back'),mqRow(te-2/24,z,0,74,33,'rotation_returned'),mqRow(te,z,0,33,33,'hold')
],rig,'source_follow_through');
// Replace this scene's line-wide focus only in B. The source text, native
// glyph layout and its blue/orange disclosure keys are not rewritten.
for(var j=1;j<=B.numLayers;j++){var l=B.layer(j);if(!l.property('ADBE Text Properties'))continue;var aa=l.property('ADBE Text Properties').property('ADBE Text Animators');for(var k=aa.numProperties;k>=1;k--)if(aa.property(k).name.indexOf('READ_FOCUS_SC09L_')===0)aa.property(k).remove();}
rfChunkSequence(B.layer('camp-source-416'),I.scan_chunks,149.416666666667,153.625,rig,'search_chunks');
rfChunkSequence(source,['feedback workshops'],155.25,156.15,rig,'keyword_hit');
rfChunkSequence(extract,['take part in'],171,171.9,rig,'comparison_source');
rfChunkSequence(choice,['Chair'],172.666666666667,173.566666666667,rig,'comparison_option');
mqPreserveAccent(extract,'take part in',s.attention_events[0].time,rig);
mqPreserveAccent(choice,'Chair',s.attention_events[1].time,rig);
for(var j=1;j<=B.numLayers;j++){
 var l=B.layer(j);if(l.name.indexOf('camp-source-')!==0||l.name==='camp-source-781')continue;
 var o=l.transform.opacity;o.setValueAtTime(155.25,100);o.setValueAtTime(155.75,18);o.setValueAtTime(158.458333333333,18);o.setValueAtTime(158.708333333333,100);
 for(var k=o.numKeys;k>=1;k--)if(o.keyTime(k)>=s.candidate_start-.0001&&o.keyTime(k)<=s.settled+.0001)o.removeKey(k);
 o.setValueAtTime(s.candidate_start,100);o.setValueAtTime(s.candidate_arrive,6);o.setValueAtTime(s.settled,6);
 rfTemporal(o,155.25,33,25);rfTemporal(o,155.75,70,33);rfTemporal(o,158.458333333333,33,25);rfTemporal(o,158.708333333333,65,33);rfTemporal(o,s.candidate_start,33,25);rfTemporal(o,s.candidate_arrive,70,33);
}
B.motionBlur=true;B.shutterAngle=120;B.shutterPhase=-60;
for(var j=1;j<=B.numLayers;j++)if(B.layer(j).threeDLayer&&!(B.layer(j) instanceof CameraLayer))B.layer(j).motionBlur=true;
mqKeyed(cam.cameraOption.aperture,[mqRow(t0,10),mqRow(s.extract_start,10),mqRow(s.settled,24,0,70),mqRow(s.return_start,24),mqRow(te,10,0,74)],rig,'reading_depth');
rig.phase_notes={search_intermediate_speeds:[85,90],hit:155.25,camera_next_departure:158.708333333333,extraction_start:s.extract_start,translation_settles:s.settled-4/24,rotation_settles:s.settled,return_translation:te-5/24,return_rotation:te-2/24,judgment_unchanged:s.event_time,shutter_angle:120,shutter_phase:-60};
rig.phase_notes.context_fade={start:s.candidate_start,end:s.candidate_arrive,opacity:6,reason:'clear foreground option before it reaches the already-identified source'};
cameraRig.comment=JSON.stringify(rig);
function wrap(comp,label){var out=app.project.items.addComp(label,3840,2160,1,I.clip_frames/24,24);out.bgColor=comp.bgColor;out.layers.addSolid(comp.bgColor,'ORIGINAL_CANVAS',3840,2160,1,out.duration);var l=out.layers.add(comp);l.timeRemapEnabled=true;var p=l.property('ADBE Time Remapping');p.setValueAtTime(0,t0);p.setValueAtTime(te-t0,te);while(p.numKeys>2)p.removeKey(p.numKeys);p.setInterpolationTypeAtKey(1,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);p.setInterpolationTypeAtKey(2,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.HOLD);l.outPoint=out.duration;out.comment=JSON.stringify({source_start:t0,last_source_time:te,common_terminal_hold:1,copy_unchanged:true,internal_trial:true});return out;}
var wa=wrap(A,'MQ_A_ORIGINAL_4K24'),wb=wrap(B,'MQ_B_OPTIMIZED_4K24');
for(var v=0;v<I.voices.length;v++){var voice=I.voices[v],audio=app.project.importFile(new ImportOptions(new File(voice.voice.path)));for(var j=0;j<2;j++){var c=j?wb:wa,l=c.layers.add(audio);l.startTime=voice.voice_start-t0;l.inPoint=l.startTime;l.outPoint=l.startTime+voice.voice_end-voice.voice_start;}}
for(var j=1;j<=app.project.numItems;j++)app.project.item(j).selected=false;wb.selected=true;wb.openInViewer();wb.time=0;
var result={project:I.native_project,A_source:A.id,B_source:B.id,A:wa.id,B:wb.id,frames:I.clip_frames,width:3840,height:2160,fps:24,rig:rig,human_review:'PENDING'};
var receipt=new File(PRE_SAVE);receipt.encoding='UTF-8';receipt.open('w');receipt.write(JSON.stringify(result));receipt.close();app.project.save(new File(I.native_project));return result;
