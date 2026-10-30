"""Protect the reviewed bounded editorial delta, not learner effectiveness."""
from copy import deepcopy
import hashlib
import json
import unittest
import yaml

from core.registry import ROOT, Registry, load


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


class PriorityEditorialDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This exact allowed-delta claim predates both the beginner-copy
        # revision and October30 source migration. Keep its original scope.
        cls.registry = Registry(snapshot_commit='1c388a0596b13935ae7c6a1af00834915a8efa33')
        for mid in cls.registry.methods:
            cls.registry.methods[mid]=yaml.safe_load((ROOT/f'method-registry/history/{mid}/editorial-before-20261028.yaml').read_text(encoding='utf-8'))

    def test_archived_cards_and_exact_allowed_delta(self):
        # Independent reviewers bound these complete prior cards, not just text snippets.
        prior = {
            'R01': '93699b391351a208e3fcf0ae611b993883931013aef06c04325c7920bcfe9d25',
            'R02': 'cdae230874d18859d6906fbb33f83b569a11d0641a1edef5b19ab60f0461ca4b',
            'R06': 'aaccd21ce53330b7ee9ea0507d3e790d482c110e783a4bb35dbf6da0e97d7497',
            'R09': '5ee4772172bc98f3a2bde83515752ea0c6cd776f5603d072fa9b08c367ea498e',
            'F01': '8a1322b0ba813363363c85ce5aae0b5a9e2cce1ffb392ea3a53a6dbe92a38b1e',
            'G01': 'a15aa437f8d9bc1b9632f0dbe4e41ed4b84f381f4ec59db699c067c040402ffe',
        }
        for mid, expected in prior.items():
            with self.subTest(method=mid):
                before = load('method-registry/history/'+mid+'/1.2.0.yaml')
                self.assertEqual(digest(before), expected)
                after = deepcopy(self.registry.methods[mid])
                self.assertEqual(after['static_design_review']['participant_validation'],
                                 'pending_real_participant_validation')
                after.pop('static_design_review')
                for key in ('regression_result', 'change_reason'):
                    after[key] = before[key]
                if mid != 'R01':
                    after['evaluation']['baseline'] = before['evaluation']['baseline']
                if mid == 'R02':
                    after['practicality_gate']['misuse_cost'] = before['practicality_gate']['misuse_cost']
                    after['version'] = before['version']
                if mid == 'R06':
                    after['levels']['L2'] = before['levels']['L2']
                    after['practicality_gate']['misuse_cost'] = before['practicality_gate']['misuse_cost']
                    after['version'] = before['version']
                self.assertEqual(after, before)
                self.assertIs(after['student_ready'], False)

    def test_unaffected_methods_preserved_in_exact_file_archive(self):
        touched = {'R01', 'R02', 'R06', 'R09', 'F01', 'G01'}
        archive = 'provenance/editorial-history/2026-10-24-priority-six-before/'
        for name in ('reading.yaml', 'seven-five.yaml', 'grammar.yaml'):
            for old in load(archive+name)['methods']:
                if old['method_id'] not in touched:
                    self.assertEqual(self.registry.methods[old['method_id']], old)

    def test_same_subject_state_branches_not_excluded_by_misuse_warning(self):
        card = self.registry.methods['R02']
        self.assertEqual(card['practicality_gate']['misuse_cost'],
            'high；无可比差异时强套会虚构偷换，因此须先确认主体、施受或愿望/事实、能力/意愿上的具体可比差异。')
        self.assertIn('希望/事实、能力/意愿', card['core_action'])
        self.assertEqual(card['core_action'], load('method-registry/history/R02/1.2.0.yaml')['core_action'])

    def test_paragraph_scope_does_not_require_framework_generation(self):
        card = self.registry.methods['R06']
        self.assertEqual(card['levels']['L2'],
            '对照所问范围已核实的核心对象与关系，比较候选的完整覆盖，不固定块数。')
        self.assertEqual(card['practicality_gate']['misuse_cost'],
            'high；核心提错会系统性误判，因此必须先由所问范围正文核实核心，不能把候选假设当作正文事实。')
        self.assertIn('没有已证核心关系先停', card['stop_rule'])
        self.assertIn('所问范围', card['core_action'])

    def test_grammar_tree_boolean_keys_survive_editorial_change(self):
        branches = self.registry.methods['G01']['full']['decision_tree']['prompt_word']
        self.assertEqual({type(key) for key in branches}, {bool})
        self.assertEqual(branches[False]['node'], 'function_word')
        self.assertEqual(branches[True]['node'], 'required_slot')


if __name__ == '__main__':
    unittest.main()
