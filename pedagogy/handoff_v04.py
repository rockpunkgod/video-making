"""Versioned narrow consumers; no automatic activation of Student POV 0.3."""
from copy import deepcopy

from video_contracts import ROOT, _validator, seal, sha, verify_seal


def _base(plan, kind):
    return {'schema_version': '0.4.0', 'kind': kind, 'plan_id': plan['plan_id'],
        'plan_sha': plan['plan_sha'], 'input_binding': deepcopy(plan['input_binding']),
        'mode': plan['mode'], 'scope': 'method_action_demo', 'public_render_ready': False,
        'generated_at': plan['generated_at'],
        'consumer_contract': 'explicit_v04_adapter_required_current_downstream_unchanged',
        'revalidation_required': 'validate_handoff with frozen source and current upstream status'}


def _work(plan, text):
    delta = plan['work_delta']
    result = {k: delta[k] for k in ('baseline_kind', 'baseline_measured', 'learner_transfer_validated', 'scope', 'status')}
    for key in ('baseline_work', 'removed_work', 'deferred_work', 'still_required_work'):
        rows = delta[key]
        result[key] = None if rows is None else [{k: deepcopy(row[k]) for k in
            (('work_id', 'text', 'scope', 'source_refs') if text else ('work_id', 'scope', 'source_refs'))} for row in rows]
    result['method_work'] = [{k: deepcopy(row[k]) for k in ('work_id', 'output_ref', 'action_artifact_refs', 'evidence_refs')}
                             for row in delta['method_work']]
    return result


def copy_projection(plan):
    result = _base(plan, 'pedagogy_copy_projection')
    result.update(learning_unit=deepcopy(plan['first_touch']),
        primary_action=deepcopy(plan['primary_action']),
        supporting_action_refs=[deepcopy(a['action_ref']) for a in plan['supporting_actions']],
        original_question=deepcopy(plan['original_question']),
        original_question_refs=deepcopy(plan['original_question_refs']),
        method_stamp=deepcopy(plan['method_stamp']),
        work_delta=_work(plan, True),
        payoff={'structural_before': deepcopy(plan['payoff']['structural_before']),
                'structural_after': deepcopy(plan['payoff']['structural_after']),
                'allowed_claim': deepcopy(plan['payoff']['allowed_claim']),
                'payoff_scope': plan['payoff']['payoff_scope'],
                'decision_completion': False},
        must_obtain=deepcopy(plan['boundary_presentations']),
        evidence_refs=deepcopy(plan['boundary_delivery']['focus_evidence_refs'] if 'boundary_delivery' in plan else plan['evidence_refs']),
        remaining_object_ids=deepcopy(plan['student_model']['uncertainty_remaining']),
        answer_permission={'answer': None, 'may_output_final_answer': False},
        do_not_say=deepcopy(plan['payoff']['forbidden_claims']),
        truth_guard_sha=sha(plan['truth_guard']))
    return seal(result)


def motion_projection(plan):
    result = _base(plan, 'pedagogy_motion_projection')
    obligations = []
    for presentation in plan['boundary_presentations']:
        # Screen/Copy own literal ranges and text. Motion keeps the reviewed
        # coverage obligation and source item IDs, not another copy of them.
        coverage = {k: deepcopy(presentation['coverage'][k]) for k in
                    ('source_items', 'coverage_type', 'review_ref')}
        obligations.append({'item_id': presentation['item_id'],
            'presentation_roles': deepcopy(presentation['presentation_roles']),
            'delivery_form': presentation['delivery_form'], 'scene': presentation['scene'],
            'coverage': coverage, 'student_obtainment_required': True})
    work = _work(plan, False)
    for key in ('baseline_work', 'removed_work', 'deferred_work', 'still_required_work'):
        rows = work[key]
        # Work objects carry these IDs and bindings; do not repeat the proof
        # on every disposition. Required/deferred work still remains explicit.
        work[key] = None if rows is None else [r['work_id'] for r in rows]
    result.update(cognitive_structure=deepcopy(plan['cognitive_structure']),
        cognitive_reduction=deepcopy(plan['cognitive_reduction']),
        work_delta=work, boundary_obligations=obligations,
        answer_permission={'answer': None, 'may_output_final_answer': False},
        truth_guard_sha=sha(plan['truth_guard']))
    catalog = {}
    def intern(value):
        if isinstance(value, dict):
            if set(value) == {'asset_id', 'pointer', 'sha'}:
                rid = 'ref:' + sha(value)[:24]
                if rid in catalog and catalog[rid] != value:
                    raise ValueError('Cognitive reference ID collision')
                catalog[rid] = deepcopy(value)
                return {'catalog_ref': rid}
            return {k: intern(v) for k, v in value.items()}
        if isinstance(value, list): return [intern(v) for v in value]
        return value
    result = intern(result)
    result['reference_catalog'] = catalog
    return seal(result)


def inspect_historical_handoff(value):
    path = ROOT / 'schemas/pedagogy-handoff-v04.json'
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(value)
    except Exception as error:
        raise ValueError('Invalid v0.4 Pedagogy handoff: ' + str(error)) from error
    verify_seal(value)
    if value['kind'] == 'pedagogy_motion_projection':
        catalog = value['reference_catalog']
        if any(rid != 'ref:' + sha(ref)[:24] for rid, ref in catalog.items()):
            raise ValueError('Cognitive reference catalog hash mismatch')
        used = set()
        def expand(item):
            if isinstance(item, dict):
                if set(item) == {'catalog_ref'}:
                    rid = item['catalog_ref']
                    if rid not in catalog: raise ValueError('Dangling cognitive source reference')
                    used.add(rid)
                    return deepcopy(catalog[rid])
                return {k: expand(v) for k,v in item.items()}
            if isinstance(item, list): return [expand(v) for v in item]
            return item
        expanded = expand({k: v for k,v in value.items() if k != 'reference_catalog'})
        if used != set(catalog): raise ValueError('Unused cognitive source reference')
        from .structure import validate_structure
        validate_structure(expanded['cognitive_structure'])
        bound_work = {o['source_work_id'] for o in expanded['cognitive_structure']['objects']
                      if o['source_work_id'] is not None}
        for key in ('baseline_work', 'removed_work', 'deferred_work', 'still_required_work'):
            if not set(expanded['work_delta'][key] or []) <= bound_work:
                raise ValueError('Work disposition lacks its bound cognitive object')
    return {'status': 'HISTORICAL_ONLY', 'contract_version': '0.4.0',
            'current_upstream_verified': False, 'consumption_allowed': False, 'public_render_ready': False}
