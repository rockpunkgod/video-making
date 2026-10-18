"""Regression checks for concrete user-reported reading/handoff failures.

These checks reject missing coverage, reversed focus, line pulses and a hard
mask reveal. They do not certify aesthetics, comprehension or human approval.
"""
import json
import math


def validate_reading(plan_scenes, audit, observed, article_chunking=None):
    authored = {c['id']: c for a in article_chunking['articles'].values() for c in a['chunks']} if article_chunking else None
    expected=[(s['id'],e['start'],e['end'],e['arrival'],e['end_time'])
              for s in plan_scenes for e in s.get('reading_events',[])]
    windows=audit.get('reading_windows',[])
    actual=[(w['scene'],w['source_start'],w['source_end'],w['arrival'],w['end_time']) for w in windows]
    if len(expected)!=len(actual) or any(a[:3]!=b[:3] or any(abs(x-y)>1e-6 for x,y in zip(a[3:],b[3:])) for a,b in zip(expected,actual)):
        raise ValueError('Every authored reading window, including scope/hit/revisit, needs phrase focus')
    samples={w['id']:w for w in observed['windows']}
    if len(samples)!=len(windows):raise ValueError('Incomplete native reading-window observation')
    count=0
    for w in windows:
        chunks=w['chunks'];sample=samples[w['id']]
        if not chunks or len(chunks)!=len(sample['chunks']):raise ValueError('Missing native phrase chunks')
        if not sample.get('all_rows_covered'):raise ValueError('A complete native reading row was skipped')
        previous=-1;last_center=-1
        for wanted,actual in zip(chunks,sample['chunks']):
            if wanted['source_start']<previous or wanted['center']<=last_center:
                raise ValueError('Reading focus must advance by row, left to right')
            previous=wanted['source_end'];last_center=wanted['center']
            if actual['text']!=wanted['text'] or actual['range']!=[wanted['start'],wanted['end']]:raise ValueError('Native phrase differs from exact source')
            if authored is not None:
                source = authored.get(wanted.get('chunk_id'))
                if source is None or (source['start'],source['end'],source['text']) != (wanted['source_start'],wanted['source_end'],wanted['text']):
                    raise ValueError('Native focus split, merged or replaced an authored sense group')
                if actual.get('no_break') is not True:raise ValueError('Native layout lost the whole-phrase noBreak constraint')
            elif len(wanted['text'].split())>6:raise ValueError('A long line was substituted for a phrase chunk')
            if not actual['inside_measured_line']:raise ValueError('Phrase crosses a native line')
            if actual['expression_error'] or not actual['threeD']:raise ValueError('Broken expression or lost native 3D')
            if max(actual['rest_error'])>.001 or not 103.9<=actual['peak']<=104.01:raise ValueError('Phrase scale must return smoothly to its original size')
            if actual['color_peak']<99.9:raise ValueError('Color and scale focus are out of sync')
            if not actual['coverage_complete']:raise ValueError('A native row contains unread words')
            count+=1
        dominant=[]
        for frame in sample['frames']:
            values=frame['amounts']
            if min(values)<-1e-5 or max(values)>100.001:raise ValueError('Focus overshoot')
            if max(values)>50:
                ix=max(range(len(values)),key=values.__getitem__)
                if not dominant or dominant[-1]!=ix:dominant.append(ix)
        if dominant!=list(range(len(chunks))):raise ValueError('Some chunks never visibly lead, or reading jumps backward')
    expected_queries=[s['id'] for s in plan_scenes if s['kind']=='locate']
    if [q['scene'] for q in audit['query_handoffs']]!=expected_queries:raise ValueError('Missing continuous question handoff')
    for q in observed['handoffs']:
        if q['margin_before_exit']>.001:raise ValueError('Top mask would reveal the full stem in one frame')
        if q['source_join']<99.9 or q['landed_error']>.01:raise ValueError('Missing-word frame or mismatched original position')
        if q['ink_error']>.001:raise ValueError('Query returns in the wrong color')
        for prev,cur in zip(q['frames'],q['frames'][1:]):
            if cur['opacity']>prev['opacity']+.001 or abs(cur['opacity']-prev['opacity'])>25:
                raise ValueError('Question mask must leave continuously')
            if max(abs(x-y) for x,y in zip(prev['color'],cur['color']))>.10:raise ValueError('Query color flashes')
        if any(not all(math.isfinite(v) for v in row['screen']) or row['screen'][1]<-.01 for row in q['frames']):raise ValueError('Carried query exits above the viewport')
    return {'status':'PASS','reading_windows':len(windows),'phrase_chunks':count,
            'query_handoffs':len(expected_queries),'article_chunking_checked':authored is not None,'human_visual_review':'PENDING'}


