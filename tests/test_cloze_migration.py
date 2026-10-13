"""Archived b04 cloze controls; the current evidence-driven epoch has separate tests."""
import unittest
from copy import deepcopy
from core.registry import Registry,load
from core.analyzer import QuestionAnalyzer
from scripts.generate_assets import build

IDS={'C'+str(i).zfill(2) for i in range(1,10)}

def role_fixture(mid,role=None):
    s={'field':'passage','start':0,'end':1,'quote':'x'}
    rel={'method_id':mid,'candidate':'A','effect':'retain','claim':'structural fixture, not an exam','evidence':[s],'decision_rule_check':'program role gate fixture','stop_rule_check':'program stop field','verification':'program verification field','reviewer':'synthetic-program-test-not-student','review_status':'reviewed'}
    if role is not None: rel['execution_role']=role
    return {'question_id':'role-guard-'+mid,'question_type':'完形填空','stem':'program fixture','passage':'x','options':{'A':'x'},'observations':[{'method_id':mid,'evidence':[s],'reviewed':True}],'relations':[rel]}

class ClozeMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')

    def test_nine_entries_ready_but_only_two_core_teaching_entries(self):
        methods=[m for m in self.r.methods.values() if m['question_type']=='完形填空']
        self.assertEqual(len(methods),9)
        self.assertEqual({m['method_id'] for m in methods if m['method_type']!='sub_action'},{'C01','C02'})
        self.assertTrue(all(m['student_ready'] and m['entry_copy'] for m in methods))

    def test_sources_roles_types_and_snapshots_not_replaced(self):
        for mid in IDS:
            m=self.r.methods[mid]; old=load('method-registry/history/'+mid+'/1.0.0.yaml')
            self.assertEqual(m['version'],'1.1.0')
            for field in ['source_name','primary_role','secondary_roles','method_type','output_type']:
                self.assertEqual(m[field],old[field])
            for ref in old['source_references']: self.assertIn(ref,m['source_references'])
            self.assertTrue(set(old['section_ids'])<=set(m['section_ids']))
            self.assertEqual(m['status'],'candidate'); self.assertEqual(m['practical_value'],'Useful')
            self.assertIsNone(m['evaluation']['trigger_precision'])

    def test_two_pass_order_has_direct_source_dependency(self):
        for mid in ['C01','C02']:
            self.assertIn('3f36ea92a4769ee5',self.r.methods[mid]['section_ids'])
            self.assertIn('按原空号走两遍',self.r.full(mid))

    def test_all_guides_preserve_actions_and_stop_independently(self):
        assets=build(self.r)
        for mid in IDS:
            m=self.r.methods[mid]; guide=assets['student-guides/'+mid+'-'+m['brand_name']+'.md']
            self.assertIn(m['core_action'],guide); self.assertIn(m['stop_rule'],guide)
            self.assertIn(m['challenge_prompt'],guide)
            self.assertTrue(all(m['compact'][duration] for duration in ['10s','30s','90s']))

    def test_individual_decisions_and_brakes_not_generic_placeholder(self):
        for key in ['decision_rule','stop_rule','visual_formula','counterexamples']:
            self.assertEqual(len({str(self.r.methods[mid][key]) for mid in IDS}),9)

    def test_all_primary_roles_cannot_decide(self):
        for mid in IDS:
            with self.subTest(method=mid),self.assertRaisesRegex(ValueError,'overreach'):
                QuestionAnalyzer(self.r).analyze(role_fixture(mid))

    def test_c01_requires_explicit_secondary_decider_stage(self):
        out=QuestionAnalyzer(self.r).analyze(role_fixture('C01','decider'))
        self.assertEqual(out['answer'],'A')
        self.assertEqual([s['role'] for s in out['method_chain']],['framework','decider'])
        self.assertIn('不是框架本身',out['method_chain'][-1]['input'])
        self.assertEqual(out['review_scope'],'external_semantic_review')

    def test_other_subactions_cannot_claim_c01_secondary_role(self):
        for mid in IDS-{'C01'}:
            with self.subTest(method=mid),self.assertRaisesRegex(ValueError,'Undeclared'):
                QuestionAnalyzer(self.r).analyze(role_fixture(mid,'decider'))

    def test_cases_and_participants_not_promoted_from_schematic_review(self):
        for mid in IDS:
            m=self.r.methods[mid]
            self.assertTrue(all(load(p)['status']=='evidence_gap' for p in m['cases'].values()))
            self.assertIsNone(m['first_use_test']['action_success'])
            self.assertIn('不是真题',m['compact']['90s'])

if __name__=='__main__': unittest.main()
