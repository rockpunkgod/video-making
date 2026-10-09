// Same original words, existing reviewed condition/evidence, no grammatical peel.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';f.open('r');var r=JSON.parse(f.read());f.close();return r;}
    var R=load(INTEGRATION_REQUEST),dest=new File(R.project);if(dest.exists||app.project.renderQueue.rendering)throw Error('New idle project required');
    app.open(new File(R.locating_project));app.project.save(dest);var cp=null;
    for(var i=1;i<=app.project.numItems;i++){var it=app.project.item(i);if(it instanceof CompItem&&it.name==='FULLTEXT_SOURCE_ACQUISITION')cp=it;}
    if(!cp||JSON.parse(cp.comment).locating_patch_sha!==R.patch_sha)throw Error('Approved native source required');
    var original=[],oldSamples=[];
    function wordAudit(){var out=[];for(var k=0;k<R.words.length;k++){var w=R.words[k],l=cp.layer(w.id),d=l.property('Source Text').value;out.push({id:w.id,layer_id:l.id,text:d.text,comment:l.comment});}return out;}
    function samples(){var out=[],times=[0,3.5,6.5,8,13.25,19.5];for(var k=0;k<R.words.length;k+=31){var l=cp.layer(R.words[k].id);for(var t=0;t<times.length;t++)out.push({id:l.id,t:times[t],p:l.transform.position.valueAtTime(times[t],false),s:l.transform.scale.valueAtTime(times[t],false),o:l.transform.opacity.valueAtTime(times[t],false)});}return out;}
    var before=wordAudit();oldSamples=samples();for(i=1;i<=cp.numLayers;i++)original.push(cp.layer(i));
    var camera=cp.layer('GUIDED_CAMERA'),focus=cp.layer('FOCUS_TARGET'),cam=camera.transform.position.valueAtTime(20,false),look=camera.transform.pointOfInterest.valueAtTime(20,false),zoom=camera.property('ADBE Camera Options Group').property('ADBE Camera Zoom').valueAtTime(20,false),z=-280;
    var ratio=zoom/(z-cam[2]),overviewCam=camera.transform.position.valueAtTime(1,false),overviewLook=camera.transform.pointOfInterest.valueAtTime(1,false),overviewFocus=focus.transform.position.valueAtTime(1,false);
    function world(screen){return [cam[0]+(screen[0]-1920)/ratio,cam[1]+(screen[1]-1080)/ratio,z];}
    // Layout uses AE's actual glyph bounds and camera projection, not estimated advances.
    for(var stateName in R.layouts){R.states[stateName]={};var layouts=R.layouts[stateName];
        for(var ui=0;ui<R.units.length;ui++){var unitLayout=layouts[R.units[ui].id];if(!unitLayout)continue;
            var left=unitLayout[0],line=unitLayout[1],size=unitLayout[3],scale=100*size/24/ratio;
            for(var wi=0;wi<R.units[ui].word_ids.length;wi++){var wordId=R.units[ui].word_ids[wi],bounds=cp.layer(wordId).sourceRectAtTime(0,false),width=bounds.width*size/24;
                if(left+width>unitLayout[0]+unitLayout[2]&&left>unitLayout[0]){left=unitLayout[0];line+=size*1.45;}
                R.states[stateName][wordId]={screen:[left-bounds.left*size/24,line],scale:scale};left+=width+size*.36;
            }
        }
    }
    function wrap(p,rows){var old=(p.expression||'value').replace(/;\s*$/,'');p.expression='if(time<=20){'+old+';}else{(function(){var rows='+JSON.stringify(rows)+';function q(u){return u*u*u*(10+u*(-15+6*u));}for(var i=1;i<rows.length;i++){if(time<rows[i][0]){var a=rows[i-1],b=rows[i],u=q(Math.max(0,Math.min(1,(time-a[0])/(b[0]-a[0]))));return a[1]*(1-u)+b[1]*u;}}return rows[rows.length-1][1];})();}';}
    function windows(){return [[20,'condition'],[22,'memory'],[23,'hard'],[24.7,'low'],[26,'pair'],[27,'process'],[30,'scope'],[33,'restore'],[35,'pair'],[37,'pair'],[40,'condition'],[44,'memory'],[47,'hard'],[51.5,'low'],[56,'pair'],[59,'process'],[68,'scope'],[76,'restore'],[83,'pair'],[87,'pair']];}
    var W=windows();
    for(i=0;i<R.words.length;i++){
        var w=R.words[i],l=cp.layer(w.id),unit=null;
        for(var u=0;u<R.units.length;u++)if(R.units[u].word_ids.indexOf(w.id)!==-1)unit=R.units[u].id;
        var origin=l.transform.position.valueAtTime(20,false),scale=l.transform.scale.valueAtTime(20,false),opacity=l.transform.opacity.valueAtTime(20,false),pp=[[20,origin]],ss=[[20,scale]],oo=[[20,opacity]];
        function state(name){var st=R.states[name]&&R.states[name][w.id];if(name==='restore')return {p:[w.position[0]*2,w.position[1]*2,0],s:[200,200,200],o:100};if(name==='condition'&&unit==='condition')return {p:origin,s:scale,o:100};if(!st)return {p:origin,s:scale,o:0};
            var depth=unit==='condition'?180:-360,alpha=unit==='condition'?72:100;if(name==='low'&&unit==='hard'){depth=180;alpha=68;}if(name==='pair'&&(unit==='hard'||unit==='low'))depth=-280;
            var projection=zoom/(depth-cam[2]),p=[cam[0]+(st.screen[0]-1920)/projection,cam[1]+(st.screen[1]-1080)/projection,depth],s=st.scale*ratio/projection;
            return {p:p,s:[s,s,s],o:alpha};}
        for(var j=0;j<W.length;j++){var at=W[j][0],name=W[j][1],st=state(name),prev=j?state(W[j-1][1]):{p:origin,s:scale,o:opacity},lead=name===unit||(name==='pair'&&(unit==='hard'||unit==='low'))||(name==='scope'&&unit==='coverage')||(name==='memory'&&unit==='condition')||name==='restore',delay=lead?0:2/24;
            if(j){pp.push([at,prev.p]);ss.push([at,prev.s]);oo.push([at,prev.o]);if(delay){pp.push([at+delay,prev.p]);ss.push([at+delay,prev.s]);oo.push([at+delay,prev.o]);}}
            pp.push([at+delay+.5,st.p]);ss.push([at+delay+.5,st.s]);oo.push([at+delay+.5,st.o]);}
        wrap(l.transform.position,pp);wrap(l.transform.scale,ss);wrap(l.transform.opacity,oo);l.outPoint=R.source_duration;
    }
    for(i=0;i<original.length;i++){var l=original[i];l.outPoint=R.source_duration;
        if(l.name.indexOf('PAPER_')===0||l.name.indexOf('LOCATING_TRANSIENT_')===0||l.name==='ACQUIRED_WORDS'||l.name==='QUESTION_TARGET')wrap(l.transform.opacity,[[20,l.transform.opacity.valueAtTime(20,false)],[20.35,0],[101.35,0]]);
    }
    function center(names,t){var lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9];for(var ui=0;ui<R.units.length;ui++)if(names.indexOf(R.units[ui].id)!==-1)for(var wi=0;wi<R.units[ui].word_ids.length;wi++){var l=cp.layer(R.units[ui].word_ids[wi]),p=l.transform.position.valueAtTime(t,false),s=l.transform.scale.valueAtTime(t,false),b=l.sourceRectAtTime(0,false),a=[p[0]+b.left*s[0]/100,p[1]+b.top*s[1]/100,p[2]],c=[a[0]+b.width*s[0]/100,a[1]+b.height*s[1]/100,p[2]];for(var axis=0;axis<3;axis++){lo[axis]=Math.min(lo[axis],a[axis]);hi[axis]=Math.max(hi[axis],c[axis]);}}return [(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2];}
    var initialFocus=focus.transform.position.valueAtTime(20,false),fr=[[20,initialFocus]],cr=[[20,cam]],lr=[[20,look]],previousFocus=initialFocus,previousCam=cam,previousLook=look;
    for(var j=1;j<W.length;j++){var at=W[j][0],name=W[j][1],names=name==='pair'?['hard','low']:(name==='restore'?['condition','hard','low','coverage','types']:[name==='memory'?'condition':(name==='scope'?'coverage':name)]),fc=center(names,at+.6),cc,lc;
        if(name==='restore'){cc=[fc[0]+40,fc[1]+40,-3960];lc=[fc[0],fc[1],0];}else{var dx=(fc[0]-initialFocus[0])*.08,dy=(fc[1]-initialFocus[1])*.08;cc=[cam[0]+dx,cam[1]+dy,cam[2]+80];lc=[look[0]+dx,look[1]+dy,look[2]];}
        fr.push([at,previousFocus],[at+.5,fc]);cr.push([at+2/24,previousCam],[at+.6,cc]);lr.push([at+2/24,previousLook],[at+.6,lc]);previousFocus=fc;previousCam=cc;previousLook=lc;
        if(name==='restore'&&at===76){
            // Restore context first, then revisit the already bound condition and samples.
            var verify=[['condition',77],['hard',78.6],['low',80.2]];
            for(var vi=0;vi<verify.length;vi++){var vt=verify[vi][1],vf=center([verify[vi][0]],vt),vc=[cc[0]+(vf[0]-fc[0])*.08,cc[1]+(vf[1]-fc[1])*.08,-3700],vl=[lc[0]+(vf[0]-fc[0])*.08,lc[1]+(vf[1]-fc[1])*.08,0];fr.push([vt,previousFocus],[vt+.7,vf]);cr.push([vt+2/24,previousCam],[vt+.8,vc]);lr.push([vt+2/24,previousLook],[vt+.8,vl]);previousFocus=vf;previousCam=vc;previousLook=vl;}
        }
    }
    wrap(camera.transform.position,cr);wrap(camera.transform.pointOfInterest,lr);wrap(focus.transform.position,fr);
    var opt=camera.property('ADBE Camera Options Group');wrap(opt.property('ADBE Camera Aperture'),[[20,opt.property('ADBE Camera Aperture').valueAtTime(20,false)],[20.5,150],[33,150],[33.6,0],[35,0],[35.6,150],[76,150],[76.6,0],[77,0],[77.7,100],[83,100],[83.6,150],[87.6,150]]);
    // Existing original options re-enter whole. Retirement is direct reviewed comparison.
    for(i=0;i<4;i++){var id='ABCD'.charAt(i),l=cp.layer('ORIGINAL_OPTION_'+id),p=l.transform.position.valueAtTime(20,false),s=l.transform.scale.valueAtTime(20,false),ranges=i===0?[[35.3,37.35],[83.35,87.35]]:(i===1?[[27.2,28.45],[59.2,62.25]]:(i===2?[[28.6,29.9],[62.25,65.75]]:[[30.2,32.9],[68.2,74.25]])),rows=[[20,0]];
        for(var ri=0;ri<ranges.length;ri++)rows.push([ranges[ri][0],0],[ranges[ri][0]+.12,100],[ranges[ri][1]-.12,100],[ranges[ri][1],0]);
        wrap(l.transform.position,[[20,p],[20.35,[500,i===0?1770:670,0]],[87.35,[500,i===0?1770:670,0]]]);wrap(l.transform.opacity,rows);wrap(l.transform.scale,[[20,s],[20.35,[250,250,100]],[87.35,[250,250,100]]]);
        var ob=l.sourceRectAtTime(0,false),om=cp.layers.addShape();om.name='OPTION_FILL_'+id;
        var og=om.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group'),ov=og.property('ADBE Vectors Group');ov.addProperty('ADBE Vector Shape - Rect');ov=om.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');ov.addProperty('ADBE Vector Graphic - Fill');ov=om.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');ov.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([ob.width+6,ob.height+6]);ov.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(i===0?[.95,.74,.43]:[.64,.79,.90]);om.setParentWithJump(l);om.transform.position.setValue([ob.left+ob.width/2,ob.top+ob.height/2]);om.moveAfter(l);om.outPoint=R.source_duration;
        var flashes=[];for(var ri=0;ri<ranges.length;ri++)flashes.push([ranges[ri][0]+.35,Math.min(ranges[ri][1]-.12,ranges[ri][0]+.95)]);visible(om,flashes);
    }
    function text(name,copy,size,pos){var l=cp.layers.addText(copy),p=l.property('Source Text'),d=p.value;d.font='NotoSansSC-Regular';d.fontSize=size;d.fillColor=[.15,.18,.17];d.applyStroke=false;p.setValue(d);l.name=name;l.transform.position.setValue(pos);l.outPoint=R.source_duration;return l;}
    function visible(l,ranges){l.transform.opacity.setValue(0);var rr=[[0,0]];for(var k=0;k<ranges.length;k++){rr.push([ranges[k][0],0],[ranges[k][0]+.15,100],[ranges[k][1]-.15,100],[ranges[k][1],0]);}wrap(l.transform.opacity,rr);}
    var title=text('METHOD_NAME',R.source.method.brand_name,44,[500,280]);visible(title,[[20,21.5],[40,42]]);
    var copies=R.screen_projections;
    var intervals=[[],[],[[65.8,67]],[[74.3,75.5]],[],[]];
    for(i=0;i<copies.length;i++){l=text('FROZEN_SCREEN_'+i,copies[i].text,42,[500,i===0?320:1820]);l.comment=JSON.stringify({source_binding:R.source_binding,segment_ref:copies[i].segment_ref,text_sha:copies[i].text_sha,projection:'existing_frozen_screen_text'});visible(l,intervals[i]);}
    // Brief filled comparison marks behind the same source words; no underline.
    var applicationBack=cp.layer(R.words[0].id);
    for(var bi=1;bi<R.words.length;bi++){var wordBack=cp.layer(R.words[bi].id);if(wordBack.index>applicationBack.index)applicationBack=wordBack;}
    var phrases=R.display_cues.cues;
    for(var a=0;a<phrases.length;a++){var ph=phrases[a],start=ph.span[0],end=ph.span[1];
        for(i=0;i<R.words.length;i++){w=R.words[i];if(w.start<end&&start<w.end){l=cp.layer(w.id);var b=l.sourceRectAtTime(0,false),mark=cp.layers.addShape();mark.name='APPLICATION_FILL_'+a+'_'+w.id;mark.threeDLayer=true;mark.outPoint=R.source_duration;
            var g=mark.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group'),v=g.property('ADBE Vectors Group');v.addProperty('ADBE Vector Shape - Rect');v=mark.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');v.addProperty('ADBE Vector Graphic - Fill');v=mark.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');v.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([b.width+3,b.height+3]);v.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue([.64,.79,.90]);mark.setParentWithJump(l);mark.transform.position.setValue([b.left+b.width/2,b.top+b.height/2,5]);mark.moveAfter(applicationBack);visible(mark,ph.windows);}}
    }
    cp.duration=R.source_duration;
    // Flat outer assembly; retain the original 3D source and word objects.
    var master=app.project.items.addComp('Q33_COMPLETE_DUAL_PASS_4K',3840,2160,1,R.duration,24);master.renderer='ADBE Calder';
    var rows=[];for(i=0;i<R.segments.length;i++){var r=R.segments[i],clip=master.layers.add(cp);clip.name=r.id;clip.startTime=r.start;clip.inPoint=r.start;clip.outPoint=r.end;clip.timeRemapEnabled=true;var t=clip.property('ADBE Time Remapping');t.setValueAtTime(r.start,r.source_start);t.setValueAtTime(r.end,r.source_end);for(var k=t.numKeys;k>=1;k--)if(Math.abs(t.keyTime(k)-r.start)>.00001&&Math.abs(t.keyTime(k)-r.end)>.00001)t.removeKey(k);for(k=1;k<=t.numKeys;k++)t.setInterpolationTypeAtKey(k,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);rows.push(r);}
    master.comment=JSON.stringify({spec_sha:R.spec_sha,source_binding:R.source_binding,strict_two_method_relay:'HOLD',public_render_ready:false});
    var sourceMeta=JSON.parse(cp.comment);sourceMeta.integration_spec_sha=R.spec_sha;cp.comment=JSON.stringify(sourceMeta);
    app.setMemoryUsageLimits(20,96);app.setMultiFrameRenderingConfig(false,100);master.openInViewer();app.project.save(dest);
    var newChecks=[];for(i=1;i<=cp.numLayers;i++){var nl=cp.layer(i);if(nl.name==='METHOD_NAME'||nl.name.indexOf('FROZEN_SCREEN_')===0||nl.name.indexOf('APPLICATION_FILL_')===0||nl.name.indexOf('OPTION_FILL_')===0)newChecks.push({id:nl.id,name:nl.name,in_point:nl.inPoint,out_point:nl.outPoint,fast_opacity:nl.transform.opacity.valueAtTime(3.5,false),guided_opacity:nl.transform.opacity.valueAtTime(13.25,false)});}
    return JSON.stringify({comp_id:master.id,source_comp_id:cp.id,renderers:{source:cp.renderer,outer:master.renderer},canvas:[master.width,master.height,master.frameRate,master.duration],segments:rows,before_words:before,after_words:wordAudit(),old_samples:oldSamples,protected_samples:samples(),new_layer_window_checks:newChecks,same_original_word_objects:true,public_render_ready:false});
})();
