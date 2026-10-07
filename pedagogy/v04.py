"""Minimal learning units compiled afresh from frozen truth and current status.

The v0.3 producer remains byte-compatible. It supplies existing disclosure and
review bindings; this lane adds work/state contracts, never a new English rule.
"""
from copy import deepcopy
import json

from video_contracts import pointer, seal, sha
from .sources import FrozenSource
from . import policy
from .work_delta import project_work_delta
from .structure import project_structure

VERSION = '0.4.0'


def _unit(ref):
    return 'truth:' + sha(ref)


def _actions(source, base):
    ids = [a.get('execution_id', a.get('action_id')) for a in source.actions]
    parents = {aid: set(a.get('input_artifact_ids', [])) & set(ids)
               for aid, a in zip(ids, source.actions)}
    used = set().union(*parents.values())
    terminals = [aid for aid in ids if aid not in used]
    primary = terminals[0] if len(terminals) == 1 else None
    ancestors, pending = set(), list(parents.get(primary, []))
    while pending:
        aid = pending.pop()
        if aid not in ancestors:
            ancestors.add(aid); pending += list(parents[aid])
    # Multiple independent operations cannot be hidden as supporting actions.
    if primary is not None and ancestors | {primary} != set(ids):
        primary = None
    rows = []
    for aid, action, path in zip(ids, source.actions, source.action_paths):
        rows.append({'action_id': aid, 'classification': 'primary' if aid == primary else
                     'supporting' if primary else 'independent_primary_candidate',
            'instruction': deepcopy(base['first_action']) if aid == primary else None,
            'action_ref': source.ref(path), 'output_ref': source.ref(path + '/output'),
            'evidence_refs': [source.ref(path + '/evidence/' + str(i)) for i in range(len(action['evidence']))],
            'requires_existing_artifact_ids': deepcopy(action.get('input_artifact_ids', []))})
    return (next((r for r in rows if r['classification'] == 'primary'), None),
            [r for r in rows if r['classification'] == 'supporting'],
            1 if primary else len(rows))


def _presentation_roles(item, coverage):
    roles = []
    if item['current_action_stop']: roles.append('action_stop')
    if any(c['mechanism'] == 'bounded_candidate_state' for c in coverage): roles.append('candidate_status')
    for ref in item['source_refs']:
        path = ref['pointer']
        role = 'scope_limit' if '/cannot_replace/' in path else \
            'counterexample_guard' if '/failure_cases/' in path else \
            'misuse_prevention' if path.endswith('/anti_rule') else 'condition'
        if role not in roles: roles.append(role)
    return roles


def _presentations(source, base):
    review = base['replay_request'].get('boundary_review')
    result = []
    for item in base['boundaries']['tell_now']:
        if review:
            index = next(i for i, g in enumerate(review['presentations']) if g['group_id'] == item['item_id'])
            group = review['presentations'][index]
            coverage = deepcopy(group['coverage'])
            review_ref = {'asset_id': 'pedagogy-boundary-review:' + review['content_sha'],
                          'pointer': '/presentations/' + str(index), 'sha': sha(group)}
            mechanisms = {c['mechanism'] for c in coverage}
            form = 'combined' if len(mechanisms) > 1 else \
                'motion_state' if mechanisms == {'bounded_candidate_state'} else 'screen'
            expression = {'text': item['text'], 'literal_ref': deepcopy(group['literal_ref']),
                          'literal_range': deepcopy(group['literal_range']),
                          'evidence_refs': deepcopy(review['delivery']['focus_evidence_refs']),
                          'candidate_state': deepcopy(base['payoff']['reviewed_support']['record']['answer_scope'])
                              if review['delivery']['bounded_candidate_state'] else None}
            coverage_type = 'explicit_reviewed_presentation'
            scene = group['scene']
        else:
            coverage = [{'source_ref': deepcopy(ref), 'range': [0, len(pointer(source.bundle, ref['pointer']))],
                         'mechanism': 'literal_display'} for ref in item['source_refs']]
            # Default is complete literal display, not permission to suppress a
            # Stop. Identical aliases keep their upstream Review credential.
            review_ref = deepcopy(item['review_refs'][0])
            expression = {'text': item['text'], 'literal_ref': deepcopy(item['source_refs'][0]),
                          'literal_range': coverage[0]['range'], 'evidence_refs': [], 'candidate_state': None}
            form, coverage_type, scene = 'screen', 'complete_literal_display', 'action' if item['current_action_stop'] else 'stop'
        result.append({'item_id': item['item_id'], 'presentation_roles': _presentation_roles(item, coverage),
            'delivery_form': form, 'scene': scene,
            'coverage': {'source_items': [_unit(r) for r in item['source_refs']],
                'displayed_expression': expression, 'coverage_type': coverage_type,
                'review_ref': review_ref, 'parts': coverage},
            'student_obtainment_required': True, 'spoken_readout_required': False})
    return result


