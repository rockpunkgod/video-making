/* Native text, font, geometry and settled reading-state audit. */
(function(){
 var cp=AEMCP.compById(V9_COMP_ID),rows=[],issues=[],samples=V9_SAMPLE_TIMES;
 for(var i=1;i<=cp.numLayers;i++){
  var l=cp.layer(i);if(!(l instanceof TextLayer))continue;
  var t=(l.inPoint+l.outPoint)/2,p=l.property('ADBE Text Properties').property('ADBE Text Document'),d=p.valueAtTime(t,false);
  rows.push({name:l.name,text:d.text,font:d.font,size:d.fontSize,fillColor:d.fillColor,motionBlur:l.motionBlur,boxOverflow:d.boxOverflow===true,expressionError:p.expressionError});
  if(d.boxOverflow===true||p.expressionError)issues.push({kind:'text_overflow_or_expression',name:l.name});
 }
 for(var s=0;s<samples.length;s++){
  var t=samples[s],active=[];
  for(var i=1;i<=cp.numLayers;i++){
   var l=cp.layer(i);if(!(l instanceof TextLayer)||t<l.inPoint||t>=l.outPoint||l.transform.opacity.valueAtTime(t,false)<99)continue;
   var r=l.sourceRectAtTime(t,false),p=l.transform.position.valueAtTime(t,false),a=l.transform.anchorPoint.valueAtTime(t,false);
   var b={name:l.name,x:p[0]+r.left-a[0],y:p[1]+r.top-a[1],width:r.width,height:r.height};active.push(b);
   if(b.x<140||b.y<92||b.x+b.width>1780||b.y+b.height>1080)issues.push({kind:'safe_bounds',time:t,bounds:b});
  }
  for(var i=0;i<active.length;i++)for(var j=i+1;j<active.length;j++){
   var a=active[i],b=active[j],dx=Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x),dy=Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y);
   if(dx>1&&dy>1)issues.push({kind:'text_collision',time:t,a:a.name,b:b.name,dx:dx,dy:dy});
  }
 }
 var audio=cp.layer('INTERNAL_SCRATCH_VOICE');
 var effects=[];for(var i=1;i<=cp.numLayers;i++){var fx=cp.layer(i).property('ADBE Effect Parade');if(fx&&fx.numProperties)effects.push(cp.layer(i).name);}
 return JSON.stringify({valid:issues.length===0,rows:rows,issues:issues,effectLayers:effects,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration,motionBlur:cp.motionBlur,shutterAngle:cp.shutterAngle,audioEnabled:audio.audioEnabled,audioFile:audio.source.file.fsName});
})();
