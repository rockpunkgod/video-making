"""Pure checks of supplied answer proofs; no Registry, solver or course imports.

The producer and portable consumer share these checks. They establish structural
consistency, not English truth, reviewer identity, or release permission.
"""
from copy import deepcopy
import hashlib
import json


def artifact_fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


MATERIAL_FIELDS = ('question_id', 'question_type', 'stem', 'passage', 'options',
                   'given_word', 'student_text', 'continuation_starters',
                   'original_images', 'student_symptoms')


def material_fingerprint(question):
    return artifact_fingerprint({k: question[k] for k in MATERIAL_FIELDS if k in question})


def validate_frozen_answer(question, analysis):
    """Check supplied proofs against their original question, without solving."""
    if any(question[key] != analysis[key] for key in ('question_id', 'question_type')):
        raise ValueError('Frozen question/answer identity differs')
    if question['question_type'] not in {'应用文', '读后续写'}:
        nodes = analysis['evidence_graph']['nodes']
        root = nodes[0] if nodes else {}
        candidates = sorted(set(question.get('options', {})) |
                            {r['candidate'] for r in question.get('relations', [])})
        if (root.get('material_sha256') != material_fingerprint(question)
                or root.get('candidate_ids') != candidates):
            raise ValueError('Frozen answer scope differs from original material/candidates')
    report = analysis.get('question_verification')
    if report is not None:
        review = report['review']
        if (review != question.get('question_verification_review')
                or review['material_sha256'] != material_fingerprint(question)
                or {c['candidate']: c['claim'] for c in review['candidate_checks']}
                   != question.get('options', {})):
            raise ValueError('Frozen terminal review differs from original complete options')

    def check_spans(value):
        if isinstance(value, dict):
            if {'field', 'start', 'end', 'quote'} <= value.keys():
                field = value['field']
                if field.startswith('option:'):
                    raw = question.get('options', {}).get(field.split(':', 1)[1])
                elif field.startswith('continuation_starters:'):
                    try:
                        raw = question.get('continuation_starters', [])[int(field.split(':', 1)[1])]
                    except (ValueError, IndexError):
                        raw = None
                else:
                    raw = question.get(field) if field in {'passage', 'stem', 'student_text'} else None
                if (not isinstance(raw, str)
                        or not 0 <= value['start'] < value['end'] <= len(raw)
                        or raw[value['start']:value['end']] != value['quote']):
                    raise ValueError('Frozen proof quote differs from original source')
            for child in value.values():
                check_spans(child)
        elif isinstance(value, list):
            for child in value:
                check_spans(child)

    check_spans(analysis)
    validate_question_verification_projection(analysis)
    validate_answer_projection(analysis)


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


