/* METHOD_DEMO_MASTER v0.1.0. One native AE template family; no method-ID branching.
   Invoked only through JUNKDOGE ae_exec. V8_CONTRACT_PATH and V8_PROJECT_PATH are explicit.
   Saves before edits; updates only the render_id's own composition. */
(function () {
    var file=new File(V8_CONTRACT_PATH); file.encoding='UTF-8';
    if(!file.open('r')) throw new Error('Render contract not readable');
    var rc=JSON.parse(file.read()); file.close();
    if(rc.usage!=='INTERNAL_ENGINEERING_PREVIEW'||rc.public_render_ready!==false) throw new Error('Internal-only template');
    if(rc.template_family!=='METHOD_DEMO_MASTER') throw new Error('Wrong template family');
    var ds=rc.design, colors=ds.colors, fonts=ds.typography, duration=rc.canvas.duration;
    function rgb(hex) { return [parseInt(hex.substr(1,2),16)/255,parseInt(hex.substr(3,2),16)/255,parseInt(hex.substr(5,2),16)/255]; }
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
            tr.property('ADBE Position').expression='var u=clamp((time-'+at+')/'+d+',0,1); var q=1-Math.pow(1-u,3); [value[0],value[1]+'+ds.motion.travel_px+'*(1-q)];';
            tr.property('ADBE Opacity').expression='var u=clamp((time-'+at+')/'+d+',0,1); 100*(1-Math.pow(1-u,3));';
        }
        rect('PAPER',0,0,1080,1920,colors.background,0,duration);
        rect('LEFT_RAIL',64,248,4,1208,colors.divider,0,duration);
        var methods=[]; for(var m=0;m<rc.methods.length;m++) methods.push(rc.methods[m].method_id+' / '+rc.methods[m].role);
        text('METHOD_TAG',methods.join(' + '),96,256,888,64,'Metadata',colors.secondary_text,0,duration);
        text('INTERNAL_ENGINEERING_PREVIEW','INTERNAL_ENGINEERING_PREVIEW',96,1744,888,48,'Metadata',colors.secondary_text,0,duration);
        text('TRACE','RENDER '+rc.render_id.split(':')[1].substr(0,12)+' / TEMPLATE '+rc.template_version,96,1792,888,48,'Metadata',colors.secondary_text,0,duration);
        if(rc.source_tags) text('SOURCE_TAG',rc.source_tags,96,1840,888,64,'Metadata',colors.secondary_text,0,duration);
        for(var i=0;i<rc.scenes.length;i++) {
            var scene=rc.scenes[i],start=scene.start,end=scene.end;
            text('PROGRESS_'+i,('0'+(i+1)).slice(-2)+' / '+scene.scene_type,96,320,888,48,'Metadata',colors.secondary_text,start,end);
            for(var j=0;j<scene.components.length;j++) {
                var c=scene.components[j],l=c.layout,kind=c.component_type,color=colors.primary_text;
                if(kind==='EVIDENCE_TEXT'||kind==='EVIDENCE_HIGHLIGHT') {
                    rect(c.component_id+'_EVIDENCE',l.x-16,l.y-8,l.width+32,fonts[c.style_token].leading*c.layout.lines.length+24,colors.evidence,start,end);
                }
                if(kind==='OPTION_CARD') {
                    rect(c.component_id+'_RULE',l.x-56,l.y-8,l.width+56,2,colors.divider,start,end);
                    text(c.component_id+'_ID',c.content.candidate,l.x-56,l.y,48,64,'Body',colors.secondary_text,start,end);
                }
                if(kind==='DECISION_PATH') {
                    rect(c.component_id+'_NODE',l.x-16,l.y-8,l.width+32,l.height,colors.divider,start,end);
                    if(c.content.terminal) rect(c.component_id+'_STOP',l.x-16,l.y+l.height, l.width+32,6,colors.valid,start,end);
                    else text(c.component_id+'_CONNECT','↓',480,l.y+l.height,96,72,'Body',colors.secondary_text,start,end);
                }
                if(kind==='STOP_RULE_CARD') { rect(c.component_id+'_BOUNDARY',l.x-16,l.y-8,6,fonts[c.style_token].leading*c.layout.lines.length+16,colors.valid,start,end); }
                if(kind==='RELATION_COMPARE' && c.content.chain_length) {
                    rect(c.component_id+'_RELATION',l.x,l.y+l.height,l.width,2,colors.divider,start,end);
                    if(c.content.column<c.content.chain_length-1) text(c.component_id+'_ARROW','→',l.x+l.width+4,l.y+64,44,80,'Body',colors.secondary_text,start,end);
                }
                if(kind==='CANDIDATE_VERDICT') color=colors.error_extra;
                var expr='var f=footage('+JSON.stringify(data.name)+'); var rc=f.sourceData || JSON.parse(f.sourceText); var c=rc.scenes['+i+'].components['+j+']; c.layout.lines.map(function(s){return s.replace(/\\n$/, "");}).join("\\r");';
                var copy=c.layout.lines.join('\r'),layer=text(c.component_id,copy,l.x,l.y,l.width,l.height,c.style_token,color,start,end,expr);
                layer.comment=JSON.stringify({component_id:c.component_id,source_refs:c.source_refs,type:kind});
                animate(layer,start,j,c.motion_primitive);
            }
        }
        rect('SUBTITLE_DIVIDER',96,1480,888,2,colors.divider,0,duration);
        for(var k=0;k<rc.subtitles.length;k++) {
            var cue=rc.subtitles[k];
            text(cue.cue_id,cue.lines.join('\r'),96,1520,888,160,'Subtitle',colors.primary_text,cue.start,cue.end,
                 'var f=footage('+JSON.stringify(data.name)+'); var rc=f.sourceData || JSON.parse(f.sourceText); rc.subtitles['+k+'].lines.join("\\r");');
        }
        comp.openInViewer(); comp.time=0;
        app.project.save(new File(V8_PROJECT_PATH));
        return JSON.stringify({ok:true,comp_id:String(comp.id),render_id:rc.render_id,package_id:rc.package_id,template_version:rc.template_version,layers:comp.numLayers,project:app.project.file.fsName});
    } finally { app.endUndoGroup(); }
})();
