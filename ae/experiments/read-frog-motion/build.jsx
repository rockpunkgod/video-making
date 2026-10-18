// Called only after parent binding and shared host ownership checks.
var inputFile=new File(INPUT);inputFile.encoding='UTF-8';inputFile.open('r');var I=JSON.parse(inputFile.read());inputFile.close();
if(app.project.dirty||app.project.renderQueue.rendering||app.project.renderQueue.numItems)throw Error('Expected clean idle native host');
if(app.project.file.fsName!==new File(I.parent_aep).fsName)throw Error('Parent project identity changed');
if(new File(I.native_project).exists)throw Error('Inspect existing trial; no rebuild');
var original=app.project.itemByID(I.native_master_id);
if(original.width!==3840||original.height!==2160||original.frameRate!==24)throw Error('Original master is not 4K24');
var A=original.duplicate();A.name='A_SOURCE_CURRENT_NATIVE_4K24';
var B=original.duplicate();B.name='B_SOURCE_MOTION_STUDY_4K24';
var s=I.source_scene,t0=I.clip_start,z=[0,0,0],rig={curves:[],chunks:[],native_temporal:[],source_scene:s.id,production_integrated:false};
function p(layer,name){return layer.property('ADBE Transform Group').property(name);}
var cam=B.layer('READING_CAMERA'),focus=B.layer('READING_FOCUS'),lift=B.layer('SOURCE_LIFT_SC03'),choice=B.layer('CANDIDATE_FLIGHT_SC03'),source=B.layer('fitbit-source-291'),ex=B.layer('EXTRACT_SC03_fitbit-source-291');
var endLook=cam.transform.pointOfInterest.valueAtTime(s.settled,false),sourceLook=cam.transform.pointOfInterest.valueAtTime(s.source_arrive,false),startLook=cam.transform.pointOfInterest.valueAtTime(t0,false);
var handoff=t0+2.1666666667,anticipate=s.extract_start-.25;
var lookKnots=[
 [t0,startLook,z],
 [handoff,[2670,sourceLook[1]-43,-100],[180,55,220]],
 [s.source_arrive,sourceLook,z],
 [anticipate,sourceLook,z],
 [s.settled,endLook,z],
 [t0+12,endLook,z]
];
rfCurve(cam.transform.pointOfInterest,lookKnots,rig,'camera_attention');
// Offset is authored independently of the travel path: pure pitch while
// reading, then restrained lateral perspective during physical extraction.
var offsets=[[t0,[0,0,1550],z],[handoff,[0,-185,1700],z],[s.source_arrive,[0,-185,1550],z],[anticipate,[0,-185,1550],z],[s.settled,[-120,-65,1600],z],[t0+12,[-120,-65,1600],z]];
var offsetExpression=rfSmoothExpression(offsets);
cam.transform.position.expression=offsetExpression.replace(/out;$/,'var aim=transform.pointOfInterest;[aim[0]+out[0],aim[1]+out[1],aim[2]-out[2]];');
rig.curves.push({name:'camera_offset',knots:offsets,expression:cam.transform.position.expression,continuity:'C2'});
rfCurve(focus.transform.position,lookKnots,rig,'focus_attention');
var originalPos=lift.transform.position.valueAtTime(s.extract_start,false),dest=lift.transform.position.valueAtTime(s.settled,false),delta=[];
for(var j=0;j<3;j++)delta.push(dest[j]-originalPos[j]);
var near=[originalPos[0]+16,originalPos[1]+delta[1]*.78-6,originalPos[2]+delta[2]*.78];
rfCurve(lift.transform.position,[[s.extract_start,originalPos,z],[s.extract_start+1,near,[-12,4,delta[2]*.35]],[s.settled,dest,z],[t0+12,dest,z]],rig,'source_extract');
rfCurve(lift.transform.orientation,[[s.extract_start,[0,0,0],z],[s.extract_start+.70,[1.5,-3.5,0],z],[s.settled-.25,[0,0,0],z],[t0+12,[0,0,0],z]],rig,'source_turn');
// Existing whole option and source lineage are retained. Only the path and
// distinct native arrival curve change; no new text object becomes evidence.
function sub3(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
function dot3(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
function cross3(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function norm3(a){var n=Math.sqrt(dot3(a,a));return [a[0]/n,a[1]/n,a[2]/n];}
function projectPoint(world,time){var c=cam.transform.position.valueAtTime(time,false),f=norm3(sub3(cam.transform.pointOfInterest.valueAtTime(time,false),c)),r=norm3(cross3([0,1,0],f)),u=cross3(f,r),v=sub3(world,c),d=dot3(v,f),zoom=cam.property('ADBE Camera Options Group').property('ADBE Camera Zoom').value;return [1920+dot3(v,r)*zoom/d,1080+dot3(v,u)*zoom/d,d];}
var cp=choice.transform.position,v0=cp.valueAtTime(s.candidate_start,false),v1=cp.valueAtTime(s.settled,false),screen0=projectPoint(v0,s.candidate_start),screen1=projectPoint(v1,s.settled);
var carrier=B.layers.addNull();carrier.name='RF_CARRY_SCREEN_PATH';carrier.threeDLayer=true;carrier.enabled=false;
var path=carrier.transform.position;path.setValueAtTime(s.candidate_start,screen0);path.setValueAtTime(s.candidate_arrive,screen1);
rfTemporal(path,s.candidate_start,33,22);rfTemporal(path,s.candidate_arrive,72,33);
path.setSpatialTangentsAtKey(1,z,[40,180,0]);path.setSpatialTangentsAtKey(2,[-30,-140,0],z);
cp.expression='var cam=thisComp.layer("READING_CAMERA"),q=thisComp.layer("RF_CARRY_SCREEN_PATH").transform.position,c=cam.transform.position,f=normalize(sub(cam.transform.pointOfInterest,c)),r=normalize(cross([0,1,0],f)),u=cross(f,r),z=cam.cameraOption.zoom,d=q[2];c+f*d+r*((q[0]-thisComp.width/2)*d/z)+u*((q[1]-thisComp.height/2)*d/z);';
rig.native_temporal.push({layer:carrier.name,consumer:choice.name,property:'Position',start:s.candidate_start,end:s.candidate_arrive,start_value:screen0,end_value:screen1,departure_out_influence:22,arrival_in_influence:72,spatial_out:[40,180,0],spatial_in:[-30,-140,0],purpose:'same native option carried visibly during continuous camera attention'});
rfCurve(choice.transform.orientation,[[s.candidate_start,[0,0,0],z],[s.candidate_start+.85,[0,3.5,0],z],[s.candidate_arrive-.20,[0,0,0],z],[t0+12,[0,0,0],z]],rig,'candidate_turn');
rfChunkSequence(source,['The Fitbit Air','is considerably cheaper','than those options'],s.source_arrive+.04,anticipate,rig,'price_read');
rfChunkSequence(ex,['Whoop and Oura'],s.settled+.06,s.settled+1.00,rig,'comparison_reference');
rfChunkSequence(choice,['more affordable'],s.attention_events[1].time,s.attention_events[1].time+.82,rig,'comparison_candidate');
// Recognition lowers unrelated context before the carried option can cross
// it. Text remains in the original 3D world, with no opaque evidence card.
for(var j=1;j<=B.numLayers;j++){
 var l=B.layer(j);if(l.name.indexOf('fitbit-source-')!==0||l.name==='fitbit-source-291')continue;
 var opacity=l.transform.opacity;
 for(var k=opacity.numKeys;k>=1;k--)if(opacity.keyTime(k)>=s.source_arrive-.0001&&opacity.keyTime(k)<=s.settled+.0001)opacity.removeKey(k);
 opacity.setValueAtTime(s.source_arrive,100);opacity.setValueAtTime(s.source_arrive+.5,6);opacity.setValueAtTime(s.settled,6);
 rfTemporal(opacity,s.source_arrive,33,25);rfTemporal(opacity,s.source_arrive+.5,70,33);
}
rig.context={start:s.source_arrive,end:s.source_arrive+.5,retained_opacity:6,selected:'fitbit-source-291',reason:'recognized source becomes foreground; surrounding source text remains in place'};
// Native shutter is a test parameter. Pixel response is audited separately;
// setting a flag is not evidence that a renderer supports the treatment.
B.motionBlur=true;B.shutterAngle=144;B.shutterPhase=-72;
for(var j=1;j<=B.numLayers;j++)if(B.layer(j).threeDLayer&&!(B.layer(j) instanceof CameraLayer))B.layer(j).motionBlur=true;
var optics=cam.property('ADBE Camera Options Group');
optics.property('ADBE Camera Aperture').expression=rfSmoothExpression([[t0,[14],[0]],[s.source_arrive,[10],[0]],[anticipate,[10],[0]],[s.settled,[36],[0]],[t0+12,[36],[0]]]).replace(/out;$/,'out[0];');
var controller=B.layers.addNull();controller.name='RF_MOTION_RIG_EXPERIMENTAL';controller.enabled=false;controller.comment=JSON.stringify(rig);
function wrap(comp,label){var out=app.project.items.addComp(label+'_12S_4K24',3840,2160,1,12,24);out.bgColor=comp.bgColor;var backing=out.layers.addSolid(comp.bgColor,'PARENT_CANVAS_BACKGROUND',3840,2160,1,12),l=out.layers.add(comp);l.startTime=-t0;l.inPoint=0;l.outPoint=12;out.comment=JSON.stringify({parent_project:I.parent_aep,source_comp:comp.id,source_start:t0,source_end:t0+12,scene:s.id,role:'INTERNAL_TECHNICAL_AB',copy_unchanged:true});return out;}
var wa=wrap(A,'A_CURRENT'),wb=wrap(B,'B_MOTION');
var io=new ImportOptions(new File(I.voice.voice.path)),audio=app.project.importFile(io);
for(var j=0;j<2;j++){var c=j?wb:wa,al=c.layers.add(audio);al.startTime=I.voice.voice_start-t0;al.inPoint=al.startTime;al.outPoint=al.startTime+(I.voice.voice_end-I.voice.voice_start);}
for(var j=1;j<=app.project.numItems;j++)app.project.item(j).selected=false;wb.selected=true;wb.openInViewer();wb.time=0;
var result={project:I.native_project,A_source:A.id,B_source:B.id,A:wa.id,B:wb.id,frames:288,width:3840,height:2160,fps:24,rig:rig,source_clip:[t0,t0+12],human_review:'PENDING'};
var receipt=new File(PRE_SAVE);receipt.encoding='UTF-8';receipt.open('w');receipt.write(JSON.stringify(result));receipt.close();
app.project.save(new File(I.native_project));return result;
