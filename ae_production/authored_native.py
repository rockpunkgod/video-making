"""Native execution of the authored AV plan through existing Adobe bridges.

Shared HostOwnership is mandatory. The machine paths and source material stay
in the private author input. Receipts permit reuse of completed render parts;
an uncertain or incomplete dispatch is never replayed automatically.
"""
import json
import shutil
from pathlib import Path
import subprocess
import time
import wave

from video_contracts import ROOT, read, write
from scripts.voice_delivery import sha256
from ae_production.bridge import JunkdogeClient, BridgeError
from ae_production.host_ownership import HostOwnership
from ae_production.memory_guard import available_memory, monitor_existing_render
from ae_production.authored_episode import checked_author,delivery_path
from ae_production.article_chunking import current_chunks
from creative_os.teaching_focus import require_focus, resource_report
from video_contracts import sha
from premiere_production.mcp import PremiereMcpClient
from premiere_production.lossless_handoff import packet_binding

TEMPLATE=ROOT/'ae/templates/authored-episode.jsx'
READING_RIG=ROOT/'ae/rigs/reading-focus.jsx'


def template_source():
    """The experiment and future builds consume this same native rig."""
    source=TEMPLATE.read_text('utf-8')
    if source.count('/* SHARED_READING_RIG */')!=1:
        raise ValueError('Production template must consume the shared reading rig exactly once')
    return source.replace('/* SHARED_READING_RIG */',READING_RIG.read_text('utf-8'))


def media_directory(folder):
    path=folder/'media';path.mkdir(exist_ok=True)
    return path


def require_disk(path,minimum):
    if shutil.disk_usage(path).free<minimum:
        raise RuntimeError('Insufficient disk space at '+str(path)+'; inspect storage before native dispatch')


def value(r):
    if isinstance(r,dict) and r.get('contentType')=='text':r=r['content']
    elif isinstance(r,dict) and 'result' in r:r=r['result']
    return json.loads(r) if isinstance(r,str) else r


