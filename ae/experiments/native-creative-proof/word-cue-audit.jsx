// Read real word/scope handoffs. Does not certify English relationships.
(function(){
    var f=new File(NCP_REQUEST);f.encoding='UTF-8';if(!f.open('r'))throw new Error('Missing frozen request');
    var R=JSON.parse(f.read());f.close();var cp=AEMCP.compById(NCP_COMP),binding=JSON.parse(cp.comment);
    if(binding.spec_sha!==R.spec_sha)throw new Error('Different recognition binding');
    var cues=[];
    for(var i=0;i<R.cue_layout.length;i++){
        var cue=R.cue_layout[i],word=cp.layer('WORD_CUE_'+cue.object_id),range=cp.layer('RANGE_CUE_'+cue.object_id);
        var joint=cp.layer('ATTACHMENT_'+cue.object_id),carrier=cp.layer('CARRIER_'+cue.object_id),hinge=word.parent;
        var onset=hinge.transform.position.keyTime(2),cut=hinge.transform.position.keyTime(3),land=hinge.transform.position.keyTime(5);
        var phases=[['word',(cue.cue_start+cue.handoff)/2],['scope',(cue.scope_ready+onset)/2],['detached',cut],['park',land+2/cp.frameRate]],samples=[];
        for(var j=0;j<phases.length;j++){
            var t=phases[j][1];samples.push({phase:phases[j][0],time:t,word:word.transform.opacity.valueAtTime(t,false),
                range:range.transform.opacity.valueAtTime(t,false),range_scale:range.transform.scale.valueAtTime(t,false)[0],
                joint:joint.transform.opacity.valueAtTime(t,false),carrier:carrier.transform.opacity.valueAtTime(t,false)});
        }
        var width=word.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').value[0];
        cues.push({object_id:cue.object_id,origin:JSON.parse(word.comment),parent:hinge.name,threeD:word.threeDLayer,
            range_parent:range.parent.name,width:width,position:word.transform.position.value,samples:samples});
    }
    return JSON.stringify({spec_sha:R.spec_sha,scene_sha:R.scene_sha,cues:cues});
})();
