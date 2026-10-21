"""Synthetic byte-binding controls; no real cover or release approval."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from content_os import bilibili_packaging as packaging


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


class BilibiliPackagingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.author = self.root / 'AV_AUTHOR.json'
        self.plan = self.root / 'AV_PLAN.json'
        self.bundle = self.root / 'synthetic-frozen.json'
        self.status = self.root / 'synthetic-status.json'
        self.bundle.write_text('SYNTHETIC SOURCE ONLY', encoding='utf-8')
        self.status.write_text('SYNTHETIC STATUS ONLY', encoding='utf-8')
        author = {'revision': 'synthetic-cut',
            'sources': {'camp': {'bundle': str(self.bundle), 'status': str(self.status)}},
            'input_files': {str(p): packaging.file_sha(p) for p in (self.bundle, self.status)}}
        write_json(self.author, author)
        plan = {'revision': 'synthetic-cut', 'frames': 240,
                'author_sha256': packaging.file_sha(self.author),
                'source_attribution': {'camp': {'source_path': str(self.bundle),
                    'source_sha256': packaging.file_sha(self.bundle), 'paper_display': 'SYNTHETIC PAPER',
                    'article_display': 'SYNTHETIC ARTICLE', 'reading_section': 'A', 'question_number': 21,
                    'question_id': 'SYNTHETIC', 'paper_heading_quotes': ['SYNTHETIC PAPER']}},
                'worlds': {'camp': {'question': {'question_id': 'SYNTHETIC',
                    'passage': 'SYNTHETIC: take part in workshops.',
                    'options': {'A': 'SYNTHETIC: Chair workshops.'}}}}}
        write_json(self.plan, plan)
        self.output = self.root / 'packaging'

        def synthetic_cover(candidate_id, folder, font_dir):
            folder = Path(folder)
            result = {}
            for key in ('full', 'mobile', 'editable_svg'):
                path = folder / (candidate_id + '-' + key + '.synthetic')
                path.write_text('SYNTHETIC ' + candidate_id + key, encoding='utf-8')
                result[key] = packaging.asset(path)
            result['text_measurements'] = []
            return result
        with patch.object(packaging, 'render_cover', side_effect=synthetic_cover):
            self.package = packaging.generate_candidates(self.output, 'synthetic-cut', self.author, self.plan)
        self.media = self.root / 'synthetic-media.bin'
        self.media.write_bytes(b'SYNTHETIC CONTROL; NOT A REAL FILM')
        self.qa = self.root / 'MASTER_DELIVERY_QA.json'
        write_json(self.qa, {'media': str(self.media), 'sha256': packaging.file_sha(self.media),
            'same_revision': 'synthetic-cut', 'plan_sha256': packaging.file_sha(self.plan),
            'frames': 240, 'full_decode': 'PASS', 'formal_4k_rendered': True})
        self.inspect = patch.object(packaging, 'inspect_media', return_value={
            'status': 'PASS', 'duration': 10, 'width': 3840, 'height': 2160,
            'fps': '24/1', 'audio_streams': 1, 'full_decode': True, 'synthetic': True})
        self.inspect.start()
        self.addCleanup(self.inspect.stop)

    def approved_control(self):
        value = deepcopy(self.package)
        review = packaging.choice_template(value, 'B')
        proof = self.root / 'synthetic-external-user-declaration.txt'
        proof.write_text('SYNTHETIC external user and ChatGPT choice', encoding='utf-8')
        review.update(status='APPROVED', reviewer='SYNTHETIC USER', reviewed_at='2026-10-21T12:00:00+08:00',
                      evidence=packaging.asset(proof))
        value['selection'] = review
        return value

    def test_actual_text_three_candidates_and_pending_not_old_film(self):
        value = self.package
        self.assertEqual([c['id'] for c in value['candidates']], ['A', 'B', 'C'])
        self.assertIsNone(value['media'])
        self.assertIsNone(value['selection'])
        self.assertFalse(value['public_render_ready'])
        self.assertFalse(any(c['selected'] for c in value['candidates']))
        self.assertTrue((self.output / '封面审阅入口.html').is_file())
        self.assertIn('workshops', (self.output / '封面审阅入口.html').read_text(encoding='utf-8'))
        self.assertIn('两道', value['publication_text']['description'])

    def test_public_description_is_self_contained_and_keeps_review_metadata_separate(self):
        text = self.package['publication_text']['description']
        self.assertIn('SYNTHETIC PAPER', text)
        self.assertIn('SYNTHETIC ARTICLE', text)
        self.assertIn('阅读A篇第21题', text)
        self.assertNotIn('本包', text)
        self.assertNotIn('待审', text)
        self.assertIn('待审', Path(self.package['publication_text_asset']['path']).read_text(encoding='utf-8'))

    def test_publication_fields_cannot_drift_from_actual_review_document(self):
        value = deepcopy(self.package)
        value['publication_text']['description'] += '\nSYNTHETIC changed description'
        with self.assertRaisesRegex(ValueError, 'actual review document'):
            packaging.validate_assets(value)

    def test_unknown_platform_refused(self):
        value = deepcopy(self.package)
        value['platform'] = 'YOUTUBE'
        with self.assertRaises(ValueError):
            packaging.validate_assets(value)

    def test_packaging_cannot_claim_release_or_publication(self):
        for key in ('public_render_ready', 'published'):
            value = deepcopy(self.package)
            value[key] = True
            with self.assertRaises(ValueError):
                packaging.validate_assets(value)

    def test_candidate_package_not_overwritten(self):
        with self.assertRaises(ValueError):
            packaging.generate_candidates(self.output, 'synthetic-cut', self.author, self.plan)

    def test_stale_source_author_plan_bytes_are_rejected(self):
        for name in ('bundle', 'author', 'plan'):
            with self.subTest(name=name):
                path = getattr(self, name)
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                with self.assertRaises(ValueError):
                    packaging.validate_assets(self.package)
                path.write_bytes(original)

    def test_cover_bytes_changed_blocks_package(self):
        Path(self.package['candidates'][0]['cover']['full']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            packaging.validate_assets(self.package)

    def test_source_anchor_missing_rejected(self):
        plan = json.loads(self.plan.read_text(encoding='utf-8'))
        plan['worlds']['camp']['question']['options']['A'] = 'SYNTHETIC unrelated option'
        write_json(self.plan, plan)
        with self.assertRaises(ValueError):
            packaging._reference_inputs(self.author, self.plan)

    def test_source_hash_author_binding_checked(self):
        self.bundle.write_text('SYNTHETIC changed source', encoding='utf-8')
        with self.assertRaises(ValueError):
            packaging._reference_inputs(self.author, self.plan)

    def test_exact_external_selection_still_not_public_release(self):
        value = self.approved_control()
        self.assertEqual(packaging.selection_status(value), 'EXTERNAL_CREATIVE_SELECTION_RECORDED')
        self.assertFalse(value['public_render_ready'])
        self.assertEqual(value['rights']['public_release'], 'HOLD')

    def test_ai_cannot_choose_for_user(self):
        value = self.approved_control()
        value['selection']['reviewer_kind'] = 'AI'
        self.assertEqual(packaging.selection_status(value), 'PENDING_USER_AND_CHATGPT_SELECTION')

    def test_changed_title_description_media_qa_source_expires_choice(self):
        mutations = (
            lambda p: p['candidates'][0].update(title='SYNTHETIC changed title'),
            lambda p: p['publication_text'].update(description='SYNTHETIC changed description'),
            lambda p: p.update(media=packaging.asset(self.media)),
            lambda p: p.update(final_media_qa=packaging.asset(self.qa)),
            lambda p: p['reference_inputs']['source_anchors'][0].update(start=999),
        )
        for mutate in mutations:
            value = self.approved_control()
            mutate(value)
            self.assertEqual(packaging.selection_status(value), 'INVALIDATED_BY_CHANGED_INPUTS')

    def test_save_recomputes_changed_title_selection_in_a_copy(self):
        value = self.approved_control()
        value['selection_status'] = 'EXTERNAL_CREATIVE_SELECTION_RECORDED'
        value['candidates'][0]['title'] = 'SYNTHETIC changed title after external choice'
        before = deepcopy(value)
        packaging.save_package(self.output, value)
        saved = json.loads((self.output / 'BILIBILI_PACKAGE.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['selection_status'], 'INVALIDATED_BY_CHANGED_INPUTS')
        self.assertEqual(saved['selection'], before['selection'])
        self.assertEqual(value, before)
        self.assertEqual(saved['schema'], packaging.VERSION)
        self.assertFalse(saved['public_render_ready'])

    def test_save_recomputes_current_external_selection_without_mutating_input(self):
        value = self.approved_control()
        value['selection_status'] = 'PENDING_USER_AND_CHATGPT_SELECTION'
        before = deepcopy(value)
        packaging.save_package(self.output, value)
        saved = json.loads((self.output / 'BILIBILI_PACKAGE.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['selection_status'], 'EXTERNAL_CREATIVE_SELECTION_RECORDED')
        self.assertEqual(value, before)

    def test_save_does_not_trust_an_approved_cache_without_external_selection(self):
        value = deepcopy(self.package)
        value['selection_status'] = 'EXTERNAL_CREATIVE_SELECTION_RECORDED'
        packaging.save_package(self.output, value)
        saved = json.loads((self.output / 'BILIBILI_PACKAGE.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['selection_status'], 'PENDING_USER_AND_CHATGPT_SELECTION')
        self.assertIsNone(saved['selection'])

    def test_save_accepts_existing_v1_without_optional_selection_cache(self):
        value = deepcopy(self.package)
        del value['selection_status']
        del value['selection']
        before = deepcopy(value)
        packaging.save_package(self.output, value)
        saved = json.loads((self.output / 'BILIBILI_PACKAGE.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['schema'], packaging.VERSION)
        self.assertEqual(saved['selection_status'], 'PENDING_USER_AND_CHATGPT_SELECTION')
        self.assertEqual(value, before)

    def test_missing_external_evidence_not_approval(self):
        value = self.approved_control()
        value['selection']['evidence'] = None
        self.assertEqual(packaging.selection_status(value), 'INVALID_EXTERNAL_CREDENTIAL_OR_ASSET')

    def test_finalize_binds_real_bytes_and_qa_leaves_user_choice(self):
        before = deepcopy(self.package)
        value = packaging.finalize(self.package, self.author, self.plan, self.media, self.qa)
        self.assertEqual(self.package, before)
        self.assertEqual(value['media']['sha256'], packaging.file_sha(self.media))
        self.assertEqual(value['final_media_qa']['sha256'], packaging.file_sha(self.qa))
        self.assertIsNone(value['selection'])
        self.assertFalse(value['published'])
        self.assertFalse(value['public_render_ready'])

    def test_earlier_selection_expires_on_final_media_binding(self):
        value = packaging.finalize(self.approved_control(), self.author, self.plan, self.media, self.qa)
        self.assertEqual(value['selection_status'], 'INVALIDATED_BY_CHANGED_INPUTS')

    def test_qa_other_revision_plan_media_and_frame_fail(self):
        original = json.loads(self.qa.read_text(encoding='utf-8'))
        for key, change in (('same_revision', 'old-r09'), ('plan_sha256', '0' * 64),
                            ('sha256', '1' * 64), ('frames', 239), ('full_decode', 'PENDING'),
                            ('formal_4k_rendered', False), ('media', 'old-file.mp4')):
            with self.subTest(key=key):
                write_json(self.qa, {**original, key: change})
                with self.assertRaises(ValueError):
                    packaging.finalize(self.package, self.author, self.plan, self.media, self.qa)

    def test_media_clock_not_matched_rejected(self):
        with patch.object(packaging, 'inspect_media', return_value={'duration': 11}):
            with self.assertRaises(ValueError):
                packaging.finalize(self.package, self.author, self.plan, self.media, self.qa)

    def test_both_real_anchor_refs_complete(self):
        anchors = self.package['reference_inputs']['source_anchors']
        self.assertEqual({a['pointer'] for a in anchors}, {'/passage', '/options/A'})
        self.assertTrue(all(a['quote'] == 'workshops' and a['end'] - a['start'] == 9 for a in anchors))

    def test_feedback_no_invented_platform_result_and_uses_existing_ledger(self):
        value = json.loads(Path(self.package['feedback_entry']['path']).read_text(encoding='utf-8'))
        self.assertEqual(value['state'], 'NOT_PUBLISHED')
        self.assertEqual(value['actual_observations'], [])
        self.assertEqual(value['consumer'], 'content_os.engagement_learning.AudienceLearning')
        self.assertEqual(value['template']['retention'], 'UNKNOWN')

    @unittest.skipUnless(Path('C:/Windows/Fonts/msyh.ttc').is_file(), 'Measured native Windows fonts not installed')
    def test_actual_vector_and_raster_full_mobile_sizes(self):
        from PIL import Image
        for candidate_id in ('A', 'B', 'C'):
            result = packaging.render_cover(candidate_id, self.root)
            with Image.open(result['full']['path']) as actual:
                self.assertEqual(actual.size, (1920, 1080))
            with Image.open(result['mobile']['path']) as actual:
                self.assertEqual(actual.size, (320, 180))
            svg = Path(result['editable_svg']['path']).read_text(encoding='utf-8')
            self.assertIn('workshops', svg)
            self.assertNotIn('<image', svg)
            self.assertNotIn('<foreignObject', svg)
            self.assertTrue(all(row['bbox'][2] <= 1856 and row['bbox'][3] <= 1016 for row in result['text_measurements']))


if __name__ == '__main__':
    unittest.main()
