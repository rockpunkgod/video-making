// P4 implementation of the supplied style and source-bound episode edit list.
// No analysis, alternative answers or teaching summaries are generated here.
(function(){
  var R=EPISODE_PREVIEW,H=R.plan,S=H.style,P=S.palette,F=S.fonts,T=S.type_scale;
  function save(name,value){var f=new File(R.output+'/'+name);f.encoding='UTF-8';f.open('w');f.write(value);f.close();}
  function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
  function keys(p,rows){for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
    for(var k=1;k<=p.numKeys;k++){var n=(p.propertyValueType===PropertyValueType.ThreeD_SPATIAL||p.propertyValueType===PropertyValueType.TwoD_SPATIAL||p.propertyValueType===PropertyValueType.COLOR)?1:(p.value instanceof Array?p.value.length:1),e=[];
      for(var j=0;j<n;j++)e.push(new KeyframeEase(0,S.motion.easing.influence));p.setTemporalEaseAtKey(k,e,e);p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);}}
  var cp;
  function material(l,lit,cast){var m=l.property('ADBE Material Options Group');m.property('ADBE Accepts Lights').setValue(lit?1:0);m.property('ADBE Casts Shadows').setValue(cast?1:0);m.property('ADBE Accepts Shadows').setValue(1);}
  function text(name,value,size,x,y,color,z,lit){var l=cp.layers.addText(value),p=l.property('Source Text'),d=p.value;d.font=/[\u3400-\u9fff]/.test(value)?F.caption.postscript:F.english.postscript;d.fontSize=size;d.fillColor=rgb(color);d.applyStroke=false;d.applyFill=true;d.tracking=0;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);if(p.value.font!==d.font)throw Error('Font substitution');var b=l.sourceRectAtTime(0,false);l.name=name;l.threeDLayer=true;l.transform.anchorPoint.setValue([b.left,0,0]);l.transform.position.setValue([x,y,z||0]);material(l,lit||false,false);return l;}
  function solid(name,color,x,y,w,h,z,lit){var l=cp.layers.addSolid(rgb(color),name,Math.ceil(w),Math.ceil(h),1);l.threeDLayer=true;l.transform.position.setValue([x+w/2,y+h/2,z||0]);material(l,lit,false);return l;}
  function center(l,y){var b=l.sourceRectAtTime(0,false),p=l.transform.position.value;l.transform.position.setValue([(1920-b.width)/2,y,p[2]]);}
  function wrapped(name,value,size,y,color,width){var tokens=value.split(/\s+/),rows=[],row='',probe=text('MEASURE','',size,0,0,color,-2,false);
    for(var i=0;i<tokens.length;i++){var next=row?row+' '+tokens[i]:tokens[i],p=probe.property('Source Text'),d=p.value;d.text=next;p.setValue(d);if(row&&probe.sourceRectAtTime(0,false).width>width){rows.push(row);row=tokens[i];}else row=next;}if(row)rows.push(row);probe.remove();
    var made=[];for(i=0;i<rows.length;i++){var l=text(name+'_'+i,rows[i],size,180,y+i*size*1.35,color,-2,false);made.push(l);}return made;}
  function sourceWorld(plan,start,end,world){var words=[],layers=[],current=-1,rowWidth=0,max=0,space=plan.size*.25;
    for(var i=0;i<plan.words.length;i++){var w=plan.words[i];if(w.line<start||w.line>=end)continue;words.push(w);}
    for(i=0;i<words.length;i++){w=words[i];if(current!==w.line){max=Math.max(max,rowWidth-space);rowWidth=0;current=w.line;}
      var l=text('ORIGINAL_'+w.start,w.text,plan.size,rowWidth,0,P.ink,-1,true);rowWidth+=l.sourceRectAtTime(0,false).width+space;layers.push(l);}
    max=Math.max(max,rowWidth-space);var x=(1920-max)/2,y=260;
    for(i=0;i<words.length;i++){var pos=layers[i].transform.position.value;layers[i].transform.position.setValue([x+pos[0],y+(words[i].line-start)*plan.line_height,-1]);layers[i].parent=world;layers[i].comment='Frozen original Unicode '+words[i].start+':'+words[i].end;}
    return {words:words,layers:layers};}
  try{
    if(app.project.renderQueue.rendering)throw Error('AE rendering');if(new File(R.output+'/P4_EPISODE.aep').exists)throw Error('Fresh revision required');
    if(app.project.numItems)app.project.save(new File(R.output+'/SESSION_BEFORE.aep'));app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=16;
    var master=app.project.items.addComp('P4_INTERNAL_PICTURE',1920,1080,1,H.duration,H.fps),sceneIds=[],lights=[];
    for(var si=0;si<H.scenes.length;si++){
      var s=H.scenes[si],dur=(s.end_frame-s.start_frame)/H.fps;
      cp=app.project.items.addComp(s.id,1920,1080,1,dur,H.fps);cp.renderer='ADBE Classic 3d';cp.bgColor=rgb(P.environment);cp.comment='Frozen asset '+s.asset_id+'; internal only';
      cp.layers.addSolid(rgb(P.environment),'ENVIRONMENT',1920,1080,1);
      var world=cp.layers.addNull();world.threeDLayer=true;world.transform.position.setValue([0,0,0]);world.name='ORIGINAL_WORLD';
      var paper=solid('PAPER',P.paper,96,64,1728,860,0,true);paper.parent=world;
      var amb=cp.layers.addLight('WORLD_AMBIENT',[960,540]);amb.lightType=LightType.AMBIENT;var ai=amb.property('ADBE Light Options Group').property('ADBE Light Intensity');ai.setValue(30);
      var key=cp.layers.addLight('PAPER_KEY',[800,200]);key.lightType=LightType.SPOT;key.transform.position.setValue([500,50,-1600]);key.transform.pointOfInterest.setValue([960,500,0]);var lo=key.property('ADBE Light Options Group');lo.property('ADBE Light Intensity').setValue(70);lo.property('ADBE Light Cone Angle').setValue(110);lo.property('ADBE Light Cone Feather 2').setValue(85);lo.property('ADBE Casts Shadows').setValue(1);lo.property('ADBE Light Shadow Darkness').setValue(S.depth.light_dark.shadow_opacity*100);lo.property('ADBE Light Shadow Diffusion').setValue(S.depth.light_dark.shadow_blur);
      var camera=cp.layers.addCamera('GUIDED_CAMERA',[960,540]);camera.transform.position.setValue([960,540,-2400]);camera.transform.pointOfInterest.setValue([960,540,0]);var co=camera.property('ADBE Camera Options Group');co.property('ADBE Camera Zoom').setValue(2400);co.property('ADBE Camera Focus Distance').setValue(2400);
      var sourceTitle=s.display_texts[0];wrapped('ORIGINAL_QUESTION',sourceTitle,T.label,140,P.secondary,1500);
      if(s.pass_label)text('PASS_LABEL',s.pass_label,T.label,1640,140,P.secondary,-2,false);
      if(s.kind==='evidence'){
        var original=sourceWorld(s.layout,s.focus_line_start,s.focus_line_end,world),hits=[];
        for(var wi=0;wi<original.words.length;wi++)if(original.words[wi].start>=s.range[0]&&original.words[wi].end<=s.range[1])hits.push(wi);
        if(!hits.length)throw Error('Visible evidence origin missing');
        var at=.55,liftAt=1.05,settle=liftAt+S.motion.actions.lift.frames/H.fps;
        var first=original.layers[hits[0]],last=original.layers[hits[hits.length-1]],fp=first.transform.position.value,lp=last.transform.position.value;
        // Orange belongs to one frozen phrase; several lines are never annotated at once.
        var hl=solid('LOCATE',P.attention_orange,fp[0]-6,fp[1]-s.layout.size*.8,first.sourceRectAtTime(0,false).width+12,s.layout.size*1.1,-.5,false);hl.parent=world;
        keys(hl.transform.opacity,[[0,0],[at,0],[at+.18,60],[liftAt,60],[settle,0]]);
        keys(world.transform.position,[[0,[0,0,0]],[liftAt,[0,0,0]],[settle,[0,0,S.depth.world_z_retreat]]]);
        keys(ai,[[0,30],[liftAt,30],[settle,7.5]]);keys(lo.property('ADBE Light Intensity'),[[0,70],[liftAt,70],[settle,17.5]]);
        co.property('ADBE Camera Depth of Field').setValue(1);co.property('ADBE Camera Aperture').setValue(60);keys(co.property('ADBE Camera Focus Distance'),[[0,2400],[liftAt,2400],[settle,2200]]);
        var exPlan=s.excerpt_layout,ratio=exPlan.size/s.layout.size,z=-S.depth.light_dark.lifted_z_forward,q=(2400+z)/2400,maxWidth=0;
        for(wi=0;wi<exPlan.words.length;wi++)maxWidth=Math.max(maxWidth,exPlan.words[wi].x+exPlan.words[wi].w);
        var startX=(1920-maxWidth)/2,startY=494-(exPlan.lines.length-1)*exPlan.line_height/2;
        for(wi=0;wi<hits.length;wi++){var index=hits[wi],ex=original.layers[index].duplicate();ex.name='EXTRACT_'+original.words[index].start;ex.parent=null;material(ex,false,true);var base=original.layers[index].transform.position.value,ew=exPlan.words[wi];if(!ew||ew.text!==original.words[index].text)throw Error('Projection token drift');
          var goal=[960+(startX+ew.x-960)*q,540+(startY+ew.y-540)*q,z];ex.inPoint=liftAt;
          keys(ex.transform.position,[[liftAt,base],[settle,goal]]);keys(ex.transform.scale,[[liftAt,[100,100,100]],[settle,[ratio*q*100,ratio*q*100,100]]]);var tp=ex.property('Source Text'),td=tp.value;td.fillColor=rgb(P.lifted_paper);tp.setValue(td);keys(ex.transform.opacity,[[liftAt,0],[liftAt+.08,100]]);ex.comment='Origin layer '+original.layers[index].id+'; frozen range '+original.words[index].start+':'+original.words[index].end;
        }
      }else if(s.kind==='comparison'){
        ai.setValue(7.5);lo.property('ADBE Light Intensity').setValue(17.5);
        var y=275;var option=wrapped('CANDIDATE',s.candidate+'. '+s.display_texts[1],T.option,y,P.lifted_paper,1500);y+=option.length*T.option*1.35+70;
        var blue=solid('COMPARE_BLUE',P.comparison_blue,160,220,1560,option.length*T.option*1.35+50,-1,false);blue.transform.opacity.setValue(25);
        for(var ei=0;ei<s.evidence.length;ei++){var rows=wrapped('EVIDENCE_'+ei,s.evidence[ei].quote,T.option,y,P.lifted_paper,1500);y+=rows.length*T.option*1.35+12;if(y>880)throw Error('Comparison evidence exceeds safe reading area');}
        if(s.effect==='eliminate'){for(ei=0;ei<option.length;ei++){var pp=option[ei].transform.position.value,dt=s.decision_frame/H.fps;keys(option[ei].transform.position,[[0,pp],[dt,pp],[dt+S.motion.actions.eliminate.frames/H.fps,[pp[0],pp[1]+S.motion.actions.eliminate.y_offset,pp[2]]]]);keys(option[ei].transform.opacity,[[0,100],[dt,100],[dt+S.motion.actions.eliminate.frames/H.fps,S.motion.actions.eliminate.opacity]]);}}
      }else{
        var startY=s.kind==='question'?320:400,size=s.kind==='recall'?T.comparison:T.option;
        for(var ti=1;ti<s.display_texts.length;ti++){var displayed=s.display_texts[ti],path=s.display_refs[ti].pointer;if(path.indexOf('/source_snapshot/options/')===0)displayed=path.substr(path.length-1)+'. '+displayed;var rows=wrapped('DISPLAY_'+ti,displayed,size,startY,P.ink,1500);startY+=rows.length*size*1.35+36;}
        if(s.answer){var answer=text('FROZEN_ANSWER',s.answer,T.decision_large,0,620,P.ink,-2,false);center(answer,620);}
      }
      // Captions use the exact existing transcript, with character-weighted estimated timing.
      for(var vi=0;vi<H.voices.length;vi++){var v=H.voices[vi];if(v.start_frame<s.start_frame||v.start_frame>=s.end_frame)continue;
        var band=cp.layers.addSolid(rgb(P.ink),'CAPTION_BAND_'+v.id,1728,72,1);band.transform.position.setValue([960,932]);band.transform.opacity.setValue(60);band.inPoint=(v.start_frame-s.start_frame)/H.fps;band.outPoint=(v.end_frame-s.start_frame)/H.fps;
        var parts=v.caption_parts,weight=v.text.length,offset=0;
        for(var pi=0;pi<parts.length;pi++){var begin=(v.start_frame-s.start_frame)/H.fps+v.duration*offset/weight,end=begin+v.duration*parts[pi].length/weight;offset+=parts[pi].length;
          var cap=text('CAPTION_'+v.id+'_'+pi,parts[pi],T.caption,0,944,P.caption_ink,-2,false);cap.threeDLayer=false;var box=cap.sourceRectAtTime(0,false);if(box.width>1728)throw Error('Caption exceeds safe width');center(cap,944);cap.inPoint=begin;cap.outPoint=end;
        }
      }
      var nested=master.layers.add(cp);nested.startTime=s.start_frame/H.fps;nested.inPoint=s.start_frame/H.fps;nested.outPoint=s.end_frame/H.fps;
      sceneIds.push(cp.id);save('PROGRESS.txt','Built '+(si+1)+' / '+H.scenes.length);
    }
    app.project.save(new File(R.output+'/P4_EPISODE.aep'));save('RENDER_COMP_ID.txt',String(master.id));
    master.saveFrameToPng(3,new File(R.output+'/QUESTION.png'));master.saveFrameToPng(H.scenes[2].start_frame/H.fps+2,new File(R.output+'/EVIDENCE.png'));
    save('BUILT.txt','native_comp_id='+master.id+'; scenes='+sceneIds.length+'; duration='+H.duration);
  }catch(e){save('ERROR.txt',e.toString()+'; line '+e.line);}
})();
