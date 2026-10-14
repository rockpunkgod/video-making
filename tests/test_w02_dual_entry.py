"""Synthetic W02 contract checks; no real pupil, exam or scoring results."""
from copy import deepcopy
import unittest
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from renderers import render
from scripts.generate_assets import build


class W02DualEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.method = cls.registry.methods['W02']
        cls.engine = QuestionAnalyzer(cls.registry)

    def question(self):
        passage = 'SYNTHETIC program-only narrative constraints, not a real exam.'
        evidence = {'field': 'passage', 'start': 0, 'end': len(passage), 'quote': passage}
        return {'question_id': 'synthetic-W02-before-writing', 'question_type': '读后续写',
                'stem': 'SYNTHETIC build a functional outline, not a pupil correction.',
                'passage': passage, 'continuation_starters': ['SYNTHETIC first opening.', 'SYNTHETIC second opening.'],
                'requested_chain': ['W02'],
                'observations': [{'method_id': 'W02', 'reviewed': True, 'evidence': [evidence]}],
                'action_executions': [{'execution_id': 'outline', 'method_id': 'W02',
                    'method_version': self.method['version'], 'role': 'framework',
                    'input_artifact_ids': [], 'concrete_action': 'Mark five planned functional positions, not existing pupil sentences.',
                    'evidence': [evidence], 'decision_rule_check': 'Program-only outline projection; no English or grading judgment.',
                    'stop_rule_check': 'Leave unsupported planned details open; do not count ten sentences.',
                    'stop_applied': False, 'reviewer': 'synthetic-contract-review-not-a-pupil', 'review_status': 'reviewed',
                    'output': {'kind': 'framework_card', 'fields': [
                        {'name': name, 'value': 'SYNTHETIC planned function, not an observed draft defect.', 'evidence': [evidence]}
                        for name in ['first_start', 'necessary_bridge', 'second_start', 'resolution', 'response']]}}]}

    def test_tracked_version_and_unpromoted_primary_role(self):
        self.assertEqual(self.method['version'], '1.3.0')
        self.assertEqual(self.registry.index['methods']['W02']['version'], '1.3.0')
        self.assertEqual(self.method['primary_role'], 'framework')
        self.assertEqual(self.method['maturity_status'], 'candidate')
        self.assertFalse(self.method['student_ready'])
        self.assertEqual(self.method['first_use_test']['final_result'], 'pending_real_student_test')

    def test_full_source_supports_planning_and_diagnosis_without_fixed_sentence_quota(self):
        full = self.registry.full('W02')
        for text in ['构思支架', '不是固定句数', '先锁定 5 个功能位', '句数不同', '给定首句']:
            self.assertIn(text, full)
        self.assertEqual(self.method['full']['summary'], self.method['core_action'] + ' ' + self.method['decision_rule'])

    def test_four_steps_and_practicality_expose_both_real_entries(self):
        for field in ['core_action', 'entry_copy']:
            self.assertIn('未', self.method[field])
            self.assertIn('已有稿', self.method[field])
        self.assertEqual(self.method['four_step_card']['stop'], self.method['stop_rule'])
        self.assertEqual(self.method['practicality_gate']['action'], self.method['core_action'])
        for text in ['缺原文', '任一首句', '留空', '不凑十句', '独立升华句非必需']:
            self.assertIn(text, self.method['stop_rule'])

    def test_before_writing_has_actual_framework_but_no_pupil_draft_or_score(self):
        question = self.question()
        before = deepcopy(question)
        result = self.engine.analyze(question)
        self.assertEqual(question, before)
        self.assertEqual(result['execution_trace'][0]['state'], 'produced')
        self.assertEqual(result['execution_trace'][0]['output']['kind'], 'framework_card')
        self.assertIsNone(result['answer'])
        self.assertIsNone(result['writing_feedback'])
        for mode in ['structured', 'student', 'legacy-wechat', 'content-export']:
            self.assertTrue(render(result, mode, self.registry))

    def test_missing_second_starter_withholds_complete_framework(self):
        question = self.question()
        question['continuation_starters'].pop()
        result = self.engine.analyze(question)
        self.assertEqual(result['execution_trace'][0]['state'], 'incomplete_input')
        self.assertIsNone(result['execution_trace'][0]['output'])
        self.assertIsNone(result['answer'])

    def test_missing_draft_cannot_supply_fabricated_student_evidence(self):
        question = self.question()
        question['action_executions'][0]['evidence'] = [
            {'field': 'student_text', 'start': 0, 'end': 7, 'quote': 'invented'}]
        with self.assertRaises(ValueError):
            self.engine.analyze(question)

    def test_old_typed_action_cannot_silently_use_new_trigger_contract(self):
        question = self.question()
        question['action_executions'][0]['method_version'] = '1.2.0'
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            self.engine.analyze(question)

    def test_generated_first_contact_is_draft_not_research_acceptance(self):
        guide = build(self.registry)['student-guides/W02-十句五锚.md']
        for text in ['学生首次接触草稿', '中文提纲', '10 秒版', '30 秒版', '90 秒版', 'student_ready=false']:
            self.assertIn(text, guide)
        self.assertIn('提纲', self.method['compact']['90s'])
        self.assertIn('非必需', self.method['compact']['90s'])
        self.assertIn('先列', self.method['compact']['10s'])
        self.assertIn('必要桥', self.method['compact']['10s'])
        self.assertIn('五格提纲', self.method['compact']['10s'])
        self.assertIn('只有选自写十句框架时', self.method['levels']['L2'])
