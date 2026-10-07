"""SYNTHETIC voice handoffs; no model weights or real exam inputs."""
from pathlib import Path
import random
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from scripts.voice_delivery import describe_clip, pad_to_video_frame
from video_contracts import sha, write
from premiere_production.student_voice import bind_voice, inspect_timeline, inspect_rendered_voice
from voicepacks.tools.generate_gpt_sovits import scripts_from, inference_request


class VoiceProducerTests(unittest.TestCase):
    def test_new_training_profile_keeps_its_pace_and_mixed_language(self):
        profile = {'settings': {'speed_factor': 1, 'seed': 42, 'top_k': 10, 'top_p': 1,
                                'temperature': .75, 'repetition_penalty': 1.15}}
        request = inference_request(profile, 'SYNTHETIC English 与中文。', 'SYNTHETIC.wav', 'SYNTHETIC prompt')
        self.assertEqual(request['text_lang'], 'zh')
        self.assertEqual(request['speed_factor'], 1)
        self.assertEqual(request['text_split_method'], 'cut0')
        self.assertEqual(request['fragment_interval'], .1)
        profile['settings'].update(split_method='cut5', fragment_interval=.3)
        legacy = inference_request(profile, 'SYNTHETIC', 'SYNTHETIC.wav', 'SYNTHETIC')
        self.assertEqual(legacy['text_split_method'], 'cut5')
        self.assertEqual(legacy['fragment_interval'], .3)

    def test_clip_names_cannot_escape_or_overwrite_other_takes(self):
        with TemporaryDirectory() as root:
            path = Path(root) / 'clips.json'
            for rows in ([{'id': '../escape', 'text': 'SYNTHETIC'}],
                         [{'id': 'same', 'text': 'SYNTHETIC'}]*2,
                         [{'id': 'first', 'text': ''}]):
                write(path, rows)
                with self.assertRaises(ValueError): scripts_from(clips_file=path)
            write(path, [{'id': 'first', 'text': 'SYNTHETIC original'}])
            self.assertEqual(scripts_from(clips_file=path)[0]['text'], 'SYNTHETIC original')


class StudentVoiceTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        self.spec = {'spec_sha': sha('SYNTHETIC spec'), 'copy_lock': {'final_copy_sha': sha('SYNTHETIC copy')},
            'direction': {'canvas': {'duration': 10}, 'voice_slots': [
                {'scene_id': 'first', 'text': 'SYNTHETIC first action'},
                {'scene_id': 'stop', 'text': 'SYNTHETIC required Stop'}]}}
        clips = []
        for slot in self.spec['direction']['voice_slots']:
            name = slot['scene_id']
            with wave.open(str(self.root / (name+'.wav')), 'wb') as audio:
                audio.setframerate(48000); audio.setnchannels(1); audio.setsampwidth(2)
                audio.writeframes(b'\0\0'*10000)
            (self.root / (name+'.txt')).write_text(slot['text'], encoding='utf-8')
            clips.append(describe_clip(self.root, name, name+'.wav', name+'.txt', 'USER_ACCEPTED'))
        self.delivery = self.root / 'delivery.json'
        write(self.delivery, {'schema': 'voice-delivery/v1', 'clips': clips})
        self.placements = [{'id': 'first', 'start': 1}, {'id': 'stop', 'start': 4}]
        self.silence = [{'start': 3, 'end': 3.75, 'function': 'SYNTHETIC payoff settle'}]

    def bind(self):
        return bind_voice(self.spec, self.delivery, self.placements, self.silence)

    def test_voice_binding_is_repeatable_and_never_inherits_release(self):
        plan = self.bind(); self.assertEqual(plan, self.bind())
        self.assertEqual(plan['listening_review'], 'PENDING')
        self.assertTrue(all(v['listening_review'] == 'PENDING' for v in plan['voices']))
        for field in ('user_voice_ready_signal_received', 'final_voice_accepted',
                      'sample_delivery_allowed', 'public_render_ready'):
            self.assertFalse(plan[field])

    def test_voice_cannot_overlap_payoff_or_truncate_to_fit(self):
        for change in ('overlap', 'silence', 'end', 'nan'):
            with self.subTest(change=change):
                self.placements = [{'id': 'first', 'start': 1}, {'id': 'stop', 'start': 4}]
                if change == 'overlap': self.placements[1]['start'] = 1.1
                if change == 'silence': self.placements[0]['start'] = 3.25
                if change == 'end': self.placements[1]['start'] = 238/24
                if change == 'nan': self.placements[0]['start'] = float('nan')
                with self.assertRaises(ValueError): self.bind()

    def test_required_stop_and_exact_copy_cannot_be_replaced(self):
        self.spec['direction']['voice_slots'][1]['text'] = 'SYNTHETIC invented shortcut'
        with self.assertRaisesRegex(ValueError, 'exact frozen Copy'): self.bind()
        self.spec['direction']['voice_slots'].pop()
        with self.assertRaisesRegex(ValueError, 'exact spoken scenes'): self.bind()

    def test_native_placement_checks_every_voice_and_refuses_extra_track(self):
        plan = self.bind()
        def clip(path, start, end):
            return {'name': Path(path).name, 'start': start, 'end': end, 'duration': end-start}
        state = {'id': 'SYNTHETIC sequence', 'end': 10,
            'videoTracks': [{'clips': [clip('SYNTHETIC.mp4', 0, 10)]}],
            'audioTracks': [{'clips': [clip(v['path'], v['start'], v['end']) for v in plan['voices']]},
                            {'clips': [clip('SYNTHETIC.wav', 0, 10)]}]}
        settings = {'frameSizeHorizontal': 1920, 'frameSizeVertical': 1080,
                    'timebase': '10584000000', 'audioSampleRateHz': 48000, 'audioChannelCount': 2}
        args = (settings, state['id'], {'output': 'SYNTHETIC.mp4'},
                {'music': {'clip_path': 'SYNTHETIC.wav'}}, plan)
        self.assertEqual(len(inspect_timeline(state, *args)), 4)
        state['audioTracks'][0]['clips'][1]['end'] -= .05
        with self.assertRaisesRegex(ValueError, 'source duration'): inspect_timeline(state, *args)
        state['audioTracks'][0]['clips'][1]['end'] += .05
        state['audioTracks'].append({'clips': [clip('SYNTHETIC other take.wav', 0, 1)]})
        with self.assertRaisesRegex(ValueError, 'clip coverage'): inspect_timeline(state, *args)


