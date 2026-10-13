"""Whole-question external review; never promote a supporting method to decider.

This validates supplied actions and exact evidence, not English truth, review
identity, learner outcomes or release eligibility. No answer key is consumed.
"""
from copy import deepcopy
from .evidence import check_span
from .execution import artifact_fingerprint

MATERIAL_FIELDS = ('question_id', 'question_type', 'stem', 'passage', 'options',
                   'given_word', 'student_text', 'continuation_starters',
                   'original_images', 'student_symptoms')


def material_fingerprint(question):
    return artifact_fingerprint({k: question[k] for k in MATERIAL_FIELDS if k in question})


def upstream_blocked(executions):
    return any(x['state']=='stopped' or (x['state']=='produced' and
        x['output']['kind']=='verification_result' and x['output'].get('scope')!='candidate_relation_check'
        and x['output']['verdict']!='supports')
        for x in executions)


def candidate_support(consumed, candidate):
    return [x for x in consumed if x['output'].get('scope')!='candidate_relation_check'
            or x['output'].get('candidate')==candidate]


def has_semantic_support(consumed, candidate):
    return any(x['output']['kind'] in {'interpretation','framework_card'} or
               (x['output']['kind']=='verification_result' and
                x['output'].get('scope')=='candidate_relation_check' and
                x['output']['candidate']==candidate) for x in consumed)


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
    retained = {c['candidate'] for c in analysis['candidate_analysis'] if c['effect'] == 'retain'}
    eliminated = {c['candidate'] for c in analysis['candidate_analysis'] if c['effect'] == 'eliminate'}
    for c in verification['candidate_bindings']:
        if c['effect'] == 'retain': retained.add(c['candidate'])
        if c['effect'] == 'eliminate': eliminated.add(c['candidate'])
    if retained & eliminated:
        raise ValueError('Whole-question review conflicts with a reviewed method decision')
    ids = {c['candidate'] for c in verification['candidate_bindings']}
    # An explicit whole-question backfill/Stop is a veto, not a chance to
    # resurrect a prior method answer when this new review is unresolved.
    held = {c['candidate'] for c in verification['candidate_bindings'] if c['effect']=='undetermined'}
    unresolved = sorted((ids - retained - eliminated) | held)
    ready = verification['state'] == 'reviewed'
    answer = next(iter(retained)) if ready and len(retained) == 1 and not unresolved else None
    analysis.update(answer=answer, answer_confidence='medium' if answer else 'low',
                    content_eligible=bool(answer), status='reviewed' if answer else 'needs_evidence',
                    review_scope='external_whole_question_review')
    analysis['answer_verification'] = {'retained_candidates': sorted(retained),
        'eliminated_candidates': sorted(eliminated), 'unresolved_candidates': unresolved,
        'candidate_coverage_complete': not unresolved, 'unique_supported_candidate': len(retained) == 1,
        'closed': bool(answer)}
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
    """Check projected review and proof identities before any renderer consumes it."""
    report = analysis.get('question_verification')
    if report is None:
        if (analysis.get('schema_version')=='1.8.0' or
                analysis.get('review_scope')=='external_whole_question_review' or
                any(n['type'].startswith('question_') and n['type']!='question_signal'
                    for n in analysis['evidence_graph']['nodes'])):
            raise ValueError('Whole-question proof cannot drop its projected review')
        return
    review = report['review']
    expected_state = ('stopped' if review['stop_applied'] else 'reviewed'
                      if review['review_status'] == 'reviewed' else 'unreviewed')
    if report['state'] != expected_state or review['question_id'] != analysis['question_id'] or review['task_type'] != analysis['task_type']:
        raise ValueError('Whole-question projected binding or state differs')
    nodes = {n['id']: n for n in analysis['evidence_graph']['nodes']}
    edges = {(e['from'], e['to']) for e in analysis['evidence_graph']['edges']}
    trace = {x['execution_id']: x for x in analysis['execution_trace']}
    if upstream_blocked(trace.values()):
        raise ValueError('Whole-question projection cannot bypass stopped or failed upstream checks')
    scope=nodes.get(report['scope_node_id'],{})
    if (scope.get('type')!='question_scope' or scope.get('review_id')!=review['review_id']
            or scope.get('material_sha256')!=review['material_sha256']
            or scope.get('artifact_fingerprint')!=artifact_fingerprint(review)
            or scope.get('candidate_ids')!=sorted(c['candidate'] for c in review['candidate_checks'])):
        raise ValueError('Whole-question scope, original material or review payload differs from graph')
    inputs = report['consumed_artifacts']
    if [x['execution_id'] for x in inputs] != review['input_artifact_ids']:
        raise ValueError('Whole-question consumed artifact identities differ')
    for item in inputs:
        x = trace.get(item['execution_id'])
        if (not x or x['state'] != 'produced' or x['artifact_node_id'] != item['artifact_node_id']
                or artifact_fingerprint(x['output']) != item['output_sha256']):
            raise ValueError('Whole-question consumed artifact projection differs')
    consumed=[trace[x['execution_id']] for x in inputs]
    if any(x['state']=='produced' and x['output'].get('scope')=='candidate_relation_check'
           and eid not in review['input_artifact_ids'] for eid,x in trace.items()):
        raise ValueError('Whole-question projection cannot bypass an existing candidate relation check')
    if not all(has_semantic_support(consumed,c['candidate']) for c in review['candidate_checks']):
        raise ValueError('Whole-question projection lacks produced interpretation')
    if registry is not None:
        sections={sid for x in inputs for sid in registry.methods[trace[x['execution_id']]['method_id']]['section_ids']}
        if review['source_commit']!=registry.index['source_baseline']['commit'] or not set(review['source_section_ids'])<=sections:
            raise ValueError('Whole-question projection differs from current course source')
    candidates=[c['candidate'] for c in review['candidate_checks']]
    if len(candidates)!=len(set(candidates)):
        raise ValueError('Repeated whole-question projected candidate')
    if len(report['candidate_bindings']) != len(review['candidate_checks']):
        raise ValueError('Whole-question projected candidate coverage differs')
    for c, b in zip(review['candidate_checks'], report['candidate_bindings']):
        own=candidate_support(consumed,c['candidate'])
        own_checks=[x['output'] for x in own if x['output'].get('scope')=='candidate_relation_check']
        if any(x['claim']!=c['claim'] for x in own_checks) or (c['effect']=='retain' and any(x['verdict']=='rejects' for x in own_checks)):
            raise ValueError('Whole-question projection contradicts its own relation check')
        effect = c['effect'] if expected_state == 'reviewed' and c['backfill_verdict']=='supports' and not any(x['verdict']=='unresolved' for x in own_checks) else 'undetermined'
        if b['candidate'] != c['candidate'] or b['effect'] != effect:
            raise ValueError('Whole-question projected candidate effect differs')
        n = nodes.get(b['review_node_id'], {})
        if (n.get('type') != 'question_review' or n.get('label') != c['decision_rule_check']
                or n.get('candidate') != c['candidate'] or n.get('review_id') != review['review_id']
                or n.get('effect') != effect or n.get('reviewed') != (expected_state == 'reviewed')):
            raise ValueError('Whole-question review node projection differs')
        incoming_artifacts={source for source,target in edges if target==n['id'] and nodes[source]['type']=='action_artifact'}
        if (scope['id'],n['id']) not in edges or incoming_artifacts!={x['artifact_node_id'] for x in own}:
            raise ValueError('Whole-question review dropped consumed proof edges')
        if not any(node['type']=='candidate_claim' and node.get('candidate')==c['candidate']
                   and node['label']==c['claim'] and (node['id'],n['id']) in edges for node in nodes.values()):
            raise ValueError('Whole-question projected complete claim differs')
        spans = [nodes.get(nid, {}).get('span') for nid in b['evidence_ids']]
        if spans != c['evidence'] or not all((nid, n['id']) in edges for nid in b['evidence_ids']):
            raise ValueError('Whole-question candidate lost its own evidence')
        if effect == 'undetermined':
            if b['decision_node_id'] is not None or b['verification_node_id'] is not None:
                raise ValueError('Undetermined whole-question candidate cannot carry a decision')
        else:
            for key, kind, label, parent in [
                ('decision_node_id', 'question_decision', effect, n['id']),
                ('verification_node_id', 'question_verification', c['backfill_check'], b['decision_node_id'])]:
                node = nodes.get(b[key], {})
                if (node.get('type') != kind or node.get('label') != label or
                        node.get('candidate') != c['candidate'] or node.get('effect') != effect or
                        node.get('review_id') != review['review_id'] or (parent, b[key]) not in edges):
                    raise ValueError('Whole-question conclusion projection differs')
    expected = deepcopy(analysis)
    apply_question_verification(expected, report)
    if any(expected[key] != analysis[key] for key in ('answer', 'answer_verification', 'answer_confidence', 'content_eligible', 'status')):
        raise ValueError('Whole-question answer aggregation differs from its reviewed proof')
