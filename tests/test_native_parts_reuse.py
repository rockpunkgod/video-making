"""Synthetic reuse/shutdown controls; never calls Adobe or certifies media taste."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production import native_parts_reuse as reuse
from ae_production.authored_episode import script_text
from ae_production.host_ownership import HostOwnership
from scripts.voice_delivery import sha256
from video_contracts import read, sha, write


class NativePartsReuseTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.parent, self.child = self.root / 'parent', self.root / 'child'
        template = b'// SYNTHETIC native template\r\n' + reuse.TITLE_OLD + b'\r\n' + reuse.LIGHT_OLD + b'\r\n'
        self.make_revision(self.parent, template, 1)
        self.make_revision(self.child, template.replace(reuse.TITLE_OLD, reuse.TITLE_NEW).replace(
            reuse.LIGHT_OLD, reuse.LIGHT_NEW), 7)
        self.mock_probe = patch.object(reuse, '_probe_master', side_effect=lambda path, frames: {
            'codec_name': 'h264', 'width': 3840, 'height': 2160, 'r_frame_rate': '24/1',
            'avg_frame_rate': '24/1', 'nb_read_frames': str(frames), 'duration': str(frames / 24)})
        self.probe = self.mock_probe.start(); self.addCleanup(self.mock_probe.stop)
        for i in range(5):
            self.make_part(i, i * 48, (i + 1) * 48)

    def make_revision(self, folder, template, offset):
        folder.mkdir(); (folder / 'media').mkdir(); (folder / 'native-source').mkdir()
        project = folder / 'media/MAIN_FILM.aep'; project.write_bytes(b'SYNTHETIC AEP ONLY')
        original, converted, padded = folder / 'take.wav', folder / 'take-48k.wav', folder / 'take-pad.wav'
        original.write_bytes(b'SYNTHETIC ORIGINAL AUDIO'); converted.write_bytes(b'SYNTHETIC 48K AUDIO')
        padded.write_bytes(b'SYNTHETIC PADDED COMPLETE AUDIO')
        transcript = folder / 'take.txt'; transcript.write_text('Synthetic spoken copy.', encoding='utf-8')
        source, status = self.root / 'source.json', self.root / 'source-status.json'
        if not source.exists():
            write(source, {'scope': 'SYNTHETIC original only'}); write(status, {'scope': 'SYNTHETIC active only'})
        scenes = [
            {'id': 'START', 'kind': 'task', 'world': 'toy', 'title': 'Opening',
             'start': 0, 'end': 2, 'voice_ids': ['take'], 'reading_events': []},
            {'id': 'CHECK_X', 'kind': 'compare', 'world': 'toy', 'title': 'Known simple check',
             'start': 2, 'end': 3, 'voice_ids': [], 'motion_treatment': 'in_place_check',
             'attention_events': [{'target': 'candidate', 'time': 2.75}], 'reading_events': []},
            {'id': 'COMPARE_Y', 'kind': 'compare', 'world': 'toy', 'title': 'Relation',
             'start': 3, 'end': 5, 'voice_ids': [], 'motion_treatment': 'critical_comparison',
             'reading_events': [{'depart': 3.25, 'arrival': 3.5, 'end_time': 4.5,
                                 'start': 0, 'end': 6, 'quote': 'source'}]},
            {'id': 'END', 'kind': 'task', 'world': 'toy', 'title': 'Closure',
             'start': 5, 'end': 10, 'voice_ids': [], 'reading_events': []}]
        author = {'revision': folder.name, 'copy_review': 'PENDING', 'voices': [
            {'id': 'take', 'text': transcript.read_text('utf-8')}], 'scenes': deepcopy(scenes),
            'sources': {'toy': {'bundle': str(source), 'status': str(status)}}, 'input_files': {},
            'voice_delivery': 'delivery.json'}
        write(folder / 'AV_AUTHOR.json', author)
        (folder / 'EPISODE_SCRIPT.md').write_text(script_text(author), encoding='utf-8')
        clip = {'id': 'take', 'audio': original.name, 'audio_sha256': sha256(original),
                'transcript': transcript.name, 'transcript_sha256': sha256(transcript)}
        write(folder / 'delivery.json', {'clips': [clip]})
        write(folder / 'VOICE_ALIGNMENT.json', {'delivery_sha256': sha256(folder / 'delivery.json'),
            'model': 'SYNTHETIC model', 'clips': [{'id': 'take', 'cues': []}]})
        write(folder / 'ARTICLE_CHUNKS.json', {'scope': 'SYNTHETIC groups only'})
        chunking = {'input_sha256': sha256(folder / 'ARTICLE_CHUNKS.json'), 'articles': {}}
        write(folder / 'READING_CHUNKS.json', chunking)
        plan = {'revision': folder.name, 'author_sha256': sha256(folder / 'AV_AUTHOR.json'),
            'voice_delivery_sha256': sha256(folder / 'delivery.json'),
            'alignment_sha256': sha256(folder / 'VOICE_ALIGNMENT.json'),
            'complete_copy_sha256': sha(script_text(author)), 'copy_review': 'PENDING',
            'format': {'width': 1920, 'height': 1080, 'fps': 24},
            'master_format': {'width': 3840, 'height': 2160, 'fps': 24}, 'frames': 240, 'duration': 10,
            'public_render_ready': False, 'scenes': scenes, 'world_order': ['toy'], 'layout': {'column': 1440},
            'worlds': {'toy': {'question': {'passage': 'source'}, 'source': author['sources']['toy']}},
            'article_chunking': chunking, 'editorial_consumption': {'manifest_sha256': folder.name,
                                                                   'source_role': 'interpreter'},
            'cues': [{'start': .1, 'end': .5, 'text': transcript.read_text('utf-8')}], 'music': [],
            'segments': [{'id': 'take', 'text': transcript.read_text('utf-8'), 'voice_start': .1,
                'voice_end': .5, 'time_stretch': False, 'truncated': False,
                'voice': {**clip, 'path': str(converted), 'sha256': sha256(converted),
                    'padded_path': str(padded), 'padded_sha256': sha256(padded),
                    'original_path': str(original), 'duration_seconds': .4}}]}
        write(folder / 'AV_PLAN.json', plan)
        template_path = folder / 'native-source/authored-episode.jsx'; template_path.write_bytes(template)
        rig = folder / 'native-source/reading-focus.jsx'; rig.write_bytes(b'SYNTHETIC unchanged reading rig')
        write(folder / 'NATIVE_SOURCES.json', {
            'template': {'path': template_path.relative_to(folder).as_posix(), 'sha256': sha256(template_path)},
            'reading_rig': {'path': rig.relative_to(folder).as_posix(), 'sha256': sha256(rig)}})
        native = {'project_path': str(project), 'comp_id': offset, 'master_comp_id': offset + 1,
            'frames': 240, 'duration': 10, 'width': 1920, 'height': 1080, 'media_role': 'EDITORIAL_PROXY',
            'plan_sha256': sha256(folder / 'AV_PLAN.json'), 'template_sha256': sha256(template_path),
            'reading_rig_sha256': sha256(rig)}
        write(folder / 'native-identity.json', native)
        write(folder / 'native-audit.json', {'project': str(project), 'width': 1920, 'height': 1080,
            'fps': 24, 'duration': 10, 'reading_rig_sha256': sha256(rig),
            'unrendered_master': {'width': 3840, 'height': 2160, 'fps': 24, 'duration': 10},
            'layers': [
                {'id': offset + 10, 'name': 'SOURCE', 'parent': None, 'text': 'source', 'font': 'ArialMT'},
                {'id': offset + 11, 'name': 'LIGHT_CANDIDATE_CHECK_X', 'parent': None,
                 'text': 'A source', 'future_color_fixed': folder == self.child},
                {'id': offset + 12, 'name': 'TASK_TITLE_COMPARE_Y', 'parent': None,
                 'text': 'Relation', 'outPoint': 3.25 if folder == self.child else 5}]})

    def make_part(self, index, start, end):
        directory = self.parent / 'native-master-parts'; directory.mkdir(exist_ok=True)
        path = directory / f'part-{index:04}.mp4'; path.write_bytes(f'SYNTHETIC part {start}:{end}'.encode())
        write(path.with_suffix('.json'), {'done': True, 'status': 3019, 'start': start, 'end': end,
            'preset': 'SYNTHETIC H.264 native setting', 'path': str(path), 'sha256': sha256(path),
            'comp_id': read(self.parent / 'native-identity.json')['master_comp_id'],
            'plan_sha256': sha256(self.parent / 'AV_PLAN.json'),
            'native_identity_sha256': sha256(self.parent / 'native-identity.json')})

    def alter_child_plan(self, edit):
        value = read(self.child / 'AV_PLAN.json'); edit(value); write(self.child / 'AV_PLAN.json', value)
        native = read(self.child / 'native-identity.json'); native['plan_sha256'] = sha256(self.child / 'AV_PLAN.json')
        write(self.child / 'native-identity.json', native)

    def change_snapshot(self, key, content):
        manifest = read(self.child / 'NATIVE_SOURCES.json'); path = self.child / manifest[key]['path']
        path.write_bytes(content); digest = sha256(path); manifest[key]['sha256'] = digest
        write(self.child / 'NATIVE_SOURCES.json', manifest)
        native = read(self.child / 'native-identity.json'); native[
            'template_sha256' if key == 'template' else 'reading_rig_sha256'] = digest
        write(self.child / 'native-identity.json', native)
        if key == 'reading_rig':
            audit = read(self.child / 'native-audit.json'); audit['reading_rig_sha256'] = digest
            write(self.child / 'native-audit.json', audit)

    def test_only_whole_disjoint_parts_reused_and_parent_provenance_retained(self):
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual([(r['start'], r['end']) for r in report['reused_parts']], [(0, 48), (144, 192), (192, 240)])
        self.assertEqual(report['reused_frames'], 144)
        self.assertEqual({r['scene'] for r in report['affected_frame_ranges']}, {'CHECK_X', 'COMPARE_Y'})
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); result = reuse.validate_reused_part(self.child, row, row['path'])
            self.assertEqual(result['status'], 'VERIFIED_PARENT_NATIVE_BYTES')
            self.assertFalse(result['new_native_render'])
            self.assertTrue(Path(row['path']).is_relative_to(self.parent))
            self.assertEqual(row['rendered_in_revision'], self.parent.name)
        self.assertEqual(list((self.child / 'native-master-parts').glob('*.mp4')), [])
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent, self.child), report)

    def test_rebound_scene_time_reading_layout_caption_and_unknown_field_changes_rejected(self):
        original = read(self.child / 'AV_PLAN.json')
        edits = [lambda p: p['scenes'][2]['reading_events'][0].update(arrival=3.6),
                 lambda p: p['scenes'][2].update(title='Changed visible title'),
                 lambda p: p['scenes'][1]['attention_events'][0].update(time=2.8),
                 lambda p: p['layout'].update(column=1500),
                 lambda p: p['cues'][0].update(text='Changed subtitle'),
                 lambda p: p.update(unknown_render_setting=True),
                 lambda p: p['worlds']['toy']['question'].update(passage='changed')]
        for edit in edits:
            with self.subTest(edit=edit):
                write(self.child / 'AV_PLAN.json', original); self.alter_child_plan(edit)
                with self.assertRaises(ValueError): reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())

    def test_fully_rebound_changed_audio_is_rejected(self):
        path = self.child / 'take-48k.wav'; path.write_bytes(b'CHANGED SYNTHETIC AUDIO')
        self.alter_child_plan(lambda p: p['segments'][0]['voice'].update(sha256=sha256(path)))
        with self.assertRaisesRegex(ValueError, 'Plans differ'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_only_two_exact_template_changes_and_same_rig_allowed(self):
        original = (self.child / 'native-source/authored-episode.jsx').read_bytes()
        for content in (original + b'// third change', original.replace(b'a+.25', b'a+.3'),
                        original.replace(reuse.LIGHT_NEW, reuse.LIGHT_OLD)):
            with self.subTest(content=content[-30:]):
                self.change_snapshot('template', content)
                with self.assertRaisesRegex(ValueError, 'two exact'):
                    reuse.reuse_unchanged_parts(self.parent, self.child)
        self.change_snapshot('template', original); self.change_snapshot('reading_rig', b'changed rig')
        with self.assertRaisesRegex(ValueError, 'reading rig'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_unaffected_real_native_layer_and_snapshot_path_must_match(self):
        audit = read(self.child / 'native-audit.json'); audit['layers'][0]['font'] = 'ChangedFont'
        write(self.child / 'native-audit.json', audit)
        with self.assertRaisesRegex(ValueError, 'Unaffected actual native layer'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        audit['layers'][0]['font'] = 'ArialMT'; write(self.child / 'native-audit.json', audit)
        manifest = read(self.child / 'NATIVE_SOURCES.json'); manifest['template']['path'] = '../outside.jsx'
        write(self.child / 'NATIVE_SOURCES.json', manifest)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_parent_receipt_media_hash_native_identity_and_master_comp_are_required(self):
        path = self.parent / 'native-master-parts/part-0000.json'; original = read(path)
        for edit in (lambda r: r.update(done=False), lambda r: r.update(sha256='0' * 64),
                     lambda r: r.update(comp_id=1), lambda r: r.update(plan_sha256='0' * 64),
                     lambda r: r.update(native_identity_sha256='0' * 64),
                     lambda r: r.update(end=241), lambda r: r.update(reuse={})):
            row = deepcopy(original); edit(row); write(path, row)
            with self.subTest(row=row), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())

    def test_wrong_resolution_fps_count_or_duration_cannot_claim_native_4k(self):
        self.mock_probe.stop()
        good = {'codec_type': 'video', 'codec_name': 'h264', 'width': 3840, 'height': 2160,
                'r_frame_rate': '24/1', 'avg_frame_rate': '24/1', 'nb_read_frames': '48', 'duration': '2.0'}
        for key, value in [('width', 1920), ('r_frame_rate', '30/1'), ('avg_frame_rate', '30/1'),
                           ('nb_read_frames', '47'), ('duration', '1.0')]:
            wrong = {**good, key: value}
            with self.subTest(key=key), patch.object(reuse.subprocess, 'check_output', return_value=json.dumps({'streams': [wrong]}).encode()):
                with self.assertRaisesRegex(ValueError, '4K24'):
                    reuse._probe_master('synthetic.mp4', 48)

    def test_resume_rechecks_parent_bytes_proof_and_exact_child_row(self):
        reuse.reuse_unchanged_parts(self.parent, self.child)
        row = read(self.child / 'native-master-parts/part-0000.json')
        changed = deepcopy(row); changed['new_native_render'] = True
        with self.assertRaises(ValueError): reuse.validate_reused_part(self.child, changed, row['path'])
        with self.assertRaises(ValueError): reuse.validate_reused_part(self.child, row, self.child / 'wrong.mp4')
        Path(row['path']).write_bytes(b'CHANGED parent media')
        with self.assertRaises(ValueError): reuse.validate_reused_part(self.child, row, row['path'])

    def test_child_save_bytes_may_change_but_historical_parent_aep_is_immutable(self):
        reuse.reuse_unchanged_parts(self.parent, self.child)
        row = read(self.child / 'native-master-parts/part-0000.json')
        # A synthetic metadata write demonstrates the intended file-key scope;
        # the caller must still validate the actual live native scene/readback.
        with (self.child / 'media/MAIN_FILM.aep').open('ab') as out:
            out.write(b'SYNTHETIC saved metadata change')
        self.assertFalse(reuse.validate_reused_part(self.child, row, row['path'])['new_native_render'])
        with (self.parent / 'media/MAIN_FILM.aep').open('ab') as out:
            out.write(b'CHANGED historical parent')
        with self.assertRaises(ValueError): reuse.validate_reused_part(self.child, row, row['path'])

    def test_dynamic_affected_scene_predicates_and_empty_title(self):
        source = read(self.parent / 'AV_PLAN.json')
        scene = deepcopy(source['scenes'][2]); scene['kind'] = 'replay'
        source['scenes'] = [scene]
        self.assertEqual(reuse._affected(source)[0]['scene'], 'COMPARE_Y')
        scene['screen_title'] = ''
        self.assertEqual(reuse._affected(source), [])
        scene.update(motion_treatment='in_place_check', event='supported', reading_events=[])
        self.assertEqual(reuse._affected(source)[0]['repairs'], ['light_candidate_initial_ink'])

    def test_no_eligible_or_overlapping_parent_parts_fail_before_writing_child_cache(self):
        path = self.parent / 'native-master-parts/part-0004.json'; value = read(path)
        value['start'] = 180; write(path, value)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())


class SavedHostShutdownTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.project = self.root / 'owned.aep'
        self.project.write_bytes(b'SYNTHETIC saved project')
        self.state = {'process_id': 123, 'project_path': str(self.project), 'target_id': 'comp:1'}
        self.lease = HostOwnership('after_effects', 'synthetic', 'r1', self.state, self.root / 'ownership')
        self.lease.acquire(); self.saved = {str(self.project): sha256(self.project)}

    def reader(self): return {**self.state, 'dirty': False, 'rendering': False}

    def test_normal_transport_disconnect_is_not_replayed_after_verified_exit(self):
        calls = []
        def dispatch():
            calls.append('normal close'); raise ConnectionError('SYNTHETIC process exited after normal request')
        receipt = self.lease.close_saved_host(self.reader, dispatch, lambda: True, self.saved)
        self.assertEqual(calls, ['normal close']); self.assertEqual(receipt['state'], 'CLOSED_VERIFIED')
        self.assertFalse(receipt['force_termination']); self.assertFalse(self.lease.path.exists())

    def test_dirty_unsaved_or_missing_clean_evidence_prevents_dispatch(self):
        readers = [lambda: {**self.reader(), 'dirty': True}, lambda: {**self.reader(), 'rendering': True},
                   lambda: dict(self.state), lambda: {**self.reader(), 'project_path': ''}]
        calls = []
        for reader in readers:
            with self.assertRaises(RuntimeError): self.lease.close_saved_host(reader, lambda: calls.append(1), lambda: True, self.saved)
        self.assertEqual(calls, [])

    def test_foreign_owner_during_read_or_timeout_is_preserved(self):
        foreign = {**read(self.lease.path), 'token': 'foreign'}
        def changed():
            write(self.lease.path, foreign); return self.reader()
        with self.assertRaises(RuntimeError):
            self.lease.close_saved_host(changed, lambda: self.fail('must not dispatch'), lambda: True, self.saved)
        self.assertEqual(read(self.lease.path), foreign)

    def test_timeout_retains_normal_shutdown_for_exact_pid_reconciliation(self):
        calls = []
        with patch('ae_production.host_ownership.time.sleep'), self.assertRaises(RuntimeError):
            self.lease.close_saved_host(self.reader, lambda: calls.append('close'), lambda: False, self.saved)
        self.assertEqual(calls, ['close']); self.assertEqual(read(self.lease.path)['state'], 'UNCERTAIN')
        observed_pids = []
        receipt = HostOwnership.reconcile_saved_shutdown('after_effects', 'synthetic', 'r1',
            self.lease.record['token'], lambda pid: observed_pids.append(pid) or True, self.lease.path.parent)
        self.assertEqual(observed_pids, [123]); self.assertFalse(receipt['shutdown_replayed'])
        self.assertFalse(self.lease.path.exists())

    def test_reconciliation_rejects_foreign_token_live_pid_or_changed_saved_bytes(self):
        with patch('ae_production.host_ownership.time.sleep'), self.assertRaises(RuntimeError):
            self.lease.close_saved_host(self.reader, lambda: None, lambda: False, self.saved)
        token = self.lease.record['token']; directory = self.lease.path.parent
        with self.assertRaises(RuntimeError): HostOwnership.reconcile_saved_shutdown(
            'after_effects', 'synthetic', 'r1', 'foreign', lambda pid: True, directory)
        with self.assertRaises(RuntimeError): HostOwnership.reconcile_saved_shutdown(
            'after_effects', 'synthetic', 'r1', token, lambda pid: False, directory)
        self.project.write_bytes(b'CHANGED saved bytes')
        with self.assertRaises(ValueError): HostOwnership.reconcile_saved_shutdown(
            'after_effects', 'synthetic', 'r1', token, lambda pid: True, directory)
        self.assertTrue(self.lease.path.exists())


if __name__ == '__main__':
    unittest.main()
