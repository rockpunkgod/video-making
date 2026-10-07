"""Replay Copy realization against the approved Plan and current upstream."""
from video_contracts import ROOT, _validator, sha, verify_seal
from .realization import realize, copy_semantics


def validate_copy(copy, projection, plan, bundle, status):
    from jsonschema import ValidationError
    path = ROOT / 'creative' / 'copy-system' / 'student-pov-copy.schema.json'
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(copy)
    except ValidationError as error:
        raise ValueError('Invalid Student POV Copy schema: ' + error.message) from error
    verify_seal(copy)
    if copy['copy_sha'] != sha(copy_semantics(copy)) or copy['copy_id'] != 'student-pov:' + copy['copy_sha']:
        raise ValueError('Student POV copy binding mismatch')
    expected = realize(projection, plan, bundle, status, **copy['realization_request'])
    if expected != copy:
        raise ValueError('Copy realization changed Pedagogy, Evidence, payoff or required boundaries')
    return {'status': 'PASS', 'consumption_allowed': copy['availability']['status'] == 'READY',
            'public_render_ready': False}
