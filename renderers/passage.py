"""Whole-passage projections preserve order and summarize by original numbers."""
import json
from core.registry import Registry,validate_schema
from core.passage_lesson import validate_passage_projection,evidence_driven_cloze


def render_passage(result,kind='structured',registry=None):
    r=registry or Registry(); validate_schema('passage-lesson-analysis',result); validate_passage_projection(result,r)
    if kind in {'structured','content-export'}:
        return json.dumps(result,ensure_ascii=False,indent=2)
    if kind not in {'student','legacy-wechat'}: raise ValueError('Unknown passage renderer')
    if result['scope']!='whole_passage_delivery':
        nums={x['analysis']['question_id']:str(x['number']) for x in result['questions']}
        gap='第'+'和第'.join(nums[qid] for qid in result['incomplete_question_ids'])+'题的完整动作、证据、候选比较或刹车讲解还没齐。' if result['incomplete_question_ids'] else '整篇材料完整性或讲解顺序还没有确认。'
        return '同学，我们来分析一下。'+gap+'先补齐这一处，暂不把单题消息拼成完整讲解，也不汇总整篇答案。'
    rows={x['analysis']['question_id']:x for x in result['questions']}; parts=['同学，我们来分析一下。']; grouped=False
    if result['question_type']=='阅读理解':
        if result['review']['reading_mode']=='central_task':
            has_main=any(x['analysis']['task_type'] in {'main_idea','purpose','title'} for x in result['questions'])
            has_vocab=any(x['analysis']['task_type'] in {'vocabulary','word_meaning'} for x in result['questions'])
            # Projection validation has already rejected unknown central tasks.
            has_detail=any(x['analysis']['task_type'] not in {'main_idea','purpose','title','vocabulary','word_meaning'} for x in result['questions'])
            if has_vocab and has_detail:
                parts.append('这里先把全文中心任务的题做掉，再回头做细节，猜词放最后。' if has_main else '这里没有全文中心任务题，就先核细节，猜词放最后。')
            elif has_vocab:
                parts.append('这里先核全文中心任务，再按原题号回文核词义。' if has_main else '这些题只问词义，按原题号回文核语境。')
            elif has_main and not has_detail:
                parts.append('这些题只问全文中心任务，按原题号回文核所问。')
            else:
                parts.append('这里先把全文中心任务的题做掉，再回头核其他题。' if has_main else '这里没有全文中心任务题，就按原题号核各题的局部任务。')
        else: parts.append('这里按原题号逐题回文找依据，不改成按难易挑题。')
    elif result['question_type']=='语法填空':
        has_no_hint=any(x['question']['given_word'] is None for x in result['questions'])
        has_hint=any(x['question']['given_word'] is not None for x in result['questions'])
        parts.append('先把无提示词的空过完，再回头做有提示词的，每一遍内部都按原空号。' if has_no_hint and has_hint else '这些空都没有提示词，按原空号逐空核功能。' if has_no_hint else '这些空都有提示词，按原空号逐空核功能，再核词形。')
    elif result['question_type']=='完形填空':
        parts.append('按当前证据推进，拿不准的先暂留，找到独立提示再回到本空核对。' if evidence_driven_cloze(r)
                     else '先按原空号逐空核证据，拿不准的先留着，走完首轮再回收。')
    if result['question_type']=='七选五':
        first=rows[result['review']['steps'][0]['question_id']]['analysis']; f=first['lesson_feedback']
        parts.append(next(s['text'] for s in f['review']['segments'] if s.get('method_id')=='F01' and s['function']=='action'))
        executions={x['execution_id']:x for x in first['execution_trace']}
        for eid in f['grouping_execution_ids']:
            output=executions[eid]['output']; label={'sentence':'句型','actor':'主角','time':'时间'}[output['axis']]
            parts.append('按'+label+'先分，'+'，'.join('和'.join(g['candidates'])+'属于'+g['label'].rstrip('。') for g in output['groups'])+'。分完回正文核内容，不把分组当答案。')
        grouped=True
    for step in result['review']['steps']:
        number=str(rows[step['question_id']]['number'])
        parts.append(('先看第'+number+'题。' if number not in step['transition'] else '')+step['transition'])
        if step['outcome']=='deferred': continue
        a=rows[step['question_id']]['analysis']; f=a['lesson_feedback']
        segments=f['review']['segments']
        # Keep every distinct reviewed order reason. Only an exact duplicate of
        # the first reading action may be displayed once rather than twice.
        duplicate_action=(result['question_type']=='阅读理解'
                          and result['review']['reading_mode']=='original_order'
                          and bool(segments) and segments[0]['function']=='action'
                          and step['transition']==segments[0]['text'])
        previous_spoken=duplicate_action
        for index,segment in enumerate(segments):
            if duplicate_action and index==0: continue
            if grouped and result['question_type']=='七选五' and segment.get('method_id')=='F01': continue
            # Segment boundaries are proof boundaries, not necessarily prose
            # boundaries. Rejoin a reading clause cut at a Chinese comma,
            # without altering either segment or merging different questions.
            if result['question_type']=='阅读理解' and previous_spoken and parts[-1].endswith('，'):
                parts[-1]+=segment['text']
            else:
                parts.append(segment['text'])
            previous_spoken=True
            if f['grouping_execution_ids'] and not grouped and segment['function']=='action' and segment.get('method_id')=='F01':
                executions={x['execution_id']:x for x in a['execution_trace']}
                for eid in f['grouping_execution_ids']:
                    output=executions[eid]['output']; label={'sentence':'句型','actor':'主角','time':'时间'}[output['axis']]
                    parts.append('按'+label+'先分，'+'，'.join('和'.join(g['candidates'])+'属于'+g['label'].rstrip('。') for g in output['groups'])+'。分完回正文核内容，不把分组当答案。')
                grouped=True
                previous_spoken=False
    parts.append('最后按原题号汇总，'+'，'.join('第'+str(x['number'])+'题'+('填' if result['question_type']=='语法填空' else '选')+x['answer'] for x in result['answer_summary'])+'。')
    return '\n\n'.join(parts)
