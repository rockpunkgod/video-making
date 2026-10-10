"""Editorial product context, outside frozen truth and voice-delivery/v1."""
from copy import deepcopy
from video_contracts import sha

STAGES = ('selection', 'copy', 'director', 'motion', 'voice', 'premiere', 'human_review')
HARD_GATES = ('Truth', 'Source Rights', 'No Fabricated Claims', 'No Unsupported Final Answer')
PROFILES = {
    'FREE_SHOWCASE': {'priority': 'Experience First', 'lead': 'Creative Director',
        'rubric': ('Hook', 'Engagement', 'Narrative', 'Cognitive Payoff', 'Visual Impact',
                   'Voice Performance', 'Memorability', 'Shareability')},
    'PAID_MASTERY': {'priority': 'Rigour First', 'lead': 'Pedagogy / Teaching Review',
        'rubric': ('Teaching Accuracy', 'Evidence', 'Applicability', 'Boundary',
                   'Action Executability', 'Method Integration', 'Practice', 'Transfer')},
}


def editorial_handoffs(content_profile, artifacts):
    """Bind product intent through existing stages; never approve their output.

    None marks an unproduced artifact. Passing a frozen artifact hashes it;
    this does not mutate its payload or its stable consumer contract.
    """
    if content_profile not in PROFILES or set(artifacts) != set(STAGES):
        raise ValueError('Explicit product and all seven editorial stages required')
    profile = deepcopy(PROFILES[content_profile])
    result = {'content_profile': content_profile, 'priority': profile['priority'],
        'organization_lead': profile['lead'], 'quality_rubric': list(profile['rubric']),
        'hard_gates': list(HARD_GATES), 'quality_review': 'PENDING',
        'propagation_results': 'UNKNOWN', 'public_render_ready': False,
        'handoffs': [{'stage': s, 'content_profile': content_profile,
                     'artifact_sha': sha(artifacts[s]) if artifacts[s] is not None else None,
                     'state': 'CANDIDATE' if artifacts[s] is not None else 'NOT_PRODUCED'}
                    for s in STAGES]}
    result['context_sha'] = sha(result)
    return result
