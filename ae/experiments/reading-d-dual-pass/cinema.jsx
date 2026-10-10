/* Presentation-only derivative. Original evidence comps and word objects survive. */
(function () {
    function load(path) { var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw Error('Missing bound input');var s=f.read();f.close();return JSON.parse(s); }
    var r=load(CINEMA_PLAN),folder=new File(CINEMA_PLAN).parent;
    if(!r.script_sha || !r.source_binding || !r.frame_mapping || !r.frame_mapping.length || Math.abs(r.duration*24-r.frame_mapping.length)>0.000001)throw Error('Exact binding and complete 24fps mapping required');
    for(var n=0;n<r.frame_mapping.length;n++){var f=r.frame_mapping[n];if(f!==Math.floor(f)||f<0||f>=2256 || (n && f<r.frame_mapping[n-1]))throw Error('Only ordered original frames and stationary holds permitted');}
    if(!r.captions || !r.captions.length)throw Error('Bound captions required');
    for(n=0;n<r.captions.length;n++){var c=r.captions[n];if(!c.text || !c.source_refs || !c.source_refs.length || c.start_frame<0 || c.end_frame<=c.start_frame || c.end_frame>r.frame_mapping.length)throw Error('Caption text, provenance and frame bounds required');}
    if(app.project.dirty || app.project.renderQueue.rendering)throw Error('Preserve native session');
    if(!app.project.file || app.project.file.fsName!==new File(r.owned_project).fsName)throw Error('Open isolated baseline copy');
    var target=new File(r.destination);if(target.exists)throw Error('Never overwrite a take');
    var old=null;
    for(var i=1;i<=app.project.numItems;i++){var x=app.project.item(i);if(x instanceof CompItem && x.name==='Q33_COMPLETE_DUAL_PASS_4K')old=x;}
    if(!old || old.width!==3840 || old.height!==2160 || old.frameRate!==24 || old.duration!==94)throw Error('Wrong native baseline');
    var comp=app.project.items.addComp('Q33_FIRST_PERSON_NARRATIVE_4K',3840,2160,1,r.duration,24);comp.renderer='ADBE Calder';
    comp.comment=JSON.stringify({script_sha:r.script_sha,source_binding:r.source_binding,public_render_ready:false,human_review:'PENDING'});
    var layer=comp.layers.add(old);layer.name='VERIFIED_NATIVE_OBJECT_LINEAGE';layer.timeRemapEnabled=true;layer.outPoint=r.duration;
    var remap=layer.property('ADBE Time Remapping');while(remap.numKeys>1)remap.removeKey(remap.numKeys);
    var times=[],values=[];for(i=0;i<r.frame_mapping.length;i++){times.push(i/24);values.push(r.frame_mapping[i]/24);}
    remap.setValuesAtTimes(times,values);for(i=1;i<=remap.numKeys;i++)remap.setInterpolationTypeAtKey(i,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);
    function cover(name,w,h,pos,a,b){var s=comp.layers.addSolid([248/255,247/255,242/255],name,w,h,1,r.duration);s.property('ADBE Transform Group').property('ADBE Position').setValue(pos);s.inPoint=a;s.outPoint=b;}
    cover('HIDE_HISTORICAL_SILENT_METADATA',350,80,[375,2040],0,r.duration);
    for(i=0;i<r.title_mask_times.length;i++)cover('OMIT_BRAND_BEFORE_PROOF_'+i,400,100,[675,265],r.title_mask_times[i][0],r.title_mask_times[i][1]);
    function wrap(s){if(s.length<=26)return s;var n=26;for(var j=25;j>=0;j--)if('，。？；：'.indexOf(s.charAt(j))>=0){n=j+1;break;}return s.slice(0,n)+'\r'+wrap(s.slice(n));}
    var checks=[];
    for(i=0;i<r.captions.length;i++){
        var row=r.captions[i],t=comp.layers.addText(wrap(row.text));t.name='BOUND_SCRATCH_CAPTION_'+row.id;t.inPoint=row.start_frame/24;t.outPoint=row.end_frame/24;
        var prop=t.property('ADBE Text Properties').property('ADBE Text Document'),d=prop.value;d.font='NotoSansSC-Regular';d.fontSize=64;d.fillColor=[40/255,44/255,46/255];d.applyFill=true;d.applyStroke=true;d.strokeColor=[1,1,1];d.strokeWidth=2;d.justification=ParagraphJustification.CENTER_JUSTIFY;d.autoLeading=false;d.leading=76;prop.setValue(d);
        var rect=t.sourceRectAtTime(t.inPoint,false);t.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([0,rect.top+rect.height]);t.property('ADBE Transform Group').property('ADBE Position').setValue([1920,r.caption_bottom || 2102]);
        t.comment=JSON.stringify({source_refs:row.source_refs,script_sha:r.script_sha,human_review:'PENDING'});checks.push({id:row.id,text:prop.value.text,font:prop.value.font,width:rect.width,height:rect.height});
    }
    var bad=0;for(i=0;i<r.frame_mapping.length;i++)if(Math.round(remap.valueAtTime(i/24,false)*24)!==r.frame_mapping[i])bad++;
    if(bad)throw Error('Native frame mapping changed');
    comp.openInViewer();comp.time=0;app.project.save(target);
    return JSON.stringify({project:target.fsName,comp_id:comp.id,source_comp_id:old.id,canvas:[3840,2160,24,comp.duration],remap_keys:remap.numKeys,frame_mapping_mismatches:bad,captions:checks,public_render_ready:false});
})();
