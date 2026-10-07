"""History integrity, fresh source revalidation and a non-rendering handoff."""
from copy import deepcopy

from video_contracts import ROOT, _validator, sha, seal, verify_seal
from student_pov import inspect_historical, validate_copy
from .registry import VERSION
from .compiler import compile_choreography, choreography_semantics
from .audit import audit_choreography


def inspect_choreography(value):
    from jsonschema import ValidationError
    path=ROOT/'creative/method-choreography/method-choreography.schema.json'
    try:_validator(str(path),path.stat().st_mtime_ns).validate(value)
    except ValidationError as error:raise ValueError('Invalid Choreography schema: '+error.message) from error
    verify_seal(value)
    if (value['choreography_sha']!=sha(choreography_semantics(value))
            or value['choreography_id']!='choreography:'+value['choreography_sha']):
        raise ValueError('Choreography semantic hash mismatch')
    audit,risks,errors=audit_choreography(value)
    if audit!=value['audit'] or risks!=value['risks'] or errors!=value['availability']['issues']:
        raise ValueError('Choreography state audit changed')
    return {'status':'HISTORICAL_ONLY','contract_version':VERSION,
        'current_upstream_verified':False,'consumption_allowed':False,'public_render_ready':False}


def validate_choreography(value,experience,plan,copy_handoff,motion_handoff,bundle,status,*,application=None):
    inspect_choreography(value)
    expected=compile_choreography(experience,plan,copy_handoff,motion_handoff,bundle,status,
        application=application,**value['replay_request'])
    if expected!=value:raise ValueError('Choreography differs from current teaching, experience, objects or state sequence')
    return {'status':'PASS','current_upstream_verified':True,
        'consumption_allowed':value['availability']['status']=='READY' and value['source']['production_eligible'],
        'public_render_ready':False}


def project_choreography(value,experience,plan,copy_handoff,motion_handoff,bundle,status,*,application=None,diagnostic=False):
    if type(diagnostic) is not bool:raise ValueError('Explicit diagnostic projection required')
    gate=validate_choreography(value,experience,plan,copy_handoff,motion_handoff,bundle,status,application=application)
    if not gate['consumption_allowed'] and not diagnostic:
        raise ValueError('HOLD cannot enter Creative production; diagnostic projection must be explicit')
    keys=('binding','experience_kind','signature','object_catalog','relation_catalog','states','operations',
        'state_transitions','object_lineage','attention_entry','collapse','resolution','payoff_event','stop',
        'memory_closure','temporal_signature','risks','availability','release_state')
    result={k:deepcopy(value[k]) for k in keys}
    result.update(schema='choreography-projection/v1',schema_version=VERSION,kind='choreography_projection',
        choreography_id=value['choreography_id'],choreography_sha=value['choreography_sha'],
        consumption_allowed=gate['consumption_allowed'] and not diagnostic,
        diagnostic_only=diagnostic, human_taste_review='PENDING',public_render_ready=False,
        generated_at=value['generated_at'])
    result['projection_sha']=sha({k:v for k,v in result.items() if k!='generated_at'})
    result=seal(result)
    path=ROOT/'creative/method-choreography/choreography-projection.schema.json'
    _validator(str(path),path.stat().st_mtime_ns).validate(result)
    return result


def validate_projection(projection,value,experience,plan,copy_handoff,motion_handoff,bundle,status,*,application=None):
    expected=project_choreography(value,experience,plan,copy_handoff,motion_handoff,bundle,status,
        application=application,diagnostic=projection['diagnostic_only'])
    if projection!=expected:raise ValueError('Creative handoff objects or current bindings changed')
    return {'status':'PASS','consumption_allowed':projection['consumption_allowed'],'public_render_ready':False}


def analyze_legacy(copy,plan,projection,bundle,status):
    """Read a real old Copy without fabricating an Experience or Work Delta."""
    integrity=inspect_historical(copy)
    if copy['schema_version']!='0.3.0' or plan['schema_version']!='0.3.0':
        raise ValueError('Legacy adapter only analyzes the existing 0.3 lane')
    current=validate_copy(copy,projection,plan,bundle,status)
    return {'kind':'legacy_choreography_analysis','status':'V04_INPUT_REQUIRED',
        'historical_integrity':integrity,'legacy_current_validation':current,
        'legacy_availability':deepcopy(copy['availability']),'copy_sha':copy['copy_sha'],
        'source_contract':'0.3.0','required_contract':'0.4.0','new_experience_created':False,
        'new_work_delta_created':False,'choreography_production_allowed':False,
        'approval_inherited':False,'public_render_ready':False}
