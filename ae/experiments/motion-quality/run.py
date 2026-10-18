"""Single-scene native experiment; reuse the existing shared-host guard."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'read-frog-motion'
spec=importlib.util.spec_from_file_location('read_frog_trial',PREVIOUS/'run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
read,write,sha256=base.read,base.write,base.sha256

class Trial(base.Trial):
    def binding(self):
        paths=[HERE/'build.jsx',HERE/'motion-rig.jsx',PREVIOUS/'motion-rig.jsx']
        if self.i.get('reading_focus_revision')==2:paths += [HERE/'reading-focus.jsx',HERE/'revise_reading.py']
        if self.i.get('reading_focus_revision')==3:paths += [HERE/'coverage-patch.jsx',HERE/'revise_coverage.py',HERE/'revise_final_copy.py',HERE.parents[1]/'rigs/reading-focus.jsx']
        import os
        return {os.path.relpath(p,HERE.parent):sha256(p) for p in paths}

    def native(self):
        n=read(self.folder/'NATIVE_IDENTITY.json')
        if n['code_binding']!=self.binding():raise ValueError('Realized code changed; inspect before continuing')
        if Path(self.h.identity()['project_path']).resolve()!=self.project:raise ValueError('Trial is not open')
        return n

    def build(self):
        if self.project.exists() or (self.folder/'NATIVE_IDENTITY.json').exists():raise FileExistsError('Inspect completed/unknown build; no replay')
        code='\n'.join(p.read_text('utf-8') for p in (PREVIOUS/'motion-rig.jsx',HERE/'motion-rig.jsx',HERE/'build.jsx'))
        code=code.replace('INPUT',json.dumps((self.folder/'TRIAL_INPUT.json').as_posix())).replace('PRE_SAVE',json.dumps((self.folder/'BUILT_BEFORE_SAVE.json').as_posix()))
        r=self.mutate('Build independent native Motion Quality trial',lambda:self.h.js(code),after=lambda r:{'process_id':self.h.pid,'project_path':str(self.project),'target_id':'comp:'+str(r['B'])})
        r.update(code_binding=self.binding(),input_sha256=sha256(self.folder/'TRIAL_INPUT.json'))
        write(self.folder/'NATIVE_IDENTITY.json',r)
        return {k:v for k,v in r.items() if k!='rig'}

    def preview(self):
        n=self.native();result=[]
        for v in ('A','B'):
            receipt=self.folder/('PREVIEW_'+v+'.json')
            if receipt.exists():
                r=read(receipt)
                if r.get('native_identity_sha256')!=sha256(self.folder/'NATIVE_IDENTITY.json') or any(sha256(f['path'])!=f['sha256'] for f in r['frames']):raise ValueError('Preview binding changed')
                result.append(v);continue
            r=self.mutate('Native preview '+v,lambda:self.h.c.call('ae_previewFrame',{'comp_id':str(n[v]),'times':[0,3,5.8,7.6,10.8,13.8,16,18.7,20.9,22.8,25.7,29.8,31.4,32.8],'layout':'grid','grid_max_side':2048,'out_dir':str(self.folder/'previews'),'include_base64':False,'scale':.5},timeout=240),after={'process_id':self.h.pid,'project_path':str(self.project),'target_id':'comp:'+str(n[v])})
            r['native_identity_sha256']=sha256(self.folder/'NATIVE_IDENTITY.json')
            write(self.folder/('PREVIEW_'+v+'.json'),r);result.append(v)
        return {'previews':result}

    def restore(self):
        before=read(self.folder/'SESSION_BEFORE.json')
        if not before.get('blank_project'):return super().restore()
        self.native();identity=before['identity']
        code='if(app.project.dirty||app.project.renderQueue.rendering)throw Error("Host busy");app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.newProject();return {restored_blank_project:true};'
        r=self.mutate('Restore current-session blank AE project',lambda:self.h.js(code),after={k:identity[k] for k in ('process_id','project_path','target_id')})
        if sha256(self.i['parent_aep'])!=self.i['parent_aep_sha256']:raise ValueError('Parent project bytes changed')
        write(self.folder/'RESTORED.json',{'result':r,'identity':self.h.identity(),'parent_unchanged':True,'trial_project_sha256':sha256(self.project)})
        return r

    def render(self):
        n=self.native();qa=read(self.folder/'NATIVE_QA.json')
        if qa['status']!='PASS' or qa['native_identity_sha256']!=sha256(self.folder/'NATIVE_IDENTITY.json'):raise ValueError('Current native audit required')
        directory=self.folder/'parts';directory.mkdir(exist_ok=True);total=self.i['clip_frames']
        for variant in ('A','B'):
            pieces=[]
            for start in range(0,total,48):
                end=min(start+48,total);dest=directory/f'{variant}-{start:04}.mp4';receipt=dest.with_suffix('.json')
                if receipt.exists():
                    r=read(receipt)
                    if sha256(dest)!=r['sha256'] or r['native_sha256']!=sha256(self.folder/'NATIVE_IDENTITY.json'):raise ValueError('Stale part')
                    pieces.append(r);continue
                if dest.exists():raise FileExistsError('Inspect unreceipted render part')
                if base.available_memory()<2*2**30:raise RuntimeError('Insufficient memory reserve')
                code="var c=app.project.itemByID(CID);if(app.project.renderQueue.numItems||c.width!==3840||c.height!==2160||c.frameRate!==24)throw Error('Unexpected target');var q=app.project.renderQueue.items.add(c),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('H.264')>=0&&o.templates[i].indexOf('15 Mbps')>=0){preset=o.templates[i];break;}if(!preset)throw Error('Missing native preset');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanDuration=(END-START)/24;q.timeSpanStart=START/24;q.skipFrames=0;app.setMultiFrameRenderingConfig(false,25);app.beginSuppressDialogs();try{app.project.renderQueue.render();}finally{app.endSuppressDialogs(false);}var r={done:q.status===RQItemStatus.DONE,status:q.status,start:START,end:END,preset:preset};if(r.done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return r;"
                for key,value in {'CID':str(n[variant]),'DEST':json.dumps(dest.as_posix()),'START':str(start),'END':str(end)}.items():code=code.replace(key,value)
                with base.monitor_existing_render(self.h.pid,self.h.hwnd,minimum_free_gib=1) as memory:
                    r=self.mutate('Render '+variant+' '+str(start)+'-'+str(end),lambda:self.h.js(code),after={'process_id':self.h.pid,'project_path':str(self.project),'target_id':'comp:'+str(n[variant])})
                r.update(memory=memory,variant=variant,native_sha256=sha256(self.folder/'NATIVE_IDENTITY.json'),path=str(dest))
                if not r['done']:write(dest.with_suffix('.stopped.json'),r);raise RuntimeError('Stopped render: inspect, no blind retry')
                st=next(x for x in base.probe(dest)['streams'] if x['codec_type']=='video')
                if [st['width'],st['height'],int(st['nb_read_frames']),st['r_frame_rate']]!=[3840,2160,end-start,'24/1']:raise ValueError('Format mismatch')
                r['sha256']=sha256(dest);write(receipt,r);pieces.append(r)
                print(json.dumps({'variant':variant,'frames':end,'total':total,'minimum_free_gib':round(memory['minimum_free_bytes']/2**30,2)}),flush=True)
            listing=directory/(variant+'-concat.txt');listing.write_text(''.join("file '"+Path(r['path']).as_posix()+"'\n" for r in pieces),'utf-8')
            picture=self.folder/'media'/(variant+'_NATIVE_PICTURE.mp4')
            if not picture.exists():subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-c','copy','-movflags','+faststart',str(picture)],check=True)
            final=self.folder/'media'/(variant+'_MOTION_QUALITY_4K24.mp4')
            if not final.exists():
                cmd=['ffmpeg','-v','error','-n','-i',str(picture)];filters=[]
                for j,take in enumerate(self.i['voices']):
                    cmd+=['-i',take['voice']['path']];offset=round((take['voice_start']-self.i['clip_start'])*48000);filters.append(f'[{j+1}:a]adelay={offset}S:all=1[a{j}]')
                filters.append(''.join(f'[a{j}]' for j in range(len(self.i['voices'])))+f'amix=inputs={len(self.i["voices"])}:normalize=0,apad,atrim=duration={total/24}[audio]')
                cmd+=['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[audio]','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(final)];subprocess.run(cmd,check=True)
            subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(final),'-f','null','-'],check=True)
            write(self.folder/('RENDER_'+variant+'.json'),{'output':str(final),'sha256':sha256(final),'parts':pieces,'probe':base.probe(final),'full_decode':'PASS','voices':self.i['voices'],'human_review':'PENDING'})
        return {'A':read(self.folder/'RENDER_A.json')['output'],'B':read(self.folder/'RENDER_B.json')['output']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['build','preview','render','restore']);p.add_argument('folder');a=p.parse_args();print(json.dumps(getattr(Trial(a.folder),a.operation)(),ensure_ascii=False),flush=True)
