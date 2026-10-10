"""Synthetic hold/caption provenance tests; no exam content."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'ae/experiments/reading-d-dual-pass/reading_pacing.py'
spec=importlib.util.spec_from_file_location('reading_pacing',path)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ReadingPacingTests(unittest.TestCase):
    def test_native_order_and_motion_are_never_dropped_or_interpolated(self):
        mapping=p.frame_map(6,[dict(frame=2,extra_frames=3,reason='read evidence')])
        self.assertEqual(mapping,[0,1,2,2,2,2,3,4,5])
        self.assertEqual([v for i,v in enumerate(mapping) if i==0 or v!=mapping[i-1]],list(range(6)))

    def test_invalid_hold_is_rejected(self):
        for frame,extra in [(-1,2),(6,2),(2,0),(2,1.5),(True,2)]:
            with self.assertRaises(ValueError):
                p.frame_map(6,[dict(frame=frame,extra_frames=extra,reason='read')])
        h=dict(frame=2,extra_frames=2,reason='read')
        with self.assertRaises(ValueError):p.frame_map(6,[h,h])

    def test_caption_is_literal_and_retains_evidence_binding(self):
        source={'segments':[dict(segment_id='s',text='Synthetic only. No decision.',screen_text='Synthetic',
                                 evidence=[{'artifact':'synthetic-evidence'}])]}
        row=dict(segment_ref='s',source_field='text',text='No decision.',base_start_frame=2,base_end_frame=4)
        mapping=p.frame_map(6,[dict(frame=3,extra_frames=3,reason='read')])
        result=p.caption_projection([row],source,mapping)[0]
        self.assertEqual((result['start_frame'],result['end_frame']),(2,7))
        self.assertEqual(result['evidence_refs'],source['segments'][0]['evidence'])
        row['text']='The answer is certain.'
        with self.assertRaises(ValueError):p.caption_projection([row],source,mapping)

    def test_copy_change_invalidates_literal_projection(self):
        source={'segments':[dict(segment_id='s',text='Known text',screen_text='') ]}
        row=dict(segment_ref='s',source_field='text',text='Known text',base_start_frame=0,base_end_frame=1)
        before=p.caption_projection([row],source,[0])[0]['source_field_sha']
        source['segments'][0]['text']='Known text plus change'
        after=p.caption_projection([row],source,[0])[0]['source_field_sha']
        self.assertNotEqual(before,after)

    def test_wrapping_changes_only_layout(self):
        text='Synthetic exact text, retained without lexical edits. '*2
        self.assertEqual(p.wrap(text).replace('\n',''),text)

    def test_overlap_cannot_hide_another_caption(self):
        source={'segments':[dict(segment_id='s',text='Synthetic',screen_text='')]}
        row=dict(segment_ref='s',source_field='text',text='Synthetic',base_start_frame=0,base_end_frame=2)
        with self.assertRaises(ValueError):p.caption_projection([row,row],source,[0,1,2])


if __name__=='__main__':unittest.main()
