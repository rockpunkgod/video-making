"""Freeze a newly authored current action for review, retaining the old Case.

This prepares a post-reveal version reacceptance packet, not a registration,
new blind prediction, answer certification or learner outcome.
"""
import argparse
from pathlib import Path
import json

from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.real_cases import (private_root, private_file, artifact, material,
                             digest, json_digest, load_catalog, _runtime_contexts,
                             _validate_request)
from scripts.ingest_exam_sources import freeze_json


def prepare(dataset, prior_request, current_question, output):
    root = private_root(dataset)
    registry = Registry()
    registry.validate()
    _, request_raw = private_file(root, prior_request)
    request = json.loads(request_raw)
    request_ref = {'path': prior_request, 'sha256': digest(request_raw)}
    catalog = load_catalog(root, registry=registry)
    records = [artifact(root, ref) for ref in catalog['cases']]
    prior_cases = [record for record in records
                   if record['registration_request_ref'] == request_ref]
    if len(prior_cases) != 1:
        raise ValueError('Use one existing registered Case; do not create duplicate source questions')
    context = _runtime_contexts(root).get((prior_request, request_ref['sha256']))
    previous = context['registry'] if context else registry
    # Read only the already registered historical packet; this cannot admit a Case.
    _, frozen, _ = _validate_request(root, request, previous, _catalog_replay=True)
    _, question_raw = private_file(root, current_question)
    question = json.loads(question_raw)
    if material(question) != material(frozen):
        raise ValueError('New action must preserve all frozen original question fields')
    mid = request['method_id']
    method = registry.methods[mid]
    current_key = [request['canonical_question_id'], mid, request['case_type'], method['version']]
    if any(record.get('registration_key') == current_key for record in records):
        raise ValueError('Current version already registered; do not prepare duplicate Case credit')
    if question.get('requested_chain') != [mid]:
        raise ValueError('Reaccept only the named method, without implicit borrowed credit')
    executions = question.get('action_executions', [])
    if not executions or any(x.get('method_id') != mid or
                             x.get('method_version') != method['version'] for x in executions):
        raise ValueError('Supply newly authored executions of the current method version')
    old_action = artifact(root, request['action'])
    old_ids = {x['execution_id'] for x in old_action['question'].get('action_executions', [])}
    if old_ids.intersection(x['execution_id'] for x in executions):
        raise ValueError('Do not re-version a frozen execution; use a distinct new action identity')
    analysis = QuestionAnalyzer(registry).analyze(question)
    own = [x for x in analysis['execution_trace'] if x['method_id'] == mid
           and x['state'] in {'produced', 'stopped'}]
    if not own:
        raise ValueError('New action has no executable own-method trace')
    destination = (root/output).resolve()
    if not destination.is_relative_to(root) or destination.exists():
        raise ValueError('Use a new private output directory without overwriting history')
    exam_id = request['source']['exam_id']
    action = {
        'exam_id': exam_id, 'question_id': request['question_id'], 'method_id': mid,
        'method_version': method['version'],
        'source_commit': registry.index['source_baseline']['commit'],
        'phase': 'post_reveal_current_source_action_not_new_blind',
        'mechanical_prediction_sha256': request['blind']['sha256'],
        'question': question, 'analysis': analysis,
        'prior_registration_request_ref': request_ref,
        'prior_action_ref': request['action'],
        'current_input_ref': {'path': current_question, 'sha256': digest(question_raw)},
        'core_material_unchanged': True,
        'new_unique_question_count': 0, 'new_blind_sample_count': 0,
        'learner_validation': 'pending_real_participant_validation',
    }
    destination.mkdir(parents=True)
    action_path = destination/'action.json'
    freeze_json(action_path, action)
    action_ref = {'path': action_path.relative_to(root).as_posix(),
                  'sha256': digest(action_path.read_bytes())}
    pending = {key: value for key, value in request.items()
               if key not in {'action', 'case_review', 'method_version', 'case_id'}}
    pending.update(method_version=method['version'], action=action_ref,
                   source_commit=action['source_commit'],
                   case_id=prior_cases[0]['case_id']+'-current-'+method['version'].replace('.', '-'))
    freeze_json(destination/'pending-request.json', pending)
    provenance = {
        'scope': 'current-version reacceptance preparation; independent review required',
        'source_commit': action['source_commit'], 'catalog_revision': catalog['revision'],
        'catalog_sha256': catalog['sha256'], 'prior_registration_request_ref': request_ref,
        'action_ref': action_ref, 'action_analysis_sha256': json_digest(analysis),
        'evidence_graph_sha256': json_digest(analysis['evidence_graph']),
        'own_execution_ids': [x['execution_id'] for x in own],
        'new_case_count': 0, 'new_unique_question_count': 0, 'new_blind_sample_count': 0,
        'independent_review': 'pending', 'registration_applied': False,
    }
    freeze_json(destination/'provenance.json', provenance)
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--prior-request', required=True)
    parser.add_argument('--current-question', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.dataset, args.prior_request, args.current_question,
                             args.output), ensure_ascii=False, indent=2))
