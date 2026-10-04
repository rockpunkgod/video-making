from collections import defaultdict
import json
from pathlib import Path
from statistics import mean
from datetime import datetime
import math
from core.registry import Registry,validate_schema

KINDS = {'positive_trigger','negative_trigger','counterexample','boundary','transfer'}
METRICS = ['trigger_precision','trigger_recall','resolution_rate','standalone_rate','assist_rate','false_trigger_rate','transfer_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']
COMMUNICATION_CHECKS={'comprehension','memory','natural_speech','visual_action','short_long_consistency'}
PRACTICALITY_CHECKS={'trigger','action','output','stop','transfer','efficiency_or_value','misuse_cost','role_correctness'}

def timestamp(value):
    if not isinstance(value,str): raise ValueError('Timestamp must be an ISO string with timezone')
    try: parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc: raise ValueError('Invalid evaluation timestamp') from exc
    if parsed.tzinfo is None: raise ValueError('Evaluation timestamp must include timezone')
    return parsed
def ratio(n,d): return n/d if d else None
def rate(rows,predicate): return ratio(sum(bool(predicate(x)) for x in rows),len(rows))
def average(rows,condition,key): return mean(x[condition][key] for x in rows) if rows else None
def action_evidence_valid(x):
    return x['action_success'] and x['evidence_success'] and not any(x[k] for k in ['answer_backfit','role_overclaim','execution_breakdown'])

def load_records(path):
    p = Path(path)
    raw = p.read_text(encoding='utf-8-sig')
    records = [json.loads(line) for line in raw.splitlines() if line.strip()] if p.suffix=='.jsonl' else json.loads(raw)
    if not isinstance(records,list): raise ValueError('Evaluation data must be a JSON array or JSONL records')
    return records

def validate_records(records):
    ids, trials = set(),set()
    for x in records:
        validate_schema('evaluation-record',x)
        key = (x['participant_id'],x['method_id'],x['method_version'],x['question_id'],x['phase'],x['compact_version'])
        if x['record_id'] in ids or key in trials: raise ValueError('Duplicate evaluation observation')
        ids.add(x['record_id']); trials.add(key)
        if 'observed_at' in x: timestamp(x['observed_at'])
        if x['standalone'] and x['assisted']: raise ValueError('Standalone and assist are mutually exclusive')
        if (x['standalone'] or x['assisted']) and not x['resolved']: raise ValueError('Role result without resolution')
        if x['resolved'] and (not x['triggered'] or not x['applicable']): raise ValueError('Resolution requires applicable trigger')
        if x['case_type'] in {'boundary','counterexample'} and not x['stop_required']:
            raise ValueError('Boundary/counterexample must explicitly test stopping')
        if x['declared_primary_role'] != x['observed_actual_role'] and not x['role_overclaim']:
            raise ValueError('Role mismatch must not be hidden in success flags')
        for condition in ['baseline','method']:
            if any(not math.isfinite(x[condition][key]) for key in ['time_seconds','candidates_remaining','evidence_span','hesitation_count']):
                raise ValueError('Measurements must be finite')
    if len({x['origin'] for x in records})>1: raise ValueError('Do not mix synthetic and real observations')

def metrics(rows):
    triggered = [x for x in rows if x['triggered']]
    applicable = [x for x in rows if x['applicable']]
    active = [x for x in triggered if x['applicable']]
    negative = [x for x in rows if not x['applicable']]
    transfer = [x for x in rows if x['case_type']=='transfer']
    boundary = [x for x in rows if x['case_type']=='boundary']
    stops = [x for x in rows if x['stop_required']]
    out = {
        'trigger_precision':rate(triggered,lambda x:x['applicable']),
        'trigger_recall':rate(applicable,lambda x:x['triggered']),
        'resolution_rate':rate(active,lambda x:x['resolved'] and action_evidence_valid(x)),
        'standalone_rate':rate(active,lambda x:x['standalone'] and action_evidence_valid(x)),
        'assist_rate':rate(active,lambda x:x['assisted'] and action_evidence_valid(x)),
        'false_trigger_rate':rate(negative,lambda x:x['triggered']),
        'transfer_rate':rate(transfer,lambda x:action_evidence_valid(x) and x['triggered']==x['applicable'] and (not x['stop_required'] or x['stopped'])),
        'boundary_accuracy':rate(boundary,lambda x:x['boundary_detected'] and x['stopped'] and x['evidence_success'] and not x['role_overclaim'] and x['method']['accuracy']),
        'role_overclaim_rate':rate(rows,lambda x:x['role_overclaim']),
        'stop_rule_failure_rate':rate(stops,lambda x:not x['stopped']),
    }
    denominators = [len(triggered),len(applicable),len(active),len(active),len(active),len(negative),len(transfer),len(boundary),len(rows),len(stops)]
    # Persist numerators, denominators, and observation ids for auditability.
    counts = {key:{'numerator':None if out[key] is None else round(out[key]*den),'denominator':den} for key,den in zip(METRICS,denominators)}
    return out,counts

