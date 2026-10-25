"""Visual specification binding. This registry has no teaching authority."""
from video_contracts import ROOT, read, sha
from copy import deepcopy
from pathlib import Path
import math
import re
import unicodedata
import hashlib

DIRECTORY = ROOT / 'creative/motion-identity'
CREATIVE_DIMENSIONS = ('Composition', 'Shot Variety', 'Graphic Continuity', 'Typography',
    'Motion Richness', 'Effect Restraint', 'Temporal Contrast', 'Depth', 'Human Voice',
    'AI Feel', 'Sound Rhythm', 'Cinematic Flow', 'Teaching Clarity',
    'Signature recognizability', 'Method-motion fidelity', 'Brand grammar consistency',
    'Mnemonic clarity', 'Motion distinctiveness', 'Motion-to-teaching alignment')


def display_identity_binding():
    """Project the real display asset to authors; never rewrite historical plans."""
    path = DIRECTORY / 'display-identity.json'
    profile = read(path)
    if profile.get('authority') != 'visual_metaphor_only':
        raise ValueError('Display identity has no teaching authority')
    if set(profile['scope']) & set(profile['excluded_scope']):
        raise ValueError('Display identity scope overlaps protected source presentation')
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'profile': profile,
            'consumer': str(DIRECTORY / 'display-identity.js'),
            'consumer_sha256': hashlib.sha256((DIRECTORY / 'display-identity.js').read_bytes()).hexdigest(),
            'execution_policy': {'final_dark_graphics': 'native_ae',
                'canvas_primitive_role': 'previsualization_and_parameter_reference',
                'handoff': 'Continuous native text/shape objects; no held-frame reset between method, CTA and brand',
                'proof': 'Native property readback, actual AE queue output and same-version encoded media'},
            'native_status': 'Map to existing AE text/shape properties; native consumption needs actual readback',
            'historical_inputs': 'Unchanged; bind only new creative requests and explicit revisions'}


def registry():
    grammar = read(DIRECTORY / 'brand-motion-grammar.json')
    signatures = read(DIRECTORY / 'method-signatures.json')
    if any(r.get('authority') != 'visual_metaphor_only' for r in (grammar, signatures)):
        raise ValueError('Motion registry cannot supply teaching facts')
    forbidden = {'answer', 'answer_key', 'evidence', 'stop_rule', 'trigger',
                 'teaching_facts', 'applicability', 'teaching_review'}
    def inspect(value):
        if isinstance(value, dict):
            if forbidden & set(value):
                raise ValueError('Teaching fact fields are forbidden in the motion registry')
            for child in value.values(): inspect(child)
        elif isinstance(value, list):
            for child in value: inspect(child)
    inspect(grammar); inspect(signatures)
    return grammar, signatures


def bind_identity(method_id, phases, brand_motion, carry_node_id):
    grammar, signatures = registry()
    signature = next(s for s in signatures['signatures'] if s['method_id'] == method_id)
    if method_id != 'G01' or signature['production_status'] != 'hero_pilot_only':
        raise ValueError('V9.1 produces G01 Hero only; other methods are specifications')
    if [p['phase'] for p in phases] != signature['required_phases']:
        raise ValueError('Signature phases missing or reordered')
    if any(p['end'] <= p['start'] for p in phases) or any(a['end'] > b['start'] for a,b in zip(phases, phases[1:])):
        raise ValueError('Signature phase overlap/order invalid')
    if not set(brand_motion) <= {g['id'] for g in grammar['grammar']}:
        raise ValueError('Unknown brand grammar')
    return {'method_id': method_id, 'signature_id': signature['signature_id'],
            'phases': phases, 'brand_motion': brand_motion, 'carry_node_id': carry_node_id,
            'grammar_sha': sha(grammar), 'signatures_sha': sha(signatures),
            'scope': 'visual_motion_specification_not_teaching_certification',
            'recognition_review': 'PENDING_human_memory_test'}


def validate_identity(identity, nodes, units, duration):
    expected = bind_identity(identity['method_id'], identity['phases'],
                             identity['brand_motion'], identity['carry_node_id'])
    if expected != identity:
        raise ValueError('Motion registry changed; new visual revision required')
    if any(u['method_id'] != identity['method_id'] for u in units.values()):
        raise ValueError('Signature method differs from frozen claim bindings')
    carry = next(n for n in nodes if n['node_id'] == identity['carry_node_id'])
    if len(carry.get('tracks', {}).get('position', [])) < 2:
        raise ValueError('Semantic Carry requires the same moving object')
    if any(p['start'] < 0 or p['end'] > duration for p in identity['phases']):
        raise ValueError('Signature phase outside the Hero')


