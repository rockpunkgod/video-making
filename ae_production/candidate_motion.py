"""Mechanical readback of authored candidate events; no teaching adjudication."""
import math
from video_contracts import pointer, sha


def audit_candidate_events(events, bundles, answers=()):
    states = {key: set(b['source_snapshot']['options']) for key, b in bundles.items()}
    checked, used, last = [], set(), {}
    for event in events:
        refs = event['source_refs']
        if not refs or len({r['asset_id'] for r in refs}) != 1:
            raise ValueError('Candidate event needs its own frozen source')
        asset = refs[0]['asset_id']; bundle = bundles[asset]
        if event['question_id'] != bundle['source_snapshot']['question_id']:
            raise ValueError('Candidate event borrowed another question')
        values = []
        for ref in refs:
            value = pointer(bundle, ref['pointer'])
            if sha(value) != ref['sha']:
                raise ValueError('Candidate event reference changed')
            values.append(value)
        actions = [v for v in values if isinstance(v, dict) and 'execution_id' in v and 'output' in v]
        if len(actions) != 1:
            raise ValueError('Candidate event needs exactly one actual action')
        action = actions[0]; key = (asset, action['execution_id'])
        if key in used:
            raise ValueError('Candidate action replay cannot count as another decision')
        output = action['output']
        if (output.get('kind') != 'candidate_decision'
                or output.get('candidate') != event['candidate']
                or output.get('effect') != event['effect']):
            raise ValueError('Animation cannot change the frozen action output')
        times = [event[k] for k in ('compare_start', 'decision_start', 'decision_end', 'confirmation_start')]
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
                or not 0 <= times[0] < times[1] < times[2] <= times[3]
                or times[0] < last.get(asset, 0)):
            raise ValueError('Observe, decide, then confirm; events must not overlap')
        candidate = event['candidate']
        if candidate not in states[asset] or event['effect'] not in ('eliminate', 'retain'):
            raise ValueError('Candidate is not in the current working set')
        before = sorted(states[asset])
        if event['effect'] == 'eliminate': states[asset].remove(candidate)
        used.add(key); last[asset] = times[2]
        checked.append({'scene_id': event['scene_id'], 'action_id': action['execution_id'],
                        'before': before, 'after': sorted(states[asset])})
    for answer in answers:
        ref = answer['source_ref']; asset = ref['asset_id']; bundle = bundles[asset]
        verification = bundle['analysis']['answer_verification']
        required = {(asset, a['execution_id']) for a in bundle['source_snapshot']['action_executions']
                    if a.get('output', {}).get('kind') == 'candidate_decision'}
        if (ref['pointer'] != '/analysis/answer' or sha(pointer(bundle, ref['pointer'])) != ref['sha']
                or not all(verification.get(k) for k in ('closed', 'candidate_coverage_complete', 'unique_supported_candidate'))
                or pointer(bundle, ref['pointer']) != answer['candidate']
                or states[asset] != {answer['candidate']}
                or not required.issubset(used)
                or type(answer['time']) not in (int,float) or not math.isfinite(answer['time'])
                or answer['time'] < last.get(asset, 0)):
            raise ValueError('Final answer requires current completed frozen closure')
    return {'status': 'PASS', 'events': checked,
            'scope': 'mechanical_action_and_timing_projection_not_semantic_or_viewing_certification',
            'public_render_ready': False}
