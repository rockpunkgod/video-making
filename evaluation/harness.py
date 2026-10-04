from collections import defaultdict
import json
from pathlib import Path
from statistics import mean
import math
from core.registry import validate_schema

KINDS = {'positive_trigger','negative_trigger','counterexample','boundary','transfer'}
METRICS = ['trigger_precision','trigger_recall','resolution_rate','standalone_rate','assist_rate','false_trigger_rate','transfer_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']
def ratio(n,d): return n/d if d else None
def rate(rows,predicate): return ratio(sum(bool(predicate(x)) for x in rows),len(rows))
def average(rows,condition,key): return mean(x[condition][key] for x in rows) if rows else None

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
        'resolution_rate':rate(active,lambda x:x['resolved']),
        'standalone_rate':rate(active,lambda x:x['standalone']),
        'assist_rate':rate(active,lambda x:x['assisted']),
        'false_trigger_rate':rate(negative,lambda x:x['triggered']),
        'transfer_rate':rate(transfer,lambda x:x['action_success'] and x['evidence_success'] and not x['answer_backfit']),
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

def evaluate(records,plan=None):
    validate_records(records)
    if plan is not None: validate_plan(plan)
    origin = records[0]['origin'] if records else 'empty'
    groups = defaultdict(list)
    for x in records: groups[(x['method_id'],x['method_version'])].append(x)
    output = {'schema_version':'1.0.0','origin':origin,'record_count':len(records),'groups':[],'limitations':['指标仅计算输入观察；origin、参与者与审阅真实性须由研究者外部审计。Synthetic 不得用于等级升级。']}
    for (mid,version),rows in groups.items():
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
        p = plan if plan and plan['method_id']==mid and plan['method_version']==version else None
        full = [x for x in blind if x['compact_version']=='90s']
        full_metrics,_ = metrics(full)
        for v in ['10s','30s','90s']:
            sample = [x for x in blind if x['compact_version']==v]
            sm,_ = metrics(sample)
            safe = 'untested'
            covered = KINDS <= {x['case_type'] for x in sample}
            # Require comparable frozen dataset, per-version independent groups/counterbalanced assignment,
            # and communication -> freeze -> first-use/blind evidence before a release recommendation.
            comparable = bool(p and full and sample and covered and KINDS <= {x['case_type'] for x in full}
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
                nums = [sm['false_trigger_rate'],sm['boundary_accuracy'],sm['role_overclaim_rate'],sm['stop_rule_failure_rate'],full_metrics['false_trigger_rate'],full_metrics['boundary_accuracy'],full_metrics['stop_rule_failure_rate']]
                if all(x is not None for x in nums):
                    safe = bool(sm['false_trigger_rate']<=full_metrics['false_trigger_rate']+p['max_false_trigger_delta']
                                and sm['boundary_accuracy']>=p['min_boundary_accuracy']
                                and sm['boundary_accuracy']>=full_metrics['boundary_accuracy']-p['max_boundary_drop']
                                and sm['role_overclaim_rate']==0
                                and sm['stop_rule_failure_rate']<=full_metrics['stop_rule_failure_rate']+p['max_stop_failure_delta'])
            safety.append({'version':v,**{k:sm[k] for k in ['false_trigger_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']},'safe_for_release':safe})
        eligible = bool(origin=='real' and p and all(x['safe_for_release'] is True for x in safety)
                        and first and not any(failure_types(x) for x in first)
                        and comm['recall_rate']>=p['min_recall_rate'] and comm['natural_restatement_rate']>=p['min_restatement_rate'])
        gain = compared['accuracy']['gain']
        improved = any(compared[k]['gain'] is not None and compared[k]['gain']>=p['minimum_efficiency_gain'].get(k,float('inf')) for k in ['time_seconds','candidates_remaining','evidence_span','hesitation_count','unresolved']) if p else False
        # Means alone do not establish significance. They can only request review.
        upgrade = 'review_for_Signature' if eligible and gain is not None and gain>=0 and improved else 'review_for_Efficient' if origin=='real' and p and blind and gain is not None and gain>=0 and improved else 'none'
        output['groups'].append({'method_id':mid,'method_version':version,'record_count':len(rows),'metrics':m,'baseline_comparison':compared,'first_use':first_result,'communication':comm,'short_version_safety':safety,'release_eligible':eligible,'upgrade_eligible':upgrade,'limitations':['缺样本指标为null；阈值与计划须测试前冻结，工具不替代真实性和统计显著性审阅。','不自动修改 Registry 状态或实用等级。']})
    validate_schema('evaluation-result',output)
    return output

def validate_plan(plan):
    required = {'method_id','method_version','dataset_id','communication_freeze_id','minimum_participants_per_version','max_false_trigger_delta','min_boundary_accuracy','max_boundary_drop','max_stop_failure_delta','min_recall_rate','min_restatement_rate','minimum_efficiency_gain','frozen_before_data_collection','rationale'}
    if set(plan)!=required: raise ValueError('Incomplete or unknown evaluation plan fields')
    if plan['frozen_before_data_collection'] is not True or plan['minimum_participants_per_version']<2 or not plan['rationale']:
        raise ValueError('Plan must be frozen in advance with sample design and risk rationale')
    for key in ['max_false_trigger_delta','min_boundary_accuracy','max_boundary_drop','max_stop_failure_delta','min_recall_rate','min_restatement_rate']:
        if isinstance(plan[key],bool) or not 0<=plan[key]<=1: raise ValueError('Invalid safety threshold')
