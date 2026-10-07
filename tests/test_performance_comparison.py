"""SYNTHETIC comparison media and optional sidecar gates, no listening claims."""
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from narration_performance.comparison import voice_only, verify_picture_pixels
from premiere_production.student_voice import preflight
from video_contracts import write
from tests import test_student_voice as voice_fixtures


class ComparisonMediaTests(unittest.TestCase):
    def test_voice_only_preserves_actual_samples_and_places_real_silence(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); src=root/'SYNTHETIC.wav'; out=root/'SYNTHETIC-output.wav'
            data=b'\x03\x04'*12000
            with wave.open(str(src),'wb') as audio:
                audio.setframerate(48000); audio.setnchannels(1); audio.setsampwidth(2); audio.writeframes(data)
            voice_only({'duration':1,'voices':[{'path':str(src),'start':.25}]},out)
            with wave.open(str(out),'rb') as audio:
                actual=audio.readframes(audio.getnframes())
            self.assertEqual(actual[:24000],b'\0'*24000)
            self.assertEqual(actual[24000:48000],data)
            self.assertEqual(actual[48000:],b'\0'*48000)

    def test_no_truncation_or_overwriting_a_b_audio(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); src=root/'SYNTHETIC.wav'; out=root/'SYNTHETIC-output.wav'
            with wave.open(str(src),'wb') as audio:
                audio.setframerate(48000); audio.setnchannels(1); audio.setsampwidth(2); audio.writeframes(b'\0\0'*48000)
            plan={'duration':1,'voices':[{'path':str(src),'start':.25}]}
            with self.assertRaisesRegex(ValueError,'truncate'): voice_only(plan,out)
            out.write_bytes(b'SYNTHETIC OLD A/B BYTES')
            with self.assertRaises(FileExistsError): voice_only(plan,out)
            self.assertEqual(out.read_bytes(),b'SYNTHETIC OLD A/B BYTES')

    def test_changed_picture_or_decode_error_invalidates_isolated_voice_variable(self):
        with TemporaryDirectory() as folder:
            completed=subprocess.CompletedProcess([],0,'','')
            with patch('narration_performance.comparison.subprocess.run',return_value=completed), patch(
                    'narration_performance.comparison.subprocess.check_output',side_effect=[b'#SYNTHETIC\nframe A\n',b'#SYNTHETIC\nframe A\n']):
                self.assertEqual(verify_picture_pixels('SYNTHETIC-A','SYNTHETIC-B',folder)['frames'],1)
            with patch('narration_performance.comparison.subprocess.run',return_value=completed), patch(
                    'narration_performance.comparison.subprocess.check_output',side_effect=[b'frame A\n',b'frame B\n']):
                with self.assertRaisesRegex(ValueError,'voice variable'):
                    verify_picture_pixels('SYNTHETIC-A','SYNTHETIC-B',folder)
            with patch('narration_performance.comparison.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','SYNTHETIC decode error')):
                with self.assertRaisesRegex(ValueError,'decode'): verify_picture_pixels('SYNTHETIC-A','SYNTHETIC-B',folder)

    def test_partial_optional_performance_sidecar_is_blocked(self):
        helper=voice_fixtures.StudentVoiceTests(); helper.setUp()
        self.addCleanup(helper.doCleanups)
        write(helper.root/'prepared.json',{})
        write(helper.root/'voice-plan.json',helper.bind())
        request={'prepared_request':str(helper.root/'prepared.json'),'voice_plan':str(helper.root/'voice-plan.json'),
                 'performance_context':'SYNTHETIC-incomplete-sidecar'}
        with patch('premiere_production.student_voice.picture_preflight',return_value=(helper.spec,{}, {'silence_candidates':helper.silence})):
            with self.assertRaisesRegex(ValueError,'complete'): preflight(request)


if __name__ == '__main__': unittest.main()
