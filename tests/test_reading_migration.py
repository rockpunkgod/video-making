"""Archived b04 editorial regressions; current epoch is tested in alignment tests."""
from copy import deepcopy
import unittest
from core.registry import Registry, ROOT, load
from scripts.generate_assets import build

REVISED={'R03','R04','R05','R07','R08','R10','R11','R12','R13','R14','R15','R16','R17'}

class ReadingMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')

    def test_every_reading_entry_has_independent_action_judgment_and_brake(self):
        methods=[m for m in self.registry.methods.values() if m['question_type']=='阅读理解']
        self.assertEqual(len(methods),17)
        for m in methods:
            with self.subTest(method=m['method_id']):
                self.assertTrue(m['student_ready'] and m['entry_copy'])
                self.assertTrue(all(m['four_step_card'][k] for k in ['start','first_cut','judge','stop']))
                self.assertTrue(m['counterexamples'] and m['challenge_prompt'] and m['visual_formula'])

    def test_revisions_preserve_source_roles_and_old_versions(self):
        for mid in REVISED:
            m=self.registry.methods[mid]; old=load('method-registry/history/'+mid+'/1.0.0.yaml')
            self.assertEqual(m['version'],'1.1.0')
            for field in ['source_name','source_references','section_ids','method_type','primary_role','output_type']:
                self.assertEqual(m[field],old[field])
            self.assertEqual(m['maturity_status'],'candidate')
            self.assertEqual(m['practical_value'],'Useful')
            self.assertNotEqual(m['decision_rule'],old['decision_rule'])
            self.assertNotEqual(m['stop_rule'],old['stop_rule'])
            self.assertEqual(m['static_design_review']['participant_validation'],'pending_real_participant_validation')

    def test_revised_copies_do_not_hide_actions_in_source_chapters(self):
        for mid in REVISED:
            m=self.registry.methods[mid]
            for copy in [m['entry_copy'],m['decision_rule'],m['stop_rule'],*m['compact'].values()]:
                for old in ['具体边界见源章节','逐条核源章节判据','完整规则必须读取对应源章节']:
                    self.assertNotIn(old,copy)
            self.assertIn('不是',m['compact']['90s'])

    def test_distinct_decision_and_stop_not_one_template(self):
        self.assertEqual(len({self.registry.methods[mid]['decision_rule'] for mid in REVISED}),13)
        self.assertEqual(len({self.registry.methods[mid]['stop_rule'] for mid in REVISED}),13)

    def test_source_high_risk_boundaries_survive_short_compression(self):
        # These are explicit course invariants, not claims of learner transfer.
        for mid,groups in {'R05':[['问因'],['因果']],'R07':[['一项','之一'],['并列','同层']],'R08':[['事实']],'R10':[['状态']],'R11':[['否定'],['条件']],'R12':[['定位','位置'],['答案','正确选项']],'R14':[['区'],['位置','定位','出处']],'R16':[['单段'],['范围']],'R17':[['缺'],['暂留','就停']]}.items():
            for duration in ['10s','30s','90s']:
                with self.subTest(method=mid,duration=duration):
                    for alternatives in groups:
                        self.assertTrue(any(marker in self.registry.methods[mid]['compact'][duration] for marker in alternatives),alternatives)

    def test_generated_student_guides_exist_for_entire_reading_module(self):
        assets=build(self.registry)
        for m in self.registry.methods.values():
            if m['question_type']=='阅读理解':
                path='student-guides/'+m['method_id']+'-'+m['brand_name']+'.md'
                self.assertIn(path,assets)
                self.assertIn(m['stop_rule'],assets[path])

    def test_no_true_case_or_participant_promoted_from_editorial_review(self):
        for mid in REVISED:
            m=self.registry.methods[mid]
            self.assertTrue(all(load(path)['status']=='evidence_gap' for path in m['cases'].values()))
            self.assertIsNone(m['first_use_test']['action_success'])
            self.assertIsNone(m['evaluation']['trigger_precision'])

    def test_student_ready_gate_rejects_generic_delegate(self):
        r=Registry(); r.methods['R03']['decision_rule']='逐条核源章节判据'
        with self.assertRaisesRegex(ValueError,'delegates'): r.validate()
    def test_static_review_cannot_point_at_other_methods_source(self):
        r=Registry(); r.methods['R03']['static_design_review']['source_section_ids']=r.methods['R04']['section_ids']
        with self.assertRaisesRegex(ValueError,'source mismatch'): r.validate()

if __name__=='__main__': unittest.main()
