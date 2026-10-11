"""Native bounded frame rendering; every Adobe write uses the owned host.

The existing full native picture supplies the unchanged old picture variants.
New pure B06 is a precise subrange of the newly rendered native context. No
teaching inference or synthetic drawing is substituted for native AE frames.
"""
import argparse
import json
from pathlib import Path
import subprocess
import shutil

from produce import (OwnedAE, current, local, read, write, sha, file_sha, ROOT,
                     available_memory, FPS)

NATIVE_COMPS = ('OLD_CONTEXT_VISUAL', 'NEW_CONTEXT_VISUAL', 'NEW_CONTEXT_FULL')


def preview(folder):
    owner = OwnedAE(folder)
    identity = read(folder/'NATIVE_IDENTITY.json')
    out = folder/'previews'; out.mkdir(exist_ok=True)
    evidence = []
    for frame in (72, 170, 255, 355, 432, 510, 636):
        path = out/f'NEW_B06_{frame:04d}.png'
        if path.exists():
            raise FileExistsError('Existing preview must be inspected rather than overwritten')
        code = '(function(){var cp=AEMCP.compById(ID);cp.saveFrameToPng(TIME,new File(PATH));return JSON.stringify({frame:FRAME,source_comp_id:cp.id,output:PATH});})();'
        code = code.replace('ID',str(identity['compositions']['NEW_B06_FULL']['comp_id'])).replace('TIME',str(frame/FPS)).replace('PATH',json.dumps(path.as_posix())).replace('FRAME',str(frame))
        result = owner.mutate('Native B06 preview '+str(frame),code,timeout=120)
        if not path.is_file(): raise ValueError('Native preview file missing')
        evidence.append({**result,'sha256':file_sha(path)})
    write(folder/'PREVIEW_RECEIPT.json',evidence)
    owner.release()
    return evidence


def verify_frames(directory, receipt):
    frames = Path(receipt['scratch'])
    expected = [f'FRAME_{i:05d}.tif' for i in range(receipt['frames'])]
    if sorted(p.name for p in frames.glob('FRAME_*.tif')) != expected:
        raise ValueError('Native frame coverage changed')
    cursor, hashes = 0, []
    for path in sorted(directory.glob('transfer-*.json')):
        transfer = read(path)
        if (transfer['start_frame'] != cursor or transfer['production_sha'] != receipt['production_sha']
                or transfer['composition'] != receipt['composition']):
            raise ValueError('Frame transfer binding/order changed')
        names = expected[cursor:cursor+transfer['count']]
        if sorted(transfer['frames']) != names:
            raise ValueError('Transfer coverage changed')
        for name in names:
            if file_sha(frames/name) != transfer['frames'][name]:
                raise ValueError('Native frame bytes changed')
        cursor += transfer['count']; hashes.append(sha(transfer))
    if cursor != receipt['frames'] or hashes != receipt['transfers']:
        raise ValueError('Incomplete render receipt')


def validate_render_binding(name, receipt, production, identity, audit):
    composition = identity['compositions'][name]
    expected = {'production_sha':production['production_sha'], 'spec_sha':production['spec_sha'],
        'composition':name, 'comp_id':composition['comp_id'],
        'source_frames':composition['source_frames'], 'frames':composition['frames'],
        'duration':composition['frames']/FPS, 'canvas':[3840,2160,24],
        'native_project':production['project']}
    if (any(receipt.get(k) != v for k,v in expected.items())
            or identity['spec_sha'] != production['spec_sha']
            or identity['project'] != production['project']
            or audit['status'] != 'PASS' or audit['spec_sha'] != production['spec_sha']
            or audit['compositions'] != 6 or audit['errors']):
        raise ValueError('Native render does not bind the current audited production and composition')


