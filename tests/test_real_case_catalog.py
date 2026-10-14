"""Synthetic contract fixtures only; no real exam or learner evidence."""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import core.real_cases as real_cases
from core.real_cases import (digest, json_digest, load_catalog,
                             material, pointer, private_root, register, validate_request)
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from tests.test_execution import fixture


def put(root, name, value):
    path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False)+'\n').encode()
    path.write_bytes(raw)
    return {'path': name, 'sha256': digest(raw)}


def word_bytes(text):
    """Minimal synthetic OOXML contract fixture, not a real exam."""
    w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    document=ET.Element(w+'document'); body=ET.SubElement(document,w+'body')
    run=ET.SubElement(ET.SubElement(body,w+'p'),w+'r')
    ET.SubElement(run,w+'t').text=text
    buf=io.BytesIO()
    with ZipFile(buf,'w') as archive:
        archive.writestr('word/document.xml',ET.tostring(document))
        archive.writestr('[Content_Types].xml',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>')
        archive.writestr('_rels/.rels',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    return buf.getvalue()


class PrivateRealCaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = Registry(); self.method = self.registry.methods['R01']
        question = {'question_id':'synthetic-001-q1','question_type':'阅读理解',
                    'stem':'SYNTHETIC prompt', 'passage':'SYNTHETIC passage',
                    'options':{'A':'SYNTHETIC A','B':'SYNTHETIC B'}}
        self.question = question
        self.root.joinpath('source.pdf').write_bytes(b'%PDF SYNTHETIC TEST ONLY')
        pdf_hash = digest(self.root.joinpath('source.pdf').read_bytes())
        source_text=' | '.join(['SYNTHETIC prompt','SYNTHETIC passage','SYNTHETIC A','SYNTHETIC B'])
        document = put(self.root,'source.json',{'document_text':source_text,'source_sha256':pdf_hash})
        blind = put(self.root,'blind.json',{'pass':'blind','exam_id':'synthetic-001',
                     'reviewer_agent':'first-ai',
                     'typed_method_actions':[{'question':question}],
                     'source_bindings':{'synthetic-001-q1':{'source_sha256':pdf_hash}}})
        reveal = put(self.root,'reveal.json',{'exam_id':'synthetic-001',
                     'prediction_sha256':blind['sha256'],
                     'questions':[{'question_id':'synthetic-001-q1','reference_answer':'A',
                                   'answer_authority':'third_party_unverified'}]})
        action_question = {**question,'observations':[{'method_id':'R01','reviewed':True}]}
        execution = {'method_id':'R01','state':'produced','role':self.method['primary_role'],
                     'execution_id':'synthetic-action','output':{'kind':'candidate_decision'}}
        analysis = {'evidence_graph':{'nodes':[],'edges':[]},'execution_trace':[execution]}
        action = put(self.root,'action.json',{'exam_id':'synthetic-001','question_id':'synthetic-001-q1',
                    'method_id':'R01','method_version':self.method['version'],
                    'mechanical_prediction_sha256':blind['sha256'],
                    'question':action_question,'analysis':analysis})
        source = {'pdf_path':'source.pdf','pdf_sha256':pdf_hash,'exam_id':'synthetic-001',
                  'question_id':'synthetic-001-q1','usage_status':'local_research_only',
                  'answer_authority':'third_party_unverified',
                  'question_binding':{'document_path':document['path'],
                                      'document_sha256':document['sha256'],
                                      'pdf_sha256_pointer':'/source_sha256',
                                      'text_pointer':'/document_text',
                                      'fields':{name:[{'start':source_text.find(value),
                                                        'end':source_text.find(value)+len(value),
                                                        'quote':value}]
                                                for name,value in {'/stem':'SYNTHETIC prompt',
                                                    '/passage':'SYNTHETIC passage',
                                                    '/options/A':'SYNTHETIC A',
                                                    '/options/B':'SYNTHETIC B'}.items()}}}
        review = {'stage':'post_reveal_case_review','reviewer_kind':'AI',
                  'reviewer':'second-ai','paper_agent':'first-ai','independent_from_paper_agent':True,
                  'checks':{k:True for k in ('trigger','action','evidence','role','stop','case_type')},
                  'pass_scope':'private_research_case_only','case_type':'canonical',
                  'case_type_reason':'Synthetic contract fixture only',
                  'question_id':'synthetic-001-q1','method_id':'R01',
                  'canonical_question_id':'synthetic-001-q1',
                  'method_version':self.method['version'],'role':self.method['primary_role'],
                  'stop_rule':self.method['stop_rule'],
                  'blind_sha256':blind['sha256'],'reveal_sha256':reveal['sha256'],
                  'action_sha256':action['sha256'],
                  'action_analysis_sha256':json_digest(analysis),
                  'replay_analysis_sha256':json_digest(analysis),
                  'evidence_graph_sha256':json_digest(analysis['evidence_graph']),
                  'own_execution_ids':['synthetic-action'],
                  'source_pdf_sha256':pdf_hash,'source_document_sha256':document['sha256'],
                  'pre_reveal_prediction_unchanged':True,'answer_backfit_excluded':True,
                  'own_method_credit_only':True,'trigger':'synthetic trigger',
                  'action':'synthetic action','evidence':[{'synthetic':True}]}
        case_review = put(self.root,'review.json',review)
        self.request = {'question_id':'synthetic-001-q1','canonical_question_id':'synthetic-001-q1','method_id':'R01',
                        'method_version':self.method['version'],'case_type':'canonical',
                        'source':source,'blind':blind,
                        'blind_question_pointer':'/typed_method_actions/0/question',
                        'question_input_sha256':json_digest(material(question)),
                        'reveal':reveal,'action':action,'case_review':case_review}
        self.request_ref = put(self.root,'request.json',self.request)

    def _analysis(self):
        return json.loads((self.root/'action.json').read_text(encoding='utf-8'))['analysis']

    def _legacy_request(self, *, phase='agent_before_reference_read', reviewers=('first-ai',),
                        top=None, action_reviewer=None):
        question=json.loads(json.dumps(self.question))
        question['action_executions']=[{'reviewer':name} for name in reviewers[:1]]
        question['relations']=[{'reviewer':name} for name in reviewers[1:]]
        blind={'phase':phase,'exam_id':'synthetic-001',
               'source_sha256':self.request['source']['pdf_sha256'],
               'typed_method_actions':[{'annotated_input':question}]}
        if top is not None: blind.update(top)
        blind_ref=put(self.root,'legacy-blind.json',blind)
        reveal=json.loads((self.root/'reveal.json').read_text(encoding='utf-8'))
        reveal['prediction_sha256']=blind_ref['sha256']
        reveal_ref=put(self.root,'legacy-reveal.json',reveal)
        action=json.loads((self.root/'action.json').read_text(encoding='utf-8'))
        action['mechanical_prediction_sha256']=blind_ref['sha256']
        if action_reviewer is not None:
            action['question']['action_executions']=[{'reviewer':action_reviewer}]
        action_ref=put(self.root,'legacy-action.json',action)
        review=json.loads((self.root/'review.json').read_text(encoding='utf-8'))
        review.update(paper_agent='first-ai',blind_sha256=blind_ref['sha256'],
                      reveal_sha256=reveal_ref['sha256'],action_sha256=action_ref['sha256'])
        review_ref=put(self.root,'legacy-review.json',review)
        request=json.loads(json.dumps(self.request))
        request.update(blind=blind_ref,blind_question_pointer='/typed_method_actions/0/annotated_input',
                       reveal=reveal_ref,action=action_ref,case_review=review_ref)
        return request

    def test_legacy_source_only_phase_and_unique_frozen_question_author_register(self):
        request=self._legacy_request(reviewers=('first-ai','first-ai'),action_reviewer='later-ai')
        ref=put(self.root,'legacy-request.json',request)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            record=register(self.root,ref['path'])
            self.assertEqual(record['status'],real_cases.STATUS)
            self.assertEqual(load_catalog(self.root)['revision'],1)

    def test_legacy_phase_and_paper_author_fail_closed(self):
        for phase in ('unknown_phase','after_reference_read'):
            with self.subTest(phase=phase):
                request=self._legacy_request(phase=phase)
                with self.assertRaisesRegex(ValueError,'pre-reveal pass'):
                    validate_request(self.root,request,self.registry)
        for reviewers,top in (((),None),(('first-ai','other-ai'),None),
                              (('first-ai',),{'reviewer_agent':''}),
                              (('first-ai',),{'paper_agent':'  '}),
                              (('first-ai',),{'reviewer_agent':'first-ai','paper_agent':'other-ai'})):
            with self.subTest(reviewers=reviewers,top=top):
                request=self._legacy_request(reviewers=reviewers,top=top)
                with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                        patch('core.real_cases.validate_execution_trace'), \
                        patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
                    with self.assertRaisesRegex(ValueError,'paper agent|Case reviewer'):
                        validate_request(self.root,request,self.registry)

    def test_explicit_frozen_author_takes_priority_over_question_labels(self):
        request=self._legacy_request(reviewers=('other-ai',),top={'paper_agent':'first-ai'})
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            validate_request(self.root,request,self.registry)
        request=self._legacy_request(reviewers=('other-ai',),action_reviewer='first-ai')
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            with self.assertRaisesRegex(ValueError,'Case reviewer'):
                validate_request(self.root,request,self.registry)

    def test_registration_overlay_and_no_duplicate(self):
        before = self.registry.case_coverage()
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            result = register(self.root, self.request_ref['path'])
        self.assertEqual(result['status'],'reviewed_real_exam_case')
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            self.assertEqual(load_catalog(self.root)['revision'],1)
            overlay = self.registry.case_coverage(self.root)
        self.assertEqual(overlay['registered_case_count'],before['registered_case_count'])
        self.assertEqual(overlay['private_catalog']['private_reviewed_case_count'],1)
        self.assertEqual(overlay['private_catalog']['unique_question_count'],1)
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            with self.assertRaisesRegex(ValueError,'already registered'):
                register(self.root,self.request_ref['path'])

    def test_frozen_material_source_and_review_fail_closed(self):
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            validate_request(self.root,self.request,self.registry)
            changed = json.loads(json.dumps(self.request)); changed['question_input_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'material fingerprint'):
                validate_request(self.root,changed,self.registry)
            changed = json.loads(json.dumps(self.request))
            changed['source']['question_binding']['fields']['/stem'][0]['quote']='wrong'
            with self.assertRaisesRegex(ValueError,'span replay'):
                validate_request(self.root,changed,self.registry)
            changed = json.loads(json.dumps(self.request)); changed['source']['pdf_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                validate_request(self.root,changed,self.registry)

    def test_private_path_and_catalog_tamper(self):
        with self.assertRaisesRegex(ValueError,'private directory'):
            private_root(Path(__file__).resolve().parents[1]/'cases')
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
        path=self.root/'real-case-catalog'/'cases'/('synthetic-001-q1-R01-canonical.json')
        path.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            load_catalog(self.root)

    def test_pointer_escape_and_source_field_omission(self):
        for path in ('/questions/-1','/questions/01','/questions/~2'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                pointer({'questions':[self.question]},path)
        changed=json.loads(json.dumps(self.request))
        changed['source']['question_binding']['fields'].pop('/options/B')
        with self.assertRaisesRegex(ValueError,'Every source question text field'):
            validate_request(self.root,changed,self.registry)
        changed=json.loads(json.dumps(self.request))
        changed['source']['question_binding']['fields']['/stem']=[
            changed['source']['question_binding']['fields']['/options/A'][0]]
        with self.assertRaisesRegex(ValueError,'do not reproduce'):
            validate_request(self.root,changed,self.registry)

    def test_blind_top_level_pdf_hash_conflict(self):
        blind=json.loads((self.root/'blind.json').read_text(encoding='utf-8'))
        blind['source_sha256']='0'*64
        ref=put(self.root,'blind-conflict.json',blind)
        changed=json.loads(json.dumps(self.request)); changed['blind']=ref
        changed['case_review']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'top-level source PDF fingerprint'):
            validate_request(self.root,changed,self.registry)

    def test_blind_requires_a_frozen_source_pdf_fingerprint(self):
        blind=json.loads((self.root/'blind.json').read_text(encoding='utf-8'))
        blind.pop('source_bindings')
        changed=json.loads(json.dumps(self.request))
        changed['blind']=put(self.root,'blind-without-source.json',blind)
        with self.assertRaisesRegex(ValueError,'source PDF fingerprint required'):
            validate_request(self.root,changed,self.registry)

    def test_canonical_id_cannot_change_for_same_frozen_question(self):
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            review=json.loads((self.root/'review.json').read_text(encoding='utf-8'))
            review['canonical_question_id']='renamed-synthetic-001-q1'
            changed=json.loads(json.dumps(self.request))
            changed['canonical_question_id']=review['canonical_question_id']
            changed['case_id']='renamed-synthetic-001-q1-R01-canonical'
            changed['case_review']=put(self.root,'review-renamed.json',review)
            changed_ref=put(self.root,'request-renamed.json',changed)
            with self.assertRaisesRegex(ValueError,'canonical ID conflict'):
                register(self.root,changed_ref['path'])

            method,question,review=validate_request(self.root,changed,self.registry)
            record=real_cases.expected_record(changed,changed_ref,method,question,review,changed['case_id'])
            case_ref=put(self.root,'real-case-catalog/cases/'+changed['case_id']+'.json',record)
            first=self.root/'real-case-catalog/catalog-000001.json'
            prior=json.loads(first.read_text(encoding='utf-8'))
            put(self.root,'real-case-catalog/catalog-000002.json',
                {'revision':2,'previous_sha256':digest(first.read_bytes()),
                 'cases':prior['cases']+[case_ref],'aliases':prior['aliases']})
            with self.assertRaisesRegex(ValueError,'canonical ID conflict'):
                load_catalog(self.root)

    def test_canonical_id_survives_blind_metadata_repackaging(self):
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            blind=json.loads((self.root/'blind.json').read_text(encoding='utf-8'))
            blind['non_material_metadata']='repackaged blind artifact'
            blind_ref=put(self.root,'blind-repackaged.json',blind)
            reveal=json.loads((self.root/'reveal.json').read_text(encoding='utf-8'))
            reveal['prediction_sha256']=blind_ref['sha256']
            reveal_ref=put(self.root,'reveal-repackaged.json',reveal)
            action=json.loads((self.root/'action.json').read_text(encoding='utf-8'))
            action['mechanical_prediction_sha256']=blind_ref['sha256']
            action_ref=put(self.root,'action-repackaged.json',action)
            review=json.loads((self.root/'review.json').read_text(encoding='utf-8'))
            review.update(canonical_question_id='renamed-after-repackaging',
                          blind_sha256=blind_ref['sha256'],
                          reveal_sha256=reveal_ref['sha256'],
                          action_sha256=action_ref['sha256'])
            review_ref=put(self.root,'review-repackaged.json',review)
            changed=json.loads(json.dumps(self.request))
            changed.update(canonical_question_id=review['canonical_question_id'],
                           case_id='renamed-after-repackaging-R01-canonical',
                           blind=blind_ref,reveal=reveal_ref,action=action_ref,case_review=review_ref)
            changed_ref=put(self.root,'request-repackaged.json',changed)
            validate_request(self.root,changed,self.registry)
            with self.assertRaisesRegex(ValueError,'canonical ID conflict'):
                register(self.root,changed_ref['path'])

    def test_reveal_adapter_requires_both_private_hashed_refs(self):
        reveal=json.loads((self.root/'reveal.json').read_text(encoding='utf-8'))
        comparison={'path':'source.json','sha256':digest((self.root/'source.json').read_bytes())}
        reveal['original_comparison_ref']=comparison
        changed=json.loads(json.dumps(self.request))
        changed['reveal']=put(self.root,'half-reveal.json',reveal)
        with self.assertRaisesRegex(ValueError,'requires both'):
            validate_request(self.root,changed,self.registry)
        reveal['reference_pdf_ref']=None
        changed['reveal']=put(self.root,'null-reveal.json',reveal)
        with self.assertRaisesRegex(ValueError,'fingerprint required'):
            validate_request(self.root,changed,self.registry)
        reveal['reference_pdf_ref']={'path':'../escaped.pdf','sha256':'0'*64}
        changed['reveal']=put(self.root,'escaped-reveal.json',reveal)
        with self.assertRaisesRegex(ValueError,'escaped private artifact'):
            validate_request(self.root,changed,self.registry)

    def test_review_and_replay_fingerprints_are_bound(self):
        changed=json.loads(json.dumps(self.request))
        changed['case_review']['sha256']='0'*64
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                validate_request(self.root,changed,self.registry)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value={'other':'result'}):
            with self.assertRaisesRegex(ValueError,'replay differs'):
                validate_request(self.root,self.request,self.registry)

    def test_unsafe_case_id_and_orphan_catalog_fail_closed(self):
        changed=json.loads(json.dumps(self.request)); changed['case_id']='../escaped'
        ref=put(self.root,'unsafe-request.json',changed)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            with self.assertRaisesRegex(ValueError,'Unsafe private Case ID'):
                register(self.root,ref['path'])
        orphan=self.root/'real-case-catalog'/'cases'/'orphan.json'
        orphan.parent.mkdir(parents=True,exist_ok=True); orphan.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Orphan'):
            load_catalog(self.root)

    def test_catalog_revision_cannot_drop_prior_case(self):
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            first=self.root/'real-case-catalog'/'catalog-000001.json'
            put(self.root,'real-case-catalog/catalog-000002.json',
                {'revision':2,'previous_sha256':digest(first.read_bytes()),'cases':[],'aliases':[]})
            with self.assertRaisesRegex(ValueError,'revision chain'):
                load_catalog(self.root)

    def test_rehashed_case_record_cannot_forge_derived_fact(self):
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            case_path=self.root/'real-case-catalog/cases/synthetic-001-q1-R01-canonical.json'
            case=json.loads(case_path.read_text(encoding='utf-8'))
            case['expected_action']='forged action'
            case_raw=(json.dumps(case,ensure_ascii=False)+'\n').encode()
            case_path.write_bytes(case_raw)
            manifest_path=self.root/'real-case-catalog/catalog-000001.json'
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest['cases'][0]['sha256']=digest(case_raw)
            manifest_path.write_text(json.dumps(manifest,ensure_ascii=False)+'\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'differs from validated request'):
                load_catalog(self.root)

    def test_alias_revision_must_replay_explicit_reconciliation(self):
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            first=self.root/'real-case-catalog/catalog-000001.json'
            prior=json.loads(first.read_text(encoding='utf-8'))
            alias={'case_id':'synthetic-001-q1-R01-canonical',
                   'registration_key':[self.request['canonical_question_id'],'R01','canonical',self.method['version']],
                   'source_pdf_sha256':self.request['source']['pdf_sha256'],
                   'registration_request_ref':self.request_ref}
            put(self.root,'real-case-catalog/catalog-000002.json',
                {'revision':2,'previous_sha256':digest(first.read_bytes()),
                 'cases':prior['cases'],'aliases':[alias]})
            with self.assertRaisesRegex(ValueError,'Source alias reconciliation mismatch'):
                load_catalog(self.root)

    def test_two_case_revisions_validate_each_distinct_request_once_per_load(self):
        second_review=json.loads((self.root/'review.json').read_text(encoding='utf-8'))
        second_review['case_type']='transfer'
        second_review['case_type_reason']='Second synthetic structural type only'
        second_ref=put(self.root,'review-transfer.json',second_review)
        second_request=json.loads(json.dumps(self.request))
        second_request['case_type']='transfer'
        second_request['case_review']=second_ref
        second_request_ref=put(self.root,'request-transfer.json',second_request)
        with patch('core.real_cases.validate_schema'),patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze',return_value=self._analysis()):
            register(self.root,self.request_ref['path'])
            register(self.root,second_request_ref['path'])
            # The readonly catalog now uses the private historical projection
            # adapter; count actual full request checks, not the admission API.
            actual_validate=real_cases._validate_request
            with patch('core.real_cases._validate_request',wraps=actual_validate) as counted:
                catalog=load_catalog(self.root)
            self.assertEqual(catalog['revision'],2)
            self.assertEqual(counted.call_count,2)
            self.assertEqual({call.args[1]['case_type'] for call in counted.call_args_list},
                             {'canonical','transfer'})

    def test_real_analyzer_schema_graph_trace_end_to_end_synthetic(self):
        self._real_pipeline_original('pdf')

    def test_word_original_real_analyzer_schema_graph_trace_end_to_end_synthetic(self):
        self._real_pipeline_original('docx')

    def _real_pipeline_original(self, fmt):
        """No mocks: exercises the real typed R01 pipeline with program-only text."""
        q=fixture(); method=self.registry.methods['R01']
        original=material(q)
        source_name='typed-source.'+fmt
        self.root.joinpath(source_name).write_bytes(
            word_bytes('Synthetic typed pipeline fixture') if fmt=='docx' else b'%PDF synthetic typed pipeline fixture')
        pdf_hash=digest(self.root.joinpath(source_name).read_bytes())
        leaves={'/stem':q['stem'],'/passage':q['passage'],
                '/options/A':q['options']['A'],'/options/B':q['options']['B']}
        text=' | '.join(leaves.values())
        fields={field:[{'start':text.find(value),'end':text.find(value)+len(value),'quote':value}]
                for field,value in leaves.items()}
        doc=put(self.root,'typed-source.json',{'source_sha256':pdf_hash,'document_text':text})
        blind=put(self.root,'typed-blind.json',{'phase':'source_only_before_reference_read',
                  'paper_id':'synthetic-typed-paper','reviewer_agent':'synthetic-paper-agent',
                  'source_sha256':pdf_hash,'questions':[original]})
        reference_pdf_path=self.root/('typed-reference.'+fmt)
        reference_pdf_path.write_bytes(word_bytes('Synthetic reference') if fmt=='docx' else b'%PDF synthetic third-party reference fixture')
        reference_pdf={'path':reference_pdf_path.name,
                       'sha256':digest(reference_pdf_path.read_bytes())}
        if fmt=='docx': reference_pdf['format']='docx'
        comparison_value={'synthetic_reference':'A','authority':'third_party_unverified'}
        if fmt=='docx': comparison_value['reference_original_ref']=reference_pdf
        comparison=put(self.root,'typed-comparison.json',comparison_value)
        reveal=put(self.root,'typed-reveal.json',{'paper_id':'synthetic-typed-paper',
                   'prediction_sha256':blind['sha256'],
                   'original_comparison_ref':comparison,
                   ('reference_original_ref' if fmt=='docx' else 'reference_pdf_ref'):reference_pdf,
                   'questions':[{'question_id':q['question_id'],'reference_answer':'A',
                                 'answer_authority':'third_party_unverified'}]})
        analysis=QuestionAnalyzer(self.registry).analyze(q)
        own=[x['execution_id'] for x in analysis['execution_trace']
             if x['method_id']=='R01' and x['state']=='produced']
        self.assertTrue(own)
        action=put(self.root,'typed-action.json',{'paper_id':'synthetic-typed-paper',
                   'question_id':q['question_id'],'method_id':'R01',
                   'method_version':method['version'],
                   'mechanical_prediction_sha256':blind['sha256'],
                   'question':q,'analysis':analysis})
        review=put(self.root,'typed-review.json',{'stage':'post_reveal_case_review',
                  'reviewer_kind':'AI','reviewer':'synthetic-second-ai',
                  'paper_agent':'synthetic-paper-agent','independent_from_paper_agent':True,
                  'checks':{k:True for k in ('trigger','action','evidence','role','stop','case_type')},
                  'pass_scope':'private_research_case_only','case_type':'canonical',
                  'case_type_reason':'Program-only structural fixture; no English semantic claim',
                  'question_id':q['question_id'],'canonical_question_id':q['question_id'],
                  'method_id':'R01','method_version':method['version'],
                  'role':method['primary_role'],'stop_rule':method['stop_rule'],
                  'blind_sha256':blind['sha256'],'reveal_sha256':reveal['sha256'],
                  'action_sha256':action['sha256'],
                  'action_analysis_sha256':json_digest(analysis),
                  'evidence_graph_sha256':json_digest(analysis['evidence_graph']),
                  'replay_analysis_sha256':json_digest(analysis),
                  'own_execution_ids':own,('source_original_sha256' if fmt=='docx' else 'source_pdf_sha256'):pdf_hash,
                  'source_document_sha256':doc['sha256'],
                  'pre_reveal_prediction_unchanged':True,'answer_backfit_excluded':True,
                  'own_method_credit_only':True,'trigger':'synthetic reviewed trigger',
                  'action':'synthetic typed decision','evidence':[{'synthetic_program_only':True}]})
        request={'question_id':q['question_id'],'canonical_question_id':q['question_id'],
                 'method_id':'R01','method_version':method['version'],'case_type':'canonical',
                 'source':{('original_path' if fmt=='docx' else 'pdf_path'):source_name,
                           ('original_sha256' if fmt=='docx' else 'pdf_sha256'):pdf_hash,
                           'exam_id':'synthetic-typed-paper','question_id':q['question_id'],
                           'usage_status':'local_research_only','answer_authority':'third_party_unverified',
                           'question_binding':{'document_path':doc['path'],
                                               'document_sha256':doc['sha256'],
                                               ('original_sha256_pointer' if fmt=='docx' else 'pdf_sha256_pointer'):'/source_sha256',
                                               'text_pointer':'/document_text','fields':fields}},
                 'blind':blind,'blind_question_pointer':'/questions/0',
                 'question_input_sha256':json_digest(original),'reveal':reveal,
                 'action':action,'case_review':review}
        if fmt=='docx': request['source']['source_format']='docx'
        req=put(self.root,'typed-request.json',request)
        result=register(self.root,req['path'])
        self.assertEqual(result['review_scope'],'private_AI_reviewed')
        catalog=load_catalog(self.root)
        self.assertEqual(catalog['revision'],1)
        self.assertEqual(self.registry.case_coverage(self.root)['private_catalog']['private_reviewed_case_count'],1)
        reference_pdf_path.write_bytes(b'%PDF changed synthetic reference')
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            load_catalog(self.root)


if __name__ == '__main__': unittest.main()
