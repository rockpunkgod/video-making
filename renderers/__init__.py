"""Pure projections: never change answer facts or supply new teaching rules."""
import json
from core.registry import Registry, validate_schema
from core.evidence import validate_graph
from core.execution import validate_execution_trace
from core.lesson_feedback import validate_lesson_projection

def render(analysis,kind='structured',registry=None):
    validate_schema('question-analysis',analysis)
    validate_graph(analysis['evidence_graph'])
    r = registry or Registry()
    validate_execution_trace(analysis,r)
    validate_lesson_projection(analysis,r)
    if kind=='structured': return json.dumps(analysis,ensure_ascii=False,indent=2)
    if kind=='content-export':
        assets = [{'method_id':x['method_id'],'method_version':r.methods[x['method_id']]['version'],'role':x['role'],'action':x['action'],'stop_rule':x['stop_rule'],'visual_formula':r.methods[x['method_id']]['visual_formula'],'compact':r.methods[x['method_id']]['compact'],'anti_rule':r.methods[x['method_id']]['anti_rule']} for x in analysis['method_chain']]
        return json.dumps({'export_schema_version':'1.5.0','question_id':analysis['question_id'],'answer':analysis['answer'],'answer_verification':analysis['answer_verification'],'grammar_navigation':analysis['grammar_navigation'],'writing_feedback':analysis['writing_feedback'],'lesson_feedback':analysis['lesson_feedback'],'execution_trace':analysis['execution_trace'],'method_chain':analysis['method_chain'],'evidence_graph':analysis['evidence_graph'],'methods':assets,'eligible_for_review':analysis['content_eligible'],'safe_for_release':'untested','limitations':analysis['limitations']},ensure_ascii=False,indent=2)
    if kind not in {'student','legacy-wechat'}: raise ValueError('Unknown renderer')
    lesson=analysis['lesson_feedback']
    if lesson and lesson['scope']=='single_question_lesson':
        paragraphs=[]; grouped=False; executions={x['execution_id']:x for x in analysis['execution_trace']}
        for s in lesson['review']['segments']:
            paragraphs.append(s['text'])
            if s['method_id']=='F01' and s['function']=='action' and not grouped and lesson['grouping_execution_ids']:
                for eid in lesson['grouping_execution_ids']:
                    output=executions[eid]['output']; label={'sentence':'句型','actor':'主角','time':'时间'}[output['axis']]
                    paragraphs.append('按'+label+'先分，'+'，'.join('和'.join(g['candidates'])+'属于'+g['label'].rstrip('。') for g in output['groups'])+'。这一步只缩范围，分完再回正文核内容。')
                grouped=True
        body='\n\n'.join(paragraphs)
        ending='最后这一空填'+analysis['answer']+'。' if analysis['question_type']=='语法填空' else '最后这一题选'+analysis['answer']+'。'
        return '同学，我们来分析一下。\n\n'+body+'\n\n'+ending
    feedback=analysis['writing_feedback']
    if feedback and feedback['scope']!='unreviewed':
        body=render_writing(feedback)
        if not feedback['review']['sections'] and not feedback['review']['corrections']:
            body+='\n\n请补题目和学生原稿后再做完整反馈。' if analysis['question_type']=='应用文' else '\n\n请补原文、两段开头语和学生自写部分后再做完整反馈。'
        return ('同学你好，咱们先看任务和框架，再逐处看语言。\n\n'+body) if kind=='legacy-wechat' else body
    parts = []
    nav=analysis['grammar_navigation']
    if nav:
        if nav['status']=='needs_hint_confirmation': parts.append('先确认这个空有无提示词，不能跳过空位功能直接变词。')
        elif nav['status']=='needs_function_confirmation': parts.append('有提示词，先圈空位所需成分或词性；提示词原词性不是答案词性。' if nav['hint_branch']=='with_hint' else '无提示词，先圈空位的限定、介词、指代、连接或句间逻辑功能；不把候选锁死为四类。')
        else: parts.append('按题面触发审阅记录进入知识节点；树只导航，词形仍须独立核验。')
    if analysis['student_symptoms']: parts.append('先解决你卡住的这一处：'+analysis['student_symptoms'][0]+'。')
    for step in analysis['method_chain']:
        m = r.methods[step['method_id']]
        output_label={'locate':'证据位置','interpret':'语义或框架','reduce':'缩小后的范围','decide':'当前候选的判断','verify':'核验结果'}[step['output']]
        prefix='已提交动作记录：' if step['state']=='executed' else '此处已刹车：' if step['state']=='stopped' else '下一步计划：'
        parts.append(prefix+m['brand_name']+'，'+step['action'].rstrip('。')+'。职责产物是'+output_label+'；计划或关系审阅不等于动作已经完成。')
        for x in analysis['execution_trace']:
            if x['execution_id'] not in step['execution_ids']: continue
            if x['state']=='produced': parts.append('实际动作：'+x['concrete_action'].rstrip('。')+'。'+render_artifact(x['output']))
            elif x['state']=='stopped': parts.append('停止原因：'+x['stop_rule_check']+'。这一步没有继续产出。')
            else: parts.append('该动作尚未形成可继续使用的审阅产物。')
        parts.append(step['stop_rule'])
    for c in analysis['candidate_analysis']:
        quotes = [n['label'] for n in analysis['evidence_graph']['nodes'] if n['id'] in c['evidence_ids']]
        effect={'retain':'有依据，暂时保留','eliminate':'依据判据排除','undetermined':'尚不能判断'}[c['effect']]
        parts.append(c['candidate']+'：'+c['claim']+'。题面证据：'+'；'.join(quotes)+'。审阅结果：'+effect+'。')
    if analysis['answer'] is None:
        parts.append('现在先不报答案。'+analysis['limitations'][-1])
        if analysis['answer_verification']['unresolved_candidates']:
            parts.append('下一步核验这些候选自己的证据：'+'、'.join(analysis['answer_verification']['unresolved_candidates'])+'。')
    else:
        parts.append('依据上述外部审阅记录，当前保留 '+analysis['answer']+'。这不是自动语义验证的结论。')
    if not parts: parts=['题面或证据不足，请补齐后再判断。']
    body = '\n\n'.join(parts)
    return ('同学你好，咱们先把下一步做清楚。\n\n'+body) if kind=='legacy-wechat' else body

