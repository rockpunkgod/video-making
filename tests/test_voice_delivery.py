"""Check the portable handoff independently of any speech model installation."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import wave

from scripts.voice_delivery import describe_clip, validate


class VoiceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with wave.open(str(self.root / 'take.wav'), 'wb') as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(48000)
            handle.writeframes(b'\0\0' * 4800)
        (self.root / 'take.txt').write_text('先看原文。', encoding='utf-8')
        self.delivery = {'schema': 'voice-delivery/v1', 'clips': [describe_clip(
            self.root, 'first', 'take.wav', 'take.txt')]}
        self.save()

    def save(self):
        (self.root / 'delivery.json').write_text(json.dumps(self.delivery), encoding='utf-8')

    def test_package_can_move_without_a_model_runtime(self):
        moved = self.root / 'moved'
        moved.mkdir()
        for name in ('take.wav', 'take.txt', 'delivery.json'):
            shutil.copyfile(self.root / name, moved / name)
        self.assertEqual(validate(moved / 'delivery.json')['clips'][0]['sample_rate'], 48000)

    def test_modified_transcript_is_rejected(self):
        (self.root / 'take.txt').write_text('改动后的稿子。', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'transcript_sha256 mismatch'):
            validate(self.root / 'delivery.json')

    def test_modified_audio_is_rejected(self):
        with (self.root / 'take.wav').open('ab') as handle:
            handle.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'audio_sha256 mismatch'):
            validate(self.root / 'delivery.json')

    def test_paths_cannot_escape_package(self):
        self.delivery['clips'][0]['transcript'] = '../take.txt'
        self.save()
        with self.assertRaisesRegex(ValueError, 'inside the delivery directory'):
            validate(self.root / 'delivery.json')

    def test_new_take_does_not_inherit_acceptance(self):
        self.assertEqual(validate(self.root / 'delivery.json')['clips'][0]['listening_review'], 'PENDING')


if __name__ == '__main__':
    unittest.main()
