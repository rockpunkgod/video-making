"""Native source-attached motion heads; verified static holds reuse the final frame."""
import json
from pathlib import Path
import subprocess
import re
from video_contracts import read,write,sha
from video_contracts.passage import require_current
from creative_os.hero import file_sha
from creative_os.passage_video import validate_plan
from .execution import mutation_call


def reuse_unchanged_heads(previous,current,previous_root,output,template_sha):
    """New receipts attest pixel-equivalent scenes; old receipts/media stay intact.

    Only global envelope bindings change. Template, literal nodes, event order,
    scene projection and both rendered media hashes must still match exactly.
    """
    for request in (previous,current):
        if request['presentation_sha']!=sha({'template':template_sha,
                'direction':request['direction']['direction_sha'],'orders':request['motion_orders']}):
            raise ValueError('Cannot reuse a different or unbound native template')
    by_id={s['segment_id']:s for s in previous['scenes']};reused=[]
    for scene in current['scenes']:
        sid=scene['segment_id']
        if (sid not in by_id or scene!=by_id[sid]
                or previous['direction']['scenes'][sid]!=current['direction']['scenes'][sid]
                or previous['motion_orders'].get(sid)!=current['motion_orders'].get(sid)):
            continue
        source=Path(previous_root)/sid/'receipt.json';head=read(source)
        if (head['scene_sha']!=sha(scene) or head['presentation_sha']!=previous['presentation_sha']
                or head['direction_sha']!=previous['direction']['direction_sha']
                or not head['static_hold_verified']
                or file_sha(head['video'])!=head['video_sha'] or file_sha(head['hold_frame'])!=head['hold_sha']):
            raise ValueError('Cannot reuse changed native media')
        dest=Path(output)/sid/'receipt.json'
        if dest.parent.exists():raise ValueError('Preserve prior reuse receipt')
        write(dest,dict(head,presentation_sha=current['presentation_sha'],
            direction_sha=current['direction']['direction_sha'],
            reuse_proof={'receipt':str(source.resolve()),'receipt_sha':file_sha(source),
                        'template_sha':template_sha,'scene_direction_sha':sha(current['direction']['scenes'][sid]),
                        'previous_presentation_sha':previous['presentation_sha']},
            renderer='native_AE_scene_equivalence_reuse'))
        reused.append(sid)
    return reused


def audit_scene(client,comp_id,scene,direction=None):
    code='''(function(){var cp=AEMCP.compById(%d),rows=[],last=0;
    for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);
      if(l instanceof TextLayer){var d=l.property('Source Text').value,b=l.sourceRectAtTime(3.5,false);rows.push({name:l.name,text:d.text,font:d.font,size:d.fontSize,width:b.width,height:b.height,position:l.transform.position.valueAtTime(3.5,false)});}
      var ts=[l.transform.position,l.transform.opacity,l.transform.scale];
      for(var j=0;j<ts.length;j++)if(ts[j].numKeys)last=Math.max(last,ts[j].keyTime(ts[j].numKeys));
    }return JSON.stringify({rows:rows,last_key:last,width:cp.width,height:cp.height,fps:cp.frameRate,binding:JSON.parse(cp.comment)});})();''' % int(comp_id)
    native=json.loads(client.call('ae_exec',{'code':code})['content'])
    expected={'HEADER':(scene['heading'],'NotoSansSC-Regular',28),'QUESTION':(scene['stem'],'NotoSansSC-Regular',38),
              'SOURCE':(scene['source'],'Georgia',42),'JUDGMENT':(scene['screen'],'NotoSansSC-Regular',52)}
    expected.update({'OPTION_'+o['letter']:(o['text'],'NotoSansSC-Regular',30) for o in scene['options']})
    if direction is not None:
        expected={n['name']:(n['text'],n['font'],n['size']) for n in direction['nodes'] if n['type']=='text'}
    if {x['name'] for x in native['rows']}!=set(expected):raise ValueError('Unexpected native text')
    for x in native['rows']:
        if (x['text'].replace('\r','\n'),x['font'],x['size'])!=expected[x['name']]:raise ValueError('Native text/font drift')
        if direction is not None:
            node=next(n for n in direction['nodes'] if n['name']==x['name'])
            if (abs(x['position'][0]-node['x'])>1 or abs(x['position'][1]-node['y'])>1
                    or x['width']>node['w']+12 or x['position'][1]+x['height']>941):
                raise ValueError('Native readable bounds drift: '+scene['segment_id']+'/'+x['name'])
    if (native['width'],native['height'],native['fps'])!=(1920,1080,24) or native['last_key']>3.5:
        raise ValueError('Profile or static-hold assumption invalid')
    if native['binding']['segment_sha']!=scene['segment_sha']:raise ValueError('Native source binding drift')
    return native


