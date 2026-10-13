"""Synthetic program controls, not exam answers, English review, or learner data."""
from copy import deepcopy
import unittest

from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry
from renderers import render
from tests.test_execution import action


class OptionlessCandidateClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.engine = QuestionAnalyzer(cls.registry)

    def question(self, effects=('retain', 'undetermined'), typed=True):
        text = 'Synthetic program grammar blank, not a real exam.'
        span = {'field': 'passage', 'start': 0, 'end': len(text), 'quote': text}
        q = {'question_id': 'synthetic-optionless-closure',
             'question_type': '语法填空', 'task_type': 'grammar_form_completion',
             'stem': 'Synthetic blank', 'passage': text, 'given_word': 'program',
             'requested_chain': ['G15'],
             'observations': [{'method_id': 'G15', 'evidence': [span], 'reviewed': True}],
             'relations': []}
        for index, effect in enumerate(effects):
            candidate = 'synthetic-form-' + str(index)
            q['relations'].append({'method_id': 'G15', 'candidate': candidate,
                'effect': effect, 'claim': candidate, 'evidence': [deepcopy(span)],
                'decision_rule_check': 'Synthetic positive or unresolved relation, not English proof',
                'stop_rule_check': 'Do not close while a known rival remains unresolved',
                'verification': 'Synthetic structural backfill only',
                'reviewer': 'synthetic-program-fixture', 'review_status': 'reviewed'})
        if typed:
            q['action_executions'] = [action('synthetic-decision-' + str(i), 'G15', 'decider',
                {'kind': 'candidate_decision', 'candidate': rel['candidate'],
                 'effect': rel['effect'], 'relation_index': i}, evidence=[deepcopy(span)])
                for i, rel in enumerate(q['relations'])]
        return q

    def test_known_undetermined_rival_withholds_typed_answer_without_options(self):
        q = self.question()
        before = deepcopy(q)
        result = self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertFalse(result['answer_verification']['closed'])
        self.assertFalse(result['answer_verification']['candidate_coverage_complete'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['synthetic-form-1'])
        self.assertEqual(result['answer_verification']['retained_candidates'], ['synthetic-form-0'])
        self.assertFalse(result['content_eligible'])
        self.assertEqual(q, before)
        for mode in ['student', 'legacy-wechat', 'structured', 'content-export']:
            self.assertTrue(render(result, mode, self.registry))

    def test_legacy_relations_also_keep_explicit_rival_unresolved(self):
        result = self.engine.analyze(self.question(typed=False))
        self.assertIsNone(result['answer'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['synthetic-form-1'])

    def test_unreviewed_elimination_does_not_resolve_known_rival(self):
        q = self.question(('retain', 'eliminate'), typed=False)
        q['relations'][1]['review_status'] = 'unreviewed'
        result = self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['synthetic-form-1'])

    def test_all_submitted_rivals_eliminated_preserves_supported_closure(self):
        result = self.engine.analyze(self.question(('retain', 'eliminate', 'eliminate')))
        self.assertEqual(result['answer'], 'synthetic-form-0')
        self.assertTrue(result['answer_verification']['closed'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'], [])

    def test_two_undetermined_forms_are_reported_without_fabricating_answer(self):
        result = self.engine.analyze(self.question(('undetermined', 'undetermined')))
        self.assertIsNone(result['answer'])
        self.assertFalse(result['answer_verification']['candidate_coverage_complete'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'],
                         ['synthetic-form-0', 'synthetic-form-1'])

    def test_elimination_only_does_not_invent_a_surviving_form(self):
        result = self.engine.analyze(self.question(('eliminate', 'eliminate')))
        self.assertIsNone(result['answer'])
        self.assertFalse(result['answer_verification']['unique_supported_candidate'])

    def test_multiple_supported_forms_still_do_not_close(self):
        result = self.engine.analyze(self.question(('retain', 'retain')))
        self.assertIsNone(result['answer'])
        self.assertFalse(result['answer_verification']['closed'])

    def test_supplied_option_without_relation_remains_unresolved(self):
        q = self.question(('retain', 'eliminate'))
        q['options'] = {name: 'synthetic choice' for name in
                        ['synthetic-form-0', 'synthetic-form-1', 'synthetic-form-2']}
        result = self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['synthetic-form-2'])

    def test_duplicate_relations_do_not_create_duplicate_unresolved_entries(self):
        q = self.question(typed=False)
        q['relations'].append(deepcopy(q['relations'][1]))
        result = self.engine.analyze(q)
        self.assertEqual(result['answer_verification']['unresolved_candidates'], ['synthetic-form-1'])

    def test_single_supported_form_without_declared_rivals_stays_compatible(self):
        result = self.engine.analyze(self.question(('retain',)))
        self.assertEqual(result['answer'], 'synthetic-form-0')
        self.assertTrue(result['answer_verification']['closed'])

    def test_paper_uses_same_known_rival_guard(self):
        result = PaperAnalyzer(self.engine).analyze({'paper_id': 'synthetic-paper',
                                                    'questions': [self.question()]})
        self.assertIsNone(result['questions'][0]['answer'])
        self.assertFalse(result['questions'][0]['answer_verification']['closed'])
