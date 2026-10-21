// Fold the actual original article glyphs into the neutral challenge view.
// The same TextLayers, source spans and sense groups return to the Reading Rig.
function cmChallengeMeasure(value,doc){
 if(!value.length)return 0;
 var probe=C.layers.addText(value),prop=probe.property("Source Text"),d=prop.value;d.font=doc.font;d.fontSize=doc.fontSize;d.tracking=doc.tracking;prop.setValue(d);
 // Ink rectangles omit spaces and side bearings. Native baseline endpoints
 // measure the actual typographic advance, including every original space.
 var bl=prop.value.baselineLocs,width=0;for(var i=0;i<bl.length;i+=4)width=Math.max(width,bl[i+2]-bl[i]);probe.remove();
 if(!isFinite(width)||width<0)throw Error("Native font advance is unavailable");return width;
}
function cmChallengeArticle(w,ch){
 var fontsize=17,width=760,lineHeight=20.4,left=w.base+40,top=132,x=0,y=fontsize,rows=[],names=[],maxRight=0;
 // Extend the existing question paper while the same article travels behind
 // it. Its inherited width left a thin clipped column at the camera's edge.
 // Restore its exact original dimensions before ordinary Reading resumes.
 hold(tr(w.questionPaper,"ADBE Scale"),0,[100,100,100]);hold(tr(w.questionPaper,"ADBE Scale"),ch.start,[115,100,100]);ease(tr(w.questionPaper,"ADBE Scale"),ch.end,[115,100,100]);ease(tr(w.questionPaper,"ADBE Scale"),ch.handoff_end,[100,100,100]);
 for(var bi=0;bi<w.blocks.length;bi++){
  var b=w.blocks[bi],l=b.layer,d=l.property("Source Text").valueAtTime(0,false),scale=fontsize/d.fontSize,baselines=d.baselineLocs,bp=d.boxTextPos;
  names.push(l.name);hold(tr(l,"ADBE Position"),0,[b.x,b.y,b.z]);hold(tr(l,"ADBE Scale"),0,[100,100,100]);
  hold(tr(l,"ADBE Position"),ch.start,[left,top,0]);hold(tr(l,"ADBE Scale"),ch.start,[scale*100,scale*100,scale*100]);
  ease(tr(l,"ADBE Position"),ch.end,[left,top,0]);ease(tr(l,"ADBE Scale"),ch.end,[scale*100,scale*100,scale*100]);
  // The article passes behind the retained question paper while returning to
  // its real place in the continuous world. No duplicate text or opacity reset.
  ease(tr(l,"ADBE Position"),ch.end+.12,[left+(b.x-left)*.08,top+(b.y-top)*.08,100]);
  ease(tr(l,"ADBE Position"),ch.handoff_end,[b.x,b.y,b.z]);ease(tr(l,"ADBE Scale"),ch.handoff_end,[100,100,100]);
  hold(tr(l,"ADBE Opacity"),ch.start,100);
  for(var ck=0;ck<b.reading_chunks.length;ck++){
   var c=b.reading_chunks[ck],lo=c.start-b.start,hi=c.end-b.start,line=null;
   for(var li=0;li<d.composedLineCount;li++){var rr=d.composedLineRange(li,li+1);if(lo>=rr.characterStart&&hi<=rr.characterEnd){line={index:li,start:rr.characterStart};break;}}
   if(!line)throw Error("Challenge cannot split original sense group: "+c.id);
   var advance=cmChallengeMeasure(c.text,d)*scale,gap=cmChallengeMeasure(" ",d)*scale;
   if(advance>width)throw Error("Challenge sense group exceeds full source column: "+c.id);
   if(x&&x+advance>width){x=0;y+=lineHeight;}
   if(y>472)throw Error("Complete original article overflows challenge; revise layout, never truncate");
   var origX=baselines[line.index*4]-bp[0]+cmChallengeMeasure(d.text.slice(line.start,lo),d),origY=baselines[line.index*4+1]-bp[1],delta=[x/scale-origX,y/scale-origY,0];
   var name="CHALLENGE_FOLD_"+ch.scene+"_"+rows.length,an=cmSelector(l,name,lo,hi);an.property("ADBE Text Animator Properties").addProperty("ADBE Text Position 3D").setValue(delta);
   var amount=cmAmount(an);hold(amount,0,0);hold(amount,ch.start,100);ease(amount,ch.end,100);ease(amount,ch.handoff_end,0);
   rows.push({chunk_id:c.id,text:c.text,start:c.start,end:c.end,source_layer:l.name,source_layer_id:l.id,animator:name,range:[lo,hi],delta:delta,source_position:[b.x,b.y,b.z],challenge_position:[left,top,0],scale:scale*100,baseline:[left+x,top+y,0],width:advance});
   maxRight=Math.max(maxRight,x+advance);x+=advance+gap;
  }
 }
 return {article_layers:names,chunks:rows,width:maxRight,height:y+4,source_identity:"SAME_ORIGINAL_TEXTLAYERS_NO_RECREATION"};
}
