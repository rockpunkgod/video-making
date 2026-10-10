"""Synthetic policy controls, never human approval or real teaching evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from content_os.showcase import CHECKS, bindings, decide, file_sha, review_template
from content_os.release import publication_check
from tests import test_video_os as fixtures
from video_contracts import sha, seal


class FreeShowcaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VideoOSTest.setUpClass()

    def setUp(self):
        control = fixtures.VideoOSTest(); control.setUp()
        self.package, self.statuses = control.package()
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.media = Path(self.tmp.name) / 'synthetic.bin'
        self.media.write_bytes(b'SYNTHETIC TEST ONLY: not an encoded video')
        asset = {'path': str(self.media), 'sha256': file_sha(self.media)}
        self.request = {'schema_version': '1.0.0', 'policy': 'free_showcase_v1', 'content_profile': 'FREE_SHOWCASE',
            'package': self.package,
            'scope': {'content_scope': 'method_action_demo', 'result': 'locate',
                'claim_validity': 'PASS', 'claim_ids': [c['claim_id'] for c in self.package['claims']],
                'required_qualifiers': ['SYNTHETIC scope only']},
            'final_copy': {'hook': 'Synthetic hook', 'voiceover': [], 'subtitles': [], 'visual_text': [], 'memory': ''},
            'source_display': {'excerpt_ids': [], 'displayed_text_sha': sha('synthetic'),
                'displayed_image_sha': sha([]), 'attribution_text': 'SYNTHETIC', 'materials': [asset],
                'rights': {k: 'approved' for k in ('question', 'images', 'music', 'voice')}},
            'media': {'path': str(self.media), 'sha256': file_sha(self.media), 'picture_sha': sha('synthetic'),
                'audio_assets': [asset], 'production_receipt_sha': sha('synthetic')}, 'reviews': {}}
        self.probe = patch('content_os.showcase.inspect_media', return_value={'status': 'PASS', 'synthetic': True})
        self.probe.start(); self.addCleanup(self.probe.stop)

    def approve(self):
        for kind in CHECKS:
            review = review_template(self.request, self.statuses, kind)
            review.update(review_id='synthetic-' + kind, reviewer='SYNTHETIC external human',
                reviewed_at='2026-10-10T10:00:00+08:00', status='pass', evidence_notes='Synthetic control only')
            review['checks'] = {k: 'pass' for k in CHECKS[kind]}
            self.request['reviews'][kind] = review

    def test_no_transfer_or_first_use_required(self):
        self.approve()
        decision = decide(self.request, self.statuses)
        self.assertEqual(decision['state'], 'APPROVED_FOR_PUBLIC_EXPORT')
        self.assertEqual(decision['method_generalizability'], 'NOT_ASSESSED')

    def test_paid_cannot_use_free_publication_review(self):
        self.approve()
        self.request['content_profile'] = 'PAID_MASTERY'
        with self.assertRaises(ValueError):
            decide(self.request, self.statuses)

    def test_internal_media_ready_for_human_review(self):
        self.assertEqual(decide(self.request, self.statuses)['state'], 'READY_FOR_HUMAN_REVIEW')
        self.assertFalse(decide(self.request, self.statuses)['public_render_ready'])

    def test_false_claim_and_helper_answer_blocked(self):
        for key, value in (('claim_validity', 'FAIL'), ('result', 'answer')):
            with self.subTest(key=key):
                request = deepcopy(self.request); request['scope'][key] = value
                self.assertEqual(decide(request, self.statuses)['state'], 'BLOCKED')

    def test_unknown_question_and_audio_rights_hold(self):
        for key in ('question', 'music', 'voice'):
            with self.subTest(key=key):
                self.approve(); self.request['source_display']['rights'][key] = 'unknown'
                self.assertFalse(decide(self.request, self.statuses)['public_render_ready'])
                self.request['source_display']['rights'][key] = 'approved'

    def test_copy_picture_attribution_changes_expire_reviews(self):
        self.approve()
        for area, key in (('final_copy', 'hook'), ('media', 'picture_sha'), ('source_display', 'attribution_text')):
            request = deepcopy(self.request); request[area][key] = sha('changed') if key.endswith('sha') else 'Changed'
            with self.subTest(key=key):
                self.assertFalse(decide(request, self.statuses)['public_render_ready'])
                self.assertEqual(decide(request, self.statuses)['checks']['editorial']['reason'], 'approval_invalidated_by_input_change')

    def test_ai_cannot_sign_human_release(self):
        self.approve()
        self.request['reviews']['editorial'].update(reviewer_kind='AI', origin='agent_authored')
        self.assertFalse(decide(self.request, self.statuses)['public_render_ready'])

    def test_missing_status_and_actual_media_hold(self):
        self.approve()
        self.assertFalse(decide(self.request, {})['public_render_ready'])
        self.request['media'].update(path='', sha256=None)
        self.assertEqual(decide(self.request, self.statuses)['state'], 'INTERNAL_ONLY')

    def test_media_audio_source_bytes_change_blocked(self):
        self.approve(); self.media.write_bytes(b'changed')
        self.assertEqual(decide(self.request, self.statuses)['state'], 'BLOCKED')

    def test_source_denial_blocks(self):
        self.request['source_display']['rights']['question'] = 'denied'
        self.assertEqual(decide(self.request, self.statuses)['state'], 'BLOCKED')

    def test_required_stop_cannot_be_removed(self):
        self.request['scope']['claim_ids'] = [c['claim_id'] for c in self.package['claims'] if c['kind'] != 'stop_rule']
        self.assertEqual(decide(self.request, self.statuses)['state'], 'BLOCKED')

    def test_legacy_gate_unchanged_and_inputs_immutable(self):
        before = sha(self.request); frozen = sha(self.package)
        self.approve(); approved_input = sha(self.request)
        self.assertTrue(decide(self.request, self.statuses)['public_render_ready'])
        self.assertEqual(sha(self.request), approved_input)
        self.assertEqual(sha(self.package), frozen)
        self.assertFalse(publication_check(self.package, self.statuses)['render_ready_for_publication'])
        self.assertNotEqual(before, approved_input)

    def test_unbound_claim_and_withdrawal_blocked(self):
        self.request['scope']['claim_ids'].append('invented')
        self.assertEqual(decide(self.request, self.statuses)['state'], 'BLOCKED')

    def test_withdrawal_is_hard_but_rights_change_is_source_hold(self):
        asset_id = next(iter(self.statuses))
        rights = deepcopy(self.statuses)
        rights[asset_id]['source_sha'] = sha('changed rights')
        rights[asset_id] = seal(rights[asset_id])
        result = decide(self.request, rights)
        self.assertNotEqual(result['state'], 'BLOCKED')
        self.assertEqual(result['checks']['source_display']['status'], 'HOLD')
        withdrawn = deepcopy(self.statuses)
        withdrawn[asset_id]['effective_status'] = 'WITHDRAWN'
        withdrawn[asset_id] = seal(withdrawn[asset_id])
        self.assertEqual(decide(self.request, withdrawn)['state'], 'BLOCKED')

    def test_rejected_human_claim_blocks(self):
        self.approve(); self.request['reviews']['teaching_claim']['status'] = 'fail'
        self.assertEqual(decide(self.request, self.statuses)['state'], 'BLOCKED')

    def test_group_and_locator_cannot_claim_reduction(self):
        self.request['scope']['result'] = 'reduce'
        self.assertIn('result_not_supported_by_selected_action_output', decide(self.request, self.statuses)['blockers'])

    def test_free_approval_cannot_promote_method_research(self):
        from core.registry import Registry
        from core.release import check_release, read_json
        registry = Registry(); before = sha(registry.methods)
        self.approve(); decide(self.request, self.statuses)
        result = check_release(registry, read_json('evaluation/release-review.example.json'))
        self.assertFalse(result['ready_for_manual_release'])
        self.assertIn('real_evaluation_release_gate', result['blocking_reasons'])
        self.assertEqual(sha(registry.methods), before)

    def test_template_never_approves(self):
        for kind in CHECKS:
            self.request['reviews'][kind] = review_template(self.request, self.statuses, kind)
        self.assertFalse(decide(self.request, self.statuses)['public_render_ready'])

    def test_status_timestamp_does_not_expire_approval(self):
        self.approve()
        for asset_id, status in self.statuses.items():
            status['generated_at'] = '2026-10-10T12:00:00+08:00'
            self.statuses[asset_id] = seal(status)
        self.assertTrue(decide(self.request, self.statuses)['public_render_ready'])

    def test_episode_arrangement_receipt_change_expires_approval(self):
        self.approve()
        self.request['media']['production_receipt_sha'] = sha('different arrangement')
        self.assertFalse(decide(self.request, self.statuses)['public_render_ready'])
