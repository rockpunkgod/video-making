"""Source-bound whole-passage order checks; external semantic review only."""
from copy import deepcopy
from .registry import Registry,validate_schema
from .evidence import check_span
from .evidence import validate_graph
from .execution import validate_execution_trace
from .lesson_feedback import DELIVERY_PATH,check_spoken_text,validate_lesson_projection

MAIN={'main_idea','purpose','title'}
# Ordering buckets do not rename the question's reviewed task. Cause and
# study-finding questions follow the detail phase, not the vocabulary phase.
DETAIL={'detail','inference','paragraph_main_idea','cause','study_finding'}
VOCAB={'vocabulary','word_meaning'}


def expected_order(kind,items,mode):
    ids=sorted(items,key=lambda q:items[q]['number'])
    if kind=='阅读理解':
        if mode=='original_order': return ids
        tasks=[items[q]['question'].get('task_type','unknown') for q in ids]
        if any(t not in MAIN|DETAIL|VOCAB for t in tasks): raise ValueError('Central-task order requires explicit main/detail/vocabulary classification')
        return sorted(ids,key=lambda q:(0 if items[q]['question']['task_type'] in MAIN else 2 if items[q]['question']['task_type'] in VOCAB else 1,items[q]['number']))
    if kind=='语法填空':
        for qid in ids:
            q=items[qid]['question']
            if 'given_word' not in q or (q['given_word'] is not None and not q['given_word'].strip()): raise ValueError('Whole grammar order requires explicit hint presence for every blank')
        return [q for q in ids if items[q]['question']['given_word'] is None]+[q for q in ids if items[q]['question']['given_word'] is not None]
    return ids


def evidence_driven_cloze(registry):
    return registry.cloze_order_policy()=='evidence_driven_visits'


def validate_order(kind,items,review,analyses,registry=None):
    registry=registry or Registry()
    steps=review['steps']; ids=set(items); first=[s for s in steps if s['pass']==1]; second=[s for s in steps if s['pass']==2]
    flexible=kind=='完形填空' and evidence_driven_cloze(registry)
    final_states={}
    if kind!='阅读理解' and review['reading_mode'] is not None: raise ValueError('Do not move reading mode to another question type')
    if kind=='阅读理解' and review['reading_mode'] is None: raise ValueError('Reading order requires reviewed task mode, not passage letter')
    if {s['question_id'] for s in first}!=ids or len(first)!=len(ids): raise ValueError('First pass must visit every original question once')
    if not flexible and steps!=first+second: raise ValueError('Do not interleave second-pass recovery before first-pass completion')
    if kind!='完形填空':
        if second or any(s['outcome']=='deferred' for s in first): raise ValueError('Only cloze uses the two-pass defer/recover delivery')
        if kind!='七选五' and [s['question_id'] for s in first]!=expected_order(kind,items,review['reading_mode']):
            raise ValueError('Spoken order violates the frozen course task order')
    elif not flexible:
        order=expected_order(kind,items,None)
        if [s['question_id'] for s in first]!=order: raise ValueError('Cloze first pass follows original blank numbers')
        deferred={s['question_id'] for s in first if s['outcome']=='deferred'}
        if [s['question_id'] for s in second]!=[q for q in order if q in deferred] or any(s['outcome']!='solved' for s in second):
            raise ValueError('Cloze recovery must cover exactly deferred blanks in original order')
    else:
        for step in steps:
            qid=step['question_id']
            if step['pass']==1:
                if qid in final_states: raise ValueError('Duplicate first cloze visit')
            elif step['pass']==2:
                if final_states.get(qid)!='deferred':
                    raise ValueError('Cloze return requires an earlier unresolved own visit')
            else: raise ValueError('Cloze visit kind must be first visit or return')
            final_states[qid]=step['outcome']
    for step in steps:
        qid=step['question_id']
        if qid not in items: raise ValueError('Unknown passage delivery question')
        q=items[qid]['question']; spans=[check_span(q,s) for s in step['evidence']]
        if not any(s['field'] in {'passage','stem'} for s in spans): raise ValueError('Order transition requires current question material')
        check_spoken_text(step['transition'],spans)
        if not any(s['quote'] in step['transition'] for s in spans): raise ValueError('Order reason must expose its own current evidence, not just assert difficulty')
        if len(step['execution_ids'])!=len(set(step['execution_ids'])): raise ValueError('Duplicate order action reference')
        executions={x['execution_id']:x for x in analyses[qid]['execution_trace']}
        if any(eid not in executions for eid in step['execution_ids']): raise ValueError('Order references unknown question action')
        if step['outcome']=='deferred' and (not step['execution_ids'] or not any(executions[eid]['state']=='stopped' for eid in step['execution_ids'])):
            raise ValueError('Cloze first-pass uncertainty needs its own reviewed stopped action')
        if flexible and step['pass']==2 and step['outcome']=='solved' and (
                not step['execution_ids'] or not any(executions[eid]['state']=='produced' for eid in step['execution_ids'])):
            raise ValueError('Cloze recovery needs its own produced evidence action, not another answer')
    if kind=='七选五':
        partitions=[]
        for step in first:
            a=analyses[step['question_id']]; lesson=a['lesson_feedback']
            if lesson and lesson['scope']=='single_question_lesson':
                ex={x['execution_id']:x for x in a['execution_trace']}
                partitions.append([ex[eid]['output'] for eid in lesson['grouping_execution_ids']])
        if partitions and any(p!=partitions[0] for p in partitions): raise ValueError('Whole seven-five grouping cannot be rebuilt for each blank')
    return all(outcome=='solved' for outcome in final_states.values()) if flexible else None


