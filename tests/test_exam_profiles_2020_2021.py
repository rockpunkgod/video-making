"""Source-isolation controls with invented strings, not exam or learner evidence."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.exam_profiles_2020_2021 import choices,parse,blind,reveal,reviewed_blind
from scripts.ingest_exam_sources import freeze_json,sha

class ExamProfileEarlyYearTest(unittest.TestCase):
    def test_control_character_labels_retained_without_text_repair(self):
        self.assertEqual(choices(['A. one B\x01 two C. three D. four']),
            {'A':'one','B':'two','C':'three','D':'four'})
        self.assertEqual(choices(['A one','B. two','C\u00a0three','D. four']),{'A':'one','B':'two','C':'three','D':'four'})
        for text in ['A. one B. two D. four','A. one A. duplicate B. two C. three D. four']:
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'Option labels'): choices([text])

    def test_problematic_profiles_are_not_answer_repaired(self):
        for exam_id in ['gaokao-2021-II']:
            source={'exam_id':exam_id,'source_kind':'blank','automatic_numbered_paragraphs':0,
                'embedded_image_count':None,'text':'PROGRAM ONLY','text_sha256':sha(b'PROGRAM ONLY'),'paragraphs':[]}
            with self.subTest(exam_id=exam_id),self.assertRaisesRegex(ValueError,'source_problem'): parse(source)

    def test_unknown_automatic_numbering_and_images_reject(self):
        base={'exam_id':'gaokao-2020-I','source_kind':'blank','text':'PROGRAM','text_sha256':sha(b'PROGRAM'),'paragraphs':[]}
        for extra,pattern in [({'exam_id':'unknown'},'Unsupported'),({'automatic_numbered_paragraphs':1},'Automatic'),({'embedded_image_count':1},'images'),({'text':'changed'},'Frozen')]:
            with self.subTest(extra=extra),self.assertRaisesRegex(ValueError,pattern): parse({**base,**extra})

    def test_reveal_needs_frozen_prediction_before_opening_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError): reveal(directory,'gaokao-2020-I')
            self.assertFalse((Path(directory)/'results').exists())

    def test_rejected_blind_opens_only_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sources/gaokao-2021-II/blank.json'
            freeze_json(path,{'exam_id':'gaokao-2021-II','source_kind':'blank','text':'PROGRAM','text_sha256':sha(b'PROGRAM')})
            read=Path.read_text
            with patch.object(Path,'read_text',autospec=True) as spy:
                spy.side_effect=read
                with self.assertRaisesRegex(ValueError,'source_problem'): blind(directory,'gaokao-2021-II')
                self.assertEqual([c.args[0].name for c in spy.call_args_list],['blank.json'])

    def test_host_review_requires_original_hash_and_never_replaces_material(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); exam='gaokao-2020-I'
            q={'question_id':'program-only','question_type':'阅读理解','stem':'PROGRAM ONLY','passage':'INVENTED','options':{'A':'CONTROL'}}
            paper={'paper_id':exam,'questions':[q]}; binding={'program-only':{'input_sha256':'program-hash'}}
            freeze_json(root/'sources'/exam/'blank.json',{'program_only':True})
            freeze_json(root/'predictions'/exam/'blind.json',{'inputs':paper,'source_bindings':binding})
            path=root/'review.json'
            for annotations,hashvalue,pattern in [({'passage':'changed'},'program-hash','cannot replace'),({},'wrong','hash mismatch')]:
                # Test inputs are separate files, not rewritten frozen exams.
                current=path.with_name(pattern.replace(' ','-')+'.json')
                freeze_json(current,{'review_stage':'before_reveal','question_id':'program-only','original_input_sha256':hashvalue,'annotations':annotations})
                with patch('scripts.exam_profiles_2020_2021.parse',return_value=(paper,binding)),self.assertRaisesRegex(ValueError,pattern):
                    reviewed_blind(root,exam,current)
            freeze_json(root/'results'/exam/'reveal.json',{'program_only':True})
            with self.assertRaisesRegex(ValueError,'after saved reveal'): reviewed_blind(root,exam,path)

if __name__=='__main__': unittest.main()
