"""Pure projections: never change answer facts or supply new teaching rules."""
import json
from core.registry import Registry, validate_schema
from core.evidence import validate_graph
from core.execution import validate_execution_trace
from core.answer_projection import validate_answer_projection
from core.lesson_feedback import validate_lesson_projection
from core.writing_feedback import validate_writing_projection
from core.question_verification import validate_question_verification_projection

def render(analysis,kind='structured',registry=None):
    validate_schema('question-analysis',analysis)
    validate_graph(analysis['evidence_graph'])
    r = registry or Registry()
    validate_execution_trace(analysis,r)
    validate_lesson_projection(analysis,r)
    validate_writing_projection(analysis,r)
    validate_question_verification_projection(analysis,r)
    validate_answer_projection(analysis)
    if kind=='structured': return json.dumps(analysis,ensure_ascii=False,indent=2)
    if kind=='content-export':
        assets = [{'method_id':x['method_id'],'method_version':r.methods[x['method_id']]['version'],'role':x['role'],'action':x['action'],'stop_rule':x['stop_rule'],'visual_formula':r.methods[x['method_id']]['visual_formula'],'compact':r.methods[x['method_id']]['compact'],'anti_rule':r.methods[x['method_id']]['anti_rule']} for x in analysis['method_chain']]
        exported={'export_schema_version':'1.7.0','question_id':analysis['question_id'],'answer':analysis['answer'],'answer_verification':analysis['answer_verification'],'grammar_navigation':analysis['grammar_navigation'],'writing_feedback':analysis['writing_feedback'],'lesson_feedback':analysis['lesson_feedback'],'execution_trace':analysis['execution_trace'],'method_chain':analysis['method_chain'],'evidence_graph':analysis['evidence_graph'],'methods':assets,'eligible_for_review':analysis['content_eligible'],'safe_for_release':'untested','limitations':analysis['limitations']}
        if 'question_verification' in analysis:
            exported.update(export_schema_version='1.8.0',question_verification=analysis['question_verification'])
            if analysis['question_verification']['review']['schema_version']=='1.1.0':
                exported['export_schema_version']='1.9.0'
        return json.dumps(exported,ensure_ascii=False,indent=2)
    if kind not in {'student','legacy-wechat'}: raise ValueError('Unknown renderer')
    lesson=analysis['lesson_feedback']
    if lesson and lesson['scope']=='single_question_lesson':
        paragraphs=[]; grouped=False; executions={x['execution_id']:x for x in analysis['execution_trace']}
        for s in lesson['review']['segments']:
            paragraphs.append(s['text'])
            if s.get('method_id')=='F01' and s['function']=='action' and not grouped and lesson['grouping_execution_ids']:
                for eid in lesson['grouping_execution_ids']:
                    output=executions[eid]['output']; label={'sentence':'句型','actor':'主角','time':'时间'}[output['axis']]
                    paragraphs.append('按'+label+'先分，'+'，'.join('和'.join(g['candidates'])+'属于'+g['label'].rstrip('。') for g in output['groups'])+'。这一步只缩范围，分完再回正文核内容。')
                grouped=True
        body='\n\n'.join(paragraphs)
        ending='最后这一空填'+analysis['answer']+'。' if analysis['question_type']=='语法填空' else '最后这一题选'+analysis['answer']+'。'
        return '同学，我们来分析一下。\n\n'+body+'\n\n'+ending
    if analysis['question_type'] in {'阅读理解','七选五','完形填空','语法填空'}:
        return render_incomplete_objective(analysis)
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
    # A plan is not an executed lesson. Keep all submitted artifacts, but expose
    # only one pending entry and never invite continuation through a stop.
    blocked = any(x['state']=='stopped' or
                  (x['state']=='produced' and x['output']['kind']=='verification_result'
                   and x['output'].get('scope')!='candidate_relation_check'
                   and x['output']['verdict']!='supports')
                  for x in analysis['execution_trace'])
    pending = next((s for s in analysis['method_chain']
                    if s['state'] not in {'executed','stopped'}),None)
    for step in analysis['method_chain']:
        m = r.methods[step['method_id']]
        output_label={'locate':'证据位置','interpret':'语义或框架','reduce':'缩小后的范围','decide':'当前候选的判断','verify':'核验结果'}[step['output']]
        if step['state'] not in {'executed','stopped'}:
            if blocked or analysis['answer_verification']['closed'] or step is not pending:
                continue
            parts.append('先核对一个入口：'+m['brand_name']+'。这是方法建议，不代表题面触发已经验证。')
            if step['role']==m['primary_role']:
                card=m['four_step_card']
                parts.extend(['什么时候启动：'+card['start'],
                              '第一刀：'+card['first_cut'],
                              '怎么判：'+card['judge'],
                              '什么时候停：'+card['stop']])
            else:
                parts.extend(['第一刀：'+step['action'],'什么时候停：'+step['stop_rule']])
            parts.append('这一步只产出'+output_label+'，不能把计划当成已完成的动作或答案。')
            continue
        prefix='已提交动作记录：' if step['state']=='executed' else '此处已刹车：'
        parts.append(prefix+m['brand_name']+'。职责产物是'+output_label+'；记录来自外部审阅，不是自动语义认证。')
        for x in analysis['execution_trace']:
            if x['execution_id'] not in step['execution_ids']: continue
            if x['state']=='produced': parts.append('实际动作：'+x['concrete_action'].rstrip('。')+'。'+render_artifact(x['output']))
            elif x['state']=='stopped': parts.append('停止原因：'+x['stop_rule_check']+'。这一步没有继续产出。')
            else: parts.append('该动作尚未形成可继续使用的审阅产物。')
        parts.append(step['stop_rule'])
    if blocked:
        parts.append('先处理已停止或未通过核验的缺口，不继续套后续方法，不消费被扣留的产物。')
    elif pending is None and not analysis['answer_verification']['closed']:
        parts.append('下一步：'+analysis['next_action'])
    for c in analysis['candidate_analysis']:
        quotes = [n['label'] for n in analysis['evidence_graph']['nodes'] if n['id'] in c['evidence_ids']]
        effect={'retain':'有依据，暂时保留','eliminate':'依据判据排除','undetermined':'尚不能判断'}[c['effect']]
        if c['effect']=='undetermined' and analysis.get('question_verification'):
            effect='这条方法记录只作解释或辅助，整项判断见后面的整题核验'
        parts.append(c['candidate']+'：'+c['claim']+'。题面证据：'+'；'.join(quotes)+'。审阅结果：'+effect+'。')
    terminal=analysis.get('question_verification')
    if terminal:
        parts.append('整题核验（不是辅助方法直接定案）：'+terminal['review']['concrete_action'])
        for c,b in zip(terminal['review']['candidate_checks'],terminal['candidate_bindings']):
            effect={'retain':'保留','eliminate':'排除','undetermined':'待定'}[b['effect']]
            parts.append(c['candidate']+'：'+c['claim']+'。题面证据：'+'；'.join(s['quote'] for s in c['evidence'])+'。'+c['decision_rule_check']+'。回填：'+c['backfill_check']+'。整题审阅结果：'+effect+'。')
        parts.append('何时停：'+terminal['review']['stop_rule_check'])
    if analysis['answer'] is None:
        parts.append('现在先不报答案。'+analysis['limitations'][-1])
        if not blocked and analysis['answer_verification']['unresolved_candidates']:
            parts.append('下一步核验这些候选自己的证据：'+'、'.join(analysis['answer_verification']['unresolved_candidates'])+'。')
    else:
        parts.append('依据上述外部审阅记录，当前保留 '+analysis['answer']+'。这不是自动语义验证的结论。')
    if not parts: parts=['题面或证据不足，请补齐后再判断。']
    body = '\n\n'.join(parts)
    return ('同学你好，咱们先把下一步做清楚。\n\n'+body) if kind=='legacy-wechat' else body

