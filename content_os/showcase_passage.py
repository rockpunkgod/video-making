"""Narrow adapter for the existing reviewed-passage transport, not a solver."""
from video_contracts import sha, validate, verify_seal
from video_contracts.passage import verify_bundle


def context(package, statuses):
    validate('showcase-passage-source', package)
    if package['kind'] != 'free_showcase_passage/v1':
        raise ValueError('Unknown frozen source adapter')
    bundle = package['bundle']; verify_bundle(bundle)
    available = bundle['asset_id'] in statuses
    current = False
    source_current = False
    if available:
        status = statuses[bundle['asset_id']]; verify_seal(status)
        current = (status.get('kind') == 'reviewed_passage_status' and status['asset_id'] == bundle['asset_id']
                   and status['semantic_binding_sha'] == bundle['semantic_binding_sha']
                   and status['effective_status'] == 'ACTIVE')
        source_current = status['source_sha'] == sha(bundle['payload']['source'])
    payload = bundle['payload']; qid = package['question_id']
    if qid not in {q['question_id'] for q in payload['questions']}:
        raise ValueError('Unknown frozen question')
    segments = [s for s in payload['review']['segments'] if s['segment_id'] in package['segment_ids']]
    actions = [a for a in payload['review']['method_actions'] if a['action_id'] in package['action_ids']]
    if (len(segments) != len(package['segment_ids']) or not segments
        or len(actions) != len(package['action_ids']) or not actions
        or any(s['question_id'] != qid for s in segments + actions)):
        raise ValueError('Missing, duplicate or cross-question selected source')
    answer = any(s['kind'] == 'closure' and any(
        payload['review']['decisions'][i]['effect'] == 'retain' for i in s['decision_refs']) for s in segments)
    return {'sources': [bundle], 'current': current, 'available': available, 'source_current': source_current,
        'scope': 'full_solution' if answer else 'method_action_demo',
        'claims': set(package['segment_ids']) | set(package['action_ids']),
        'required': set(package['action_ids']), 'engineering': True,
        'outputs': [{'kind': 'interpretation'}] + ([{'kind': 'candidate_decision', 'effect': 'retain'}] if answer else []),
        'teaching_stale': False}
