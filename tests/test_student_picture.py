"""SYNTHETIC-only picture bindings and explicit final-voice waiting controls."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from creative_os.student_sample import build_spec, resolve_text, validate_direction, validate_spec, require_sample_delivery
from ae_production.student_picture import _tracks_close
from premiere_production.student_picture import inspect_timeline, inspect_media_items
from video_contracts import pointer, sha


class StudentPictureTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {'asset_id': 'SYNTHETIC:asset', 'semantic_binding_sha': sha('SYNTHETIC semantic'),
            'analysis': {'execution_trace': [{'output': {'candidate': 'B'},
                'evidence': [{'quote': 'SYNTHETIC source relation'}]}]}}
        act = {'asset_id': self.bundle['asset_id'], 'pointer': '/analysis/execution_trace/0',
               'sha': sha(self.bundle['analysis']['execution_trace'][0])}
        evidence = {'asset_id': self.bundle['asset_id'], 'pointer': '/analysis/execution_trace/0/evidence/0',
                    'sha': sha(self.bundle['analysis']['execution_trace'][0]['evidence'][0])}
        self.plan = {'plan_sha': sha('SYNTHETIC plan'),
            'original_question': {'stem': 'SYNTHETIC original question?', 'passage': 'SYNTHETIC passage.',
                                 'options': {'A': 'SYNTHETIC alpha.', 'B': 'SYNTHETIC beta.', 'C': 'SYNTHETIC gamma.'}},
            'source_refs': [act, evidence], 'truth_guard': {'action_refs': [act], 'evidence_refs': [evidence]},
            'evidence_refs': [evidence], 'boundary_delivery': {'focus_evidence_refs': [evidence]},
            'answer_scope': {'may_output_final_answer': False,
                'actual_outputs': [{'kind': 'candidate_decision', 'candidate': 'B', 'effect': 'eliminate'}]}}
        self.copy = {'copy_sha': sha('SYNTHETIC copy'), 'final_copy_sha': sha('SYNTHETIC final'),
            'method_id': 'R02', 'role': 'decider',
            'student_path_comparison': {'baseline_path': [{'candidate_ids': ['A', 'B', 'C']}],
                                      'method_path': [{'candidate_ids': ['A', 'C']}]},
            'script': {}, 'tell_now_boundaries': [{'text': 'SYNTHETIC required boundary'}],
            'final_script': [{'scene_id': 'synthetic-1', 'vo': 'SYNTHETIC execute action',
                             'screen_copy': ['A', 'B', 'C', 'SYNTHETIC required boundary']}]}
        self.documents = {'bundle': self.bundle, 'plan': self.plan, 'copy': self.copy}

        def text(nid, doc, path, x=140, y=250):
            value = pointer(self.documents[doc], path)
            return {'node_id': nid, 'kind': 'text', 'text': value,
                'text_binding': {'document': doc, 'pointer': path, 'sha': sha(value)},
                'size': 30, 'position': [x, y], 'color': '#243530', 'font': 'SYNTHETIC-Font',
                'in_point': 0, 'out_point': 10, 'tracks': {}}
        nodes = [text('question', 'plan', '/original_question/stem', y=120)]
        for index, label in enumerate(('A', 'B', 'C')):
            nodes += [text('option-' + label, 'plan', '/original_question/options/' + label),
                      text('choice-label-' + label, 'copy', f'/final_script/0/screen_copy/{index}')]
        nodes += [text('boundary', 'copy', '/final_script/0/screen_copy/3'),
                  {'node_id': 'choice-B-strike', 'kind': 'line', 'size': 3, 'height': 3,
                   'width': 200, 'position': [140, 250], 'color': '#A17748',
                   'in_point': 7, 'out_point': 10, 'source_refs': [act],
                   'tracks': {'width': [[7, 0], [7.5, 200]]}}]
        self.direction = {'version': '0.1.0', 'profile': 'relation_comparison',
            'canvas': {'width': 1920, 'height': 1080, 'fps': 24, 'duration': 10},
            'palette': {'paper': '#FAF8F2', 'ink': '#243530'}, 'nodes': nodes,
            'phases': {'original': 0, 'focus': 1, 'action': 2, 'collapse': 7, 'stamp': 8, 'end': 10},
            'voice_status': 'AWAITING_USER_AUDIO',
            'voice_slots': [{'scene_id': 'synthetic-1', 'text': 'SYNTHETIC execute action', 'start': 2, 'end': 6}],
            'candidate_transition': {'before': ['A', 'B', 'C'], 'after': ['A', 'C'], 'selected_answer': None}}
        self.fonts = {'synthetic': {'path': 'SYNTHETIC-font.ttf', 'sha256': sha('SYNTHETIC font'),
                                    'postscript': 'SYNTHETIC-Font'}}

    def build(self):
        with patch('creative_os.student_sample.validate_copy', return_value={'consumption_allowed': True}) as gate:
            result = build_spec(self.copy, {}, self.plan, self.bundle, {}, self.direction, self.fonts)
            gate.assert_called_once_with(self.copy, {}, self.plan, self.bundle, {})
            return result

    def test_repeatable_bound_picture_keeps_voice_and_delivery_pending(self):
        spec = self.build()
        self.assertEqual(spec, self.build())
        self.assertFalse(spec['sample_delivery_allowed'])
        self.assertFalse(spec['public_render_ready'])
        with self.assertRaisesRegex(ValueError, 'confirm final voice'):
            require_sample_delivery(spec)

    def test_local_flags_cannot_masquerade_as_user_voice_confirmation(self):
        spec = self.build(); spec['sample_delivery_allowed'] = True; spec['preparation_state'] = 'FINAL_AUDIO_BOUND'
        spec['spec_sha'] = sha({k: v for k, v in spec.items() if k != 'spec_sha'})
        with self.assertRaises(ValueError):
            require_sample_delivery(spec)
        with patch('creative_os.student_sample.validate_copy', return_value={'consumption_allowed': True}):
            with self.assertRaisesRegex(ValueError, 'waiting-for-voice'):
                validate_spec(spec, self.copy, {}, self.plan, self.bundle, {})

    def test_upstream_hold_blocks_even_picture_preparation(self):
        with patch('creative_os.student_sample.validate_copy', return_value={'consumption_allowed': False}):
            with self.assertRaisesRegex(ValueError, 'READY Copy'):
                build_spec(self.copy, {}, self.plan, self.bundle, {}, self.direction, self.fonts)

    def test_reference_text_cannot_be_rewritten_or_sliced_outside_source(self):
        node = self.direction['nodes'][0]
        node['text'] = 'SYNTHETIC invented conclusion'
        with self.assertRaisesRegex(ValueError, 'changed the frozen'):
            self.build()
        binding = dict(node['text_binding'], start=0, end=999)
        with self.assertRaisesRegex(ValueError, 'outside'):
            resolve_text(binding, self.documents)

    def test_backend_or_later_teaching_cannot_enter_the_picture(self):
        self.plan['private_teaching'] = 'SYNTHETIC not disclosed'
        node = self.direction['nodes'][-2]
        node['text_binding'] = {'document': 'plan', 'pointer': '/private_teaching', 'sha': sha(self.plan['private_teaching'])}
        node['text'] = self.plan['private_teaching']
        with self.assertRaisesRegex(ValueError, 'backend-only'):
            self.build()

    def test_scope_role_and_remaining_candidates_cannot_be_promoted(self):
        for change in ('answer', 'role', 'correct_color', 'output'):
            with self.subTest(change=change):
                saved = deepcopy((self.direction, self.plan, self.copy))
                if change == 'answer': self.direction['candidate_transition']['selected_answer'] = 'A'
                if change == 'role': self.copy['role'] = 'framework'
                if change == 'correct_color': self.direction['nodes'][1]['color'] = '#527B65'
                if change == 'output': self.plan['answer_scope']['actual_outputs'][0]['candidate'] = 'C'
                with self.assertRaises(ValueError): self.build()
                self.direction, self.plan, self.copy = saved

    def test_first_question_boundary_and_payoff_presence_are_required(self):
        for change in ('question', 'boundary', 'payoff'):
            with self.subTest(change=change):
                saved = deepcopy(self.direction)
                if change == 'question': self.direction['nodes'][0]['out_point'] = 4
                if change == 'boundary': self.direction['nodes'] = [n for n in self.direction['nodes'] if n['node_id'] != 'boundary']
                if change == 'payoff': self.direction['nodes'][-1]['in_point'] = 1
                with self.assertRaises(ValueError): self.build()
                self.direction = saved

    def test_unbound_action_and_unreadable_key_values_are_rejected(self):
        self.direction['nodes'][-1]['source_refs'][0]['sha'] = sha('SYNTHETIC another action')
        with self.assertRaisesRegex(ValueError, 'unbound source'):
            self.build()
        self.direction['canvas']['duration'] = float('nan')
        with self.assertRaises(ValueError): self.build()

    def test_ae_two_dimensional_readback_handles_native_third_component(self):
        self.assertTrue(_tracks_close({'position': [[0, [140, 120, 0]]], 'scale': [[0, [100, 100, 100]]]},
                                     {'position': [[0, [140, 120]]], 'scale': [[0, [100, 100]]]}))
        self.assertFalse(_tracks_close({'position': [[0, [140, 120, 40]]]}, {'position': [[0, [140, 120]]]}))


class PreparedTimelineTests(unittest.TestCase):
    def test_premiere_reserves_empty_a1_and_refuses_extra_voice_source(self):
        identity = {'sequence_id': 'SYNTHETIC-sequence', 'item_ids': {'picture': 'SYNTHETIC-picture', 'music': 'SYNTHETIC-music'}}
        receipt = {'output': 'SYNTHETIC_PICTURE.mp4'}
        audio = {'duration': 10, 'music': {'clip_path': 'SYNTHETIC_PIANO.wav'}}
        def clip(name): return {'nodeId': name, 'name': name, 'start': 0, 'end': 10, 'duration': 10}
        state = {'id': identity['sequence_id'], 'end': 10,
                 'videoTracks': [{'clips': [clip(receipt['output'])]}],
                 'audioTracks': [{'clips': []}, {'clips': [clip(audio['music']['clip_path'])]}]}
        settings = {'frameSizeHorizontal': 1920, 'frameSizeVertical': 1080, 'timebase': '10584000000',
                    'audioSampleRateHz': 48000, 'audioChannelCount': 2}
        self.assertEqual(inspect_timeline(state, settings, identity, receipt, audio), 'SYNTHETIC_PIANO.wav')
        state['audioTracks'][0]['clips'].append(clip('SYNTHETIC_unapproved_voice.wav'))
        with self.assertRaisesRegex(ValueError, 'empty A1'):
            inspect_timeline(state, settings, identity, receipt, audio)
        media = [{'nodeId': 'SYNTHETIC-picture', 'mediaPath': receipt['output']},
                 {'nodeId': 'SYNTHETIC-music', 'mediaPath': audio['music']['clip_path']}]
        inspect_media_items(media, identity, receipt, audio)
        media.append({'nodeId': 'SYNTHETIC-voice', 'mediaPath': 'SYNTHETIC_voice.wav'})
        with self.assertRaisesRegex(ValueError, 'voice media'):
            inspect_media_items(media, identity, receipt, audio)


if __name__ == '__main__':
    unittest.main()
