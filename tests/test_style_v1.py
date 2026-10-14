"""Contrast math and horizontal profile checks, not visual taste certification."""
from copy import deepcopy
import unittest
from video_contracts import ROOT,read
from ae_production.platforms import resolve_profile
from scripts.contrast_check import rgb,contrast,evaluate


class StyleV1Tests(unittest.TestCase):
    def test_dark_scene_composites_against_its_own_background(self):
        style=read(ROOT/'ae/design/light-dual-space-v1.json')
        self.assertTrue(all(r['passed'] for r in evaluate(style)))
        style['contrast']['combinations']=[dict(foreground='paper',background='comparison_blue',background_opacity=0.25,base='environment',minimum=7)]
        dark=evaluate(style)[0]['ratio']
        del style['contrast']['combinations'][0]['base']
        self.assertGreater(dark,evaluate(style)[0]['ratio'])

    def test_known_wcag_reference(self):
        self.assertAlmostEqual(contrast(rgb('#FFFFFF'),rgb('#000000')),21)
        self.assertEqual(contrast(rgb('#F2F0EA'),rgb('#F2F0EA')),1)

    def test_actual_composited_style_passes(self):
        self.assertTrue(all(r['passed'] for r in evaluate(read(ROOT/'ae/design/style-v1.json'))))

    def test_original_orange_pair_is_not_falsely_certified(self):
        style=read(ROOT/'ae/design/style-v1.json')
        self.assertLess(contrast(rgb(style['palette']['ink']),rgb(style['palette']['attention_orange'])),4.5)
        changed=deepcopy(style)
        changed['palette']['highlight_ink']=changed['palette']['ink']
        self.assertFalse(next(r for r in evaluate(changed) if r['role']=='orange_hit')['passed'])

    def test_horizontal_profile_is_valid_without_stretching_vertical(self):
        horizontal=resolve_profile('bilibili_16x9');vertical=resolve_profile()
        self.assertEqual(horizontal['canvas'],[1920,1080])
        self.assertEqual(horizontal['safe_area_profile']['core'],[96,64,1728,896])
        self.assertEqual(vertical['safe_area_profile']['core'],[96,248,792,1208])
        changed=deepcopy(horizontal);changed['safe_area_profile']['core']=[96,64,1900,1000]
        with self.assertRaises(ValueError):resolve_profile(changed)


if __name__=='__main__':unittest.main()