def validate_answer_projection(analysis):
    if analysis['question_type'] in {'应用文', '读后续写'}:
        # Writing relation nodes certify feedback, not objective option effects.
        # validate_writing_projection checks their complete own proof paths.
        if (analysis['answer'] is not None or analysis['answer_verification']['closed']
                or analysis['answer_confidence'] != 'low' or analysis['content_eligible']):
            raise ValueError('Writing feedback cannot project an objective answer')
        return
    nodes = analysis['evidence_graph']['nodes']
    root = nodes[0] if nodes else {}
    if (root.get('type') != 'question_signal' or root.get('method_id')
            or root.get('reviewed') or not root.get('material_sha256')):
        raise ValueError('Answer projection requires original question candidate scope')
    known_candidates = set(root.get('candidate_ids',[]))
    edges = {(e['from'], e['to']) for e in analysis['evidence_graph']['edges']}
    # Spoken lesson relations have no candidate; their payload is checked by
    # validate_lesson_projection and must not masquerade as option decisions.
    relations = [n for n in nodes if n['type'] == 'relation' and 'candidate' in n]
    rows = analysis['candidate_analysis']
    if len(rows) != len(relations):
        raise ValueError('Candidate projection dropped or added a relation')
    retained, eliminated = set(), set()
    for row, relation in zip(rows, relations):
        candidate, mid = relation['candidate'], relation['method_id']
        claims = [n for n in nodes if n['type'] == 'candidate_claim'
                  and (n['id'], relation['id']) in edges]
        evidence = [n['id'] for n in nodes if n['type'] == 'source_evidence'
                    and (n['id'], relation['id']) in edges]
        actions = [n for n in nodes if n['type'] == 'method_action'
                   and (relation['id'], n['id']) in edges
                   and not n.get('execution_id')]
        decisions = [n for n in nodes if n['type'] == 'decision'
                     and any((a['id'], n['id']) in edges for a in actions)]
        if len(claims) != 1 or len(actions) != 1 or len(decisions) > 1:
            raise ValueError('Candidate projection has ambiguous relation proof')
        effect = 'undetermined'
        if decisions:
            decision = decisions[0]
            effect = decision['label'].split(': ', 1)[0]
            if (effect not in {'retain', 'eliminate'} or not relation.get('reviewed')
                    or decision.get('candidate') != candidate
                    or decision.get('method_id') != mid):
                raise ValueError('Candidate projection decision differs from own relation')
            (retained if effect == 'retain' else eliminated).add(candidate)
        if (row['candidate'] != candidate or row['method_id'] != mid
                or claims[0].get('candidate') != candidate
                or row['claim'] != claims[0]['label']
                or row['effect'] != effect or row['evidence_ids'] != evidence):
            raise ValueError('Candidate projection differs from relation proof')
        if candidate not in known_candidates:
            raise ValueError('Candidate projection exceeds original question scope')
    if retained & eliminated:
        raise ValueError('Candidate projection contains contradictory decisions')
    for execution in analysis['execution_trace']:
        output = execution['output']
        if execution['state'] != 'produced' or output['kind'] != 'candidate_decision':
            continue
        index = output['relation_index']
        if index < 0 or index >= len(rows):
            raise ValueError('Typed decision projection has no own relation')
        row = rows[index]
        relation = relations[index]
        if (row['candidate'] != output['candidate'] or row['effect'] != output['effect']
                or row['method_id'] != execution['method_id']
                or (relation['id'], execution['action_node_id']) not in edges):
            raise ValueError('Typed decision projection differs from relation proof')
    if analysis.get('question_verification') is not None:
        # Its validator computes the terminal result from its complete review,
        # not from auxiliary/legacy candidate rows.
        report = analysis['question_verification']
        scope = next((n for n in nodes if n['id'] == report['scope_node_id']), {})
        if (set(scope.get('candidate_ids',[])) != known_candidates
                or scope.get('material_sha256') != root['material_sha256']):
            raise ValueError('Whole-question projection differs from original question scope')
        return
    verification = analysis['answer_verification']
    if (verification['retained_candidates'] != sorted(retained)
            or verification['eliminated_candidates'] != sorted(eliminated)):
        raise ValueError('Answer projection candidate summary differs from proof')
    unresolved = verification['unresolved_candidates']
    if (len(unresolved) != len(set(unresolved)) or unresolved != sorted(unresolved)
            or set(unresolved) & (retained | eliminated)
            or set(unresolved) != known_candidates - retained - eliminated
            or verification['candidate_coverage_complete'] != (not unresolved)
            or verification['unique_supported_candidate'] != (len(retained) == 1)):
        raise ValueError('Answer projection coverage differs from candidate proof')
    blocked = any(x['state'] == 'produced' and x['output']['kind'] == 'verification_result'
                  and ((x['output'].get('scope') != 'candidate_relation_check'
                        and x['output']['verdict'] != 'supports')
                       or (x['output'].get('scope') == 'candidate_relation_check'
                           and (x['output']['verdict'] == 'unresolved'
                                or (x['output']['verdict'] == 'rejects'
                                    and x['output']['candidate'] in retained))))
                  for x in analysis['execution_trace'])
    answer = (next(iter(retained)) if len(retained) == 1 and not unresolved
              and not blocked and analysis['question_type'] not in {'应用文', '读后续写'} else None)
    if (analysis['answer'] != answer or verification['closed'] != bool(answer)
            or analysis['answer_confidence'] != ('medium' if answer else 'low')
            or analysis['content_eligible'] != bool(answer)):
        raise ValueError('Answer projection differs from reviewed decision proof')


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
