/* Neutral original-task projections, before any reviewed explanation. */
(function(){
 var f=new File(QUESTION_FIRST_REQUEST);f.encoding='UTF-8';f.open('r');var r=JSON.parse(f.read());f.close();
 var dest=new File(r.project);
 if(dest.exists||!app.project.file||app.project.file.fsName!==(new File(r.previous_project)).fsName)throw new Error('Project changed');
 app.project.save();app.project.save(dest);
 function rgb(hex){return [parseInt(hex.substr(1,2),16)/255,parseInt(hex.substr(3,2),16)/255,parseInt(hex.substr(5,2),16)/255];}
 function text(cp,name,value,x,y,size,font){
  var l=cp.layers.addText(value);l.name=name;var st=l.property('Source Text'),d=st.value;
  d.font=font;d.fontSize=size;d.applyFill=true;d.fillColor=rgb('#243530');d.applyStroke=false;
  d.tracking=0;d.autoLeading=false;d.leading=size*1.24;d.justification=ParagraphJustification.LEFT_JUSTIFY;st.setValue(d);
  var b=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue([b.left,b.top]);l.transform.position.setValue([x,y]);return l;
 }
 var result=[];
 app.beginUndoGroup('Original task before explanation');
 try{
  for(var cid in r.sequence.cards){
   if(!r.sequence.cards.hasOwnProperty(cid))continue;
   var card=r.sequence.cards[cid],cp=app.project.items.addComp(cid,1920,1080,1,60,24),rows=[];
   cp.layers.addSolid(rgb('#FAF8F2'),'PAPER',1920,1080,1,60);
   for(var i=0;i<card.nodes.length;i++){
    var n=card.nodes[i],l=text(cp,n.name,n.text,n.x,n.y,n.size,n.font),b=l.sourceRectAtTime(0,false),d=l.property('Source Text').value;
    if(b.width>n.w+12||n.y+b.height>1000)throw new Error('Original task overflow: '+cid+'/'+n.name);
    rows.push({name:n.name,text:d.text,font:d.font,size:d.fontSize,width:b.width,height:b.height});
   }
   text(cp,'PAUSE_HINT','原题 · 可暂停阅读',110,1022,24,'NotoSansSC-Regular');
   cp.comment=JSON.stringify({sequence_sha:r.sequence.sequence_sha,card_id:cid,kind:card.kind,answer_states:'absent'});
   var frame=new File(r.frames+'/'+cid+'.png');cp.saveFrameToPng(0,frame);
   result.push({card_id:cid,comp_id:cp.id,frame:frame.fsName,rows:rows});
  }
  app.project.save(dest);return JSON.stringify({project:dest.fsName,cards:result});
 }finally{app.endUndoGroup();}
})();
