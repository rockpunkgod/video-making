"""Whole-question external review; never promote a supporting method to decider.

This validates supplied actions and exact evidence, not English truth, review
identity, learner outcomes or release eligibility. No answer key is consumed.
"""
from copy import deepcopy
from .evidence import check_span
from .execution import artifact_fingerprint

from video_contracts.question_verification import (
    MATERIAL_FIELDS, material_fingerprint, upstream_blocked, candidate_support,
    has_semantic_support, question_verification_answer_fields,
    validate_question_verification_projection as validate_structural_question_verification,
)


def verify_question(question, analysis, registry, graph):
    review = question.get('question_verification_review')
    if review is None:
        return None
    if question['question_type'] not in {'阅读理解', '七选五', '完形填空'}:
        raise ValueError('Whole-question option review requires a supported option question')
    if not question.get('passage') or not question['stem'] or not question.get('options'):
        raise ValueError('Whole-question review requires complete supplied material')
    if (review['question_id'] != question['question_id'] or
            review['task_type'] != question.get('task_type') or
            review['source_commit'] != registry.index['source_baseline']['commit'] or
            review['material_sha256'] != material_fingerprint(question)):
        raise ValueError('Whole-question review binding differs from original material or task')
    for key in ('review_id', 'reviewer', 'concrete_action', 'stop_rule_check'):
        if not review[key].strip():
            raise ValueError('Whole-question review requires concrete named review fields')
    checks = review['candidate_checks']
    ids = [c['candidate'] for c in checks]
    if len(ids) != len(set(ids)) or set(ids) != set(question['options']):
        raise ValueError('Whole-question review must check every candidate exactly once')
    executions = {x['execution_id']: x for x in analysis['execution_trace']}
    inputs = review['input_artifact_ids']
    if len(inputs) != len(set(inputs)):
        raise ValueError('Repeated whole-question input artifact')
    consumed = []
    for eid in inputs:
        x = executions.get(eid)
        if not x or x['state'] != 'produced':
            raise ValueError('Whole-question review needs actual produced earlier artifacts')
        consumed.append(x)
    if any(x['state']=='produced' and x['output'].get('scope')=='candidate_relation_check'
           and eid not in inputs for eid,x in executions.items()):
        raise ValueError('Whole-question review cannot bypass an existing candidate relation check')
    if not all(has_semantic_support(consumed,c) for c in question['options']):
        raise ValueError('Location, partition or remaining candidates cannot alone decide a question')
    sections = {sid for x in consumed for sid in registry.methods[x['method_id']]['section_ids']}
    if not set(review['source_section_ids']) <= sections:
        raise ValueError('Whole-question source must belong to its consumed current methods')
    if upstream_blocked(executions.values()):
        raise ValueError('Whole-question review cannot bypass a stopped or failed upstream check')
    active = review['review_status'] == 'reviewed' and not review['stop_applied']
    state = 'stopped' if review['stop_applied'] else 'reviewed' if active else 'unreviewed'
    scope_node=graph.node('question_scope','完整原题、任务与整题审阅载荷绑定',
        review_id=review['review_id'],material_sha256=review['material_sha256'],
        candidate_ids=sorted(question['options']),artifact_fingerprint=artifact_fingerprint(review))
    stem = graph.node('source_evidence', question['stem'], span={
        'field': 'stem', 'start': 0, 'end': len(question['stem']), 'quote': question['stem']})
    bindings = []
    for c in checks:
        if c['claim'] != question['options'][c['candidate']]:
            raise ValueError('Whole-question claim must preserve the complete option text')
        for key in ('decision_rule_check', 'backfill_check'):
            if not c[key].strip():
                raise ValueError('Candidate review requires concrete decision and backfill checks')
        spans = [check_span(question, s) for s in c['evidence']]
        if not any(s['field'] == 'passage' for s in spans):
            raise ValueError('Each candidate needs its own passage evidence, not option self-proof')
        own = candidate_support(consumed,c['candidate'])
        own_checks=[x['output'] for x in own if x['output'].get('scope')=='candidate_relation_check']
        if any(x['claim']!=c['claim'] for x in own_checks):
            raise ValueError('Whole-question relation check must bind its own complete claim')
        if c['effect']=='retain' and any(x['verdict']=='rejects' for x in own_checks):
            raise ValueError('Whole-question retain contradicts its own relation check')
        effect = c['effect'] if active and c['backfill_verdict']=='supports' and not any(x['verdict']=='unresolved' for x in own_checks) else 'undetermined'
        claim = graph.node('candidate_claim', c['claim'], candidate=c['candidate'])
        relation = graph.node('question_review', c['decision_rule_check'],
                              candidate=c['candidate'], review_id=review['review_id'],
                              reviewed=active, effect=effect)
        graph.edge(stem, relation, 'supports')
        graph.edge(scope_node, relation, 'supports')
        graph.edge(claim, relation, 'supports')
        for x in own:
            graph.edge(x['artifact_node_id'], relation, 'supports')
        evidence_ids = []
        for s in spans:
            nid = graph.node('source_evidence', s['quote'], span=s)
            evidence_ids.append(nid)
            graph.edge(nid, relation, 'supports')
        decision = verification = None
        if effect != 'undetermined':
            decision = graph.node('question_decision', effect, candidate=c['candidate'],
                                  review_id=review['review_id'], effect=effect, reviewed=True)
            graph.edge(relation, decision, 'eliminates' if effect == 'eliminate' else 'supports')
            verification = graph.node('question_verification', c['backfill_check'],
                                      candidate=c['candidate'], review_id=review['review_id'],
                                      effect=effect, reviewed=True)
            graph.edge(decision, verification, 'verifies')
        bindings.append({'candidate': c['candidate'], 'effect': effect,
                         'review_node_id': relation, 'decision_node_id': decision,
                         'verification_node_id': verification, 'evidence_ids': evidence_ids})
    return {'review': deepcopy(review), 'state': state, 'scope_node_id':scope_node,'candidate_bindings': bindings,
            'consumed_artifacts': [{'execution_id': x['execution_id'],
                'artifact_node_id': x['artifact_node_id'],
                'output_sha256': artifact_fingerprint(x['output'])} for x in consumed],
            'scope': 'external_whole_question_review_not_brand_method_credit'}