def process(name):
    payload=subprocess.check_output(['powershell','-NoProfile','-Command',
        "@(Get-Process -Name '"+name+"' -ErrorAction SilentlyContinue | Select-Object Id,MainWindowHandle) | ConvertTo-Json -Compress"],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    rows=json.loads(payload or '[]')
    if not rows:raise RuntimeError('Adobe host is not running: '+name+'; saved outputs remain available')
    if isinstance(rows,dict):rows=[rows]
    if len(rows)!=1:raise RuntimeError('Expected one unambiguous Adobe host: '+name)
    return rows[0]


def plan(folder):
    a,bundles=checked_author(folder);p=read(folder/'AV_PLAN.json')
    if p['author_sha256']!=sha256(folder/'AV_AUTHOR.json') or p['voice_delivery_sha256']!=sha256(delivery_path(folder,a)) or p['alignment_sha256']!=sha256(folder/'VOICE_ALIGNMENT.json'):
        raise ValueError('Copy/voice/director changes have not propagated through prepare')
    for s in p['segments']:
        v=s['voice']
        if sha256(v['path'])!=v['sha256'] or sha256(v['padded_path'])!=v['padded_sha256']:
            raise ValueError('Complete audio take changed')
    if 'teaching_focus' in a:
        if p.get('teaching_focus_sha')!=sha(a['teaching_focus']) or p.get('teaching_resources')!=resource_report(a,p):
            raise ValueError('Teaching value allocation is stale or was bypassed')
    if 'article_chunking' in p and p['article_chunking'] != current_chunks(folder,bundles):
        raise ValueError('Article chunking has not propagated into the native plan')
    return a,p


class Host:
    def __init__(self,folder,kind):
        self.folder=folder;self.a,_=plan(folder);self.kind=kind;self.h=self.a['host']
        self.native_name='AfterFX' if kind=='after_effects' else 'Adobe Premiere Pro'
        proc=process(self.native_name);self.pid=proc['Id'];self.hwnd=proc['MainWindowHandle']
        self.project=(media_directory(folder)/('MAIN_FILM.aep' if kind=='after_effects' else 'MAIN_FILM.prproj')).resolve()
        if kind=='after_effects':self.c=JunkdogeClient(self.h['ae_endpoint'])
        else:self.c=PremiereMcpClient(self.h['premiere_endpoint'],Path(self.h['premiere_token_file']).read_text().strip())
        self.c.initialize()

    def js(self,code,label=None,timeout=600):
        args={'code':'(function(){return JSON.stringify((function(){'+code+'})());})();','timeout_sec':min(timeout,600)}
        if label:args['undo_group_name']=label
        return value(self.c.call('ae_exec',args,timeout=timeout+30))

    def identity(self):
        pid=process(self.native_name)['Id']
        if self.kind=='after_effects':
            # v0.11's instance registry can briefly lag a save/open/new. Retry
            # only this read-only identity inspection with a fresh binding.
            # Never replay the mutation whose result is being inspected.
            for attempt in range(5):
                try:
                    self.c.bind_current_project(pid,self.folder.resolve())
                    r=self.js('var a=app.project.activeItem;if(!(a instanceof CompItem)&&app.project.selection.length===1)a=app.project.selection[0];return {project_path:app.project.file?app.project.file.fsName:"",target_id:a instanceof CompItem?"comp:"+a.id:"none",dirty:app.project.dirty,rendering:app.project.renderQueue.rendering};')
                    break
                except BridgeError as error:
                    if 'SOURCE_PROJECT_CHANGED' not in str(error) or attempt==4:raise
                    self.c.context_id=None;self.c.bound_project=None;time.sleep(.4)
        else:
            data=self.c.call('get_project_info');active=data.get('activeSequence');r={'project_path':data['path'],'target_id':'sequence:'+active['id'] if active else 'none'}
        r['project_path']=str(Path(r['project_path']).resolve()) if r['project_path'] else ''
        return {**r,'process_id':pid}

    def mutate(self,label,operation,after=None):
        plan(self.folder);before=self.identity();key='ae_expected_project' if self.kind=='after_effects' else 'premiere_expected_project'
        if Path(before['project_path']).resolve() not in (Path(self.h[key]).resolve(),self.project.resolve()):
            raise ValueError('Unexpected host project; do not replace another task')
        if Path(before['project_path']).resolve()==self.project.resolve():
            bound=self.folder/('native-identity.json' if self.kind=='after_effects' else 'PR_SEQUENCE.json')
            if bound.exists():
                data=read(bound);expected='comp:'+str(data['comp_id']) if self.kind=='after_effects' else 'sequence:'+data['id']
                if before['target_id']!=expected:raise ValueError('Active native target changed; inspect before continuing')
        if before.get('dirty') or before.get('rendering'):raise ValueError('Host must be clean and idle')
        target={k:before[k] for k in ('process_id','project_path','target_id')}
        lease=HostOwnership(self.kind,'/root',self.folder.name,target,Path(self.h['ownership_directory']));lease.acquire()
        receipt=self.folder/'dispatch'/str(time.time_ns());receipt.parent.mkdir(exist_ok=True)
        write(receipt.with_suffix('.pending.json'),{'label':label,'before':before,'token':lease.record['token']})
        def call():
            try:r=operation()
            except BaseException as e:write(receipt.with_suffix('.error.json'),{'error':str(e)});raise
            write(receipt.with_suffix('.transport.json'),r);return r
        result=lease.mutate(self.identity,call,target_after=after);observed=self.identity();lease.release(self.identity)
        write(receipt.with_suffix('.complete.json'),{'label':label,'result':result,'identity':observed,'token':lease.record['token']})
        return result

    def mutation_js(self,code,label,after=None):
        # v0.11 rejects project transitions/rendering inside a tool undo group.
        # The ownership/checkpoint label is independent of AE's undo stack.
        return self.mutate(label,lambda:self.js(code),after)

    def pr(self,name,args=None,after=None,timeout=180):
        return self.mutate(name,lambda:self.c.call(name,args or {},timeout=timeout),after)


def build(folder):
    a,p=plan(folder);require_focus(a)
    if 'article_chunking' not in p:raise ValueError('Run chunks and prepare before a new native build')
    h=Host(folder,'after_effects');before=h.identity()
    require_disk(folder,64*1024**2)
    require_disk(h.project.parent,256*1024**2)
    if h.project.exists() or (folder/'native-identity.json').exists():raise FileExistsError('Inspect saved native output; no implicit rebuild')
    code=template_source().replace('PLAN_PATH',json.dumps((folder/'AV_PLAN.json').as_posix())).replace('PROJECT_PATH',json.dumps(h.project.as_posix())).replace('PLAN_SHA',json.dumps(sha256(folder/'AV_PLAN.json'))).replace('BUILD_RECEIPT_PATH',json.dumps((folder/'BUILD_BEFORE_SAVE.json').as_posix()))
    write(folder/'SESSION_BEFORE.json',{'identity':before,'sha256':sha256(before['project_path']) if before['project_path'] else None})
    r=h.mutation_js(code,'Build current authored main film',after=lambda r:{'process_id':h.pid,'project_path':str(h.project.resolve()),'target_id':'comp:'+str(r['comp_id'])})
    r.update(plan_sha256=sha256(folder/'AV_PLAN.json'),template_sha256=sha256(TEMPLATE),reading_rig_sha256=sha256(READING_RIG))
    write(folder/'native-identity.json',r)
    return {k:r[k] for k in ('comp_id','master_comp_id','duration','frames','layers','media_role')}


def current_native(folder):
    a,p=plan(folder);n=read(folder/'native-identity.json')
    if n['plan_sha256']!=sha256(folder/'AV_PLAN.json') or n['template_sha256']!=sha256(TEMPLATE) or n.get('reading_rig_sha256')!=sha256(READING_RIG):
        raise ValueError('Native picture is stale after author or realization changes')
    return a,p,n


def audit(folder):
    a,p,n=current_native(folder);h=Host(folder,'after_effects')
    code="var c=app.project.itemByID(CID),rows=[];for(var i=1;i<=c.numLayers;i++){var l=c.layer(i),r={name:l.name,id:l.id,inPoint:l.inPoint,outPoint:l.outPoint,threeD:l.threeDLayer,parent:l.parent?l.parent.id:null,comment:l.comment};if(l instanceof TextLayer){r.text=l.property('Source Text').value.text;r.font=l.property('Source Text').value.font;if(l.name.indexOf('-source-')>=0&&l.name.indexOf('EXTRACT_')!==0){var initial=l.property('Source Text').valueAtTime(0,false);r.initial_color=initial.characterRange(0,initial.text.length).fillColor||null;r.text_height=l.sourceRectAtTime(0,false).height;}}if(l instanceof CameraLayer||l.name.indexOf('SOURCE_LIFT_')===0||l.name.indexOf('CANDIDATE_FLIGHT_')===0||l.name.indexOf('-source-')>=0){r.position=[];r.orientation=[];var pos=l.transform.position;r.position_value=pos.value;r.scale=[];var sp=l.transform.scale;if(sp)for(var sk=1;sk<=sp.numKeys;sk++)r.scale.push([sp.keyTime(sk),sp.keyValue(sk)]);for(var j=1;j<=pos.numKeys;j++)r.position.push([pos.keyTime(j),pos.keyValue(j)]);if(!(l instanceof CameraLayer)){var ori=l.transform.orientation;for(var j=1;j<=ori.numKeys;j++)r.orientation.push([ori.keyTime(j),ori.keyValue(j)]);}}rows.push(r);}return {project:app.project.file.fsName,width:c.width,height:c.height,duration:c.duration,fps:c.frameRate,layers:rows};".replace('CID',str(n['comp_id']))
    r=h.js(code)
    r['candidate_initial_opacity']=h.js('var c=app.project.itemByID('+str(n['comp_id'])+'),rows=[];for(var i=1;i<=c.numLayers;i++){var l=c.layer(i);if(l.name.indexOf("_OPTION_")>=0)rows.push({name:l.name,opacity:l.transform.opacity.valueAtTime(0,false)});}return rows;')
    write(folder/'NATIVE_READBACK.json',r)
    native={x['name']:x for x in r['layers']}
    if [r['width'],r['height'],r['fps'],round(r['duration']*24)]!=[1920,1080,24,p['frames']]:raise ValueError('Native canvas changed')
    if Path(r['project']).resolve()!=h.project.resolve():raise ValueError('Wrong native project')
    if any(x['opacity']!=100 for x in r['candidate_initial_opacity']):raise ValueError('Candidate elimination leaked into the question opening')
    for world,w in p['worlds'].items():
        for b in w['blocks']:
            if b['visible'] and native[b['id']]['text'].replace('\r','\n')!=b['text']:raise ValueError('Frozen source text altered')
            if b['visible'] and p.get('realization')=='continuous_paper_scan':
                color=native[b['id']].get('initial_color')
                if not color or len(color)!=3 or any(abs(x-y)>.002 for x,y in zip(color,[.09,.13,.16])):
                    raise ValueError('Search highlight appeared before its reading event')
        for cid,text in w['question']['options'].items():
            if native[world+'_OPTION_'+cid]['text']!=cid+'   '+text:raise ValueError('Candidate text altered')
    for ex in n['audit']['extractions']:
        row=native['SOURCE_LIFT_'+ex['scene']]
        # AE stores spatial coordinates as float32; compare within 0.001 px,
        # while retaining the actual readback rather than rounding its evidence.
        same_origin=lambda v:all(abs(x-y)<.001 for x,y in zip(v,ex['origin']))
        if not row['threeD'] or not same_origin(row['position'][0][1]) or not same_origin(row['position'][-1][1]):
            raise ValueError('Source lift/return lost its native origin')
        if abs(row['position'][0][0]-ex['start'])>1e-4:raise ValueError('Source recognition clock not consumed')
        if p.get('realization')=='continuous_paper_scan':
            shot=next(s for s in p['scenes'] if s['id']==ex['scene']);excerpt=p['excerpts'][shot['excerpt']]
            blocks={b['id']:b for b in p['worlds'][excerpt['world']]['blocks']}
            refs=[r for r in shot['source_refs'] if r['world']==excerpt['world'] and r['pointer']=='/passage']
            selected=[bid for bid in excerpt['block_ids'] if any(r['start']<blocks[bid]['end'] and r['end']>blocks[bid]['start'] for r in refs)]
            prefix='EXTRACT_'+ex['scene']+'_'
            if not selected or {name for name in native if name.startswith(prefix)}!={prefix+bid for bid in selected}:
                raise ValueError('Working comparison must use its explicitly bound source blocks')
            first=native[selected[0]]['position_value'];height=sum(native[bid]['text_height'] for bid in selected)+36*(len(selected)-1)
            expected_scale=min(100,310/height*100)
            scales=[v for t,v in row['scale'] if abs(t-ex['settled'])<.0001]
            if len(scales)!=1 or any(abs(v-expected_scale)>.002 for v in scales[0]):raise ValueError('Readable source placement was not consumed')
            for bid in selected:
                child=native[prefix+bid];origin=[0,native[bid]['position_value'][1]-first[1],0]
                ends=[child['position'][0][1],child['position'][-1][1]] if child['position'] else [child['position_value']]
                if child['parent']!=row['id'] or child['text'].replace('\r','\n')!=blocks[bid]['text'] or any(any(abs(a-b)>.002 for a,b in zip(v,origin)) for v in ends):
                    raise ValueError('Selected source text lost its own original position')

    for ev in n['audit']['candidates']:
        if ev['kind']=='final':continue
        if ev.get('treatment')=='in_place_check':
            row=native['LIGHT_CANDIDATE_'+ev['scene']]
            if row['text']!=ev['whole_option_text'] or 'SOURCE_LIFT_'+ev['scene'] in native or 'CANDIDATE_FLIGHT_'+ev['scene'] in native:
                raise ValueError('Quick check gained an unplanned extraction or lost its whole option')
            continue
        row=native['CANDIDATE_FLIGHT_'+ev['scene']]
        if row['text']!=ev['whole_option_text'] or not row['threeD']:raise ValueError('Candidate identity detached')
        if ev['kind']=='eliminate' and (row['position'][-1][1][2]!=420 or row['orientation'][-1][1]!=[0,72,0]):raise ValueError('Whole candidate withdrawal lost')
    if 'teaching_focus' in a:
        expected=[{'scene':s['id'],'treatment':s['teaching_treatment'],'motion':s['motion_treatment'],'critical_units':s['critical_units']} for s in p['scenes'] if 'teaching_treatment' in s]
        if n['audit'].get('teaching_resources')!=expected:
            raise ValueError('Teaching resource handoff did not reach the native director')
        for s in p['scenes']:
            if s.get('motion_treatment')=='critical_comparison' and 'SOURCE_LIFT_'+s['id'] not in native:
                raise ValueError('Critical method execution was silently replaced by a light check')
        light=[{'id':s['id'],'world':s['world'],'candidate':s['candidate'],'event_time':s['event_time'],
                'decision_end':s['decision_end'],'end':s['end'],'effect':s['event']} for s in p['scenes'] if s.get('motion_treatment')=='in_place_check']
        values=h.js('var c=app.project.itemByID('+str(n['comp_id'])+'),rows=[],items='+json.dumps(light)+';for(var i=0;i<items.length;i++){var s=items[i],l=c.layer("LIGHT_CANDIDATE_"+s.id),o=c.layer(s.world+"_OPTION_"+s.candidate),band=c.layer("LIGHT_READING_MARGIN_"+s.id);rows.push({scene:s.id,before:l.transform.opacity.valueAtTime(s.event_time,false),after:l.transform.opacity.valueAtTime(s.decision_end,false),original:o.transform.opacity.valueAtTime(s.decision_end,false),position_keys:l.transform.position.numKeys,scale_keys:l.transform.scale.numKeys,header_height:band.source.height,header_scale:band.transform.scale.value[1],header_read:band.transform.opacity.valueAtTime(s.event_time,false),header_exit:band.transform.opacity.valueAtTime(s.end-.5/24,false),label_above_header:l.index<band.index});}return rows;')
        for s,v in zip(light,values):
            target=38 if s['effect']=='eliminate' else 100
            if abs(v['before']-100)>.01 or abs(v['after']-target)>.01 or abs(v['original']-target)>.01 or v['position_keys'] or v['scale_keys']:
                raise ValueError('Native quick check did not consume its light state change')
            if abs(v['header_read']-100)>.01 or v['header_exit']>.01 or not v['label_above_header'] or abs(v['header_height']*v['header_scale']/100-105*r['width']/1280)>.01:
                raise ValueError('Light option overlaps source text or its header hard-pops at exit')
        write(folder/'TEACHING_RESOURCE_NATIVE.json',{'rows':values,'policy_sha':p['teaching_focus_sha'],'human_review':'PENDING'})
        accents=[{k:s[k] for k in ('id','world','source_arrive','end','attention_events')} for s in p['scenes'] if s.get('motion_treatment')=='in_place_check']
        code='var ids='+json.dumps([n['comp_id'],n['master_comp_id']])+',shots='+json.dumps(accents)+';'+r'''
var out=[];for(var ci=0;ci<ids.length;ci++){var c=app.project.itemByID(ids[ci]);for(var si=0;si<shots.length;si++){var s=shots[si];for(var ei=0;ei<s.attention_events.length;ei++){var e=s.attention_events[ei];if(e.target!=='source')continue;var matched=0;for(var li=1;li<=c.numLayers;li++){var l=c.layer(li);if(l.name.indexOf(s.world+'-source-')!==0)continue;var d=l.property('Source Text').valueAtTime(s.end-.5/24,false),at=d.text.indexOf(e.phrase);if(at<0)continue;matched++;var an=l.property('ADBE Text Properties').property('ADBE Text Animators').property('LIGHT_ACCENT_'+s.id+'_'+ei),amount=an.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount'),values=[];for(var f=Math.ceil((s.end-.5)*24);f<=Math.ceil(s.end*24);f++)values.push(amount.valueAtTime(f/24,false));out.push({comp:c.id,scene:s.id,phrase:e.phrase,before:amount.valueAtTime(Math.max(e.time,s.source_arrive)-1/24,false),peak:amount.valueAtTime(Math.max(e.time,s.source_arrive)+.25,false),after:amount.valueAtTime(s.end-.5/24,false),expression_error:amount.expressionError,ink:d.characterRange(at,at+e.phrase.length).fillColor,exit_values:values});}if(!matched)throw Error('Missing source accent');}}}return out;
'''
        accent_values=h.js(code)
        for v in accent_values:
            if (abs(v['before'])>.01 or v['peak']<99.9 or abs(v['after'])>.01 or v['expression_error']
                    or not v['ink'] or any(abs(x-y)>.002 for x,y in zip(v['ink'],[.09,.13,.16]))
                    or any(y>x+.01 or abs(x-y)>25 for x,y in zip(v['exit_values'],v['exit_values'][1:]))):
                raise ValueError('Light source accent persists into the next judgement or snaps to ink')
        write(folder/'LIGHT_ACCENT_CONTINUITY.json',{'rows':accent_values,'human_review':'PENDING'})
    for c in p['cues']:
        row=native['CAPTION_'+c['id']]
        if row['text'].replace('\r','\n')!='\n'.join(c['display_lines']) or abs(row['inPoint']-c['start'])>1e-4 or abs(row['outPoint']-c['end'])>1e-4:
            raise ValueError('Caption text or audio clock changed')
    if len(n['audit']['replays'])!=1 or any(e['scene']==n['audit']['replays'][0]['scene'] for e in p['candidate_events']):raise ValueError('Replay repeated a candidate decision')
    if p.get('realization')=='continuous_paper_scan':
        # Read real native keys/focus, not just the authored camera receipt.
        camera=h.js('var c=app.project.itemByID('+str(n['comp_id'])+'),l=c.layer("READING_CAMERA"),o=l.property("ADBE Camera Options Group"),f=c.layer("READING_FOCUS"),rows=[];for(var k=1;k<=l.transform.position.numKeys;k++){var t=l.transform.position.keyTime(k);rows.push({time:t,position:l.transform.position.keyValue(k),look:l.transform.pointOfInterest.valueAtTime(t,false),focus:f.transform.position.valueAtTime(t,false),aperture:o.property("ADBE Camera Aperture").valueAtTime(t,false)});}return {dof:o.property("ADBE Camera Depth of Field").value,focus_expression:o.property("ADBE Camera Focus Distance").expression,keys:rows};')
        expected={round(x['time'],6):x for x in n['audit']['camera']}
        close=lambda a,b:len(a)==len(b) and all(abs(x-y)<.002 for x,y in zip(a,b))
        if not camera['dof'] or 'READING_FOCUS' not in camera['focus_expression']:raise ValueError('Source reading lost its native focus consumer')
        for row in camera['keys']:
            # AE quantizes subframe scan keys (observed < 0.00003 s).
            # Keep their measured values and require one unambiguous match.
            matches=[k for k,v in expected.items() if abs(v['time']-row['time'])<.0001]
            if len(matches)!=1:raise ValueError('Unbound native camera event')
            ex=expected.pop(matches[0])
            pos=[ex['target'][0]+ex['offset'][0],ex['target'][1]+ex['offset'][1],ex['target'][2]-ex['distance']]
            if not close(row['position'],pos) or not close(row['look'],ex['target']) or not close(row['focus'],ex['target']):
                raise ValueError('Reading direction did not reach the native camera/focus')
        if expected:raise ValueError('Missing native reading camera key')
        planned=[(s['id'],e['start'],e['end'],e['arrival'],e['end_time']) for s in p['scenes'] for e in s['reading_events']]
        actual=[(e['scene'],e['start'],e['end'],e['arrival'],e['end_time']) for e in n['audit']['reading']]
        if len(planned)!=len(actual) or any(a[:3]!=b[:3] or any(abs(x-y)>.0001 for x,y in zip(a[3:],b[3:])) for a,b in zip(planned,actual)):
            raise ValueError('A reading path was silently dropped')
        for e in n['audit']['reading']:
            if not e['lines'] or any(line['start']>=e['end'] or line['end']<=e['start'] for line in e['lines']):raise ValueError('Reading path uses unrelated native lines')
        for carry in n['audit']['query_carries']:
            row=next(x for x in r['layers'] if x['id']==carry['layer_id']);binding=json.loads(row['comment'])
            if not row['threeD'] or row['text']!=binding['exact_text']:raise ValueError('Search query lost its original identity')
        r['reading_camera_and_focus']=camera
        r['measured_reading_events']=n['audit']['reading']
        if n['audit'].get('scan_motion'):
            # Read the actual continuous curves, not only their end keys. A
            # diagonal scan or a pitch reset between lines must not pass.
            source_names={x['layer_id']:x['id'] for x in n['audit']['sources']}
            spec={'comps':[n['comp_id'],n['master_comp_id']],
                  'scans':n['audit']['scan_motion'],
                  'words':[{**x,'layer_name':source_names[x['layer_id']]} for x in n['audit']['word_focus']]}
            code='var S='+json.dumps(spec)+';'+'''var errors=[],scans=[],words=[];
            for(var ci=0;ci<S.comps.length;ci++){
              var cp=app.project.itemByID(S.comps[ci]),cam=cp.layer("READING_CAMERA");
              for(var j=0;j<S.scans.length;j++){
                var s=S.scans[j],last=-1e20,count=0,p0=cam.transform.position.valueAtTime(s.pitch_start,false),p1=cam.transform.position.valueAtTime(s.pitch_end,false);
                for(var d=0;d<3;d++)if(Math.abs(p0[d]-p1[d])>.01)errors.push(s.scene+": pitch moved camera");
                for(var frame=Math.ceil(s.start*24);frame<=Math.floor(s.end*24);frame++){
                  var t=frame/24,p=cam.transform.position.valueAtTime(t,false),q=cam.transform.pointOfInterest.valueAtTime(t,false);
                  if(Math.abs(q[0]-s.column_x)>.01||Math.abs(p[0]-q[0])>.01)errors.push(s.scene+": horizontal scan");
                  if(Math.abs((p[1]-q[1])/(q[2]-p[2])+s.pitch_ratio)>.00001)errors.push(s.scene+": pitch reset");
                  if(q[1]<last-.01)errors.push(s.scene+": backward reading motion");last=q[1];count++;
                }
                scans.push({comp_id:cp.id,scene:s.scene,checked_frames:count});
              }
              for(var j=0;j<S.words.length;j++){
                var w=S.words[j],text=cp.layer(w.layer_name).property("ADBE Text Properties"),a=text.property("ADBE Text Animators").property(w.animator),scale=a.property("ADBE Text Animator Properties").property("ADBE Text Scale 3D"),sel=a.property("ADBE Text Selectors").property(1),adv=sel.property("ADBE Text Range Advanced"),values=[];
                if(scale.expression!==w.expression||scale.expressionError||text.property("ADBE Text More Options").property("ADBE Text Anchor Point Option").value!==2||sel.property("ADBE Text Index Start").value!==w.start||sel.property("ADBE Text Index End").value!==w.end||adv.property("ADBE Text Selector Smoothness").value!==0)errors.push(w.animator+": unbound word function");
                for(var k=-1;k<=21;k++){var t=w.time_start+(w.time_end-w.time_start)*k/20,v=scale.valueAtTime(t,false);if(v[0]<99.999||v[0]>104.001||Math.abs(v[0]-v[1])>.001||Math.abs(v[2]-100)>.001)errors.push(w.animator+": scale overshoot");values.push(v[0]);}
                if(Math.abs(values[0]-100)>.001||Math.abs(values[1]-100)>.001||Math.abs(values[11]-104)>.001||Math.abs(values[21]-100)>.001||Math.abs(values[22]-100)>.001)errors.push(w.animator+": attack/rest/return");
                words.push({comp_id:cp.id,animator:w.animator,values:values});
              }
            }return {errors:errors,scans:scans,words:words};'''
            motion=h.js(code)
            write(folder/'PITCH_WORD_NATIVE_AUDIT.json',motion)
            if motion['errors']:raise ValueError('Native pitch/word-focus curve failed: '+str(motion['errors'][:3]))
            r['pitch_word_time_functions']=motion
    master=h.js('var c=app.project.itemByID('+str(n['master_comp_id'])+');return {width:c.width,height:c.height,fps:c.frameRate,duration:c.duration,comment:c.comment};')
    if [master['width'],master['height'],master['fps'],round(master['duration']*24)]!=[3840,2160,24,p['frames']]:raise ValueError('Unrendered master format changed')
    r['unrendered_master']=master
    from ae_production.reading_review import native_reading_script, validate_reading
    regression=[]
    for comp_id in (n['comp_id'],n['master_comp_id']):
        observed=h.js(native_reading_script(comp_id,n['audit']))
        write(folder/('READING_CONTINUITY_NATIVE_'+str(comp_id)+'.json'),observed)
        regression.append({'comp_id':comp_id,**validate_reading(p['scenes'],n['audit'],observed,p.get('article_chunking'))})
    r['reading_continuity_regression']=regression
    r['reading_rig_sha256']=sha256(READING_RIG)
    write(folder/'native-audit.json',r)
    return {'source_text':'PASS','complete_candidate_identity_and_withdrawal':'PASS','replay_candidate_state':'PASS','caption_clock':'PASS','native_layers':len(native),'human_creative_review':'PENDING'}


def preview(folder):
    a,p,n=current_native(folder);h=Host(folder,'after_effects');loc=n['audit']['locators'][0]
    times=[2,loc['opening_at']+.2,loc['match_at']+.2,loc['scope_at']+.2,p['scenes'][2]['settled']+.25,p['scenes'][2]['candidate_start']+1,p['scenes'][7]['settled']+.2,p['scenes'][9]['settled']+1,p['scenes'][11]['settled']+1]
    out=folder/'previews';out.mkdir(exist_ok=True)
    r=h.mutate('Preview current main film native scenes',lambda:h.c.call('ae_previewFrame',{'comp_id':str(n['comp_id']),'times':times,'layout':'grid','grid_max_side':2048,'out_dir':str(out),'include_base64':False,'scale':1},timeout=220))
    write(folder/'preview-receipt.json',{'times':times,'result':r});return r


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))


