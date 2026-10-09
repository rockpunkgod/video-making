"""Synthetic timing counterexamples; no actual English or teaching labels."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'ae/experiments/method-relay-dual-pass'
spec = importlib.util.spec_from_file_location('recognition_timing', HERE / 'recognition_timing.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class RecognitionTimingTests(unittest.TestCase):
    def test_fast_transfer_slow_recognition_and_no_overlap(self):
        p = timing.schedule(['span-1', 'span-2', 'span-3'], 'span-3', [252, 354])
        cursor = p['unallocated_window'][1]
        for index,event in enumerate(p['events']):
            for stage in ('transfer', 'activation', 'recognition'):
                start, end = event[stage]
                self.assertEqual(start, cursor)
                self.assertGreater(end, start)
                cursor = end
            if index<len(p['events'])-1:
                next_event=p['events'][index+1]
                self.assertEqual(event['retirement'][0],next_event['transfer'][0])
                self.assertLessEqual(event['retirement'][1],next_event['activation'][0])
            self.assertLess(event['transfer'][1] - event['transfer'][0],
                            event['recognition'][1] - event['recognition'][0])
        self.assertEqual(cursor,354)
        self.assertNotIn('retirement', p['events'][-1])
        self.assertEqual(p['unallocated_window'], [252, 306])
        self.assertTrue(p['requires_director_timing_alignment'])
        self.assertNotIn('acquired_hold', p['events'][-1])
        self.assertIsNone(p['candidate_verdict'])
        self.assertFalse(p['render_ready'])
        self.assertFalse(p['public_render_ready'])

    def test_overflow_reports_retiming_never_drops_candidates(self):
        ids = [f'span-{i}' for i in range(7)]
        with self.assertRaises(timing.RecognitionTimingOverflow) as result:
            timing.schedule(ids, ids[-1], [252, 354])
        self.assertEqual((result.exception.required_frames,
                          result.exception.available_frames,
                          result.exception.additional_frames), (112, 102, 10))
        self.assertEqual(len(ids), 7)

    def test_no_implicit_candidate_selection_or_reordering(self):
        for ids, acquired in (([], 'missing'), (['a', 'a'], 'a'), (['a', 'b'], 'a'),
                              (['a', 'b'], 'unknown'), ([''], '')):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                timing.schedule(ids, acquired, [0, 100])

    def test_invalid_frames_and_compressed_recognition_are_rejected(self):
        for frames in ((0, 0), (-1, 100), (False, 100), (0, 100.5)):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                timing.schedule(['a'], 'a', frames)
        for policy in ({**timing.DEFAULT, 'recognition': 1},
                       {**timing.DEFAULT, 'transfer': True},
                       {**timing.DEFAULT, 'extra_zoom': 2}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                timing.schedule(['a'], 'a', [0, 100], policy)

    def test_strings_cannot_be_misread_as_an_ordered_candidate_list(self):
        for ids, frames in (('abc', [0, 100]), (['a'], '00'), (None, [0, 100])):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                timing.schedule(ids, 'a', frames)

    def test_expression_rhythm_is_explicit_and_can_vary(self):
        policies={'a': timing.DEFAULT, 'b': {**timing.DEFAULT, 'transfer':8, 'recognition':9}}
        p=timing.schedule(['a','b'],'b',[0,100],event_policies=policies)
        self.assertEqual(p['candidate_rhythm_source'],'editor_supplied_per_expression')
        self.assertEqual(p['events'][0]['transfer'],[62,66])
        self.assertEqual(p['events'][1]['transfer'],[78,86])
        self.assertEqual(p['events'][1]['recognition'],[91,100])
        self.assertFalse(p['render_ready'])
        for bad in ({'a':timing.DEFAULT}, {**policies,'unbound':timing.DEFAULT}):
            with self.assertRaises(ValueError):
                timing.schedule(['a','b'],'b',[0,100],event_policies=bad)
        other={**policies,'b':timing.DEFAULT}
        self.assertNotEqual(p['plan_sha'],timing.schedule(['a','b'],'b',[0,100],event_policies=other)['plan_sha'])

    def test_replay_and_frame_window_are_bound(self):
        a = timing.schedule(['a', 'b'], 'b', [100, 200])
        self.assertEqual(a, timing.schedule(['a', 'b'], 'b', [100, 200]))
        self.assertNotEqual(a['plan_sha'], timing.schedule(['a', 'b'], 'b', [101, 201])['plan_sha'])

    def test_unresolved_retires_last_without_implicit_acquisition(self):
        p=timing.schedule(['a','b'],None,[0,35])
        self.assertEqual(p['required_frames'],35)
        self.assertEqual(p['events'][-1]['retirement'],[32,35])
        self.assertEqual(p['outcome'],'unresolved')
        self.assertIsNone(p['acquired_id'])
        with self.assertRaises(timing.RecognitionTimingOverflow):
            timing.schedule(['a','b'],None,[0,34])

    def test_empty_search_has_no_fake_event(self):
        p=timing.schedule([],None,[0,40])
        self.assertEqual(p['events'],[])
        self.assertEqual(p['outcome'],'unresolved')


if __name__ == '__main__':
    unittest.main()
