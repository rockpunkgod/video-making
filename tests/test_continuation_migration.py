"""Continuation source, role and functional-scaffold regression tests."""
import unittest
from core.registry import Registry,load
from core.analyzer import QuestionAnalyzer
from scripts.generate_assets import build

IDS={'W'+str(i).zfill(2) for i in range(1,17)}

class ContinuationMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry()

    def test_all_nodes_have_static_entries_without_branding_every_rule(self):
        self.assertEqual({m['method_id'] for m in self.r.methods.values() if m['question_type']=='读后续写'},IDS)
        self.assertTrue(all(self.r.methods[mid]['student_ready'] for mid in IDS))
        self.assertEqual(self.r.methods['W14']['method_type'],'category')
        self.assertEqual(self.r.methods['W15']['method_type'],'internal_rule')
        self.assertEqual(self.r.methods['W16']['method_type'],'framework')

    def test_histories_preserve_original_identity_and_roles(self):
        for mid in IDS:
            old=load('method-registry/history/'+mid+'/1.0.0.yaml'); m=self.r.methods[mid]
            self.assertEqual(m['version'],'1.1.0')
            for key in ['source_name','source_alias','primary_role','secondary_roles','method_type','output_type','source_references']:
                self.assertEqual(m.get(key),old.get(key))
            self.assertTrue(set(old['section_ids'])<=set(m['section_ids']))
            self.assertEqual(m['static_design_review']['source_section_ids'],m['section_ids'])

    def test_all_guides_preserve_independent_actions_stops_and_short_versions(self):
        assets=build()
        for mid in IDS:
            m=self.r.methods[mid]; guide=assets['student-guides/'+mid+'-'+m['brand_name']+'.md']
            for value in [m['core_action'],m['stop_rule'],m['challenge_prompt'],*(m['compact'][key] for key in ['10s','30s','90s'])]: self.assertIn(value,guide)
        for key in ['decision_rule','stop_rule','visual_formula','challenge_prompt']:
            self.assertEqual(len({self.r.methods[mid][key] for mid in IDS}),16)

    def test_five_step_parent_heading_now_depends_on_actual_actions(self):
        self.assertTrue({'40089c4aea5930c9','81f56745e0f0ef4f','2f8f6bf8b2c518b4','b7f00dc50a26467d','d6a05f90dcbf2050'}<=set(self.r.methods['W01']['section_ids']))

    def test_scaffolding_and_score_have_direct_non_penalty_boundaries(self):
        for mid in ['W01','W02','W15','W16']: self.assertIn('7b4c299267a685c2',self.r.methods[mid]['section_ids'])
        for mid in ['W01','W02','W15']: self.assertIn('540b6fb2783f6027',self.r.methods[mid]['section_ids'])
        self.assertIn('529088be97f3f185',self.r.methods['W15']['section_ids'])
        self.assertIn('363d35dec7fda958',self.r.methods['W09']['section_ids'])
        self.assertIn('d9120aa3501ea2ec',self.r.methods['W11']['section_ids'])

    def test_ptsd_stays_source_alias_not_student_brand(self):
        m=self.r.methods['W03']; self.assertEqual(m['brand_name'],'剧情四格')
        self.assertIn('PTSD',m['source_name'])
        self.assertIn('3f0307af95397320',m['section_ids'])

    def test_auxiliary_roles_cannot_retain_a_final_answer(self):
        for mid in IDS:
            # Pure program fixture; never counted as an exam/learner observation.
            span={'field':'passage','start':0,'end':1,'quote':'x'}
            q={'question_id':'continuation-role-guard','question_type':'读后续写','stem':'program fixture','passage':'x','continuation_starters':['program first','program second'],
               'observations':[{'method_id':mid,'reviewed':True,'evidence':[span]}],
               'relations':[{'method_id':mid,'candidate':'a draft','effect':'retain','claim':'synthetic fixture','evidence':[span],'decision_rule_check':'program only','stop_rule_check':'program only','verification':'program only','reviewer':'synthetic-not-student','review_status':'reviewed'}]}
            with self.subTest(method=mid),self.assertRaisesRegex(ValueError,'overreach'): QuestionAnalyzer(self.r).analyze(q)

    def test_schematics_do_not_promote_empirical_or_case_status(self):
        for mid in IDS:
            m=self.r.methods[mid]
            self.assertEqual(m['status'],'candidate'); self.assertEqual(m['practical_value'],'Useful')
            self.assertIsNone(m['first_use_test']['action_success']); self.assertIsNone(m['evaluation']['trigger_precision'])
            self.assertTrue(all(load(path)['status']=='evidence_gap' for path in m['cases'].values()))

if __name__=='__main__': unittest.main()
