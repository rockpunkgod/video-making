// Shared native grammar. Temporal curves extracted from the approved RCF proof.
// Standalone native scripting has no JSON global. Parse only our generated comments.
if(typeof JSON==='undefined'){
 var JSON={stringify:function(v){
  if(v===null)return 'null';if(typeof v==='number'||typeof v==='boolean')return String(v);
  if(typeof v==='string')return '"'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\x00-\x1f]/g,function(c){var s=c.charCodeAt(0).toString(16);return '\\u'+('0000'+s).slice(-4);})+'"';
  var a=[],i;if(v instanceof Array){for(i=0;i<v.length;i++)a.push(JSON.stringify(v[i]));return '['+a.join(',')+']';}
  for(i in v)if(v.hasOwnProperty(i)&&v[i]!==undefined)a.push(JSON.stringify(i)+':'+JSON.stringify(v[i]));return '{'+a.join(',')+'}';
 },parse:function(s){return eval('('+s+')');}};
}
function SG_keys(p,rows,hold){
    var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;
    for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
    for(var k=1;k<=p.numKeys;k++){
        if(hold){p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);continue;}
        var n=spatial||p.propertyValueType===PropertyValueType.COLOR?1:(p.value instanceof Array?p.value.length:1),e=[];
        for(var j=0;j<n;j++)e.push(new KeyframeEase(0,55));
        p.setTemporalEaseAtKey(k,e,e);p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
        if(spatial){var z=[];for(j=0;j<p.value.length;j++)z.push(0);p.setSpatialAutoBezierAtKey(k,false);p.setSpatialContinuousAtKey(k,false);p.setSpatialTangentsAtKey(k,z,z);}
    }
}
function SG_cameraKeys(p,rows,carry){
    SG_keys(p,rows,false);
    for(var k=2;k<p.numKeys;k++){
        var use=false;for(var i=0;i<carry.length;i++)if(carry[i]===k-1)use=true;if(!use)continue;
        var a=p.keyValue(k-1),b=p.keyValue(k),c=p.keyValue(k+1),da=0,db=0;
        for(var j=0;j<a.length;j++){da+=Math.pow(b[j]-a[j],2);db+=Math.pow(c[j]-b[j],2);}
        var speed=.65*Math.min(Math.sqrt(da)/(p.keyTime(k)-p.keyTime(k-1)),Math.sqrt(db)/(p.keyTime(k+1)-p.keyTime(k)));
        p.setTemporalEaseAtKey(k,[new KeyframeEase(speed,22)],[new KeyframeEase(speed,22)]);
    }
}
function SG_locate(fill,at,frames,fps){
    // Left-anchored shape; scaling X wipes its fill, not an underline.
    SG_keys(fill.transform.scale,[[at,[0,100,100]],[at+frames/fps,[100,100,100]]],false);
}
function SG_lift(original,target,at,config){
    var l=original.duplicate(),origin;
    // Caller supplies native measured world coordinates, never guessed text coordinates.
    origin=config.origin;l.parent=null;l.name=config.name;
    var anim=l.property('ADBE Text Properties').property('ADBE Text Animators');
    while(anim.numProperties)anim.property(1).remove();
    l.transform.opacity.expression='';while(l.transform.opacity.numKeys)l.transform.opacity.removeKey(1);
    l.transform.position.expression='';while(l.transform.position.numKeys)l.transform.position.removeKey(1);
    l.transform.scale.expression='';while(l.transform.scale.numKeys)l.transform.scale.removeKey(1);
    l.inPoint=at;l.outPoint=config.returnAt+config.returnFrames/config.fps+1/config.fps;
    SG_keys(l.transform.position,[[at,origin],[at+config.frames/config.fps,target]],false);
    SG_keys(l.transform.scale,[[at,[100,100,100]],[at+config.frames/config.fps,[config.scale,config.scale,config.scale]]],false);
    l.transform.opacity.setValue(100);
    l.comment=JSON.stringify({kind:'native_origin_projection',origin_layer_id:original.id,origin:origin,source:config.source});
    return {layer:l,origin:origin,target:target,scale:config.scale};
}
function SG_compare(projection,target,at,frames,fps){
    var l=projection.layer;SG_keys(l.transform.position,[[at,l.transform.position.valueAtTime(at,false)],[at+frames/fps,target]],false);
}
function SG_eliminate(layers,at,frames,fps){
    for(var i=0;i<layers.length;i++){
        var l=layers[i],p=l.transform.position.valueAtTime(at,true);
        SG_keys(l.transform.position,[[at,p],[at+frames/fps,[p[0],p[1]+48,p[2]]]],false);
        SG_keys(l.transform.opacity,[[at,100],[at+frames/fps,20]],false);
    }
}
function SG_return(projection,at,frames,fps){
    // Reversed lift path, ending at the exact glyph origin and original scale.
    var l=projection.layer;SG_keys(l.transform.position,[[at,projection.target],[at+frames/fps,projection.origin]],false);
    SG_keys(l.transform.scale,[[at,[projection.scale,projection.scale,projection.scale]],[at+frames/fps,[100,100,100]]],false);
}
