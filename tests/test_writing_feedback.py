"""Host review transport tests. Fixtures are synthetic program records, not exams."""
from copy import deepcopy
import json
import unittest
from jsonschema import ValidationError
from core.registry import Registry,validate_schema
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.evidence import validate_graph
from core.writing_feedback import ORDERS
from renderers import render

def span(field,value): return {'field':field,'start':0,'end':len(value),'quote':value}

def fixture(kind='应用文'):
    # Deliberately not an English test: no fake teaching success or real student.
    draft='synthetic program first. synthetic program second.'
    stem='synthetic program task; no real exam or student'
    s=span('student_text',draft); t=span('stem',stem)
    mid='A09' if kind=='应用文' else 'W15'
    rubric='254fa3adfb42db4e' if kind=='应用文' else 'd2dc77b78b7ce906'
    boundary='f8cfb194a81aad6e' if kind=='应用文' else '7b4c299267a685c2'
    sections=[{'key':key,'text':'synthetic section '+key,'evidence':[s,t]} for key in ORDERS[kind] if key!='corrections']
    review={'schema_version':'1.0.0','question_type':kind,'kind':'correction','reviewer':'synthetic-program-fixture-not-teacher-study','review_status':'reviewed','source_section_ids':[rubric,boundary],'student_text_complete':True,'student_text_excludes_given_starters':True,'sections':sections,
            'corrections':[{'original':{'field':'student_text','start':0,'end':23,'quote':draft[:23]},'replacement':'synthetic replacement first','reason':'synthetic transport assertion','kind':'error'},
                           {'original':{'field':'student_text','start':25,'end':len(draft),'quote':draft[25:]},'replacement':'synthetic replacement second','reason':'synthetic optional assertion','kind':'optional'}],
            'reviewed_student_spans':[s],'proposed_score':{'scale':15 if kind=='应用文' else 25,'lower':10 if kind=='应用文' else 16,'upper':12 if kind=='应用文' else 20,'band':'第四档','rationale':'synthetic program grade range, NOT observed real scoring','evidence':[s,t],'source_section_id':rubric,'handwriting_applied':False,'original_handwriting_reference':None}}
    q={'question_id':'synthetic-review-transport-'+mid,'question_type':kind,'stem':stem,'student_text':draft,'writing_review':review,'observations':[{'method_id':mid,'reviewed':True,'evidence':[s,t]}]}
    if kind=='读后续写':
        q.update(passage='synthetic source; not a real story',continuation_starters=['synthetic first starter','synthetic second starter'])
        review['sections'][1]['evidence'].extend([span('passage',q['passage']),*(span('continuation_starters:'+str(i),v) for i,v in enumerate(q['continuation_starters']))])
    return q

class WritingFeedbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=QuestionAnalyzer(cls.r)

    def test_full_external_correction_preserves_two_independent_orders(self):
        for kind in ORDERS:
            q=fixture(kind); out=self.a.analyze(q)
            validate_schema('question-analysis',out)
            f=out['writing_feedback']; self.assertEqual(f['scope'],'full_correction')
            self.assertIsNone(out['answer']); self.assertFalse(out['content_eligible'])
            self.assertEqual(out['review_scope'],'external_writing_review')
            self.assertEqual(f['score_status'],'external_proposal_not_certified')
            body=render(out,'legacy-wechat',self.r)
            positions=[]
            for key in ORDERS[kind]:
                marker='synthetic replacement first' if key=='corrections' else 'synthetic section '+key
                positions.append(body.index(marker))
            self.assertEqual(positions,sorted(positions))
            self.assertIn('synthetic replacement second',body)
            self.assertIn('可选润色，不算确定错误',body)
            self.assertNotIn('# ',body); self.assertNotIn('1. ',body)
            self.assertNotIn('\n原句：',body); self.assertNotIn('\n改法：',body)

    def test_machine_exports_keep_all_corrections_and_evidence(self):
        out=self.a.analyze(fixture())
        for renderer in ['structured','content-export']:
            projected=json.loads(render(out,renderer,self.r))
            self.assertEqual(projected['writing_feedback'],out['writing_feedback'])
            self.assertEqual(projected['evidence_graph'],out['evidence_graph'])

    def test_feedback_graph_has_current_input_and_independent_trigger_paths(self):
        q=fixture(); out=self.a.analyze(q); g=out['evidence_graph']
        self.assertTrue(out['writing_feedback']['evidence_ids'])
        self.assertTrue(any(n['type']=='verification' and n.get('candidate')=='student_draft' for n in g['nodes']))
        validate_graph(g,q)
        q['student_text']='another draft'
        with self.assertRaises(ValueError): validate_graph(g,q)

    def test_wrong_module_and_rubric_rejected(self):
        for mutation in ['type','source','scale','rubric','band']:
            q=fixture(); review=q['writing_review']
            if mutation=='type': review['question_type']='读后续写'
            elif mutation=='source': review['source_section_ids'].append('d2dc77b78b7ce906')
            elif mutation=='scale': review['proposed_score']['scale']=25
            elif mutation=='rubric': review['proposed_score']['source_section_id']='f8cfb194a81aad6e'
            else: review['proposed_score']['band']='第六档'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_missing_materials_or_coverage_withholds_score(self):
        for mutation in ['task','draft','complete','coverage','trigger','section','starters','includes_starters']:
            q=fixture('读后续写'); review=q['writing_review']
            if mutation=='task': q['stem']=''; q['observations'][0]['evidence']=q['observations'][0]['evidence'][:1]; [s.update(evidence=s['evidence'][:1]) for s in review['sections']]; review['proposed_score']['evidence']=review['proposed_score']['evidence'][:1]
            elif mutation=='draft': review['student_text_complete']=False
            elif mutation=='complete':
                q['passage']=''
                [s.update(evidence=[e for e in s['evidence'] if e['field']!='passage']) for s in review['sections']]
            elif mutation=='coverage': review['reviewed_student_spans']=[]
            elif mutation=='trigger': q.pop('observations')
            elif mutation=='section': review['sections']=[s for s in review['sections'] if s['key']!='anchors']
            elif mutation=='starters':
                q['continuation_starters']=q['continuation_starters'][:1]
                [s.update(evidence=[e for e in s['evidence'] if e['field']!='continuation_starters:1']) for s in review['sections']]
            else: review['student_text_excludes_given_starters']=False
            out=self.a.analyze(q); f=out['writing_feedback']
            self.assertEqual(f['scope'],'partial_feedback'); self.assertIsNone(f['review']['proposed_score'])
            self.assertEqual(f['score_status'],'withheld')
            self.assertIn('暂不作完整评分',render(out,'student',self.r))

    def test_missing_story_actually_suppresses_plot_and_rewrite_not_just_warning(self):
        q=fixture('读后续写'); q['passage']=''
        for s in q['writing_review']['sections']: s['evidence']=[e for e in s['evidence'] if e['field']!='passage']
        out=self.a.analyze(q); body=render(out,'legacy-wechat',self.r)
        self.assertEqual(out['writing_feedback']['review']['sections'],[])
        self.assertNotIn('synthetic section diagnostics',body)
        self.assertNotIn('synthetic section revised_text',body)
        self.assertIn('synthetic replacement first',body)

    def test_unreviewed_never_delivers_diagnosis_rewrite_or_grade(self):
        q=fixture(); q['writing_review']['review_status']='unreviewed'
        out=self.a.analyze(q); body=render(out,'legacy-wechat',self.r)
        self.assertEqual(out['writing_feedback']['scope'],'unreviewed')
        self.assertNotIn('synthetic section',body); self.assertNotIn('synthetic replacement',body)
        self.assertIsNone(out['writing_feedback']['review']['proposed_score'])

    def test_fabricated_original_and_overlapping_corrections_rejected(self):
        for mutation in ['quote','overlap','field']:
            q=fixture(); c=q['writing_review']['corrections']
            if mutation=='quote': c[0]['original']['quote']='invented original'
            elif mutation=='overlap': c[1]['original']=deepcopy(c[0]['original'])
            else: c[0]['original']=span('stem',q['stem'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_handwriting_penalty_not_proven_by_text_or_a_filename(self):
        q=fixture(); score=q['writing_review']['proposed_score']; score.update(handwriting_applied=True,original_handwriting_reference='not-reviewed-image.png')
        with self.assertRaisesRegex(ValueError,'original-image'): self.a.analyze(q)

    def test_guidance_no_fake_student_corrections_or_score(self):
        q=fixture(); q['writing_review']['kind']='guidance'
        with self.assertRaisesRegex(ValueError,'guidance'): self.a.analyze(q)
        q['writing_review'].update(corrections=[],proposed_score=None)
        out=self.a.analyze(q); self.assertEqual(out['writing_feedback']['scope'],'guidance')
        self.assertIsNone(out['answer'])

    def test_empty_evidence_and_duplicate_sections_rejected(self):
        q=fixture(); q['writing_review']['sections'][0]['evidence']=[]
        with self.assertRaises(ValidationError): self.a.analyze(q)
        q=fixture(); q['writing_review']['sections'].append(deepcopy(q['writing_review']['sections'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.a.analyze(q)

    def test_paper_never_promotes_proposed_writing_grades_to_closed_answers(self):
        out=PaperAnalyzer(self.a).analyze({'paper_id':'synthetic-program-paper','questions':[fixture()]})
        self.assertEqual(out['recommendations'],[]); self.assertEqual(out['evidence_complete_count'],0)

if __name__=='__main__': unittest.main()
