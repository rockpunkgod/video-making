"""SYNTHETIC frozen transport controls, not teaching or learner Reviews.

Real frozen inputs are deliberately absent from this public test module. The
Analyzer/Exporter below only prepare labelled program fixtures; the consumer
must never call them or modify an upstream artifact.
"""
import ast
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from answer_engine.frozen_export import FrozenAssetExporter
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from tests.test_execution import action, span
from video_contracts import pointer, review_semantics, seal, sha
from pedagogy import compile_plan, copy_projection, validate_plan
from pedagogy.mechanical_payoff import frozen_candidate_transition
from pedagogy.sources import FrozenSource
from student_pov.payoff import supported_payoff


def request(*, second=None, options=None):
    """Explicit synthetic Review credentials; never applied to a real case."""
    registry = Registry()
    methods = ['R02'] + (['R01'] if second == 'R01' else [])
    evidence = [span()]
    q = {'question_id': 'SYNTHETIC-mechanical-payoff', 'question_type': '阅读理解',
         'stem': 'SYNTHETIC PROGRAM CONTROL, not a real exam question',
         'passage': 'alpha beta gamma',
         'options': options or {'A': 'SYNTHETIC alpha', 'B': 'SYNTHETIC beta',
                               'C': 'SYNTHETIC gamma', 'D': 'SYNTHETIC delta'},
         'requested_chain': methods,
         'observations': [{'method_id': mid, 'evidence': deepcopy(evidence), 'reviewed': True}
                          for mid in methods], 'relations': [], 'action_executions': []}
    for index, (mid, candidate) in enumerate([('R02', 'D')] + ([(second, 'C')] if second else [])):
        q['relations'].append({'method_id': mid, 'candidate': candidate, 'effect': 'eliminate',
            'claim': 'SYNTHETIC relation ' + candidate, 'evidence': deepcopy(evidence),
            'decision_rule_check': 'SYNTHETIC structural check only',
            'stop_rule_check': 'SYNTHETIC local boundary; other candidates unresolved',
            'verification': 'SYNTHETIC structural verification only',
            'reviewer': 'SYNTHETIC PROGRAM ONLY', 'review_status': 'reviewed',
            'execution_role': 'decider'})
        q['action_executions'].append(action('synthetic-cut-' + candidate, mid, 'decider',
            {'kind': 'candidate_decision', 'candidate': candidate, 'effect': 'eliminate',
             'relation_index': index}))
    analysis = QuestionAnalyzer(registry).analyze(q)
    review = {'question_id': q['question_id'], 'input_sha256': sha(q),
              'analysis_sha256': sha(analysis), 'method_id': 'R02',
              'method_version': registry.methods['R02']['version'],
              'reviewer': 'SYNTHETIC PROGRAM CREDENTIAL ONLY', 'reviewer_kind': 'AI',
              'evaluation_phase': 'post_reveal',
              'semantic_review': {'action': {'valid': True}, 'evidence': {'valid': True},
                  'output': {'valid': True, 'primary_role': 'decider', 'output_type': 'decide',
                             'artifact': 'candidate_decision', 'candidate': 'D', 'effect': 'eliminate',
                             'claim_limit': 'SYNTHETIC current D elimination only; no final answer'},
                  'stop': {'valid': True, 'stop_applied': False, 'action_output_usable': True}}}
    return {'question': q, 'analysis': analysis,
            'methods': [deepcopy(registry.methods[mid]) for mid in analysis['method_versions']],
            'reviews': [review], 'withdrawals': [], 'evaluation_phase': 'post_reveal',
            'source': {'usage_status': 'internal_only', 'redistribution_status': 'unconfirmed',
                       'source_reference': 'SYNTHETIC ONLY', 'attribution_text': 'SYNTHETIC'}}


def freeze(req=None):
    req = deepcopy(request() if req is None else req)
    # Rebind only the SYNTHETIC credential after a deliberate program mutation.
    for review in req['reviews']:
        review['input_sha256'], review['analysis_sha256'] = sha(req['question']), sha(req['analysis'])
    exp = FrozenAssetExporter()
    return exp.export(req, 'synthetic'), exp.status(req, 'synthetic'), {
        'method_id': 'R02', 'action_ids': ['synthetic-cut-D']}


def refs(value):
    if isinstance(value, dict):
        if {'asset_id', 'pointer', 'sha'} <= set(value):
            yield value
        for child in value.values():
            yield from refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from refs(child)


