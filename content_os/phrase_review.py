"""Explicit host-authored phrase reviews, separate from frozen teaching bundles.

This producer verifies bindings and freezes a supplied semantic judgement. It
does not infer English roles, generate judgements, or upgrade AI credentials.
"""
from copy import deepcopy

from video_contracts import now, pointer, sha, status_matches
from ae_production.judgement_preflight import inspect_phrase_requests

CONTRACT = 'reviewed-phrase-operations/1.0'
DERIVED_REQUEST_FIELDS = {'lexical_range', 'evidence_container_refs',
    'existing_review_scope', 'operation_authorization', 'required_response'}
PRIMITIVES = {'focus_in_context', 'move_as_group', 'compare_bound_relation'}


def request_bindings(request, bundles, statuses):
    """Recheck this exact request against current upstream source and lifecycle."""
    if request['kind'] != 'upstream_annotation_request':
        raise ValueError('An existing upstream annotation request is required')
    asset = request['action_ref']['asset_id']
    bundle, status = bundles[asset], statuses[asset]
    if not status_matches(bundle, status):
        raise ValueError('Current upstream bundle status is not active')
    action = pointer(bundle, request['action_ref']['pointer'])
    relation = pointer(bundle, request['relation_ref']['pointer'])
    if (action['method_id'] != 'R06' or action['role'] != 'decider'
            or action.get('stop_applied') is not False
            or bundle['evaluation_phase'] != 'post_reveal'
            or action['output']['kind'] != 'candidate_decision'
            or relation['effect'] != action['output']['effect']):
        raise ValueError('Only the current post-reveal R06 decider is supported')
    life = status['lifecycle']
    if not any(r['artifact_id'] == action['execution_id'] and r['status'] == 'active'
               for r in life['actions']):
        raise ValueError('The reviewed action is no longer active')
    relation_id = 'relation:' + str(action['output']['relation_index'])
    if not any(r['artifact_id'] == relation_id and r['status'] == 'active'
               for r in life['decisions']):
        raise ValueError('The reviewed relation is no longer active')
    if any(not any(r['artifact_id'] == wanted['artifact_id'] and r['status'] == 'active'
                   for r in life['reviews']) for wanted in request['review_refs']):
        raise ValueError('An upstream review was withdrawn')
    operations = [{k: deepcopy(v) for k, v in op.items() if k not in DERIVED_REQUEST_FIELDS}
                  for op in request['operations']]
    event = {'scene_id': operations[0]['scene_id'], 'question_id': request['question_id'],
             'source_refs': [request['action_ref'], request['relation_ref']]}
    if inspect_phrase_requests(bundles, event, operations) != request:
        raise ValueError('Request differs from its exact source/action/relation/review')
    return {'request_sha': request['request_sha'], 'request_content_sha': sha(request),
        'question_id': request['question_id'], 'asset_id': asset,
        'action_ref': deepcopy(request['action_ref']),
        'relation_ref': deepcopy(request['relation_ref']),
        'review_refs': deepcopy(request['review_refs']),
        'bundle_content_sha': bundle['content_sha'],
        'semantic_binding_sha': bundle['semantic_binding_sha'],
        'binding_fingerprint': deepcopy(bundle['binding_fingerprint']),
        'upstream_status_sha': sha(status), 'evaluation_phase': bundle['evaluation_phase']}


def validate_decision(decision, request_row, bundles):
    if (decision['operation_id'] != request_row['operation_id']
            or decision['selection'] != request_row['selection']
            or decision['proposed_operation_sha'] != sha(request_row['proposed_operation'])
            or decision['evidence_container_refs'] != request_row['evidence_container_refs']):
        raise ValueError('Reviewed operation is not exactly bound to the request')
    if decision['disposition'] not in ('SUPPORTED_WITH_CONSTRAINTS', 'HOLD'):
        raise ValueError('Explicit supported-or-hold semantic disposition required')
    for key in ('semantic_role', 'judgement', 'basis', 'allowed_use'):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError('A substantive host-authored semantic review is required: ' + key)
    if (not decision.get('prohibited_inferences')
            or any(not isinstance(x, str) or not x.strip() for x in decision['prohibited_inferences'])):
        raise ValueError('Explicit prohibited inferences are required')
    execution = decision['execution']
    if not execution.get('primitives') or not set(execution['primitives']) <= PRIMITIVES:
        raise ValueError('Unknown or missing bounded visual primitive')
    if set(execution) != {'primitives', 'keep_context', 'relation_ref'}:
        raise ValueError('Only explicit bounded visual operations are supported')
    if not execution['keep_context']:
        raise ValueError('Phrase operations must retain their grammatical context')
    for selection in execution['keep_context']:
        ref = selection['source_ref']; source = pointer(bundles[ref['asset_id']], ref['pointer'])
        start, end = selection['start'], selection['end']
        if (sha(source) != ref['sha'] or type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(source) or source[start:end] != selection['quote']
                or ref != decision['selection']['source_ref']
                or not start <= decision['selection']['start'] < decision['selection']['end'] <= end):
            raise ValueError('Context must exactly contain the reviewed source range')


def freeze_phrase_review(request, bundles, statuses, authored):
    binding = request_bindings(request, bundles, statuses)
    if (authored.get('reviewer_kind') != 'ai_host' or not authored.get('reviewer')
            or authored.get('independent_human_certified') is not False
            or not authored.get('revision_id') or not authored.get('review_note')):
        raise ValueError('Explicit AI host review identity and limits required')
    rows = {row['operation_id']: row for row in request['operations']}
    decisions = authored['decisions']
    if (len({r['operation_id'] for r in decisions}) != len(decisions)
            or set(r['operation_id'] for r in decisions) != set(rows)):
        raise ValueError('Each requested operation needs its own explicit review')
    for decision in decisions:
        validate_decision(decision, rows[decision['operation_id']], bundles)
        if decision['execution']['relation_ref'] != request['relation_ref']:
            raise ValueError('An operation cannot substitute another relation')
    review = {'contract': CONTRACT, 'kind': 'frozen_host_phrase_review',
        'created_at': now(), 'revision_id': authored['revision_id'],
        'reviewer': authored['reviewer'], 'reviewer_kind': 'ai_host',
        'level': 'ai_reviewed', 'independent_human_certified': False,
        'review_note': authored['review_note'], 'binding': binding,
        'decisions': deepcopy(decisions), 'scope': 'PRIVATE_BOUNDED_G2_ONLY',
        'public_render_ready': False}
    review['review_sha'] = sha(review)
    state = {'contract': CONTRACT, 'kind': 'phrase_review_current_status',
        'revision_id': review['revision_id'], 'review_sha': review['review_sha'],
        'request_content_sha': sha(request), 'upstream_status_sha': binding['upstream_status_sha'],
        'effective_status': 'ACTIVE', 'operation_states': [
            {'operation_id': r['operation_id'], 'decision_sha': sha(r),
             'status': 'active' if r['disposition'] == 'SUPPORTED_WITH_CONSTRAINTS' else 'hold'}
            for r in decisions], 'public_render_ready': False}
    state['status_sha'] = sha(state)
    return review, state


def bounded_plan(review):
    """Exact operation transport; a caller cannot add operations via a pass flag."""
    return {'contract': CONTRACT, 'review_sha': review['review_sha'],
        'operations': [{'operation_id': row['operation_id'], 'decision_sha': sha(row),
            'selection': deepcopy(row['selection']), 'execution': deepcopy(row['execution'])}
            for row in review['decisions']], 'public_render_ready': False}