def render_artifact(output):
    kind=output['kind']
    if kind=='located_evidence': return '定位到：'+'；'.join(s['quote'] for s in output['spans'])+'。定位仍不等于定案。'
    if kind=='interpretation': return '拆解结果：'+'；'.join(p['name']+'：'+p['value'] for p in output['parts'])+'。'
    if kind=='framework_card':
        labels={'object':'对象','core_judgement':'核心判断','text_task':'全文任务'}
        return '骨架产物：'+'；'.join(labels.get(p['name'],p['name'])+'：'+p['value'] for p in output['fields'])+'。'
    if kind=='candidate_partition': return '按'+output['axis']+'分组：'+'；'.join(g['label']+'：'+'、'.join(g['candidates']) for g in output['groups'])+'。分组不排除任何选项，也不定答案。'
    if kind=='text_groups': return '文本分组：'+'；'.join(g['label']+'：'+'、'.join(s['quote'] for s in g['spans']) for g in output['groups'])+'。'
    if kind=='route_selection':
        labels={'entry':'先判空位','hint':'核有无提示词','with_hint':'有提示词','without_hint':'无提示词','article':'限定/冠词','pronoun':'指代','preposition':'介词场景','clause':'从句缺口','discourse':'句间关系','noun':'名词功能','modifier':'修饰功能','number':'数词','verb':'动词功能','predicate':'谓语','nonfinite':'非谓语'}
        return '待调用知识节点：'+' → '.join(labels.get(n,n) for n in output['node_ids'])+'。节点不是词形答案。'
    if kind=='candidate_decision': return '候选'+output['candidate']+'：'+{'retain':'保留','eliminate':'排除','undetermined':'待定'}[output['effect']]+'；依赖独立关系审阅。'
    return '回填核验：'+{'supports':'支持当前候选判断','rejects':'不支持当前候选判断','unresolved':'尚未闭合'}[output['verdict']]+'。'

def render_writing(feedback):
    """Original delivery order, natural paragraphs, no limit on corrections."""
    review=feedback['review']; sections={s['key']:s for s in review['sections']}
    parts=[]
    if feedback['scope']=='partial_feedback': parts.append('材料或审阅覆盖还不完整，下面只反馈目前有依据的部分，暂不作完整评分。')
    for key in feedback['section_order']:
        if key=='corrections':
            for c in review['corrections']:
                prefix='这一处是可选润色，不算确定错误。' if c['kind']=='optional' else '这里有一处需要改。'
                parts.append(prefix+'原文这里写的是 '+c['original']['quote']+' 建议改为 '+c['replacement']+'。'+c['reason'])
        elif key in sections:
            parts.append(sections[key]['text'])
        if key=='overall' and review['proposed_score'] is not None:
            s=review['proposed_score']
            parts.append('外部审阅建议：'+str(s['lower'])+'—'+str(s['upper'])+' / '+str(s['scale'])+'，'+s['band']+'。'+s['rationale']+' 这是外部建议，不是程序自动评分认证。')
    return '\n\n'.join(parts)
