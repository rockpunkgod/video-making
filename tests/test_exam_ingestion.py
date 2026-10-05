"""Program-only extraction/isolation controls; not exam/learner validation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from scripts.ingest_exam_sources import extract_docx,freeze,freeze_json
from scripts.run_exam_regression import choices,parse_2024_i,reveal,blind
from scripts.summarize_exam_ingestion import summary

class ExamIngestionTest(unittest.TestCase):
    def test_summary_uses_latest_frozen_revision_and_adapter_counts(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            entry={'exam_id':'PROGRAM','year':2024,'exam_name':'PROGRAM ONLY',
                   'usage_status':'program_only','source_ids':[],'source_issue':[]}
            freeze_json(directory/'source-manifest.json',{'papers':[entry],'sources':[]})
            target=directory/'results/PROGRAM'
            freeze_json(target/'reveal.json',{'written_questions':1})
            freeze_json(target/'reveal-v1.1.json',{'written_questions':47,
                'mechanical_answered_count':0,'mechanical_unresolved_count':45})
            freeze_json(target/'contribution-summary.json',{'written_questions':1})
            freeze_json(target/'contribution-summary-v2.json',{'written_questions':47,
                'reviewed_prediction_sha256':'PROGRAM HASH','host_reviewed_answered_count':1,
                'host_reviewed_match_count':1})
            value=summary(directory)
            self.assertEqual(value['new_question_count'],47)
            self.assertEqual(value['papers'][0]['unresolved_count'],45)
            self.assertEqual(value['host_reviewed_question_count'],1)
            self.assertEqual(value['host_reviewed_reference_match_count'],1)
            self.assertTrue(value['papers'][0]['result_artifact'].endswith('reveal-v1.1.json'))
    def test_public_summary_never_exports_question_or_answer_payload(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            entry={'exam_id':'PROGRAM','year':2024,'exam_name':'PROGRAM ONLY','usage_status':'program_only',
                   'source_ids':[],'source_issue':[]}
            freeze_json(directory/'source-manifest.json',{'papers':[entry],'sources':[]})
            freeze_json(directory/'results/PROGRAM/reveal.json',{'status':'PARTIAL','new_question_count':2,
                'questions':[{'passage':'DO NOT EXPORT PROGRAM BODY','reference_answer':'DO NOT EXPORT PROGRAM KEY'}],
                'safe_abstention':None})
            result=summary(directory)
            encoded=json.dumps(result)
            self.assertNotIn('DO NOT EXPORT',encoded)
            self.assertEqual(result['new_question_count'],2)
            self.assertIsNone(result['papers'][0]['safe_abstention'])

    def test_helper_and_bounded_actions_are_not_mixed_or_counted_as_registered_cases(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            entry={'exam_id':'PROGRAM','year':2024,'exam_name':'PROGRAM ONLY','usage_status':'program_only',
                   'source_ids':[],'source_issue':[]}
            freeze_json(directory/'source-manifest.json',{'papers':[entry],'sources':[]})
            actions=[{'stage':'post_reveal_action_review'}, {'stage':'post_reveal_bounded_action_review'}]
            with patch('scripts.summarize_exam_ingestion.load_action_metadata',return_value=actions):
                result=summary(directory)
            self.assertEqual(result['post_reveal_helper_action_review_count'],1)
            self.assertEqual(result['post_reveal_bounded_action_review_count'],1)
            self.assertEqual(result['new_registered_cases'],0)

    def test_freeze_is_idempotent_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'frozen.json'
            freeze_json(path,{'program_only':True})
            before=path.read_bytes(); freeze_json(path,{'program_only':True})
            self.assertEqual(before,path.read_bytes())
            with self.assertRaisesRegex(ValueError,'Frozen artifact differs'):
                freeze_json(path,{'program_only':False})
            self.assertEqual(before,path.read_bytes())

    def test_ooxml_retains_table_paragraphs_tabs_breaks_and_image_gap(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'program.docx'
            xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>PROGRAM</w:t><w:tab/><w:t>ONLY</w:t><w:br/><w:t>CONTROL</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>TABLE</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
            with ZipFile(path,'w') as z:
                z.writestr('word/document.xml',xml)
                z.writestr('word/media/program.png',b'not a real image; count only')
            result=extract_docx(path)
            self.assertEqual(result['paragraphs'],['PROGRAM\tONLY\nCONTROL','TABLE'])
            self.assertEqual(result['automatic_numbered_paragraphs'],1)
            self.assertEqual(result['embedded_image_count'],1)

    def test_incomplete_duplicate_or_reordered_options_are_rejected(self):
        self.assertEqual(choices(['A. program\tB. only\tC. control\tD. data']),
                         {'A':'program','B':'only','C':'control','D':'data'})
        for text in ['A. program B. only','A. one A. two B. three C. four D. five','B. one A. two C. three D. four']:
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'Option labels'):
                choices([text])

    def test_unsupported_profile_and_missing_prediction_fail_before_reveal(self):
        with self.assertRaisesRegex(ValueError,'No audited extraction profile'):
            parse_2024_i({'exam_id':'program-only','source_kind':'blank'})
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError): reveal(d,'program-only')
            self.assertFalse((Path(d)/'results').exists())

    def test_blind_never_opens_reveal_source(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sources/program-only/blank.json'
            freeze_json(path,{'exam_id':'program-only','source_kind':'blank','text':'PROGRAM','text_sha256':__import__('hashlib').sha256(b'PROGRAM').hexdigest()})
            # A rejected profile cannot fall back to answers to reconstruct a paper.
            original_read=Path.read_text
            with patch.object(Path,'read_text',autospec=True) as read:
                read.side_effect=original_read
                with self.assertRaisesRegex(ValueError,'No audited extraction profile'):
                    blind(d,'program-only')
                self.assertEqual([x.args[0].name for x in read.call_args_list],['blank.json'])
