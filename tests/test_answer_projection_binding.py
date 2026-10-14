"""Synthetic renderer integrity controls; not exam or learner evidence."""
from copy import deepcopy
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from renderers import render
from tests.test_execution import fixture


class AnswerProjectionBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.analyzer = QuestionAnalyzer(cls.registry)

    def rejected_everywhere(self, result):
        for kind in ('structured', 'content-export', 'student', 'legacy-wechat'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                render(deepcopy(result), kind, self.registry)

    def test_answer_only_mutation_rejected(self):
        result = self.analyzer.analyze(fixture())
        result['answer'] = 'B'
        self.rejected_everywhere(result)

    def test_coherent_answer_and_summary_mutation_rejected(self):
        result = self.analyzer.analyze(fixture())
        result['answer'] = 'B'
        result['answer_verification']['retained_candidates'] = ['B']
        result['answer_verification']['eliminated_candidates'] = ['A']
        self.rejected_everywhere(result)

    def test_coherent_candidate_rows_mutation_rejected(self):
        result = self.analyzer.analyze(fixture())
        result['answer'] = 'B'
        for row in result['candidate_analysis']:
            row['effect'] = 'eliminate' if row['candidate'] == 'A' else 'retain'
        result['answer_verification']['retained_candidates'] = ['B']
        result['answer_verification']['eliminated_candidates'] = ['A']
        self.rejected_everywhere(result)

    def test_drop_relation_projection_rejected(self):
        result = self.analyzer.analyze(fixture())
        result['candidate_analysis'].pop()
        self.rejected_everywhere(result)

    def test_typed_effect_must_agree_even_when_artifact_hash_rebound(self):
        from core.execution import artifact_fingerprint
        result = self.analyzer.analyze(fixture())
        execution = result['execution_trace'][2]
        execution['output']['effect'] = 'eliminate'
        node = next(n for n in result['evidence_graph']['nodes']
                    if n['id'] == execution['artifact_node_id'])
        node['artifact_fingerprint'] = artifact_fingerprint(execution['output'])
        self.rejected_everywhere(result)

    def test_false_closure_and_confidence_rejected(self):
        for field, value in [('closed', False), ('unique_supported_candidate', False),
                             ('candidate_coverage_complete', False)]:
            result = self.analyzer.analyze(fixture())
            result['answer_verification'][field] = value
            self.rejected_everywhere(result)
        result = self.analyzer.analyze(fixture())
        result['answer_confidence'] = 'low'
        self.rejected_everywhere(result)

    def test_valid_typed_and_legacy_inputs_still_render_without_mutation(self):
        for typed in (True, False):
            question = fixture()
            if not typed:
                question.pop('action_executions')
            result = self.analyzer.analyze(question)
            before = deepcopy(result)
            for kind in ('structured', 'content-export', 'student', 'legacy-wechat'):
                self.assertTrue(render(result, kind, self.registry))
            self.assertEqual(result, before)

    def test_unreviewed_rival_does_not_disappear(self):
        question = fixture()
        question.pop('action_executions')
        question['relations'][1]['review_status'] = 'unreviewed'
        result = self.analyzer.analyze(question)
        self.assertIsNone(result['answer'])
        result['answer_verification']['unresolved_candidates'] = []
        result['answer_verification']['candidate_coverage_complete'] = True
        result['answer_verification']['closed'] = True
        result.update(answer='A', answer_confidence='medium', content_eligible=True)
        self.rejected_everywhere(result)

    def test_unrepresented_original_option_cannot_disappear(self):
        question = fixture()
        question['options']['C'] = 'unrepresented program-only rival'
        result = self.analyzer.analyze(question)
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['C'])
        result['answer_verification'].update(unresolved_candidates=[],
                                            candidate_coverage_complete=True, closed=True)
        result.update(answer='A', answer_confidence='medium', content_eligible=True)
        self.rejected_everywhere(result)

    def test_scope_cannot_be_dropped_to_bypass_candidate_coverage(self):
        for key in ['candidate_ids', 'material_sha256']:
            result = self.analyzer.analyze(fixture())
            result['evidence_graph']['nodes'][0].pop(key)
            self.rejected_everywhere(result)

    def test_original_input_scope_checked_against_raw_question(self):
        from core.evidence import validate_graph
        question = fixture()
        result = self.analyzer.analyze(question)
        result['evidence_graph']['nodes'][0]['candidate_ids'] = ['A']
        with self.assertRaises(ValueError):
            validate_graph(result['evidence_graph'], question)

    def test_failed_backfill_cannot_restore_prior_answer(self):
        question = fixture()
        question['action_executions'][-1]['output']['verdict'] = 'unresolved'
        result = self.analyzer.analyze(question)
        self.assertIsNone(result['answer'])
        result.update(answer='A', answer_confidence='medium', content_eligible=True)
        result['answer_verification']['closed'] = True
        self.rejected_everywhere(result)

    def test_repeated_relations_for_same_candidate_remain_supported(self):
        question = fixture()
        question.pop('action_executions')
        question['relations'].append(deepcopy(question['relations'][0]))
        result = self.analyzer.analyze(question)
        self.assertEqual(result['answer'], 'A')
        self.assertTrue(render(result, 'student', self.registry))