def render(folder,proof=False,batch_size=96):
    a,p,n=current_native(folder);audit(folder);h=Host(folder,'after_effects')
    if not 1<=batch_size<=480:raise ValueError('Native batches are limited to 20 seconds')
    total=round(p['scenes'][2]['end']*24) if proof else p['frames'];parts=[];cursor=0;cached={}
    directory=folder/'native-parts';directory.mkdir(exist_ok=True)
    require_disk(directory,2*1024**3)
    require_disk(media_directory(folder),2*1024**3)
    for receipt in sorted(directory.glob('part-*.json')):
        r=read(receipt)
        if r['plan_sha256']!=sha256(folder/'AV_PLAN.json') or r.get('native_identity_sha256')!=sha256(folder/'native-identity.json') or r['start']<cursor or not 0<=r['start']<r['end']<=p['frames'] or sha256(r['path'])!=r['sha256']:raise ValueError('Completed render part changed')
        cursor=r['end'];cached[r['start']]=r
    if cursor>total and proof:raise ValueError('Full render already exists; retain the previous proof')
    cursor=0
    while cursor<total:
        if cursor in cached:
            r=cached[cursor];parts.append(r);cursor=r['end'];continue
        if available_memory()<2*2**30:raise RuntimeError('Insufficient reserve for the next native batch')
        next_cached=min((start for start in cached if start>cursor),default=total)
        end=min(total,cursor+batch_size,next_cached);dest=directory/f'part-{len(parts):04}.mp4'
        if dest.exists():raise FileExistsError('Inspect an unreceipted native part; do not repeat it')
        code="var c=app.project.itemByID(CID);if(app.project.renderQueue.numItems||Math.round(c.duration*24)!==FRAMES)throw Error('Unexpected render queue/target');var q=app.project.renderQueue.items.add(c),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('H.264')>=0&&o.templates[i].indexOf('15 Mbps')>=0){preset=o.templates[i];break;}if(!preset)throw Error('Native H264 preset unavailable');o.applyTemplate(preset);o.file=new File(DEST);app.beginSuppressDialogs();try{q.timeSpanDuration=(END-START)/24;q.timeSpanStart=START/24;q.skipFrames=0;app.setMultiFrameRenderingConfig(false,25);app.project.renderQueue.render();}finally{app.endSuppressDialogs(false);}var result={done:q.status===RQItemStatus.DONE,status:q.status,start:START,end:END,preset:preset};if(result.done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return result;"
        for key,v in {'CID':str(n['comp_id']),'FRAMES':str(p['frames']),'DEST':json.dumps(dest.as_posix()),'START':str(cursor),'END':str(end)}.items():code=code.replace(key,v)
        with monitor_existing_render(h.pid,h.hwnd,minimum_free_gib=1) as memory:r=h.mutation_js(code,'Render current main film frames '+str(cursor)+' to '+str(end))
        r.update(path=str(dest),plan_sha256=sha256(folder/'AV_PLAN.json'),native_identity_sha256=sha256(folder/'native-identity.json'),memory=memory)
        if not r['done']:
            write(directory/f'stopped-{cursor}.json',r);raise RuntimeError('Native render stopped; inspect this attempt before resuming')
        stream=next(s for s in probe(dest)['streams'] if s['codec_type']=='video')
        if int(stream['nb_read_frames'])!=end-cursor:raise ValueError('Incomplete native frame range')
        r['sha256']=sha256(dest);write(directory/f'part-{len(parts):04}.json',r);parts.append(r);cursor=end
        print(json.dumps({'native_frames':cursor,'target_frames':total,'minimum_free_bytes':memory['minimum_free_bytes']}),flush=True)
    label='PROOF' if proof else 'MAIN_FILM';target=media_directory(folder)/(label+'_PICTURE_1080.mp4');listing=folder/(label+'_parts.txt')
    listing.write_text(''.join("file '"+Path(r['path']).as_posix().replace("'","'\\''")+"'\n" for r in parts),'utf-8')
    if not target.exists():subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-c','copy','-movflags','+faststart',str(target)],check=True)
    r={'output':str(target),'sha256':sha256(target),'frames':total,'duration':total/24,'parts':parts,'plan_sha256':sha256(folder/'AV_PLAN.json'),'media_role':'EDITORIAL_PROXY','formal_4k_rendered':False}
    write(folder/('PROOF_PICTURE_RECEIPT.json' if proof else 'PICTURE_RECEIPT.json'),r)
    if proof:
        # The proof is a bounded view of this same film and its complete takes.
        # It is an internal narration preview; full delivery still requires PR.
        segments=[s for s in p['segments'] if s['voice_start']<total/24]
        if any(s['voice_end']>total/24 for s in segments):raise ValueError('Proof boundary would cut a complete take')
        dest=media_directory(folder)/'PROOF_AV_INTERNAL.mp4'
        if not dest.exists():
            args=['ffmpeg','-v','error','-n','-i',str(target)]
            for s in segments:args+=['-i',s['voice']['path']]
            filters=[f'[{i+1}:a]adelay={round(s["voice_start"]*48000)}S:all=1[a{i}]' for i,s in enumerate(segments)]
            filters.append(''.join(f'[a{i}]' for i in range(len(segments)))+f'amix=inputs={len(segments)}:normalize=0,apad,atrim=duration={total/24}[voice]')
            subprocess.run(args+['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[voice]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(dest)],check=True)
        if packet_binding(target,'v:0')!=packet_binding(dest,'v:0'):raise ValueError('Proof replaced the actual native picture')
        write(folder/'PROOF_AV_RECEIPT.json',{'media':str(dest),'sha256':sha256(dest),'plan_sha256':sha256(folder/'AV_PLAN.json'),'seconds':total/24,'complete_takes':[s['id'] for s in segments],'scope':'same-film internal narration preview; no Premiere mix or human approval'})
        return {'picture':str(target),'voice_preview':str(dest),'duration':total/24}
    return {'picture':str(target),'duration':total/24}


def flatten(rows):
    if isinstance(rows,dict):rows=rows.get('items',rows.get('children',[]))
    result=[]
    for r in rows:
        result.append(r)
        if r.get('children'):result+=flatten(r['children'])
    return result


def validate_edit(p,timeline,picture):
    """Check the real native edit before export, including complete audio takes."""
    if timeline.get('pagination',{}).get('truncated'):raise ValueError('Read the complete native timeline before export')
    if [timeline['frameSizeHorizontal'],timeline['frameSizeVertical']]!=[1920,1080]:raise ValueError('Native edit canvas changed')
    videos=[c for t in timeline['videoTracks'] for c in t['clips']]
    if len(videos)!=1 or videos[0]['name']!=Path(picture).name or abs(videos[0]['start'])>1e-5 or abs(videos[0]['duration']-p['duration'])>1e-5 or abs(videos[0].get('inPoint',0))>1e-5:
        raise ValueError('Native picture was cut, shifted or replaced')
    audio=[c for t in timeline['audioTracks'] for c in t['clips']]
    if len(audio)!=len(p['segments'])+len(p.get('music',[])):raise ValueError('Native edit must contain every complete take and authored music clip exactly once')
    for s in p['segments']:
        matches=[c for c in audio if c['name']==Path(s['voice']['padded_path']).name]
        with wave.open(s['voice']['padded_path']) as w:duration=w.getnframes()/w.getframerate()
        if len(matches)!=1 or abs(matches[0]['start']-s['voice_start'])>1/48000 or abs(matches[0]['duration']-duration)>1/48000:
            raise ValueError('Native complete take placement changed: '+s['id'])
    for music in p.get('music',[]):
        tracks=timeline.get('audioTracks',[]);idx=music['audio_track_index']
        rows=tracks[idx]['clips'] if len(tracks)>idx else []
        matches=[x for x in rows if x['name']==Path(music['clip_path']).name]
        if len(matches)!=1 or abs(matches[0]['start']-music['timeline_start'])>1/48000 or abs(matches[0]['duration']-music['duration'])>1/48000:
            raise ValueError('Native music placement changed')


def premiere(folder):
    a,p,n=current_native(folder);picture=read(folder/'PICTURE_RECEIPT.json')
    require_disk(media_directory(folder),2*1024**3)
    if sha256(picture['output'])!=picture['sha256'] or picture['frames']!=p['frames']:raise ValueError('Full current native picture required')
    h=Host(folder,'premiere')
    if h.project.exists():raise FileExistsError('Inspect the existing native edit instead of repeating assembly')
    before=h.identity();oldsha=sha256(before['project_path'])
    write(folder/'PR_SESSION_BEFORE.json',{'identity':before,'sha256':oldsha})
    h.pr('save_project_as',{'path':str(h.project)},after={**before,'project_path':str(h.project)})
    if sha256(before['project_path'])!=oldsha:raise ValueError('Original Premiere project changed')
    paths=[picture['output']]+[s['voice']['padded_path'] for s in p['segments']]+[m['clip_path'] for m in p.get('music',[])]
    h.pr('import_media',{'file_paths':paths,'suppress_ui':True});items=flatten(h.c.call('list_project_items'))
    def item(path):
        matches=[r for r in items if r.get('name')==Path(path).name]
        if len(matches)!=1:raise ValueError('Ambiguous native media item: '+Path(path).name)
        return matches[0].get('nodeId',matches[0].get('id'))
    seq=h.pr('create_sequence_from_clips',{'name':'MAIN_FILM_EDITORIAL_PROXY','item_ids':[item(picture['output'])]},after=lambda r:{'process_id':h.pid,'project_path':str(h.project),'target_id':'sequence:'+r['id']})
    write(folder/'PR_SEQUENCE.json',seq)
    for s in p['segments']:
        h.pr('overwrite_clip',{'item_id':item(s['voice']['padded_path']),'start_seconds':s['voice_start'],'track_index':0,'audio_track_index':0})
        print('Placed complete '+s['id'],flush=True)
    for music in p.get('music',[]):
        from premiere_production.music import apply_music
        h.pr('overwrite_clip',{'item_id':item(music['clip_path']),'start_seconds':music['timeline_start'],'track_index':0,'audio_track_index':music['audio_track_index']})
        state=h.c.call('get_active_sequence',{'clip_limit':200})
        clip=next(x for x in state['audioTracks'][music['audio_track_index']]['clips'] if x['name']==Path(music['clip_path']).name)
        props=h.c.call('get_clip_properties',{'node_id':clip['nodeId']})
        effect=next(e for e in props['effects'] if e.get('matchName','').startswith('Internal Volume'))
        parameters=h.c.call('get_effect_properties',{'node_id':clip['nodeId'],'effect_name':effect['matchName']})
        level=next(x['displayName'] for x in parameters['properties'] if x['displayName'] in ('级别','Level','Nivel'))
        class OwnedMusic:
            def execute(self,name,args,sequence_id=None):return h.pr(name,args)
        result=apply_music(OwnedMusic(),seq['id'],clip['nodeId'],effect['matchName'],level,music['gain_keys'])
        write(folder/'MUSIC_NATIVE_AUTOMATION.json',result)
    h.pr('save_project');timeline=h.c.call('get_active_sequence',{'clip_limit':200})
    write(folder/'PR_TIMELINE.json',timeline);write(folder/'PR_SETTINGS.json',h.c.call('get_sequence_settings'))
    validate_edit(p,timeline,picture['output'])
    dest=media_directory(folder)/'PR_NATIVE_EXPORT.mp4';preset=Path(a['host']['export_preset'])
    if not preset.exists():raise FileNotFoundError('Installed Premiere export preset unavailable')
    r=h.pr('export_sequence',{'output_path':str(dest),'preset_path':str(preset),'range':'entire','overwrite':False,'timeout_minutes':20},timeout=1260)
    write(folder/'PR_EXPORT_RECEIPT.json',{'result':r,'output':str(dest),'preset_sha256':sha256(preset)})
    return {'project':str(h.project),'native_export':str(dest)}


def measured_audio_delay(p,pcm):
    """Accept only zero or one measured AAC frame of uniform export delay."""
    import numpy as np
    rows=[]
    for s in p['segments']:
        with wave.open(s['voice']['path']) as w:x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)
        start=round(s['voice_start']*48000);matches=[]
        for lag in (0,1024):
            y=pcm[start+lag:start+lag+len(x)]
            corr=float(np.corrcoef(x,y)[0,1]) if len(y)==len(x) else -1
            matches.append((corr,lag))
        corr,lag=max(matches)
        if not np.isfinite(corr) or corr<.99:raise ValueError('Export audio is not an intact take at a supported offset: '+s['id'])
        rows.append({'id':s['id'],'delay_samples':lag,'correlation':corr,'complete_samples':len(x)})
    offsets={r['delay_samples'] for r in rows}
    if len(offsets)!=1:raise ValueError('Nonuniform native audio timing must be repaired in the edit')
    delay=offsets.pop()
    if any(round(s['voice_start']*48000)<delay for s in p['segments']):raise ValueError('Delay correction could trim a spoken take')
    return delay,rows


def audio_packet_rows(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_data_hash','sha256','-show_entries','packet=pts,dts,duration,data_hash','-of','json',str(path)]))['packets']


def package(folder):
    a,p,n=current_native(folder);pic=read(folder/'PICTURE_RECEIPT.json');pr=media_directory(folder)/'PR_NATIVE_EXPORT.mp4'
    if sha256(pic['output'])!=pic['sha256'] or not pr.exists():raise ValueError('Current native picture and real Premiere export required')
    import numpy as np
    native_audio=next(s for s in probe(pr)['streams'] if s['codec_type']=='audio')
    if native_audio['codec_name']!='aac' or int(native_audio['sample_rate'])!=48000 or native_audio['time_base']!='1/48000':raise ValueError('Unsupported native audio export format')
    native_pcm=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(pr),'-map','0:a:0','-ac','1','-ar','48000','-f','s16le','-']),dtype='<i2').astype(np.float64)
    delay,delay_rows=measured_audio_delay(p,native_pcm)
    write(folder/'NATIVE_AUDIO_DELAY.json',{'native_export_sha256':sha256(pr),'delay_samples':delay,'sample_rate':48000,'takes':delay_rows,'operation':'packet timestamp correction only; complete voices retained'})
    dest=media_directory(folder)/'MAIN_FILM_EDITORIAL_PROXY.mp4'
    if not dest.exists():subprocess.run(['ffmpeg','-v','error','-n','-i',pic['output'],'-itsoffset',str(-delay/48000),'-i',str(pr),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(dest)],check=True)
    streams=probe(dest);video=next(s for s in streams['streams'] if s['codec_type']=='video');audio=next(s for s in streams['streams'] if s['codec_type']=='audio')
    if [video['width'],video['height'],video['r_frame_rate'],int(video['nb_read_frames'])]!=[1920,1080,'24/1',p['frames']]:raise ValueError('Encoded film frame coverage changed')
    packets={'video':packet_binding(pic['output'],'v:0'),'audio':packet_binding(pr,'a:0')}
    if packets['video']!=packet_binding(dest,'v:0'):raise ValueError('Native picture packets or timestamps changed during handoff')
    before_packets=audio_packet_rows(pr);after_packets=audio_packet_rows(dest)
    if len(before_packets)!=len(after_packets) or any(a['data_hash']!=b['data_hash'] or a['duration']!=b['duration'] or a['pts']-delay!=b['pts'] or a['dts']-delay!=b['dts'] for a,b in zip(before_packets,after_packets)):
        raise ValueError('Audio payload changed beyond the measured delay correction')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(dest),'-f','null','-'],check=True)
    pcm=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(dest),'-map','0:a:0','-ac','1','-ar','48000','-f','s16le','-']),dtype='<i2').astype(np.float64)
    rows=[]
    for s in p['segments']:
        with wave.open(s['voice']['path']) as w:x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)
        start=round(s['voice_start']*48000);y=pcm[start:start+len(x)]
        if len(y)!=len(x):raise ValueError('Native export truncated a complete take')
        corr=float(np.corrcoef(x,y)[0,1]);rows.append({'id':s['id'],'correlation_at_actual_start':corr,'complete_samples':len(x)})
        if corr<.99:raise ValueError('Native audio placement differs from actual clock: '+s['id'])
    for path,digest in read(folder/'BASELINE_PROTECTION.json')['protected'].items():
        if sha256(path)!=digest:raise ValueError('Protected prior production changed: '+path)
    qa={'media':str(dest),'sha256':sha256(dest),'actual_seconds':p['frames']/24,'frames':p['frames'],'video':video,'audio':audio,'full_decode':'PASS','complete_takes':rows,'same_revision':a['revision'],'native_project':str(folder/'MAIN_FILM.aep'),'premiere_project':str(folder/'MAIN_FILM.prproj'),'media_role':'EDITORIAL_PROXY','formal_4k_rendered':False,'independent_new_copy_review':'PENDING','human_creative_review':'PENDING','human_listening_review':'PENDING','student_count':0,'public_render_ready':False}
    qa['native_packet_identity']=packets
    qa['audio_timestamp_correction_samples']=-delay
    qa['video_payload_and_timestamps_unchanged']=True
    qa['audio_payload_unchanged']=True
    qa['native_project']=str((media_directory(folder)/'MAIN_FILM.aep').resolve())
    qa['premiere_project']=str((media_directory(folder)/'MAIN_FILM.prproj').resolve())
    qa['native_project_sha256']=sha256(qa['native_project'])
    qa['premiere_project_sha256']=sha256(qa['premiere_project'])
    qa['plan_sha256']=sha256(folder/'AV_PLAN.json')
    qa['voice_delivery_sha256']=p['voice_delivery_sha256']
    qa['copy_review']=p['copy_review']
    qa['complete_copy_sha256']=p['complete_copy_sha256']
    qa['music']=[{k:m[k] for k in ('title','clip_sha','duration','timeline_start','status','public_use_allowed')} for m in p.get('music',[])]
    write(folder/'DELIVERY_QA.json',qa);return {k:qa[k] for k in ('media','actual_seconds','frames','full_decode','media_role')}


