"""Bounded local A/B experiment. Reuses the current bridge and shared ownership.

It does not replace the production entry, select evidence, generate copy, or
promote a rig. Every operation needs a private TRIAL_INPUT and actual receipts.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ae_production.authored_native import Host, plan, probe
from ae_production.host_ownership import HostOwnership
from ae_production.memory_guard import available_memory, monitor_existing_render
from scripts.voice_delivery import sha256
from video_contracts import read, write

HERE=Path(__file__).resolve().parent

class Trial:
    def __init__(self, folder):
        self.folder=Path(folder).resolve(); self.i=read(self.folder/'TRIAL_INPUT.json')
        self.parent=Path(self.i['parent_folder']);plan(self.parent)
        if sha256(self.parent/'AV_PLAN.json')!=self.i['plan_sha256'] or sha256(self.i['parent_aep'])!=self.i['parent_aep_sha256']:
            raise ValueError('Parent production changed; inspect before experiment')
        self.h=Host(self.parent,'after_effects')
        self.project=Path(self.i['native_project']).resolve()

    def mutate(self,label,fn,after=None):
        before=self.h.identity()
        if Path(before['project_path']).resolve() not in (self.project,Path(self.i['parent_aep']).resolve()):
            raise ValueError('Another project is active')
        if before.get('dirty') or before.get('rendering'):raise ValueError('Host must be clean and idle')
        key={k:before[k] for k in ('process_id','project_path','target_id')}
        lease=HostOwnership('after_effects','/root',self.i['revision'],key,Path(self.i['ownership_directory']));lease.acquire()
        dest=self.folder/'dispatch'/str(time.time_ns());dest.parent.mkdir(exist_ok=True)
        write(dest.with_suffix('.pending.json'),{'label':label,'before':before,'token':lease.record['token']})
        def call():
            try:r=fn()
            except BaseException as exc:write(dest.with_suffix('.error.json'),{'error':str(exc)});raise
            write(dest.with_suffix('.transport.json'),r);return r
        result=lease.mutate(self.h.identity,call,target_after=after)
        lease.release(self.h.identity)
        write(dest.with_suffix('.complete.json'),{'label':label,'identity':self.h.identity(),'result':result})
        return result

    def native(self):
        n=read(self.folder/'NATIVE_IDENTITY.json')
        if n['rig_sha256']!=sha256(HERE/'motion-rig.jsx') or n['build_sha256']!=sha256(HERE/'build.jsx'):
            raise ValueError('Rig changed since realization; inspect and save a new revision')
        if Path(self.h.identity()['project_path']).resolve()!=self.project:raise ValueError('Trial is not open')
        return n

    def build(self):
        if self.project.exists() or (self.folder/'NATIVE_IDENTITY.json').exists():raise FileExistsError('Do not replay completed/unknown build')
        code=(HERE/'motion-rig.jsx').read_text('utf-8')+'\n'+(HERE/'build.jsx').read_text('utf-8')
        code=code.replace('INPUT',json.dumps((self.folder/'TRIAL_INPUT.json').as_posix())).replace('PRE_SAVE',json.dumps((self.folder/'BUILT_BEFORE_SAVE.json').as_posix()))
        r=self.mutate('Build separate native motion A/B',lambda:self.h.js(code,'Build separate native motion A/B'),after=lambda r:{'process_id':self.h.pid,'project_path':str(self.project),'target_id':'comp:'+str(r['B'])})
        r.update(rig_sha256=sha256(HERE/'motion-rig.jsx'),build_sha256=sha256(HERE/'build.jsx'),input_sha256=sha256(self.folder/'TRIAL_INPUT.json'))
        write(self.folder/'NATIVE_IDENTITY.json',r)
        return {k:v for k,v in r.items() if k!='rig'}

    def preview(self):
        n=self.native();out=[]
        for variant in ('A','B'):
            r=self.mutate('Capture trial '+variant,lambda:self.h.c.call('ae_previewFrame',{'comp_id':str(n[variant]),'times':[0,.8,1.6,2.5,3.6,4.5,5.25,5.8,6.5,7.5,9.5,11.6],'layout':'grid','grid_max_side':2048,'out_dir':str(self.folder/'previews'),'include_base64':False,'scale':.5},timeout=240))
            write(self.folder/('PREVIEW_'+variant+'.json'),r);out.append({'variant':variant,'result':r})
        return out

    def render(self):
        n=self.native();qa=read(self.folder/'NATIVE_QA.json')
        if qa['status']!='PASS' or qa['native_identity_sha256']!=sha256(self.folder/'NATIVE_IDENTITY.json'):
            raise ValueError('The realized trial needs its current native audit')
        directory=self.folder/'parts';directory.mkdir(exist_ok=True)
        for variant in ('A','B'):
            pieces=[]
            for start in range(0,288,48):
                end=min(start+48,288);dest=directory/f'{variant}-{start:04}.mp4';receipt=dest.with_suffix('.json')
                if receipt.exists():
                    r=read(receipt)
                    if sha256(dest)!=r['sha256'] or r['native_sha256']!=sha256(self.folder/'NATIVE_IDENTITY.json'):raise ValueError('Stale native part')
                    pieces.append(r);continue
                if dest.exists():raise FileExistsError('Unreceipted native part: inspect before resuming')
                if available_memory()<2*2**30:raise RuntimeError('Insufficient memory reserve')
                code="var c=app.project.itemByID(CID);if(app.project.renderQueue.numItems||c.width!==3840||c.height!==2160||c.frameRate!==24)throw Error('Unexpected native target');var q=app.project.renderQueue.items.add(c),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('H.264')>=0&&o.templates[i].indexOf('15 Mbps')>=0){preset=o.templates[i];break;}if(!preset)throw Error('Missing native preset');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanDuration=(END-START)/24;q.timeSpanStart=START/24;q.skipFrames=0;app.setMultiFrameRenderingConfig(false,25);app.beginSuppressDialogs();try{app.project.renderQueue.render();}finally{app.endSuppressDialogs(false);}var r={done:q.status===RQItemStatus.DONE,status:q.status,start:START,end:END,preset:preset};if(r.done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return r;"
                for key,v in {'CID':str(n[variant]),'DEST':json.dumps(dest.as_posix()),'START':str(start),'END':str(end)}.items():code=code.replace(key,v)
                with monitor_existing_render(self.h.pid,self.h.hwnd,minimum_free_gib=1) as memory:
                    r=self.mutate('Render '+variant+' frames '+str(start)+'-'+str(end),lambda:self.h.js(code))
                r.update(memory=memory,variant=variant,native_sha256=sha256(self.folder/'NATIVE_IDENTITY.json'),path=str(dest))
                if not r['done']:write(dest.with_suffix('.stopped.json'),r);raise RuntimeError('Native render stopped; inspect, do not retry blindly')
                stream=next(x for x in probe(dest)['streams'] if x['codec_type']=='video')
                if [stream['width'],stream['height'],int(stream['nb_read_frames']),stream['r_frame_rate']]!=[3840,2160,end-start,'24/1']:raise ValueError('Native format/frame mismatch')
                r['sha256']=sha256(dest);write(receipt,r);pieces.append(r)
                print(json.dumps({'variant':variant,'frames':end,'total':288,'minimum_free_bytes':memory['minimum_free_bytes']}),flush=True)
            listing=directory/(variant+'-concat.txt');listing.write_text(''.join("file '"+Path(r['path']).as_posix()+"'\n" for r in pieces),encoding='utf-8')
            picture=self.folder/'media'/(variant+'_PICTURE_4K24.mp4')
            if not picture.exists():subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-c','copy','-movflags','+faststart',str(picture)],check=True)
            # Exact same complete take/offset is supplied to both outputs. No
            # cut, time stretch, added music, sound effect, or narration change.
            take=self.i['voice'];offset=round((take['voice_start']-self.i['clip_start'])*48000)
            final=self.folder/'media'/(variant+'_MOTION_AB_4K24.mp4')
            if not final.exists():subprocess.run(['ffmpeg','-v','error','-n','-i',str(picture),'-i',take['voice']['path'],'-filter_complex',f'[1:a]adelay={offset}S:all=1,apad,atrim=duration=12[a]','-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(final)],check=True)
            subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(final),'-f','null','-'],check=True)
            write(self.folder/('RENDER_'+variant+'.json'),{'output':str(final),'sha256':sha256(final),'parts':pieces,'probe':probe(final),'full_decode':'PASS','voice':take,'offset_samples':offset,'human_review':'PENDING'})
        return {'A':read(self.folder/'RENDER_A.json')['output'],'B':read(self.folder/'RENDER_B.json')['output']}

    def restore(self):
        n=self.native();before=read(self.folder/'SESSION_BEFORE.json');identity=before['identity']
        code='if(app.project.dirty||app.project.renderQueue.rendering)throw Error("Host busy");app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.open(new File('+json.dumps(Path(identity['project_path']).as_posix())+'));for(var j=1;j<=app.project.numItems;j++)app.project.item(j).selected=false;var c=app.project.itemByID('+identity['target_id'].split(':')[1]+');c.selected=true;c.openInViewer();return {restored:true};'
        r=self.mutate('Restore exact prior AE project',lambda:self.h.js(code),after={k:identity[k] for k in ('process_id','project_path','target_id')})
        if sha256(identity['project_path'])!=before['sha256']:raise ValueError('Parent project bytes changed')
        write(self.folder/'RESTORED.json',{'result':r,'identity':self.h.identity(),'parent_unchanged':True,'trial_project_sha256':sha256(self.project)})
        return r

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['build','preview','render','restore']);parser.add_argument('folder');args=parser.parse_args()
    print(json.dumps(getattr(Trial(args.folder),args.operation)(),ensure_ascii=False),flush=True)
