/* Frozen presentation projection. The pinned question never follows body motion. */
(function(){
    var f=new File(PASSAGE_REQUEST);f.encoding='UTF-8';f.open('r');var r=JSON.parse(f.read());f.close();
    var dest=new File(r.project);if(dest.exists)throw new Error('Preserve existing revision');
    if(!app.project.file||app.project.file.fsName.toLowerCase()!==(new File(r.previous_project)).fsName.toLowerCase())throw new Error('Active project changed');
    app.project.save();app.newProject();app.project.save(dest);
    function col(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    function ease(p){for(var k=1;k<=p.numKeys;k++){
        var n=p.keyValue(k) instanceof Array?p.keyValue(k).length:1,a=[],b=[];
        if(p.isSpatial)n=1;
        for(var j=0;j<n;j++){a.push(new KeyframeEase(0,72));b.push(new KeyframeEase(0,72));}
        p.setTemporalEaseAtKey(k,a,b);
    }}
    app.beginUndoGroup('Expression-led frozen passage');
    var results=[];
    try{
        for(var i=0;i<r.scenes.length;i++){
            var s=r.scenes[i],d=r.direction.scenes[s.segment_id],cp=app.project.items.addComp('DIRECTED_'+s.segment_id,1920,1080,1,24,24);
            cp.bgColor=col('#FAF8F2');cp.comment=JSON.stringify({segment_sha:s.segment_sha,
                plan_sha:r.direction.plan_sha,presentation_sha:r.presentation_sha,direction_sha:r.direction.direction_sha});
            var order=r.motion_orders[s.segment_id]||[];
            if(!order.length){for(var a=0;a<s.annotations.length;a++)order.push('source_'+a);if(s.kind==='closure')order.push('verdict');}
            for(var j=0;j<d.nodes.length;j++){
                var n=d.nodes[j],l;
                if(n.type==='panel'){
                    l=cp.layers.addShape();l.name=n.name;
                    var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
                    var rect=g.addProperty('ADBE Vector Shape - Rect');rect.property('ADBE Vector Rect Size').setValue([n.w,n.h]);
                    var fill=g.addProperty('ADBE Vector Graphic - Fill');fill.property('ADBE Vector Fill Color').setValue(col(n.color));
                    l.transform.anchorPoint.setValue([-n.w/2,-n.h/2]);
                }else{
                    l=cp.layers.addText(n.text);l.name=n.name;var st=l.property('Source Text'),doc=st.value;
                    doc.font=n.font;doc.fontSize=n.size;doc.applyFill=true;doc.fillColor=col(n.color);doc.applyStroke=false;
                    doc.tracking=0;doc.autoLeading=false;doc.leading=n.size*1.24;doc.justification=ParagraphJustification.LEFT_JUSTIFY;st.setValue(doc);
                    var box=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue([box.left,box.top]);
                }
                l.comment=JSON.stringify({origin:n.origin||'presentation',direction_sha:r.direction.direction_sha});
                l.transform.position.setValue([n.x,n.y]);
                var start=n.event ? .5+order.indexOf(n.event)*.75 : 0;
                if(n.event&&order.indexOf(n.event)<0)throw new Error('Unbound native event');
                if(n.travel||n.from_position){
                    l.transform.position.setValueAtTime(start,n.from_position||[n.x+n.travel,n.y]);
                    l.transform.position.setValueAtTime(start+.5,[n.x,n.y]);ease(l.transform.position);
                }
                if(n.event){
                    l.transform.opacity.setValueAtTime(start,0);l.transform.opacity.setValueAtTime(start+.16,100);
                    if(n.type==='panel'){
                        l.transform.scale.setValueAtTime(start,[60,100]);l.transform.scale.setValueAtTime(start+.5,[100,100]);ease(l.transform.scale);
                    }else if(n.from_scale||(n.zoom&&n.zoom!==1)){
                        var initialScale=n.from_scale||n.zoom;
                        l.transform.scale.setValueAtTime(start,[100*initialScale,100*initialScale]);
                        l.transform.scale.setValueAtTime(start+.5,[100,100]);ease(l.transform.scale);
                    }
                    if(n.exclusive){
                        var next=order.length;
                        for(var z=order.indexOf(n.event)+1;z<order.length;z++)if(order[z].indexOf('source_')===0){next=z;break;}
                        if(next<order.length){var at=.5+next*.75;l.transform.opacity.setValueAtTime(at-1/24,100);l.transform.opacity.setValueAtTime(at+.08,0);}
                    }
                }
                l.motionBlur=false;
            }
            cp.saveFrameToPng(3.5,new File(r.styleframes+'/'+s.segment_id+'.png'));
            if(r.wide_frames)cp.saveFrameToPng(.45,new File(r.styleframes+'/'+s.segment_id+'-wide.png'));
            results.push({segment_id:s.segment_id,comp_id:cp.id,mode:d.mode});
        }
        app.project.save(dest);return JSON.stringify({project:dest.fsName,scenes:results,direction_sha:r.direction.direction_sha});
    }finally{app.endUndoGroup();}
})();
