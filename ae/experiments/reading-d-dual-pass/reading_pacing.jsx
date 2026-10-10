/* New editable timing/caption master; never mutate the historical source comp. */
(function () {
    function load(path) { var f = new File(path); f.encoding = 'UTF-8'; if (!f.open('r')) throw Error('Missing binding'); var s=f.read(); f.close(); return JSON.parse(s); }
    var R=load(READING_PACING_PLAN), folder=new File(READING_PACING_PLAN).parent;
    var recovering=typeof READING_RECOVERY!=='undefined' && READING_RECOVERY;
    if ((!recovering && app.project.dirty) || app.project.renderQueue.rendering) throw Error('Preserve current edits/render');
    var expected=R.baseline+'/Q33_COMPLETE_4K.aep';
    var destination=new File(folder.fsName+'/Q33_READABLE_4K_SUBTITLED.aep');
    if (!app.project.file || app.project.file.fsName !== (recovering?destination:new File(expected)).fsName) throw Error('Open bound baseline first');
    if (destination.exists && !recovering) throw Error('Never overwrite a take');
    var old=null;
    for(var i=1;i<=app.project.numItems;i++){var item=app.project.item(i);if(item instanceof CompItem && item.name==='Q33_COMPLETE_DUAL_PASS_4K') old=item;}
    if(!old || old.width!==3840 || old.height!==2160 || old.frameRate!==24 || old.duration!==94) throw Error('Bound baseline comp missing');
    var comp=null;
    if(recovering){for(i=1;i<=app.project.numItems;i++){item=app.project.item(i);if(item instanceof CompItem && item.name==='Q33_READABLE_SUBTITLED_4K')comp=item;}if(!comp || comp.numLayers!==1)throw Error('Recovery must reconcile the single partial timing layer');}
    else{app.project.save(destination);comp=app.project.items.addComp('Q33_READABLE_SUBTITLED_4K',3840,2160,1,R.duration,24);}
    comp.renderer='ADBE Calder';
    comp.comment=JSON.stringify({plan_sha:R.plan_sha,source_binding:R.source_binding,public_render_ready:false,human_review:'PENDING'});
    var layer=recovering?comp.layer(1):comp.layers.add(old);layer.name='UNCHANGED_NATIVE_PICTURE_WITH_READING_HOLDS';layer.timeRemapEnabled=true;layer.outPoint=R.duration;
    // Removing the final key disables time remapping in AE. Keep its first key.
    var remap=layer.property('ADBE Time Remapping');while(remap.numKeys>1)remap.removeKey(remap.numKeys);
    var times=[],values=[];
    for(i=0;i<R.frame_mapping.length;i++){times.push(i/24);values.push(R.frame_mapping[i]/24);}
    remap.setValuesAtTimes(times,values);
    for(i=1;i<=remap.numKeys;i++)remap.setInterpolationTypeAtKey(i,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);
    var checks=[];
    function wrap(s){ if(s.length<=26)return s;var cut=26;for(var n=25;n>=0;n--)if('，。？；：'.indexOf(s.charAt(n))>=0){cut=n+1;break;}return s.slice(0,cut)+'\r'+wrap(s.slice(cut)); }
    for(i=0;i<R.captions.length;i++){
        var r=R.captions[i],text=comp.layers.addText(wrap(r.text));text.name='REVIEW_CAPTION_'+(i+1);
        text.inPoint=r.start_frame/24;text.outPoint=r.end_frame/24;
        var doc=text.property('ADBE Text Properties').property('ADBE Text Document'),d=doc.value;
        d.font='NotoSansSC-Regular';d.fontSize=64;d.applyFill=true;d.fillColor=[40/255,44/255,46/255];d.applyStroke=true;d.strokeColor=[1,1,1];d.strokeWidth=2;d.strokeOverFill=false;d.justification=ParagraphJustification.CENTER_JUSTIFY;d.autoLeading=false;d.leading=76;doc.setValue(d);
        var bounds=text.sourceRectAtTime(text.inPoint,false);
        text.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([0,bounds.top+bounds.height]);
        text.property('ADBE Transform Group').property('ADBE Position').setValue([1920,2102]);
        text.comment=JSON.stringify({text_sha:r.text_sha,segment_ref:r.segment_ref,source_span:r.source_span,review:'PENDING'});
        checks.push({text:doc.value.text,font:doc.value.font,bounds:[bounds.left,bounds.top,bounds.width,bounds.height],in_point:text.inPoint,out_point:text.outPoint});
    }
    comp.openInViewer();comp.time=0;app.project.save();
    return JSON.stringify({project:destination.fsName,comp_id:comp.id,source_comp_id:old.id,canvas:[3840,2160,24,comp.duration],remap_keys:remap.numKeys,captions:checks,public_render_ready:false});
})();