def render_incomplete_objective(analysis):
    """Expose delivery status, never turn audit annotations into a lesson.

    Analysis and its closed answer remain available to machine consumers. A
    missing/partial/unreviewed lesson does not authorize copying free-form
    action, artifact, candidate or terminal-review text to a student.
    """
    trace=analysis['execution_trace']
    terminal=analysis.get('question_verification')
    stopped=any(x['state']=='stopped' for x in trace) or bool(terminal and terminal['state']=='stopped')
    failed=any(x['state']=='produced' and x['output']['kind']=='verification_result'
               and (x['output']['verdict']=='unresolved' or
                    (x['output'].get('scope')!='candidate_relation_check'
                     and x['output']['verdict']=='rejects')) for x in trace)
    if stopped:
        next_step='这一步需要先停下来，核清影响判断的依据后再继续，现在先不报答案。'
    elif failed:
        next_step='当前判断还没有通过核对，需要先回到题面核清依据，现在先不报答案。'
    elif not analysis['answer_verification']['closed']:
        next_step='决定答案的题面依据还没核清，现在先不报答案。'
    else:
        next_step='还需要补齐从题面依据到结论的讲解，当前不单独报答案。'
    return '同学，这题的逐步讲解还没齐，暂时不能给你完整解答。\n\n'+next_step

