"""Native short motion segments; final narration and cuts belong to Premiere."""
import json
from pathlib import Path

from video_contracts import write, sha
from creative_os.hero import TEMPLATE, validate_contract, file_sha
from .execution import mutation_call


def build(client, contract, package, manifest, statuses, full, excerpt, out, project):
    validate_contract(contract, package, manifest, statuses, full, excerpt)
    out, project = Path(out).resolve(), Path(project).resolve()
    path = out / 'render-contract.json'
    write(path, contract)
    detach = '(function(){var f=new File(%s);if(!app.project.file||app.project.file.fsName!==f.fsName){if(f.exists)throw new Error("Existing project: explicitly open and inspect");app.project.save(f);}return JSON.stringify({project:app.project.file.fsName});})();' % json.dumps(project.as_posix())
    write(out / 'detach-result.json', mutation_call(client, 'ae_exec', {'code': detach}, out, 60))
    code = 'var H_CONTRACT_PATH=%s;var H_PROJECT_PATH=%s;\n' % (json.dumps(path.as_posix()), json.dumps(project.as_posix()))
    code += TEMPLATE.read_text(encoding='utf-8')
    result = mutation_call(client, 'ae_exec', {'code': code, 'timeout_sec': 180, 'checkpoint_label': 'V9.1-before-build'}, out, 200)
    write(out / 'build-result.json', result)
    identity = json.loads(result['content'])
    if not identity.get('ok') or identity['render_contract_sha'] != contract['render_contract_sha']:
        raise ValueError('Native composition identity mismatch')
    write(out / 'build-identity.json', identity)
    return identity


def audit(client, contract, comp_id, out):
    code = '''(function(){var cp=AEMCP.compById(%d),rows=[],effects=[];for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l instanceof TextLayer){var d=l.property('Source Text').value;rows.push({id:l.name,text:d.text,font:d.font,size:d.fontSize});}var fx=l.property('ADBE Effect Parade');if(fx)for(var j=1;j<=fx.numProperties;j++)effects.push({id:l.name,match:fx.property(j).matchName});}var f=cp.layer('RENDER_CONTRACT').source.file;f.encoding='UTF-8';f.open('r');var text=f.read();f.close();return JSON.stringify({binding:JSON.parse(cp.comment),contract_text:text,rows:rows,effects:effects,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration,motionBlur:cp.motionBlur,shutter:cp.shutterAngle});})();''' % int(comp_id)
    result = json.loads(client.call('ae_exec', {'code': code})['content'])
    if sha(json.loads(result['contract_text'])) != sha(contract) or result['binding']['render_contract_sha'] != contract['render_contract_sha']:
        raise ValueError('Native contract changed')
    expected = {n['node_id']: n for n in contract['nodes'] if n['kind'] == 'text'}
    if {r['id'] for r in result['rows']} != set(expected):
        raise ValueError('Unexpected or missing native text')
    if any(r['text'] != expected[r['id']]['text'] or r['font'] != expected[r['id']]['font']
           or r['size'] != expected[r['id']]['size'] for r in result['rows']):
        raise ValueError('Native copy/font/size drift')
    if (result['width'], result['height'], result['fps'], result['duration']) != (1920, 1080, 24, contract['canvas']['duration']):
        raise ValueError('Native profile drift')
    if not result['motionBlur'] or result['shutter'] != 180 or any(r['match'] != 'ADBE Gaussian Blur 2' for r in result['effects']):
        raise ValueError('Native effects policy drift')
    tracks_code = '''(function(){var cp=AEMCP.compById(%d),rows=[];function values(p){var out=[];for(var k=1;k<=p.numKeys;k++)out.push([p.keyTime(k),p.keyValue(k)]);return out;}for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.name==='BACKGROUND'||l.name==='RENDER_CONTRACT')continue;var t={position:values(l.transform.position),opacity:values(l.transform.opacity),scale:values(l.transform.scale)};if(l instanceof ShapeLayer){var g=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');t.width=values(g.property('ADBE Vector Shape - Rect').property('ADBE Vector Rect Size'));}var fx=l.property('ADBE Effect Parade');if(fx&&fx.numProperties)t.blur=values(fx.property(1).property(1));rows.push({id:l.name,tracks:t,inPoint:l.inPoint,outPoint:l.outPoint,initialPosition:l.transform.position.valueAtTime(0,false),initialOpacity:l.transform.opacity.valueAtTime(0,false),enabled:l.enabled});}return JSON.stringify(rows);})();''' % int(comp_id)
    native_tracks = json.loads(client.call('ae_exec', {'code': tracks_code})['content'])
    expected_nodes = {n['node_id']:n for n in contract['nodes']}
    if {r['id'] for r in native_tracks} != set(expected_nodes):
        raise ValueError('Native node set drift')
    def close(a,b):
        if isinstance(a,list) and isinstance(b,list):
            return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
        return isinstance(a,(int,float)) and isinstance(b,(int,float)) and abs(a-b)<1e-5
    for row in native_tracks:
        node=expected_nodes[row['id']]
        if not row['enabled'] or set(node.get('tracks',{}))-set(row['tracks']):
            raise ValueError('Native node disabled or animated property missing')
        if not node.get('tracks',{}).get('position') and not close(row['initialPosition'][:2],node['position']):
            raise ValueError('Native static position drift')
        if not node.get('tracks',{}).get('opacity') and abs(row['initialOpacity']-node.get('opacity',100))>1e-5:
            raise ValueError('Native static visibility drift')
        for name, actual in row['tracks'].items():
            expected_track=node.get('tracks',{}).get(name,[])
            if name=='scale':
                actual=[[t,v[:2]] for t,v in actual]
            if name=='position':
                if any(len(v)==3 and abs(v[2])>1e-5 for t,v in actual):
                    raise ValueError('Unexpected native Z position')
                actual=[[t,v[:2]] for t,v in actual]
            # AE stores subframe key times on its own time grid. Keep values
            # strict while allowing less than 1/1024 of a 24fps frame in time.
            if (len(actual)!=len(expected_track) or any(abs(a[0]-b[0])>1/(24*1024)
                    or not close(a[1],b[1]) for a,b in zip(actual,expected_track))):
                raise ValueError('Native motion keyframe drift: '+row['id']+'/'+name)
        if abs(row['inPoint']-node.get('in_point',0))>1/(24*1024) or abs(row['outPoint']-node.get('out_point',contract['canvas']['duration']))>1/(24*1024):
            raise ValueError('Native node visibility span drift')
    result['motion_keyframes']=native_tracks
    write(Path(out) / 'native-audit.json', result)
    return result


