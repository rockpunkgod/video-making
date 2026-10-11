"""Six bounded native Premiere sequences from byte-bound AE pictures and takes.

All native writes, including Save As, activation and export, pass through the
same HostOwnership boundary. Timeout recovery is deliberately not automatic.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import wave

from produce import current, local, read, write, sha, file_sha, process_identity, ROOT
from ae_production.host_ownership import HostOwnership
from premiere_production.mcp import PremiereMcpClient
from premiere_production.cinema import resolve_media, audit_timeline, audit_encoded


def inputs(folder, pictures=False):
    production, _ = current(folder)
    plan = read(folder/'AV_PLAN.json'); identity = read(folder/'NATIVE_IDENTITY.json')
    if (plan['production_sha'] != production['production_sha']
            or plan['av_plan_sha'] != sha({k:v for k,v in plan.items() if k!='av_plan_sha'})
            or set(plan['variants']) != set(identity['compositions'])
            or plan['public_render_ready'] is not False):
        raise ValueError('Bound six-variant AV plan changed')
    for name, variant in plan['variants'].items():
        composition = identity['compositions'][name]
        if (variant['frames'] != composition['frames'] or variant['source_frames'] != composition['source_frames']
                or abs(variant['duration']-variant['frames']/24)>1e-8
                or variant['voice_stretched'] or variant['voice_truncated']
                or file_sha(variant['music']['path']) != variant['music']['sha256']
                or file_sha(variant['srt_path']) != variant['srt_sha']):
            raise ValueError('Variant media/timing changed')
        expected = []
        for source in production['voices']:
            start = source['start'] if name.startswith('NEW_') else source['original_start']
            end = source['end'] if name.startswith('NEW_') else source['original_end']
            a,b = [f/24 for f in variant['source_frames']]
            if end<=a or start>=b or name.endswith('_VISUAL'): continue
            if not a<=start<end<=b: raise ValueError('Excerpt cuts a bound voice take')
            expected.append((source,start-a,end-a))
        if [v['id'] for v in variant['voices']] != [v['id'] for v,_,_ in expected]:
            raise ValueError('Variant complete voice coverage changed')
        for observed,(source,start,end) in zip(variant['voices'],expected):
            if (any(observed[k] != source[k] for k in ('id','path','sha256','text','duration','transcript_sha'))
                    or abs(observed['start']-start)>1e-8 or abs(observed['end']-end)>1e-8
                    or file_sha(observed['path']) != source['sha256']):
                raise ValueError('Bound complete voice changed')
            with wave.open(observed['path'],'rb') as audio:
                if audio.getframerate()!=48000 or audio.getnframes()!=round(source['duration']*48000):
                    raise ValueError('Complete voice sample extent changed')
    picture = read(folder/'PICTURE_INDEX.json') if pictures else None
    if picture:
        if picture['production_sha'] != production['production_sha'] or not set(picture['pictures']) <= set(plan['variants']):
            raise ValueError('Current bounded native pictures required')
        for name, item in picture['pictures'].items():
            composition = identity['compositions'][name]
            if (any(item[k]!=composition[k] for k in ('comp_id','frames','source_frames'))
                    or item['full_decode']!='PASS' or file_sha(item['path'])!=item['sha256']):
                raise ValueError('Current encoded native picture binding changed')
    workspace = read(folder/'PR_WORKSPACE.json') if (folder/'PR_WORKSPACE.json').exists() else None
    if workspace and (workspace['production_sha']!=production['production_sha'] or workspace['av_plan_sha']!=plan['av_plan_sha']):
        raise ValueError('Premiere workspace revision changed')
    return production, plan, picture, workspace


class OwnedPR:
    def __init__(self,folder,completed_reconciliation=None,*,saving_new_project_as=None):
        self.folder=folder; self.production,self.plan,_,workspace=inputs(folder)
        self.client=PremiereMcpClient('http://127.0.0.1:11489/mcp',
            (ROOT/'local-data/v9.1/mcp-token.txt').read_text().strip())
        self.client.initialize()
        self.pid,_=process_identity("'Adobe Premiere Pro'")
        initial=self.reader()
        if saving_new_project_as is None:
            if (workspace is None or not initial['project_path']
                    or Path(initial['project_path']).resolve()!=Path(workspace['project']).resolve()):
                raise ValueError('The intended PR workspace project must be active before ownership')
        else:
            intended=folder/'B06_JUDGEMENT_AB_4K.prproj'
            if (workspace is not None or completed_reconciliation is not None or intended.exists()
                    or Path(saving_new_project_as).resolve()!=intended.resolve()):
                raise ValueError('Only the explicit new bounded PR Save As transition is supported')
        self.lease=HostOwnership('premiere','/root/astra_b06_execution',folder.name,
            {k:initial[k] for k in ('process_id','project_path','target_id')})
        if completed_reconciliation is None:
            self.lease.acquire()
        else:
            self.lease=HostOwnership.reconcile_completed('premiere','/root/astra_b06_execution',folder.name,
                completed_reconciliation['token'],completed_reconciliation['target'],self.reader,
                completed_reconciliation['evidence'],expected_state='OWNED')
        self.log=read(folder/'PR_OWNERSHIP_RECEIPTS.json') if (folder/'PR_OWNERSHIP_RECEIPTS.json').exists() else []

    def reader(self):
        pid,_=process_identity("'Adobe Premiere Pro'")
        project=self.client.call('get_project_info')
        active=project.get('activeSequence')
        return {'process_id':pid,'project_path':str(Path(project['path']).resolve()),
            'target_id':'sequence:'+str(active['id']) if active else 'none',
            'sequence_name':active['name'] if active else None,
            'num_sequences':project['numSequences'],'num_items':project['numItems']}

    def mutate(self,tool,args=None,project=None,new_sequence=False,sequence_id=None,timeout=180):
        inputs(self.folder); before=self.reader(); args=args or {}
        write(self.folder/'PR_PENDING_MUTATION.json',{'tool':tool,'inputs':args,'before':before})
        destination=None
        if project or new_sequence or sequence_id:
            def destination(result):
                return {'process_id':self.pid,
                    'project_path':str(Path(project or before['project_path']).resolve()),
                    'target_id':'sequence:'+str(result['id'] if new_sequence else sequence_id)
                        if new_sequence or sequence_id else before['target_id']}
        result=self.lease.mutate(self.reader,lambda:self.client.call(tool,args,timeout=timeout),target_after=destination)
        self.log.append({'tool':tool,'inputs':args,'result':result,'before':before,
            'after':self.reader(),'lease_token':self.lease.record['token']})
        write(self.folder/'PR_OWNERSHIP_RECEIPTS.json',self.log)
        return result

    def release(self): self.lease.release(self.reader)


def setup(folder):
    production,plan,_,workspace=inputs(folder)
    target=folder/'B06_JUDGEMENT_AB_4K.prproj'
    if target.exists() or workspace: raise FileExistsError('Inspect the existing Premiere workspace; do not replay setup')
    owner=OwnedPR(folder,saving_new_project_as=target); prior=owner.reader()
    if prior['num_sequences'] or prior['num_items']:
        owner.release(); raise ValueError('Expected the previously inspected empty native project')
    old_path=Path(prior['project_path']); old_sha=file_sha(old_path)
    owner.mutate('save_project_as',{'path':str(target)},project=target)
    paths={}
    for variant in plan['variants'].values():
        for media in [variant['music'],*variant['voices']]: paths[media['path']]=media['path']
    owner.mutate('import_media',{'file_paths':list(paths),'suppress_ui':True})
    items=owner.client.call('list_project_items');items=items['items'] if isinstance(items,dict) else items
    ids=resolve_media(items,paths)
    owner.mutate('save_project')
    if file_sha(old_path)!=old_sha: raise ValueError('Original Premiere project changed')
    workspace={'production_sha':production['production_sha'],'av_plan_sha':plan['av_plan_sha'],
        'project':str(target),'prior_project':str(old_path),'prior_project_sha':old_sha,
        'audio_item_ids':ids,'sequences':{},'public_render_ready':False}
    write(folder/'PR_WORKSPACE.json',workspace);owner.release()
    return {'project':str(target),'imported_complete_audio_sources':len(ids),'sequences':0}


def native_audit(owner,workspace,name,picture,variant):
    state=owner.client.call('get_active_sequence',{'clip_limit':200})
    settings=owner.client.call('get_sequence_settings')
    identity=workspace['sequences'][name]
    if state['id']!=identity['id'] or state['name']!=name:
        raise ValueError('Wrong native sequence for this variant')
    audit_timeline(state,settings,variant['voices'],variant['duration'])
    expected={'videoTracks':{0:[(picture['path'],0,variant['duration'])]},
        'audioTracks':{0:[(v['path'],v['start'],v['end']) for v in variant['voices']],
                       1:[(variant['music']['path'],0,variant['duration'])]}}
    properties=[]; levels=[];sources=[]
    for kind in ('videoTracks','audioTracks'):
        for index,track in enumerate(state[kind]):
            clips=track['clips'];wanted=expected[kind].get(index,[])
            if len(clips)!=len(wanted):raise ValueError('Missing or extra native timeline clip')
            for clip,(path,start,end) in zip(clips,wanted):
                if clip['name']!=Path(path).name or abs(clip['start']-start)>1/48000 or abs(clip['end']-end)>1/48000:
                    raise ValueError('Actual complete clip placement differs')
                prop=owner.client.call('get_clip_properties',{'node_id':clip['nodeId']})
                if (abs(prop['inPoint'])>1/48000 or abs(prop['outPoint']-(end-start))>1/48000
                        or abs(prop['duration']-(end-start))>1/48000 or prop['isSpeedReversed']):
                    raise ValueError('Native source range or playback rate changed')
                properties.append(prop)
                full=owner.client.call('get_full_clip_info',{'node_id':clip['nodeId']})
                source_id=identity['picture_item_id'] if kind=='videoTracks' else workspace['audio_item_ids'][path]
                if (Path(full['source']['mediaPath']).resolve()!=Path(path).resolve()
                        or str(full['source']['nodeId'])!=str(source_id) or full['speed']!=1
                        or full['reversed'] or not full['enabled'] or full['source']['offline']):
                    raise ValueError('Actual native source identity, full-speed playback or availability changed')
                sources.append(full)
                if kind=='audioTracks':
                    effect=next(c for c in full['components'] if c['matchName'].startswith('Internal Volume'))
                    scalar=[p for p in effect['properties'] if isinstance(p.get('value'),(int,float)) and not isinstance(p.get('value'),bool)]
                    level=next((p for p in scalar if abs(p['value']-10**(-15/20))<1e-6),None)
                    if not level or level['isTimeVarying']:raise ValueError('Complete source must play at flat native 0 dB')
                    keys=owner.client.call('get_keyframes',{'node_id':clip['nodeId'],'effect_name':effect['matchName'],'property_name':level['displayName']})
                    if keys.get('isTimeVarying') or keys.get('keyframes'):raise ValueError('Unexpected native source gain automation')
                    levels.append({'clip':clip['nodeId'],'effect':effect,'keyframes':keys})
    receipt={'status':'PASS_NATIVE_TIMELINE','production_sha':owner.production['production_sha'],
        'av_plan_sha':owner.plan['av_plan_sha'],'sequence':state,'settings':settings,'source_items':sources,
        'clip_properties':properties,'flat_audio_levels':levels,'picture_sha':picture['sha256'],
        'public_render_ready':False,'human_visual_review':'PENDING','human_listening_review':'PENDING'}
    write(owner.folder/'premiere-audits'/(name+'.json'),receipt)
    return receipt


def realize_audio_positions(owner,variant):
    """Correct a measured import snap once; retain exact source range and rate."""
    state=owner.client.call('get_active_sequence',{'clip_limit':200})
    for voice in variant['voices']:
        matches=[c for c in state['audioTracks'][0]['clips'] if c['name']==voice['native_name']]
        if len(matches)!=1:raise ValueError('Unique complete imported take required before placement correction')
        clip=matches[0]
        if abs(clip['start']-voice['start'])<=1/48000:continue
        props=owner.client.call('get_full_clip_info',{'node_id':clip['nodeId']})
        if (abs(clip['start']-voice['start'])>1/48+1e-8 or abs(props['inPointSeconds'])>1/48000
                or abs(props['outPointSeconds']-voice['duration'])>1/48000
                or abs(props['durationSeconds']-voice['duration'])>1/48000 or props['speed']!=1):
            raise ValueError('Measured placement is not a bounded frame snap of the complete take')
        owner.mutate('move_clip',{'node_id':clip['nodeId'],'new_start_seconds':voice['start']})
        after=owner.client.call('get_full_clip_info',{'node_id':clip['nodeId']})
        if (abs(after['startSeconds']-voice['start'])>1/48000 or abs(after['endSeconds']-voice['end'])>1/48000
                or after['inPointSeconds']!=props['inPointSeconds'] or after['outPointSeconds']!=props['outPointSeconds']
                or after['speed']!=1):
            write(owner.folder/'PR_EXACT_PLACEMENT_HOLD.json',{'before':props,'after':after,'expected':voice})
            raise ValueError('Exact authored voice placement unavailable; inspect instead of repeating the move')


def finish(folder,names,token):
    production,plan,pictures,workspace=inputs(folder,True)
    if not token or not names or len(names)!=1 or workspace['sequences'][names[0]]['state']!='PICTURE_CREATED':
        raise ValueError('Explicit single completed-edit checkpoint required')
    previous=read(ROOT/'local-data/adobe-host-ownership/premiere.json')
    count=subprocess.check_output(['powershell','-NoProfile','-Command',
        '@(Get-Process -ErrorAction Stop | Where-Object Id -eq '+str(previous['controller_pid'])+').Count'],
        creationflags=subprocess.CREATE_NO_WINDOW).strip()
    if int(count)!=0:raise ValueError('Original Premiere controller is still alive')
    name=names[0]
    if previous['target']['target_id']!='sequence:'+workspace['sequences'][name]['id']:
        raise ValueError('Checkpoint is not the requested existing sequence')
    evidence={str(folder/n):file_sha(folder/n) for n in ('PR_OWNERSHIP_RECEIPTS.json','PR_WORKSPACE.json',
        'PR_TIMING_INSPECTION_R1.json','PR_COMPLETE_VOICE_INSPECTION_R1.json')}
    owner=OwnedPR(folder,{'token':token,'target':previous['target'],'evidence':evidence})
    write(folder/'PR_PLACEMENT_CHECKPOINT_RECONCILIATION.json',owner.lease.record)
    realize_audio_positions(owner,plan['variants'][name])
    owner.mutate('save_project')
    native_audit(owner,workspace,name,pictures['pictures'][name],plan['variants'][name])
    workspace['sequences'][name]['state']='PASS_NATIVE_TIMELINE';write(folder/'PR_WORKSPACE.json',workspace)
    owner.release()
    return {'sequence':name,'status':'PASS_NATIVE_TIMELINE','source_reimported':False}


def assemble(folder, names=None):
    production,plan,pictures,workspace=inputs(folder,True)
    names=list(plan['variants']) if names is None else names
    if (workspace is None or not names or len(names)!=len(set(names))
            or not set(names)<=pictures['pictures'].keys() or set(names)&workspace['sequences'].keys()):
        raise ValueError('Only explicit new variants with complete native pictures can be assembled')
    owner=OwnedPR(folder)
    if owner.reader()['project_path']!=workspace['project']:raise ValueError('Dedicated Premiere project must already be active')
    owner.mutate('import_media',{'file_paths':[pictures['pictures'][n]['path'] for n in names],'suppress_ui':True})
    items=owner.client.call('list_project_items');items=items['items'] if isinstance(items,dict) else items
    ids=resolve_media(items,{k:pictures['pictures'][k]['path'] for k in names})
    for name in names:
        variant=plan['variants'][name]
        created=owner.mutate('create_sequence_from_clips',{'name':name,'item_ids':[ids[name]]},new_sequence=True)
        workspace['sequences'][name]={'id':created['id'],'picture_item_id':ids[name],
            'picture_sha':pictures['pictures'][name]['sha256'],'state':'PICTURE_CREATED'}
        write(folder/'PR_WORKSPACE.json',workspace)
        for media,start,track in [(variant['music'],0,1)]+[(v,v['start'],0) for v in variant['voices']]:
            owner.mutate('overwrite_clip',{'item_id':workspace['audio_item_ids'][media['path']],
                'start_seconds':start,'track_index':0,'audio_track_index':track})
        realize_audio_positions(owner,variant)
        owner.mutate('save_project')
        native_audit(owner,workspace,name,pictures['pictures'][name],variant)
        workspace['sequences'][name]['state']='PASS_NATIVE_TIMELINE'
        write(folder/'PR_WORKSPACE.json',workspace)
        print(json.dumps({'sequence':name,'status':'PASS_NATIVE_TIMELINE'}),flush=True)
    owner.release()
    return {'native_sequences':len(workspace['sequences']),'public_render_ready':False}


def export(folder, names=None):
    production,plan,pictures,workspace=inputs(folder,True)
    names=list(plan['variants']) if names is None else names
    if (not workspace or not names or len(names)!=len(set(names))
            or not set(names)<=workspace['sequences'].keys()
            or any(workspace['sequences'][n]['state']!='PASS_NATIVE_TIMELINE' for n in names)):
        raise ValueError('Explicit verified native sequences required')
    preset=read(folder/'PR_EXPORT_PRESET.json')
    if file_sha(preset['path'])!=preset['sha256']:raise ValueError('Explicit bound export preset changed')
    owner=OwnedPR(folder);destination=folder/'exports';destination.mkdir(exist_ok=True)
    previous=read(folder/'EXPORT_INDEX.json') if (folder/'EXPORT_INDEX.json').exists() else None
    if previous and previous['production_sha']!=production['production_sha']:raise ValueError('Export revision changed')
    results=previous['exports'] if previous else {}
    if set(names)&results.keys():raise FileExistsError('Do not replay completed native exports')
    for name in names:
        variant=plan['variants'][name]
        target=destination/(name+'.mp4')
        if target.exists():raise FileExistsError('Existing native export needs explicit reconciliation, never blind retry')
        owner.mutate('set_active_sequence',{'sequence_id':workspace['sequences'][name]['id']},sequence_id=workspace['sequences'][name]['id'])
        audit=native_audit(owner,workspace,name,pictures['pictures'][name],variant)
        validated=owner.client.call('validate_export_preset',{'preset_path':preset['path']})
        if not validated.get('hostValidated') or validated['outputExtension'].lstrip('.')!='mp4':
            raise ValueError('The bound preset must be host-validated as MP4 before export')
        native=owner.mutate('export_sequence',{'output_path':str(target),'preset_path':preset['path'],
            'range':'entire','overwrite':False,'timeout_minutes':15},timeout=960)
        if variant['voices']:
            encoded=audit_encoded(target,{'voices':variant['voices']},variant['duration'])
        else:
            # The visual control intentionally has no narration to correlate.
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(target)]))
            v=next(s for s in probe['streams'] if s['codec_type']=='video')
            a=next(s for s in probe['streams'] if s['codec_type']=='audio')
            if [v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']),int(a['sample_rate']),a['channels']]!=[3840,2160,'24/1',variant['frames'],48000,2]:
                raise ValueError('Native visual control encoding differs')
            subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
            encoded={'status':'PASS_ENCODED_CONFORMANCE','media':probe,'voices':'OMITTED_BY_DESIGN'}
        receipt={'production_sha':production['production_sha'],'av_plan_sha':plan['av_plan_sha'],
            'sequence_id':workspace['sequences'][name]['id'],'frames':variant['frames'],
            'source_frames':variant['source_frames'],'output':str(target),'output_sha':file_sha(target),
            'native_export':native,'native_audit_sha':sha(audit),'encoded':encoded,
            'preset':preset,'native_preset_validation':validated,
            'human_visual_review':'PENDING','human_listening_review':'PENDING','public_render_ready':False}
        write(destination/(name+'.receipt.json'),receipt);results[name]=receipt
        write(folder/'export-progress.json',{'completed':list(results),'production_sha':production['production_sha']})
        write(folder/'EXPORT_INDEX.json',{'production_sha':production['production_sha'],'exports':results,
            'G3':'STOPPED_PENDING_HUMAN_VIEWING_AND_LISTENING' if len(results)==6 else 'G2_INCOMPLETE',
            'public_render_ready':False})
        print(json.dumps({'exported':name,'frames':variant['frames']}),flush=True)
    owner.mutate('save_project');owner.release()
    return {'exports':len(results),'G3':'PENDING' if len(results)==6 else 'G2_INCOMPLETE','public_render_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('setup','assemble','export','finish'))
    parser.add_argument('folder');parser.add_argument('--variants',nargs='+');parser.add_argument('--token');args=parser.parse_args()
    folder=local(args.folder)
    result=(setup(folder) if args.operation=='setup' else finish(folder,args.variants,args.token)
        if args.operation=='finish' else globals()[args.operation](folder,args.variants))
    print(json.dumps(result,ensure_ascii=True,indent=2))
