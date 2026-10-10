from copy import deepcopy
import unittest
from creative_os.content_profiles import editorial_handoffs, STAGES


class ContentProfilesTest(unittest.TestCase):
    def test_product_context_preserves_frozen_inputs_and_marks_unproduced(self):
        frozen = {'transcript': 'SYNTHETIC ONLY', 'teaching_sha': 'unchanged'}
        before = deepcopy(frozen)
        artifacts = {s: None for s in STAGES}; artifacts['copy'] = frozen
        context = editorial_handoffs('FREE_SHOWCASE', artifacts)
        self.assertEqual(frozen, before)
        self.assertFalse(context['public_render_ready'])
        self.assertEqual(context['quality_review'], 'PENDING')
        self.assertEqual(context['handoffs'][-1]['state'], 'NOT_PRODUCED')
        self.assertTrue(all(h['content_profile'] == 'FREE_SHOWCASE' for h in context['handoffs']))
        self.assertEqual(context, editorial_handoffs('FREE_SHOWCASE', artifacts))

    def test_paid_and_free_have_separate_rubrics_and_bindings(self):
        artifacts = {s: None for s in STAGES}
        free = editorial_handoffs('FREE_SHOWCASE', artifacts)
        paid = editorial_handoffs('PAID_MASTERY', artifacts)
        self.assertNotEqual(free['quality_rubric'], paid['quality_rubric'])
        self.assertNotEqual(free['context_sha'], paid['context_sha'])
        self.assertEqual(free['hard_gates'], paid['hard_gates'])
        self.assertNotIn('Truth', free['quality_rubric'])

    def test_missing_stage_or_unknown_profile_rejected(self):
        with self.assertRaises(ValueError): editorial_handoffs('FREE_SHOWCASE', {})
        with self.assertRaises(ValueError): editorial_handoffs('UNKNOWN', {s: None for s in STAGES})
