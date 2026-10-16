// One native question; accepted dark-field functions, exact originals and WAVs.
(function(){
var H=DQ_INPUT.plan,out=DQ_INPUT.output,cp,originals=[],words=[],origins=[],clips=[];
function save(n,v){var f=new File(out+'/'+n);f.encoding='UTF-8';f.open('w');f.write(v);f.close();}
function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
function xyz(x,y,z){return [x*2,y*2,(z||0)*2];}
var pal=H.style.palette,sz=H.style.type_scale,paper=rgb(pal.paper),ink=rgb(pal.ink),dark=rgb(pal.environment),muted=rgb('#42464A');
function text(n,s,size,x,y,three){var l=cp.layers.addText(s),d=l.property('Source Text').value;
 d.font=/[\u3400-\u9fff]/.test(s)?H.renderer_fonts.caption:H.renderer_fonts.english;d.fontSize=size*2;d.fillColor=ink;d.applyStroke=false;
 l.property('Source Text').setValue(d);if(l.property('Source Text').value.font!==d.font)throw Error('Font substitution '+d.font);
 l.name=n;l.threeDLayer=three;l.motionBlur=three;var b=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue(three?[b.left,0,0]:[b.left,0]);l.transform.position.setValue(three?xyz(x,y,0):[x*2,y*2]);return l;}
function color(l){var a=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');a.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color');return a.property('ADBE Text Animator Properties').property('ADBE Text Fill Color');}
function rect(n,x,y,w,h,col,three){var l=cp.layers.addSolid(col,n,Math.ceil(w*2),Math.ceil(h*2),1);l.threeDLayer=three;l.transform.anchorPoint.setValue(three?[0,0,0]:[0,0]);l.transform.position.setValue(three?xyz(x,y,1):[x*2,y*2]);return l;}
function original(l){l.parent=world;var fx=l.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');fx.property(2).setValue(1);originals.push({layer:l,color:color(l),blur:fx.property(1)});return l;}
function flow(n,s,size,x,y,width,offset){var rx=/\S+/g,m,xx=x,yy=y,result=[];
 while((m=rx.exec(s))!==null){var l=text(n+'_'+(offset+m.index),m[0],size,xx,yy,true),b=l.sourceRectAtTime(0,false),w=b.width/2;
 if(xx+w>x+width&&xx>x){xx=x;yy+=sz.focus_line_height;}l.transform.position.setValue(xyz(xx,yy,0));
 l.comment=JSON.stringify({field:n,range:[offset+m.index,offset+m.index+m[0].length],text:m[0],asset_id:H.asset_id});
 result.push({layer:l,x:xx,y:yy,w:w,size:size,text:m[0],start:offset+m.index,end:offset+m.index+m[0].length});original(l);xx+=w+size*.24;}return result;}
function camera(name){var c=cp.layers.addCamera(name,[1920,1080]);c.transform.position.setValue(xyz(960,540,-2400));c.transform.pointOfInterest.setValue(xyz(960,540,0));var o=c.property('ADBE Camera Options Group');o.property('ADBE Camera Zoom').setValue(4800);o.property('ADBE Camera Depth of Field').setValue(0);return c;}
function selected(list,a,b){var r=[];for(var j=0;j<list.length;j++)if(list[j].start>=a&&list[j].end<=b)r.push(list[j]);if(!r.length)throw Error('No original words');return r;}
function setMask(l,bottom){var m=l.property('ADBE Mask Parade').addProperty('ADBE Mask Atom'),s=new Shape();s.vertices=[[180,360],[2390,360],[2390,bottom*2],[180,bottom*2]];s.closed=true;s.inTangents=[[0,0],[0,0],[0,0],[0,0]];s.outTangents=s.inTangents;m.property('ADBE Mask Shape').setValue(s);return m;}
function lift(list,a,b,index){var selectedWords=selected(list,a,b),nodes=[],at=H.integration.lifts[index].start_frame/24,end=H.integration.lifts[index].end_frame/24,back=H.integration.lifts[index].return_at;
 var first=selectedWords[0],last=selectedWords[selectedWords.length-1],scroll=index<3?scrollFor[index]:0;
 if(first.y!==last.y)throw Error('Selected phrase crosses source lines; adjust native layout');
 var fill=rect('LOCATE_'+index,first.x-3,first.y-first.size*.9,last.x+last.w-first.x+6,first.size*1.18,rgb(index===3?pal.comparison_blue:pal.attention_orange),true);
 fill.parent=world;fill.inPoint=at-10/24;fill.outPoint=at+.1;fill.transform.opacity.setValue(75);fill.moveAfter(first.layer);
 var cfg={name:'LIFT_'+index,locate:at-10/24,locateFrames:10,start:at,end:back+1.5,
 color:[[at,paper],[36.25,ink]],tracks:[]},x=200,y=570+index*100,ratio=2200/2400;
 for(var j=0;j<selectedWords.length;j++){var w=selectedWords[j],origin=xyz(w.x,w.y-scroll,600),home=xyz(w.x,w.y-scroll+(index===3?24:0),0),target=xyz(960+(x-960)*ratio,540+(y-540)*ratio,-200),sc=sz.comparison/w.size*ratio*100;
 cfg.tracks.push({position:[[at,origin],[end,target],[back,target],[back+1.5,home]],scale:[[at,[100,100,100]],[end,[sc,sc,100]],[back,[sc,sc,100]],[back+1.5,[100,100,100]]],opacity:[[at,100],[back+1.35,100],[back+1.5,0]]});nodes.push(w.layer);
 origins.push({group:index,original:JSON.parse(w.layer.comment),origin:origin,target:target,home:home,start:at,arrival:end,return_at:back,return_end:back+1.5});x+=w.w*sz.comparison/w.size+18;}
 var lifted=lift_phrase(nodes,fill,cfg);for(j=0;j<lifted.length;j++)clips.push(lifted[j]);
 if(index===3){var blue=rect('COMPARISON_BLUE',186,795,x-186+8,92,rgb(pal.comparison_blue),false);blue.inPoint=end;blue.outPoint=back;blue.transform.opacity.setValue(40);blue.moveAfter(lifted[0]);}
 return fill;
}
try{
 if(app.project.renderQueue.rendering)throw Error('AE busy');if(new File(out+'/CONTINUOUS_QUESTION.aep').exists)throw Error('Preserve earlier revision');
 if(app.project.numItems)app.project.save(new File(out+'/SESSION_BEFORE.aep'));app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();app.project.bitsPerChannel=16;
 cp=app.project.items.addComp('QUESTION_WORLD_4K',3840,2160,1,70,24);cp.renderer='ADBE Classic 3D';cp.motionBlur=true;cp.shutterAngle=90;
 var bg=cp.layers.addSolid(paper,'ENVIRONMENT',3840,2160,1),fx=bg.property('ADBE Effect Parade').addProperty('ADBE Fill'),bgColor=fx.property('ADBE Fill-0002');
 var world=cp.layers.addNull();world.name='REALITY';world.threeDLayer=true;world.transform.position.setValue([0,0,0]);world.enabled=false;
 var stem=original(text('QUESTION',H.source.stem,sz.question,96,126,true));
 // The complete frozen passage remains one ordered native source world.
 words=flow('passage',H.source.passage,sz.focus_text,96,250,1080,0);
 var opts={},optionLayers=[stem];for(var i=0;i<4;i++){var letter='ABCD'.charAt(i),lab=original(text('OPTION_'+letter,letter+'.',sz.option,1240,230+i*105,true));var ls=flow('options/'+letter,H.source.options[letter],sz.option,1300,230+i*105,530,0);opts[letter]=ls;optionLayers.push(lab);for(var j=0;j<ls.length;j++)optionLayers.push(ls[j].layer);}
 var cam=camera('FIXED_WORLD_CAMERA');
 var field={background:[[0,paper],[16,paper],[16.5,dark],[36,dark],[36.5,paper]],originalColor:[[0,ink],[16,ink],[16.5,muted],[36,muted],[36.5,ink]],depth:[[0,[0,0,0]],[16,[0,0,0]],[16.5,[0,0,1200]],[36,[0,0,1200]],[36.5,[0,0,0]]],blur:[[0,0],[16,0],[16.25,24],[16.5,6.4],[36,6.4],[36.25,24],[36.5,0]]};
 transition_to_dark_field(bgColor,originals,world,field);
 var scrollFor=[],centers=[];for(i=0;i<3;i++){var p=H.projections[i],sel=selected(words,p.range[0],p.range[1]);centers.push(sel[0].y);scrollFor.push(sel[0].y-330);}
 // Slow reading and faster changes between the three already-bound evidence locations.
 var scrollRows=[[0,0],[4,0],[7.25,Math.max(0,centers[0]-300)],[8,Math.max(0,centers[1]-500)],[11.25,centers[1]-250],[12,Math.max(0,centers[2]-450)],[15.5,centers[2]-250],[17.4,scrollFor[0]],[19.8,scrollFor[0]],[20.1,scrollFor[1]],[22.55,scrollFor[1]],[23.1,scrollFor[2]],[36,scrollFor[2]],[36.9,scrollFor[0]],[38.6,scrollFor[0]],[39.8,scrollFor[1]],[41.6,scrollFor[1]],[42.8,scrollFor[2]],[49.9,scrollFor[2]],[60,scrollFor[2]],[70,scrollFor[2]]];
 var fills=[];for(i=0;i<3;i++){p=H.projections[i];fills.push(lift(words,p.range[0],p.range[1],i));}
 var from=H.source.options.D.indexOf('Healthy');if(from<0)throw Error('Bound D keyword missing');fills.push(lift(opts.D,from,from+7,3));
 var dl=[cp.layer('OPTION_D')];for(i=0;i<opts.D.length;i++)dl.push(opts.D[i].layer);
 for(i=0;i<dl.length;i++){var pos=dl[i].transform.position.valueAtTime(35.25,false);SG_keys(dl[i].transform.position,[[35.25,pos],[35.25+10/24,[pos[0],pos[1]+60,pos[2]]],[36.5,[pos[0],pos[1]+48,pos[2]]]],false);SG_keys(dl[i].transform.opacity,[[35.25,100],[35.25+10/24,20]],false);}
 var result=text('BOUND_RESULT','排除 D',sz.decision,1230,865,false);color(result).setValue(paper);result.inPoint=35.25;result.outPoint=36;
 // Keep original glyph identities inside a masked reading window. Only its
 // native camera moves; options remain fixed in the same visible question world.
 for(i=0;i<originals.length;i++)while(originals[i].layer.property('ADBE Effect Parade').numProperties)originals[i].layer.property('ADBE Effect Parade').property(1).remove();
 var passageWorld=world.duplicate();passageWorld.name='PASSAGE_DEPTH';var indices=[passageWorld.index];
 for(i=0;i<words.length;i++)words[i].layer.parent=passageWorld;
 for(i=0;i<3;i++)fills[i].parent=passageWorld;
 indices=[passageWorld.index];for(i=0;i<words.length;i++)indices.push(words[i].layer.index);for(i=0;i<3;i++)indices.push(fills[i].index);
 var reading=cp.layers.precompose(indices,'PASSAGE_WORLD',true);cam.copyToComp(reading);var rc=reading.layer(1),posRows=[],poiRows=[];
 for(i=0;i<scrollRows.length;i++){posRows.push([scrollRows[i][0],xyz(960,540+scrollRows[i][1],-2400)]);poiRows.push([scrollRows[i][0],xyz(960,540+scrollRows[i][1],0)]);}
 SG_cameraKeys(rc.transform.position,posRows,[2,4,6]);SG_cameraKeys(rc.transform.pointOfInterest,poiRows,[2,4,6]);
 var readLayer=cp.layer('PASSAGE_WORLD'),mask=setMask(readLayer,850),shape=mask.property('ADBE Mask Shape').value;
 mask.property('ADBE Mask Feather').setValue([0,16]);mask.property('ADBE Mask Shape').setValueAtTime(16,shape);shape.vertices=[[180,500],[2390,500],[2390,990],[180,990]];mask.property('ADBE Mask Shape').setValueAtTime(16.5,shape);
 // Restore the reading window top after the field brightens, without exposing
 // paragraph glyphs over the question stem while the world is recessed.
 mask.property('ADBE Mask Shape').setValueAtTime(36,shape);shape.vertices=[[180,360],[2390,360],[2390,990],[180,990]];mask.property('ADBE Mask Shape').setValueAtTime(36.5,shape);
 var blur=readLayer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');SG_keys(blur.property(1),field.blur,false);
 indices=[world.index,fills[3].index];for(i=0;i<optionLayers.length;i++)indices.push(optionLayers[i].index);var ow=cp.layers.precompose(indices,'QUESTION_OPTIONS_WORLD',true);cam.copyToComp(ow);
 var optLayer=cp.layer('QUESTION_OPTIONS_WORLD'),ob=optLayer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');SG_keys(ob.property(1),field.blur,false);
 readLayer.moveToEnd();optLayer.moveToEnd();bg.moveToEnd();
 var work=cp;cp=app.project.items.addComp('QUESTION_NATIVE_4K',3840,2160,1,70,24);var full=cp.layers.add(work);
 // Visual-only slow replay of exactly the already shown comparison/decision.
 var replay=cp.layers.add(work);replay.name='JUDGMENT_REPLAY_NOT_NEW_DECISION';replay.timeRemapEnabled=true;
 var remap=replay.property('ADBE Time Remapping');remap.setValueAtTime(50,30);remap.setValueAtTime(60,36);for(i=remap.numKeys;i>=1;i--)if(remap.keyTime(i)<50||remap.keyTime(i)>60)remap.removeKey(i);for(i=1;i<=remap.numKeys;i++)remap.setInterpolationTypeAtKey(i,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);replay.inPoint=50;replay.outPoint=60;
 // Review subtitles: original words during speech, neutral operation cues in gaps.
 var cue=[[0,4,'读题'],[4,8,'阅读第一段'],[8,12,'阅读第二段'],[12,16,'阅读第三段'],[16,18,'进入对照'],[18,20,'提取第一段证据'],[20,23,'提取第二段证据'],[23,27,'提取第三段证据'],[27,30,'提取 D 的关键词'],[30,34,'对照三段证据与 D'],[34,36,'判断并排除 D'],[36,40,'原词归位：第一段'],[40,43,'原词归位：第二段'],[43,46,'原词归位：第三段'],[46,50,'选项关键词归位'],[50,55,'慢放复盘：对照'],[55,60,'慢放复盘：排除 D'],[60,70,'方法记忆']];
 var captionRecords=[];
 function caption(s,a,b,kind){if(b<=a)return;var l=text('CAPTION_'+captionRecords.length,s,36,0,970,false),d=l.property('Source Text').value;d.font=H.renderer_fonts.caption;l.property('Source Text').setValue(d);var r=l.sourceRectAtTime(0,false);l.transform.position.setValue([(3840-r.width)/2,1940]);color(l).setValue(paper);l.inPoint=a;l.outPoint=b;var pad=rect('CAPTION_BACK_'+captionRecords.length,(3840-r.width)/4-18,925,r.width/2+36,62,ink,false);pad.transform.opacity.setValue(60);pad.inPoint=a;pad.outPoint=b;pad.moveAfter(l);captionRecords.push({start:a,end:b,text:s,kind:kind,width:r.width/2});}
 var spoken=[];for(i=0;i<H.voices.length;i++){var v=H.voices[i],total=0;for(j=0;j<v.caption_parts.length;j++)total+=v.caption_parts[j].length;var cursor=v.start_frame;for(j=0;j<v.caption_parts.length;j++){var endFrame=j===v.caption_parts.length-1?v.end_frame:cursor+Math.round((v.end_frame-v.start_frame)*v.caption_parts[j].length/total);caption(v.caption_parts[j],cursor/24,endFrame/24,'exact_voice');cursor=endFrame;}spoken.push([v.start_frame/24,v.end_frame/24]);}
 for(i=0;i<cue.length;i++){var pieces=[[cue[i][0],cue[i][1]]];for(j=0;j<spoken.length;j++){var next=[];for(var k=0;k<pieces.length;k++){var a=pieces[k][0],b=pieces[k][1];if(spoken[j][1]<=a||spoken[j][0]>=b)next.push([a,b]);else{if(a<spoken[j][0])next.push([a,spoken[j][0]]);if(b>spoken[j][1])next.push([spoken[j][1],b]);}}pieces=next;}for(j=0;j<pieces.length;j++)if(pieces[j][1]-pieces[j][0]>.25)caption(cue[i][2],pieces[j][0],pieces[j][1],'review_operation');}
 var stamp=text('METHOD_MEMORY',H.memory_line,60,200,780,false);stamp.inPoint=60;var mr=stamp.sourceRectAtTime(60,false);stamp.transform.position.setValue([(3840-mr.width)/2,1560]);var method=text('METHOD_NAME','标题对照',36,200,680,false);method.inPoint=60;var mt=method.sourceRectAtTime(60,false);method.transform.position.setValue([(3840-mt.width)/2,1360]);
 // The memory sentence occupies the empty foreground; no pale veil over originals.
 var proxy=app.project.items.addComp('QUESTION_REVIEW_1080',1920,1080,1,70,24),nest=proxy.layers.add(cp);nest.transform.scale.setValue([50,50]);
 app.project.save(new File(out+'/CONTINUOUS_QUESTION.aep'));save('RENDER_COMP_ID.txt',String(cp.id));save('PROXY_COMP_ID.txt',String(proxy.id));
 save('NATIVE_GEOMETRY.json',JSON.stringify({origins:origins,captions:captionRecords,scroll:scrollRows,field:field,review:[1920,1080],duration:70,public_render_ready:false}));
 for(i=0;i<10;i++){var t=[2,10,17,19,24,30.5,35.8,43,58.9,64][i];proxy.saveFrameToPng(t,new File(out+'/FRAME_'+t+'.png'));}
 save('BUILD_DONE.txt','70s native question prepared; 1080 review only');
}catch(e){save('ERROR.txt',e.toString()+' line '+e.line);}
})();
