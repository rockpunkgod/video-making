"""Small, sealed Copy/Motion handoffs; downstream consumers must revalidate."""
from copy import deepcopy

from video_contracts import pointer, seal, sha, verify_seal
from .validation import validate_plan


def _ready(plan, bundle, status):
    validate_plan(plan, bundle, status)
    if plan['availability']['status'] != 'READY':
        raise ValueError('Pedagogy handoff blocked: ' + plan['availability']['status']
                         + ' ' + ', '.join(plan['availability']['blockers'] + plan['availability']['gaps']))


def _base(plan, kind):
    return {'schema_version': '0.1.0', 'kind': kind, 'plan_id': plan['plan_id'],
        'plan_sha': plan['plan_sha'], 'input_binding': deepcopy(plan['input_binding']),
        'mode': plan['mode'], 'scope': 'method_action_demo', 'public_render_ready': False,
        'generated_at': plan['generated_at'],
        'revalidation_required': 'validate_handoff with frozen source and current upstream status'}


def copy_projection(plan, bundle, status):
    _ready(plan, bundle, status)
    result = _base(plan, 'pedagogy_copy_projection')
    result.update(hookable_problem=deepcopy(plan['symptom']),
        first_signal=deepcopy(plan['first_signal']), first_action=deepcopy(plan['first_action']),
        judgment_point=deepcopy(plan['judgment_point']), memory_phrase=deepcopy(plan['memory_phrase']),
        method_stamp=deepcopy(plan['method_stamp']),
        original_question=deepcopy(plan['original_question']),
        must_show_boundary=deepcopy(plan['boundaries']['tell_now']),
        student_model=deepcopy(plan['student_model']),
        payoff_structure=deepcopy(plan['payoff']), do_not_say=deepcopy(plan['prohibited_claims']),
        evidence_snippets=[{'ref': deepcopy(ref), 'span': deepcopy(pointer(bundle, ref['pointer']))}
                           for ref in plan['evidence_refs']],
        claim_bindings=deepcopy(plan['public_claims']),
        answer_scope=deepcopy(plan['answer_scope']),
        omitted_boundary_ids=[x['item_id'] for x in plan['boundaries']['tell_later']],
        truth_guard_sha=sha(plan['truth_guard']))
    return seal(result)


def motion_projection(plan, bundle, status):
    _ready(plan, bundle, status)
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
    return seal(result)


def validate_handoff(handoff, plan, bundle, status):
    verify_seal(handoff)
    kinds = {'pedagogy_copy_projection': copy_projection,
             'pedagogy_motion_projection': motion_projection}
    if handoff.get('kind') not in kinds:
        raise ValueError('Unknown pedagogy handoff')
    expected = kinds[handoff['kind']](plan, bundle, status)
    if expected != handoff:
        raise ValueError('Handoff modified a frozen teaching projection')
    return {'status': 'PASS', 'public_render_ready': False}
