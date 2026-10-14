// Independent P1 static storyboard. Request contains local frozen excerpts only.
(function () {
  var r=DUAL_SPACE_DATA;
  // Standalone ExtendScript has no JSON global; input is a generated JS literal.
  function encode(o){if(o===null)return 'null';if(typeof o==='string')return '"'+o.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n').replace(/\t/g,'\\t')+'"';if(typeof o==='number'||typeof o==='boolean')return String(o);var a=[],k;if(o instanceof Array){for(k=0;k<o.length;k++)a.push(encode(o[k]));return '['+a.join(',')+']';}for(k in o)if(o.hasOwnProperty(k))a.push(encode(k)+':'+encode(o[k]));return '{'+a.join(',')+'}';}
  function save(p,o){var q=new File(p);q.encoding='UTF-8';if(!q.open('w'))throw Error('Cannot write receipt');q.write(encode(o));q.close();}
  try {
    if(app.project.renderQueue.rendering)throw Error('Render already active');
    if(app.project.numItems){if(!r.preserve_session_path || new File(r.preserve_session_path).exists)throw Error('Fresh session checkpoint path required');app.project.save(new File(r.preserve_session_path));}
    app.newProject();app.project.bitsPerChannel=16;
    var results=[],cp,dim=false,fonts=[];
    function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    function mat(l,lit,shadow){var m=l.property('ADBE Material Options Group');m.property('ADBE Accepts Lights').setValue(lit?1:0);m.property('ADBE Casts Shadows').setValue(shadow?1:0);m.property('ADBE Accepts Shadows').setValue(1);}
    function rect(name,x,y,w,h,c,z,lit){var l=cp.layers.addSolid(rgb(c),name,Math.ceil(w),Math.ceil(h),1);l.threeDLayer=true;l.transform.position.setValue([x+w/2,y+h/2,z]);mat(l,lit,false);return l;}
    function txt(name,s,x,y,size,c,font,z,lit){var l=cp.layers.addText(s),p=l.property('Source Text'),d=p.value;d.font=font;d.fontSize=size;d.fillColor=rgb(c);d.applyFill=true;d.applyStroke=false;d.leading=size*1.32;d.autoLeading=false;p.setValue(d);if(p.value.font!==font)fonts.push({wanted:font,actual:p.value.font});l.name=name;l.threeDLayer=true;l.transform.position.setValue([x,y,z]);mat(l,lit,!lit&&z<0);return l;}
    function wrap(s,font,size,width){if(s.indexOf('\n')>=0){var chunks=s.split(/\r?\n/),wrapped=[];for(var n=0;n<chunks.length;n++)wrapped.push(wrap(chunks[n],font,size,width));return wrapped.join('\r');}var a=s.split(/\s+/),lines=[],line='',probe=cp.layers.addText(''),p=probe.property('Source Text'),d=p.value;d.font=font;d.fontSize=size;for(var j=0;j<a.length;j++){var next=line?line+' '+a[j]:a[j];d.text=next;p.setValue(d);if(probe.sourceRectAtTime(0,false).width>width&&line){lines.push(line);line=a[j];}else line=next;}if(line)lines.push(line);probe.remove();return lines.join('\r');}
    for(var i=0;i<r.frames.length;i++){
      var s=r.frames[i],eng=s.font||'SourceSerif4-Regular';dim=s.dark;fonts=[];
      cp=app.project.items.addComp(s.id,1920,1080,1,1,24);cp.renderer='ADBE Classic 3d';cp.bgColor=rgb('#17181A');cp.layers.addSolid(rgb('#17181A'),'ENVIRONMENT',1920,1080,1);
      rect('PAPER',96,64,1728,860,'#F2F0EA',dim?600:0,true);
      txt('SOURCE_HEADING',s.source_label,150,125,28,'#20211F','NotoSansSC-StyleV1Medium',dim?599:-1,true);
      txt('SOURCE_PASSAGE',wrap(s.passage.replace(/\r?\n/g,' '),eng,dim?25:46,dim?1040:1450),160,210,dim?25:46,'#20211F',eng,dim?599:-1,true);
      if(dim)txt('SOURCE_OPTIONS',wrap(s.options,eng,28,440),1300,220,28,'#20211F',eng,dim?599:-1,true);
      var amb=cp.layers.addLight('WORLD_AMBIENT',[960,540]);amb.lightType=LightType.AMBIENT;amb.property('ADBE Light Options Group').property('ADBE Light Intensity').setValue(dim?5:30);
      var key=cp.layers.addLight('PAPER_KEY',[800,200]);key.lightType=LightType.SPOT;key.transform.position.setValue([500,50,-1600]);key.transform.pointOfInterest.setValue([960,500,0]);var lo=key.property('ADBE Light Options Group');lo.property('ADBE Light Intensity').setValue(dim?20:70);lo.property('ADBE Light Cone Angle').setValue(110);lo.property('ADBE Light Cone Feather 2').setValue(85);lo.property('ADBE Casts Shadows').setValue(1);lo.property('ADBE Light Shadow Darkness').setValue(22);lo.property('ADBE Light Shadow Diffusion').setValue(70);
      var z=-220,fg=dim?'#F2F0EA':'#20211F';
      if(s.heading)txt('FOCUS_TITLE',s.heading,230,300,48,fg,'NotoSansSC-StyleV1Medium',z,false);
      for(var k=0;k<s.lines.length;k++){var ln=s.lines[k],x=230,y=430+k*(s.lines[0].size>100?200:115);
        if(ln.highlight)rect('ATTENTION_'+k,x-12,y-ln.size,Math.min(ln.width||1100,1400),ln.size*1.3,ln.highlight==='orange'?'#C8622E':'#3A6A8A',z+1,false);
        txt('EXTRACT_'+k,ln.text,x,y,ln.size,ln.highlight==='orange'?'#10110F':fg,ln.chinese?'NotoSansSC-StyleV1Medium':eng,z,false);
      }
      var caption=txt('CAPTION',s.vo,150,994,36,'#F2F0EA','NotoSansSC-StyleV1Medium',0,false);caption.threeDLayer=false;caption.transform.position.setValue([150,994]);
      var camera=cp.layers.addCamera('P1_CAMERA',[960,540]);camera.transform.position.setValue([960,540,-2400]);camera.transform.pointOfInterest.setValue([960,540,0]);var co=camera.property('ADBE Camera Options Group');co.property('ADBE Camera Zoom').setValue(2400);co.property('ADBE Camera Depth of Field').setValue(dim?1:0);co.property('ADBE Camera Focus Distance').setValue(dim?2180:2400);co.property('ADBE Camera Aperture').setValue(dim?360:60);
      var master=app.project.items.addComp(s.id+'_4K',3840,2160,1,1,24),nested=master.layers.add(cp);nested.transform.scale.setValue([200,200]);nested.transform.position.setValue([1920,1080]);
      master.saveFrameToPng(0,new File(r.output+'/'+s.id+'.png'));
      results.push({id:s.id,font_substitutions:fonts,frame:[3840,2160],native_render:true,static_only:true});save(r.output+'/progress.json',results);
    }
    app.project.save(new File(r.output+'/P1_DUAL_SPACE.aep'));save(r.output+'/native-receipt.json',{frames:results,motion_tested:false,public_render_ready:false});
  }catch(e){save(r.output+'/native-error.json',{message:e.toString(),line:e.line});}
})();
