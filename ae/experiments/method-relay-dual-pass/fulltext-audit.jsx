(function(){
    var cp=AEMCP.compById(FULLTEXT_COMP),binding=JSON.parse(cp.comment),file=new File(binding.data_file);file.encoding='UTF-8';file.open('r');var b=JSON.parse(file.read());file.close();
    if(b.spec_sha!==binding.spec_sha)throw new Error('Native geometry sidecar binding differs');
    var words=[],handles={},passes=[],probes=[],annotations=[],questionParts=[],questionHandles={},optionTexts={},guards={};
    for(var i=1;i<=cp.numLayers;i++){
        var l=cp.layer(i);if(l.name==='TEMP_GEOMETRY_PROBE')probes.push(l.id);
        if(l.name.indexOf('SCOPE_')===0||l.name==='SERIES'||l.name==='P0_BADGE')annotations.push(l.name);
        if(l.name==='PAPER_TOP_GUARD'||l.name==='PAPER_FOOT_GUARD'){
            var masks=l.property('ADBE Mask Parade'),mask=masks.property(1),shape=mask.property('ADBE Mask Shape'),feather=mask.property('ADBE Mask Feather');
            guards[l.name]={vertices:shape.value.vertices,feather:feather.value,mask_keys:shape.numKeys,feather_keys:feather.numKeys,
                mask_count:masks.numProperties,mask_add:mask.maskMode===MaskMode.ADD,inverted:mask.inverted,
                mask_opacity:mask.property('ADBE Mask Opacity').value,layer_opacity:l.transform.opacity.value,enabled:l.enabled,
                threeD:l.threeDLayer,parent:l.parent?l.parent.id:null,rotation:l.property('ADBE Transform Group').property('ADBE Rotate Z').value,
                position:l.transform.position.value,anchor:l.transform.anchorPoint.value,scale:l.transform.scale.value,
                size:[l.source.width,l.source.height],color:l.source.mainSource.color};}
        if(l.name==='QUESTION_PREFIX'||l.name==='QUESTION_KEYWORD'||l.name==='QUESTION_SUFFIX'){
            var m=JSON.parse(l.comment);questionParts.push({id:m.id,text:l.property('Source Text').value.text,start:m.start,end:m.end,text_sha:m.text_sha,
                source_text_keys:l.property('Source Text').numKeys,position:l.transform.position.value,scale:l.transform.scale.value,
                font_size:l.property('Source Text').value.fontSize});questionHandles[m.id]=l.id;}
        if(l.name.indexOf('ORIGINAL_OPTION_')===0)optionTexts[l.name.replace('ORIGINAL_OPTION_','')]=l.property('Source Text').value.text;
        if(l.name.indexOf('source-word-')===0){var d=l.property('Source Text').value,m=JSON.parse(l.comment);
            words.push({id:m.id,layer_id:l.id,text:d.text,start:m.start,end:m.end,text_sha:m.text_sha,source_sha:m.source_sha,
                source_text_keys:l.property('Source Text').numKeys,font_size:d.fontSize,threeD:l.threeDLayer,rect:l.sourceRectAtTime(0,false),
                position:l.transform.position.valueAtTime(0,false),anchor:l.transform.anchorPoint.value,scale:l.transform.scale.valueAtTime(0,false),
                parent:l.parent?l.parent.id:null,rotation:l.property('ADBE Transform Group').property('ADBE Rotate Z').value,
                x_rotation:l.property('ADBE Transform Group').property('ADBE Rotate X').value,y_rotation:l.property('ADBE Transform Group').property('ADBE Rotate Y').value});handles[m.id]=l.id;}
    }
    for(var i=0;i<b.director.passes.length;i++){
        var p=b.director.passes[i],visit=b.scan_visits[i],visited=[],samples=[],opt=cp.layer('GUIDED_CAMERA').property('ADBE Camera Options Group');
        for(var j=0;j<visit.lines.length;j++){
            visited.push(visit.lines[j].line_id);var t=(visit.lines[j].start+visit.lines[j].end)/2;
            samples.push({time:t,reader:cp.layer('READING_GUIDE').transform.position.valueAtTime(t,false),
                camera:cp.layer('GUIDED_CAMERA').transform.position.valueAtTime(t,false),look:cp.layer('GUIDED_CAMERA').transform.pointOfInterest.valueAtTime(t,false),
                focus:cp.layer('FOCUS_TARGET').transform.position.valueAtTime(t,false),
                focus_distance:opt.property('ADBE Camera Focus Distance').valueAtTime(t,false),aperture:opt.property('ADBE Camera Aperture').valueAtTime(t,false),
                reader_opacity:cp.layer('READING_GUIDE').transform.opacity.valueAtTime(t,false)});
        }
        var mark=cp.layer('ACQUIRED_WORDS'),positions=[];
        for(var j=0;j<words.length;j++){var l=cp.layer(words[j].id);positions.push({id:l.name,initial:l.transform.position.valueAtTime(0,false),at_lift:l.transform.position.valueAtTime(p.lift[1],false),restored:l.transform.position.valueAtTime(8,false),
            pre_hit_opacity:l.transform.opacity.valueAtTime(p.hit[0],false),lift_opacity:l.transform.opacity.valueAtTime(p.lift[1],false),
            lifted_scale:l.transform.scale.valueAtTime(p.lift[1],false),restored_scale:l.transform.scale.valueAtTime(8,false)});}
        var opt=cp.layer('GUIDED_CAMERA').property('ADBE Camera Options Group');
        var liftTime=(p.lift[0]+p.lift[1])/2,lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9];
        for(var id in b.handles){if(b.retreat_positions[id])continue;var l=cp.layer(id),rect=l.sourceRectAtTime(liftTime,false),position=l.transform.position.valueAtTime(liftTime,false),scale=l.transform.scale.valueAtTime(liftTime,false);
            var a=[position[0]+rect.left*scale[0]/100,position[1]+rect.top*scale[1]/100,position[2]],bb=[position[0]+(rect.left+rect.width)*scale[0]/100,position[1]+(rect.top+rect.height)*scale[1]/100,position[2]];
            for(var axis=0;axis<3;axis++){lo[axis]=Math.min(lo[axis],a[axis],bb[axis]);hi[axis]=Math.max(hi[axis],a[axis],bb[axis]);}}
        passes.push({kind:p.kind,visited_lines:visited,scan_samples:samples,pre_hit_mark:mark.transform.opacity.valueAtTime(p.hit[0],false),
            peak_hit_mark:mark.transform.opacity.valueAtTime(p.hit_flash[0]+(p.hit_flash[1]-p.hit_flash[0])/3,false),hit_mark:mark.transform.opacity.valueAtTime(p.hit[1],false),
            lift_handles:handles,positions:positions,
            mark_position:mark.transform.position.valueAtTime(p.hit[1],false),
            mark_size:mark.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').value,
            mark_strokes:mark.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Graphic - Stroke')?1:0,
            lift_focus:{time:liftTime,actual_sentence_center:[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2],
                focus:cp.layer('FOCUS_TARGET').transform.position.valueAtTime(liftTime,false),error:cp.layer('FOCUS_TARGET').transform.position.expressionError},
            apertures:{overview:opt.property('ADBE Camera Aperture').valueAtTime(p.overview[0],false),scan:opt.property('ADBE Camera Aperture').valueAtTime(p.scan[0],false),
                hit:opt.property('ADBE Camera Aperture').valueAtTime(p.hit[1],false),lock:opt.property('ADBE Camera Aperture').valueAtTime(p.lock[1],false),lift:opt.property('ADBE Camera Aperture').valueAtTime(p.lift[1],false)},
            camera:{dof:opt.property('ADBE Camera Depth of Field').value,aperture:opt.property('ADBE Camera Aperture').valueAtTime(p.hit[1],false),
                zoom:opt.property('ADBE Camera Zoom').value,focus_distance:opt.property('ADBE Camera Focus Distance').valueAtTime(p.hit[1],false),focus_error:opt.property('ADBE Camera Focus Distance').expressionError}});
        var states={},times={initial:p.target[0],scan:p.scan[0],before_lift:p.lift[0],lifted:p.lift[1]};
        for(var phase in times){var qo={},oo={};for(var id in questionHandles)qo[id]=cp.layer(id).transform.opacity.valueAtTime(times[phase],false);
            for(var id in optionTexts)oo[id]=cp.layer('ORIGINAL_OPTION_'+id).transform.opacity.valueAtTime(times[phase],false);
            states[phase]={question_opacity:qo,option_opacity:oo};}passes[passes.length-1].mental_state=states;
    }
    return JSON.stringify({kind:b.kind,spec_sha:b.spec_sha,canvas:[cp.width,cp.height,cp.frameRate,cp.duration],renderer:cp.renderer,draft3d:cp.draft3d,resolution_factor:cp.resolutionFactor,
        words:words,handles:handles,initial_handles:b.handles,passes:passes,geometry:{whole:b.whole,hit:b.hit,scope:b.scope,lifted:b.lifted,line_boxes:b.line_boxes,space:b.geometry_space},
        question_parts:questionParts,question_handles:questionHandles,initial_question_handles:b.question_handles,option_texts:optionTexts,viewport_guards:guards,
        temporary_probes:probes,annotation_layers:annotations,visible_attention_cursor:cp.layer('READING_GUIDE').enabled,
        new_method_certification:b.new_method_certification,public_render_ready:b.public_render_ready});
})();
