"""Synthetic projection consistency tests, not English or learner acceptance."""
from copy import deepcopy
import hashlib,json,unittest
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.writing_feedback import ORDERS
from renderers import render
from tests.test_writing_feedback import fixture,span

MODES=['student','legacy-wechat','structured','content-export']

def guidance(kind='应用文'):
    q=fixture(kind);q.pop('student_text');q.pop('observations')
    evidence=[span('stem',q['stem'])]
    if kind=='读后续写':
        evidence += [span('passage',q['passage'])]+[span('continuation_starters:'+str(i),s) for i,s in enumerate(q['continuation_starters'])]
    q['writing_review'].update(kind='guidance',student_text_complete=False,
        sections=[{'key':'overall','text':'Synthetic natural guidance paragraph.','evidence':evidence},
                  {'key':'practice','text':'Synthetic observable practice action.','evidence':evidence}],
        corrections=[],reviewed_student_spans=[],proposed_score=None)
    return q

def resign_anchor(a):
    fingerprint=hashlib.sha256(json.dumps(a['writing_feedback'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    for n in a['evidence_graph']['nodes']:
        if n.get('candidate')=='writing_feedback_projection':n['artifact_fingerprint']=fingerprint

class WritingProjectionBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=Registry();cls.analyzer=QuestionAnalyzer(cls.r)
    def reject(self,a):
        for mode in MODES:
            with self.subTest(mode=mode),self.assertRaises(ValueError):render(a,mode,self.r)
    def test_actual_guidance_bodies_and_machine_projections_still_work(self):
        for kind in ['应用文','读后续写']:
            q=guidance(kind);before=deepcopy(q);a=self.analyzer.analyze(q)
            self.assertEqual(q,before);self.assertIsNone(a['answer'])
            self.assertEqual(a['writing_feedback']['scope'],'guidance')
            for mode in MODES:self.assertIn('Synthetic natural guidance paragraph.',render(a,mode,self.r))
    def test_returned_order_is_not_shared_with_frozen_module_or_other_outputs(self):
        for kind in ['应用文','读后续写']:
            original_order=list(ORDERS[kind]);a=self.analyzer.analyze(guidance(kind))
            self.assertIsNot(a['writing_feedback']['section_order'],ORDERS[kind])
            a['writing_feedback']['section_order'].reverse()
            self.assertEqual(ORDERS[kind],original_order)
            next_analysis=self.analyzer.analyze(guidance(kind))
            self.assertEqual(next_analysis['writing_feedback']['section_order'],original_order)
            resign_anchor(a);self.reject(a)
    def test_changed_guidance_text_cannot_reuse_old_graph(self):
        for kind in ['应用文','读后续写']:
            a=self.analyzer.analyze(guidance(kind))
            a['writing_feedback']['review']['sections'][0]['text']='Synthetic unreviewed replacement.'
            self.reject(a)
    def test_source_order_reviewer_kind_and_notes_are_bound(self):
        original=self.analyzer.analyze(guidance())
        for field in ['source','order','reviewer','kind','limits']:
            a=deepcopy(original);f=a['writing_feedback']
            if field=='source':f['source_document']='other/source.md'
            elif field=='order':f['section_order']=list(reversed(f['section_order']))
            elif field=='reviewer':f['review']['reviewer']='different-reviewer'
            elif field=='kind':f['review']['kind']='correction'
            else:f['limitations']=['Synthetic altered release boundary.']
            with self.subTest(field=field):self.reject(a)
    def test_rehashed_cross_module_source_still_fails_input_admission(self):
        original=self.analyzer.analyze(guidance())
        for field in ['document','section_ids']:
            a=deepcopy(original)
            if field=='document':a['writing_feedback']['source_document']='gaokao-writing/references/continuation-writing-and-correction.md'
            else:a['writing_feedback']['review']['source_section_ids']=['d2dc77b78b7ce906']
            resign_anchor(a)
            with self.subTest(field=field):self.reject(a)
    def test_rehashed_guidance_cannot_borrow_stem_claim_to_invent_student_correction(self):
        q=guidance();q['writing_review']['sections'][0]['text']='Synthetic replacement；Synthetic reason'
        a=self.analyzer.analyze(q)
        a['writing_feedback']['review']['corrections']=[{'original':q['writing_review']['sections'][0]['evidence'][0],
            'replacement':'Synthetic replacement','reason':'Synthetic reason','kind':'error'}]
        resign_anchor(a);self.reject(a)
    def test_rehashed_duplicate_or_foreign_sections_are_rejected(self):
        original=self.analyzer.analyze(guidance())
        for change in ['duplicate','foreign-key','order']:
            a=deepcopy(original)
            if change=='duplicate':a['writing_feedback']['review']['sections'].append(deepcopy(a['writing_feedback']['review']['sections'][0]))
            elif change=='foreign-key':a['writing_feedback']['review']['sections'][0]['key']='anchors'
            else:a['writing_feedback']['section_order'].reverse()
            resign_anchor(a)
            with self.subTest(change=change):self.reject(a)
    def test_scope_and_unreviewed_status_cannot_be_upgraded_after_analysis(self):
        q=guidance();q['writing_review']['review_status']='unreviewed';a=self.analyzer.analyze(q)
        for mode in ['student','legacy-wechat']:self.assertNotIn('Synthetic natural guidance paragraph.',render(a,mode,self.r))
        a['writing_feedback']['review']['review_status']='reviewed';a['writing_feedback']['scope']='guidance'
        self.reject(a)
    def test_unreviewed_to_guidance_cannot_be_upgraded_by_rehashing_only(self):
        q=guidance();q['writing_review']['review_status']='unreviewed';a=self.analyzer.analyze(q)
        a['writing_feedback']['review']['review_status']='reviewed';a['writing_feedback']['scope']='guidance'
        resign_anchor(a);self.reject(a)
    def test_partial_correction_cannot_be_upgraded_by_rehashing_only(self):
        q=fixture();q['writing_review']['student_text_complete']=False;q['writing_review']['proposed_score']=None
        a=self.analyzer.analyze(q);self.assertEqual(a['writing_feedback']['scope'],'partial_feedback')
        a['writing_feedback']['scope']='full_correction';resign_anchor(a);self.reject(a)
    def test_reviewed_guidance_without_method_trigger_stays_deliverable(self):
        a=self.analyzer.analyze(guidance());self.assertEqual(a['writing_feedback']['scope'],'guidance')
        self.assertTrue(any(n['type']=='relation' and n.get('reviewed') is False for n in a['evidence_graph']['nodes']))
        for mode in MODES:self.assertIn('Synthetic natural guidance paragraph.',render(a,mode,self.r))
    def test_claimed_completion_and_student_fingerprint_are_bound(self):
        original=self.analyzer.analyze(guidance())
        for field in ['complete','fingerprint','sections']:
            a=deepcopy(original)
            if field=='complete':a['writing_feedback']['review']['student_text_complete']=True
            elif field=='fingerprint':a['writing_feedback']['student_text_sha256']='0'*64
            else:a['writing_feedback']['review']['sections'].reverse()
            with self.subTest(field=field):self.reject(a)
    def test_guide_evidence_change_and_id_removal_are_bound(self):
        original=self.analyzer.analyze(guidance())
        for field in ['span','ids']:
            a=deepcopy(original)
            if field=='span':
                original_span=a['writing_feedback']['review']['sections'][0]['evidence'][0]
                a['writing_feedback']['review']['sections'][0]['evidence']=[{**original_span,'end':9,'quote':original_span['quote'][:9]}]
            else:a['writing_feedback']['evidence_ids']=[]
            with self.subTest(field=field):self.reject(a)
    def test_projection_anchor_and_its_edges_cannot_be_removed(self):
        original=self.analyzer.analyze(guidance())
        anchors=[n for n in original['evidence_graph']['nodes'] if n.get('candidate')=='writing_feedback_projection']
        self.assertEqual(len(anchors),1);nid=anchors[0]['id']
        for mutation in ['anchor','edges','fingerprint']:
            a=deepcopy(original)
            if mutation=='anchor':
                a['evidence_graph']['nodes']=[n for n in a['evidence_graph']['nodes'] if n['id']!=nid]
                a['evidence_graph']['edges']=[e for e in a['evidence_graph']['edges'] if e['to']!=nid]
            elif mutation=='edges':a['evidence_graph']['edges']=[e for e in a['evidence_graph']['edges'] if e['to']!=nid]
            else:next(n for n in a['evidence_graph']['nodes'] if n['id']==nid)['artifact_fingerprint']='0'*64
            with self.subTest(mutation=mutation):self.reject(a)
    def test_rehashing_text_alone_cannot_replace_original_claim_path(self):
        a=self.analyzer.analyze(guidance())
        a['writing_feedback']['review']['sections'][0]['text']='Synthetic new text, no old claim path.'
        resign_anchor(a);self.reject(a)
    def test_rehashing_evidence_alone_cannot_borrow_another_section_source(self):
        a=self.analyzer.analyze(guidance('读后续写'))
        a['writing_feedback']['review']['sections'][0]['evidence'][0]={'field':'stem','start':0,'end':9,'quote':a['writing_feedback']['review']['sections'][0]['evidence'][0]['quote'][:9]}
        resign_anchor(a);self.reject(a)
    def test_actual_corrections_work_but_changed_replacement_reason_or_kind_rejected(self):
        for kind in ['应用文','读后续写']:
            original=self.analyzer.analyze(fixture(kind))
            for mode in MODES:self.assertTrue(render(original,mode,self.r))
            for key,value in [('replacement','Synthetic swapped replacement.'),('reason','Synthetic swapped reason.'),('kind','optional')]:
                a=deepcopy(original);a['writing_feedback']['review']['corrections'][0][key]=value
                with self.subTest(kind=kind,key=key):self.reject(a)
    def test_rehashing_changed_correction_still_requires_own_original_claim(self):
        a=self.analyzer.analyze(fixture());a['writing_feedback']['review']['corrections'][0]['replacement']='Synthetic new replacement.'
        resign_anchor(a);self.reject(a)
    def test_duplicate_anchor_or_foreign_source_edge_are_rejected(self):
        original=self.analyzer.analyze(guidance())
        anchor=next(n for n in original['evidence_graph']['nodes'] if n.get('candidate')=='writing_feedback_projection')
        a=deepcopy(original);extra=deepcopy(anchor);extra['id']='new-synthetic-duplicate-anchor';a['evidence_graph']['nodes'].append(extra);self.reject(a)
        a=deepcopy(original);a['evidence_graph']['edges'].append({'from':anchor['id'],'to':anchor['id'],'type':'supports'});self.reject(a)

if __name__=='__main__':unittest.main()
