"""Synthetic partition controls, not English or learner validation."""
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from renderers import render
from tests.test_execution import action


class OptionOnlyPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.analyzer = QuestionAnalyzer(cls.registry)

    def question(self, mid='F01'):
        options = {key: 'program option '+key for key in 'ABCDEFG'}
        evidence = [{'field': 'option:'+key, 'start': 0, 'end': len(text), 'quote': text}
                    for key, text in options.items()]
        return {'question_id': 'synthetic-option-partition', 'question_type': '七选五',
                'stem': 'program-only blank', 'passage': 'program-only passage',
                'options': options, 'requested_chain': [mid],
                'observations': [{'method_id': mid, 'evidence': evidence, 'reviewed': True}],
                'action_executions': [action('option-group', mid, 'reducer',
                    {'kind': 'candidate_partition', 'axis': 'program-no-distinction',
                     'groups': [{'label': 'no distinction', 'candidates': list(options)}]},
                    evidence=evidence)]}

    def test_all_four_grouping_methods_can_inspect_options_without_passage_quote(self):
        for mid in ['F01', 'F02', 'F03', 'F04']:
            with self.subTest(method=mid):
                result = self.analyzer.analyze(self.question(mid))
                self.assertEqual(result['execution_trace'][0]['state'], 'produced')
                self.assertIsNone(result['answer'])
                self.assertEqual(result['candidate_analysis'], [])
                self.assertFalse(result['content_eligible'])
                self.assertEqual(result['answer_verification']['unresolved_candidates'], list('ABCDEFG'))
                for renderer in ['structured', 'student', 'legacy-wechat', 'content-export']:
                    self.assertTrue(render(result, renderer, self.registry))

    def test_every_candidate_still_needs_own_option_evidence(self):
        q = self.question()
        q['action_executions'][0]['evidence'].pop()
        with self.assertRaisesRegex(ValueError, 'option wording'):
            self.analyzer.analyze(q)

    def test_partition_still_cannot_omit_or_repeat_candidates(self):
        for candidates in [list('ABCDEF'), list('ABCDEFGG')]:
            q = self.question()
            q['action_executions'][0]['output']['groups'][0]['candidates'] = candidates
            with self.assertRaisesRegex(ValueError, 'cover every option'):
                self.analyzer.analyze(q)

    def test_candidate_relation_cannot_use_partition_exception(self):
        q = self.question()
        q['relations'] = [{'method_id': 'F01', 'candidate': 'A', 'effect': 'retain',
                          'claim': 'not a real semantic claim',
                          'evidence': q['action_executions'][0]['evidence'],
                          'decision_rule_check': 'program-only', 'stop_rule_check': 'program-only',
                          'verification': 'program-only', 'reviewer': 'synthetic',
                          'review_status': 'reviewed'}]
        with self.assertRaisesRegex(ValueError, 'method_overreach'):
            self.analyzer.analyze(q)

    def test_non_grouping_method_cannot_borrow_option_only_exception(self):
        q = self.question()
        q['requested_chain'] = ['F11']
        q['observations'][0]['method_id'] = 'F11'
        x = q['action_executions'][0]
        x.update(method_id='F11', method_version=self.registry.methods['F11']['version'], role='decider')
        with self.assertRaisesRegex(ValueError, 'option wording'):
            self.analyzer.analyze(q)

    def test_unreviewed_trigger_cannot_create_reviewed_grouping(self):
        q = self.question()
        q['observations'][0]['reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'independently reviewed trigger'):
            self.analyzer.analyze(q)

    def test_stopped_action_cannot_keep_partition_output(self):
        q = self.question()
        q['action_executions'][0]['stop_applied'] = True
        with self.assertRaisesRegex(ValueError, 'Stopped action'):
            self.analyzer.analyze(q)


if __name__ == '__main__':
    unittest.main()
