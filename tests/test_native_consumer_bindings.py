"""Native consumer byte mutations invalidate receipts; no Adobe execution."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ae_production import authored_native as native
from scripts.voice_delivery import sha256
from video_contracts import read, write


class NativeConsumerBindings(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.folder = self.base/'production'; self.folder.mkdir()
        self.live = self.base/'live'; self.live.mkdir()
        self.paths = {}
        names = {'template': 'authored-episode.jsx', 'reading_rig': 'reading-focus.jsx',
                 'challenge_rig': 'first-person-challenge.jsx', 'symbol_rig': 'cognitive-symbols.jsx'}
        for key, name in names.items():
            path = self.live/name; path.write_text('// Actual fixture bytes: '+key, encoding='utf-8')
            self.paths[key] = path
        for key, constant in [('template', 'TEMPLATE'), ('reading_rig', 'READING_RIG'),
                              ('challenge_rig', 'CHALLENGE_RIG'), ('symbol_rig', 'SYMBOL_RIG')]:
            patcher = patch.object(native, constant, self.paths[key]); patcher.start(); self.addCleanup(patcher.stop)
        self.a = {'revision': 'synthetic'}; self.p = {'revision': 'synthetic', 'frames': 240}
        write(self.folder/'AV_PLAN.json', self.p)
        patcher = patch.object(native, 'plan', return_value=(self.a, self.p)); patcher.start(); self.addCleanup(patcher.stop)
        self.n = {'plan_sha256': sha256(self.folder/'AV_PLAN.json'),
                  **{key+'_sha256': sha256(path) for key, path in self.paths.items()}}
        self.save_identity()

    def save_identity(self): write(self.folder/'native-identity.json', self.n)

    def snapshots(self, keys=None):
        keys = list(self.paths) if keys is None else keys
        directory = self.folder/'native-source'; directory.mkdir(exist_ok=True)
        manifest = {}
        for key in keys:
            path = directory/self.paths[key].name; path.write_bytes(self.paths[key].read_bytes())
            manifest[key] = {'path': path.relative_to(self.folder).as_posix(), 'sha256': sha256(path)}
        write(self.folder/'NATIVE_SOURCES.json', manifest)
        return manifest

    def current(self): return native.current_native(self.folder)

    def test_all_recorded_consumers_bind_to_actual_snapshot_bytes(self):
        self.snapshots(); a, p, n = self.current()
        self.assertEqual((a, p, n), (self.a, self.p, self.n))

    def test_new_consumer_identity_cannot_contradict_an_internally_valid_snapshot(self):
        self.snapshots()
        for key in ('challenge_rig', 'symbol_rig'):
            with self.subTest(consumer=key):
                digest = self.n[key+'_sha256']; self.n[key+'_sha256'] = '0'*64; self.save_identity()
                with self.assertRaisesRegex(ValueError, 'Native picture is stale'): self.current()
                self.n[key+'_sha256'] = digest; self.save_identity()

    def test_changed_new_snapshot_bytes_reject_old_qa_and_native_identity(self):
        manifest = self.snapshots()
        write(self.folder/'native-audit.json', {'status': 'PASS_OLD_RECEIPT'})
        write(self.folder/'MASTER_DELIVERY_QA.json', {'status': 'PASS_OLD_RECEIPT'})
        for key in ('challenge_rig', 'symbol_rig'):
            with self.subTest(consumer=key):
                path = self.folder/manifest[key]['path']; original = path.read_bytes()
                path.write_bytes(original+b'\n// changed real native consumer')
                with self.assertRaisesRegex(ValueError, 'snapshot changed'): self.current()
                # Updating only the snapshot's own hash cannot grant the old
                # native build or old QA validity for these different bytes.
                manifest[key]['sha256'] = sha256(path); write(self.folder/'NATIVE_SOURCES.json', manifest)
                with self.assertRaisesRegex(ValueError, 'Native picture is stale'): self.current()
                path.write_bytes(original); manifest[key]['sha256'] = sha256(path)
                write(self.folder/'NATIVE_SOURCES.json', manifest)

    def test_missing_new_snapshot_does_not_fall_back_to_matching_live_file(self):
        for missing in ('challenge_rig', 'symbol_rig'):
            with self.subTest(consumer=missing):
                manifest = self.snapshots(); manifest.pop(missing)
                write(self.folder/'NATIVE_SOURCES.json', manifest)
                with self.assertRaisesRegex(ValueError, 'missing its source snapshot'): self.current()

    def test_missing_snapshot_file_and_external_snapshot_path_rejected(self):
        manifest = self.snapshots(); path = self.folder/manifest['symbol_rig']['path']; path.unlink()
        with self.assertRaisesRegex(ValueError, 'snapshot changed'): self.current()
        manifest = self.snapshots(); manifest['symbol_rig'] = {'path': str(self.paths['symbol_rig']),
                                                             'sha256': sha256(self.paths['symbol_rig'])}
        write(self.folder/'NATIVE_SOURCES.json', manifest)
        with self.assertRaisesRegex(ValueError, 'snapshot changed'): self.current()

    def test_saved_snapshots_keep_completed_native_build_inspectable_after_live_code_moves(self):
        self.snapshots()
        for path in self.paths.values(): path.write_text('// New repository implementation', encoding='utf-8')
        self.assertEqual(self.current()[2], self.n)

    def test_no_snapshot_uses_live_hashes_for_each_new_recorded_consumer(self):
        self.current()
        for key in ('challenge_rig', 'symbol_rig'):
            with self.subTest(consumer=key):
                path = self.paths[key]; original = path.read_bytes(); path.write_bytes(original+b'\n// live mutation')
                with self.assertRaisesRegex(ValueError, 'Native picture is stale'): self.current()
                path.write_bytes(original)

    def test_historical_identity_without_new_fields_or_snapshots_remains_readable(self):
        self.n.pop('challenge_rig_sha256'); self.n.pop('symbol_rig_sha256'); self.save_identity()
        self.paths['challenge_rig'].unlink(); self.paths['symbol_rig'].unlink()
        self.assertEqual(self.current()[2], self.n)

    def test_historical_two_snapshot_manifest_remains_readable_without_new_live_files(self):
        self.n.pop('challenge_rig_sha256'); self.n.pop('symbol_rig_sha256'); self.save_identity()
        self.snapshots(['template', 'reading_rig'])
        for path in self.paths.values(): path.unlink()
        self.assertEqual(self.current()[2], self.n)

    def test_new_snapshot_cannot_claim_an_unrecorded_native_consumer(self):
        self.snapshots(); self.n.pop('symbol_rig_sha256'); self.save_identity()
        with self.assertRaisesRegex(ValueError, 'no matching saved identity'): self.current()

    def test_partial_historical_opt_in_binds_only_consumers_it_actually_recorded(self):
        self.n.pop('symbol_rig_sha256'); self.save_identity()
        self.snapshots(['template', 'reading_rig', 'challenge_rig'])
        self.paths['symbol_rig'].unlink()
        self.current()
        manifest = read(self.folder/'NATIVE_SOURCES.json'); manifest.pop('challenge_rig')
        write(self.folder/'NATIVE_SOURCES.json', manifest)
        with self.assertRaisesRegex(ValueError, 'missing its source snapshot'): self.current()

    def test_changed_plan_still_invalidates_the_saved_native_picture(self):
        self.snapshots(); write(self.folder/'AV_PLAN.json', {'revision': 'another input'})
        with self.assertRaisesRegex(ValueError, 'Native picture is stale'): self.current()

    def active_feature(self, key):
        if key == 'symbol_rig':
            self.p['symbol_recipes'] = {'rows': [{'symbol_id': 'actual-planned-feature'}]}
        else:
            self.p['audience_challenges'] = {'rows': [{'scene': 'SC01'}]}
            self.n['audit'] = {'audience_challenges': [
                {'scene_id': 'SC01', 'source_identity': 'SAME_ORIGINAL_TEXTLAYERS_NO_RECREATION'}]}
        write(self.folder/'AV_PLAN.json', self.p)
        self.n['plan_sha256'] = sha256(self.folder/'AV_PLAN.json'); self.save_identity()

    def test_active_features_keep_their_exact_saved_snapshot_bindings(self):
        for key in ('symbol_rig', 'challenge_rig'):
            with self.subTest(feature=key):
                self.active_feature(key); self.snapshots()
                self.assertEqual(self.current()[2], self.n)

    def test_active_features_cannot_downgrade_by_removing_identity_and_snapshot_together(self):
        for key in ('symbol_rig', 'challenge_rig'):
            with self.subTest(feature=key):
                # Retain the real active plan/build marker. Removing both
                # optional metadata entries cannot impersonate an old build.
                self.active_feature(key); manifest = self.snapshots()
                digest = self.n.pop(key+'_sha256'); manifest.pop(key)
                self.save_identity(); write(self.folder/'NATIVE_SOURCES.json', manifest)
                with self.assertRaisesRegex(ValueError, 'missing its saved consumer identity'): self.current()
                self.n[key+'_sha256'] = digest; self.save_identity()

    def test_active_features_require_saved_sources_instead_of_falling_back_to_live_code(self):
        for key in ('symbol_rig', 'challenge_rig'):
            with self.subTest(feature=key):
                self.active_feature(key)
                with self.assertRaisesRegex(ValueError, 'requires saved consumer source snapshots'): self.current()

    def test_old_inline_challenge_remains_readable_without_a_new_rig_identity(self):
        # The former challenge lived inside its already byte-bound template;
        # it did not consume the later same-original-layer challenge rig.
        self.p['audience_challenges'] = {'rows': [{'scene': 'SC01'}]}
        self.n['audit'] = {'audience_challenges': [{'scene_id': 'SC01'}]}
        self.n.pop('challenge_rig_sha256'); self.n.pop('symbol_rig_sha256')
        write(self.folder/'AV_PLAN.json', self.p)
        self.n['plan_sha256'] = sha256(self.folder/'AV_PLAN.json'); self.save_identity()
        self.snapshots(['template', 'reading_rig'])
        self.paths['challenge_rig'].unlink(); self.paths['symbol_rig'].unlink()
        self.assertEqual(self.current()[2], self.n)


if __name__ == '__main__': unittest.main()
