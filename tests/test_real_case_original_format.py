"""Synthetic original-format and alias contracts; no English/learner claims."""
from copy import deepcopy
import json
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import tests.test_real_case_catalog as fixtures
from core.real_cases import digest, load_catalog, register, source_check, validate_request
from core.real_cases import json_digest, material


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

    def test_top_source_hash_can_bind_field_only_question_metadata(self):
        request,blind=self.word_request()
        fingerprint=request['source']['original_sha256']
        blind['source_sha256']=fingerprint
        blind['source_bindings'][request['question_id']]={'fields':{'synthetic_metadata':True}}
        source_check(self.root,request['source'],self.fixture.question,blind)
        # An unrelated truthy object is not sufficient without either identity.
        blind.pop('source_sha256')
        with self.assertRaisesRegex(ValueError,'fingerprint required'):
            source_check(self.root,request['source'],self.fixture.question,blind)

    def test_question_source_hash_cannot_conflict_with_top_hash(self):
        request,blind=self.word_request()
        blind['source_sha256']=request['source']['original_sha256']
        for fingerprint in ('0'*64,None,''):
            with self.subTest(fingerprint=fingerprint):
                blind['source_bindings'][request['question_id']]['source_sha256']=fingerprint
                with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                    source_check(self.root,request['source'],self.fixture.question,blind)

    def test_blind_source_bindings_and_question_entries_require_objects(self):
        request,blind=self.word_request()
        blind['source_sha256']=request['source']['original_sha256']
        for bindings in ([],None,'invalid',{request['question_id']:[]}):
            with self.subTest(bindings=bindings):
                blind['source_bindings']=bindings
                with self.assertRaisesRegex(ValueError,'source binding'):
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

    def test_xml_only_zip_is_not_a_docx_package(self):
        request,blind=self.word_request(); source=request['source']
        buf=io.BytesIO()
        with ZipFile(buf,'w') as archive:
            archive.writestr('word/document.xml',
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
        raw=buf.getvalue(); (self.root/'incomplete.docx').write_bytes(raw)
        source.update(original_path='incomplete.docx',original_sha256=digest(raw))
        with self.assertRaisesRegex(ValueError,'DOCX'):
            source_check(self.root,source,self.fixture.question,blind)

    def test_legacy_doc_signature_checked_without_converting_original(self):
        request,blind=self.word_request(); source=request['source']
        raw=bytes.fromhex('d0cf11e0a1b11ae1')+b'SYNTHETIC MAGIC FIXTURE ONLY'
        (self.root/'legacy.doc').write_bytes(raw)
        source.update(original_path='legacy.doc',original_sha256=digest(raw),source_format='doc')
        # A magic prefix is not sufficient: the compound file must be readable.
        with self.assertRaisesRegex(ValueError,'legacy Word'):
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

    def test_same_canonical_id_cannot_alias_different_complete_question(self):
        request,blind=self.word_request()
        question=blind['typed_method_actions'][0]['question']
        question['options']['B']='SYNTHETIC Z'
        request['question_input_sha256']=json_digest(material(question))
        request['blind']=fixtures.put(self.root,'changed-blind.json',blind)
        source=request['source']; binding=source['question_binding']
        doc=json.loads((self.root/binding['document_path']).read_text(encoding='utf-8'))
        doc['document_text']=doc['document_text'].replace('SYNTHETIC B','SYNTHETIC Z')
        doc_ref=fixtures.put(self.root,'changed-document.json',doc)
        binding.update(document_path=doc_ref['path'],document_sha256=doc_ref['sha256'])
        binding['fields']['/options/B'][0]['quote']='SYNTHETIC Z'
        reveal=json.loads((self.root/request['reveal']['path']).read_text(encoding='utf-8'))
        reveal['prediction_sha256']=request['blind']['sha256']
        request['reveal']=fixtures.put(self.root,'changed-reveal.json',reveal)
        action=json.loads((self.root/request['action']['path']).read_text(encoding='utf-8'))
        action['question']['options']['B']='SYNTHETIC Z'
        action['mechanical_prediction_sha256']=request['blind']['sha256']
        request['action']=fixtures.put(self.root,'changed-action.json',action)
        review=json.loads((self.root/request['case_review']['path']).read_text(encoding='utf-8'))
        review.update(blind_sha256=request['blind']['sha256'],reveal_sha256=request['reveal']['sha256'],
                      action_sha256=request['action']['sha256'],source_document_sha256=doc_ref['sha256'],
                      source_alias_reconciled=True)
        request['case_review']=fixtures.put(self.root,'changed-review.json',review)
        request['source_alias']={'case_id':'synthetic-001-q1-R01-canonical',
            'old_original_sha256':self.fixture.request['source']['pdf_sha256'],
            'new_original_sha256':source['original_sha256']}
        ref=fixtures.put(self.root,'changed-alias-request.json',request)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self.fixture._analysis()):
            register(self.root,self.fixture.request_ref['path'])
            with self.assertRaisesRegex(ValueError,'full question material differs'):
                register(self.root,ref['path'])
            self.assertEqual(load_catalog(self.root)['revision'],1)

    def test_generic_comparison_must_bind_reference_original(self):
        request,_=self.word_request()
        reveal=json.loads((self.root/request['reveal']['path']).read_text(encoding='utf-8'))
        source=request['source']
        reveal['reference_original_ref']={'path':source['original_path'],'sha256':source['original_sha256'],'format':'docx'}
        reveal['original_comparison_ref']=fixtures.put(self.root,'unrelated-comparison.json',{'unrelated':True})
        request['reveal']=fixtures.put(self.root,'adapter-reveal.json',reveal)
        with self.assertRaisesRegex(ValueError,'does not bind the exact reference original'):
            validate_request(self.root,request)


if __name__=='__main__': unittest.main()
