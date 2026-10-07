"""Native Cognitive Shot execution; AE produces motion only, PR finishes it."""
import json
import re
import subprocess
from pathlib import Path

from video_contracts import ROOT, read, write
from creative_os.cognitive_pov import validate_spec
from creative_os.hero import file_sha
from .execution import mutation_call

TEMPLATE=ROOT/'ae/templates/cognitive-pov-v0.1.jsx'


def validate_inputs(request):
    spec=read(request['spec'])
    validate_spec(spec,read(request['application']),read(request['bundle']),read(request['status']),
        read(request['package']),read(request['manifest']),
        {k:read(v) for k,v in request['statuses'].items()},
        read(request['full_delivery']),read(request['excerpt']))
    return spec


def build(client, request):
    spec=validate_inputs(request); out=Path(request['output']).resolve();out.mkdir(parents=True,exist_ok=True)
    native=dict(spec=spec,project=str(Path(request['project']).resolve()))
    write(out/'build-request.json',native)
    client.call('ae_skillUse',{'name':'ae-execution-guide'})
    code='var COGNITIVE_REQUEST='+json.dumps((out/'build-request.json').as_posix())+';\n'+TEMPLATE.read_text(encoding='utf-8')
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':180,
        'checkpoint_label':'before-swiss-cognitive-pov'},out,210)
    write(out/'build-result.json',result); identity=json.loads(result['content'])
    if identity.get('spec_sha')!=spec['spec_sha'] or not identity.get('ok'):
        raise ValueError('Native Cognitive Shot identity missing')
    write(out/'identity.json',identity);return identity


def audit(client, request, comp_id):
    spec=validate_inputs(request)
    code='''(function(){var cp=AEMCP.compById(%d),rows=[];function vals(p){var a=[];for(var k=1;k<=p.numKeys;k++)a.push([p.keyTime(k),p.keyValue(k)]);return a;}for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.name==='SPEC_BINDING'||l.name==='PAPER'||l.name==='CAPTION_PAPER'||l.name==='COGNITIVE_CAMERA'||l.name==='COGNITIVE_ATTENTION')continue;var r={id:l.name,threeD:l.threeDLayer,inPoint:l.inPoint,outPoint:l.outPoint,position:l.transform.position.valueAtTime(0,false),positionKeys:vals(l.transform.position),opacityKeys:vals(l.transform.opacity),blurKeys:[]};if(l instanceof TextLayer){var d=l.property('Source Text').value;r.text=d.text;r.font=d.font;r.size=d.fontSize;var b=l.sourceRectAtTime(18,false);r.bounds={left:b.left,top:b.top,width:b.width,height:b.height};}var fx=l.property('ADBE Effect Parade');if(fx&&fx.numProperties)r.blurKeys=vals(fx.property(1).property(1));rows.push(r);}return JSON.stringify({binding:JSON.parse(cp.comment),rows:rows,camera:vals(cp.layer('COGNITIVE_ATTENTION').transform.position),zoom:cp.layer('COGNITIVE_CAMERA').property('ADBE Camera Options Group').property('ADBE Camera Zoom').value,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration});})();'''%int(comp_id)
    result=json.loads(client.call('ae_exec',{'code':code})['content'])
    write(Path(request['output'])/'native-audit.json',result)
    if (result['binding']['spec_sha']!=spec['spec_sha'] or
            (result['width'],result['height'],result['fps'],result['duration'])!=(1920,1080,24,20)):
        raise ValueError('Native composition binding/profile changed')
    expected={n['node_id']:n for n in spec['nodes']}
    if set(expected)!={r['id'] for r in result['rows']}:raise ValueError('Native node set changed')
    def close(a,b):
        if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
        return isinstance(a,(int,float)) and isinstance(b,(int,float)) and abs(a-b)<1e-4
    def track(a,b):return len(a)==len(b) and all(abs(x[0]-y[0])<1/(24*1024) and close(x[1],y[1]) for x,y in zip(a,b))
    for r in result['rows']:
        n=expected[r['id']]
        if n['kind']=='text' and (r['text'].replace('\r','\n')!=n['text'] or r['font']!=n['font'] or r['size']!=n['size']):
            raise ValueError('Native copy/font drift: '+r['id'])
        if (r['threeD']!=(n['space']=='world') or abs(r['inPoint']-n.get('in_point',0))>1e-4
                or abs(r['outPoint']-n.get('out_point',20))>1e-4):raise ValueError('Native source presence changed')
        if not close(r['position'] if n['space']=='world' else r['position'][:2],
                     n['position'] if n['space']=='world' else n['position'][:2]):
            raise ValueError('Native initial semantic geometry changed: '+r['id']+' '+str(r['position'])+' versus '+str(n['position']))
        for field,key in [('positionKeys','position'),('opacityKeys','opacity'),('blurKeys','blur')]:
            if not track(r[field],n['tracks'].get(key,[])):raise ValueError('Native semantic motion changed: '+r['id']+'/'+key)
        if n['kind']=='text' and n['space']=='screen' and (n['position'][0]+r['bounds']['left']<80 or
                n['position'][0]+r['bounds']['left']+r['bounds']['width']>1840):
            raise ValueError('Native Chinese copy overflows the safe width')
    if result['zoom']!=spec['camera']['zoom'] or not track(result['camera'],spec['camera']['position']):
        raise ValueError('Native attention camera changed')
    write(Path(request['output'])/'native-audit.json',result);return result


