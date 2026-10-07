"""Selective disclosure of frozen assertions, never new teaching assertions."""
from copy import deepcopy
import math

from video_contracts import now, pointer, review_semantics, seal, sha
from .sources import FrozenSource
from . import policy

VERSION = '0.2.0'
FIELD_CANDIDATES = {
    'symptom': ('/student_symptoms/0', '/four_step_card/start', '/trigger_cues/0'),
    'first_signal': ('/four_step_card/start', '/trigger_cues/0'),
    'first_action': ('/four_step_card/first_cut', '/core_action'),
    'judgment_point': ('/four_step_card/judge', '/decision_rule'),
    'memory_phrase': ('/compact/line', '/memory_hook'),
}
FIELD_ALLOWED = {
    'symptom': ('/student_symptoms/', '/four_step_card/start', '/trigger_cues/', '/common_wrong_instinct'),
    'first_signal': ('/four_step_card/start', '/trigger_cues/'),
    'first_action': ('/four_step_card/first_cut', '/core_action', '/compact/line'),
    'judgment_point': ('/four_step_card/judge', '/decision_rule'),
    'memory_phrase': ('/compact/line', '/memory_hook', '/four_step_card/first_cut'),
}


def _field_allowed(source, key, path):
    for suffix in FIELD_ALLOWED[key]:
        allowed = source.method_path + suffix
        if path == allowed or (suffix.endswith('/') and path.startswith(allowed)
                               and path[len(allowed):].isdigit()):
            return True
    if key == 'first_action':
        return any(path == p + '/' + source.action_key for p in source.action_paths)
    if key == 'judgment_point' and source.transport == 'frozen_asset':
        return any(path == p + '/decision_rule_check' for p in source.action_paths)
    return False


def plan_semantics(plan):
    return {k: v for k, v in plan.items()
            if k not in ('plan_sha', 'plan_id', 'generated_at', 'content_sha', 'envelope_sha')}


def _item(source, item_id, path):
    original = pointer(source.bundle, path)
    if not isinstance(original, str) or not original.strip():
        raise ValueError('Student projection requires an existing nonempty text assertion')
    literal = path.startswith(source.question_path + '/') or '/evidence/' in path
    return {'item_id': item_id, 'text': original if literal else policy.surface_text(original),
        'projection_operation': 'literal_source_v1' if literal else 'implementation_labels_only_v1',
        'source_refs': [source.ref(path)],
        'action_artifact_refs': [source.ref(p) for p in source.action_paths],
        'evidence_refs': [source.ref(p) for p in source.evidence_paths],
        'review_refs': [source.ref(p) for p in source.review_paths]}


def _request(selection, fields, extra_boundary_refs):
    if not isinstance(fields, dict) or set(fields) - set(FIELD_CANDIDATES):
        raise ValueError('Only known projection fields may be selected; free-form copy is forbidden')
    if any(not isinstance(v, str) for v in fields.values()):
        raise ValueError('Field selections must be exact frozen JSON pointers')
    if not isinstance(extra_boundary_refs, list) or any(not isinstance(p, str) for p in extra_boundary_refs):
        raise ValueError('Boundary selections must be frozen JSON pointers')
    if len(set(extra_boundary_refs)) != len(extra_boundary_refs):
        raise ValueError('Duplicate boundary selection')
    return deepcopy({'selection': selection, 'fields': fields,
                     'extra_boundary_refs': extra_boundary_refs})


