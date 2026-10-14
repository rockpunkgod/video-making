// One native 3D world; approved glyph-origin grammar, no option cards or scene cuts.
(function(){
var H=SG_INPUT.plan,out=SG_INPUT.output,cp,geometry=[],proof=[];
function save(n,s){var f=new File(out+'/'+n);f.encoding='UTF-8';f.open('w');f.write(s);f.close();}
function rgb(s){return [parseInt(s.substr(1,2),16)/255,parseInt(s.substr(3,2),16)/255,parseInt(s.substr(5,2),16)/255];}
function vec(x,y,z){return [x*2,y*2,(z||0)*2];}
function text(n,s,size,x,y,font,world){
 if(font===H.renderer_fonts.english&&/[\u3400-\u9fff]/.test(s))font=H.renderer_fonts.caption;
 var l=cp.layers.addText(s);l.name=n;var d=l.property('Source Text').value;
 d.font=font;d.fontSize=size*2;d.fillColor=rgb('#20211F');d.applyFill=true;d.applyStroke=false;
 l.property('Source Text').setValue(d);
 // Native font service can settle after newProject; retries never accept a fallback.
 for(var attempt=0;attempt<10&&l.property('Source Text').value.font!==font;attempt++){
  $.sleep(100);d=l.property('Source Text').value;d.font=font;l.property('Source Text').setValue(d);
 }
 if(l.property('Source Text').value.font!==font)throw Error('Native font substitution: '+font+' -> '+l.property('Source Text').value.font);
 l.threeDLayer=world;l.motionBlur=world;
 var r=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue(world?[r.left,0,0]:[r.left,0]);
 l.transform.position.setValue(world?vec(x,y,0):[x*2,y*2]);return l;
}
function fill(n,x,y,w,h,color,world){
 var l=cp.layers.addShape();l.name=n;l.threeDLayer=world;
 var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
 g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
 g=l.property('ADBE Root Vectors Group').property(1);
 g.property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([w*2,h*2]);
 g.property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(rgb(color));
 l.transform.anchorPoint.setValue(world?[-w,-h,0]:[-w,-h]);l.transform.position.setValue(world?vec(x,y,1):[x*2,y*2]);return l;
}
var font=H.renderer_fonts.english,cn=H.renderer_fonts.caption,serif=H.renderer_fonts.decision;
function flow(n,value,size,x,y,width,parent,ref){
 var rx=/\S+/g,m,layers=[],line=0,xx=x,yy=y;
 while((m=rx.exec(value))!==null){
  var l=text(n+'_'+m.index,m[0],size,xx,yy,font,true),r=l.sourceRectAtTime(0,false),ww=r.width/2;
  if(xx+ww>x+width&&xx>x){xx=x;line++;yy=y+line*62;}
  l.transform.position.setValue(vec(xx,yy,0));if(parent)l.parent=parent;
  var v={layer:l,start:m.index,end:m.index+m[0].length,text:m[0],line:line,x:xx,y:yy,width:ww,size:size};layers.push(v);
  l.comment=JSON.stringify({kind:'source_world_word',range:[v.start,v.end],source_ref:ref});
  geometry.push({layer_id:l.id,name:l.name,text:v.text,range:[v.start,v.end],origin:vec(xx,yy,0),size:size,font:l.property('Source Text').value.font});
  xx+=ww+size*.24;
 }
 return layers;
}
function range(words,a,b){var found=[];for(var i=0;i<words.length;i++)if(words[i].start>=a&&words[i].end<=b)found.push(words[i]);return found;}
function highlight(words,at,until,color){
 var lines={},i;
 for(i=0;i<words.length;i++){var w=words[i],key=w.line;if(!lines[key])lines[key]={x:w.x,y:w.y,end:w.x+w.width};else lines[key].end=w.x+w.width;}
 for(var k in lines){var r=lines[k],f=fill('LOCATE_'+at+'_'+k,r.x-3,r.y-48,r.end-r.x+6,58,color,true);
  f.parent=words[0].layer.parent;f.inPoint=at;f.outPoint=until;f.transform.opacity.setValue(60);SG_locate(f,at,10,24);f.moveAfter(words[0].layer);}
}
function workspace(x,y){var f=(1100-160)/1100;return vec(960+(x-960)*f,540+(y-540)*f,-160);}
function project(words,at,back,x,y,name){
 var made=[],xx=x,yy=y,scale=72/words[0].size*(1100-160)/1100*100;
 for(var i=0;i<words.length;i++){
  var w=words[i],projectedWidth=w.width*72/w.size;
  if(xx+projectedWidth>1130&&xx>x){xx=x;yy+=94;}
  var offset=w.layer.parent===rail?rail.transform.position.valueAtTime(at,false):[0,0,0];
  var p=w.layer.transform.position.valueAtTime(at,false),origin=[p[0]+offset[0],p[1]+offset[1],0];
  var target=workspace(xx+12,yy);
  var item=SG_lift(w.layer,target,at,{origin:origin,name:name+'_'+i,source:JSON.parse(w.layer.comment),frames:14,fps:24,scale:scale,returnAt:back,returnFrames:16});
  SG_compare(item,workspace(xx,yy),at+14/24,12,24);item.target=workspace(xx,yy);
  var anim=item.layer.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');
  anim.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');
  var color=item.layer.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');
  SG_keys(color,[[at,rgb('#20211F')],[at+26/24,rgb('#3A6A8A')],[back,rgb('#3A6A8A')],[back+16/24,rgb('#20211F')]],false);
  SG_return(item,back,16,24);made.push(item);
  proof.push({projection_id:item.layer.id,origin_layer_id:w.layer.id,origin:origin,return_origin:origin,lift_at:at,return_at:back,projected_size:72,range:[w.start,w.end]});
  xx+=projectedWidth+17;
 }
 return made;
}
try{
 if(app.project.renderQueue.rendering)throw Error('AE busy');if(new File(out+'/CONTINUOUS_QUESTION.aep').exists)throw Error('Fresh output required');
 if(app.project.numItems)app.project.save(new File(out+'/SESSION_BEFORE.aep'));
 app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=16;
 var nativeFontList=app.fonts.allFonts;$.sleep(500);
 cp=app.project.items.addComp('QUESTION_NATIVE_4K',3840,2160,1,H.duration,24);cp.renderer='ADBE Classic 3D';cp.bgColor=rgb('#F2F0EA');cp.motionBlur=true;cp.shutterAngle=180;
 cp.layers.addSolid(rgb('#F2F0EA'),'REALITY_PAPER_FULL_FRAME',3840,2160,1).moveToEnd();
 var world=cp.layers.addNull();world.name='REALITY_CONTENT';world.threeDLayer=true;world.transform.position.setValue([0,0,0]);world.enabled=false;
 var rail=cp.layers.addNull();rail.name='PASSAGE_READING_RAIL';rail.threeDLayer=true;rail.transform.position.setValue([0,0,0]);rail.enabled=false;
 var state=cp.layers.addNull();state.name='COGNITIVE_DIM';state.enabled=false;state.property('ADBE Effect Parade').addProperty('ADBE Slider Control');
 var dim=state.property('ADBE Effect Parade').property(1).property(1);dim.setValue(100);
 // Stem and options occupy stable authored positions, with the user's requested sizes.
 var stem=flow('STEM',H.source.stem,48,100,142,1720,null,H.source_refs.stem);
 highlight(range(stem,13,27),3,4,'#C8622E');
 var source=flow('PASSAGE',H.source.passage,46,100,292,1020,rail,H.source_refs.passage);
 for(var i=0;i<source.length;i++)source[i].layer.transform.opacity.expression='var y=transform.position[1]+thisComp.layer("PASSAGE_READING_RAIL").transform.position[1]; var edge=Math.min(linear(y,470,550,0,1),linear(y,1680,1760,1,0));edge*thisComp.layer("COGNITIVE_DIM").effect(1)(1);';
 var options={},allOptions=[];
 for(var oi=0;oi<4;oi++){
  var letter='ABCD'.charAt(oi),label=text('OPTION_'+letter,letter+'.',44,1200,296+oi*146,font,true);
  var group=flow('OPTION_'+letter,H.source.options[letter],44,1270,296+oi*146,550,null,H.source_refs.options);
  options[letter]=group;allOptions.push(label);
  for(i=0;i<group.length;i++)allOptions.push(group[i].layer);
 }
 for(i=0;i<allOptions.length;i++)allOptions[i].transform.opacity.expression='value*thisComp.layer("COGNITIVE_DIM").effect(1)(1)/100;';
 var focus=cp.layers.addNull();focus.name='FOCUS_TARGET';focus.threeDLayer=true;focus.enabled=false;focus.transform.position.setValue(vec(960,540,0));
 var cam=cp.layers.addCamera('GUIDED_CAMERA',[1920,1080]);cam.transform.position.setValue(vec(960,540,-1100));cam.transform.pointOfInterest.setValue(vec(960,540,0));
 var co=cam.property('ADBE Camera Options Group');co.property('ADBE Camera Zoom').setValue(2200);co.property('ADBE Camera Depth of Field').setValue(1);co.property('ADBE Camera Aperture').setValue(22);co.property('ADBE Camera Blur Level').setValue(45);
 co.property('ADBE Camera Focus Distance').expression='var p=thisComp.layer("FOCUS_TARGET").toWorld([0,0,0]);var c=transform.position;var v=normalize(sub(transform.pointOfInterest,c));Math.max(1,dot(sub(p,c),v));';
 SG_cameraKeys(cam.transform.position,[[0,vec(960,540,-1100)],[10,vec(956,540,-1100)],[18,vec(964,540,-1100)],[22,vec(960,540,-1100)],[30,vec(960,540,-1100)],[46,vec(956,540,-1100)],[56,vec(960,540,-1100)],[70,vec(960,540,-1100)]],[1,2,5]);
 // Original source retreats in true Z. Counter-scaling retains the specified screen text size.
 var retreats=[],dims=[],railKeys=[[0,[0,0,0]]],focusKeys=[[0,vec(960,540,0)]];
 var passes=[{start:10,step:4,label:'原速'},{start:30,step:8,label:'慢放'}];
 var health=H.source.options.D.indexOf('Keep');var dwords=range(options.D,health,H.source.options.D.length);
 for(var pi=0;pi<passes.length;pi++){
  var pass=passes[pi],tag=text('PASS_LABEL_'+pi,pass.label,28,100,212,cn,false);tag.inPoint=pass.start;tag.outPoint=pi===0?28:64;
  for(var qi=0;qi<3;qi++){
   var p=H.projections[qi],at=pass.start+qi*pass.step,hits=range(source,p.range[0],p.range[1]);if(!hits.length)throw Error('No bound glyph');
   var shift=-Math.max(0,hits[0].line-2)*62,oldShift=railKeys[railKeys.length-1][1];
   railKeys.push([at,oldShift],[at+1,vec(0,shift,0)]);SG_keys(rail.transform.position,railKeys,false);
   var lift=at+1.5,back=at+pass.step-.8;
   highlight(hits,at+1,at+1.5,'#C8622E');
   // Exact source words and the original option keywords, not replacement cards.
   project(hits,lift,back,120,448,'EVIDENCE_'+pi+'_'+qi);
   project(dwords,lift,back,120,760,'OPTION_KEYWORDS_'+pi+'_'+qi);
   dims.push([lift,100],[lift+.5,35],[back,35],[back+16/24,100]);
   focusKeys.push([lift,vec(960,540,0)],[lift+.5,vec(960,540,-160)],[back,vec(960,540,-160)],[back+16/24,vec(960,540,0)]);
  }
 }
 dims.push([22,100],[22.5,35],[25,35],[25.5,100],[56,100],[56.5,35],[62,35],[62.5,100]);
 focusKeys.push([22,vec(960,540,0)],[22.5,vec(960,540,-160)],[25,vec(960,540,-160)],[25.5,vec(960,540,0)],
  [56,vec(960,540,0)],[56.5,vec(960,540,-160)],[62,vec(960,540,-160)],[62.5,vec(960,540,0)]);
 SG_keys(dim,dims,false);SG_keys(focus.transform.position,focusKeys,false);
 // One native parent handles depth, replacing hundreds of redundant per-word transforms.
 var srcAndOpts=[];for(i=0;i<source.length;i++)srcAndOpts.push(source[i].layer);for(i=0;i<allOptions.length;i++)srcAndOpts.push(allOptions[i]);
 world.transform.anchorPoint.setValue(vec(960,540,0));world.transform.position.setValue(vec(960,540,0));
 rail.parent=world;for(i=0;i<allOptions.length;i++)allOptions[i].parent=world;
 world.transform.position.expression='var a=thisComp.layer("COGNITIVE_DIM").effect(1)(1);[1920,1080,(100-a)/65*1200];';
 world.transform.scale.expression='var a=thisComp.layer("COGNITIVE_DIM").effect(1)(1);var f=(2200+(100-a)/65*1200)/2200;[100*f,100*f,100*f];';
 // Temporal bounds skip dormant glyph textures; include complete scroll intervals.
 for(i=0;i<source.length;i++){
  var w=source[i],first=70,last=0;
  for(var ri=0;ri<railKeys.length;ri++){
   var next=ri+1<railKeys.length?railKeys[ri+1]:[70,railKeys[ri][1]];
   var lo=w.y+Math.min(railKeys[ri][1][1],next[1][1])/2,hi=w.y+Math.max(railKeys[ri][1][1],next[1][1])/2;
   if(lo<=880&&hi>=235){first=Math.min(first,railKeys[ri][0]);last=Math.max(last,next[0]);}
  }
  if(first<last){w.layer.inPoint=first;w.layer.outPoint=Math.min(70,last+1/24);}else w.layer.enabled=false;
 }
 var dl=[cp.layer('OPTION_D')];for(i=0;i<options.D.length;i++)dl.push(options.D[i].layer);
 // Replay is a visual reset of the same existing action, never a second candidate decision.
 for(i=0;i<dl.length;i++){
  var l=dl[i];SG_keys(l.transform.opacity,[[0,100],[22,100],[22+10/24,20],[29.8,20],[30,100],[56,100],[56+10/24,20],[70,20]],false);
  var pos=l.transform.position.valueAtTime(0,true);
  SG_eliminate([l],22,10,24);SG_keys(l.transform.position,[[29.8,[pos[0],pos[1]+48,0]],[30,pos]],false);SG_eliminate([l],56,10,24);
 }
 for(var ji=0;ji<2;ji++){var dec=text('BOUNDED_DECISION_'+ji,'排除 D',100,130,570,serif,false);dec.inPoint=ji===0?23:57;dec.outPoint=ji===0?25:62;}
 var memory=text('FROZEN_MEMORY',H.memory_line,48,100,902,cn,false);memory.inPoint=66;memory.outPoint=70;memory.comment=JSON.stringify(H.memory_ref);
 // Caption is lexical projection of existing WAV transcripts, never improvised VO.
 for(i=0;i<H.voices.length;i++){
  var v=H.voices[i],start=v.start_frame/24,end=v.end_frame/24,chars=v.text.length,cursor=start;
  for(var ci=0;ci<v.caption_parts.length;ci++){
   var sentence=v.caption_parts[ci],stop=ci===v.caption_parts.length-1?end:cursor+(end-start)*sentence.length/chars;
   var cap=text('CAPTION_'+v.id+'_'+ci,sentence,36,100,978,cn,false);var d=cap.property('Source Text').value;d.fillColor=[1,1,1];cap.property('Source Text').setValue(d);
   var rr=cap.sourceRectAtTime(0,false),bg=fill('CAPTION_BAND',90,926,1740,76,'#20211F',false);bg.transform.opacity.setValue(60);bg.moveAfter(cap);
   cap.inPoint=bg.inPoint=cursor;cap.outPoint=bg.outPoint=stop;cursor=stop;
  }
 }
 // Native 4K master; proxy is one exact 50% projection, no nested camera/collapse transform.
 var proxy=app.project.items.addComp('QUESTION_REVIEW_1080',1920,1080,1,H.duration,24),nest=proxy.layers.add(cp);nest.transform.scale.setValue([50,50]);nest.transform.position.setValue([960,540]);
 app.project.save(new File(out+'/CONTINUOUS_QUESTION.aep'));save('RENDER_COMP_ID.txt',String(cp.id));save('PROXY_COMP_ID.txt',String(proxy.id));
 save('NATIVE_GEOMETRY.json',JSON.stringify({geometry:geometry,projections:proof,renderer:cp.renderer,master:cp.id,proxy:proxy.id,public_render_ready:false}));
 proxy.openInViewer();save('BUILD_DONE.txt','native glyph origin grammar');
}catch(e){save('BUILD_ERROR.txt',e.toString()+' line '+e.line);}
})();