def render_artifact(output):
    kind=output['kind']
    if kind=='verification_result' and output.get('scope')=='candidate_relation_check':
        return '候选'+output['candidate']+'关系核查：'+output['relation_check']+'。回填：'+output['backfill_check']+'。'+{'supports':'该关系有支持','rejects':'该关系不成立','unresolved':'该关系仍未核清'}[output['verdict']]+'，不代表整题答案。'
    if kind=='located_evidence': return '定位到：'+'；'.join(s['quote'] for s in output['spans'])+'。定位仍不等于定案。'
    if kind=='interpretation': return '拆解结果：'+'；'.join(p['name']+'：'+p['value'] for p in output['parts'])+'。'
    if kind=='framework_card':
        labels={'object':'对象','core_judgement':'核心判断','text_task':'全文任务'}
        return '骨架产物：'+'；'.join(labels.get(p['name'],p['name'])+'：'+p['value'] for p in output['fields'])+'。'
    if kind=='candidate_partition': return '按'+output['axis']+'分组：'+'；'.join(g['label']+'：'+'、'.join(g['candidates']) for g in output['groups'])+'。分组不排除任何选项，也不定答案。'
    if kind=='text_groups': return '文本分组：'+'；'.join(g['label']+'：'+'、'.join(s['quote'] for s in g['spans']) for g in output['groups'])+'。'
    if kind=='route_selection':
        labels={'entry':'先判空位','hint':'核有无提示词','with_hint':'有提示词','without_hint':'无提示词','article':'限定/冠词','pronoun':'指代','preposition':'介词场景','clause':'连接/关系词','discourse':'句间关系','noun':'名词功能','modifier':'修饰功能','number':'数词','verb':'动词功能','predicate':'谓语','nonfinite':'非谓语'}
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
            adjustment=s.get('word_count_adjustment')
            if adjustment:
                before=adjustment['score_before']
                parts.append('外部审阅先定为'+s['band']+'，档内建议'+str(before['lower'])+'—'+str(before['upper'])+' / '+str(s['scale'])+'。核词数为'+str(adjustment['word_count'])+'，按该模块课程规范扣'+str(adjustment['deduction_points'])+'分后，建议'+str(s['lower'])+'—'+str(s['upper'])+' / '+str(s['scale'])+'。'+adjustment['rationale']+'。'+s['rationale']+' 词数与评分仍为外部审阅建议，不是程序自动评分认证。')
            else:
                parts.append('外部审阅建议：'+str(s['lower'])+'—'+str(s['upper'])+' / '+str(s['scale'])+'，'+s['band']+'。'+s['rationale']+' 这是外部建议，不是程序自动评分认证。')
            visual=review.get('handwriting_review')
            if visual and s['handwriting_applied']:
                parts.append('原稿中实际影响辨认的地方是'+'；'.join(r['observed']+'，'+r['communication_impact'] for r in visual['regions'])+'。'+visual['rationale']+'。书写处理依据原图的外部审阅，不按字迹美观扣分。')
            elif visual and visual['review_status']=='reviewed' and not visual['clear_image']:
                parts.append('原图清晰度不足，书写影响还不能确认；本次不依据书写扣分。')
    return '\n\n'.join(parts)