def render_heads(client,request,bundle,status_path,identities,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    by_id={i['segment_id']:i for i in identities['scenes']}
    for scene in request['scenes']:
        require_current(bundle,read(status_path))
        folder=out/scene['segment_id'];receipt=folder/'receipt.json'
        if receipt.exists():
            prior=read(receipt)
            if (prior['scene_sha']!=sha(scene) or file_sha(prior['video'])!=prior['video_sha']
                    or prior.get('presentation_sha')!=request.get('presentation_sha')):
                raise ValueError('Existing head changed')
            continue
        if folder.exists():raise ValueError('Uncertain render exists; reconcile before continuing')
        folder.mkdir();frames=folder/'frames';frames.mkdir()
        comp=by_id[scene['segment_id']]['comp_id']
        native_audit=audit_scene(client,comp,scene,request.get('direction',{}).get('scenes',{}).get(scene['segment_id']))
        if native_audit['binding'].get('presentation_sha')!=request.get('presentation_sha'):
            raise ValueError('Native presentation binding changed')
        write(folder/'native-audit.json',native_audit)
        code='''(function(){var cp=AEMCP.compById(%d);
        for(var i=1;i<=app.project.renderQueue.numItems;i++){var x=app.project.renderQueue.item(i);if(x.render&&x.status===RQItemStatus.QUEUED)throw new Error('Queued conflict');}
        var rq=app.project.renderQueue.items.add(cp),om=rq.outputModule(1),preset=null;
        for(var j=0;j<om.templates.length;j++)if(om.templates[j].indexOf('TIFF')!==-1){preset=om.templates[j];break;}
        if(!preset)throw new Error('TIFF preset missing');om.applyTemplate(preset);om.file=new File(%s);
        rq.timeSpanStart=0;rq.timeSpanDuration=4;app.project.save();app.project.renderQueue.render();
        var done=rq.status===RQItemStatus.DONE;app.purge(PurgeTarget.ALL_CACHES);
        return JSON.stringify({ok:done,preset:preset});})();''' % (int(comp),json.dumps((frames/'FRAME_[#####].tif').resolve().as_posix()))
        result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':180,'checkpoint_label':'before-reading-scene-head'},folder,200)
        write(folder/'render-result.json',result)
        if not json.loads(result['content'])['ok']:raise ValueError('Native head incomplete')
        files=sorted(frames.glob('*.tif'))
        if len(files)!=96:raise ValueError('Native frame count mismatch')
        matches=[re.fullmatch(r'(.*?)(\d+)(\.[^.]+)',f.name) for f in files]
        if not all(matches):raise ValueError('Unexpected frame filename')
        first=matches[0];start=int(first[2]);pattern=frames/(first[1]+'%0'+str(len(first[2]))+'d'+first[3])
        if [int(m[2]) for m in matches]!=list(range(start,start+96)):raise ValueError('Native frame gap')
        video=(folder/'head.mp4').resolve()
        subprocess.run(['ffmpeg','-v','error','-n','-framerate','24','-start_number',str(start),'-i',str(pattern),
            '-frames:v','96','-an','-c:v','libx264','-crf','16','-pix_fmt','yuv420p',str(video)],check=True)
        # A real second native hold frame proves the steady state rather than assuming a freeze.
        hold=(folder/'hold.png').resolve()
        client.call('ae_exec',{'code':'(function(){AEMCP.compById('+str(comp)+').saveFrameToPng(6,new File('+json.dumps(hold.as_posix())+'));return JSON.stringify({ok:true});})();'})
        from PIL import Image,ImageChops
        if ImageChops.difference(Image.open(files[-1]).convert('RGB'),Image.open(hold).convert('RGB')).getbbox():
            raise ValueError('Native scene changes after motion head')
        write(receipt,{'scene_sha':sha(scene),'segment_sha':scene['segment_sha'],'presentation_sha':request.get('presentation_sha'),'video':str(video),'video_sha':file_sha(video),
            'direction_sha':native_audit['binding'].get('direction_sha'),
            'native_frames':[{'name':f.name,'sha':file_sha(f)} for f in files],
            'static_hold_verified':True,'hold_frame':str(hold),'hold_sha':file_sha(hold),
            'renderer':'native_AE_4s_motion_then_verified_static_hold','public_render_ready':False})
        print('Rendered native scene',scene['segment_id'],flush=True)


def build_master(client,plan,bundle,status_path,identities,mix,output,motion=None,direction=None):
    """Save a new editable native visual/audio master; captions stay in delivery ASS."""
    validate_plan(plan,bundle,read(status_path))
    if direction is not None:
        from creative_os.passage_director import validate_direction
        validate_direction(direction,plan,bundle)
        if identities.get('direction_sha')!=direction['direction_sha']:
            raise ValueError('Native project uses a different direction')
    if motion is not None and (motion['plan_sha']!=plan['plan_sha']
            or motion['motion_sha']!=sha({k:v for k,v in motion.items() if k!='motion_sha'})):
        raise ValueError('Native master motion is stale')
    if mix['plan_sha']!=plan['plan_sha'] or file_sha(mix['mix'])!=mix['mix_sha']:
        raise ValueError('Mix is stale')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve existing native master')
    by_id={s['segment_id']:s for s in identities['scenes']}
    for s in plan['scenes']:audit_scene(client,by_id[s['segment_id']]['comp_id'],s,
                                      direction['scenes'][s['segment_id']] if direction else None)
    request={'project':str(output),'previous_project':identities['project'],'plan_sha':plan['plan_sha'],
        'duration':plan['canvas']['duration'],'mix':mix['mix'],'motion':motion,
        'scenes':[dict(s,comp_id=by_id[s['segment_id']]['comp_id']) for s in plan['scenes']]}
    code='var R='+json.dumps(request,ensure_ascii=False)+';'+'''
    (function(){
      if(!app.project.file||app.project.file.fsName.toLowerCase()!==(new File(R.previous_project)).fsName.toLowerCase())throw new Error('Active project changed');
      var dest=new File(R.project);if(dest.exists)throw new Error('Destination exists');
      app.project.save(dest);app.beginUndoGroup('Frozen passage master');
      try{
        var master=app.project.items.addComp('READING_D_VISUAL_MASTER',1920,1080,1,R.duration,24),probes=[];
        master.comment=JSON.stringify({plan_sha:R.plan_sha,motion_sha:R.motion?R.motion.motion_sha:null,public_render_ready:false,captions:'bound delivery ASS, not in this composition'});
        for(var i=0;i<R.scenes.length;i++){
          var s=R.scenes[i],cp=AEMCP.compById(s.comp_id);cp.duration=s.duration;
          for(var j=1;j<=cp.numLayers;j++)cp.layer(j).outPoint=s.duration;
          var binding=JSON.parse(cp.comment);binding.segment_sha=s.segment_sha;binding.plan_sha=R.plan_sha;cp.comment=JSON.stringify(binding);
          var layer=master.layers.add(cp);layer.startTime=s.start;layer.inPoint=s.start;layer.outPoint=s.start+s.duration;
          if(R.motion){
            layer.timeRemapEnabled=true;var remap=layer.property('ADBE Time Remapping');
            // Removing the last key disables Time Remap in AE; keep one live key.
            while(remap.numKeys>1)remap.removeKey(remap.numKeys);
            var firstTime=remap.keyTime(1);remap.setValueAtTime(s.start,0);
            if(Math.abs(firstTime-s.start)>.000001)remap.removeKey(remap.nearestKeyIndex(firstTime));
            var events=R.motion.scenes[s.segment_id],delay=0;
            for(var e=0;e<events.length;e++){
              var ev=events[e],holdAt=s.start+ev.native_start+delay-1/24;
              remap.setValueAtTime(holdAt,ev.native_start-1/24);
              remap.setInterpolationTypeAtKey(remap.nearestKeyIndex(holdAt),KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.HOLD);
              remap.setValueAtTime(s.start+ev.start,ev.native_start);
              // AE inherits HOLD from the previous key unless reset explicitly.
              remap.setInterpolationTypeAtKey(remap.nearestKeyIndex(s.start+ev.start),KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.LINEAR);
              delay=ev.start-ev.native_start;
            }
            var last=events.length?events[events.length-1]:null;
            var endAt=s.start+(last?last.start+.5:.5),endNative=last?last.native_start+.5:.5;
            remap.setValueAtTime(endAt,endNative);
            remap.setInterpolationTypeAtKey(remap.nearestKeyIndex(endAt),KeyframeInterpolationType.LINEAR,KeyframeInterpolationType.HOLD);
            layer.outPoint=s.start+s.duration;
            for(var probe=0;probe<events.length;probe++){
              var event=events[probe],actual=remap.valueAtTime(s.start+event.start+.25,false),expected=event.native_start+.25;
              if(Math.abs(actual-expected)>1/48)throw new Error('Native motion clock drift: '+s.segment_id);
              probes.push({segment_id:s.segment_id,purpose:event.purpose,actual:actual,expected:expected});
            }
          }
        }
        var audio=app.project.importFile(new ImportOptions(new File(R.mix)));
        master.layers.add(audio);app.project.save(dest);
        return JSON.stringify({project:dest.fsName,comp_id:master.id,duration:master.duration,num_layers:master.numLayers,plan_sha:R.plan_sha,motion_clock_probes:probes});
      }finally{app.endUndoGroup();}
    })();'''
    output.parent.mkdir(parents=True,exist_ok=True)
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':120,'checkpoint_label':'before-passage-master'},output.parent,150)
    native=json.loads(result['content'])
    if native['num_layers']!=len(plan['scenes'])+1 or abs(native['duration']-plan['canvas']['duration'])>1/48:
        raise ValueError('Native timeline incomplete')
    record={'native':native,'project_sha':file_sha(output),'public_render_ready':False}
    write(output.with_suffix('.json'),record);return record
