"""Synthetic protection tests for visual-only Hero alternatives."""
from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from http.client import RemoteDisconnected
from unittest.mock import Mock, patch

from video_contracts import read, sha, seal
from tests import test_hero_identity
from creative_os.hero_directions import make_direction
from ae_production.execution import mutation_call
from ae_production.hero_execution import render_intermediate


class DirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_hero_identity.HeroTests.setUpClass()

    def setUp(self):
        self.fixture = test_hero_identity.HeroTests()
        self.fixture.setUp()
        for node in self.fixture.nodes:
            node.update(size=32, font='NotoSansSC-Regular', color='#20211F')
        self.fixture.nodes[0]['node_id'] = 'EVIDENCE_BLANK'
        self.fixture.nodes.append({'node_id': 'SLOT_CARRY', 'kind': 'shape',
                                   'position': [980, 552], 'size': [440, 4], 'fill': '#7E96A8',
                                   'tracks': {'position': [[0, [980, 552]], [3.25, [980, 552]],
                                               [4.05, [273, 405]], [4.25, [268, 405]]]}})
        self.fixture.beats = [{'start': 0, 'end': 8, 'phase': 'MOVE'},
                              {'start': 8, 'end': 12, 'phase': 'HOLD'}]
        self.base = self.fixture.build(design={'id': 'A_PAPER_CUT', 'background': '#F2F0EA',
                                              'ink': '#20211F', 'secondary': '#58625C'})
        self.profiles = read('ae/design/swiss-cognitive-directions-v0.5.json')['directions']

    def variant(self, profile, statuses=None, base=None):
        f = self.fixture
        return make_direction(base or self.base, profile, f.package, f.manifest,
                              f.statuses if statuses is None else statuses,
                              f.full, f.excerpt, 7)

    def test_variants_preserve_frozen_copy_micro_lock_and_base(self):
        before = sha(self.base)
        results = [self.variant(profile) for profile in self.profiles]
        self.assertEqual(before, sha(self.base))
        self.assertEqual(len({r['render_contract_sha'] for r in results}), 3)
        for result in results:
            for key in ('package_sha', 'excerpt_sha', 'full_delivery_sha', 'scope', 'copy_lock', 'beats'):
                self.assertEqual(result[key], self.base[key])
            texts = lambda c: [(n['text'], n['unit_id']) for n in c['nodes'] if n['kind'] == 'text']
            self.assertEqual(texts(result), texts(self.base))
            keys = next(n for n in result['nodes'] if n['node_id'] == 'SLOT_CARRY')['tracks']['position']
            self.assertEqual(keys[-2][1][0] - keys[-1][1][0], 5)
            self.assertAlmostEqual((keys[-1][0] - keys[-2][0]) * 24, 4.8)
            self.assertEqual(result['human_taste_review'], 'PENDING')
            self.assertFalse(result['public_render_ready'])

    def test_visual_alternative_cannot_bypass_withdrawal(self):
        statuses = deepcopy(self.fixture.statuses)
        for key, value in statuses.items():
            value['effective_status'] = 'WITHDRAWN'
            statuses[key] = seal(value)
        with self.assertRaises(ValueError):
            self.variant(self.profiles[0], statuses=statuses)

    def test_changed_source_text_cannot_be_disguised_as_direction(self):
        base = deepcopy(self.base)
        base['nodes'][0]['text'] = '答案已经确定'
        with self.assertRaises(ValueError):
            self.variant(self.profiles[0], base=base)

    def test_native_disconnect_is_recorded_without_retry(self):
        client = Mock()
        client.call.side_effect = RemoteDisconnected('Synthetic native host exit')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RemoteDisconnected):
                mutation_call(client, 'ae_exec', {'code': 'SYNTHETIC'}, directory, 60)
            self.assertEqual(client.call.call_count, 1)
            failure = read(Path(directory) / 'last-mutation-failure.json')
            self.assertEqual(failure['result']['state'], 'uncertain')
            self.assertEqual(failure['result']['error_type'], 'RemoteDisconnected')

    def test_incomplete_native_sequence_never_reaches_encoder(self):
        client = Mock()
        client.call.side_effect = [{'layers': []}, {'valid': True, 'truncated': False}]
        with tempfile.TemporaryDirectory() as directory:
            def native_result(*args, **kwargs):
                (Path(directory) / 'native-tiff' / 'FRAME_00000.tif').write_bytes(b'SYNTHETIC')
                return {'content': '{"ok":true}'}
            with patch('ae_production.hero_execution.validate_contract'), \
                 patch('ae_production.hero_execution.audit'), \
                 patch('ae_production.hero_execution.mutation_call', side_effect=native_result), \
                 patch('ae_production.hero_execution.subprocess.run') as encoder:
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    render_intermediate(client, {'canvas': {'duration': 10}}, {}, {}, {}, {}, {}, 1, directory)
                encoder.assert_not_called()

    def test_existing_intermediate_requires_reconciliation(self):
        client = Mock()
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'native-tiff').mkdir()
            with patch('ae_production.hero_execution.validate_contract'):
                with self.assertRaisesRegex(ValueError, 'inspect rather than retry'):
                    render_intermediate(client, {}, {}, {}, {}, {}, {}, 1, directory)
            client.call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