def render_checkpoint(folder, name, token, completed):
    production,_=current(folder);identity=read(folder/'NATIVE_IDENTITY.json')
    directory=folder/'renders'/name
    parts=[read(p) for p in sorted(directory.glob('transfer-*.json'))]
    if not parts or completed!=sum(p['count'] for p in parts):
        raise ValueError('Explicit checkpoint must match all completed transfers')
    frames=Path('G:/AdobeCache/video-os')/folder.name/name
    checkpoint={'scratch':str(frames),'frames':completed,'production_sha':production['production_sha'],
        'composition':name,'transfers':[sha(p) for p in parts]}
    verify_frames(directory,checkpoint)
    for part in parts:
        result=read(directory/f"native-batch-{part['start_frame']:05d}.json")['native']
        if (not result['done'] or result['count']!=part['count'] or result['start_frame']!=part['start_frame']
                or result['comp_id']!=identity['compositions'][name]['comp_id']):
            raise ValueError('Every checkpoint transfer requires a completed native batch')
    for path in frames.iterdir():
        if path.is_dir() and any(path.iterdir()):raise ValueError('Partial native frames remain outside completed transfers')
    previous=read(ROOT/'local-data/adobe-host-ownership/after_effects.json')
    running=subprocess.check_output(['powershell','-NoProfile','-Command',
        '@(Get-Process -ErrorAction Stop | Where-Object Id -eq '+str(previous['controller_pid'])+').Count'],
        creationflags=subprocess.CREATE_NO_WINDOW).strip()
    if int(running)!=0:raise ValueError('The original checkpoint controller is still alive')
    last=read(folder/'AE_OWNERSHIP_RECEIPTS.json')[-1]
    if (last['lease_token']!=token or not last['native'].get('done')
            or last['native']['start_frame']+last['native']['count']!=completed
            or last['after']['target_id']!='comp:'+str(identity['compositions'][name]['comp_id'])):
        raise ValueError('Last guarded native completion does not bind the checkpoint')
    evidence={str(p):file_sha(p) for p in [folder/'AE_OWNERSHIP_RECEIPTS.json',
        folder/'NATIVE_IDENTITY.json',folder/'NATIVE_AUDIT_SUMMARY.json',*sorted(directory.glob('*.json'))]}
    owner=OwnedAE(folder,{'token':token,'target':previous['target'],'expected_state':'OWNED','evidence':evidence})
    write(folder/'AE_RENDER_CHECKPOINT_RECONCILIATION.json',owner.lease.record)
    owner.mutate('Release completed render cache at verified checkpoint',
        "if(app.project.renderQueue.rendering)throw Error('Unexpected active render');app.purge(PurgeTarget.ALL_CACHES);JSON.stringify({comp_id:app.project.activeItem.id,purged_completed_cache:true});")
    return owner


