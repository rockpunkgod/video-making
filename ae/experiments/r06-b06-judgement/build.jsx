// Native source continuity: duplicate the existing source comp, keep every
// original text object, and replace only authored property tracks/timing.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw Error('Missing bound input');var v=JSON.parse(f.read());f.close();return v;}
    function keys(p,rows){
        while(p.numKeys)p.removeKey(p.numKeys);
        for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
        var spatial=p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL;
        for(var k=1;k<=p.numKeys;k++){
            var n=spatial||p.propertyValueType===PropertyValueType.COLOR?1:(p.value instanceof Array?p.value.length:1),a=[],b=[];
            for(var j=0;j<n;j++){a.push(new KeyframeEase(0,65));b.push(new KeyframeEase(0,65));}
            p.setTemporalEaseAtKey(k,a,b);if(spatial)p.setSpatialAutoBezierAtKey(k,true);
        }
    }
    var P=load(B06_PRODUCTION),S=load(B06_SPEC),old=AEMCP.compById(P.baseline_comp_id);
    if(app.project.file.fsName!==new File(P.project).fsName||app.project.renderQueue.rendering)throw Error('Wrong or busy native project');
    app.beginUndoGroup('Bounded B06 judgement');
    try{
        var cp=old.duplicate();cp.name='B06_JUDGEMENT_SOURCE_R3';cp.duration=S.canvas.duration;
        cp.comment=JSON.stringify({spec_sha:S.spec_sha,parent_spec_sha:P.baseline_spec_sha,review_sha:S.phrase_review_sha,public_render_ready:false});
        for(var i=0;i<S.nodes.length;i++){
            var n=S.nodes[i],l=cp.layer(n.node_id);if(!l)throw Error('Original source object missing: '+n.node_id);
            if(n.kind==='text'&&l.property('Source Text').value.text.replace(/\r/g,'\n')!==n.text)throw Error('Original glyphs differ');
            l.inPoint=n.in_point;l.outPoint=n.out_point;
            for(var name in n.tracks){
                var p=null;
                if(name==='position'||name==='scale'||name==='opacity')p=l.transform[name];
                else if(name==='color')p=l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');
                else if(name==='blur')p=l.property('ADBE Effect Parade').property(1).property(1);
                else continue;
                if(!p)throw Error('Existing native property missing: '+n.node_id+':'+name);keys(p,n.tracks[name]);
            }
        }
        keys(cp.layer('COGNITIVE_ATTENTION').transform.position,S.camera.position);
        for(var i=1;i<=cp.numLayers;i++){
            var l=cp.layer(i);if(l.name==='PAPER'||l.name==='CAPTION_PAPER'||l.name==='COGNITIVE_ATTENTION'||l.name==='COGNITIVE_CAMERA')l.outPoint=cp.duration;
        }
        var link=S.reviewed_connector,shape=cp.layers.addShape();shape.name=link.node_id;
        shape.comment=JSON.stringify({review_sha:link.review_sha,operation_ids:link.operation_ids,relation_ref:link.relation_ref});
        shape.inPoint=P.bounds.new_pure[0]/24;shape.outPoint=P.bounds.new_pure[1]/24;
        var group=shape.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
        group.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Group');
        group.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Stroke');
        group=shape.property('ADBE Root Vectors Group').property(1);
        var path=new Shape();path.vertices=link.points;path.closed=false;path.inTangents=[];path.outTangents=[];
        for(var v=0;v<link.points.length;v++){path.inTangents.push([0,0]);path.outTangents.push([0,0]);}
        group.property('ADBE Vectors Group').property('ADBE Vector Shape - Group').property('ADBE Vector Shape').setValue(path);
        var stroke=group.property('ADBE Vectors Group').property('ADBE Vector Graphic - Stroke');
        stroke.property('ADBE Vector Stroke Width').setValue(link.stroke);
        stroke.property('ADBE Vector Stroke Color').setValue([parseInt(link.color.substr(1,2),16)/255,parseInt(link.color.substr(3,2),16)/255,parseInt(link.color.substr(5,2),16)/255]);
        shape.transform.position.setValue([0,0]);keys(shape.transform.opacity,link.opacity);
        var results={},definitions=[
            ['OLD_B06_FULL',old,P.bounds.old_pure,false],['NEW_B06_FULL',cp,P.bounds.new_pure,false],
            ['OLD_CONTEXT_VISUAL',old,P.bounds.old_context,true],['NEW_CONTEXT_VISUAL',cp,P.bounds.new_context,true],
            ['OLD_CONTEXT_FULL',old,P.bounds.old_context,false],['NEW_CONTEXT_FULL',cp,P.bounds.new_context,false]];
        for(var k=0;k<definitions.length;k++){
            var d=definitions[k],duration=(d[2][1]-d[2][0])/24,part=app.project.items.addComp(d[0],3840,2160,1,duration,24);
            var content=part.layers.add(d[1]);content.name='BOUND_NATIVE_SOURCE';content.startTime=-d[2][0]/24;content.inPoint=0;content.outPoint=duration;
            if(d[3]){
                var mask=part.layers.addSolid([243/255,240/255,233/255],'REMOVE_EXPLANATORY_CAPTIONS',3840,2160-S.caption_safe_top,1,duration);
                mask.transform.position.setValue([1920,(2160+S.caption_safe_top)/2]);
            }
            part.comment=JSON.stringify({production_sha:P.production_sha,native_source_comp_id:d[1].id,source_frames:d[2],mode:d[3]?'visual_only':'full',public_render_ready:false});
            results[d[0]]={comp_id:part.id,frames:d[2][1]-d[2][0],source_frames:d[2]};
        }
        var active=AEMCP.compById(results.NEW_B06_FULL.comp_id);active.openInViewer();app.project.save();
        var probe=app.project.renderQueue.items.add(active),templates=probe.outputModule(1).templates;probe.remove();
        return JSON.stringify({comp_id:active.id,source_comp_id:cp.id,old_source_comp_id:old.id,compositions:results,output_templates:templates,project:app.project.file.fsName,spec_sha:S.spec_sha,public_render_ready:false});
    }finally{app.endUndoGroup();}
})();
