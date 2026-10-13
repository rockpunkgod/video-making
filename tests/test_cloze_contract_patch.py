"""Layered source consistency and version controls, not English acceptance."""
from copy import deepcopy
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry, load
from core.release import digest, method_facts
from scripts.generate_assets import build
from tests.test_execution import action, fixture, span


class ClozeContractPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def test_complete_old_cards_preserved_with_bounded_patch_delta(self):
        for mid in ('C01', 'C02'):
            with self.subTest(method=mid):
                old = load('method-registry/history/' + mid + '/1.2.0.yaml')
                current = self.registry.methods[mid]
                self.assertEqual(old['version'], '1.2.0')
                self.assertEqual(current['version'], '1.2.1')
                expected = deepcopy(old)
                expected['version'] = current['version']
                expected['change_reason'] = current['change_reason']
                expected['levels']['L3'] = old['stop_rule']
                self.assertEqual(current, expected)
                self.assertNotEqual(digest(method_facts(old)), digest(method_facts(current)))

    def test_generated_projections_do_not_reintroduce_old_order(self):
        assets = build(self.registry)
        for folder in ('gaokao-english', 'gaokao-objective'):
            self.assertNotIn('原空号走两遍', assets[folder + '/generated-methods.yaml'])
            self.assertNotIn('按原空号先做', assets[folder + '/generated-methods.yaml'])

    def test_old_actions_rejected_instead_of_silently_upgraded(self):
        for mid in ('C01', 'C02'):
            with self.subTest(method=mid):
                question = fixture()
                question.update(question_type='完形填空', task_type='cloze_blank',
                                requested_chain=[mid], relations=[],
                                observations=[{'method_id': mid, 'evidence': [span()], 'reviewed': True}])
                if mid == 'C01':
                    output = {'kind': 'framework_card', 'fields': [
                        {'name': name, 'value': 'program-only relation', 'evidence': [span()]}
                        for name in ('current_blank_role', 'recent_clue', 'expansion_gate', 'backfill_check')]}
                else:
                    output = {'kind': 'verification_result', 'scope': 'candidate_relation_check',
                              'candidate': 'A', 'claim': question['options']['A'],
                              'target_execution_ids': [], 'evidence': [span()],
                              'relation_check': 'program-only relation',
                              'backfill_check': 'program-only check', 'verdict': 'unresolved'}
                question['action_executions'] = [action('patch-' + mid, mid,
                    self.registry.methods[mid]['primary_role'], output)]
                result = QuestionAnalyzer(self.registry).analyze(question)
                self.assertIsNone(result['answer'])
                self.assertEqual(result['execution_trace'][0]['method_version'], '1.2.1')
                question['action_executions'][0]['method_version'] = '1.2.0'
                with self.assertRaisesRegex(ValueError, 'Action method version mismatch'):
                    QuestionAnalyzer(self.registry).analyze(question)


if __name__ == '__main__':
    unittest.main()
