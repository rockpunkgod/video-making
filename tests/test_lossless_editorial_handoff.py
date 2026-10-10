import shutil
import subprocess
from pathlib import Path

import tempfile
import unittest

from premiere_production.lossless_handoff import assemble


def media(tmp_path):
    picture, editorial = tmp_path/'picture.mp4', tmp_path/'editorial.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-f', 'lavfi', '-i',
        'color=c=0xf3f0e9:s=3840x2160:r=24', '-frames:v', '4', '-an',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '2',
        '-pix_fmt', 'yuv420p', '-x264-params',
        'colorprim=bt709:transfer=bt709:colormatrix=bt709', str(picture)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(picture),
        '-f', 'lavfi', '-i', 'sine=frequency=700:sample_rate=48000',
        '-map', '0:v:0', '-map', '1:a:0', '-t', str(4/24),
        '-c:v', 'copy', '-c:a', 'aac', '-ac', '2', str(editorial)], check=True)
    return picture, editorial


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Actual codec tools required')
class LosslessHandoffTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.inputs = media(self.folder)

    def test_encoded_picture_audio_and_timestamps_are_preserved(self):
        target = self.folder/'final.mp4'
        receipt = assemble(*self.inputs, target, 4)
        self.assertEqual(receipt['encoded_payload_and_timestamps'], 'UNCHANGED')
        self.assertEqual(receipt['video_packets']['count'], 4)
        self.assertGreater(receipt['audio_packets']['count'], 0)
        self.assertEqual(receipt['decoded_color']['color_space'], 'bt709')
        self.assertEqual(receipt['full_decode'], 'PASS')
        self.assertFalse(receipt['final_voice_accepted'])
        self.assertFalse(receipt['public_render_ready'])
        with self.assertRaises(FileExistsError):
            assemble(*self.inputs, target, 4)

    def test_wrong_whole_episode_duration_is_rejected_before_writing(self):
        target = self.folder/'wrong.mp4'
        with self.assertRaisesRegex(ValueError, 'coverage'):
            assemble(*self.inputs, target, 5)
        self.assertFalse(target.exists())

    def test_source_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError):
            assemble(*self.inputs, self.inputs[0], 4)
