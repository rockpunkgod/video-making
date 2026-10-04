"""Frozen-rubric transport boundaries, not real English grading observations."""
from copy import deepcopy
import unittest
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from renderers import render
from tests.test_writing_feedback import fixture, span
from tests.test_image_evidence import visual_fixture


def count_fixture(kind='应用文',count=59,points=2):
    q=fixture(kind); review=q['writing_review']; review['schema_version']='1.2.0'
    score=review['proposed_score']; before={'lower':score['lower'],'upper':score['upper']}
    # These are externally asserted test counts, not an English token counter.
    quote='词数少于 60 或多于 100，从总分中减 2 分。' if kind=='应用文' else '词数少于 120 时酌情扣分'
    score['word_count_adjustment']={'reviewer':'synthetic-count-transport-only','review_status':'reviewed','source_section_id':score['source_section_id'],'source_quote':quote,'word_count':count,'deduction_points':points,'score_before':before,'evidence':[span('student_text',q['student_text'])],'rationale':'synthetic external count assertion, not observed real scoring'}
    score.update(lower=max(0,before['lower']-points),upper=max(0,before['upper']-points))
    return q


class ScoreBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=QuestionAnalyzer(cls.r)

    def test_both_modules_reject_mismatched_unadjusted_band_ranges(self):
        for kind,lo,hi in [('应用文',13,15),('应用文',7,9),('应用文',9,13),('读后续写',21,25),('读后续写',11,15)]:
            q=fixture(kind); q['writing_review']['proposed_score'].update(lower=lo,upper=hi)
            with self.subTest(kind=kind,lo=lo,hi=hi),self.assertRaisesRegex(ValueError,'outside.*band'): self.a.analyze(q)

    def test_exact_source_band_endpoints_including_zero(self):
        for kind in ['应用文','读后续写']:
            sid='254fa3adfb42db4e' if kind=='应用文' else 'd2dc77b78b7ce906'
            for line in self.r.sources['sections'][sid]['content'].splitlines():
                cells=[c.strip() for c in line.split('|')]
                if len(cells)<4 or not (cells[1].startswith('第') or cells[1]=='0 分档'): continue
                nums=list(map(int,cells[2].split('–'))); lo,hi=nums[0],nums[-1]
                for lower,upper in [(lo,hi),(lo,lo),(hi,hi)]:
                    q=fixture(kind); q['writing_review']['proposed_score'].update(lower=lower,upper=upper,band=cells[1])
                    self.assertEqual(self.a.analyze(q)['writing_feedback']['scope'],'full_correction')

    def test_word_count_adjustment_retains_the_declared_band_but_explains_final_score(self):
        for kind,count,points in [('应用文',59,2),('应用文',101,2),('读后续写',119,1),('读后续写',100,3)]:
            out=self.a.analyze(count_fixture(kind,count,points)); score=out['writing_feedback']['review']['proposed_score']
            self.assertEqual(score['band'],'第四档')
            for renderer in ['structured','student','legacy-wechat','content-export']: render(out,renderer,self.r)
            body=render(out,'student',self.r)
            self.assertIn('档内建议',body); self.assertIn('扣'+str(points)+'分后',body)
            self.assertIn('不是程序自动评分认证',body)

    def test_word_count_thresholds_points_and_source_cannot_be_invented(self):
        for kind,mutation in [('应用文','60'),('应用文','100'),('应用文','points'),('读后续写','120'),('读后续写','150'),('应用文','quote'),('应用文','source'),('应用文','before'),('应用文','after'),('应用文','version'),('应用文','unreviewed')]:
            q=count_fixture(kind); s=q['writing_review']['proposed_score']; w=s['word_count_adjustment']
            if mutation.isdigit(): w['word_count']=int(mutation)
            elif mutation=='points': w['deduction_points']=1
            elif mutation=='quote': w['source_quote']='invented rule'
            elif mutation=='source': w['source_section_id']='d2dc77b78b7ce906'
            elif mutation=='before': w['score_before']['upper']=15
            elif mutation=='after': s['upper']=9
            elif mutation=='version': q['writing_review']['schema_version']='1.1.0'
            else: w['review_status']='unreviewed'
            with self.subTest(kind=kind,mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_count_evidence_is_actual_full_student_draft_not_given_starters(self):
        for mutation in ['field','partial','quote']:
            q=count_fixture('读后续写'); w=q['writing_review']['proposed_score']['word_count_adjustment']
            if mutation=='field': w['evidence']=[span('continuation_starters:0',q['continuation_starters'][0])]
            elif mutation=='partial': w['evidence']=[{'field':'student_text','start':0,'end':3,'quote':q['student_text'][:3]}]
            else: w['evidence'][0]['quote']='invented draft'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_floor_at_zero_and_joint_word_count_handwriting_adjustments(self):
        q=count_fixture(); s=q['writing_review']['proposed_score']; s.update(band='第一档',lower=0,upper=1); s['word_count_adjustment']['score_before']={'lower':1,'upper':3}
        self.a.analyze(q)
        for kind in ['应用文','读后续写']:
            q=visual_fixture(kind); q['writing_review']['schema_version']='1.2.0'
            s=q['writing_review']['proposed_score']; w=count_fixture(kind,points=2)['writing_review']['proposed_score']['word_count_adjustment']
            s['word_count_adjustment']=w; s.update(lower=w['score_before']['lower']-2,upper=w['score_before']['upper']-2)
            out=self.a.analyze(q)
            self.assertIn('synthetic observed region',render(out,'student',self.r))
            self.assertIn('扣2分后',render(out,'student',self.r))

    def test_every_renderer_rechecks_text_only_score_payload_and_owned_graph_path(self):
        out=self.a.analyze(count_fixture())
        for mutation in ['score','rationale','count','band','source','edge','claim','scope']:
            forged=deepcopy(out); f=forged['writing_feedback']; s=f['review']['proposed_score']; g=forged['evidence_graph']
            if mutation=='score': s['lower']=9
            elif mutation=='rationale': s['rationale']='another proposal'
            elif mutation=='count': s['word_count_adjustment']['word_count']=101
            elif mutation=='band': s['band']='第五档'
            elif mutation=='source': s['source_section_id']='d2dc77b78b7ce906'
            elif mutation=='edge':
                claims={n['id'] for n in g['nodes'] if n.get('artifact_fingerprint') and n['type']=='candidate_claim'}
                g['edges']=[e for e in g['edges'] if e['from'] not in claims]
            elif mutation=='claim':
                for n in g['nodes']:
                    if n.get('artifact_fingerprint'): n['artifact_fingerprint']='0'*64
            else: f['scope']='partial_feedback'
            for renderer in ['structured','student','legacy-wechat','content-export']:
                with self.subTest(mutation=mutation,renderer=renderer),self.assertRaises(ValueError): render(forged,renderer,self.r)

    def test_missing_materials_still_withhold_adjusted_score(self):
        q=count_fixture(); q['writing_review']['student_text_complete']=False
        out=self.a.analyze(q); self.assertIsNone(out['writing_feedback']['review']['proposed_score'])
        self.assertNotIn('扣2分后',render(out,'student',self.r))


if __name__=='__main__': unittest.main()
