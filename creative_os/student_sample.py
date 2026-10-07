"""Copy-bound local picture preparation, with an explicit wait for user audio.

The direction file supplies layout and already reviewed relations. This module
does not parse English, choose disclosure, infer an answer, or certify semantics.
"""
from copy import deepcopy
import math
import re

from video_contracts import pointer, sha
from student_pov.validation import validate_copy

VERSION = '0.1.0'


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()


def resolve_text(binding, documents):
    if set(binding) - {'document', 'pointer', 'sha', 'start', 'end'}:
        raise ValueError('Unknown visual text binding field')
    if binding['document'] not in documents:
        raise ValueError('Visual text must come from the provided frozen inputs')
    value = pointer(documents[binding['document']], binding['pointer'])
    if not isinstance(value, str) or sha(value) != binding['sha']:
        raise ValueError('Visual text source binding changed')
    if ('start' in binding) != ('end' in binding):
        raise ValueError('Visual source span needs both offsets')
    if 'start' in binding:
        start, end = binding['start'], binding['end']
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(value)):
            raise ValueError('Visual source span is outside the frozen text')
        value = value[start:end]
    return value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_direction(direction, copy, plan, bundle):
    if direction['version'] != VERSION or direction['profile'] != 'relation_comparison':
        raise ValueError('Unsupported picture preparation profile')
    if copy['method_id'] != 'R02' or copy['role'] != 'decider':
        raise ValueError('This pilot only supports an existing R02 bounded decision')
    canvas = direction['canvas']
    if (canvas['width'], canvas['height'], canvas['fps']) != (1920, 1080, 24):
        raise ValueError('Picture preparation requires the 1080p24 profile')
    duration = canvas['duration']
    if not _number(duration) or duration <= 0 or duration * 24 != round(duration * 24):
        raise ValueError('Duration must be finite and frame aligned')
    phases = direction['phases']
    names = ('original', 'focus', 'action', 'collapse', 'stamp', 'end')
    if (set(phases) != set(names) or phases['original'] != 0 or phases['end'] != duration
            or any(not _number(phases[n]) for n in names)
            or any(phases[a] >= phases[b] for a, b in zip(names, names[1:]))):
        raise ValueError('Original question must precede the method action and payoff')
    if direction['voice_status'] != 'AWAITING_USER_AUDIO':
        raise ValueError('Picture preparation cannot declare voice readiness')
    documents = {'copy': copy, 'plan': plan, 'bundle': bundle}
    focus_quotes = {r['pointer'] + '/quote' for r in
                    plan.get('boundary_delivery', {}).get('focus_evidence_refs', plan['evidence_refs'])}
    ids = set()
    for node in direction['nodes']:
        if node['node_id'] in ids:
            raise ValueError('Duplicate picture node')
        ids.add(node['node_id'])
        if node['kind'] not in ('text', 'line', 'panel'):
            raise ValueError('Unsupported native picture primitive')
        if (not 0 <= node['in_point'] < node['out_point'] <= duration
                or not _number(node['size']) or node['size'] <= 0
                or len(node['position']) != 2 or any(not _number(x) for x in node['position'])
                or not re.fullmatch(r'#[0-9A-Fa-f]{6}', node['color'])):
            raise ValueError('Invalid native node geometry')
        if node['kind'] == 'text':
            binding = node['text_binding']; doc = binding['document']; path = binding['pointer']
            if (doc == 'bundle' and path not in focus_quotes
                    or doc == 'plan' and not re.fullmatch(r'/original_question/(?:stem|passage|options/[^/]+)', path)
                    or doc == 'copy' and not re.fullmatch(r'/final_script/\d+/(?:vo|screen_copy/\d+)', path)):
                raise ValueError('Picture cannot display undisclosed or backend-only teaching text')
            literal = resolve_text(node['text_binding'], documents)
            if normalized(node['text']) != normalized(literal):
                raise ValueError('Visual copy changed the frozen source text')
            if re.search(r'\b[RFGCW]\d{2}\b', node['text']):
                raise ValueError('Internal method IDs are not consumer-facing copy')
        elif not node.get('source_refs'):
            raise ValueError('A visual relation or mark needs an existing source binding')
        for ref in node.get('source_refs', []):
            if (ref['asset_id'] != bundle['asset_id']
                    or sha(pointer(bundle, ref['pointer'])) != ref['sha']
                    or ref not in plan['source_refs'] + plan['truth_guard']['action_refs']
                    + plan['truth_guard']['evidence_refs']):
                raise ValueError('Motion uses an unbound source or another action')
        dimensions = {'position': 2, 'scale': 2, 'opacity': None, 'width': None}
        for key, rows in node['tracks'].items():
            if key not in dimensions:
                raise ValueError('Unsupported native animation property')
            previous = -1
            for time, value in rows:
                if not _number(time) or not 0 <= time < duration or time <= previous:
                    raise ValueError('Animation key times must be ordered within the picture')
                previous = time
                values = value if isinstance(value, list) else [value]
                if (any(not _number(v) for v in values)
                        or dimensions[key] and len(values) != dimensions[key]
                        or key in ('opacity', 'width') and isinstance(value, list)
                        or key == 'opacity' and not 0 <= value <= 100):
                    raise ValueError('Invalid animation key value')
    question = next((n for n in direction['nodes'] if n['node_id'] == 'question'), None)
    if (not question or question['text_binding']['document'] != 'plan'
            or question['text_binding']['pointer'] != '/original_question/stem'
            or normalized(question['text']) != normalized(plan['original_question']['stem'])
            or question['in_point'] != 0 or question['out_point'] != duration
            or question['position'][1] > 160 or question['tracks']):
        raise ValueError('The original question must persist in the upper picture')
    for label, text in plan['original_question']['options'].items():
        option = next((n for n in direction['nodes'] if n['node_id'] == 'option-' + label), None)
        if (not option or normalized(option['text']) != normalized(text)
                or option['text_binding']['document'] != 'plan'
                or option['text_binding']['pointer'] != '/original_question/options/' + label
                or option['in_point'] != 0 or option['out_point'] < phases['focus']):
            raise ValueError('Show the original choices before method demonstration')
    transition = direction['candidate_transition']
    baseline = copy['student_path_comparison']['baseline_path']
    current = copy['student_path_comparison']['method_path']
    before = [label for row in baseline for label in row.get('candidate_ids', [])]
    after = [label for row in current for label in row.get('candidate_ids', [])]
    if transition != {'before': before, 'after': after, 'selected_answer': None}:
        raise ValueError('Picture cannot upgrade candidate reduction into an answer')
    if not after or len(after) >= len(before):
        raise ValueError('This profile needs a reviewed, bounded candidate reduction')
    eliminated = set(before) - set(after)
    actual = {o['candidate'] for o in plan['answer_scope']['actual_outputs']
              if o.get('kind') == 'candidate_decision' and o.get('effect') == 'eliminate'}
    if eliminated != actual or plan['answer_scope']['may_output_final_answer']:
        raise ValueError('Candidate change must match the existing bounded action output')
    for label in after:
        for nid in ('option-' + label, 'choice-label-' + label):
            node = next((n for n in direction['nodes'] if n['node_id'] == nid), None)
            if not node or node['color'] != direction['palette']['ink'] or any(
                    value != 100 for _, value in node['tracks'].get('opacity', [])):
                raise ValueError('Remaining candidates must stay neutral and unresolved')
    for label in eliminated:
        mark = next((n for n in direction['nodes'] if n['node_id'] == 'choice-' + label + '-strike'), None)
        if not mark or mark['kind'] != 'line' or mark['in_point'] != phases['collapse']:
            raise ValueError('Show only the reviewed candidate elimination at the payoff')
    visible = [normalized(n['text']) for n in direction['nodes'] if n['kind'] == 'text']
    for boundary in copy.get('tell_now_boundaries', []):
        if normalized(boundary['text']) not in visible:
            raise ValueError('Required reviewed boundary presentation missing')
    voiced = [(s['scene_id'], s['vo']) for s in copy['final_script'] if s['vo']]
    slots = direction['voice_slots']
    if [(s['scene_id'], s['text']) for s in slots] != voiced:
        raise ValueError('Pending voice slots must preserve the reviewed narration')
    if any(not 0 <= s['start'] < s['end'] <= duration for s in slots):
        raise ValueError('Pending voice slot outside the picture')
    return documents


