// Layout executor only. Text and relations arrive with frozen source bindings.
(function () {
    function load(path) { var f=new File(path); f.encoding='UTF-8'; if(!f.open('r'))throw new Error('Missing request'); var s=f.read();f.close();return JSON.parse(s); }
    function rgb(h) { return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255]; }
    function keys(p, rows, ease) {
        for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
        if(ease)for(var i=1;i<=p.numKeys;i++) {
            var count=p.isSpatial?1:(p.value instanceof Array?p.value.length:1),a=[],b=[];
            for(var j=0;j<count;j++){a.push(new KeyframeEase(0,66));b.push(new KeyframeEase(0,66));}
            p.setTemporalEaseAtKey(i,a,b);
            if(p.isSpatial)p.setSpatialAutoBezierAtKey(i,true);
        }
    }
    var R=load(STUDENT_PICTURE_REQUEST),S=R.spec,D=S.direction,dest=new File(R.project);
    if(dest.exists)throw new Error('Preserve earlier project revisions');
    app.project.save(dest);app.beginUndoGroup('Student POV picture preparation');
    try {
        var cp=app.project.items.addComp('STUDENT_POV_PICTURE',1920,1080,1,D.canvas.duration,24);
        cp.bgColor=rgb(D.palette.paper);cp.motionBlur=false;
        cp.comment=JSON.stringify({spec_sha:S.spec_sha,plan_sha:S.plan_sha,copy_sha:S.copy_sha,voice_status:D.voice_status,public_render_ready:false});
        cp.layers.addSolid(rgb(D.palette.paper),'PAPER',1920,1080,1,D.canvas.duration);
        for(var i=0;i<D.nodes.length;i++) {
            var n=D.nodes[i],l;
            if(n.kind==='text') {
                l=cp.layers.addText('');var p=l.property('ADBE Text Properties').property('ADBE Text Document'),t=p.value;
                t.text=n.text;t.font=n.font;t.fontSize=n.size;t.applyFill=true;t.applyStroke=false;
                t.fillColor=rgb(n.color);t.justification=ParagraphJustification.LEFT_JUSTIFY;
                t.tracking=0;t.autoLeading=false;t.leading=n.leading||n.size*1.42;p.setValue(t);
                l.transform.anchorPoint.setValue([0,0]);
            } else {
                l=cp.layers.addShape();var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
                g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
                g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
                g=l.property('ADBE Root Vectors Group').property(1);
                var rect=g.property('ADBE Vectors Group').property('ADBE Vector Shape - Rect');
                rect.property('ADBE Vector Rect Size').setValue([n.width,n.height]);
                rect.property('ADBE Vector Rect Position').setValue([n.width/2,n.kind==='line'?0:n.height/2]);
                rect.property('ADBE Vector Rect Roundness').setValue(n.radius||0);
                g.property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(rgb(n.color));
                var widths=[],centers=[];if(n.tracks.width)for(var w=0;w<n.tracks.width.length;w++) {
                    widths.push([n.tracks.width[w][0],[n.tracks.width[w][1],n.height]]);
                    centers.push([n.tracks.width[w][0],[n.tracks.width[w][1]/2,n.kind==='line'?0:n.height/2]]);
                }
                if(widths.length) {
                    keys(rect.property('ADBE Vector Rect Size'),widths,false);
                    keys(rect.property('ADBE Vector Rect Position'),centers,false);
                }
            }
            l.name=n.node_id;l.comment=JSON.stringify({text_binding:n.text_binding||null,source_refs:n.source_refs||[]});
            l.inPoint=n.in_point;l.outPoint=n.out_point;l.transform.position.setValue(n.position);
            if(n.rotation)l.transform.rotation.setValue(n.rotation);
            if(n.tracks.position)keys(l.transform.position,n.tracks.position,true);
            if(n.tracks.opacity)keys(l.transform.opacity,n.tracks.opacity,true);
            if(n.tracks.scale)keys(l.transform.scale,n.tracks.scale,true);
        }
        for(var name in D.phases)if(name!=='end') {
            var m=new MarkerValue(name);cp.markerProperty.setValueAtTime(D.phases[name],m);
        }
        var lock=cp.layers.addText('');lock.name='SPEC_BINDING';lock.enabled=false;lock.comment=S.spec_sha;
        cp.openInViewer();app.project.save(dest);
        return JSON.stringify({ok:true,project:dest.fsName,comp_id:cp.id,spec_sha:S.spec_sha,layers:cp.numLayers});
    } finally {app.endUndoGroup();}
})();
