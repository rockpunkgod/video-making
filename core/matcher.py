import re
from .evidence import check_span

MAIN_TASKS = {'main_idea','purpose','title','paragraph_main_idea'}
FULL_TEXT_METHODS = {'R06', 'R09'}

def full_text_only(mid, registry):
    # New R06 is a candidate diagnosis within the asked range. Preserve the
    # old full-text algorithm boundary when replaying its archived Registry.
    return mid in FULL_TEXT_METHODS and not (
        mid=='R06' and registry.methods[mid]['method_type']=='internal_rule')

def normalize_symptom(text):
    return re.sub(r'[\s，。？！、；：,.!?;:]+','',text).casefold()

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
        if full_text_only(mid,registry) and task=='paragraph_main_idea':
            raise ValueError('Full-text method cannot replace paragraph task')
        found[mid] = {'method_id':mid,'role':m['primary_role'],'confidence':'medium' if verified else 'low','reason':reason,'trigger_verified':verified}
    # Structural routing only. It suggests methods; it NEVER produces candidate truth.
    default = {'阅读理解':'R12','七选五':'F01','完形填空':'C01','语法填空':'G01','应用文':'A01','读后续写':'W01'}
    if qtype in default: add(default[qtype],'题型结构入口；适用关系仍待核')
    if qtype=='阅读理解' and task in MAIN_TASKS:
        found.pop('R12',None)
        if task=='paragraph_main_idea':
            add('R16','先圈题干指定段，再核该段对象与核心判断；不压全文')
        else:
            add('R09','主旨任务先生成全文骨架，不把取证入口当答案')
            add('R06','骨架形成后检查覆盖与错误关系')
    symptom_ids = set()
    for symptom in question.get('student_symptoms',[]):
        normalized = normalize_symptom(symptom)
        if not normalized: continue
        for m in registry.methods.values():
            if m['question_type'] != qtype: continue
            if m['method_id'] in {'R06','R09','R16'} and task not in MAIN_TASKS: continue
            if full_text_only(m['method_id'],registry) and task=='paragraph_main_idea': continue
            aliases = next((r['phrases'] for r in registry.symptom_cues if r['method_id']==m['method_id']),[])
            if any(normalized in normalize_symptom(s) or normalize_symptom(s) in normalized for s in m['student_symptoms']+aliases):
                add(m['method_id'],'学生自述卡点，仅作为可能入口')
                symptom_ids.add(m['method_id'])
    # A specific student obstacle takes priority over an unrelated generic entry.
    # Observations below can independently restore any reviewed structural method.
    if symptom_ids:
        if 'R06' in symptom_ids and task=='paragraph_main_idea' and not full_text_only('R06',registry):
            # A diagnosis needs an established paragraph core. Do not let a
            # generic "two summaries both look right" symptom skip that step.
            add('R16','先核所问段落核心，再诊断候选是否遗漏；不是全文框架')
            symptom_ids.add('R16')
        found = {mid:value for mid,value in found.items() if mid in symptom_ids}
    for observation in question.get('observations',[]):
        mid = observation['method_id']
        if mid not in registry.methods: raise ValueError('Unknown method id')
        for span in observation['evidence']: check_span(question,span)
        add(mid,'带可核跨度的外部触发观察；语义审阅不是统计校准',observation['reviewed'])
    return list(found.values())

def symptom_route(question_type,symptom,registry):
    q = {'question_id':'symptom-query','question_type':question_type,'stem':'','student_symptoms':[symptom]}
    # Main-idea route requires the caller to establish task scope separately.
    if any(x in symptom for x in ['主旨','主题','标题']):
        q['task_type']='paragraph_main_idea' if any(x in symptom for x in ['段落','这段','本段']) else 'main_idea'
    matches = match_methods(q,registry)
    return [{'method_id':x['method_id'],'role':x['role'],'action':registry.methods[x['method_id']]['core_action'],'stop_rule':registry.methods[x['method_id']]['stop_rule'],'confidence':x['confidence']} for x in matches]