def build_spec(copy, projection, plan, bundle, status, direction, fonts):
    result = validate_copy(copy, projection, plan, bundle, status)
    if not result['consumption_allowed']:
        raise ValueError('Picture generation requires current READY Copy')
    validate_direction(direction, copy, plan, bundle)
    if not fonts or any(n['font'] not in {f['postscript'] for f in fonts.values()}
                        for n in direction['nodes'] if n['kind'] == 'text'):
        raise ValueError('Every visible text font needs an explicit measurement binding')
    spec = {
        'version': VERSION, 'kind': 'student_pov_picture_preparation',
        'asset_id': bundle['asset_id'], 'semantic_binding_sha': bundle['semantic_binding_sha'],
        'plan_sha': plan['plan_sha'], 'copy_sha': copy['copy_sha'],
        'copy_lock': {'final_copy_sha': copy['final_copy_sha'], 'polished_from_sha': None,
                      'editorial_review_sha': None},
        'direction': deepcopy(direction), 'fonts': deepcopy(fonts),
        'preparation_state': 'PICTURE_PREPARED_VOICE_PENDING',
        'timing_basis': 'editorial_estimate_pending_final_audio',
        'sample_delivery_allowed': False, 'public_render_ready': False,
        'verification_boundary': 'deterministic_binding_lint_not_semantic_or_human_taste_certification',
    }
    spec['spec_sha'] = sha(spec)
    return spec


def validate_spec(spec, copy, projection, plan, bundle, status):
    expected = build_spec(copy, projection, plan, bundle, status, spec['direction'], spec['fonts'])
    if expected != spec:
        raise ValueError('Picture spec or waiting-for-voice gate changed')
    return spec


def require_sample_delivery(spec):
    """This preparation artifact cannot stand in for a voiced delivery."""
    if (spec.get('kind') == 'student_pov_picture_preparation'
            or not spec.get('sample_delivery_allowed') or spec.get('preparation_state') != 'FINAL_AUDIO_BOUND'):
        raise ValueError('Wait for the user to confirm final voice before sample delivery')
