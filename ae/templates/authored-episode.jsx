// Portable native realization of the existing private AV-plan choreography.
// ES3; every source and candidate string comes from the checked frozen input.
var f=new File(PLAN_PATH);f.encoding="UTF-8";if(!f.open("r"))throw Error("Missing AV plan");var P=JSON.parse(f.read());f.close();
if(app.project.dirty||app.project.renderQueue.rendering)throw Error("Existing project must be clean and idle");
if(new File(PROJECT_PATH).exists)throw Error("Inspect existing revision before build");
app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=8;
var C=app.project.items.addComp("MAIN_FILM_EDITORIAL_PROXY",1280,720,1,P.duration,24);
C.renderer="ADBE Advanced 3d";C.bgColor=[.035,.065,.10];C.motionBlur=true;C.shutterAngle=120;
var ink=[.08,.12,.16],paper=[.955,.946,.92],ivory=[.96,.95,.91],blue=[.28,.66,.89],orange=[1,.58,.24],muted=[.55,.65,.70];
var audit={sources:[],extractions:[],candidates:[],camera:[],locators:[],replays:[],scenes:[],captions:[]};
function tr(l,n){return l.property("ADBE Transform Group").property(n);}
function ease(p,t,v){p.setValueAtTime(t,v);var n=p.nearestKeyIndex(t),a=[],b=[],dims=v instanceof Array?v.length:1;var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;if(spatial||p.propertyValueType===PropertyValueType.COLOR)dims=1;for(var i=0;i<dims;i++){a.push(new KeyframeEase(0,65));b.push(new KeyframeEase(0,65));}p.setTemporalEaseAtKey(n,a,b);p.setInterpolationTypeAtKey(n,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);if(spatial&&p.matchName!=="ADBE Orientation"){var z=v.length===3?[0,0,0]:[0,0];p.setSpatialTangentsAtKey(n,z,z);}}
function hold(p,t,v){p.setValueAtTime(t,v);var k=p.nearestKeyIndex(t);p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}
function text(name,value,x,y,z,size,width,color,font){var l=C.layers.addBoxText([width,1500]);l.name=name;var p=l.property("Source Text"),d=p.value;d.text=value;d.font=font||"ArialMT";d.fontSize=size;d.autoLeading=false;d.leading=size*1.22;d.fillColor=color;d.applyFill=true;d.applyStroke=false;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);l.threeDLayer=true;var bp=p.value.boxTextPos;tr(l,"ADBE Anchor Point").setValue([bp[0],bp[1],0]);tr(l,"ADBE Position").setValue([x,y,z]);return l;}
function rect(name,w,h,x,y,z,col){var l=C.layers.addSolid(col,name,w,h,1,P.duration);l.threeDLayer=true;tr(l,"ADBE Anchor Point").setValue([0,0,0]);tr(l,"ADBE Position").setValue([x,y,z]);return l;}
function overlay(name,value,x,y,size,width,col,a,b){var l=text(name,value,x,y,0,size,width,col,"MicrosoftYaHei");l.threeDLayer=false;l.inPoint=a;l.outPoint=b;return l;}
function style(l,t,color,phrase,accent){var p=l.property("Source Text"),d=p.valueAtTime(t,false);d.fillColor=color;if(phrase){var at=d.text.indexOf(phrase);if(at>=0)d.characterRange(at,at+phrase.length).fillColor=accent;}p.setValueAtTime(t,d);hold(p,t,d);}
var bg=C.layers.addSolid([.035,.065,.10],"COGNITIVE_SPACE",1280,720,1,P.duration);bg.moveToEnd();
var cam=C.layers.addCamera("READING_CAMERA",[640,360]);cam.property("ADBE Camera Options Group").property("ADBE Camera Zoom").setValue(1500);cam.property("ADBE Camera Options Group").property("ADBE Camera Depth of Field").setValue(false);
function camera(t,c,dist,tilt){dist=dist||1500;tilt=tilt||[0,0];ease(tr(cam,"ADBE Anchor Point"),t,c);ease(tr(cam,"ADBE Position"),t,[c[0]+tilt[0],c[1]+tilt[1],c[2]-dist]);audit.camera.push({time:t,target:c,distance:dist,offset:tilt});}
var worlds={},blocks={},lastTarget=[640,330,0],lastDistance=1500,titles=[];
function stage(w){return [w.base+640,-1450,-140];}
function question(w){return [w.base+640,330,0];}
for(var wi=0;wi<P.world_order.length;wi++){
 var name=P.world_order[wi],data=P.worlds[name],q=data.question,base=wi*10000,w={base:base,blocks:[],options:{},question:q};worlds[name]=w;
 rect(name+"_QUESTION_PAPER",1320,780,base-20,-40,60,paper);
 w.stem=text(name+"_QUESTION",q.stem,base+80,95,0,50,1120,ink);
 for(var j=0;j<4;j++){var cid="ABCD".charAt(j),op=text(name+"_OPTION_"+cid,cid+"   "+q.options[cid],base+90,230+j*80,0,46,1120,ink);op.comment=JSON.stringify({kind:"original_option",question_id:q.question_id,candidate:cid,exact_text:q.options[cid]});hold(tr(op,"ADBE Opacity"),0,100);style(op,0,ink,null,null);w.options[cid]=op;}
 var y=40;
 for(var j=0;j<data.blocks.length;j++){var b=data.blocks[j];if(!b.visible){y+=22;continue;}var l=text(b.id,b.text,base+2250,y,100,46,1080,ink),r=l.sourceRectAtTime(0,false);l.comment=JSON.stringify({kind:"original_passage",source:data.source,field:"passage",start:b.start,end:b.end,exact_text:b.text});var row={id:b.id,start:b.start,end:b.end,text:b.text,layer:l,x:base+2250,y:y,z:100,height:r.height};blocks[b.id]=row;w.blocks.push(row);audit.sources.push({id:b.id,layer_id:l.id,start:b.start,end:b.end,text:b.text,position:[row.x,y,100],height:r.height});y+=Math.max(r.height+38,50);}
 w.paper=rect(name+"_PASSAGE_PAPER",1300,Math.ceil(y+100),base+2190,-20,150,paper);
 rect(name+"_EXIT_OCCLUDER",1400,950,base+1300,-1900,0,[.035,.065,.10]);
}
function info(key){var ex=P.excerpts[key],a=[];for(var i=0;i<ex.block_ids.length;i++)a.push(blocks[ex.block_ids[i]]);var first=a[0],last=a[a.length-1];return {key:key,blocks:a,x:first.x,y:first.y,z:100,height:last.y+last.height-first.y,world:worlds[ex.world]};}
function sourceTarget(ex){return [ex.x+540,ex.y+Math.min(245,ex.height/2)+15,100];}
function lift(key,s,start,end,replay){var ex=info(key),w=ex.world,ns=C.layers.addNull();ns.name="SOURCE_LIFT_"+s.id;ns.threeDLayer=true;ns.inPoint=start;ns.outPoint=end;tr(ns,"ADBE Anchor Point").setValue([0,0,0]);var origin=[ex.x,ex.y,100],dest=[w.base+80,-1690,-140],settled=start+s.travel_seconds,clones=[];var scale=Math.min(110,360/ex.height*100);
 for(var j=0;j<ex.blocks.length;j++){var b=ex.blocks[j],l=b.layer.duplicate();l.name="EXTRACT_"+s.id+"_"+b.id;l.parent=ns;tr(l,"ADBE Position").setValue([0,b.y-ex.y,0]);l.inPoint=start;l.outPoint=end;l.motionBlur=true;hold(tr(b.layer,"ADBE Opacity"),Math.max(0,start-1/24),100);hold(tr(b.layer,"ADBE Opacity"),start,0);hold(tr(b.layer,"ADBE Opacity"),end,100);style(l,start,ink,null,null);style(l,start+s.travel_seconds*.4,ivory,null,null);clones.push(l);}
 ease(tr(ns,"ADBE Position"),start,origin);ease(tr(ns,"ADBE Position"),start+s.travel_seconds*.5,[(origin[0]+dest[0])/2,(origin[1]+dest[1])/2,(origin[2]+dest[2])/2]);ease(tr(ns,"ADBE Position"),settled,dest);
 ease(tr(ns,"ADBE Orientation"),start,[0,0,0]);ease(tr(ns,"ADBE Orientation"),start+s.travel_seconds*.45,[4,-9,0]);ease(tr(ns,"ADBE Orientation"),settled,[0,0,0]);ease(tr(ns,"ADBE Scale"),start,[100,100,100]);ease(tr(ns,"ADBE Scale"),settled,[scale,scale,scale]);
 var returnStart=end-.65;ease(tr(ns,"ADBE Position"),returnStart,dest);ease(tr(ns,"ADBE Position"),end-1/24,origin);ease(tr(ns,"ADBE Scale"),returnStart,[scale,scale,scale]);ease(tr(ns,"ADBE Scale"),end-1/24,[100,100,100]);
 for(var j=0;j<clones.length;j++)style(clones[j],end-1/24,ink,null,null);
 ns.comment=JSON.stringify({kind:replay?"replay_of_reviewed_comparison":"continuous_source_extraction",scene_id:s.id,source:P.excerpts[key],original_ids:(function(){var a=[];for(var k=0;k<ex.blocks.length;k++)a.push(ex.blocks[k].layer.id);return a;})(),new_candidate_event:false});
 audit.extractions.push({scene:s.id,key:key,start:start,settled:settled,end:end,group_id:ns.id,origin:origin,destination:dest,return_start:returnStart,scale:scale,replay:replay});return {group:ns,clones:clones};}
