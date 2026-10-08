// Read actual supplied visual anchors; no English analysis or project mutation.
(function(){
    var f=new File(NCP_REQUEST);f.encoding='UTF-8';if(!f.open('r'))throw new Error('Missing frozen request');
    var R=JSON.parse(f.read());f.close();var cp=AEMCP.compById(NCP_COMP),binding=JSON.parse(cp.comment);
    if(binding.spec_sha!==R.spec_sha||binding.presentation_id!==R.presentation.id)throw new Error('Different native layout binding');
    function present(t){var r=R.presentation.time_map;for(var i=1;i<r.length;i++)if(t<=r[i][0])return r[i-1][1]+(t-r[i-1][0])*(r[i][1]-r[i-1][1])/(r[i][0]-r[i-1][0]);return cp.duration;}
    var rows=[];
    for(var i=0;i<R.layout.length;i++)if(R.layout[i].role==='supplied_modifier'){
        var n=R.layout[i],l=cp.layer(n.id),h=l.parent,a=cp.layer(n.attachment),line=cp.layer('RELATION_'+n.id);
        var times=[['original',0],['park',present(n.id==='aside-time'?10.9:17.5)],['final',cp.duration-1/cp.frameRate]];
        if(n.id==='aside-time')times.push(['follow',present(10.7)+Math.min(2/cp.frameRate,(present(10.9)-present(10.7))/2)]);
        for(var j=0;j<times.length;j++){
            var phase=times[j][0],t=times[j][1],hp=h.transform.position.valueAtTime(t,false),ap=a.transform.position.valueAtTime(t,false);
            var sc=h.transform.scale.valueAtTime(t,false)[0],lp=l.transform.position.valueAtTime(t,false);
            var br=l.sourceRectAtTime(t,false),ar=a.sourceRectAtTime(t,false);
            var path=line.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Group').property('ADBE Vector Shape').valueAtTime(t,false);
            rows.push({object_id:n.id,anchor_id:n.attachment,phase:phase,time:t,pivot:hp,anchor_position:ap,scale_percent:sc,
                center_error:hp[0]+(lp[0]+br.left+br.width/2)*sc/100-(ap[0]+ar.left+ar.width/2),
                baseline_gap:hp[1]+lp[1]*sc/100-ap[1],y_rotation:h.transform.yRotation.valueAtTime(t,false),z_rotation:h.transform.zRotation.valueAtTime(t,false),
                text_opacity:l.transform.opacity.valueAtTime(t,false),connector:JSON.parse(line.comment),connector_opacity:line.transform.opacity.valueAtTime(t,false),connector_vertices:path.vertices});
        }
    }
    return JSON.stringify({spec_sha:R.spec_sha,scene_sha:R.scene_sha,kind:'supplied_synthetic_visual_attachment',samples:rows});
})();
