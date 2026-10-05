"""Typed external action results, not automatic semantic execution or scoring.

Only reviewed, non-stopped earlier artifacts can be consumed. Raw input spans
remain available at every step; a previous locator never limits evidence scope.
"""
from copy import deepcopy
import hashlib
import json
from .composer import ROLE_ARTIFACTS, INPUT_ARTIFACTS, bind_contract
from .evidence import check_span
from .grammar_navigation import navigate_grammar


def output_spans(output):
    if output is None: return []
    if output['kind']=='located_evidence': return output['spans']
    if output['kind']=='interpretation': return [s for p in output['parts'] for s in p['evidence']]
    if output['kind']=='framework_card': return [s for f in output['fields'] for s in f['evidence']]
    if output['kind']=='text_groups': return [s for g in output['groups'] for s in g['spans']]
    return []


def covered_by(span, evidence):
    return any(s['field']==span['field'] and s['start']<=span['start'] and span['end']<=s['end'] for s in evidence)


def artifact_fingerprint(output):
    return hashlib.sha256(json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def check_output(question, execution, registry, produced):
    output=execution['output']
    if output is None: return
    mid=execution['method_id']; kind=output['kind']; role=execution['role']
    if kind not in ROLE_ARTIFACTS[role]: raise ValueError('Artifact output overclaims execution role')
    if mid in {'F01','F02','F03','F04'} and kind!='candidate_partition':
        raise ValueError('Seven-five grouping must produce a complete candidate partition')
    if mid in {'G01','G02'} and kind!='route_selection': raise ValueError('Grammar entry must produce a decision-tree route')
    for s in output_spans(output):
        check_span(question,s)
        if not covered_by(s,execution['evidence']): raise ValueError('Artifact quote lacks own action evidence')
    if kind=='candidate_partition':
        if not question.get('options'): raise ValueError('Candidate partition requires supplied options')
        ids=[c for g in output['groups'] for c in g['candidates']]
        if len(ids)!=len(set(ids)) or set(ids)!=set(question['options']):
            raise ValueError('Partition must cover every option exactly once; grouping is not elimination')
    elif kind=='candidate_decision':
        if question.get('options') and output['candidate'] not in question['options']: raise ValueError('Unknown artifact candidate')
        index=output['relation_index']; relations=question.get('relations',[])
        if index>=len(relations): raise ValueError('Decision artifact requires its own reviewed relation')
        relation=relations[index]
        if (relation['method_id']!=mid or relation['candidate']!=output['candidate'] or relation['effect']!=output['effect'] or relation['review_status']!='reviewed'
                or relation.get('execution_role',registry.methods[mid]['primary_role'])!=role):
            raise ValueError('Decision artifact does not match its reviewed candidate relation')
        if not all(covered_by(s,execution['evidence']) for s in relation['evidence']):
            raise ValueError('Decision artifact cannot borrow another action evidence')
    elif kind=='verification_result':
        targets=output['target_execution_ids']
        if len(targets)!=len(set(targets)) or not set(targets)<=set(execution['input_artifact_ids']):
            raise ValueError('Verifier must consume its named earlier decisions')
        for eid in targets:
            prior=produced.get(eid)
            if not prior or prior['output']['kind']!='candidate_decision' or prior['output']['candidate']!=output['candidate']:
                raise ValueError('Verification target must be the same candidate decision')
    elif kind=='framework_card':
        names=[f['name'] for f in output['fields']]
        if len(names)!=len(set(names)): raise ValueError('Repeated framework field')
        if mid=='R09' and set(names)!={'object','core_judgement','text_task'}:
            raise ValueError('R09 must produce object + core judgement + text task, not evidence-entry shortcuts')
        if mid=='C01' and set(names)!={'current_blank_role','recent_clue','expansion_gate','backfill_check'}:
            raise ValueError('C01 framework needs blank role, nearest clue, expansion gate and backfill check')
    elif kind=='route_selection':
        if question['question_type']!='语法填空': raise ValueError('Grammar route artifact requires grammar input')
        nav=navigate_grammar(question,registry)
        confirmed={n for path in nav['paths'] for n in path}
        if nav['hint_branch']!='unknown': confirmed.update({'entry','hint',nav['hint_branch']})
        ids=output['node_ids']
        if len(ids)!=len(set(ids)) or not set(ids)<=confirmed:
            raise ValueError('Route artifact requires explicit hint and separately reviewed function paths')
        basic={'entry','hint',nav['hint_branch']}
        if mid in {'G01','G02'} and nav['hint_branch'] not in ids: raise ValueError('Grammar entry route must expose its hint branch')
        if set(ids)-basic and not {p[-1] for p in nav['paths']}<=set(ids):
            raise ValueError('Route artifact must not silently drop competing reviewed functions')
    if mid=='R09' and kind!='framework_card': raise ValueError('R09 only produces a full-text skeleton card')
    if mid=='C01' and role=='framework' and kind!='framework_card': raise ValueError('C01 primary role only produces its four-field framework')


def execute_actions(question, chain, matches, registry, graph, trigger_nodes, complete, relation_nodes):
    """Validate and connect supplied actions; never manufacture missing actions."""
    records=question.get('action_executions',[]); result=[]; produced={}; seen=set()
    allowed={m['method_id']:m for m in matches}
    planned={s['method_id'] for s in chain}
    for supplied in records:
        x=deepcopy(supplied); eid=x['execution_id']; mid=x['method_id']; role=x['role']
        if eid in seen: raise ValueError('Duplicate action execution id')
        seen.add(eid)
        if mid not in allowed or mid not in planned: raise ValueError('Action requires a matched and planned method')
        method=registry.methods[mid]
        if x['method_version']!=method['version']: raise ValueError('Action method version mismatch')
        if role not in [method['primary_role']]+method['secondary_roles']: raise ValueError('Undeclared action role')
        inputs=x['input_artifact_ids']
        if len(inputs)!=len(set(inputs)): raise ValueError('Repeated action input artifact')
        for source_id in inputs:
            if source_id not in produced: raise ValueError('Action input must be earlier, reviewed, complete and not stopped')
            if produced[source_id]['output']['kind'] not in INPUT_ARTIFACTS[role]:
                raise ValueError('Incompatible action artifact dependency')
        evidence=[check_span(question,s) for s in x['evidence']]
        if not any(s['field'] in {'passage','stem','student_text'} for s in evidence): raise ValueError('Action cannot be supported only by option wording')
        if question['question_type'] in {'阅读理解','七选五','完形填空'} and not any(s['field']=='passage' for s in evidence):
            raise ValueError('Objective action requires current passage evidence')
        if x['stop_applied'] and x['output'] is not None: raise ValueError('Stopped action must not produce an artifact')
        if not x['stop_applied'] and x['output'] is None: raise ValueError('Continuing action requires a concrete output')
        check_output(question,x,registry,produced)
        reviewed=x['review_status']=='reviewed'
        if reviewed and not allowed[mid]['trigger_verified']: raise ValueError('Action requires independently reviewed trigger')
        if reviewed and x['stop_applied'] and role=='decider' and any(r['method_id']==mid and r['review_status']=='reviewed' and r['effect']!='undetermined' and r.get('execution_role',method['primary_role'])==role for r in question.get('relations',[])):
            raise ValueError('Stopped decider cannot simultaneously assert reviewed candidate effects')
        action_complete=complete
        if question['question_type'] in {'阅读理解','七选五','完形填空'}:
            kind=x['output']['kind'] if x['output'] else None
            requires_choices=role=='decider' or kind in {'candidate_partition','candidate_decision','verification_result'}
            # Missing choices blocks decisions, not an independently supported
            # locate/interpret/framework action on the supplied passage and task.
            action_complete=complete if requires_choices else bool(question.get('passage') and question['stem'])
        state='unreviewed' if not reviewed else 'incomplete_input' if not action_complete else 'stopped' if x['stop_applied'] else 'produced'
        evidence_ids=[]; action_id=None; artifact_id=None
        if reviewed:
            action_id=graph.node('method_action',x['concrete_action'],method_id=mid,execution_id=eid,reviewed=state in {'produced','stopped'})
            for signal in trigger_nodes.get(mid,[]): graph.edge(signal,action_id,'supports')
            for span in evidence:
                nid=graph.node('source_evidence',span['quote'],span=span); evidence_ids.append(nid); graph.edge(nid,action_id,'supports')
            for source_id in inputs: graph.edge(produced[source_id]['artifact_node_id'],action_id,'supports')
            if state=='produced':
                attrs={}
                if x['output']['kind']=='candidate_decision':
                    attrs['candidate']=x['output']['candidate']
                    graph.edge(relation_nodes[x['output']['relation_index']],action_id,'supports')
                elif x['output']['kind']=='verification_result': attrs['candidate']=x['output']['candidate']
                artifact_id=graph.node('action_artifact',x['output']['kind'],method_id=mid,execution_id=eid,artifact_kind=x['output']['kind'],artifact_fingerprint=artifact_fingerprint(x['output']),reviewed=True,**attrs)
                edge={'locator':'locates','reducer':'narrows','verifier':'verifies'}.get(role,'supports')
                graph.edge(action_id,artifact_id,edge)
        item={**x,'output':x['output'] if state=='produced' else None,'state':state,'evidence_ids':evidence_ids,'action_node_id':action_id,'artifact_node_id':artifact_id,'scope':'external_action_review_not_semantic_certification'}
        result.append(item)
        if state=='produced': produced[eid]=item
        step=next((s for s in chain if s['method_id']==mid and s['role']==role),None)
        if step is None:
            step=bind_contract({'method_id':mid,'role':role,'input':'显式副职责阶段；消费已审阅产物或重新回题面取证，不代表主要职责自动升级','output':{'locator':'locate','interpreter':'interpret','reducer':'reduce','decider':'decide','verifier':'verify','framework':'interpret'}[role],'action':x['concrete_action'],'stop_rule':method['stop_rule'],'state':'planned'})
            chain.append(step)
        step['execution_ids'].append(eid)
        states={r['state'] for r in result if r['execution_id'] in step['execution_ids']}
        if 'produced' in states: step['state']='executed'
        elif 'stopped' in states: step['state']='stopped'
    return result


def validate_execution_trace(analysis,registry=None):
    """Check serialized trace/chain/graph binding; not semantic authenticity."""
    nodes={n['id']:n for n in analysis['evidence_graph']['nodes']}; produced={}; seen={}
    for x in analysis['execution_trace']:
        eid=x['execution_id']; mid=x['method_id']; role=x['role']
        if eid in seen: raise ValueError('Duplicate serialized execution')
        seen[eid]=x
        if analysis['method_versions'].get(mid)!=x['method_version']: raise ValueError('Serialized action version mismatch')
        if registry is not None:
            method=registry.methods.get(mid)
            if not method or method['version']!=x['method_version'] or role not in [method['primary_role']]+method['secondary_roles']:
                raise ValueError('Serialized action violates Registry role/version binding')
        if len(x['input_artifact_ids'])!=len(set(x['input_artifact_ids'])): raise ValueError('Repeated serialized action input')
        for source_id in x['input_artifact_ids']:
            if source_id not in produced or produced[source_id]['output']['kind'] not in INPUT_ARTIFACTS[role]:
                raise ValueError('Serialized trace has unusable or incompatible dependency')
        if x['state']=='produced':
            if x['stop_applied'] or x['review_status']!='reviewed' or x['output'] is None or x['output']['kind'] not in ROLE_ARTIFACTS[role]:
                raise ValueError('Serialized artifact must have a reviewed continuing role')
            artifact=nodes.get(x['artifact_node_id'],{}); action=nodes.get(x['action_node_id'],{})
            if (artifact.get('type')!='action_artifact' or artifact.get('execution_id')!=eid or artifact.get('method_id')!=mid
                    or artifact.get('artifact_kind')!=x['output']['kind'] or artifact.get('artifact_fingerprint')!=artifact_fingerprint(x['output'])
                    or action.get('type')!='method_action' or action.get('execution_id')!=eid or action.get('method_id')!=mid or action.get('label')!=x['concrete_action']):
                raise ValueError('Serialized output is not bound to its own action graph')
            if not any(e['from']==x['action_node_id'] and e['to']==x['artifact_node_id'] for e in analysis['evidence_graph']['edges']):
                raise ValueError('Serialized artifact lacks direct producing action edge')
            produced[eid]=x
        elif x['output'] is not None or x['artifact_node_id'] is not None:
            raise ValueError('Unusable action must not expose a produced artifact')
        if x['state']=='stopped' and (not x['stop_applied'] or x['review_status']!='reviewed'):
            raise ValueError('Serialized stop was not reviewed')
        if (x['state']=='unreviewed')!=(x['review_status']=='unreviewed'):
            raise ValueError('Serialized action review state mismatch')
        evidence_nodes=[nodes.get(nid,{}) for nid in x['evidence_ids']]
        if any(n.get('type')!='source_evidence' or n.get('span') not in x['evidence'] for n in evidence_nodes):
            raise ValueError('Serialized action evidence ids do not bind current spans')
        if x['review_status']=='reviewed':
            action=nodes.get(x['action_node_id'],{})
            if action.get('type')!='method_action' or action.get('execution_id')!=eid or action.get('method_id')!=mid or action.get('label')!=x['concrete_action']:
                raise ValueError('Serialized reviewed action lacks its own graph node')
            if [n.get('span') for n in evidence_nodes]!=x['evidence']:
                raise ValueError('Serialized action omits its own evidence bindings')
            incoming={e['from'] for e in analysis['evidence_graph']['edges'] if e['to']==x['action_node_id'] and nodes[e['from']]['type']=='action_artifact'}
            if incoming!={produced[source_id]['artifact_node_id'] for source_id in x['input_artifact_ids']}:
                raise ValueError('Serialized action input IDs differ from graph dependencies')
        elif x['action_node_id'] is not None or x['evidence_ids']:
            raise ValueError('Unreviewed action must not expose reviewed graph bindings')
    bound=[]
    for step in analysis['method_chain']:
        if registry is not None:
            method=registry.methods.get(step['method_id'])
            if (not method or analysis['method_versions'].get(step['method_id'])!=method['version']
                    or method['question_type']!=analysis['question_type']
                    or step['role'] not in [method['primary_role']]+method['secondary_roles']):
                raise ValueError('Serialized method plan violates Registry role/version binding')
            expected_output=method['output_type'] if step['role']==method['primary_role'] else {
                'locator':'locate','interpreter':'interpret','reducer':'reduce',
                'decider':'decide','verifier':'verify','framework':'interpret'}[step['role']]
            if step['output']!=expected_output or step['stop_rule']!=method['stop_rule']:
                raise ValueError('Serialized method plan changed Registry output/stop rule')
            if step['role']==method['primary_role'] and step['action']!=method['core_action']:
                raise ValueError('Serialized method plan changed Registry primary action')
        if step['input_artifact_types']!=INPUT_ARTIFACTS[step['role']] or step['output_artifact_types']!=ROLE_ARTIFACTS[step['role']]:
            raise ValueError('Serialized method contract was changed')
        for eid in step['execution_ids']:
            if eid not in seen or seen[eid]['method_id']!=step['method_id'] or seen[eid]['role']!=step['role']:
                raise ValueError('Serialized execution does not belong to chain step')
            bound.append(eid)
        states={seen[eid]['state'] for eid in step['execution_ids']}
        expected='executed' if 'produced' in states else 'stopped' if 'stopped' in states else None
        if (expected is not None and step['state']!=expected) or (expected is None and step['state'] in {'executed','stopped'}):
            raise ValueError('Serialized method execution state was fabricated')
    if len(bound)!=len(set(bound)) or set(bound)!=set(seen): raise ValueError('Serialized chain must bind each execution once')
    if {x['artifact_node_id'] for x in produced.values()}!={n['id'] for n in nodes.values() if n['type']=='action_artifact'}:
        raise ValueError('Serialized graph must bind every artifact to its execution trace')
    return analysis['execution_trace']
