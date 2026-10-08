"""Guard tests for the isolated synthetic proof, not mocked Adobe acceptance."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from video_contracts import read, sha, write

HERE = Path(__file__).resolve().parents[1] / 'ae/experiments/method-relay-dual-pass'
spec = importlib.util.spec_from_file_location('relay_proof', HERE / 'run.py')
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
with patch.dict(sys.modules, {'run': relay}):
    spec = importlib.util.spec_from_file_location('relay_editorial', HERE / 'editorial.py')
    editorial = importlib.util.module_from_spec(spec); spec.loader.exec_module(editorial)


class MethodRelayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = read(HERE / 'synthetic-relay.json')

    def request(self, phase='p0'):
        # Portable metrics for contract tests; actual font/AE measurements live
        # in the private production receipts, never substituted by these mocks.
        names = [{'method_id': m, 'name': n} for m, n in
                 [('R12', '关键词追踪'), ('R11', '长句拆骨'), ('R02', '谁干的陷阱')]]
        with patch.object(relay, 'name_snapshots', return_value=names), \
                patch.object(relay, 'file_sha', return_value='a'*64), \
                patch('PIL.ImageFont.truetype', return_value=Mock(getlength=lambda text: len(text)*10)):
            return relay.make_request(relay.LOCAL / 'test', phase)

    def native_fixture(self, request):
        pieces = request['layout'] + [p for o in request['options'] for p in o['pieces']]
        objects = [{'id': o['id'], 'text': o['text'], 'native_layer_id': i+1,
                    'threeD': True, 'source_text_keys': 0, 'origin_sha': request['fixture_sha'],
                    'font': 'Georgia', 'font_size': 40} for i, o in enumerate(pieces)]
        handles = {o['id']: o['native_layer_id'] for o in objects}
        passes = [{'kind': p['kind'], 'handles': deepcopy(handles),
                   'checks': [{'core_opacity': 100}], 'retained_opacities': [{'value': 100}],
                   'column_alignment': [{'id': o['id'], 'dx': 0} for o in objects[5:]],
                   'option_rows': [{'id': o['id'], 'y': o['comparison_y']} for o in request['options']],
                   'peels': [{'id': oid, 'onset': 4, 'release': 4.25, 'detach_seconds': .25}
                             for oid in ('aside-time', 'aside-map')]}
                  for p in request['passes']]
        return {'spec_sha': request['spec_sha'], 'trajectory_sha': request['trajectory_sha'],
                'canvas': [1920, 1080, 24, request['duration']], 'objects': objects, 'passes': passes,
                'name_counts': {m['method_id']: 1 for m in request['method_names']},
                'visible_internal_method_ids': [], 'renderer': 'ADBE Advanced 3d',
                'question': {'text': request['fixture']['stem'], 'source_text_keys': 0},
                'rewind_restore': [{'initial': [100, 100, 100], 'restored': [100, 100, 100]}],
                'production_eligible': False, 'public_render_ready': False}

    def test_synthetic_cannot_be_promoted_to_teaching_or_public(self):
        for field in ('not_a_teaching_asset', 'production_eligible', 'public_render_ready'):
            f = deepcopy(self.fixture); f[field] = not f[field]
            with self.subTest(field=field), self.assertRaises(ValueError): relay.validate_fixture(f)
        for field in self.fixture['claims']:
            f = deepcopy(self.fixture); f['claims'][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_all_characters_keep_their_original_span(self):
        for mutate in (lambda f: f['objects'][1].update(text=', after lunch,'),
                       lambda f: f['objects'][1].update(start=7),
                       lambda f: f['objects'].pop()):
            f = deepcopy(self.fixture); mutate(f)
            with self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_no_protected_peeling_or_deferred_destruction(self):
        for change in ({'protected': True}, {'disposition': 'removed'}, {'attachment': 'unknown'}):
            f = deepcopy(self.fixture); f['objects'][1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): relay.validate_fixture(f)
        f = deepcopy(self.fixture); f['objects'][0]['protected'] = False
        with self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_cue_cannot_borrow_another_span(self):
        for mutate in (lambda f: f['attention_cues'][0].update(object_id='aside-map'),
                       lambda f: f['locate_cues']['stem'].update(text='who'),
                       lambda f: f['attention_cues'].pop()):
            f = deepcopy(self.fixture); mutate(f)
            with self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_relay_requires_predecessor_output_and_explicit_stop(self):
        for change in ({'input': ['new-unreviewed-evidence']}, {'output': 'original-passage'}, {'stop': ''}):
            f = deepcopy(self.fixture); f['trace'][1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_supplied_candidates_cannot_infer_a_new_answer(self):
        f = deepcopy(self.fixture); f['options'][1]['supplied_state'] = 'matches_supplied_fixture'
        with self.assertRaises(ValueError): relay.validate_fixture(f)

    def test_hash_is_stable_across_output_locations_but_tracks_fixture(self):
        r = self.request(); second = deepcopy(r); second['project'] = 'different/diagnostic.aep'
        self.assertEqual(r['spec_sha'], sha({k: v for k, v in second.items() if k not in ('project', 'spec_sha')}))
        second['fixture']['options'][0]['parts'][0] = 'A different actor'
        self.assertNotEqual(r['fixture_sha'], sha(second['fixture']))

    def test_dual_directors_share_trace_but_are_not_scaled_playback(self):
        p0, full = self.request(), self.request('full')
        self.assertEqual(p0['trajectory_sha'], full['trajectory_sha'])
        a, b = full['passes']
        self.assertEqual(a['end']-a['start'], 10)
        self.assertEqual(b['end']-b['start'], 31)
        ratios = [(b[key][1]-b[key][0])/(a[key][1]-a[key][0]) for key in ('locate','align','compare')]
        self.assertGreater(max(ratios)-min(ratios), 1)
        for p in (a, b): self.assertAlmostEqual(p['peel_a'][3]-p['peel_a'][2], .25)

    def test_native_guard_rejects_substitution_loss_and_id_reuse(self):
        r = self.request('full'); good = self.native_fixture(r)
        relay.validate_native(r, good)
        mutations = (lambda n: n['objects'][0].update(text='replacement'),
                     lambda n: n['objects'][0].update(source_text_keys=1),
                     lambda n: n['objects'][0].update(native_layer_id=n['objects'][1]['native_layer_id']),
                     lambda n: n['passes'][1]['handles'].update({'core-subject': 999}),
                     lambda n: n['passes'][0]['checks'][0].update(core_opacity=1),
                     lambda n: n['passes'].pop())
        for mutate in mutations:
            bad = deepcopy(good); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): relay.validate_native(r, bad)

    def test_native_guard_rejects_overlap_misalignment_wrong_peel_and_rewind(self):
        r = self.request('full'); good = self.native_fixture(r)
        mutations = (lambda n: n['passes'][0]['option_rows'][0].update(y=790),
                     lambda n: n['passes'][0]['column_alignment'][0].update(dx=4),
                     lambda n: n['passes'][0].update(column_alignment=[]),
                     lambda n: n['question'].update(text='Different question'),
                     lambda n: n['passes'][0]['peels'][0].update(detach_seconds=1),
                     lambda n: n['passes'][0]['peels'][0].update(onset=None),
                     lambda n: n['rewind_restore'][0].update(restored=[76, 76, 76]),
                     lambda n: n.update(rewind_restore=[]),
                     lambda n: n.update(visible_internal_method_ids=['R02']),
                     lambda n: n['name_counts'].update(R11=2),
                     lambda n: n.update(public_render_ready=True))
        for mutate in mutations:
            bad = deepcopy(good); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): relay.validate_native(r, bad)

    def voices(self, request):
        return [{'id': s['id'], 'text': s['text'], 'text_sha': sha(s['text']),
                 'start': s['start'], 'end': s['start']+1, 'duration': 1, 'listening_review': 'PENDING'}
                for s in relay.voice_slots(request)]

    def test_exact_voices_need_full_length_frame_placement_and_new_review(self):
        r = self.request('full'); voices = self.voices(r); editorial.validate_voices(r, voices)
        mutations = (lambda v: v[0].update(text='New conclusion'),
                     lambda v: v[0].update(id='new-clip'),
                     lambda v: v[0].update(listening_review='ACCEPTED'),
                     lambda v: v[0].update(end=v[0]['end']-.01),
                     lambda v: v[0].update(duration=float('nan')),
                     lambda v: v.pop())
        for mutate in mutations:
            bad = deepcopy(voices); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): editorial.validate_voices(r, bad)

    def test_voices_consume_frozen_request_not_latest_repository_copy(self):
        r = self.request('full'); r['fixture']['voice'][0]['text'] = 'Frozen revision'
        with patch.object(relay, 'read', side_effect=AssertionError('Must not read a different copy')):
            self.assertEqual(relay.voice_slots(r)[0]['text'], 'Frozen revision')

    def test_public_path_and_unrendered_p0_are_rejected(self):
        with self.assertRaises(ValueError): relay.local(relay.ROOT/'ae/outputs')
        with TemporaryDirectory() as tmp, patch.object(relay, 'LOCAL', Path(tmp)):
            out = Path(tmp)/'unrendered'; out.mkdir()
            with patch.object(relay, 'current', return_value=self.request()):
                with self.assertRaises(FileNotFoundError): relay.require_p0(out)

    def test_rendered_p0_requires_unchanged_movie_and_native_completion(self):
        r = self.request(); good = self.native_fixture(r)
        with TemporaryDirectory() as tmp, patch.object(relay, 'LOCAL', Path(tmp)), \
                patch.object(relay, 'current', return_value=r):
            out = Path(tmp); movie = out/'P0.mp4'; project = out/'P0.aep'
            movie.write_bytes(b'unit guard fixture, not an Adobe render'); project.write_bytes(b'unit fixture')
            write(out/'native-audit.json', good)
            receipt = {'spec_sha': r['spec_sha'], 'trajectory_sha': r['trajectory_sha'],
                       'native': {'done': True}, 'output': str(movie), 'output_sha': relay.file_sha(movie),
                       'project': str(project), 'project_sha': relay.file_sha(project)}
            write(out/'render-receipt.json', receipt); relay.require_p0(out)
            movie.write_bytes(b'changed')
            with self.assertRaises(ValueError): relay.require_p0(out)

    def test_uncertain_render_requires_exact_official_recovery_before_connecting(self):
        r = self.request('full')
        with TemporaryDirectory() as tmp, patch.object(relay, 'current', return_value=r), \
                patch.object(relay, 'client') as connect:
            out=Path(tmp)
            write(out/'last-mutation-failure.json',{'tool':'ae_exec','result':{'recoveryId':'abc123'}})
            with self.assertRaises(ValueError):relay.finish(out,'DUAL','madeup')
            connect.assert_not_called()


if __name__ == '__main__': unittest.main()