class MechanicalPayoffTests(unittest.TestCase):
    def test_pure_replay_refs_and_no_solver_calls(self):
        bundle, status, selected = freeze()
        before = sha([bundle, status, selected])
        with patch.object(QuestionAnalyzer, 'analyze', side_effect=AssertionError('consumer must not solve')):
            first = frozen_candidate_transition(bundle, status, selected)
            second = frozen_candidate_transition(bundle, status, selected)
            dispatched = FrozenSource(bundle, status, selected).payoff_support()
        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        self.assertEqual(first, dispatched)
        self.assertEqual(before, sha([bundle, status, selected]))
        for ref in refs(first):
            self.assertEqual(ref['asset_id'], bundle['asset_id'])
            self.assertEqual(ref['sha'], sha(review_semantics(pointer(bundle, ref['pointer']))))
        first['record']['method_path'][0]['text'] = 'tampered return'
        self.assertEqual(second, frozen_candidate_transition(bundle, status, selected))
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'pedagogy/mechanical_payoff.py').read_text(encoding='utf-8'))
        imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name.startswith(('core', 'answer_engine', 'renderers')) for name in imports))

    def test_work_is_local_candidate_task_and_all_remaining_work_is_kept(self):
        bundle, status, selected = freeze()
        support = frozen_candidate_transition(bundle, status, selected)
        record = support['record']
        self.assertEqual(support['origin'], 'frozen_candidate_transition')
        self.assertEqual(support['baseline_kind'], 'structural_candidate_state')
        self.assertFalse(support['baseline_measured'])
        self.assertFalse(record['temporal_learner_path_asserted'])
        self.assertFalse(record['learner_transfer_validated'])
        self.assertEqual(record['cognitive_work']['removed'], ['current_candidate_check:D'])
        self.assertEqual(record['cognitive_work']['deferred'], [])
        self.assertEqual(record['cognitive_work']['still_required'], [
            'current_candidate_check:A', 'current_candidate_check:B', 'current_candidate_check:C',
            'method_stop_condition', 'action_stop_condition'])
        self.assertTrue(record['removed_steps'][0]['reopen_on_upstream_change'])
        self.assertEqual(record['reduction']['before'], 4)
        self.assertEqual(record['reduction']['after'], 3)
        self.assertIn('time_saved', record['prohibited_inferences'])
        self.assertIn('reading_removed', record['prohibited_inferences'])
        self.assertFalse(record['answer_scope']['may_output_final_answer'])
        self.assertIsNone(record['answer_scope']['answer'])
        self.assertEqual(record['answer_scope']['remaining_candidates'], ['A', 'B', 'C'])
        self.assertEqual(record['allowed_claim'], bundle['reviews'][0]['record']['semantic_review']['output']['claim_limit'])

    def test_actual_compiler_handoff_and_student_payoff_accept_the_support(self):
        bundle, status, selected = freeze()
        plan = compile_plan(bundle, status, selected, mode='worked_example', duration_target=1000)
        self.assertEqual(plan['availability']['status'], 'READY')
        self.assertTrue(validate_plan(plan, bundle, status)['consumption_allowed'])
        projection = copy_projection(plan, bundle, status)
        payoff, gaps = supported_payoff(plan, projection)
        self.assertEqual(gaps, [])
        self.assertIsNotNone(payoff)
        self.assertEqual(payoff['payoff_type'], 'TYPE_A')
        self.assertFalse(plan['answer_scope']['may_output_final_answer'])
        self.assertFalse(plan['public_render_ready'])
        for boundary in plan['boundaries']['tell_now']:
            self.assertIn(boundary, projection['must_show_boundary'])

    def test_current_manifest_and_owned_lifecycle_are_required(self):
        bundle, status, selected = freeze()
        self.assertIsNone(frozen_candidate_transition(bundle, None, selected))
        for field, value in [('effective_status', 'WITHDRAWN'), ('semantic_binding_sha', '0' * 64),
                             ('source_sha', '0' * 64), ('asset_id', 'another-asset')]:
            changed = deepcopy(status); changed[field] = value
            with self.subTest(field=field):
                self.assertIsNone(frozen_candidate_transition(bundle, seal(changed), selected))
        for field, value in [('status', 'STALE'), ('snapshot_sha', '0' * 64)]:
            changed = deepcopy(status); changed['question'][field] = value
            self.assertIsNone(frozen_candidate_transition(bundle, seal(changed), selected))
        changed = deepcopy(status); changed['method_versions']['R02'] = '9.0.0'
        self.assertIsNone(frozen_candidate_transition(bundle, seal(changed), selected))
        for kind in ('actions', 'reviews', 'decisions', 'evidence'):
            changed = deepcopy(status)
            target = (bundle['analysis']['execution_trace'][0]['evidence_ids'][0] if kind == 'evidence'
                      else changed['lifecycle'][kind][0]['artifact_id'])
            next(row for row in changed['lifecycle'][kind] if row['artifact_id'] == target)['status'] = 'withdrawn'
            with self.subTest(kind=kind):
                self.assertIsNone(frozen_candidate_transition(bundle, seal(changed), selected))

    def test_selection_cannot_borrow_or_ambiguously_combine_actions(self):
        bundle, status, selected = freeze()
        for wrong in [{'method_id': 'R01', 'action_ids': selected['action_ids']},
                      {'method_id': 'R02', 'action_ids': ['missing']},
                      {'method_id': 'R02', 'action_ids': selected['action_ids'] * 2},
                      {'method_id': 'R02', 'action_ids': []}, None]:
            self.assertIsNone(frozen_candidate_transition(bundle, status, wrong))
        for second in ('R01', 'R02'):
            bundle, status, selected = freeze(request(second=second))
            self.assertIsNone(frozen_candidate_transition(bundle, status, selected))

    def test_one_remaining_candidate_never_becomes_an_answer(self):
        bundle, status, selected = freeze(request(options={'A': 'SYNTHETIC alpha', 'D': 'SYNTHETIC delta'}))
        support = frozen_candidate_transition(bundle, status, selected)
        self.assertIsNotNone(support)
        self.assertEqual(support['record']['reduction']['after_ids'], ['A'])
        self.assertFalse(support['record']['answer_scope']['may_output_final_answer'])
        self.assertFalse(support['record']['answer_scope']['closed'])
        self.assertIsNone(support['record']['answer_scope']['answer'])

    def test_even_rebound_synthetic_closed_or_inconsistent_states_are_rejected(self):
        for change in [lambda a: a.update(answer='A'),
                       lambda a: a['answer_verification'].update(closed=True),
                       lambda a: a['answer_verification'].update(unique_supported_candidate=True),
                       lambda a: a['answer_verification'].update(candidate_coverage_complete=True),
                       lambda a: a['answer_verification'].update(retained_candidates=['A']),
                       lambda a: a['answer_verification'].update(unresolved_candidates=['A', 'B']),
                       lambda a: a['answer_verification'].update(eliminated_candidates=['C'])]:
            req = request(); change(req['analysis'])
            with self.assertRaisesRegex(ValueError, 'Answer projection'):
                freeze(req)
            # Explicitly adversarial SYNTHETIC transport: the strengthened
            # producer must reject above. Bypass only that producer check to
            # retain the original real-consumer rejection assertion below.
            with patch('answer_engine.frozen_export.validate_frozen_answer'):
                bundle, status, selected = freeze(req)
            self.assertIsNone(frozen_candidate_transition(bundle, status, selected))

    def test_exact_review_attribution_and_output_stop_support_required(self):
        changes = [lambda r: r.update(method_id='R01'), lambda r: r.update(method_version='9.0.0'),
                   lambda r: r['semantic_review'].update(trigger={'valid': False}),
                   lambda r: r['semantic_review']['output'].update(candidate='C'),
                   lambda r: r['semantic_review']['output'].update(primary_role='reducer'),
                   lambda r: r['semantic_review']['output'].update(valid=False),
                   lambda r: r['semantic_review']['stop'].update(action_output_usable=False),
                   lambda r: r['semantic_review']['stop'].update(stop_applied=True),
                   lambda r: r['semantic_review'].pop('action')]
        for change in changes:
            req = request(); change(req['reviews'][0])
            bundle, status, selected = freeze(req)
            self.assertIsNone(frozen_candidate_transition(bundle, status, selected))

    def test_review_wrong_question_is_rejected_by_upstream_exporter(self):
        req = request(); req['reviews'][0]['question_id'] = 'another-question'
        with self.assertRaisesRegex(ValueError, 'Review question mismatch'):
            freeze(req)

    def test_explicit_payoff_dispatch_has_precedence_without_record_mutation(self):
        for measured in (None, False, True, 'unknown'):
            req = request(); bundle, status, selected = freeze(req)
            record = deepcopy(frozen_candidate_transition(bundle, status, selected)['record'])
            record['allowed_claim'] = 'SYNTHETIC explicit payoff credential takes precedence'
            if measured is None:
                record.pop('baseline_measured')
            else:
                record['baseline_measured'] = measured
            req['reviews'][0]['reviewed_payoff'] = deepcopy(record)
            bundle, status, selected = freeze(req)
            support = FrozenSource(bundle, status, selected).payoff_support()
            self.assertEqual(support['record'], record)
            self.assertEqual(support['origin'], 'explicit_reviewed_payoff')
            self.assertEqual(support['baseline_kind'], 'reviewed_path')
            self.assertEqual(support['baseline_measured'], measured if isinstance(measured, bool) else False)
            self.assertTrue(support['source_refs'][0]['pointer'].endswith('/reviewed_payoff'))

    def test_malformed_or_unsealed_transport_is_unavailable(self):
        bundle, status, selected = freeze()
        for invalid in (None, [], {}, 'unknown'):
            self.assertIsNone(frozen_candidate_transition(invalid, status, selected))
            self.assertIsNone(frozen_candidate_transition(bundle, invalid, selected))
        changed = deepcopy(bundle); changed['analysis']['answer_verification']['closed'] = True
        self.assertIsNone(frozen_candidate_transition(changed, status, selected))


if __name__ == '__main__':
    unittest.main()
