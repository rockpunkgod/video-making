"""Source-bound application entry checks; no simulated learner outcomes."""
import unittest
from core.registry import Registry,load
from core.analyzer import QuestionAnalyzer
from scripts.generate_assets import build

IDS={'A'+str(i).zfill(2) for i in range(1,11)}

class ApplicationMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry()

    def test_ten_entries_ready_without_turning_templates_into_brands(self):
        methods=[m for m in self.r.methods.values() if m['question_type']=='应用文']
        self.assertEqual({m['method_id'] for m in methods},IDS)
        self.assertTrue(all(m['student_ready'] and m['entry_copy'] for m in methods))
        self.assertEqual(self.r.methods['A08']['method_type'],'category')
        self.assertEqual(self.r.methods['A09']['method_type'],'internal_rule')

    def test_snapshots_preserve_roles_types_and_old_sources(self):
        for mid in IDS:
            old=load('method-registry/history/'+mid+'/1.0.0.yaml'); m=self.r.methods[mid]
            self.assertEqual(m['version'],'1.1.0')
            for key in ['source_name','primary_role','secondary_roles','method_type','output_type','source_references']:
                self.assertEqual(m[key],old[key])
            self.assertTrue(set(old['section_ids'])<=set(m['section_ids']))
            self.assertEqual(m['static_design_review']['source_section_ids'],m['section_ids'])

    def test_independent_entries_include_exact_actions_and_brakes(self):
        assets=build()
        for mid in IDS:
            m=self.r.methods[mid]; guide=assets['student-guides/'+mid+'-'+m['brand_name']+'.md']
            for text in [m['core_action'],m['stop_rule'],m['challenge_prompt'],*(m['compact'][key] for key in ['10s','30s','90s'])]: self.assertIn(text,guide)
        for key in ['decision_rule','stop_rule','visual_formula','challenge_prompt']:
            self.assertEqual(len({self.r.methods[mid][key] for mid in IDS}),10)

    def test_scoring_and_reference_cycle_have_direct_boundary_sources(self):
        for mid in ['A01','A09']:
            self.assertIn('f8cfb194a81aad6e',self.r.methods[mid]['section_ids'])
            self.assertIn('ed19bd45d6bc3762',self.r.methods[mid]['section_ids'])
        self.assertIn('1b1197e2fa02ee07',self.r.methods['A06']['section_ids'])
        self.assertIn('e68392b5352c1bc7',self.r.methods['A08']['section_ids'])

    def test_all_primary_roles_cannot_retain_an_answer(self):
        for mid in IDS:
            # Program-only schema fixture, not an authored exam or student draft.
            span={'field':'stem','start':0,'end':1,'quote':'x'}
            q={'question_id':'application-role-guard','question_type':'应用文','stem':'x','observations':[{'method_id':mid,'reviewed':True,'evidence':[span]}],
               'relations':[{'method_id':mid,'candidate':'a draft','effect':'retain','claim':'synthetic program fixture','evidence':[span],'decision_rule_check':'program fixture','stop_rule_check':'program fixture','verification':'program fixture','reviewer':'synthetic-not-student','review_status':'reviewed'}]}
            with self.subTest(method=mid),self.assertRaisesRegex(ValueError,'overreach'): QuestionAnalyzer(self.r).analyze(q)

    def test_source_wordcount_conflict_is_visible_not_silently_normalized(self):
        risk=next(x for x in self.r.risks if x['risk_id']=='APPLICATION-TRAINING-WORDCOUNT-TENSION')
        self.assertIn(risk['source_quote'],self.r.sources['sections'][risk['section_id']]['content'])
        for mid in risk['affected_methods']: self.assertIn(risk['action'],self.r.full(mid))

    def test_static_revision_never_promotes_real_cases_or_effectiveness(self):
        for mid in IDS:
            m=self.r.methods[mid]
            self.assertEqual(m['status'],'candidate'); self.assertEqual(m['practical_value'],'Useful')
            self.assertIsNone(m['first_use_test']['action_success']); self.assertIsNone(m['evaluation']['trigger_precision'])
            self.assertTrue(all(load(path)['status']=='evidence_gap' for path in m['cases'].values()))

if __name__=='__main__': unittest.main()
