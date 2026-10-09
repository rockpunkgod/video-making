"""Frame timing only; callers must supply upstream-bound locating expressions.

No passage parsing, POS tagging, synonym judgement, candidate exclusion or
teaching review is performed here. This plan alone cannot authorize rendering.
"""
from video_contracts import sha

VERSION = '0.1.1'
DEFAULT = {'transfer': 4, 'activation': 5, 'recognition': 7, 'retirement': 3}
LIMITS = {'transfer': (3, 240), 'activation': (4, 6),
          'recognition': (6, 9), 'retirement': (2, 3)}


class RecognitionTimingOverflow(ValueError):
    def __init__(self, required, available):
        self.required_frames = required
        self.available_frames = available
        self.additional_frames = required - available
        super().__init__(f'Recognition needs {required} frames, has {available}; '
                         'retime explicitly, never drop candidates or recognition holds')


def schedule(candidate_ids, acquired_id, frame_range, policy=None, event_policies=None):
    """Schedule supplied IDs without choosing words or assigning correspondence.

The caller supplies an already bound sequence, optionally ending at its acquired ID.
None retains an unresolved result, including an empty eligible sequence.
Frame ranges are half-open at 24 fps. The acquired expression remains active;
retirement is attention departure, never an excluded option or sentence.
"""
    if not isinstance(candidate_ids, (list, tuple)) or not isinstance(frame_range, (list, tuple)):
        raise ValueError('Explicit candidate sequence and frame pair required')
    ids = list(candidate_ids)
    if (any(not isinstance(i, str) or not i.strip() for i in ids)
            or len(set(ids)) != len(ids) or (acquired_id is not None and (not ids or acquired_id != ids[-1]))):
        raise ValueError('Explicit unique ordered IDs ending at supplied acquired ID required')
    if (len(frame_range) != 2 or any(type(i) is not int for i in frame_range)
            or not 0 <= frame_range[0] < frame_range[1]):
        raise ValueError('Positive explicit integer frame window required')
    policy = dict(DEFAULT if policy is None else policy)
    if event_policies is not None and (not isinstance(event_policies, dict)
            or set(event_policies) != set(ids)):
        raise ValueError('Per-expression timing must bind every explicit candidate ID')
    policies = {identity: dict(policy if event_policies is None else event_policies[identity])
                for identity in ids}
    for candidate_policy in policies.values():
        if set(candidate_policy) != set(LIMITS) or any(type(candidate_policy[k]) is not int or
                not lo <= candidate_policy[k] <= hi for k, (lo, hi) in LIMITS.items()):
            raise ValueError('Use bounded recognition timing; no hidden speed compression')
    for previous, current in zip(ids, ids[1:]):
        if policies[current]['transfer'] < policies[previous]['retirement']:
            raise ValueError('Previous highlight must retire before next activation')
    needed = sum(p['transfer']+p['activation']+p['recognition'] for p in policies.values())
    if ids and acquired_id is None: needed += policies[ids[-1]]['retirement']
    available = frame_range[1] - frame_range[0]
    if needed > available:
        raise RecognitionTimingOverflow(needed, available)
    cursor = frame_range[1] - needed
    unallocated = [frame_range[0], cursor]
    events = []
    for identity in ids:
        candidate_policy = policies[identity]
        event = {'candidate_id': identity}
        for stage in ('transfer', 'activation', 'recognition'):
            event[stage] = [cursor, cursor + candidate_policy[stage]]
            cursor += candidate_policy[stage]
        if identity != acquired_id:
            event['retirement'] = [cursor, cursor+candidate_policy['retirement']]
        events.append(event)
    plan = {'kind': 'locating_expression_recognition_timing', 'version': VERSION,
            'fps': 24, 'ranking': 'caller_supplied_order', 'event_policies': policies,
            'candidate_rhythm_source': 'editor_supplied_per_expression' if event_policies is not None else 'uniform_trial_only',
            'frame_range': list(frame_range), 'events': events,
            'acquired_id': acquired_id, 'required_frames': needed,
            'remaining_frames': available - needed, 'unallocated_window': unallocated,
            'requires_director_timing_alignment': unallocated[0] != unallocated[1],
            'anchor': 'supplied_final_recognition_end' if acquired_id is not None else 'unresolved_scan_end',
            'outcome': 'acquired' if acquired_id is not None else 'unresolved',
            'transfer_geometry_verified': False,
            'authority': 'timing_only_not_POS_or_correspondence_certification',
            'requires_bound_upstream_inputs': True, 'render_ready': False,
            'candidate_verdict': None, 'public_render_ready': False}
    return {**plan, 'plan_sha': sha(plan)}