def failure_types(x):
    fail = []
    if x['applicable'] and not x['triggered']: fail.append('missed_trigger')
    if not x['applicable'] and x['triggered']: fail.append('false_trigger')
    if x['triggered'] and not x['action_success']: fail.append('wrong_first_action')
    if x['triggered'] and not x['evidence_success']: fail.append('wrong_evidence')
    if x['stop_required'] and not x['stopped']: fail.append('ignored_stop_rule')
    if x['answer_backfit']: fail.append('answer_backfit')
    if x['role_overclaim']: fail.append('method_overreach')
    if x['execution_breakdown'] and not fail: fail.append('execution_breakdown')
    return fail

def comparison(rows):
    out = {}
    for key in ['accuracy','time_seconds','candidates_remaining','evidence_span','hesitation_count','unresolved']:
        baseline = average(rows,'baseline',key)
        method = average(rows,'method',key)
        out[key] = {'baseline':baseline,'method':method,'gain':None if baseline is None else method-baseline if key=='accuracy' else baseline-method}
    out['paired_observations'] = len(rows)
    return out

def audit_design(rows,plan,registry):
    """Check declared study lineage, not authenticity of people or timestamps."""
    checks={}; phases={phase:[x for x in rows if x['phase']==phase] for phase in ['communication','first_use','blind']}
    checks['matching_frozen_plan']=bool(plan)
    method=registry.methods.get(rows[0]['method_id']) if rows else None
    checks['registry_version_role_binding']=bool(method and method['version']==rows[0]['method_version'] and all(x['declared_primary_role']==method['primary_role'] for x in rows))
    checks['standalone_role_capacity']=bool(method and (method['primary_role']=='decider' or 'decider' in method['secondary_roles'] or not any(x['standalone'] for x in rows)))
    workflow=plan.get('workflow') if plan else None
    checks['workflow_artifact_present']=bool(workflow)
    checks['all_three_phases_present']=all(phases.values())
    checks['all_observation_times_present']=all('observed_at' in x for x in rows)
    checks['controlled_blind_assignment']=bool(phases['blind']) and all(x['assignment'] in {'randomized','counterbalanced'} for x in phases['blind'])
    item_labels=defaultdict(set)
    for x in rows:
        item_labels[x['question_id']].add((x['case_type'],x['applicable'],x['stop_required']))
    checks['consistent_frozen_item_labels']=all(len(labels)==1 for labels in item_labels.values())
    checks['no_role_overclaim']=not any(x['role_overclaim'] for x in rows)
    checks['first_use_without_failures']=bool(phases['first_use']) and not any(failure_types(x) for x in phases['first_use'])
    checks['workflow_checks_passed']=bool(workflow and all(workflow['communication_checks'].values()) and all(workflow['practicality_checks'].values()))
    checks['communication_freeze_bound_to_observations']=bool(workflow and set(workflow['communication_record_ids'])=={x['record_id'] for x in phases['communication']} and phases['communication'])
    checks['communication_observed_success']=bool(plan and phases['communication'] and rate(phases['communication'],lambda x:x['recall_success'])>=plan['min_recall_rate'] and rate(phases['communication'],lambda x:x['natural_restatement'])>=plan['min_restatement_rate'])
    checks['demonstration_not_reused_as_test']=bool(workflow and all(x['question_id'] not in workflow['demonstration_item_ids'] for x in phases['first_use']+phases['blind']))
    seen={}
    for x in rows:
        seen.setdefault(x['participant_id'],set()).add(x['compact_version'])
    checks['cross_phase_learning_control']=all(len(seen[x['participant_id']])==1 or x['assignment']=='counterbalanced' for x in phases['blind'])
    first_seen={(x['participant_id'],x['question_id']) for x in phases['first_use']}
    checks['first_use_item_not_repeated_blind']=not any((x['participant_id'],x['question_id']) in first_seen for x in phases['blind'])
    checks['phase_order']=False
    if workflow and checks['all_three_phases_present'] and checks['all_observation_times_present']:
        times={phase:[timestamp(x['observed_at']) for x in entries] for phase,entries in phases.items()}
        study=timestamp(workflow['study_frozen_at']); freeze=timestamp(workflow['communication_frozen_at']); gate=timestamp(workflow['practicality_reviewed_at'])
        checks['phase_order']=study<=min(min(values) for values in times.values()) and max(times['communication'])<=freeze<=gate<min(times['first_use']) and max(times['first_use'])<min(times['blind'])
    # Binding failures must also block efficiency suggestions, not just release.
    blockers=[key for key,value in checks.items() if not value]
    return {'ready_for_review':not blockers,'blocking_reasons':blockers,'checks':checks,'record_ids':[x['record_id'] for x in rows],'scope':'declared lineage only; dates, people, gate judgements and collected data require independent external audit'}

