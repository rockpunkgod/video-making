/* V9.1 bounded Hero, declarative native AE graphics. Official ae_exec only.
   H_CONTRACT_PATH and H_PROJECT_PATH are explicit frozen local inputs. */
(function () {
    var f=new File(H_CONTRACT_PATH);f.encoding='UTF-8';
    if(!f.open('r'))throw new Error('Missing hero contract');
    var rc=JSON.parse(f.read());f.close();
    if(rc.version!=='0.4.0'||rc.public_render_ready!==false||rc.usage!=='INTERNAL_CREATIVE_PREVIEW')throw new Error('Internal hero contract required');
    var project=new File(H_PROJECT_PATH);
    if(!app.project.file||app.project.file.fsName!==project.fsName)throw new Error('Detach/save the new project before building');
    var name='HERO_'+rc.render_contract_sha.substr(0,12);
    for(var j=1;j<=app.project.numItems;j++)if(app.project.item(j).name===name)throw new Error('Identity already built; inspect instead of retrying');
    function color(hex){return [parseInt(hex.substr(1,2),16)/255,parseInt(hex.substr(3,2),16)/255,parseInt(hex.substr(5,2),16)/255];}
    function keys(p,values){
        if(!values)return;
        for(var i=0;i<values.length;i++){
            var value=values[i][1];
            if(p.propertyValueType===PropertyValueType.ThreeD&&value instanceof Array&&value.length===2)value=[value[0],value[1],100];
            p.setValueAtTime(values[i][0],value);
        }
        for(var i=1;i<=p.numKeys;i++){
            var ease=[],count=(p.propertyValueType===PropertyValueType.TwoD)?2:(p.propertyValueType===PropertyValueType.ThreeD?3:1);
            for(var k=0;k<count;k++)ease.push(new KeyframeEase(0,70));
            p.setTemporalEaseAtKey(i,ease,ease);
            p.setInterpolationTypeAtKey(i,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
            if(p.isSpatial){var tangent=p.value.length===3?[0,0,0]:[0,0];p.setSpatialAutoBezierAtKey(i,false);p.setSpatialTangentsAtKey(i,tangent,tangent);}
        }
    }
    app.beginUndoGroup('V9.1 Hero '+rc.render_contract_sha.substr(0,12));
    try{
        var cp=app.project.items.addComp(name,1920,1080,1,rc.canvas.duration,24);
        cp.bgColor=color(rc.design.background);cp.motionBlur=true;cp.shutterAngle=180;cp.shutterPhase=-90;
        cp.comment=JSON.stringify({render_contract_sha:rc.render_contract_sha,package_sha:rc.package_sha,version:rc.version});
        var background=cp.layers.addSolid(color(rc.design.background),'BACKGROUND',1920,1080,1,cp.duration);
        var rows=[];
        for(var i=0;i<rc.nodes.length;i++){
            var n=rc.nodes[i],l,r=null;
            if(n.kind==='text'){
                l=cp.layers.addText(n.text);l.name=n.node_id;
                var p=l.property('Source Text'),d=p.value;d.font=n.font;d.fontSize=n.size;d.fillColor=color(n.color);d.applyFill=true;d.applyStroke=false;
                d.tracking=n.tracking||0;d.autoLeading=false;d.leading=n.leading||n.size*1.25;
                d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);
                r=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue([r.left,r.top]);
                if(n.reveal){
                    var mask=l.Masks.addProperty('ADBE Mask Atom');mask.name='EDITORIAL_CROP';
                    mask.property('ADBE Mask Shape').expression='var a='+n.reveal[0]+',b='+n.reveal[1]+';var q=ease(time,a,b,0,1);var r=thisLayer.sourceRectAtTime(time,false);var x=r.left-8,y=r.top-8,w=(r.width+16)*q,h=r.height+16;createPath([[x,y],[x+w,y],[x+w,y+h],[x,y+h]],[],[],true);';
                }
            }else{
                l=cp.layers.addShape();l.name=n.node_id;
                var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
                var rr=g.addProperty('ADBE Vector Shape - Rect');rr.property('ADBE Vector Rect Size').setValue(n.size);
                if(n.fill){var fill=g.addProperty('ADBE Vector Graphic - Fill');fill.property('ADBE Vector Fill Color').setValue(color(n.fill));}
                if(n.stroke){var stroke=g.addProperty('ADBE Vector Graphic - Stroke');stroke.property('ADBE Vector Stroke Color').setValue(color(n.stroke));stroke.property('ADBE Vector Stroke Width').setValue(n.stroke_width||2);}
                if(n.tracks&&n.tracks.width)keys(l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size'),n.tracks.width);
            }
            l.transform.position.setValue(n.position);l.transform.opacity.setValue(n.opacity===undefined?100:n.opacity);
            l.inPoint=n.in_point||0;l.outPoint=n.out_point||cp.duration;l.motionBlur=n.motion_blur!==false;
            var t=n.tracks||{};keys(l.transform.position,t.position);keys(l.transform.opacity,t.opacity);keys(l.transform.scale,t.scale);
            if(t.blur){var effect=l.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');keys(effect.property(1),t.blur);effect.property(3).setValue(true);}
            l.comment=JSON.stringify({unit_id:n.unit_id||null,binding:n.binding||'graphic_only',effects:n.effects||{}});
            if(r)rows.push({node_id:n.node_id,text:n.text,font:l.property('Source Text').value.font,size:n.size,width:r.width,height:r.height});
        }
        var imported=app.project.importFile(new ImportOptions(f));imported.name='HERO_CONTRACT_'+rc.render_contract_sha.substr(0,12);
        var data=cp.layers.add(imported);data.name='RENDER_CONTRACT';data.enabled=false;data.shy=true;
        cp.openInViewer();app.project.save(project);
        return JSON.stringify({ok:true,comp_id:cp.id,name:cp.name,render_contract_sha:rc.render_contract_sha,rows:rows});
    }finally{app.endUndoGroup();}
})();