def _leaves(value, path):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from _leaves(child, path + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list) and value:
        for i, child in enumerate(value): yield from _leaves(child, path + '/' + str(i))
    else:
        yield path


def validate_compression_audit(audit):
    universe = audit['source_truth_items']
    covered = [*audit['presented_now'], *audit['deferred'], *audit['engine_only'], *audit['explicit_merge_coverage']]
    if (len(universe) != len(set(universe)) or len(covered) != len(set(covered))
            or set(universe) != set(covered) or audit['omitted']):
        raise ValueError('Compression audit must conserve every selected source truth item exactly once')
    if {r['item_id'] for r in audit['item_bindings']} != set(universe):
        raise ValueError('Compression audit source bindings incomplete')
    return audit


def _compression(source, base, presentations):
    roots = [source.method_path, *source.action_paths]
    paths = []
    for root in roots: paths += list(_leaves(pointer(source.bundle, root), root))
    for ref in base['original_question_refs'].values():
        paths += list(_leaves(pointer(source.bundle, ref['pointer']), ref['pointer']))
    paths = list(dict.fromkeys(paths))
    selected = [r['pointer'] for key in ('symptom', 'first_signal', 'first_action', 'judgment_point',
                                       'memory_phrase', 'method_stamp') if base[key] for r in base[key]['source_refs']]
    selected += [r['pointer'] for r in base['original_question_refs'].values()]
    selected += [p + '/' + source.action_key for p in source.action_paths]
    selected += [p + '/output' for p in source.action_paths] + source.evidence_paths
    current = {r['pointer']: item for item in base['boundaries']['tell_now'] for r in item['source_refs']}
    later = {r['pointer'] for item in base['boundaries']['tell_later'] for r in item['source_refs']}
    presentation_by_id = {p['item_id']: p for p in presentations}
    buckets = {k: [] for k in ('presented_now', 'deferred', 'engine_only', 'explicit_merge_coverage')}
    bindings, merged = [], []
    metadata = {'method_id', 'version', 'method_version', 'primary_role', 'role', 'execution_id',
                'action_id', 'review_status', 'state', 'stop_applied', 'evidence_ids', 'input_artifact_ids',
                'question_id', 'status', 'utility_level', 'maturity', 'generated_at', 'created_at', 'updated_at'}
    for path in paths:
        ref = source.ref(path); uid = _unit(ref)
        prefix = lambda parent: path == parent or path.startswith(parent + '/')
        now_item = next((item for parent, item in current.items() if prefix(parent)), None)
        if now_item:
            group = presentation_by_id[now_item['item_id']]
            bucket = 'explicit_merge_coverage' if len(now_item['source_refs']) > 1 else 'presented_now'
            reason = 'Required boundary retained by complete bound presentation coverage'
        elif any(prefix(parent) for parent in later):
            bucket, reason = 'deferred', 'Existing disclosure retains this unexercised boundary for its later branch'
        elif any(prefix(parent) for parent in selected):
            bucket, reason = 'presented_now', 'Selected frozen field or actual action/evidence/output is represented'
        elif any(part in metadata for part in path.split('/')[2:]):
            bucket, reason = 'engine_only', 'Typed implementation identity, lifecycle or maturity metadata'
        else:
            bucket, reason = 'deferred', 'Supplementary frozen detail not selected by existing disclosure; still retained'
        buckets[bucket].append(uid)
        bindings.append({'item_id': uid, 'source_ref': ref, 'disposition': bucket, 'reason': reason})
    for item in base['boundaries']['tell_now']:
        if len(item['source_refs']) > 1:
            group = presentation_by_id[item['item_id']]
            merged.append({'presentation_id': item['item_id'], 'source_items': deepcopy(group['coverage']['source_items']),
                           'review_ref': deepcopy(group['coverage']['review_ref'])})
    result = {'source_truth_items': [b['item_id'] for b in bindings], **buckets, 'merged': merged,
        'omitted': [], 'item_bindings': bindings,
        'inventory_scope': 'selected_frozen_method_actions_and_original_question_fields',
        'coverage_observation_scope': 'planned_handoff_not_rendered_or_student_understanding',
        'reason': 'Full selected frozen inputs remain bound; no semantic deletion or automatic learning certification',
        'guard_sha': sha(base['truth_guard']), 'preserved': deepcopy(base['compression_audit']['preserved']),
        'prohibited_changes': deepcopy(base['compression_audit']['prohibited_changes']),
        'structural_lint_only': True, 'semantic_truth_certification': False}
    return validate_compression_audit(result)


