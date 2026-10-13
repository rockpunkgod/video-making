"""Archived b04 seven-five source controls, not current epoch or learner validation."""
import unittest
from core.registry import Registry, load
from core.analyzer import QuestionAnalyzer
from scripts.generate_assets import build
from scripts.prepare_revision import prepare

IDS={'F'+str(i).zfill(2) for i in range(2,12)}

class SevenFiveMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')

    def test_all_eleven_student_entries_are_static_ready_only(self):
        methods=[m for m in self.r.methods.values() if m['question_type']=='七选五']
        self.assertEqual(len(methods),11)
        for m in methods:
            self.assertTrue(m['student_ready'] and m['entry_copy'])
            self.assertEqual(m['status'],'candidate'); self.assertEqual(m['practical_value'],'Useful')
            self.assertIsNone(m['first_use_test']['action_success'])

    def test_old_versions_source_and_primary_roles_preserved(self):
        for mid in IDS:
            m=self.r.methods[mid]; old=load('method-registry/history/'+mid+'/1.0.0.yaml')
            self.assertEqual(m['version'],'1.2.0' if mid=='F05' else '1.1.0')
            for field in ['source_name','source_references','section_ids','primary_role','output_type','method_type']:
                self.assertEqual(m[field],old[field])
            self.assertNotEqual(m['decision_rule'],old['decision_rule'])
            self.assertNotEqual(m['stop_rule'],old['stop_rule'])
            self.assertEqual(m['static_design_review']['participant_validation'],'pending_real_participant_validation')

    def test_individual_boundaries_not_generic_copied_placeholder(self):
        for key in ['decision_rule','stop_rule','counterexamples','visual_formula']:
            values={str(self.r.methods[mid][key]) for mid in IDS}
            self.assertEqual(len(values),10)

    def test_F05_restores_source_branch_without_role_or_arbitrary_tail_overreach(self):
        m=self.r.methods['F05']; old=load('method-registry/history/F05/1.1.0.yaml')
        self.assertEqual(old['version'],'1.1.0')
        self.assertNotIn('第一段段尾',old['trigger_cues'][0])
        for text in [*m['trigger_cues'],m['four_step_card']['start'],m['practicality_gate']['trigger'],
                     m['entry_copy'],*m['compact'].values()]:
            self.assertTrue('第一段段尾' in text or '首段尾' in text)
        for field in ['primary_role','output_type','decision_rule','stop_rule','source_references']:
            self.assertEqual(m[field],old[field])
        self.assertIn('不因任意段尾',m['full']['boundaries'][0])

    def test_all_guides_keep_four_steps_brake_challenge_and_counterexample(self):
        assets=build(self.r)
        for m in self.r.methods.values():
            if m['question_type']=='七选五':
                text=assets['student-guides/'+m['method_id']+'-'+m['brand_name']+'.md']
                self.assertIn(m['stop_rule'],text); self.assertIn(m['challenge_prompt'],text)
                self.assertTrue(all(k in text for k in ['四步实战卡','10 秒版','30 秒版','90 秒版']))

    def test_grouping_roles_stay_reducers_not_deciders(self):
        for mid in ['F01','F02','F03','F04','F08']:
            self.assertEqual(self.r.methods[mid]['primary_role'],'reducer')
            self.assertEqual(self.r.methods[mid]['output_type'],'reduce')
        for mid in ['F06','F07','F10']:
            self.assertEqual(self.r.methods[mid]['primary_role'],'verifier')
        self.assertEqual(self.r.methods['F11']['method_type'],'internal_rule')
        self.assertEqual(self.r.methods['F11']['primary_role'],'decider')

    def test_each_auxiliary_method_is_rejected_if_used_to_answer(self):
        # Structural safety fixture only; no invented exam or efficacy claim.
        s={'field':'passage','start':0,'end':1,'quote':'x'}
        for mid in IDS-{'F11'}:
            q={'question_id':'role-guard-'+mid,'question_type':'七选五','stem':'structural fixture','passage':'x','options':{'A':'x'},'observations':[{'method_id':mid,'evidence':[s],'reviewed':True}],'relations':[{'method_id':mid,'candidate':'A','effect':'retain','claim':'fixture','evidence':[s],'decision_rule_check':'fixture','stop_rule_check':'fixture','verification':'fixture','reviewer':'program-test-not-participant','review_status':'reviewed'}]}
            with self.subTest(method=mid),self.assertRaisesRegex(ValueError,'overreach'):
                QuestionAnalyzer(self.r).analyze(q)

    def test_revised_examples_remain_source_schematics_not_verified_exams(self):
        for mid in IDS:
            for path in self.r.methods[mid]['cases'].values():
                self.assertEqual(load(path)['status'],'evidence_gap')
            self.assertIn('不是真题',self.r.methods[mid]['compact']['90s'])

    def test_prepare_revision_is_read_only_and_rejects_repeat(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            prepare('seven-five',{'F02':{}})
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            prepare('../anything',{'F02':{}})
        with self.assertRaisesRegex(ValueError,'Unexpected prior version'):
            prepare('seven-five',{'F02':{k:'fixture' for k in ['judge','stop','wrong','anti','counter','visual','challenge','ten','thirty','benefit','transfer']}})

if __name__=='__main__': unittest.main()
