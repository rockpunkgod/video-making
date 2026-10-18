"""Synthetic normal-restart/cache tests. Never starts or controls Adobe."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from ae_production import authored_native as native
from ae_production import native_host_restart as restart
from scripts.voice_delivery import sha256
from video_contracts import read, write


class NativeHostRestartTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / 'synthetic-revision'; self.folder.mkdir()
        (self.folder / 'media').mkdir()
        self.project = self.folder / 'media/MAIN_FILM.aep'; self.project.write_bytes(b'SYNTHETIC saved native project')
        self.executable = self.folder / 'AfterFX.exe'; self.executable.write_bytes(b'SYNTHETIC executable - never run')
        self.ownership = self.folder / 'ownership'
        write(self.folder / 'native-identity.json', {'comp_id': 7, 'master_comp_id': 19})
        self.host_class = native.Host
        self.old = self.make_host(123, str(self.project), 'comp:7')
        self.fresh = self.make_host(456, '', 'none')
        self.shutdown_calls = []; self.open_calls = []

        def old_js(code, label=None, timeout=600):
            self.shutdown_calls.append(code)
            self.assertIn('app.quit()', code)
            return {'quit_requested': True}

        def fresh_js(code, label=None, timeout=600):
            self.open_calls.append(code)
            self.assertIn('app.open(new File(', code)
            self.fresh.state.update(project_path=str(self.project), target_id='comp:7')
            return {'project': str(self.project), 'comp_id': 7}

        self.old.js = Mock(side_effect=old_js); self.fresh.js = Mock(side_effect=fresh_js)

    def make_host(self, pid, project, target):
        host = self.host_class.__new__(self.host_class)
        host.folder = self.folder; host.project = self.project; host.pid = pid; host.hwnd = pid + 1
        host.kind = 'after_effects'; host.native_name = 'AfterFX'
        host.h = {'ownership_directory': str(self.ownership), 'ae_expected_project': ''}
        host.state = {'process_id': pid, 'project_path': project, 'target_id': target,
                      'dirty': False, 'rendering': False}
        host.identity = Mock(side_effect=lambda: dict(host.state))
        return host

    def environment(self, factory=None, observed=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(native, 'plan', return_value=({}, {})))
        stack.enter_context(patch.object(native, 'current_native', return_value=(
            {}, {}, {'comp_id': 7, 'master_comp_id': 19})))
        process = stack.enter_context(patch.object(native, 'process', return_value=observed or {
            'Id': self.old.pid, 'Path': str(self.executable)}))
        constructor = stack.enter_context(patch.object(native, 'Host', side_effect=factory or (lambda *a: self.fresh)))
        launch = stack.enter_context(patch.object(restart.subprocess, 'run', return_value=None))
        absent = stack.enter_context(patch.object(restart, 'process_absent', return_value=True))
        stack.enter_context(patch.object(restart.time, 'sleep'))
        return constructor, launch, absent, process

    def test_reconstructs_new_pid_and_new_ownership_target_after_one_normal_restart(self):
        constructor, launch, absent, _ = self.environment()
        before_sha = sha256(self.project)
        result = restart.restart_saved_host(self.old, 768)
        self.assertIs(result, self.fresh)
        self.assertEqual(len(self.shutdown_calls), 1); self.assertEqual(len(self.open_calls), 1)
        self.assertEqual(launch.call_count, 1); self.assertEqual(constructor.call_count, 1)
        self.assertTrue(all(call.args == (123,) for call in absent.call_args_list))
        self.assertEqual(sha256(self.project), before_sha)
        recorded_pids = []

        def next_native_write():
            recorded_pids.append(read(self.ownership / 'after_effects.json')['target']['process_id'])
            return {'synthetic_render': True}

        result.mutate('SYNTHETIC next native operation', next_native_write)
        self.assertEqual(recorded_pids, [456])
        self.assertFalse((self.ownership / 'after_effects.json').exists())
        record = read(next(self.folder.glob('HOST_RESTART_*.json')))
        self.assertEqual(record['state'], 'RESTARTED_SAVED_TARGET_VERIFIED')
        self.assertEqual(record['before']['process_id'], 123)
        self.assertEqual(record['after']['process_id'], 456)
        self.assertFalse(record['forced_termination'])
        self.assertFalse(record['shutdown']['force_termination'])

    def test_existing_saved_target_does_not_repeat_the_open(self):
        self.fresh.state.update(project_path=str(self.project), target_id='comp:7')
        _, launch, _, _ = self.environment()
        self.assertIs(restart.restart_saved_host(self.old, 768), self.fresh)
        self.assertEqual(self.open_calls, []); self.assertEqual(launch.call_count, 1)

    def test_other_current_project_dirty_host_or_changed_process_is_preserved(self):
        self.environment()
        original = dict(self.old.state)
        cases = [{'project_path': str(self.folder / 'unrelated.aep')}, {'dirty': True}, {'rendering': True}]
        for change in cases:
            self.old.state = {**original, **change}
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                restart.restart_saved_host(self.old, 768)
        self.assertEqual(self.shutdown_calls, []); self.assertEqual(self.open_calls, [])
        self.assertFalse(self.ownership.exists())

    def test_foreign_owned_or_uncertain_dispatch_prevents_shutdown_and_launch(self):
        _, launch, _, _ = self.environment()
        self.ownership.mkdir()
        foreign = {'state': 'UNCERTAIN', 'token': 'other-task', 'target': {'process_id': 999}}
        write(self.ownership / 'after_effects.json', foreign)
        with self.assertRaises(FileExistsError): restart.restart_saved_host(self.old, 768)
        self.assertEqual(read(self.ownership / 'after_effects.json'), foreign)
        self.assertEqual(self.shutdown_calls, []); launch.assert_not_called()

    def test_unknown_project_open_is_dispatched_once_and_preserves_new_pid_uncertainty(self):
        def unknown_open(code, label=None, timeout=600):
            self.open_calls.append(code)
            self.fresh.state.update(project_path=str(self.project), target_id='comp:7')
            raise TimeoutError('SYNTHETIC response lost after possible native project open')

        self.fresh.js.side_effect = unknown_open
        constructor, launch, _, _ = self.environment()
        with self.assertRaises(TimeoutError): restart.restart_saved_host(self.old, 768)
        self.assertEqual(len(self.open_calls), 1); self.assertEqual(constructor.call_count, 1)
        self.assertEqual(launch.call_count, 1)
        record = read(self.ownership / 'after_effects.json')
        self.assertEqual(record['state'], 'UNCERTAIN')
        self.assertEqual(record['target']['process_id'], 456)
        self.assertEqual(len(self.shutdown_calls), 1)

    def test_a_new_host_with_another_project_or_target_gets_no_open_write(self):
        self.fresh.state.update(project_path=str(self.folder / 'someone-elses.aep'))
        constructor, _, _, _ = self.environment()
        with self.assertRaisesRegex(RuntimeError, 'another project'):
            restart.restart_saved_host(self.old, 768)
        self.assertEqual(constructor.call_count, 1); self.assertEqual(self.open_calls, [])

    def test_unavailable_read_only_startup_can_be_polled_without_relaunch_or_open_replay(self):
        count = []

        def factory(*args):
            count.append(1)
            if len(count) < 3: raise RuntimeError('SYNTHETIC startup not yet visible')
            return self.fresh

        _, launch, _, _ = self.environment(factory=factory)
        self.assertIs(restart.restart_saved_host(self.old, 768), self.fresh)
        self.assertEqual(len(count), 3); self.assertEqual(launch.call_count, 1)
        self.assertEqual(len(self.open_calls), 1); self.assertEqual(len(self.shutdown_calls), 1)

    def test_save_checkpoint_change_aborts_before_new_project_open(self):
        def changed_during_shutdown(code, label=None, timeout=600):
            self.shutdown_calls.append(code); self.project.write_bytes(b'CHANGED saved checkpoint')

        self.old.js.side_effect = changed_during_shutdown
        constructor, launch, _, _ = self.environment()
        with self.assertRaises(ValueError): restart.restart_saved_host(self.old, 768)
        launch.assert_not_called(); constructor.assert_not_called()
        self.assertEqual(read(self.ownership / 'after_effects.json')['state'], 'SHUTTING_DOWN')

    def test_invalid_current_comp_or_process_identity_is_rejected_before_quit(self):
        self.environment()
        original = dict(self.old.state)
        for change in ({'target_id': 'none'}, {'target_id': 'comp:19'}, {'process_id': 789}):
            self.old.state = {**original, **change}
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                restart.restart_saved_host(self.old, 768)
        self.assertEqual(self.shutdown_calls, []); self.assertEqual(self.open_calls, [])

    def test_new_process_change_between_constructor_and_identity_prevents_open(self):
        self.fresh.state['process_id'] = 789
        constructor, _, _, _ = self.environment()
        with self.assertRaises((RuntimeError, ValueError)):
            restart.restart_saved_host(self.old, 768)
        self.assertEqual(self.open_calls, [])
        self.assertEqual(constructor.call_count, 1)

    def test_post_open_process_change_cannot_return_a_stale_host_controller(self):
        def changed_after_release():
            value = dict(self.fresh.state)
            if self.open_calls and not (self.ownership / 'after_effects.json').exists():
                value['process_id'] = 789
            return value

        self.fresh.identity.side_effect = changed_after_release
        constructor, _, _, _ = self.environment()
        with self.assertRaises((RuntimeError, ValueError)):
            restart.restart_saved_host(self.old, 768)
        self.assertEqual(len(self.open_calls), 1)
        self.assertEqual(constructor.call_count, 1)

    def test_changed_saved_checkpoint_during_startup_is_rejected_before_open(self):
        def changed_file(*args):
            self.project.write_bytes(b'CHANGED while the application was starting')
            return self.fresh

        constructor, _, _, _ = self.environment(factory=changed_file)
        with self.assertRaises(ValueError): restart.restart_saved_host(self.old, 768)
        self.assertEqual(self.open_calls, [])
        self.assertEqual(constructor.call_count, 1)


class NativeCacheWiringTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name); self.directory = self.folder / 'native-master-parts'
        self.directory.mkdir(); (self.folder / 'media').mkdir()
        self.a = {'host': {}}; self.p = {'frames': 96, 'duration': 4}; self.n = {'comp_id': 1, 'master_comp_id': 2}
        write(self.folder / 'AV_PLAN.json', self.p); write(self.folder / 'native-identity.json', self.n)

    def row(self, filename, start=0, end=96, **extra):
        media = self.directory / (filename + '.mp4'); media.write_bytes(b'SYNTHETIC cache media only')
        result = {'done': True, 'status': 3019, 'start': start, 'end': end, 'path': str(media),
            'sha256': sha256(media), 'comp_id': 2, 'plan_sha256': sha256(self.folder / 'AV_PLAN.json'),
            'native_identity_sha256': sha256(self.folder / 'native-identity.json'), **extra}
        write(media.with_suffix('.json'), result)
        return result

    def environment(self):
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(native, 'current_native', return_value=(self.a, self.p, self.n)))
        stack.enter_context(patch.object(native, 'audit', return_value={}))
        host = Mock(); host.mutation_js.side_effect = AssertionError('No native write is authorized by this synthetic cache test')
        stack.enter_context(patch.object(native, 'Host', return_value=host))
        stack.enter_context(patch.object(native, 'require_disk'))
        stack.enter_context(patch.object(native, 'available_memory', return_value=16 * 2**30))
        stack.enter_context(patch.object(native, 'monitor_existing_render', return_value=nullcontext({'minimum_free_bytes': 16 * 2**30})))
        run = stack.enter_context(patch.object(native.subprocess, 'run', side_effect=AssertionError('No concat/render subprocess is authorized by this negative cache test')))
        stream = {'codec_type': 'video', 'width': 3840, 'height': 2160, 'r_frame_rate': '24/1', 'nb_read_frames': '96'}
        stack.enter_context(patch.object(native, 'probe', return_value={'streams': [stream]}))
        return host, run

    def test_empty_or_erased_reuse_proof_cannot_fall_through_as_new_native_render(self):
        self.row('part-0000', reuse={}, new_native_render=False, rendered_in_revision='parent')
        self.environment()
        with patch('ae_production.native_parts_reuse.validate_reused_part', side_effect=ValueError('SYNTHETIC missing reuse proof')) as check:
            with self.assertRaises(ValueError): native.render(self.folder, master=True)
        check.assert_called_once()

    def test_unreceipted_native_media_requires_inspection_instead_of_new_filename_replay(self):
        (self.directory / 'part-0000.mp4').write_bytes(b'SYNTHETIC unknown partial native write')
        host, _ = self.environment()
        with self.assertRaises(ValueError): native.render(self.folder, master=True)
        host.mutation_js.assert_not_called()

    def test_false_done_cached_receipt_is_not_a_completed_render(self):
        self.row('part-0000', done=False)
        self.environment()
        with self.assertRaises(ValueError): native.render(self.folder, master=True)

    def test_cache_is_sorted_by_frame_start_and_valid_reuse_is_revalidated(self):
        first = self.row('part-0009', start=0, end=48, reuse={'schema': 'SYNTHETIC'}, new_native_render=False)
        second = self.row('part-0001', start=48, end=96)
        picture = self.folder / 'media/MASTER_PICTURE_4K24.mp4'; picture.write_bytes(b'SYNTHETIC joined picture')
        write(self.folder / 'MASTER_PICTURE_RECEIPT.json', {'plan_sha256': sha256(self.folder / 'AV_PLAN.json'),
            'comp_id': 2, 'frames': 96, 'parts': [first, second], 'sha256': sha256(picture)})
        host, run = self.environment()
        with patch('ae_production.native_parts_reuse.validate_reused_part', return_value={'status': 'SYNTHETIC verified'}) as check:
            result = native.render(self.folder, master=True)
        self.assertEqual(result['duration'], 4)
        check.assert_called_once_with(self.folder, first, first['path'])
        host.mutation_js.assert_not_called(); run.assert_not_called()
        self.assertEqual([p['start'] for p in read(self.folder / 'MASTER_PICTURE_RECEIPT.json')['parts']], [0, 48])


if __name__ == '__main__':
    unittest.main()
