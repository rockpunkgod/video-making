"""Synthetic external-source provenance controls; no real exam credit."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.real_cases import frozen_question, json_digest, material
from tests.test_real_case_catalog import put


class ExternalFrozenSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.q = {'question_id': 'fixture-q1', 'question_type': '阅读理解',
                  'stem': 'Synthetic question', 'passage': 'Synthetic material',
                  'options': {'A': 'Synthetic A', 'B': 'Synthetic B'}}
        self.source = {'phase': 'low_model_source_transcription_no_answers',
                       'reference_read': False, 'paper_id': 'fixture-paper',
                       'source_sha256': 'a'*64, 'inputs': {'questions': [self.q]}}
        self.source_ref = put(self.root, 'original-source.json', self.source)
        self.blind = {'phase': 'agent_before_reference_read', 'paper_id': 'fixture-paper',
                      'source_sha256': 'a'*64, 'reviewer_agent': 'old-prediction-author',
                      'input_sha256': {'original-source.json': self.source_ref['sha256']},
                      'objective_predictions': [{'question_id': 'fixture-q1', 'predicted_answer': None}]}
        self.request = {'question_id': 'fixture-q1', 'blind_question_ref': self.source_ref,
                        'blind_question_pointer': '/inputs/questions/0',
                        'question_input_sha256': json_digest(material(self.q))}

    def test_exact_original_external_source_resolves_without_new_prediction(self):
        before = deepcopy(self.blind)
        self.assertEqual(frozen_question(self.blind, self.request, self.root), self.q)
        self.assertEqual(self.blind, before)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_internal_legacy_pointer_remains_supported(self):
        blind = {'pass': 'blind', 'questions': [self.q]}
        request = {'question_id': 'fixture-q1', 'blind_question_pointer': '/questions/0',
                   'question_input_sha256': json_digest(material(self.q))}
        self.assertEqual(frozen_question(blind, request), self.q)

    def test_rehashing_external_source_cannot_change_original_hash_binding(self):
        self.source['inputs']['questions'][0]['options']['A'] = 'Changed material'
        ref = put(self.root, 'original-source.json', self.source)
        request = dict(self.request, blind_question_ref=ref,
                       question_input_sha256=json_digest(material(self.source['inputs']['questions'][0])))
        with self.assertRaisesRegex(ValueError, 'hash-bind'):
            frozen_question(self.blind, request, self.root)

    def test_source_identity_phase_and_exposure_fail_closed(self):
        for field, value in [('phase', 'post_reveal'), ('reference_read', True),
                             ('reference_read', None), ('paper_id', 'other'),
                             ('source_sha256', 'b'*64)]:
            with self.subTest(field=field, value=value):
                source = deepcopy(self.source); source[field] = value
                ref = put(self.root, 'original-source.json', source)
                blind = deepcopy(self.blind); blind['input_sha256']['original-source.json'] = ref['sha256']
                with self.assertRaisesRegex(ValueError, 'identity differs'):
                    frozen_question(blind, dict(self.request, blind_question_ref=ref), self.root)

    def test_original_prediction_phase_identity_and_uniqueness_required(self):
        for changes in ({'phase': 'post_reveal'}, {'reviewer_agent': ''},
                        {'objective_predictions': []},
                        {'objective_predictions': self.blind['objective_predictions']*2},
                        {'objective_predictions': [{'question_id': 'other'}]},
                        {'input_sha256': {}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                frozen_question(dict(self.blind, **changes), self.request, self.root)

    def test_pointer_material_digest_and_private_root_required(self):
        with self.assertRaisesRegex(ValueError, 'dataset root'):
            frozen_question(self.blind, self.request)
        for changes in ({'blind_question_pointer': '/inputs/questions/1'},
                        {'question_id': 'other'}, {'question_input_sha256': '0'*64},
                        {'blind_question_ref': {'path': '../escaped.json', 'sha256': 'a'*64}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                frozen_question(self.blind, dict(self.request, **changes), self.root)

    def external_registration_fixture(self):
        from tests.test_real_case_catalog import PrivateRealCaseTest
        fixture = PrivateRealCaseTest()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        root = fixture.root
        request = deepcopy(fixture.request)
        source = dict(self.source, paper_id='synthetic-001',
                      source_sha256=request['source']['pdf_sha256'],
                      inputs={'questions': [fixture.question]})
        source_ref = put(root, 'original-source.json', source)
        blind = dict(self.blind, paper_id='synthetic-001', reviewer_agent='first-ai',
                     source_sha256=request['source']['pdf_sha256'],
                     input_sha256={'original-source.json': source_ref['sha256']},
                     objective_predictions=[{'question_id': fixture.question['question_id'],
                                             'predicted_answer': 'A', 'candidate_if_unresolved': None,
                                             'decisive_evidence': []}])
        blind_ref = put(root, 'external-blind.json', blind)
        import json
        reveal = json.loads((root/'reveal.json').read_bytes())
        reveal['prediction_sha256'] = blind_ref['sha256']
        reference_raw = b'%PDF SYNTHETIC REFERENCE ONLY'
        (root/'reference.pdf').write_bytes(reference_raw)
        from core.real_cases import digest
        reference_ref = {'path': 'reference.pdf', 'sha256': digest(reference_raw)}
        comparison = {'phase': 'after_source_only_freeze_reference_read',
                      'paper_id': 'synthetic-001', 'source_sha256': blind['source_sha256'],
                      'reviewer_agent': 'first-ai', 'reference_sha256': reference_ref['sha256'],
                      'rows': [{'question_id': fixture.question['question_id'],
                                'agent_before_reference_read': 'A', 'agent_unresolved_candidate': None,
                                'source_evidence_retained_in_blind': [], 'third_party_reference': 'A'}]}
        reveal.update(phase='post_reveal_adapter_not_new_prediction', reference_pdf_ref=reference_ref,
                      original_comparison_ref=put(root, 'external-comparison.json', comparison),
                      source_only_checkpoint_ref=put(root, 'checkpoint.json', {
                          'blind_sha256': blind_ref['sha256'], 'reference_read': False,
                          'paper_id': 'synthetic-001', 'source_sha256': blind['source_sha256'],
                          'reviewer_agent': 'first-ai'}))
        reveal_ref = put(root, 'external-reveal.json', reveal)
        action = json.loads((root/'action.json').read_bytes())
        action['mechanical_prediction_sha256'] = blind_ref['sha256']
        action['question']['action_executions'] = [{'reviewer': 'current-ai'}]
        action_ref = put(root, 'external-action.json', action)
        review = json.loads((root/'review.json').read_bytes())
        review.update(blind_sha256=blind_ref['sha256'], reveal_sha256=reveal_ref['sha256'],
                      action_sha256=action_ref['sha256'], action_author='current-ai',
                      independent_from_action_author=True, blind_question_ref=source_ref)
        request.update(blind=blind_ref, blind_question_ref=source_ref,
                       blind_question_pointer='/inputs/questions/0', reveal=reveal_ref,
                       action=action_ref, case_review=put(root, 'external-review.json', review))
        return fixture, request, review, action

    def validate_mocked_registration(self, fixture, request):
        # Keep existing synthetic analyzer/schema fixtures explicitly mocked.
        # Real source, review and provenance binding logic runs unchanged.
        from core.real_cases import validate_request
        with patch('core.real_cases.validate_schema'), patch('core.real_cases.validate_graph'), \
                patch('core.real_cases.validate_execution_trace'), \
                patch('core.real_cases.QuestionAnalyzer.analyze', return_value=fixture._analysis()):
            return validate_request(fixture.root, request, fixture.registry)

    def test_external_request_runs_existing_reveal_source_and_case_review_contract(self):
        fixture, request, _, _ = self.external_registration_fixture()
        _, question, _ = self.validate_mocked_registration(fixture, request)
        self.assertEqual(material(question), material(fixture.question))

    def test_distinct_old_author_does_not_allow_current_action_self_review(self):
        fixture, request, review, _ = self.external_registration_fixture()
        review['reviewer'] = 'current-ai'
        request['case_review'] = put(fixture.root, 'external-review.json', review)
        with self.assertRaisesRegex(ValueError, 'actual current action author'):
            self.validate_mocked_registration(fixture, request)

    def test_other_annotation_author_and_wrong_review_source_ref_rejected(self):
        for variant in ('mixed_author', 'wrong_source_ref', 'independence_missing'):
            with self.subTest(variant=variant):
                fixture, request, review, action = self.external_registration_fixture()
                if variant == 'mixed_author':
                    action['question']['lesson_review'] = {'reviewer': 'second-ai'}
                    request['action'] = put(fixture.root, 'external-action.json', action)
                    review['action_sha256'] = request['action']['sha256']
                elif variant == 'wrong_source_ref':
                    review['blind_question_ref'] = dict(request['blind_question_ref'], sha256='0'*64)
                else:
                    review.pop('independent_from_action_author')
                request['case_review'] = put(fixture.root, 'external-review.json', review)
                with self.assertRaisesRegex(ValueError, 'actual current action author'):
                    self.validate_mocked_registration(fixture, request)

    def test_rehashed_same_question_comparison_tampering_is_rejected(self):
        import json
        variants = ('answer', 'prediction', 'evidence', 'unresolved', 'duplicate',
                    'missing_qid', 'paper', 'phase', 'author', 'reference')
        for variant in variants:
            with self.subTest(variant=variant):
                fixture, request, review, _ = self.external_registration_fixture()
                root = fixture.root
                reveal = json.loads((root/'external-reveal.json').read_bytes())
                comparison = json.loads((root/'external-comparison.json').read_bytes())
                if variant == 'answer': reveal['questions'][0]['reference_answer'] = 'B'
                elif variant == 'prediction': comparison['rows'][0]['agent_before_reference_read'] = 'B'
                elif variant == 'evidence': comparison['rows'][0]['source_evidence_retained_in_blind'] = ['fake']
                elif variant == 'unresolved': comparison['rows'][0]['agent_unresolved_candidate'] = 'B'
                elif variant == 'duplicate': comparison['rows'] *= 2
                elif variant == 'missing_qid': comparison['rows'][0]['question_id'] = 'other'
                elif variant == 'paper': comparison['paper_id'] = 'other'
                elif variant == 'phase': comparison['phase'] = 'unknown'
                elif variant == 'author': comparison['reviewer_agent'] = 'other'
                else: comparison['reference_sha256'] = '0'*64
                reveal['original_comparison_ref'] = put(root, 'external-comparison.json', comparison)
                request['reveal'] = put(root, 'external-reveal.json', reveal)
                review['reveal_sha256'] = request['reveal']['sha256']
                request['case_review'] = put(root, 'external-review.json', review)
                with self.assertRaises(ValueError): self.validate_mocked_registration(fixture, request)

    def test_checkpoint_and_comparison_cannot_be_omitted_or_retargeted(self):
        import json
        for variant in ('omit_comparison', 'omit_checkpoint', 'prediction', 'exposure', 'paper'):
            with self.subTest(variant=variant):
                fixture, request, review, _ = self.external_registration_fixture()
                root = fixture.root; reveal = json.loads((root/'external-reveal.json').read_bytes())
                checkpoint = json.loads((root/'checkpoint.json').read_bytes())
                if variant == 'omit_comparison':
                    reveal.pop('original_comparison_ref'); reveal.pop('reference_pdf_ref')
                elif variant == 'omit_checkpoint': reveal.pop('source_only_checkpoint_ref')
                else:
                    key, value = {'prediction': ('blind_sha256', '0'*64),
                                  'exposure': ('reference_read', True), 'paper': ('paper_id', 'other')}[variant]
                    checkpoint[key] = value
                    reveal['source_only_checkpoint_ref'] = put(root, 'checkpoint.json', checkpoint)
                request['reveal'] = put(root, 'external-reveal.json', reveal)
                review['reveal_sha256'] = request['reveal']['sha256']
                request['case_review'] = put(root, 'external-review.json', review)
                with self.assertRaises(ValueError): self.validate_mocked_registration(fixture, request)

    def test_historical_null_is_preserved_but_missing_prediction_field_is_not_null(self):
        import json
        from core.real_cases import check_external_reveal
        fixture, request, _, _ = self.external_registration_fixture()
        root = fixture.root
        blind = json.loads((root/'external-blind.json').read_bytes())
        blind['objective_predictions'][0].update(predicted_answer=None, candidate_if_unresolved='B')
        request['blind'] = put(root, 'external-blind.json', blind)
        checkpoint = json.loads((root/'checkpoint.json').read_bytes())
        checkpoint['blind_sha256'] = request['blind']['sha256']
        reveal = json.loads((root/'external-reveal.json').read_bytes())
        reveal['source_only_checkpoint_ref'] = put(root, 'checkpoint.json', checkpoint)
        comparison = json.loads((root/'external-comparison.json').read_bytes())
        comparison['rows'][0].update(agent_before_reference_read=None, agent_unresolved_candidate='B')
        reveal['original_comparison_ref'] = put(root, 'external-comparison.json', comparison)
        before = deepcopy(blind)
        check_external_reveal(root, request, blind, reveal, reveal['questions'][0])
        self.assertEqual(blind, before)
        blind['objective_predictions'][0].pop('predicted_answer')
        with self.assertRaisesRegex(ValueError, 'predicted_answer'):
            check_external_reveal(root, request, blind, reveal, reveal['questions'][0])
