// Same frozen scene, separate diagnostic comps. Not a production renderer.
(function(){
    var src=AEMCP.compById(NCP_COMP),binding=JSON.parse(src.comment),ids={};
    if(binding.kind!=='synthetic_ae_visual_research'||binding.production_eligible!==false)
        throw new Error('Explicit isolated synthetic scene required');
    function freeze(p,time){var v=p.valueAtTime(time,false);while(p.numKeys)p.removeKey(1);p.expression='';p.setValue(v);}
    function flat(p){var rows=[];for(var k=1;k<=p.numKeys;k++){var v=p.keyValue(k);v[2]=0;rows.push([p.keyTime(k),v]);}
        if(!rows.length){var v=p.value;v[2]=0;p.setValue(v);}else for(var k=0;k<rows.length;k++)p.setValueAtTime(rows[k][0],rows[k][1]);}
    function clone(label){var c=src.duplicate();c.name=src.name+'_'+label;var b=JSON.parse(src.comment);b.variant=label;c.comment=JSON.stringify(b);ids[label]=c.id;return c;}
    var a=clone('A'),cam=a.layer('GUIDED_CAMERA');
    freeze(cam.transform.position,0);freeze(cam.transform.pointOfInterest,0);
    cam.property('ADBE Camera Options Group').property('ADBE Camera Depth of Field').setValue(0);
    for(var i=1;i<=a.numLayers;i++){
        var l=a.layer(i);if(!l.threeDLayer||l instanceof CameraLayer)continue;
        flat(l.transform.position);freeze(l.transform.yRotation,0);freeze(l.transform.zRotation,0);
        if(l.name.indexOf('CARRIER_')===0) {freeze(l.transform.opacity,0);l.transform.opacity.setValue(0);}
    }
    var c=clone('C_FIXED_CAMERA');cam=c.layer('GUIDED_CAMERA');
    freeze(cam.transform.position,0);freeze(cam.transform.pointOfInterest,0);
    // Geometry, parenting, focus target and DOF remain unchanged: camera transform only.
    var d=clone('D_RESTORE');
    // Capture expression-driven attachment travel before reversing its anchors.
    // Otherwise a forward-time follow expression would undo the restoration.
    var baked={};
    if(binding.presentation_id==='SYNTHETIC-ATTACHMENT-LAYOUT-R5'||binding.presentation_id==='SYNTHETIC-ATTACHMENT-LAYOUT-R5-FAST'){
        for(var i=1;i<=d.numLayers;i++){
            var l=d.layer(i),p=l.transform.position;
            if(l.name.indexOf('HINGE_')!==0||!p.expressionEnabled)continue;
            var rows=[];
            for(var j=0;j<=Math.round(src.duration*src.frameRate);j++){
                var tm=j/src.frameRate;rows.push([6*(src.duration-tm)/src.duration,p.valueAtTime(tm,false)]);
            }
            baked[l.name]=rows;
        }
    }
    function reverse(p){var rows=[];for(var k=1;k<=p.numKeys;k++)rows.push([6*(src.duration-p.keyTime(k))/src.duration,p.keyValue(k)]);
        if(!rows.length)return;while(p.numKeys)p.removeKey(1);
        for(var k=rows.length-1;k>=0;k--)p.setValueAtTime(rows[k][0],rows[k][1]);}
    for(var i=1;i<=d.numLayers;i++){
        var l=d.layer(i),t=l.transform;
        if(baked[l.name]){
            var p=t.position,rows=baked[l.name];p.expression='';while(p.numKeys)p.removeKey(1);
            for(var k=rows.length-1;k>=0;k--)p.setValueAtTime(rows[k][0],rows[k][1]);
        }else reverse(t.position);
        reverse(t.opacity);reverse(t.scale);
        if(l.threeDLayer){reverse(t.yRotation);reverse(t.zRotation);}
        if(l instanceof CameraLayer)reverse(t.pointOfInterest);
    }
    // This diagnostic reverses the keyframed rig, not the forward-time focus
    // expression. Its keyed focus returns to the original plane with the objects.
    d.layer('FOCUS_TARGET').transform.position.expression='';
    var restored=[];
    for(var i=1;i<=d.numLayers;i++){
        var l=d.layer(i);if(!(l instanceof TextLayer)||!l.comment)continue;
        var o=JSON.parse(l.comment),p=l.parent?l.parent.transform.position.valueAtTime(7,false):l.transform.position.valueAtTime(7,false);
        restored.push({object_id:o.object_id,layer_id:l.id,text:l.property('Source Text').value.text,
            position:p,parent:l.parent?l.parent.name:null,y_rotation:l.parent?l.parent.transform.yRotation.valueAtTime(7,false):0});
    }
    src.openInViewer();app.project.save();
    return JSON.stringify({comp_ids:ids,restore_at:7,restored:restored});
})();
