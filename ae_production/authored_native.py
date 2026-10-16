"""Native execution of the authored AV plan through existing Adobe bridges.

Shared HostOwnership is mandatory. The machine paths and source material stay
in the private author input. Receipts permit reuse of completed render parts;
an uncertain or incomplete dispatch is never replayed automatically.
"""
import json
from pathlib import Path
import subprocess
import time
import wave

from video_contracts import ROOT, read, write
from scripts.voice_delivery import sha256
from ae_production.bridge import JunkdogeClient
from ae_production.host_ownership import HostOwnership
from ae_production.memory_guard import available_memory, monitor_existing_render
from ae_production.authored_episode import checked_author,delivery_path
from premiere_production.mcp import PremiereMcpClient
from premiere_production.lossless_handoff import packet_binding

TEMPLATE=ROOT/'ae/templates/authored-episode.jsx'


def value(r):
    if isinstance(r,dict) and r.get('contentType')=='text':r=r['content']
    elif isinstance(r,dict) and 'result' in r:r=r['result']
    return json.loads(r) if isinstance(r,str) else r


def process(name):
    rows=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        "@(Get-Process -Name '"+name+"' | Select-Object Id,MainWindowHandle) | ConvertTo-Json -Compress"],creationflags=subprocess.CREATE_NO_WINDOW))
    if isinstance(rows,dict):rows=[rows]
    if len(rows)!=1:raise RuntimeError('Expected one unambiguous Adobe host: '+name)
    return rows[0]


def plan(folder):
    a,_=checked_author(folder);p=read(folder/'AV_PLAN.json')
    if p['author_sha256']!=sha256(folder/'AV_AUTHOR.json') or p['voice_delivery_sha256']!=sha256(delivery_path(folder,a)) or p['alignment_sha256']!=sha256(folder/'VOICE_ALIGNMENT.json'):
        raise ValueError('Copy/voice/director changes have not propagated through prepare')
    for s in p['segments']:
        v=s['voice']
        if sha256(v['path'])!=v['sha256'] or sha256(v['padded_path'])!=v['padded_sha256']:
            raise ValueError('Complete audio take changed')
    return a,p


class Host:
    def __init__(self,folder,kind):
        self.folder=folder;self.a,_=plan(folder);self.kind=kind;self.h=self.a['host']
        self.native_name='AfterFX' if kind=='after_effects' else 'Adobe Premiere Pro'
        proc=process(self.native_name);self.pid=proc['Id'];self.hwnd=proc['MainWindowHandle']
        self.project=folder/('MAIN_FILM.aep' if kind=='after_effects' else 'MAIN_FILM.prproj')
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
            r=self.js('var a=app.project.activeItem;if(!(a instanceof CompItem)&&app.project.selection.length===1)a=app.project.selection[0];return {project_path:app.project.file?app.project.file.fsName:"",target_id:a instanceof CompItem?"comp:"+a.id:"none",dirty:app.project.dirty,rendering:app.project.renderQueue.rendering};')
        else:
            data=self.c.call('get_project_info');active=data.get('activeSequence');r={'project_path':data['path'],'target_id':'sequence:'+active['id'] if active else 'none'}
        r['project_path']=str(Path(r['project_path']).resolve()) if r['project_path'] else ''
        return {**r,'process_id':pid}

    def mutate(self,label,operation,after=None):
        plan(self.folder);before=self.identity();key='ae_expected_project' if self.kind=='after_effects' else 'premiere_expected_project'
        if Path(before['project_path']).resolve() not in (Path(self.h[key]).resolve(),self.project.resolve()):
            raise ValueError('Unexpected host project; do not replace another task')
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
        return self.mutate(label,lambda:self.js(code,label),after)

    def pr(self,name,args=None,after=None,timeout=180):
        return self.mutate(name,lambda:self.c.call(name,args or {},timeout=timeout),after)


def build(folder):
    a,p=plan(folder);h=Host(folder,'after_effects');before=h.identity()
    if h.project.exists() or (folder/'native-identity.json').exists():raise FileExistsError('Inspect saved native output; no implicit rebuild')
    code=TEMPLATE.read_text('utf-8').replace('PLAN_PATH',json.dumps((folder/'AV_PLAN.json').as_posix())).replace('PROJECT_PATH',json.dumps(h.project.as_posix())).replace('PLAN_SHA',json.dumps(sha256(folder/'AV_PLAN.json')))
    write(folder/'SESSION_BEFORE.json',{'identity':before,'sha256':sha256(before['project_path'])})
    r=h.mutation_js(code,'Build current authored main film',after=lambda r:{'process_id':h.pid,'project_path':str(h.project.resolve()),'target_id':'comp:'+str(r['comp_id'])})
    r.update(plan_sha256=sha256(folder/'AV_PLAN.json'),template_sha256=sha256(TEMPLATE))
    write(folder/'native-identity.json',r)
    return {k:r[k] for k in ('comp_id','master_comp_id','duration','frames','layers','media_role')}


