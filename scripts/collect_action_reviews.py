"""Freeze post-reveal helper artifacts without claiming whole-question success.

This lane deliberately does not read answer keys, change blind predictions,
register Cases, or promote methods. Full source text stays in local-data.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from core.analyzer import QuestionAnalyzer
from core.registry import Registry, validate_schema
from core.evidence import validate_graph
from core.execution import validate_execution_trace
from renderers import render
from scripts.collect_exam_cases import material_equal
from scripts.ingest_exam_sources import ROOT, freeze_json, sha

STAGE = 'post_reveal_action_review'
FIELDS = {'exam_id', 'stage', 'reviewer', 'reviewer_kind', 'method_id',
          'mechanical_prediction_sha256', 'question', 'semantic_review'}
REVIEW_FIELDS = {'trigger', 'action', 'evidence', 'output', 'stop', 'transfer',
                 'practical_benefit', 'limitations', 'proposed_case_type'}
ANNOTATIONS = {'requested_chain', 'observations', 'action_executions'}
HELPER_KINDS = {'located_evidence', 'interpretation', 'candidate_partition',
                'framework_card', 'text_groups', 'route_selection'}


def nonempty(value):
    """Require actual review payload, without imposing another teaching Schema."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and any(nonempty(v) for v in value.values())
    if isinstance(value, list):
        return bool(value) and any(nonempty(v) for v in value)
    return False


def identifier(value):
    if not isinstance(value, str) or not value or any(c not in
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in value):
        raise ValueError('Unsafe artifact identifier')
    return value


def review_action(request, mechanical, analyzer=None):
    """Validate supplied annotations and replay real artifacts, not solve English."""
    if set(request) != FIELDS or request['stage'] != STAGE:
        raise ValueError('Explicit post-reveal action stage required')
    if request['reviewer_kind'] not in {'AI', 'human'} or not isinstance(request['reviewer'], str) or not request['reviewer'].strip():
        raise ValueError('Explicit external reviewer required')
    semantic = request['semantic_review']
    if not isinstance(semantic, dict) or set(semantic) != REVIEW_FIELDS:
        raise ValueError('Own role review fields required')
    for key in REVIEW_FIELDS - {'proposed_case_type'}:
        if not nonempty(semantic[key]):
            raise ValueError('Nonempty own role review required: ' + key)
    proposal = semantic['proposed_case_type']
    if isinstance(proposal, dict):
        if proposal.get('method_id') != request['method_id'] or proposal.get('registered') is not False or proposal.get('promotion_allowed') is not False:
            raise ValueError('Case proposal cannot register or promote a method')
        proposal = proposal.get('case_type')
    if proposal not in {None, 'canonical', 'counterexample', 'boundary', 'transfer', 'hard'}:
        raise ValueError('Unknown proposed case type')
    exam = identifier(request['exam_id']); mid = identifier(request['method_id'])
    if mechanical.get('exam_id') != exam or mechanical.get('pass') != 'blind':
        raise ValueError('Wrong frozen source prediction')
    question = request['question']; qid = identifier(question['question_id'])
    originals = [q for q in mechanical['inputs']['questions'] if q['question_id'] == qid]
    if len(originals) != 1:
        raise ValueError('Unknown or duplicate original question')
    original = originals[0]
    material_equal(original, question)
    # Nothing beyond the three supported annotation fields may be added,
    # removed or replaced, including task type and preexisting source metadata.
    if {k: v for k, v in original.items() if k not in ANNOTATIONS} != {
            k: v for k, v in question.items() if k not in ANNOTATIONS}:
        raise ValueError('Action review changed frozen question fields')
    if question.get('relations') or question.get('word_answer'):
        raise ValueError('Helper action lane cannot assert answers or candidate effects')
    analyzer = analyzer or QuestionAnalyzer(Registry())
    if mid not in analyzer.registry.methods:
        raise ValueError('Unknown reviewed method')
    method = analyzer.registry.methods[mid]
    if method['primary_role'] not in {'locator', 'interpreter', 'reducer', 'framework'}:
        raise ValueError('Helper lane cannot claim a decision or verification role')
    validate_schema('question-input', question)
    analysis = analyzer.analyze(deepcopy(question))
    validate_schema('question-analysis', analysis)
    validate_graph(analysis['evidence_graph'], question)
    registry = analyzer.registry
    validate_execution_trace(analysis, registry)
    actions = analysis['execution_trace']
    if not actions or any(x['method_id'] != mid or x['role'] != method['primary_role'] or
            x['state'] != 'produced' or x['output']['kind'] not in HELPER_KINDS for x in actions):
        raise ValueError('Requires actual own reviewed helper artifacts only')
    if analysis['answer'] is not None or analysis['content_eligible'] or analysis['candidate_analysis']:
        raise ValueError('Helper action must not assert whole-question closure')
    for kind in ('structured', 'content-export', 'student', 'legacy-wechat'):
        render(analysis, kind, registry)
    return {'exam_id': exam, 'question_id': qid, 'method_id': mid,
            'method_version': method['version'], 'primary_role': method['primary_role'],
            'output_role': method['output_type'], 'stage': STAGE,
            'reviewer': request['reviewer'], 'reviewer_kind': request['reviewer_kind'],
            'mechanical_prediction_sha256': request['mechanical_prediction_sha256'],
            'question': deepcopy(question), 'analysis': analysis, 'semantic_review': deepcopy(semantic),
            'candidate_status': 'pending_independent_case_review', 'case_type': None,
            'registry_updates': 0, 'case_slots_filled': 0,
            'learner_validation': 'pending_real_participant_validation',
            'semantic_certification': 'external_action_review_not_certified',
            'source_rights': 'local_research_only; redistribution_not_verified'}


