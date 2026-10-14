"""Reject even resealed edits by replaying the projection from frozen inputs."""
from video_contracts import ROOT, _validator, sha, verify_seal
from .compiler import VERSION, CURRENT_VERSION, compile_plan, plan_semantics


def _schema(plan):
    from jsonschema import ValidationError
    path = ROOT / 'schemas' / 'pedagogy-plan.json'
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(plan)
    except ValidationError as error:
        raise ValueError('Invalid PedagogyPlan schema: ' + error.message) from error


def inspect_historical(plan):
    _schema(plan)
    verify_seal(plan)
    if plan['plan_sha'] != sha(plan_semantics(plan)) or plan['plan_id'] != 'pedagogy:' + plan['plan_sha']:
        raise ValueError('Pedagogy semantic hash mismatch')
    from .boundary_review import VERSION as delivery_version
    current = plan['schema_version'] == CURRENT_VERSION and plan.get('boundary_delivery', {}).get(
        'contract_version', delivery_version) == delivery_version
    compatible = plan['schema_version'] == VERSION and plan.get('boundary_delivery', {}).get(
        'contract_version', delivery_version) == delivery_version
    return {'status': 'HISTORICAL_ONLY', 'current_upstream_verified': False,
            'contract_status': 'CURRENT_CONTRACT' if current else 'COMPATIBILITY_CONTRACT' if compatible else 'LEGACY_CONTRACT',
            'contract_version': plan['schema_version'], 'current_contract_version': CURRENT_VERSION,
            'consumption_allowed': False, 'public_render_ready': False}


def validate_plan(plan, bundle, status, *, required_version=None):
    inspect_historical(plan)
    version = plan['schema_version']
    if version not in (VERSION, CURRENT_VERSION) or required_version is not None and version != required_version:
        raise ValueError('Historical Pedagogy contract ' + plan['schema_version']
            + ' cannot be consumed by ' + (required_version or CURRENT_VERSION)
            + '; recompile from frozen inputs and current status')
    from .boundary_review import VERSION as delivery_version
    if plan.get('boundary_delivery', {}).get('contract_version', delivery_version) != delivery_version:
        raise ValueError('Historical boundary delivery cannot be consumed; regenerate from frozen inputs and review')
    request = plan['replay_request']
    expected = compile_plan(bundle, status, request['selection'], mode=plan['mode'],
        audience=plan['audience'], channel=plan['channel'], duration_target=plan['duration_target'],
        fields=request['fields'], extra_boundary_refs=request['extra_boundary_refs'],
        generated_at=plan['generated_at'], boundary_review=request.get('boundary_review'),
        contract_version=version, structure_input=request.get('structure_input'),
        answer_scope=request.get('answer_scope', 'method_action_demo'))
    if expected != plan:
        raise ValueError('PedagogyPlan differs from the frozen source projection or current bindings')
    return {'status': 'PASS', 'current_upstream_verified': True,
            'consumption_allowed': plan['availability']['status'] == 'READY',
            'public_render_ready': False}
