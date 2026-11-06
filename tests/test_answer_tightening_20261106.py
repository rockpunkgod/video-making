"""Program controls for explicit evidence, not English/learner certification."""
from copy import deepcopy
import unittest
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from scripts.align_answer_20261106 import TARGET,PREVIOUS,RULES
from scripts.generate_assets import build
from unittest.mock import patch
from scripts.rebind_question_corpus import approved_changes
from core.registry import ROOT
import json


class TighteningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=Registry();cls.old=Registry(snapshot_commit=PREVIOUS)
        cls.analyzer=QuestionAnalyzer(cls.r)

    def fixture(self,mid):
        text='The library keeps printed books. They remain available.'
        span={'field':'passage','start':0,'end':len(text),'quote':text}
        return {'question_id':'synthetic-criteria-'+mid,'question_type':self.r.methods[mid]['question_type'],
            'task_type':'main_idea' if mid=='R16' else 'synthetic interface, not an exam','stem':'Synthetic role/evidence wiring only',
            'passage':text,'options':{'A':'The printed books remain available.','B':'The library removed all printed books.'},
            'requested_chain':[mid],'observations':[{'method_id':mid,'reviewed':True,'evidence':[span]}],
            'relations':[{'method_id':mid,'execution_role':'decider','candidate':c,'effect':effect,
                'claim':'synthetic content comparison '+c,'evidence':[span],
                'decision_rule_check':'Compare the retained books with the incompatible removal claim.',
                'stop_rule_check':'Not relying on repetition, grouping, color or a remaining option.',
                'verification':'Both candidate statements compared to the provided content.',
                'reviewer':'synthetic program control, not a student or independent English reviewer',
                'review_status':'reviewed'} for c,effect in [('A','retain'),('B','eliminate')]]}

    def test_primary_jobs_and_student_readiness_preserved(self):
        self.assertEqual(self.r.index['source_baseline']['commit'],TARGET)
        self.assertEqual(self.r.validate()['methods'],82)
        self.assertEqual(self.r.case_inventory(),self.old.case_inventory())
        changed={k for k in self.r.methods if self.r.methods[k]['version']!=self.old.methods[k]['version']}
        self.assertEqual(changed,set(RULES))
        for mid,m in self.r.methods.items():
            for key in ('brand_name','primary_role','output_type','maturity_status','practical_value','first_use_test','evaluation'):
                self.assertEqual(m[key],self.old.methods[mid][key],(mid,key))
            self.assertFalse(m['student_ready'])
            if mid not in RULES:self.assertEqual(m['compact'],self.old.methods[mid]['compact'])

    def test_reviewed_content_can_use_explicit_secondary_decision(self):
        for mid in RULES:
            with self.subTest(mid=mid):
                result=self.analyzer.analyze(self.fixture(mid))
                self.assertEqual(result['answer'],'A')

    def test_primary_role_still_cannot_silently_decide(self):
        for mid in RULES:
            q=self.fixture(mid)
            for relation in q['relations']:relation.pop('execution_role')
            with self.subTest(mid=mid),self.assertRaisesRegex(ValueError,'method_overreach'):
                self.analyzer.analyze(q)

    def test_unreviewed_and_ungrounded_decisions_still_withheld(self):
        for mid in RULES:
            q=self.fixture(mid)
            for relation in q['relations']:relation['review_status']='unreviewed'
            with self.subTest(mid=mid):self.assertIsNone(self.analyzer.analyze(q)['answer'])
            q=self.fixture(mid)
            for relation in q['relations']:relation['evidence']=[{'field':'options.A','start':0,'end':39,'quote':'The printed books remain available.'}]
            with self.assertRaises(ValueError):self.analyzer.analyze(q)

    def test_grouping_not_promoted_and_delivery_names_reach_consumer(self):
        q=self.fixture('F01')
        with self.assertRaisesRegex(ValueError,'Undeclared secondary role'):self.analyzer.analyze(q)
        assets=build(self.r)
        for name in ('gaokao-english','gaokao-objective'):
            self.assertIn('不为辅助标签重复回文',assets[name+'/SKILL.md'])
            self.assertIn('哪一道题的题干',assets[name+'/references/reading-comprehension.md'])
            self.assertIn('已有足够证据',assets[name+'/references/cloze.md'])

    def test_common_delivery_delta_requires_exact_content_not_just_heading(self):
        changes=approved_changes(self.old,self.r)
        self.assertTrue(any(path.endswith('delivery-contract.md') for path,heading in changes))
        report=json.loads((ROOT/'provenance/runtime-alignments'/f'{TARGET}-reviewed.json').read_bytes())
        broken=deepcopy(report);broken['source_sections_reviewed'][0]['after_sha256']='0'*64
        with patch('scripts.rebind_question_corpus.json.loads',return_value=broken):
            with self.assertRaisesRegex(ValueError,'exact before/after'):
                approved_changes(self.old,self.r)


if __name__=='__main__':unittest.main()
