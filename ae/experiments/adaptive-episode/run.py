"""Small adapter over the existing Cognitive POV executor and AE bridge.

Authored direction and source geometry arrive from explicit private inputs.
No solver, Registry, English parsing, new motion library or public approval.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from video_contracts import read,write,sha,pointer,ROOT
from content_os.showcase import file_sha
from creative_os.episode import validate_episode
from ae_production.bridge import JunkdogeClient
from ae_production.execution import mutation_call
from ae_production.memory_guard import monitor_existing_render,available_memory


def current(folder):
    r=read(folder/'native-request.json');s=r['spec']
    if s['spec_sha']!=sha({k:v for k,v in s.items() if k!='spec_sha'}) or r['public_render_ready'] is not False:
        raise ValueError('Changed spec or invalid internal release state')
    if any(file_sha(p)!=digest for p,digest in r['input_files'].items()):
        raise ValueError('Authored source, voice, font or template changed')
    episode=read(r['episode_plan']);statuses={k:read(v) for k,v in r['statuses'].items()}
    if validate_episode(episode,statuses)['engineering_status']!='PASS':
        raise ValueError('Current frozen episode dependency invalid')
    bundles={b['asset_id']:b for q in episode['questions'] for b in q['package']['source_items']}
    ids=set()
    for n in s['nodes']:
        if n['node_id'] in ids:raise ValueError('Duplicate native object identity')
        ids.add(n['node_id'])
        for ref in n['source_refs']:
            b=bundles[ref['asset_id']];value=pointer(b,ref['pointer'])
            if sha(value)!=ref['sha']:raise ValueError('Changed native source reference')
            if n['node_id'].startswith('source:') and value[n['start']:n['end']]!=n['text']:
                raise ValueError('Native source text changed')
    for voice in r['voices']:
        if file_sha(voice['path'])!=voice['sha256']:raise ValueError('Bound voice changed')
    return r


def client():
    c=JunkdogeClient();c.initialize();c.call('ae_skillUse',{'name':'ae-execution-guide'});return c


def build(folder):
    r=current(folder);c=client();target=Path(r['project'])
    if target.exists() or (folder/'SESSION_START.aep').exists():raise FileExistsError('Preserve revisions; inspect prior attempt')
    before=json.loads(c.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty});'})['content'])
    previous_sha=file_sha(before['path']) if before['path'] else None
    write(folder/'session-before.json',{'before':before,'previous_sha':previous_sha})
    code='app.project.save(new File('+json.dumps((folder/'SESSION_START.aep').as_posix())+'));app.newProject();'
    code+='var COGNITIVE_REQUEST='+json.dumps((folder/'native-request.json').as_posix())+';\n'+Path(r['template']).read_text(encoding='utf-8')
    result=mutation_call(c,'ae_exec',{'code':code,'timeout_sec':600,'checkpoint_label':'before-adaptive-episode'},folder,630)
    write(folder/'build-result.json',result);identity=json.loads(result['content'])
    if identity.get('spec_sha')!=r['spec']['spec_sha'] or not identity.get('ok'):raise ValueError('Native build identity uncertain; inspect host')
    write(folder/'native-identity.json',identity);return identity


def audit(folder):
    r=current(folder);identity=read(folder/'native-identity.json');c=client()
    code='''(function(){var cp=AEMCP.compById(COMP),a=[];for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.property('Source Text')){var d=l.property('Source Text').value;a.push({name:l.name,text:d.text,font:d.font,comment:l.comment});}}return JSON.stringify({project:app.project.file.fsName,comp_id:cp.id,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration,comment:cp.comment,objects:a});})();'''.replace('COMP',str(identity['comp_id']))
    result=json.loads(c.call('ae_exec',{'code':code})['content']);write(folder/'native-audit.json',result)
    duration=r['spec']['canvas']['duration']
    if ([result[k] for k in ('width','height','fps')]!=[3840,2160,24]
            or abs(result['duration']-duration)>0.000001
            or round(result['duration']*24)!=round(duration*24)):
        raise ValueError('Native canvas/timing mismatch')
    if Path(result['project']).resolve()!=Path(r['project']).resolve() or json.loads(result['comment'])['spec_sha']!=r['spec']['spec_sha']:
        raise ValueError('Wrong native project or frozen spec')
    native={n['name']:n for n in result['objects']}
    for n in r['spec']['nodes']:
        value=native[n['node_id']]
        # AE stores authored line breaks as CR; lexical text stays exact.
        if value['text'].replace('\r\n','\n').replace('\r','\n')!=n['text'] or value['font']!=n['font']:
            raise ValueError('Native glyph or font changed: '+n['node_id'])
        comment=json.loads(value['comment'])
        if comment['origin_object_id']!=n['origin_object_id'] or comment['source_refs']!=n['source_refs']:
            raise ValueError('Native object source lineage changed')
    # Audit the actual motion and caption protection, not just the text manifest.
    code='''(function(){var f=new File(REQUEST);f.encoding='UTF-8';f.open('r');var s=JSON.parse(f.read()).spec;f.close();var cp=AEMCP.compById(COMP),errors=[],checked=0;
      function equal(a,b){if(a instanceof Array){if(!(b instanceof Array)||a.length!==b.length)return false;for(var j=0;j<a.length;j++)if(!equal(a[j],b[j]))return false;return true;}return Math.abs(a-b)<0.0001;}
      function verify(p,rows,name,screenPosition){if(!p||p.numKeys!==rows.length){errors.push(name+': key count');return;}for(var k=1;k<=p.numKeys;k++){var actual=p.keyValue(k),expected=rows[k-1][1];if(p.propertyValueType===PropertyValueType.COLOR&&actual.length===4&&expected.length===3&&Math.abs(actual[3]-1)<0.0001)actual=actual.slice(0,3);if(screenPosition&&actual instanceof Array&&expected instanceof Array&&actual.length===3&&expected.length===2&&Math.abs(actual[2])<0.0001)actual=actual.slice(0,2);if(Math.abs(p.keyTime(k)-rows[k-1][0])>0.0001||!equal(actual,expected))errors.push(name+': key '+k);checked++;}}
      verify(cp.layer('COGNITIVE_ATTENTION').transform.position,s.camera.position,'camera');
      for(var i=0;i<s.nodes.length;i++){var n=s.nodes[i],l=cp.layer(n.node_id);if(Math.abs(l.inPoint-n.in_point)>0.0001||Math.abs(l.outPoint-n.out_point)>0.0001)errors.push(n.node_id+': lifetime');for(var name in n.tracks){var p=null;if(name==='position'||name==='scale'||name==='opacity')p=l.transform[name];else if(name==='color')p=l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');else continue;verify(p,n.tracks[name],n.node_id+': '+name,name==='position'&&n.space==='screen'&&l.threeDLayer===false);}}
      if(s.inline_captions){var band=cp.layer('CAPTION_PAPER'),top=band.transform.position.value[1]-band.source.height/2;if(s.caption_safe_top!==undefined&&Math.abs(top-s.caption_safe_top)>0.001)errors.push('caption safe area');for(var i=0;i<s.nodes.length;i++){var n=s.nodes[i],l=cp.layer(n.node_id);if(n.node_id.indexOf('caption:')===0&&l.index>band.index)errors.push('caption hidden behind band');if(n.node_id.indexOf('source:')===0&&l.index<band.index)errors.push('source above caption protection');}}
      return JSON.stringify({checked_keys:checked,errors:errors});})();'''
    code=code.replace('REQUEST',json.dumps((folder/'native-request.json').as_posix())).replace('COMP',str(identity['comp_id']))
    motion=json.loads(c.call('ae_exec',{'code':code,'timeout_sec':120},timeout=150)['content'])
    write(folder/'native-motion-audit.json',motion)
    if motion['errors']:raise ValueError('Native motion/timing/caption audit failed: '+str(motion['errors'][:3]))
    return {'native_objects':len(r['spec']['nodes']),'canvas':'4K24','source_and_fonts':'PASS'}


def preview(folder):
    r=current(folder);identity=read(folder/'native-identity.json');c=client();out=folder/'previews';out.mkdir(exist_ok=True)
    direction=read(folder/'DIRECTION_REALIZED.json');scenes={v['scene_id']:v for v in direction['scenes']}
    points=[('a-entry',3),('a-options',2),('a-p1',4),('a-p3',5),('a-p4',5),('a-p5',5),
            ('a-connect',1),('a-connect-replay',4),('a-payoff',1),('b-entry',3),
            ('b-p2',5),('b-p4',5),('b-p3',6),('b-p1',6),('b-scope',5),('b-payoff',1)]
    times=[min(scenes[sid]['time_range'][0]+offset,scenes[sid]['time_range'][1]-1/24) for sid,offset in points]
    result=c.call('ae_previewFrame',{'comp_id':str(identity['comp_id']),
        'times':times,
        'layout':'grid','grid_max_side':2048,'out_dir':str(out)},timeout=220)
    write(folder/'preview-receipt.json',result);return {'preview':str(out)}


def render(folder,pid,hwnd,batch_size=96):
    if not isinstance(batch_size,int) or isinstance(batch_size,bool) or not 1<=batch_size<=240:
        raise ValueError('Batch size must be 1–240 frames')
    r=current(folder);audit(folder);identity=read(folder/'native-identity.json');c=client()
    frames=Path(r['scratch']).resolve()
    if not frames.is_relative_to(Path('G:/AdobeCache/video-os').resolve()):raise ValueError('Explicit owned scratch root required')
    frames.mkdir(parents=True,exist_ok=True);total=round(r['spec']['canvas']['duration']*24)
    existing=sorted(frames.glob('FRAME_*.tif'));cursor=len(existing)
    if [p.name for p in existing]!=[f'FRAME_{i:05d}.tif' for i in range(cursor)]:raise ValueError('Inspect incomplete transfer before resume')
    receipts=[]
    for p in sorted(folder.glob('transfer-*.json')):
        receipt=read(p)
        if receipt['spec_sha']!=r['spec']['spec_sha']:raise ValueError('Resume spec changed')
        receipts.append(receipt)
    if sum(x['count'] for x in receipts)!=cursor:raise ValueError('Incomplete transfer receipt')
    if cursor:
        verify_rendered_frames(folder,{'scratch':str(frames),'frames':cursor,
            'spec_sha':r['spec']['spec_sha'],'transfers':[sha(x) for x in receipts]})
    while cursor<total:
        current(folder)
        if available_memory()<2**30:raise RuntimeError('Below user one GiB reserve')
        count=min(batch_size,total-cursor);part=frames/('batch-'+str(cursor))
        if part.exists():raise FileExistsError('Inspect uncertain native batch, never repeat blindly')
        part.mkdir()
        code='''(function(){var cp=AEMCP.compById(COMP);if(app.project.renderQueue.rendering||JSON.parse(cp.comment).spec_sha!==SPEC)throw Error('Wrong or busy native comp');for(var i=1;i<=app.project.renderQueue.numItems;i++){var old=app.project.renderQueue.item(i);if(old.render&&old.status===RQItemStatus.QUEUED)throw Error('Unrelated queued render');}app.purge(PurgeTarget.ALL_CACHES);var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var j=0;j<o.templates.length;j++)if(o.templates[j].indexOf('TIFF')!==-1){preset=o.templates[j];break;}if(!preset)throw Error('TIFF unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=COUNT/24;app.setMultiFrameRenderingConfig(true,100);app.project.renderQueue.render();var done=q.status===RQItemStatus.DONE;if(done)q.remove();app.project.save();return JSON.stringify({done:done,start:START,count:COUNT,comp_id:cp.id,preset:preset});})();'''
        for k,v in {'COMP':str(identity['comp_id']),'SPEC':json.dumps(r['spec']['spec_sha']),
          'DEST':json.dumps((part/'NATIVE_[#####].tif').as_posix()),'START':str(cursor/24),'COUNT':str(count)}.items():code=code.replace(k,v)
        with monitor_existing_render(pid,hwnd,minimum_free_gib=1) as memory:
            result=mutation_call(c,'ae_exec',{'code':code,'timeout_sec':600},folder,630)
        native=json.loads(result['content']);paths=sorted(part.glob('*.tif'))
        write(folder/f'native-batch-{cursor:05d}.json',{'native':native,'memory':memory,'spec_sha':r['spec']['spec_sha']})
        if not native['done'] or len(paths)!=count:raise ValueError('Native batch incomplete; inspect before resuming')
        checks={}
        for i,path in enumerate(paths):
            target=frames/f'FRAME_{cursor+i:05d}.tif'
            if target.exists() or path.resolve().parent!=part.resolve() or target.resolve().parent!=frames:
                raise ValueError('Unsafe or duplicate frame transfer')
            checks[target.name]=file_sha(path);path.rename(target)
        receipt={'spec_sha':r['spec']['spec_sha'],'start_frame':cursor,'count':count,'frames':checks,'memory':memory}
        write(folder/f'transfer-{cursor:05d}.json',receipt);receipts.append(receipt)
        cursor+=count;print(json.dumps({'native_frames':cursor,'total':total}),flush=True)
    write(folder/'NATIVE_RENDER_RECEIPT.json',{'spec_sha':r['spec']['spec_sha'],'frames':total,
      'duration':total/24,'canvas':[3840,2160,24],'scratch':str(frames),'transfers':[sha(x) for x in receipts],
      'native_project':r['project'],'project_sha':file_sha(r['project']),'human_taste_review':'PENDING','public_render_ready':False})
    return {'native_frames':total}


def package(folder):
    r=current(folder);receipt=read(folder/'NATIVE_RENDER_RECEIPT.json');frames=Path(receipt['scratch']);target=folder/'ADAPTIVE_EPISODE_PICTURE_4K.mp4'
    if target.exists() or receipt['spec_sha']!=r['spec']['spec_sha']:raise ValueError('New picture revision required')
    if (receipt['frames']!=round(r['spec']['canvas']['duration']*24)
            or receipt['canvas']!=[3840,2160,24]
            or abs(receipt['duration']-receipt['frames']/24)>0.000001
            or Path(receipt['native_project']).resolve()!=Path(r['project']).resolve()
            or receipt['project_sha']!=file_sha(r['project'])):
        raise ValueError('Native render no longer binds the full current episode')
    verify_rendered_frames(folder,receipt)
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','24','-start_number','0','-i',str(frames/'FRAME_%05d.tif'),
      '-frames:v',str(receipt['frames']),'-an','-vf','scale=out_color_matrix=bt709:out_range=tv',
      '-c:v','libx264','-preset','fast','-crf','16','-threads','6','-pix_fmt','yuv420p',
      '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
      '-x264-params','colorprim=bt709:transfer=bt709:colormatrix=bt709',
      '-movflags','+write_colr',str(target)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))['streams'][0]
    if [probe['width'],probe['height'],probe['r_frame_rate'],int(probe['nb_frames'])]!=[3840,2160,'24/1',receipt['frames']]:raise ValueError('Encoded picture profile changed')
    # Inspect a decoded frame: stream summaries can omit primaries/transfer.
    color=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
      '-read_intervals','%+#1','-show_frames','-show_entries',
      'frame=color_range,color_space,color_primaries,color_transfer','-of','json',str(target)]))['frames'][0]
    if [color.get(k) for k in ('color_range','color_space','color_primaries','color_transfer')]!=['tv','bt709','bt709','bt709']:
        raise ValueError('Encoded picture Rec.709 color binding missing')
    write(folder/'PICTURE_RECEIPT.json',{'native_receipt_sha':sha(receipt),'output':str(target),'output_sha':file_sha(target),
      'duration':receipt['duration'],'frames':receipt['frames'],'full_decode':'PASS',
      'color_policy':'RGB_to_limited_BT709_with_explicit_primaries_transfer_and_matrix',
      'decoded_color':{k:color[k] for k in ('color_range','color_space','color_primaries','color_transfer')},
      'public_render_ready':False})
    return {'picture':str(target),'frames':receipt['frames']}


def verify_rendered_frames(folder,receipt):
    """Check the actual native frame bytes again before encoding the final picture."""
    frames=Path(receipt['scratch']).resolve();count=receipt['frames']
    if not isinstance(count,int) or isinstance(count,bool) or count<=0:
        raise ValueError('Invalid native frame count')
    actual=sorted(p.name for p in frames.glob('FRAME_*.tif'))
    expected=[f'FRAME_{i:05d}.tif' for i in range(count)]
    if actual!=expected:raise ValueError('Missing or unexpected native frame')
    cursor=0;transfers=[]
    for path in sorted(folder.glob('transfer-*.json')):
        transfer=read(path)
        if (not isinstance(transfer['count'],int) or isinstance(transfer['count'],bool)
                or not 0<transfer['count']<=count-cursor):
            raise ValueError('Invalid native transfer count')
        if transfer['spec_sha']!=receipt['spec_sha'] or transfer['start_frame']!=cursor:
            raise ValueError('Native transfer binding or order changed')
        names=[f'FRAME_{i:05d}.tif' for i in range(cursor,cursor+transfer['count'])]
        if sorted(transfer['frames'])!=names:
            raise ValueError('Native transfer coverage changed')
        for name in names:
            if file_sha(frames/name)!=transfer['frames'][name]:
                raise ValueError('Native frame bytes changed')
        cursor+=transfer['count'];transfers.append(sha(transfer))
    if cursor!=count or transfers!=receipt['transfers']:
        raise ValueError('Native transfer receipt incomplete or changed')
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('build','audit','preview','render','package'));p.add_argument('folder')
    p.add_argument('--pid',type=int);p.add_argument('--hwnd',type=int);p.add_argument('--batch-size',type=int,default=96)
    a=p.parse_args();folder=Path(a.folder).resolve()
    if not folder.is_relative_to(ROOT/'local-data'):raise ValueError('Real assets belong in ignored local-data')
    result=render(folder,a.pid,a.hwnd,a.batch_size) if a.operation=='render' else globals()[a.operation](folder)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
