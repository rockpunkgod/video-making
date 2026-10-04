ROLE_ORDER = {'framework':0,'locator':1,'interpreter':2,'reducer':3,'decider':4,'verifier':5}
ROLE_ARTIFACTS = {
    'framework':['framework_card','route_selection'],
    'locator':['located_evidence'],
    'interpreter':['interpretation'],
    'reducer':['candidate_partition','text_groups','route_selection'],
    'decider':['candidate_decision'],
    'verifier':['verification_result','located_evidence'],
}
INPUT_ARTIFACTS = {
    'framework':['located_evidence','interpretation','framework_card','route_selection'],
    'locator':['framework_card','route_selection'],
    'interpreter':['located_evidence','framework_card','route_selection'],
    'reducer':['located_evidence','interpretation','framework_card','route_selection'],
    'decider':['located_evidence','interpretation','candidate_partition','text_groups','framework_card','route_selection','verification_result'],
    'verifier':['located_evidence','interpretation','candidate_decision','framework_card'],
}

def bind_contract(step):
    """Contracts describe acceptable artifacts, not an assertion of execution."""
    step.update(input_artifact_types=list(INPUT_ARTIFACTS[step['role']]),output_artifact_types=list(ROLE_ARTIFACTS[step['role']]),execution_ids=[])
    return step

def compose(question,matches,registry):
    allowed = {m['method_id'] for m in matches}
    requested = question.get('requested_chain')
    ids = requested if requested is not None else [m['method_id'] for m in sorted(matches,key=lambda x:ROLE_ORDER[x['role']])]
    if len(ids) != len(set(ids)): raise ValueError('Repeated method in chain')
    steps = []
    for mid in ids:
        if mid not in allowed: raise ValueError('Chain contains unmatched method: '+mid)
        m = registry.methods[mid]
        if m['question_type'] != question['question_type']: raise ValueError('Mixed question types')
        if any(x in m['conflicts_with'] for x in ids): raise ValueError('Conflicting methods')
        steps.append(bind_contract({'method_id':mid,'role':m['primary_role'],'input': '题面与当前学生卡点' if not steps else f'{steps[-1]["method_id"]} 的 {steps[-1]["output"]}；必要时返回原文补足输入','output':m['output_type'],'action':m['core_action'],'stop_rule':m['stop_rule'],'state':'planned'}))
    return steps