def compile_plan(bundle, status, selection, *, mode='first_touch', audience='first_time_student',
                 channel='video', duration_target=30, fields=None, extra_boundary_refs=None,
                 generated_at=None):
    if mode not in policy.MODES or channel not in policy.CHANNELS:
        raise ValueError('Unsupported pedagogy mode or channel')
    if audience not in ('first_time_student', 'returning_student'):
        raise ValueError('Unsupported audience')
    if (isinstance(duration_target, bool) or not isinstance(duration_target, (int, float))
            or not math.isfinite(duration_target) or duration_target <= 0):
        raise ValueError('Finite positive duration target required')
    request = _request(selection, fields or {}, extra_boundary_refs or [])
    source = FrozenSource(bundle, status, request['selection'])
    guard = source.guard()
    fields_out, gaps = {}, []
    for key, candidates in FIELD_CANDIDATES.items():
        path = request['fields'].get(key, source.field_path(candidates))
        if path is None:
            fields_out[key] = None
            if mode == 'first_touch' or key in ('first_signal', 'first_action') or (
                    key == 'judgment_point' and mode != 'boundary'):
                gaps.append('missing_frozen_' + key)
            continue
        # A short copy cannot cite an unrelated method or its competing action.
        if not (path.startswith(source.method_path + '/')
                or any(path.startswith(p + '/') for p in source.action_paths)):
            raise ValueError('Field borrows an assertion from another method/action')
        if not _field_allowed(source, key, path):
            raise ValueError('Typed projection field cannot display engineering metadata or arbitrary method internals')
        if '/output/' in path or path.endswith('/answer'):
            raise ValueError('Output/answer values are not a first-action teaching rule')
        fields_out[key] = _item(source, key, path)
    boundary_paths = [source.method_path + '/stop_rule'] + [
        p + '/' + source.stop_key for p in source.action_paths]
    boundary_paths += source.caveat_paths()
    for path in request['extra_boundary_refs']:
        allowed = any(path == source.method_path + '/' + key
                      or path.startswith(source.method_path + '/' + key + '/')
                      for key in ('stop_rule', 'four_step_card/stop', *policy.CAVEAT_FIELDS))
        allowed |= any(path.startswith(p + '/reviewed_claims/')
                       for p in source.review_paths)
        allowed |= any(path.startswith(p + '/record/reviewed_claims/')
                       for p in source.review_paths)
        if not allowed:
            raise ValueError('Additional caveat must come from this method or its active review')
        if path not in boundary_paths:
            boundary_paths.append(path)
    boundaries = {'tell_now': [], 'tell_later': [], 'engine_only': []}
    risk_items = []
    for i, path in enumerate(boundary_paths):
        item = _item(source, 'boundary-' + str(i + 1), path)
        risk, refs = source.risk(path)
        current_stop = any(path == p + '/' + source.stop_key for p in source.action_paths)
        if current_stop:
            risk['current_relevance'] = 'high'
        tier, reason = policy.disclosure(risk, current_stop=current_stop)
        item.update(disclosure_tier=tier, risk=risk, risk_assessment_refs=refs,
                    disclosure_reason=reason, current_action_stop=current_stop)
        # Identical assertions do not become two different student boundaries.
        # Both original source bindings remain. Different wording is not merged.
        existing = next((x for x in boundaries[tier.lower()] if x['text'] == item['text']), None)
        if existing:
            existing['source_refs'] += item['source_refs']
            existing['risk_assessment_refs'] += refs
            existing['current_action_stop'] |= current_stop
        else:
            boundaries[tier.lower()].append(item)
        risk_items.append({'item_id': existing['item_id'] if existing else item['item_id'],
            'source_refs': deepcopy(item['source_refs']), 'risk': deepcopy(risk),
            'tier': tier, 'assessment_refs': refs, 'reason': reason})
    for key in policy.ENGINE_FIELDS:
        boundaries['engine_only'].append({'item_id': 'engine-' + key, 'field': key,
            'disclosure_tier': 'ENGINE_ONLY',
            'reason': 'Typed implementation metadata retained in the guard; not a student rule'})
    cases = source.cases()
    required_case = policy.MODE_CASE.get(mode)
    if required_case and required_case not in cases:
        gaps.append('missing_reviewed_' + required_case + '_case')
    if not source.actions:
        gaps.append('missing_actual_action')
    current_boundaries = boundaries['tell_now']
    steps = []
    if mode == 'first_touch':
        for kind, field in (('observation', 'first_signal'), ('action', 'first_action'),
                            ('judgment', 'judgment_point')):
            if fields_out[field]:
                steps.append({'kind': kind, 'item': deepcopy(fields_out[field])})
    else:
        question_stem_path = source.question_path + '/stem'
        steps.append({'kind': 'question', 'item': _item(source, 'original-question', question_stem_path)})
        if fields_out['first_signal']:
            steps.append({'kind': 'observation', 'item': deepcopy(fields_out['first_signal'])})
        if mode != 'boundary':
            for i, path in enumerate(source.action_paths):
                steps.append({'kind': 'action', 'item': _item(source, 'actual-action-' + str(i + 1),
                                                            path + '/' + source.action_key)})
            for i, path in enumerate(source.evidence_paths):
                steps.append({'kind': 'evidence', 'item': _item(source, 'evidence-' + str(i + 1),
                                                              path + '/quote')})
        if required_case in cases and '/reviewed_claims/' in cases[required_case]['pointer']:
            steps.append({'kind': 'case', 'item': _item(source, 'case-claim', cases[required_case]['pointer'])})
        if fields_out['judgment_point'] and mode != 'boundary':
            steps.append({'kind': 'judgment', 'item': deepcopy(fields_out['judgment_point'])})
        steps += [{'kind': 'stop', 'item': deepcopy(b)} for b in current_boundaries]
    student_items = [v for v in fields_out.values() if v] + current_boundaries
    student_items += [s['item'] for s in steps]
    lint = sorted(set(code for item in student_items
                      for code in policy.claim_lint(item['text'], source.method['primary_role'])))
    metrics = {'core_actions': len(source.actions), 'primary_boundary': len(current_boundaries),
        'memory_phrase': int(fields_out['memory_phrase'] is not None),
        'primary_evidence_cluster': len(source.actions),
        'simultaneous_concepts': len({s['kind'] for s in steps
                                      if s['kind'] in ('observation', 'action', 'judgment')})}
    excess = policy.overload(metrics, student_items) if mode == 'first_touch' else []
    blockers = (['PEDAGOGY_OVERLOAD:' + e for e in excess]
                + ['CLAIM_LINT:' + e for e in lint])
    availability = 'UNAVAILABLE_EVIDENCE_GAP' if gaps else 'HOLD' if blockers else 'READY'
    role = source.method['primary_role']
    prohibited = ['不得新增教学判断或 Evidence', '不得把局部动作包装成整题答案',
                  '不得提高确定性或方法成熟度', '不得隐去当前必要刹车']
    if role == 'reducer':
        prohibited.append('不要说：做到这里答案就出来了')
    elif role == 'locator':
        prohibited.append('不要说：找到这句话就能选答案')
    elif role in ('framework', 'interpreter'):
        prohibited.append('不要说：结构或理解产物已经确定最终答案')
    if source.method['method_id'] == 'G01':
        prohibited.append('不要说：到这里词形就确定了或所以填具体词')
    omitted = [dict(item_id=x['item_id'], source_refs=deepcopy(x['source_refs']),
                    reason=x['disclosure_reason'], disclosure_tier='TELL_LATER',
                    still_exists=True, risk_assessment_refs=deepcopy(x['risk_assessment_refs']))
               for x in boundaries['tell_later']]
    omitted += [dict(item_id=x['item_id'], reason=x['reason'], disclosure_tier='ENGINE_ONLY',
                     still_exists=True, source_refs=[]) for x in boundaries['engine_only']]
    omitted.append({'item_id': 'complete_truth_payload',
        'reason': 'Full frozen contract remains the guard; only selected assertions form this projection',
        'disclosure_tier': 'BACKEND_GUARD', 'still_exists': True,
        'source_refs': [source.ref(source.method_path)] + [source.ref(p) for p in source.action_paths]})
    followup = {kind: {'status': 'AVAILABLE' if kind in cases else 'UNAVAILABLE_EVIDENCE_GAP',
                      'case_ref': deepcopy(cases.get(kind))}
                for kind in ('counterexample', 'boundary', 'transfer', 'hard')}
    source_binding = {'asset_id': bundle['asset_id'], 'semantic_binding_sha': bundle['semantic_binding_sha'],
        'source_sha': sha(source.source), 'question_sha': sha(source.question),
        'selected_method_sha': sha(review_semantics(source.method)),
        'selected_actions_sha': sha(review_semantics(source.actions)), 'transport': source.transport}
    stamp_path = source.field_path(('/brand_name', '/source_name'))
    method_stamp = _item(source, 'method_stamp', stamp_path) if stamp_path else None
    public_claims = []
    if availability == 'READY':
        seen = set()
        for item in student_items:
            key = sha(item)
            if key not in seen:
                seen.add(key)
                public_claims.append(deepcopy(item))
    plan = {'schema_version': VERSION, 'kind': 'pedagogy_plan',
        'compiler_version': VERSION, 'policy_version': policy.VERSION,
        'source_analysis_sha': source.analysis_sha, 'input_binding': source_binding,
        'method_id': source.method['method_id'], 'method_version': source.method['version'], 'role': role,
        'question_id': source.question['question_id'],
        'original_question': {k: deepcopy(source.question[k]) for k in ('question_id', 'stem', 'options') if k in source.question},
        'mode': mode, 'audience': audience, 'channel': channel, 'duration_target': duration_target,
        'method_stamp': method_stamp,
        'duration_status': 'editorial_target_not_timing_or_learning_efficacy_certification',
        **fields_out, 'student_steps': steps,
        'student_model': {'see': deepcopy(fields_out['symptom']),
            'think': deepcopy(fields_out['first_signal']), 'do': deepcopy(fields_out['first_action']),
            'check': deepcopy(fields_out['judgment_point']), 'stop': deepcopy(current_boundaries)},
        'evidence_refs': [source.ref(p) for p in source.evidence_paths],
        'boundaries': boundaries, 'omitted_items': omitted, 'followup_content': followup,
        'case_content_matrix': {k: list(v) for k, v in policy.CASE_CONTENT_MATRIX.items()},
        'teaching_risk': {'levels': list(policy.RISK_LEVELS), 'items': risk_items,
                          'unknown_is_low': False, 'numeric_score': None},
        'compression_audit': {'included': [i['item_id'] for i in public_claims],
            'omitted': deepcopy(omitted), 'preserved': ['evidence', 'role', 'stop', 'certainty', 'answer', 'maturity'],
            'prohibited_changes': list(policy.PROHIBITED_CHANGES),
            'guard_sha': sha(guard), 'structural_lint_only': True,
            'semantic_truth_certification': False},
        'cognitive_load': {'budget': deepcopy(policy.FIRST_TOUCH_BUDGET), 'metrics': metrics,
            'status': 'PEDAGOGY_OVERLOAD' if excess else 'PASS' if mode == 'first_touch' else 'NOT_FIRST_TOUCH',
            'exceeded': excess},
        'answer_scope': {'scope': 'method_action_demo', 'answer': None,
            'may_output_final_answer': False, 'upstream_answer': deepcopy(source.upstream_answer),
            'upstream_closed': source.upstream_closed,
            'actual_outputs': [deepcopy(a['output']) for a in source.actions]},
        'stop_state': {'state': 'produced_bounded_action', 'stop_applied': False,
            'method_stop_ref': deepcopy(guard['method_stop_ref']),
            'action_stop_refs': deepcopy(guard['action_stop_refs'])},
        'working_rule': {'text': fields_out['first_action']['text'] if fields_out['first_action'] else None,
            'method_id': source.method['method_id'], 'version': source.method['version'], 'role': role,
            'scope': 'selected_question_and_actual_action',
            'certainty': 'upstream_reviewed_assertion_not_independent_semantic_certification',
            'source_action_refs': [source.ref(p) for p in source.action_paths],
            'source_text_refs': deepcopy(fields_out['first_action']['source_refs']) if fields_out['first_action'] else []},
        'payoff': {'before_complexity': [pointer(bundle, p)['quote'] for p in source.evidence_paths],
            'after_structure': [deepcopy(a['output']) for a in source.actions],
            'allowed_claim': deepcopy(fields_out['judgment_point']),
            'visualizable': True, 'performance_claim_allowed': False,
            'reviewed_support': source.payoff_support()},
        'prohibited_claims': prohibited, 'public_claims': public_claims,
        'source_refs': [source.ref(source.method_path)] + [source.ref(p) for p in source.action_paths],
        'truth_guard': guard,
        'semantic_review': {'level': source.review_level,
                           'independent_human_certified': source.review_level == 'human_certified'},
        'availability': {'status': availability, 'gaps': gaps, 'blockers': blockers},
        'release_state': {'teaching': 'HOLD', 'source_display': 'HOLD', 'editorial': 'HOLD'},
        'public_render_ready': False, 'replay_request': request,
        'generated_at': generated_at or now()}
    plan['plan_sha'] = sha(plan_semantics(plan))
    plan['plan_id'] = 'pedagogy:' + plan['plan_sha']
    return seal(plan)


class PedagogyCompiler:
    def compile(self, analysis, *, status, selection, **kwargs):
        """`analysis` is an exported frozen transport, never an unbound Core result."""
        return compile_plan(analysis, status, selection, **kwargs)
