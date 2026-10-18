"""SYNTHETIC B06-shaped event tests; no real question, media or taste result."""
from copy import deepcopy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_video_os as fixtures
from tests import test_method_episode as method_fixtures
from tests.test_adaptive_native_frames import adapter as adaptive
from video_contracts import sha, write, seal
from creative_os.audience_engagement import design_engagement, EDITORIAL_SIGNALS
from ae_production.audience_adapter import compile_adapter, consume_request


class AudienceAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VideoOSTest.setUpClass()

    def setUp(self):
        # Build real frozen packages through project validators, rather than
        # mocking either validate_episode or director_handoff.
        original = deepcopy(fixtures.VideoOSTest.base)
        q = original['question']
        q['options'] = {'B': 'beta', 'C': 'alpha', 'D': 'gamma'}
        for rel in q['relations']:
            if rel['candidate'] == 'A': rel['candidate'] = 'C'
        for action in q['action_executions']:
            if action.get('output', {}).get('candidate') == 'A':
                action['output']['candidate'] = 'C'
        original['analysis'] = fixtures.VideoOSTest.engine.analyze(q)
        original['reviews'][0].update(input_sha256=sha(q), analysis_sha256=sha(original['analysis']))
        # MethodEpisode's fixture creates two independent, genuinely different
        # source materials with their own current manifests.
        with patch.object(fixtures.VideoOSTest, 'base', original):
            base = method_fixtures.MethodEpisodeTests()
            base.setUp()
        self.episode, self.statuses = base.plan, base.statuses
        self.addCleanup(base.doCleanups)
        self.direction = {'schema_version': '0.2.0', 'content_profile': 'FREE_SHOWCASE',
            'opening': {'question_id': self.episode['questions'][0]['question_id'],
                'beat_id': '0', 'hook_strategy': 'actual_problem', 'promise_scope': 'none'}, 'questions': []}
        self.native = {'content_profile': 'FREE_SHOWCASE', 'episode_plan_sha': sha(self.episode), 'scenes': []}
        self.mapping = {}; nodes = []; events = []
        for index, question in enumerate(self.episode['questions']):
            qid = question['question_id']; self.mapping[qid] = {}; beats = []
            bundle = question['package']['source_items'][0]
            action = bundle['source_snapshot']['action_executions'][3]
            self.assertEqual(action['output']['candidate'], 'B')
            ref = {'asset_id': bundle['asset_id'], 'pointer': '/source_snapshot/action_executions/3', 'sha': sha(action)}
            for i, beat in enumerate(question['narrative_beats']):
                sid = f'q{index}-{i}'; start = (index*8+i)*10
                if index == 1 and beat['function'] == 'judgement': sid = 'B06'
                self.mapping[qid][beat['beat_id']] = [sid]
                self.native['scenes'].append({'scene_id': sid, 'question_id': qid,
                    'source_refs': deepcopy(beat['source_refs']), 'time_range': [start, start+10]})
                nodes.append({'node_id': sid, 'source_refs': deepcopy(beat['source_refs']),
                    'in_point': start, 'out_point': start+10,
                    'tracks': {'position': [[start, [0, 0, 20]], [start+10, [0, 0, 20]]]}})
                beats.append({'beat_id': beat['beat_id'], 'engagement_function': 'PAYOFF' if beat['function'] == 'payoff' else 'COMPARISON',
                    'viewer_action': 'compare', 'playback': 'guided_inline', 'energy': 'building',
                    'fresh_information': i > 0, 'editorial_signals': {k: k in ('hook_link_clear', 'reading_space') for k in EDITORIAL_SIGNALS},
                    'viewer_state': {'current_problem': 'SYNTHETIC task', 'information_already_seen': [],
                        'current_attention_object': sid, 'viewer_expectation': 'SYNTHETIC gain',
                        'viewer_task': '只比较已给出的对象', 'unresolved_question': '这两个对象差在哪？',
                        'next_information_gain': '只排除当前候选，不宣布答案'}})
                if sid == 'B06':
                    events.append({'scene_id': sid, 'question_id': qid, 'source_refs': [ref],
                        'candidate': 'B', 'effect': 'eliminate', 'compare_start': start,
                        'decision_start': start+4, 'decision_end': start+5, 'confirmation_start': start+6})
                    self.binding = {'question_id': qid, 'beat_id': beat['beat_id'], 'scene_id': sid,
                        'object_ids': [sid], 'attention_range': [start, start+1], 'reading_range': [start+1, start+4],
                        'candidate_event_id': sid}
            self.direction['questions'].append({'question_id': qid, 'speed_strategy': 'guided_inline',
                'novelty': 'none' if index == 0 else 'new_obstacle', 'payoff_scope': 'locate', 'beats': beats})
        self.spec = {'canvas': {'duration': 160}, 'camera': {'position': [[0, [0, 0, -100]], [160, [0, 0, -100]]]},
                     'nodes': nodes, 'events': events}
        self.reseal()
        self.plan = design_engagement(self.episode, self.statuses, self.direction)
        self.transitions = [{'from_question_id': self.episode['questions'][0]['question_id'],
            'to_question_id': self.episode['questions'][1]['question_id'],
            'payoff_beat_id': '7', 'obstacle_beat_id': '0', 'gain_beat_id': '6'}]

    def reseal(self):
        self.spec['spec_sha'] = sha({k: v for k, v in self.spec.items() if k != 'spec_sha'})

    def compile(self, **kwargs):
        return compile_adapter(self.plan, self.episode, self.statuses, self.direction,
            self.native, self.mapping, self.spec, [self.binding], self.transitions, **kwargs)

    def test_real_validators_b06_task_to_event_and_no_mutation(self):
        before = deepcopy((self.episode, self.direction, self.native, self.spec))
        report = self.compile(); row = report['selected_scenes'][0]
        self.assertEqual(row['candidate_projection']['before'], ['B', 'C', 'D'])
        self.assertEqual(row['candidate_projection']['after'], ['C', 'D'])
        self.assertEqual(row['viewer_task'], '只比较已给出的对象')
        self.assertEqual(report['code_verification'], 'PASS')
        self.assertEqual(report['native_execution'], 'NOT_ASSESSED')
        self.assertEqual(report['actual_media_mapping'], 'UNAVAILABLE')
        self.assertFalse(report['public_render_ready'])
        self.assertEqual(before, (self.episode, self.direction, self.native, self.spec))
        self.assertEqual(self.compile(), report)
        self.assertTrue(report['unselected_handoff_rows'])

    def test_changed_plan_status_and_spec_rejected(self):
        self.plan['human_review'] = 'PASS'
        with self.assertRaises(ValueError): self.compile()
        self.plan = design_engagement(self.episode, self.statuses, self.direction)
        self.spec['canvas']['duration'] += 10
        with self.assertRaisesRegex(ValueError, 'Changed native spec'): self.compile()
        self.reseal()
        for asset, status in self.statuses.items():
            status['effective_status'] = 'WITHDRAWN'; self.statuses[asset] = seal(status)
        with self.assertRaisesRegex(ValueError, 'Withdrawn'): self.compile()

    def test_duplicate_missing_cross_question_or_expired_objects_fail(self):
        for kind in ('duplicate', 'missing', 'expired', 'cross'):
            with self.subTest(kind=kind):
                native = deepcopy(self.spec)
                if kind == 'duplicate': self.binding['object_ids'] = ['B06', 'B06']
                elif kind == 'missing': self.binding['object_ids'] = ['unknown']
                elif kind == 'expired': next(n for n in self.spec['nodes'] if n['node_id'] == 'B06')['out_point'] = 130.5
                else: next(n for n in self.spec['nodes'] if n['node_id'] == 'B06')['source_refs'] = self.spec['nodes'][0]['source_refs']
                self.reseal()
                with self.assertRaises((ValueError, KeyError)): self.compile()
                self.spec = native; self.binding['object_ids'] = ['B06']

    def test_read_before_decision_and_event_cannot_disappear(self):
        self.binding['reading_range'] = [131, 135]
        with self.assertRaisesRegex(ValueError, 'before decision'): self.compile()
        self.binding['reading_range'] = [131, 134]; self.binding['candidate_event_id'] = None
        with self.assertRaisesRegex(ValueError, 'omit'): self.compile()

    def test_no_candidate_promotion_even_with_resealed_spec(self):
        self.spec['events'][0]['effect'] = 'retain'; self.reseal()
        with self.assertRaisesRegex(ValueError, 'frozen action'): self.compile()

    def test_quiet_hold_rejects_voice_and_moving_camera(self):
        self.direction['questions'][1]['beats'][5]['playback'] = 'read_hold'
        self.plan = design_engagement(self.episode, self.statuses, self.direction)
        self.assertTrue(self.compile()['selected_scenes'][0]['quiet_hold'])
        with self.assertRaisesRegex(ValueError, 'voice overlaps'):
            self.compile(voices=[{'start': 132, 'end': 133}])
        self.spec['camera']['position'][1][1][0] = 20; self.reseal()
        with self.assertRaisesRegex(ValueError, 'settled'): self.compile()

    def test_adjacent_progression_projects_existing_states_without_duration_padding(self):
        result = self.compile()['progressions'][0]
        self.assertEqual(result['novelty'], 'new_obstacle')
        self.assertFalse(result['automatic_duration_extension'])
        self.transitions[0]['gain_beat_id'] = '0'
        with self.assertRaisesRegex(ValueError, 'later fresh gain'): self.compile()

    def test_progression_reorder_and_early_payoff_rejected(self):
        self.transitions[0]['to_question_id'] = self.transitions[0]['from_question_id']
        with self.assertRaisesRegex(ValueError, 'adjacent'): self.compile()
        self.transitions[0]['to_question_id'] = self.episode['questions'][1]['question_id']
        self.transitions[0]['payoff_beat_id'] = '0'
        with self.assertRaisesRegex(ValueError, 'Earned payoff'): self.compile()

    def request(self, folder):
        files = {'plan': self.plan, 'audience_direction': self.direction,
                 'native_direction': self.native, 'beat_scenes': self.mapping,
                 'bindings': [self.binding], 'transitions': self.transitions, 'compiled': self.compile()}
        request = {'spec': self.spec, 'voices': [], 'input_files': {}, 'audience_adapter': {}}
        for name, value in files.items():
            path = folder / (name+'.json'); write(path, value)
            request['audience_adapter'][name] = str(path)
            request['input_files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return request

    def test_saved_compilation_is_reconstructed_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = self.request(Path(tmp))
            result = consume_request(request, self.episode, self.statuses)
            self.assertEqual(result, self.compile())
            report = deepcopy(result); report['native_execution'] = 'PASS'
            write(request['audience_adapter']['compiled'], report)
            with self.assertRaises(ValueError): consume_request(request, self.episode, self.statuses)

    def test_unprotected_paths_rejected_and_legacy_request_unchanged(self):
        self.assertIsNone(consume_request({}, self.episode, self.statuses))
        with tempfile.TemporaryDirectory() as tmp:
            request = self.request(Path(tmp)); request['input_files'] = {}
            with self.assertRaisesRegex(ValueError, 'SHA-bound'):
                consume_request(request, self.episode, self.statuses)

    def test_adaptive_current_calls_consumer_and_preflight_never_calls_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); request = self.request(folder)
            # Minimal current() geometry fixture still uses actual episode and
            # status verification. Synthetic text nodes need no lexical slices.
            request.update(episode_plan=str(folder/'episode.json'), statuses={}, public_render_ready=False)
            write(request['episode_plan'], self.episode)
            for asset, status in self.statuses.items():
                path = folder/(asset+'.json'); write(path, status); request['statuses'][asset] = str(path)
            write(folder/'native-request.json', request)
            with patch.object(adaptive, 'client', side_effect=AssertionError('no Adobe')):
                self.assertEqual(adaptive.audience_preflight(folder)['code_verification'], 'PASS')
                self.assertTrue((folder/'AUDIENCE_ADAPTIVE_PREFLIGHT.json').exists())
                wrong = deepcopy(self.compile()); wrong['selected_scenes'] = []
                target = Path(request['audience_adapter']['compiled']); write(target, wrong)
                request['input_files'][str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
                write(folder/'native-request.json', request)
                with self.assertRaisesRegex(ValueError, 'Stale or tampered'):
                    adaptive.current(folder)

    def test_adaptive_preview_consumes_compiled_event_samples(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); request = self.request(folder)
            write(folder/'native-identity.json', {'comp_id': 42})
            host = Mock()
            host.call.return_value = {'synthetic_preview': True}
            with patch.object(adaptive, 'current', return_value=request), \
                    patch.object(adaptive, 'client', return_value=host):
                adaptive.preview(folder)
            expected = self.compile()['preview_times']
            self.assertEqual(host.call.call_args.args[0], 'ae_previewFrame')
            self.assertEqual(host.call.call_args.args[1]['times'], expected)
            self.assertIn(self.spec['events'][0]['confirmation_start'], expected)

    def test_resealed_native_object_source_hash_is_not_trusted(self):
        node = next(n for n in self.spec['nodes'] if n['node_id'] == 'B06')
        node['source_refs'].append({**node['source_refs'][0], 'sha': '0'*64})
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Changed attended object source'):
            self.compile()

    def test_blank_camera_keys_do_not_certify_settled_hold(self):
        self.direction['questions'][1]['beats'][5]['playback'] = 'read_hold'
        self.plan = design_engagement(self.episode, self.statuses, self.direction)
        self.spec['camera']['position'] = []; self.reseal()
        with self.assertRaisesRegex(ValueError, 'ordered authored keys'):
            self.compile()

    def test_b07_retention_preserves_cd_and_prefix_is_not_recounted(self):
        from ae_production.candidate_motion import audit_candidate_events
        question = self.episode['questions'][1]
        bundle = question['package']['source_items'][0]
        action = bundle['source_snapshot']['action_executions'][2]
        self.assertEqual(action['output']['candidate'], 'C')
        event = {'scene_id': 'B07', 'question_id': question['question_id'],
            'source_refs': [{'asset_id': bundle['asset_id'],
                'pointer': '/source_snapshot/action_executions/2', 'sha': sha(action)}],
            'candidate': 'C', 'effect': 'retain', 'compare_start': 150,
            'decision_start': 152, 'decision_end': 153, 'confirmation_start': 154}
        self.spec['events'].append(event); self.reseal()
        report = self.compile()
        self.assertEqual(report['selected_scenes'][0]['candidate_projection']['after'], ['C', 'D'])
        bundles = {b['asset_id']: b for q in self.episode['questions'] for b in q['package']['source_items']}
        self.assertEqual(audit_candidate_events(self.spec['events'], bundles)['events'][1]['after'], ['C', 'D'])
        self.spec['events'].append(deepcopy(self.spec['events'][0])); self.reseal()
        with self.assertRaisesRegex(ValueError, 'Duplicate scene_id'):
            self.compile()


if __name__ == '__main__':
    unittest.main()
