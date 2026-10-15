// Explicit native 4K proof. No TTS, answer inference or changes to frozen text.
(function(){
var H=DF_INPUT.plan,out=DF_INPUT.output,cp,originals=[],words=[],audit=[];
function save(n,v){var f=new File(out+'/'+n);f.encoding='UTF-8';f.open('w');f.write(v);f.close();}
function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
function xyz(x,y,z){return [x*2,y*2,(z||0)*2];}
var paper=rgb('#F2F0EA'),ink=rgb('#20211F'),dark=rgb('#17181A'),muted=rgb('#42464A');
function text(n,s,size,x,y,three){
 var l=cp.layers.addText(s),d=l.property('Source Text').value;
 d.font=/[\u3400-\u9fff]/.test(s)?H.renderer_fonts.caption:H.renderer_fonts.english;d.fontSize=size*2;d.fillColor=ink;d.applyStroke=false;
 l.property('Source Text').setValue(d);if(l.property('Source Text').value.font!==d.font)throw Error('Font substitution');
 l.name=n;l.threeDLayer=three;l.motionBlur=three;var b=l.sourceRectAtTime(0,false);
 l.transform.anchorPoint.setValue(three?[b.left,0,0]:[b.left,0]);l.transform.position.setValue(three?xyz(x,y,0):[x*2,y*2]);return l;
}
function color(l){var a=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');a.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');return a.property('ADBE Text Animator Properties').property('ADBE Text Fill Color');}
function rect(n,x,y,w,h,col){var l=cp.layers.addSolid(col,n,Math.ceil(w*2),Math.ceil(h*2),1);l.threeDLayer=true;l.transform.anchorPoint.setValue([0,0,0]);l.transform.position.setValue(xyz(x,y,1));return l;}
function original(l){l.parent=world;var blur=l.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');blur.property(2).setValue(1);originals.push({layer:l,color:color(l),blur:blur.property(1)});return l;}
function flow(n,s,size,x,y,width,offset){
 var rx=/\S+/g,m,xx=x,yy=y,result=[];
 while((m=rx.exec(s))!==null){var l=text(n+'_'+m.index,m[0],size,xx,yy,true),b=l.sourceRectAtTime(0,false),w=b.width/2;
  if(xx+w>x+width&&xx>x){xx=x;yy+=62;}l.transform.position.setValue(xyz(xx,yy,0));
  l.comment=JSON.stringify({field:n,range:[offset+m.index,offset+m.index+m[0].length],text:m[0],asset_id:H.asset_id});
  result.push({layer:l,x:xx,y:yy,w:w,text:m[0],start:offset+m.index,end:offset+m.index+m[0].length});original(l);xx+=w+size*.24;
 }return result;
}
function phrase(list,start,end,name,at,arrival,targetX,targetY,back){
 var nodes=[],selected=[],total=0,i;
 for(i=0;i<list.length;i++)if(list[i].start>=start&&list[i].end<=end){selected.push(list[i]);nodes.push(list[i].layer);}
 if(!nodes.length)throw Error('No original source for '+name);
 for(i=0;i<selected.length;i++)total+=selected[i].w*72/46+18;
 var first=selected[0],last=selected[selected.length-1];
 if(first.y!==last.y)throw Error('Proof highlight needs one measured source line');
 var highlight=rect('LOCATE_'+name,first.x-3,first.y-42,last.x+last.w-first.x+6,54,rgb(name==='OPTION_KEYWORD'?'#3A6A8A':'#C8622E'));
 highlight.parent=world;highlight.inPoint=at-.6;highlight.outPoint=at+.15;highlight.transform.opacity.setValue(75);highlight.moveAfter(nodes[0]);
 var cfg={name:name,locate:at-.6,locateFrames:10,start:at,end:back+2,color:[[at,at<3.6?ink:paper],[at<3.6?2.7:arrival,paper],[back,paper],[11,ink]],tracks:[]};
 var x=targetX,ratio=(2400-200)/2400;
 for(i=0;i<selected.length;i++){
  var w=selected[i],depth=world.transform.position.valueAtTime(at,false)[2],origin=[w.x*2,w.y*2,depth],home=xyz(w.x,w.y,0),target=xyz(960+(x-960)*ratio,540+(targetY-540)*ratio,-200);
  // One direct continuous trajectory. Never create an unrelated title layer.
  cfg.tracks.push({position:[[at,origin],[arrival,target],[back,target],[back+2,home]],
   scale:[[at,[100,100,100]],[arrival,[72/46*ratio*100,72/46*ratio*100,100]],[back,[72/46*ratio*100,72/46*ratio*100,100]],[back+2,[100,100,100]]],
   opacity:[[at,100],[back+1.75,100],[back+2,0]]});
  audit.push({name:name,source:JSON.parse(w.layer.comment),origin:origin,target:target,start:at,arrive:arrival,return_end:back+2});x+=w.w*72/46+18;
 }
 return lift_phrase(nodes,highlight,cfg);
}
try{
 if(app.project.renderQueue.rendering)throw Error('AE busy');if(new File(out+'/DARK_FIELD.aep').exists)throw Error('Preserve previous project');
 if(app.project.numItems)app.project.save(new File(out+'/SESSION_BEFORE.aep'));app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=16;
 cp=app.project.items.addComp('DARK_FIELD_COMBINED_20',3840,2160,1,20,24);cp.renderer='ADBE Classic 3D';cp.motionBlur=true;cp.shutterAngle=90;
 var bg=cp.layers.addSolid(paper,'ENVIRONMENT',3840,2160,1);var fx=bg.property('ADBE Effect Parade').addProperty('ADBE Fill'),bgColor=fx.property('ADBE Fill-0002');
 var world=cp.layers.addNull();world.name='REALITY';world.threeDLayer=true;world.transform.position.setValue([0,0,0]);world.enabled=false;
 var stem=original(text('QUESTION',H.source.stem,48,96,126,true));
 var offset=H.source.passage.indexOf('Dogs are known');if(offset<0)throw Error('Frozen paragraph missing');
 words=flow('passage',H.source.passage.slice(offset),46,96,280,1040,offset);
 var opts={},optionLayers=[];
 for(var i=0;i<4;i++){var letter='ABCD'.charAt(i),lab=original(text('OPTION_'+letter,letter+'.',44,1240,280+i*146,true));var ls=flow('options/'+letter,H.source.options[letter],46,1300,280+i*146,530,0);opts[letter]=ls;optionLayers.push(lab);for(var j=0;j<ls.length;j++)optionLayers.push(ls[j].layer);}
 var camera=cp.layers.addCamera('CAMERA',[1920,1080]);camera.transform.position.setValue(xyz(960,540,-2400));camera.transform.pointOfInterest.setValue(xyz(960,540,0));
 var co=camera.property('ADBE Camera Options Group');co.property('ADBE Camera Zoom').setValue(4800);co.property('ADBE Camera Depth of Field').setValue(1);co.property('ADBE Camera Aperture').setValue(36);co.property('ADBE Camera Focus Distance').setValue(4800);
 var field={background:[[0,paper],[1.6,paper],[3.6,dark],[10,dark],[12,paper],[14,paper],[15,dark],[20,dark]],
  originalColor:[[0,ink],[1.6,ink],[2.1,muted],[10,muted],[12,ink],[14,ink],[15,muted]],
  depth:[[0,[0,0,0]],[1.6,[0,0,0]],[3.6,[0,0,1200]],[10,[0,0,1200]],[12,[0,0,0]],[14,[0,0,0]],[15,[0,0,1200]]],
  blur:[[0,0],[1.6,0],[2.1,24],[3.6,6.4],[10,6.4],[10.4,24],[12,0],[14,0],[15,6.4]]};
 transition_to_dark_field(bgColor,originals,world,field);
 var p=H.projections[2];phrase(words,p.range[0],p.range[1],'EVIDENCE',1.6,3.5,200,470,10);
 // Option words have a different source size; keep exact 46px in this mechanical proof.
 var op=H.source.options.D,from=op.indexOf('Keep');
 // D spans two lines in the original. Lift only the literal one-line keyword
 // Healthy; it remains an option-word comparison, never a new teaching claim.
 from=op.indexOf('Healthy');phrase(opts.D,from,from+7,'OPTION_KEYWORD',5.6,7.1,200,640,10);
 var blue=rect('COMPARISON_PLANE',186,570,340,100,rgb('#3A6A8A'));blue.inPoint=7.1;blue.outPoint=10;blue.transform.opacity.setValue(40);blue.moveAfter(cp.layer('OPTION_KEYWORD_0'));
 // The judgment test shows all three existing frozen evidence summaries first.
 for(i=0;i<3;i++){var e=text('REVIEWED_EVIDENCE_'+i,H.projections[i].text,60,96,370+i*100,false);color(e).setValue(paper);e.inPoint=15;e.outPoint=20;}
 var judgement=text('FROZEN_ACTION_RESULT','排除 D',100,96,860,false);color(judgement).setValue(paper);judgement.inPoint=17;judgement.outPoint=20;
 var dl=[cp.layer('OPTION_D')];for(i=0;i<opts.D.length;i++)dl.push(opts.D[i].layer);
 // At z=600, 30 author units project to exactly 24 screen pixels.
 for(i=0;i<dl.length;i++){var pos=dl[i].transform.position.valueAtTime(17,false);SG_keys(dl[i].transform.position,[[17,pos],[17+10/24,[pos[0],pos[1]+60,pos[2]]]],false);SG_keys(dl[i].transform.opacity,[[17,100],[17+10/24,20]],false);}
 var label=text('PROOF_LABEL','明暗 / 原位提取测试',28,96,1010,false);SG_keys(color(label),field.originalColor,false);
 // Render the background as one physical world. Blurring every native word
 // separately allocates a 4K buffer per glyph and makes this simple proof slow.
 // Original glyph layer identities survive precomposition; foreground copies
 // remain in the main world with their exact measured source trajectories.
 var indices=[world.index];for(i=0;i<originals.length;i++){var ol=originals[i].layer;while(ol.property('ADBE Effect Parade').numProperties)ol.property('ADBE Effect Parade').property(1).remove();indices.push(ol.index);}
 for(i=1;i<=cp.numLayers;i++)if(cp.layer(i).name.indexOf('LOCATE_')===0)indices.push(i);
 var reality=cp.layers.precompose(indices,'REALITY_WORLD',true);camera.copyToComp(reality);
 reality.layer(1).property('ADBE Camera Options Group').property('ADBE Camera Depth of Field').setValue(0);
 var realityLayer=cp.layer('REALITY_WORLD'),worldBlur=realityLayer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');SG_keys(worldBlur.property(1),field.blur,false);realityLayer.moveToEnd();bg.moveToEnd();
 var proxy=app.project.items.addComp('PROOF_1080',1920,1080,1,20,24),nest=proxy.layers.add(cp);nest.transform.scale.setValue([50,50]);
 var light=app.project.items.addComp('LIGHT_TEST_10',3840,2160,1,10,24);light.layers.add(cp);
 var lift=app.project.items.addComp('LIFT_TEST_5',3840,2160,1,5,24);lift.layers.add(cp);
 app.project.save(new File(out+'/DARK_FIELD.aep'));
 var values=[];for(i=0;i<cp.numLayers;i++){var l=cp.layer(i+1);if(l.name.indexOf('EVIDENCE_')===0||l.name.indexOf('OPTION_KEYWORD_')===0){var samples=[];for(j=0;j<=480;j++)samples.push({t:j/24,p:l.transform.position.valueAtTime(j/24,false),s:l.transform.scale.valueAtTime(j/24,false),o:l.transform.opacity.valueAtTime(j/24,false)});values.push({name:l.name,samples:samples});}}
 save('NATIVE_READBACK.json',JSON.stringify({mode:H.proof.mode,origin:audit,tracks:values,contrast:H.proof.contrast,background0:bgColor.valueAtTime(0,false),background4_5:bgColor.valueAtTime(4.5,false),master:cp.id}));
 save('COMP_ID.txt',String(cp.id));save('PROXY_ID.txt',String(proxy.id));
 for(i=0;i<5;i++){var t=[0,2.5,4.5,8,18][i];proxy.saveFrameToPng(t,new File(out+'/FRAME_'+t+'.png'));}
 save('BUILD_DONE.txt','Native proof complete');
}catch(e){save('ERROR.txt',e.toString()+' line '+e.line);}
})();
