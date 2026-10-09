"""One native SYNTHETIC relay film; consumes no solver or live Registry."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from video_contracts import read, sha, write, status_matches
from video_contracts import passage
from ae_production.bridge import JunkdogeClient
from ae_production.execution import mutation_call

HERE = Path(__file__).resolve().parent
LOCAL = ROOT / 'local-data' / 'method-relay-dual-pass'


def file_sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def local(path):
    path = Path(path).resolve()
    if not path.is_relative_to(LOCAL):
        raise ValueError('Relay artifacts stay in the ignored independent research directory')
    return path


def validate_fixture(f):
    if (f['kind'] != 'synthetic_method_relay_visual_research'
            or f['authority'] != 'supplied_visual_objects_and_outcomes_not_english_analysis'
            or f['not_a_teaching_asset'] is not True
            or f['production_eligible'] is not False or f['public_render_ready'] is not False
            or any(v is not False for v in f['claims'].values())):
        raise ValueError('Explicitly SYNTHETIC / VISUAL-ONLY source required')
    pos = 0; ids = set()
    for obj in f['objects']:
        if (obj['id'] in ids or obj['start'] != pos or type(obj['end']) is not int
                or obj['end'] <= pos or f['sentence'][pos:obj['end']] != obj['text']):
            raise ValueError('Every original character needs a unique continuous identity')
        ids.add(obj['id']); pos = obj['end']
        if obj['role'] == 'supplied_modifier':
            if obj['protected'] or obj['disposition'] != 'deferred':
                raise ValueError('Deferred text cannot be destroyed or protected text peeled')
        elif obj['role'] != 'core' or obj['protected'] is not True:
            raise ValueError('Only explicitly supplied protected cores may remain')
    if pos != len(f['sentence']): raise ValueError('Source partition incomplete')
    by_id = {o['id']: o for o in f['objects']}
    for field,cue in f.get('locate_cues',{}).items():
        if (field not in ('stem','sentence') or set(cue)!={'start','end','text'}
                or type(cue['start']) is not int or type(cue['end']) is not int
                or not 0<=cue['start']<cue['end']<=len(f[field])
                or f[field][cue['start']:cue['end']]!=cue['text']):
            raise ValueError('Location cue must be an explicitly supplied literal substring')
    cores = {o['id'] for o in f['objects'] if o['role'] == 'core'}
    for o in f['objects']:
        if o['role'] == 'supplied_modifier' and o['attachment'] not in cores:
            raise ValueError('Explicit existing visual anchor required')
    seen = set()
    for c in f['attention_cues']:
        o = by_id.get(c['object_id'])
        if (o is None or o['role'] != 'supplied_modifier' or o['id'] in seen
                or not o['start'] <= c['start'] < c['end'] <= o['end']
                or f['sentence'][c['start']:c['end']] != c['text']):
            raise ValueError('Attention cue must bind its own exact original span')
        seen.add(o['id'])
    if seen != {o['id'] for o in f['objects'] if o['role'] == 'supplied_modifier'}:
        raise ValueError('Each supplied fragment needs its own cue')
    available = {'original-question', 'original-passage', 'original-options'}
    for step in f['trace']:
        if (not set(step['input']) <= available or step['output'] in available
                or not set(step['object_ids']) <= ids or not step['stop']):
            raise ValueError('Relay must consume existing outputs without inventing source objects')
        available.add(step['output'])
    if [x['id'] for x in f['trace']] != ['locate', 'interpret', 'compare', 'verify']:
        raise ValueError('Only this explicit shared synthetic trajectory is supported')
    if ([o['id'] for o in f['options']] != list('ABCD')
            or any(len(o['parts']) != 3 or not all(isinstance(t, str) and t for t in o['parts']) for o in f['options'])
            or f['options'][0]['supplied_state'] != 'matches_supplied_fixture'
            or any(o['supplied_state'] != 'conflicts_supplied_fixture' for o in f['options'][1:])):
        raise ValueError('Use explicitly supplied synthetic candidate outcomes; never infer answers')
    guide = f.get('guided_method_copy')
    if f['version']=='0.1.1' and guide is None:
        raise ValueError('The revised method copy requires its explicit source-binding contract')
    if guide is not None:
        if (guide['scope'] != 'frozen_general_action_with_synthetic_visual_example_not_case_certification'
                or [(x['id'], x['method_id'], x['fields']) for x in guide['clips']] != [
                    (cid, mid, ['core_action', 'decision_rule', 'stop_rule'])
                    for cid, mid in [('locate', 'R12'), ('carry', 'R11'), ('basis', 'R02')]]
                or guide['column_labels'] != [{'part':p, 'text':t} for p,t in
                    [('subject','谁'), ('verb','做什么'), ('object','对象')]]):
            raise ValueError('Bind only these frozen method actions; no invented explanation fields')
        e = guide['emphasis']; voices = {v['id']:v['text'] for v in f['voice']}
        if (e['object_id'] != 'option-B-subject' or e['clip_id'] != 'compare'
                or e['phrase'] not in voices.get(e['clip_id'], '')
                or len(e['window']) != 2 or any(type(t) not in (int,float) or not math.isfinite(t) for t in e['window'])
                or not 31 <= e['window'][0] < e['window'][1] <= 34.8):
            raise ValueError('The supplied comparison phrase needs its own bounded observation window')
    return f


def name_snapshots():
    """Names only from existing frozen transports; no raw Registry or teaching prose."""
    a = ROOT/'local-data/reading-d-2025/frozen-r1'
    b = ROOT/'local-data/video-os/pilot/gaokao-2021-I-q26-R02'
    result = []
    for folder, mids in ((a, ('R12', 'R11')), (b, ('R02',))):
        bundle, status = read(folder/'bundle.json'), read(folder/'status.json')
        if bundle.get('kind') == 'frozen_reviewed_passage':
            passage.require_current(bundle, status); methods = bundle['payload']['methods']
            prefix = '/payload/methods/'
        else:
            if not status_matches(bundle, status): raise ValueError('Name source is no longer current')
            methods = bundle['methods']; prefix = '/methods/'
        for mid in mids:
            i, method = next((i, m) for i, m in enumerate(methods) if m['method_id'] == mid)
            result.append({'method_id': mid, 'name': method['brand_name'], 'version': method['version'],
                'asset_id': bundle['asset_id'], 'semantic_binding_sha': bundle['semantic_binding_sha'],
                'pointer': prefix+str(i)+'/brand_name', 'name_sha': sha(method['brand_name']),
                'authority': 'frozen_name_projection_only_not_synthetic_method_certification'})
    return result


def explanation_snapshots(fixture):
    """Read existing structured actions and boundaries, without certifying this synthetic case."""
    result = []
    for clip in fixture['guided_method_copy']['clips']:
        folder = (ROOT/'local-data/video-os/pilot/gaokao-2021-I-q26-R02' if clip['method_id']=='R02'
                  else ROOT/'local-data/reading-d-2025/frozen-r1')
        bundle,status=read(folder/'bundle.json'),read(folder/'status.json')
        if bundle.get('kind')=='frozen_reviewed_passage':
            passage.require_current(bundle,status);methods=bundle['payload']['methods'];prefix='/payload/methods/'
        else:
            if not status_matches(bundle,status):raise ValueError('Explanation source is no longer current')
            methods=bundle['methods'];prefix='/methods/'
        index,method=next((i,m) for i,m in enumerate(methods) if m['method_id']==clip['method_id'])
        fields={key:method[key] for key in clip['fields']}
        if any(not isinstance(value,str) or not value.strip() for value in fields.values()):
            raise ValueError('Explicit frozen action and boundary text required')
        voice=next(v for v in fixture['voice'] if v['id']==clip['id'])
        result.append({'clip_id':clip['id'],'method_id':clip['method_id'],'version':method['version'],
            'asset_id':bundle['asset_id'],'semantic_binding_sha':bundle['semantic_binding_sha'],
            'fields':fields,'refs':[{'pointer':prefix+str(index)+'/'+key,'value_sha':sha(value)} for key,value in fields.items()],
            'voice_text_sha':sha(voice['text']),'authority':fixture['guided_method_copy']['scope'],
            'synthetic_case_certified':False})
    return result


def direction(phase):
    # Each director supplies actual seconds. Guided time is not a multiplier of Fast.
    def row(kind, start, end, locate, lift, a, b, tighten, align, compare, others, verify):
        return dict(kind=kind, start=start, end=end, locate=locate, lift=lift,
                    peel_a=a, peel_b=b, tighten=tighten, align=align,
                    compare=compare, others=others, verify=verify)
    if phase == 'p0':
        return {'duration': 20.0, 'passes': [row('relay', 0, 20, [2, 3.3], [3.3, 4.2],
            [4.2, 4.5, 4.8, 5.05, 5.88], [6.6, 6.9, 7.2, 7.45, 8.28],
            [5.5, 6.7], [9, 11], [11.5, 14], [14.2, 16], [17, 18.5])], 'rewind': None}
    if phase != 'full': raise ValueError('Only P0 relay and the complete dual pass are supported')
    return {'duration': 46.5, 'passes': [
        row('fast', 2.5, 12.5, [2.65, 3.2], [3.2, 3.65],
            [3.65, 3.85, 4.03, 4.28, 4.78], [4.85, 5.05, 5.23, 5.48, 5.98],
            [4.6, 5.45], [6.1, 7.2], [7.3, 8.6], [8.65, 9.65], [10.1, 11.6]),
        row('guided', 15.5, 46.5, [16, 19.7], [19.7, 21.3],
            [21.3, 21.6, 21.9, 22.15, 22.98], [24.1, 24.4, 24.7, 24.95, 25.78],
            [22.8, 24.0], [27, 29.3], [30.1, 34.8], [35, 38.1], [40, 43.5])],
        'rewind': [12.5, 15.25]}


def voice_slots(request=None):
    f = request['fixture'] if request is not None else read(HERE/'synthetic-relay.json')
    return [dict(v, start=t) for v, t in zip(f['voice'], (15.75, 20, 26.25, 31, 40))]


def acquisition_plan(request):
    """Astra-directed attention path, bound to supplied literal spans only."""
    if request['phase'] != 'full' or 'locate_geometry' not in request:
        raise ValueError('Acquisition v0.2 requires the complete literal-cue dual proof')
    stages = ('target', 'enter', 'browse', 'hit', 'confirm')
    fast = ([1.5,2.25], [2.25,2.625], [2.625,2.875], [2.875,3], [3,3.2])
    guided = ([16,16.875], [16.875,17.5], [17.5,18.125], [18.125,18.5], [18.5,19.125])
    return {'version':'0.2.0','decision_author':'astra_creative_advice','second_reviewer':'root',
        'authority':'supplied_visual_location_not_reader_performance_measurement',
        'cue_refs':{k:dict(v,text_sha=sha(v['text'])) for k,v in request['fixture']['locate_cues'].items()},
        'passes':[dict(kind=kind, **dict(zip(stages, times)),
            settle=[times[-1][1],p['locate'][1]],lift=p['lift'],
            context_retire=[times[3][0],times[-1][1]])
            for kind,times,p in zip(('fast','guided'),(fast,guided),request['passes'])],
        'complete_fast_action':[1.5,12.5], 'duration_changed':False,
        'transcript_changed':False, 'source_objects_replaced':False,
        'public_render_ready':False}


def validate_acquisition(request):
    if request.get('native_acquisition_geometry') and 'source_acquisition' not in request:
        raise ValueError('Native acquisition geometry requires its literal-cue director')
    if 'source_acquisition' in request and request['source_acquisition'] != acquisition_plan(request):
        raise ValueError('Exact literal-cue and ordered acquisition director binding required')


def make_request(output, phase, acquisition_v2=False):
    from PIL import ImageFont
    f = validate_fixture(read(HERE/'synthetic-relay.json'))
    font = ImageFont.truetype(f['font']['english_file'], f['font']['size'])
    x = 190; layout = []
    for o in f['objects']:
        w = float(font.getlength(o['text'])); layout.append(dict(o, x=x, width=w, text_sha=sha(o['text']))); x += w
    if x > 1775: raise ValueError('Original sentence must fit the readable source plane')
    by_id = {o['id']: o for o in layout}
    cues = [dict(c, offset_x=float(font.getlength(by_id[c['object_id']]['text'][:c['start']-by_id[c['object_id']]['start']])),
                 width=float(font.getlength(c['text'])), text_sha=sha(c['text'])) for c in f['attention_cues']]
    options = []
    for i, o in enumerate(f['options']):
        x = 230; pieces = []
        for part, text in zip(('subject', 'verb', 'object'), o['parts']):
            width = float(font.getlength(text))
            pieces.append({'id': 'option-'+o['id']+'-'+part, 'part': part, 'text': text, 'text_sha': sha(text), 'x': x, 'width': width})
            x += width
        # Preserve source order during transport; swapping A/B causes a crossing.
        options.append(dict(o, y=650+i*62, comparison_y={'A':645,'B':715,'C':790,'D':850}[o['id']], pieces=pieces))
    columns={'subject':by_id['core-verb']['x']-by_id['core-subject']['width']}
    columns['verb']=columns['subject']+max(o['pieces'][0]['width'] for o in options)+14
    columns['object']=columns['verb']+max(o['pieces'][1]['width'] for o in options)+14
    request = {'fixture': f, 'fixture_sha': sha(f), 'phase': phase, **direction(phase),
        'layout': layout, 'cue_layout': cues, 'options': options, 'comparison_columns':columns,'method_names': name_snapshots(),
        'trajectory_sha': sha(f['trace']), 'font_shas': {k:file_sha(f['font'][k+'_file']) for k in ('english','chinese')},
        'template_sha': file_sha(HERE/'build.jsx'), 'project': str(output/'METHOD_RELAY.aep')}
    if phase=='full' and 'guided_method_copy' in f:
        request['method_explanations']=explanation_snapshots(f)
    if 'locate_cues' in f:
        stem_font=ImageFont.truetype(f['font']['english_file'],38)
        a,b=f['locate_cues']['stem'],f['locate_cues']['sentence']
        request['locate_geometry']={'stem_x':190+float(stem_font.getlength(f['stem'][:a['start']])),
            'stem_width':float(stem_font.getlength(a['text'])),
            'source_x':190+float(font.getlength(f['sentence'][:b['start']])),
            'source_width':float(font.getlength(b['text']))}
    if acquisition_v2:
        request['source_acquisition']=acquisition_plan(request)
        request['native_acquisition_geometry']=True
    request['spec_sha'] = sha({k:v for k,v in request.items() if k != 'project'})
    return request


def current(output):
    r = read(output/'request.json'); validate_fixture(r['fixture'])
    validate_acquisition(r)
    if (r['fixture_sha'] != sha(r['fixture']) or r['trajectory_sha'] != sha(r['fixture']['trace'])
            or r['spec_sha'] != sha({k:v for k,v in r.items() if k not in ('project','spec_sha')})
            or file_sha(output/'executed-template.jsx') != r['template_sha']
            or r['method_names'] != name_snapshots()
            or any(file_sha(r['fixture']['font'][k+'_file']) != v for k,v in r['font_shas'].items())):
        raise ValueError('Frozen source, trajectory, names, font or executed template changed')
    if r['phase']=='full' and 'guided_method_copy' in r['fixture']:
        if r.get('method_explanations')!=explanation_snapshots(r['fixture']):
            raise ValueError('Frozen method action, boundary or its copy binding changed')
    return r


def client():
    c = JunkdogeClient(); c.initialize(); c.call('ae_skillUse', {'name':'ae-execution-guide'}); return c


def require_p0(output):
    output=local(output);r=current(output);receipt=read(output/'render-receipt.json')
    validate_native(r,read(output/'native-audit.json'))
    if (r['phase']!='p0' or receipt['spec_sha']!=r['spec_sha']
            or receipt['trajectory_sha']!=sha(read(HERE/'synthetic-relay.json')['trace'])
            or receipt['native']['done'] is not True
            or file_sha(receipt['output'])!=receipt['output_sha']
            or file_sha(receipt['project'])!=receipt['project_sha']):
        raise ValueError('P0 actual native relay render required before dual assembly')
    return {'spec_sha':r['spec_sha'],'trajectory_sha':r['trajectory_sha'],
            'movie_sha':receipt['output_sha'],'project_sha':receipt['project_sha']}


def build(output, phase, p0=None, acquisition_v2=False):
    proof=require_p0(p0) if phase=='full' and p0 is not None else None
    if phase=='full' and proof is None:raise ValueError('Supply the completed P0 relay before building the dual pass')
    output = local(output); output.mkdir(parents=True, exist_ok=False)
    r = make_request(output, phase, acquisition_v2)
    if proof is not None:
        r['p0_proof']=proof;r['spec_sha']=sha({k:v for k,v in r.items() if k not in ('project','spec_sha')})
    write(output/'request.json', r)
    shutil.copy2(HERE/'build.jsx', output/'executed-template.jsx')
    c = client()
    before = json.loads(c.call('ae_exec', {'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty,items:app.project.numItems});'})['content'])
    old_sha = file_sha(before['path']) if before['path'] else None
    # Save As first: public checkpoints save the loaded project, so isolate it.
    session = output/'SESSION_START.aep'
    result = mutation_call(c, 'ae_exec', {'code':'(function(){app.project.save(new File('+json.dumps(session.as_posix())+'));return JSON.stringify({path:app.project.file.fsName});})();',
        'undo_group_name':'Isolate Method Relay session'}, output, 90)
    native = json.loads(result['content'])
    if Path(native['path']).resolve() != session or (before['path'] and file_sha(before['path']) != old_sha):
        raise ValueError('Session isolation changed a historical project')
    write(output/'session-isolation.json', {'before':before, 'old_sha':old_sha, 'isolated':native})
    code = 'var RELAY_REQUEST='+json.dumps((output/'request.json').as_posix())+';\n'+(output/'executed-template.jsx').read_text(encoding='utf-8')
    result = mutation_call(c, 'ae_exec', {'code':code, 'undo_group_name':'Native Method Relay '+phase,
        'checkpoint_label':'before-method-relay-'+phase, 'timeout_sec':120}, output, 150)
    write(output/'build-result.json', result); identity = json.loads(result['content']); write(output/'identity.json', identity)
    return audit(output)


def audit(output):
    r = current(output); identity = read(output/'identity.json'); c = client()
    code = 'var RELAY_REQUEST='+json.dumps((output/'request.json').as_posix())+';var RELAY_COMP='+str(identity['comp_id'])+';\n'+(HERE/'audit.jsx').read_text(encoding='utf-8')
    native = json.loads(c.call('ae_exec', {'code':code})['content']); write(output/'native-audit.json', native)
    validate_native(r, native)
    expressions = c.call('ae_validateExpressions', {'comp_id':str(identity['comp_id']),
        'sample_times':[p['align'][1] for p in r['passes']], 'max_results':1500})
    write(output/'expressions.json', expressions)
    if expressions.get('valid') is not True or expressions.get('errors') or expressions.get('truncated'): raise ValueError('Native expression error or incomplete validation')
    return native


def close_vectors(actual, expected, tolerance=.01):
    return (len(actual)==len(expected) and all(math.isfinite(x) and abs(x-y)<=tolerance
                                              for x,y in zip(actual,expected)))


def native_acquisition_geometry(r, acquisition, handles):
    """Cross-check toWorld against actual native glyph rects and initial transforms."""
    g=acquisition.get('geometry') or {}
    if (g.get('space')!='native_toWorld' or g.get('sample_time')!=0
            or g.get('cue_refs')!=r['source_acquisition']['cue_refs']
            or g.get('probe_retained') is not False or acquisition.get('temporary_probes')!=[]):
        raise ValueError('Native text geometry and literal cue provenance required')
    rects=acquisition.get('native_source_rects',[])
    expected={o['id'] for o in r['layout']}|{'EVIDENCE_LOCATION_CUE','CONTEXT_BEFORE'}
    if len(rects)!=len(expected) or {x['name'] for x in rects}!=expected:
        raise ValueError('Read native glyphs and the independent highlight rectangle')
    bounds={}
    for row in rects:
        box=row['rect'];offset=[0,0,0]
        for parent in row['parents']:
            if (not close_vectors(parent['scale'],[100,100,100]) or parent['rotation']!=0
                    or parent['x_rotation']!=0 or parent['y_rotation']!=0):
                raise ValueError('Initial readback must agree with the translation-only source plane')
            offset=[a+b-c for a,b,c in zip(offset,parent['position'],parent['anchor'])]
        bounds[row['name']]={'min':[offset[0]+box['left'],offset[1]+box['top'],offset[2]],
                            'max':[offset[0]+box['left']+box['width'],offset[1]+box['top']+box['height'],offset[2]]}
    for field,expected_names in (('keyword_layers',['core-verb','core-object']),
                                 ('sentence_layers',[o['id'] for o in r['layout']])):
        rows=g[field]
        if [x['name'] for x in rows]!=expected_names:
            raise ValueError('Geometry must measure the actual source objects')
        for row in rows:
            if row['layer_id']!=handles[row['name']] or any(not close_vectors(row[k],bounds[row['name']][k]) for k in ('min','max')):
                raise ValueError('Stored toWorld geometry does not match native text')
        aggregate=g['keyword' if field=='keyword_layers' else 'sentence']
        mn=[min(x['min'][i] for x in rows) for i in range(3)]
        mx=[max(x['max'][i] for x in rows) for i in range(3)]
        if any(not close_vectors(aggregate[k],v) for k,v in (('min',mn),('max',mx),('center',[(a+b)/2 for a,b in zip(mn,mx)]))):
            raise ValueError('Camera target must come from the measured glyph union')
    marker=g['marker_after'];hit=g['keyword']
    if any(not close_vectors(marker[k],bounds['EVIDENCE_LOCATION_CUE'][k]) for k in ('min','max')):
        raise ValueError('Highlight readback differs from its measured shape')
    if any(abs(marker['min'][i]-(hit['min'][i]-4))>.01 or abs(marker['max'][i]-(hit['max'][i]+4))>.01 for i in (0,1)):
        raise ValueError('The highlight must cover the exact glyph union with a 4 px margin')
    projections=g.get('projections',[])
    if len(projections)!=2:
        raise ValueError('Read native toComp projections at both acquisition handoffs')
    for row,plan,p in zip(projections,r['source_acquisition']['passes'],r['passes']):
        times=[plan['enter'][1],plan['hit'][1],plan['confirm'][1],p['lift'][1]]
        if row['kind']!=p['kind'] or len(row['samples'])!=len(times):
            raise ValueError('Projection readback missing')
        for sample,time in zip(row['samples'],times):
            b=sample['source']
            if (abs(sample['time']-time)>.001 or not all(math.isfinite(v) for k in ('min','max') for v in b[k])
                    or b['min'][0]<100 or b['max'][0]>1820 or b['min'][1]<165 or b['max'][1]>930):
                raise ValueError('Acquisition text clips outside the readable native viewport')
    return g


def validate_acquisition_camera(actual, plan, hit):
    depth=-2000 if plan['kind']=='fast' else -1940
    for key in ('lock_camera','settled_camera'):
        c=actual[key]
        if (not close_vectors(c['look'],hit) or not close_vectors(c['focus'],hit)
                or not close_vectors(c['position'],[hit[0]+30,hit[1]+15,depth])):
            raise ValueError('Camera and focus must acquire and hold the actual keyword')
    c=actual['lift_camera'];depth=-1960 if plan['kind']=='fast' else -1880
    if (not close_vectors(c['position'],[820,410,depth]) or not close_vectors(c['look'],[800,420,-140])
            or not close_vectors(c['focus'],[800,420,-140])):
        raise ValueError('Lift must reach the accepted camera before the first word cue')
    for key in ('lock_camera','settled_camera','lift_camera'):
        c=actual[key];distance=math.dist(c['focus'],c['position'])
        if (c['dof']!=1 or c['zoom']!=1950 or c['aperture']!=40 or c['focus_error']
                or abs(c['focus_distance']-distance)>.02):
            raise ValueError('Read actual native DOF and focus distance, without obscuring the source')
    curves=actual.get('curves',[]);times=[plan['enter'][0],plan['enter'][1],plan['browse'][1],plan['hit'][1]]
    if len(curves)!=3:
        raise ValueError('Read actual camera and focus curves')
    for keys in curves:
        if (len(keys)!=4 or any(abs(key['time']-time)>.001 for key,time in zip(keys,times))
                or keys[0]['out_speed']!=0 or keys[-1]['in_speed']!=0
                or any(keys[i]['out_speed']<=0 for i in (1,2))
                or keys[1]['out_influence']!=25 or keys[-1]['in_influence']!=70):
            raise ValueError('Navigate must continue through Browse and decelerate into Lock')


def validate_native(r, native):
    validate_acquisition(r)
    if (native['spec_sha'] != r['spec_sha'] or native['trajectory_sha'] != r['trajectory_sha']
            or native['canvas'] != [1920,1080,24,r['duration']]
            or native['renderer'] != 'ADBE Advanced 3d'
            or native['production_eligible'] is not False or native['public_render_ready'] is not False):
        raise ValueError('Wrong native identity, canvas or research scope')
    expected = {o['id']:o['text'] for o in r['layout']}
    expected.update({p['id']:p['text'] for o in r['options'] for p in o['pieces']})
    rows = native['objects']
    if (len(rows) != len(expected) or {x['id']:x['text'] for x in rows} != expected
            or any(not x['threeD'] or x['source_text_keys'] for x in rows)
            or any(x['font']!=r['fixture']['font']['english'] or x['font_size']!=r['fixture']['font']['size'] for x in rows)
            or any(x['origin_sha'] != r['fixture_sha'] for x in rows)):
        raise ValueError('One enduring native object per frozen source; no text substitution')
    handles = {x['id']:x['native_layer_id'] for x in rows}
    if len(set(handles.values())) != len(expected):
        raise ValueError('Distinct semantic objects require distinct native identities')
    if 'question' in native and (native['question']['text'] != r['fixture']['stem']
                                or native['question']['source_text_keys']):
        raise ValueError('Keep the original bound question unchanged across both passes')
    if [p['kind'] for p in native['passes']] != [p['kind'] for p in r['passes']]:
        raise ValueError('Every directed pass needs its own complete native audit')
    for state in native['passes']:
        if state['handles'] != handles: raise ValueError('An object was replaced between methods or passes')
        if any(not 99.999 <= x['core_opacity'] <= 100.001 for x in state['checks']):
            raise ValueError('Retained basis must survive each relay')
        if any(x['value'] < 65 for x in state['retained_opacities']): raise ValueError('Do not hide the retained basis')
        columns=state['column_alignment']
        if (len(columns)!=12 or {x['id'] for x in columns}!=set(expected)-{o['id'] for o in r['layout']}
                or any(not math.isfinite(x['dx']) or abs(x['dx'])>.15 for x in columns)):
            raise ValueError('Native source and option columns do not align')
        expected_y={o['id']:o['comparison_y'] for o in r['options']}
        if ({x['id'] for x in state['option_rows']}!=set(expected_y)
                or len(state['option_rows'])!=len(expected_y)
                or any(abs(x['y']-expected_y[x['id']])>.15 for x in state['option_rows'])):
            raise ValueError('Native option rows overlap or diverge from frozen geometry')
        if (len(state['peels']) != 2 or {x['id'] for x in state['peels']} != {'aside-time','aside-map'}
                or any(x['onset'] is None or x['release'] is None
                       or abs(x['detach_seconds']-.25) > 1/(24*1024)+1e-8 for x in state['peels'])):
            raise ValueError('Native peel must execute the brief physical release')
    if r['phase']=='full':
        restoration=native.get('rewind_restore',[])
        if not restoration:raise ValueError('Read back physical restoration before Guided')
        for row in restoration:
            a=row['initial'] if isinstance(row['initial'],list) else [row['initial']]
            b=row['restored'] if isinstance(row['restored'],list) else [row['restored']]
            if len(a)!=len(b) or any(abs(x-y)>.001 for x,y in zip(a,b)):
                raise ValueError('Rewind must restore original objects before Guided')
    if native['visible_internal_method_ids']: raise ValueError('Internal method numbers must not be visible')
    if native['name_counts'] != {m['method_id']:1 for m in r['method_names']}:
        raise ValueError('Each method gets one small name per complete film')
    if r['phase']=='full' and 'guided_method_copy' in r['fixture']:
        guide=r['fixture']['guided_method_copy'];actual=native.get('method_guidance') or {}
        labels=actual.get('column_labels',[])
        if (len(labels)!=3 or [x['text'] for x in labels]!=[x['text'] for x in guide['column_labels']]
                or any(x['font']!=r['fixture']['font']['chinese'] or x['source_text_keys']
                       or abs(x['x']-r['comparison_columns'][expected['part']])>.15
                       or x['fast_opacity']!=0 or x['guided_opacity']<60
                       for x,expected in zip(labels,guide['column_labels']))):
            raise ValueError('The three comparison headers must bind their columns and stay out of Fast')
        samples=actual.get('subject_emphasis',[])
        w=guide['emphasis']['window'];times=[w[0]+.25,(w[0]+w[1])/2,w[1]-.25]
        if len(samples)!=3 or any(x['opacity']<20 or abs(x['time']-t)>.001 for x,t in zip(samples,times)):
            raise ValueError('Keep actor emphasis across the supplied spoken phrase window')
    if 'source_acquisition' in r:
        a=native.get('source_acquisition')
        if not a or a['version']!='0.2.0' or len(a['passes'])!=2:
            raise ValueError('Read the actual acquisition states, not just the intended timeline')
        geometry=native_acquisition_geometry(r,a,handles) if r.get('native_acquisition_geometry') else None
        for actual,plan in zip(a['passes'],r['source_acquisition']['passes']):
            if actual['kind']!=plan['kind'] or actual['pre_hit']['source_mark']!=0 or actual['pre_hit']['sentence_scope']!=0:
                raise ValueError('Source evidence cannot be marked before the directed hit')
            if any(c['opacity']<99.9 or c['font_size']!=40 or c['z']!=0 for c in actual['pre_hit']['contexts']):
                raise ValueError('Do not preselect evidence by degrading its context')
            if actual['hit']['source_mark']<15 or actual['hit']['sentence_scope']!=0:
                raise ValueError('Word-group hit precedes whole-sentence confirmation')
            if actual['confirm']['sentence_scope']<40 or actual['confirm']['reader_guide']!=0:
                raise ValueError('Reading guide must hand off to the acquired sentence')
            center=r['locate_geometry']['source_x']+r['locate_geometry']['source_width']/2
            end=r['layout'][-1]['x']+r['layout'][-1]['width']
            left,y=190,472
            if geometry:
                center=geometry['keyword']['center'][0];left=geometry['sentence']['min'][0]
                end=geometry['sentence']['max'][0];y=geometry['sentence']['max'][1]+9
                validate_acquisition_camera(actual,plan,geometry['keyword']['center'])
            if (len(actual['scope_start'])!=2 or len(actual['scope_end'])!=2
                    or any(not close_vectors(v,[center,y]) for v in actual['scope_start'])
                    or any(not close_vectors(v,expected) for v,expected in zip(actual['scope_end'],[[left,y],[end,y]]))):
                raise ValueError('Confirm the whole original sentence outward from the literal hit')
            if any(c['font_size']!=32 or abs(c['opacity']-15)>.001 or abs(c['z']-expected)>.001
                   for c,expected in zip(actual['confirm']['contexts'],(130,180))):
                raise ValueError('Context must converge to the accepted later composition')
            if actual['peel']['source_mark']!=0 or actual['peel']['reader_guide']!=0 or actual['peel']['sentence_scope']!=0:
                raise ValueError('Search markings must not compete with the first peel')
        restoration=a['rewind_restore']
        if (len(restoration)!=2 or any(x['opacity']!=100 or x['font_size']!=40 or x['z']!=0
                                      for x in restoration)):
            raise ValueError('Restore the new unselected source context before Guided')
        if any(a['rewind_marks'][k]!=0 for k in ('source_mark','sentence_scope','reader_guide')):
            raise ValueError('Clear acquisition markings before Guided')
        if (len(a['focus_restore'])!=2 or [x['name'] for x in a['focus_restore']]!=['FOCUS_TARGET','GUIDED_CAMERA']
                or any(abs(x-y)>.001 for row in a['focus_restore'] for x,y in zip(row['initial'],row['restored']))):
            raise ValueError('Restore focus and camera direction before Guided')
        for state in a['passes']:
            for phase in ('pre_hit','hit','confirm','peel'):
                if len(state[phase]['contexts'])!=2:
                    raise ValueError('Read both contexts at each acquisition handoff')
                for c,text in zip(state[phase]['contexts'],r['fixture']['context']):
                    if c['text']!=text or any(value!=text for value in c['key_texts']):
                        raise ValueError('Context styling cannot substitute source characters')
    return native


def preview(output):
    r = current(output); c = client(); identity = read(output/'identity.json'); folder = output/'previews'; folder.mkdir(exist_ok=True)
    times = [0]
    for p in r['passes']:
        times += [p['locate'][1],p['lift'][1],p['peel_a'][2],p['peel_a'][4],p['peel_b'][4],p['align'][1],p['compare'][1],p['verify'][1]]
    if len(times)>16: times=times[1:]
    if 'source_acquisition' in r:
        times=[]
        for a,p in zip(r['source_acquisition']['passes'],r['passes']):
            times += [a['target'][0]+.3,a['enter'][0]+.05,a['enter'][1]-.02,a['browse'][1]-.02,
                      a['hit'][1]-.02,sum(a['confirm'])/2,sum(p['lift'])/2,p['peel_b'][4]+.15]
    result = c.call('ae_previewFrame', {'comp_id':str(identity['comp_id']), 'times':times,
        'layout':'grid', 'grid_max_side':2048, 'out_dir':str(folder)}, timeout=180)
    # Never print inline base64; paths and native capture receipt are sufficient.
    write(output/'preview.json', result); return result


ACQUISITION_RANGES={'FAST_ACQUISITION':(36,150),'GUIDED_ACQUISITION':(384,625)}


def render_span(r,label):
    if label in ACQUISITION_RANGES:
        if not r.get('native_acquisition_geometry'):
            raise ValueError('Acquisition P0 ranges require the geometry-bound v0.2 request')
        start,end=ACQUISITION_RANGES[label]
        return {'start':start/24,'duration':(end-start)/24,'frame_range':[start,end],'frames':end-start}
    if label != ('P0' if r['phase']=='p0' else 'DUAL'):
        raise ValueError('Exact directed complete phase or acquisition P0 range required')
    return {'start':0,'duration':r['duration'],'frame_range':[0,round(r['duration']*24)],'frames':round(r['duration']*24)}


def require_acquisition_review(output,r,label):
    if not r.get('native_acquisition_geometry') or label in ACQUISITION_RANGES:
        return
    review=read(output/'acquisition-human-review.json')
    expected={}
    for key in ACQUISITION_RANGES:
        receipt=read(output/('render-receipt-'+key+'.json'))
        if receipt['spec_sha']!=r['spec_sha'] or file_sha(receipt['output'])!=receipt['output_sha']:
            raise ValueError('Human review requires the current P0 movies')
        expected[key]=receipt['output_sha']
    if (review.get('spec_sha')!=r['spec_sha'] or review.get('reviewer_type')!='human'
            or review.get('status')!='PASS' or not review.get('feedback')
            or review.get('p0_clip_shas')!=expected):
        raise ValueError('P2 requires explicit human visual approval bound to both new P0 movies')


def render(output, label='P0'):
    r = current(output); audit(output); identity = read(output/'identity.json'); c = client()
    span=render_span(r,label);require_acquisition_review(output,r,label)
    target=output/(label+'.mp4'); frames=output/('frames-'+label)
    if target.exists() or frames.exists(): raise FileExistsError('Never overwrite a previous film')
    frames.mkdir()
    code='''(function(){var cp=AEMCP.compById(COMP);for(var i=1;i<=app.project.renderQueue.numItems;i++){var e=app.project.renderQueue.item(i);if(e.render&&e.status===RQItemStatus.QUEUED)throw new Error('Unrelated queued render');}var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var j=0;j<o.templates.length;j++)if(o.templates[j].indexOf('TIFF')!==-1){preset=o.templates[j];break;}if(!preset)throw new Error('Native TIFF unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=DURATION;app.project.save();app.setMultiFrameRenderingConfig(false,100);var begin=(new Date()).getTime();app.project.renderQueue.render();app.project.save();return JSON.stringify({done:q.status===RQItemStatus.DONE,renderer:cp.renderer,preset:preset,render_ms:(new Date()).getTime()-begin,comp_id:cp.id,start:q.timeSpanStart,duration:q.timeSpanDuration});})();'''
    code=code.replace('COMP',str(identity['comp_id'])).replace('DEST',json.dumps((frames/'FRAME_[#####].tif').as_posix())).replace('START',str(span['start'])).replace('DURATION',str(span['duration']))
    # Native render resets Undo; a surrounding Undo group can cause a modal.
    native = mutation_call(c,'ae_exec',{'code':code,
        'checkpoint_label':'before-relay-render-'+label,'timeout_sec':600},output,630)
    write(output/('native-render-'+label+'.json' if label in ACQUISITION_RANGES else 'native-render.json'),native)
    return package_render(output,label,json.loads(native['content']))


def finish(output,label,recovery_id):
    """Reconcile a completed queue after an official uncertain dispatch. Never rerender."""
    r=current(output);span=render_span(r,label);require_acquisition_review(output,r,label);failure=read(output/'last-mutation-failure.json')
    if (not recovery_id or failure['tool']!='ae_exec'
            or failure['result'].get('recoveryId')!=recovery_id):
        raise ValueError('Use the exact issued recovery ID from the recorded render failure')
    target=output/(label+'.mp4');frames=output/('frames-'+label)
    if target.exists() or not frames.is_dir():raise ValueError('Reconcile existing frames without overwriting a movie')
    write(output/'reconciled-render-failure.json',failure)
    identity=read(output/'identity.json');c=client()
    code='''(function(){var cp=AEMCP.compById(COMP),q=null,expected=new File(PROJECT),dir=new Folder(DIR);
    if(!app.project.file||app.project.file.fsName!==expected.fsName||JSON.parse(cp.comment).spec_sha!==SPEC)throw new Error('Wrong frozen project');
    for(var i=1;i<=app.project.renderQueue.numItems;i++){var candidate=app.project.renderQueue.item(i);if(candidate.comp.id===cp.id&&candidate.status===RQItemStatus.DONE&&Math.abs(candidate.timeSpanStart-START)<.0001&&Math.abs(candidate.timeSpanDuration-DURATION)<.0001&&candidate.outputModule(1).file.parent.fsName===dir.fsName)q=candidate;}
    if(!q)throw new Error('No completed native queue matching frozen frames');app.project.save(expected);
    return JSON.stringify({done:true,renderer:cp.renderer,preset:null,render_ms:null,comp_id:cp.id,start:q.timeSpanStart,duration:q.timeSpanDuration,output_module_file:q.outputModule(1).file.fsName,reconciled_completed_queue:true,no_rerender:true});})();'''
    for key,value in {'COMP':str(identity['comp_id']),'PROJECT':json.dumps(Path(r['project']).as_posix()),
                      'DIR':json.dumps(frames.as_posix()),'SPEC':json.dumps(r['spec_sha']),'START':str(span['start']),'DURATION':str(span['duration'])}.items():
        code=code.replace(key,value)
    result=mutation_call(c,'ae_execRecover',{'recoveryId':recovery_id,'retryMode':'continue',
        'code':code,'undo_group_name':'Reconcile completed Method Relay render','timeout_sec':90},output,120)
    write(output/('native-render-'+label+'.json' if label in ACQUISITION_RANGES else 'native-render.json'),result);audit(output)
    return package_render(output,label,json.loads(result['content']))


def package_render(output,label,rendered):
    r=current(output);target=output/(label+'.mp4');frames=output/('frames-'+label)
    span=render_span(r,label);require_acquisition_review(output,r,label)
    if target.exists():raise ValueError('Package without overwriting a previous movie')
    if label in ACQUISITION_RANGES and (abs(rendered.get('start',-1)-span['start'])>.0001
            or abs(rendered.get('duration',-1)-span['duration'])>.0001):
        raise ValueError('Native queue must render the exact directed P0 frame range')
    paths=sorted(frames.glob('*.tif'))
    expected=span['frames']; matches=[re.fullmatch(r'(.*?)(\d+)\.tif',p.name) for p in paths]
    if (not rendered['done'] or len(paths)!=expected or any(x is None for x in matches)):
        raise ValueError('Incomplete native frame sequence')
    first=int(matches[0][2])
    if [int(x[2]) for x in matches]!=list(range(first,first+expected)): raise ValueError('Native frame gap')
    pattern=frames/(matches[0][1]+'%0'+str(len(matches[0][2]))+'d.tif')
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','24','-start_number',str(first),'-i',str(pattern),
        '-frames:v',str(expected),'-an','-c:v','libx264','-threads','4','-crf','16','-pix_fmt','yuv420p',str(target)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    snapshot=output/('PROJECT_'+label+'.aep');shutil.copy2(r['project'],snapshot)
    archive=output/('NATIVE_TIFF_'+label+'.zip'); manifest={p.name:file_sha(p) for p in paths}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        for name,expected_sha in manifest.items():
            with z.open(name) as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=expected_sha: raise ValueError('Native archive mismatch')
    manifest_file=output/('native-frame-shas-'+label+'.json' if label in ACQUISITION_RANGES else 'native-frame-shas.json')
    write(manifest_file,manifest)
    for p in paths:
        if p.resolve().parent!=frames.resolve() or not p.resolve().is_relative_to(LOCAL): raise ValueError('Unsafe generated frame path')
    for p in paths:p.unlink()
    receipt={'kind':'synthetic_native_method_relay','phase':r['phase'],'spec_sha':r['spec_sha'],
        'trajectory_sha':r['trajectory_sha'],'project':str(snapshot),'project_sha':file_sha(snapshot),
        'output':str(target),'output_sha':file_sha(target),'duration':span['duration'],'frames':expected,
        'absolute_span':[span['start'],span['start']+span['duration']],'frame_range':span['frame_range'],
        'native':rendered,'archive_sha':file_sha(archive),'frame_manifest_sha':file_sha(manifest_file),
        'human_viewing_review':'PENDING','production_eligible':False,'public_render_ready':False}
    receipt_file=output/('render-receipt-'+label+'.json' if label in ACQUISITION_RANGES else 'render-receipt.json')
    write(receipt_file,receipt);return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('build','audit','preview','render','finish'))
    p.add_argument('output');p.add_argument('--phase',choices=('p0','full'),default='p0');p.add_argument('--label',choices=('P0','DUAL',*ACQUISITION_RANGES),default='P0')
    p.add_argument('--p0',help='Completed native P0 directory; required for full assembly')
    p.add_argument('--acquisition-v2',action='store_true',help='Independent v0.2 source evidence acquisition director')
    p.add_argument('--recovery-id',help='Exact server-issued render failure ID; finish reconciles existing DONE queue only')
    a=p.parse_args();output=local(a.output)
    if a.operation=='build':result=build(output,a.phase,a.p0,a.acquisition_v2)
    elif a.operation=='render':result=render(output,a.label)
    elif a.operation=='finish':result=finish(output,a.label,a.recovery_id)
    else:result=globals()[a.operation](output)
    if a.operation=='preview':print(json.dumps({'saved':str(output/'preview.json')},ensure_ascii=True))
    else:print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__': main()