def identity_shot_plan(contract, excerpt):
    identity=contract['design']['motion_identity'];units=excerpt['units']
    validate_identity(identity,contract['nodes'],{u['unit_id']:u for u in units},contract['canvas']['duration'])
    shots=[]
    for i,phase in enumerate(identity['phases']):
        selected=units[:1] if phase['phase']=='extract' else (units[:2] if phase['phase']=='route' else units[1:])
        shots.append({'shot_id':'hero-'+phase['phase'],
            'semantic_scene_id':selected[0]['scene_id'],
            'source_claim_refs':sorted({r for u in selected for r in u['source_claim_refs']}),
            'start':0 if i==0 else phase['start'],
            'end':contract['canvas']['duration'] if i==len(identity['phases'])-1 else phase['end'],
            'signature_motion':{'method_id':identity['method_id'],'signature_id':identity['signature_id'],
                                'phase':phase['phase']},
            'brand_motion':{'extract':['evidence_develop','focus_breathing','semantic_carry','magnetic_alignment'],
                            'route':['semantic_carry','magnetic_alignment','micro_lock'],
                            'seal':['micro_lock','boundary_seal']}[phase['phase']],
            'effects':{'structural':'bound geometry, masks and persistent object movement',
                       'depth':['focus separation','motion blur'],'accent':[]}})
    return {'render_contract_sha':contract['render_contract_sha'],'shots':shots,
            'preferred_transition':'logic_match_cut','human_direction':'PENDING',
            'public_render_ready':False}


def creative_review(contract, copy_lock, video_sha, observations):
    if set(observations)!=set(CREATIVE_DIMENSIONS) or any(not str(v).strip() for v in observations.values()):
        raise ValueError('All creative and recognition dimensions need explicit observations')
    return {'render_contract_sha':contract['render_contract_sha'],'copy_lock':copy_lock,
            'video_sha':video_sha,'reviewer_kind':'ai_host','independent':False,
            'dimensions':{k:{'observation':observations[k],'human_status':'PENDING'} for k in CREATIVE_DIMENSIONS},
            'direction_status':'READY_FOR_HUMAN_DIRECTION_REVIEW',
            'human_taste_review':'PENDING','public_render_ready':False}


# These recipes consume frozen judgements; they do not decide English meaning.
# The original G01 registry API above remains unchanged for historical inputs.
SYMBOL_VERSION = 'COGNITIVE_SYMBOL_LIBRARY_V1'
SYMBOL_DIRECTORY = DIRECTORY / 'cognitive-symbol-library'
_RECIPE_ROLES = {
    'semantic_isomorphism': ('subject', 'referent', 'source_relation', 'candidate_relation'),
    'same_form_different_relation': ('source_noun', 'candidate_noun', 'source_action', 'candidate_action'),
}
_RELATIONS = {'semantic_isomorphism': 'same_price_relation',
              'same_form_different_relation': 'different_action_role'}


def symbol_registry():
    """Load executable specifications, without upgrading preview/review status."""
    catalog = read(SYMBOL_DIRECTORY / 'catalog.json')
    if (catalog.get('contract_version') != SYMBOL_VERSION
            or catalog.get('authority') != 'visual_metaphor_only'
            or set(catalog.get('recipes', {})) != set(_RECIPE_ROLES)):
        raise ValueError('Unsupported cognitive symbol catalog')
    recipes = {}
    for recipe_id, relative in catalog['recipes'].items():
        path = (SYMBOL_DIRECTORY / relative).resolve()
        if not path.is_relative_to(SYMBOL_DIRECTORY.resolve()):
            raise ValueError('Recipe path escapes its authoritative library')
        recipe = read(path)
        if (recipe.get('recipe_id') != recipe_id or recipe.get('authority') != 'visual_metaphor_only'
                or recipe.get('consumer') != 'ae/rigs/cognitive-symbols.jsx'
                or tuple(recipe.get('lesson_roles', [])) != _RECIPE_ROLES[recipe_id]):
            raise ValueError('Cognitive symbol recipe identity/consumer changed')
        recipes[recipe_id] = recipe
    return catalog, recipes


def _finite(value, label, low=None, high=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or low is not None and value < low or high is not None and value > high):
        raise ValueError('Invalid cognitive symbol ' + label)
    return value


def _source_ref(ref, bundles):
    from video_contracts import pointer
    if (not isinstance(ref, dict) or set(ref) != {'world', 'pointer', 'start', 'end', 'quote'}
            or ref['world'] not in bundles or ref['pointer'] not in {'/passage', '/options/A', '/options/B', '/options/C', '/options/D'}):
        raise ValueError('Cognitive symbols require source-exact passage/option references')
    text = pointer(bundles[ref['world']]['source_snapshot'], ref['pointer'])
    if (type(ref['start']) is not int or type(ref['end']) is not int
            or not 0 <= ref['start'] < ref['end'] <= len(text)
            or text[ref['start']:ref['end']] != ref['quote'] or not ref['quote'].strip()):
        raise ValueError('Cognitive symbol source span is stale or incomplete')
    return text