def current_native(folder):
    a,p=plan(folder);n=read(folder/'native-identity.json')
    if n['plan_sha256']!=sha256(folder/'AV_PLAN.json') or n['template_sha256']!=sha256(TEMPLATE):
        raise ValueError('Native picture is stale after author or realization changes')
    return a,p,n


def audit(folder):
    a,p,n=current_native(folder);h=Host(folder,'after_effects')
    code="var c=app.project.itemByID(CID),rows=[];for(var i=1;i<=c.numLayers;i++){var l=c.layer(i),r={name:l.name,id:l.id,inPoint:l.inPoint,outPoint:l.outPoint,threeD:l.threeDLayer,parent:l.parent?l.parent.id:null,comment:l.comment};if(l instanceof TextLayer){r.text=l.property('Source Text').value.text;r.font=l.property('Source Text').value.font;}if(l instanceof CameraLayer||l.name.indexOf('SOURCE_LIFT_')===0||l.name.indexOf('CANDIDATE_FLIGHT_')===0){r.position=[];r.orientation=[];var pos=l.transform.position;for(var j=1;j<=pos.numKeys;j++)r.position.push([pos.keyTime(j),pos.keyValue(j)]);if(!(l instanceof CameraLayer)){var ori=l.transform.orientation;for(var j=1;j<=ori.numKeys;j++)r.orientation.push([ori.keyTime(j),ori.keyValue(j)]);}}rows.push(r);}return {project:app.project.file.fsName,width:c.width,height:c.height,duration:c.duration,fps:c.frameRate,layers:rows};".replace('CID',str(n['comp_id']))
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
    for ev in n['audit']['candidates']:
        if ev['kind']=='final':continue
        row=native['CANDIDATE_FLIGHT_'+ev['scene']]
        if row['text']!=ev['whole_option_text'] or not row['threeD']:raise ValueError('Candidate identity detached')
        if ev['kind']=='eliminate' and (row['position'][-1][1][2]!=420 or row['orientation'][-1][1]!=[0,72,0]):raise ValueError('Whole candidate withdrawal lost')
    for c in p['cues']:
        row=native['CAPTION_'+c['id']]
        if row['text'].replace('\r','\n')!='\n'.join(c['display_lines']) or abs(row['inPoint']-c['start'])>1e-4 or abs(row['outPoint']-c['end'])>1e-4:
            raise ValueError('Caption text or audio clock changed')
    if len(n['audit']['replays'])!=1 or any(e['scene']==n['audit']['replays'][0]['scene'] for e in p['candidate_events']):raise ValueError('Replay repeated a candidate decision')
    master=h.js('var c=app.project.itemByID('+str(n['master_comp_id'])+');return {width:c.width,height:c.height,fps:c.frameRate,duration:c.duration,comment:c.comment};')
    if [master['width'],master['height'],master['fps'],round(master['duration']*24)]!=[3840,2160,24,p['frames']]:raise ValueError('Unrendered master format changed')
    r['unrendered_master']=master
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


def render(folder,proof=False,batch_size=480):
    a,p,n=current_native(folder);audit(folder);h=Host(folder,'after_effects')
    if not 1<=batch_size<=480:raise ValueError('Native batches are limited to 20 seconds')
    total=round(p['scenes'][2]['end']*24) if proof else p['frames'];parts=[];cursor=0;cached={}
    directory=folder/'native-parts';directory.mkdir(exist_ok=True)
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
    label='PROOF' if proof else 'MAIN_FILM';target=folder/(label+'_PICTURE_1080.mp4');listing=folder/(label+'_parts.txt')
    listing.write_text(''.join("file '"+Path(r['path']).as_posix().replace("'","'\\''")+"'\n" for r in parts),'utf-8')
    if not target.exists():subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-c','copy','-movflags','+faststart',str(target)],check=True)
    r={'output':str(target),'sha256':sha256(target),'frames':total,'duration':total/24,'parts':parts,'plan_sha256':sha256(folder/'AV_PLAN.json'),'media_role':'EDITORIAL_PROXY','formal_4k_rendered':False}
    write(folder/('PROOF_PICTURE_RECEIPT.json' if proof else 'PICTURE_RECEIPT.json'),r);return {'picture':str(target),'duration':total/24}


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
    if len(audio)!=len(p['segments']):raise ValueError('Native edit must contain every complete take exactly once')
    for s in p['segments']:
        matches=[c for c in audio if c['name']==Path(s['voice']['padded_path']).name]
        with wave.open(s['voice']['padded_path']) as w:duration=w.getnframes()/w.getframerate()
        if len(matches)!=1 or abs(matches[0]['start']-s['voice_start'])>1/48000 or abs(matches[0]['duration']-duration)>1/48000:
            raise ValueError('Native complete take placement changed: '+s['id'])


