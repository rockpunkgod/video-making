"""Synthetic presentation checks; no exam content or teaching certification."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from creative_os.passage_director import direct, validate_direction
from ae_production.passage_execution import reuse_unchanged_heads
from creative_os.hero import file_sha
from video_contracts import sha,write
from pathlib import Path
import tempfile


class Font:
    def getlength(self, text): return len(text)*20


def inputs():
    scene=dict(segment_id='synthetic', segment_sha='frozen', kind='comparison',
               heading='Synthetic passage', stem='Which example?', source='alpha beta',
               screen='合成比较', annotations=[{'quote':'alpha'}],
               options=[dict(letter='A',text='A alpha',state='retain'),
                        dict(letter='B',text='B beta',state='eliminate')])
    plan=dict(plan_sha='synthetic-plan',fonts=dict(chinese='synthetic',english='synthetic'),scenes=[scene])
    bundle={'payload':{'review':{'segments':[dict(segment_id='synthetic',
                    evidence=[dict(field='passage',quote='alpha beta')])]}}}
    return plan,bundle


@patch('PIL.ImageFont.truetype',return_value=Font())
class DirectorTests(TestCase):
    def test_chinese_heading_does_not_leave_one_glyph_on_a_line(self, font):
        class SizedFont:
            def __init__(self,size): self.size=size
            def getlength(self,text): return len(text)*self.size
        font.side_effect=lambda path,size:SizedFont(size)
        plan,bundle=inputs();plan['scenes'][0].update(kind='boundary',screen='甲乙丙丁戊己庚辛壬癸\n合成限定')
        d=direct(plan,bundle,{'synthetic':'boundary'})
        node=next(n for n in d['scenes']['synthetic']['nodes'] if n['name']=='JUDGMENT')
        self.assertEqual(node['size'],63)
        self.assertEqual(node['text'],plan['scenes'][0]['screen'])

    def test_reworded_claim_or_changed_native_geometry_requires_new_direction(self, font):
        plan,bundle=inputs();d=direct(plan,bundle,{'synthetic':'comparison'})
        validate_direction(d,plan,bundle)
        changed=deepcopy(d)
        next(n for n in changed['scenes']['synthetic']['nodes'] if n['name']=='SOURCE')['text']='unbound conclusion'
        with self.assertRaises(ValueError):validate_direction(changed,plan,bundle)
        changed=deepcopy(d)
        next(n for n in changed['scenes']['synthetic']['nodes'] if n['name']=='QUESTION')['y']=300
        with self.assertRaises(ValueError):validate_direction(changed,plan,bundle)

    def test_overview_cannot_be_promoted_to_verdict_or_cross_question_summary(self, font):
        plan,bundle=inputs()
        for mode in ('verdict','recap','boundary'):
            with self.assertRaises(ValueError):direct(plan,bundle,{'synthetic':mode})

    def test_native_events_leave_question_fixed_and_captions_readable(self, font):
        plan,bundle=inputs();d=direct(plan,bundle,{'synthetic':'comparison'})
        nodes=d['scenes']['synthetic']['nodes'];q=next(n for n in nodes if n['name']=='QUESTION')
        self.assertIsNone(q['event']);self.assertEqual(q['travel'],0);self.assertEqual(q['zoom'],1)
        self.assertEqual(nodes[-1]['name'],'CAPTION_PAPER')
        self.assertTrue(all(n['y']+n['h']<=934 for n in nodes if n['type']=='text'))
        self.assertFalse(d['public_render_ready']);self.assertFalse(d['semantic_certification'])
        phrase=next(n for n in nodes if n['name']=='FOCUS_0')
        self.assertEqual(phrase['from_source'],'SOURCE')
        self.assertEqual(phrase['from_position'],[110,275])
        self.assertLess(phrase['from_scale'],1)


class NativeReuseTests(TestCase):
    def test_only_exact_scene_template_and_media_can_be_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);media=root/'synthetic-media';media.write_bytes(b'synthetic-only')
            scenes=[{'segment_id':'a'},{'segment_id':'b'}]
            old={'scenes':scenes,'motion_orders':{},'direction':{'direction_sha':'old','scenes':{'a':{'text':'alpha'},'b':{'text':'beta'}}}}
            new=deepcopy(old);new['direction'].update(direction_sha='new',scenes={'a':{'text':'alpha'},'b':{'text':'beta revised'}})
            for request in (old,new):
                request['presentation_sha']=sha({'template':'synthetic-template','direction':request['direction']['direction_sha'],'orders':{}})
            write(root/'old/a/receipt.json',dict(scene_sha=sha(scenes[0]),presentation_sha=old['presentation_sha'],direction_sha='old',
                  static_hold_verified=True,video=str(media),video_sha=file_sha(media),hold_frame=str(media),hold_sha=file_sha(media)))
            self.assertEqual(reuse_unchanged_heads(old,new,root/'old',root/'new','synthetic-template'),['a'])
            self.assertFalse((root/'new/b').exists())
            with self.assertRaises(ValueError):reuse_unchanged_heads(old,new,root/'old',root/'bad-template','changed')
            media.write_bytes(b'mutated')
            with self.assertRaises(ValueError):reuse_unchanged_heads(old,new,root/'old',root/'bad-media','synthetic-template')
