"""Bounded native rendering of a validated locating patch; current status required."""
import argparse
import hashlib
import json
import re
import shutil
import os
import zipfile
from pathlib import Path
import run as relay
import fulltext
import locating_native
import acquisition_ab
from ae_production.execution import mutation_call
from video_contracts import read, write, sha
from video_contracts.locating_trace import require_trace


def current(config):
    trace=read(config['trace']);status=read(config['trace_status'])
    require_trace(trace,status,read(config['bundle']),read(config['source_status']))
    patch=read(config['patch'])
    if (patch['patch_sha']!=sha({k:v for k,v in patch.items() if k!='patch_sha'})
            or patch['plan']['trace_sha']!=trace['semantic_binding_sha']):
        raise ValueError('Current trace and patch required')
    audit=json.loads(read(config['native_audit'])['content'])
    locating_native.validate_motion(patch,audit)
    frames=config['frames']
    if (len(frames)!=2 or any(type(v) is not int for v in frames) or not 0<=frames[0]<frames[1]
            or config.get('chunk_frames',96) not in range(1,121)):
        raise ValueError('Explicit positive frame window and bounded chunks required')
    return patch


def render(config):
    patch=current(config);out=relay.local(config['output']);out.mkdir(exist_ok=False,parents=True)
    write(out/'render-input.json',config);c=relay.client();first,last=config['frames'];chunks=[]
    folder=out/'native-frames';folder.mkdir()
    for start in range(first,last,config.get('chunk_frames',96)):
        current(config);count=min(config.get('chunk_frames',96),last-start)
        if os.name=='nt':
            from ae_production.memory_guard import available_memory
            minimum=config.get('minimum_free_gib',1)
            if not 1<=minimum<=20:raise ValueError('At least 1 GiB system memory reserve required')
            if available_memory()<minimum*2**30:
                raise RuntimeError('Low free memory; next native batch not started')
        part=out/('part-'+str(start));part.mkdir()
        code='''(function(){var cp=AEMCP.compById(COMP),binding=JSON.parse(cp.comment);if(binding.locating_patch_sha!==PATCH)throw Error('Wrong live locating patch');if(cp.width!==3840||cp.height!==2160||Math.abs(cp.frameRate-24)>.0001||cp.resolutionFactor[0]!==1||cp.resolutionFactor[1]!==1)throw Error('Native 4K required');if(END>cp.duration+0.0001)throw Error('Render exceeds composition');for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).render&&app.project.renderQueue.item(i).status===RQItemStatus.QUEUED)throw Error('Unrelated queued render');var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('TIFF')!==-1){preset=o.templates[i];break;}if(!preset)throw Error('TIFF preset required');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=DURATION;app.project.save();app.setMultiFrameRenderingConfig(false,100);var begin=(new Date()).getTime();app.project.renderQueue.render();app.project.save();return JSON.stringify({done:q.status===RQItemStatus.DONE,comp_id:cp.id,start:q.timeSpanStart,duration:q.timeSpanDuration,preset:preset,render_ms:(new Date()).getTime()-begin});})();'''
        # Unique delimiters prevent accidental replacements inside identifiers.
        for key,value in {'COMP':str(config['comp_id']),'PATCH':json.dumps(patch['patch_sha']),
            'END':str(last/24),'DEST':json.dumps((part/'FRAME_[#####].tif').as_posix()),
            'START':str(start/24),'DURATION':str(count/24)}.items():
            code=re.sub(r'\b'+key+r'\b',lambda m,v=value:v,code)
        if config.get('purge_between_chunks',False):
            purge=mutation_call(c,'ae_exec',{'code':"(function(){if(app.project.renderQueue.rendering)throw Error('Render active');app.purge(PurgeTarget.ALL_CACHES);return JSON.stringify({purged:'transient_AE_caches'});})();",
                'checkpoint_label':'before-locating-batch-cache-purge','timeout_sec':120},out,150)
            write(out/('pre-chunk-purge-'+str(start)+'.json'),purge)
        result=mutation_call(c,'ae_exec',{'code':code,'checkpoint_label':'before-locating-render-'+str(start),
                                        'timeout_sec':600},out,630)
        write(out/('native-render-'+str(start)+'.json'),result);chunk=json.loads(result['content'])
        paths=sorted(part.glob('*.tif'));fulltext.validate_render_chunk(chunk,paths,start,count,config['comp_id'])
        for index,path in enumerate(paths):
            destination=folder/('FRAME_'+str(start+index).zfill(5)+'.tif')
            if not path.resolve().is_relative_to(out) or destination.exists():raise ValueError('Unsafe frame transfer')
            shutil.move(str(path),str(destination))
        part.rmdir();chunks.append(chunk);write(out/'native-render-segments.json',chunks)
        print(json.dumps({'native_frames_completed':start+count-first,'total_frames':last-first}),flush=True)
    purge=mutation_call(c,'ae_exec',{'code':"(function(){if(app.project.renderQueue.rendering)throw Error('Render active');app.purge(PurgeTarget.ALL_CACHES);return JSON.stringify({purged:'transient_AE_caches'});})();",'checkpoint_label':'before-locating-cache-purge','timeout_sec':120},out,150)
    write(out/'post-render-cache-purge.json',purge)
    paths=sorted(folder.glob('*.tif'))
    if [p.name for p in paths]!=['FRAME_'+str(i).zfill(5)+'.tif' for i in range(first,last)]:
        raise ValueError('Incomplete native frames')
    manifest={p.name:relay.file_sha(p) for p in paths};write(out/'native-frame-shas.json',manifest)
    archive=out/'NATIVE_TIFF_LOCATING.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        for name,digest in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Native archive differs')
    current(config)
    movie=acquisition_ab.encode_frames(folder,first,last-first,out/'GUIDED_B.mp4',width=3840,height=2160)
    receipt={'kind':'locating_trace_native_render','patch_sha':patch['patch_sha'],
             'trace_sha':patch['plan']['trace_sha'],'frames':[first,last],'native_canvas':[3840,2160,24],
             'native_audit_sha':relay.file_sha(config['native_audit']),
             'executed_template_sha':relay.file_sha(Path(config['project']).parent/'executed-template.jsx'),
             'workflow_sha':relay.file_sha(Path(__file__)),
             'director_version':patch['plan']['version'],'purge_between_chunks':config.get('purge_between_chunks',False),
             'chunks':chunks,'frame_manifest_sha':sha(manifest),'native_archive_sha':relay.file_sha(archive),
             'movie':movie,'project_sha':relay.file_sha(config['project']),
             'human_visual_review':'PENDING','independent_human_certified':False,'public_render_ready':False}
    write(out/'render-receipt.json',receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request');a=p.parse_args()
    result=render(read(a.request));print(json.dumps({'kind':result['kind'],'patch_sha':result['patch_sha']}))
