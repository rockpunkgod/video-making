/* V9 CINEMATIC_LANDSCAPE_MASTER. Official JUNKDOGE ae_exec only.
   V9_CONTRACT_PATH and V9_PROJECT_PATH are explicit. No teaching inference. */
(function () {
    var file=new File(V9_CONTRACT_PATH);file.encoding='UTF-8';
    if(!file.open('r'))throw new Error('Landscape contract missing');
    var rc=JSON.parse(file.read());file.close();
    if(rc.usage!=='INTERNAL_CREATIVE_PREVIEW'||rc.public_render_ready!==false||rc.template_version!=='0.3.0')throw new Error('Internal landscape only');
    var plan=rc.shot_plan,ds=plan.design,colors=ds.colors,fps=rc.canvas.fps;
    function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    function smooth(at,seconds){return 'var u=clamp((time-'+at+')/'+seconds+',0,1);var q=u*u*(3-2*u);';}
    function out(at,seconds){return 'var u=clamp((time-'+at+')/'+seconds+',0,1);var q=1-Math.pow(1-u,3);';}
    app.beginUndoGroup('V9 landscape '+rc.render_id);
    try {
        var bin=null,cp=null,name='CINEMATIC_LANDSCAPE_'+rc.render_id.split(':')[1].substr(0,12);
        for(var i=1;i<=app.project.numItems;i++){var it=app.project.item(i);if(it instanceof FolderItem&&it.name==='VIDEO_OS_V9')bin=it;if(it instanceof CompItem&&it.name===name)cp=it;}
        if(!bin)bin=app.project.items.addFolder('VIDEO_OS_V9');
        if(cp)throw new Error('Render identity already built; use new revision');
        cp=app.project.items.addComp(name,1920,1080,1,rc.canvas.duration,24);cp.parentFolder=bin;cp.bgColor=rgb(colors.background);
        cp.motionBlur=true;cp.shutterAngle=ds.motion.shutter_angle;cp.shutterPhase=ds.motion.shutter_phase;
        cp.comment=JSON.stringify({render_id:rc.render_id,package_id:rc.package_id,package_sha:rc.package_sha,delivery_sha:rc.delivery_sha,template_version:rc.template_version});
        var data=app.project.importFile(new ImportOptions(file));data.name='V9_RC_'+rc.render_id.split(':')[1].substr(0,12);data.parentFolder=bin;
        var dl=cp.layers.add(data);dl.name='RENDER_CONTRACT';dl.enabled=false;dl.shy=true;
        var audio=app.project.importFile(new ImportOptions(new File(rc.audio.path)));audio.name='SCRATCH_VOICE_'+rc.render_id.split(':')[1].substr(0,12);audio.parentFolder=bin;
        var al=cp.layers.add(audio);al.name='INTERNAL_SCRATCH_VOICE';al.startTime=0;al.inPoint=0;al.outPoint=rc.canvas.duration;al.audioEnabled=true;
        function rect(name,x,y,w,h,color,start,end){
            var l=cp.layers.addShape();l.name=name;l.inPoint=start;l.outPoint=end;l.transform.position.setValue([0,0]);
            var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
            var r=g.addProperty('ADBE Vector Shape - Rect');r.property('ADBE Vector Rect Size').setValue([w,h]);r.property('ADBE Vector Rect Position').setValue([x+w/2,y+h/2]);
            var f=g.addProperty('ADBE Vector Graphic - Fill');f.property('ADBE Vector Fill Color').setValue(rgb(color));return l;
        }
        function line(name,x,y,w,color,start,end,at,seconds){
            var l=rect(name,x,y,w,3,color,start,end),p=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Rect');
            var expression=out(at,seconds||.5);p.property('ADBE Vector Rect Size').expression=expression+'['+w+'*q,3];';
            p.property('ADBE Vector Rect Position').expression=expression+'['+x+'+'+w+'*q/2,'+(y+1.5)+'];';return l;
        }
        function txt(name,copy,x,y,w,h,token,color,start,end,expression){
            var l=cp.layers.addBoxText([w,h]);l.name=name;l.inPoint=start;l.outPoint=end;
            var p=l.property('Source Text'),d=p.value;d.text=copy.replace(/\n/g,'');d.font=ds.font.postscript;d.fontSize=ds.typography[token].size;
            d.autoLeading=false;d.leading=ds.typography[token].leading;d.fillColor=rgb(color);d.applyFill=true;d.applyStroke=false;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);
            // Explicit top-left paragraph anchoring, independently audited after composition.
            var r=l.sourceRectAtTime((start+end)/2,false);l.transform.anchorPoint.setValue([r.left,r.top]);l.transform.position.setValue([x,y]);
            if(expression)p.expression=expression;l.motionBlur=false;return l;
        }
        rect('PAPER',0,0,1920,1080,colors.background,0,cp.duration);
        txt('METHOD_TAG',rc.method_tags,144,96,1400,48,'Metadata',colors.secondary_text,0,cp.duration);
        txt('TRACE','INTERNAL_CREATIVE_PREVIEW / SCRATCH VO / '+rc.render_id.split(':')[1].substr(0,12),144,1044,1632,32,'Metadata',colors.secondary_text,0,cp.duration);
        for(var i=0;i<plan.shots.length;i++){
            var shot=plan.shots[i],start=shot.start,end=shot.end,st=shot.structure;
            txt('SHOT_'+i,('0'+(i+1)).slice(-2)+' / '+('0'+plan.shots.length).slice(-2),1664,96,112,48,'Metadata',colors.secondary_text,start,end);
            for(var j=0;j<shot.components.length;j++){
                var c=shot.components[j],l=c.layout;
                var expression='var f=footage('+JSON.stringify(data.name)+');var r=f.sourceData||JSON.parse(f.sourceText);r.shot_plan.shots['+i+'].components['+j+'].layout.lines.join("\\r").replace(/\\n/g,"");';
                var layer=txt(c.component_id,l.lines.join('\r'),l.x,l.y,l.width,l.height,l.style_token,colors.primary_text,start,end,expression);
                layer.comment=JSON.stringify({component_id:c.component_id,unit_id:shot.unit_id,source_claim_refs:c.source_claim_refs,evidence_refs:c.evidence_refs,motion:c.motion});
                var phase=start;
                if(st&&st.kind==='regroup'&&c.component_id.indexOf(':candidate:')!==-1){
                    var id=c.component_id.split(':').pop(),card=null;for(var k=0;k<st.cards.length;k++)if(st.cards[k].candidate===id)card=st.cards[k];
                    layer.transform.position.expression=smooth(start+card.start_offset,1)+'['+card.from[0]+'+('+card.to[0]+'-'+card.from[0]+')*q,'+card.from[1]+'+('+card.to[1]+'-'+card.from[1]+')*q];';
                    layer.motionBlur=true;
                }else if(st&&st.kind==='routing'&&c.component_id.indexOf(':node:')!==-1){
                    var id=c.component_id.split(':').pop(),node=null;for(var k=0;k<st.nodes.length;k++)if(st.nodes[k].node_id===id)node=st.nodes[k];
                    phase=start+node.activation_offset;
                    layer.transform.position.expression=out(phase,.5)+'[value[0]-32*(1-q),value[1]];';
                    layer.motionBlur=true;layer.transform.opacity.expression=out(phase,.25)+'100*q;';
                }else if(st&&st.kind==='rewire'&&c.component_id.indexOf(':relation:')!==-1){
                    var parts=c.component_id.split(':'),row=parseInt(parts[parts.length-2],10),col=parseInt(parts[parts.length-1],10),cell=null;
                    for(var k=0;k<st.cells.length;k++)if(st.cells[k].row===row&&st.cells[k].column===col)cell=st.cells[k];
                    phase=start+cell.entry_offset;
                    layer.transform.position.expression=smooth(phase,.8)+'[value[0],'+cell.from_y+'+('+cell.y+'-'+cell.from_y+')*q];';
                    layer.motionBlur=row===1;layer.transform.opacity.expression=out(phase,.2)+'100*q;';
                }else{
                    if(c.motion.mode==='after_settle')phase=start+2.2;
                    layer.transform.opacity.expression=out(phase,.25)+'100*q;';
                }
                if(c.motion.mode==='evidence_focus'){
                    var er=line(c.component_id+'_FOCUS',l.x,l.y-28,l.width,colors.evidence,start,end,start+.35,.75);
                    // Editorial depth by foreground rule and quiet evidence, no filter or heavy shadow.
                }
            }
            if(st&&st.kind==='regroup'){
                line(shot.shot_id+'_GROUP_LOCK',144,864,1632,colors.divider,start,end,start+2.15,.5);
            }
            if(st&&st.kind==='routing'){
                for(var k=0;k<st.nodes.length-1;k++)line(shot.shot_id+'_ROUTE_'+k,st.nodes[k].x+280,730,140,colors.evidence,start,end,start+st.nodes[k+1].activation_offset,.5);
                var terminal=st.nodes[st.nodes.length-1];
                line(shot.shot_id+'_TERMINAL_LOCK',terminal.x,736,360,colors.valid,start,end,start+3.25,.5);
                var cap=rect(shot.shot_id+'_FORWARD_SPACE_CLOSED',1772,448,4,320,colors.valid,start,end);
                cap.transform.opacity.expression=out(start+3.25,.35)+'100*q;';
                // Deliberately no outgoing connector, new branch or answer object.
            }
            if(st&&st.kind==='rewire'){
                for(var k=0;k<3;k++)txt(shot.shot_id+'_SLOT_'+k,st.slot_labels[k],144+k*560,344,512,40,'Metadata',colors.secondary_text,start,end);
                for(var k=0;k<2;k++)line(shot.shot_id+'_SOURCE_CONNECT_'+k,400+k*560,596,300,colors.evidence,start,end,start+.7+k*.3,.5);
                var edge=line(shot.shot_id+'_CANDIDATE_REWIRE',400,832,300,colors.error,start,end,start+3.25,.5);
                edge.transform.position.expression=out(start+st.shift_offset,.6)+'[6*q,-6*q];';edge.motionBlur=true;
            }
            if(shot.intent==='stop'||shot.intent==='boundary'){
                var close=line(shot.shot_id+'_STOP_LOCK',144,248,1632,colors.valid,start,end,start,.5);
                // Settled boundary replaces the active graph. Caption silence is retained in the audio track.
            }
        }
        for(var k=0;k<plan.captions.length;k++){
            var cue=plan.captions[k];
            txt(cue.cue_id,cue.lines.join('\r'),192,916,1536,120,'Subtitle',colors.secondary_text,cue.start,cue.end,
                'var f=footage('+JSON.stringify(data.name)+');var r=f.sourceData||JSON.parse(f.sourceText);r.shot_plan.captions['+k+'].lines.join("\\r");');
        }
        cp.openInViewer();cp.time=0;app.project.save(new File(V9_PROJECT_PATH));
        return JSON.stringify({ok:true,render_id:rc.render_id,package_id:rc.package_id,comp_id:String(cp.id),layers:cp.numLayers,template_version:rc.template_version,project:app.project.file.fsName});
    }finally{app.endUndoGroup();}
})();
