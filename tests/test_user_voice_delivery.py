"""Synthetic signal fixtures only: no actual user recording or listening acceptance.

Real FFmpeg imports the WAV fixtures. The declaration and MATCHED evidence are
explicit synthetic controls, not claims that generated tones contain speech.
"""
from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from ae_production import authored_episode as authored
from scripts import voice_delivery as voice


class UserRecordingImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'synthetic signal.wav'
        self.make_wav(self.source)
        (self.root / 'text.txt').write_text('SYNTHETIC FIXTURE: no real spoken transcript.', encoding='utf-8')
        (self.root / 'declaration.txt').write_text(
            'SYNTHETIC TEST ONLY. Generated signal, not a human recording declaration.', encoding='utf-8')
        (self.root / 'check.txt').write_text(
            'SYNTHETIC TEST ONLY. Simulated comparison credential, no listening approval.', encoding='utf-8')
        self.request = {
            'schema': 'voice-delivery-import/v1', 'source_kind': 'user_recording',
            'speaker': 'SYNTHETIC FIXTURE, NOT A REAL SPEAKER',
            'declaration': self.binding('declaration.txt'),
            'clips': [{'id': 'synthetic_take', 'audio': self.binding(self.source.name),
                       'transcript': self.binding('text.txt'),
                       'content_check': {**self.binding('check.txt'), 'status': 'MATCHED'}}],
        }
        self.request_path = self.root / 'request.json'

    @staticmethod
    def make_wav(path, rate=48000, channels=1, frames=12345):
        # Non-silent first and last samples expose accidental trims; no speech.
        pcm = b''.join(struct.pack('<h', (i * 97) % 20001 - 10000) * channels
                       for i in range(frames))
        with wave.open(str(path), 'wb') as handle:
            handle.setnchannels(channels); handle.setsampwidth(2); handle.setframerate(rate)
            handle.writeframes(pcm)
        return pcm

    def binding(self, name):
        return {'path': name, 'sha256': voice.sha256(self.root / name)}

    def save_request(self):
        self.request_path.write_text(json.dumps(self.request), encoding='utf-8')

    def imported(self, name='delivery'):
        self.save_request()
        result = voice.import_user_recordings(self.request_path, self.root / name)
        path = Path(result['delivery'])
        return path, voice.validate_user_recordings(path)

    @staticmethod
    def save_delivery(path, delivery):
        path.write_text(json.dumps(delivery), encoding='utf-8')

    def test_real_ffmpeg_preserves_original_bytes_and_complete_pcm_take(self):
        original = self.source.read_bytes()
        path, delivery = self.imported()
        source = delivery['sources'][0]; clip = delivery['clips'][0]
        self.assertEqual((path.parent / source['original_audio']['path']).read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        with wave.open(str(self.source), 'rb') as before, \
                wave.open(str(path.parent / clip['audio']), 'rb') as after:
            self.assertEqual(after.getparams()[:4], before.getparams()[:4])
            self.assertEqual(after.readframes(after.getnframes()), before.readframes(before.getnframes()))
        self.assertEqual(clip['sample_rate'], 48000)
        self.assertEqual(clip['channels'], 1)
        self.assertAlmostEqual(clip['duration_seconds'], 12345 / 48000, places=9)
        self.assertEqual(clip['audio_sha256'], voice.sha256(path.parent / clip['audio']))
        self.assertEqual(source['original_audio']['sha256'], voice.sha256(self.source))
        self.assertEqual(source['derived_audio_sha256'], clip['audio_sha256'])
        self.assertEqual(clip['listening_review'], 'PENDING')
        self.assertFalse(source['speaker_identity_verified_by_software'])

    def test_resampling_stereo_retains_actual_full_duration_and_source(self):
        self.make_wav(self.source, rate=44100, channels=2, frames=11025)
        self.request['clips'][0]['audio'] = self.binding(self.source.name)
        path, delivery = self.imported()
        clip = delivery['clips'][0]
        with wave.open(str(path.parent / clip['audio']), 'rb') as handle:
            self.assertEqual((handle.getframerate(), handle.getnchannels(), handle.getnframes()), (48000, 1, 12000))
        self.assertAlmostEqual(clip['duration_seconds'], .25, places=6)
        source = delivery['sources'][0]
        self.assertEqual((path.parent / source['original_audio']['path']).read_bytes(), self.source.read_bytes())
        stream = next(s for s in source['original_probe']['streams'] if s['codec_type'] == 'audio')
        self.assertEqual(int(stream['sample_rate']), 44100)
        self.assertEqual(stream['channels'], 2)

    def test_dirty_output_is_rejected_without_overwriting_anything(self):
        output = self.root / 'delivery'; output.mkdir()
        marker = output / 'existing.wav'; marker.write_bytes(b'KEEP EXISTING TAKE')
        self.save_request()
        with self.assertRaises(FileExistsError):
            voice.import_user_recordings(self.request_path, output)
        self.assertEqual(marker.read_bytes(), b'KEEP EXISTING TAKE')
        self.assertEqual(list(output.iterdir()), [marker])

    def test_tts_missing_or_unmatched_evidence_and_stale_hash_are_rejected(self):
        original = deepcopy(self.request)
        mutations = (
            lambda r: r.update(source_kind='tts'),
            lambda r: r.pop('declaration'),
            lambda r: r['clips'][0].pop('content_check'),
            lambda r: r['clips'][0]['content_check'].update(status='PENDING'),
            lambda r: r['clips'][0]['audio'].update(sha256='0' * 64),
        )
        for i, mutate in enumerate(mutations):
            with self.subTest(control=i):
                self.request = deepcopy(original); mutate(self.request); self.save_request()
                output = self.root / ('rejected-' + str(i))
                with self.assertRaises((ValueError, KeyError, FileNotFoundError)):
                    voice.import_user_recordings(self.request_path, output)
                self.assertFalse(output.exists())

    def test_blank_provenance_files_do_not_count_as_recording_evidence(self):
        for name in ('declaration.txt', 'check.txt'):
            with self.subTest(evidence=name):
                original = (self.root / name).read_bytes()
                (self.root / name).write_text(' \n\t', encoding='utf-8')
                if name == 'declaration.txt':
                    self.request['declaration'] = self.binding(name)
                else:
                    self.request['clips'][0]['content_check'].update(self.binding(name))
                self.save_request()
                with self.assertRaises(ValueError):
                    voice.import_user_recordings(self.request_path, self.root / (name + '-invalid'))
                (self.root / name).write_bytes(original)
                self.request['declaration'] = self.binding('declaration.txt')
                self.request['clips'][0]['content_check'].update(self.binding('check.txt'))

    def test_unsafe_or_duplicate_take_ids_are_rejected_before_output(self):
        for unsafe in ('../escape', 'nested/take', 'take name'):
            self.request['clips'][0]['id'] = unsafe; self.save_request()
            with self.assertRaises(ValueError):
                voice.import_user_recordings(self.request_path, self.root / 'unsafe')
            self.assertFalse((self.root / 'unsafe').exists())
        self.request['clips'][0]['id'] = 'same'
        self.request['clips'].append(deepcopy(self.request['clips'][0])); self.save_request()
        with self.assertRaises(ValueError):
            voice.import_user_recordings(self.request_path, self.root / 'duplicate')
        self.assertFalse((self.root / 'duplicate').exists())

    def test_original_derivative_transcript_and_evidence_tampering_are_rejected(self):
        path, delivery = self.imported()
        clip = delivery['clips'][0]; source = delivery['sources'][0]
        names = [clip['audio'], clip['transcript'], source['original_audio']['path'],
                 source['content_check']['path'], delivery['recording_source']['declaration']['path']]
        for name in names:
            with self.subTest(asset=name):
                target = path.parent / name; original = target.read_bytes()
                target.write_bytes(original + b' changed')
                with self.assertRaises(ValueError):
                    voice.validate_user_recordings(path)
                target.write_bytes(original)

    def test_delivery_tts_or_absent_provenance_cannot_become_user_voice(self):
        path, delivery = self.imported()
        for mutate in (lambda d: d.pop('recording_source'),
                       lambda d: d['recording_source'].update(kind='tts'),
                       lambda d: d.update(sources=[]),
                       lambda d: d['clips'][0].update(listening_review='REJECTED')):
            changed = deepcopy(delivery); mutate(changed); self.save_delivery(path, changed)
            with self.assertRaises((ValueError, KeyError)):
                voice.validate_user_recordings(path)

    def test_rebound_trimmed_derivative_cannot_claim_the_original_complete_take(self):
        path, delivery = self.imported()
        clip = delivery['clips'][0]
        self.make_wav(path.parent / clip['audio'], frames=6000)
        updated = voice.describe_clip(path.parent, clip['id'], clip['audio'], clip['transcript'])
        delivery['clips'][0] = updated
        delivery['sources'][0]['derived_audio_sha256'] = updated['audio_sha256']
        self.save_delivery(path, delivery)
        # Every derivative hash is current; rejection must check original continuity.
        with self.assertRaises(ValueError):
            voice.validate_user_recordings(path)


class RecordingGuideAndDefaultVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.author = {
            'revision': 'SYNTHETIC RECORDING HANDOFF', 'copy_review': 'PENDING',
            'production_policy': 'industrial_bplus_v1',
            'voices': [{'id': 'one', 'text': 'SYNTHETIC exact copy. No real user recording.'}],
            'scenes': [{'id': 'scene-one', 'title': 'Synthetic', 'voice_ids': ['one']}],
            'recording_direction': {'one': {key: 'SYNTHETIC authored ' + key for key in authored.RECORDING_FIELDS}},
        }
        (self.root / authored.AUTHOR).write_text(json.dumps(self.author), encoding='utf-8')
        (self.root / 'EPISODE_SCRIPT.md').write_text(authored.script_text(self.author), encoding='utf-8')

    def test_guide_binds_exact_copy_scene_and_pending_status_without_claiming_duration(self):
        original = deepcopy(self.author)
        authored.recording_guide(self.root, self.author)
        handoff = json.loads((self.root / 'RECORDING_HANDOFF.json').read_text('utf-8'))
        self.assertEqual(handoff['author_sha256'], voice.sha256(self.root / authored.AUTHOR))
        self.assertEqual(handoff['status'], 'PENDING_HUMAN_VO')
        self.assertFalse(handoff['human_approved'])
        take = handoff['takes'][0]
        self.assertEqual((take['scene_id'], take['take_id'], take['text']),
                         ('scene-one', 'one', self.author['voices'][0]['text']))
        self.assertEqual(take['suggested_file'], 'one__take01.wav')
        self.assertNotIn('duration_seconds', take)
        self.assertEqual(self.author, original)

    def test_every_take_needs_complete_authored_recording_direction(self):
        for field in authored.RECORDING_FIELDS:
            changed = deepcopy(self.author); changed['recording_direction']['one'][field] = ' '
            with self.subTest(field=field), self.assertRaises(ValueError):
                authored.recording_guide(self.root, changed)
        changed = deepcopy(self.author); changed['recording_direction'] = {}
        with self.assertRaises(ValueError):
            authored.recording_guide(self.root, changed)

    def test_default_voice_waits_without_starting_tts_or_creating_takes(self):
        with patch.object(authored, 'checked_author', return_value=(self.author, {})), \
                patch.object(authored.subprocess, 'run', side_effect=AssertionError('Must not launch TTS')), \
                patch.object(authored, 'select_takes', side_effect=AssertionError('Must not select/generate takes')):
            result = authored.voice(self.root)
        self.assertEqual(result['status'], 'PENDING_HUMAN_VO')
        self.assertFalse((self.root / 'voice').exists())
        self.assertFalse((self.root / 'VOICE_INPUT.json').exists())

    def test_existing_legacy_delivery_is_rejected_on_default_human_path(self):
        folder = self.root / 'voice'; folder.mkdir()
        UserRecordingImportTests.make_wav(folder / 'one.wav')
        (folder / 'one.txt').write_text(self.author['voices'][0]['text'], encoding='utf-8')
        legacy = {'schema': 'voice-delivery/v1', 'clips': [voice.describe_clip(folder, 'one', 'one.wav', 'one.txt')]}
        (folder / 'delivery.json').write_text(json.dumps(legacy), encoding='utf-8')
        with patch.object(authored, 'checked_author', return_value=(self.author, {})), \
                patch.object(authored.subprocess, 'run', side_effect=AssertionError('Must not launch TTS')):
            with self.assertRaises(ValueError):
                authored.voice(self.root)


if __name__ == '__main__':
    unittest.main()
