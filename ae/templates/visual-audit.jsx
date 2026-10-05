/* Read-only actual AE color/style/shape audit; V8_COMP_ID supplied by caller. */
(function(){
 var cp=AEMCP.compById(V8_COMP_ID),rows=[],warnings=[];
 for(var i=1;i<=cp.numLayers;i++){
  var l=cp.layer(i);if(!l.enabled)continue;var at=(l.inPoint+l.outPoint)/2;
  if(l.threeDLayer)warnings.push({layer:l.name,reason:'large_3d_transform_not_allowed'});
  if(l.property('ADBE Effect Parade')&&l.property('ADBE Effect Parade').numProperties)warnings.push({layer:l.name,reason:'unapproved_effect'});
  if(l instanceof TextLayer){var d=l.property('Source Text').valueAtTime(at,false);rows.push({name:l.name,type:'text',color:d.fillColor,font:d.font,size:d.fontSize,tracking:d.tracking});}
  if(l instanceof ShapeLayer){
   var groups=l.property('ADBE Root Vectors Group');
   for(var j=1;j<=groups.numProperties;j++){
    var props=groups.property(j).property('ADBE Vectors Group');
    for(var k=1;k<=props.numProperties;k++){
     var p=props.property(k);
     if(p.matchName==='ADBE Vector Graphic - Fill')rows.push({name:l.name,type:'fill',color:p.property('ADBE Vector Fill Color').valueAtTime(at,false)});
     if(p.matchName==='ADBE Vector Shape - Rect'&&p.property('ADBE Vector Rect Roundness').value>0)warnings.push({layer:l.name,reason:'bubble_card'});
     if(p.matchName==='ADBE Vector Graphic - G-Fill')warnings.push({layer:l.name,reason:'gradient'});
    }
   }
  }
  if(l.name==='PAPER'&&(l.position.numKeys||l.position.expression))warnings.push({layer:l.name,reason:'constant_background_motion'});
 }
 return JSON.stringify({comp_id:String(cp.id),rows:rows,style_drift_warnings:warnings});
})();
