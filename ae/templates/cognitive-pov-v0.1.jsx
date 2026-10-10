// Deterministic executor. English roles, spans and results arrive in the spec.
// One persistent Reality Layer; camera distance expresses attention scope.
(function () {
    function load(path) { var f=new File(path); f.encoding='UTF-8'; if(!f.open('r'))throw new Error('Missing spec'); var s=f.read();f.close();return JSON.parse(s); }
    function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    function keys(p, rows, ease) {
        var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;
        for(var k=0;k<rows.length;k++)p.setValueAtTime(rows[k][0],rows[k][1]);
        if(ease) for(var k=1;k<=p.numKeys;k++) {
            var count=spatial||p.propertyValueType===PropertyValueType.COLOR?1:(p.value instanceof Array?p.value.length:1), ins=[],outs=[];
            for(var j=0;j<count;j++){ins.push(new KeyframeEase(0,65));outs.push(new KeyframeEase(0,65));}
            p.setTemporalEaseAtKey(k,ins,outs);
            if(spatial)p.setSpatialAutoBezierAtKey(k,true);
        }
    }
    var R=load(COGNITIVE_REQUEST), S=R.spec, dest=new File(R.project);
    if(dest.exists)throw new Error('Existing revision; inspect rather than rebuild');
    app.project.save(dest); app.beginUndoGroup('Swiss Cognitive POV');
    try {
        var W=S.canvas.width||1920,H=S.canvas.height||1080;
        var cp=app.project.items.addComp('SWISS_COGNITIVE_POV',W,H,1,S.canvas.duration,S.canvas.fps||24);
        cp.bgColor=rgb(S.palette.paper);cp.motionBlur=true;cp.shutterAngle=120;
        cp.comment=JSON.stringify({spec_sha:S.spec_sha,application_sha:S.application_sha,public_render_ready:false});
        cp.layers.addSolid(rgb(S.palette.paper),'PAPER',W,H,1,S.canvas.duration);
        var rig=cp.layers.addNull(S.canvas.duration);rig.name='COGNITIVE_ATTENTION';rig.threeDLayer=true;
        keys(rig.transform.position,S.camera.position,true);
        var camera=cp.layers.addCamera('COGNITIVE_CAMERA',[W/2,H/2]);camera.autoOrient=AutoOrientType.NO_AUTO_ORIENT;
        camera.parent=rig;camera.transform.position.setValue([0,0,0]);camera.transform.orientation.setValue([0,0,0]);
        camera.property('ADBE Camera Options Group').property('ADBE Camera Zoom').setValue(S.camera.zoom);
        camera.property('ADBE Camera Options Group').property('ADBE Camera Depth of Field').setValue(0);
        for(var i=0;i<S.nodes.length;i++) {
            var n=S.nodes[i],l;
            if(n.kind==='text') {
                l=cp.layers.addText('');var prop=l.property('ADBE Text Properties').property('ADBE Text Document'),d=prop.value;
                d.text=n.text;d.font=n.font;d.fontSize=n.size;d.fillColor=rgb(n.color);d.applyFill=true;d.applyStroke=false;
                d.justification=ParagraphJustification.LEFT_JUSTIFY;d.tracking=0;d.autoLeading=false;d.leading=n.size*1.42;
                prop.setValue(d);l.transform.anchorPoint.setValue([0,0]);
            } else if(n.kind==='line') {
                l=cp.layers.addShape();var group=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
                group.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
                group.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
                // Reacquire after adding indexed properties.
                group=l.property('ADBE Root Vectors Group').property(1);
                var rect=group.property('ADBE Vectors Group').property('ADBE Vector Shape - Rect');
                rect.property('ADBE Vector Rect Size').setValue([n.width,n.stroke]);
                rect.property('ADBE Vector Rect Position').setValue([n.width/2,0]);
                group.property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(rgb(n.color));
                var wt=[];for(var w=0;w<n.tracks.width.length;w++)wt.push([n.tracks.width[w][0],[n.tracks.width[w][1],n.stroke]]);
                keys(rect.property('ADBE Vector Rect Size'),wt,false);
            } else throw new Error('Unsupported native node');
            l.name=n.node_id;l.comment=JSON.stringify({span_id:n.span_id||null,unit_id:n.unit_id||null,source_start:n.start,source_end:n.end,source_refs:n.source_refs||[],origin_object_id:n.origin_object_id||n.node_id});
            l.threeDLayer=n.space==='world';l.motionBlur=l.threeDLayer;
            l.transform.position.setValue(l.threeDLayer?n.position:n.position.slice(0,2));
            l.inPoint=n.in_point||0;l.outPoint=n.out_point||S.canvas.duration;
            if(n.tracks.position)keys(l.transform.position,n.tracks.position,true);
            if(n.tracks.scale)keys(l.transform.scale,n.tracks.scale,true);
            if(n.tracks.opacity)keys(l.transform.opacity,n.tracks.opacity,true);
            if(n.tracks.color && n.kind==='text') {
                var animator=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');
                var fill=animator.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');
                keys(fill,n.tracks.color,true);
            }
            if(n.tracks.blur) {
                l.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');
                keys(l.property('ADBE Effect Parade').property(1).property(1),n.tracks.blur,false);
            }
        }
        // The lower band belongs to captions/PR; it never replaces the Reality Layer.
        var captionHeight=S.inline_captions&&S.caption_safe_top!==undefined?H-S.caption_safe_top:112*H/1080;
        var band=cp.layers.addSolid(rgb(S.palette.paper),'CAPTION_PAPER',W,captionHeight,1,S.canvas.duration);
        band.transform.position.setValue([W/2,H-captionHeight/2]);
        if(S.inline_captions) {
            // Keep the reading surface out of the caption area; captions stay above it.
            var lowestCaption=null;
            for(var ci=1;ci<=cp.numLayers;ci++)if(cp.layer(ci).name.indexOf('caption:')===0)lowestCaption=cp.layer(ci);
            if(lowestCaption)band.moveAfter(lowestCaption);
        }
        var binding=cp.layers.addText('');binding.name='SPEC_BINDING';binding.enabled=false;binding.comment=S.spec_sha;
        cp.openInViewer();app.project.save(dest);
        return JSON.stringify({ok:true,project:dest.fsName,comp_id:cp.id,spec_sha:S.spec_sha,layers:cp.numLayers});
    } finally {app.endUndoGroup();}
})();
