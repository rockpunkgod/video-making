"""Fail-closed G2 consumer for explicit current phrase-operation reviews."""
from content_os.phrase_review import (
    CONTRACT, bounded_plan, request_bindings, validate_decision)
from video_contracts import sha


def consume_phrase_review(request, review, state, bundles, statuses, plan):
    binding = request_bindings(request, bundles, statuses)
    if (review.get('contract') != CONTRACT or review.get('kind') != 'frozen_host_phrase_review'
            or review.get('review_sha') != sha({k: v for k, v in review.items() if k != 'review_sha'})
            or review.get('binding') != binding or review.get('level') != 'ai_reviewed'
            or review.get('reviewer_kind') != 'ai_host' or not review.get('reviewer')
            or review.get('independent_human_certified') is not False
            or review.get('scope') != 'PRIVATE_BOUNDED_G2_ONLY'
            or review.get('public_render_ready') is not False):
        raise ValueError('Frozen phrase review or exact current source binding changed')
    if (state.get('contract') != CONTRACT or state.get('kind') != 'phrase_review_current_status'
            or state.get('status_sha') != sha({k: v for k, v in state.items() if k != 'status_sha'})
            or state.get('review_sha') != review['review_sha']
            or state.get('revision_id') != review['revision_id']
            or state.get('request_content_sha') != sha(request)
            or state.get('upstream_status_sha') != binding['upstream_status_sha']
            or state.get('public_render_ready') is not False):
        raise ValueError('Current phrase-review status does not bind this revision')
    rows = {r['operation_id']: r for r in request['operations']}
    decisions = review['decisions']
    if len({r['operation_id'] for r in decisions}) != len(decisions):
        raise ValueError('Duplicate reviewed operations')
    for row in decisions:
        if row['operation_id'] not in rows:
            raise ValueError('Review contains an unrequested operation')
        validate_decision(row, rows[row['operation_id']], bundles)
        if row['execution']['relation_ref'] != request['relation_ref']:
            raise ValueError('Renderer relation changed')
    if plan != bounded_plan(review):
        raise ValueError('Renderer plan differs from exact reviewed operations')
    status_rows = state['operation_states']
    if (len({r['operation_id'] for r in status_rows}) != len(status_rows)
            or set(r['operation_id'] for r in status_rows) != set(r['operation_id'] for r in decisions)):
        raise ValueError('Current operation status coverage differs')
    states = {r['operation_id']: r for r in status_rows}
    reasons = []
    if state['effective_status'] != 'ACTIVE':
        reasons.append('review_not_active')
    if set(r['operation_id'] for r in decisions) != set(rows):
        reasons.append('incomplete_review_coverage')
    for row in decisions:
        current = states[row['operation_id']]
        if current['decision_sha'] != sha(row):
            raise ValueError('An operation state refers to another decision')
        if row['disposition'] != 'SUPPORTED_WITH_CONSTRAINTS' or current['status'] != 'active':
            reasons.append(row['operation_id'] + ':not_supported_or_active')
    result = {'kind': 'bounded_g2_phrase_consumption', 'contract': CONTRACT,
        'request_content_sha': sha(request), 'review_sha': review['review_sha'],
        'review_status_sha': state['status_sha'], 'plan_sha': sha(plan),
        'binding': binding, 'accepted_operation_ids': [] if reasons else list(rows),
        'gate': 'HOLD' if reasons else 'READY_FOR_BOUNDED_G2', 'reasons': reasons,
        'semantic_review_level': 'ai_reviewed', 'independent_human_certified': False,
        'human_visual_review': 'PENDING', 'public_render_ready': False}
    result['receipt_sha'] = sha(result)
    return result
