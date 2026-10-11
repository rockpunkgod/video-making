// One frozen real-action experiment. RCF_SPEC names a private authored input.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw Error('Missing input');var v=JSON.parse(f.read());f.close();return v;}
    var S=load(RCF_SPEC),scale=2,words={},origins={},sourceLayers={},geometry=[],baselineOffsets={};
    if(S.kind!=='reality_cognitive_native_fast_pass'||S.public_render_ready!==false)throw Error('Bound internal proof required');
    if(app.project.file.fsName!==new File(S.project).fsName||app.project.renderQueue.rendering)throw Error('Wrong or busy native project');
    var cp=app.project.items.addComp('B_CONTINUOUS_COGNITIVE_CAMERA',3840,2160,1,S.duration,24);
    cp.renderer='ADBE Classic 3D';cp.bgColor=S.palette.background;cp.motionBlur=true;cp.shutterAngle=90;
    cp.comment=JSON.stringify({kind:S.kind,spec_sha:S.spec_sha,variant:'B',public_render_ready:false});
    function xyz(p){return [p[0]*scale,p[1]*scale,(p[2]||0)*scale];}
    function rows(items){var result=[];for(var i=0;i<items.length;i++)result.push([items[i][0],items[i][1] instanceof Array?xyz(items[i][1]):items[i][1]]);return result;}
    function baselineOffset(size){
        if(baselineOffsets[size]===undefined){
            var probe=cp.layers.addText('Hgj'),d=probe.property('Source Text').value;
            d.font=S.font;d.fontSize=size*scale;probe.property('Source Text').setValue(d);
            baselineOffsets[size]=-probe.sourceRectAtTime(0,false).top/scale;probe.remove();
        }
        return baselineOffsets[size];
    }
    function text(name,value,size,pos,color,world){
        var l=cp.layers.addText(value);l.name=name;
        var doc=l.property('ADBE Text Properties').property('ADBE Text Document').value;
        doc.font=S.font;doc.fontSize=size*scale;doc.fillColor=color;doc.applyFill=true;doc.applyStroke=false;
        doc.justification=ParagraphJustification.LEFT_JUSTIFY;doc.tracking=0;
        l.property('ADBE Text Properties').property('ADBE Text Document').setValue(doc);
        l.threeDLayer=world;l.motionBlur=world;
        var r=l.sourceRectAtTime(0,false),baseline=S.text_alignment==='shared_baseline';
        l.transform.anchorPoint.setValue(world?[r.left,baseline?0:r.top,0]:[r.left,baseline?0:r.top]);
        var y=pos[1]+(baseline?baselineOffset(size):0);
        l.transform.position.setValue(world?xyz([pos[0],y,pos[2]||0]):[pos[0]*scale,y*scale]);
        return l;
    }
    function rect(name,w,h,pos,color){
        var l=cp.layers.addShape();l.name=name;l.threeDLayer=true;
        var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
        g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
        g=l.property('ADBE Root Vectors Group').property(1);g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
        g=l.property('ADBE Root Vectors Group').property(1);
        g.property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([w*scale,h*scale]);
        g.property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(color);
        l.transform.position.setValue(xyz(pos));return l;
    }
    function colour(l,track){
        var anim=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');
        anim.name='BOUND_ATTENTION_COLOR';anim.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');
        var p=l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');
        RCF_keys(p,track,false);
    }
    rect('REALITY_PAPER_EDGE',2058,1276,[1136,750,10],S.palette.edge);
    rect('REALITY_PAPER',2058,1276,[1111,728,8],S.palette.paper);
    // Native glyph measurements determine actual wrapping, origin and capture.
    for(var ci=0;ci<S.columns.length;ci++){
        var col=S.columns[ci],x=col.x,y=col.y,space=col.space*scale;
        for(var wi=0;wi<col.words.length;wi++){
            var w=col.words[wi];if(w.new_paragraph){x=col.x;y+=col.paragraph_gap;}
            var l=text(w.id,w.text,col.size,[x,y,0],S.palette.ink,true),r=l.sourceRectAtTime(0,false);
            if(x+r.width/scale>col.x+col.width&&x>col.x){x=col.x;y+=col.line_height;}
            var origin=[x,y+(S.text_alignment==='shared_baseline'?baselineOffset(col.size):0),0];
            l.transform.position.setValue(xyz(origin));
            l.comment=JSON.stringify({kind:'source_world_word',id:w.id,object_id:col.object_id,range:w.range,source_ref:col.source_ref});
            origins[w.id]=origin;words[w.id]=l;sourceLayers[w.id]=w;
            var visibility=w.opacity_track||(col.object_id===S.eliminated_object_id?S.world_eliminated_opacity:S.world_opacity);
            RCF_keys(l.transform.opacity,visibility,false);
            if(w.colour_track)colour(l,w.colour_track);
            geometry.push({id:w.id,layer_id:l.id,object_id:col.object_id,range:w.range,text:w.text,font:l.property('Source Text').value.font,
                origin:origin,size:col.size,bounds:[r.left,r.top,r.width,r.height]});
            x+=r.width/scale+space/scale;
        }
    }
    for(var i=0;i<S.labels.length;i++){var q=S.labels[i],label=text(q.id,q.text,q.size,q.position,S.palette.ink,true);
        RCF_keys(label.transform.opacity,q.opacity_track||S.world_opacity,false);}
    function duplicateProjection(node){
        var original=words[node.origin_word_id];if(!original)throw Error('No actual glyph origin');
        var l=original.duplicate();l.name=node.id;while(l.transform.opacity.numKeys)l.transform.opacity.removeKey(1);
        var anims=l.property('ADBE Text Properties').property('ADBE Text Animators');while(anims.numProperties)anims.property(1).remove();
        l.comment=JSON.stringify({kind:'bound_projection',id:node.id,origin_word_id:node.origin_word_id,origin_layer_id:original.id,
            object_id:sourceLayers[node.origin_word_id].object_id,range:sourceLayers[node.origin_word_id].range});
        var base=origins[node.origin_word_id],path=[];
        for(var j=0;j<node.path.length;j++){
            var value=node.path[j][1];if(value==='ORIGIN')value=base;
            else if(value.origin_offset)value=[base[0]+value.origin_offset[0],base[1]+value.origin_offset[1],base[2]+value.origin_offset[2]];
            path.push([node.path[j][0],xyz(value)]);
        }
        RCF_keys(l.transform.position,path,false);RCF_keys(l.transform.scale,node.scale,false);
        RCF_keys(l.transform.opacity,node.opacity,false);if(node.colour_track)colour(l,node.colour_track);
        return l;
    }
    for(var i=0;i<S.projections.length;i++)duplicateProjection(S.projections[i]);
    var state=cp.layers.addNull(cp.duration);state.name='FROZEN_CANDIDATE_STATE';state.enabled=false;
    state.property('ADBE Effect Parade').addProperty('ADBE Slider Control').name='CANDIDATE_MASK';
    RCF_keys(state.property('ADBE Effect Parade').property(1).property(1),S.candidate_mask,true);
    var focus=cp.layers.addNull(cp.duration);focus.name='FOCUS_TARGET';focus.threeDLayer=true;focus.enabled=false;
    RCF_cameraKeys(focus.transform.position,rows(S.camera.focus),S.camera.carry_keys);
    var cam=cp.layers.addCamera('GUIDED_CAMERA',[1920,1080]);cam.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    RCF_cameraKeys(cam.transform.position,rows(S.camera.position),S.camera.carry_keys);
    RCF_cameraKeys(cam.transform.pointOfInterest,rows(S.camera.look),S.camera.carry_keys);
    var opt=cam.property('ADBE Camera Options Group');opt.property('ADBE Camera Zoom').setValue(S.camera.zoom*scale);
    opt.property('ADBE Camera Depth of Field').setValue(1);opt.property('ADBE Camera Blur Level').setValue(65);
    RCF_keys(opt.property('ADBE Camera Aperture'),rows(S.camera.aperture),false);
    opt.property('ADBE Camera Focus Distance').expression='var p=thisComp.layer("FOCUS_TARGET").toWorld([0,0,0]);var c=transform.position;var v=normalize(sub(transform.pointOfInterest,c));Math.max(1,dot(sub(p,c),v));';
    var marker=text('INTERNAL_REVIEW_MARKER',S.internal_marker,16,[56,1038],S.palette.muted,false);marker.transform.opacity.setValue(55);
    // Strict camera control: clone the whole completed scene and change only
    // camera Position / Point of Interest. All other objects/tracks remain.
    var a=cp.duplicate();a.name='A_FIXED_CAMERA';a.comment=JSON.stringify({kind:S.kind,spec_sha:S.spec_sha,variant:'A',public_render_ready:false});
    var fixed=a.layer('GUIDED_CAMERA');var props=[fixed.transform.position,fixed.transform.pointOfInterest];
    for(var j=0;j<props.length;j++){var initial=props[j].valueAtTime(0,false);while(props[j].numKeys)props[j].removeKey(1);props[j].setValue(initial);}
    for(var i=1;i<=a.numLayers;i++){var l=a.layer(i);if(!l.comment)continue;var binding=JSON.parse(l.comment);
        if(binding.kind==='bound_projection'){binding.origin_layer_id=a.layer(binding.origin_word_id).id;l.comment=JSON.stringify(binding);}}
    cp.openInViewer();app.project.save();
    return JSON.stringify({comp_id:cp.id,compositions:{A:a.id,B:cp.id},project:app.project.file.fsName,spec_sha:S.spec_sha,
        geometry:geometry,renderer:cp.renderer,frames:S.frames,public_render_ready:false});
})();
