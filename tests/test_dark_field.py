"""Synthetic pixel/readback checks, not a certification of visual taste."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from video_contracts import write
from scripts.check_dark_field import check
from creative_os.dark_field_proof import contrast


class DarkFieldChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.a=Path(self.temp.name)/'direct';self.b=Path(self.temp.name)/'rebuilt'
        for folder in (self.a,self.b):
            folder.mkdir();write(folder/'NATIVE_READBACK.json',dict(origin=[],tracks=[{'x':1}],background0=[1],background4_5=[0]))
            write(folder/'STATE_AUDIT.json',dict(world_opacity_4_5=100,world_blur_4_5=3.2,
                world_depth_4_5=600,eliminate_screen_dy=24,eliminate_opacity=20))
            for t in (0,2.5,4.5,8,18):
                im=Image.new('RGB',(1920,1080),'#F2F0EA' if t==0 else '#17181A')
                if t==18:ImageDraw.Draw(im).rectangle((110,790,200,840),fill='#F2F0EA')
                im.save(folder/f'FRAME_{t}.png')

    def test_real_dark_field_and_equal_rebuild(self):
        self.assertGreater(contrast('#F2F0EA','#17181A'),15)
        self.assertTrue(check(self.a,self.b)['sample_frames_pixel_identical'])

    def test_gray_is_not_a_dark_field(self):
        Image.new('RGB',(1920,1080),'#777777').save(self.b/'FRAME_4.5.png')
        with self.assertRaisesRegex(ValueError,'Rendered field'):check(self.a,self.b)

    def test_same_palette_does_not_hide_changed_trajectory(self):
        write(self.b/'NATIVE_READBACK.json',dict(origin=[],tracks=[{'x':2}],background0=[1],background4_5=[0]))
        with self.assertRaisesRegex(ValueError,'tracks'):check(self.a,self.b)
