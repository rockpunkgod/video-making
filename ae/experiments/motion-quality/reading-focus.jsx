// Local revision of the existing B. The supplied spans come from measured
// composed lines and reviewed exact source text, not a language parser.
function mqReadingEnvelope(c) {
    return 'function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}\n'+
      'var a=s((time-('+c.center+'-'+c.hold/2+'-'+c.attack+'))/'+c.attack+')*'+
      's((('+c.center+'+'+c.hold/2+'+'+c.release+')-time)/'+c.release+');\n';
}
function mqReadingSelector(layer,name,lo,hi) {
    var an=layer.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');an.name=name;
    var sel=an.property('ADBE Text Selectors').addProperty('ADBE Text Selector'),adv=sel.property('ADBE Text Range Advanced');
    adv.property('ADBE Text Range Units').setValue(2);
    sel.property('ADBE Text Index Start').setValue(lo);sel.property('ADBE Text Index End').setValue(hi);
    adv.property('ADBE Text Selector Smoothness').setValue(0);
    return an;
}
function mqReviseReading(comp,I,rig) {
    var plan=I.reading_focus,source=comp.layer(plan.layer),st=source.property('Source Text'),d=st.valueAtTime(I.clip_start,false);
    var ink=d.characterRange(0,1).fillColor,blue=null,at=st.valueAtTime(plan.start+1/24,false);
    for(var k=0;k<at.text.length;k++){var color=at.characterRange(k,k+1).fillColor;if(Math.abs(color[0]-ink[0])+Math.abs(color[1]-ink[1])+Math.abs(color[2]-ink[2])>.05){blue=color;break;}}
    if(!blue)throw Error('Existing blue attention color not found');
    var aa=source.property('ADBE Text Properties').property('ADBE Text Animators');
    for(var j=aa.numProperties;j>=1;j--)if(aa.property(j).name.indexOf('RF_CHUNK_search_chunks_')===0)aa.property(j).remove();
    var keep=[];for(var j=0;j<rig.chunks.length;j++)if(rig.chunks[j].group!=='search_chunks')keep.push(rig.chunks[j]);rig.chunks=keep;
    // Existing held, line-wide blue would conflict with the moving block.
    // Override only its color in this search interval; source keys stay intact.
    var base=mqReadingSelector(source,'MQ_READING_NEUTRAL_BASE',0,d.text.length);
    base.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(ink);
    base.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount').expression='time>='+I.clip_start+'&&time<='+plan.end+'?100:0;';
    for(var j=0;j<plan.chunks.length;j++){
        var c=plan.chunks[j],line=d.composedLineRange(c.row,c.row+1);
        if(c.start<line.characterStart||c.end>line.characterEnd||d.text.slice(c.start,c.end)!==c.text)throw Error('Chunk no longer matches measured line');
        var name='RF_CHUNK_reading_line_'+c.row+'_'+j,an=mqReadingSelector(source,name,c.start,c.end),e=mqReadingEnvelope(c);
        an.property('ADBE Text Animator Properties').addProperty('ADBE Text Scale 3D').expression=e+'[100+4*a,100+4*a,100];';
        var colorAn=mqReadingSelector(source,'MQ_READING_COLOR_'+j,c.start,c.end);
        colorAn.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(blue);
        colorAn.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount').expression=e+'100*a;';
        rig.chunks.push({layer:source.name,animator:name,start:c.start,end:c.end,text:c.text,row:c.row,center:c.center,attack:c.attack,hold:c.hold,release:c.release,peak:104,group:'reading_line_chunks',expression:e+'[100+4*a,100+4*a,100];',colorAnimator:colorAn.name});
    }
    var query=comp.layer('CARRIED_QUERY_SC09L'),question=comp.layer('camp_QUESTION'),q=I.query_rejoin;
    var from=query.property('Source Text').value.characterRange(0,1).fillColor;
    var to=question.property('Source Text').valueAtTime(I.locator_scene.end,false).characterRange(I.locator_scene.locator.stem_span[0],I.locator_scene.locator.stem_span[0]+1).fillColor;
    var an=mqReadingSelector(query,'MQ_QUERY_REJOIN_COLOR',0,query.property('Source Text').value.text.length);
    var e='function s(x){x=Math.max(0,Math.min(1,x));return x*x*x*(x*(6*x-15)+10);}\nvar a=s((time-'+q.start+')/('+q.end+'-'+q.start+')),from='+JSON.stringify([from[0],from[1],from[2],1])+',to='+JSON.stringify([to[0],to[1],to[2],1])+';\nfrom*(1-a)+to*a;';
    an.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').expression=e;
    rig.reading_revision={measured_rows:plan.rows,chunks:plan.chunks,ink:ink,blue:blue,focus:'row-major, left-to-right; color and scale share one envelope',query_rejoin:{layer:query.name,animator:an.name,start:q.start,end:q.end,from:from,to:to,expression:e}};
    // Restore the source across the shutter interval before the clone ends.
    // A boundary-only switch can pass valueAtTime yet leave a rendered gap.
    // The clone is already at its exact source position during this overlap.
    var span=I.locator_scene.locator.stem_span,join=mqReadingSelector(question,'MQ_QUERY_REJOIN_SOURCE',span[0],span[1]);
    join.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').setValue(to);
    var joinTime=I.locator_scene.end-.5/24,joinExpr='time>='+joinTime+'&&time<='+I.last_source_time+'?100:0;';
    join.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount').expression=joinExpr;
    rig.reading_revision.source_rejoin={layer:question.name,animator:join.name,start:span[0],end:span[1],time:joinTime,original_handoff:I.locator_scene.end,color:to,expression:joinExpr};
    comp.layer('MQ_CAMERA_RIG').comment=JSON.stringify(rig);
    return rig;
}
