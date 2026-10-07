"""Native AE picture preparation. No voice generation or final sample delivery."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from video_contracts import ROOT, read, write
from creative_os.hero import file_sha
from creative_os.student_sample import validate_spec
from .bridge import JunkdogeClient
from .execution import mutation_call

TEMPLATE = ROOT / 'ae/templates/student-pov-picture-v0.1.jsx'


def preflight(request):
    spec = read(request['spec'])
    validate_spec(spec, *(read(request[k]) for k in ('copy', 'projection', 'plan', 'bundle', 'status')))
    for font in spec['fonts'].values():
        if file_sha(font['path']) != font['sha256']:
            raise ValueError('Picture measurement font changed')
    return spec


def build(client, request):
    spec = preflight(request)
    out = Path(request['output']).resolve(); out.mkdir(parents=True, exist_ok=True)
    native = {'spec': spec, 'project': str(Path(request['project']).resolve())}
    write(out / 'build-request.json', native)
    before = client.call('ae_read', {'target': 'project'})
    write(out / 'project-before.json', before)
    code = 'var STUDENT_PICTURE_REQUEST=' + json.dumps((out / 'build-request.json').as_posix()) + ';\n'
    code += TEMPLATE.read_text(encoding='utf-8')
    result = mutation_call(client, 'ae_exec', {'code': code, 'timeout_sec': 180,
        'undo_group_name': 'Student POV picture preparation',
        'checkpoint_label': 'before-student-picture'}, out, 210)
    write(out / 'build-result.json', result)
    identity = json.loads(result['content'])
    if not identity.get('ok') or identity.get('spec_sha') != spec['spec_sha']:
        raise ValueError('Native picture identity missing; reconcile before retry')
    write(out / 'identity.json', identity)
    return identity


def _close(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a-b) < 1e-4


def audit(client, request, comp_id):
    spec = preflight(request); d = spec['direction']
    code = '''(function(){var cp=AEMCP.compById(%d),rows=[];
    function keys(p){var a=[];for(var k=1;k<=p.numKeys;k++)a.push([p.keyTime(k),p.keyValue(k)]);return a;}
    for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.name==='PAPER'||l.name==='SPEC_BINDING')continue;
    var r={id:l.name,enabled:l.enabled,threeD:l.threeDLayer,position:l.transform.position.valueAtTime(0,false),rotation:l.transform.rotation.value,
    anchor:l.transform.anchorPoint.value,scale:l.transform.scale.valueAtTime(0,false),opacity:l.transform.opacity.valueAtTime(0,false),
    effects:l.property('ADBE Effect Parade').numProperties,masks:l.property('ADBE Mask Parade').numProperties,
    expression:l.transform.position.expressionEnabled||l.transform.scale.expressionEnabled||l.transform.opacity.expressionEnabled,
    in_point:l.inPoint,out_point:l.outPoint,comment:JSON.parse(l.comment),tracks:{}};
    if(l.transform.position.numKeys)r.tracks.position=keys(l.transform.position);
    if(l.transform.opacity.numKeys)r.tracks.opacity=keys(l.transform.opacity);
    if(l.transform.scale.numKeys)r.tracks.scale=keys(l.transform.scale);
    if(l instanceof TextLayer){var st=l.property('Source Text'),t=st.value;r.sourceTextKeys=st.numKeys;r.sourceTextExpression=st.expressionEnabled;r.text=t.text;r.font=t.font;r.size=t.fontSize;r.color=t.fillColor;r.leading=t.leading;r.fill=t.applyFill;r.stroke=t.applyStroke;
    var b=l.sourceRectAtTime((l.inPoint+l.outPoint)/2,false);r.bounds={left:b.left,top:b.top,width:b.width,height:b.height};}
    else {var g=l.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
    var rect=g.property('ADBE Vector Shape - Rect');r.color=g.property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').value;
    r.size=rect.property('ADBE Vector Rect Size').value;r.radius=rect.property('ADBE Vector Rect Roundness').value;
    r.rectPosition=rect.property('ADBE Vector Rect Position').valueAtTime(0,false);r.rectPositionKeys=keys(rect.property('ADBE Vector Rect Position'));
    var p=rect.property('ADBE Vector Rect Size');if(p.numKeys){var a=keys(p),w=[],h=[];for(var j=0;j<a.length;j++){w.push([a[j][0],a[j][1][0]]);h.push(a[j][1][1]);}r.tracks.width=w;r.keyHeights=h;}}
    rows.push(r);}var paper=cp.layer('PAPER');return JSON.stringify({binding:JSON.parse(cp.comment),rows:rows,layerCount:cp.numLayers,
    bindingDisabled:!cp.layer('SPEC_BINDING').enabled,paper:{enabled:paper.enabled,color:paper.source.mainSource.color,opacity:paper.transform.opacity.value},
    width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration});})();''' % int(comp_id)
    actual = json.loads(client.call('ae_exec', {'code': code})['content'])
    write(Path(request['output']) / 'native-audit.json', actual)
    if (actual['binding']['spec_sha'] != spec['spec_sha'] or
            [actual[k] for k in ('width', 'height', 'fps', 'duration')]
            != [d['canvas'][k] for k in ('width', 'height', 'fps', 'duration')]):
        raise ValueError('Native picture identity or timing drift')
    expected = {n['node_id']: n for n in d['nodes']}
    if (set(expected) != {r['id'] for r in actual['rows']} or len(actual['rows']) != len(expected)
            or actual['layerCount'] != len(expected)+2 or not actual['bindingDisabled']
            or not actual['paper']['enabled'] or actual['paper']['opacity'] != 100
            or not _close(actual['paper']['color'][:3], [int(d['palette']['paper'][i:i+2],16)/255 for i in (1,3,5)])):
        raise ValueError('Native visible node set drift')
    for r in actual['rows']:
        n = expected[r['id']]
        color = [int(n['color'][i:i+2], 16)/255 for i in (1, 3, 5)]
        if (not r['enabled'] or r['threeD'] or r['effects'] or r['masks'] or r['expression']
                or not _close(r['anchor'][:2], [0,0]) or not _close(r['color'][:3], color)
                or len(r['color']) == 4 and abs(r['color'][3]-1) > 1e-4
                or not _close(r['position'][:2], n['position'])
                or r['tracks'] != n['tracks'] and not _tracks_close(r['tracks'], n['tracks'])
                or abs(r['in_point']-n['in_point']) > 1e-4
                or abs(r['out_point']-n['out_point']) > 1e-4
                or abs(r['rotation']-n.get('rotation', 0)) > 1e-4
                or not n['tracks'].get('scale') and not _close(r['scale'][:2], [100,100])
                or not n['tracks'].get('opacity') and abs(r['opacity']-100) > 1e-4
                or r['comment'] != {'text_binding': n.get('text_binding'), 'source_refs': n.get('source_refs', [])}):
            raise ValueError('Native source/motion drift: ' + r['id'])
        if n['kind'] == 'text':
            if (r['sourceTextKeys'] or r['sourceTextExpression'] or r['text'].replace('\r', '\n') != n['text']
                    or r['font'] != n['font'] or r['size'] != n['size'] or not r['fill'] or r['stroke']
                    or abs(r['leading']-n.get('leading',n['size']*1.42)) > 1e-3):
                raise ValueError('Native text/font drift: ' + r['id'])
        elif (not _close(r['size'][1], n['height'])
                or any(not _close(height, n['height']) for height in r.get('keyHeights', []))
                or not n['tracks'].get('width') and not _close(r['size'][0], n['width'])
                or r['radius'] != n.get('radius', 0)):
            raise ValueError('Native mark geometry drift: ' + r['id'])
        if n['kind'] != 'text':
            y = 0 if n['kind'] == 'line' else n['height']/2
            centers = [[time,[width/2,y]] for time,width in n['tracks'].get('width',[])]
            if (not _close(r['rectPositionKeys'],centers) or not centers
                    and not _close(r['rectPosition'],[n['width']/2,y])):
                raise ValueError('Native relation/mark growth origin changed: ' + r['id'])
    return actual


def _tracks_close(a, b):
    if set(a) != set(b):
        return False
    actual = {}
    for key, rows in a.items():
        if key in ('position', 'scale'):
            tail = 0 if key == 'position' else 100
            if any(len(value) > 2 and abs(value[2]-tail) > 1e-4 for _, value in rows):
                return False
            actual[key] = [[time, value[:2]] for time, value in rows]
        else:
            actual[key] = rows
    return all(_close(actual[k], b[k]) for k in actual)


def reconcile_build(client, request):
    """Resolve a late completed write with fresh readback, never by rebuilding."""
    spec = preflight(request); out = Path(request['output'])
    code = '''(function(){var a=[];for(var i=1;i<=app.project.numItems;i++){var c=app.project.item(i);
    if(!(c instanceof CompItem))continue;try{var b=JSON.parse(c.comment);if(b.spec_sha===%s)a.push({comp_id:c.id,layers:c.numLayers});}catch(e){}}
    return JSON.stringify({project:app.project.file?app.project.file.fsName:null,matches:a});})();''' % json.dumps(spec['spec_sha'])
    observed = json.loads(client.call('ae_exec', {'code': code})['content'])
    if (Path(observed['project']).resolve() != Path(request['project']).resolve()
            or len(observed['matches']) != 1
            or observed['matches'][0]['layers'] != len(spec['direction']['nodes'])+2):
        raise ValueError('Uncertain build has no single complete native match; inspect before proceeding')
    identity = dict(observed['matches'][0], ok=True, project=observed['project'], spec_sha=spec['spec_sha'])
    audit(client, request, identity['comp_id'])
    write(out / 'build-reconciliation.json', {'status': 'COMPLETE_CONFIRMED_BY_FRESH_READBACK',
        'native': observed, 'project_sha': file_sha(request['project']), 'build_retried': False})
    write(out / 'identity.json', identity)
    return identity


def preview(client, request, comp_id):
    spec = preflight(request); out = Path(request['output']) / 'previews'
    out.mkdir(exist_ok=False)
    result = client.call('ae_previewFrame', {'comp_id': str(comp_id),
        'times': request['preview_times'], 'layout': 'grid', 'grid_max_side': 2048,
        'out_dir': str(out.resolve())}, timeout=120)
    write(out / 'receipt.json', {'spec_sha': spec['spec_sha'], 'native': result})
    return result


def render(client, request, comp_id):
    spec = preflight(request); audit(client, request, comp_id)
    out = Path(request['output']).resolve(); frames = out / 'native-tiff'; video = out / 'PICTURE_ONLY.mp4'
    if frames.exists() or video.exists():
        raise ValueError('Preserve picture renders; inspect before resuming')
    frames.mkdir()
    duration = spec['direction']['canvas']['duration']
    code = '''(function(){for(var i=1;i<=app.project.renderQueue.numItems;i++){var q=app.project.renderQueue.item(i);if(q.render&&q.status===RQItemStatus.QUEUED)throw new Error('Unrelated queued render');}
    var cp=AEMCP.compById(%d),rq=app.project.renderQueue.items.add(cp),om=rq.outputModule(1),preset=null;
    for(var j=0;j<om.templates.length;j++)if(om.templates[j].indexOf('TIFF')!==-1){preset=om.templates[j];break;}
    if(!preset){rq.remove();throw new Error('TIFF preset unavailable');}om.applyTemplate(preset);om.file=new File(%s);
    rq.timeSpanStart=0;rq.timeSpanDuration=%s;app.project.save();app.project.renderQueue.render();
    return JSON.stringify({ok:rq.status===RQItemStatus.DONE,preset:preset});})();''' % (
        int(comp_id), json.dumps((frames / 'FRAME_[#####].tif').as_posix()), duration)
    native = mutation_call(client, 'ae_exec', {'code': code, 'timeout_sec': 600,
        'checkpoint_label': 'before-student-picture-render'}, out, 630)
    write(out / 'render-result.json', native)
    files = sorted(frames.glob('*.tif')); count = round(duration * 24)
    if not json.loads(native['content']).get('ok') or len(files) != count or not all(p.stat().st_size for p in files):
        raise ValueError('Incomplete native picture render; inspect before retry')
    matches = [re.fullmatch(r'(.*?)(\d+)(\.[^.]+)', p.name) for p in files]
    if any(m is None for m in matches):
        raise ValueError('Unrecognized frame names')
    first = matches[0]; start = int(first[2])
    if [int(m[2]) for m in matches] != list(range(start, start+count)):
        raise ValueError('Native picture frames are not contiguous')
    pattern = frames / (first[1] + '%0' + str(len(first[2])) + 'd' + first[3])
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-framerate', '24', '-start_number', str(start),
        '-i', str(pattern), '-frames:v', str(count), '-an', '-c:v', 'libx264', '-threads', '4',
        '-crf', '16', '-pix_fmt', 'yuv420p', str(video)], check=True)
    preflight(request)
    receipt = {'spec_sha': spec['spec_sha'], 'template_sha': file_sha(TEMPLATE),
        'project': str(Path(request['project']).resolve()), 'project_sha': file_sha(request['project']),
        'output': str(video), 'output_sha': file_sha(video), 'frames': count,
        'duration': duration, 'renderer': 'native_AE_TIFF', 'audio': False,
        'preparation_state': 'PICTURE_PREPARED_VOICE_PENDING',
        'sample_delivery_allowed': False, 'public_render_ready': False}
    write(out / 'picture-receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('build', 'reconcile-build', 'audit', 'preview', 'render'))
    parser.add_argument('request'); args = parser.parse_args(); request = read(args.request)
    client = JunkdogeClient(request.get('endpoint', 'http://127.0.0.1:11488/mcp'))
    client.initialize(); client.call('ae_skillUse', {'name': 'ae-execution-guide'})
    if args.operation == 'build':
        build(client, request)
    elif args.operation == 'reconcile-build':
        reconcile_build(client, request)
    else:
        identity = read(Path(request['output']) / 'identity.json')
        globals()[args.operation](client, request, identity['comp_id'])
    print(args.operation + ' complete; final audio and sample delivery remain pending', flush=True)


if __name__ == '__main__':
    main()