def evaluate(records,plan=None):
    validate_records(records)
    if plan is not None: validate_plan(plan)
    origin = records[0]['origin'] if records else 'empty'
    registry=Registry() if records else None
    groups = defaultdict(list)
    for x in records: groups[(x['method_id'],x['method_version'],x['dataset_id'],x['communication_freeze_id'])].append(x)
    output = {'schema_version':'1.1.0','origin':origin,'record_count':len(records),'groups':[],'limitations':['指标仅计算输入观察；origin、参与者与审阅真实性须由研究者外部审计。Synthetic 不得用于等级升级。']}
    for (mid,version,dataset,freeze),rows in groups.items():
        blind = [x for x in rows if x['phase']=='blind']
        first = [x for x in rows if x['phase']=='first_use']
        communication = [x for x in rows if x['phase']=='communication']
        m,counts = metrics(blind)
        compared = comparison(blind)
        compared['metric_counts'] = counts
        compared['record_ids'] = [x['record_id'] for x in blind]
        first_result = {'record_count':len(first),'trigger_success':rate(first,lambda x:x['triggered']==x['applicable']),'action_success':rate([x for x in first if x['applicable']],lambda x:x['action_success']),'evidence_success':rate(first,lambda x:x['evidence_success']),'stop_rule_success':rate([x for x in first if x['stop_required']],lambda x:x['stopped']),'final_result':'pending_real_participant_validation' if origin!='real' or not first else 'observed_not_automatically_passed','failures':[{'record_id':x['record_id'],'failure_type':failure_types(x),'observed_first_action':x['observed_first_action'],'observed_evidence':x['observed_evidence'],'notes':x['notes']} for x in first],'role_correctness':[{'declared_primary_role':x['declared_primary_role'],'observed_actual_role':x['observed_actual_role'],'role_match':x['declared_primary_role']==x['observed_actual_role'],'overclaim_detected':x['role_overclaim'],'notes':x['notes']} for x in first]}
        comm = {'record_count':len(communication),'recall_rate':rate(communication,lambda x:x['recall_success']),'natural_restatement_rate':rate(communication,lambda x:x['natural_restatement'])}
        safety = []
        p = plan if plan and plan['method_id']==mid and plan['method_version']==version and plan['dataset_id']==dataset and plan['communication_freeze_id']==freeze else None
        design=audit_design(rows,p,registry)
        full = [x for x in blind if x['compact_version']=='90s']
        full_metrics,_ = metrics(full)
        for v in ['10s','30s','90s']:
            sample = [x for x in blind if x['compact_version']==v]
            sm,sm_counts = metrics(sample)
            active_sample=[x for x in sample if x['triggered'] and x['applicable']]
            active_full=[x for x in full if x['triggered'] and x['applicable']]
            action_failure=rate(active_sample,lambda x:not x['action_success'] or x['execution_breakdown'] or x['answer_backfit'])
            evidence_failure=rate(active_sample,lambda x:not x['evidence_success'])
            full_action_failure=rate(active_full,lambda x:not x['action_success'] or x['execution_breakdown'] or x['answer_backfit'])
            full_evidence_failure=rate(active_full,lambda x:not x['evidence_success'])
            safe = 'untested'
            covered = KINDS <= {x['case_type'] for x in sample}
            # Require comparable frozen dataset, per-version independent groups/counterbalanced assignment,
            # and communication -> freeze -> first-use/blind evidence before a release recommendation.
            comparable = bool(p and all(key in p for key in ['max_action_failure_delta','max_evidence_failure_delta']) and design['ready_for_review'] and full and sample and covered and KINDS <= {x['case_type'] for x in full}
                              and len({x['participant_id'] for x in sample})>=p['minimum_participants_per_version']
                              and len({x['participant_id'] for x in full})>=p['minimum_participants_per_version']
                              and all(x['dataset_id']==p['dataset_id'] and x['communication_freeze_id']==p['communication_freeze_id'] and x['assignment'] in {'randomized','counterbalanced'} for x in sample+full)
                              and bool(communication) and bool(first))
            if comparable:
                versions_by_person = defaultdict(set)
                for x in sample+full: versions_by_person[x['participant_id']].add(x['compact_version'])
                reused = {person for person,versions in versions_by_person.items() if len(versions)>1}
                if any(x['participant_id'] in reused and x['assignment']!='counterbalanced' for x in sample+full):
                    comparable = False
                if {x['question_id'] for x in sample} != {x['question_id'] for x in full}:
                    comparable = False
            if origin=='real' and comparable:
                nums = [sm['false_trigger_rate'],sm['boundary_accuracy'],sm['role_overclaim_rate'],sm['stop_rule_failure_rate'],full_metrics['false_trigger_rate'],full_metrics['boundary_accuracy'],full_metrics['stop_rule_failure_rate'],action_failure,evidence_failure,full_action_failure,full_evidence_failure]
                if all(x is not None for x in nums):
                    safe = bool(sm['false_trigger_rate']<=full_metrics['false_trigger_rate']+p['max_false_trigger_delta']
                                and sm['boundary_accuracy']>=p['min_boundary_accuracy']
                                and sm['boundary_accuracy']>=full_metrics['boundary_accuracy']-p['max_boundary_drop']
                                and sm['role_overclaim_rate']==0
                                and sm['stop_rule_failure_rate']<=full_metrics['stop_rule_failure_rate']+p['max_stop_failure_delta']
                                and action_failure<=full_action_failure+p['max_action_failure_delta']
                                and evidence_failure<=full_evidence_failure+p['max_evidence_failure_delta'])
            safety_counts={k:sm_counts[k] for k in ['false_trigger_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']}
            safety_counts.update(action_failure_rate={'numerator':None if action_failure is None else round(action_failure*len(active_sample)),'denominator':len(active_sample)},evidence_failure_rate={'numerator':None if evidence_failure is None else round(evidence_failure*len(active_sample)),'denominator':len(active_sample)})
            safety.append({'version':v,**{k:sm[k] for k in ['false_trigger_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']},'action_failure_rate':action_failure,'evidence_failure_rate':evidence_failure,'metric_counts':safety_counts,'record_ids':[x['record_id'] for x in sample],'safe_for_release':safe})
        eligible = bool(origin=='real' and p and all(x['safe_for_release'] is True for x in safety)
                        and first and not any(failure_types(x) for x in first)
                        and comm['recall_rate']>=p['min_recall_rate'] and comm['natural_restatement_rate']>=p['min_restatement_rate'])
        gain = compared['accuracy']['gain']
        improved = any(compared[k]['gain'] is not None and compared[k]['gain']>=p['minimum_efficiency_gain'].get(k,float('inf')) for k in ['time_seconds','candidates_remaining','evidence_span','hesitation_count','unresolved']) if p else False
        # Means alone do not establish significance. They can only request review.
        blind_covered=bool(p and KINDS<={x['case_type'] for x in blind} and len({x['participant_id'] for x in blind})>=p['minimum_participants_per_version'])
        upgrade = 'review_for_Signature' if eligible and gain is not None and gain>=0 and improved else 'review_for_Efficient' if origin=='real' and p and design['ready_for_review'] and blind_covered and gain is not None and gain>=0 and improved else 'none'
        output['groups'].append({'method_id':mid,'method_version':version,'dataset_id':dataset,'communication_freeze_id':freeze,'record_count':len(rows),'design_audit':design,'metrics':m,'baseline_comparison':compared,'first_use':first_result,'communication':comm,'short_version_safety':safety,'release_eligible':eligible,'upgrade_eligible':upgrade,'limitations':['缺样本指标为null；阈值与计划须测试前冻结，工具不替代真实性和统计显著性审阅。','不自动修改 Registry 状态或实用等级。']})
    validate_schema('evaluation-result',output)
    return output

