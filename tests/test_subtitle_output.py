from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ae_production.subtitles import validate_native_captions,deliver_sidecar
from video_contracts import write,read


class SubtitleOutput(unittest.TestCase):
    def test_external_mode_refuses_a_single_baked_caption(self):
        plan={'subtitle_mode':'premiere_sidecar','cues':[]}
        self.assertEqual(validate_native_captions(plan,[])['native_caption_layers'],0)
        with self.assertRaises(ValueError):validate_native_captions(plan,[{'name':'CAPTION_old'}])

    def test_legacy_caption_clock_is_still_checked(self):
        plan={'cues':[{'id':'cue','display_lines':['Actual speech'],'start':1,'end':2}]}
        layer={'name':'CAPTION_cue','text':'Actual speech','inPoint':1,'outPoint':2}
        validate_native_captions(plan,[layer])
        layer['outPoint']=2.5
        with self.assertRaises(ValueError):validate_native_captions(plan,[layer])

    def test_sidecar_is_exact_and_cannot_overwrite_a_different_revision(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);video=p/'video.mp4';video.write_bytes(b'unit-test-placeholder-not-media-proof')
            write(p/'AV_PLAN.json',{'subtitle_mode':'premiere_sidecar','cues':[]})
            source=p/'EPISODE_SUBTITLES.srt';source.write_text('1\n00:00:00,000 --> 00:00:01,000\nText\n',encoding='utf-8')
            receipt=deliver_sidecar(p,video)
            self.assertEqual(Path(receipt['srt']).read_bytes(),source.read_bytes())
            Path(receipt['srt']).write_text('foreign revision',encoding='utf-8')
            with self.assertRaises(FileExistsError):deliver_sidecar(p,video)