def native_reading_script(comp_id,audit):
    spec={'comp':comp_id,'windows':audit['reading_windows'],'handoffs':audit['query_handoffs']}
    return 'var S='+json.dumps(spec,ensure_ascii=False)+';'+r'''
var c=app.project.itemByID(S.comp),out={windows:[],handoffs:[]};
for(var wi=0;wi<S.windows.length;wi++){
 var w=S.windows[wi],checks=[],props=[],rows={};
 for(var j=0;j<w.chunks.length;j++){
  var ck=w.chunks[j],l=c.layer(ck.layer_name),d=l.property('Source Text').valueAtTime(w.arrival,false),aa=l.property('ADBE Text Properties').property('ADBE Text Animators'),an=aa.property(ck.animator),scale=an.property('ADBE Text Animator Properties').property('ADBE Text Scale 3D'),sel=an.property('ADBE Text Selectors').property(1),co=aa.property(ck.color_animator).property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount'),line=d.composedLineRange(ck.row,ck.row+1),key=l.name+':'+ck.row;
  if(!rows[key])rows[key]={text:d.text,lo:line.characterStart,hi:line.characterEnd,spans:[]};rows[key].spans.push([ck.start,ck.end]);
  checks.push({text:d.text.slice(ck.start,ck.end),range:[sel.property('ADBE Text Index Start').value,sel.property('ADBE Text Index End').value],no_break:d.characterRange(ck.start,ck.end).noBreak===true,inside_measured_line:ck.start>=line.characterStart&&ck.end<=line.characterEnd,expression_error:scale.expressionError,threeD:l.threeDLayer,peak:scale.valueAtTime(ck.center,false)[0],rest_error:[Math.abs(scale.valueAtTime(ck.time_start-1/24,false)[0]-100),Math.abs(scale.valueAtTime(ck.time_end+1/24,false)[0]-100)],color_peak:co.valueAtTime(ck.center,false),row_key:key});props.push(co);
 }
 for(var j=0;j<checks.length;j++){var row=rows[checks[j].row_key],complete=true;for(var k=row.lo;k<row.hi;k++){if(/\s/.test(row.text.charAt(k)))continue;var covered=false;for(var sp=0;sp<row.spans.length;sp++)if(k>=row.spans[sp][0]&&k<row.spans[sp][1])covered=true;if(!covered)complete=false;}checks[j].coverage_complete=complete;}
 var frames=[];for(var frame=Math.ceil(w.arrival*24-1e-6);frame<=Math.floor(w.end_time*24+1e-6);frame++){var amounts=[];for(var j=0;j<props.length;j++)amounts.push(props[j].valueAtTime(frame/24,false));frames.push({frame:frame,amounts:amounts});}
 var complete=true,prefix=w.chunks[0].layer_name.split('-source-')[0]+'-source-';
 for(var li=1;li<=c.numLayers;li++){var source=c.layer(li);if(source.name.indexOf(prefix)!==0)continue;var binding=JSON.parse(source.comment);if(binding.start>=w.source_end||binding.end<=w.source_start)continue;var d=source.property('Source Text').valueAtTime(0,false);for(var lineIndex=0;lineIndex<d.composedLineCount;lineIndex++){var line=d.composedLineRange(lineIndex,lineIndex+1);if(binding.start+line.characterStart>=w.source_end||binding.start+line.characterEnd<=w.source_start)continue;if(!rows[source.name+':'+lineIndex])complete=false;}}
 out.windows.push({id:w.id,chunks:checks,frames:frames,all_rows_covered:complete});
}
function project(p,t){var cam=c.layer('READING_CAMERA'),a=cam.transform.position.valueAtTime(t,false),b=cam.transform.pointOfInterest.valueAtTime(t,false),f=[],n=0;for(var j=0;j<3;j++){f[j]=b[j]-a[j];n+=f[j]*f[j];}n=Math.sqrt(n);for(var j=0;j<3;j++)f[j]/=n;n=Math.sqrt(f[2]*f[2]+f[0]*f[0]);var r=[f[2]/n,0,-f[0]/n],u=[f[1]*r[2],f[2]*r[0]-f[0]*r[2],-f[1]*r[0]],d=0,x=0,y=0;for(var j=0;j<3;j++){var v=p[j]-a[j];d+=v*f[j];x+=v*r[j];y+=v*u[j];}return [c.width/2+cam.cameraOption.zoom.value*x/d,c.height/2+cam.cameraOption.zoom.value*y/d,d];}
for(var j=0;j<S.handoffs.length;j++){
 var q=S.handoffs[j],l=c.layer(q.layer_name),m=c.layer(q.margin),an=l.property('ADBE Text Properties').property('ADBE Text Animators').property(q.color_animator),color=an.property('ADBE Text Animator Properties').property('ADBE Text Fill Color'),source=c.layer(q.question).property('ADBE Text Properties').property('ADBE Text Animators').property(q.source_animator),join=source.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount'),frames=[];
 for(var fr=Math.ceil(q.start*24);fr<=Math.ceil(q.end*24);fr++){var t=fr/24;frames.push({frame:fr,opacity:m.transform.opacity.valueAtTime(t,false),screen:project(l.transform.position.valueAtTime(t,false),t),color:color.valueAtTime(t,false)});}
 var p=l.transform.position.valueAtTime(q.landed,false),err=0,col=color.valueAtTime(q.landed,false),ink=source.property('ADBE Text Animator Properties').property('ADBE Text Fill Color').value,ce=0;for(var k=0;k<3;k++){err=Math.max(err,Math.abs(p[k]-q.origin[k]));ce=Math.max(ce,Math.abs(col[k]-ink[k]));}
 out.handoffs.push({scene:q.scene,margin_before_exit:m.transform.opacity.valueAtTime(q.end-.5/24,false),source_join:join.valueAtTime(q.end-.25/24,false),landed_error:err,ink_error:ce,frames:frames});
}return out;
'''
