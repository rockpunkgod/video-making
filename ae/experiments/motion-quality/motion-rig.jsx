// Opt-in native curves for the single bound Motion Quality experiment.
// Positions use AE's editable Speed Graph; no frame baking or global easing.
function mqKeyed(property, rows, rig, name) {
    if (property.canSetExpression) property.expression='';
    while(property.numKeys)property.removeKey(property.numKeys);
    var spatial=property.propertyValueType===PropertyValueType.ThreeD_SPATIAL||property.propertyValueType===PropertyValueType.TwoD_SPATIAL;
    for(var i=0;i<rows.length;i++)property.setValueAtTime(rows[i].t,rows[i].v);
    for(var i=0;i<rows.length;i++){
        var r=rows[i],dims=spatial?1:(r.v instanceof Array?r.v.length:1),ins=[],outs=[];
        for(var j=0;j<dims;j++){ins.push(new KeyframeEase(r.speed||0,r.influenceIn||33));outs.push(new KeyframeEase(r.speed||0,r.influenceOut||33));}
        var k=i+1;property.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
        property.setTemporalEaseAtKey(k,ins,outs);
        if(spatial){
            property.setSpatialAutoBezierAtKey(k,false);
            var incoming=[0,0,0],outgoing=[0,0,0];
            if(r.speed&&i>0&&i<rows.length-1){
                var prev=rows[i-1].v,next=rows[i+1].v,dir=[],n=0,a=0,b=0;
                for(var j=0;j<r.v.length;j++){dir[j]=next[j]-prev[j];n+=dir[j]*dir[j];a+=Math.pow(r.v[j]-prev[j],2);b+=Math.pow(next[j]-r.v[j],2);}
                n=Math.sqrt(n);var reach=Math.min(Math.sqrt(a),Math.sqrt(b))/3;
                if(n>0)for(var j=0;j<r.v.length;j++){incoming[j]=-dir[j]/n*reach;outgoing[j]=dir[j]/n*reach;}
                property.setTemporalContinuousAtKey(k,true);
            }
            property.setSpatialTangentsAtKey(k,incoming,outgoing);
        }
    }
    rig.native_curves.push({name:name,property:property.matchName,keys:rows});
}
function mqRow(t,v,speed,inside,outside,phase){return {t:t,v:v,speed:speed||0,influenceIn:inside||33,influenceOut:outside||33,phase:phase};}
function mqBasis(camera,t){
    function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
    function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
    function norm(a){var n=Math.sqrt(dot(a,a));return [a[0]/n,a[1]/n,a[2]/n];}
    function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
    var c=camera.transform.position.valueAtTime(t,false),f=norm(sub(camera.transform.pointOfInterest.valueAtTime(t,false),c)),r=norm(cross([0,1,0],f));
    return {c:c,f:f,r:r,u:cross(f,r),zoom:camera.cameraOption.zoom.value};
}
function mqProject(world,camera,t){var b=mqBasis(camera,t),v=[world[0]-b.c[0],world[1]-b.c[1],world[2]-b.c[2]];function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}var d=dot(v,b.f);return [1920+dot(v,b.r)*b.zoom/d,1080+dot(v,b.u)*b.zoom/d,d];}
function mqScreenExpression(controller){return 'var cam=thisComp.layer("READING_CAMERA"),q=thisComp.layer("'+controller+'").transform.position,c=cam.toWorld([0,0,0]),f=normalize(sub(cam.transform.pointOfInterest,c)),r=normalize(cross([0,1,0],f)),u=cross(f,r),z=cam.cameraOption.zoom,d=q[2];c+f*d+r*((q[0]-thisComp.width/2)*d/z)+u*((q[1]-thisComp.height/2)*d/z);';}
function mqPreserveAccent(layer,phrase,time,rig){
    var d=layer.property('Source Text').valueAtTime(time,false),at=d.text.indexOf(phrase);
    if(at<0||d.text.indexOf(phrase,at+1)>=0)throw Error('Unambiguous existing accent required');
    var color=d.characterRange(at,at+1).fillColor;
    var an=layer.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');an.name='MQ_PRESERVE_EXISTING_ACCENT';
    var sel=an.property('ADBE Text Selectors').addProperty('ADBE Text Selector'),adv=sel.property('ADBE Text Range Advanced');adv.property('ADBE Text Range Units').setValue(2);sel.property('ADBE Text Index Start').setValue(at);sel.property('ADBE Text Index End').setValue(at+phrase.length);adv.property('ADBE Text Selector Smoothness').setValue(0);adv.property('ADBE Text Selector Max Amount').expression='time>='+time+'?100:0;';
    an.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(color);
    if(!rig.preserved_accents)rig.preserved_accents=[];rig.preserved_accents.push({layer:layer.name,phrase:phrase,start:at,end:at+phrase.length,time:time,color:color,reason:'preserve existing source-text emphasis through the animated renderer'});
}
