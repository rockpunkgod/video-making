/* Read-only independent pixel/layout state audit. V8_COMP_ID supplied by caller. */
(function(){
 var cp=AEMCP.compById(V8_COMP_ID),rows=[],overflow=[];
 for(var i=1;i<=cp.numLayers;i++){
  var l=cp.layer(i); if(!(l instanceof TextLayer)) continue;
  var t=Math.max(l.inPoint,0)+(Math.min(l.outPoint,cp.duration)-Math.max(l.inPoint,0))/2;
  var p=l.property('ADBE Text Properties').property('ADBE Text Document');var d=p.valueAtTime(t,false);
  var r=l.sourceRectAtTime(t,false),pos=l.transform.position.valueAtTime(t,false),a=l.transform.anchorPoint.valueAtTime(t,false);
  var x=pos[0]+r.left-a[0],y=pos[1]+r.top-a[1];
  var row={name:l.name,font:d.font,size:d.fontSize,x:x,y:y,width:r.width,height:r.height,start:l.inPoint,end:l.outPoint,text:d.text,boxOverflow:d.boxOverflow===true,expressionError:p.expressionError};
  rows.push(row);
  if(row.boxOverflow||x<80||x+r.width>1010||y<248||y+r.height>1904||p.expressionError) overflow.push(row);
 }
 for(var i=0;i<rows.length;i++) for(var j=i+1;j<rows.length;j++) {
  var a=rows[i],b=rows[j];
  if(Math.max(a.start,b.start)>=Math.min(a.end,b.end)-0.001)continue;
  var dx=Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x),dy=Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y);
  if(dx>1&&dy>1)overflow.push({type:'text_collision',a:a.name,b:b.name,dx:dx,dy:dy});
 }
 return JSON.stringify({ok:true,comp_id:String(cp.id),rows:rows,overflow:overflow,valid:overflow.length===0});
})();