def render(client, contract, package, manifest, statuses, full, excerpt, comp_id, out):
    validate_contract(contract, package, manifest, statuses, full, excerpt)
    out = Path(out).resolve()
    video = out / 'AE_HERO_MOTION.mp4'
    if video.exists():
        raise ValueError('Use a new revision rather than overwrite rendered media')
    audit(client, contract, comp_id, out)
    layers = client.call('ae_read', {'target': 'layers', 'comp': {'id': str(comp_id)}, 'page': {'limit': 200}})
    check = client.call('ae_validateExpressions', {'comp_id': str(comp_id),
        'layer_ids': [l['stackIndex'] for l in layers['layers'] if l['name'] != 'RENDER_CONTRACT'],
        'sample_times': [2, 4.5, 5.6, 6.3, 8.5, 11.5], 'max_results': 1000})
    write(out / 'expression-audit.json', check)
    if not check.get('valid') or check.get('truncated'):
        raise ValueError('Native expression audit incomplete')
    code = '''(function(){var cp=AEMCP.compById(%d);for(var i=1;i<=app.project.renderQueue.numItems;i++){var x=app.project.renderQueue.item(i);if(x.render&&x.status===RQItemStatus.QUEUED)throw new Error('Queued render conflict');}var rq=app.project.renderQueue.items.add(cp),om=rq.outputModule(1),preset=null;for(var i=0;i<om.templates.length;i++)if(om.templates[i].indexOf('H.264')===0&&om.templates[i].indexOf('15')!==-1){preset=om.templates[i];break;}if(!preset){rq.remove();throw new Error('Native H.264 unavailable');}om.applyTemplate(preset);om.file=new File(%s);rq.timeSpanStart=0;rq.timeSpanDuration=cp.duration;app.project.save();app.project.renderQueue.render();return JSON.stringify({ok:rq.status===RQItemStatus.DONE,path:om.file.fsName,preset:preset});})();''' % (int(comp_id), json.dumps(video.as_posix()))
    result = mutation_call(client, 'ae_exec', {'code': code, 'timeout_sec': 600, 'checkpoint_label': 'V9.1-before-render'}, out, 630)
    write(out / 'render-result.json', result)
    if not json.loads(result['content']).get('ok') or not video.exists() or video.stat().st_size == 0:
        raise ValueError('Native render incomplete; reconcile before retrying')
    return video