function candidate(s,w,replay){var origin=w.options[s.candidate],r=tr(origin,"ADBE Position").value,l=origin.duplicate();l.name=(replay?"REPLAY_CANDIDATE_":"CANDIDATE_FLIGHT_")+s.id;l.inPoint=s.candidate_start;l.outPoint=s.end;l.motionBlur=true;var arrive=s.candidate_start+.8,dest=[w.base+90,-1265,-175];
 style(origin,s.start,ink,s.candidate+"   ",[.64,.22,.045]);style(origin,s.end,ink,null,null);if(s.candidate_entry_seconds){hold(tr(origin,"ADBE Opacity"),s.start,100);hold(tr(origin,"ADBE Opacity"),s.candidate_start,0);if(s.event!=="eliminate")hold(tr(origin,"ADBE Opacity"),s.end,100);}
 ease(tr(l,"ADBE Position"),s.candidate_start,r);if(s.candidate_entry_seconds)ease(tr(l,"ADBE Position"),s.candidate_start+.4,[(r[0]+dest[0])/2,(r[1]+dest[1])/2,(r[2]+dest[2])/2]);ease(tr(l,"ADBE Position"),arrive,dest);ease(tr(l,"ADBE Orientation"),s.candidate_start,[0,0,0]);ease(tr(l,"ADBE Orientation"),arrive-.25,[0,9,0]);ease(tr(l,"ADBE Orientation"),arrive,[0,0,0]);ease(tr(l,"ADBE Scale"),s.candidate_start,[100,100,100]);ease(tr(l,"ADBE Scale"),arrive,[112,112,112]);style(l,s.candidate_start,ink,null,null);style(l,s.candidate_start+(s.candidate_entry_seconds?.25:.35),ivory,null,null);
 if(s.event){var ev=s.event_time;if(s.event==="eliminate"){ease(tr(l,"ADBE Position"),ev,dest);ease(tr(l,"ADBE Position"),ev+.45,[w.base+1750,-1210,420]);ease(tr(l,"ADBE Orientation"),ev,[0,0,0]);ease(tr(l,"ADBE Orientation"),ev+.45,[0,72,0]);hold(tr(origin,"ADBE Opacity"),ev+.45,38);}var st=overlay("LOCAL_STATE_"+s.id,s.event==="supported"?s.candidate+" 有依据 · 其余待核":s.candidate+" 排除",76,83,25,1120,s.event==="supported"?blue:muted,ev,s.end);titles.push(st);audit.candidates.push({scene:s.id,kind:s.event,candidate:s.candidate,time:ev,layer_id:l.id,whole_option_text:l.property("Source Text").value.text,refs:s.terminal_refs,exit_end:s.event==="eliminate"?ev+.45:null});}
 l.comment=JSON.stringify({kind:replay?"recalled_candidate":"whole_candidate_with_attached_identity",candidate:s.candidate,scene:s.id,source_layer_id:origin.id,terminal_refs:s.terminal_refs});return l;}
