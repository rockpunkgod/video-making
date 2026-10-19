// Current author -> native paper, measured reading lines and continuous 3D objects.
// Facts, exact copy and event authority come only from the checked AV plan.
/* SHARED_READING_RIG */
var f=new File(PLAN_PATH);f.encoding="UTF-8";if(!f.open("r"))throw Error("Missing AV plan");var P=JSON.parse(f.read());f.close();
if(!P.article_chunking)throw Error("Article sense groups must be compiled before native layout");
if(P.realization!=="continuous_paper_scan")throw Error("Explicit reading/motion decisions required; replay historical films with their bound execution version");
if(app.project.dirty||app.project.renderQueue.rendering)throw Error("Existing project must be clean and idle");
if(new File(PROJECT_PATH).exists)throw Error("Inspect existing revision before build");
app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=8;
var C=app.project.items.addComp("MAIN_FILM_EDITORIAL_PROXY",1280,720,1,P.duration,24);
C.renderer="ADBE Advanced 3d";C.bgColor=[.91,.905,.88];C.motionBlur=true;C.shutterAngle=90;
var ink=[.09,.13,.16],paper=[.955,.946,.92],muted=[.48,.51,.51],blue=[.10,.37,.57],orange=[.69,.27,.06];
if(P.visual_states){paper=[242/255,240/255,234/255];ink=[32/255,33/255,31/255];C.bgColor=paper;}
var column=P.layout?P.layout.passage_width:1080,readingDistance=P.layout?P.layout.reading_distance:1550,stageDistance=P.layout?P.layout.stage_distance:1600;
var audit={sources:[],extractions:[],candidates:[],camera:[],locators:[],replays:[],scenes:[],captions:[],reading:[],query_carries:[],scan_motion:[],word_focus:[],reading_windows:[],query_handoffs:[],teaching_resources:[]};
function tr(l,n){return l.property("ADBE Transform Group").property(n);}
function ease(p,t,v){p.setValueAtTime(t,v);var n=p.nearestKeyIndex(t),a=[],b=[],dims=v instanceof Array?v.length:1;var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;if(spatial||p.propertyValueType===PropertyValueType.COLOR)dims=1;for(var i=0;i<dims;i++){a.push(new KeyframeEase(0,55));b.push(new KeyframeEase(0,55));}p.setTemporalEaseAtKey(n,a,b);p.setInterpolationTypeAtKey(n,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);if(spatial&&p.matchName!=="ADBE Orientation"){var z=v.length===3?[0,0,0]:[0,0];p.setSpatialTangentsAtKey(n,z,z);}}
function hold(p,t,v){p.setValueAtTime(t,v);var k=p.nearestKeyIndex(t);p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}
function text(name,value,x,y,z,size,width,color,font){var l=C.layers.addBoxText([width,2200]);l.name=name;var p=l.property("Source Text"),d=p.value;d.text=value;d.font=font||"ArialMT";d.fontSize=size;d.autoLeading=false;d.leading=size*1.32;d.fillColor=color;d.applyFill=true;d.applyStroke=false;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);l.threeDLayer=true;var bp=p.value.boxTextPos;tr(l,"ADBE Anchor Point").setValue([bp[0],bp[1],0]);tr(l,"ADBE Position").setValue([x,y,z]);return l;}
function rect(name,w,h,x,y,z,col){var l=C.layers.addSolid(col,name,w,h,1,P.duration);l.threeDLayer=true;tr(l,"ADBE Anchor Point").setValue([0,0,0]);tr(l,"ADBE Position").setValue([x,y,z]);return l;}
function overlay(name,value,x,y,size,width,col,a,b){var l=text(name,value,x,y,0,size,width,col,"MicrosoftYaHei");l.threeDLayer=false;l.inPoint=a;l.outPoint=b;return l;}
function style(l,t,color,phrase,accent){var p=l.property("Source Text"),d=p.valueAtTime(t,false);d.fillColor=color;if(d.text.length)d.characterRange(0,d.text.length).fillColor=color;if(phrase){var at=d.text.indexOf(phrase);if(at>=0)d.characterRange(at,at+phrase.length).fillColor=accent;}hold(p,t,d);}
var cam=C.layers.addCamera("READING_CAMERA",[640,360]),opt=cam.property("ADBE Camera Options Group");opt.property("ADBE Camera Zoom").setValue(1500);opt.property("ADBE Camera Depth of Field").setValue(true);opt.property("ADBE Camera Blur Level").setValue(55);
var focus=C.layers.addNull();focus.name="READING_FOCUS";focus.threeDLayer=true;focus.enabled=false;
opt.property("ADBE Camera Focus Distance").expression='var p=thisComp.layer("READING_FOCUS").toWorld([0,0,0]);var c=transform.position;var v=normalize(sub(transform.pointOfInterest,c));Math.max(1,dot(sub(p,c),v));';
function camera(t,c,dist,tilt,aperture){dist=dist||1550;tilt=tilt||[0,0];ease(tr(cam,"ADBE Anchor Point"),t,c);ease(tr(cam,"ADBE Position"),t,[c[0]+tilt[0],c[1]+tilt[1],c[2]-dist]);ease(tr(focus,"ADBE Position"),t,c);ease(opt.property("ADBE Camera Aperture"),t,aperture===undefined?14:aperture);audit.camera.push({time:t,target:c,distance:dist,offset:tilt,aperture:aperture===undefined?14:aperture});}
var worlds={},blocks={},lastTarget=[640,320,0],lastDistance=1550,lastOffset=[0,0],lastAperture=14,titles=[];
function question(w){return [w.base+640,320,0];}
for(var wi=0;wi<P.world_order.length;wi++){
 var name=P.world_order[wi],data=P.worlds[name],q=data.question,base=wi*10000,w={base:base,blocks:[],options:{},question:q};worlds[name]=w;
 w.questionPaper=rect(name+"_QUESTION_PAPER",1320,790,base-20,-40,60,paper);
 w.stem=text(name+"_QUESTION",q.stem,base+80,95,0,50,1120,ink);style(w.stem,0,ink,null,null);
 for(var j=0;j<4;j++){var cid="ABCD".charAt(j),op=text(name+"_OPTION_"+cid,cid+"   "+q.options[cid],base+90,230+j*80,0,46,1120,ink);op.comment=JSON.stringify({kind:"original_option",question_id:q.question_id,candidate:cid,exact_text:q.options[cid]});hold(tr(op,"ADBE Opacity"),0,100);style(op,0,ink,null,null);w.options[cid]=op;}
 var y=40;
 for(var j=0;j<data.blocks.length;j++){var b=data.blocks[j];if(!b.visible){y+=28;continue;}var l=text(b.id,b.text,base+2250,y,100,46,column,ink);cmKeepChunks(l,b);var r=l.sourceRectAtTime(0,false);style(l,0,ink,null,null);l.comment=JSON.stringify({kind:"original_passage",source:data.source,field:"passage",start:b.start,end:b.end,exact_text:b.text});var row={id:b.id,start:b.start,end:b.end,text:b.text,reading_chunks:b.reading_chunks,layer:l,x:base+2250,y:y,z:100,height:r.height};blocks[b.id]=row;w.blocks.push(row);audit.sources.push({id:b.id,layer_id:l.id,start:b.start,end:b.end,text:b.text,position:[row.x,y,100],height:r.height});y+=Math.max(r.height+36,50);}
 w.paper=rect(name+"_PASSAGE_PAPER",column+220,Math.ceil(y+100),base+2190,-20,150,paper);
}
function info(key,shot){var ex=P.excerpts[key],a=[],packed=0;for(var i=0;i<ex.block_ids.length;i++){var b=blocks[ex.block_ids[i]],used=false;for(var j=0;j<shot.source_refs.length;j++){var r=shot.source_refs[j];if(r.world===ex.world&&r.pointer==="/passage"&&r.start<b.end&&r.end>b.start)used=true;}if(used){a.push(b);packed+=b.height+(a.length>1?36:0);}}if(!a.length)throw Error("Excerpt has no explicitly bound passage blocks");var first=a[0],last=a[a.length-1];return {key:key,blocks:a,x:first.x,y:first.y,z:100,height:last.y+last.height-first.y,packed_height:packed,world:worlds[ex.world]};}
function sourceTarget(ex){return [ex.x+column/2,ex.y+ex.height/2+12,100];}
function stage(ex){return [ex.x+column/2,ex.y+230,-280];}
function destSource(ex){var p=stage(ex);return [p[0]-column/2,p[1]-225,-340];}
function destCandidate(ex){var p=stage(ex);return [p[0]-column/2,p[1]+140,-390];}
function lineRows(w,lo,hi){var rows=[];for(var j=0;j<w.blocks.length;j++){var b=w.blocks[j];if(b.end<=lo||b.start>=hi)continue;var d=b.layer.property("Source Text").valueAtTime(0,false),bl=d.baselineLocs,bp=d.boxTextPos;for(var k=0;k<d.composedLineCount;k++){var range=d.composedLineRange(k,k+1),start=b.start+range.characterStart,end=b.start+range.characterEnd;if(end<=lo||start>=hi)continue;var yy=b.y+bl[k*4+1]-bp[1]-d.fontSize*.36;rows.push({block:b,start:start,end:end,left:b.x+bl[k*4]-bp[0],right:b.x+bl[k*4+2]-bp[0],y:yy,line:k});}}if(!rows.length)throw Error("No measured source lines for reading path");return rows;}
function readPath(s,w,from,fromDistance){var target=from,dist=fromDistance,events=s.reading_events,offset=[0,0],aperture=14,pitched=false,scanStart=null,scanEnd=null,pitchStart=null,pitchEnd=null;
 for(var k=0;k<events.length;k++){var e=events[k],rows=lineRows(w,e.start,e.end),first=rows[0],last=rows[rows.length-1],mid=(first.y+last.y)/2,scope=[w.base+2250+column/2,mid,100];camera(e.depart,target,dist,offset,pitched?aperture:14);
  if(e.mode==="scan"){
   var span=e.end_time-e.arrival,slot=span/rows.length;
   if(!pitched){pitchStart=e.depart;pitchEnd=e.depart+Math.min(.7,(e.arrival-e.depart)*.4);var pitch=dist*185/1550;camera(pitchEnd,[target[0],target[1]+pitch,target[2]],dist,[0,-pitch],16);pitched=true;scanStart=e.arrival;}
   offset=[0,-readingDistance*185/1550];aperture=16;dist=readingDistance;target=[w.base+2250+column/2,first.y+70,100];camera(e.arrival,target,dist,offset,aperture);
   // The attention window travels down the paper; it never sweeps left/right
   // or resets pitch at each line. Only the actual attended words pulse.
   target=[w.base+2250+column/2,last.y+70,100];camera(e.end_time,target,dist,offset,aperture);scanEnd=e.end_time;
  }else{
   dist=e.mode==="scope"?Math.max(readingDistance,1650,(last.y-first.y+140)*3.1):readingDistance;if(pitched&&e.mode==="hit")scope[1]=Math.max(target[1],mid+70);target=scope;offset=pitched?[0,-dist*185/1550]:(e.mode==="hit"?[-110,-60]:[0,0]);aperture=e.mode==="hit"?18:5;camera(e.arrival,target,dist,offset,aperture);camera(e.end_time,target,dist,offset,aperture);if(pitched&&e.mode==="hit")scanEnd=e.end_time;
  }
  cmReadingSequence(rows,e,s.id,audit,ink,blue,orange);
  audit.reading.push({scene:s.id,start:e.start,end:e.end,mode:e.mode,arrival:e.arrival,end_time:e.end_time,lines:(function(){var out=[];for(var j=0;j<rows.length;j++)out.push({layer_id:rows[j].block.layer.id,start:rows[j].start,end:rows[j].end,y:rows[j].y});return out;})()});
 }
 if(pitched)audit.scan_motion.push({scene:s.id,pitch_start:pitchStart,pitch_end:pitchEnd,start:scanStart,end:scanEnd,column_x:w.base+2250+column/2,pitch_ratio:185/1550,mode:"pitch_then_vertical_scan"});
 return {target:target,distance:dist,offset:offset,aperture:aperture,pitched:pitched};
}
function carryPose(c){var x=-c.offset[0],y=-c.offset[1],z=c.distance,n=Math.sqrt(x*x+y*y+z*z),f=[x/n,y/n,z/n],rn=Math.sqrt(f[2]*f[2]+f[0]*f[0]),right=[f[2]/rn,0,-f[0]/rn],up=[f[1]*right[2],f[2]*right[0]-f[0]*right[2],-f[1]*right[0]],depth=c.distance-130,k=depth/1500,campos=[c.target[0]+c.offset[0],c.target[1]+c.offset[1],c.target[2]-c.distance],pos=[];for(var i=0;i<3;i++)pos.push(campos[i]+f[i]*depth+right[i]*(-480*k)+up[i]*(-315*k));return {position:pos,scale:68*k};}
function queryCarry(s,w){var loc=s.locator,d=w.stem.property("Source Text").value,bl=d.baselineLocs,bp=d.boxTextPos,idx=loc.stem_span[0],origin=null;
 var baseline=0;for(var k=0;k<d.composedLineCount;k++){var r=d.composedLineRange(k,k+1);if(r.characterStart<=idx&&idx<r.characterEnd){var prefix=d.text.slice(r.characterStart,idx),probe=C.layers.addText(prefix+"M"),pd=probe.property("Source Text").value;pd.font=d.font;pd.fontSize=d.fontSize;probe.property("Source Text").setValue(pd);var fullWidth=probe.sourceRectAtTime(0,false).width;pd.text="M";probe.property("Source Text").setValue(pd);var width=prefix?fullWidth-probe.sourceRectAtTime(0,false).width:0;probe.remove();baseline=95+bl[k*4+1]-bp[1];origin=[w.base+80+bl[k*4]-bp[0]+width,baseline,0];break;}}
 if(!origin)throw Error("Missing original query line");var q=text("CARRIED_QUERY_"+s.id,loc.identity,origin[0],origin[1],origin[2],50,900,orange);q.inPoint=s.oriented;q.outPoint=s.end;q.motionBlur=true;style(w.stem,s.start,ink,loc.identity,orange);style(w.stem,s.oriented,ink,loc.identity,paper);style(w.stem,s.end,ink,null,null);ease(tr(q,"ADBE Position"),s.oriented,origin);ease(tr(q,"ADBE Scale"),s.oriented,[100,100,100]);
 var qd=q.property("Source Text").value;origin[1]=baseline-(qd.baselineLocs[1]-qd.boxTextPos[1]);ease(tr(q,"ADBE Position"),s.oriented,origin);
 var keys=[];for(var j=0;j<audit.camera.length;j++){var c=audit.camera[j];if(c.time>s.oriented&&c.time<=s.return_start)keys.push(c);}keys.sort(function(a,b){return a.time-b.time;});
 for(var j=0;j<keys.length;j++){var c=keys[j],pose=carryPose(c);ease(tr(q,"ADBE Position"),c.time,pose.position);ease(tr(q,"ADBE Scale"),c.time,[pose.scale,pose.scale,pose.scale]);}
 ease(tr(q,"ADBE Position"),s.end-1/24,origin);ease(tr(q,"ADBE Scale"),s.end-1/24,[100,100,100]);q.comment=JSON.stringify({kind:"query_from_original_stem",source_layer_id:w.stem.id,span:loc.stem_span,exact_text:loc.identity,origin:origin});audit.query_carries.push({scene:s.id,layer_id:q.id,origin:origin,start:s.oriented,end:s.end});
}
function cutCamera(t,target,dist){camera(t,target,dist);var ps=[tr(cam,"ADBE Position"),tr(cam,"ADBE Anchor Point"),tr(focus,"ADBE Position"),opt.property("ADBE Camera Aperture")];for(var j=0;j<ps.length;j++){var k=ps[j].nearestKeyIndex(t);if(k>1)ps[j].setInterpolationTypeAtKey(k-1,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}}
function recapCamera(s){var first=worlds[s.recap_worlds[0]],second=worlds[s.recap_worlds[1]],cut=(s.start+s.end)/2,v=null,best=1e20;for(var j=0;j<P.segments.length;j++)if(P.segments[j].scene_id===s.id){v=P.segments[j];break;}if(v){var midpoint=(v.voice_start+v.voice_end)/2;for(var j=0;j<P.cues.length;j++){var cue=P.cues[j];if(cue.segment===v.id&&cue.start>s.oriented+.5&&cue.start<v.voice_end-.5&&Math.abs(cue.start-midpoint)<best){best=Math.abs(cue.start-midpoint);cut=Math.ceil((cue.start-1e-8)*24)/24;}}}cutCamera(s.start,question(first),1650);camera(s.oriented,question(first),1550);camera(cut-1/24,question(first),1550);cutCamera(cut,question(second),1650);camera(Math.min(cut+s.choreography.orient_seconds,s.end-1/24),question(second),1550);camera(s.end-1/24,question(second),1550);return {target:question(second),distance:1550,cut:cut};}
function lift(key,s,start,end,replay){var ex=info(key,s),w=ex.world,ns=C.layers.addNull();ns.name="SOURCE_LIFT_"+s.id;ns.threeDLayer=true;ns.inPoint=start;ns.outPoint=end;tr(ns,"ADBE Anchor Point").setValue([0,0,0]);var origin=[ex.x,ex.y,100],dest=destSource(ex),settled=start+s.travel_seconds,clones=[],scale=Math.min(100,310/ex.packed_height*100),returnStart=s.return_start;
 for(var j=0;j<ex.blocks.length;j++){var b=ex.blocks[j],l=b.layer.duplicate();l.name="EXTRACT_"+s.id+"_"+b.id;l.parent=ns;tr(l,"ADBE Position").setValue([0,b.y-ex.y,0]);l.inPoint=start;l.outPoint=end;l.motionBlur=true;hold(tr(b.layer,"ADBE Opacity"),Math.max(0,start-1/24),100);hold(tr(b.layer,"ADBE Opacity"),start,0);hold(tr(b.layer,"ADBE Opacity"),end,100);style(l,start,ink,null,null);clones.push(l);}
 var packedY=0;for(var j=0;j<ex.blocks.length;j++){var b=ex.blocks[j],l=clones[j];if(ex.blocks.length>1){ease(tr(l,"ADBE Position"),start,[0,b.y-ex.y,0]);ease(tr(l,"ADBE Position"),settled,[0,packedY,0]);ease(tr(l,"ADBE Position"),returnStart,[0,packedY,0]);ease(tr(l,"ADBE Position"),end-1/24,[0,b.y-ex.y,0]);}packedY+=b.height+36;}
 ease(tr(ns,"ADBE Position"),start,origin);ease(tr(ns,"ADBE Position"),settled,dest);ease(tr(ns,"ADBE Orientation"),start,[0,0,0]);ease(tr(ns,"ADBE Orientation"),start+s.travel_seconds*.5,[3,-7,0]);ease(tr(ns,"ADBE Orientation"),settled,[0,0,0]);ease(tr(ns,"ADBE Scale"),start,[100,100,100]);ease(tr(ns,"ADBE Scale"),settled,[scale,scale,scale]);ease(tr(ns,"ADBE Position"),returnStart,dest);ease(tr(ns,"ADBE Position"),end-1/24,origin);ease(tr(ns,"ADBE Scale"),returnStart,[scale,scale,scale]);ease(tr(ns,"ADBE Scale"),end-1/24,[100,100,100]);
 ns.comment=JSON.stringify({kind:replay?"replay_of_reviewed_comparison":"continuous_source_extraction",scene_id:s.id,source:P.excerpts[key],selected_block_ids:(function(){var ids=[];for(var j=0;j<ex.blocks.length;j++)ids.push(ex.blocks[j].id);return ids;})(),new_candidate_event:false});audit.extractions.push({scene:s.id,key:key,start:start,settled:settled,end:end,group_id:ns.id,origin:origin,destination:dest,return_start:returnStart,scale:scale,packed_height:ex.packed_height,selected_block_ids:(function(){var ids=[];for(var j=0;j<ex.blocks.length;j++)ids.push(ex.blocks[j].id);return ids;})(),replay:replay});return {group:ns,clones:clones};}
function candidate(s,w,ex,replay){var origin=w.options[s.candidate],r=tr(origin,"ADBE Position").value,l=origin.duplicate(),dest=destCandidate(ex),arrive=s.candidate_arrive;l.name=(replay?"REPLAY_CANDIDATE_":"CANDIDATE_FLIGHT_")+s.id;l.inPoint=s.candidate_start;l.outPoint=s.end;l.motionBlur=true;
 style(origin,s.start,ink,s.candidate+"   ",orange);style(origin,s.end,ink,null,null);hold(tr(origin,"ADBE Opacity"),s.start,100);hold(tr(origin,"ADBE Opacity"),s.candidate_start,0);hold(tr(origin,"ADBE Opacity"),s.end,s.event==="eliminate"?38:100);
 // Constant ink at source, handoff, travel and landing avoids a dark blink.
 style(l,s.candidate_start,ink,null,null);ease(tr(l,"ADBE Position"),s.candidate_start,r);ease(tr(l,"ADBE Position"),arrive,dest);ease(tr(l,"ADBE Orientation"),s.candidate_start,[0,0,0]);ease(tr(l,"ADBE Orientation"),s.candidate_start+(arrive-s.candidate_start)*.5,[0,8,0]);ease(tr(l,"ADBE Orientation"),arrive,[0,0,0]);ease(tr(l,"ADBE Scale"),s.candidate_start,[100,100,100]);ease(tr(l,"ADBE Scale"),arrive,[104,104,104]);
 if(s.event){var ev=s.event_time;if(s.event==="eliminate"){ease(tr(l,"ADBE Position"),ev,dest);ease(tr(l,"ADBE Position"),s.decision_end,[dest[0]+1500,dest[1]+60,420]);ease(tr(l,"ADBE Orientation"),ev,[0,0,0]);ease(tr(l,"ADBE Orientation"),s.decision_end,[0,72,0]);hold(tr(origin,"ADBE Opacity"),s.decision_end,38);}else style(l,ev,blue,null,null);audit.candidates.push({scene:s.id,kind:s.event,candidate:s.candidate,time:ev,layer_id:l.id,whole_option_text:l.property("Source Text").value.text,refs:s.terminal_refs,exit_end:s.event==="eliminate"?s.decision_end:null});}
 if(s.candidate_reading_policy==="quiet_source_until_read"&&s.reading_events.length){var firstRead=s.reading_events[0],lastRead=s.reading_events[s.reading_events.length-1],op=tr(l,"ADBE Opacity");ease(op,Math.max(s.candidate_arrive,firstRead.arrival-.3),100);ease(op,firstRead.arrival,0);ease(op,lastRead.end_time,0);ease(op,lastRead.end_time+.3,100);}
 if(s.event!=="eliminate"){ease(tr(l,"ADBE Position"),s.return_start,dest);ease(tr(l,"ADBE Position"),s.end-1/24,r);ease(tr(l,"ADBE Scale"),s.return_start,[104,104,104]);ease(tr(l,"ADBE Scale"),s.end-1/24,[100,100,100]);}
 l.comment=JSON.stringify({kind:replay?"recalled_candidate":"whole_candidate_with_attached_identity",candidate:s.candidate,scene:s.id,source_layer_id:origin.id,terminal_refs:s.terminal_refs});return l;}
function lightAccent(layer,e,s,index){var d=layer.property("Source Text").valueAtTime(0,false),at=d.text.indexOf(e.phrase);if(at<0)return;var start=Math.max(e.time,s.source_arrive),end=s.end-1/24,an=cmSelector(layer,"LIGHT_ACCENT_"+s.id+"_"+index,at,at+e.phrase.length);an.property("ADBE Text Animator Properties").addProperty("ADBE Text Fill Color").setValue(orange);cmAmount(an).expression='function q(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}100*q((time-'+start+')/.2)*q(('+end+'-time)/.4);';}
for(var si=0;si<P.scenes.length;si++){
 var s=P.scenes[si],w=worlds[s.world],a=s.start,b=s.end,m=s.choreography,heading=s.screen_title===undefined?s.title:s.screen_title;if(heading){var title=overlay("TASK_TITLE_"+s.id,heading,72,24,28,1120,muted,a,b);if((s.kind==="compare"||s.kind==="replay")&&s.motion_treatment!=="in_place_check"&&s.reading_events.length){var titleEnd=Math.max(a+.25,s.reading_events[0].depart);title.outPoint=Math.min(b,titleEnd);ease(tr(title,"ADBE Opacity"),Math.max(a,titleEnd-.2),100);ease(tr(title,"ADBE Opacity"),titleEnd,0);}titles.push(title);}camera(a,lastTarget,lastDistance,lastOffset,lastAperture);lastOffset=[0,0];lastAperture=14;
 if(s.kind==="task"||s.kind==="answer"){
  var qt=question(w);if(si&&P.scenes[si-1].world!==s.world)camera(a,qt,1650);camera(s.oriented,qt,1550);camera(b-1/24,qt,1550);lastTarget=qt;lastDistance=1550;
  if(s.kind==="answer"){for(var j=0;j<4;j++){var cid="ABCD".charAt(j);style(w.options[cid],s.event_time,cid===s.candidate?blue:muted,null,null);}var answer=text("FINAL_"+s.world,"答案 "+s.candidate,w.base+100,610,-30,34,600,blue,"MicrosoftYaHei");answer.inPoint=s.event_time;answer.outPoint=P.duration;audit.candidates.push({scene:s.id,kind:"final",candidate:s.candidate,time:s.event_time,refs:s.terminal_refs});}
 }else if(s.kind==="locate"){
  var qt=question(w);camera(s.oriented,qt,1550);var read=readPath(s,w,qt,1550);camera(s.return_start,read.target,read.distance,read.offset,read.aperture);camera(b-1/24,qt,1550,[0,0],14);lastTarget=qt;lastDistance=1550;lastOffset=[0,0];lastAperture=14;queryCarry(s,w);
  var hit=s.reading_events[0],scope=s.reading_events[s.reading_events.length-1];for(var j=0;j<s.reading_events.length;j++)if(s.reading_events[j].mode==="hit")hit=s.reading_events[j];audit.locators.push({scene:s.id,question_span:s.locator.stem_span,passage_span:s.locator.passage_span,block_span:s.locator.block_span,opening_at:s.reading_events[0].arrival,match_at:hit.arrival,scope_at:scope.arrival,scope_until:b});
 }else if(s.kind==="compare"&&s.motion_treatment==="in_place_check"){
  // A short check stays on the real paper. No source lift or option flight.
  var ex=info(s.excerpt,s),visit=sourceTarget(ex),distance=Math.max(readingDistance,ex.height*3.0);
  camera(s.oriented,visit,distance,[0,0],12);
  var read=readPath(s,w,visit,distance);
  camera(s.source_arrive,visit,distance,[0,0],12);camera(b-1/24,visit,distance,[0,0],12);
  lastTarget=visit;lastDistance=distance;lastAperture=12;
  var header=C.layers.addSolid(paper,"LIGHT_READING_MARGIN_"+s.id,1280,105,1,P.duration);header.transform.position.setValue([640,52.5]);header.inPoint=a;header.outPoint=b;
  ease(tr(header,"ADBE Opacity"),a,0);ease(tr(header,"ADBE Opacity"),s.oriented,100);ease(tr(header,"ADBE Opacity"),s.return_start,100);ease(tr(header,"ADBE Opacity"),b-1/24,0);
  var origin=w.options[s.candidate],choice=overlay("LIGHT_CANDIDATE_"+s.id,origin.property("Source Text").value.text,84,65,30,1110,ink,s.oriented,b);
  choice.motionBlur=false;style(choice,s.oriented,ink,null,null);
  ease(tr(choice,"ADBE Opacity"),s.oriented,0);ease(tr(choice,"ADBE Opacity"),s.oriented+.25,100);
  for(var j=0;j<s.attention_events.length;j++){var e=s.attention_events[j];if(e.target==="candidate")style(choice,Math.max(e.time,s.oriented),ink,e.phrase,orange);else for(var k=0;k<w.blocks.length;k++)lightAccent(w.blocks[k].layer,e,s,j);}
  ease(tr(choice,"ADBE Opacity"),s.event_time,100);ease(tr(choice,"ADBE Opacity"),s.decision_end,s.event==="eliminate"?38:100);
  if(s.event==="supported")style(choice,s.event_time,blue,null,null);
  hold(tr(origin,"ADBE Opacity"),s.decision_end,s.event==="eliminate"?38:100);
  ease(tr(choice,"ADBE Opacity"),s.return_start,s.event==="eliminate"?38:100);ease(tr(choice,"ADBE Opacity"),b-1/24,0);
  choice.comment=JSON.stringify({kind:"in_place_candidate_check",scene:s.id,source_layer_id:origin.id,terminal_refs:s.terminal_refs});
  audit.candidates.push({scene:s.id,kind:s.event,candidate:s.candidate,time:s.event_time,layer_id:choice.id,whole_option_text:choice.property("Source Text").value.text,refs:s.terminal_refs,treatment:"in_place_check"});
 }else if(s.kind==="compare"||s.kind==="replay"){
  // Keep the moving whole option legible while the original world stays present.
  for(var j=0;j<4;j++){var other=w.options["ABCD".charAt(j)];if("ABCD".charAt(j)===s.candidate)continue;var opacity=tr(other,"ADBE Opacity"),prior=opacity.valueAtTime(s.oriented,false);ease(opacity,s.candidate_start-.5,prior);ease(opacity,s.candidate_start,prior*.10);ease(opacity,s.candidate_arrive,prior*.10);ease(opacity,s.source_arrive,prior);}
  for(var j=0;j<w.blocks.length;j++){var opacity=tr(w.blocks[j].layer,"ADBE Opacity"),readAt=s.reading_events.length?s.reading_events[0].arrival:s.source_arrive;ease(opacity,s.candidate_start-.5,100);ease(opacity,s.candidate_start,14);ease(opacity,s.candidate_arrive,14);ease(opacity,readAt,100);}
  var ex=info(s.excerpt,s),st=stage(ex),visit=sourceTarget(ex),qt=question(w);camera(s.oriented,qt,1550);camera(s.candidate_start,qt,1550);camera(s.candidate_arrive,st,stageDistance,[-120,-65],22);
  var read=readPath(s,w,st,stageDistance),visual=s.reading_events.length?s.reading_events[s.reading_events.length-1].end_time:s.candidate_arrive;camera(visual,read.target,read.distance,read.pitched?read.offset:[0,0],read.pitched?read.aperture:14);camera(s.source_arrive,visit,Math.max(readingDistance,ex.height*3.0),[-90,-45],12);camera(s.extract_start,visit,Math.max(readingDistance,ex.height*3.0),[-90,-45],12);camera(s.settled,st,stageDistance,[-120,-65],65);camera(s.return_start,st,stageDistance,[-120,-65],65);camera(b-1/24,visit,Math.max(readingDistance,ex.height*3.0),[-80,-30],12);lastTarget=visit;lastDistance=Math.max(readingDistance,ex.height*3.0);
  for(var j=0;j<w.blocks.length;j++){var row=w.blocks[j],selected=false;for(var k=0;k<ex.blocks.length;k++)if(row.id===ex.blocks[k].id)selected=true;if(!selected){if(s.comparison_background_policy==="isolate_selected_passage"){var lastRead=s.reading_events[s.reading_events.length-1];if(!lastRead||row.start<lastRead.end&&row.end>lastRead.start)throw Error("Background isolation would hide necessary reading");ease(tr(row.layer,"ADBE Opacity"),Math.max(s.candidate_arrive,lastRead.end_time-.3),100);ease(tr(row.layer,"ADBE Opacity"),lastRead.end_time,0);ease(tr(row.layer,"ADBE Opacity"),Math.max(s.return_start,b-.35),0);ease(tr(row.layer,"ADBE Opacity"),b-1/24,100);}else{ease(tr(row.layer,"ADBE Opacity"),s.extract_start,100);ease(tr(row.layer,"ADBE Opacity"),s.settled,6);ease(tr(row.layer,"ADBE Opacity"),s.return_start,6);ease(tr(row.layer,"ADBE Opacity"),b-1/24,100);}}}
  var group=lift(s.excerpt,s,s.extract_start,b,s.kind==="replay"),choice=candidate(s,w,ex,s.kind==="replay");
  for(var j=0;j<s.attention_events.length;j++){var e=s.attention_events[j];if(e.target==="candidate")style(choice,Math.max(e.time,s.candidate_arrive),ink,e.phrase,orange);else for(var k=0;k<group.clones.length;k++)style(group.clones[k],Math.max(e.time,s.settled),ink,e.phrase,orange);}
  if(s.kind==="replay")audit.replays.push({scene:s.id,replay_of:s.replay_of,no_new_candidate_event:true});
 }else if(s.kind==="recap"){
  var recap=recapCamera(s);lastTarget=recap.target;lastDistance=recap.distance;
 }
 if(s.teaching_treatment)audit.teaching_resources.push({scene:s.id,treatment:s.teaching_treatment,motion:s.motion_treatment,critical_units:s.critical_units});
 audit.scenes.push({id:s.id,kind:s.kind,start:a,end:b,recognition_end:s.recognition_end,settled:s.settled,voice_start:s.voice_start,voice_end:s.voice_end,return_start:s.return_start,audience_intent:s.audience_intent});
}
for(var j=0;j<P.scenes.length;j++){var ss=P.scenes[j];if(ss.kind==="locate"){var margin=C.layers.addSolid(paper,"QUERY_READING_MARGIN_"+ss.id,1280,104,1,P.duration);margin.transform.position.setValue([640,52]);margin.inPoint=ss.start;margin.outPoint=ss.end;var carried=C.layer("CARRIED_QUERY_"+ss.id);carried.moveToBeginning();cmQueryHandoff(C,carried,worlds[ss.world].stem,margin,{scene:ss.id,return_start:ss.return_start,end:ss.end,origin:JSON.parse(carried.comment).origin,span:ss.locator.stem_span},audit,ink);}}
var band=C.layers.addSolid(paper,"CAPTION_SAFE_AREA",1280,105,1,P.duration);band.transform.position.setValue([640,667.5]);
for(var j=0;j<P.cues.length;j++){var q=P.cues[j],l=overlay("CAPTION_"+q.id,q.display_lines.join("\r"),84,624,33,1110,ink,q.start,q.end);l.comment=JSON.stringify({kind:"audio_aligned_exact_caption",segment:q.segment,text:q.text,start:q.start,end:q.end});audit.captions.push({id:l.id,text:q.text,start:q.start,end:q.end});}
for(var j=0;j<titles.length;j++)titles[j].moveToBeginning();overlay("MATERIAL_IDENTITY","英语有画说 · 学霸这题怎么做？  |  模拟诊断材料",76,570,20,1100,muted,0,P.scenes[0].end);
/* AUDIENCE_HOOK_V1_BEGIN */
// An explicitly source-bound teaser precedes the unchanged original tasks.
// Anonymous relation geometry is a viewing question, not another English fact.
function buildAudienceOpening(H){
 var d=H.decision,ph=H.phases,names=[],symbols=[],align0=ph.surface_align[0],align1=ph.surface_align[1],split1=ph.relation_displace[1],release=ph.match_into_task[0],end=H.end;
 function tag(l,role,source,sourceLayer){l.name="AUDIENCE_HOOK_"+role;l.inPoint=0;l.outPoint=end;l.motionBlur=true;l.comment=JSON.stringify({kind:"audience_opening_native_object",scene:H.scene_id,decision_sha:H.decision_sha,role:role,source_ref:source||null,source_layer_name:sourceLayer?sourceLayer.name:null,not_a_candidate_verdict:true});names.push(l.name);symbols.push(l);return l;}
 function clearKeys(p){while(p.numKeys)p.removeKey(p.numKeys);}
 function anchor(ref,start,col,k){var origin=null,w=worlds[ref.world];if(ref.pointer.indexOf("/options/")===0)origin=w.options[ref.pointer.slice(9)];else for(var i=0;i<w.blocks.length;i++){var row=w.blocks[i];if(row.start<=ref.start&&ref.end<=row.end){origin=row.layer;break;}}if(!origin)throw Error("Hook anchor lost its real native source");var l=origin.duplicate(),st=l.property("Source Text"),doc=st.value;clearKeys(st);doc.text=ref.quote;doc.fontSize=60;doc.leading=79.2;doc.fillColor=col;doc.applyFill=true;doc.applyStroke=false;st.setValue(doc);var anim=l.property("ADBE Text Properties").property("ADBE Text Animators");while(anim.numProperties)anim.property(anim.numProperties).remove();l.parent=null;var props=["ADBE Position","ADBE Scale","ADBE Orientation","ADBE Opacity"];for(var i=0;i<props.length;i++)clearKeys(tr(l,props[i]));tr(l,"ADBE Position").setValue(start);tr(l,"ADBE Scale").setValue([100,100,100]);tr(l,"ADBE Orientation").setValue([0,0,0]);tr(l,"ADBE Opacity").setValue(100);l.moveToBeginning();return tag(l,"ANCHOR_"+k,ref,origin);}
 function node(name,pos,col){var l=C.layers.addShape();l.threeDLayer=true;var g=l.property("ADBE Root Vectors Group"),circle=g.addProperty("ADBE Vector Shape - Ellipse");circle.property("ADBE Vector Ellipse Size").setValue([18,18]);var stroke=g.addProperty("ADBE Vector Graphic - Stroke");stroke.property("ADBE Vector Stroke Color").setValue(col);stroke.property("ADBE Vector Stroke Width").setValue(2.1);tr(l,"ADBE Position").setValue(pos);return tag(l,name);}
 function pathValue(vertices){var shape=new Shape();shape.vertices=vertices;shape.inTangents=[[0,0],[0,0],[0,0]];shape.outTangents=[[0,0],[0,0],[0,0]];shape.closed=false;return shape;}
 function edge(name,points,col){var l=C.layers.addShape();l.threeDLayer=true;tr(l,"ADBE Position").setValue([0,0,0]);var g=l.property("ADBE Root Vectors Group"),p=g.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape"),stroke=g.addProperty("ADBE Vector Graphic - Stroke");stroke.property("ADBE Vector Stroke Color").setValue(col);stroke.property("ADBE Vector Stroke Width").setValue(1.5);p=l.property("ADBE Root Vectors Group").property("ADBE Vector Shape - Group").property("ADBE Vector Shape");p.setValue(pathValue(points));tag(l,name);return {layer:l,path:p};}
 function move(l,a,b,c){ease(tr(l,"ADBE Position"),0,[a[0]-12,a[1]+8,a[2]]);ease(tr(l,"ADBE Position"),Math.min(1.1,align0-.1),a);ease(tr(l,"ADBE Position"),align0,a);ease(tr(l,"ADBE Position"),align1,b);ease(tr(l,"ADBE Position"),split1,c);ease(tr(l,"ADBE Position"),release,c);}
 var ends=[[[370,455,0],[785,455,0]],[[470,490,45],[880,490,45]]],same=[[425,455,0],[850,455,0]],different=[[[425,455,0],[850,455,0]],[[515,500,55],[755,420,55]]];
 for(var k=0;k<2;k++){
  var col=P.visual_states?(k?[.96,.66,.38]:[.47,.72,.9]):(k?orange:blue),start=k?[580,300,45]:[390,230,-25],word=anchor(d.confusion_trigger.anchor_refs[k],start,col,k);
  move(word,start,[490,275,0],[490,275,0]);
  for(var j=0;j<2;j++){var nd=node("ROLE_"+k+"_"+j,ends[k][j],col);move(nd,ends[k][j],same[j],different[k][j]);}
  var p0=[[ends[k][0][0],ends[k][0][1]],[640,440],[ends[k][1][0],ends[k][1][1]]],p1=[[425,455],[640,420],[850,455]],p2=[[different[k][0][0],different[k][0][1]],[640,420],[different[k][1][0],different[k][1][1]]],ed=edge("RELATION_"+k,p0,col);
  ease(ed.path,align0,pathValue(p0));ease(ed.path,align1,pathValue(p1));ease(ed.path,split1,pathValue(p2));ease(ed.path,release,pathValue(p2));ease(tr(ed.layer,"ADBE Position"),0,[0,0,k?45:0]);ease(tr(ed.layer,"ADBE Position"),align0,[0,0,k?45:0]);ease(tr(ed.layer,"ADBE Position"),align1,[0,0,0]);ease(tr(ed.layer,"ADBE Position"),split1,[0,0,k?55:0]);ease(tr(ed.layer,"ADBE Position"),release,[0,0,k?55:0]);
 }
 // The paper is revealed under the same settled camera; no black or source swap.
 var cover=C.layers.addSolid(P.visual_states?[23/255,24/255,26/255]:paper,"AUDIENCE_HOOK_SPACE",1280,720,1,P.duration);cover.inPoint=0;cover.outPoint=end;cover.moveAfter(C.layer("CAPTION_SAFE_AREA"));cover.comment=JSON.stringify({kind:"audience_opening_background",decision_sha:H.decision_sha,scene:H.scene_id});names.push(cover.name);
 ease(tr(cover,"ADBE Opacity"),0,100);ease(tr(cover,"ADBE Opacity"),release+.3,100);ease(tr(cover,"ADBE Opacity"),end-.1,0);
 for(var j=0;j<symbols.length;j++){var op=tr(symbols[j],"ADBE Opacity");ease(op,0,0);ease(op,.6,100);ease(op,release,100);ease(op,Math.min(end-.1,release+.3),0);}
 C.layer("MATERIAL_IDENTITY").inPoint=end;
 camera(0,[650,318,0],1580,[-8,-4],10);camera(align1,[640,320,0],1540,[8,-3],12);camera(split1,[640,320,0],1560,[0,0],12);camera(end,[640,320,0],1550,[0,0],14);
 audit.audience_hook={scene:H.scene_id,decision_sha:H.decision_sha,range:[0,end],phases:ph,objects:names,anchor_refs:d.confusion_trigger.anchor_refs,source_texts:d.visual_conflict.visible_text,payoff_scene_id:d.payoff_scene_id,original_task_scene:P.scenes[0].id,original_task_start:P.scenes[0].start,spoiler_boundary:d.spoiler_boundary,normal_speed_review:"UNOBSERVED",listening_review:"UNOBSERVED"};
}
if(P.audience_hook)buildAudienceOpening(P.audience_hook);
/* AUDIENCE_HOOK_V1_END */
/* SOURCE_ATTRIBUTION_V1_BEGIN */
if(P.source_attribution){
 audit.source_attribution=[];
 for(var worldName in P.source_attribution){
  var credit=P.source_attribution[worldName],scene=null;
  for(var si=0;si<P.scenes.length;si++)if(P.scenes[si].id===credit.scene_id)scene=P.scenes[si];
  if(!scene)throw Error("Paper attribution lost its question scene");
  var backing=C.layers.addSolid(paper,"SOURCE_ATTRIBUTION_SPACE_"+scene.id,1280,88,1,P.duration);
  backing.transform.position.setValue([640,99]);backing.inPoint=scene.start;backing.outPoint=scene.end;
  var paperCredit=overlay("SOURCE_PAPER_"+scene.id,credit.paper_display,72,63,17,1120,muted,scene.start,scene.end);
  var articleCredit=overlay("SOURCE_ARTICLE_"+scene.id,"阅读 "+credit.reading_section+" 篇 · 第"+credit.question_number+"题  |  "+credit.article_display,72,96,18,1120,ink,scene.start,scene.end);
  paperCredit.comment=JSON.stringify(credit);articleCredit.comment=JSON.stringify(credit);
  audit.source_attribution.push({world:worldName,scene:scene.id,start:scene.start,end:scene.end,paper:paperCredit.name,article:articleCredit.name,source_sha256:credit.source_sha256});
 }
}
/* SOURCE_ATTRIBUTION_V1_END */
/* READING_THINKING_STATE_V1_BEGIN */
if(P.visual_states){
 var windows=P.visual_states.thinking_windows,stateCode='function q(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}var w=0;';
 for(var i=0;i<windows.length;i++){var win=windows[i];stateCode+='w=Math.max(w,q((time-'+win.enter+')/'+(win.settled-win.enter)+')*(1-q((time-'+win.release+')/'+(win.end-win.release)+')));';}
 var screenCode=stateCode;
 if(P.audience_hook)screenCode+='if(time<'+P.audience_hook.end+')w=Math.max(w,thisComp.layer("AUDIENCE_HOOK_SPACE").transform.opacity/100);';
 var env=C.layers.addSolid([23/255,24/255,26/255],"THINKING_ENVIRONMENT",1280,720,1,P.duration);env.moveToEnd();tr(env,"ADBE Opacity").expression=stateCode+'100*w;';
 var reality=[];
 for(var name in worlds){var w=worlds[name];reality.push(w.questionPaper,w.paper,w.stem);for(var j=0;j<4;j++)reality.push(w.options["ABCD".charAt(j)]);for(var j=0;j<w.blocks.length;j++)reality.push(w.blocks[j].layer);}
 var stateAudit={definition:P.visual_states.definition,thinking_windows:windows,reality_layers:[],foreground_layers:[],environment:env.name,normal_speed_review:"UNOBSERVED"};
 for(var i=0;i<reality.length;i++){
  var l=reality[i],tint=l.property("ADBE Effect Parade").addProperty("ADBE Tint");tint.name="REALITY_DIM";tint.property(1).setValue([23/255,24/255,26/255]);tint.property(2).setValue([.125,.13,.14]);tint.property(3).expression=stateCode+'100*w;';
  var blur=l.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");blur.name="REALITY_BLUR";blur.property(1).expression=stateCode+'12*w;';blur.property(3).setValue(true);
  stateAudit.reality_layers.push(l.name);
 }
 for(var i=1;i<=C.numLayers;i++){
  var l=C.layer(i),st=l.property("Source Text");
  if(!st||l.name.indexOf("AUDIENCE_HOOK_")===0)continue;
  var original=false;for(var j=0;j<reality.length;j++)if(l.id===reality[j].id)original=true;if(original)continue;
  var screen=l.name.indexOf("CAPTION_")===0||l.name.indexOf("TASK_TITLE_")===0;
  var foreground=l.name.indexOf("EXTRACT_")===0||l.name.indexOf("CANDIDATE_FLIGHT_")===0||l.name.indexOf("REPLAY_")===0;
  if(!screen&&!foreground)continue;
  var code=screen?screenCode:stateCode,animators=l.property("ADBE Text Properties").property("ADBE Text Animators");
  for(var j=1;j<=animators.numProperties;j++){var props=animators.property(j).property("ADBE Text Animator Properties"),fill=props.property("ADBE Text Fill Color");if(fill&&fill.canSetExpression){var bright=fill.value[0]>.5?[.96,.66,.38]:[.47,.72,.9];fill.expression=code+'linear(w,0,1,value,'+JSON.stringify(bright)+');';}}
  var base=cmSelector(l,"THINKING_FOREGROUND_INK",0,st.value.text.length);base.property("ADBE Text Animator Properties").addProperty("ADBE Text Fill Color").setValue(paper);cmAmount(base).expression=code+'100*w;';base.moveTo(1);
  stateAudit.foreground_layers.push(l.name);
 }
 // Captions belong to the viewing state, not the blurred Reality Layer.
 if(P.audience_hook)tr(band,"ADBE Opacity").expression="time<"+P.audience_hook.end+"?0:100;";
 var bandTint=band.property("ADBE Effect Parade").addProperty("ADBE Tint");bandTint.name="CAPTION_STATE_BACKGROUND";bandTint.property(1).setValue([23/255,24/255,26/255]);bandTint.property(2).setValue([23/255,24/255,26/255]);bandTint.property(3).expression=screenCode+'100*w;';
 audit.visual_states=stateAudit;
}
/* READING_THINKING_STATE_V1_END */
function resize(comp,width,height){var factor=width/comp.width;comp.width=width;comp.height=height;for(var j=1;j<=comp.numLayers;j++){var l=comp.layer(j);if(l instanceof CameraLayer){var p=l.property("ADBE Camera Options Group").property("ADBE Camera Zoom");p.setValue(p.value*factor);}else if(!l.threeDLayer){var pos=l.transform.position,scale=l.transform.scale;if(pos.numKeys||scale.numKeys)throw Error("Unexpected animated screen transform");var v=pos.value;pos.setValue([v[0]*factor,v[1]*factor]);v=scale.value;scale.setValue([v[0]*factor,v[1]*factor]);}}}
resize(C,1920,1080);C.comment=JSON.stringify({revision:P.revision,author_sha256:P.author_sha256,role:"EDITORIAL_PROXY",plan_sha256:PLAN_SHA});var master=C.duplicate();master.name="MAIN_FILM_MASTER_4K24";resize(master,3840,2160);master.comment=JSON.stringify({revision:P.revision,author_sha256:P.author_sha256,role:"UNRENDERED_4K_MASTER",plan_sha256:PLAN_SHA});
for(var j=1;j<=app.project.numItems;j++)app.project.item(j).selected=false;C.selected=true;C.openInViewer();C.time=0;
var result={project_path:PROJECT_PATH,comp_id:C.id,master_comp_id:master.id,frames:P.frames,duration:C.duration,width:C.width,height:C.height,layers:C.numLayers,audit:audit,media_role:"EDITORIAL_PROXY",formal_4k_rendered:false};
var recoveryFile=new File(BUILD_RECEIPT_PATH);recoveryFile.encoding="UTF-8";if(!recoveryFile.open("w"))throw Error("Cannot preserve pre-save native readback");recoveryFile.write(JSON.stringify({state:"BUILT_NOT_SAVED",result:result}));recoveryFile.close();
app.project.save(new File(PROJECT_PATH));if(!app.project.file)throw Error("Native project save failed; inspect the preserved build before any retry");result.project_path=app.project.file.fsName;return result;
