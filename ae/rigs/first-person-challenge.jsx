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
// Layout only: keep the original paragraph and table boundaries. Measurements
// are native font advances; no new text objects replace the reading glyphs.
function cmChallengeStructuredLayout(groups,layout,width,fontsize,lineHeight){
 var placed={},y=fontsize,regions=[],maxRight=0;
 function region(cell,left,available,top,kind,row,col){
  var selected=[],i,x=0,yy=top,lines=[[]];
  if(cell.start===null)return top;
  for(i=0;i<groups.length;i++){var g=groups[i];if(g.end<=cell.start||g.start>=cell.end)continue;
   if(g.start<cell.start||g.end>cell.end)throw Error("Sense group crosses original paragraph/table boundary: "+g.id);
   selected.push(g);
  }
  if(!selected.length)throw Error("Original layout region has no source glyphs");
  // A paragraph indent is expressed relative to its source font size. Retain
  // it only when the original source actually records it.
  var indent=cell.first_line_indent_twips,sourceSize=cell.font_size_half_points;
  if(kind!=="table"&&typeof indent==="number"&&typeof sourceSize==="number"&&sourceSize>0)x=indent/(sourceSize*10)*fontsize;
  if(x<0||x>=available)throw Error("Original paragraph indent cannot fit challenge column");
  for(i=0;i<selected.length;i++){var g=selected[i];if(g.width>available)throw Error("Original layout sense group exceeds its column: "+g.id);
   if(x&&x+g.width>available&&lines[lines.length-1].length){x=0;yy+=lineHeight;lines.push([]);}
   if(x+g.width>available)throw Error("Original first-line indent leaves insufficient readable space");
   var p={x:left+x,y:yy,width:g.width,kind:kind,row:row,column:col};placed[g.id]=p;lines[lines.length-1].push(p);x+=g.width+g.gap;
  }
  for(i=0;i<lines.length;i++){var line=lines[i],right=line[line.length-1].x+line[line.length-1].width,shift=0;
   if(cell.alignment==="center")shift=(2*left+available-line[0].x-right)/2;
   else if(cell.alignment==="right")shift=left+available-right;
   for(var j=0;j<line.length;j++){
    if(cell.alignment==="both"&&i<lines.length-1&&line.length>1)line[j].x+=j*(left+available-right)/(line.length-1);
    line[j].x+=shift;maxRight=Math.max(maxRight,line[j].x+line[j].width);
   }
  }
  regions.push({start:cell.start,end:cell.end,kind:kind,block_index:bi,row:row,column:col,left:left,top:top,bottom:yy+4,width:available,alignment:cell.alignment||null});
  return yy;
 }
 for(var bi=0;bi<layout.blocks.length;bi++){var block=layout.blocks[bi];
  if(block.kind==="table"){
   var sum=0;for(var ci=0;ci<block.column_widths_twips.length;ci++)sum+=block.column_widths_twips[ci];
   for(var ri=0;ri<block.rows.length;ri++){var xx=0,bottom=y;
    for(var ci=0;ci<block.rows[ri].length;ci++){var cw=width*block.column_widths_twips[ci]/sum;
     bottom=Math.max(bottom,region(block.rows[ri][ci],xx+4,cw-8,y,"table",ri,ci));xx+=cw;
    }y=bottom+lineHeight;
   }
   y+=lineHeight*.4;
  }else{y=region(block,0,width,y,block.kind,null,null)+lineHeight*1.5;}
 }
 for(var i=0;i<groups.length;i++)if(!placed[groups[i].id])throw Error("Original layout omitted source glyphs: "+groups[i].id);
 var bottom=0;for(var id in placed)bottom=Math.max(bottom,placed[id].y+4);
 if(bottom>476)throw Error("Original article format exceeds challenge area; revise layout, never flatten or truncate");
 return {positions:placed,regions:regions,height:bottom,width:maxRight};
}
function cmChallengeArticle(w,ch){
 var fontsize=17,width=760,lineHeight=20.4,left=w.base+40,top=132,x=0,y=fontsize,rows=[],names=[],maxRight=0;
 var structured=null;
 if(ch.source_layout){var groups=[];
  for(var bi=0;bi<w.blocks.length;bi++){var bb=w.blocks[bi],dd=bb.layer.property("Source Text").valueAtTime(0,false),ss=fontsize/dd.fontSize;
   for(var ck=0;ck<bb.reading_chunks.length;ck++){var cc=bb.reading_chunks[ck];groups.push({id:cc.id,start:cc.start,end:cc.end,width:cmChallengeMeasure(cc.text,dd)*ss,gap:cmChallengeMeasure(" ",dd)*ss});}
  }
  structured=cmChallengeStructuredLayout(groups,ch.source_layout,width,fontsize,lineHeight);
 }
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
   var placement=structured?structured.positions[c.id]:null;
   if(placement){x=placement.x;y=placement.y;}
   else if(x&&x+advance>width){x=0;y+=lineHeight;}
   if(y>472)throw Error("Complete original article overflows challenge; revise layout, never truncate");
   var origX=baselines[line.index*4]-bp[0]+cmChallengeMeasure(d.text.slice(line.start,lo),d),origY=baselines[line.index*4+1]-bp[1],delta=[x/scale-origX,y/scale-origY,0];
   var name="CHALLENGE_FOLD_"+ch.scene+"_"+rows.length,an=cmSelector(l,name,lo,hi);an.property("ADBE Text Animator Properties").addProperty("ADBE Text Position 3D").setValue(delta);
   var amount=cmAmount(an);hold(amount,0,0);hold(amount,ch.start,100);ease(amount,ch.end,100);ease(amount,ch.handoff_end,0);
   rows.push({chunk_id:c.id,text:c.text,start:c.start,end:c.end,source_layer:l.name,source_layer_id:l.id,animator:name,range:[lo,hi],delta:delta,source_position:[b.x,b.y,b.z],challenge_position:[left,top,0],scale:scale*100,baseline:[left+x,top+y,0],width:advance});
   maxRight=Math.max(maxRight,x+advance);x+=advance+gap;
  }
 }
 return {article_layers:names,chunks:rows,width:structured?structured.width:maxRight,height:structured?structured.height:y+4,source_identity:"SAME_ORIGINAL_TEXTLAYERS_NO_RECREATION",source_layout:structured?{regions:structured.regions,binding:ch.source_layout_binding,status:"NATIVE_STRUCTURAL_LAYOUT"}:null};
}