function locate(s,w){var loc=s.locator,first=null,last=null,hit=null;for(var j=0;j<w.blocks.length;j++){var b=w.blocks[j];if(b.start>=loc.block_span[0]&&b.end<=loc.block_span[1]){if(!first)first=b;last=b;}if(b.start<=loc.passage_span[0]&&b.end>=loc.passage_span[1])hit=b;}if(!first||!last||!hit)throw Error("Locator source block is unavailable");
 var a=s.start,b=s.end,span=b-a,opening=[w.base+2780,300,100],match=[w.base+2780,hit.y+70,100],scope=[w.base+2780,(first.y+last.y+last.height)/2,100];var arrive=a+span*.24,found=a+span*.55,scoped=a+span*.74;
 camera(a,lastTarget,lastDistance);camera(arrive,opening,2000);camera(arrive+.45,opening,2000);camera(found,match,2000);camera(found+.35,match,2000);camera(scoped,scope,Math.max(2300,(last.y+last.height-first.y)*3.6));camera(b-.08,scope,Math.max(2300,(last.y+last.height-first.y)*3.6));
 style(w.stem,a,ink,loc.identity,[.64,.22,.045]);style(w.stem,b,ink,null,null);style(hit.layer,found,ink,loc.identity,[.64,.22,.045]);style(hit.layer,b,ink,null,null);
 var query=overlay("LOCATOR_QUERY_"+s.id,loc.identity,76,89,32,1000,orange,a,b);titles.push(query);
 var bracket=rect("LOCATOR_SCOPE_"+s.id,3,Math.ceil(last.y+last.height-first.y),w.base+2215,first.y,99,blue);bracket.inPoint=scoped;bracket.outPoint=b;
 audit.locators.push({scene:s.id,question_span:loc.stem_span,passage_span:loc.passage_span,block_span:loc.block_span,opening_at:arrive,match_at:found,scope_at:scoped,scope_until:b});lastTarget=scope;lastDistance=Math.max(2300,(last.y+last.height-first.y)*3.6);
}
for(var si=0;si<P.scenes.length;si++){
 var s=P.scenes[si],w=worlds[s.world],a=s.start,b=s.end;var title=overlay("TASK_TITLE_"+s.id,s.title,76,24,42,1120,ivory,a,b);titles.push(title);
 if(s.kind==="task"||s.kind==="answer"){
  var qt=question(w);camera(a,lastTarget,lastDistance);camera(a+.75,qt,1500);camera(b-.08,qt,1500);lastTarget=qt;lastDistance=1500;
  if(s.kind==="answer"){for(var j=0;j<4;j++){var cid="ABCD".charAt(j),label=cid===s.candidate?"答案 "+cid:cid+" 已排除",col=cid===s.candidate?[.06,.39,.54]:[.38,.41,.42];var st=text("FINAL_"+s.world+cid,label,w.base+960,232+j*80,-10,25,235,col,"MicrosoftYaHei");st.inPoint=s.event_time;st.outPoint=P.duration;}style(w.options[s.candidate],s.event_time,[.06,.39,.54],null,null);audit.candidates.push({scene:s.id,kind:"final",candidate:s.candidate,time:s.event_time,refs:s.terminal_refs});}
 }else if(s.kind==="locate"){locate(s,w);
 }else if(s.kind==="compare"||s.kind==="replay"){
  var ex=info(s.excerpt),visit=sourceTarget(ex),st=stage(w),liftStart=s.extract_start,settle=s.settled;
  camera(a,lastTarget,lastDistance);
  var lead=s.candidate_entry_seconds||0;if(lead){var qt=question(w),ct=s.candidate_start;camera(a+.4,qt,1500);camera(ct,qt,1500);camera(ct+.4,[(qt[0]+st[0])/2,(qt[1]+st[1])/2,(qt[2]+st[2])/2],1500,[70,-25]);camera(ct+.8,st,1500);camera(ct+1.2,st,1500);}
  if(s.pre_excerpt){var pre=sourceTarget(info(s.pre_excerpt));camera(a+.65,pre,1500);camera(a+s.recognition_seconds*.48,pre,1500);camera(liftStart-.45,visit,1500);}
  else camera(a+lead+Math.min(.75,s.recognition_seconds*.55),visit,1500);
  camera(liftStart,visit,1500);camera(liftStart+s.travel_seconds*.5,[(visit[0]+st[0])/2,(visit[1]+st[1])/2,(visit[2]+st[2])/2],1500,[70,-25]);camera(settle,st,1500);camera(b-.75,st,1500);
  var returned=sourceTarget(ex);camera(b-.65,st,1500);camera(b-.08,returned,1500);lastTarget=returned;lastDistance=1500;
  var group=lift(s.excerpt,s,liftStart,s.secondary_excerpt?s.secondary_at:b,s.kind==="replay"),choice=s.candidate?candidate(s,w,s.kind==="replay"):null;
  if(s.secondary_excerpt){var second=info(s.secondary_excerpt),visit2=sourceTarget(second),t=s.secondary_at,s2={id:s.id+"_SECOND",travel_seconds:1.2};camera(t-.8,st,1500);camera(t,visit2,1500);camera(t+.6,visit2,1500);camera(t+1.2,[(visit2[0]+st[0])/2,(visit2[1]+st[1])/2,(visit2[2]+st[2])/2],1500,[70,-25]);camera(t+1.8,st,1500);lift(s.secondary_excerpt,s2,t+.6,b,false);camera(b-.08,visit2,1500);lastTarget=visit2;}
  for(var j=0;j<s.attention_events.length;j++){var e=s.attention_events[j];if(e.target==="candidate"&&choice)style(choice,Math.max(e.time,s.candidate_start+.8),ivory,e.phrase,orange);else for(var k=0;k<group.clones.length;k++)style(group.clones[k],Math.max(e.time,settle),ivory,e.phrase,orange);}
  if(s.kind==="replay"){var r=overlay("REPLAY_STATE_"+s.id,"回看已完成的比较 · 答案保持",76,83,25,1100,blue,a,b);titles.push(r);audit.replays.push({scene:s.id,replay_of:s.replay_of,no_new_candidate_event:true});}
 }else if(s.kind==="recap"){
  // Preserve completed states. This is a question-world return, not a second replay.
  var first=worlds[s.recap_worlds[0]],second=worlds[s.recap_worlds[1]],mid=a+(b-a)*.5;
  camera(a,lastTarget,lastDistance);camera(a+.8,question(first),1500);camera(mid-.4,question(first),1500);camera(mid+.5,question(second),1500);camera(b-.1,question(second),1500);lastTarget=question(second);lastDistance=1500;
 }
 audit.scenes.push({id:s.id,kind:s.kind,start:a,end:b,recognition_end:s.recognition_end,settled:s.settled,voice_start:s.voice_start,voice_end:s.voice_end,audience_intent:s.audience_intent});
}
var header=C.layers.addSolid([.035,.065,.10],"TITLE_SAFE_AREA",1280,78,1,P.duration);header.transform.position.setValue([640,39]);
for(var j=0;j<P.scenes.length;j++){var s=P.scenes[j];if(s.kind==="locate"){var h=C.layers.addSolid([.035,.065,.10],"LOCATOR_HEADER_"+s.id,1280,139,1,P.duration);h.transform.position.setValue([640,69.5]);h.inPoint=s.start;h.outPoint=s.end;}}
var band=C.layers.addSolid([.025,.045,.07],"CAPTION_SAFE_AREA",1280,114,1,P.duration);band.transform.position.setValue([640,663]);
var line=C.layers.addSolid([.22,.41,.50],"LOWER_RULE",1128,2,1,P.duration);line.transform.position.setValue([640,605]);
for(var j=0;j<P.cues.length;j++){var q=P.cues[j],l=overlay("CAPTION_"+q.id,q.display_lines.join("\r"),84,617,36,1110,[.97,.97,.95],q.start,q.end);l.comment=JSON.stringify({kind:"audio_aligned_exact_caption",segment:q.segment,text:q.text,start:q.start,end:q.end});audit.captions.push({id:l.id,text:q.text,start:q.start,end:q.end});}
for(var j=0;j<titles.length;j++)titles[j].moveToBeginning();
overlay("MATERIAL_IDENTITY","英语有画说 · 学霸这题怎么做？  |  模拟诊断材料",76,566,23,1100,muted,0,P.scenes[0].end);
function resize(comp,width,height){var factor=width/comp.width;comp.width=width;comp.height=height;for(var j=1;j<=comp.numLayers;j++){var l=comp.layer(j);if(l instanceof CameraLayer){var p=l.property("ADBE Camera Options Group").property("ADBE Camera Zoom");p.setValue(p.value*factor);}else if(!l.threeDLayer){var pos=l.transform.position,scale=l.transform.scale;if(pos.numKeys||scale.numKeys)throw Error("Unexpected animated screen transform");var v=pos.value;pos.setValue([v[0]*factor,v[1]*factor]);v=scale.value;scale.setValue([v[0]*factor,v[1]*factor]);}}}
resize(C,1920,1080);C.comment=JSON.stringify({revision:P.revision,author_sha256:P.author_sha256,role:"EDITORIAL_PROXY",plan_sha256:PLAN_SHA});
var master=C.duplicate();master.name="MAIN_FILM_MASTER_4K24";resize(master,3840,2160);master.comment=JSON.stringify({revision:P.revision,author_sha256:P.author_sha256,role:"UNRENDERED_4K_MASTER",plan_sha256:PLAN_SHA});
for(var j=1;j<=app.project.numItems;j++)app.project.item(j).selected=false;C.selected=true;C.openInViewer();C.time=0;app.project.save(new File(PROJECT_PATH));
return {project_path:app.project.file.fsName,comp_id:C.id,master_comp_id:master.id,frames:P.frames,duration:C.duration,width:C.width,height:C.height,layers:C.numLayers,audit:audit,media_role:"EDITORIAL_PROXY",formal_4k_rendered:false};
