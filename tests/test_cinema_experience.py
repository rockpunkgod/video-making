"""Synthetic editorial provenance and complete-voice timing boundaries."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'ae/experiments/reading-d-dual-pass/cinema.py'
spec=importlib.util.spec_from_file_location('cinema',path)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class CinemaTests(unittest.TestCase):
    def test_native_event_is_mapped_through_inserted_reading_holds(self):
        mapping=[0,1,1,1,2,3,4]
        self.assertEqual(c.map_event(mapping,1,3),[1,5])
        with self.assertRaises(ValueError):c.map_event(mapping,9,10)

    def test_changed_source_invalidates_editorial_binding(self):
        source={'semantic_binding_sha':'synthetic','text':'SYNTHETIC ONLY'}
        ref=c.reference(source,'/text')
        source['text']='SYNTHETIC CHANGED'
        self.assertNotEqual(ref,c.reference(source,'/text'))

    def test_locator_cannot_claim_an_answer(self):
        source={'semantic_binding_sha':'synthetic','text':'SYNTHETIC ONLY'}
        script={'source_binding':'synthetic','clips':[dict(id='x',text='SYNTHETIC',source_refs=[c.reference(source,'/text')],authority='locating_trace',answer_claim=True,reading_task='synthetic',beat_id='x')]}
        review=dict(script_sha=c.sha(script),status='approved_for_internal_scratch',reviewer='synthetic AI',reviewer_kind='ai_host',human_review='PENDING',public_render_ready=False)
        with self.assertRaises(ValueError):c.validate_copy(script,source,review)

    def test_new_speech_extends_picture_without_changing_motion(self):
        mapping,rows,holds=c.fit_voice(list(range(24)),[dict(id='x',base_start_frame=0,base_end_frame=24,safe_hold_frame=12,settle_frames=12)],{'x':1.5},{12})
        self.assertEqual(len(mapping),48)
        self.assertEqual(rows[0]['end_frame'],36)
        self.assertFalse(rows[0]['speech_cut'])
        self.assertFalse(rows[0]['speech_tempo_changed'])
        self.assertEqual([v for i,v in enumerate(mapping) if i==0 or v!=mapping[i-1]],list(range(24)))
        self.assertEqual(holds[0]['source_frame'],12)

    def test_unverified_hold_is_refused(self):
        with self.assertRaises(ValueError):c.fit_voice(list(range(24)),[dict(id='x',base_start_frame=0,base_end_frame=24,safe_hold_frame=12)],{'x':2},set())

    def test_overlapping_voice_is_refused(self):
        placements=[dict(id='a',base_start_frame=0,base_end_frame=20,safe_hold_frame=4,settle_frames=0),dict(id='b',base_start_frame=10,base_end_frame=24,safe_hold_frame=14,settle_frames=0)]
        with self.assertRaises(ValueError):c.fit_voice(list(range(24)),placements,{'a':.8,'b':.5},{4,14})

    def test_invalid_measured_duration_is_refused(self):
        for duration in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):c.fit_voice(list(range(24)),[dict(id='a',base_start_frame=0,base_end_frame=24,safe_hold_frame=12)],{'a':duration},{12})

    def test_native_event_changes_invalidate_the_viewer_plan(self):
        source={'text':'SYNTHETIC ONLY'};events={'timing':[1,2]}
        beat=dict(beat_id='synthetic',**{'pass':'guided'},source_refs=[c.reference(source,'/text')],
            source_event_refs=[c.reference(events,'/timing')],viewer_state={'current_goal':'synthetic'},
            presentation={'reading_task':'synthetic'},learning={'boundary_preserved':True},
            what_guided_adds='synthetic verification',clocks={k:[0,24] for k in ('action','attention','comprehension')})
        c.validate_experience([beat],source,events)
        events['timing']=[2,3]
        with self.assertRaises(ValueError):c.validate_experience([beat],source,events)


if __name__=='__main__':unittest.main()