def compile_v04(bundle, status, selection, *, mode='first_touch', audience='first_time_student',
                channel='video', duration_target=30, fields=None, extra_boundary_refs=None,
                generated_at=None, boundary_review=None, structure_input=None):
    from .compiler import compile_plan, plan_semantics
    # Frozen JSON transports have string keys. Match their actual serialized
    # form also for in-memory synthetic controls (e.g. YAML boolean map keys).
    # Canonical JSON bytes/hash and lexical teaching values stay unchanged.
    bundle = json.loads(json.dumps(bundle, ensure_ascii=False, sort_keys=True, allow_nan=False))
    status = json.loads(json.dumps(status, ensure_ascii=False, sort_keys=True, allow_nan=False))
    # Recompile the supplied current source; no historical Plan is a truth input.
    base = compile_plan(bundle, status, selection, mode=mode, audience=audience, channel=channel,
        duration_target=duration_target, fields=fields, extra_boundary_refs=extra_boundary_refs,
        generated_at=generated_at, boundary_review=boundary_review, contract_version='0.3.0')
    source = FrozenSource(bundle, status, selection)
    delta, payoff = project_work_delta(source, base)
    primary, supporting, count = _actions(source, base)
    presentations = _presentations(source, base)
    structure = project_structure(source, base, delta, structure_input)
    result = deepcopy(base)
    result.update(schema_version=VERSION, compiler_version=VERSION,
        compatibility={'previous_contract': '0.3.0', 'recompiled_v03_plan_sha': base['plan_sha'],
                       'migration': 'fresh_compile_from_frozen_asset_and_current_status',
                       'old_outputs_overwritten': False},
        primary_action=primary, supporting_actions=supporting,
        deferred_actions=deepcopy(delta['deferred_work']), primary_action_count=count,
        work_delta=delta, boundary_presentations=presentations, cognitive_structure=structure,
        first_touch={'pain': deepcopy(base['symptom']), 'first_signal': deepcopy(base['first_signal']),
            'first_action': deepcopy(base['first_action']), 'judgment_point': deepcopy(base['judgment_point']),
            'immediate_output': [{'output_ref': source.ref(p + '/output'),
                                 'value': deepcopy(a['output'])} for p,a in zip(source.action_paths, source.actions)],
            'stop': [p['item_id'] for p in presentations], 'memory_phrase': deepcopy(base['memory_phrase'])},
        primary_simplification={'before': deepcopy(payoff['structural_before']) if payoff else None,
            'operation': deepcopy(primary), 'after': deepcopy(payoff['structural_after']) if payoff else None},
        cognitive_reduction={'types': deepcopy(payoff['reduction_types']) if payoff else ['none'],
                             'decision_completion': False, 'source_support_status': delta['status']},
        human_pedagogy_taste={'status': 'PENDING', 'reviewer': None, 'first_action_clear': None,
            'too_much_information': None, 'payoff_clear': None, 'stop_clear': None,
            'reusable_next_time': None, 'notes': None, 'self_signed': False})
    result['payoff'].update(structural_before=deepcopy(payoff['structural_before']) if payoff else None,
        structural_after=deepcopy(payoff['structural_after']) if payoff else None,
        work_delta=deepcopy(delta), allowed_claim=deepcopy(payoff['allowed_claim']) if payoff else None,
        forbidden_claims=deepcopy(base['prohibited_claims']) + [r['claim_key'] for r in delta['unsupported_savings']],
        payoff_scope=payoff['payoff_scope'] if payoff else None)
    before_candidates = len(base['original_question'].get('options', {})) or None
    after_candidates = payoff['structural_reduction']['after'] if payoff and payoff['structural_reduction']['unit'] == 'candidate' else None
    def load(objects, candidates):
        return {'active_objects': deepcopy(objects), 'candidate_count': candidates,
                'evidence_scope': deepcopy(base['evidence_refs']), 'simultaneous_relations': None}
    result['cognitive_load_projection'] = {'before': load(structure['reality_objects'], before_candidates),
        'after': load(structure['focus_objects'], after_candidates),
        'evidence_level': 'reviewed_structure' if payoff else 'unknown',
        'psychological_measurement': False, 'semantic_truth_certification': False}
    unresolved = [o['object_id'] for o in structure['objects'] if o['state'] == 'unresolved']
    result['student_model'].update(attention=deepcopy(structure['attention_transition']),
        object_in_focus=deepcopy(structure['focus_objects']),
        objects_backgrounded=deepcopy(structure['backgroundable_objects']), uncertainty_remaining=unresolved)
    result['compression_audit'] = _compression(source, base, presentations)
    metrics = result['cognitive_load']['metrics']; budget = result['cognitive_load']['budget']
    budget['core_actions'] = 1
    metrics['core_actions'] = count; metrics['primary_evidence_cluster'] = count
    excess = [k for k,v in metrics.items() if k in budget and v > budget[k]] if mode == 'first_touch' else []
    excess += [e for e in base['cognitive_load']['exceeded'] if e not in ('core_actions', 'primary_evidence_cluster')]
    excess = sorted(set(excess))
    result['cognitive_load'].update(exceeded=excess, status='PEDAGOGY_OVERLOAD' if excess else
                                  'PASS' if mode == 'first_touch' else 'NOT_FIRST_TOUCH')
    blockers = [b for b in base['availability']['blockers'] if not b.startswith('PEDAGOGY_OVERLOAD:')]
    blockers += ['PEDAGOGY_OVERLOAD:' + e for e in excess]
    if mode == 'first_touch' and channel == 'video' and count != 1:
        blockers.append('FIRST_TOUCH_ONE_PRIMARY_ACTION_REQUIRED')
    gaps = base['availability']['gaps'] + delta['gaps']
    available = 'UNAVAILABLE_EVIDENCE_GAP' if base['availability']['gaps'] else 'HOLD' if blockers or gaps else 'READY'
    result['availability'] = {'status': available, 'gaps': gaps, 'blockers': blockers}
    result['first_touch_audit'] = {'primary_action_count': count, 'first_action_present': bool(base['first_action']),
        'immediate_output_present': bool(result['first_touch']['immediate_output']),
        'stop_present': bool(presentations), 'memory_phrase_present': bool(base['memory_phrase']),
        'unsupported_payoff': payoff is None,
        'unresolved_work_preserved': payoff is not None and bool(delta['still_required_work'] or delta['deferred_work']),
        'structural_lint_only': True, 'student_understanding_certified': False}
    result['public_claims'] = deepcopy(base['public_claims']) if available == 'READY' else []
    result['replay_request']['contract_version'] = VERSION
    if structure_input is not None: result['replay_request']['structure_input'] = deepcopy(structure_input)
    result['plan_sha'] = sha(plan_semantics(result)); result['plan_id'] = 'pedagogy:' + result['plan_sha']
    return seal(result)
