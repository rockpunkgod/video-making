"""Display binding is a style input, never source-layout or aesthetic approval."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
from creative_os.motion_identity import display_identity_binding
from ae_production.autonomous_episode import request_author
from video_contracts import read, write


class DisplayIdentityTests(unittest.TestCase):
    def test_style_cannot_claim_teaching_authority_or_apply_to_source(self):
        original = display_identity_binding()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = original['profile'].copy()
            profile['authority'] = 'teaching'
            write(root / 'display-identity.json', profile)
            with patch('creative_os.motion_identity.DIRECTORY', root):
                with self.assertRaises(ValueError):
                    display_identity_binding()
                profile['authority'] = 'visual_metaphor_only'
                profile['scope'] = ['source_glyph']
                write(root / 'display-identity.json', profile)
                with self.assertRaises(ValueError):
                    display_identity_binding()

    def test_exact_file_hash_and_protected_source_scope(self):
        item = display_identity_binding()
        self.assertEqual(item['sha256'], hashlib.sha256(Path(item['path']).read_bytes()).hexdigest())
        self.assertEqual(item['consumer_sha256'], hashlib.sha256(Path(item['consumer']).read_bytes()).hexdigest())
        self.assertFalse(set(item['profile']['scope']) & set(item['profile']['excluded_scope']))
        self.assertIn('original_exam_layout', item['profile']['excluded_scope'])
        self.assertIn('source_glyph', item['profile']['excluded_scope'])

    def test_author_request_really_binds_profile_and_consumer(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'FREE_SHOWCASE_POLICY.md').write_text('Synthetic policy', encoding='utf-8')
            brief = folder / 'brief.json'
            hook = folder / 'hook.json'
            write(hook, {'synthetic': True})
            write(brief, {'schema': 'autonomous-episode-brief/v1', 'product': 'FREE_SHOWCASE',
                          'asset_pool': [], 'style_inputs': [],
                          'audience_hook_decision': {'path': str(hook),
                            'sha256': hashlib.sha256(hook.read_bytes()).hexdigest()}})
            with patch('ae_production.autonomous_episode.ROOT', folder):
                result = request_author(folder, brief)
            packet = read(result['request'])['packet']
            item = packet['display_identity']
            self.assertEqual(packet['input_files'][item['path']], item['sha256'])
            self.assertEqual(packet['input_files'][item['consumer']], item['consumer_sha256'])
            self.assertFalse((folder / 'AV_AUTHOR.json').exists())

    def test_changed_style_changes_new_job_without_rewriting_old_request(self):
        original = display_identity_binding()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            style = folder / 'style'
            style.mkdir()
            shutil.copy2(original['path'], style / 'display-identity.json')
            shutil.copy2(original['consumer'], style / 'display-identity.js')
            (folder / 'FREE_SHOWCASE_POLICY.md').write_text('Synthetic policy', encoding='utf-8')
            hook = folder / 'hook.json'
            write(hook, {'synthetic': True})
            brief = folder / 'brief.json'
            write(brief, {'schema': 'autonomous-episode-brief/v1', 'product': 'FREE_SHOWCASE',
                'asset_pool': [], 'style_inputs': [], 'audience_hook_decision': {'path': str(hook),
                'sha256': hashlib.sha256(hook.read_bytes()).hexdigest()}})
            with patch('ae_production.autonomous_episode.ROOT', folder), patch('creative_os.motion_identity.DIRECTORY', style):
                first = request_author(folder, brief)
                old = Path(first['request']).read_bytes()
                data = read(style / 'display-identity.json')
                data['type']['semantic_heading']['size_px'] = 62
                write(style / 'display-identity.json', data)
                second = request_author(folder, brief)
            self.assertNotEqual(first['request_sha'], second['request_sha'])
            self.assertEqual(Path(first['request']).read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