class PassageLessonAnalyzer:
    def __init__(self,analyzer=None):
        if analyzer is None:
            from .analyzer import QuestionAnalyzer
            analyzer=QuestionAnalyzer()
        self.analyzer=analyzer

    def analyze(self,packet):
        validate_schema('passage-lesson-input',packet)
        p=deepcopy(packet); items={}; nums=set(); kind=p['question_type']; r=self.analyzer.registry
        for item in p['questions']:
            q=item['question']; qid=q['question_id']
            if qid in items or item['number'] in nums: raise ValueError('Duplicate original question id/number')
            if q['question_type']!=kind: raise ValueError('One passage lesson cannot mix question types')
            if 'passage' in q and q['passage']!=p['passage']: raise ValueError('Passage lessons must share the supplied original passage')
            q['passage']=p['passage']; items[qid]=item; nums.add(item['number'])
        review=p['review']; source_ids=review['source_section_ids']
        if len(source_ids)!=len(set(source_ids)) or any(s not in r.sources['sections'] for s in source_ids): raise ValueError('Unknown/duplicate delivery contract source')
        if not any(r.sources['sections'][s]['path']==DELIVERY_PATH and r.sources['sections'][s]['heading']=='做题顺序' for s in source_ids):
            raise ValueError('Whole passage delivery must bind the frozen doing-order section')
        if kind=='七选五':
            if any(item['question'].get('options')!=next(iter(items.values()))['question'].get('options') for item in items.values()):
                raise ValueError('Seven-five blanks must share the same full candidate set')
        analyses={qid:self.analyzer.analyze(item['question']) for qid,item in items.items()}
        order_complete=validate_order(kind,items,review,analyses,r)
        complete=order_complete is not False and p['material_complete'] and review['review_status']=='reviewed' and all(a['lesson_feedback'] and a['lesson_feedback']['scope']=='single_question_lesson' for a in analyses.values())
        result={'schema_version':'1.0.0','lesson_id':p['lesson_id'],'question_type':kind,'questions':[{'number':items[qid]['number'],'question':items[qid]['question'],'analysis':analyses[qid]} for qid in sorted(items,key=lambda q:items[q]['number'])],
                'scope':'whole_passage_delivery' if complete else 'partial_delivery','review':review if complete else {**review,'steps':[]},'answer_summary':[{'number':items[qid]['number'],'answer':analyses[qid]['answer']} for qid in sorted(items,key=lambda q:items[q]['number'])] if complete else [],
                'material_complete':p['material_complete'],'limitations':['篇级顺序、材料完整性与自由文字均为外部审阅声明；结构、跨度和动作检查不能认证英语语义、真实采集或旧宿主表现。','整篇一次交付；完整口播或任何题的闭合不足时扣留整篇消息及答案串，单题结构分析仍可检查。']}
        result['incomplete_question_ids']=[qid for qid,a in analyses.items() if not a['lesson_feedback'] or a['lesson_feedback']['scope']!='single_question_lesson']
        validate_schema('passage-lesson-analysis',result); validate_passage_projection(result,r)
        return result


def validate_passage_projection(result,registry):
    rows=result['questions']; analyses={x['analysis']['question_id']:x['analysis'] for x in rows}
    if len(analyses)!=len(rows) or len({x['number'] for x in rows})!=len(rows): raise ValueError('Duplicate projected passage questions')
    source_ids=result['review']['source_section_ids']
    if len(source_ids)!=len(set(source_ids)) or any(s not in registry.sources['sections'] for s in source_ids) or not any(registry.sources['sections'][s]['path']==DELIVERY_PATH and registry.sources['sections'][s]['heading']=='做题顺序' for s in source_ids):
        raise ValueError('Projected passage lost the frozen doing-order source')
    if len({x['question'].get('passage') for x in rows})!=1: raise ValueError('Projected questions no longer share their original passage')
    items={x['question']['question_id']:x for x in rows}
    for row in rows:
        q=row['question']; a=row['analysis']
        if q['question_id']!=a['question_id'] or q['question_type']!=a['question_type'] or q.get('task_type','unknown')!=a['task_type']:
            raise ValueError('Projected original material differs from question analysis metadata')
        validate_graph(a['evidence_graph'],q); validate_execution_trace(a,registry); validate_lesson_projection(a,registry)
    if set(result['incomplete_question_ids'])!={qid for qid,a in analyses.items() if not a['lesson_feedback'] or a['lesson_feedback']['scope']!='single_question_lesson'}:
        raise ValueError('Projected incomplete-question diagnostic was changed')
    if result['scope']!='whole_passage_delivery':
        if result['review']['steps'] or result['answer_summary']: raise ValueError('Partial passage must withhold whole-message delivery')
        return
    if not result['material_complete'] or result['review']['review_status']!='reviewed': raise ValueError('Whole passage was not externally reviewed as complete')
    for a in analyses.values():
        validate_lesson_projection(a,registry)
        if not a['lesson_feedback'] or a['lesson_feedback']['scope']!='single_question_lesson' or a['question_type']!=result['question_type']: raise ValueError('Whole message requires every own single-question closure')
    expected=[{'number':x['number'],'answer':x['analysis']['answer']} for x in sorted(rows,key=lambda x:x['number'])]
    if result['answer_summary']!=expected: raise ValueError('Passage answer summary differs from core original-number closure')
    if validate_order(result['question_type'],items,result['review'],analyses,registry) is False:
        raise ValueError('Whole cloze delivery still has unresolved visits')