def premiere(folder):
    a,p,n=current_native(folder);picture=read(folder/'PICTURE_RECEIPT.json')
    if sha256(picture['output'])!=picture['sha256'] or picture['frames']!=p['frames']:raise ValueError('Full current native picture required')
    h=Host(folder,'premiere')
    if h.project.exists():raise FileExistsError('Inspect the existing native edit instead of repeating assembly')
    before=h.identity();oldsha=sha256(before['project_path'])
    write(folder/'PR_SESSION_BEFORE.json',{'identity':before,'sha256':oldsha})
    h.pr('save_project_as',{'path':str(h.project)},after={**before,'project_path':str(h.project)})
    if sha256(before['project_path'])!=oldsha:raise ValueError('Original Premiere project changed')
    paths=[picture['output']]+[s['voice']['padded_path'] for s in p['segments']]
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
    h.pr('save_project');timeline=h.c.call('get_active_sequence',{'clip_limit':200})
    write(folder/'PR_TIMELINE.json',timeline);write(folder/'PR_SETTINGS.json',h.c.call('get_sequence_settings'))
    validate_edit(p,timeline,picture['output'])
    dest=folder/'PR_NATIVE_EXPORT.mp4';preset=Path(a['host']['export_preset'])
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
    a,p,n=current_native(folder);pic=read(folder/'PICTURE_RECEIPT.json');pr=folder/'PR_NATIVE_EXPORT.mp4'
    if sha256(pic['output'])!=pic['sha256'] or not pr.exists():raise ValueError('Current native picture and real Premiere export required')
    import numpy as np
    native_audio=next(s for s in probe(pr)['streams'] if s['codec_type']=='audio')
    if native_audio['codec_name']!='aac' or int(native_audio['sample_rate'])!=48000 or native_audio['time_base']!='1/48000':raise ValueError('Unsupported native audio export format')
    native_pcm=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(pr),'-map','0:a:0','-ac','1','-ar','48000','-f','s16le','-']),dtype='<i2').astype(np.float64)
    delay,delay_rows=measured_audio_delay(p,native_pcm)
    write(folder/'NATIVE_AUDIO_DELAY.json',{'native_export_sha256':sha256(pr),'delay_samples':delay,'sample_rate':48000,'takes':delay_rows,'operation':'packet timestamp correction only; complete voices retained'})
    dest=folder/'MAIN_FILM_EDITORIAL_PROXY.mp4'
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
    qa['native_project_sha256']=sha256(folder/'MAIN_FILM.aep')
    qa['premiere_project_sha256']=sha256(folder/'MAIN_FILM.prproj')
    qa['plan_sha256']=sha256(folder/'AV_PLAN.json')
    qa['voice_delivery_sha256']=p['voice_delivery_sha256']
    write(folder/'DELIVERY_QA.json',qa);return {k:qa[k] for k in ('media','actual_seconds','frames','full_decode','media_role')}


def restore(folder):
    a,p,n=current_native(folder);results={}
    h=Host(folder,'after_effects');old=read(folder/'SESSION_BEFORE.json');target=old['identity']
    if Path(h.identity()['project_path']).resolve()==h.project.resolve():
        cid=int(target['target_id'].split(':')[1]);code='app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.open(new File('+json.dumps(target['project_path'].replace('\\','/'))+'));for(var i=1;i<=app.project.numItems;i++)app.project.item(i).selected=false;var c=app.project.itemByID('+str(cid)+');c.selected=true;c.openInViewer();return {restored:true};'
        results['after_effects']=h.mutation_js(code,'Restore saved prior AE project',{k:target[k] for k in ('process_id','project_path','target_id')})
    if sha256(target['project_path'])!=old['sha256']:raise ValueError('Prior AE project changed')
    if (folder/'PR_SESSION_BEFORE.json').exists():
        h=Host(folder,'premiere');old=read(folder/'PR_SESSION_BEFORE.json');target=old['identity']
        # Saving the new edit is intentional; restoration is a distinct native action.
        if Path(h.identity()['project_path']).resolve()==h.project.resolve():
            h.pr('save_project');results['premiere']=h.pr('open_project',{'path':target['project_path']},after={k:target[k] for k in ('process_id','project_path','target_id')})
        if sha256(target['project_path'])!=old['sha256']:raise ValueError('Prior Premiere project changed')
    write(folder/'RESTORED_HOSTS.json',{'results':results,'shared_ownership_directory':a['host']['ownership_directory']});return results


def execute(operation,folder,**kwargs):
    if operation=='render':return render(folder,kwargs.get('proof',False),kwargs.get('batch_size',480))
    operations={'build':build,'audit':audit,'preview':preview,'premiere':premiere,'package':package,'restore':restore}
    if operation not in operations:raise ValueError('Unsupported current production operation: '+operation)
    return operations[operation](folder)
