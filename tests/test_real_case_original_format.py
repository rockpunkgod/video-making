"""Synthetic original-format and alias contracts; no English/learner claims."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import tests.test_real_case_catalog as fixtures
from core.real_cases import digest, load_catalog, register, source_check, validate_request


class OriginalFormatTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PrivateRealCaseTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root

    def word_request(self, variant='one'):
        base=self.fixture.request
        raw=fixtures.word_bytes('SYNTHETIC original '+variant)
        name='source-'+variant+'.docx'; (self.root/name).write_bytes(raw)
        fingerprint=digest(raw)
        source=deepcopy(base['source'])
        source.pop('pdf_path'); source.pop('pdf_sha256')
        source.update(original_path=name,original_sha256=fingerprint,source_format='docx')
        document=json.loads((self.root/'source.json').read_text(encoding='utf-8'))
        document['source_sha256']=fingerprint
        doc=fixtures.put(self.root,'document-'+variant+'.json',document)
        binding=source['question_binding']
        binding.pop('pdf_sha256_pointer')
        binding.update(original_sha256_pointer='/source_sha256',document_path=doc['path'],document_sha256=doc['sha256'])
        blind=json.loads((self.root/'blind.json').read_text(encoding='utf-8'))
        blind['source_bindings'][base['question_id']]['source_sha256']=fingerprint
        blind_ref=fixtures.put(self.root,'blind-'+variant+'.json',blind)
        reveal=json.loads((self.root/'reveal.json').read_text(encoding='utf-8'))
        reveal['prediction_sha256']=blind_ref['sha256']
        reveal_ref=fixtures.put(self.root,'reveal-'+variant+'.json',reveal)
        action=json.loads((self.root/'action.json').read_text(encoding='utf-8'))
        action['mechanical_prediction_sha256']=blind_ref['sha256']
        action_ref=fixtures.put(self.root,'action-'+variant+'.json',action)
        review=json.loads((self.root/'review.json').read_text(encoding='utf-8'))
        review.pop('source_pdf_sha256')
        review.update(source_original_sha256=fingerprint,source_document_sha256=doc['sha256'],
                      blind_sha256=blind_ref['sha256'],reveal_sha256=reveal_ref['sha256'],action_sha256=action_ref['sha256'])
        review_ref=fixtures.put(self.root,'review-'+variant+'.json',review)
        request=deepcopy(base)
        request.update(source=source,blind=blind_ref,reveal=reveal_ref,action=action_ref,case_review=review_ref)
        return request,blind

    def test_word_original_exact_source_check(self):
        request,blind=self.word_request()
        source_check(self.root,request['source'],self.fixture.question,blind)
        (self.root/request['source']['original_path']).write_bytes(fixtures.word_bytes('CHANGED'))
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            source_check(self.root,request['source'],self.fixture.question,blind)

    def test_original_format_is_not_inferred_or_laundered(self):
        request,blind=self.word_request()
        for edit in ({'source_format':'pdf'}, {'source_format':'unknown'},
                     {'pdf_sha256':request['source']['original_sha256']}, {'source_format':None}):
            source={**request['source'],**edit}
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                source_check(self.root,source,self.fixture.question,blind)
        source=deepcopy(request['source']); source['original_path']='fake.docx'
        for raw in (b'%PDF renamed to docx', b'not a ZIP', b'PK\x03\x04broken ZIP'):
            (self.root/'fake.docx').write_bytes(raw); source['original_sha256']=digest(raw)
            with self.assertRaisesRegex(ValueError,'DOCX'):
                source_check(self.root,source,self.fixture.question,blind)

    def test_word_bytes_cannot_use_legacy_pdf_metadata(self):
        request,blind=self.word_request()
        raw=(self.root/request['source']['original_path']).read_bytes()
        (self.root/'disguised.pdf').write_bytes(raw)
        legacy=deepcopy(self.fixture.request['source'])
        legacy.update(pdf_path='disguised.pdf',pdf_sha256=digest(raw))
        with self.assertRaisesRegex(ValueError,'not PDF bytes'):
            source_check(self.root,legacy,self.fixture.question,blind)

    def test_legacy_doc_signature_checked_without_converting_original(self):
        request,blind=self.word_request(); source=request['source']
        raw=bytes.fromhex('d0cf11e0a1b11ae1')+b'SYNTHETIC MAGIC FIXTURE ONLY'
        (self.root/'legacy.doc').write_bytes(raw)
        source.update(original_path='legacy.doc',original_sha256=digest(raw),source_format='doc')
        # Valid magic gets as far as the immutable document/hash mismatch.
        with self.assertRaisesRegex(ValueError,'not bound'):
            source_check(self.root,source,self.fixture.question,blind)
        (self.root/'legacy.doc').write_bytes(b'%PDF wrong original')
        source['original_sha256']=digest(b'%PDF wrong original')
        with self.assertRaisesRegex(ValueError,'legacy Word bytes'):
            source_check(self.root,source,self.fixture.question,blind)

    def test_word_source_requires_generic_reviewer_hash(self):
        request,_=self.word_request()
        review=json.loads((self.root/request['case_review']['path']).read_text(encoding='utf-8'))
        review['source_pdf_sha256']=review.pop('source_original_sha256')
        request['case_review']=fixtures.put(self.root,'wrong-review.json',review)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self.fixture._analysis()):
            with self.assertRaisesRegex(ValueError,'source version'):
                validate_request(self.root,request)

    def test_source_span_cannot_run_beyond_document_or_use_boolean_offsets(self):
        request,blind=self.word_request()
        source=request['source']; fields=source['question_binding']['fields']
        original=deepcopy(fields['/options/B'][0])
        fields['/options/B'][0]['end']=100000
        with self.assertRaisesRegex(ValueError,'Exact source span'):
            source_check(self.root,source,self.fixture.question,blind)
        fields['/options/B'][0]=original
        fields['/stem'][0]['start']=False
        with self.assertRaisesRegex(ValueError,'Exact source span'):
            source_check(self.root,source,self.fixture.question,blind)

    def test_pdf_to_word_alias_reuses_case_and_replays_history(self):
        request,_=self.word_request()
        source=request['source']
        request['source_alias']={'case_id':'synthetic-001-q1-R01-canonical',
            'old_original_sha256':self.fixture.request['source']['pdf_sha256'],
            'new_original_sha256':source['original_sha256']}
        review=json.loads((self.root/request['case_review']['path']).read_text(encoding='utf-8'))
        review['source_alias_reconciled']=True
        request['case_review']=fixtures.put(self.root,'alias-review.json',review)
        ref=fixtures.put(self.root,'alias-request.json',request)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self.fixture._analysis()):
            register(self.root,self.fixture.request_ref['path'])
            result=register(self.root,ref['path'])
            self.assertEqual((result['new_case_count'],result['catalog_revision']),(0,2))
            catalog=load_catalog(self.root)
            self.assertEqual(len(catalog['cases']),1)
            self.assertEqual(catalog['aliases'][0]['source_original_sha256'],source['original_sha256'])
            with self.assertRaisesRegex(ValueError,'Duplicate source alias'):
                register(self.root,ref['path'])


if __name__=='__main__': unittest.main()
