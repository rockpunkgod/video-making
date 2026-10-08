// Independent SYNTHETIC visual research. Does not consume a production Direction.
// NCP_REQUEST is an explicit frozen local file, prepared by the research runner.
(function () {
    function load(path) { var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw new Error('Missing research input');var s=f.read();f.close();return JSON.parse(s); }
    function rgb(h) { return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255]; }
    function present(t) {
        if(!P)return t;
        var rows=P.time_map;
        for(var i=1;i<rows.length;i++)if(t<=rows[i][0])return rows[i-1][1]+(t-rows[i-1][0])*(rows[i][1]-rows[i-1][1])/(rows[i][0]-rows[i-1][0]);
        return P.duration;
    }
    function setKeys(p, rows, incoming, outgoing, spatial) {
        for(var k=0;k<rows.length;k++)p.setValueAtTime(present(rows[k][0]),rows[k][1]);
        for(var k=1;k<=p.numKeys;k++) {
            var count=p.isSpatial?1:(p.value instanceof Array?p.value.length:1),ins=[],outs=[];
            for(var j=0;j<count;j++){ins.push(new KeyframeEase(0,incoming||55));outs.push(new KeyframeEase(0,outgoing||35));}
            p.setTemporalEaseAtKey(k,ins,outs);
            if(P)p.setInterpolationTypeAtKey(k,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
            if(p.isSpatial){p.setSpatialAutoBezierAtKey(k,!!spatial);p.setSpatialContinuousAtKey(k,!!spatial);}
        }
    }
    function text(cp,name,copy,size,color,font,point,world) {
        var l=cp.layers.addText(''),p=l.property('Source Text'),d=p.value;
        d.text=copy;d.font=font;d.fontSize=size;d.fillColor=rgb(color);d.applyFill=true;d.applyStroke=false;
        d.justification=ParagraphJustification.LEFT_JUSTIFY;d.tracking=0;p.setValue(d);
        l.name=name;l.threeDLayer=!!world;l.transform.anchorPoint.setValue(world?[0,0,0]:[0,0]);
        l.transform.position.setValue(point);l.motionBlur=!!world;return l;
    }
    function rectangle(cp,name,w,h,color,point,world) {
        var l=cp.layers.addShape();l.name=name;l.threeDLayer=!!world;
        var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
        g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
        g=l.property('ADBE Root Vectors Group').property(1);
        g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');
        g=l.property('ADBE Root Vectors Group').property(1);
        g.property('ADBE Vectors Group').property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size').setValue([w,h]);
        g.property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue(rgb(color));
        l.transform.position.setValue(point);l.motionBlur=!!world;return l;
    }
    function null3(cp,name,p) { var n=cp.layers.addNull(cp.duration);n.name=name;n.threeDLayer=true;n.transform.anchorPoint.setValue([0,0,0]);n.transform.position.setValue(p);return n; }
    var R=load(NCP_REQUEST),S=R.scene,P=R.presentation||null,A=P&&(P.id==='SYNTHETIC-ATTACHMENT-LAYOUT-R5'||P.id==='SYNTHETIC-ATTACHMENT-LAYOUT-R5-FAST')?P.attachment_layout:null,dest=new File(R.project);
    if(dest.exists)throw new Error('Research revision already exists');
    if(S.kind!=='synthetic_ae_visual_research'||S.method_id!==null||S.production_eligible!==false||S.public_render_ready!==false)throw new Error('SYNTHETIC research only');
    app.project.save(dest);
    var folder=app.project.items.addFolder('NATIVE_CREATIVE_PROOF_'+R.revision);
    var cp=app.project.items.addComp('NATIVE_PEEL_'+R.revision,1920,1080,1,P?P.duration:S.canvas.duration,24);cp.parentFolder=folder;
    cp.renderer='ADBE Advanced 3d';cp.bgColor=rgb(S.palette.paper);cp.motionBlur=true;cp.shutterAngle=100;
    cp.motionBlurSamplesPerFrame=8;cp.motionBlurAdaptiveSampleLimit=32;
    cp.comment=JSON.stringify({kind:S.kind,scene_sha:R.scene_sha,spec_sha:R.spec_sha,revision:R.revision,presentation_id:P?P.id:null,production_eligible:false,public_render_ready:false});
    cp.layers.addSolid(rgb(S.palette.paper),'PAPER',1920,1080,1,cp.duration);
    text(cp,'SERIES',S.screen.series,36,S.palette.ink,S.font.chinese,[110,125],false);
    text(cp,'RESEARCH_MARKER',S.screen.marker,22,S.palette.muted,S.font.chinese,[110,1015],false);
    rectangle(cp,'EDITORIAL_RULE',1700,1,S.palette.edge,[960,165],false);
    var result=text(cp,'CURRENT_TASK',S.screen.result,24,S.palette.muted,S.font.chinese,[110,230],false);
    setKeys(result.transform.opacity,[[0,0],[21.8,0],[22.6,100],[27,100]],35,55,false);
    var upper=text(cp,'CONTEXT_BEFORE',S.context[0],34,S.palette.muted,S.font.english,[190,340,160],true);
    var lower=text(cp,'CONTEXT_AFTER',S.context[1],34,S.palette.muted,S.font.english,[190,770,230],true);
    setKeys(upper.transform.opacity,[[0,75],[3,75],[5.2,P?P.context_rest_opacity:18],[27,P?P.context_rest_opacity:18]],42,60,false);
    setKeys(lower.transform.opacity,[[0,75],[3,75],[5.2,P?P.context_rest_opacity:18],[27,P?P.context_rest_opacity:18]],42,60,false);
    var pivots={},objects={},i;
    for(i=0;i<R.layout.length;i++) {
        var n=R.layout[i],l=text(cp,n.id,n.text,S.font.size,S.palette.ink,S.font.english,[n.x,540,0],true);
        l.comment=JSON.stringify({object_id:n.id,start:n.start,end:n.end,text_sha:n.text_sha,"protected":n["protected"],origin:R.scene_sha});objects[n.id]=l;
        if(n.role==='supplied_modifier') {
            var hinge=null3(cp,'HINGE_'+n.id,[n.x,540,0]);pivots[n.id]=hinge;
            l.parent=hinge;l.transform.position.setValue([0,0,-1]);
            var carrier=rectangle(cp,'CARRIER_'+n.id,n.width+14,68,'#EFECE2',[n.width/2-1,-22,1],true);
            carrier.parent=hinge;carrier.transform.position.setValue([n.width/2-1,-22,1]);carrier.moveAfter(l);
            var side=rectangle(cp,'THIN_SIDE_'+n.id,3,68,S.palette.fog,[-7,-22,1],true);
            side.parent=hinge;side.transform.position.setValue([-7,-22,1]);side.transform.yRotation.setValue(90);
            var lip=rectangle(cp,'EDGE_'+n.id,2,66,S.palette.fog,[-5,-22,-2],true);
            lip.parent=hinge;lip.transform.position.setValue([-5,-22,-2]);
            var joint=rectangle(cp,'ATTACHMENT_'+n.id,2,60,S.palette.fog,[n.x-5,518,0],true);
            var label=text(cp,'PARK_LABEL_'+n.id,S.screen.deferred,18,S.palette.muted,S.font.chinese,[0,-72,0],true);
            label.parent=hinge;label.transform.position.setValue([0,-72,0]);
            var a=n.id==='aside-time',begin=a?5.6:11.8,release=a?7.9:14.6,park=a?10.7:17.5;
            setKeys(lip.transform.opacity,[[0,0],[begin,0],[begin+.55,78],[release,78],[park,A?0:28],[27,A?0:28]],55,32,false);
            setKeys(joint.transform.opacity,[[0,0],[begin,0],[begin+.5,80],[release-.15,80],[release+.35,0],[27,0]],35,65,false);
            setKeys(label.transform.opacity,A?[[0,0],[park-.3,0],[park+.25,45],[park+.85,0],[27,0]]:[[0,0],[park-.3,0],[park+.25,62],[27,62]],65,40,false);
            setKeys(carrier.transform.opacity,P?[[0,0],[begin,0],[begin+.6,92],[park,92],[park+.6,P.carrier_rest_opacity],[27,P.carrier_rest_opacity]]:[[0,0],[begin,0],[begin+.6,92],[27,92]],45,30,false);
            setKeys(side.transform.opacity,[[0,0],[begin,0],[begin+.6,70],[park,70],[park+.6,P?P.side_rest_opacity:22],[27,P?P.side_rest_opacity:22]],45,30,false);
            setKeys(l.transform.opacity,[[0,100],[park,100],[park+.6,P?P.text_rest_opacity:42],[27,P?P.text_rest_opacity:42]],45,30,false);
            var path=a?[[0,[n.x,540,0]],[6.7,[n.x,540,0]],[7.9,[n.x,540,0]],[9.2,[620,365,160]],[10.7,[1120,340,360]],[27,[1120,340,360]]]
                :[[0,[n.x,540,0]],[12.9,[n.x,540,0]],[14.6,[n.x,540,0]],[16.0,[1260,680,200]],[17.5,[1000,800,330]],[27,[1000,800,330]]];
            if(A){
                // These are supplied visual anchors, not newly inferred grammar.
                var anchor=objects[n.attachment],ar=anchor.sourceRectAtTime(0,false),br=l.sourceRectAtTime(0,false);
                var restX=anchor.transform.position.value[0]+ar.left+ar.width/2-(br.left+br.width/2)*A.scale_percent/100;
                var restY=540+(a?-1:1)*A.baseline_gap;
                path[3][1]=[restX+(a?42:65),restY+(a?-38:38),a?95:85];
                path[4][1]=[restX,restY,0];path[5][1]=[restX,restY,0];
                setKeys(hinge.transform.scale,[[0,[100,100,100]],[release,[100,100,100]],[park,[A.scale_percent,A.scale_percent,A.scale_percent]],[27,[A.scale_percent,A.scale_percent,A.scale_percent]]],60,30,false);
                hinge.transform.position.expression='var a=thisComp.layer('+JSON.stringify(n.attachment)+');var delta=sub(a.toWorld([0,0,0],time),a.toWorld([0,0,0],0));add(value,mul(delta,ease(time,'+present(release)+','+present(park)+',0,1)));';
            }else if(P){path[3][1]=P.parks[n.id].via;path[4][1]=P.parks[n.id].rest;path[5][1]=P.parks[n.id].rest;}
            setKeys(hinge.transform.position,path,67,25,true);
            // Cross the intermediate path point continuously, then settle once.
            // Do not ease to zero at every waypoint of the same transport.
            if(P){var p=hinge.transform.position,a0=p.keyValue(3),a1=p.keyValue(4),a2=p.keyValue(5);
                function distance(a,b){var total=0;for(var j=0;j<3;j++)total+=(a[j]-b[j])*(a[j]-b[j]);return Math.sqrt(total);}
                var speed=.6*Math.min(distance(a0,a1)/(p.keyTime(4)-p.keyTime(3)),distance(a1,a2)/(p.keyTime(5)-p.keyTime(4)));
                p.setTemporalEaseAtKey(4,[new KeyframeEase(speed,32)],[new KeyframeEase(speed,24)]);}
            setKeys(hinge.transform.yRotation,a?[[0,0],[6.7,0],[7.9,-55],[9.2,-48],[10.7,A?0:-8],[27,A?0:-8]]:[[0,0],[12.9,0],[14.6,-52],[16,-37],[17.5,A?0:7],[27,A?0:7]],64,28,false);
            setKeys(hinge.transform.zRotation,a?[[0,0],[7.9,0],[9.2,-7],[10.7,A?0:-3],[27,A?0:-3]]:[[0,0],[14.6,0],[16,6],[17.5,A?0:3],[27,A?0:3]],60,30,false);
        }
    }
    var targetX=650;
    for(i=0;i<R.layout.length;i++)if(R.layout[i].role==='core') {
        var n=R.layout[i],l=objects[n.id];
        var response=n.id==='core-subject'?519:n.x;
        var corePath=P?[[0,[n.x,540,0]],[9.65,[n.x,540,0]],[10.9,[response,540,0]],[27,[response,540,0]]]
            :[[0,[n.x,540,0]],[9.65,[n.x,540,0]],[10.9,[response,540,0]],[18.6,[response,540,0]],[19.7,[targetX-5,537,0]],[20.55,[targetX,540,0]],[27,[targetX,540,0]]];
        setKeys(l.transform.position,corePath,70,18,false);
        targetX+=n.width;
    }
    var axis=rectangle(cp,'CORE_READING_AXIS',targetX-650,1,S.palette.fog,[P?803.5:(targetX+650)/2,573,0],true);
    setKeys(axis.transform.opacity,P?[[0,0],[15.3,0],[17.5,45],[27,45]]:[[0,0],[20.0,0],[20.65,45],[27,45]],55,35,false);
    var focus=null3(cp,'FOCUS_TARGET',[915,540,0]);
    setKeys(focus.transform.position,[[0,[915,540,0]],[3,[915,540,0]],[5.4,[545,540,0]],[7.8,[520,540,65]],[8.6,[820,540,0]],[10.8,[820,540,0]],[11.8,[1330,540,0]],[14.6,[1320,540,80]],[15.3,[820,540,0]],[18.5,[820,540,0]],[20.6,[P?803.5:934,540,0]],[27,[P?803.5:934,540,0]]],55,50,true);
    // Resolve the rotated text through its real parent hierarchy. After release,
    // give focus back to the retained structure; do not chase the parked fragment.
    var clock=P?'var rows='+JSON.stringify(P.time_map)+';function original(t){for(var i=1;i<rows.length;i++)if(t<=rows[i][1])return rows[i-1][0]+(t-rows[i-1][1])*(rows[i][0]-rows[i-1][0])/(rows[i][1]-rows[i-1][1]);return 27;}var beat=original(time);':'var beat=time;';
    focus.transform.position.expression=clock+'function center(name){var l=thisComp.layer(name);var r=l.sourceRectAtTime(time,false);return l.toWorld([r.left+r.width/2,r.top+r.height/2,0]);}function w(a,b,c,d){if(beat<a||beat>d)return 0;if(beat<b)return ease(beat,a,b,0,1);if(beat<=c)return 1;return ease(beat,c,d,1,0);}var wa=w(5.6,6.5,7.9,8.6);var wb=w(11.8,12.8,14.6,15.3);var amount=wa+wb;amount>0?add(value,mul(sub(center(wa>0?"aside-time":"aside-map"),value),amount)):value;';
    var camera=cp.layers.addCamera('GUIDED_CAMERA',[960,540]);camera.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    var cameraPath=P?[[0,[960,540,-2100]],[3,[960,540,-2100]],[5.3,[650,470,-1640]],[10.9,[650,470,-1640]],[11.7,[1230,505,-1710]],[17.6,[1230,505,-1710]],[22.5,[803.5,540,-1280]],[27,[803.5,540,-1280]]]
        :[[0,[960,540,-2100]],[3,[960,540,-2100]],[5.3,[650,470,-1850]],[10.9,[650,470,-1850]],[11.7,[1230,505,-1710]],[17.6,[1230,505,-1710]],[18.4,[970,540,-1900]],[20.6,[970,540,-1900]],[22.5,[934,540,-1320]],[27,[934,540,-1320]]];
    var lookPath=P?[[0,[960,540,0]],[3,[960,540,0]],[5.3,[810,520,0]],[10.9,[810,520,0]],[11.7,[1090,535,0]],[17.6,[1090,535,0]],[22.5,[803.5,540,0]],[27,[803.5,540,0]]]
        :[[0,[960,540,0]],[3,[960,540,0]],[5.3,[830,520,0]],[10.9,[830,520,0]],[11.7,[1090,535,0]],[17.6,[1090,535,0]],[18.4,[950,540,0]],[20.6,[950,540,0]],[22.5,[934,540,0]],[27,[934,540,0]]];
    setKeys(camera.transform.position,cameraPath,68,30,true);
    setKeys(camera.transform.pointOfInterest,lookPath,65,35,true);
    var opt=camera.property('ADBE Camera Options Group');opt.property('ADBE Camera Zoom').setValue(1850);
    opt.property('ADBE Camera Depth of Field').setValue(1);opt.property('ADBE Camera Aperture').setValue(64);opt.property('ADBE Camera Blur Level').setValue(100);
    opt.property('ADBE Camera Focus Distance').expression='var p=thisComp.layer("FOCUS_TARGET").toWorld([0,0,0]);var c=transform.position;var v=normalize(sub(transform.pointOfInterest,c));dot(sub(p,c),v);';
    if(A){
        for(i=0;i<R.layout.length;i++)if(R.layout[i].role==='supplied_modifier'){
            var n=R.layout[i],above=n.id==='aside-time',release=present(above?7.9:14.6),park=present(above?10.7:17.5);
            var line=cp.layers.addShape();line.name='RELATION_'+n.id;
            line.comment=JSON.stringify({origin:R.scene_sha,anchor_id:n.attachment,object_id:n.id,kind:'supplied_synthetic_visual_attachment'});
            line.transform.anchorPoint.setValue([0,0]);line.transform.position.setValue([0,0]);
            line.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
            line.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Group');
            line.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Stroke');
            var vectors=line.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
            vectors.property('ADBE Vector Graphic - Stroke').property('ADBE Vector Stroke Color').setValue(rgb(S.palette.fog));
            vectors.property('ADBE Vector Graphic - Stroke').property('ADBE Vector Stroke Width').setValue(1.5);
            vectors.property('ADBE Vector Shape - Group').property('ADBE Vector Shape').expression=
                'var a=thisComp.layer('+JSON.stringify(n.attachment)+'),b=thisComp.layer('+JSON.stringify(n.id)+');var ar=a.sourceRectAtTime(time,false),br=b.sourceRectAtTime(time,false);var p=a.toComp([ar.left+ar.width/2,'+(above?'ar.top-8':'ar.top+ar.height+8')+',0]);var q=b.toComp([br.left+br.width/2,'+(above?'br.top+br.height+8':'br.top-8')+',0]);createPath([[p[0],p[1]],[q[0],q[1]]],[],[],false);';
            var rows=[[0,0],[release+.1,0],[release+.3,62],[park+A.connector_hold_seconds,62],[park+A.connector_hold_seconds+A.connector_fade_seconds,0],[cp.duration,0]];
            for(var j=0;j<rows.length;j++)line.transform.opacity.setValueAtTime(rows[j][0],rows[j][1]);
        }
    }
    cp.openInViewer();app.project.save(dest);
    return JSON.stringify({ok:true,comp_id:cp.id,scene_sha:R.scene_sha,spec_sha:R.spec_sha,project:dest.fsName,renderer:cp.renderer,objects:R.layout.length});
})();