def apply_question_verification(analysis, verification):
    analysis['question_verification'] = verification
    if verification is None:
        return
    analysis.update(question_verification_answer_fields(analysis, verification))
    analysis['review_scope'] = 'external_whole_question_review'
    answer = analysis['answer']
    # Replace only this analyzer's earlier aggregation warnings; don't erase
    # source risks, stopped-action limitations or external review caveats.
    analysis['limitations'] = [s for s in analysis['limitations'] if not s.startswith((
        '仍有未完成决定性核验的候选：', '多个候选获得保留证据，', '缺少唯一候选自身的审阅证据；'))]
    analysis['limitations'].append('整题终判来自逐项外部审阅，不增加辅助方法定案信用，也不证明英语语义或学生实效。')
    if not answer:
        analysis['limitations'].append('整题终判尚未闭合；核清竞争候选、停止条件及回填，不由剩余项自动选。')
    analysis['next_action'] = ('整题候选和回填已逐项审阅；仍需独立语义验收。' if answer else
                               '先解决整题停止条件或待定候选，再逐项回填验证。')


def validate_question_verification_projection(analysis, registry=None):
    # Preserve the teaching-source check for upstream callers. Portable consumers
    # check only the supplied proof, never the current Registry or English truth.
    validate_structural_question_verification(analysis)
    report = analysis.get('question_verification')
    if report is not None and registry is not None:
        trace = {x['execution_id']: x for x in analysis['execution_trace']}
        review = report['review']
        sections = {sid for x in report['consumed_artifacts']
                    for sid in registry.methods[trace[x['execution_id']]['method_id']]['section_ids']}
        if (review['source_commit'] != registry.index['source_baseline']['commit']
                or not set(review['source_section_ids']) <= sections):
            raise ValueError('Whole-question projection differs from current course source')
