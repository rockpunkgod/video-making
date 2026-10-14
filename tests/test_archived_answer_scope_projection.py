"""Historical serialization compatibility only; no current Case credit."""
from copy import deepcopy
import inspect
import unittest
from unittest.mock import patch

from core.analyzer import QuestionAnalyzer
from core.real_cases import _archived_scope_projection_equal, validate_request
from core.registry import Registry
from tests.test_execution import fixture


class ArchivedScopeProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = QuestionAnalyzer(Registry()).analyze(fixture())

    def archived(self):
        archived = deepcopy(self.current)
        root = archived['evidence_graph']['nodes'][0]
        root.pop('material_sha256')
        root.pop('candidate_ids')
        return archived

    def test_only_exact_old_serialization_is_compatible(self):
        current = deepcopy(self.current)
        archived = self.archived()
        before = deepcopy(archived)
        self.assertTrue(_archived_scope_projection_equal(current, archived))
        self.assertEqual(current, self.current)
        self.assertEqual(archived, before)

    def test_current_admission_api_has_no_historical_switch(self):
        self.assertEqual(list(inspect.signature(validate_request).parameters),
                         ['root', 'request', 'registry'])

    def test_partial_scope_and_changed_claim_or_answer_fail_closed(self):
        for mutation in ['material_only', 'candidates_only', 'answer', 'claim',
                         'row', 'root_label', 'scope_on_wrong_node']:
            old = self.archived()
            if mutation == 'material_only':
                old['evidence_graph']['nodes'][0]['material_sha256'] = '0' * 64
            elif mutation == 'candidates_only':
                old['evidence_graph']['nodes'][0]['candidate_ids'] = ['A']
            elif mutation == 'answer':
                old['answer'] = 'B'
            elif mutation == 'claim':
                next(n for n in old['evidence_graph']['nodes']
                     if n['type'] == 'candidate_claim')['label'] = 'changed claim'
            elif mutation == 'row':
                old['candidate_analysis'][0]['effect'] = 'eliminate'
            elif mutation == 'root_label':
                old['evidence_graph']['nodes'][0]['label'] = 'changed stem'
            else:
                old['evidence_graph']['nodes'][1]['material_sha256'] = '0' * 64
            with self.subTest(mutation=mutation):
                self.assertFalse(_archived_scope_projection_equal(self.current, old))

    def test_new_scope_is_never_stripped_from_an_existing_scoped_proof(self):
        self.assertFalse(_archived_scope_projection_equal(self.current, self.current))

    def test_missing_new_anchor_cannot_use_historical_adapter(self):
        self.assertFalse(_archived_scope_projection_equal(self.archived(), self.archived()))

    def test_old_catalog_loads_but_cannot_register_or_credit_current_slot(self):
        import json
        from core.real_cases import load_catalog, register
        from tests.test_real_case_catalog import PrivateRealCaseTest
        fixture_case = PrivateRealCaseTest()
        fixture_case.setUp()
        self.addCleanup(fixture_case.doCleanups)
        actual_analyze = QuestionAnalyzer.analyze

        def historical_serialization(engine, question):
            # Simulate only the old serializer's root shape in a synthetic
            # temporary corpus; all other fields use the actual analyzer.
            result = actual_analyze(engine, question)
            root = result['evidence_graph']['nodes'][0]
            root.pop('material_sha256')
            root.pop('candidate_ids', None)
            return result

        with patch.object(QuestionAnalyzer, 'analyze', historical_serialization):
            fixture_case._real_pipeline_original('pdf')
        # The helper ends with a source-fingerprint negative control. Restore
        # only this known synthetic fixture, never a user's original document.
        (fixture_case.root / 'typed-reference.pdf').write_bytes(
            b'%PDF synthetic third-party reference fixture')
        original_bytes = {str(p): p.read_bytes() for p in fixture_case.root.rglob('*') if p.is_file()}
        self.assertEqual(load_catalog(fixture_case.root)['revision'], 1)
        request = json.loads((fixture_case.root / 'typed-request.json').read_text())
        with self.assertRaisesRegex(ValueError, 'replay differs'):
            validate_request(fixture_case.root, request, fixture_case.registry)
        with self.assertRaisesRegex(ValueError, 'replay differs'):
            register(fixture_case.root, 'typed-request.json')
        coverage = fixture_case.registry.case_coverage(fixture_case.root)
        self.assertEqual(coverage['private_catalog']['private_reviewed_case_count'], 1)
        self.assertEqual(coverage['private_catalog']['current_structural_case_count'], 0)
        self.assertEqual(coverage['private_catalog']['historical_or_unbound_case_count'], 1)
        own = next(m for m in coverage['methods'] if m['method_id'] == 'R01')
        self.assertEqual(sum(s['private_registered_case_count'] for s in own['slots']), 0)
        self.assertEqual({str(p): p.read_bytes() for p in fixture_case.root.rglob('*') if p.is_file()}, original_bytes)