def restore(folder):
    a,p,n=current_native(folder);results={}
    h=Host(folder,'after_effects');old=read(folder/'SESSION_BEFORE.json');target=old['identity']
    if Path(h.identity()['project_path']).resolve()==h.project.resolve():
        if target['target_id']=='none':
            focus='app.project.showWindow(true);'
        elif target['target_id'].startswith('comp:'):
            cid=int(target['target_id'].split(':')[1])
            focus='var c=app.project.itemByID('+str(cid)+');c.selected=true;c.openInViewer();'
        else:raise ValueError('Unsupported prior AE target: '+target['target_id'])
        opening='app.open(new File('+json.dumps(target['project_path'].replace('\\','/'))+'));' if target['project_path'] else 'app.newProject();'
        code='app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);'+opening+'for(var i=1;i<=app.project.numItems;i++)app.project.item(i).selected=false;'+focus+'return {restored:true};'
        results['after_effects']=h.mutation_js(code,'Restore saved prior AE project',{k:target[k] for k in ('process_id','project_path','target_id')})
    if target['project_path'] and sha256(target['project_path'])!=old['sha256']:raise ValueError('Prior AE project changed')
    if (folder/'PR_SESSION_BEFORE.json').exists():
        h=Host(folder,'premiere');old=read(folder/'PR_SESSION_BEFORE.json');target=old['identity']
        # Saving the new edit is intentional; restoration is a distinct native action.
        if Path(h.identity()['project_path']).resolve()==h.project.resolve():
            h.pr('save_project');results['premiere']=h.pr('open_project',{'path':target['project_path']},after={k:target[k] for k in ('process_id','project_path','target_id')})
        if sha256(target['project_path'])!=old['sha256']:raise ValueError('Prior Premiere project changed')
    # Premiere may rewrite project metadata on Save without changing the edit.
    # Keep the package-time QA snapshot and bind the final saved projects here.
    saved={}
    for name,filename in (('after_effects','MAIN_FILM.aep'),('premiere','MAIN_FILM.prproj')):
        path=media_directory(folder)/filename
        if path.exists():saved[name]={'path':str(path.resolve()),'sha256':sha256(path)}
    write(folder/'RESTORED_HOSTS.json',{'results':results,'shared_ownership_directory':a['host']['ownership_directory'],
                                     'saved_current_projects':saved});return results


def execute(operation,folder,**kwargs):
    if operation=='render':return render(folder,kwargs.get('proof',False),kwargs.get('batch_size',96))
    operations={'build':build,'audit':audit,'preview':preview,'premiere':premiere,'package':package,'restore':restore}
    if operation not in operations:raise ValueError('Unsupported current production operation: '+operation)
    return operations[operation](folder)
