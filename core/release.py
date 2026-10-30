"""Read-only checks for an explicitly approved human release; never promote cards."""
import hashlib
import json
from pathlib import Path
from .registry import ROOT,CASE_TYPES,PRIMARY_OUTPUTS,validate_schema

CHECKS=('course_provenance','compact_full_consistency','role_correctness','case_legality','case_semantics','practicality','first_use','regression','stable_transfer','statistical_significance','visual_memory_speech','short_version_safety')
COMMON=CHECKS[:8]
STATE_FIELDS={'status','maturity_status','practical_value','usefulness_level'}

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def material_path(path):
    candidate=Path(path)
    resolved=(ROOT/candidate).resolve()
    if candidate.is_absolute() or not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
        raise ValueError('Release material must be an existing repository-relative file: '+path)
    return resolved

def read_json(path): return json.loads(material_path(path).read_text(encoding='utf-8-sig'))

def method_facts(method): return {k:v for k,v in method.items() if k not in STATE_FIELDS}

def regression_snapshot(registry):
    runtime={}
    for folder,pattern in [('core','*.py'),('answer_engine','*.py'),('renderers','*.py'),('video_contracts','*.py'),('evaluation','*.py'),('scripts','*.py'),('tests','*.py'),('schemas','*.json'),('video/schemas','*.json')]:
        for path in sorted((ROOT/folder).rglob(pattern)):
            runtime[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    runtime['EVALUATION_PROTOCOL.md']=hashlib.sha256((ROOT/'EVALUATION_PROTOCOL.md').read_bytes()).hexdigest()
    return {'runtime_files':runtime,'semantic_registry_sha256':digest({'methods':{mid:method_facts(m) for mid,m in registry.methods.items()},'sources':registry.sources,'risks':registry.risks,'symptoms':registry.symptom_cues,'grammar_tree':registry.grammar_tree}),
            'cases_sha256':digest(registry.case_inventory())}

def release_bindings(registry,mid,inputs):
    from evaluation.harness import load_records
    method=registry.methods[mid]; inventory=registry.case_inventory()
    return {'method_sha256':digest(method_facts(method)),
            'cases_sha256':digest({kind:inventory[path] for kind,path in method['cases'].items()}),
            'records_sha256':digest(load_records(material_path(inputs['records']))),
            'plan_sha256':digest(read_json(inputs['plan'])),
            'regression_sha256':digest(read_json(inputs['regression']))}

def check_release(registry,review,applied=False,visited=None):
    from evaluation.harness import evaluate,load_records,timestamp
    validate_schema('method-release',review)
    mid=review['method_id']; method=registry.methods.get(mid)
    if method is None: raise ValueError('Unknown release method: '+mid)
    records=load_records(material_path(review['inputs']['records']))
    plan=read_json(review['inputs']['plan']); regression=read_json(review['inputs']['regression'])
    relevant=[x for x in records if x['method_id']==mid and x['method_version']==review['method_version'] and x['dataset_id']==plan.get('dataset_id') and x['communication_freeze_id']==plan.get('communication_freeze_id')]
    checks={'approved_by_named_reviewer':review['approved'] is True and bool((review['reviewer'] or '').strip()) and bool(review['evidence_refs']) and bool(review['notes'].strip()),
            'current_method_version':review['method_version']==method['version'],
            'primary_role_output_match':method['output_type'] in PRIMARY_OUTPUTS[method['primary_role']],
            'material_bindings_match':review['bindings']==release_bindings(registry,mid,review['inputs']),
            'human_common_checks':all(review['checks'][key] is True for key in COMMON)}
    if applied: checks['applied_state_matches_approval']=method['maturity_status']==review['target_maturity'] and method['practical_value']==review['target_practical_value']
    inventory=registry.case_inventory()
    checks['five_verified_case_slots']=set(method['cases'])==set(CASE_TYPES) and all(
        inventory[path]['status']=='verified_course_example' and bool(inventory[path]['question'])
        and registry.case_is_current(inventory[path]) for path in method['cases'].values())
    stats=regression.get('after_refactor',{})
    checks['regression_matches_current_material']=all(regression.get(key)==value for key,value in regression_snapshot(registry).items())
    checks['regression_passed']=all(type(stats.get(key)) is int for key in ('tests_run','failures','errors')) and stats.get('tests_run',0)>=16 and stats.get('failures')==0 and stats.get('errors')==0 and stats.get('registry',{}).get('status')=='PASS' and stats.get('generated',{}).get('generated_assets')=='PASS' and regression.get('source_commit')==registry.index['source_baseline']['commit']
    # New runner records include CLI failures and run stability. Preserve old
    # report reading, but never let a declared failed current run grant release.
    if 'engineering_status' in regression:
        checks['regression_passed'] = (checks['regression_passed']
            and regression['engineering_status'] == 'PASS'
            and stats.get('material_stable') is True
            and type(stats.get('cli_failures')) is int and stats['cli_failures'] == 0
            and type(stats.get('cli_commands_run')) is int and stats['cli_commands_run'] > 0)
    evaluation_error=None; group=None
    try:
        result=evaluate(records,plan)
        matches=[g for g in result['groups'] if g['method_id']==mid and g['method_version']==review['method_version'] and g['dataset_id']==plan['dataset_id'] and g['communication_freeze_id']==plan['communication_freeze_id']]
        group=matches[0] if len(matches)==1 else None
        checks['real_evaluation_release_gate']=result['origin']=='real' and group is not None and group['release_eligible'] is True
    except (ValueError,KeyError) as exc:
        evaluation_error=str(exc); checks['real_evaluation_release_gate']=False
    try:
        reviewed=timestamp(review['reviewed_at'])
        checks['approval_after_observations']=bool(relevant) and all('observed_at' in x and reviewed>=timestamp(x['observed_at']) for x in relevant)
    except ValueError: checks['approval_after_observations']=False
    grade=review['target_practical_value']
    if grade in {'Efficient','Signature'}:
        checks['efficiency_review']=bool(group and group['upgrade_eligible'] in {'review_for_Efficient','review_for_Signature'} and review['checks']['statistical_significance'])
    if grade=='Signature':
        checks['signature_review']=bool(group and group['upgrade_eligible']=='review_for_Signature' and method['method_type'] in {'method','framework'} and method['visual_formula'] and review['checks']['visual_memory_speech'] and review['checks']['short_version_safety'])
    if review['target_maturity']=='stable':
        checks['stable_transfer_review']=review['checks']['stable_transfer'] is True and len({x['question_id'] for x in relevant if x['phase']=='blind' and x['case_type']=='transfer'})>=2
        previous=review['validated_review']; visited=set(visited or [])
        checks['prior_validated_approval']=False
        if previous:
            path=material_path(previous).as_posix()
            if path in visited: raise ValueError('Circular validated release reference')
            prior=read_json(previous)
            if prior.get('target_maturity')=='validated' and prior.get('method_id')==mid and prior.get('method_version')==review['method_version']:
                audit=check_release(registry,prior,visited=visited|{path})
                checks['prior_validated_approval']=audit['ready_for_manual_release'] and timestamp(prior['reviewed_at'])<timestamp(review['reviewed_at'])
    return {'method_id':mid,'method_version':review['method_version'],'target_maturity':review['target_maturity'],'target_practical_value':grade,'ready_for_manual_release':all(checks.values()),'checks':checks,'blocking_reasons':[key for key,value in checks.items() if not value],'evaluation_error':evaluation_error,
            'scope':'Consistency of an explicit external human approval; not authentication of people, exam legality, statistical significance or teaching semantics. No Registry writes.'}