def render(folder, names, batch_size=96, checkpoint=None):
    if not 1 <= batch_size <= 240 or any(n not in NATIVE_COMPS for n in names):
        raise ValueError('Explicit bounded native compositions and batches required')
    owner = render_checkpoint(folder,names[0],checkpoint['token'],checkpoint['frames']) if checkpoint else OwnedAE(folder)
    production = owner.p
    identity = read(folder/'NATIVE_IDENTITY.json')
    source_audit = read(folder/'NATIVE_AUDIT_SUMMARY.json')
    if source_audit['spec_sha'] != production['spec_sha'] or source_audit['status'] != 'PASS':
        raise ValueError('Current actual source and motion audit required')
    receipts = {}
    for name in names:
        composition = identity['compositions'][name]
        directory = folder/'renders'/name; directory.mkdir(parents=True,exist_ok=True)
        frames = Path('G:/AdobeCache/video-os')/folder.name/name
        frames.mkdir(parents=True,exist_ok=True)
        first_frame=checkpoint['frames'] if checkpoint and name==names[0] else 0
        if (any(frames.iterdir()) and not first_frame) or (directory/'NATIVE_RENDER_RECEIPT.json').exists():
            raise FileExistsError('Existing native render requires explicit reconciliation; no automatic replay')
        total = composition['frames']
        transfers=[sha(read(p)) for p in sorted(directory.glob('transfer-*.json'))] if first_frame else []
        if shutil.disk_usage(frames).free < total*3840*2160*4 + 5*2**30:
            raise RuntimeError('Insufficient space for this native frame pack and reserve')
        for first in range(first_frame,total,batch_size):
            current(folder)
            if available_memory() < 2**30: raise RuntimeError('Below one GiB free-memory reserve')
            count = min(batch_size,total-first); part = frames/('batch-'+str(first)); part.mkdir()
            code = '''(function(){var cp=AEMCP.compById(COMP);if(app.project.renderQueue.rendering||JSON.parse(cp.comment).production_sha!==PRODUCTION)throw Error('Wrong or busy bounded composition');for(var i=1;i<=app.project.renderQueue.numItems;i++){var old=app.project.renderQueue.item(i);if(old.render&&old.status===RQItemStatus.QUEUED)throw Error('Unrelated queued render');}cp.openInViewer();app.purge(PurgeTarget.ALL_CACHES);var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var j=0;j<o.templates.length;j++)if(o.templates[j].indexOf('TIFF')!==-1){preset=o.templates[j];break;}if(!preset)throw Error('TIFF unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=FIRST/24;q.timeSpanDuration=COUNT/24;app.setMultiFrameRenderingConfig(true,50);app.project.renderQueue.render();var done=q.status===RQItemStatus.DONE;if(done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return JSON.stringify({done:done,start_frame:FIRST,count:COUNT,comp_id:cp.id,preset:preset,mfr_cpu_percent:50,purged_after_render:true});})();'''
            for key,value in {'COMP':str(composition['comp_id']), 'PRODUCTION':json.dumps(production['production_sha']),
                              'DEST':json.dumps((part/'NATIVE_[#####].tif').as_posix()),'FIRST':str(first),'COUNT':str(count)}.items():
                code = code.replace(key,value)
            write(folder/'render-progress.json',{'state':'RENDERING','composition':name,'completed':first,'total':total,'production_sha':production['production_sha']})
            # No background keypress or cancellation can bypass the ownership
            # boundary. Check resources between bounded calls; never auto-retry.
            memory = {'free_before':available_memory(),'automatic_host_abort':False}
            native = owner.mutate('Render '+name+' frames '+str(first)+'..'+str(first+count),code,new_comp=True)
            memory['free_after'] = available_memory()
            paths = sorted(part.glob('*.tif'))
            write(directory/f'native-batch-{first:05d}.json',{'native':native,'memory':memory})
            if not native['done'] or len(paths)!=count:
                raise ValueError('Native render incomplete; inspect before any continuation')
            checks = {}
            for offset,path in enumerate(paths):
                destination = frames/f'FRAME_{first+offset:05d}.tif'
                if destination.exists() or path.resolve().parent != part.resolve() or destination.resolve().parent != frames.resolve():
                    raise ValueError('Unsafe or duplicate frame transfer')
                checks[destination.name] = file_sha(path)
                path.rename(destination)
            transfer = {'production_sha':production['production_sha'],'composition':name,'start_frame':first,
                        'count':count,'frames':checks,'memory':memory}
            write(directory/f'transfer-{first:05d}.json',transfer); transfers.append(sha(transfer))
            print(json.dumps({'composition':name,'native_frames':first+count,'total':total}),flush=True)
        receipt = {'production_sha':production['production_sha'],'spec_sha':production['spec_sha'],
            'composition':name,'comp_id':composition['comp_id'],'source_frames':composition['source_frames'],
            'frames':total,'duration':total/FPS,'canvas':[3840,2160,24],'scratch':str(frames),
            'transfers':transfers,'native_project':production['project'],'project_sha_at_completion':file_sha(production['project']),
            'human_visual_review':'PENDING','public_render_ready':False}
        write(directory/'NATIVE_RENDER_RECEIPT.json',receipt); receipts[name]=receipt
    write(folder/'render-progress.json',{'state':'COMPLETE','compositions':{k:v['frames'] for k,v in receipts.items()},'production_sha':production['production_sha']})
    owner.release()
    return {k:v['frames'] for k,v in receipts.items()}


def encode(args, target, count):
    subprocess.run(['ffmpeg','-v','error','-n',*args,'-frames:v',str(count),'-an',
        '-vf','scale=out_color_matrix=bt709:out_range=tv,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709',
        '-c:v','libx264','-preset','fast','-crf','16',
        '-threads','6','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709',
        '-color_primaries','bt709','-color_trc','bt709','-movflags','+write_colr',str(target)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))['streams'][0]
    if [probe['width'],probe['height'],probe['r_frame_rate'],int(probe['nb_frames'])] != [3840,2160,'24/1',count]:
        raise ValueError('Actual picture format/frame count changed')
    from premiere_production.lossless_handoff import rec709_binding
    rec709_binding(target)
    return {'path':str(target),'sha256':file_sha(target),'frames':count,'duration':count/FPS,'full_decode':'PASS',
            'public_render_ready':False}


