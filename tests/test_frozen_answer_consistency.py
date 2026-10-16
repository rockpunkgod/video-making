"""Synthetic frozen-boundary controls; not English or student validation."""
from copy import deepcopy
import ast
import subprocess
import sys
import unittest
from unittest.mock import patch

from answer_engine.frozen_export import FrozenAssetExporter
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from tests.test_execution import fixture
import tests.test_question_verification as terminal_fixtures
from video_contracts import ROOT, sha, verify_bundle


class FrozenAnswerConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.engine = QuestionAnalyzer(cls.registry)
        cls.exporter = FrozenAssetExporter()

    def request(self, question):
        analysis = self.engine.analyze(question)
        return {'question': question, 'analysis': analysis,
                'methods': [deepcopy(self.registry.methods[m]) for m in analysis['method_versions']],
                'reviews': [], 'withdrawals': [], 'evaluation_phase': 'post_reveal',
                'source': {'usage_status': 'internal_only',
                           'redistribution_status': 'redistribution_not_verified',
                           'source_reference': 'synthetic-program-fixture',
                           'attribution_text': 'SYNTHETIC'}}

    def rebind_synthetic_review(self, request):
        request['reviews'] = [{'question_id': request['question']['question_id'],
            'input_sha256': sha(request['question']), 'analysis_sha256': sha(request['analysis']),
            'reviewer_kind': 'AI', 'reviewer': 'EXPLICIT SYNTHETIC DEFECT CONTROL',
            'evaluation_phase': 'post_reveal'}]

    def rejected_at_boundaries(self, request):
        self.rebind_synthetic_review(request)
        with self.assertRaises(ValueError):
            self.exporter.export(request)
        with self.assertRaises(ValueError):
            self.exporter.status(request)
        # Construct a fully rehashed adversarial transport. Disabling checks is
        # confined to this explicit synthetic fixture; the consumer stays real.
        with patch('answer_engine.frozen_export.validate_frozen_answer'), \
                patch('answer_engine.frozen_export.validate_graph'):
            bad_bundle = self.exporter.export(request)
        with self.assertRaises(ValueError):
            verify_bundle(bad_bundle)

    def terminal_question(self):
        helper = terminal_fixtures.QuestionVerificationTests()
        helper.registry = self.registry
        return helper.question()

    def test_partial_elimination_cannot_be_promoted_to_closed_answer(self):
        q = fixture()
        q['options']['C'] = 'synthetic unresolved rival'
        req = self.request(q)
        self.assertIsNone(req['analysis']['answer'])
        a = req['analysis']
        a.update(answer='A', answer_confidence='medium', content_eligible=True)
        a['answer_verification'].update(unresolved_candidates=[], closed=True,
                                        candidate_coverage_complete=True)
        self.rejected_at_boundaries(req)

    def test_answer_and_summary_cannot_disagree_with_relation_proof(self):
        req = self.request(fixture())
        a = req['analysis']
        a['answer'] = 'B'
        a['answer_verification'].update(retained_candidates=['B'], eliminated_candidates=['A'])
        self.rejected_at_boundaries(req)

    def test_original_candidate_scope_cannot_be_dropped_or_rebound(self):
        for mutation in ('missing_material', 'missing_candidates', 'shrunken_candidates', 'changed_stem'):
            with self.subTest(mutation=mutation):
                req = self.request(fixture())
                root = req['analysis']['evidence_graph']['nodes'][0]
                if mutation == 'missing_material': root.pop('material_sha256')
                elif mutation == 'missing_candidates': root.pop('candidate_ids')
                elif mutation == 'shrunken_candidates': root['candidate_ids'] = ['A']
                else: req['question']['stem'] += ' changed synthetic source'
                self.rejected_at_boundaries(req)

    def test_whole_question_terminal_answer_and_decisions_are_checked(self):
        for mutation in ('answer', 'decision', 'dropped_report'):
            with self.subTest(mutation=mutation):
                req = self.request(self.terminal_question())
                a = req['analysis']
                if mutation == 'answer': a['answer'] = 'B'
                elif mutation == 'decision':
                    a['question_verification']['candidate_bindings'][0]['effect'] = 'eliminate'
                else:
                    a.pop('question_verification')
                    a['schema_version'] = '1.7.0'
                self.rejected_at_boundaries(req)

    def test_terminal_proof_must_bind_original_complete_claims(self):
        req = self.request(self.terminal_question())
        req['question']['options']['A'] = 'changed complete claim'
        self.rejected_at_boundaries(req)

    def test_original_quote_is_checked_by_portable_consumer(self):
        req = self.request(self.terminal_question())
        evidence = next(n for n in req['analysis']['evidence_graph']['nodes']
                        if n['type'] == 'source_evidence')
        evidence['span']['quote'] = 'forged synthetic quote'
        self.rejected_at_boundaries(req)

    def test_stopped_backfill_cannot_restore_answer(self):
        q = fixture()
        q['action_executions'][-1]['output']['verdict'] = 'unresolved'
        req = self.request(q)
        self.assertIsNone(req['analysis']['answer'])
        req['analysis'].update(answer='A', answer_confidence='medium', content_eligible=True)
        req['analysis']['answer_verification']['closed'] = True
        self.rejected_at_boundaries(req)

    def test_valid_typed_legacy_terminal_and_open_proofs_are_read_only(self):
        typed = fixture()
        legacy = fixture(); legacy.pop('action_executions')
        unresolved = fixture(); unresolved['options']['C'] = 'synthetic unresolved rival'
        for q in (typed, legacy, self.terminal_question(), unresolved):
            req = self.request(q)
            self.rebind_synthetic_review(req)
            before = deepcopy(req)
            with patch.object(QuestionAnalyzer, 'analyze', side_effect=AssertionError('must not solve')):
                bundle = self.exporter.export(req)
                verify_bundle(bundle)
                self.assertEqual(self.exporter.status(req)['effective_status'],
                                 'ACTIVE' if req['analysis']['execution_trace'] else 'INCOMPLETE')
            self.assertEqual(req, before)

    def test_portable_import_does_not_load_solver_or_course_runtime(self):
        result = subprocess.run([sys.executable, '-c',
            "import sys; from video_contracts import verify_bundle; "
            "from video_contracts.answer_consistency import validate_frozen_answer; "
            "assert not any(n.split('.')[0] in {'core','answer_engine','renderers'} for n in sys.modules)"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        tree = ast.parse((ROOT / 'video_contracts/answer_consistency.py').read_text('utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or '').split('.')[0], {'core', 'answer_engine', 'renderers'})


if __name__ == '__main__':
    unittest.main()