class NativeVoiceFrameTests(unittest.TestCase):
    def test_padding_preserves_every_sample_and_never_overwrites(self):
        with TemporaryDirectory() as root:
            source = Path(root) / 'source.wav'; target = Path(root) / 'padded.wav'
            data = b'\x01\x02'*102720  # SYNTHETIC 2.14 s, not a 24 fps boundary.
            with wave.open(str(source), 'wb') as audio:
                audio.setframerate(48000); audio.setnchannels(1); audio.setsampwidth(2)
                audio.writeframes(data)
            receipt = pad_to_video_frame(source, target)
            with wave.open(str(target), 'rb') as audio:
                self.assertEqual(audio.getnframes(), 104000)
                actual = audio.readframes(audio.getnframes())
            self.assertEqual(actual[:len(data)], data)
            self.assertEqual(actual[len(data):], b'\0'*2560)
            self.assertLess(receipt['padding_seconds'], 1/24)
            self.assertFalse(receipt['speech_tempo_changed'])
            with self.assertRaises(FileExistsError): pad_to_video_frame(source, target)

    def test_encoded_media_must_contain_the_bound_voice_not_just_an_audio_stream(self):
        with TemporaryDirectory() as root:
            source = Path(root) / 'SYNTHETIC.wav'
            rng = random.Random(42)
            samples = [rng.randint(-1000, 1000)*2 for i in range(48000)]
            with wave.open(str(source), 'wb') as audio:
                audio.setframerate(48000); audio.setnchannels(1); audio.setsampwidth(2)
                audio.writeframes(struct.pack('<48000h', *samples))
            plan = {'voices': [{'id': 'SYNTHETIC', 'start': 0, 'path': str(source)}]}
            encoded = struct.pack('<48000h', *(x//2 for x in samples))
            with patch('premiere_production.student_voice.subprocess.check_output', return_value=encoded):
                result = inspect_rendered_voice('SYNTHETIC.mp4', plan)
                self.assertGreater(result['voices'][0]['waveform_correlation'], .99)
            with patch('premiere_production.student_voice.subprocess.check_output', return_value=b'\0\0'*1024+encoded):
                result = inspect_rendered_voice('SYNTHETIC.mp4', plan)
                self.assertEqual(result['voices'][0]['codec_offset_samples'], 1024)
            with patch('premiere_production.student_voice.subprocess.check_output', return_value=b'\0\0'*4800+encoded):
                with self.assertRaisesRegex(ValueError, 'missing, muting or shifting'):
                    inspect_rendered_voice('SYNTHETIC.mp4', plan)
            with patch('premiere_production.student_voice.subprocess.check_output', return_value=b'\0\0'*48000):
                with self.assertRaisesRegex(ValueError, 'missing, muting or shifting'):
                    inspect_rendered_voice('SYNTHETIC.mp4', plan)


if __name__ == '__main__': unittest.main()
