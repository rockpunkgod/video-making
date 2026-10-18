"""Pure supplied whole-question proof checks; no Registry or teaching imports."""
from . import sha as artifact_fingerprint

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


def question_verification_answer_fields(analysis, verification):
    """Project only existing candidate effects; never infer an English answer."""
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
    return {'answer': answer, 'answer_confidence': 'medium' if answer else 'low',
            'content_eligible': bool(answer), 'status': 'reviewed' if answer else 'needs_evidence',
            'answer_verification': {'retained_candidates': sorted(retained),
        'eliminated_candidates': sorted(eliminated), 'unresolved_candidates': unresolved,
        'candidate_coverage_complete': not unresolved, 'unique_supported_candidate': len(retained) == 1,
        'closed': bool(answer)}}


def validate_question_verification_projection(analysis):
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
    expected = question_verification_answer_fields(analysis, report)
    if any(expected[key] != analysis[key] for key in ('answer', 'answer_verification', 'answer_confidence', 'content_eligible', 'status')):
        raise ValueError('Whole-question answer aggregation differs from its reviewed proof')
