// Presentation only. All words and decisions come from the bound PLAN.
function transition_to_dark_field(background, originals, world, config) {
    SG_keys(background, config.background, false);
    SG_keys(world.transform.position, config.depth, false);
    for (var i=0;i<originals.length;i++) {
        SG_keys(originals[i].color, config.originalColor, false);
        SG_keys(originals[i].blur, config.blur, false);
    }
}
function lift_phrase(originals, highlight, config) {
    SG_locate(highlight, config.locate, config.locateFrames, 24);
    var result=[];
    for (var i=0;i<originals.length;i++) {
        var l=originals[i].duplicate();l.parent=null;l.name=config.name+'_'+i;
        while(l.property('ADBE Text Properties').property('ADBE Text Animators').numProperties)
            l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).remove();
        while(l.property('ADBE Effect Parade').numProperties)l.property('ADBE Effect Parade').property(1).remove();
        l.inPoint=config.start;l.outPoint=config.end;
        var tr=config.tracks[i];
        SG_keys(l.transform.position,tr.position,false);SG_keys(l.transform.scale,tr.scale,false);
        SG_keys(l.transform.opacity,tr.opacity,false);
        var a=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');
        a.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');
        // A gray-to-gray crossfade erases the moving glyph mid-transition.
        // Switch foreground polarity at the field crossover; motion stays eased.
        SG_keys(a.property('ADBE Text Animator Properties').property('ADBE Text Fill Color'),config.color,true);
        l.comment=JSON.stringify({origin_layer:originals[i].id,source:originals[i].comment});result.push(l);
    }
    return result;
}
