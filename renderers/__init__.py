"""Pure projections: never change answer facts or supply new teaching rules."""
import json
from core.registry import Registry, validate_schema
from core.evidence import validate_graph

def render(analysis,kind='structured',registry=None):
    validate_schema('question-analysis',analysis)
    validate_graph(analysis['evidence_graph'])
    r = registry or Registry()
    if kind=='structured': return json.dumps(analysis,ensure_ascii=False,indent=2)
    if kind=='content-export':
        assets = [{'method_id':x['method_id'],'method_version':r.methods[x['method_id']]['version'],'role':x['role'],'action':x['action'],'stop_rule':x['stop_rule'],'visual_formula':r.methods[x['method_id']]['visual_formula'],'compact':r.methods[x['method_id']]['compact'],'anti_rule':r.methods[x['method_id']]['anti_rule']} for x in analysis['method_chain']]
        return json.dumps({'export_schema_version':'1.1.0','question_id':analysis['question_id'],'answer':analysis['answer'],'answer_verification':analysis['answer_verification'],'evidence_graph':analysis['evidence_graph'],'methods':assets,'eligible_for_review':analysis['content_eligible'],'safe_for_release':'untested','limitations':analysis['limitations']},ensure_ascii=False,indent=2)
    if kind not in {'student','legacy-wechat'}: raise ValueError('Unknown renderer')
    parts = []
    if analysis['student_symptoms']: parts.append('先解决你卡住的这一处：'+analysis['student_symptoms'][0]+'。')
    for step in analysis['method_chain']:
        m = r.methods[step['method_id']]
        output_label={'locate':'证据位置','interpret':'语义或框架','reduce':'缩小后的范围','decide':'当前候选的判断','verify':'核验结果'}[step['output']]
        parts.append(m['brand_name']+'，'+step['action'].rstrip('。')+'。这一步得到的是'+output_label+'，仍要核题面证据。')
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