def _inside(ref, scope):
    return (ref['world'] == scope['world'] and ref['pointer'] == scope['pointer']
            and scope['start'] <= ref['start'] < ref['end'] <= scope['end'])


def _in_evidence(ref, evidence):
    return any(e.get('field') == ref['pointer'].lstrip('/')
               and e.get('start', -1) <= ref['start'] < ref['end'] <= e.get('end', -1)
               for e in evidence)


def _symbol_parameters(parameters):
    keys = {'duration_seconds', 'space', 'font', 'layout', 'curve', 'mask'}
    if not isinstance(parameters, dict) or set(parameters)-{'phase_seconds','composition','surface_hold_frames','keyword_pair','context_hold_seconds'} != keys:
        raise ValueError('Complete parameterized cognitive symbol geometry is required')
    if parameters.get('composition') not in (None,'keyword_equivalence','noun_divergence'):
        raise ValueError('Unknown authored relation composition')
    if 'surface_hold_frames' in parameters and (type(parameters['surface_hold_frames']) is not int
            or parameters['surface_hold_frames']!=18 or parameters.get('composition')!='noun_divergence'):
        raise ValueError('Surface match requires the authored eighteen-frame hold')
    if 'keyword_pair' in parameters:
        pair=parameters['keyword_pair']
        if (parameters.get('composition')!='keyword_equivalence' or not isinstance(pair,dict)
                or set(pair)!={'source_relation','candidate_relation'}
                or any(not isinstance(v,str) or not v.strip() for v in pair.values())):
            raise ValueError('Keyword alignment requires two actual source-bound terms')
    if 'context_hold_seconds' in parameters:
        if parameters.get('composition')!='keyword_equivalence':raise ValueError('Comparison context belongs to price equivalence')
        _finite(parameters['context_hold_seconds'],'context recognition',.25,parameters['duration_seconds']-.75)
    _finite(parameters['duration_seconds'], 'duration', 3, 30)
    if 'phase_seconds' in parameters:
        phases=parameters['phase_seconds']
        if not isinstance(phases,list) or len(phases)!=3:
            raise ValueError('Recipe phase_seconds requires three authored movement/settle durations')
        for seconds in phases:_finite(seconds,'phase seconds',1/24,10)
        if sum(phases)+parameters.get('surface_hold_frames',0)/24+.95>parameters['duration_seconds']:
            raise ValueError('Recipe must retain recognition and continuous return time')
    space = parameters['space']; font = parameters['font']; layout = parameters['layout']
    if (not isinstance(space, dict) or set(space) != {'origin', 'depth'}
            or not isinstance(space['origin'], list) or len(space['origin']) != 3):
        raise ValueError('Cognitive symbol requires a three-dimensional origin')
    for number in space['origin']: _finite(number, 'origin', -100000, 100000)
    _finite(space['depth'], 'camera depth', -1200, 1200)
    if not isinstance(font, dict) or set(font) != {'family', 'size', 'advance_factor', 'line_height'}:
        raise ValueError('Cognitive symbol requires explicit font metrics')
    if not isinstance(font['family'], str) or not font['family'].strip():
        raise ValueError('Cognitive symbol font family is missing')
    _finite(font['size'], 'font size', 20, 100)
    _finite(font['advance_factor'], 'font advance', .35, 1.2)
    _finite(font['line_height'], 'line height', 1.05, 1.7)
    if not isinstance(layout, dict) or set(layout) != {'width', 'height', 'min_gap'}:
        raise ValueError('Cognitive symbol layout bounds are missing')
    _finite(layout['width'], 'layout width', 400, 2400)
    _finite(layout['height'], 'layout height', 240, 1600)
    _finite(layout['min_gap'], 'layout gap', 8, 160)
    if parameters['curve'] != 'smoothstep' or parameters['mask'] != 'source_glyphs_only':
        raise ValueError('Cognitive symbols require continuous restrained movement and original glyph masks')