def render(client, request, comp_id):
    spec=validate_inputs(request);out=Path(request['output']).resolve();audit(client,request,comp_id)
    frames=out/'native-tiff';video=out/'COGNITIVE_SHOT.mp4'
    if frames.exists() or video.exists():raise ValueError('Existing native render; reconcile before continuing')
    frames.mkdir()
    code='''(function(){for(var i=1;i<=app.project.renderQueue.numItems;i++){var q=app.project.renderQueue.item(i);if(q.render&&q.status===RQItemStatus.QUEUED)throw new Error('Queued render conflict');}var cp=AEMCP.compById(%d),rq=app.project.renderQueue.items.add(cp),om=rq.outputModule(1),preset=null;for(var j=0;j<om.templates.length;j++)if(om.templates[j].indexOf('TIFF')!==-1){preset=om.templates[j];break;}if(!preset){rq.remove();throw new Error('Native TIFF preset unavailable');}om.applyTemplate(preset);om.file=new File(%s);rq.timeSpanStart=0;rq.timeSpanDuration=20;app.project.save();app.project.renderQueue.render();return JSON.stringify({ok:rq.status===RQItemStatus.DONE,preset:preset,path:om.file.fsName});})();'''%(int(comp_id),json.dumps((frames/'FRAME_[#####].tif').as_posix()))
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':600,
        'checkpoint_label':'before-cognitive-native-render'},out,630)
    write(out/'render-result.json',result)
    files=sorted(frames.glob('*.tif')); count=round(spec['canvas']['duration']*24)
    if not json.loads(result['content']).get('ok') or len(files)!=count or not all(p.stat().st_size for p in files):
        raise ValueError('Native frame sequence incomplete')
    matches=[re.fullmatch(r'(.*?)(\d+)(\.[^.]+)',p.name) for p in files]
    if any(m is None for m in matches):raise ValueError('Unexpected native frame names')
    first=matches[0];start=int(first[2])
    if [int(m[2]) for m in matches]!=list(range(start,start+count)):
        raise ValueError('Native frames are not continuous')
    pattern=frames/(first[1]+'%0'+str(len(first[2]))+'d'+first[3])
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','24','-start_number',str(start),'-i',str(pattern),
        '-frames:v',str(count),'-an','-c:v','libx264','-threads','4','-crf','16','-pix_fmt','yuv420p',str(video)],check=True)
    validate_inputs(request)
    receipt=dict(spec_sha=spec['spec_sha'],template_sha=file_sha(TEMPLATE),
        project=str(Path(request['project']).resolve()),project_sha=file_sha(request['project']),
        output=str(video),output_sha=file_sha(video),frames=count,renderer='native_AE_TIFF',
        audio=False,public_render_ready=False)
    write(out/'render-receipt.json',receipt);return receipt


def preview(client, request, comp_id):
    spec=validate_inputs(request);out=Path(request['output']).resolve();frames=out/'previews'
    if frames.exists():raise ValueError('Preserve existing previews; choose a new revision')
    frames.mkdir();times=[0,4.75,9.75,11.5,15,18]
    code='''(function(){var cp=AEMCP.compById(%d),times=%s,root=%s;for(var i=0;i<times.length;i++)cp.saveFrameToPng(times[i],new File(root+'/frame-'+times[i]+'.png'));return JSON.stringify({ok:true,spec_sha:%s});})();'''%(int(comp_id),json.dumps(times),json.dumps(frames.as_posix()),json.dumps(spec['spec_sha']))
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':120,
        'checkpoint_label':'before-cognitive-preview'},out,150)
    # saveFrameToPng may return just before Windows exposes the final file.
    import time
    deadline=time.monotonic()+10
    while not all((frames/('frame-'+str(t)+'.png')).exists() for t in times):
        if time.monotonic()>deadline:raise ValueError('Native preview incomplete; inspect before retry')
        time.sleep(.2)
    rows=[dict(time=t,path=str(frames/('frame-'+str(t)+'.png')),
               sha256=file_sha(frames/('frame-'+str(t)+'.png'))) for t in times]
    write(out/'preview-receipt.json',dict(spec_sha=spec['spec_sha'],frames=rows,native=result))
    return rows


def main():
    import argparse
    from .bridge import JunkdogeClient
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['build','audit','preview','render'])
    parser.add_argument('request');args=parser.parse_args();request=read(args.request)
    client=JunkdogeClient();client.initialize();client.call('ae_skillUse',{'name':'ae-execution-guide'})
    if args.operation=='build':result=build(client,request)
    else:
        identity=read(Path(request['output'])/'identity.json')
        result=globals()[args.operation](client,request,identity['comp_id'])
    print(args.operation,'complete',flush=True)


if __name__=='__main__':main()
