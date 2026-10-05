/* METHOD_DEMO_MASTER v0.2.0. Same native template family, editorial visual revision.
   Invoked only through JUNKDOGE ae_exec. V8_CONTRACT_PATH and V8_PROJECT_PATH are explicit.
   Saves before edits; updates only the render_id's own composition. */
(function () {
    var file=new File(V8_CONTRACT_PATH); file.encoding='UTF-8';
    if(!file.open('r')) throw new Error('Render contract not readable');
    var rc=JSON.parse(file.read()); file.close();
    if(rc.usage!=='INTERNAL_ENGINEERING_PREVIEW'||rc.public_render_ready!==false) throw new Error('Internal-only template');
    if(rc.template_family!=='METHOD_DEMO_MASTER') throw new Error('Wrong template family');
    if(rc.template_version!=='0.2.0'||rc.design_system_version!=='0.2.0') throw new Error('Wrong visual version');
    var ds=rc.design, colors=ds.colors, fonts=ds.typography, duration=rc.canvas.duration;
    var core=rc.actual_content_area,caption=rc.platform_profile.caption_profile,labels=ds.localized_labels;
    function rgb(hex) { return [parseInt(hex.substr(1,2),16)/255,parseInt(hex.substr(3,2),16)/255,parseInt(hex.substr(5,2),16)/255]; }
    function tint(hex,amount) {var a=rgb(hex),b=rgb(colors.background),s='#';for(var k=0;k<3;k++){var v=Math.round(255*(a[k]*amount+b[k]*(1-amount))).toString(16);s+=(v.length<2?'0':'')+v;}return s;}
    function growRule(layer,x,y,w,h,at,frames) {
        var p=layer.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Rect');
        var u='var u=clamp((time-'+at+')/'+((frames||12)/30)+',0,1);var q=1-Math.pow(1-u,3);';
        p.property('ADBE Vector Rect Size').expression=u+'['+w+'*q,'+h+'];';
        p.property('ADBE Vector Rect Position').expression=u+'['+x+'+'+w+'*q/2,'+(y+h/2)+'];';
    }
    var name='METHOD_DEMO_MASTER_'+rc.render_id.split(':')[1].substr(0,12), comp=null, data;
    // Preserve any user project and unrelated compositions. No app.newProject / blanket removals.
    if(app.project.file) app.project.save();
    app.beginUndoGroup('Video OS internal preview '+rc.render_id);
    try {
        var bin=null;
        for(var n=1;n<=app.project.numItems;n++) { var it=app.project.item(n); if(it instanceof FolderItem&&it.name==='VIDEO_OS_V8') bin=it; }
        if(!bin) bin=app.project.items.addFolder('VIDEO_OS_V8');
        for(var n=app.project.numItems;n>=1;n--) { var it=app.project.item(n); if(it instanceof CompItem&&it.name===name) { comp=it; break; } }
        if(comp) { while(comp.numLayers) comp.layer(1).remove(); comp.duration=duration; }
        else comp=app.project.items.addComp(name,1080,1920,1,duration,30);
        comp.parentFolder=bin; comp.bgColor=rgb(colors.background); comp.comment=JSON.stringify({render_id:rc.render_id,package_id:rc.package_id,template_version:rc.template_version,package_sha:rc.package_sha});
        data=app.project.importFile(new ImportOptions(file)); data.name='RC_'+rc.render_id.split(':')[1].substr(0,12); data.parentFolder=bin;
        var dataLayer=comp.layers.add(data); dataLayer.name='RENDER_CONTRACT'; dataLayer.enabled=false;
        function rect(label,x,y,w,h,color,start,end) {
            var layer=comp.layers.addShape(); layer.name=label; layer.inPoint=start; layer.outPoint=end;
            var group=layer.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
            var contents=group.property('ADBE Vectors Group');
            var shape=contents.addProperty('ADBE Vector Shape - Rect'); shape.property('ADBE Vector Rect Size').setValue([w,h]);
            shape.property('ADBE Vector Rect Position').setValue([x+w/2,y+h/2]);
            var fill=contents.addProperty('ADBE Vector Graphic - Fill'); fill.property('ADBE Vector Fill Color').setValue(rgb(color));
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([0,0]);
            return layer;
        }
        function text(label,value,x,y,w,h,token,color,start,end,expression) {
            var layer=comp.layers.addBoxText([w,h]); layer.name=label; layer.inPoint=start; layer.outPoint=end;
            var prop=layer.property('ADBE Text Properties').property('ADBE Text Document'), doc=prop.value;
            doc.text=value; doc.font=ds.font.postscript; doc.fontSize=fonts[token].size;
            doc.applyFill=true; doc.fillColor=rgb(color); doc.applyStroke=false;
            doc.justification=ParagraphJustification.LEFT_JUSTIFY; doc.autoLeading=false; doc.leading=fonts[token].leading;
            doc.tracking=fonts[token].tracking||0;
            prop.setValue(doc);
            layer.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([0,0]);
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([x,y]);
            if(expression) prop.expression=expression;
            var measured=layer.sourceRectAtTime((start+end)/2,false);
            layer.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([measured.left,measured.top]);
            return layer;
        }
        function animate(layer,start,index,primitive) {
            var tr=layer.property('ADBE Transform Group'); var delay=index*primitive.delay_frames/30;
            var d=primitive.duration_frames/30; var at=start+delay;
            // Deliberate ease-out, no bounce; a static anchor remains throughout each shot.
            if(primitive.type==='compare')
                tr.property('ADBE Position').expression='var u=clamp((time-'+at+')/'+d+',0,1); var q=1-Math.pow(1-u,3); [value[0]+'+ds.motion.travel_px+'*(1-q),value[1]];';
            else if(primitive.type!=='focus'&&primitive.type!=='eliminate')
                tr.property('ADBE Position').expression='var u=clamp((time-'+at+')/'+d+',0,1); var q=1-Math.pow(1-u,3); [value[0],value[1]+'+ds.motion.travel_px+'*(1-q)];';
            tr.property('ADBE Opacity').expression='var u=clamp((time-'+at+')/'+d+',0,1); 100*(1-Math.pow(1-u,3));';
        }
        rect('PAPER',0,0,1080,1920,colors.background,0,duration);
        var methods=[]; for(var m=0;m<rc.methods.length;m++) methods.push(rc.methods[m].brand+' · '+rc.methods[m].method_id+' / '+rc.methods[m].role);
        text('METHOD_TAG',methods.join(' + '),core[0],256,core[2]-144,64,'Metadata',colors.secondary_text,0,duration);
        // Debug/provenance is confined to the footer, independent of editorial body geometry.
        text('INTERNAL_ENGINEERING_PREVIEW','INTERNAL_ENGINEERING_PREVIEW',96,1744,888,48,'Metadata',colors.secondary_text,0,duration);
        text('TRACE','RENDER '+rc.render_id.split(':')[1].substr(0,12)+' / TEMPLATE '+rc.template_version,96,1792,888,48,'Metadata',colors.secondary_text,0,duration);
        if(rc.source_tags) text('SOURCE_TAG',rc.source_tags,96,1840,888,64,'Metadata',colors.secondary_text,0,duration);
        for(var i=0;i<rc.scenes.length;i++) {
            var scene=rc.scenes[i],start=scene.start,end=scene.end;
            text('PROGRESS_'+i,('0'+(i+1)).slice(-2)+' / '+('0'+rc.scenes.length).slice(-2),core[0]+core[2]-112,256,112,48,'Metadata',colors.secondary_text,start,end);
            for(var j=0;j<scene.components.length;j++) {
                var c=scene.components[j],l=c.layout,kind=c.component_type,color=colors.primary_text;
                var phase=start,phaseIndex=j;
                if(kind==='OPTION_CARD'){phase=start+0.8+(j-1)*0.25;phaseIndex=0;}
                if(kind==='DECISION_PATH'){phase=start+j*ds.motion.node_interval_seconds;phaseIndex=0;}
                if(kind==='RELATION_COMPARE'&&c.content.chain_length){phase=start+(c.content.row===1?ds.motion.relation_candidate_delay_seconds:0)+c.content.column*0.35;phaseIndex=0;}
                if(kind==='CANDIDATE_VERDICT'){phase=start+ds.motion.relation_verdict_delay_seconds;phaseIndex=0;}
                if(kind==='EVIDENCE_TEXT'||kind==='EVIDENCE_HIGHLIGHT') {
                    rect(c.component_id+'_EVIDENCE',l.x-16,l.y-16,l.width+32,fonts[c.style_token].leading*c.layout.lines.length+24,tint(colors.evidence,ds.treatment.evidence_tint),start,end);
                    var er=rect(c.component_id+'_EVIDENCE_RULE',l.x,l.y-32,l.width,3,colors.evidence,start,end);
                    growRule(er,l.x,l.y-32,l.width,3,start+0.3,16);
                }
                if(kind==='OPTION_GROUP_GRID') {
                    var universe=[];for(var gr=0;gr<c.content.groups.length;gr++)universe=universe.concat(c.content.groups[gr].candidates);
                    text(c.component_id+'_UNIVERSE',universe.join('   '),l.x,l.y+l.height+16,l.width,64,'Body',colors.primary_text,start,end);
                    var groupRule=rect(c.component_id+'_GROUP',l.x,l.y+l.height+80,l.width,2,colors.divider,start,end);
                    growRule(groupRule,l.x,l.y+l.height+80,l.width,2,start+0.4);
                }
                if(kind==='OPTION_CARD') {
                    var align=rect(c.component_id+'_RULE',l.x-56,l.y-8,l.width+56,2,colors.divider,start,end);
                    growRule(align,l.x-56,l.y-8,l.width+56,2,phase,12);
                    var id=text(c.component_id+'_ID',c.content.candidate,l.x-56,l.y,48,64,'Body',colors.primary_text,start,end);
                    animate(id,phase,0,c.motion_primitive);
                }
                if(kind==='DECISION_PATH') {
                    if(c.content.terminal) {
                        var sr=rect(c.component_id+'_STOP',core[0],l.y+l.height+24,core[2],4,colors.valid,start,end);
                        growRule(sr,core[0],l.y+l.height+24,core[2],4,phase+0.4,16);
                        text(c.component_id+'_TERMINAL',labels.stop,l.x,l.y+l.height+64,l.width,64,'Metadata',colors.primary_text,phase+0.4,end);
                    } else {
                        var connector=text(c.component_id+'_CONNECT','↓',l.x,l.y+l.height+8,64,48,'Metadata',colors.secondary_text,start,end);
                        animate(connector,phase+0.3,0,c.motion_primitive);
                    }
                }
                if(kind==='STOP_RULE_CARD') {
                    var boundary=rect(c.component_id+'_BOUNDARY',core[0],400,core[2],4,colors.valid,start,end);
                    growRule(boundary,core[0],400,core[2],4,start,16);
                    text(c.component_id+'_TERMINAL',labels.stop,l.x,440,l.width,48,'Metadata',colors.primary_text,start,end);
                }
                if(kind==='RELATION_COMPARE' && c.content.chain_length) {
                    text(c.component_id+'_SLOT',labels.relation_slots[c.content.column],l.x,l.y-72,l.width,48,'Metadata',colors.secondary_text,phase,end);
                    var relation=rect(c.component_id+'_RELATION',l.x,l.y-16,l.width,2,colors.divider,start,end);
                    growRule(relation,l.x,l.y-16,l.width,2,phase,12);
                    if(c.content.column<c.content.chain_length-1){
                        var arrow=text(c.component_id+'_ARROW','→',l.x+l.width+2,l.y+68,32,48,'Metadata',c.content.row===1?colors.error_extra:colors.secondary_text,start,end);
                        animate(arrow,phase+0.35,0,{type:'connect',duration_frames:12,delay_frames:0});
                        if(c.content.row===1)arrow.transform.position.expression='var u=clamp((time-'+(phase+1.0)+')/0.4,0,1);var q=1-Math.pow(1-u,3);[value[0],value[1]+'+ds.motion.micro_alignment_px+'*q];';
                    }
                }
                if(kind==='CANDIDATE_VERDICT') {
                    var br=rect(c.component_id+'_LOCAL',l.x,1264,152,4,colors.error_extra,start,end);
                    growRule(br,l.x,1264,152,4,phase,8);
                    if(c.content.effect==='eliminate'&&c.content.whole_question_answer===false){
                        var local=text(c.component_id+'_LOCAL_LABEL',labels.local_eliminate+' '+c.content.candidate,l.x,1280,l.width,64,'Body',colors.primary_text,start,end);
                        animate(local,phase,0,{type:'eliminate',duration_frames:8,delay_frames:0});
                    }
                }
                var expr='var f=footage('+JSON.stringify(data.name)+'); var rc=f.sourceData || JSON.parse(f.sourceText); var c=rc.scenes['+i+'].components['+j+']; c.layout.lines.map(function(s){return s.replace(/\\n$/, "");}).join("\\r");';
                var copy=c.layout.lines.join('\r'),layer=text(c.component_id,copy,l.x,l.y,l.width,l.height,c.style_token,color,start,end,expr);
                layer.comment=JSON.stringify({component_id:c.component_id,source_refs:c.source_refs,type:kind});
                // A Stop closes and settles; the full boundary copy stays still for reading.
                if(kind!=='STOP_RULE_CARD')animate(layer,phase,phaseIndex,c.motion_primitive);
            }
        }
        for(var k=0;k<rc.subtitles.length;k++) {
            var cue=rc.subtitles[k];
            text(cue.cue_id,cue.lines.join('\r'),caption.x,caption.y,caption.width,caption.height,'Subtitle',colors.secondary_text,cue.start,cue.end,
                 'var f=footage('+JSON.stringify(data.name)+'); var rc=f.sourceData || JSON.parse(f.sourceText); rc.subtitles['+k+'].lines.join("\\r");');
        }
        comp.openInViewer(); comp.time=0;
        app.project.save(new File(V8_PROJECT_PATH));
        return JSON.stringify({ok:true,comp_id:String(comp.id),render_id:rc.render_id,package_id:rc.package_id,template_version:rc.template_version,layers:comp.numLayers,project:app.project.file.fsName});
    } finally { app.endUndoGroup(); }
})();
