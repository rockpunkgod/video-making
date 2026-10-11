"""Bounded native A/B execution, using existing frozen and Adobe ownership gates."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from video_contracts import read,write,sha
from ae_production.bridge import JunkdogeClient
from ae_production.candidate_motion import audit_candidate_events
from ae_production.experience_proof import validate_proof,file_sha
from ae_production.host_ownership import HostOwnership
from ae_production.memory_guard import available_memory,monitor_existing_render

HERE=Path(__file__).resolve().parent

def validate_spec(s,parent,bundle):
    if (s['kind']!='reality_cognitive_native_fast_pass' or s['parent_plan_sha']!=parent['plan_sha']
            or s['spec_sha']!=sha({k:v for k,v in s.items() if k!='spec_sha'})
            or s['public_render_ready'] is not False or s['human_review']!='PENDING'
            or s['method_id']!=parent['method_id'] or s['selection']!=parent['selection']):
        raise ValueError('Native experiment must bind the unchanged frozen parent and internal scope')
    if (s['frames']!=s['duration']*24 or s['frames']<=0 or s['canvas']!=[3840,2160,24]
            or s['variants']!=['A','B'] or s['answer_event'] is not None or s['replays']):
        raise ValueError('One native 4K24 Fast Pass, no replay or answer upgrade')
    if len(s['candidate_events'])!=len(parent['candidate_events']):raise ValueError('Same existing actions only')
    for old,new in zip(parent['candidate_events'],s['candidate_events']):
        for key in ('question_id','source_refs','candidate','effect'):
            if new[key]!=old[key]:raise ValueError('Frozen judgement changed')
    events=audit_candidate_events(s['candidate_events'],{bundle['asset_id']:bundle})['events']
    objects={o['id']:o for o in parent['objects']};world={}
    for column in s['columns']:
        source=objects[column['object_id']]
        if column['source_ref']!=source['source_ref']:raise ValueError('Column borrowed a source')
        for word in column['words']:
            if word['id'] in world:raise ValueError('Duplicate world identity')
            a,b=word['range'];base=source['range'][0]
            if not base<=a<b<=source['range'][1] or source['text'][a-base:b-base]!=word['text']:
                raise ValueError('Native glyph cannot change the frozen lexical content')
            world[word['id']]=word
        # Token coverage prevents silent deletion or duplication of original words.
        import re
        expected=[(m.group(),[source['range'][0]+m.start(),source['range'][0]+m.end()]) for m in re.finditer(r'\S+',source['text'])]
        if [(w['text'],w['range']) for w in column['words']]!=expected:
            raise ValueError('Incomplete original-source world')
    ids=set()
    for projection in s['projections']:
        if projection['id'] in ids or projection['origin_word_id'] not in world:
            raise ValueError('Projection must have one actual source glyph origin')
        ids.add(projection['id'])
        for key in ('path','opacity','scale'):
            rows=projection[key]
            if (not rows or rows[0][0]!=0 or rows[-1][0]!=s['duration']
                    or any(not 0<=r[0]<=s['duration'] for r in rows)
                    or any(a[0]>=b[0] for a,b in zip(rows,rows[1:]))):
                raise ValueError('Explicit ordered bounded projection timing required')
    before=events[0]['before'];after=events[-1]['after']
    mask=lambda candidates:sum(1<<('ABCDEFG'.index(c)) for c in candidates)
    if s['candidate_mask']!=[[0,mask(before)],[s['candidate_events'][0]['decision_end'],mask(after)],[s['duration'],mask(after)]]:
        raise ValueError('Candidate state must derive from the audited action sequence')
    return {'status':'PASS','candidate_states':events,'world_words':len(world),'projections':len(ids)}

def current(folder):
    s=read(folder/'NATIVE_SPEC.json');parent=read(s['parent_plan'])
    validate_proof(parent)
    for entry in s['input_files']:
        if file_sha(entry['path'])!=entry['sha256']:raise ValueError('Bound production input changed')
    checked=validate_spec(s,parent,read(parent['bundle_path']))
    return s,checked

def process():
    value=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-Process AfterFX -ErrorAction Stop | Select-Object Id,MainWindowHandle | ConvertTo-Json -Compress'],
        encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW))
    if not isinstance(value,dict):raise ValueError('Exactly one AE host required')
    return value['Id'],value['MainWindowHandle']

class OwnedNative:
    def __init__(self,folder,opening=False):
        self.folder=folder;self.spec,_=current(folder);self.pid,self.hwnd=process()
        self.client=JunkdogeClient();self.client.initialize()
        self.client.call('ae_skillUse',{'name':'ae-execution-guide'})
        initial=self.reader()
        if initial['rendering']:raise ValueError('AE is already rendering')
        if not opening and initial['project_path']!=str(Path(self.spec['project']).resolve()):
            raise ValueError('Intended native project must be active')
        self.lease=HostOwnership('after_effects','/root',folder.name,{k:initial[k] for k in ('process_id','project_path','target_id')})
        self.lease.acquire();self.log=[]
        if (folder/'HOST_RECEIPTS.json').exists():self.log=read(folder/'HOST_RECEIPTS.json')
    def call_read(self,code):
        raw=self.client.call('ae_exec',{'code':code,'timeout_sec':60},timeout=75)
        return json.loads(raw['content'])
    def reader(self):
        pid,_=process();r=self.call_read("JSON.stringify({path:app.project.file?app.project.file.fsName:'',comp:app.project.activeItem instanceof CompItem?app.project.activeItem.id:null,rendering:app.project.renderQueue.rendering});")
        return {'process_id':pid,'project_path':str(Path(r['path']).resolve()) if r['path'] else '',
                'target_id':'comp:'+str(r['comp']) if r['comp'] is not None else 'none','rendering':r['rendering']}
    def mutate(self,label,code,*,switch=False,new_project=None,timeout=600):
        current(self.folder);before=self.reader()
        args={'code':code,'undo_group_name':label,'timeout_sec':timeout}
        write(self.folder/'PENDING_WRITE.json',{'args':args,'before':before,'lease':self.lease.record})
        target=None
        if switch or new_project:
            def target(result):
                value=json.loads(result['content']);comp=value.get('comp_id')
                return {'process_id':self.pid,'project_path':str(Path(new_project or before['project_path']).resolve()),
                        'target_id':'comp:'+str(comp) if comp is not None else 'none'}
        result=self.lease.mutate(self.reader,lambda:self.client.call('ae_exec',args,timeout=timeout+30),target_after=target)
        native=json.loads(result['content'])
        self.log.append({'label':label,'code_sha':sha(code),'before':before,'after':self.reader(),
                         'token':self.lease.record['token'],'native':native})
        write(self.folder/'HOST_RECEIPTS.json',self.log);return native
    def release(self):self.lease.release(self.reader)

def build(folder):
    s,_=current(folder)
    if Path(s['project']).exists():raise FileExistsError('Use a new native revision')
    owner=OwnedNative(folder,opening=True)
    snapshot=folder/'HOST_PRIOR_SNAPSHOT.aep'
    if snapshot.exists():raise FileExistsError('Prior-host snapshot already exists')
    code='app.project.save(new File('+json.dumps(snapshot.as_posix())+'));JSON.stringify({comp_id:app.project.activeItem instanceof CompItem?app.project.activeItem.id:null});'
    owner.mutate('Preserve prior AE session in new private snapshot',code,new_project=snapshot)
    owner.mutate('Create independent native Fast Pass project',
        'app.newProject();app.project.save(new File('+json.dumps(Path(s['project']).as_posix())+'));JSON.stringify({comp_id:null});',new_project=s['project'])
    code='var RCF_SPEC='+json.dumps((folder/'NATIVE_SPEC.json').as_posix())+';\n'+(HERE/'motion.jsx').read_text(encoding='utf-8')+'\n'+(HERE/'build.jsx').read_text(encoding='utf-8')
    identity=owner.mutate('Build one native Fast Pass and fixed camera control',code,switch=True)
    write(folder/'NATIVE_IDENTITY.json',identity);owner.release();return identity

def native_audit(folder):
    s,_=current(folder);identity=read(folder/'NATIVE_IDENTITY.json')
    c=JunkdogeClient();c.initialize()
    code='var RCF_COMPS='+json.dumps(identity['compositions'])+';var RCF_SHA='+json.dumps(s['spec_sha'])+';var RCF_FRAMES='+str(s['frames'])+';\n'+(HERE/'audit.jsx').read_text(encoding='utf-8')
    raw=json.loads(c.call('ae_exec',{'code':code,'timeout_sec':180},timeout=195)['content'])
    summary=check_native_audit(s,raw)
    write(folder/'NATIVE_AUDIT.json',raw);write(folder/'NATIVE_AUDIT_SUMMARY.json',summary);return summary

def check_native_audit(s,raw):
    if raw['spec_sha']!=s['spec_sha'] or set(raw['compositions'])!={'A','B'}:raise ValueError('Wrong native audit')
    expected={w['id']:w['text'] for col in s['columns'] for w in col['words']}
    projections={p['id']:p for p in s['projections']}
    normalized={};first_after=math.ceil(s['candidate_events'][0]['decision_end']*24)
    for variant,comp in raw['compositions'].items():
        if comp['canvas']!=[3840,2160,24,s['duration']]:raise ValueError('Wrong native canvas')
        layers={l['name']:l for l in comp['layers']}
        if len(layers)!=len(comp['layers']):raise ValueError('Ambiguous native identity')
        for name,text in expected.items():
            layer=layers[name]
            if layer['text']!=text or not layer['threeD'] or layer['sourceTextKeys'] or layer['sourceTextExpression']:
                raise ValueError('Native source glyph changed')
        for name,node in projections.items():
            layer=layers[name];origin=layers[node['origin_word_id']];binding=json.loads(layer['comment'])
            if (layer['text']!=origin['text'] or binding['origin_layer_id']!=origin['layer_id']
                    or layer['position']['keys'][0][1]!=origin['position']['value'] or not layer['threeD']):
                raise ValueError('Projection detached from actual native origin')
        cam=layers['GUIDED_CAMERA']
        if cam['focus_error'] or not cam['dof'] or not cam['focus']['expression']:raise ValueError('Real camera focus invalid')
        for n,sample in enumerate(comp['samples']):
            if sample['mask']!=(s['candidate_mask'][0][1] if n<first_after else s['candidate_mask'][-1][1]):
                raise ValueError('Actual native candidate state differs')
            if not math.isfinite(sample['focus']) or sample['focus']<=0:raise ValueError('Focus behind camera')
        if len(comp['samples'])!=s['frames']:raise ValueError('Missing actual-time audit')
        clone=deepcopy(layers)
        for row in clone.values():
            row.pop('layer_id')
            if row['comment']:
                b=json.loads(row['comment']);b.pop('origin_layer_id',None);row['comment']=b
        for key in ('position','look'):clone['GUIDED_CAMERA'].pop(key)
        normalized[variant]=clone
    if normalized['A']!=normalized['B']:raise ValueError('A/B altered more than camera Position / Point of Interest')
    a=raw['compositions']['A']['samples'];b=raw['compositions']['B']['samples']
    if any(r['camera']!=a[0]['camera'] or r['look']!=a[0]['look'] for r in a):raise ValueError('A camera not fixed')
    if all(r['camera']==b[0]['camera'] for r in b):raise ValueError('B camera not actually moving')
    return {'status':'PASS','spec_sha':s['spec_sha'],'native_source_words':len(expected),'native_projections':len(projections),
            'frames_per_variant':s['frames'],'first_after_frame':first_after,'camera_only_control':True,
            'native_glyphs_and_origins_read_back':True,'human_review':'PENDING','public_render_ready':False}

def preview(folder):
    s,_=current(folder);identity=read(folder/'NATIVE_IDENTITY.json');owner=OwnedNative(folder)
    out=folder/'native-previews';out.mkdir(exist_ok=True);receipt=[]
    for variant,comp in identity['compositions'].items():
        for frame in (36,116,171,249,300,324,400):
            path=out/f'{variant}_{frame:04d}.png'
            if path.exists():raise FileExistsError('Preview already exists')
            code='var cp=AEMCP.compById('+str(comp)+');cp.saveFrameToPng('+str(frame/24)+',new File('+json.dumps(path.as_posix())+'));JSON.stringify({comp_id:app.project.activeItem.id});'
            native=owner.mutate('Save native '+variant+' preview '+str(frame),code)
            receipt.append({'variant':variant,'frame':frame,'path':str(path),'sha256':file_sha(path)})
    owner.release();write(folder/'NATIVE_PREVIEW_RECEIPT.json',receipt);return receipt

def render(folder,variants):
    s,_=current(folder);identity=read(folder/'NATIVE_IDENTITY.json')
    if read(folder/'NATIVE_AUDIT_SUMMARY.json')['status']!='PASS':raise ValueError('Native audit required')
    owner=OwnedNative(folder);receipts={}
    for variant in variants:
        if variant not in ('A','B'):raise ValueError('Bound A/B only')
        directory=Path(s['scratch'])/variant
        directory.mkdir(parents=True,exist_ok=False);transfers=[]
        if available_memory()<2**30:raise RuntimeError('Below user one GiB reserve')
        for first in range(0,s['frames'],48):
            count=min(48,s['frames']-first);part=directory/f'batch-{first:05d}';part.mkdir()
            code='''(function(){var cp=AEMCP.compById(COMP);if(app.project.renderQueue.rendering||JSON.parse(cp.comment).spec_sha!==BINDING)throw Error('Wrong or busy target');for(var i=1;i<=app.project.renderQueue.numItems;i++){var old=app.project.renderQueue.item(i);if(old.render&&old.status===RQItemStatus.QUEUED)throw Error('Unrelated queued render');}cp.openInViewer();var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('TIFF')!==-1){preset=o.templates[i];break;}if(!preset)throw Error('Native TIFF unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=FIRST/24;q.timeSpanDuration=COUNT/24;app.setMultiFrameRenderingConfig(true,50);app.project.renderQueue.render();var done=q.status===RQItemStatus.DONE;if(done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return JSON.stringify({comp_id:cp.id,done:done,first:FIRST,count:COUNT,preset:preset});})();'''
            for key,value in {'COMP':str(identity['compositions'][variant]),'BINDING':json.dumps(s['spec_sha']),
                'DEST':json.dumps((part/'NATIVE_[#####].tif').as_posix()),'FIRST':str(first),'COUNT':str(count)}.items():code=code.replace(key,value)
            write(folder/'PROGRESS.json',{'variant':variant,'completed':first,'total':s['frames'],'status':'RENDERING'})
            with monitor_existing_render(owner.pid,owner.hwnd,minimum_free_gib=1) as memory:
                native=owner.mutate('Render native '+variant+' frames '+str(first),code,switch=True)
            paths=sorted(part.glob('*.tif'))
            if not native['done'] or len(paths)!=count or memory['abort_requested']:raise RuntimeError('Native frames incomplete; no automatic retry')
            hashes={}
            for offset,path in enumerate(paths):
                target=directory/f'FRAME_{first+offset:05d}.tif'
                if target.exists():raise FileExistsError('Never overwrite native frames')
                path.rename(target);hashes[target.name]=file_sha(target)
            transfer={'first':first,'count':count,'frame_shas':hashes,'memory':memory,'native':native,'spec_sha':s['spec_sha']}
            write(folder/f'FRAME_TRANSFER_{variant}_{first:05d}.json',transfer);transfers.append(sha(transfer))
            print(json.dumps({'variant':variant,'native_frames':first+count,'total':s['frames']}),flush=True)
        receipt={'variant':variant,'comp_id':identity['compositions'][variant],'spec_sha':s['spec_sha'],
            'frames':s['frames'],'directory':str(directory),'transfers':transfers,'project_sha':file_sha(s['project'])}
        write(folder/f'NATIVE_RENDER_{variant}.json',receipt);receipts[variant]=receipt
    owner.release();write(folder/'PROGRESS.json',{'status':'COMPLETE','variants':variants,'frames_per_variant':s['frames']});return receipts

def package(folder,variants):
    s,_=current(folder);outputs=[]
    for variant in variants:
        receipt=read(folder/f'NATIVE_RENDER_{variant}.json');directory=Path(receipt['directory']);cursor=0;transfers=[]
        for path in sorted(folder.glob('FRAME_TRANSFER_'+variant+'_*.json')):
            part=read(path)
            if part['first']!=cursor or part['spec_sha']!=s['spec_sha']:raise ValueError('Wrong native frame receipt')
            for name,value in part['frame_shas'].items():
                if file_sha(directory/name)!=value:raise ValueError('Native pixels changed')
            cursor+=part['count'];transfers.append(sha(part))
        if cursor!=s['frames'] or transfers!=receipt['transfers']:raise ValueError('Incomplete native provenance')
        target=folder/(variant+'_NATIVE_FAST_PASS_4K.mp4')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-framerate','24','-start_number','0',
            '-i',str(directory/'FRAME_%05d.tif'),'-frames:v',str(s['frames']),'-an','-vf','scale=out_color_matrix=bt709:out_range=tv',
            '-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709',
            '-color_trc','bt709','-color_primaries','bt709','-movflags','+faststart',str(target)],check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(target)],text=True))
        video=next(v for v in probe['streams'] if v['codec_type']=='video')
        if (video['width'],video['height'],video['avg_frame_rate'],int(video['nb_read_frames']))!=(3840,2160,'24/1',s['frames']):raise ValueError('Actual encoded media mismatch')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
        outputs.append({'variant':variant,'path':str(target),'sha256':file_sha(target),'spec_sha':s['spec_sha'],
            'native_render_sha':sha(receipt),'canvas':[3840,2160,24],'frames':s['frames'],'decode':'PASS','human_review':'PENDING','public_render_ready':False})
    write(folder/'MEDIA_INDEX.json',outputs);return outputs

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('check','build','audit','preview','render','package'))
    parser.add_argument('folder');parser.add_argument('--variants',nargs='+',default=['A','B']);args=parser.parse_args()
    folder=Path(args.folder).resolve()
    if not folder.is_relative_to(ROOT/'local-data'):raise ValueError('Private revision under local-data required')
    operation={'check':lambda:current(folder)[1],'build':lambda:build(folder),'audit':lambda:native_audit(folder),'preview':lambda:preview(folder),
        'render':lambda:render(folder,args.variants),'package':lambda:package(folder,args.variants)}[args.operation]
    result=operation();print(json.dumps(result if args.operation not in ('build','preview') else {'status':'DONE','operation':args.operation},ensure_ascii=False))