def validate_plan(plan):
    required = {'method_id','method_version','dataset_id','communication_freeze_id','minimum_participants_per_version','max_false_trigger_delta','min_boundary_accuracy','max_boundary_drop','max_stop_failure_delta','min_recall_rate','min_restatement_rate','minimum_efficiency_gain','frozen_before_data_collection','rationale'}
    if not required<=set(plan) or set(plan)-required-{'workflow','max_action_failure_delta','max_evidence_failure_delta'}: raise ValueError('Incomplete or unknown evaluation plan fields')
    if any(not isinstance(plan[key],str) or not plan[key].strip() for key in ['method_id','method_version','dataset_id','communication_freeze_id','rationale']): raise ValueError('Invalid plan identity or rationale')
    participants=plan['minimum_participants_per_version']
    if plan['frozen_before_data_collection'] is not True or isinstance(participants,bool) or not isinstance(participants,int) or participants<2:
        raise ValueError('Plan must be frozen in advance with sample design and risk rationale')
    for key in ['max_false_trigger_delta','min_boundary_accuracy','max_boundary_drop','max_stop_failure_delta','min_recall_rate','min_restatement_rate']:
        if isinstance(plan[key],bool) or not isinstance(plan[key],(int,float)) or not math.isfinite(plan[key]) or not 0<=plan[key]<=1: raise ValueError('Invalid safety threshold')
    if any(plan[key]<=0 for key in ['min_boundary_accuracy','min_recall_rate','min_restatement_rate']): raise ValueError('Passing thresholds require positive observed evidence')
    for key in ['max_action_failure_delta','max_evidence_failure_delta']:
        if key in plan and (isinstance(plan[key],bool) or not isinstance(plan[key],(int,float)) or not math.isfinite(plan[key]) or not 0<=plan[key]<=1): raise ValueError('Invalid action/evidence safety threshold')
    gains=plan['minimum_efficiency_gain']
    if not isinstance(gains,dict) or set(gains)-{'time_seconds','candidates_remaining','evidence_span','hesitation_count','unresolved'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in gains.values()):
        raise ValueError('Efficiency gain thresholds must be finite positive effects')
    workflow=plan.get('workflow')
    if workflow is not None:
        fields={'study_frozen_at','communication_frozen_at','practicality_reviewed_at','communication_record_ids','communication_checks','practicality_checks','demonstration_item_ids','reviewer','evidence_notes'}
        if not isinstance(workflow,dict) or set(workflow)!=fields: raise ValueError('Incomplete workflow artifact')
        for key in ['study_frozen_at','communication_frozen_at','practicality_reviewed_at']: timestamp(workflow[key])
        for key,expected in [('communication_checks',COMMUNICATION_CHECKS),('practicality_checks',PRACTICALITY_CHECKS)]:
            if not isinstance(workflow[key],dict) or set(workflow[key])!=expected or any(not isinstance(v,bool) for v in workflow[key].values()): raise ValueError('Invalid workflow gate checks')
        for key in ['communication_record_ids','demonstration_item_ids']:
            values=workflow[key]
            if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values): raise ValueError('Invalid workflow evidence ids')
        if any(not isinstance(workflow[key],str) or not workflow[key].strip() for key in ['reviewer','evidence_notes']): raise ValueError('Workflow requires reviewer and actual evidence notes')
