// Read-only native glyph, world, projection, camera and candidate state audit.
(function(){
    var result={compositions:{},spec_sha:RCF_SHA,errors:[]};
    function track(p){if(!p)return null;var rows=[];for(var i=1;i<=p.numKeys;i++)rows.push([p.keyTime(i),p.keyValue(i)]);return {value:p.value,keys:rows,expression:p.expressionEnabled?p.expression:null};}
    for(var variant in RCF_COMPS){
        var cp=AEMCP.compById(RCF_COMPS[variant]),r={canvas:[cp.width,cp.height,cp.frameRate,cp.duration],renderer:cp.renderer,layers:[],samples:[]};
        if(JSON.parse(cp.comment).spec_sha!==RCF_SHA)throw Error('Wrong comp binding');
        for(var i=1;i<=cp.numLayers;i++){
            var l=cp.layer(i),t=l.transform,row={name:l.name,layer_id:l.id,threeD:l.threeDLayer,parent:l.parent?l.parent.name:null,
                position:track(t.position),anchor:track(t.anchorPoint),opacity:track(t.opacity),scale:track(t.scale),enabled:l.enabled,motionBlur:l.motionBlur,
                rotation:track(t.rotation),comment:l.comment};
            if(l instanceof TextLayer){var p=l.property('ADBE Text Properties').property('ADBE Text Document');
                row.text=p.value.text;row.font=p.value.font;row.fontSize=p.value.fontSize;row.sourceTextKeys=p.numKeys;row.sourceTextExpression=p.expressionEnabled;
                row.bounds=l.sourceRectAtTime(0,false);var anim=l.property('ADBE Text Properties').property('ADBE Text Animators');
                row.color=anim.numProperties?track(anim.property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color')):p.value.fillColor;}
            if(l instanceof CameraLayer){row.look=track(t.pointOfInterest);var o=l.property('ADBE Camera Options Group');
                row.zoom=track(o.property('ADBE Camera Zoom'));row.aperture=track(o.property('ADBE Camera Aperture'));
                row.dof=o.property('ADBE Camera Depth of Field').value;row.focus=track(o.property('ADBE Camera Focus Distance'));
                row.focus_error=o.property('ADBE Camera Focus Distance').expressionError;}
            r.layers.push(row);
        }
        for(var n=0;n<RCF_FRAMES;n++){
            var time=n/24,cam=cp.layer('GUIDED_CAMERA'),o=cam.property('ADBE Camera Options Group');
            r.samples.push({frame:n,mask:cp.layer('FROZEN_CANDIDATE_STATE').property('ADBE Effect Parade').property(1).property(1).valueAtTime(time,false),
                camera:cam.transform.position.valueAtTime(time,false),look:cam.transform.pointOfInterest.valueAtTime(time,false),
                focus:o.property('ADBE Camera Focus Distance').valueAtTime(time,false)});
        }
        r.comparison_rows=[];
        for(var j=0;j<RCF_LAYOUT.length;j++){
            var row=RCF_LAYOUT[j],sample={id:row.id,words:[]};
            for(var k=0;k<row.projection_ids.length;k++){
                var word=cp.layer(row.projection_ids[k]);sample.words.push({id:word.name,
                    position:word.transform.position.valueAtTime(row.settled_at,false),
                    anchor:word.transform.anchorPoint.value,
                    effective_font_size:word.property('Source Text').value.fontSize*word.transform.scale.valueAtTime(row.settled_at,false)[1]/100});
            }
            r.comparison_rows.push(sample);
        }
        result.compositions[variant]=r;
    }
    return JSON.stringify(result);
})();