def _validate_relation(instance, scene, bundles):
    from video_contracts import pointer
    relation = instance['relation']
    if not isinstance(relation, dict) or set(relation) != {'type', 'dimension', 'action_ref', 'verification_ref', 'terminal_ref'}:
        raise ValueError('Cognitive symbols cannot invent or omit their frozen relationship authority')
    recipe_id = instance['recipe_id']
    if relation['type'] != _RELATIONS[recipe_id] or relation['dimension'] != ('price' if recipe_id == 'semantic_isomorphism' else 'action_role'):
        raise ValueError('Unsupported semantic relation for this cognitive recipe')
    action_ref = relation['action_ref']; terminal = relation['terminal_ref']; verification = relation['verification_ref']
    if (not isinstance(action_ref, dict) or set(action_ref) != {'world', 'pointer', 'sha'}
            or action_ref not in scene['action_refs'] or action_ref['world'] != scene['world']
            or not action_ref['pointer'].startswith('/execution_trace/')):
        raise ValueError('Recipe action must be the actual scene frozen execution')
    analysis = bundles[scene['world']]['analysis']; action = pointer(analysis, action_ref['pointer'])
    if (sha(action) != action_ref['sha'] or action.get('review_status') != 'reviewed'
            or action.get('state') != 'produced' or action.get('stop_applied') is not False
            or not action.get('stop_rule_check') or action.get('output', {}).get('kind') != 'interpretation'
            or not action['output'].get('parts')
            or any(not p.get('value') or not p.get('evidence') for p in action['output']['parts'])):
        raise ValueError('Recipe requires an actual reviewed interpretation output, not a declared relation')
    question = analysis['question_verification']; review = question['review']
    if (terminal not in scene['terminal_refs'] or terminal not in question['candidate_bindings']
            or question.get('state') != 'reviewed' or review.get('review_status') != 'reviewed'
            or review.get('stop_applied') is not False
            or action['execution_id'] not in review.get('input_artifact_ids', [])):
        raise ValueError('Recipe cannot borrow another candidate or an unconsumed interpretation')
    if (not isinstance(verification, dict) or set(verification) != {'pointer', 'sha'}
            or not verification['pointer'].startswith('/question_verification/review/candidate_checks/')):
        raise ValueError('Recipe must bind the complete candidate verification')
    check = pointer(analysis, verification['pointer'])
    effect = 'retain' if recipe_id == 'semantic_isomorphism' else 'eliminate'
    if (check not in review['candidate_checks'] or sha(check) != verification['sha']
            or check.get('candidate') != scene.get('candidate') or terminal['candidate'] != scene.get('candidate')
            or check.get('effect') != effect or terminal['effect'] != effect
            or check.get('claim') != bundles[scene['world']]['source_snapshot']['options'][scene['candidate']]
            or not check.get('decision_rule_check') or not check.get('backfill_check') or not check.get('evidence')):
        raise ValueError('Recipe relationship conflicts with the complete frozen candidate check')
    for item in instance['inputs']:
        ref = item['source_ref']
        if ref['pointer'] == '/passage' and (not _in_evidence(ref, action['evidence'])
                or not _in_evidence(ref, check['evidence'])
                or not any(_in_evidence(ref, part['evidence']) for part in action['output']['parts'])):
            raise ValueError('Recipe text is outside the actual action output or candidate evidence')
    return {'execution_sha': sha(action), 'interpretation_sha': sha(action['output']),
            'candidate_check_sha': sha(check), 'terminal_sha': sha(terminal),
            'authority': 'FROZEN_UPSTREAM_INTERPRETATION_AND_WHOLE_QUESTION_REVIEW'}


