"""Synthetic information-handoff/provenance checks, not semantic certification."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'ae/experiments/reading-d-dual-pass'
previous=sys.path[:];sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('reading_continuity',HERE/'continuity.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);sys.path[:]=previous


class ContinuityTests(unittest.TestCase):
    def bridge(self):
        return dict(id='synthetic',parent_frame=3,frames=24,source_frame=0,reason='return to options',carry_after_frames=2)

    def test_inserted_bridge_keeps_all_parent_frames_in_order(self):
        rows,windows=c.splice([0,1,2,3,4], [self.bridge()])
        self.assertEqual([r['parent_frame'] for r in rows if 'parent_frame' in r],list(range(5)))
        self.assertEqual(windows['synthetic'],[3,27])
        self.assertEqual(sum('blend_frame' in r for r in rows),12)

    def test_memory_cannot_first_appear_after_return_to_question(self):
        recipe={'bridges':[self.bridge()]};windows={'synthetic':[3,27]}
        row=dict(style='Memory',start_frame=3,end_frame=29,authority='existing_review_projection')
        with self.assertRaises(ValueError):c.validate_memory_carry(recipe,[row],windows)
        row['start_frame']=2;c.validate_memory_carry(recipe,[row],windows)
        row['end_frame']=27
        with self.assertRaises(ValueError):c.validate_memory_carry(recipe,[row],windows)

    def test_invented_memory_is_not_accepted_as_evidence(self):
        row=dict(style='Memory',start_frame=1,end_frame=29,authority='editorial_navigation')
        with self.assertRaises(ValueError):c.validate_memory_carry({'bridges':[self.bridge()]},[row],{'synthetic':[3,27]})

    def test_bound_action_output_cannot_drop_qualifier(self):
        source={'action':{'output':'Synthetic requires enough material.'}}
        item=dict(document='projection',pointer='/action/output',text='Synthetic requires enough material.')
        self.assertEqual(c.literal(item,source,{})['span'],[0,35])
        item['text']='Synthetic requires material.'
        with self.assertRaises(ValueError):c.literal(item,source,{})

    def test_navigation_cannot_be_used_to_insert_answer_claim(self):
        with self.assertRaises(ValueError):c.literal({'navigation':True,'text':'The answer is A.'},{},{})

    def test_cross_segment_context_requires_explicit_target(self):
        bundle={'text':'Next, synthetic question. It asks about conditions.'}
        item=dict(document='bundle',pointer='/text',text='It asks about conditions.',task_context=True,context_target='synthetic question')
        self.assertEqual(c.literal(item,{},bundle)['authority'],'existing_review_projection')
        item['context_target']='different question'
        with self.assertRaises(ValueError):c.literal(item,{},bundle)

    def test_start_and_end_boundaries_do_not_bleed_into_bridge(self):
        b=[self.bridge()]
        self.assertEqual(c.boundary(3,b,end=True),3)
        self.assertEqual(c.boundary(3,b),27)


if __name__=='__main__':unittest.main()
