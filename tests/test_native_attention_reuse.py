"""Synthetic counterfactuals for bounded authored repairs; no Adobe or real media.

Only ffprobe is mocked. File hashes, snapshot allowlist, complete-plan deltas,
author/editorial mirrors, original-receipt ancestry and resume are real code.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production import native_parts_reuse as reuse
from ae_production.authored_episode import script_text
from scripts.voice_delivery import sha256
from tests import test_native_parts_reuse as fixtures
from video_contracts import read, sha, write


class AuthoredRepairReuseTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.parent, self.child = self.root / 'parent', self.root / 'child'
        template = Path(__file__).resolve().parents[1] / 'ae/templates/authored-episode.jsx'
        # Historical AE snapshots used Windows line endings. Keep this exact
        # fixture stable even when Git checks the maintained source out with LF.
        self.template = template.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        self.assertEqual(hashlib.sha256(self.template).hexdigest(), reuse.SOURCE_ATTENTION_TEMPLATE_SHA256)
        self.make_revision(self.parent, 1, 'These')
        self.make_revision(self.child, 7, 'Name')
        self.mock_probe = patch.object(reuse, '_probe_master', side_effect=lambda path, frames: {
            'codec_name': 'h264', 'width': 3840, 'height': 2160, 'r_frame_rate': '24/1',
            'avg_frame_rate': '24/1', 'nb_read_frames': str(frames), 'duration': str(frames / 24)})
        self.probe = self.mock_probe.start(); self.addCleanup(self.mock_probe.stop)
        for index in range(5):
            self.make_part(self.parent, index, index * 48, (index + 1) * 48)

    def make_revision(self, folder, offset, anchor, *, template=None):
        fixtures.NativePartsReuseTests.make_revision(self, folder, template or self.template, offset)
        author = read(folder / 'AV_AUTHOR.json'); plan = read(folder / 'AV_PLAN.json')
        text = 'Name it. These point back. Same relation.'
        passage = 'Alpha and Beta are cheaper than these options.'
        transcript = folder / 'take.txt'; transcript.write_text(text, encoding='utf-8')
        delivery = read(folder / 'delivery.json'); clip = delivery['clips'][0]
        clip.update(transcript_sha256=sha256(transcript), duration_seconds=1.4)
        write(folder / 'delivery.json', delivery)
        alignment = {'delivery_sha256': sha256(folder / 'delivery.json'), 'model': 'SYNTHETIC model',
            'clips': [{'id': 'take', 'transcript': text, 'audio_sha256': clip['audio_sha256'],
                       'transcript_sha256': clip['transcript_sha256'], 'duration_seconds': 1.4,
                       'cues': [{'text': text[lo:hi], 'text_start': lo, 'text_end': hi,
                                 'start': start, 'end': end} for lo, hi, start, end in
                                [(0, 9, 0, .4), (9, 27, .5, .9), (27, len(text), 1, 1.4)]]}]}
        write(folder / 'VOICE_ALIGNMENT.json', alignment)
        original_alignment = self.root / (folder.name + '-source-alignment.json')
        write(original_alignment, alignment)
        author.update(voices=[{'id': 'take', 'text': text}], alignment_source=str(original_alignment),
                      input_files={str(original_alignment): sha256(original_alignment)})
        for scene in author['scenes']:
            scene.update(voice_ids=[], attention=[])
            scene.pop('attention_events', None)
        scene = author['scenes'][2]
        scene.update(voice_ids=['take'], extract_start=3.25, settled=3.5, candidate_start=3,
                     candidate_arrive=3.25, candidate='A', excerpt='relation',
                     source_refs=[{'world': 'toy', 'pointer': '/passage', 'start': 0,
                                   'end': len(passage), 'quote': passage}],
                     attention=[{'anchor': anchor, 'phrase': 'these options', 'target': 'source'},
                                {'anchor': 'point back', 'phrase': 'Alpha and Beta', 'target': 'source'},
                                {'anchor': 'relation', 'phrase': 'same relation', 'target': 'candidate'}])
        plan['scenes'] = deepcopy(author['scenes'])
        for scene in plan['scenes']:
            scene['attention_events'] = []
        plan['scenes'][2]['attention_events'] = [
            {**event, 'time': (3.5 if anchor == 'Name' else 4) if i == 0 else 4 if i == 1 else 4.5}
            for i, event in enumerate(author['scenes'][2]['attention'])]
        plan['worlds']['toy']['question']['passage'] = passage
        plan['worlds']['toy']['blocks'] = [{'id': 'toy-source-0', 'start': 0, 'end': len(passage),
                                          'text': passage, 'visible': True}]
        plan['excerpts'] = {'relation': {'world': 'toy', 'start': 0, 'end': len(passage),
                                        'quote': passage, 'block_ids': ['toy-source-0']}}
        voice = plan['segments'][0]['voice']; voice.update(transcript_sha256=clip['transcript_sha256'], duration_seconds=1.4)
        plan['segments'][0].update(text=text, scene_id='COMPARE_Y', voice_start=3.5, voice_end=4.9)
        plan['cues'] = [{**cue, 'start': 3.5 + cue['start'], 'end': 3.5 + cue['end']}
                        for cue in alignment['clips'][0]['cues']]
        plan['voice_delivery_sha256'] = sha256(folder / 'delivery.json')
        plan['alignment_sha256'] = sha256(folder / 'VOICE_ALIGNMENT.json')
        manifest = {'authority': 'internal_ai_editorial_only', 'human_approved': False,
                    'source_files': {}, 'scenes': {s['id']: {'consumed_decisions': {
                        'attention': deepcopy(s['attention'])}} for s in author['scenes']}}
        manifest_path = folder / 'EDITORIAL_MANIFEST.json'; write(manifest_path, manifest)
        author['editorial'] = {'schema': 'authored-editorial/v1', 'manifest': str(manifest_path),
                               'sha256': sha256(manifest_path)}
        plan['editorial_consumption']['rows'] = [
            {'scene': s['id'], 'attention': deepcopy(s['attention_events']),
             'candidate_reading_policy': 'visible', 'candidate_states_after': {'A': 'unchecked'}}
            for s in plan['scenes']]
        self.save_author_plan(folder, author, plan)
        audit = read(folder / 'native-audit.json')
        audit['layers'] = [
            {'id': offset + 10, 'name': 'toy-source-0', 'parent': None, 'text': passage,
             'font': 'ArialMT', 'inPoint': 0, 'outPoint': 10},
            {'id': offset + 11, 'name': 'SOURCE_LIFT_COMPARE_Y', 'parent': None,
             'threeD': True, 'inPoint': 3.25, 'outPoint': 5, 'position': [[3.25, [0, 0, 0]], [3.5, [1, 0, 0]]]},
            {'id': offset + 12, 'name': 'EXTRACT_COMPARE_Y_toy-source-0', 'parent': offset + 11,
             'threeD': True, 'inPoint': 3.25, 'outPoint': 5, 'text': passage, 'font': 'ArialMT'},
            {'id': offset + 13, 'name': 'CANDIDATE_FLIGHT_COMPARE_Y', 'parent': None,
             'threeD': True, 'inPoint': 3, 'outPoint': 5, 'text': 'same relation', 'font': 'ArialMT'},
            {'id': offset + 14, 'name': 'TASK_TITLE_COMPARE_Y', 'parent': None,
             'text': 'Relation', 'inPoint': 3, 'outPoint': 5 if template else 3.25},
            {'id': offset + 15, 'name': 'READING_CAMERA', 'parent': None, 'position': [[0, [0, 0, -1500]]]}]
        audit['reading_camera_and_focus'] = {'dof': True, 'keys': [{'time': 3, 'aperture': 14}]}
        write(folder / 'native-audit.json', audit)

    def save_author_plan(self, folder, author, plan):
        write(folder / 'AV_AUTHOR.json', author)
        (folder / 'EPISODE_SCRIPT.md').write_text(script_text(author), encoding='utf-8')
        plan.update(author_sha256=sha256(folder / 'AV_AUTHOR.json'), complete_copy_sha256=sha(script_text(author)))
        write(folder / 'AV_PLAN.json', plan)
        native = read(folder / 'native-identity.json'); native['plan_sha256'] = sha256(folder / 'AV_PLAN.json')
        write(folder / 'native-identity.json', native)

    def change_scene(self, folder, edit, *, time=None):
        author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
        edit(author['scenes'][2])
        a, p = author['scenes'][2], plan['scenes'][2]
        p['attention'] = deepcopy(a['attention'])
        for i, event in enumerate(p['attention_events']):
            event.update(a['attention'][i])
        if time is not None:
            p['attention_events'][0]['time'] = time
        p.pop('candidate_reading_policy', None)
        if 'candidate_reading_policy' in a:
            p['candidate_reading_policy'] = a['candidate_reading_policy']
        manifest = read(author['editorial']['manifest'])
        decisions = manifest['scenes'][a['id']]['consumed_decisions']; decisions['attention'] = deepcopy(a['attention'])
        decisions.pop('candidate_reading_policy', None)
        if 'candidate_reading_policy' in a:
            decisions['candidate_reading_policy'] = a['candidate_reading_policy']
        write(author['editorial']['manifest'], manifest); author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
        mirror = plan['editorial_consumption']['rows'][2]
        mirror.update(attention=deepcopy(p['attention_events']), candidate_reading_policy=p.get('candidate_reading_policy', 'visible'))
        self.save_author_plan(folder, author, plan)

    def mutate_plan(self, edit):
        author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
        edit(plan); self.save_author_plan(self.child, author, plan)

    def make_part(self, folder, index, start, end):
        original = self.parent; self.parent = folder
        try:
            fixtures.NativePartsReuseTests.make_part(self, index, start, end)
        finally:
            self.parent = original

    def set_template_snapshot(self, folder, content):
        snapshot = read(folder / 'NATIVE_SOURCES.json'); path = folder / snapshot['template']['path']
        path.write_bytes(content); digest = sha256(path)
        snapshot['template']['sha256'] = digest; write(folder / 'NATIVE_SOURCES.json', snapshot)
        native = read(folder / 'native-identity.json'); native['template_sha256'] = digest
        write(folder / 'native-identity.json', native)
        for receipt in (folder / 'native-master-parts').glob('part-*.json'):
            row = read(receipt); row['native_identity_sha256'] = sha256(folder / 'native-identity.json')
            write(receipt, row)

    def test_exact_canonical_lf_snapshots_can_reuse_and_resume_unchanged_native_parts(self):
        lf = self.template.replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(lf).hexdigest(), reuse.SOURCE_ATTENTION_TEMPLATE_LF_SHA256)
        for folder in (self.parent, self.child):
            self.set_template_snapshot(folder, lf)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['reused_frames'], 144)
        for receipt in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(receipt)
            self.assertEqual(reuse.validate_reused_part(self.child, row, row['path'])['status'],
                             'VERIFIED_PARENT_NATIVE_BYTES')

    def test_two_approved_representations_still_cannot_differ_between_parent_and_child(self):
        self.set_template_snapshot(self.child, self.template.replace(b'\r\n', b'\n'))
        with self.assertRaises(ValueError):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())

    def test_canonical_lf_allowlist_does_not_normalize_or_accept_unknown_variants(self):
        lf = self.template.replace(b'\r\n', b'\n')
        for variant in (lf + b'\n', lf.replace(b'\n', b'\r\n', 1),
                        lf.replace(b'ink=[.09,.13,.16]', b'ink=[.10,.13,.16]')):
            with self.subTest(digest=hashlib.sha256(variant).hexdigest()):
                for folder in (self.parent, self.child):
                    self.set_template_snapshot(folder, variant)
                with self.assertRaisesRegex(ValueError, 'Unknown native source-attention template'):
                    reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())

    def test_real_cue_anchor_change_excludes_whole_dynamic_scene_and_preserves_origin(self):
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['operation'], reuse.ATTENTION_OPERATION)
        self.assertEqual(report['affected_frame_ranges'], [{'scene': 'COMPARE_Y', 'start': 72, 'end': 120,
                                                          'repairs': ['source_attention_anchor_cue_rebind']}])
        self.assertEqual(report['reused_frames'], 144)
        self.assertEqual([(r['start'], r['end']) for r in report['excluded_parts']], [(48, 96), (96, 144)])
        self.assertEqual(report['source_attention_repairs'][0]['new_effective_frame'], 84)
        self.assertEqual(report['excluded_native_layers'], ['EXTRACT_COMPARE_Y_toy-source-0', 'SOURCE_LIFT_COMPARE_Y'])
        self.assertIn('KEYS_NOT_OBSERVED', report['source_text_readback'])
        self.assertFalse(report['new_native_render']); self.assertFalse(report['human_approved'])
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); checked = reuse.validate_reused_part(self.child, row, row['path'])
            self.assertEqual(checked['status'], 'VERIFIED_PARENT_NATIVE_BYTES')
            self.assertEqual(row['rendered_in_revision'], self.parent.name)
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent, self.child), report)

    def test_visibility_can_be_only_repair_and_requires_actual_bounded_candidate(self):
        self.change_scene(self.child, lambda s: s['attention'][0].update(anchor='These'), time=4)
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['source_attention_repairs'], [])
        self.assertEqual(report['excluded_native_layers'], ['CANDIDATE_FLIGHT_COMPARE_Y'])
        self.assertEqual(report['candidate_reading_visibility_repairs'][0]['scene'], 'COMPARE_Y')

    def test_combined_repairs_keep_independent_footprints(self):
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['affected_frame_ranges'][0]['repairs'],
                         ['source_attention_anchor_cue_rebind', 'quiet_candidate_during_source_reading'])
        self.assertEqual(len(report['excluded_native_layers']), 3)

    def test_policy_cannot_change_to_an_unknown_value_or_reverse_an_existing_quiet_policy(self):
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='hide_all_candidates'))
        with self.assertRaisesRegex(ValueError, 'visible-to-quiet'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        self.change_scene(self.parent, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='visible'))
        with self.assertRaisesRegex(ValueError, 'visible-to-quiet'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_quiet_policy_requires_compare_and_actual_reading_events(self):
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        for kind, readings in [('replay', True), ('compare', False)]:
            for folder in (self.parent, self.child):
                author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
                author['scenes'][2]['kind'] = plan['scenes'][2]['kind'] = kind
                if not readings:
                    author['scenes'][2]['reading_events'] = plan['scenes'][2]['reading_events'] = []
                self.save_author_plan(folder, author, plan)
            with self.subTest(kind=kind, readings=readings), self.assertRaisesRegex(ValueError, 'visible-to-quiet'):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_policy_manifest_must_consume_the_actual_visibility_decision(self):
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
        manifest = read(author['editorial']['manifest'])
        manifest['scenes']['COMPARE_Y']['consumed_decisions'].pop('candidate_reading_policy')
        write(author['editorial']['manifest'], manifest)
        author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
        self.save_author_plan(self.child, author, plan)
        with self.assertRaisesRegex(ValueError, 'must consume the repaired candidate reading policy'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_policy_candidate_cannot_leak_outside_the_changed_scene(self):
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        for folder in (self.parent, self.child):
            audit = read(folder / 'native-audit.json'); audit['layers'][3]['outPoint'] = 5.25
            write(folder / 'native-audit.json', audit)
        with self.assertRaisesRegex(ValueError, 'visibility escapes its scene lifetime'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_phrase_target_and_candidate_anchor_cannot_change_even_if_fully_rebound(self):
        original = {self.child / name: (self.child / name).read_bytes() for name in (
            'AV_AUTHOR.json', 'AV_PLAN.json', 'EPISODE_SCRIPT.md', 'EDITORIAL_MANIFEST.json', 'native-identity.json')}
        for edit in [lambda s: s['attention'][0].update(phrase='cheaper'),
                     lambda s: s['attention'][0].update(target='candidate'),
                     lambda s: s['attention'][2].update(anchor='Same')]:
            with self.subTest(edit=edit):
                for path, content in original.items():
                    path.write_bytes(content)
                self.change_scene(self.child, edit)
                with self.assertRaisesRegex(ValueError, 'Only a source attention anchor'):
                    reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_changed_anchor_must_have_a_real_cue_and_a_different_effective_frame(self):
        for anchor, time in [('missing words', 3.5), ('These point', 4), ('Name', 3.75), ('Name', float('nan'))]:
            with self.subTest(anchor=anchor, time=time):
                with self.assertRaises(ValueError):
                    self.change_scene(self.child, lambda s: s['attention'][0].update(anchor=anchor), time=time)
                    reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_source_collision_cannot_remain_after_anchor_repair(self):
        # A new real anchor may be distinct as text yet compile to a time already
        # used by another source event. This must not certify a repaired shot.
        self.change_scene(self.child, lambda s: s['attention'][1].update(anchor='Name it.'))
        self.mutate_plan(lambda p: p['scenes'][2]['attention_events'][1].update(time=3.5))
        self.mutate_plan(lambda p: p['editorial_consumption']['rows'][2].update(attention=deepcopy(p['scenes'][2]['attention_events'])))
        with self.assertRaisesRegex(ValueError, 'Coincident source attention'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_reading_terminal_timing_layout_or_unknown_plan_fields_fail(self):
        original = read(self.child / 'AV_PLAN.json')
        for edit in [lambda p: p['scenes'][2]['reading_events'][0].update(arrival=3.6),
                     lambda p: p['scenes'][2].update(candidate='D'),
                     lambda p: p['scenes'][2].update(end=5.25),
                     lambda p: p['layout'].update(column=1500),
                     lambda p: p['cues'][0].update(start=3.6),
                     lambda p: p['editorial_consumption']['rows'][2]['candidate_states_after'].update(A='supported'),
                     lambda p: p.update(unreviewed_global_render_flag=True)]:
            with self.subTest(edit=edit):
                write(self.child / 'AV_PLAN.json', original); self.mutate_plan(edit)
                with self.assertRaises(ValueError):
                    reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_missing_or_stale_editorial_attention_and_policy_mirrors_fail(self):
        for edit in [lambda p: p['editorial_consumption']['rows'][2]['attention'][0].update(time=4),
                     lambda p: p['editorial_consumption']['rows'][2].update(candidate_reading_policy='quiet_source_until_read')]:
            with self.subTest(edit=edit):
                original = read(self.child / 'AV_PLAN.json'); self.mutate_plan(edit)
                with self.assertRaisesRegex(ValueError, 'editorial mirror'):
                    reuse.reuse_unchanged_parts(self.parent, self.child)
                write(self.child / 'AV_PLAN.json', original); self.mutate_plan(lambda p: None)

    def test_unaffected_native_font_camera_and_affected_geometry_must_match(self):
        original = read(self.child / 'native-audit.json')
        for edit in [lambda a: a['layers'][0].update(font='ChangedFont'),
                     lambda a: a['layers'][1]['position'][1][1].__setitem__(0, 8),
                     lambda a: a['layers'][2].update(outPoint=5.25),
                     lambda a: a['reading_camera_and_focus']['keys'][0].update(aperture=65)]:
            with self.subTest(edit=edit):
                audit = deepcopy(original); edit(audit); write(self.child / 'native-audit.json', audit)
                with self.assertRaises(ValueError):
                    reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_unknown_template_or_changed_rig_cannot_expand_hidden_key_proof(self):
        for folder in (self.parent, self.child):
            source = folder / 'native-source/authored-episode.jsx'
            source.write_bytes(source.read_bytes() + b'// unknown new common consumer\r\n')
            manifest = read(folder / 'NATIVE_SOURCES.json'); manifest['template']['sha256'] = sha256(source)
            write(folder / 'NATIVE_SOURCES.json', manifest)
            native = read(folder / 'native-identity.json'); native['template_sha256'] = sha256(source)
            write(folder / 'native-identity.json', native)
        with self.assertRaisesRegex(ValueError, 'Unknown native source-attention template'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_identical_template_with_changed_reading_rig_fails(self):
        fixtures.NativePartsReuseTests.change_snapshot(self, 'reading_rig', b'SYNTHETIC changed reading rig')
        with self.assertRaisesRegex(ValueError, 'Changed reading rig'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_only_declared_alignment_path_can_change_and_semantic_cues_must_match(self):
        self.change_scene(self.child, lambda s: None)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['reused_frames'], 144)
        author = read(self.child / 'AV_AUTHOR.json'); path = Path(author['alignment_source'])
        measured = read(path); measured['clips'][0]['cues'][0]['start'] = .1; write(path, measured)
        author['input_files'][str(path)] = sha256(path)
        self.save_author_plan(self.child, author, read(self.child / 'AV_PLAN.json'))
        with self.assertRaisesRegex(ValueError, 'Alignment source changed'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_new_author_decisions_or_additional_input_cannot_hide_in_hash_envelope(self):
        author = read(self.child / 'AV_AUTHOR.json'); plan = read(self.child / 'AV_PLAN.json')
        extra = self.root / 'other.txt'; extra.write_bytes(b'SYNTHETIC unrelated new input')
        author['input_files'][str(extra)] = sha256(extra)
        self.save_author_plan(self.child, author, plan)
        with self.assertRaisesRegex(ValueError, 'Author differs'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_changed_host_decision_is_not_hidden_by_an_identical_plan(self):
        author = read(self.child / 'AV_AUTHOR.json'); plan = read(self.child / 'AV_PLAN.json')
        author['host'] = {'render_backend': 'different_unreviewed_backend'}
        self.save_author_plan(self.child, author, plan)
        with self.assertRaisesRegex(ValueError, 'Author differs'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_full_parent_required_and_files_sorted_by_frame_start(self):
        directory = self.parent / 'native-master-parts'
        (directory / 'part-0000.json').rename(directory / 'part-0999.json')
        (directory / 'part-0000.mp4').rename(directory / 'part-0999.mp4')
        row = read(directory / 'part-0999.json'); row['path'] = str(directory / 'part-0999.mp4')
        write(directory / 'part-0999.json', row)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual([p['start'] for p in report['reused_parts']], [0, 144, 192])

    def test_parent_gap_or_unreceipted_native_bytes_fail(self):
        directory = self.parent / 'native-master-parts'
        (directory / 'part-0002.json').unlink()
        with self.assertRaisesRegex(ValueError, 'lacks a completed receipt'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        (directory / 'part-0002.mp4').unlink()
        with self.assertRaisesRegex(ValueError, 'gap-free'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def make_nested_parent(self):
        grand = self.root / 'original-render'
        old_template = self.template.replace(reuse.LIGHT_NEW, reuse.LIGHT_OLD).replace(reuse.TITLE_NEW, reuse.TITLE_OLD)
        self.make_revision(grand, 17, 'These', template=old_template)
        for index in range(5):
            self.make_part(grand, index, index * 48, (index + 1) * 48)
        # Only temporary synthetic fixture files are removed. The middle revision
        # genuinely retains completed original renders for its affected parts.
        for index in (0, 3, 4):
            for suffix in ('.json', '.mp4'):
                (self.parent / 'native-master-parts' / f'part-{index:04}{suffix}').unlink()
        report = reuse.reuse_unchanged_parts(grand, self.parent)
        self.assertEqual(report['reused_frames'], 144)
        return grand

    def test_nested_template_reuse_is_reproved_and_original_renderer_is_retained(self):
        grand = self.make_nested_parent()
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['reused_frames'], 144)
        self.assertTrue(all(len(item['reuse_chain']) == 1 for item in report['reused_parts']))
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); checked = reuse.validate_reused_part(self.child, row, row['path'])
            self.assertEqual(row['rendered_in_revision'], grand.name)
            self.assertEqual(len(checked['provenance_chain']), 2)
            self.assertTrue(Path(row['path']).is_relative_to(grand))
            self.assertFalse(row['new_native_render'])

    def test_nested_receipt_cannot_claim_it_was_rendered_in_intermediate_revision(self):
        self.make_nested_parent()
        path = self.parent / 'native-master-parts/part-0000.json'
        row = read(path); row['rendered_in_revision'] = self.parent.name; write(path, row)
        with self.assertRaisesRegex(ValueError, 'exceeds its unchanged parent'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_rehashed_nested_proof_cannot_forge_the_original_media(self):
        self.make_nested_parent()
        path = self.parent / reuse.PROOF; proof = read(path)
        proof['reused_parts'][0]['media'] = proof['reused_parts'][-1]['media']; write(path, proof)
        for receipt in (self.parent / 'native-master-parts').glob('part-*.json'):
            row = read(receipt)
            if 'reuse' in row:
                row['reuse']['proof_sha256'] = sha256(path); write(receipt, row)
        with self.assertRaisesRegex(ValueError, 'parent media or observation changed'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_nested_resume_rechecks_original_leaf_bytes_and_every_proof(self):
        grand = self.make_nested_parent(); reuse.reuse_unchanged_parts(self.parent, self.child)
        row = read(self.child / 'native-master-parts/part-0000.json')
        (grand / 'native-master-parts/part-0000.mp4').write_bytes(b'CHANGED ORIGINAL LEAF')
        with self.assertRaises(ValueError):
            reuse.validate_reused_part(self.child, row, row['path'])


if __name__ == '__main__':
    unittest.main()
