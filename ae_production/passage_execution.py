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


def audit_scene(client,comp_id,scene):
    code='''(function(){var cp=AEMCP.compById(%d),rows=[],last=0;
    for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);
      if(l instanceof TextLayer){var d=l.property('Source Text').value;rows.push({name:l.name,text:d.text,font:d.font,size:d.fontSize});}
      var ts=[l.transform.position,l.transform.opacity,l.transform.scale];
      for(var j=0;j<ts.length;j++)if(ts[j].numKeys)last=Math.max(last,ts[j].keyTime(ts[j].numKeys));
    }return JSON.stringify({rows:rows,last_key:last,width:cp.width,height:cp.height,fps:cp.frameRate,binding:JSON.parse(cp.comment)});})();''' % int(comp_id)
    native=json.loads(client.call('ae_exec',{'code':code})['content'])
    expected={'HEADER':(scene['heading'],'NotoSansSC-Regular',28),'QUESTION':(scene['stem'],'NotoSansSC-Regular',38),
              'SOURCE':(scene['source'],'Georgia',42),'JUDGMENT':(scene['screen'],'NotoSansSC-Regular',52)}
    expected.update({'OPTION_'+o['letter']:(o['text'],'NotoSansSC-Regular',30) for o in scene['options']})
    if {x['name'] for x in native['rows']}!=set(expected):raise ValueError('Unexpected native text')
    for x in native['rows']:
        if (x['text'].replace('\r','\n'),x['font'],x['size'])!=expected[x['name']]:raise ValueError('Native text/font drift')
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
            if prior['scene_sha']!=sha(scene) or file_sha(prior['video'])!=prior['video_sha']:
                raise ValueError('Existing head changed')
            continue
        if folder.exists():raise ValueError('Uncertain render exists; reconcile before continuing')
        folder.mkdir();frames=folder/'frames';frames.mkdir()
        comp=by_id[scene['segment_id']]['comp_id']
        write(folder/'native-audit.json',audit_scene(client,comp,scene))
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
        write(receipt,{'scene_sha':sha(scene),'segment_sha':scene['segment_sha'],'video':str(video),'video_sha':file_sha(video),
            'native_frames':[{'name':f.name,'sha':file_sha(f)} for f in files],
            'static_hold_verified':True,'hold_frame':str(hold),'hold_sha':file_sha(hold),
            'renderer':'native_AE_4s_motion_then_verified_static_hold','public_render_ready':False})
        print('Rendered native scene',scene['segment_id'],flush=True)


def build_master(client,plan,bundle,status_path,identities,mix,output):
    """Save a new editable native visual/audio master; captions stay in delivery ASS."""
    validate_plan(plan,bundle,read(status_path))
    if mix['plan_sha']!=plan['plan_sha'] or file_sha(mix['mix'])!=mix['mix_sha']:
        raise ValueError('Mix is stale')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve existing native master')
    by_id={s['segment_id']:s for s in identities['scenes']}
    for s in plan['scenes']:audit_scene(client,by_id[s['segment_id']]['comp_id'],s)
    request={'project':str(output),'previous_project':identities['project'],'plan_sha':plan['plan_sha'],
        'duration':plan['canvas']['duration'],'mix':mix['mix'],
        'scenes':[dict(s,comp_id=by_id[s['segment_id']]['comp_id']) for s in plan['scenes']]}
    code='var R='+json.dumps(request,ensure_ascii=False)+';'+'''
    (function(){
      if(!app.project.file||app.project.file.fsName.toLowerCase()!==(new File(R.previous_project)).fsName.toLowerCase())throw new Error('Active project changed');
      var dest=new File(R.project);if(dest.exists)throw new Error('Destination exists');
      app.project.save(dest);app.beginUndoGroup('Frozen passage master');
      try{
        var master=app.project.items.addComp('READING_D_VISUAL_MASTER',1920,1080,1,R.duration,24);
        master.comment=JSON.stringify({plan_sha:R.plan_sha,public_render_ready:false,captions:'bound delivery ASS, not in this composition'});
        for(var i=0;i<R.scenes.length;i++){
          var s=R.scenes[i],cp=AEMCP.compById(s.comp_id);cp.duration=s.duration;
          for(var j=1;j<=cp.numLayers;j++)cp.layer(j).outPoint=s.duration;
          cp.comment=JSON.stringify({segment_sha:s.segment_sha,plan_sha:R.plan_sha});
          var layer=master.layers.add(cp);layer.startTime=s.start;layer.inPoint=s.start;layer.outPoint=s.start+s.duration;
        }
        var audio=app.project.importFile(new ImportOptions(new File(R.mix)));
        master.layers.add(audio);app.project.save(dest);
        return JSON.stringify({project:dest.fsName,comp_id:master.id,duration:master.duration,num_layers:master.numLayers,plan_sha:R.plan_sha});
      }finally{app.endUndoGroup();}
    })();'''
    output.parent.mkdir(parents=True,exist_ok=True)
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':120,'checkpoint_label':'before-passage-master'},output.parent,150)
    native=json.loads(result['content'])
    if native['num_layers']!=len(plan['scenes'])+1 or abs(native['duration']-plan['canvas']['duration'])>1/48:
        raise ValueError('Native timeline incomplete')
    record={'native':native,'project_sha':file_sha(output),'public_render_ready':False}
    write(output.with_suffix('.json'),record);return record
