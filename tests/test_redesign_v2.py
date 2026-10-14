"""Synthetic checks only; no learner, teaching or voice approval."""
from copy import deepcopy
import unittest

from creative_os.role_evaluation import evaluate, summarize
from pedagogy.sources import FrozenSource
from student_pov.speech import narration_coverage, speech_lint
from tests import test_redesign_content as fixtures


class RedesignV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RedesignContentTest.setUpClass()
        cls.bundle = fixtures.RedesignContentTest.bundle
        cls.status = fixtures.RedesignContentTest.status

    def test_locator_measures_actual_output_not_its_broader_citation(self):
        downstream = FrozenSource(self.bundle, self.status, {'method_id':'R01',
                                                            'action_ids':['choice-A','choice-B']})
        ref = downstream.ref(downstream.evidence_paths[0])
        row = evaluate(self.bundle, self.status, {'method_id':'R12','action_ids':['loc']},
                       {'required_evidence_refs':[ref]})
        self.assertFalse(row['success'])  # output alpha does not cover alpha beta gamma
        self.assertEqual(row['metrics']['coverage'], 0)
        self.assertFalse(summarize([row])['public_render_ready'])

    def test_decider_requires_complete_selected_actions(self):
        selected = {'method_id':'R01', 'action_ids':['choice-A','choice-B']}
        full = evaluate(self.bundle, self.status, selected, {})
        self.assertTrue(full['success'])
        partial = evaluate(self.bundle, self.status, {**selected,'action_ids':['choice-A']}, {})
        self.assertFalse(partial['success'])
        self.assertEqual(summarize([full])['methods'][0]['status'], 'HOLD_SAMPLE_UNDER_TEN')
        with self.assertRaises(ValueError): summarize([full, full])
        with self.assertRaises(ValueError): evaluate(self.bundle, None, selected, {})

    def test_verifier_without_independent_injected_error_stays_unknown(self):
        row = evaluate(self.bundle, self.status, {'method_id':'R17','action_ids':['verify-A']}, {})
        self.assertIsNone(row['success'])
        self.assertEqual(summarize([row])['methods'][0]['status'], 'HOLD_MISSING_OBSERVATIONS')

    def exemption(self):
        return {'start':5, 'end':14, 'kind':'reading', 'reason':'Read the displayed passage',
                'reviewer':'SYNTHETIC TEST'}

    def test_reading_pause_preserved_without_padding_and_warns_over_twenty_percent(self):
        row = narration_coverage([[0,5],[14,20]],20,exemptions=[self.exemption()])
        self.assertEqual(row['coverage'], .55)
        self.assertEqual(row['adjusted_coverage'], 1)
        self.assertIn('EXEMPTIONS_OVER_20_PERCENT_REVIEW_EPISODE', row['warnings'])
        self.assertNotIn('SILENCE_OVER_6_SECONDS', row['warnings'])
        self.assertFalse(row['actual_delivery_pass'])
        self.assertFalse(row['natural_speech_certified'])

    def test_exemptions_cannot_cover_voice_overlap_or_lack_reason(self):
        for edits in ({'start':4}, {'reason':''}, {'end':21}):
            with self.assertRaises(ValueError):
                narration_coverage([[0,5],[14,20]],20,exemptions=[{**self.exemption(),**edits}])
        with self.assertRaises(ValueError):
            narration_coverage([[0,5],[14,20]],20,exemptions=[self.exemption(),self.exemption()])

    def test_speech_lint_ignores_english_and_only_flags_style(self):
        self.assertEqual(speech_lint('ABCDEFGHIJKLMNOPQRSTUVWXYZ')['warnings'], [])
        row = speech_lint('同学们，我当年也这样。甲、乙、丙、丁。')
        self.assertEqual({r['code'] for r in row['warnings']},
                         {'PEER_VOICE_WORDING_REVIEW','BIOGRAPHY_CLAIM_REVIEW','ENUMERATION_OVER_TWO'})
        self.assertFalse(row['natural_speech_certified'])


if __name__ == '__main__': unittest.main()