def validate_authored_symbols(author, bundles, folder=None):
    """Validate opt-in source/geometry contracts; never certify semantic or artistic success."""
    if 'cognitive_symbols' not in author: return None
    from scripts.voice_delivery import sha256
    contract = author['cognitive_symbols']; catalog, recipes = symbol_registry()
    if (not isinstance(contract, dict) or set(contract) != {'contract_version', 'request_source', 'instances'}
            or contract['contract_version'] != SYMBOL_VERSION or not isinstance(contract['instances'], list)
            or not contract['instances']):
        raise ValueError('Unsupported cognitive symbol author contract')
    binding = contract['request_source']
    if not isinstance(binding, dict) or set(binding) != {'path', 'sha256'} or not isinstance(binding['path'], str) or not Path(binding['path']).is_absolute():
        raise ValueError('Cognitive symbol direction requires its bound external user request')
    path = Path(binding['path']).resolve()
    if (path.suffix.lower() not in {'.txt', '.md'} or folder is not None and path.is_relative_to(Path(folder).resolve())
            or not path.is_file() or sha256(path) != binding['sha256']
            or 'VIDEO_EXPERIENCE_UPGRADE_V1' not in path.read_text('utf-8-sig')
            or [v for k, v in author.get('input_files', {}).items() if Path(k).resolve() == path] != [binding['sha256']]):
        raise ValueError('Cognitive symbol creative request is missing, changed or self-authorized')
    for world, bundle in bundles.items():
        source = author.get('sources', {}).get(world, {}).get('bundle')
        if not isinstance(source, str) or not Path(source).is_absolute() or not Path(source).is_file():
            raise ValueError('Cognitive symbol frozen source file is missing')
        source_path = Path(source).resolve()
        digests = [digest for name, digest in author.get('input_files', {}).items() if Path(name).resolve() == source_path]
        if (read(source_path) != bundle or digests != [sha256(source_path)]):
            raise ValueError('Cognitive symbol frozen source file bytes or declared bundle changed')
    scenes = {s['id']: s for s in author['scenes']}; seen = {}; rows = []
    if len(scenes) != len(author['scenes']):
        raise ValueError('Cognitive symbols require unique actual scene identities')
    for instance in contract['instances']:
        keys = {'symbol_id', 'recipe_id', 'scene_id', 'variant', 'inputs', 'relation', 'parameters'}
        if not isinstance(instance, dict) or set(instance) != keys | ({'recall_of'} if instance.get('variant') == 'recall' else set()):
            raise ValueError('Unsupported cognitive symbol instance fields')
        ident = instance['symbol_id']; recipe_id = instance['recipe_id']; variant = instance['variant']
        if (not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+', ident) or ident in seen
                or recipe_id not in recipes or variant not in {'lesson', 'hook', 'recall'}):
            raise ValueError('Cognitive symbol identity, recipe or variant is invalid')
        _symbol_parameters(instance['parameters'])
        inputs = instance['inputs']; roles = ('source_noun', 'candidate_noun') if variant == 'hook' else _RECIPE_ROLES[recipe_id]
        if (not isinstance(inputs, list) or len(inputs) != len(roles)
                or any(not isinstance(i, dict) or set(i) != {'object_id', 'role', 'source_ref'} for i in inputs)
                or {i['role'] for i in inputs} != set(roles)
                or any(not isinstance(i['object_id'], str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+', i['object_id']) for i in inputs)
                or len({i['object_id'] for i in inputs}) != len(inputs)):
            raise ValueError('Recipe needs distinct, persistent objects for all semantic slots')
        for item in inputs: _source_ref(item['source_ref'], bundles)
        by_role = {i['role']: i for i in inputs}; relation = instance['relation']
        composition=instance['parameters'].get('composition')
        if composition:
            if variant=='hook' or composition!=('keyword_equivalence' if recipe_id=='semantic_isomorphism' else 'noun_divergence'):
                raise ValueError('Relation composition cannot change the source-bound recipe or expose Hook evidence')
            for role,word in instance['parameters'].get('keyword_pair',{}).items():
                if by_role[role]['source_ref']['quote'].count(word)!=1:
                    raise ValueError('Keyword must identify one exact span in its real relation text')
        if variant == 'hook':
            hook = author.get('audience_hook', {})
            if (recipe_id != 'same_form_different_relation' or instance['scene_id'] != hook.get('scene_id')
                    or relation != {'type': 'anonymous_relation_conflict', 'dimension': 'unresolved',
                                    'action_ref': None, 'verification_ref': None, 'terminal_ref': None}
                    or [i['source_ref'] for i in inputs] != hook.get('visual_conflict', {}).get('anchor_refs')
                    or hook.get('visual_conflict', {}).get('relation_labels') is not False):
                raise ValueError('Hook recipe cannot expose real actions, candidate verdicts or new creative decisions')
            authority = {'authority': 'BOUND_EXISTING_ABSTRACT_HOOK', 'hook_decision_sha': sha(hook)}
        elif variant == 'recall':
            original = seen.get(instance['recall_of'])
            scene = scenes.get(instance['scene_id'])
            if (not original or original['variant'] != 'lesson' or scene is None or scene['kind'] != 'recap'
                    or any(instance[k] != original[k] for k in ('recipe_id', 'inputs', 'relation'))):
                raise ValueError('Recall can only replay the same demonstrated source objects and relation')
            authority = deepcopy(next(r['authority'] for r in rows if r['symbol_id'] == instance['recall_of']))
        else:
            scene = scenes.get(instance['scene_id'])
            if (scene is None or scene['kind'] != 'compare' or scene.get('event') not in {'supported', 'eliminate'}
                    or any(i['source_ref']['world'] != scene['world']
                           or not any(_inside(i['source_ref'], scope) for scope in scene['source_refs']) for i in inputs)):
                raise ValueError('Recipe must consume the actual visible comparison source and candidate')
            authority = _validate_relation(instance, scene, bundles)
        if recipe_id == 'same_form_different_relation':
            a = by_role['source_noun']['source_ref']; b = by_role['candidate_noun']['source_ref']
            if (unicodedata.normalize('NFC', a['quote']) != unicodedata.normalize('NFC', b['quote'])
                    or a['pointer'] != '/passage' or not b['pointer'].startswith('/options/')):
                raise ValueError('Same-form recipe needs the identical real noun in passage and candidate')
            if variant != 'hook' and (by_role['source_action']['source_ref']['quote'].casefold() == by_role['candidate_action']['source_ref']['quote'].casefold()
                    or by_role['source_action']['source_ref']['pointer'] != '/passage'
                    or not by_role['candidate_action']['source_ref']['pointer'].startswith('/options/')):
                raise ValueError('Same-form recipe requires distinct, source-bound actions')
        else:
            if (any(by_role[r]['source_ref']['pointer'] != '/passage' for r in ('subject', 'referent', 'source_relation'))
                    or not by_role['candidate_relation']['source_ref']['pointer'].startswith('/options/')
                    or by_role['source_relation']['source_ref']['quote'].casefold() == by_role['candidate_relation']['source_ref']['quote'].casefold()):
                raise ValueError('Isomorphism needs different expressions with the actual subject and comparator')
        seen[ident] = instance
        rows.append({'symbol_id': ident, 'authority': authority})
    return {'contract_version': SYMBOL_VERSION, 'decision_sha': sha(contract),
            'catalog_sha': sha(catalog), 'recipes_sha': {k: sha(v) for k, v in recipes.items()},
            'instances': rows, 'semantic_certification': False, 'artistic_review': 'PENDING',
            'public_render_ready': False}


def _symbol_layout(instance):
    """Conservative metrics, followed by mandatory native font/bounds readback."""
    p = instance['parameters']; font = p['font']; layout = p['layout']
    width = layout['width']; height = layout['height']; gap = layout['min_gap']
    col = (width - gap) / 2; row = (height - gap) / 2
    role_order = _RECIPE_ROLES[instance['recipe_id']]
    positions = {}; boxes = []
    for item in instance['inputs']:
        role = item['role']; lines = item['source_ref']['quote'].replace('\r\n', '\n').split('\n')
        # No inferred wrapping or font shrinking: oversized text is a layout decision.
        measured_w = max(len(line) for line in lines) * font['size'] * font['advance_factor']
        measured_h = len(lines) * font['size'] * font['line_height']
        if measured_w > col - 2 * gap or measured_h > row - gap:
            raise ValueError('Cognitive symbol text exceeds readable layout; revise layout, never shrink or replace by a card')
        index = role_order.index(role); x = -width / 2 + (index % 2) * (col + gap)
        y = -height / 2 + (index // 2) * (row + gap)
        if instance['recipe_id'] == 'same_form_different_relation' and role in {'source_noun', 'candidate_noun'}:
            x = -measured_w / 2; y = -height / 2  # common noun remains one stable spatial anchor
        if instance['recipe_id'] == 'semantic_isomorphism' and role in {'source_relation', 'candidate_relation'}:
            x = -measured_w / 2
            source_lines=next(i['source_ref']['quote'] for i in instance['inputs'] if i['role']=='source_relation').replace('\r\n','\n').split('\n')
            y = -10 if role == 'source_relation' else -10+len(source_lines)*font['size']*font['line_height']+gap
        if p.get('composition')=='noun_divergence':
            if role in {'source_noun','candidate_noun'}:x=-width/2+gap;y=-measured_h/2
            else:x=gap*3;y=-height/3 if role=='source_action' else height/3-measured_h
        elif p.get('composition')=='keyword_equivalence':
            if role in {'subject','referent'}:
                x=-measured_w/2;y=-height/2+(0 if role=='subject' else font['size']*font['line_height']+8)
            else:
                word=p.get('keyword_pair',{}).get(role)
                if not word:raise ValueError('Equivalence composition requires explicit keyword spans')
                quote=item['source_ref']['quote'];prefix=quote[:quote.index(word)]
                x=-(len(prefix)+len(word)/2)*font['size']*font['advance_factor']
                y=-8 if role=='source_relation' else font['size']*font['line_height']+gap*2
        if x < -width/2 or x+measured_w > width/2 or y < -height/2 or y+measured_h > height/2:
            raise ValueError('Cognitive symbol text exceeds its comparison boundary')
        positions[item['object_id']] = [x, y, p['space']['depth']]
        boxes.append({'object_id': item['object_id'], 'role': role, 'left': x, 'top': y,
                      'right': x + measured_w, 'bottom': y + measured_h})
    for index, a in enumerate(boxes):
        for b in boxes[index + 1:]:
            shared = instance['recipe_id'] == 'same_form_different_relation' and {a['role'], b['role']} == {'source_noun', 'candidate_noun'}
            overlap = min(a['right'], b['right']) > max(a['left'], b['left']) and min(a['bottom'], b['bottom']) > max(a['top'], b['top'])
            if overlap and not shared: raise ValueError('Cognitive symbol relations overlap unreadably')
    return {'positions': positions, 'estimated_boxes': boxes, 'native_metric_check': 'REQUIRED_BEFORE_RENDER',
            'coordinate_space': 'LOCAL_RIG_PIXELS_FROM_SPACE_ORIGIN', 'text_reflow': False, 'font_shrink': False}


def compile_symbols(author, bundles, clock, worlds=None, folder=None):
    """Compile into the existing AV plan; no renderer, director or answer engine."""
    checked = validate_authored_symbols(author, bundles, folder)
    if checked is None: return None
    worlds = clock.get('worlds') if worlds is None else worlds
    if not isinstance(worlds, dict) or set(worlds) != set(bundles):
        raise ValueError('Cognitive symbols require actual prepared source worlds')
    for world, bundle in bundles.items():
        if worlds[world]['question'] != bundle['source_snapshot'] or worlds[world]['source'] != author['sources'][world]:
            raise ValueError('Cognitive symbol source world changed')
    scenes = {s['id']: s for s in clock['scenes']}; fps = author['format']['fps']; rows = []
    if len(scenes) != len(clock['scenes']):
        raise ValueError('Cognitive symbol clock contains repeated scene identities')
    _finite(fps, 'frame rate', 24, 24)
    instances = author['cognitive_symbols']['instances']
    for instance in instances:
        variant = instance['variant']; ident = instance['symbol_id']; scene_id = instance['scene_id']
        if variant == 'hook':
            live = clock.get('audience_hook', {})
            if live.get('scene_id') != scene_id or live.get('decision_sha') != sha(author['audience_hook']):
                raise ValueError('Recipe must use the actual compiled Hook clock')
            start, end = live['start'], live['end']
        else:
            live = scenes.get(scene_id)
            authored = next(s for s in author['scenes'] if s['id'] == scene_id)
            if 'teaching_focus' in author:
                from creative_os.teaching_focus import direct_scene
                authored = direct_scene(author, authored)
            if live is None or any(live.get(k) != v for k, v in authored.items()):
                raise ValueError('Cognitive symbol clock differs from its actual authored scene')
            if variant == 'lesson':
                start = math.ceil((live['settled'] + .3 - 1e-8) * fps) / fps
                end = live['event_time']
                if not start < end <= live['return_start'] <= live['end']:
                    raise ValueError('Cognitive symbol comparison cannot overrun the actual judgement/source return')
            else:
                recalls = [i for i in instances if i['variant'] == 'recall' and i['scene_id'] == scene_id]
                index = recalls.index(instance); count = len(recalls)
                if count != 2: raise ValueError('This ending recalls both demonstrated relations exactly once')
                split = round((live['start'] + (live['end'] - live['start']) / 2) * fps) / fps
                first_voice=next((v for v in clock.get('segments',[]) if v['scene_id']==scene_id),None)
                if first_voice:
                    mid=(first_voice['voice_start']+first_voice['voice_end'])/2
                    candidates=[c for c in clock.get('cues',[]) if c.get('segment')==first_voice['id']
                                and live['oriented']+.5<c['start']<first_voice['voice_end']-.5]
                    if candidates:split=math.ceil((min(candidates,key=lambda c:abs(c['start']-mid))['start']-1e-8)*fps)/fps
                closing=authored.get('closing_memory')
                recall_end=live['end']-(closing['hold_frames']+closing['fade_frames'])/fps-.25 if closing else live['end']
                start, end = (live['start'], split) if index == 0 else (split, recall_end)
        duration = end - start
        if (not math.isfinite(start) or not math.isfinite(end) or start < 0 or duration < 3
                or abs(duration - instance['parameters']['duration_seconds']) > 1 / fps + 1e-7):
            raise ValueError('Recipe duration must bind the existing clock and leave at least three seconds to recognize the relation')
        native_inputs = []
        for item in instance['inputs']:
            ref = item['source_ref']; world = ref['world']
            if ref['pointer'] == '/passage':
                blocks = [b for b in worlds[world]['blocks'] if b['visible'] and b['start'] <= ref['start'] < ref['end'] <= b['end']
                          and b['text'] == bundles[world]['source_snapshot']['passage'][b['start']:b['end']]]
                if len(blocks) != 1: raise ValueError('Recipe glyphs must retain one real original native source block')
                source_id = blocks[0]['id']; local_start = ref['start'] - blocks[0]['start']
            else:
                source_id = world + '_OPTION_' + ref['pointer'].split('/')[-1]; local_start = ref['start'] + 4
            native_inputs.append({**deepcopy(item), 'source_object_id': source_id,
                                  'source_character_start': local_start,
                                  'source_character_end': local_start + len(ref['quote']),
                                  'source_snapshot_sha': sha(bundles[world]['source_snapshot'])})
        travel = round(min(1.35, duration * .45) * fps) / fps; settle = 6 / fps
        phase_names = (['surface_align', 'relation_displace', 'precise_lock', 'hold'] if instance['recipe_id'] == 'same_form_different_relation'
                       else ['carry_relations', 'structural_align', 'precise_lock', 'hold'])
        endpoints = [start, start + travel * .5, start + travel, start + travel + settle, end]
        if 'phase_seconds' in instance['parameters']:
            endpoints=[start]
            for seconds in instance['parameters']['phase_seconds']:
                endpoints.append(round((endpoints[-1]+seconds)*fps)/fps)
            endpoints.append(end)
        # Keep the original three movement phase indices stable for native audit.
        # The surface hold is an explicit subrange before phase 1 displacement.
        surface_hold=instance['parameters'].get('surface_hold_frames',0)/fps
        if surface_hold:
            endpoints[2]+=surface_hold;endpoints[3]+=surface_hold
        phases = [{'phase': name, 'start': endpoints[n], 'end': endpoints[n + 1]} for n, name in enumerate(phase_names)]
        states=[]
        if surface_hold:
            states=[{'state':'apparent_identity_hold','start':endpoints[1],
                     'end':endpoints[1]+surface_hold,'frames':round(surface_hold*fps)}]
            if variant=='lesson':
                explanation=[v for v in clock['segments'] if v['scene_id']==scene_id and v['voice_start']>=endpoints[1]]
                if not explanation or abs(min(v['voice_start'] for v in explanation)-endpoints[3]-.875)>1e-6:
                    raise ValueError('Role recognition requires 875ms after landing before the unchanged explanation take')
                if any(v['voice_start']<endpoints[3]+.875-1e-6 and v['voice_end']>endpoints[1]+1e-6 for v in clock['segments']):
                    raise ValueError('Apparent identity and relation recognition require a silent visual comparison')
        if variant == 'hook':
            names = ['surface_align', 'relation_displace', 'unresolved_hold', 'match_into_task']
            existing = live.get('phases', {})
            if set(existing) != {'enter', *names}:
                raise ValueError('Hook recipe must retain the existing anonymous visual phase clock')
            phases = []
            previous = start
            for name in ['enter', *names]:
                span = existing[name]
                if (not isinstance(span, list) or len(span) != 2
                        or any(type(v) not in (int, float) or not math.isfinite(v) for v in span)
                        or abs(span[0] - previous) > 1e-7 or not span[0] < span[1] <= end):
                    raise ValueError('Hook recipe phase ranges are discontinuous, reordered or out of bounds')
                previous = span[1]
                if name != 'enter': phases.append({'phase': name, 'start': span[0], 'end': span[1]})
            if abs(previous - end) > 1e-7:
                raise ValueError('Hook recipe must finish at the actual task handoff')
        authority = next(i['authority'] for i in checked['instances'] if i['symbol_id'] == ident)
        rows.append({'symbol_id': ident, 'recipe_id': instance['recipe_id'], 'scene_id': scene_id,
                     'variant': variant, 'start': start, 'end': end, 'start_frame': round(start * fps), 'end_frame': round(end * fps),
                     'phases': phases, **({'states':states} if states else {}), 'inputs': native_inputs, 'relation': deepcopy(instance['relation']),
                     'parameters': deepcopy(instance['parameters']), 'layout': _symbol_layout(instance),
                     'authority': deepcopy(authority), 'instance_sha': sha(instance),
                     'glyph_continuity': 'ORIGINAL_SOURCE_RANGE_CONTINUOUS_CARRIED_OBJECT',
                     'visible_relation_labels': [], 'verdict': None,
                     'recall_of': instance.get('recall_of')})
    return {'contract_version': SYMBOL_VERSION, 'owner': 'MOTION_IDENTITY',
            'decision_sha': checked['decision_sha'], 'request_source': deepcopy(author['cognitive_symbols']['request_source']),
            'catalog_sha': checked['catalog_sha'], 'recipes_sha': checked['recipes_sha'], 'rows': rows,
            'native_consumer': 'ae/rigs/cognitive-symbols.jsx', 'actual_native_consumption': 'UNVERIFIED',
            'normal_speed_review': 'UNOBSERVED', 'artistic_review': 'PENDING', 'semantic_certification': False,
            'public_render_ready': False}


def validate_compiled_symbols(compiled, author, bundles, clock, worlds=None, folder=None):
    expected = compile_symbols(author, bundles, clock, worlds, folder)
    if compiled != expected:
        raise ValueError('Stale cognitive symbol plan or promoted review/approval claim')
    return expected
