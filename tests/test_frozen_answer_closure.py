"""Synthetic structural regressions only; no English or learner certification."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from answer_engine.frozen_export import FrozenAssetExporter
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from tests.test_execution import fixture
from tests import test_question_verification as terminal_fixtures
from tests import test_optionless_candidate_closure as grammar_fixtures
from video_contracts import (
    ROOT, seal, sha, semantic_payload, presentation_payload, review_semantics,
    verify_bundle, status_matches,
)


class FrozenAnswerClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.engine = QuestionAnalyzer(cls.registry)
        cls.exporter = FrozenAssetExporter()

    def request(self, question=None):
        q = fixture() if question is None else question
        a = self.engine.analyze(q)
        return {'question': q, 'analysis': a,
                'methods': [deepcopy(self.registry.methods[m]) for m in a['method_versions']],
                'reviews': [{'question_id': q['question_id'], 'input_sha256': sha(q),
                    'analysis_sha256': sha(a), 'reviewer_kind': 'AI',
                    'reviewer': 'SYNTHETIC ONLY', 'evaluation_phase': 'post_reveal'}],
                'withdrawals': [], 'evaluation_phase': 'post_reveal',
                'source': {'usage_status': 'internal_only',
                    'redistribution_status': 'redistribution_not_verified',
                    'source_reference': 'synthetic-program-fixture', 'attribution_text': 'SYNTHETIC'}}

    def rebind(self, req):
        for r in req['reviews']:
            r.update(input_sha256=sha(req['question']), analysis_sha256=sha(req['analysis']))

    def resealed_bundle(self, bundle, analysis):
        """Rebind every affected credential/hash; this is not a stale-byte test."""
        b = deepcopy(bundle)
        b['analysis'] = deepcopy(analysis)
        q = b['source_snapshot']
        b['asset_id'] = 'answer:' + q['question_id'] + ':' + sha([
            sha(q), sha(analysis), [(m['method_id'], m['version']) for m in b['methods']]])
        for r in b['reviews']:
            r['record'].update(input_sha256=sha(q), analysis_sha256=sha(analysis))
            r['sha'] = sha(r['record'])
            r['semantic_sha'] = sha(review_semantics(r['record']))
        b['binding_fingerprint'].update(analysis_sha=sha(analysis),
            evidence_graph_sha=sha(analysis['evidence_graph']),
            execution_trace_sha=sha(analysis['execution_trace']))
        b['answer_visible_in_this_bundle'] = analysis['answer'] is not None
        b['semantic_binding_sha'] = sha(semantic_payload(b))
        b['presentation_sha'] = sha(presentation_payload(b))
        return seal(b)

    def reject_at_all_boundaries(self, req, mutate):
        bundle = self.exporter.export(req)
        status = self.exporter.status(req)
        changed = deepcopy(req)
        mutate(changed['analysis'])
        self.rebind(changed)
        before = deepcopy(changed)
        with self.assertRaises(ValueError):
            self.exporter.export(changed)
        with self.assertRaises(ValueError):
            self.exporter.status(changed)
        self.assertEqual(changed, before)
        bad = self.resealed_bundle(bundle, changed['analysis'])
        rebound_status = deepcopy(status)
        rebound_status.update(asset_id=bad['asset_id'], semantic_binding_sha=bad['semantic_binding_sha'])
        rebound_status = seal(rebound_status)
        with self.assertRaises(ValueError):
            verify_bundle(bad)
        with self.assertRaises(ValueError):
            status_matches(bad, rebound_status)
        return bad

    def test_rebound_false_closure_with_unchanged_relation_graph(self):
        q = fixture()
        q['options']['C'] = 'SYNTHETIC unresolved rival'
        req = self.request(q)
        self.assertIsNone(req['analysis']['answer'])
        graph = deepcopy(req['analysis']['evidence_graph'])
        def false_close(a):
            a.update(answer='A', answer_confidence='medium', content_eligible=True)
            a['answer_verification'].update(closed=True, candidate_coverage_complete=True,
                unresolved_candidates=[], eliminated_candidates=['B', 'C'])
        bad = self.reject_at_all_boundaries(req, false_close)
        self.assertEqual(bad['analysis']['evidence_graph'], graph)

    def test_optionless_unresolved_rival_cannot_be_hidden_by_rebound_summary(self):
        grammar = grammar_fixtures.OptionlessCandidateClosureTests()
        req = self.request(grammar.question())
        def false_close(a):
            a.update(answer='synthetic-form-0', answer_confidence='medium', content_eligible=True)
            a['answer_verification'].update(closed=True, candidate_coverage_complete=True,
                unresolved_candidates=[], eliminated_candidates=['synthetic-form-1'])
        self.reject_at_all_boundaries(req, false_close)

    def test_candidate_rows_summary_answer_and_typed_decision_cannot_diverge(self):
        def answer(a): a['answer'] = 'B'
        def rows(a): a['candidate_analysis'][0]['effect'] = 'eliminate'
        def summary(a): a['answer_verification']['retained_candidates'] = ['B']
        def coverage(a): a['answer_verification']['unique_supported_candidate'] = False
        def confidence(a): a['answer_confidence'] = 'low'
        def eligible(a): a['content_eligible'] = False
        def dropped(a): a['candidate_analysis'].pop()
        def typed(a): a['execution_trace'][2]['output']['candidate'] = 'B'
        def edge(a):
            relations = {n['id'] for n in a['evidence_graph']['nodes'] if n['type'] == 'relation'}
            a['evidence_graph']['edges'] = [e for e in a['evidence_graph']['edges']
                                          if e['from'] not in relations]
        for mutation in (answer, rows, summary, coverage, confidence, eligible, dropped, typed, edge):
            with self.subTest(mutation=mutation.__name__):
                self.reject_at_all_boundaries(self.request(), mutation)

    def test_whole_question_proof_is_checked_before_terminal_shortcut(self):
        f = terminal_fixtures.QuestionVerificationTests()
        f.registry = self.registry
        req = self.request(f.question())
        self.assertEqual(req['analysis']['answer'], 'A')
        def changed_answer(a): a['answer'] = 'B'
        def dropped(a): a.pop('question_verification')
        def wrong_effect(a): a['question_verification']['candidate_bindings'][0]['effect'] = 'eliminate'
        def detached(a):
            target = a['question_verification']['candidate_bindings'][0]['decision_node_id']
            a['evidence_graph']['edges'] = [e for e in a['evidence_graph']['edges'] if e['to'] != target]
        for mutation in (changed_answer, dropped, wrong_effect, detached):
            with self.subTest(mutation=mutation.__name__):
                self.reject_at_all_boundaries(req, mutation)

    def test_valid_closed_partial_legacy_optionless_terminal_and_writing_survive(self):
        legacy = fixture(); legacy.pop('action_executions')
        partial = fixture(); partial['options']['C'] = 'SYNTHETIC unresolved rival'
        helper = fixture(); helper.update(relations=[], requested_chain=['R12'])
        helper['observations'] = helper['observations'][:1]
        helper['action_executions'] = helper['action_executions'][:1]
        terminal = terminal_fixtures.QuestionVerificationTests(); terminal.registry = self.registry
        grammar = grammar_fixtures.OptionlessCandidateClosureTests()
        stopped = terminal.question(); stopped['question_verification_review']['stop_applied'] = True
        unresolved = terminal.question()
        unresolved['question_verification_review']['candidate_checks'][1]['backfill_verdict'] = 'unresolved'
        questions = [fixture(), legacy, partial, helper, terminal.question(), stopped, unresolved,
                     grammar.question(), grammar.question(('retain', 'eliminate')),
                     grammar.question(('retain', 'retain')), grammar.question(('eliminate', 'eliminate')),
                     {'question_id': 'synthetic-writing', 'question_type': '应用文',
                      'stem': 'SYNTHETIC writing prompt', 'requested_chain': ['A01']}]
        for q in questions:
            with self.subTest(question=q['question_id'], typed='action_executions' in q):
                req = self.request(q)
                before = deepcopy(req)
                with patch.object(QuestionAnalyzer, 'analyze', side_effect=AssertionError('must not solve')):
                    bundle = self.exporter.export(req)
                    verify_bundle(bundle)
                    status = self.exporter.status(req)
                    self.assertEqual(status_matches(bundle, status), status['effective_status'] == 'ACTIVE')
                self.assertEqual(req, before)
                self.assertEqual(bundle['semantic_review']['level'], 'ai_reviewed')
                self.assertFalse(bundle['semantic_review']['independent_human_certified'])
                self.assertEqual(bundle['source'], req['source'])

    def test_portable_verifier_runs_without_any_teaching_packages(self):
        req = self.request()
        good = self.exporter.export(req)
        a = deepcopy(req['analysis']); a['answer'] = 'B'
        bad = self.resealed_bundle(good, a)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            shutil.copytree(ROOT / 'video_contracts', target / 'video_contracts',
                            ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'schemas', target / 'schemas')
            (target / 'assets.json').write_text(json.dumps([good, bad]))
            code = '''
import builtins, json
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if kwargs.get('level', args[3] if len(args) > 3 else 0) == 0 and name.split('.')[0] in {'core', 'answer_engine', 'renderers'}:
        raise AssertionError('Teaching dependency: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from video_contracts import verify_bundle
valid, invalid = json.load(open('assets.json'))
verify_bundle(valid)
try:
    verify_bundle(invalid)
except ValueError:
    pass
else:
    raise AssertionError('Portable verifier accepted false closure')
'''
            result = subprocess.run([sys.executable, '-c', code], cwd=target,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
