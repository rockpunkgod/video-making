"""Index actual reviewed method actions for later Case Review, without credit.

Post-reveal question reviews are not Blind predictions or Case-type reviews.
This private, append-only report cannot fill coverage slots or register cases.
"""
import argparse
from collections import Counter
import json

from core.registry import Registry
from core.real_cases import private_root, artifact, digest
from scripts.ingest_exam_sources import freeze_json
from scripts.replay_current_paper import read_reviewed_question


def collect(dataset, replay_ref, output, registry=None):
    root = private_root(dataset)
    registry = registry or Registry()
    registry.validate()
    report = artifact(root, replay_ref)
    if report.get('source_commit') != registry.index['source_baseline']['commit']:
        raise ValueError('Current source epoch required')
    paper = artifact(root, report['paper_material_ref'])
    if paper['paper_id'] != report.get('paper_id'):
        raise ValueError('Replay paper identity differs')
    original_ids = {q['question_id'] for q in paper['questions']}
    seen = set()
    candidates = []
    for binding in report.get('independent_question_reviews', []):
        # Check the replay's exact review bytes before replaying current actions.
        artifact(root, binding)
        question, checked = read_reviewed_question(root, binding['path'], registry)
        qid = question['question_id']
        if qid != binding.get('question_id') or qid not in original_ids or qid in seen:
            raise ValueError('Duplicate, mismatched or foreign reviewed question')
        seen.add(qid)
        review = artifact(root, binding)
        if {k: review['source_question_ref'][k] for k in ('path', 'sha256')} != report['paper_material_ref']:
            raise ValueError('Reviewed original is not the replay paper material')
        analysis = artifact(root, checked['analysis_ref'])
        own = {}
        for execution in analysis['execution_trace']:
            if execution['state'] in {'produced', 'stopped'}:
                own.setdefault(execution['method_id'], []).append(execution)
        for mid, executions in sorted(own.items()):
            method = registry.methods[mid]
            candidates.append({
                'question_id': qid, 'method_id': mid,
                'method_version': method['version'], 'primary_role': method['primary_role'],
                'question_review_ref': {'path': binding['path'], 'sha256': binding['sha256']},
                'question_ref': checked['question_ref'], 'analysis_ref': checked['analysis_ref'],
                'own_executions': executions,
                'question_answer_closed': analysis['answer_verification']['closed'],
                'case_type': None, 'case_type_review': 'pending_separate_own_method_review',
                'pre_reveal_provenance': 'not_established_by_question_review',
                'registration_eligible': False,
                'missing_requirements': ['verified_existing_pre_reveal_prediction_and_reveal_chain',
                                         'independent_own_method_case_type_review'],
            })
    result = {
        'scope': 'private_post_reveal_case_candidate_index_only',
        'source_commit': report['source_commit'], 'paper_id': report['paper_id'],
        'replay_report_ref': replay_ref, 'reviewed_question_count': len(seen),
        'candidate_question_method_count': len(candidates),
        'candidate_method_counts': dict(sorted(Counter(c['method_id'] for c in candidates).items())),
        'candidates': candidates, 'new_case_count': 0, 'filled_case_slots': 0,
        'new_unique_question_count': 0, 'new_blind_sample_count': 0,
        'learner_validation': None, 'method_promotion_applied': False,
        'scope_exclusions': ['existing_registered_request_actions', 'unreviewed_author_drafts'],
        'warning': 'Whole-question closure is not own-method decision credit; no automatic Case type assignment.',
    }
    destination = (root/output).resolve()
    if not destination.is_relative_to(root) or destination.exists():
        raise ValueError('Use a new private candidate report without overwriting history')
    freeze_json(destination, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--replay-report', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = private_root(args.dataset)
    raw = (root/args.replay_report).read_bytes()
    result = collect(root, {'path': args.replay_report, 'sha256': digest(raw)}, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}, ensure_ascii=False, indent=2))
