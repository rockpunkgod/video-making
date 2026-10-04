import re
from .evidence import check_span

MAIN_TASKS = {'main_idea','purpose','title','paragraph_main_idea'}

def match_methods(question,registry):
    qtype = question['question_type']
    task = question.get('task_type','unknown')
    found = {}
    def add(mid, reason, verified=False):
        m = registry.methods[mid]
        if m['question_type'] != qtype:
            raise ValueError('Cross-type method invocation: '+mid)
        if mid in {'R06','R09','R16'} and task not in MAIN_TASKS:
            raise ValueError('Main idea method used on a different task')
        if mid=='R06' and task=='paragraph_main_idea':
            raise ValueError('Full-text coverage cannot replace paragraph task')
        found[mid] = {'method_id':mid,'role':m['primary_role'],'confidence':'medium' if verified else 'low','reason':reason,'trigger_verified':verified}
    # Structural routing only. It suggests methods; it NEVER produces candidate truth.
    default = {'阅读理解':'R12','七选五':'F01','完形填空':'C01','语法填空':'G01','应用文':'A01','读后续写':'W01'}
    if qtype in default: add(default[qtype],'题型结构入口；适用关系仍待核')
    if qtype=='阅读理解' and task in MAIN_TASKS:
        found.pop('R12',None)
        add('R09','主旨任务先生成全文骨架，不把取证入口当答案')
        if task!='paragraph_main_idea': add('R06','骨架形成后检查覆盖与错误关系')
    for symptom in question.get('student_symptoms',[]):
        for m in registry.methods.values():
            if m['question_type'] != qtype: continue
            if m['method_id'] in {'R06','R09','R16'} and task not in MAIN_TASKS: continue
            if m['method_id']=='R06' and task=='paragraph_main_idea': continue
            if symptom in m['student_symptoms'] or any(symptom in s or s in symptom for s in m['student_symptoms']):
                add(m['method_id'],'学生自述卡点，仅作为可能入口')
    for observation in question.get('observations',[]):
        mid = observation['method_id']
        if mid not in registry.methods: raise ValueError('Unknown method id')
        for span in observation['evidence']: check_span(question,span)
        add(mid,'带可核跨度的外部触发观察；语义审阅不是统计校准',observation['reviewed'])
    return list(found.values())

def symptom_route(question_type,symptom,registry):
    q = {'question_id':'symptom-query','question_type':question_type,'stem':'','student_symptoms':[symptom]}
    # Main-idea route requires the caller to establish task scope separately.
    if any(x in symptom for x in ['主旨','主题','标题']): q['task_type']='main_idea'
    matches = match_methods(q,registry)
    return [{'method_id':x['method_id'],'role':x['role'],'action':registry.methods[x['method_id']]['core_action'],'stop_rule':registry.methods[x['method_id']]['stop_rule'],'confidence':x['confidence']} for x in matches]
