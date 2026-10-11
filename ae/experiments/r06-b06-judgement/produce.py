"""Bounded B06 production from an explicit phrase review and existing G0 handoff.

Real source/layout inputs and all media remain under ignored local-data. This
entry point consumes the prior handoff; it does not rerun the original G0.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from video_contracts import read, write, sha, pointer
from content_os.showcase import file_sha
from ae_production.phrase_consumer import consume_phrase_review
from ae_production.judgement_preflight import candidate_prefix
from ae_production.host_ownership import HostOwnership
from ae_production.bridge import JunkdogeClient
from ae_production.memory_guard import monitor_existing_render, available_memory

HERE = Path(__file__).resolve().parent
FPS = 24


def local(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / 'local-data').resolve()):
        raise ValueError('Private production stays under ignored local-data')
    return path


def review_current(folder):
    inputs = read(folder / 'REVIEW_INPUTS.json')
    bundle = read(inputs['bundle']); status = read(inputs['status'])
    receipt = consume_phrase_review(read(inputs['request']), read(folder / 'HOST_PHRASE_REVIEW.json'),
        read(folder / 'HOST_PHRASE_REVIEW_STATUS.json'), {bundle['asset_id']: bundle},
        {bundle['asset_id']: status}, read(folder / 'BOUNDED_G2_PLAN.json'))
    if receipt['gate'] != 'READY_FOR_BOUNDED_G2':
        raise ValueError('G2 HOLD: ' + ', '.join(receipt['reasons']))
    if receipt != read(folder / 'G2_CONSUMPTION_RECEIPT.json'):
        raise ValueError('Current review differs from the frozen G2 consumption')
    return inputs, bundle, receipt


def last_value(rows, time, default):
    prior = [row[1] for row in rows if row[0] <= time + 1e-5]
    return deepcopy(prior[-1] if prior else rows[0][1] if rows else default)


def retime(value, cut, extra):
    return value + extra if value >= cut - 1e-5 else value


def set_window(node, prop, start, end, interior, fallback):
    rows = node['tracks'].get(prop, [])
    before = last_value(rows, start, fallback)
    after = last_value(rows, end, fallback)
    # Native time keys are unique; authored boundary values may deliberately
    # replace the baseline boundary, but never add two nearly equal AE keys.
    combined = sorted([row for row in rows if row[0] < start - 1e-5 or row[0] > end + 1e-5]
        + [[start, before], *interior, [end, after]], key=lambda row: row[0])
    unique = []
    for row in combined:
        if unique and abs(unique[-1][0] - row[0]) < 1e-5:
            unique[-1] = row
        else:
            unique.append(row)
    node['tracks'][prop] = unique


def rgb(hex_color):
    return [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]


def validate_visual_operations(visual, review):
    operations = {d['operation_id']: d for d in review['decisions']}
    if set(g['operation_id'] for g in visual['groups']) != set(operations):
        raise ValueError('Each exact reviewed operation requires a visual group')
    for group in visual['groups']:
        operation = operations[group['operation_id']]
        if not {'focus_in_context','move_as_group','compare_bound_relation'} <= set(operation['execution']['primitives']):
            raise ValueError('The actual native focus/move/comparison is not authorized')
        selection = operation['selection']
        for line in group['lines']:
            if line['emphasize'] and not selection['start'] <= line['range'][0] < line['range'][1] <= selection['end']:
                raise ValueError('Visual emphasis escapes its exact reviewed semantic selection')


def prepare(folder, baseline, visual_path):
    folder, baseline = local(folder), local(baseline)
    inputs, bundle, consumption = review_current(folder)
    if (folder / 'PRODUCTION.json').exists():
        raise FileExistsError('Choose a new production revision')
    handoff = Path(inputs['handoff']); index = read(handoff / 'PRODUCTION_INDEX.json')
    preparation = read(handoff / 'PREPARATION_RECEIPT.json')
    for name, expected in preparation['artifacts'].items():
        if file_sha(handoff / name) != expected:
            raise ValueError('Existing G0/G1 handoff changed: ' + name)
    old_request = read(baseline / 'native-request.json'); old = old_request['spec']
    for path in (baseline / 'native-request.json', Path(old_request['project'])):
        if file_sha(path) != index['input_files'][str(path.resolve())]:
            raise ValueError('Bound baseline production changed')
    episode = read(old_request['episode_plan'])
    bundles = {b['asset_id']: b for q in episode['questions'] for b in q['package']['source_items']}
    prefix = candidate_prefix(old, bundles, 'B06')
    if prefix != read(handoff / 'CANDIDATE_PREFIX.json'):
        raise ValueError('Whole ordered candidate prefix changed')
    boundaries = read(handoff / 'EXCERPT_BOUNDARIES.json')
    visual = read(visual_path)
    validate_visual_operations(visual,read(folder/'HOST_PHRASE_REVIEW.json'))
    if (visual['review_sha'] != consumption['review_sha'] or visual['scene_id'] != 'B06'
            or type(visual['extra_hold_frames']) is not int or not 0 <= visual['extra_hold_frames'] <= 240):
        raise ValueError('Explicit bounded reviewed visual direction required')
    extra = visual['extra_hold_frames'] / FPS
    selected = next(e for e in old['events'] if e['scene_id'] == 'B06')
    cut = selected['decision_start']; start, original_end = [x / FPS for x in boundaries['pure_original_frames']]
    end = original_end + extra
    spec = deepcopy(old)
    spec['canvas']['duration'] += extra
    spec['parent_spec_sha'] = old['spec_sha']
    spec['phrase_review_sha'] = consumption['review_sha']
    for node in spec['nodes']:
        node['in_point'] = retime(node['in_point'], cut, extra)
        node['out_point'] = retime(node['out_point'], cut, extra)
        for rows in node['tracks'].values():
            for row in rows: row[0] = retime(row[0], cut, extra)
    for row in spec['camera']['position']: row[0] = retime(row[0], cut, extra)
    for event in spec['events']:
        for field in ('compare_start', 'decision_start', 'decision_end', 'confirmation_start'):
            event[field] = retime(event[field], cut, extra)
    for answer in spec['answer_confirmations']: answer['time'] = retime(answer['time'], cut, extra)
    spec['preview_times'] = [start + x / FPS for x in visual['preview_local_frames']]
    # Complete candidate history remains in the audit even though only an
    # excerpt is rendered. Retain C never becomes eliminate D or final answer.
    new_prefix = candidate_prefix(spec, bundles, 'B06')
    if new_prefix['selected']['before'] != ['B', 'C', 'D'] or new_prefix['selected']['after'] != ['C', 'D']:
        raise ValueError('B06 must consume the actual complete prior action chain')
    from PIL import ImageFont
    font_path = Path(visual['geometry_font'])
    node_by_id = {n['node_id']: n for n in spec['nodes']}
    operations = {r['operation_id']: r for r in read(folder / 'HOST_PHRASE_REVIEW.json')['decisions']}
    carriers, changed, covered_contexts = [], set(), {}
    for group in visual['groups']:
        operation = operations[group['operation_id']]
        context = operation['execution']['keep_context'][0]
        ref = context['source_ref']; source = pointer(bundle, ref['pointer'])
        for line in group['lines']:
            left, right = line['range']
            if not context['start'] <= left < right <= context['end']:
                raise ValueError('Layout line escapes explicitly reviewed grammatical context')
            matches = [n for n in spec['nodes'] if n['node_id'].startswith('source:')
                and ref in n['source_refs'] and n['start'] < right and n['end'] > left]
            matches.sort(key=lambda n: n['start'])
            covered = set()
            for n in matches:
                outside = source[n['start']:left] if n['start'] < left else ''
                outside += source[right:n['end']] if n['end'] > right else ''
                if outside and (n is not matches[-1] or outside not in ('.', ',', ';', ':', '!', '?')):
                    raise ValueError('Existing native carrier crosses the reviewed semantic range')
                covered.update(range(max(left, n['start']), min(right, n['end'])))
            if any(i not in covered for i in range(left, right) if not source[i].isspace()):
                raise ValueError('Native original glyph objects do not cover the requested line')
            face = ImageFont.truetype(str(font_path), line['size'])
            if line['position'][0] + face.getlength(source[left:right]) > 3580:
                raise ValueError('Reviewed line exceeds the native right reading margin')
            cursor = line['position'][0]
            focus = start + group['focus_frame'] / FPS
            settle = start + visual['difference_frame'] / FPS
            settle_end = settle + visual['regroup_frames'] / FPS
            decision = cut + extra
            for n in matches:
                if n['node_id'] in changed:
                    raise ValueError('Each original glyph has one authored motion owner')
                changed.add(n['node_id'])
                covered_contexts.setdefault(ref['pointer'], set()).update(range(n['start'], n['end']))
                shape = len(last_value(n['tracks']['position'], start, n['position']))
                at = [cursor, line['position'][1]] + ([0] if shape == 3 else [])
                delta = line.get('regroup_delta', [0, 0])
                grouped = [at[0] + delta[0], at[1] + delta[1]] + ([0] if shape == 3 else [])
                scale = [line['size'] / n['size'] * 100] * 3
                position_rows = [[start + 20/FPS, at], [settle, at], [settle_end, grouped],
                    [decision, grouped]]
                opacity_rows = [[start + 20/FPS, line.get('initial_opacity', 48)],
                    [focus, line.get('initial_opacity', 48)], [focus + 14/FPS, line.get('focus_opacity', 100)],
                    [decision, line.get('focus_opacity', 100)]]
                scale_rows = [[start + 20/FPS, scale], [decision, scale]]
                color_rows = [[start, rgb(spec['palette']['ink'])], [focus, rgb(spec['palette']['ink'])],
                    [focus + 14/FPS, rgb(spec['palette']['blue'] if line['emphasize'] else spec['palette']['ink'])],
                    [decision, rgb(spec['palette']['blue'] if line['emphasize'] else spec['palette']['ink'])]]
                if ref['pointer'].startswith('/source_snapshot/options/'):
                    for prop, rows, fallback in [('position', position_rows, at), ('scale', scale_rows, scale),
                                                 ('opacity', opacity_rows, 100), ('color', color_rows, rgb(n['color']))]:
                        original_rows = node_by_id[n['node_id']]['tracks'].get(prop, [])
                        rows.append([decision + 15/FPS, last_value(original_rows, decision + 15/FPS, fallback)])
                        rows.append([end - 1/FPS, last_value(original_rows, end - 1/FPS, fallback)])
                else:
                    position_rows.append([end - 20/FPS, grouped]); scale_rows.append([end - 20/FPS, scale])
                    opacity_rows.append([end - 20/FPS, line.get('focus_opacity', 100)])
                    color_rows.append([end - 20/FPS, rgb(spec['palette']['blue'] if line['emphasize'] else spec['palette']['ink'])])
                for prop, rows, fallback in [('position', position_rows, at), ('scale', scale_rows, scale),
                                             ('opacity', opacity_rows, 100), ('color', color_rows, rgb(n['color']))]:
                    set_window(n, prop, start, end, rows, fallback)
                carriers.append({'node_id': n['node_id'], 'operation_id': group['operation_id'],
                    'semantic_range': [max(n['start'], operation['selection']['start']), min(n['end'], operation['selection']['end'])]
                        if n['start'] < operation['selection']['end'] and n['end'] > operation['selection']['start'] else None,
                    'native_carrier_range': [n['start'], n['end']],
                    'retained_terminal_punctuation': source[right:n['end']] if n['end'] > right else '',
                    'source_ref': ref, 'text': n['text'], 'context_only': not line['emphasize']})
                cursor += face.getlength(n['text'] + ' ')
    if set(g['operation_id'] for g in visual['groups']) != set(operations):
        raise ValueError('Each reviewed phrase operation requires an actual bound native group')
    for operation in operations.values():
        context = operation['execution']['keep_context'][0]
        source = pointer(bundle, context['source_ref']['pointer'])
        coverage = covered_contexts[context['source_ref']['pointer']]
        if any(i not in coverage for i in range(context['start'], context['end']) if not source[i].isspace()):
            raise ValueError('All explicitly preserved grammatical context must remain visible')
    # One restrained native bracket groups the already reviewed problem and
    # response; it introduces neither labels nor a new English relation.
    spec['reviewed_connector'] = {
        'node_id': 'B06_REVIEWED_PROBLEM_RESPONSE',
        'review_sha': consumption['review_sha'],
        'operation_ids': ['screen_problem', 'nature_response'],
        'relation_ref': read(folder/'HOST_PHRASE_REVIEW.json')['binding']['relation_ref'],
        'points': visual['relationship_bracket'],
        'color': spec['palette']['blue'], 'stroke': 3,
        'opacity': [[start, 0], [start+visual['relationship_frame']/FPS, 0],
            [start+(visual['relationship_frame']+24)/FPS, 60], [end-20/FPS, 60], [end, 0]]}
    # Auxiliary evidence stays as the already present reading surface. It does
    # not compete with the two relationship objects at equal salience.
    for n in spec['nodes']:
        if (n['node_id'].startswith('source:passage:') and n['node_id'] not in changed
                and any(r['asset_id'] == bundle['asset_id'] for r in n['source_refs'])):
            raw = n['position']
            set_window(n, 'position', start, end, [[start+20/FPS, raw], [end-20/FPS, raw]], raw)
            set_window(n, 'scale', start, end, [[start+20/FPS, [100]*3], [end-20/FPS, [100]*3]], [100]*3)
            set_window(n, 'opacity', start, end, [[start+20/FPS, 4], [end-20/FPS, 4]], 4)
    for n in spec['nodes']:
        for prop, rows in n['tracks'].items():
            if any(a[0] >= b[0] for a, b in zip(rows, rows[1:])):
                raise ValueError('Motion keys must be uniquely ordered: ' + n['node_id'] + ':' + prop)
    spec.pop('spec_sha', None); spec['spec_sha'] = sha(spec)
    voices = []
    for source in old_request['voices']:
        if source['start'] >= boundaries['context_original_frames'][0]/FPS and source['end'] <= boundaries['context_original_frames'][1]/FPS:
            if file_sha(source['path']) != source['sha256']:
                raise ValueError('Frozen voice bytes changed')
            with wave.open(source['path'], 'rb') as wav:
                if wav.getnframes() != round(source['duration'] * 48000):
                    raise ValueError('Voice sample count changed')
            voices.append({**source, 'original_start': source['start'], 'original_end': source['end'],
                'start': retime(source['start'], cut, extra), 'end': retime(source['end'], cut, extra)})
    production = {'kind': 'bounded_b06_native_production', 'revision_id': folder.name,
        'baseline_folder': str(baseline), 'baseline_project': old_request['project'],
        'baseline_project_sha': file_sha(old_request['project']), 'baseline_spec_sha': old['spec_sha'],
        'baseline_comp_id': read(baseline/'native-identity.json')['comp_id'],
        'baseline_request_sha': file_sha(baseline/'native-request.json'),
        'baseline_picture': read(baseline/'PICTURE_RECEIPT.json'),
        'spec_sha': spec['spec_sha'], 'review_receipt_sha': consumption['receipt_sha'],
        'visual_path': str(Path(visual_path).resolve()), 'visual_sha': file_sha(visual_path),
        'geometry_font': str(font_path), 'geometry_font_sha': file_sha(font_path),
        'executor_sha': file_sha(HERE/'build.jsx'),
        'project': str(folder / 'B06_JUDGEMENT_NATIVE_4K.aep'),
        'bounds': {'old_pure': boundaries['pure_original_frames'], 'old_context': boundaries['context_original_frames'],
            'new_pure': [boundaries['pure_original_frames'][0], boundaries['pure_original_frames'][1]+visual['extra_hold_frames']],
            'new_context': [boundaries['context_original_frames'][0], boundaries['context_original_frames'][1]+visual['extra_hold_frames']]},
        'insert': {'original_frame': round(cut*FPS), 'frames': visual['extra_hold_frames']},
        'voices': voices, 'full_candidate_prefix_audit': new_prefix,
        'scope': 'SIX_BOUNDED_AB_EXCERPTS_ONLY', 'actual_media_mapping': 'PENDING_NATIVE_MEDIA',
        'G3': 'NOT_STARTED', 'human_visual_review': 'PENDING', 'human_listening_review': 'PENDING',
        'public_render_ready': False}
    production['production_sha'] = sha(production)
    write(folder/'NEW_NATIVE_SPEC.json', spec); write(folder/'PRODUCTION.json', production)
    write(folder/'NATIVE_PHRASE_CARRIERS.json', {'review_sha': consumption['review_sha'], 'carriers': carriers,
        'original_native_text_objects_preserved': True, 'public_render_ready': False})
    return {'prepared': str(folder), 'new_pure_frames': round((end-start)*FPS), 'carriers': len(carriers)}


def current(folder):
    review_current(folder); p = read(folder/'PRODUCTION.json'); s = read(folder/'NEW_NATIVE_SPEC.json')
    validate_visual_operations(read(p['visual_path']),read(folder/'HOST_PHRASE_REVIEW.json'))
    if (p['production_sha'] != sha({k:v for k,v in p.items() if k!='production_sha'})
            or s['spec_sha'] != p['spec_sha'] or s['spec_sha'] != sha({k:v for k,v in s.items() if k!='spec_sha'})
            or file_sha(p['visual_path']) != p['visual_sha'] or file_sha(p['geometry_font']) != p['geometry_font_sha']
            or file_sha(p['baseline_project']) != p['baseline_project_sha']
            or file_sha(Path(p['baseline_folder'])/'native-request.json') != p['baseline_request_sha']
            or file_sha(HERE/'build.jsx') != p['executor_sha'] or p['public_render_ready'] is not False):
        raise ValueError('Bound production input changed')
    baseline = read(Path(p['baseline_folder'])/'native-request.json')
    from creative_os.episode import validate_episode
    episode = read(baseline['episode_plan'])
    statuses = {key: read(path) for key, path in baseline['statuses'].items()}
    if validate_episode(episode, statuses)['engineering_status'] != 'PASS':
        raise ValueError('Current complete episode source dependencies changed')
    bundles = {b['asset_id']: b for q in episode['questions'] for b in q['package']['source_items']}
    if candidate_prefix(s, bundles, 'B06') != p['full_candidate_prefix_audit']:
        raise ValueError('Current full candidate history changed')
    original = {n['node_id']: n for n in baseline['spec']['nodes']}
    if set(original) != {n['node_id'] for n in s['nodes']}:
        raise ValueError('Original native object identity changed')
    for n in s['nodes']:
        if any(n.get(k) != original[n['node_id']].get(k) for k in ('text','start','end','source_refs','origin_object_id','font')):
            raise ValueError('Original source text identity changed')
    for voice in p['voices']:
        if file_sha(voice['path']) != voice['sha256']:
            raise ValueError('Complete bound voice bytes changed')
    return p, s


def process_identity(name):
    result = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process '+name+' -ErrorAction Stop | Select-Object Id,MainWindowHandle | ConvertTo-Json -Compress'],
        encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
    value = json.loads(result)
    if not isinstance(value, dict): raise ValueError('Exactly one Adobe host required')
    return value['Id'], value['MainWindowHandle']


class OwnedAE:
    def __init__(self, folder, completed_reconciliation=None, *, opening_revision=None):
        self.folder = folder; self.p, self.spec = current(folder)
        self.client = JunkdogeClient(); self.client.initialize()
        self.client.call('ae_skillUse', {'name':'ae-execution-guide'})
        self.pid, self.hwnd = process_identity('AfterFX')
        initial = self.reader()
        if initial['rendering']: raise ValueError('AE is already rendering')
        intended = Path(self.p['project']).resolve()
        if opening_revision is None:
            if not initial['project_path'] or Path(initial['project_path']).resolve() != intended:
                raise ValueError('The intended AE production project must be active before ownership')
        elif (completed_reconciliation is not None or Path(opening_revision).resolve() != intended
                or intended.exists()):
            raise ValueError('Only an explicit new bound AE project transition is supported')
        self.lease = HostOwnership('after_effects', '/root/astra_b06_execution', self.p['revision_id'],
            {k: initial[k] for k in ('process_id','project_path','target_id')})
        if completed_reconciliation is None:
            self.lease.acquire()
        else:
            # Only the explicitly invoked completed-result reconciliation path
            # supplies this; ordinary work never expires or resumes a lock.
            self.lease = HostOwnership.reconcile_completed('after_effects',
                '/root/astra_b06_execution', self.p['revision_id'],
                completed_reconciliation['token'], completed_reconciliation['target'],
                self.reader, completed_reconciliation['evidence'],
                expected_state=completed_reconciliation.get('expected_state','UNCERTAIN'))
        self.log = read(folder/'AE_OWNERSHIP_RECEIPTS.json') if (folder/'AE_OWNERSHIP_RECEIPTS.json').exists() else []

    def read_code(self, code, timeout=120):
        return json.loads(self.client.call('ae_exec', {'code':code, 'timeout_sec':timeout}, timeout=timeout+15)['content'])

    def reader(self):
        pid, _ = process_identity('AfterFX')
        raw = self.read_code("JSON.stringify({path:app.project.file?app.project.file.fsName:'',dirty:app.project.dirty,comp:app.project.activeItem instanceof CompItem?app.project.activeItem.id:null,rendering:app.project.renderQueue.rendering});", 30)
        return {'process_id': pid, 'project_path': str(Path(raw['path']).resolve()) if raw['path'] else '',
            'target_id': 'comp:'+str(raw['comp']) if raw['comp'] is not None else 'none',
            'dirty': raw['dirty'], 'rendering': raw['rendering']}

    def mutate(self, label, code, project=None, new_comp=False, timeout=600):
        current(self.folder)
        before = self.reader()
        args = {'code':code, 'timeout_sec':timeout, 'undo_group_name':label}
        write(self.folder/'AE_PENDING_MUTATION.json', {'label':label,'args':args,'before':before})
        target = None
        if project is not None or new_comp:
            def target(result):
                native = json.loads(result['content'])
                return {'process_id': self.pid, 'project_path':str(Path(project or before['project_path']).resolve()),
                    'target_id': 'comp:'+str(native['comp_id']) if native.get('comp_id') is not None else 'none'}
        result = self.lease.mutate(self.reader, lambda: self.client.call('ae_exec', args, timeout=timeout+30), target_after=target)
        native = json.loads(result['content'])
        self.log.append({'label':label,'code_sha':sha(code),'before':before,'after':self.reader(),
            'native':native,'lease_token':self.lease.record['token']})
        write(self.folder/'AE_OWNERSHIP_RECEIPTS.json', self.log)
        return native

    def release(self):
        self.lease.release(self.reader)


def reconcile(folder, token):
    p, _ = current(folder); identity = read(folder/'NATIVE_IDENTITY.json')
    summary = read(folder/'NATIVE_AUDIT_SUMMARY.json')
    if (not token or summary['status'] != 'PASS' or summary['spec_sha'] != p['spec_sha']
            or summary['compositions'] != 6 or summary['errors']
            or identity['spec_sha'] != p['spec_sha'] or not identity.get('reconciled_after_timeout')
            or Path(identity['project']).resolve() != Path(p['project']).resolve()):
        raise ValueError('The completed bounded build must be independently audited first')
    prior = read(ROOT/'local-data/adobe-host-ownership/after_effects.json')
    evidence = {str(folder/name): file_sha(folder/name) for name in
        ('AE_PENDING_MUTATION.json', 'AE_TIMEOUT_RECONCILIATION_READ.json',
         'NATIVE_IDENTITY.json', 'NATIVE_SOURCE_AUDIT.json', 'NATIVE_MOTION_AUDIT.json',
         'NATIVE_COMPOSITION_AUDIT.json', 'NATIVE_AUDIT_SUMMARY.json',
         'B06_JUDGEMENT_NATIVE_4K.aep')}
    target = {'process_id': prior['target']['process_id'], 'project_path':p['project'],
              'target_id':'comp:'+str(identity['comp_id'])}
    owned = OwnedAE(folder, {'token':token,'target':target,'evidence':evidence})
    receipt = deepcopy(owned.lease.record)
    write(folder/'AE_COMPLETED_RECONCILIATION.json', receipt)
    saved = owned.mutate('Save independently reconciled completed B06 project',
        'app.project.save();JSON.stringify({comp_id:app.project.activeItem.id,project:app.project.file.fsName});')
    receipt['guarded_save'] = saved
    receipt['project_sha_after_save'] = file_sha(p['project'])
    owned.release()
    receipt['released_after_fresh_identity_check'] = True
    write(folder/'AE_COMPLETED_RECONCILIATION.json', receipt)
    return {'resolution':'COMPLETED_VERIFIED','mutation_replayed':False,
            'same_token':receipt['token'],'released':True}


def build(folder):
    p, _ = current(folder); target = Path(p['project'])
    if target.exists(): raise FileExistsError('Inspect the existing native revision')
    owned = OwnedAE(folder, opening_revision=target)
    before = owned.reader()
    if before['dirty']:
        backup = folder/'AE_SESSION_BEFORE.aep'
        owned.mutate('Preserve prior unsaved Adobe session',
            'app.project.save(new File('+json.dumps(backup.as_posix())+'));JSON.stringify({comp_id:app.project.activeItem instanceof CompItem?app.project.activeItem.id:null});', project=backup)
    code = '(function(){app.open(new File(PATH));var cp=AEMCP.compById(ID);cp.openInViewer();return JSON.stringify({comp_id:cp.id,path:app.project.file.fsName});})();'
    owned.mutate('Open bound old native project', code.replace('PATH',json.dumps(Path(p['baseline_project']).as_posix())).replace('ID',str(p['baseline_comp_id'])), project=p['baseline_project'], new_comp=True)
    owned.mutate('Save isolated B06 project revision',
        'app.project.save(new File('+json.dumps(target.as_posix())+'));JSON.stringify({comp_id:app.project.activeItem.id});', project=target)
    code = 'var B06_PRODUCTION='+json.dumps((folder/'PRODUCTION.json').as_posix())+';var B06_SPEC='+json.dumps((folder/'NEW_NATIVE_SPEC.json').as_posix())+';\n'+(HERE/'build.jsx').read_text(encoding='utf-8')
    identity = owned.mutate('Build bounded B06 source and six excerpt compositions', code, project=target, new_comp=True)
    write(folder/'NATIVE_IDENTITY.json', identity)
    owned.release()
    return identity


def audit(folder):
    p, spec = current(folder); identity = read(folder/'NATIVE_IDENTITY.json')
    c = JunkdogeClient(); c.initialize(); c.call('ae_skillUse', {'name':'ae-execution-guide'})
    code = "(function(){var cp=AEMCP.compById(ID),rows=[];for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i);if(l.property('Source Text')){var d=l.property('Source Text').value;rows.push({name:l.name,text:d.text,font:d.font,comment:l.comment,in_point:l.inPoint,out_point:l.outPoint});}}return JSON.stringify({project:app.project.file.fsName,comp_id:cp.id,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration,rows:rows});})();".replace('ID',str(identity['source_comp_id']))
    result = json.loads(c.call('ae_exec', {'code':code,'timeout_sec':120}, timeout=150)['content'])
    if Path(result['project']).resolve()!=Path(p['project']).resolve(): raise ValueError('Unexpected active native project')
    actual = {n['name']:n for n in result['rows']}
    for n in spec['nodes']:
        if n['kind'] != 'text': continue
        a = actual[n['node_id']]
        if (a['text'].replace('\r','\n') != n['text'] or a['font'] != n['font']
                or json.loads(a['comment'])['source_refs'] != n['source_refs']
                or abs(a['in_point']-n['in_point'])>1e-4 or abs(a['out_point']-n['out_point'])>1e-4):
            raise ValueError('Native original text/source/lifetime changed: '+n['node_id'])
    if [result[k] for k in ('width','height','fps')] != [3840,2160,24]: raise ValueError('Native 4K24 canvas required')
    write(folder/'NATIVE_SOURCE_AUDIT.json', result)
    motion = {'checked_keys':0,'errors':[],'batches':[]}
    for first in range(0,len(spec['nodes']),48):
        chunk = folder/'NATIVE_MOTION_AUDIT_INPUT.json'
        write(chunk,{'comp_id':identity['source_comp_id'],'camera':spec['camera'],
            'reviewed_connector':spec['reviewed_connector'],'nodes':spec['nodes'][first:first+48]})
        code = 'var AUDIT_INPUT='+json.dumps(chunk.as_posix())+';\n'+(HERE/'audit.jsx').read_text(encoding='utf-8')
        part = json.loads(c.call('ae_exec',{'code':code,'timeout_sec':120},timeout=150)['content'])
        if Path(part['project']).resolve()!=Path(p['project']).resolve():raise ValueError('Native project changed during audit')
        motion['checked_keys']+=part['checked_keys'];motion['errors'].extend(part['errors'])
        motion['batches'].append({'first':first,'end':min(first+48,len(spec['nodes'])),'checked_keys':part['checked_keys']})
        write(folder/'NATIVE_MOTION_AUDIT.json',motion)
    code = "(function(){var rows=[],ids=IDS;for(var i=0;i<ids.length;i++){var cp=AEMCP.compById(ids[i]),l=cp.layer('BOUND_NATIVE_SOURCE');rows.push({id:cp.id,name:cp.name,width:cp.width,height:cp.height,fps:cp.frameRate,duration:cp.duration,comment:JSON.parse(cp.comment),source_comp_id:l.source.id,source_comment:JSON.parse(l.source.comment),source_duration:l.source.duration,source_start:-l.startTime,in_point:l.inPoint,out_point:l.outPoint,mask:!!cp.layer('REMOVE_EXPLANATORY_CAPTIONS')});}return JSON.stringify(rows);})();".replace('IDS',json.dumps([v['comp_id'] for v in identity['compositions'].values()]))
    compositions=json.loads(c.call('ae_exec',{'code':code,'timeout_sec':60},timeout=90)['content'])
    for row in compositions:
        expected=identity['compositions'][row['name']]
        new=row['name'].startswith('NEW_')
        expected_source=identity['source_comp_id'] if new else identity['old_source_comp_id']
        expected_spec=p['spec_sha'] if new else p['baseline_spec_sha']
        expected_duration=spec['canvas']['duration']-(0 if new else p['insert']['frames']/FPS)
        if ([row[k] for k in ('width','height','fps')]!=[3840,2160,24]
                or abs(row['duration']-expected['frames']/FPS)>1e-6
                or abs(row['source_start']-expected['source_frames'][0]/FPS)>1e-6
                or row['in_point']!=0 or abs(row['out_point']-row['duration'])>1e-6
                or row['comment']['production_sha']!=p['production_sha']
                or row['source_comp_id']!=expected_source or row['comment']['native_source_comp_id']!=expected_source
                or row['comment']['source_frames']!=expected['source_frames']
                or row['source_comment']['spec_sha']!=expected_spec
                or abs(row['source_duration']-expected_duration)>1e-6
                or row['mask']!=row['name'].endswith('_VISUAL')):
            motion['errors'].append('Composition excerpt mapping changed: '+row['name'])
    write(folder/'NATIVE_COMPOSITION_AUDIT.json',compositions)
    summary={'status':'HOLD' if motion['errors'] else 'PASS','spec_sha':p['spec_sha'],
        'source_objects':len(actual),'checked_keys':motion['checked_keys'],'errors':motion['errors'],
        'compositions':len(compositions),'public_render_ready':False}
    write(folder/'NATIVE_AUDIT_SUMMARY.json',summary)
    if motion['errors']:raise ValueError('Actual native motion audit failed: '+str(motion['errors'][:6]))
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('operation',choices=('prepare','build','audit','reconcile'))
    ap.add_argument('folder'); ap.add_argument('--baseline'); ap.add_argument('--visual')
    ap.add_argument('--token')
    args=ap.parse_args(); folder=local(args.folder)
    result=(prepare(folder,args.baseline,args.visual) if args.operation=='prepare' else
            reconcile(folder,args.token) if args.operation=='reconcile' else globals()[args.operation](folder))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
