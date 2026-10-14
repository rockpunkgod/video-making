// Native P3 bounded motion preview. Uses supplied frozen slices and existing style.
// Deliberately does not implement candidate judgement or publication delivery.
(function(){
  var R=SHOT_PREVIEW, H=R.handoff, S=H.style, P=S.palette, T=S.type_scale;
  function save(path, text){var f=new File(path);f.encoding='UTF-8';f.open('w');f.write(text);f.close();}
  function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
  function keys(p,rows){for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
    for(var k=1;k<=p.numKeys;k++){var n=(p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL||p.propertyValueType===PropertyValueType.COLOR)?1:(p.value instanceof Array?p.value.length:1),e=[];
      for(var j=0;j<n;j++)e.push(new KeyframeEase(0,S.motion.easing.influence));p.setTemporalEaseAtKey(k,e,e);
      p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);}}
  try{
    if(app.project.renderQueue.rendering)throw Error('AE busy');
    if(new File(R.output+'/P3_PREVIEW.aep').exists)throw Error('Use fresh revision');
    if(app.project.numItems)app.project.save(new File(R.output+'/SESSION_BEFORE.aep'));
    app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=16;
    var cp=app.project.items.addComp('P3_SOURCE_LIFT_RETURN',1920,1080,1,H.script.duration,H.script.fps);
    cp.renderer='ADBE Classic 3d';cp.bgColor=rgb(P.environment);
    cp.layers.addSolid(rgb(P.environment),'ENVIRONMENT',1920,1080,1);
    var world=cp.layers.addNull();world.name='ORIGINAL_WORLD';world.threeDLayer=true;world.transform.position.setValue([0,0,0]);
    function material(l,lit,cast){var m=l.property('ADBE Material Options Group');m.property('ADBE Accepts Lights').setValue(lit?1:0);m.property('ADBE Casts Shadows').setValue(cast?1:0);m.property('ADBE Accepts Shadows').setValue(1);}
    var paper=cp.layers.addSolid(rgb(P.paper),'PAPER',1728,860,1);paper.threeDLayer=true;paper.transform.position.setValue([960,494,0]);material(paper,true,false);paper.parent=world;
    var layout=H.layouts[R.layout_id], win=layout.focus_windows[R.window_index], words=[],sourceLayers=[],target=H.script.targets[0];
    for(var i=0;i<layout.words.length;i++)if(layout.words[i].start>=win.start&&layout.words[i].end<=win.end)words.push(layout.words[i]);
    function text(value,size,font,c){var l=cp.layers.addText(value),p=l.property('Source Text'),d=p.value;d.font=font;d.fontSize=size;d.fillColor=rgb(c);d.applyStroke=false;d.applyFill=true;d.tracking=0;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);if(p.value.font!==font)throw Error('Font substitution: '+font);return l;}
    // Native widths determine row spacing; Python's word order and line breaks survive.
    var widths=[],maxWidth=0,current=-1,rowWidth=0,space=layout.size*.25;
    for(i=0;i<words.length;i++){var w=words[i];if(w.line!==current){if(current>=0){widths.push(rowWidth-space);maxWidth=Math.max(maxWidth,rowWidth-space);}rowWidth=0;current=w.line;}
      var font=w.font_role==='fallback'?S.fonts.caption.postscript:S.fonts.english.postscript;
      var l=text(w.text,layout.size,font,P.ink),b=l.sourceRectAtTime(0,false);l.name='SOURCE_'+w.start;l.threeDLayer=true;l.transform.anchorPoint.setValue([b.left,0,0]);
      l.comment='Original source range '+w.start+':'+w.end;l.transform.position.setValue([rowWidth,0,-1]);material(l,true,false);sourceLayers.push(l);rowWidth+=b.width+space;}
    widths.push(rowWidth-space);maxWidth=Math.max(maxWidth,rowWidth-space);
    var x0=(1920-maxWidth)/2,y0=494-((S.layout.focus_max_lines-1)*layout.line_height-layout.size)/2;
    for(i=0;i<words.length;i++){var pos=sourceLayers[i].transform.position.value;sourceLayers[i].transform.position.setValue([x0+pos[0],y0+(words[i].line-win.line_start)*layout.line_height,-1]);sourceLayers[i].parent=world;}
    var lift,ret,dim,bright,loc;
    for(i=0;i<H.actions.length;i++){var a=H.actions[i];if(a.action==='lift')lift=a;if(a.action==='return')ret=a;if(a.action==='dim_world')dim=a;if(a.action==='brighten_world')bright=a;if(a.action==='locate')loc=a;}
    if(!lift||!ret||!dim||!bright||!loc)throw Error('Preview requires locate/lift/return and light transitions');
    keys(world.transform.position,[[0,[0,0,0]],[dim.at,[0,0,0]],[dim.end,[0,0,S.depth.world_z_retreat]],[bright.at,[0,0,S.depth.world_z_retreat]],[bright.end,[0,0,0]]]);
    var ambient=cp.layers.addLight('WORLD_AMBIENT',[960,540]);ambient.lightType=LightType.AMBIENT;
    keys(ambient.property('ADBE Light Options Group').property('ADBE Light Intensity'),[[0,30],[dim.at,30],[dim.end,7.5],[bright.at,7.5],[bright.end,30]]);
    var light=cp.layers.addLight('PAPER_KEY',[800,200]);light.lightType=LightType.SPOT;light.transform.position.setValue([500,50,-1600]);light.transform.pointOfInterest.setValue([960,500,0]);
    var lo=light.property('ADBE Light Options Group');lo.property('ADBE Light Cone Angle').setValue(110);lo.property('ADBE Light Cone Feather 2').setValue(85);lo.property('ADBE Casts Shadows').setValue(1);lo.property('ADBE Light Shadow Darkness').setValue(S.depth.light_dark.shadow_opacity*100);lo.property('ADBE Light Shadow Diffusion').setValue(S.depth.light_dark.shadow_blur);
    keys(lo.property('ADBE Light Intensity'),[[0,70],[dim.at,70],[dim.end,17.5],[bright.at,17.5],[bright.end,70]]);
    var matches=[],total=0,ratio=T.comparison/layout.size,z=-S.depth.light_dark.lifted_z_forward,q=(2400+z)/2400;
    for(i=0;i<words.length;i++)if(words[i].start>=target.range[0]&&words[i].end<=target.range[1]){matches.push(i);total+=sourceLayers[i].sourceRectAtTime(0,false).width*ratio+space*ratio;}
    if(!matches.length)throw Error('Target not visible in focus window');total-=space*ratio;var cursor=(1920-total)/2;
    for(var k=0;k<matches.length;k++){i=matches[k];var original=sourceLayers[i],ex=original.duplicate();ex.name='EXTRACT_'+words[i].start;ex.parent=null;material(ex,false,true);
      var base=original.transform.position.value,back=[base[0],base[1],base[2]+S.depth.world_z_retreat],goal=[960+(cursor-960)*q,540+(540-540)*q,z];
      ex.inPoint=lift.at;ex.outPoint=ret.end;
      keys(ex.transform.position,[[lift.at,base],[lift.end,goal],[ret.at,goal],[ret.end,back]]);
      keys(ex.transform.scale,[[lift.at,[100,100,100]],[lift.end,[ratio*q*100,ratio*q*100,100]],[ret.at,[ratio*q*100,ratio*q*100,100]],[ret.end,[100,100,100]]]);
      var tp=ex.property('Source Text'),td=tp.value;td.fillColor=rgb(P.lifted_paper);tp.setValue(td);
      keys(ex.transform.opacity,[[lift.at,0],[lift.at+2/H.script.fps,100],[ret.end-2/H.script.fps,100],[ret.end,0]]);
      cursor+=original.sourceRectAtTime(0,false).width*ratio+space*ratio;
    }
    // One orange region only, attached to the original phrase. No underline or added annotation.
    var first=sourceLayers[matches[0]],last=sourceLayers[matches[matches.length-1]],fp=first.transform.position.value,lp=last.transform.position.value;
    if(Math.abs(fp[1]-lp[1])>1)throw Error('This bounded preview expects a single-line slice');
    var hl=cp.layers.addSolid(rgb(P.attention_orange),'LOCATE_ORIGINAL',Math.ceil(lp[0]-fp[0]+last.sourceRectAtTime(0,false).width+12),Math.ceil(layout.size*1.2),1);
    hl.threeDLayer=true;hl.transform.position.setValue([fp[0]-6+hl.width/2,fp[1]-layout.size*.35,-0.5]);material(hl,false,false);hl.parent=world;
    keys(hl.transform.opacity,[[0,0],[loc.at,0],[loc.end,60],[lift.at,60],[lift.end,0]]);
    var camera=cp.layers.addCamera('GUIDED_CAMERA',[960,540]);camera.transform.position.setValue([960,540,-2400]);camera.transform.pointOfInterest.setValue([960,540,0]);
    var co=camera.property('ADBE Camera Options Group');co.property('ADBE Camera Zoom').setValue(2400);co.property('ADBE Camera Depth of Field').setValue(1);co.property('ADBE Camera Aperture').setValue(60);
    keys(co.property('ADBE Camera Focus Distance'),[[0,2400],[lift.at,2400],[lift.end,2400+z],[ret.at,2400+z],[ret.end,2400]]);
    var master=app.project.items.addComp('P3_PREVIEW_4K',3840,2160,1,H.script.duration,H.script.fps),nested=master.layers.add(cp);nested.transform.scale.setValue([200,200]);nested.transform.position.setValue([1920,1080]);
    app.project.save(new File(R.output+'/P3_PREVIEW.aep'));
    master.saveFrameToPng(1,new File(R.output+'/READ.png'));master.saveFrameToPng(7,new File(R.output+'/LIFT.png'));
    save(R.output+'/BUILT.txt','Native 4K preview; light intensity 25% is not calibrated luminance. No teaching decision.');
    var rq=app.project.renderQueue.items.add(master),om=rq.outputModule(1);save(R.output+'/templates.txt',om.templates.join('\n'));
    rq.render=false;save(R.output+'/RENDER_COMP_ID.txt',String(master.id));app.project.save();
  }catch(e){save(R.output+'/ERROR.txt',e.toString()+' line '+e.line);}
})();
