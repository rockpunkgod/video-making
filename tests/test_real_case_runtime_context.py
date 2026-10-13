"""Historical transport tests; synthetic records are not teaching validation."""
import json
import unittest
from unittest.mock import patch

from core.registry import Registry
from core.real_cases import (CATALOG, _runtime_contexts, artifact, coverage_overlay,
                             digest, freeze_runtime_context, load_catalog, register)
from tests import test_real_case_catalog as fixtures

BASELINE = 'b04ebc26d7fa096404111a0bb12f6c77cc8525b9'


class RuntimeContextTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing *synthetic* source/review fixture, not private exams.
        self.fixture = fixtures.PrivateRealCaseTest()
        history=Registry(snapshot_commit=BASELINE)
        with patch.object(fixtures,'Registry',return_value=history):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        for name in ('validate_schema', 'validate_graph', 'validate_execution_trace'):
            mock = patch('core.real_cases.' + name)
            mock.start(); self.addCleanup(mock.stop)
        mock = patch('core.real_cases.QuestionAnalyzer.analyze',
                     return_value=self.fixture._analysis())
        mock.start(); self.addCleanup(mock.stop)
        # Seed a synthetic catalog as it existed in the old epoch. This is
        # not an admission path for new requests under archived rules.
        with patch('core.real_cases.Registry',return_value=history):
            register(self.root, self.fixture.request_ref['path'])
        self.original = {p.relative_to(self.root).as_posix():p.read_bytes()
                         for p in self.root.rglob('*') if p.is_file()}

    def freeze(self):
        return freeze_runtime_context(self.root, BASELINE)

    def mutate_context(self, change):
        path = self.root / CATALOG / 'runtime-context-000001.json'
        value = json.loads(path.read_bytes()); change(value)
        path.write_bytes(json.dumps(value).encode())

    def test_freeze_is_append_only_idempotent_and_not_new_evidence(self):
        result = self.freeze()
        self.assertEqual(result['historical_request_count'], 1)
        self.assertFalse(result['current_rule_acceptance'])
        before = (self.root/result['context_ref']['path']).read_bytes()
        self.assertEqual(self.freeze()['new_context_count'], 0)
        self.assertEqual((self.root/result['context_ref']['path']).read_bytes(), before)
        for path, raw in self.original.items():
            self.assertEqual((self.root/path).read_bytes(), raw)
        self.assertEqual(load_catalog(self.root)['revision'], 1)

    def test_current_changes_do_not_reinterpret_frozen_requests(self):
        self.freeze()
        current = Registry()
        current.methods['R01']['version'] = '99.0.0'
        current.methods['R01']['stop_rule'] = 'New current boundary'
        self.assertEqual(load_catalog(self.root, registry=current)['revision'], 1)
        with self.assertRaisesRegex(ValueError, 'version'):
            load_catalog(self.root, registry=current, use_runtime_contexts=False)

    def test_history_cannot_admit_new_old_version_requests(self):
        self.freeze()
        current = Registry(); current.methods['R01']['version'] = '99.0.0'
        with patch('core.real_cases.Registry', return_value=current):
            with self.assertRaisesRegex(ValueError, 'version'):
                register(self.root, self.fixture.request_ref['path'])

    def test_coverage_does_not_credit_old_version_to_current_slots(self):
        self.freeze()
        current = Registry(); current.methods['R01']['version'] = '99.0.0'
        coverage = coverage_overlay(current.case_coverage(), self.root)
        own = next(m for m in coverage['methods'] if m['method_id']=='R01')
        self.assertEqual(sum(s['private_registered_case_count'] for s in own['slots']), 0)
        self.assertEqual(coverage['private_catalog']['historical_version_case_count'], 1)
        self.assertEqual(coverage['private_catalog']['private_reviewed_case_count'], 1)

    def test_evidence_upgrade_flags_fail_closed(self):
        self.freeze()
        for field in ('current_rule_acceptance','new_blind_sample'):
            with self.subTest(field=field):
                self.mutate_context(lambda v: v.update({field:True}))
                with self.assertRaisesRegex(ValueError, 'chain mismatch'):
                    load_catalog(self.root)
                self.mutate_context(lambda v: v.update({field:False}))

    def test_frontier_and_snapshot_hashes_are_required(self):
        self.freeze()
        raw = (self.root/CATALOG/'runtime-context-000001.json').read_bytes()
        for field in ('snapshot_manifest_sha256','catalog_ref'):
            with self.subTest(field=field):
                self.mutate_context(lambda v: v.update({field:'0'*64 if field.endswith('sha256')
                                                       else {'path':'request.json','sha256':'0'*64}}))
                with self.assertRaises(ValueError): load_catalog(self.root)
                (self.root/CATALOG/'runtime-context-000001.json').write_bytes(raw)

    def test_missing_or_duplicate_request_assignment_rejected(self):
        self.freeze()
        raw = (self.root/CATALOG/'runtime-context-000001.json').read_bytes()
        for transform in (lambda v:v.update(request_refs=[]),
                          lambda v:v.update(request_refs=v['request_refs']*2)):
            self.mutate_context(transform)
            with self.assertRaisesRegex(ValueError, 'coverage differs'):
                load_catalog(self.root)
            (self.root/CATALOG/'runtime-context-000001.json').write_bytes(raw)

    def test_context_revision_gap_rejected(self):
        result = self.freeze()
        path = self.root/result['context_ref']['path']
        path.rename(path.with_name('runtime-context-000002.json'))
        with self.assertRaisesRegex(ValueError, 'revisions are missing'):
            load_catalog(self.root)


if __name__=='__main__': unittest.main()