def public_metadata(report):
    # Do not expose reviewer prose, English text, graph, quotes, or option groups.
    result = {k: report[k] for k in ('exam_id', 'question_id', 'method_id', 'method_version',
              'primary_role', 'output_role', 'stage', 'reviewer_kind',
              'mechanical_prediction_sha256', 'candidate_status', 'case_type',
              'registry_updates', 'case_slots_filled', 'learner_validation', 'semantic_certification')}
    result.update({'produced_action_count': len(report['analysis']['execution_trace']),
                   'artifact_kinds': [x['output']['kind'] for x in report['analysis']['execution_trace']],
                   'answer_withheld': report['analysis']['answer'] is None,
                   'whole_question_content_eligible': report['analysis']['content_eligible']})
    return result


def collect(dataset, request_path):
    root = Path(dataset).resolve(); path = Path(request_path).resolve()
    if not path.is_relative_to(root / 'action-reviews'):
        raise ValueError('Action requests must stay in private action-reviews directory')
    raw = path.read_bytes(); request = json.loads(raw)
    exam = identifier(request['exam_id'])
    if not path.is_relative_to(root / 'action-reviews' / exam):
        raise ValueError('Action request must stay in its own exam directory')
    # Timing is explicitly after an existing reveal; never label this blind.
    if not list((root / 'results' / exam).glob('reveal*.json')):
        raise ValueError('Post-reveal lane requires existing reveal artifact')
    mechanical_raw = (root / 'predictions' / exam / 'blind.json').read_bytes()
    if request['mechanical_prediction_sha256'] != sha(mechanical_raw):
        raise ValueError('Frozen mechanical prediction binding mismatch')
    report = review_action(request, json.loads(mechanical_raw))
    report['request_sha256'] = sha(raw)
    report['request_artifact'] = path.relative_to(root).as_posix()
    output = root / 'action-reviews' / exam / (report['method_id'] + '-' + report['question_id'] + '.review.json')
    freeze_json(output, report)
    return public_metadata(report)


def load_metadata(dataset, exam_id):
    root = Path(dataset); exam = identifier(exam_id); results = []
    for path in sorted((root / 'action-reviews' / exam).glob('*.review.json')):
        report = json.loads(path.read_bytes())
        if report['exam_id'] != exam or report['stage'] != STAGE:
            raise ValueError('Wrong action review identity')
        raw = (root / 'predictions' / exam / 'blind.json').read_bytes()
        if report['mechanical_prediction_sha256'] != sha(raw):
            raise ValueError('Action review source binding mismatch')
        request_path = (root / report['request_artifact']).resolve()
        if not request_path.is_relative_to((root / 'action-reviews' / exam).resolve()):
            raise ValueError('Action request binding escapes private review directory')
        request_raw = request_path.read_bytes()
        if sha(request_raw) != report['request_sha256']:
            raise ValueError('Action review request binding mismatch')
        expected = review_action(json.loads(request_raw), json.loads(raw))
        expected.update({'request_sha256': sha(request_raw), 'request_artifact': report['request_artifact']})
        if expected != report:
            raise ValueError('Action replay drift requires explicit regression review')
        results.append(public_metadata(report))
    return results


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('request')
    parser.add_argument('--dataset', default=str(ROOT / 'local-data/exams-2020-2025'))
    args = parser.parse_args()
    print(json.dumps(collect(args.dataset, args.request), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
