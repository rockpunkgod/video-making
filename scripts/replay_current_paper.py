"""Replay private paper material with explicitly reviewed current-version actions.

Unannotated structural control is NOT a learner Baseline. Unreviewed tasks
remain pending; this tool never upgrades a partial paper to semantic PASS.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from core.registry import Registry
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.real_cases import (private_root, private_file, material, digest, json_digest,
                             validate_request, artifact, pointer)
from scripts.ingest_exam_sources import freeze_json


def bind_questions(paper, reviewed_questions):
    """Drop historical assertions; retain original material and task scope."""
    if not isinstance(paper.get('questions'), list) or not paper.get('paper_id'):
        raise ValueError('Paper material requires paper_id and questions')
    questions = []
    for old in paper['questions']:
        question = deepcopy(material(old))
        if 'task_type' in old:
            question['task_type'] = old['task_type']
        questions.append(question)
    ids = [q['question_id'] for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source question identity')
    control = {'paper_id': paper['paper_id'], 'questions': deepcopy(questions)}
    selected = set()
    for current in reviewed_questions:
        qid = current['question_id']
        if qid in selected or qid not in ids:
            raise ValueError('Reviewed question is duplicate or outside this paper')
        index = ids.index(qid)
        if material(current) != material(questions[index]):
            raise ValueError('Reviewed action changes original paper question material')
        # Task type is a reviewed annotation, not original question material.
        # Older imports may label every reading question generically. Retaining
        # that label would prevent a genuine main-idea/paragraph task from using
        # its proper method. The caller validates the current independent review;
        # the report below exposes any annotation correction rather than hiding it.
        questions[index] = deepcopy(current)
        selected.add(qid)
    return control, {'paper_id': paper['paper_id'], 'questions': questions}


def read_reviewed_question(root, relative, registry):
    """Accept a distinct current review without inventing a pre-reveal Case.

    These checks bind asserted independent AI review to actual input, source and
    replay. They do not authenticate identities or prove English semantics.
    """
    _, raw = private_file(root, relative)
    review = json.loads(raw)
    if (review.get('stage') != 'post_reveal_current_source_independent_question_review'
            or review.get('review_scope') != 'private_current_question_review_only'
            or review.get('reviewer_kind') != 'AI'
            or review.get('source_commit') != registry.index['source_baseline']['commit']):
        raise ValueError('Explicit current-source private question review required')
    author, reviewer = review.get('author'), review.get('reviewer')
    if (not isinstance(author, str) or not author.strip()
            or not isinstance(reviewer, str) or not reviewer.strip() or author == reviewer
            or review.get('independent_from_author') is not True):
        raise ValueError('Question reviewer must be distinct from the action author')
    checks = review.get('checks', {})
    if any(checks.get(key) is not True for key in
           ['source_material', 'question_scope', 'trigger', 'action', 'evidence', 'role', 'stop']):
        raise ValueError('All current question review checks must be explicit')
    if not isinstance(review.get('review_notes'), str) or not review['review_notes'].strip():
        raise ValueError('Question review needs concrete independent notes')
    question = artifact(root, review['question_ref'])
    source_ref = review['source_question_ref']
    original = pointer(artifact(root, source_ref), source_ref['question_pointer'])
    if (material(question) != material(original)
            or question['question_id'] != review.get('question_id')):
        raise ValueError('Current question review changes original source material')
    authors = {x.get('reviewer') for field in ['action_executions', 'relations']
               for x in question.get(field, [])}
    # New annotation channels also carry actual authors. A reviewer cannot
    # self-certify their terminal/lesson simply by naming another action author.
    for field in ['grammar_hint_review','question_verification_review','lesson_review','writing_review']:
        if question.get(field) is not None:
            authors.add(question[field].get('reviewer'))
    if not authors or authors != {author}:
        raise ValueError('Question review author does not bind actual annotations')
    analysis = QuestionAnalyzer(registry).analyze(question)
    if (artifact(root, review['analysis_ref']) != analysis
            or review.get('analysis_sha256') != json_digest(analysis)
            or review.get('evidence_graph_sha256') != json_digest(analysis['evidence_graph'])
            or review.get('method_versions') != analysis['method_versions']
            or review.get('answer_closed') is not analysis['answer_verification']['closed']):
        raise ValueError('Current question review does not bind the actual replay')
    if not any(x['state'] in {'produced', 'stopped'} for x in analysis['execution_trace']):
        raise ValueError('Current question review requires actual typed method actions')
    return question, {'path': relative, 'sha256': digest(raw),
                      'question_id': question['question_id'],
                      'review_scope': review['review_scope'], 'reviewer': reviewer,
                      'question_ref': review['question_ref'], 'analysis_ref': review['analysis_ref']}


def replay(dataset, paper_path, reviewed_requests, output, reviewed_questions=()):
    root = private_root(dataset)
    registry = Registry()
    registry.validate()
    _, raw = private_file(root, paper_path)
    paper = json.loads(raw)
    reviewed = []
    bindings = []
    for relative in reviewed_requests:
        _, request_raw = private_file(root, relative)
        request = json.loads(request_raw)
        validate_request(root, request, registry)
        action = artifact(root, request['action'])
        if action.get('exam_id', action.get('paper_id')) != paper['paper_id']:
            raise ValueError('Current action belongs to a different paper')
        reviewed.append(action['question'])
        bindings.append({'path': relative, 'sha256': digest(request_raw),
                         'question_id': request['question_id'], 'method_id': request['method_id'],
                         'method_version': request['method_version'], 'action_ref': request['action'],
                         'case_review_ref': request['case_review']})
    question_reviews = []
    for relative in reviewed_questions:
        question, binding = read_reviewed_question(root, relative, registry)
        reviewed.append(question)
        question_reviews.append(binding)
    control, current = bind_questions(paper, reviewed)
    analyzer = PaperAnalyzer(QuestionAnalyzer(registry))
    control_analysis = analyzer.analyze(control)
    current_analysis = analyzer.analyze(current)
    selected = {q['question_id'] for q in reviewed}
    report = {
        'scope': 'current paper structural replay plus named private AI-reviewed actions; not whole-paper semantic acceptance',
        'source_commit': registry.index['source_baseline']['commit'],
        'paper_id': paper['paper_id'],
        'paper_material_ref': {'path': paper_path, 'sha256': digest(raw)},
        'reviewed_requests': bindings,
        'independent_question_reviews': question_reviews,
        'input_task_count': len(current['questions']),
        'replayed_task_count': len(current_analysis['questions']),
        'current_action_reviewed_task_count': len(selected),
        'pending_current_semantic_review_ids': [q['question_id'] for q in current['questions']
                                               if q['question_id'] not in selected],
        'task_coverage_scope': 'only supplied tasks; omitted listening or other sections are not certified',
        'structural_control_scope': 'unannotated same-material engine control; not learner Baseline',
        'task_type_annotation_changes': [
            {'question_id': before['question_id'],
             'previous_task_type': before.get('task_type'),
             'reviewed_task_type': after.get('task_type'),
             'scope': 'independently AI-reviewed annotation; original material unchanged'}
            for before, after in zip(control['questions'], current['questions'])
            if before.get('task_type') != after.get('task_type')],
        'original_material_unchanged': all(material(a) == material(b)
                                          for a, b in zip(control['questions'], current['questions'])),
        'per_question': [
            {'question_id': q['question_id'], 'question_type': q['question_type'],
             'current_action_independently_AI_reviewed': q['question_id'] in selected,
             'produced_executions': [x['execution_id'] for x in result['execution_trace']
                                     if x['state'] == 'produced'],
             'stopped_executions': [x['execution_id'] for x in result['execution_trace']
                                    if x['state'] == 'stopped'],
             'answer_closed': result['answer_verification']['closed']}
            for q, result in zip(current['questions'], current_analysis['questions'])],
        'whole_paper_semantic_acceptance': 'PARTIAL',
        'new_case_count': 0, 'new_unique_question_count': 0, 'new_blind_sample_count': 0,
        'learner_validation': 'pending_real_participant_validation',
        'method_promotion_applied': False,
    }
    destination = (root/output).resolve()
    if not destination.is_relative_to(root) or destination.exists():
        raise ValueError('Use a new private replay directory without overwriting history')
    destination.mkdir(parents=True)
    for name, value in [('control-input.json', control), ('current-input.json', current),
                        ('control-analysis.json', control_analysis), ('current-analysis.json', current_analysis),
                        ('report.json', report)]:
        freeze_json(destination/name, value)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--paper', required=True)
    parser.add_argument('--reviewed-request', action='append', default=[])
    parser.add_argument('--reviewed-question', action='append', default=[],
                        help='Independent current question review; no invented Case/Blind prerequisite')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = replay(args.dataset, args.paper, args.reviewed_request, args.output, args.reviewed_question)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {'per_question', 'pending_current_semantic_review_ids',
                                     'reviewed_requests', 'independent_question_reviews'}},
                     ensure_ascii=False, indent=2))
