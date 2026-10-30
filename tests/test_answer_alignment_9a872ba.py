"""Current source and compatibility checks, never learner-outcome evidence."""
from copy import deepcopy
import hashlib
import json
import unittest
from core.registry import Registry, ROOT
from scripts.align_answer_9a872ba import PREVIOUS, TARGET, correct, prepare
from scripts.generate_assets import build, apply_reference_supplements


class LatestAnswerAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=Registry(snapshot_commit=PREVIOUS)
        cls.current=Registry()
        cls.assets=build(cls.current)

    def test_both_epochs_validate_and_no_promotion(self):
        self.assertEqual(self.old.validate()['status'],'PASS')
        self.assertEqual(self.current.validate()['status'],'PASS')
        self.assertEqual(self.current.index['source_baseline']['commit'],TARGET)
        self.assertEqual(set(self.old.methods),set(self.current.methods))
        for mid,m in self.current.methods.items():
            self.assertFalse(m['student_ready'])
            for key in ('brand_name','source_name','primary_role','output_type','maturity_status','practical_value','first_use_test','evaluation'):
                self.assertEqual(m[key],self.old.methods[mid][key],(mid,key))
            self.assertEqual(m['full']['beginner_support'],self.old.methods[mid]['full']['beginner_support'])

    def test_only_three_explicit_card_revisions(self):
        changed={mid for mid,m in self.current.methods.items() if m['version']!=self.old.methods[mid]['version']}
        self.assertEqual(changed,{'G03','A05','W03'})
        for mid,m in self.current.methods.items():
            for key in ('core_action','decision_rule','stop_rule','compact','four_step_card'):
                self.assertEqual(m[key],correct(deepcopy(self.old.methods[mid]))[key],(mid,key))

    def test_all_source_bytes_are_exact_and_no_old_supplement_returns(self):
        manifest=self.current._load('provenance/manifest.yaml')
        for row in manifest['files']:
            self.assertEqual(hashlib.sha256((ROOT/'provenance/ANSWER'/row['path']).read_bytes()).hexdigest(),row['sha256'])
        for path in ('gaokao-english/references/reading-comprehension.md','gaokao-writing/references/application-writing-and-correction.md'):
            self.assertEqual(self.assets[path],self.current.document(path))
        catalog=json.loads((ROOT/'creative/method-choreography/course-method-mapping.json').read_bytes())
        catalog['methods'][0]['definition']+='\nSYNTHETIC tamper'
        with self.assertRaisesRegex(ValueError,'supersession content mismatch'):
            apply_reference_supplements(self.current,dict(self.assets),catalog)

    def test_current_boundaries_and_distinct_names_reach_consumer(self):
        grammar=self.assets['gaokao-grammar-fill/references/grammar-fill.md']
        for phrase in ('不能见修饰就填','cattle','先发生也不强制完成式','不是 `practice` 所选的宾语'):
            self.assertIn(phrase,grammar)
        self.assertNotIn('所指是否唯一不清',json.dumps(self.current.methods['G03'],ensure_ascii=False))
        self.assertNotIn('缺连续口述',json.dumps(self.current.methods['A05'],ensure_ascii=False))
        self.assertIn('核清后可',self.current.methods['W03']['stop_rule'])
        name='中心思想（8.7讲义原名，受限记叙文本推断入口）'
        identity=self.current.course_identity(name)['identity']
        self.assertTrue(identity['source_activation'])
        self.assertFalse(identity['equivalent_to_existing_brand'])
        for name in ('十二字真言','大小三圈','综合运用小结'):
            self.assertFalse(self.current.course_identity(name)['identity']['equivalent_to_existing_brand'])

    def test_r09_original_contract_and_full_source_unchanged(self):
        before,after=self.old.methods['R09'],self.current.methods['R09']
        for key in ('core_action','decision_rule','stop_rule','compact','four_step_card','visual_formula'):
            self.assertEqual(before[key],after[key])
        self.assertEqual([self.old.sources['sections'][s]['content'] for s in before['section_ids']],
            [self.current.sources['sections'][s]['content'] for s in after['section_ids']])

    def test_old_cases_remain_historical_and_reapply_cannot_downgrade(self):
        self.assertEqual(self.current.case_inventory(),self.old.case_inventory())
        with self.assertRaisesRegex(ValueError,'explicit previous epoch'):
            prepare()


if __name__=='__main__':unittest.main()
