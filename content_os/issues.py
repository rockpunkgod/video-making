"""Prepare upstream review requests without creating or changing teaching facts."""
from video_contracts import sha


def teaching_issue_candidate(artifact_id, reason, refs):
    if not artifact_id or not reason.strip() or not refs:
        raise ValueError('Issue requires artifact identity, reason and bound references')
    result = {'type': 'teaching_issue_candidate', 'status': 'pending_answer_review',
              'artifact_id': artifact_id, 'reason': reason, 'refs': refs,
              'teaching_changes_applied': False}
    result['issue_id'] = 'issue:' + sha(result)
    return result
