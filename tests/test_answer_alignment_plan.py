"""Binding checks only, explicitly not student or practical acceptance."""
import unittest
from unittest.mock import patch
from scripts.plan_answer_alignment import build_plan, TARGET
from core.registry import Registry


class AlignmentPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.plan=build_plan()

    def test_all_cards_and_renamed_bindings_have_exact_targets(self):
        self.assertEqual(self.plan['method_count'],82)
        self.assertEqual(self.plan['source_changed_method_count'],51)
        self.assertEqual(self.plan['to_commit'],TARGET)
        self.assertFalse(self.plan['runtime_migration_applied'])
        for m in self.plan['methods']:
            self.assertTrue(m['bindings']); self.assertTrue(m['resolved_references'])
            for b in m['bindings']:
                self.assertTrue(b['targets'])
                self.assertTrue(all(t['commit']==TARGET for t in b['targets']))

    def test_course_identities_not_generic_brand_aliases(self):
        identities={x['source_heading']:x for x in self.plan['course_identities']}
        self.assertFalse(identities['中心思想（8.7讲义原名，强版本未激活）']['source_activation'])
        self.assertFalse(identities['定位阅读法（应用文阅读课程题名）']['source_activation'])
        self.assertEqual(identities['顺藤摸瓜（记叙文细节的原命名）']['task_scope'],['narrative_detail'])
        self.assertTrue(all(not x['equivalent_to_existing_brand'] for x in identities.values()))

    def test_no_source_result_is_treated_as_release_evidence(self):
        self.assertEqual(self.plan['scope'],'binding_plan_only')
        self.assertTrue(self.plan['retain_historical_risks'])
        self.assertTrue(all(m['semantic_review']=='required_before_apply' for m in self.plan['methods']))

    def test_missing_exact_heading_fails_instead_of_fuzzy_fallback(self):
        with patch.dict('scripts.plan_answer_alignment.RELOCATIONS',
                        {'gaokao-english/references/reading-comprehension.md':
                         {'主客一致':['不存在的相似主客章节']}}):
            with self.assertRaisesRegex(ValueError,'exact target heading'):
                build_plan()

    def test_planning_does_not_switch_runtime(self):
        before=Registry().index['source_baseline']['commit']
        build_plan()
        self.assertEqual(Registry().index['source_baseline']['commit'],before)


if __name__=='__main__': unittest.main()