def package(folder, names=None):
    production,_=current(folder); identity=read(folder/'NATIVE_IDENTITY.json')
    audit=read(folder/'NATIVE_AUDIT_SUMMARY.json')
    destination=folder/'pictures';destination.mkdir(exist_ok=True)
    names=list(identity['compositions']) if names is None else names
    if not names or len(set(names))!=len(names) or any(n not in identity['compositions'] for n in names):
        raise ValueError('Explicit bounded picture variants required')
    existing=read(folder/'PICTURE_INDEX.json') if (folder/'PICTURE_INDEX.json').exists() else None
    if existing and existing['production_sha']!=production['production_sha']:raise ValueError('Existing picture revision changed')
    pictures=existing['pictures'] if existing else {}
    if set(names)&pictures.keys():raise FileExistsError('Inspect existing pictures instead of overwriting or replaying')
    needed={n if n in NATIVE_COMPS else 'NEW_CONTEXT_FULL' for n in names if n in NATIVE_COMPS or n=='NEW_B06_FULL'}
    receipts={name:read(folder/'renders'/name/'NATIVE_RENDER_RECEIPT.json') for name in needed}
    for name,receipt in receipts.items():
        validate_render_binding(name,receipt,production,identity,audit)
        verify_frames(folder/'renders'/name,receipt)
    old=Path(production['baseline_picture']['output'])
    if file_sha(old)!=production['baseline_picture']['output_sha']:raise ValueError('Old native picture changed')
    for name in names:
        target=destination/(name+'.mp4');composition=identity['compositions'][name]
        if name in NATIVE_COMPS:
            receipt=receipts[name]
            args=['-framerate','24','-start_number','0','-i',str(Path(receipt['scratch'])/'FRAME_%05d.tif')]
            origin={'native_receipt_sha':sha(receipt),'native_local_start_frame':0}
        elif name=='NEW_B06_FULL':
            receipt=receipts['NEW_CONTEXT_FULL'];first=production['bounds']['new_pure'][0]-production['bounds']['new_context'][0]
            args=['-framerate','24','-start_number',str(first),'-i',str(Path(receipt['scratch'])/'FRAME_%05d.tif')]
            origin={'native_receipt_sha':sha(receipt),'native_local_start_frame':first}
        else:
            first=composition['source_frames'][0]
            args=['-ss',str(first/FPS),'-i',str(old)]
            origin={'baseline_picture_sha':production['baseline_picture']['output_sha'],'native_source_start_frame':first,
                    'reuse':'Existing complete native AE picture, exact source frame interval'}
        pictures[name]={**encode(args,target,composition['frames']),**origin,'comp_id':composition['comp_id'],
                        'source_frames':composition['source_frames']}
        write(folder/'picture-progress.json',{'completed':list(pictures)})
        index={'production_sha':production['production_sha'],'pictures':pictures,
            'coverage':'SIX_COMPLETE' if len(pictures)==6 else 'PARTIAL_BOUND_VARIANTS',
            'human_visual_review':'PENDING','public_render_ready':False}
        write(folder/'PICTURE_INDEX.json',index)
    return {k:v['frames'] for k,v in pictures.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('preview','render','resume','package'))
    parser.add_argument('folder');parser.add_argument('--compositions',nargs='+',default=list(NATIVE_COMPS));parser.add_argument('--batch-size',type=int,default=96)
    parser.add_argument('--variants',nargs='+')
    parser.add_argument('--token');parser.add_argument('--completed-frames',type=int)
    args=parser.parse_args();folder=local(args.folder)
    result=(render(folder,args.compositions,args.batch_size,
                {'token':args.token,'frames':args.completed_frames} if args.operation=='resume' else None)
            if args.operation in ('render','resume') else
            package(folder,args.variants) if args.operation=='package' else preview(folder))
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
