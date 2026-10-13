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
from core.real_cases import private_root, private_file, material, digest, validate_request, artifact
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
        if current.get('task_type') != questions[index].get('task_type'):
            raise ValueError('Reviewed action changes the source task scope')
        questions[index] = deepcopy(current)
        selected.add(qid)
    return control, {'paper_id': paper['paper_id'], 'questions': questions}


def replay(dataset, paper_path, reviewed_requests, output):
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
        'input_task_count': len(current['questions']),
        'replayed_task_count': len(current_analysis['questions']),
        'current_action_reviewed_task_count': len(selected),
        'pending_current_semantic_review_ids': [q['question_id'] for q in current['questions']
                                               if q['question_id'] not in selected],
        'task_coverage_scope': 'only supplied tasks; omitted listening or other sections are not certified',
        'structural_control_scope': 'unannotated same-material engine control; not learner Baseline',
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
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = replay(args.dataset, args.paper, args.reviewed_request, args.output)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {'per_question', 'pending_current_semantic_review_ids', 'reviewed_requests'}},
                     ensure_ascii=False, indent=2))
