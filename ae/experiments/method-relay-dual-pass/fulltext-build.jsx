// Whole frozen reading page -> actual line-order scan -> reviewed span -> same-word lift.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';f.open('r');var s=f.read();f.close();return JSON.parse(s);}
    var R=load(FULLTEXT_REQUEST),dest=new File(R.project),S=R.render_scale; if(dest.exists)throw new Error('Fresh fulltext project required');
    function physical(v){var result=[];for(var i=0;i<v.length;i++)result.push(v[i]*S);return result;}
    app.newProject();app.project.save(dest);var cp=app.project.items.addComp('FULLTEXT_SOURCE_ACQUISITION',R.canvas[0],R.canvas[1],1,R.canvas[3],R.canvas[2]);
    cp.renderer='ADBE Advanced 3d';cp.draft3d=false;cp.resolutionFactor=[1,1];cp.bgColor=[.973,.969,.949];cp.motionBlur=true;cp.shutterAngle=70;
    var ink=[.15,.18,.17],paper=[.973,.969,.949],words={},rects={},handles={},questionHandles={};
    function text(name,copy,size,point,world,chinese){var l=cp.layers.addText(copy),p=l.property('Source Text'),d=p.value;
        d.font=chinese?R.font.chinese:R.font.english;d.fontSize=size;d.fillColor=ink;d.applyFill=true;d.applyStroke=false;
        p.setValue(d);l.name=name;l.threeDLayer=!!world;l.transform.anchorPoint.setValue(world?[0,0,0]:[0,0]);l.transform.position.setValue(physical(point));
        l.transform.scale.setValue([100*S,100*S,100*S]);l.motionBlur=!!world;return l;}
    function keys(p,rows,linear){rows.sort(function(a,b){return a[0]-b[0];});for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
        for(var i=1;i<=p.numKeys;i++){
            if(p.isSpatial){var zero=[];for(var z=0;z<p.value.length;z++)zero.push(0);p.setSpatialAutoBezierAtKey(i,false);p.setSpatialContinuousAtKey(i,false);p.setSpatialTangentsAtKey(i,zero,zero);}
            if(linear){p.setInterpolationTypeAtKey(i,KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);continue;}
            var n=p.isSpatial?1:(p.value instanceof Array?p.value.length:1),es=[];for(var j=0;j<n;j++)es.push(new KeyframeEase(0,40));
            p.setTemporalEaseAtKey(i,es,es);p.setInterpolationTypeAtKey(i,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
            if(p.isSpatial){p.setSpatialAutoBezierAtKey(i,false);p.setSpatialContinuousAtKey(i,false);}
        }}
    // Carry velocity through adjacent reading rows; only acquisition and holds stop.
    function cameraKeys(property,rows){
        var adjusted=[];
        for(var i=0;i<rows.length;i++){
            var t=rows[i][0];
            for(var j=0;j<R.director.passes.length;j++){
                var pass=R.director.passes[j],lag=(pass.kind==='fast'?1:2)/24;
                if(t>pass.scan[0]&&t<pass.hit[0])t+=lag;
                if(Math.abs(t-pass.lift[0])<.00001)t+=(pass.kind==='fast'?1:2)/24;
            }
            adjusted.push([t,rows[i][1]]);
        }
        adjusted.sort(function(a,b){return a[0]-b[0];});
        var filtered=[];
        for(var i=0;i<adjusted.length;i++){
            var row=adjusted[i],interior=false;
            for(var j=0;j<R.director.passes.length;j++)if(row[0]>R.director.passes[j].scan[0]&&row[0]<R.director.passes[j].hit[0])interior=true;
            var same=filtered.length>0;if(same)for(var axis=0;axis<row[1].length;axis++)if(Math.abs(row[1][axis]-filtered[filtered.length-1][1][axis])>.001)same=false;
            if(interior&&same)continue;
            filtered.push(row);
        }
        keys(property,filtered,false);
        for(var k=2;k<property.numKeys;k++){
            var t=property.keyTime(k),inside=false;
            for(var j=0;j<R.director.passes.length;j++)if(t>R.director.passes[j].scan[0]&&t<R.director.passes[j].hit[0])inside=true;
            if(!inside)continue;
            var a=property.keyValue(k-1),b=property.keyValue(k),c=property.keyValue(k+1),da=0,db=0;
            for(var axis=0;axis<a.length;axis++){da+=Math.pow(b[axis]-a[axis],2);db+=Math.pow(c[axis]-b[axis],2);}
            var speed=Math.min(Math.sqrt(da)/(t-property.keyTime(k-1)),Math.sqrt(db)/(property.keyTime(k+1)-t));
            property.setTemporalEaseAtKey(k,[new KeyframeEase(speed,22)],[new KeyframeEase(speed,22)]);
        }
    }
    function union(ids,lift){var mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];for(var i=0;i<ids.length;i++){
        var id=ids[i],r=rects[id],p=lift?physical(R.lift_positions[id]):words[id].transform.position.valueAtTime(0,false),s=(lift?32/24:1)*S;
        var a=[p[0]+r.left*s,p[1]+r.top*s,p[2]],b=[p[0]+(r.left+r.width)*s,p[1]+(r.top+r.height)*s,p[2]];
        for(var j=0;j<3;j++){mn[j]=Math.min(mn[j],a[j]);mx[j]=Math.max(mx[j],b[j]);}}
        return {min:mn,max:mx,center:[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2]};}
    function across(initial,fn){var rows=[[0,initial]];for(var i=0;i<R.director.passes.length;i++){
        var next=fn(R.director.passes[i]);rows=rows.concat(next);if(i===0){rows.push([7,next[next.length-1][1]]);rows.push([8,initial]);}}return rows;}
    function solidRect(name,w,h,color,point){var l=cp.layers.addSolid(color,name,w,h,1,20);l.transform.position.setValue(point);return l;}
    function filledMark(name,w,h,point,world){var l=cp.layers.addShape();l.name=name;l.threeDLayer=world;
        var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group'),v=g.property('ADBE Vectors Group');
        v.addProperty('ADBE Vector Shape - Rect');v=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        v.addProperty('ADBE Vector Graphic - Fill');v=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        v.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([w,h]);
        v.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue([.87,.90,.88]);l.transform.position.setValue(point);return l;}
    function paperBorder(name,top,bottom,feather){var l=solidRect(name,cp.width,cp.height,paper,[cp.width/2,cp.height/2]),m=l.property('ADBE Mask Parade').addProperty('ADBE Mask Atom'),s=new Shape();
        s.vertices=[[0,top*S],[cp.width,top*S],[cp.width,bottom*S],[0,bottom*S]];s.inTangents=[[0,0],[0,0],[0,0],[0,0]];s.outTangents=s.inTangents;s.closed=true;
        m.property('ADBE Mask Shape').setValue(s);m.property('ADBE Mask Feather').setValue([0,feather*S]);return l;}
    solidRect('PAPER',cp.width,cp.height,paper,[cp.width/2,cp.height/2]);
    for(var i=0;i<R.words.length;i++){
        var w=R.words[i],l=text(w.id,w.text,24,w.position,true,w.chinese);words[w.id]=l;handles[w.id]=l.id;rects[w.id]=l.sourceRectAtTime(0,false);
        l.comment=JSON.stringify({id:w.id,start:w.start,end:w.end,text_sha:w.text_sha,source_sha:R.source.passage_sha});
        var selected=!!R.lift_positions[w.id];
        if(selected){keys(l.transform.position,across(physical(w.position),function(p){var depart=p.lift[0]+(p.kind==='fast'?1:2)/24;var lead=physical([w.position[0],w.position[1],-24]);return [[p.lift[0],physical(w.position)],[depart,lead],[p.lift[1],physical(R.lift_positions[w.id])],[p.end,physical(R.lift_positions[w.id])]];}));
            keys(l.transform.scale,across([100*S,100*S,100*S],function(p){return [[p.lift[0]+(p.kind==='fast'?2:3)/24,[100*S,100*S,100*S]],[p.lift[1],[100*S*32/24,100*S*32/24,100*S*32/24]],[p.end,[100*S*32/24,100*S*32/24,100*S*32/24]]];}));}
        keys(l.transform.opacity,across(0,function(p){var rows=[[p.overview[0],0],[p.source_reveal_end,100],[p.hit[0],100],[p.lock[1],selected?100:28]];if(!selected)rows=rows.concat([[p.lift[0],28],[p.lift[0]+(p.kind==='fast'?1:2)/24,0],[p.lift[1]-2/24,0],[p.lift[1],28]]);rows.push([p.end,selected?100:28]);return rows;}));
    }
    var allIds=[];for(var i=0;i<R.words.length;i++)allIds.push(R.words[i].id);
    var whole=union(allIds,false),hit=union(R.hit_ids,false),scope=union(R.target_ids,false),lifted=union(R.target_ids,true),lineBoxes=[];
    for(var i=0;i<R.lines.length;i++)lineBoxes.push(union(R.lines[i].word_ids,false));
    var style={};for(var key in R.camera_style){var value=R.camera_style[key];
        if(key==='aperture'){style[key]={};for(var stage in value)style[key][stage]=value[stage]*S;}
        else style[key]=(key==='background_max_word_scale'||key==='reader_opacity')?value:value*S;}
    var column=whole.center[0],overviewDepth=Math.max(2180*S,(whole.max[1]-whole.min[1])/(style.overview_bottom-style.overview_top)*style.zoom);
    var overviewScale=style.zoom/overviewDepth,overviewY=whole.center[1]-((style.overview_top+style.overview_bottom)/2-cp.height/2)/overviewScale;
    var overviewLook=[column,overviewY,0],overviewPosition=[column+20*S,overviewY+12*S,-overviewDepth];
    var foregroundScale=style.zoom/((1980-140)*S),liftLook=[lifted.center[0],lifted.center[1]+(cp.height/2-style.foreground_screen_y)/foregroundScale,-140*S];
    var backgroundProjection=style.zoom/(1980*S+style.background_z),backgroundWordScale=Math.min(style.background_max_word_scale,
        (style.background_bottom-style.background_top)/((whole.max[1]-whole.min[1])*backgroundProjection));
    var backgroundOrigin=liftLook[1]+(style.background_top-cp.height/2)/backgroundProjection,retreatPositions={};
    for(var i=0;i<R.words.length;i++){
        var w=R.words[i];if(R.lift_positions[w.id])continue;
        var destination=[column+(w.position[0]*S-column)*backgroundWordScale,backgroundOrigin+(w.position[1]*S-whole.min[1])*backgroundWordScale,style.background_z];
        retreatPositions[w.id]=destination;
        keys(words[w.id].transform.position,across(physical(w.position),function(p){return [[p.lift[0]+(p.kind==='fast'?1:2)/24,physical(w.position)],[p.lift[1],destination],[p.end,destination]];}));
        keys(words[w.id].transform.scale,across([100*S,100*S,100*S],function(p){return [[p.lift[0]+(p.kind==='fast'?1:2)/24,[100*S,100*S,100*S]],[p.lift[1],[100*S*backgroundWordScale,100*S*backgroundWordScale,100*S*backgroundWordScale]],
            [p.end,[100*S*backgroundWordScale,100*S*backgroundWordScale,100*S*backgroundWordScale]]];}));
    }
    // Invisible geometric cursor binds the lens path; it never annotates the page.
    var reader=cp.layers.addNull(20);reader.name='READING_GUIDE';reader.threeDLayer=true;reader.enabled=false;
    var readerRows=[],readerAlpha=[[0,0]],focusRows=[[0,whole.center]],lookRows=[[0,overviewLook]],cameraRows=[[0,overviewPosition]],visits=[],apertureRows=[[0,0]];
    for(var i=0;i<R.director.passes.length;i++){
        var p=R.director.passes[i],total=0;for(var j=0;j<R.scan_line_ids.length;j++){var b=lineBoxes[R.scan_line_ids[j]];total+=b.max[0]-b.min[0];}
        var t=p.scan[0],cumulative=0,entry={kind:p.kind,lines:[],column_x:column};
        var first=lineBoxes[0].center;
        focusRows.push([p.overview[0],whole.center],[p.enter_start,whole.center]);
        lookRows.push([p.overview[0],overviewLook],[p.enter_start,overviewLook],[t,[column,first[1]+style.reading_offset,0]]);
        cameraRows.push([p.overview[0],overviewPosition],[p.enter_start,overviewPosition],[t,[column+20*S,first[1]+style.reading_offset+style.camera_tilt_offset,style.scan_depth]]);
        for(var j=0;j<R.scan_line_ids.length;j++){
            var index=R.scan_line_ids[j],b=lineBoxes[index],last=j===R.scan_line_ids.length-1,width=b.max[0]-b.min[0];
            cumulative+=width;var end=last?p.scan[1]:Math.round((p.scan[0]+(p.scan[1]-p.scan[0])*cumulative/total)*24)/24,readY=b.max[1]+6*S;
            readerRows.push([t,[b.min[0],readY,S]]);readerRows.push([end-1/24,[last?b.min[0]+16*S:b.max[0]-style.reader_length,readY,S]]);
            readerAlpha.push([t,0],[t+1/24,style.reader_opacity],[end-1/24,style.reader_opacity],[end,0]);
            focusRows.push([t,[b.min[0]+style.reader_length/2,b.center[1],0]],
                [end-1/24,[last?b.min[0]+16*S+style.reader_length/2:b.max[0]-style.reader_length/2,b.center[1],0]]);
            lookRows.push([end-1/24,[column,b.center[1]+style.reading_offset,0]]);cameraRows.push([end-1/24,[column+20*S,b.center[1]+style.reading_offset+style.camera_tilt_offset,style.scan_depth]]);
            entry.lines.push({line_id:index,start:t,end:end,bounds:b});t=end;
        }
        readerRows.push([p.hit[1],[hit.center[0]-style.reader_length/2,hit.max[1]+6*S,S]],[p.end,[hit.center[0]-style.reader_length/2,hit.max[1]+6*S,S]]);
        readerAlpha.push([p.hit[0],style.reader_opacity],[p.hit[1],0],[p.end,0]);
        focusRows.push([p.hit_settle_end,hit.center],[p.hit[1],hit.center],[p.lock[1],scope.center],[p.lift[0],scope.center],[p.lift[1],lifted.center],[p.end,lifted.center]);
        lookRows.push([p.hit_settle_end,[column,hit.center[1]+style.reading_offset,0]],[p.hit[1],[column,hit.center[1]+style.reading_offset,0]],[p.lift[0],[column,hit.center[1]+style.reading_offset,0]],[p.lift[1],liftLook],[p.end,liftLook]);
        cameraRows.push([p.hit_settle_end,[column+20*S,hit.center[1]+style.reading_offset+style.camera_tilt_offset,style.scan_depth]],[p.hit[1],[column+20*S,hit.center[1]+style.reading_offset+style.camera_tilt_offset,style.scan_depth]],[p.lift[0],[column+20*S,hit.center[1]+style.reading_offset+style.camera_tilt_offset,style.scan_depth]],
            [p.lift[1],[liftLook[0]+20*S,liftLook[1]+12*S,-1980*S]],[p.end,[liftLook[0]+20*S,liftLook[1]+12*S,-1980*S]]);
        if(i===0){readerRows.push([7,readerRows[readerRows.length-1][1]],[8,[lineBoxes[0].min[0],lineBoxes[0].max[1]+6*S,S]]);readerAlpha.push([7,0],[8,0]);
            focusRows.push([7,lifted.center],[8,whole.center]);lookRows.push([7,liftLook],[8,overviewLook]);cameraRows.push([7,cameraRows[cameraRows.length-1][1]],[8,overviewPosition]);}
        apertureRows.push([p.overview[0],style.aperture.overview],[p.enter_start,style.aperture.overview],[p.scan[0],style.aperture.scan],[p.hit[0],style.aperture.scan],
            [p.hit[1],style.aperture.hit],[p.lock[1],style.aperture.lock],[p.lift[0],style.aperture.lock],[p.lift[1],style.aperture.lift],[p.end,style.aperture.lift]);
        if(i===0)apertureRows.push([7,style.aperture.lift],[8,style.aperture.overview]);
        visits.push(entry);
    }
    keys(reader.transform.position,readerRows,true);keys(reader.transform.opacity,readerAlpha,true);
    var focus=cp.layers.addNull(20);focus.name='FOCUS_TARGET';focus.threeDLayer=true;focus.transform.anchorPoint.setValue([0,0,0]);keys(focus.transform.position,focusRows,true);
    var liftWindows=[];for(var i=0;i<R.director.passes.length;i++)liftWindows.push([R.director.passes[i].lift[0],R.director.passes[i].end]);
    focus.transform.position.expression='(function(){var windows='+JSON.stringify(liftWindows)+';var active=false;for(var i=0;i<windows.length;i++)if(time>=windows[i][0]&&time<=windows[i][1])active=true;if(!active)return value;'
        +'var names='+JSON.stringify(R.target_ids)+';var lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9];'
        +'for(var i=0;i<names.length;i++){var l=thisComp.layer(names[i]),r=l.sourceRectAtTime(time,false),a=l.toWorld([r.left,r.top,0]),b=l.toWorld([r.left+r.width,r.top+r.height,0]);'
        +'for(var j=0;j<3;j++){lo[j]=Math.min(lo[j],a[j],b[j]);hi[j]=Math.max(hi[j],a[j],b[j]);}}return [(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2];})();';
    var camera=cp.layers.addCamera('GUIDED_CAMERA',[cp.width/2,cp.height/2]);camera.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    cameraKeys(camera.transform.position,cameraRows);cameraKeys(camera.transform.pointOfInterest,lookRows);
    var opt=camera.property('ADBE Camera Options Group');opt.property('ADBE Camera Zoom').setValue(style.zoom);opt.property('ADBE Camera Depth of Field').setValue(1);
    keys(opt.property('ADBE Camera Aperture'),apertureRows,false);opt.property('ADBE Camera Blur Level').setValue(100);
    opt.property('ADBE Camera Focus Distance').expression='var p=thisComp.layer("FOCUS_TARGET").toWorld([0,0,0]);dot(sub(p,transform.position),normalize(sub(transform.pointOfInterest,transform.position)));';
    var hitLine=filledMark('ACQUIRED_WORDS',hit.max[0]-hit.min[0]+8*S,hit.max[1]-hit.min[1]+8*S,[hit.center[0],hit.center[1],S],true);
    keys(hitLine.transform.opacity,across(0,function(p){return [[p.hit[0],0],[p.hit_flash[0],0],[p.hit_flash[0]+(p.hit_flash[1]-p.hit_flash[0])/3,85],[p.hit[1],0],[p.end,0]];}));
    // Extend the outer mask edges off-canvas: two-sided feather must not reveal
    // source glyphs again at the image boundary after their inner-edge fade.
    for(var guardName in R.viewport_guards){var guard=R.viewport_guards[guardName];
        paperBorder(guardName,guard.top,guard.bottom,guard.feather);}
    for(var i=0;i<R.question_parts.length;i++){
        var q=R.question_parts[i],l=text(q.id,q.text,34,q.position,false,false);questionHandles[q.id]=l.id;
        l.comment=JSON.stringify({id:q.id,start:q.start,end:q.end,text_sha:q.text_sha,question_pointer:R.source.question_pointer});
        if(q.id==='QUESTION_KEYWORD')keys(l.transform.opacity,across(100,function(p){return [[p.target[1],100],[p.source_reveal_end,60],[p.lift[0],60],[p.lift[0]+(p.lift[1]-p.lift[0])/2,0],[p.end,0]];}));
        else keys(l.transform.opacity,across(100,function(p){return [[p.target[1],100],[p.source_reveal_end,0],[p.end,0]];}));
    }
    for(var i=0;i<4;i++){var id='ABCD'.charAt(i),l=text('ORIGINAL_OPTION_'+id,id+'. '+R.source.question.options[id],24,[150+(i%2)*850,250+Math.floor(i/2)*38],false,false);
        keys(l.transform.opacity,across(100,function(p){return [[p.target[1],100],[p.source_reveal_end,0],[p.end,0]];}));}
    var label=text('INTERNAL_MARKER','内部研究 · 无声预览',14,[110,1020],false,true);label.transform.opacity.setValue(35);
    var qg=R.question_cue_geometry,qline=filledMark('QUESTION_TARGET',(qg.width+8)*S,40*S,physical([qg.x+qg.width/2,192]),false);qline.moveAfter(cp.layer('QUESTION_KEYWORD'));
    keys(qline.transform.opacity,across(0,function(p){return [[p.target[0],0],[p.target[0]+.1,80],[p.target[1],0],[p.end,0]];}));
    var data={kind:R.kind,spec_sha:R.spec_sha,whole:whole,hit:hit,scope:scope,lifted:lifted,
        director:R.director,line_boxes:lineBoxes,scan_visits:visits,handles:handles,question_handles:questionHandles,
        retreat_positions:retreatPositions,background_word_scale:backgroundWordScale,lift_look:liftLook,
        geometry_space:'native_sourceRect_scaled_plus_unparented_translation',new_method_certification:false,public_render_ready:false};
    var sidecar=new File(dest.parent.fsName+'/native-geometry.json');sidecar.encoding='UTF-8';sidecar.open('w');sidecar.write(JSON.stringify(data));sidecar.close();
    cp.comment=JSON.stringify({kind:R.kind,spec_sha:R.spec_sha,semantic_binding_sha:R.source.semantic_binding_sha,data_file:sidecar.fsName,public_render_ready:false});
    cp.openInViewer();app.project.save(dest);return JSON.stringify({ok:true,comp_id:cp.id,spec_sha:R.spec_sha,project:dest.fsName,data_file:sidecar.fsName});
})();
