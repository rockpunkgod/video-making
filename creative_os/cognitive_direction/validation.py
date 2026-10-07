"""History is inspectable; every current direction/handoff revalidates its sources."""
from copy import deepcopy

from jsonschema import ValidationError
from video_contracts import _validator, sha, seal, verify_seal
from .policy import VERSION, SCHEMA, PROJECTION_SCHEMA, DIRECTORY, semantic_payload


def schema_check(value):
    path = DIRECTORY / 'cognitive-direction.v0.2.json'
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(value)
    except ValidationError as error:
        def leaves(item):
            if not item.context: return [item]
            return [leaf for child in item.context for leaf in leaves(child)]
        specific = max(leaves(error), key=lambda e: len(e.absolute_path))
        location = '/'.join(map(str, specific.absolute_path)) or '<root>'
        raise ValueError('Invalid Cognitive Direction schema at ' + location + ': '
                         + specific.message[:240]) from error


def inspect_direction(value):
    schema_check(value); verify_seal(value)
    if (value['schema'] != SCHEMA or value['direction_sha'] != sha(semantic_payload(value))
            or value['direction_id'] != 'direction:' + value['direction_sha']):
        raise ValueError('Direction semantic hash mismatch')
    return {'status': 'HISTORICAL_ONLY', 'contract_version': VERSION,
            'current_upstream_verified': False, 'consumption_allowed': False,
            'execution_allowed': False, 'public_render_ready': False}


def validate_direction(value, choreography, experience, plan, copy_handoff, motion_handoff,
                       bundle, status, *, application=None):
    from .compiler import compile_direction
    inspect_direction(value)
    if value['source']['kind'] == 'synthetic_contract_test':
        raise ValueError('Synthetic directions require their exact synthetic fixture')
    expected = compile_direction(choreography, experience, plan, copy_handoff, motion_handoff,
                                 bundle, status, application=application,
                                 diagnostic=value['replay_request']['diagnostic'])
    if expected != value:
        raise ValueError('Direction differs from current Choreography, Experience, Copy or source state')
    return {'status': 'PASS', 'current_upstream_verified': True,
            'consumption_allowed': value['availability']['status'] == 'READY' and value['source']['production_eligible'],
            'execution_allowed': False, 'public_render_ready': False}


def validate_synthetic_direction(value, choreography, fixture):
    from .compiler import compile_synthetic_direction
    inspect_direction(value)
    expected = compile_synthetic_direction(choreography, fixture,
        restore=value['replay_request']['synthetic_restore'],
        test_window_seconds=value['timing_context']['duration_seconds'])
    if expected != value:
        raise ValueError('Synthetic direction or supplied span lineage changed')
    return {'status': 'PASS', 'current_upstream_verified': False,
            'consumption_allowed': False, 'execution_allowed': False, 'public_render_ready': False}


def _projection(value, gate, diagnostic):
    result = {
        'schema': PROJECTION_SCHEMA, 'schema_version': VERSION, 'kind': 'cognitive_direction_projection',
        'direction_id': value['direction_id'], 'direction_sha': value['direction_sha'],
        'binding': deepcopy(value['binding']), 'direction_plan': deepcopy(value),
        'diagnostic_only': diagnostic,
        'consumption_allowed': gate['consumption_allowed'] and not diagnostic,
        'execution_allowed': False, 'public_render_ready': False,
        'human_direction_review': deepcopy(value['human_direction_review']),
        'generated_at': value['generated_at'],
    }
    result['projection_sha'] = sha({k: v for k, v in result.items() if k != 'generated_at'} | {
        'direction_plan': semantic_payload(value) | {
            'direction_id': value['direction_id'], 'direction_sha': value['direction_sha'],
        },
    })
    result = seal(result); schema_check(result)
    return result


def project_direction(value, choreography, experience, plan, copy_handoff, motion_handoff,
                      bundle, status, *, application=None, diagnostic=False):
    if type(diagnostic) is not bool:
        raise ValueError('Explicit diagnostic projection required')
    gate = validate_direction(value, choreography, experience, plan, copy_handoff, motion_handoff,
                              bundle, status, application=application)
    if not gate['consumption_allowed'] and not diagnostic:
        raise ValueError('HOLD cannot enter production planning; explicit diagnostic projection required')
    return _projection(value, gate, diagnostic)


def project_synthetic_direction(value, choreography, fixture):
    return _projection(value, validate_synthetic_direction(value, choreography, fixture), True)


def validate_projection(projection, value, choreography, *sources, application=None, fixture=None):
    if fixture is not None:
        if sources or application is not None:
            raise ValueError('Synthetic and real source lanes cannot be mixed')
        expected = project_synthetic_direction(value, choreography, fixture)
    else:
        expected = project_direction(value, choreography, *sources, application=application,
                                     diagnostic=projection['diagnostic_only'])
    if projection != expected:
        raise ValueError('Direction projection or current binding changed')
    return {'status': 'PASS', 'consumption_allowed': projection['consumption_allowed'],
            'execution_allowed': False, 'public_render_ready': False}
