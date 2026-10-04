"""Synthetic image transport only: no real handwriting/learner conclusions."""
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import unittest
from unittest.mock import patch
from PIL import Image
from core.analyzer import QuestionAnalyzer
from core.evidence import validate_graph
from core.image_evidence import image_manifest
from core.registry import Registry, validate_schema
from renderers import render
from tests.test_writing_feedback import fixture


def visual_fixture(kind='应用文', format='PNG'):
    q=fixture(kind)
    image=Image.new('RGB',(20,30),'white')
    buffer=BytesIO(); image.save(buffer,format=format); raw=buffer.getvalue()
    digest=hashlib.sha256(raw).hexdigest()
    q['original_images']=[{'image_id':'synthetic-image-NOT-handwriting','sha256':digest,'mime_type':'image/png' if format=='PNG' else 'image/jpeg','data_base64':base64.b64encode(raw).decode()}]
    review=q['writing_review']; review['schema_version']='1.1.0'
    score=review['proposed_score']; score.update(handwriting_applied=True,original_handwriting_reference=q['original_images'][0]['image_id'])
    review['handwriting_review']={'reviewer':'synthetic-external-visual-transport','review_status':'reviewed','original_handwriting':True,'clear_image':True,'affects_communication':True,'rationale':'synthetic assertion, NOT a real image judgement','source_section_id':score['source_section_id'],'regions':[{'image_id':q['original_images'][0]['image_id'],'sha256':digest,'box':[0,0,10,10],'observed':'synthetic observed region','communication_impact':'synthetic communication impact'}],'adjustment_kind':'lower_one_band' if kind=='应用文' else 'discretionary_deduction','band_before':'第五档' if kind=='应用文' else None,'deduction_points':None if kind=='应用文' else 1,'score_before':None if kind=='应用文' else {'lower':17,'upper':21},'student_text_sha256':hashlib.sha256(q['student_text'].encode()).hexdigest()}
    return q


class ImageEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=QuestionAnalyzer(cls.r)

    def test_valid_bytes_regions_and_two_distinct_course_adjustments(self):
        for kind,format in [('应用文','PNG'),('读后续写','JPEG')]:
            q=visual_fixture(kind,format); out=self.a.analyze(q)
            validate_schema('question-analysis',out); validate_graph(out['evidence_graph'],q)
            f=out['writing_feedback']
            self.assertEqual(f['scope'],'full_correction')
            self.assertEqual(f['score_status'],'external_proposal_not_certified')
            self.assertEqual(f['image_manifest'][0]['width'],20)
            self.assertEqual(len(f['image_evidence_ids']),1)
            for renderer in ['student','legacy-wechat','structured','content-export']:
                body=render(out,renderer,self.r)
                self.assertNotIn('data_base64',body)
            body=render(out,'student',self.r)
            self.assertIn('synthetic observed region',body)
            self.assertIn('不按字迹美观扣分',body)
            image_id=f['image_evidence_ids'][0]
            relations={n['id'] for n in out['evidence_graph']['nodes'] if n['type']=='relation' and n['label'].endswith(f['review']['proposed_score']['rationale'])}
            self.assertTrue(any(e['from']==image_id and e['to'] in relations and e['type']=='supports' for e in out['evidence_graph']['edges']))
            self.assertIsNone(out['answer']); self.assertFalse(out['content_eligible'])

    def test_payload_integrity_mime_decode_and_duplicate_gate(self):
        for mutation in ['hash','mime','base64','not_image','truncated','duplicate']:
            q=visual_fixture(); asset=q['original_images'][0]
            if mutation=='hash': asset['sha256']='0'*64
            elif mutation=='mime': asset['mime_type']='image/jpeg'
            elif mutation=='base64': asset['data_base64']='!notbase64'
            elif mutation in {'not_image','truncated'}:
                raw=b'not an image' if mutation=='not_image' else base64.b64decode(asset['data_base64'])[:35]
                asset.update(data_base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
            else: q['original_images'].append(deepcopy(asset))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): image_manifest(q)

    def test_bounded_decode_does_not_change_global_pillow_settings(self):
        q=visual_fixture(); previous=Image.MAX_IMAGE_PIXELS
        with patch('core.image_evidence.MAX_BYTES',10),self.assertRaisesRegex(ValueError,'byte limit'): image_manifest(q)
        with patch('core.image_evidence.MAX_PIXELS',10),self.assertRaisesRegex(ValueError,'pixel limit'): image_manifest(q)
        self.assertEqual(Image.MAX_IMAGE_PIXELS,previous)

    def test_no_filename_transcription_unclear_or_unreviewed_penalty(self):
        for mutation in ['missing','foreign_hash','foreign_id','outside','empty_box','clear','original','impact','unreviewed','draft','version','source']:
            q=visual_fixture(); v=q['writing_review']['handwriting_review']; region=v['regions'][0]
            if mutation=='missing': q.pop('original_images')
            elif mutation=='foreign_hash': region['sha256']='0'*64
            elif mutation=='foreign_id': region['image_id']='another-image'
            elif mutation=='outside': region['box']=[0,0,21,10]
            elif mutation=='empty_box': region['box']=[0,0,0,10]
            elif mutation=='clear': v['clear_image']=False
            elif mutation=='original': v['original_handwriting']=False
            elif mutation=='impact': v['affects_communication']=False
            elif mutation=='unreviewed': v['review_status']='unreviewed'
            elif mutation=='draft': v['student_text_sha256']='0'*64
            elif mutation=='version': q['writing_review']['schema_version']='1.0.0'
            else: v['source_section_id']='f8cfb194a81aad6e'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_course_rules_not_interchangeable_or_unbounded(self):
        for kind,mutation in [('应用文','deduction'),('应用文','skip_band'),('读后续写','band'),('读后续写','mismatch'),('读后续写','unordered_before')]:
            q=visual_fixture(kind); v=q['writing_review']['handwriting_review']
            if mutation=='deduction': v['adjustment_kind']='discretionary_deduction'
            elif mutation=='skip_band': v['band_before']='第三档'
            elif mutation=='band': v['adjustment_kind']='lower_one_band'
            elif mutation=='mismatch': v['deduction_points']=2
            else: v['score_before']={'lower':22,'upper':21}
            with self.subTest(kind=kind,mutation=mutation),self.assertRaises(ValueError): self.a.analyze(q)

    def test_unclear_image_can_be_recorded_without_any_adjustment(self):
        q=visual_fixture(); v=q['writing_review']['handwriting_review']; v.update(clear_image=False,affects_communication=None,adjustment_kind='none',band_before=None)
        q['writing_review']['proposed_score'].update(handwriting_applied=False,original_handwriting_reference=None)
        out=self.a.analyze(q)
        self.assertEqual(out['writing_feedback']['scope'],'full_correction')
        self.assertNotIn('synthetic observed region',render(out,'student',self.r))
        self.assertFalse(out['writing_feedback']['review']['proposed_score']['handwriting_applied'])

    def test_material_gap_actually_withholds_visual_score_and_penalty_text(self):
        q=visual_fixture(); q['writing_review']['student_text_complete']=False
        out=self.a.analyze(q)
        self.assertIsNone(out['writing_feedback']['review']['proposed_score'])
        self.assertEqual(out['writing_feedback']['score_status'],'withheld')
        self.assertNotIn('synthetic communication impact',render(out,'legacy-wechat',self.r))
        self.assertIn('暂不作完整评分',render(out,'student',self.r))

    def test_render_rechecks_manifest_visual_score_and_graph_binding(self):
        out=self.a.analyze(visual_fixture())
        for mutation in ['manifest','observed','impact','draft','score','graph','missing_ids','region','edge']:
            forged=deepcopy(out); f=forged['writing_feedback']
            if mutation=='manifest': f['image_manifest'][0]['width']=30
            elif mutation=='observed': f['review']['handwriting_review']['regions'][0]['observed']='changed judgement'
            elif mutation=='impact': f['review']['handwriting_review']['affects_communication']=False
            elif mutation=='draft': f['student_text_sha256']='0'*64
            elif mutation=='score': f['review']['proposed_score']['upper']=11
            elif mutation=='graph': next(n for n in forged['evidence_graph']['nodes'] if n['type']=='image_evidence')['image_ref']['sha256']='0'*64
            elif mutation=='missing_ids': f['image_evidence_ids']=[]
            elif mutation=='edge': forged['evidence_graph']['edges']=[e for e in forged['evidence_graph']['edges'] if e['from'] not in f['image_evidence_ids']]
            else: f['review']['handwriting_review']['regions'][0]['box']=[0,0,21,10]
            for renderer in ['structured','student','legacy-wechat','content-export']:
                with self.subTest(mutation=mutation,renderer=renderer),self.assertRaises(ValueError): render(forged,renderer,self.r)

    def test_current_question_graph_rejects_swapped_original_image(self):
        q=visual_fixture(); out=self.a.analyze(q)
        other=visual_fixture(format='JPEG'); q['original_images']=other['original_images']
        with self.assertRaises(ValueError): validate_graph(out['evidence_graph'],q)

    def test_text_only_1_0_remains_compatible_and_no_implicit_visual_review(self):
        out=self.a.analyze(fixture()); f=out['writing_feedback']
        self.assertEqual(f['image_manifest'],[]); self.assertEqual(f['image_evidence_ids'],[])
        render(out,'legacy-wechat',self.r)


if __name__=='__main__': unittest.main()
