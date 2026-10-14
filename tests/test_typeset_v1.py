"""Synthetic text only; layout never creates or upgrades teaching assets."""
from copy import deepcopy
from pathlib import Path
import re
import unittest

from creative_os.semantic_text_layout import layout_words, focus_windows, strip_hard_breaks
from creative_os.typeset import typeset


class TypesetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = next((p for p in (Path('C:/Windows/Fonts/georgia.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')) if p.exists()), None)
        if cls.font is None: raise unittest.SkipTest('Measurement font unavailable')
        cls.style = dict(type_scale=dict(focus_text=30, focus_line_height=42),
                         layout=dict(focus_width=420, focus_max_lines=9,
                                     focus_characters_per_line=[20, 65]))

    def test_display_normalization_preserves_paragraphs(self):
        self.assertEqual(strip_hard_breaks('alpha\r\nbeta\r\n \r\ngamma'), 'alpha beta\n\ngamma')

    def test_original_offsets_and_unicode_survive_flow(self):
        text='Alpha 🙂\r\nbeta of the river.\r\n\r\n中文 delta and another object.'
        words=layout_words(text,str(self.font),30,420,flow=True)
        self.assertEqual([text[w['start']:w['end']] for w in words],re.findall(r'\S+',text))
        self.assertEqual([w['paragraph'] for w in words], [0]*6+[1]*5)
        self.assertTrue(all(w['x']+w['w']<=420+1e-8 for w in words))
        raw=text.encode('utf-16-le')
        self.assertEqual([raw[w['utf16_start']*2:w['utf16_end']*2].decode('utf-16-le') for w in words],
                         re.findall(r'\S+',text))

    def test_legacy_hard_line_break_behavior_unchanged(self):
        text='alpha\nbeta'
        self.assertEqual([w['line'] for w in layout_words(text,str(self.font),30,420)],[0,1])
        self.assertEqual([w['line'] for w in layout_words(text,str(self.font),30,420,flow=True)],[0,0])

    def test_connectors_are_kept_when_feasible(self):
        words=layout_words('Look at the river and the bridge near the garden.',str(self.font),30,200,flow=True)
        ends=[w for i,w in enumerate(words[:-1]) if w['line']!=words[i+1]['line']]
        self.assertTrue(ends)
        self.assertFalse(any(w['text'] in ('at','the','and') for w in ends))

    def test_short_paragraph_is_reported_not_padded(self):
        plan=typeset('Small.',self.font,self.style)
        self.assertEqual(plan['lines'][0]['text'],'Small.')
        self.assertIn('SHORT_LINE',plan['lines'][0]['warnings'])

    def test_impossible_connector_chain_reports_without_losing_words(self):
        words=layout_words('the the the the',str(self.font),30,70,flow=True)
        self.assertEqual([w['text'] for w in words],['the']*4)
        self.assertTrue(any('KEEP_WITH_NEXT_UNSATISFIED' in w['layout_warnings'] for w in words))

    def test_windows_cover_every_token_once(self):
        words=layout_words(' '.join(['alpha beta gamma delta']*60),str(self.font),30,420,flow=True)
        windows=focus_windows(words,9)
        self.assertGreater(len(windows),1)
        self.assertTrue(all(w['line_count']<=9 for w in windows))
        self.assertEqual([s for w in windows for s in w['word_spans']],[[w['start'],w['end']] for w in words])

    def test_invalid_geometry_and_oversize_token(self):
        for width in (0,-1,float('nan'),5):
            with self.assertRaises(ValueError):layout_words('alpha',str(self.font),30,width,flow=True)
        for limit in (0,1.2,True):
            with self.assertRaises(ValueError):focus_windows([],limit)

    def test_replay_and_binding(self):
        text='The synthetic subject crosses a small bridge near the garden.'
        a=typeset(text,self.font,self.style)
        self.assertEqual(a,typeset(text,self.font,self.style))
        s=deepcopy(self.style);s['layout']['focus_width']=500
        b=typeset(text,self.font,s)
        self.assertEqual(a['source_sha256'],b['source_sha256'])
        self.assertNotEqual(a['style_sha256'],b['style_sha256'])
        self.assertNotEqual(a['source_sha256'],typeset(text+'!',self.font,s)['source_sha256'])

    def test_style_character_limit_is_applied_without_changing_tokens(self):
        style=deepcopy(self.style);style['layout']['focus_characters_per_line']=[10,24]
        text=' '.join(['alpha beta gamma delta']*4)
        plan=typeset(text,self.font,style)
        self.assertTrue(all(len(l['text'])<=24 for l in plan['lines']))
        self.assertEqual([w['text'] for w in plan['words']],text.split())

    def test_cjk_fallback_uses_explicit_font_and_requires_it_for_partial_binding(self):
        from creative_os.semantic_text_layout import bind_words
        words=layout_words('中文 text',str(self.font),30,420,flow=True,fallback_font_path=self.font)
        self.assertEqual(words[0]['font_role'],'fallback')
        with self.assertRaisesRegex(ValueError,'fallback token'):
            bind_words(words,[dict(span_id='part',start=0,end=1)],str(self.font))
        parts=bind_words(words,[dict(span_id='part',start=0,end=1)],str(self.font),self.font)
        self.assertEqual(''.join(w['text'] for w in parts),'中文text')

    def test_empty_and_paragraph_boundaries(self):
        self.assertEqual(typeset('',self.font,self.style)['focus_windows'],[])
        plan=typeset('one\n\ntwo',self.font,self.style)
        self.assertEqual(len(plan['lines']),2)


if __name__=='__main__':unittest.main()

