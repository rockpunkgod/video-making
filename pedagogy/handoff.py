"""Small, sealed Copy/Motion handoffs; downstream consumers must revalidate."""
from copy import deepcopy

from video_contracts import pointer, seal, sha, verify_seal
from .validation import validate_plan
from .compiler import VERSION


def inspect_historical_handoff(handoff):
    """Read a preserved envelope without upgrading its contract or release."""
    if handoff.get('schema_version') == '0.4.0':
        from .handoff_v04 import inspect_historical_handoff as inspect
        return inspect(handoff)
    verify_seal(handoff)
    if (handoff.get('schema_version') not in ('0.1.0', '0.2.0', '0.3.0')
            or handoff.get('kind') not in ('pedagogy_copy_projection', 'pedagogy_motion_projection')
            or handoff.get('plan_id') != 'pedagogy:' + handoff.get('plan_sha', '')
            or handoff.get('public_render_ready') is not False):
        raise ValueError('Invalid historical Pedagogy handoff envelope')
    return {'status': 'HISTORICAL_ONLY', 'contract_version': handoff['schema_version'],
            'current_upstream_verified': False, 'consumption_allowed': False, 'public_render_ready': False}


def _ready(plan, bundle, status):
    validate_plan(plan, bundle, status)
    if plan['availability']['status'] != 'READY':
        raise ValueError('Pedagogy handoff blocked: ' + plan['availability']['status']
                         + ' ' + ', '.join(plan['availability']['blockers'] + plan['availability']['gaps']))


def _base(plan, kind):
    return {'schema_version': VERSION, 'kind': kind, 'plan_id': plan['plan_id'],
        'plan_sha': plan['plan_sha'], 'input_binding': deepcopy(plan['input_binding']),
        'mode': plan['mode'], 'scope': plan['answer_scope']['scope'], 'public_render_ready': False,
        'generated_at': plan['generated_at'],
        'revalidation_required': 'validate_handoff with frozen source and current upstream status'}


def copy_projection(plan, bundle, status):
    _ready(plan, bundle, status)
    if plan['schema_version'] == '0.4.0':
        from .handoff_v04 import copy_projection as project, inspect_historical_handoff
        result = project(plan)
        inspect_historical_handoff(result)
        return result
    result = _base(plan, 'pedagogy_copy_projection')
    result.update(hookable_problem=deepcopy(plan['symptom']),
        first_signal=deepcopy(plan['first_signal']), first_action=deepcopy(plan['first_action']),
        judgment_point=deepcopy(plan['judgment_point']), memory_phrase=deepcopy(plan['memory_phrase']),
        method_stamp=deepcopy(plan['method_stamp']),
        original_question=deepcopy(plan['original_question']),
        original_question_refs=deepcopy(plan['original_question_refs']),
        must_show_boundary=deepcopy(plan['boundaries']['tell_now']),
        student_model=deepcopy(plan['student_model']),
        payoff_structure=deepcopy(plan['payoff']), do_not_say=deepcopy(plan['prohibited_claims']),
        evidence_snippets=[{'ref': deepcopy(ref), 'span': deepcopy(pointer(bundle, ref['pointer']))}
                           for ref in plan['evidence_refs']],
        claim_bindings=deepcopy(plan['public_claims']),
        answer_scope=deepcopy(plan['answer_scope']),
        omitted_boundary_ids=[x['item_id'] for x in plan['boundaries']['tell_later']],
        truth_guard_sha=sha(plan['truth_guard']))
    if 'boundary_delivery' in plan:
        result['boundary_delivery'] = deepcopy(plan['boundary_delivery'])
        result['evidence_snippets'] = [s for s in result['evidence_snippets']
            if s['ref'] in plan['boundary_delivery']['focus_evidence_refs']]
    return seal(result)


def motion_projection(plan, bundle, status):
    _ready(plan, bundle, status)
    if plan['schema_version'] == '0.4.0':
        from .handoff_v04 import motion_projection as project, inspect_historical_handoff
        result = project(plan)
        inspect_historical_handoff(result)
        return result
    result = _base(plan, 'pedagogy_motion_projection')
    result.update(symptom_object=deepcopy(plan['symptom']),
        action_object=deepcopy(plan['first_action']),
        transformation={'evidence_refs': deepcopy(plan['evidence_refs']),
                        'actual_outputs': deepcopy(plan['answer_scope']['actual_outputs'])},
        settle_state=deepcopy(plan['judgment_point']),
        boundary_event=deepcopy(plan['boundaries']['tell_now']),
        do_not_say=deepcopy(plan['prohibited_claims']),
        truth_guard_sha=sha(plan['truth_guard']),
        ae_effect_selection=None)
    if 'boundary_delivery' in plan:
        result['boundary_delivery'] = deepcopy(plan['boundary_delivery'])
    return seal(result)


def validate_handoff(handoff, plan, bundle, status, *, required_version=None):
    verify_seal(handoff)
    if required_version is not None and handoff.get('schema_version') != required_version:
        raise ValueError('Handoff contract mismatch; recompile and reproject from current frozen inputs')
    kinds = {'pedagogy_copy_projection': copy_projection,
             'pedagogy_motion_projection': motion_projection}
    if handoff.get('kind') not in kinds:
        raise ValueError('Unknown pedagogy handoff')
    expected = kinds[handoff['kind']](plan, bundle, status)
    if expected != handoff:
        raise ValueError('Handoff modified a frozen teaching projection')
    return {'status': 'PASS', 'public_render_ready': False}
