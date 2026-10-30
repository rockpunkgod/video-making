"""Synthetic scope controls; no question source, learner or release approval."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.registry import Registry
from core.release import regression_snapshot


class RegressionSnapshotScopeTests(unittest.TestCase):
    def fixture(self):
        temporary=TemporaryDirectory(prefix='synthetic-snapshot-runtime-')
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        for relative,data in {
            'EVALUATION_PROTOCOL.md':b'synthetic protocol',
            'core/synthetic.py':b'# unchanged synthetic core',
            'video_contracts/objective_images.py':b'# synthetic image binding before',
            'video/schemas/frozen-asset-bundle.json':b'{"synthetic":1}',
        }.items():
            target=root/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        substitution=patch('core.release.ROOT',root)
        substitution.start()
        self.addCleanup(substitution.stop)
        registry=SimpleNamespace(methods={},sources={},risks=[],symptom_cues=[],
                                 grammar_tree={},case_inventory=lambda:{})
        return root,registry

    def test_real_snapshot_covers_pure_answer_proof_runtime_and_embedded_schema(self):
        files=regression_snapshot(Registry())['runtime_files']
        for relative in ('video_contracts/objective_images.py',
                         'video_contracts/image_evidence.py',
                         'video_contracts/answer_consistency.py',
                         'video/schemas/video-package.json'):
            with self.subTest(path=relative):
                self.assertTrue(relative in files,'Snapshot omits '+relative)

    def test_portable_runtime_mutation_invalidates_frozen_snapshot(self):
        root,registry=self.fixture()
        before=regression_snapshot(registry)
        (root/'video_contracts/objective_images.py').write_bytes(b'# synthetic changed owner gate')
        after=regression_snapshot(registry)
        self.assertNotEqual(before,after)
        self.assertNotEqual(before['runtime_files']['video_contracts/objective_images.py'],
                            after['runtime_files']['video_contracts/objective_images.py'])

    def test_embedded_schema_mutation_invalidates_frozen_snapshot(self):
        root,registry=self.fixture()
        before=regression_snapshot(registry)
        (root/'video/schemas/frozen-asset-bundle.json').write_bytes(b'{"synthetic":2}')
        self.assertNotEqual(before,regression_snapshot(registry))

    def test_unchanged_snapshot_is_repeatable_and_does_not_read_private_exam_data(self):
        root,registry=self.fixture()
        before=regression_snapshot(registry)
        private=root/'local-data/synthetic-private-source.json'
        private.parent.mkdir()
        private.write_bytes(b'{"synthetic_private":true}')
        self.assertEqual(before,regression_snapshot(registry))
        self.assertFalse(any('local-data' in name for name in before['runtime_files']))


if __name__=='__main__':
    unittest.main()
