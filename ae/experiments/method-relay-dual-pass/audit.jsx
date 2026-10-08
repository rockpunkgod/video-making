// Actual native source identity and object carry, not a semantic truth certificate.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';f.open('r');var s=f.read();f.close();return JSON.parse(s);}
    var R=load(RELAY_REQUEST),cp=AEMCP.compById(RELAY_COMP),binding=JSON.parse(cp.comment),ids=[],objects=[],handles={},passes=[],names={},visibleIds=[];
    for(var i=0;i<R.layout.length;i++)ids.push(R.layout[i].id);
    for(var i=0;i<R.options.length;i++)for(var j=0;j<R.options[i].pieces.length;j++)ids.push(R.options[i].pieces[j].id);
    for(var i=0;i<ids.length;i++){
        var l=cp.layer(ids[i]),meta=JSON.parse(l.comment),d=l.property('Source Text').value;
        objects.push({id:meta.object_id,native_layer_id:l.id,text:d.text,font:d.font,font_size:d.fontSize,threeD:l.threeDLayer,source_text_keys:l.property('Source Text').numKeys,origin_sha:meta.origin_sha,start:meta.start,end:meta.end,parent:l.parent?l.parent.name:null});
        handles[ids[i]]=l.id;
    }
    for(var i=1;i<=cp.numLayers;i++){
        var l=cp.layer(i);if(l.property('Source Text')){
            var t=l.property('Source Text').value.text;if(/\b[RGFC]\d{2}\b/.test(t))visibleIds.push(t);
        }
    }
    for(var i=0;i<R.method_names.length;i++){
        var m=R.method_names[i],count=0;
        for(var j=1;j<=cp.numLayers;j++){var l=cp.layer(j);if(l.property('Source Text')&&l.property('Source Text').value.text===m.name)count++;}
        names[m.method_id]=count;
    }
    for(var i=0;i<R.passes.length;i++){
        var p=R.passes[i],state={kind:p.kind,handles:handles,checks:[],retained_opacities:[],column_alignment:[],option_rows:[],peels:[],camera:[]};
        var checkpoints=[p.locate[1],p.lift[1],p.peel_a[4],p.peel_b[4],p.align[1],p.compare[1],p.verify[1]];
        for(var j=0;j<checkpoints.length;j++){
            var t=checkpoints[j];state.checks.push({time:t,core_opacity:cp.layer('core-subject').transform.opacity.valueAtTime(t,false)});
            state.camera.push({time:t,position:cp.layer('GUIDED_CAMERA').transform.position.valueAtTime(t,false),look:cp.layer('GUIDED_CAMERA').transform.pointOfInterest.valueAtTime(t,false)});
            var c=['core-subject','core-verb','core-object'];for(var k=0;k<c.length;k++)state.retained_opacities.push({id:c[k],time:t,value:cp.layer(c[k]).transform.opacity.valueAtTime(t,false)});
        }
        for(var j=0;j<R.options.length;j++)for(var k=0;k<R.options[j].pieces.length;k++){
            var part=R.options[j].pieces[k],s=cp.layer('core-'+part.part),o=cp.layer(part.id),t=p.align[1]+.05;
            var sp=s.transform.position.valueAtTime(t,false),op=o.transform.position.valueAtTime(t,false);
            var sr=s.parent.transform.position.valueAtTime(t,false),orr=o.parent.transform.position.valueAtTime(t,false);
            state.column_alignment.push({id:part.id,dx:op[0]+orr[0]-sp[0]-sr[0]});
        }
        for(var j=0;j<R.options.length;j++)state.option_rows.push({id:R.options[j].id,y:cp.layer('option-'+R.options[j].id+'-subject').transform.position.valueAtTime(p.align[1]+.05,false)[1]});
        var fragments=['aside-time','aside-map'];
        for(var j=0;j<fragments.length;j++){
            var h=cp.layer('HINGE_'+fragments[j]),q=j===0?p.peel_a:p.peel_b,onset=null,release=null;
            var rot=h.transform.yRotation;
            for(var k=1;k<=rot.numKeys;k++)if(Math.abs(rot.keyTime(k)-q[2])<.001)onset=rot.keyTime(k);else if(Math.abs(rot.keyTime(k)-q[3])<.001)release=rot.keyTime(k);
            state.peels.push({id:fragments[j],onset:onset,release:release,detach_seconds:release-onset,position_at_land:h.transform.position.valueAtTime(q[4],false),rotation_at_land:rot.valueAtTime(q[4],false),original_text:cp.layer(fragments[j]).property('Source Text').value.text});
        }
        passes.push(state);
    }
    var restored=[];
    if(R.rewind){
        var restoreNames=ids.concat(['EVIDENCE_PLANE','HINGE_aside-time','HINGE_aside-map','GUIDED_CAMERA']);
        for(var i=0;i<R.options.length;i++)restoreNames.push('OPTION_PLANE_'+R.options[i].id);
        for(var i=0;i<restoreNames.length;i++){
            var l=cp.layer(restoreNames[i]),props=['ADBE Position','ADBE Scale','ADBE Opacity'];
            if(l.threeDLayer)props.push('ADBE Rotate Y');
            for(var j=0;j<props.length;j++){
                var p=l.property('ADBE Transform Group').property(props[j]);
                if(p)restored.push({name:l.name,property:props[j],initial:p.valueAtTime(0,false),restored:p.valueAtTime(R.rewind[1],false)});
            }
        }
    }
    var task=cp.layer('ORIGINAL_QUESTION'),question={native_layer_id:task.id,text:task.property('Source Text').value.text,source_text_keys:task.property('Source Text').numKeys};
    var guidance=null;
    if(R.phase==='full'&&R.fixture.guided_method_copy){
        var g=R.fixture.guided_method_copy,fast=null,guided=null;
        for(var i=0;i<R.passes.length;i++){if(R.passes[i].kind==='fast')fast=R.passes[i];if(R.passes[i].kind==='guided')guided=R.passes[i];}
        guidance={column_labels:[],subject_emphasis:[]};
        for(var i=0;i<g.column_labels.length;i++){
            var l=cp.layer('GUIDED_COLUMN_'+g.column_labels[i].part),d=l.property('Source Text').value;
            guidance.column_labels.push({text:d.text,font:d.font,source_text_keys:l.property('Source Text').numKeys,
                native_layer_id:l.id,x:l.transform.position.value[0],fast_opacity:l.transform.opacity.valueAtTime(fast.align[1],false),
                guided_opacity:l.transform.opacity.valueAtTime(guided.align[1],false)});
        }
        var mark=cp.layer('DIFFERENCE_'+g.emphasis.object_id),w=g.emphasis.window,times=[w[0]+.25,(w[0]+w[1])/2,w[1]-.25];
        for(var i=0;i<times.length;i++)guidance.subject_emphasis.push({time:times[i],opacity:mark.transform.opacity.valueAtTime(times[i],false)});
    }
    return JSON.stringify({spec_sha:binding.spec_sha,trajectory_sha:binding.trajectory_sha,canvas:[cp.width,cp.height,cp.frameRate,cp.duration],question:question,objects:objects,passes:passes,rewind_restore:restored,name_counts:names,visible_internal_method_ids:visibleIds,renderer:cp.renderer,method_guidance:guidance,production_eligible:binding.production_eligible,public_render_ready:binding.public_render_ready});
})();
