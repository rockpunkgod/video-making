"""Synthetic lesson transport, not real exam material or semantic certification."""
from copy import deepcopy
import unittest
from video_contracts import sha,seal
from video_contracts.passage import material,export_bundle,status_manifest,require_current,validate_review


def fixture():
    e=[{'field':'passage','start':0,'end':5,'quote':'alpha'}]
    q={'question_id':'synthetic-1','number':1,'stem':'Synthetic task','options':{'A':'alpha','B':'beta'}}
    r={'reviewer':'SYNTHETIC AI','reviewer_kind':'AI','status':'reviewed','evaluation_phase':'post_reveal',
       'order':['synthetic-1'],'order_rationale':'Synthetic input order, not exam instruction.',
       'method_actions':[], 'decisions':[
           {'question_id':'synthetic-1','candidate':c,'effect':effect,'basis':'direct_text_review',
            'method_id':None,'rationale':'Synthetic comparison only','evidence':e}
           for c,effect in [('A','retain'),('B','eliminate')]],
       'segments':[{'segment_id':str(i),'question_id':'synthetic-1','kind':kind,
           'text':'合成数据，不是真题','screen_text':'合成样例','evidence':e,
           'decision_refs':[0,1] if i==0 else [],'action_refs':[],'fidelity_reviewed':True}
           for i,kind in enumerate(['comparison','closure','boundary'])]}
    p={'lesson_id':'synthetic','passage':'alpha beta','questions':[q],'methods':[],
       'review':r,'source':{'usage_status':'internal_only','redistribution_status':'unconfirmed'}}
    r['material_sha']=sha(material(p));return p


class ReviewedPassageTests(unittest.TestCase):
    def test_replay_time_and_readonly(self):
        p=fixture();prior=deepcopy(p);a=export_bundle(p,'one');b=export_bundle(p,'two')
        self.assertEqual(prior,p);self.assertEqual(a['semantic_binding_sha'],b['semantic_binding_sha'])
        self.assertNotEqual(a['envelope_sha'],b['envelope_sha'])
        self.assertEqual(a['semantic_review']['level'],'ai_reviewed')
        self.assertFalse(a['semantic_review']['independent_human_certified'])
        self.assertFalse(a['public_render_ready'])

    def test_current_status_required_and_withdrawal_blocks(self):
        b=export_bundle(fixture(),'one');require_current(b,status_manifest(b,'one'))
        with self.assertRaises(ValueError):require_current(b,None)
        for state in ['WITHDRAWN','SUPERSEDED','STALE','BLOCKED']:
            with self.assertRaises(ValueError):require_current(b,status_manifest(b,'two',state))

    def test_source_changes_do_not_reuse_status(self):
        p=fixture();b=export_bundle(p,'one');s=status_manifest(b,'one')
        p['source']['redistribution_status']='withdrawn';c=export_bundle(p,'two')
        with self.assertRaises(ValueError):require_current(c,s)

    def test_missing_competitor_cannot_close(self):
        p=fixture();p['review']['decisions'].pop()
        with self.assertRaises(ValueError):validate_review(p)

    def test_bad_span_and_borrowed_claim_are_rejected(self):
        p=fixture();p['review']['segments'][0]['decision_refs']=[99]
        with self.assertRaises(ValueError):validate_review(p)
        p=fixture();p['review']['decisions'][0]['evidence'][0]['quote']='wrong'
        with self.assertRaises(ValueError):validate_review(p)

    def test_no_method_credit_or_human_upgrade(self):
        p=fixture();p['review']['decisions'][0]['method_id']='R12'
        with self.assertRaises(ValueError):validate_review(p)
        b=export_bundle(fixture(),'one');b['semantic_review']['level']='human_certified';b=seal(b)
        with self.assertRaises(ValueError):require_current(b,None)

    def test_copy_review_and_summary_binding(self):
        p=fixture();p['review']['segments'][-1].update(summary_refs=[0],screen_text='1 B')
        with self.assertRaises(ValueError):validate_review(p)
        p['review']['segments'][-1]['screen_text']='1 A';validate_review(p)
        p['review']['segments'][-1]['fidelity_reviewed']=False
        with self.assertRaises(ValueError):validate_review(p)

    def test_boundaries_and_consumer_codes(self):
        p=fixture();p['review']['segments'].pop()
        with self.assertRaises(ValueError):validate_review(p)
        p=fixture();p['review']['segments'][0]['text']='G01'
        with self.assertRaises(ValueError):validate_review(p)

    def test_material_mutation_requires_new_review_binding(self):
        p=fixture();p['questions'][0]['options']['A']='changed'
        with self.assertRaises(ValueError):validate_review(p)
