// Experimental, opt-in native rig. No production template or teaching parser.
// Exact object spans and authority must be supplied by the current checked plan.
function rfSmoothExpression(knots) {
    // Quintic Hermite segments: position, velocity and acceleration agree at
    // joins. Velocities are world units / second; acceleration is zero here.
    return 'var K=' + JSON.stringify(knots) + ';\n' +
      'function mix5(a,b,t){var d=b[0]-a[0],u=(t-a[0])/d,u2=u*u,u3=u2*u,u4=u3*u,u5=u4*u;var h0=1-10*u3+15*u4-6*u5,h1=u-6*u3+8*u4-3*u5,h2=10*u3-15*u4+6*u5,h3=-4*u3+7*u4-3*u5;var out=[];for(var j=0;j<a[1].length;j++)out.push(h0*a[1][j]+h1*d*a[2][j]+h2*b[1][j]+h3*d*b[2][j]);return out;}\n' +
      'var out=K[0][1];if(time>=K[K.length-1][0])out=K[K.length-1][1];else for(var i=0;i<K.length-1;i++){if(time>=K[i][0]&&time<K[i+1][0]){out=mix5(K[i],K[i+1],time);break;}}out;';
}
function rfCurve(property, knots, rig, name) {
    property.expression=rfSmoothExpression(knots);
    rig.curves.push({name:name,property:property.matchName,knots:knots,expression:property.expression,continuity:'C2',units:'world units / seconds'});
}
function rfChunkPulse(layer, lo, hi, center, attack, release, rig, group) {
    var txt=layer.property('ADBE Text Properties');
    txt.property('ADBE Text More Options').property('ADBE Text Anchor Point Option').setValue(2);
    var anim=txt.property('ADBE Text Animators').addProperty('ADBE Text Animator');
    anim.name='RF_CHUNK_'+group+'_'+rig.chunks.length;
    var sel=anim.property('ADBE Text Selectors').addProperty('ADBE Text Selector');
    var adv=sel.property('ADBE Text Range Advanced');
    adv.property('ADBE Text Range Units').setValue(2);
    sel.property('ADBE Text Index Start').setValue(lo);
    sel.property('ADBE Text Index End').setValue(hi);
    adv.property('ADBE Text Selector Smoothness').setValue(0);
    var p=anim.property('ADBE Text Animator Properties').addProperty('ADBE Text Scale 3D');
    p.expression='function s(u){u=Math.max(0,Math.min(1,u));return u*u*u*(u*(6*u-15)+10);}\nvar a=s((time-('+center+'-'+attack+'))/'+attack+')*s((('+center+'+'+release+')-time)/'+release+');\n[100+4*a,100+4*a,100];';
    rig.chunks.push({layer:layer.name,animator:anim.name,start:lo,end:hi,text:layer.property('Source Text').value.text.slice(lo,hi),center:center,attack:attack,release:release,peak:104,group:group,expression:p.expression});
}
function rfChunkSequence(layer, chunks, start, end, rig, group) {
    var original=layer.property('Source Text').value.text,ranges=[],prior=-1;
    // Author-supplied exact visual chunks, not a linguistic/teaching parser.
    for(var i=0;i<chunks.length;i++){
        var base=original.indexOf(chunks[i]);
        if(base<0||base<prior||original.indexOf(chunks[i],base+1)>=0)throw Error('Expected one ordered exact chunk: '+group);
        ranges.push({start:base,end:base+chunks[i].length});prior=base+chunks[i].length;
    }
    var attack=.24,release=.32,first=start+attack,last=end-release;
    if(!ranges.length||last<first)throw Error('Insufficient chunk-focus time');
    for(var i=0;i<ranges.length;i++)rfChunkPulse(layer,ranges[i].start,ranges[i].end,ranges.length===1?(first+last)/2:first+(last-first)*i/(ranges.length-1),attack,release,rig,group);
}
function rfTemporal(property, time, inInfluence, outInfluence) {
    var k=property.nearestKeyIndex(time),v=property.keyValue(k),spatial=property.propertyValueType===PropertyValueType.ThreeD_SPATIAL||property.propertyValueType===PropertyValueType.TwoD_SPATIAL;
    var dims=spatial?1:(v instanceof Array?v.length:1),a=[],b=[];
    for(var i=0;i<dims;i++){a.push(new KeyframeEase(0,inInfluence));b.push(new KeyframeEase(0,outInfluence));}
    property.setTemporalEaseAtKey(k,a,b);
    property.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
}
