"""Program controls, not independent English semantics or learner results."""
from copy import deepcopy
import unittest
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.registry import Registry
from core.review_withdrawal import withdraw_review,fingerprint
from renderers import render
from tests.test_execution import fixture,seven_chain_fixture

class ReviewWithdrawalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.engine=QuestionAnalyzer(Registry())

    def pair(self):
        question=fixture(); analysis=self.engine.analyze(question)
        finding={'question_id':question['question_id'],'input_sha256':fingerprint(question),
            'analysis_sha256':fingerprint(analysis),'review_stage':'post_reveal',
            'reviewer':'PROGRAM CONTROL','reviewer_kind':'AI','reason':'PROGRAM-ONLY invalid reviewed claim',
            'withdrawn_relation_indexes':[0],'withdrawn_execution_ids':[],
            'failure_categories':['semantic_review_problem']}
        return question,analysis,finding

    def test_rejected_relation_retracts_answer_and_renders_no_closed_answer(self):
        q,a,f=self.pair(); before=deepcopy((q,a,f)); out=withdraw_review(q,a,f,self.engine)
        self.assertEqual((q,a,f),before)
        self.assertIsNone(out['analysis']['answer'])
        self.assertFalse(out['analysis']['content_eligible'])
        self.assertEqual(out['input']['relations'][0]['review_status'],'unreviewed')
        self.assertEqual(out['input']['relations'][0]['claim'],q['relations'][0]['claim'])
        for kind in ['structured','student','legacy-wechat','content-export']:
            text=render(out['analysis'],kind,self.engine.registry)
            self.assertNotIn('当前保留 ',text)
        paper=PaperAnalyzer(self.engine).analyze({'paper_id':'PROGRAM','questions':[out['input']]})
        self.assertEqual(paper['recommendations'],[])
        self.assertEqual(paper['case_candidates'],[])

    def test_withdrawn_locator_invalidates_all_transitive_consumers(self):
        q,a,f=self.pair(); f['withdrawn_relation_indexes']=[]
        f['withdrawn_execution_ids']=[q['action_executions'][0]['execution_id']]
        out=withdraw_review(q,a,f,self.engine)
        self.assertEqual(out['input']['action_executions'],[])
        self.assertIsNone(out['analysis']['answer'])
        self.assertEqual(set(out['withdrawal']['effective_execution_ids']),{x['execution_id'] for x in q['action_executions']})

    def test_withdrawn_group_invalidates_scope_decisions_and_verification(self):
        q=seven_chain_fixture(); a=self.engine.analyze(q); _,_,f=self.pair()
        f.update(question_id=q['question_id'],input_sha256=fingerprint(q),analysis_sha256=fingerprint(a),
            withdrawn_relation_indexes=[],withdrawn_execution_ids=['group-actor'])
        out=withdraw_review(q,a,f,self.engine)
        self.assertIsNone(out['analysis']['answer'])
        self.assertEqual(out['withdrawal']['effective_relation_indexes'],[0,1])
        self.assertEqual([x['execution_id'] for x in out['input']['action_executions']],['group-sentence','group-time'])
        self.assertFalse(out['analysis']['content_eligible'])

    def test_only_negative_fields_and_exact_hashes_accepted(self):
        q,a,f=self.pair()
        for changed in [{**f,'answer':'A'},{**f,'input_sha256':'wrong'},
                        {**f,'analysis_sha256':'wrong'},{**f,'question_id':'foreign'},
                        {**f,'review_stage':'before_reveal'}]:
            with self.subTest(changed=changed),self.assertRaises(ValueError): withdraw_review(q,a,changed,self.engine)

    def test_unknown_duplicate_noninteger_and_empty_targets_rejected(self):
        q,a,f=self.pair()
        for changed in [{**f,'withdrawn_relation_indexes':[True]},
                        {**f,'withdrawn_relation_indexes':[-1]},
                        {**f,'withdrawn_relation_indexes':[999]},
                        {**f,'withdrawn_relation_indexes':[0,0]},
                        {**f,'withdrawn_execution_ids':['unknown']},
                        {**f,'withdrawn_relation_indexes':[]},
                        {**f,'failure_categories':['unknown']}]:
            with self.subTest(changed=changed),self.assertRaises(ValueError): withdraw_review(q,a,changed,self.engine)

    def test_mismatching_engine_snapshot_cannot_be_backfitted(self):
        q,a,f=self.pair(); changed=deepcopy(a); changed['answer_confidence']='low'
        f['analysis_sha256']=fingerprint(changed)
        with self.assertRaisesRegex(ValueError,'Engine no longer matches'): withdraw_review(q,changed,f,self.engine)
