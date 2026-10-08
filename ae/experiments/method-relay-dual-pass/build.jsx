// One shared object space. Timelines execute supplied synthetic states, not reasoning.
(function(){
    function load(path){var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw new Error('Missing frozen relay input');var s=f.read();f.close();return JSON.parse(s);}
    function rgb(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    function text(name,copy,size,color,point,world){
        var l=cp.layers.addText(''),p=l.property('Source Text'),d=p.value;
        d.text=copy;d.font=world?S.font.english:S.font.chinese;d.fontSize=size;d.fillColor=rgb(color);
        d.applyFill=true;d.applyStroke=false;d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);
        l.name=name;l.threeDLayer=!!world;l.transform.anchorPoint.setValue(world?[0,0,0]:[0,0]);
        l.transform.position.setValue(point);l.motionBlur=!!world;return l;
    }
    function rect(name,w,h,color,point,world){
        var l=cp.layers.addShape();l.name=name;l.threeDLayer=!!world;l.motionBlur=!!world;
        var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
        g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
        l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
        var v=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        v.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([w,h]);
        v.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(rgb(color));
        l.transform.position.setValue(point);return l;
    }
    function null3(name,point){var l=cp.layers.addNull(cp.duration);l.name=name;l.threeDLayer=true;l.transform.anchorPoint.setValue([0,0,0]);l.transform.position.setValue(point);return l;}
    function keys(p,rows,spatial){
        rows.sort(function(a,b){return a[0]-b[0];});
        for(var i=0;i<rows.length;i++)p.setValueAtTime(rows[i][0],rows[i][1]);
        for(var i=1;i<=p.numKeys;i++){
            var n=p.isSpatial?1:(p.value instanceof Array?p.value.length:1),a=[],b=[];
            for(var j=0;j<n;j++){a.push(new KeyframeEase(0,55));b.push(new KeyframeEase(0,32));}
            p.setTemporalEaseAtKey(i,a,b);p.setInterpolationTypeAtKey(i,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
            if(p.isSpatial){p.setSpatialAutoBezierAtKey(i,!!spatial);p.setSpatialContinuousAtKey(i,!!spatial);}
        }
    }
    function across(initial,fn){
        var a=[[0,initial]];
        for(var i=0;i<R.passes.length;i++){
            var more=fn(R.passes[i]);for(var j=0;j<more.length;j++)a.push(more[j]);
            if(i===0&&R.rewind){a.push([R.rewind[0],more[more.length-1][1]]);a.push([R.rewind[1],initial]);}
        }
        return a;
    }
    // Clear the core slots before descending deferred fragments into the row.
    // Lateral transport happens on the parked upper/lower plane; no word crosses
    // a readable core while returning to the original sentence.
    function restoreCore(p){return p.verify[0]+(p.verify[1]-.35-p.verify[0])*.30;}
    function restoreRoute(p){return p.verify[0]+(p.verify[1]-.35-p.verify[0])*.48;}
    function origin(l,id,copy,start,end){l.comment=JSON.stringify({object_id:id,origin_sha:R.fixture_sha,text_sha:copy,start:start,end:end});}
    function stroke(name,points,color,world){
        var l=cp.layers.addShape();l.name=name;l.threeDLayer=!!world;l.motionBlur=!!world;
        l.transform.anchorPoint.setValue(world?[0,0,0]:[0,0]);l.transform.position.setValue(world?[0,0,0]:[0,0]);
        var root=l.property('ADBE Root Vectors Group');root.addProperty('ADBE Vector Group');
        l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Group');
        l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Stroke');
        var v=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group'),s=new Shape();
        s.vertices=points;s.closed=false;s.inTangents=[];s.outTangents=[];
        for(var i=0;i<points.length;i++){s.inTangents.push([0,0]);s.outTangents.push([0,0]);}
        v.property('ADBE Vector Shape - Group').property('ADBE Vector Shape').setValue(s);
        v.property('ADBE Vector Graphic - Stroke').property('ADBE Vector Stroke Color').setValue(rgb(color));
        v.property('ADBE Vector Graphic - Stroke').property('ADBE Vector Stroke Width').setValue(1.5);return l;
    }
    var R=load(RELAY_REQUEST),S=R.fixture,dest=new File(R.project);
    if(dest.exists||S.production_eligible!==false||S.public_render_ready!==false)throw new Error('New independent synthetic project required');
    app.newProject();app.project.save(dest);
    var cp=app.project.items.addComp('METHOD_RELAY_'+R.phase,1920,1080,1,R.duration,24);
    cp.renderer='ADBE Advanced 3d';cp.bgColor=rgb(S.palette.paper);cp.motionBlur=true;cp.shutterAngle=100;
    cp.motionBlurSamplesPerFrame=8;cp.motionBlurAdaptiveSampleLimit=32;
    cp.comment=JSON.stringify({kind:S.kind,spec_sha:R.spec_sha,trajectory_sha:R.trajectory_sha,fixture_sha:R.fixture_sha,production_eligible:false,public_render_ready:false});
    cp.layers.addSolid(rgb(S.palette.paper),'PAPER',1920,1080,1,cp.duration);
    text('SERIES',S.screen.series,42,S.palette.ink,[110,105],false);
    text('SYNTHETIC_MARKER',S.screen.marker,20,S.palette.muted,[110,1015],false);
    rect('EDITORIAL_RULE',1700,1,S.palette.edge,[960,155],false);
    var task=text('ORIGINAL_QUESTION',S.stem,38,S.palette.ink,[190,246],false);
    var td=task.property('Source Text').value;td.font=S.font.english;task.property('Source Text').setValue(td);
    origin(task,'original-question',null,0,S.stem.length);
    var badge=text('PASS_BADGE',R.phase==='p0'?'方法接棒 · 技术镜头':S.screen.fast,23,S.palette.muted,[1420,110],false);
    if(R.phase==='full'){
        var bd=badge.property('Source Text').value;bd.text=S.screen.fast;badge.property('Source Text').setValueAtTime(0,bd);
        bd=badge.property('Source Text').value;bd.text=S.screen.guided;badge.property('Source Text').setValueAtTime(15.5,bd);
    }
    var evidence=null3('EVIDENCE_PLANE',[0,0,0]),objects={},hinges={},labels={},optionObjects={},basisX={},i,j;
    keys(evidence.transform.position,across([0,0,0],function(p){return [[p.lift[0],[0,0,0]],[p.lift[1],[0,-40,-140]],[p.end,[0,-40,-140]]];}),true);
    var before=text('CONTEXT_BEFORE',S.context[0],32,S.palette.muted,[190,365,130],true);
    var after=text('CONTEXT_AFTER',S.context[1],32,S.palette.muted,[190,542,180],true);
    keys(before.transform.opacity,across(65,function(p){return [[p.locate[0],65],[p.locate[1],15],[p.verify[0],15],[p.verify[1],35],[p.end,35]];}),false);
    keys(after.transform.opacity,across(65,function(p){return [[p.locate[0],65],[p.locate[1],15],[p.verify[0],15],[p.verify[1],35],[p.end,35]];}),false);
    for(i=0;i<R.layout.length;i++){
        var n=R.layout[i],l=text(n.id,n.text,S.font.size,S.palette.ink,[n.x,460,0],true);
        l.parent=evidence;l.transform.position.setValue([n.x,460,0]);origin(l,n.id,n.text_sha,n.start,n.end);objects[n.id]=l;
        if(n.role==='supplied_modifier'){
            var h=null3('HINGE_'+n.id,[n.x,460,0]);h.parent=evidence;h.transform.position.setValue([n.x,460,0]);
            l.parent=h;l.transform.position.setValue([0,0,-1]);hinges[n.id]=h;
        }else{basisX[n.id]=n.x;}
    }
    var subjectRow=R.layout[0],verbRow=R.layout[2];basisX['core-subject']=verbRow.x-subjectRow.width;
    keys(objects['core-subject'].transform.position,across([subjectRow.x,460,0],function(p){return [[p.tighten[0],[subjectRow.x,460,0]],[p.tighten[1],[basisX['core-subject'],460,0]],[p.verify[0],[basisX['core-subject'],460,0]],[restoreCore(p),[subjectRow.x,460,0]],[p.end,[subjectRow.x,460,0]]];}),false);
    for(i=0;i<R.layout.length;i++)if(R.layout[i].id==='core-verb'||R.layout[i].id==='core-object'){
        (function(n){
            var part=n.id==='core-verb'?'verb':'object',cx=R.comparison_columns[part];
            keys(objects[n.id].transform.position,across([n.x,460,0],function(p){return [[p.align[0],[n.x,460,0]],[p.align[1],[cx,460,0]],[p.verify[0],[cx,460,0]],[restoreCore(p),[n.x,460,0]],[p.end,[n.x,460,0]]];}),false);
        })(R.layout[i]);
    }
    for(i=0;i<R.layout.length;i++)if(R.layout[i].role==='supplied_modifier'){
        (function(n){
            var h=hinges[n.id],l=objects[n.id],above=n.id==='aside-time',cue=null;
            for(var k=0;k<R.cue_layout.length;k++)if(R.cue_layout[k].object_id===n.id)cue=R.cue_layout[k];
            var anchor=objects[n.attachment],ar=anchor.sourceRectAtTime(0,false),br=l.sourceRectAtTime(0,false),scale=76;
            var restX=basisX[n.attachment]+ar.left+ar.width/2-(br.left+br.width/2)*scale/100;
            var restY=460+(above?-96:96);
            keys(h.transform.position,across([n.x,460,0],function(p){var q=above?p.peel_a:p.peel_b;return [[q[2],[n.x,460,0]],[q[3],[n.x,460+(above?-56:56),32]],[q[4],[restX,restY,0]],[p.verify[0],[restX,restY,0]],[restoreCore(p),[restX,restY,0]],[restoreRoute(p),[n.x,restY,0]],[p.verify[1]-.35,[n.x,460,0]],[p.end,[n.x,460,0]]];}),false);
            keys(h.transform.yRotation,across(0,function(p){var q=above?p.peel_a:p.peel_b;return [[q[2],0],[q[3],-53],[q[4],0],[p.end,0]];}),false);
            keys(h.transform.scale,across([100,100,100],function(p){var q=above?p.peel_a:p.peel_b;return [[q[3],[100,100,100]],[q[4],[76,76,76]],[restoreRoute(p),[76,76,76]],[p.verify[1]-.35,[100,100,100]],[p.end,[100,100,100]]];}),false);
            keys(l.transform.opacity,across(100,function(p){var q=above?p.peel_a:p.peel_b;return [[q[4],100],[q[4]+.15,72],[p.verify[0],72],[p.verify[1]-.35,100],[p.end,100]];}),false);
            var mark=rect('WORD_CUE_'+n.id,cue.width+8,46,S.palette.fog,[0,0,0],true);mark.parent=h;mark.transform.position.setValue([cue.offset_x+cue.width/2,-15,1]);mark.moveAfter(l);
            keys(mark.transform.opacity,across(0,function(p){var q=above?p.peel_a:p.peel_b;return [[q[0],0],[q[0]+.05,28],[q[1]-.035,28],[q[1]+.02,0],[p.end,0]];}),false);
            var range=stroke('RANGE_'+n.id,[[0,7],[0,12],[n.width,12],[n.width,7]],S.palette.fog,true);range.parent=h;range.transform.position.setValue([0,0,-2]);
            keys(range.transform.scale,across([0,100,100],function(p){var q=above?p.peel_a:p.peel_b;return [[q[1]+.025,[0,100,100]],[q[2]-.06,[100,100,100]],[p.end,[100,100,100]]];}),false);
            keys(range.transform.opacity,across(0,function(p){var q=above?p.peel_a:p.peel_b;return [[q[1]+.03,0],[q[2]-.06,65],[q[2],65],[q[2]+1/24,0],[p.end,0]];}),false);
            var carrier=rect('CARRIER_'+n.id,n.width+12,56,'#EFECE2',[0,0,0],true);carrier.parent=h;carrier.transform.position.setValue([n.width/2,-17,1]);carrier.moveAfter(l);
            keys(carrier.transform.opacity,across(0,function(p){var q=above?p.peel_a:p.peel_b;return [[q[2],0],[q[2]+.035,82],[q[4],70],[q[4]+.125,0],[p.end,0]];}),false);
            var edge=rect('EDGE_'+n.id,2,53,S.palette.fog,[0,0,0],true);edge.parent=h;edge.transform.position.setValue([-4,-17,-2]);
            keys(edge.transform.opacity,across(0,function(p){var q=above?p.peel_a:p.peel_b;return [[q[2],0],[q[2]+.035,72],[q[3],72],[q[4],0],[p.end,0]];}),false);
        })(R.layout[i]);
    }
    if(R.locate_geometry){
        var lg=R.locate_geometry;
        var stemMark=rect('QUESTION_LOCATION_CUE',lg.stem_width+8,44,S.palette.fog,[lg.stem_x+lg.stem_width/2,233],false);stemMark.moveAfter(task);
        var sourceMark=rect('EVIDENCE_LOCATION_CUE',lg.source_width+8,46,S.palette.fog,[lg.source_x+lg.source_width/2,445,1],true);sourceMark.parent=evidence;sourceMark.transform.position.setValue([lg.source_x+lg.source_width/2,445,1]);sourceMark.moveAfter(objects['core-verb']);
        keys(stemMark.transform.opacity,across(0,function(p){return [[p.locate[0],0],[p.locate[0]+.12,20],[p.locate[1],20],[p.lift[1],0],[p.end,0]];}),false);
        keys(sourceMark.transform.opacity,across(0,function(p){return [[p.locate[0]+.15,0],[p.locate[1]-.15,24],[p.locate[1],24],[p.peel_a[0],0],[p.end,0]];}),false);
    }
    var sentenceEnd=R.layout[R.layout.length-1].x+R.layout[R.layout.length-1].width;
    var sentenceScope=stroke('LOCATED_SENTENCE',[[190,472],[sentenceEnd,472]],S.palette.fog,true);sentenceScope.parent=evidence;sentenceScope.transform.position.setValue([0,0,0]);
    keys(sentenceScope.transform.scale,across([0,100,100],function(p){return [[p.locate[0],[0,100,100]],[p.locate[1],[100,100,100]],[p.end,[100,100,100]]];}),false);
    keys(sentenceScope.transform.opacity,across(0,function(p){return [[p.locate[0],0],[p.locate[1],45],[p.lift[1],45],[p.peel_a[0],0],[p.end,0]];}),false);
    var axis=stroke('RETAINED_READING_AXIS',[[basisX['core-subject']-5,480],[basisX['core-object']+objects['core-object'].sourceRectAtTime(0,false).width,480]],S.palette.fog,true);axis.parent=evidence;axis.transform.position.setValue([0,0,0]);
    axis.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Shape - Group').property('ADBE Vector Shape').expression='var a=thisComp.layer("core-subject"),b=thisComp.layer("core-object");var r=b.sourceRectAtTime(time,false);createPath([[a.transform.position[0]-5,480],[b.transform.position[0]+r.left+r.width,480]],[],[],false);';
    keys(axis.transform.opacity,across(0,function(p){return [[p.peel_b[4],0],[p.peel_b[4]+.3,42],[p.verify[0],42],[p.verify[1]-.35,0],[p.end,0]];}),false);
    for(i=0;i<R.options.length;i++){
        (function(o){
            var root=null3('OPTION_PLANE_'+o.id,[0,0,0]);
            keys(root.transform.position,across([0,0,0],function(p){return [[p.lift[0],[0,0,0]],[p.lift[1],[0,-35,240]],[p.align[0],[0,-35,240]],[p.align[1],[0,-40,-140]],[p.end,[0,-40,-140]]];}),true);
            var compareY=o.comparison_y;
            var label=text('OPTION_LABEL_'+o.id,o.id+'.',28,S.palette.muted,[185,o.y,0],true);label.parent=root;label.transform.position.setValue([185,o.y,0]);labels[o.id]=label;
            keys(label.transform.position,across([185,o.y,0],function(p){return [[p.align[0],[185,o.y,0]],[p.align[1],[basisX['core-subject']-50,compareY,0]],[p.end,[basisX['core-subject']-50,compareY,0]]];}),true);
            for(var k=0;k<o.pieces.length;k++){
                (function(piece){
                    var l=text(piece.id,piece.text,S.font.size,S.palette.ink,[piece.x,o.y,0],true);l.parent=root;l.transform.position.setValue([piece.x,o.y,0]);origin(l,piece.id,piece.text_sha,null,null);optionObjects[piece.id]=l;
                    var x=R.comparison_columns[piece.part];
                    keys(l.transform.position,across([piece.x,o.y,0],function(p){return [[p.align[0],[piece.x,o.y,0]],[p.align[1],[x,compareY,0]],[p.end,[x,compareY,0]]];}),true);
                    keys(l.transform.opacity,across(100,function(p){var fade=o.id==='A'?100:24,t=o.id==='B'?p.compare[1]:p.others[1];return [[p.lift[0],100],[p.lift[1],35],[p.align[0],35],[p.align[1],100],[t-.35,100],[t,fade],[p.end,fade]];}),false);
                    if(o.difference===piece.part){
                        var mark=rect('DIFFERENCE_'+piece.id,piece.width+12,46,S.palette.difference,[0,0,0],true);mark.parent=l;mark.transform.position.setValue([piece.width/2,-15,1]);mark.moveAfter(l);
                        keys(mark.transform.opacity,across(0,function(p){
                            if(p.kind==='guided'&&S.guided_method_copy&&piece.id===S.guided_method_copy.emphasis.object_id){
                                var w=S.guided_method_copy.emphasis.window;
                                return [[w[0],0],[w[0]+.16,24],[w[1]-.16,24],[w[1],0],[p.end,0]];
                            }
                            var t=o.id==='B'?p.compare[0]:p.others[0];return [[t,0],[t+.16,24],[t+.62,24],[t+1.0,0],[p.end,0]];
                        }),false);
                    }
                })(o.pieces[k]);
            }
            keys(label.transform.opacity,across(75,function(p){var t=o.id==='B'?p.compare[1]:p.others[1];return [[t-.35,75],[t,o.id==='A'?100:24],[p.end,o.id==='A'?100:24]];}),false);
        })(R.options[i]);
    }
    // Small names for the existing comparison dimensions, in Guided only.
    // They label the original objects; they add no grammatical attachment or verdict.
    if(R.phase==='full'&&S.guided_method_copy){
        var guide=null;for(i=0;i<R.passes.length;i++)if(R.passes[i].kind==='guided')guide=R.passes[i];
        for(i=0;i<S.guided_method_copy.column_labels.length;i++){
            var labelSpec=S.guided_method_copy.column_labels[i];
            var header=text('GUIDED_COLUMN_'+labelSpec.part,labelSpec.text,24,S.palette.muted,[R.comparison_columns[labelSpec.part],610,0],true);
            var hd=header.property('Source Text').value;hd.font=S.font.chinese;header.property('Source Text').setValue(hd);
            header.parent=evidence;header.transform.position.setValue([R.comparison_columns[labelSpec.part],610,0]);
            header.comment=JSON.stringify({kind:'frozen_comparison_dimension_label',part:labelSpec.part,source_refs:R.method_explanations[2].refs,synthetic_case_certified:false});
            keys(header.transform.opacity,[[0,0],[guide.align[0],0],[guide.align[0]+.25,76],
                [S.guided_method_copy.emphasis.window[1]-.25,76],[S.guided_method_copy.emphasis.window[1],0],[cp.duration,0]],false);
        }
    }
    var compareLine=stroke('SOURCE_TO_OPTION',[[0,0],[1,1]],S.palette.fog,false);
    var vv=compareLine.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
    vv.property('ADBE Vector Shape - Group').property('ADBE Vector Shape').expression='var a=thisComp.layer("core-subject"),b=thisComp.layer("option-B-subject");var ar=a.sourceRectAtTime(time,false),br=b.sourceRectAtTime(time,false);var p=a.toComp([ar.left+ar.width/2,ar.top+ar.height+8,0]),q=b.toComp([br.left+br.width/2,br.top-10,0]);createPath([[p[0],p[1]],[p[0],(p[1]+q[1])/2],[q[0],q[1]]],[],[],false);';
    keys(compareLine.transform.opacity,across(0,function(p){return [[p.align[1],0],[p.compare[0],50],[p.compare[1]-.4,50],[p.compare[1],0],[p.end,0]];}),false);
    var result=text('SYNTHETIC_RESULT',S.screen.result,24,S.palette.ink,[1300,845],false);
    keys(result.transform.opacity,across(0,function(p){return [[p.verify[1]-.35,0],[p.verify[1],100],[p.end,100]];}),false);
    // Three small names exist exactly once; Guided explains the actions without more stamps.
    var first=R.passes[0];
    for(i=0;i<R.method_names.length;i++){
        var m=R.method_names[i],t=first.compare[0];
        if(m.method_id==='R12')t=first.locate[1];else if(m.method_id==='R11')t=first.peel_a[2];
        var point=m.method_id==='R02'?[1250,660,-140]:[310,305,-140];
        var stamp=text('METHOD_NAME_'+m.method_id,m.name,24,S.palette.muted,point,true);
        var sd=stamp.property('Source Text').value;sd.font=S.font.chinese;stamp.property('Source Text').setValue(sd);
        stamp.comment=JSON.stringify({kind:'frozen_method_name_only',method_id:m.method_id,source_ref:m});
        keys(stamp.transform.opacity,[[0,0],[t,0],[t+.1,85],[t+.9,85],[t+1.15,0],[cp.duration,0]],false);
    }
    var focus=null3('FOCUS_TARGET',[960,540,0]);
    keys(focus.transform.position,across([960,540,0],function(p){return [[p.locate[0],[960,540,0]],[p.locate[1],[800,460,0]],[p.lift[1],[800,420,-140]],[p.peel_a[4],[825,420,-140]],[p.peel_b[4],[725,420,-140]],[p.align[1],[785,525,-140]],[p.verify[0],[785,525,-140]],[p.verify[1],[800,530,-140]],[p.end,[800,530,-140]]];}),true);
    var camera=cp.layers.addCamera('GUIDED_CAMERA',[960,540]);camera.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    keys(camera.transform.position,across([960,540,-2180],function(p){var fast=p.kind==='fast';return [[p.locate[0],[960,540,-2180]],[p.locate[1],[830,460,fast?-2000:-1940]],[p.lift[1],[820,410,fast?-1960:-1880]],[p.peel_a[4],[830,390,fast?-1850:-1760]],[p.peel_b[4],[785,425,fast?-1900:-1800]],[p.align[1],[820,505,fast?-2050:-2000]],[p.verify[0],[820,505,fast?-2050:-2000]],[p.verify[1],[900,540,-2180]],[p.end,[900,540,-2180]]];}),true);
    keys(camera.transform.pointOfInterest,across([960,540,0],function(p){return [[p.locate[0],[960,540,0]],[p.locate[1],[800,460,0]],[p.lift[1],[800,420,-140]],[p.peel_a[4],[840,420,-140]],[p.peel_b[4],[735,440,-140]],[p.align[1],[790,535,-140]],[p.verify[0],[790,535,-140]],[p.verify[1],[800,540,-140]],[p.end,[800,540,-140]]];}),true);
    var opt=camera.property('ADBE Camera Options Group');opt.property('ADBE Camera Zoom').setValue(1950);
    opt.property('ADBE Camera Depth of Field').setValue(1);opt.property('ADBE Camera Aperture').setValue(40);opt.property('ADBE Camera Blur Level').setValue(100);
    opt.property('ADBE Camera Focus Distance').expression='var p=thisComp.layer("FOCUS_TARGET").toWorld([0,0,0]);var c=transform.position;var v=normalize(sub(transform.pointOfInterest,c));dot(sub(p,c),v);';
    cp.openInViewer();app.project.save(dest);
    return JSON.stringify({ok:true,phase:R.phase,comp_id:cp.id,spec_sha:R.spec_sha,trajectory_sha:R.trajectory_sha,project:dest.fsName,renderer:cp.renderer});
})();
