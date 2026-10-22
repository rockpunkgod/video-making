// Shared production rig. Literal glyph ranges only: no evidence selection,
// method inference or new wording. The language-author's article units survive
// native line composition; layout must not invent a new linguistic boundary.
function cmSmooth(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(x*6-15)+10);}
function cmEnvelope(start,end){
 var ramp=Math.min(3/24,(end-start)*.375);
 return 'function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}\nvar a=s((time-'+start+')/'+ramp+')*s(('+end+'-time)/'+ramp+');\n';
}
function cmSelector(layer,name,lo,hi){
 var tp=layer.property('ADBE Text Properties'),an=tp.property('ADBE Text Animators').addProperty('ADBE Text Animator');an.name=name;
 tp.property('ADBE Text More Options').property('ADBE Text Anchor Point Option').setValue(2);
 var sel=an.property('ADBE Text Selectors').addProperty('ADBE Text Selector'),ad=sel.property('ADBE Text Range Advanced');
 ad.property('ADBE Text Range Units').setValue(2);sel.property('ADBE Text Index Start').setValue(lo);sel.property('ADBE Text Index End').setValue(hi);ad.property('ADBE Text Selector Smoothness').setValue(0);
 return an;
}
function cmAmount(an){return an.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount');}
function cmKeepChunks(layer,block){
 if(!block.reading_chunks||!block.reading_chunks.length)throw Error('Missing article sense groups: '+block.id);
 var prop=layer.property('Source Text'),d=prop.value;
 for(var j=0;j<block.reading_chunks.length;j++){var c=block.reading_chunks[j],lo=c.start-block.start,hi=c.end-block.start;
  if(d.text.slice(lo,hi)!==c.text)throw Error('Article chunk differs from source: '+c.id);
  var range=d.characterRange(lo,hi);if(typeof range.noBreak==='undefined')throw Error('Native noBreak support required');range.noBreak=true;
 }
 prop.setValue(d);d=prop.value;
 for(var j=0;j<block.reading_chunks.length;j++){var c=block.reading_chunks[j],found=false;
  for(var k=0;k<d.composedLineCount;k++){var r=d.composedLineRange(k,k+1);if(c.start-block.start>=r.characterStart&&c.end-block.start<=r.characterEnd)found=true;}
  if(!found)throw Error('Sense group does not fit the native line; revise layout, never auto-split: '+c.text);
 }
 if(layer.sourceRectAtTime(0,false).width>d.boxTextSize[0]+1)throw Error('Sense group overflows the reading column: '+block.id);
}
function cmMappedChunks(value,lo,hi,block){
 if(!block.reading_chunks)throw Error('Run article chunking before native reading');
 var out=[];
 for(var j=0;j<block.reading_chunks.length;j++){var c=block.reading_chunks[j],a=c.start-block.start,b=c.end-block.start;if(a>=hi||b<=lo)continue;
  if(a<lo||b>hi)throw Error('Native line split a semantic chunk: '+c.text);
  if(value.slice(a,b)!==c.text)throw Error('Chunk text changed: '+c.id);
  out.push({chunk_id:c.id,start:a,end:b,text:c.text});
 }
 return out;
}
function cmReadingSequence(rows,event,scene,audit,ink,blue,orange,preferred){
 var units=[],layers={},j,k;
 for(j=0;j<rows.length;j++){
  var r=rows[j],b=r.block,d=b.layer.property('Source Text').valueAtTime(0,false),lo=r.start-b.start,hi=r.end-b.start;
  var chunks=preferred?[]:cmMappedChunks(d.text,lo,hi,b);
  for(k=0;k<chunks.length;k++){chunks[k].row=r.line;chunks[k].layer=b.layer;chunks[k].source_start=b.start;units.push(chunks[k]);}
  layers[b.layer.id]=b.layer;
 }
 if(preferred){
  var measured=units;units=[];
  for(j=0;j<preferred.length;j++){var pc=preferred[j],match=null;for(k=0;k<rows.length;k++)if(rows[k].line===pc.row&&pc.start>=rows[k].start-rows[k].block.start&&pc.end<=rows[k].end-rows[k].block.start){match=rows[k];break;}
   if(!match||match.block.layer.property('Source Text').value.text.slice(pc.start,pc.end)!==pc.text)throw Error('Preferred chunk no longer matches native layout');
   units.push({row:pc.row,layer:match.block.layer,source_start:match.block.start,start:pc.start,end:pc.end,text:pc.text,center:pc.center,half:pc.attack+pc.hold/2});
  }
 }
 if(!units.length)throw Error('No exact reading chunks: '+scene);
 var span=event.end_time-event.arrival,slot=span/units.length;
 if(slot<4/24-1e-6)throw Error('Reading window too short for visible phrase handoffs: '+scene+' span '+event.start+'-'+event.end+'; '+units.length+' native groups in '+span+' seconds; minimum '+(units.length*4/24)+' seconds');
 var half=slot*.55,windowId=scene+'_'+audit.reading_windows.length,records=[];
 for(var id in layers){
  var l=layers[id],neutral=cmSelector(l,'CM_BASE_'+windowId,0,l.property('Source Text').value.text.length);
  neutral.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(ink);
  cmAmount(neutral).expression='time>='+event.arrival+'&&time<'+event.end_time+'?100:0;';
 }
 for(j=0;j<units.length;j++){
  var u=units[j],center=u.center===undefined?event.arrival+(j+.5)*slot:u.center,radius=u.half===undefined?half:u.half,start=Math.max(event.arrival,center-radius),end=Math.min(event.end_time,center+radius),name='CM_READ_'+windowId+'_'+j;
  var an=cmSelector(u.layer,name,u.start,u.end),expr=cmEnvelope(start,end)+'[100+4*a,100+4*a,100];';
  an.property('ADBE Text Animator Properties').addProperty('ADBE Text Scale 3D').expression=expr;
  var color=cmSelector(u.layer,name+'_COLOR',u.start,u.end);
  color.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(blue);cmAmount(color).expression=cmEnvelope(start,end)+'100*a;';
  var record={scene:scene,window:windowId,chunk_id:u.chunk_id||null,layer_id:u.layer.id,layer_name:u.layer.name,animator:name,color_animator:color.name,row:u.row,start:u.start,end:u.end,text:u.text,source_start:u.source_start+u.start,source_end:u.source_start+u.end,time_start:start,time_end:end,center:center,peak_scale:104,expression:expr,curve:'C2_smootherstep_attack_hold_release'};
  audit.word_focus.push(record);records.push(record);
 }
 // Orange is a hit, not an early answer marker: reveal it after the reading
 // focus has actually reached the bound phrase; no new hit is inferred.
 if(event.phrase)for(var id in layers){var l=layers[id],d=l.property('Source Text').valueAtTime(0,false),at=d.text.indexOf(event.phrase);if(at<0)continue;
  var reached=null;for(j=0;j<records.length;j++)if(records[j].layer_id===l.id&&records[j].start<=at&&records[j].end>at)reached=records[j].center;
  if(reached!==null){var hit=cmSelector(l,'CM_HIT_'+windowId,at,at+event.phrase.length);hit.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(orange);cmAmount(hit).expression='function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}time<'+event.end_time+'?100*s((time-'+reached+')/'+Math.min(.25,slot)+'):0;';}
 }
 audit.reading_windows.push({id:windowId,scene:scene,source_start:event.start,source_end:event.end,arrival:event.arrival,end_time:event.end_time,mode:event.mode,chunk_count:records.length,chunks:records});
 return records;
}
function cmProject(point,cam,t,width,height){
 var c=cam.transform.position.valueAtTime(t,false),q=cam.transform.pointOfInterest.valueAtTime(t,false),f=[],v=[],n=0;
 for(var j=0;j<3;j++){f[j]=q[j]-c[j];n+=f[j]*f[j];v[j]=point[j]-c[j];}n=Math.sqrt(n);for(var j=0;j<3;j++)f[j]/=n;
 n=Math.sqrt(f[2]*f[2]+f[0]*f[0]);var r=[f[2]/n,0,-f[0]/n],u=[f[1]*r[2],f[2]*r[0]-f[0]*r[2],-f[1]*r[0]],depth=0,x=0,y=0;
 for(var j=0;j<3;j++){depth+=v[j]*f[j];x+=v[j]*r[j];y+=v[j]*u[j];}
 var zoom=cam.cameraOption.zoom.value;return [width/2+x*zoom/depth,height/2+y*zoom/depth,depth];
}
function cmQueryHandoff(comp,query,question,margin,spec,audit,ink){
 var start=spec.return_start,end=spec.end-1/24,origin=spec.origin,cam=comp.layer('READING_CAMERA'),screen=cmProject(query.transform.position.valueAtTime(start,false),cam,start,comp.width,comp.height),prior=query.transform.position.expression||'value;';
 var normal=[screen[0]/comp.width,screen[1]/comp.height,screen[2]],qscale=query.transform.scale.valueAtTime(start,false),priorScale=query.transform.scale.expression||'value;';
 var blend='function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}var a=s((time-'+start+')/'+(end-start)+');';
 var body=blend+'var cam=thisComp.layer("READING_CAMERA"),c=cam.toWorld([0,0,0]),f=normalize(sub(cam.transform.pointOfInterest,c)),r=normalize(cross([0,1,0],f)),u=cross(f,r),z=cam.cameraOption.zoom,o='+JSON.stringify(origin)+',v=o-c,od=dot(v,f),q='+JSON.stringify(normal)+';var ox=thisComp.width/2+dot(v,r)*z/od,oy=thisComp.height/2+dot(v,u)*z/od;var x=q[0]*thisComp.width*(1-a)+Math.max(q[0]*thisComp.width,Math.min(thisComp.width*.86,ox))*a,y=q[1]*thisComp.height*(1-a)+Math.max(q[1]*thisComp.height,oy)*a,d=q[2]*(1-a)+od*a;c+f*d+r*((x-thisComp.width/2)*d/z)+u*((y-thisComp.height/2)*d/z);';
 query.transform.position.expression='if(time<'+start+'){'+prior+'}else if(time>='+end+'){'+JSON.stringify(origin)+';}else{'+body+'}';
 query.transform.scale.expression='if(time<'+start+'){'+priorScale+'}else{'+blend+JSON.stringify(qscale)+'*(1-a)+[100,100,100]*a;}';
 var color=cmSelector(query,'CM_QUERY_COLOR_'+spec.scene,0,query.property('Source Text').value.text.length),from=query.property('Source Text').value.characterRange(0,1).fillColor;
 color.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').expression=blend+JSON.stringify([from[0],from[1],from[2],1])+'*(1-a)+'+JSON.stringify([ink[0],ink[1],ink[2],1])+'*a;';
 var join=cmSelector(question,'CM_QUERY_SOURCE_'+spec.scene,spec.span[0],spec.span[1]);join.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(ink);cmAmount(join).expression='time>='+ (spec.end-.5/24) +'?100:0;';
 // The top band must be gone before the sentence returns into view.
 var fadeStart=start+(end-start)*.40,fadeEnd=end-Math.min(.25,(end-start)*.2);
 margin.transform.opacity.expression='function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}100*(1-s((time-'+fadeStart+')/'+(fadeEnd-fadeStart)+'));';
 var receipt={scene:spec.scene,layer_id:query.id,layer_name:query.name,margin:margin.name,question:question.name,origin:origin,span:spec.span,start:start,end:spec.end,landed:end,fade_start:fadeStart,fade_end:fadeEnd,screen:normal,position_expression:query.transform.position.expression,color_animator:color.name,source_animator:join.name};
 audit.query_handoffs.push(receipt);return receipt;
}
