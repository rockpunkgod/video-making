/* Reads explicit frozen scene projections only. Not a solver or Review producer. */
(function(){
    var f=new File(PASSAGE_REQUEST);f.encoding='UTF-8';f.open('r');var r=JSON.parse(f.read());f.close();
    var project=new File(r.project);
    if(project.exists)throw new Error('Preserve existing project revision');
    app.project.save(project);
    function col(h){return [parseInt(h.substr(1,2),16)/255,parseInt(h.substr(3,2),16)/255,parseInt(h.substr(5,2),16)/255];}
    var ink='#243530',accent='#527B65',secondary='#64716C',paper='#FAF8F2',results=[];
    function text(cp,name,copy,x,y,size,font,color){
        var l=cp.layers.addText(copy);l.name=name;
        var p=l.property('Source Text'),d=p.value;d.font=font;d.fontSize=size;d.applyFill=true;
        d.fillColor=col(color);d.applyStroke=false;d.tracking=0;d.autoLeading=false;d.leading=size*1.24;
        d.justification=ParagraphJustification.LEFT_JUSTIFY;p.setValue(d);
        var box=l.sourceRectAtTime(0,false);l.transform.anchorPoint.setValue([box.left,box.top]);l.transform.position.setValue([x,y]);
        return l;
    }
    function line(cp,name,x,y,width,start){
        var l=cp.layers.addShape();l.name=name;
        var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
        var rect=g.addProperty('ADBE Vector Shape - Rect');rect.property('ADBE Vector Rect Size').setValue([width,3]);
        var fill=g.addProperty('ADBE Vector Graphic - Fill');fill.property('ADBE Vector Fill Color').setValue(col(accent));
        l.transform.anchorPoint.setValue([-width/2,0]);l.transform.position.setValue([x,y]);
        l.transform.scale.setValueAtTime(start,[0,100]);l.transform.scale.setValueAtTime(start+.6,[100,100]);
        var a=new KeyframeEase(0,70);for(var k=1;k<=2;k++)l.transform.scale.setTemporalEaseAtKey(k,[a,a,a],[a,a,a]);
        l.motionBlur=false;return l;
    }
    app.beginUndoGroup('Bound passage scenes');
    try{
        for(var i=0;i<r.scenes.length;i++){
            var s=r.scenes[i],cp=app.project.items.addComp('PASSAGE_'+s.segment_id,1920,1080,1,s.duration||24,24);
            cp.bgColor=col(paper);cp.comment=JSON.stringify({segment_sha:s.segment_sha,plan_sha:r.plan_sha||'STYLE_ONLY'});
            cp.layers.addSolid(col(paper),'BACKGROUND',1920,1080,1,cp.duration);
            text(cp,'HEADER',s.heading,150,55,28,'NotoSansSC-Regular',secondary);
            text(cp,'QUESTION',s.stem,150,112,38,'NotoSansSC-Regular',ink);
            text(cp,'SOURCE',s.source,150,266,42,'Georgia',ink);
            text(cp,'JUDGMENT',s.screen,150,575,52,'NotoSansSC-Regular',ink);
            for(var o=0;o<s.options.length;o++){
                var option=s.options[o],color=option.state==='retain'?accent:option.state==='eliminate'?secondary:ink;
                text(cp,'OPTION_'+option.letter,option.text,1080,560+o*79,30,'NotoSansSC-Regular',color);
                if(option.state==='retain')line(cp,'SELECT_'+option.letter,1047,579+o*79,18,1.0);
            }
            function measure(copy){var probe=text(cp,'MEASURE',copy,0,0,42,'Georgia',ink),box=probe.sourceRectAtTime(0,false);probe.remove();return box.width;}
            for(var j=0;j<s.annotations.length;j++){
                var an=s.annotations[j],offset=measure(an.prefix+'|')-measure('|');
                line(cp,'SOURCE_MARK_'+j,150+offset,266+an.line*52.08+48,measure(an.quote),.5+j*.65);
            }
            var rows=[];
            for(var z=1;z<=cp.numLayers;z++){
                var l=cp.layer(z);if(l instanceof TextLayer){var d=l.property('Source Text').value,b=l.sourceRectAtTime(0,false);
                    rows.push({name:l.name,text:d.text,font:d.font,size:d.fontSize,width:b.width,height:b.height,position:l.transform.position.value});}
            }
            if(r.styleframes){var target=new File(r.styleframes+'/'+s.segment_id+'.png');cp.saveFrameToPng(3.5,target);}
            results.push({segment_id:s.segment_id,comp_id:cp.id,rows:rows});
        }
        app.project.save(project);return JSON.stringify({project:project.fsName,scenes:results});
    }finally{app.endUndoGroup();}
})();
