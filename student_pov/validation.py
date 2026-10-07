"""Replay Copy realization against the approved Plan and current upstream."""
from video_contracts import ROOT, _validator, sha, verify_seal
from .realization import VERSION, realize, copy_semantics


def inspect_historical(copy):
    """Check saved copy integrity without granting current consumption."""
    from jsonschema import ValidationError
    version = copy.get('schema_version')
    if version == '0.4.0':
        from .experience import inspect_experience
        return inspect_experience(copy)
    if version not in ('0.1.0', '0.2.0', VERSION):
        raise ValueError('Unsupported Student POV Copy contract version')
    name = 'student-pov-copy.v' + version[:3] + '.schema.json' if version != VERSION else 'student-pov-copy.schema.json'
    path = ROOT / 'creative' / 'copy-system' / name
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(copy)
    except ValidationError as error:
        raise ValueError('Invalid Student POV Copy schema: ' + error.message) from error
    verify_seal(copy)
    if copy['copy_sha'] != sha(copy_semantics(copy)) or copy['copy_id'] != 'student-pov:' + copy['copy_sha']:
        raise ValueError('Student POV copy binding mismatch')
    final_payload = {'script': copy['script'], 'final_script': copy['final_script']}
    if version == VERSION:
        final_payload['reality_layer'] = copy['reality_layer']
    if copy['script_sha'] != sha(copy['final_script']) or copy['final_copy_sha'] != sha(final_payload):
        raise ValueError('Student POV final copy lock mismatch')
    return {'status': 'HISTORICAL_ONLY', 'current_upstream_verified': False,
            'contract_status': 'CURRENT_CONTRACT' if version == VERSION else 'LEGACY_CONTRACT',
            'contract_version': version, 'current_contract_version': VERSION,
            'consumption_allowed': False, 'public_render_ready': False}


def validate_copy(copy, projection, plan, bundle, status, *, motion_projection=None, required_version=None):
    inspect_historical(copy)
    if required_version is not None and copy['schema_version'] != required_version:
        raise ValueError('Student POV contract mismatch; regenerate from current Pedagogy')
    if copy['schema_version'] == '0.4.0':
        from .experience import validate_experience
        return validate_experience(copy, projection, motion_projection, plan, bundle, status)
    if motion_projection is not None:
        raise ValueError('Historical Copy 0.3 cannot consume a v0.4 Motion Handoff')
    if copy['schema_version'] != VERSION:
        raise ValueError('Historical Student POV Copy contract ' + copy['schema_version']
            + ' cannot be consumed by ' + VERSION + '; regenerate from current Pedagogy and frozen inputs')
    expected = realize(projection, plan, bundle, status, **copy['realization_request'])
    if expected != copy:
        raise ValueError('Copy realization changed Pedagogy, Evidence, payoff or required boundaries')
    return {'status': 'PASS', 'current_upstream_verified': True,
            'consumption_allowed': copy['availability']['status'] == 'READY',
            'public_render_ready': False}
