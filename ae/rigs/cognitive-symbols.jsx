function cmHookSymbolPose(S,p){if(!S)return p;var k=S.parameters.layout.width/1080,o=S.parameters.space.origin;return [640+(p[0]-640)*k+o[0],320+(p[1]-320)*k+o[1],(p.length>2?p[2]:0)+S.parameters.space.depth+o[2]];}
function cmHookSymbolPaths(S,points){var out=[];for(var i=0;i<points.length;i++){var p=cmHookSymbolPose(S,points[i]);out.push([p[0],p[1]]);}return out;}
// Cognitive Symbol Library native consumer. One authored timeline and host.
// Every visible letter is a source-range handoff, never a replacement text card.
function cmSymbolLine(layer,at){
 var d=layer.property("Source Text").valueAtTime(0,false),bp=d.boxTextPos,bl=d.baselineLocs;
 for(var k=0;k<d.composedLineCount;k++){var r=d.composedLineRange(k,k+1);if(at>=r.characterStart&&at<r.characterEnd)return {x:bl[k*4]-bp[0]+cmChallengeMeasure(d.text.slice(r.characterStart,at),d),y:bl[k*4+1]-bp[1],doc:d};}
 throw Error("Symbol glyph no longer belongs to a measured original line");
}
function cmSymbolWorld(layer,t,offset){
 var p=tr(layer,"ADBE Position").valueAtTime(t,false),sc=tr(layer,"ADBE Scale").valueAtTime(t,false),point=[p[0]+offset[0]*sc[0]/100,p[1]+offset[1]*sc[1]/100,p[2]],scale=sc[0];
 if(layer.parent){var par=layer.parent,pp=tr(par,"ADBE Position").valueAtTime(t,false),ps=tr(par,"ADBE Scale").valueAtTime(t,false),o=tr(par,"ADBE Orientation").valueAtTime(t,false);if(Math.abs(o[0])+Math.abs(o[1])+Math.abs(o[2])>.001)throw Error("Read the settled source before symbolic carry");point=[pp[0]+point[0]*ps[0]/100,pp[1]+point[1]*ps[1]/100,pp[2]+point[2]*ps[2]/100];scale*=ps[0]/100;}
 return {position:point,scale:scale};
}
function cmSymbolSource(S,input){
 var id=input.source_object_id;
 if(S.variant==="lesson")id=input.source_ref.pointer==="/passage"?"EXTRACT_"+S.scene_id+"_"+id:"CANDIDATE_FLIGHT_"+S.scene_id;
 var layer=C.layer(id);if(!layer)throw Error("Recipe lost native original: "+id);
 var text=layer.property("Source Text").valueAtTime(S.start,false).text;
 if(text.slice(input.source_character_start,input.source_character_end).replace(/\r/g,"\n")!==input.source_ref.quote.replace(/\r/g,"\n"))throw Error("Recipe glyphs changed source identity");
 return layer;
}
function cmSymbolMask(layer,name,lo,hi){if(hi>lo){var an=cmSelector(layer,name,lo,hi);an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);cmAmount(an).setValue(100);}}
function cmSymbolGlyph(S,input,origin){
 var source=cmSymbolSource(S,input),lo=input.source_character_start,hi=input.source_character_end,line=cmSymbolLine(source,lo),doc=line.doc,bp=doc.boxTextPos,pose=cmSymbolWorld(source,S.start,[line.x,line.y]),l=source.duplicate();
 l.name="SYMBOL_GLYPH_"+S.symbol_id+"_"+input.object_id;l.parent=null;l.inPoint=S.start;l.outPoint=S.end;l.motionBlur=true;
 var st=l.property("Source Text");while(st.numKeys)st.removeKey(st.numKeys);doc=source.property("Source Text").valueAtTime(S.start,false);doc.fillColor=ink;if(doc.text.length)doc.characterRange(0,doc.text.length).fillColor=ink;st.setValue(doc);
 var anim=l.property("ADBE Text Properties").property("ADBE Text Animators");while(anim.numProperties)anim.property(anim.numProperties).remove();
 for(var pi=0;pi<4;pi++){var prop=tr(l,["ADBE Position","ADBE Scale","ADBE Orientation","ADBE Opacity"][pi]);while(prop.numKeys)prop.removeKey(prop.numKeys);if(prop.canSetExpression)prop.expression="";}
 tr(l,"ADBE Anchor Point").setValue([bp[0]+line.x,bp[1]+line.y,0]);tr(l,"ADBE Orientation").setValue([0,0,0]);tr(l,"ADBE Opacity").setValue(100);
 cmSymbolMask(l,"SYMBOL_OUTSIDE_BEFORE",0,lo);cmSymbolMask(l,"SYMBOL_OUTSIDE_AFTER",hi,doc.text.length);
 var target=S.layout.positions[input.object_id],dest=[origin[0]+target[0],origin[1]+target[1],origin[2]+target[2]],finalScale=S.parameters.font.size/doc.fontSize*100,lock=S.phases[2].end,returnAt=S.end-.45;
 if(returnAt<lock+.5)throw Error("Recipe lacks stable recognition before return");
 var actualWidth=cmChallengeMeasure(input.source_ref.quote,doc)*finalScale/100;
 if(actualWidth>(S.parameters.layout.width-S.parameters.layout.min_gap)/2-2*S.parameters.layout.min_gap)throw Error("Actual native font exceeds Recipe slot: "+input.object_id);
 // Preserve each original glyph while a wrapped source phrase reflows into its
 // compact comparison slot. The inverse motion restores the complete source.
 var staged=S.recipe_id==="same_form_different_relation"&&S.parameters.phase_seconds,action=input.role==="source_action"||input.role==="candidate_action",depart=staged&&action?S.phases[0].end:S.start,arrive=staged&&!action?S.phases[0].end:S.phases[1].end;
 var rx=/\S+/g,m,advance=0,wordRows=[],priorEnd=0,reflowRow=0;
 while((m=rx.exec(input.source_ref.quote))!==null){var newlines=input.source_ref.quote.slice(priorEnd,m.index).match(/\n/g);if(newlines){reflowRow+=newlines.length;advance=0;}var a=lo+m.index,z=a+m[0].length,word=cmSymbolLine(source,a),delta=[line.x+advance-word.x,line.y+reflowRow*doc.fontSize*S.parameters.font.line_height-word.y,0],an=cmSelector(l,"SYMBOL_REFLOW_"+wordRows.length,a,z);an.property("ADBE Text Animator Properties").addProperty("ADBE Text Position 3D").setValue(delta);var amt=cmAmount(an);ease(amt,S.start,0);ease(amt,depart,0);ease(amt,arrive,100);ease(amt,returnAt,100);ease(amt,S.end-1/240,0);wordRows.push({start:a,end:z,delta:delta});advance+=cmChallengeMeasure(m[0]+" ",doc);priorEnd=m.index+m[0].length;}
 ease(tr(l,"ADBE Position"),S.start,pose.position);ease(tr(l,"ADBE Scale"),S.start,[pose.scale,pose.scale,pose.scale]);ease(tr(l,"ADBE Position"),depart,pose.position);ease(tr(l,"ADBE Scale"),depart,[pose.scale,pose.scale,pose.scale]);ease(tr(l,"ADBE Position"),arrive,dest);ease(tr(l,"ADBE Scale"),arrive,[finalScale,finalScale,finalScale]);ease(tr(l,"ADBE Position"),returnAt,dest);ease(tr(l,"ADBE Scale"),returnAt,[finalScale,finalScale,finalScale]);
 if(staged&&action){ease(tr(l,"ADBE Opacity"),S.start,100);ease(tr(l,"ADBE Opacity"),S.start+.25,18);ease(tr(l,"ADBE Opacity"),depart,18);ease(tr(l,"ADBE Opacity"),arrive,100);}
 // A recap is already a completed judgement. Fade its carried glyphs during
 // source return, so the ending cannot freeze on an isolated rejected option.
 if(S.variant==="recall"){ease(tr(l,"ADBE Opacity"),returnAt,100);ease(tr(l,"ADBE Opacity"),S.end-1/24,0);}
 var back=cmSymbolWorld(source,S.end,[line.x,line.y]);ease(tr(l,"ADBE Position"),S.end-1/240,back.position);ease(tr(l,"ADBE Scale"),S.end-1/240,[back.scale,back.scale,back.scale]);
 var hidden=cmSelector(source,"SYMBOL_SOURCE_HANDOFF_"+S.symbol_id+"_"+input.object_id,lo,hi);hidden.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);hold(cmAmount(hidden),0,0);hold(cmAmount(hidden),S.start,100);hold(cmAmount(hidden),S.end,0);
 l.comment=JSON.stringify({kind:"continuous_original_glyph_range",symbol_id:S.symbol_id,recipe_id:S.recipe_id,role:input.role,source_layer_name:source.name,source_layer_id:source.id,source_object_id:input.source_object_id,source_ref:input.source_ref,range:[lo,hi],original_text:doc.text,new_text_created:false,word_reflow:wordRows});
 return {name:l.name,id:l.id,source_name:source.name,source_id:source.id,range:[lo,hi],quote:input.source_ref.quote,origin:pose.position,destination:dest,return_position:back.position,scale:finalScale,width:actualWidth,role:input.role,object_id:input.object_id,return_at:returnAt};
}
function cmSymbolPath(S,name,from,to,col,planeZ){
 var l=C.layers.addShape();l.name="SYMBOL_RELATION_"+S.symbol_id+"_"+name;l.threeDLayer=true;l.inPoint=S.start;l.outPoint=S.end;tr(l,"ADBE Position").setValue([0,0,0]);
 var root=l.property("ADBE Root Vectors Group"),path=root.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape"),stroke=root.addProperty("ADBE Vector Graphic - Stroke");stroke.property("ADBE Vector Stroke Color").setValue(col);stroke.property("ADBE Vector Stroke Width").setValue(1.5);path=root.property("ADBE Vector Shape - Group").property("ADBE Vector Shape");
 function shape(points){var sh=new Shape();sh.vertices=points;sh.inTangents=[[0,0],[0,0],[0,0]];sh.outTangents=[[0,0],[0,0],[0,0]];sh.closed=false;return sh;}
 ease(path,S.start,shape(from));ease(path,S.phases[1].end,shape(to));ease(path,S.end-.45,shape(to));ease(tr(l,"ADBE Opacity"),S.start,0);ease(tr(l,"ADBE Opacity"),S.phases[0].end,100);ease(tr(l,"ADBE Opacity"),S.end-.45,100);ease(tr(l,"ADBE Opacity"),S.end,0);
 tr(l,"ADBE Position").setValue([0,0,planeZ]);l.comment=JSON.stringify({kind:"verified_relation_structure",symbol_id:S.symbol_id,recipe_id:S.recipe_id,relation:S.relation,authority:S.authority,source_refs:(function(){var out=[];for(var i=0;i<S.inputs.length;i++)out.push(S.inputs[i].source_ref);return out;})(),not_teaching_authority:true});return {name:l.name,id:l.id,from:from,to:to};
}
function cmBuildSymbolRecipe(S){
 if(S.variant==="hook"){
  var names=["AUDIENCE_HOOK_ANCHOR_0","AUDIENCE_HOOK_ANCHOR_1","AUDIENCE_HOOK_ROLE_0_0","AUDIENCE_HOOK_ROLE_0_1","AUDIENCE_HOOK_ROLE_1_0","AUDIENCE_HOOK_ROLE_1_1","AUDIENCE_HOOK_RELATION_0","AUDIENCE_HOOK_RELATION_1"];
  for(var i=0;i<names.length;i++)if(!C.layer(names[i]))throw Error("Anonymous Recipe lost its current source-bound Hook objects");
  return {symbol_id:S.symbol_id,recipe_id:S.recipe_id,variant:S.variant,scene_id:S.scene_id,range:[S.start,S.end],objects:names,consumer:"PARAMETERIZED_EXISTING_ANONYMOUS_HOOK",spoiler_boundary:"NO_ACTION_LABELS_NO_VERDICT",source_refs:S.inputs};
 }
 var scene=null;for(var i=0;i<P.scenes.length;i++)if(P.scenes[i].id===S.scene_id)scene=P.scenes[i];if(!scene)throw Error("Recipe lost current scene");
 var center=S.variant==="lesson"?stage(info(scene.excerpt,scene)):question(worlds[S.inputs[0].source_ref.world]),o=S.parameters.space.origin,origin=[center[0]+o[0],center[1]+o[1],center[2]+o[2]],glyphs=[],roles={};
 for(var i=0;i<S.inputs.length;i++){var g=cmSymbolGlyph(S,S.inputs[i],origin);glyphs.push(g);roles[g.role]=g;}
 if(S.variant==="recall"){
  // Recalled glyph ranges carry the evidence; the full old question is not a
  // second readable layer behind them. Restore only after this ending scene.
  var w=worlds[S.inputs[0].source_ref.world],background=[w.stem];
  for(var ci=0;ci<4;ci++)background.push(w.options["ABCD".charAt(ci)]);
  for(var bi=0;bi<w.blocks.length;bi++)background.push(w.blocks[bi].layer);
  for(var bi=0;bi<background.length;bi++){var op=tr(background[bi],"ADBE Opacity"),prior=op.valueAtTime(S.start,false);ease(op,S.start,prior);ease(op,S.start+.3,0);ease(op,scene.end-1/24,0);hold(op,scene.end,prior);}
 }
 if(S.variant==="lesson"){var dimmed={};for(var gi=0;gi<glyphs.length;gi++){var name=glyphs[gi].source_name;if(dimmed[name])continue;dimmed[name]=true;var op=tr(C.layer(name),"ADBE Opacity");ease(op,S.start,100);ease(op,S.start+.3,0);ease(op,S.end-.45,0);ease(op,S.end,100);}}
 var blueSymbol=[126/255,150/255,168/255],brick=[163/255,111/255,100/255],paths=[],z=origin[2];
 function point(role){var g=roles[role];return [g.destination[0]+g.width/2,g.destination[1]+28];}
 if(S.recipe_id==="semantic_isomorphism"){
  var subject=point("subject"),referent=point("referent"),relation=[origin[0],origin[1]-65],same=[subject,relation,referent];
  paths.push(cmSymbolPath(S,"source_price",[subject,[origin[0]-90,origin[1]-25],referent],same,blueSymbol,glyphs[0].destination[2]));paths.push(cmSymbolPath(S,"candidate_price",[subject,[origin[0]+90,origin[1]-100],referent],same,blueSymbol,glyphs[0].destination[2]));
 }else{
  var noun=point("source_noun"),left=point("source_action"),right=point("candidate_action");left[1]-=60;right[1]-=60;var join=[noun,[noun[0],noun[1]+60],left];
  paths.push(cmSymbolPath(S,"participation",join,join,blueSymbol,glyphs[0].destination[2]));paths.push(cmSymbolPath(S,"chair_role",join,[noun,[noun[0],noun[1]+60],right],brick,glyphs[0].destination[2]));
 }
 return {symbol_id:S.symbol_id,recipe_id:S.recipe_id,scene_id:S.scene_id,variant:S.variant,range:[S.start,S.end],glyphs:glyphs,paths:paths,origin:origin,actual_native_font_metrics:true,source_identity:"SOURCE_RANGE_SAME_GLYPHS_CONTINUOUS_HANDOFF",artistic_review:"PENDING"};
}
