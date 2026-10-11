// Read-only native key/value audit. AUDIT_INPUT is a bounded JSON page.
(function(){
    var f=new File(AUDIT_INPUT);f.encoding='UTF-8';f.open('r');var s=JSON.parse(f.read());f.close();
    var cp=AEMCP.compById(s.comp_id),errors=[],checked=0;
    function equal(a,b){if(a instanceof Array){if(!(b instanceof Array)||a.length!==b.length)return false;for(var j=0;j<a.length;j++)if(!equal(a[j],b[j]))return false;return true;}return Math.abs(a-b)<0.0001;}
    function verify(p,rows,name,screenPosition,screenScale){
        if(!p||p.numKeys!==rows.length){errors.push(name+': key count');return;}
        for(var k=1;k<=p.numKeys;k++){
            var actual=p.keyValue(k),expected=rows[k-1][1];
            if(p.propertyValueType===PropertyValueType.COLOR&&actual.length===4&&expected.length===3&&Math.abs(actual[3]-1)<0.0001)actual=actual.slice(0,3);
            if(screenPosition&&actual instanceof Array&&expected instanceof Array&&actual.length===3&&expected.length===2&&Math.abs(actual[2])<0.0001)actual=actual.slice(0,2);
            if(screenScale&&actual instanceof Array&&expected instanceof Array&&actual.length===3&&expected.length===3&&Math.abs(actual[2]-100)<0.0001){actual=actual.slice(0,2);expected=expected.slice(0,2);}
            if(Math.abs(p.keyTime(k)-rows[k-1][0])>0.0001||!equal(actual,expected))errors.push(name+': key '+k);
            checked++;
        }
    }
    verify(cp.layer('COGNITIVE_ATTENTION').transform.position,s.camera.position,'camera');
    for(var i=0;i<s.nodes.length;i++){
        var n=s.nodes[i],l=cp.layer(n.node_id);
        if(Math.abs(l.inPoint-n.in_point)>0.0001||Math.abs(l.outPoint-n.out_point)>0.0001)errors.push(n.node_id+': lifetime');
        for(var name in n.tracks){
            var p=null;
            if(name==='position'||name==='scale'||name==='opacity')p=l.transform[name];
            else if(name==='color')p=l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');
            else if(name==='blur')p=l.property('ADBE Effect Parade').property(1).property(1);
            else continue;
            verify(p,n.tracks[name],n.node_id+': '+name,name==='position'&&n.space==='screen'&&!l.threeDLayer,name==='scale'&&n.space==='screen'&&!l.threeDLayer);
        }
        var band=cp.layer('CAPTION_PAPER');
        if(n.node_id.indexOf('caption:')===0&&l.index>band.index)errors.push('caption behind band');
        if(n.node_id.indexOf('source:')===0&&l.index<band.index)errors.push('source above caption protection');
    }
    var link=s.reviewed_connector,shape=cp.layer(link.node_id),group=shape.property('ADBE Root Vectors Group').property(1);
    var actualPath=group.property('ADBE Vectors Group').property('ADBE Vector Shape - Group').property('ADBE Vector Shape').value;
    if(!equal(actualPath.vertices,link.points)||shape.comment!==JSON.stringify({review_sha:link.review_sha,operation_ids:link.operation_ids,relation_ref:link.relation_ref}))errors.push('reviewed relation connector changed');
    verify(shape.transform.opacity,link.opacity,'reviewed relation');
    return JSON.stringify({project:app.project.file.fsName,comp_id:cp.id,checked_keys:checked,errors:errors});
})();
