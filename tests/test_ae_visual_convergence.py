"""Synthetic controls for versioned visual mapping; not human taste certification."""
from copy import deepcopy
from pathlib import Path
import unittest
from video_contracts import ROOT,read,sha
from ae_production.contract import build_contract,validate_contract,template_path
from ae_production.platforms import resolve_profile
from ae_production.layout import wrap,subtitle_cues,LINE_START_FORBIDDEN,LINE_END_FORBIDDEN
from ae_production.visual_qa import contrast,projection_qa
from tests import test_ae_production as fixture


class VisualConvergenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.AEProductionTest.setUpClass()
        cls.package=fixture.AEProductionTest.package;cls.manifest=fixture.AEProductionTest.manifest
        cls.statuses=fixture.AEProductionTest.statuses
        cls.design=read(ROOT/'ae/design/legacy/swiss-academic-motion-v0.2.json')
        if not Path(cls.design['font']['measurement_file']).exists():
            cls.design['font']=deepcopy(fixture.AEProductionTest.design['font'])
            cls.design['font']['measurement_margin_px']=16

    def contract(self,**kwargs):return build_contract(self.package,self.manifest,self.statuses,self.design,**kwargs)

    def test_versioned_templates_and_design_are_distinct(self):
        self.assertNotEqual(template_path('0.1.0'),template_path('0.2.0'))
        old=build_contract(self.package,self.manifest,self.statuses,fixture.AEProductionTest.design)
        new=self.contract();self.assertNotEqual(old['render_id'],new['render_id'])
        self.assertEqual(old['package_sha'],new['package_sha']);self.assertEqual(old['final_copy_sha'],new['final_copy_sha'])

    def test_same_input_replays_without_teaching_changes(self):
        before=sha([self.package,self.manifest,self.statuses]);self.assertEqual(self.contract(),self.contract())
        self.assertEqual(before,sha([self.package,self.manifest,self.statuses]))

    def test_palette_is_semantic_and_contrast_checked(self):
        colors=self.design['colors'];self.assertEqual(colors['evidence'],'#7E96A8')
        self.assertEqual(colors['error_extra'],'#C97868');self.assertEqual(colors['valid'],'#91A58F')
        for name in ('primary_text','secondary_text'):self.assertGreaterEqual(contrast(colors[name],colors['background']),4.5)

    def test_neon_palette_and_bounce_cannot_bypass_brand(self):
        for change in ('palette','bounce'):
            d=deepcopy(self.design)
            if change=='palette':d['colors']['evidence']='#00FF00'
            else:d['motion']['overshoot']=10
            with self.assertRaises(ValueError):build_contract(self.package,self.manifest,self.statuses,d)

    def test_platform_changes_identity_not_claims(self):
        a=self.contract()
        for name in ('DOUYIN_VERTICAL','XHS_VERTICAL','BILIBILI_VERTICAL','WECHAT_CHANNELS_VERTICAL'):
            b=self.contract(platform_profile=name);self.assertNotEqual(a['render_id'],b['render_id'])
            self.assertEqual(a['scenes'],b['scenes']);self.assertEqual(a['upstream_bindings'],b['upstream_bindings'])
            self.assertIn('simulation',b['platform_profile']['status'])

    def test_platform_override_cannot_hide_unsafe_content(self):
        profile=resolve_profile();profile['safe_area_profile']['core']=[0,0,1080,1920]
        with self.assertRaises(ValueError):self.contract(platform_profile=profile)

    def test_critical_projection_outside_core_blocks(self):
        rc=self.contract();rc['scenes'][0]['components'][0]['layout']['x']=900
        with self.assertRaises(ValueError):projection_qa(rc)

    def test_literal_hook_and_screen_copy_remain_exact(self):
        rc=self.contract()
        for s in self.package['semantic_scenes']:
            if s['method_visual'] is None:
                comps=[c for rendered in rc['scenes'] if rendered['package_scene_id']==s['scene_id'] for c in rendered['components']]
                self.assertEqual(''.join(c['content']['text'] for c in comps),s['on_screen']['primary_text'])
        self.assertIn(rc['cover_candidate']['hook_text'],self.package['semantic_scenes'][0]['on_screen']['primary_text'])

    def test_cjk_phrases_and_punctuation_preserve_every_character(self):
        samples=['中文排版：原文其实没有支持这个判断。','A/B/C/D：R01、F01、G01；正确率 50%。',
                 '（中文括号）“原文依据”：谁 → 做什么 → 对谁。','中文 English mixed baseline 2025。',
                 '先判断——再比较；不要拆开 English words。']
        f=self.design['font']
        for text in samples:
            lines=wrap(text,360,44,f['measurement_file'],variation=f.get('variation'),cjk=True)
            self.assertEqual(''.join(lines),text)
            for line in lines:
                self.assertNotIn(line.strip()[0],LINE_START_FORBIDDEN);self.assertNotIn(line.rstrip()[-1],LINE_END_FORBIDDEN)

    def test_subtitle_phrase_boundary_not_character_split(self):
        f=self.design['font'];lines=wrap('原文其实没有支持这个判断',600,44,f['measurement_file'],max_units=7,variation=f.get('variation'),cjk=True)
        self.assertEqual(lines,['原文其实没有','支持这个判断'])

    def test_subtitles_are_exact_and_two_lines(self):
        text='原文依据：提示词是什么词性，不等于答案就是什么词性。R01 / F01 / G01。'
        cues=subtitle_cues(text,0,12,'synthetic',self.design)
        self.assertEqual(''.join(c['text'] for c in cues),text);self.assertTrue(all(len(c['lines'])<=2 for c in cues))

    def test_visual_profile_is_bound_and_required(self):
        rc=self.contract();del rc['platform_profile']
        with self.assertRaises(Exception):validate_contract(rc,self.package,self.manifest,self.statuses)

    def test_semantic_payload_still_matches_each_original_scene(self):
        rc=self.contract()
        for original in self.package['semantic_scenes']:
            for projected in (s for s in rc['scenes'] if s['package_scene_id']==original['scene_id']):
                self.assertEqual(projected['semantic_payload_sha'],sha(original));self.assertEqual(projected['typed_output'],original['method_visual'])

if __name__=='__main__':unittest.main()
