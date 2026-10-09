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
    if(P.entry_state){var props=[focus.transform.position,camera.transform.position,camera.transform.pointOfInterest],expected=[P.entry_state.focus,P.entry_state.camera,P.entry_state.look];
        for(var i=0;i<3;i++){var actual=props[i].valueAtTime(start,false);for(var a=0;a<3;a++)if(Math.abs(actual[a]-expected[i][a])>.001)throw Error('Native entry state changed');}}
    app.project.save(dest); // all subsequent writes belong to a fresh project
    function pathExpression(rows){return 'function tracePath(t){var R='+JSON.stringify(rows)+';var frame=t*24;for(var i=1;i<R.length;i++){var a=R[i-1],b=R[i];if(frame<=b.frame){var d=b.frame-a.frame,u=Math.max(0,(frame-a.frame)/d),u3=u*u*u,u4=u3*u,u5=u4*u,q=6*u5-15*u4+10*u3,h0=u-6*u3+8*u4-3*u5,h1=-4*u3+7*u4-3*u5;return a.center*(1-q)+b.center*q+a.velocity*(d*h0)+b.velocity*(d*h1);}}return R[R.length-1].center;}';}
    function wrap(prop,body,begin,rows){var old=(prop.expression||'value').replace(/;\s*$/,'');prop.expression='(function(){if(time<'+(begin===undefined?start:begin)+'||time>'+end+')return ('+old+');'+pathExpression(rows||P.rows)+body+'})();';}
    var focusBody='return tracePath(time);',focusBegin=start;
    if(P.focus_entry){var E=P.focus_entry;focusBegin=E.frames[0]/24;
        var actual=focus.transform.position.valueAtTime(focusBegin,false);for(var a=0;a<3;a++)if(Math.abs(actual[a]-E.from[a])>.001)throw Error('Focus entry origin changed');
        focusBody='if(time<'+start+'){var u=(time-'+focusBegin+')/('+start+'-'+focusBegin+'),q=u*u*u*(10+u*(-15+6*u));var a='+JSON.stringify(E.from)+',b='+JSON.stringify(E.to)+';return a*(1-q)+b*q;}'+focusBody;}
    wrap(focus.transform.position,focusBody,focusBegin);
    var column=camera.transform.pointOfInterest.valueAtTime(start,true)[0],S=P.render_scale;
    var lookOffset=P.entry_state?P.entry_state.look[1]-P.rows[0].center[1]:P.camera_style.reading_offset*S;
    var cameraOffset=P.entry_state?P.entry_state.camera[1]-P.rows[0].center[1]:(P.camera_style.reading_offset+P.camera_style.camera_tilt_offset)*S;
    wrap(camera.transform.pointOfInterest,'var p=tracePath(time);return ['+column+',p[1]+'+lookOffset+',0];',start,P.camera_rows);
    wrap(camera.transform.position,'var p=tracePath(time);return ['+(column+20*S)+',p[1]+'+cameraOffset+','+(P.camera_style.scan_depth*S)+'];',start,P.camera_rows);
    // Rebind the existing low-gain baseline-locked envelopes to the same clock.
    var attentionGroups=P.attention_groups||[];
    for(var gi=0;gi<attentionGroups.length;gi++){
        var group=attentionGroups[gi];for(var wi=0;wi<group.ids.length;wi++){
            var l=cp.layer(group.ids[wi]),props=[l.transform.scale,l.transform.position];
            for(var pi=0;pi<props.length;pi++)if(props[pi].expression){
                var old=props[pi].expression;if(old.indexOf('var W=')!==0)throw Error('Unsupported legacy attention expression');
                props[pi].expression=old.replace(/^var W=(\[[\s\S]*?\]);function smooth/,
                    function(match,original){return 'var W=time<'+start+'?'+original+':'+JSON.stringify(group.windows)+';function smooth';});
            }
        }
    }
    var marks=[];
    var palette=P.plan.highlight_palette;
    if(palette){var questionFill=cp.layer('QUESTION_TARGET').property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color');
        var oldColor=(questionFill.expression||'value').replace(/;\s*$/,'');
        questionFill.expression='time>='+((P.fast_end_frame+24)/24)+'?'+JSON.stringify(palette.question.concat([1]))+':('+oldColor+');';}
    for(var i=0;i<P.plan.targets.length;i++){
        var target=P.plan.targets[i],e=P.plan.clock.events[i],l=cp.layers.addShape();l.name='LOCATING_TRANSIENT_'+target.candidate_id;l.threeDLayer=true;
        var group=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group'),contents=group.property('ADBE Vectors Group');
        contents.addProperty('ADBE Vector Shape - Rect');contents=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        contents.addProperty('ADBE Vector Graphic - Fill');contents=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        contents.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([target.max[0]-target.min[0]+8*S,target.max[1]-target.min[1]+8*S]);
        var fill=contents.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color');
        fill.setValue(palette?palette.comparison:[.87,.90,.88]);
        if(palette&&target.recognition_state==='acquired')fill.expression='time<'+e.recognition[1]+'/24?'+JSON.stringify(palette.comparison.concat([1]))+':'+JSON.stringify(palette.acquired.concat([1]))+';';
        fill.valueAtTime(e.recognition[1]/24,false);
        if(fill.expressionError)throw Error(fill.expressionError);
        // Keep fills inside the original words' 3D stacking group, behind ink.
        // A new top layer can be separated by 2D overlays and defeat Z sorting.
        var back=cp.layer(P.geometry.words[0].id);
        for(var wi=1;wi<P.geometry.words.length;wi++){var word=cp.layer(P.geometry.words[wi].id);if(word.index>back.index)back=word;}
        l.moveAfter(back);
        l.transform.position.setValue([target.center[0],target.center[1],4*S]);
        var retire=e.retirement||[e.recognition[1]+6,e.recognition[1]+9];
        l.transform.opacity.expression='var a='+e.activation[0]+'/24,b='+e.activation[1]+'/24,c='+retire[0]+'/24,d='+retire[1]+'/24;function q(u){return u*u*u*(10+u*(-15+6*u));}time<a||time>d?0:(time<b?85*q((time-a)/(b-a)):(time<c?85:85*(1-q((time-c)/(d-c)))));';
        marks.push({candidate_id:target.candidate_id,layer_id:l.id});
    }
    // Prevent the old Guided cue from announcing an unsupplied acquisition.
    var oldMark=cp.layer('ACQUIRED_WORDS'),oldExpression=(oldMark.transform.opacity.expression||'value').replace(/;\s*$/,'');
    oldMark.transform.opacity.expression='time>='+start+'?0:('+oldExpression+');';
    if(!P.plan.handoff)cp.duration=end; // no legacy lock/lift after unresolved scan
    if(palette){questionFill.valueAtTime(start,false);if(questionFill.expressionError)throw Error(questionFill.expressionError);}
    var errors=[];for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.name.indexOf('LOCATING_TRANSIENT_')===0&&l.transform.opacity.expressionError)errors.push(l.transform.opacity.expressionError);}
    for(var i=0;i<3;i++){var prop=i===0?focus.transform.position:(i===1?camera.transform.position:camera.transform.pointOfInterest);if(prop.expressionError)errors.push(prop.expressionError);}
    if(errors.length)throw Error(JSON.stringify(errors));
    binding.locating_patch_sha=P.patch_sha;binding.locating_patch_file=f.fsName;cp.comment=JSON.stringify(binding);
    app.project.save(dest);
    return JSON.stringify({patch_sha:P.patch_sha,comp_id:cp.id,canvas:[cp.width,cp.height,cp.frameRate],
        source_objects:source,marks:marks,expression_errors:errors,native_execution:'PATCH_EXECUTED_NOT_RENDER_REVIEW',public_render_ready:false});
})();
