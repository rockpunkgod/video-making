from copy import deepcopy
import unittest
from tests import test_video_os as fixtures
from video_contracts import sha, seal
from content_os.candidates import make_candidate
from content_os.director import build_draft, finalize_copy
from content_os.polisher import IdentityPolisher, polish
from creative_os.episode import STAGES, validate_episode


class MethodEpisodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VideoOSTest.setUpClass()

    def setUp(self):
        control = fixtures.VideoOSTest(); control.setUp()
        first, self.statuses = control.package()
        control.req['question']['question_id'] = 'synthetic-variation'
        control.req['question']['stem'] += ' different synthetic task'
        control.req['analysis'] = control.engine.analyze(control.req['question'])
        review = control.req['reviews'][0]
        review.update(question_id='synthetic-variation', input_sha256=sha(control.req['question']),
                      analysis_sha256=sha(control.req['analysis']))
        bundle, statuses = control.assets(); self.statuses.update(statuses)
        selection = {'asset_id': bundle['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']}
        candidate = make_candidate([bundle], [selection], statuses)
        second = finalize_copy(polish(build_draft(candidate, statuses), IdentityPolisher()))
        self.plan = {'schema_version': '1.0.0', 'kind': 'method_centered_episode',
            'method': {'method_id': 'R12', 'version': '1.1.0', 'theme': 'SYNTHETIC ONLY', 'signature_motion': 'synthetic'},
            'viewer_question': 'Synthetic task', 'questions': [], 'method_recall': 'Synthetic memory',
            'duration_policy': 'reading_narration_and_action_determine_duration', 'public_render_ready': False}
        for index, package in enumerate((first, second)):
            b = package['source_items'][0]
            ref = {'asset_id': b['asset_id'], 'pointer': '/source_snapshot/stem', 'sha': sha(b['source_snapshot']['stem'])}
            action = b['analysis']['execution_trace'][0]
            self.plan['questions'].append({'question_id': b['source_snapshot']['question_id'],
                'editorial_role': 'establish' if index == 0 else 'variation', 'package': package,
                'narrative_beats': [{'beat_id': str(i), 'function': stage, 'viewer_sees': 'synthetic',
                    'action': 'synthetic', 'source_refs': [ref]} for i, stage in enumerate(STAGES) if stage != 'helper'],
                'payoff': {'result_scope': 'locate', 'action_refs': [{'asset_id': b['asset_id'],
                    'pointer': '/analysis/execution_trace/0', 'sha': sha(action)}],
                    'output_shas': [sha(action['output'])], 'allowed_claim': 'synthetic located span only'}, 'helper_methods': []})

    def test_two_independent_questions_no_public_self_approval(self):
        result = validate_episode(self.plan, self.statuses)
        self.assertEqual(result['engineering_status'], 'PASS')
        self.assertFalse(result['public_render_ready'])

    def test_same_question_cannot_be_second_case(self):
        self.plan['questions'][1] = deepcopy(self.plan['questions'][0])
        self.plan['questions'][1]['editorial_role'] = 'variation'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_episode(self.plan, self.statuses)

    def test_evidence_cannot_cross_questions(self):
        self.plan['questions'][1]['narrative_beats'][0]['source_refs'] = self.plan['questions'][0]['narrative_beats'][0]['source_refs']
        with self.assertRaises((KeyError, ValueError)):
            validate_episode(self.plan, self.statuses)

    def test_helper_cannot_become_answer(self):
        self.plan['questions'][1]['payoff']['result_scope'] = 'answer'
        with self.assertRaisesRegex(ValueError, 'Helper'):
            validate_episode(self.plan, self.statuses)

    def test_withdrawal_invalidates_segment_and_episode(self):
        asset = self.plan['questions'][1]['package']['source_items'][0]['asset_id']
        self.statuses[asset]['effective_status'] = 'WITHDRAWN'
        self.statuses[asset] = seal(self.statuses[asset])
        result = validate_episode(self.plan, self.statuses)
        self.assertEqual(result['engineering_status'], 'BLOCKED')
        self.assertEqual(result['questions'][0]['state'], 'VALID_INTERNAL')
        self.assertTrue(result['questions'][1]['teaching_stale'])

    def test_each_question_requires_own_complete_narrative(self):
        self.plan['questions'][1]['narrative_beats'].pop()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            validate_episode(self.plan, self.statuses)
