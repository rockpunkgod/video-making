"""Check supplied answers against their candidate and terminal proof projections.

Pure structural consistency only: no solver, Registry, teaching-source lookup,
reviewer authentication, English certification or release authorization.
"""


def validate_answer_projection(analysis, question=None):
    from .question_verification import validate_question_verification_projection, material_fingerprint
    validate_question_verification_projection(analysis)
    if question is not None:
        if (question['question_id'] != analysis['question_id']
                or question['question_type'] != analysis['question_type']):
            raise ValueError('Question/analysis identity mismatch')
        nodes = analysis['evidence_graph']['nodes']
        root = nodes[0] if nodes else {}
        candidates = sorted(set(question.get('options', {}))
                            | {r['candidate'] for r in question.get('relations', [])})
        if (root.get('material_sha256') != material_fingerprint(question)
                or root.get('candidate_ids', []) != candidates):
            raise ValueError('Answer projection scope differs from original question')
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
