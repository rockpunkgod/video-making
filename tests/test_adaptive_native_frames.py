"""Synthetic native-frame receipts: packaging cannot trust stale audit results."""
import importlib.util
import tempfile
import unittest
import json
from unittest.mock import Mock, patch
from pathlib import Path

from content_os.showcase import file_sha
from video_contracts import sha, write


MODULE = Path(__file__).resolve().parents[1] / 'ae/experiments/adaptive-episode/run.py'
SPEC = importlib.util.spec_from_file_location('adaptive_native', MODULE)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class NativeFramesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.frames = self.folder / 'frames'
        self.frames.mkdir()
        self.transfer = {'spec_sha': 'synthetic-spec', 'start_frame': 0,
                         'count': 2, 'frames': {}}
        for i in range(2):
            path = self.frames / f'FRAME_{i:05d}.tif'
            path.write_bytes(b'synthetic frame ' + bytes([i]))
            self.transfer['frames'][path.name] = file_sha(path)
        self.receipt = {'scratch': str(self.frames), 'frames': 2,
                        'spec_sha': 'synthetic-spec', 'transfers': [sha(self.transfer)]}
        self.save()

    def save(self):
        write(self.folder / 'transfer-00000.json', self.transfer)

    def test_complete_bytes_verified(self):
        self.assertEqual(adapter.verify_rendered_frames(self.folder, self.receipt), 2)

    def test_changed_frame_rejected(self):
        (self.frames / 'FRAME_00001.tif').write_bytes(b'changed after native audit')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_missing_frame_rejected(self):
        (self.frames / 'FRAME_00001.tif').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_extra_frame_rejected(self):
        (self.frames / 'FRAME_00002.tif').write_bytes(b'unregistered')
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_changed_binding_rejected(self):
        self.transfer['spec_sha'] = 'other-spec'
        self.save()
        with self.assertRaisesRegex(ValueError, 'binding'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_changed_transfer_order_rejected(self):
        self.transfer['start_frame'] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, 'order'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_forged_receipt_rejected(self):
        self.receipt['transfers'] = ['old-approval']
        with self.assertRaisesRegex(ValueError, 'receipt'):
            adapter.verify_rendered_frames(self.folder, self.receipt)

    def test_invalid_batch_rejected_before_host_access(self):
        for count in (0, -1, 241, True):
            with self.assertRaisesRegex(ValueError, 'Batch size'):
                adapter.render(self.folder, None, None, count)

    def test_fractional_duration_roundoff_preserves_actual_frame_count(self):
        project = self.folder / 'synthetic.aep'
        request = {'project': str(project), 'spec': {'spec_sha': 'synthetic-spec',
            'canvas': {'duration': 235.333333}, 'nodes': []}}
        write(self.folder / 'native-identity.json', {'comp_id': 1})
        native = {'project': str(project), 'comp_id': 1, 'width': 3840,
            'height': 2160, 'fps': 24, 'duration': 5648/24,
            'comment': json.dumps({'spec_sha': 'synthetic-spec'}), 'objects': []}
        client = Mock()
        client.call.side_effect = [{'content': json.dumps(native)},
                                  {'content': json.dumps({'checked_keys': 0, 'errors': []})}]
        with patch.object(adapter, 'current', return_value=request), patch.object(adapter, 'client', return_value=client):
            self.assertEqual(adapter.audit(self.folder)['canvas'], '4K24')
        native['duration'] += 1/24
        client.call.side_effect = [{'content': json.dumps(native)}]
        with patch.object(adapter, 'current', return_value=request), patch.object(adapter, 'client', return_value=client):
            with self.assertRaisesRegex(ValueError, 'timing mismatch'):
                adapter.audit(self.folder)

    def test_partial_episode_cannot_be_packaged(self):
        request = {'project': str(self.folder/'synthetic.aep'),
                   'spec': {'spec_sha': 'synthetic-spec', 'canvas': {'duration': 235.333333}}}
        receipt = dict(self.receipt, canvas=[3840,2160,24], duration=2/24,
                       native_project=request['project'], project_sha='unused')
        write(self.folder/'NATIVE_RENDER_RECEIPT.json', receipt)
        with patch.object(adapter, 'current', return_value=request), patch.object(adapter.subprocess, 'run') as process:
            with self.assertRaisesRegex(ValueError, 'full current episode'):
                adapter.package(self.folder)
            process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
