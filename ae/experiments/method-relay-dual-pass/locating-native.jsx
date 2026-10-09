// Guided-only adapter. Run on a copy of the matching existing fulltext project.
(function(){
    var f=new File(LOCATING_PATCH_PATH);f.encoding='UTF-8';f.open('r');var P=JSON.parse(f.read());f.close();
    var dest=new File(LOCATING_DESTINATION);if(dest.exists)throw Error('Fresh project required');
    var cp=null;for(var i=1;i<=app.project.numItems;i++){
        var item=app.project.item(i);if(item instanceof CompItem&&item.name==='FULLTEXT_SOURCE_ACQUISITION')cp=item;}
    if(!cp||cp.width!==3840||cp.height!==2160||Math.abs(cp.frameRate-24)>.0001)throw Error('Native 4K base required');
    var binding=JSON.parse(cp.comment);if(binding.spec_sha!==P.base_spec_sha)throw Error('Base request mismatch');
    var source=[];
    for(var i=0;i<P.geometry.words.length;i++){
        var w=P.geometry.words[i],l=cp.layer(w.id),r=l.sourceRectAtTime(0,false),pos=l.transform.position.valueAtTime(0,false),s=l.transform.scale.valueAtTime(0,false);
        if(l.id!==w.layer_id||l.property('Source Text').value.text!==w.text)throw Error('Original identity changed');
        var min=[pos[0]+r.left*s[0]/100,pos[1]+r.top*s[1]/100,pos[2]];
        for(var a=0;a<3;a++)if(Math.abs(min[a]-w.min[a])>.05)throw Error('Native glyph geometry changed');
        source.push({id:w.id,layer_id:l.id});
    }
    var focus=cp.layer('FOCUS_TARGET'),camera=cp.layer('GUIDED_CAMERA'),start=P.frame_range[0]/24,end=P.frame_range[1]/24;
    function pathExpression(rows){return 'function tracePath(t){var R='+JSON.stringify(rows)+';var frame=t*24;for(var i=1;i<R.length;i++){var a=R[i-1],b=R[i];if(frame<=b.frame){var d=b.frame-a.frame,u=Math.max(0,(frame-a.frame)/d),u3=u*u*u,u4=u3*u,u5=u4*u,q=6*u5-15*u4+10*u3,h0=u-6*u3+8*u4-3*u5,h1=-4*u3+7*u4-3*u5;return a.center*(1-q)+b.center*q+a.velocity*(d*h0)+b.velocity*(d*h1);}}return R[R.length-1].center;}';}
    function wrap(prop,body){var old=(prop.expression||'value').replace(/;\s*$/,'');prop.expression='(function(){if(time<'+start+'||time>'+end+')return ('+old+');'+pathExpression(P.rows)+body+'})();';}
    wrap(focus.transform.position,'return tracePath(time);');
    var column=camera.transform.pointOfInterest.valueAtTime(start,true)[0],S=P.render_scale;
    wrap(camera.transform.pointOfInterest,'var p=tracePath(time);return ['+column+',p[1]+'+(P.camera_style.reading_offset*S)+',0];');
    wrap(camera.transform.position,'var p=tracePath(time);return ['+(column+20*S)+',p[1]+'+((P.camera_style.reading_offset+P.camera_style.camera_tilt_offset)*S)+','+(P.camera_style.scan_depth*S)+'];');
    var marks=[];
    for(var i=0;i<P.plan.targets.length;i++){
        var target=P.plan.targets[i],e=P.plan.clock.events[i],l=cp.layers.addShape();l.name='LOCATING_TRANSIENT_'+target.candidate_id;l.threeDLayer=true;
        var group=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group'),contents=group.property('ADBE Vectors Group');
        contents.addProperty('ADBE Vector Shape - Rect');contents=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        contents.addProperty('ADBE Vector Graphic - Fill');contents=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        contents.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([target.max[0]-target.min[0]+8*S,target.max[1]-target.min[1]+8*S]);
        contents.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue([.87,.90,.88]);
        l.transform.position.setValue([target.center[0],target.center[1],S]);
        var retire=e.retirement||[e.recognition[1],e.recognition[1]+3];
        l.transform.opacity.expression='var a='+e.activation[0]+'/24,b='+e.activation[1]+'/24,c='+retire[0]+'/24,d='+retire[1]+'/24;function q(u){return u*u*u*(10+u*(-15+6*u));}time<a||time>d?0:(time<b?85*q((time-a)/(b-a)):(time<c?85:85*(1-q((time-c)/(d-c)))));';
        marks.push({candidate_id:target.candidate_id,layer_id:l.id});
    }
    // Prevent the old Guided cue from announcing an unsupplied acquisition.
    var oldMark=cp.layer('ACQUIRED_WORDS'),oldExpression=(oldMark.transform.opacity.expression||'value').replace(/;\s*$/,'');
    oldMark.transform.opacity.expression='time>='+start+'?0:('+oldExpression+');';
    if(!P.plan.handoff)cp.duration=end; // no legacy lock/lift after unresolved scan
    var errors=[];for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.name.indexOf('LOCATING_TRANSIENT_')===0&&l.transform.opacity.expressionError)errors.push(l.transform.opacity.expressionError);}
    for(var i=0;i<3;i++){var prop=i===0?focus.transform.position:(i===1?camera.transform.position:camera.transform.pointOfInterest);if(prop.expressionError)errors.push(prop.expressionError);}
    if(errors.length)throw Error(JSON.stringify(errors));
    app.project.save(dest);
    return JSON.stringify({patch_sha:P.patch_sha,comp_id:cp.id,canvas:[cp.width,cp.height,cp.frameRate],
        source_objects:source,marks:marks,expression_errors:errors,native_execution:'PATCH_EXECUTED_NOT_RENDER_REVIEW',public_render_ready:false});
})();
