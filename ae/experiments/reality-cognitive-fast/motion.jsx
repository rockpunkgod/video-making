// Motion-only adaptation of native-creative-proof/build.jsx and
// method-relay-dual-pass/fulltext-build.jsx. No synthetic semantic authority.
function RCF_keys(p,rows,hold){
    var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;
    for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
    for(var k=1;k<=p.numKeys;k++){
        if(hold){p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);continue;}
        var n=spatial||p.propertyValueType===PropertyValueType.COLOR?1:(p.value instanceof Array?p.value.length:1),e=[];
        for(var j=0;j<n;j++)e.push(new KeyframeEase(0,55));
        p.setTemporalEaseAtKey(k,e,e);
        p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
        if(spatial){var z=[];for(var j=0;j<p.value.length;j++)z.push(0);
            p.setSpatialAutoBezierAtKey(k,false);p.setSpatialContinuousAtKey(k,false);p.setSpatialTangentsAtKey(k,z,z);}
    }
}
function RCF_cameraKeys(p,rows,carry){
    RCF_keys(p,rows,false);
    for(var k=2;k<p.numKeys;k++){
        var use=false;for(var ci=0;ci<carry.length;ci++)if(carry[ci]===k-1)use=true;if(!use)continue;
        var a=p.keyValue(k-1),b=p.keyValue(k),c=p.keyValue(k+1),da=0,db=0;
        for(var j=0;j<a.length;j++){da+=Math.pow(b[j]-a[j],2);db+=Math.pow(c[j]-b[j],2);}
        var speed=.65*Math.min(Math.sqrt(da)/(p.keyTime(k)-p.keyTime(k-1)),Math.sqrt(db)/(p.keyTime(k+1)-p.keyTime(k)));
        p.setTemporalEaseAtKey(k,[new KeyframeEase(speed,22)],[new KeyframeEase(speed,22)]);
    }
}
