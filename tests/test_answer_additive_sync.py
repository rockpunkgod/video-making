"""Isolated source-epoch mechanics, never teaching or learner acceptance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.registry import ROOT, Registry
from scripts.capture_answer_revision import sections
from scripts.plan_answer_alignment import build_plan
from scripts.sync_answer_revision import prepare_payload


PREVIOUS = '61bc9c3e15004639cb442c20e7946ca9631f14ce'
TARGET = '1c388a0596b13935ae7c6a1af00834915a8efa33'
ORIGINAL = 'b04ebc26d7fa096404111a0bb12f6c77cc8525b9'


def tree_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


class AdditiveSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory(prefix='answer-additive-test-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name) / 'source'
        cls.old = Registry(snapshot_commit=PREVIOUS)
        shutil.copytree(cls.old.asset_root, cls.root)
        shutil.copytree(ROOT / 'schemas', cls.root / 'schemas')
        for commit in (ORIGINAL, PREVIOUS):
            shutil.copytree(ROOT / 'provenance/runtime-snapshots' / commit,
                            cls.root / 'provenance/runtime-snapshots' / commit)
        for commit in (PREVIOUS, TARGET):
            shutil.copytree(ROOT / 'provenance/upstream-revisions' / commit,
                            cls.root / 'provenance/upstream-revisions' / commit)
        cls.before = tree_bytes(cls.root)
        write_bytes = Path.write_bytes
        def confined_write(path, raw):
            if path.resolve().is_relative_to(ROOT.resolve()):
                raise AssertionError('Fixture staging attempted to write live assets: ' + str(path))
            return write_bytes(path, raw)
        with patch.object(Path, 'write_bytes', confined_write):
            cls.payload, cls.report = prepare_payload(TARGET, root=cls.root)
        cls.after = tree_bytes(cls.root)
        cls.candidate_root = Path(cls.temporary.name) / 'candidate'
        shutil.copytree(cls.root, cls.candidate_root)
        for relative, raw in cls.payload.items():
            path = cls.candidate_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        with patch('core.registry.ROOT', cls.candidate_root):
            cls.candidate = Registry()

    def captured_manifest(self):
        return self.root / 'provenance/upstream-revisions' / TARGET / 'manifest.json'

    def replace_fixture_bytes(self, path, raw):
        previous = path.read_bytes()
        self.addCleanup(path.write_bytes, previous)
        path.write_bytes(raw)

    def edit_captured_section(self, rename=False):
        method = self.old.methods['R01']
        section = self.old.sources['sections'][method['section_ids'][0]]
        manifest_path = self.captured_manifest()
        manifest = json.loads(manifest_path.read_bytes())
        path = manifest_path.parent / 'files' / section['path']
        text = path.read_text(encoding='utf-8')
        current = next(s for s in sections(text) if s['heading'] == section['heading'])
        changed = (current['content'].replace(section['heading'], 'SYNTHETIC_REMOVED_HEADING', 1)
                   if rename else current['content'] + '\nSYNTHETIC changed method instruction.\n')
        raw = text.replace(current['content'], changed, 1).encode('utf-8')
        self.replace_fixture_bytes(path, raw)
        row = next(r for r in manifest['files'] if r['path'] == section['path'])
        row['sha256'] = hashlib.sha256(raw).hexdigest()
        row['byte_count'] = len(raw)
        self.replace_fixture_bytes(manifest_path, json.dumps(manifest).encode('utf-8'))

    def test_staging_preserves_source_and_returns_unapplied_payload(self):
        self.assertEqual(self.before, self.after)
        self.assertEqual(self.before, tree_bytes(self.root))
        self.assertEqual(self.report['from_commit'], PREVIOUS)
        self.assertEqual(self.report['to_commit'], TARGET)
        self.assertEqual(self.report['captured_documents_verified'], 51)
        self.assertEqual(self.report['validation']['methods'], 82)
        self.assertEqual(self.report['validation']['status'], 'PASS')
        for key in ('source_repository_modified', 'historical_cases_modified', 'method_promotion_applied'):
            self.assertFalse(self.report[key])
        self.assertEqual(self.report['learner_acceptance'], 'pending')
        self.assertFalse(any(p.startswith(('cases/', 'provenance/runtime-snapshots/')) for p in self.payload))

    def test_all_method_versions_actions_and_roles_survive_source_rebinding(self):
        self.assertEqual(len(self.candidate.methods), 82)
        self.assertEqual(set(self.old.methods), set(self.candidate.methods))
        self.assertEqual(self.candidate.index['source_baseline']['commit'], TARGET)
        for mid, old in self.old.methods.items():
            with self.subTest(method=mid):
                new = self.candidate.methods[mid]
                for key in ('version', 'core_action', 'primary_role', 'output_type', 'maturity_status',
                            'practical_value', 'four_step_card', 'stop_rule', 'decision_rule'):
                    self.assertEqual(new[key], old[key])
                self.assertFalse(new['student_ready'])
                self.assertEqual(new['source_alignment']['commit'], TARGET)
                self.assertFalse(new['source_alignment']['source_content_changed'])
                self.assertEqual(new['source_alignment']['state'], 'live_source_bound')
                old_sections = [self.old.sources['sections'][sid] for sid in old['section_ids']]
                new_sections = [self.candidate.sources['sections'][sid] for sid in new['section_ids']]
                self.assertEqual([(s['path'], s['heading'], s['content']) for s in old_sections],
                                 [(s['path'], s['heading'], s['content']) for s in new_sections])
                self.assertTrue(all(s['commit'] == TARGET for s in new_sections))
                self.assertTrue(all(r['commit'] == TARGET for r in new['source_references']))
                normalized = deepcopy(new)
                for key in ('section_ids', 'change_reason', 'student_ready'):
                    normalized[key] = deepcopy(old[key])
                normalized['full']['section_ids'] = deepcopy(old['full']['section_ids'])
                for ref in normalized['source_references']:
                    ref['commit'] = PREVIOUS
                for key in ('commit', 'state', 'source_content_changed', 'acceptance'):
                    if key in old['source_alignment']:
                        normalized['source_alignment'][key] = old['source_alignment'][key]
                    else:
                        normalized['source_alignment'].pop(key, None)
                if old.get('static_design_review'):
                    for key in ('source_section_ids', 'status'):
                        normalized['static_design_review'][key] = deepcopy(old['static_design_review'][key])
                self.assertEqual(normalized, old)

    def test_added_source_sections_are_preserved_without_new_method_activation(self):
        known = {(s['path'], s['heading']) for s in self.old.sources['sections'].values()}
        expected = {}
        manifest = self.old._load('provenance/manifest.yaml')
        for row in manifest['files']:
            if not row['path'].endswith('.md'):
                continue
            raw = self.payload['provenance/ANSWER/' + row['path']]
            captured = self.captured_manifest().parent / 'files' / row['path']
            self.assertEqual(raw, captured.read_bytes())
            for section in sections(raw.decode('utf-8')):
                key = (row['path'], section['heading'])
                if key not in known:
                    expected[key] = section['content']
        actual = {(s['path'], s['heading']): s['content']
                  for s in self.candidate.sources['sections'].values()
                  if (s['path'], s['heading']) not in known}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 23)
        self.assertTrue({'题干永远对', '连连看', '图片定位法', '句子写作思路'} <=
                        {heading for _, heading in actual})
        self.assertEqual(self.candidate.index['methods'], self.old.index['methods'])

    def test_historical_case_bytes_and_current_epoch_credit_do_not_change(self):
        self.assertEqual(tree_bytes(self.root / 'cases'), tree_bytes(self.candidate_root / 'cases'))
        with patch('core.registry.ROOT', self.candidate_root):
            inventory = self.candidate.case_inventory()
            examples = [c for c in inventory.values() if c['status'] == 'verified_course_example']
            self.assertEqual(len(examples), 7)
            self.assertTrue(all(c['source_commit'] != TARGET for c in examples))
            self.assertTrue(all(not self.candidate.case_is_current(c) for c in inventory.values()))
            coverage = self.candidate.case_coverage()
            self.assertTrue(all(not s['current_epoch_credit'] for m in coverage['methods'] for s in m['slots']))

    def test_changed_bound_section_with_rehashed_capture_requires_semantic_migration(self):
        self.edit_captured_section()
        with self.assertRaisesRegex(ValueError, 'Changed method content requires semantic migration'):
            prepare_payload(TARGET, root=self.root)

    def test_missing_exact_heading_with_rehashed_capture_is_rejected(self):
        self.edit_captured_section(rename=True)
        with self.assertRaisesRegex(ValueError, 'Existing section removed or renamed'):
            prepare_payload(TARGET, root=self.root)

    def test_tampered_capture_digest_is_rejected(self):
        path = self.captured_manifest()
        manifest = json.loads(path.read_bytes())
        manifest['files'][0]['sha256'] = '0' * 64
        self.replace_fixture_bytes(path, json.dumps(manifest).encode('utf-8'))
        with self.assertRaisesRegex(ValueError, 'Captured source changed'):
            prepare_payload(TARGET, root=self.root)

    def test_wrong_previous_epoch_is_rejected(self):
        path = self.captured_manifest()
        manifest = json.loads(path.read_bytes())
        manifest['previous_runtime_commit'] = ORIGINAL
        self.replace_fixture_bytes(path, json.dumps(manifest).encode('utf-8'))
        with self.assertRaisesRegex(ValueError, 'does not extend the current source epoch'):
            prepare_payload(TARGET, root=self.root)

    def test_historical_plan_stays_bound_to_original_epoch_after_additive_sync(self):
        with patch('core.registry.ROOT', self.root):
            before = build_plan(PREVIOUS, repo_root=self.root)
        with patch('core.registry.ROOT', self.candidate_root):
            after = build_plan(PREVIOUS, repo_root=self.candidate_root)
        self.assertEqual(before['from_commit'], ORIGINAL)
        self.assertEqual(after['from_commit'], ORIGINAL)
        self.assertEqual(before['source_changed_method_count'], 51)
        self.assertEqual(after['source_changed_method_count'], 51)
        self.assertEqual(after['current_runtime_commit'], TARGET)
        before.pop('current_runtime_commit')
        after.pop('current_runtime_commit')
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
