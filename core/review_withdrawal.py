"""Apply explicitly bound negative semantic findings, never repair blind truth.

Reviewer identity and English judgement are external assertions. This operator
only withdraws reviewed credit and dependent artifacts, then reruns the engine.
"""
from copy import deepcopy
import hashlib
import json
from .analyzer import QuestionAnalyzer

FIELDS={'question_id','input_sha256','analysis_sha256','review_stage','reviewer','reviewer_kind',
        'reason','withdrawn_relation_indexes','withdrawn_execution_ids','failure_categories'}
FAILURES={'source_problem','method_trigger_problem','method_boundary_problem','evidence_problem',
          'method_composition_problem','semantic_review_problem','analyzer_problem','renderer_problem'}

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def withdraw_review(question,frozen_analysis,finding,analyzer=None):
    if set(finding)!=FIELDS:
        raise ValueError('Withdrawal permits only explicit negative review fields')
    if finding['question_id']!=question['question_id'] or frozen_analysis['question_id']!=question['question_id']:
        raise ValueError('Withdrawal question identity mismatch')
    if finding['input_sha256']!=fingerprint(question) or finding['analysis_sha256']!=fingerprint(frozen_analysis):
        raise ValueError('Withdrawal must bind exact input and frozen analysis')
    if finding['review_stage']!='post_reveal' or finding['reviewer_kind'] not in {'AI','human'}:
        raise ValueError('Withdrawal must declare actual post-reveal review')
    if any(not isinstance(finding[k],str) or not finding[k].strip() for k in ('reason','reviewer')):
        raise ValueError('Withdrawal needs named reviewer and concrete reason')
    categories=finding['failure_categories']
    if not isinstance(categories,list) or not categories or any(x not in FAILURES for x in categories) or len(categories)!=len(set(categories)):
        raise ValueError('Unknown, duplicate or missing failure classification')
    indices=finding['withdrawn_relation_indexes']; ids=finding['withdrawn_execution_ids']
    if (not isinstance(indices,list) or any(type(x) is not int for x in indices)
        or not isinstance(ids,list) or any(not isinstance(x,str) for x in ids)
        or len(indices)!=len(set(indices)) or len(ids)!=len(set(ids)) or not (indices or ids)):
        raise ValueError('Explicit unique withdrawal targets required')
    relations=question.get('relations',[]); actions=question.get('action_executions',[])
    if any(i<0 or i>=len(relations) for i in indices) or not set(ids)<={x['execution_id'] for x in actions}:
        raise ValueError('Unknown withdrawal target')
    engine=analyzer or QuestionAnalyzer()
    if engine.analyze(deepcopy(question))!=frozen_analysis:
        raise ValueError('Engine no longer matches frozen review; do not backfit a withdrawal')
    revised=deepcopy(question); withdrawn_relations=set(indices); withdrawn_actions=set(ids)
    # Keep relation indexes stable; never rewrite the candidate claim or effect.
    # A removed framework/decision also invalidates consumers, transitively.
    changed=True
    while changed:
        changed=False
        for action in actions:
            output=action.get('output') or {}
            targets=action['input_artifact_ids']+output.get('target_execution_ids',[])
            bad_relation=output.get('kind')=='candidate_decision' and output['relation_index'] in withdrawn_relations
            if action['execution_id'] in withdrawn_actions or bad_relation or set(targets)&withdrawn_actions:
                if action['execution_id'] not in withdrawn_actions:
                    withdrawn_actions.add(action['execution_id']); changed=True
                if output.get('kind')=='candidate_decision' and output['relation_index'] not in withdrawn_relations:
                    withdrawn_relations.add(output['relation_index']); changed=True
    for i in withdrawn_relations: revised['relations'][i]['review_status']='unreviewed'
    if 'action_executions' in revised:
        revised['action_executions']=[x for x in revised['action_executions'] if x['execution_id'] not in withdrawn_actions]
    # Old delivery assertions must not reappear after their proof was withdrawn.
    revised.pop('lesson_review',None); revised.pop('writing_review',None)
    result=engine.analyze(revised)
    return {'input':revised,'analysis':result,'withdrawal':{**deepcopy(finding),
        'effective_relation_indexes':sorted(withdrawn_relations),'effective_execution_ids':sorted(withdrawn_actions),
        'scope':'negative external review control; not semantic authentication, answer correction or new blind pass'}}
