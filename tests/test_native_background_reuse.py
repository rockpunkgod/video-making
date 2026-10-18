"""Exact display-repair counterfactuals using temporary synthetic native data.

No Adobe, real AEP, media decoding or production receipt is opened. Only the
existing ffprobe boundary is mocked; template bytes and all bound hashes are
real. The fixture retains the old authored-repair proof tests unchanged.
"""
from copy import deepcopy
import hashlib
import json
import unittest

from ae_production import native_parts_reuse as reuse
from scripts.voice_delivery import sha256
from tests import test_native_attention_reuse as attention_fixtures
from video_contracts import read, write


class NativeBackgroundReuseTests(unittest.TestCase):
    make_revision = attention_fixtures.AuthoredRepairReuseTests.make_revision
    save_author_plan = attention_fixtures.AuthoredRepairReuseTests.save_author_plan
    change_scene = attention_fixtures.AuthoredRepairReuseTests.change_scene
    make_part = attention_fixtures.AuthoredRepairReuseTests.make_part
    set_template_snapshot = attention_fixtures.AuthoredRepairReuseTests.set_template_snapshot
    mutate_plan = attention_fixtures.AuthoredRepairReuseTests.mutate_plan

    def setUp(self):
        attention_fixtures.AuthoredRepairReuseTests.setUp(self)
        # Start from equal spoken anchors, then change display decisions only.
        self.change_scene(self.child, lambda s: s['attention'][0].update(anchor='These'), time=4)
        for folder in (self.parent, self.child):
            self.change_scene(folder, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene.update(screen_title='Relation', extract_start=4.4, settled=4.5, return_start=4.8)
                scene['reading_events'][0].update(end_time=4.25, end=len(plan['worlds']['toy']['question']['passage']))
            blocks = plan['worlds']['toy']['blocks']
            end = blocks[0]['end']
            blocks.append({'id': 'toy-source-other', 'start': end + 1, 'end': end + 15,
                           'text': 'Other context.', 'visible': True})
            plan['worlds']['toy']['question']['passage'] += '\nOther context.'
            self.save_author_plan(folder, author, plan)
            audit = read(folder / 'native-audit.json')
            audit['layers'][0]['threeD'] = True
            audit['layers'][1].update(inPoint=4.4, position=[[4.4, [0, 0, 0]], [4.5, [1, 0, 0]]])
            audit['layers'][2]['inPoint'] = 4.4
            audit['layers'].append({'id': audit['layers'][-1]['id'] + 1, 'name': 'toy-source-other',
                                   'parent': None, 'threeD': True, 'text': 'Other context.',
                                   'font': 'ArialMT', 'inPoint': 0, 'outPoint': 10})
            write(folder / 'native-audit.json', audit)
            self.sync_native_count(folder)
        self.display(self.child, screen_title='', comparison_background_policy='isolate_selected_passage')
        audit = read(self.child / 'native-audit.json')
        audit['layers'] = [r for r in audit['layers'] if r['name'] != 'TASK_TITLE_COMPARE_Y']
        write(self.child / 'native-audit.json', audit); self.sync_native_count(self.child)
        self.set_template_snapshot(self.child, self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW))
        self.bind_parent_parts()
        self.write_readbacks()
        self.child_state = {p: p.read_bytes() for p in self.child.rglob('*') if p.is_file()}

    def sync_native_count(self, folder):
        native = read(folder / 'native-identity.json'); audit = read(folder / 'native-audit.json')
        native['layers'] = len(audit['layers'])
        native['audit'] = {'sources': [{'layer_id': audit['layers'][0]['id'], 'text': audit['layers'][0]['text']}],
                           'camera': [{'time': 0, 'position': [0, 0, -1500]}]}
        write(folder / 'native-identity.json', native)

    def bind_parent_parts(self):
        for path in (self.parent / 'native-master-parts').glob('part-*.json'):
            row = read(path)
            row.update(plan_sha256=sha256(self.parent / 'AV_PLAN.json'),
                       native_identity_sha256=sha256(self.parent / 'native-identity.json'))
            write(path, row)

    def display(self, folder, **decisions):
        author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
        author['scenes'][2].update(decisions); plan['scenes'][2].update(decisions)
        manifest = read(author['editorial']['manifest'])
        manifest['scenes']['COMPARE_Y']['consumed_decisions'].update(decisions)
        write(author['editorial']['manifest'], manifest)
        author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
        plan['editorial_consumption']['rows'][2].update(decisions)
        self.save_author_plan(folder, author, plan)

    def write_readbacks(self, folder=None):
        folder = folder or self.child
        native = read(folder / 'native-identity.json')
        for cid in (native['comp_id'], native['master_comp_id']):
            write(folder / f'COMPARISON_BACKGROUND_NATIVE_{cid}.json', {
                'rows': [{'scene': 'COMPARE_Y', 'hidden': [{'layer': 'toy-source-other',
                    'before': 100, 'quiet': 0, 'settled': 0, 'restore_start': 0, 'restored': 100}],
                    'reading': [{'layer': 'toy-source-0', 'time': 3.875, 'opacity': 100}]}],
                'plan_sha256': native['plan_sha256'], 'human_visual_review': 'PENDING'})

    def reset_child(self):
        for path in self.child.rglob('*'):
            if path.is_file() and path not in self.child_state:
                path.unlink()
        for path, content in self.child_state.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)

    def add_caption_readbacks(self):
        for folder in (self.parent, self.child):
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            audit = read(folder / 'native-audit.json'); rows = []
            first = max(l['id'] for l in audit['layers']) + 20
            for i, cue in enumerate(plan['cues']):
                cue.update(id='take_' + str(i), segment='take', display_lines=[cue['text']])
                # Real AE JSON may round 2.1550000000000002 to 2.155.
                start, end = float(format(cue['start'], '.15g')), float(format(cue['end'], '.15g'))
                audit['layers'].append({'id': first + i, 'name': 'CAPTION_' + cue['id'],
                    'threeD': False, 'parent': None, 'text': cue['text'], 'font': 'MicrosoftYaHei',
                    'inPoint': start, 'outPoint': end,
                    'comment': json.dumps({'kind': 'audio_aligned_exact_caption', 'segment': 'take',
                                          'text': cue['text'], 'start': start, 'end': end})})
                rows.append({'id': first + i, 'text': cue['text'], 'start': start, 'end': end})
            self.save_author_plan(folder, author, plan); write(folder / 'native-audit.json', audit)
            self.sync_native_count(folder)
            native = read(folder / 'native-identity.json'); native['audit']['captions'] = rows
            write(folder / 'native-identity.json', native)
        self.bind_parent_parts(); self.write_readbacks()

    def background_only_scene(self, kind='compare', policy='visible'):
        """Same reviewed template, existing candidate visibility left intact."""
        for folder in (self.parent, self.child):
            self.display(folder, screen_title='')
            def visibility(scene):
                if policy is None:
                    scene.pop('candidate_reading_policy', None)
                else:
                    scene['candidate_reading_policy'] = policy
            self.change_scene(folder, visibility)
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene['kind'] = kind
                if kind == 'replay':
                    scene.update(event=None, replay_of='CHECK_X')
            self.save_author_plan(folder, author, plan)
            audit = read(folder / 'native-audit.json')
            audit['layers'] = [l for l in audit['layers'] if l['name'] != 'TASK_TITLE_COMPARE_Y']
            if kind == 'replay':
                for layer in audit['layers']:
                    if layer['name'] == 'CANDIDATE_FLIGHT_COMPARE_Y':
                        layer['name'] = 'REPLAY_CANDIDATE_COMPARE_Y'
            write(folder / 'native-audit.json', audit); self.sync_native_count(folder)
            if kind == 'replay':
                native = read(folder / 'native-identity.json')
                native['audit'].update(candidates=[], replays=[{
                    'scene': 'COMPARE_Y', 'replay_of': 'CHECK_X', 'no_new_candidate_event': True}])
                write(folder / 'native-identity.json', native)
            self.set_template_snapshot(folder, self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW))
        self.bind_parent_parts(); self.write_readbacks()

    def locate_title_only(self):
        for folder in (self.parent, self.child):
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene.update(kind='locate', locator={'identity': 'Alpha', 'stem_span': [0, 5],
                                                   'passage_span': [0, 5], 'block_span': [0, 45]})
                scene.pop('motion_treatment', None); scene.pop('candidate_reading_policy', None)
                scene.pop('comparison_background_policy', None)
            manifest = read(author['editorial']['manifest'])
            decisions = manifest['scenes']['COMPARE_Y']['consumed_decisions']
            decisions.pop('candidate_reading_policy', None); decisions.pop('comparison_background_policy', None)
            write(author['editorial']['manifest'], manifest)
            author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
            mirror = plan['editorial_consumption']['rows'][2]
            mirror.update(candidate_reading_policy='visible'); mirror.pop('comparison_background_policy', None)
            self.save_author_plan(folder, author, plan)
            audit = read(folder / 'native-audit.json')
            for layer in audit['layers']:
                if layer['name'] == 'TASK_TITLE_COMPARE_Y':
                    layer['outPoint'] = 5
            ident = max(l['id'] for l in audit['layers']) + 50
            audit['layers'].append({'name': 'CARRIED_QUERY_COMPARE_Y', 'id': ident,
                'parent': None, 'threeD': True, 'inPoint': 3.1, 'outPoint': 5,
                'text': 'Alpha', 'font': 'ArialMT',
                'position': [[3.1, [0, 0, 0]], [4.8, [1, 2, 3]]],
                'comment': json.dumps({'kind': 'query_from_original_stem', 'span': [0, 5],
                                       'exact_text': 'Alpha', 'origin': [0, 0, 0]})})
            write(folder / 'native-audit.json', audit); self.sync_native_count(folder)
            native = read(folder / 'native-identity.json')
            native['audit']['query_carries'] = [{'scene': 'COMPARE_Y', 'layer_id': ident,
                                                'origin': [0, 0, 0], 'start': 3.1, 'end': 5}]
            write(folder / 'native-identity.json', native)
            self.set_template_snapshot(folder, self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW))
        self.bind_parent_parts()

    def replay_title_only(self):
        self.background_only_scene(kind='replay', policy='visible')
        # The parent and child already share background isolation; the sole
        # new decision removes the existing replay title, as in R08 -> R09.
        self.display(self.parent, screen_title='Relation', comparison_background_policy='isolate_selected_passage')
        audit = read(self.parent / 'native-audit.json')
        audit['layers'].append({'id': max(l['id'] for l in audit['layers']) + 1,
            'name': 'TASK_TITLE_COMPARE_Y', 'parent': None, 'threeD': False,
            'text': 'Relation', 'font': 'MicrosoftYaHei', 'inPoint': 3, 'outPoint': 3.25})
        write(self.parent / 'native-audit.json', audit)
        native = read(self.parent / 'native-identity.json'); native['layers'] = len(audit['layers'])
        write(self.parent / 'native-identity.json', native)
        self.bind_parent_parts(); self.write_readbacks(self.parent)

    def test_exact_display_patch_reuses_only_disjoint_bytes_and_preserves_renderer(self):
        self.assertEqual(hashlib.sha256(self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW)).hexdigest(),
                         reuse.BACKGROUND_TEMPLATE_SHA256)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['operation'], reuse.DISPLAY_OPERATION)
        self.assertEqual(report['reused_frames'], 144)
        self.assertEqual(report['removed_native_layers'], ['TASK_TITLE_COMPARE_Y'])
        self.assertEqual(report['affected_frame_ranges'], [{'scene': 'COMPARE_Y', 'start': 71, 'end': 121,
            'repairs': ['hide_comparison_screen_title', 'isolate_nonselected_comparison_background']}])
        self.assertEqual(len(report['background_isolation_readbacks']['child']), 2)
        self.assertEqual(report['background_isolation_scope'][0]['hidden'], ['toy-source-other'])
        self.assertFalse(report['human_approved']); self.assertFalse(report['new_native_render'])
        self.assertFalse(report['public_render_ready'])
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path)
            self.assertEqual(row['rendered_in_revision'], self.parent.name)
            self.assertEqual(reuse.validate_reused_part(self.child, row, row['path'])['status'],
                             'VERIFIED_PARENT_NATIVE_BYTES')
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent, self.child), report)
        self.assertEqual(list((self.child / 'native-master-parts').glob('*.mp4')), [])

    def test_title_deletion_may_renumber_only_exact_bound_caption_layer_ids(self):
        self.add_caption_readbacks()
        parent = read(self.parent / 'native-identity.json')['audit']['captions']
        child = read(self.child / 'native-identity.json')['audit']['captions']
        self.assertNotEqual(parent[0]['id'], child[0]['id'])
        old, new, context = reuse._context(self.parent, self.child)
        self.assertEqual(reuse._display_build_observations(old), reuse._display_build_observations(new))
        self.assertEqual(context['removed_native_layers'], ['TASK_TITLE_COMPARE_Y'])
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent, self.child)['reused_frames'], 144)

    def test_caption_id_cannot_point_to_a_different_layer_or_change_text_or_clock(self):
        self.add_caption_readbacks()
        path = self.child / 'native-identity.json'; original = path.read_bytes()
        for edit in [lambda n: n['audit']['captions'][0].update(id=n['audit']['captions'][1]['id']),
                     lambda n: n['audit']['captions'][0].update(id=999999),
                     lambda n: n['audit']['captions'][0].update(text='Changed subtitle'),
                     lambda n: n['audit']['captions'][0].update(start=3.51),
                     lambda n: n['audit']['captions'].pop()]:
            path.write_bytes(original); native = read(path); edit(native); write(path, native)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_unrelated_build_id_fields_still_compare_exactly(self):
        self.add_caption_readbacks()
        for folder in (self.parent, self.child):
            path = folder / 'native-identity.json'; native = read(path)
            native['audit']['unrecognized_id_record'] = {'id': 400 if folder == self.parent else 401}
            write(path, native)
        self.bind_parent_parts()
        with self.assertRaisesRegex(ValueError, 'build layout'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_exact_lf_pair_is_allowed_but_not_a_cross_eol_pair(self):
        old = self.template.replace(b'\r\n', b'\n')
        new = old.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW)
        self.assertEqual(hashlib.sha256(new).hexdigest(), reuse.BACKGROUND_TEMPLATE_LF_SHA256)
        self.set_template_snapshot(self.child, new)
        with self.assertRaisesRegex(ValueError, 'exact approved background template'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        self.set_template_snapshot(self.parent, old)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['reused_frames'], 144)

    def test_unknown_common_or_extra_template_changes_are_rejected(self):
        patched = self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW)
        for variant in (patched + b'\r\n', patched.replace(b'b-.35', b'b-.5'),
                        patched.replace(b'ink=[.09,.13,.16]', b'ink=[.10,.13,.16]')):
            self.reset_child(); self.set_template_snapshot(self.child, variant)
            with self.subTest(digest=hashlib.sha256(variant).hexdigest()), self.assertRaisesRegex(ValueError, 'exact approved'):
                reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertFalse((self.child / reuse.PROOF).exists())

    def test_display_repair_on_same_reviewed_patched_template_is_bounded(self):
        self.set_template_snapshot(self.parent, self.template.replace(reuse.BACKGROUND_OLD, reuse.BACKGROUND_NEW))
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['template_repairs'], [])
        self.assertEqual(report['reused_frames'], 144)

    def test_background_repair_preserves_existing_visible_candidate_without_adding_quiet_policy(self):
        self.background_only_scene()
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['template_repairs'], [])
        self.assertEqual(report['removed_native_layers'], [])
        self.assertEqual([r['field'] for r in report['display_repairs']], ['comparison_background_policy'])
        for folder in (self.parent, self.child):
            self.assertEqual(read(folder / 'AV_AUTHOR.json')['scenes'][2]['candidate_reading_policy'], 'visible')
        self.assertEqual(report['reused_frames'], 144)

    def test_replay_background_repair_keeps_default_candidate_visibility_and_no_new_event(self):
        self.background_only_scene(kind='replay', policy=None)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['template_repairs'], [])
        self.assertEqual(report['affected_frame_ranges'], [{'scene': 'COMPARE_Y', 'start': 71, 'end': 121,
            'repairs': ['isolate_nonselected_comparison_background']}])
        for folder in (self.parent, self.child):
            scene = read(folder / 'AV_PLAN.json')['scenes'][2]
            self.assertNotIn('candidate_reading_policy', scene)
            self.assertIsNone(scene['event'])
            self.assertEqual(read(folder / 'native-identity.json')['audit']['candidates'], [])
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); reuse.validate_reused_part(self.child, row, row['path'])

    def test_explicit_visible_replay_is_valid_but_quiet_policy_cannot_change_during_background_repair(self):
        self.background_only_scene(kind='replay', policy='visible')
        _, _, report = reuse._context(self.parent, self.child)
        self.assertEqual(len(report['display_repairs']), 1)
        self.change_scene(self.child, lambda s: s.update(candidate_reading_policy='quiet_source_until_read'))
        with self.assertRaisesRegex(ValueError, 'Plans differ beyond'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_replay_background_repair_cannot_acquire_a_new_candidate_event(self):
        self.background_only_scene(kind='replay', policy='visible')
        author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
        author['scenes'][2]['event'] = plan['scenes'][2]['event'] = 'supported'
        manifest = read(author['editorial']['manifest'])
        manifest['scenes']['COMPARE_Y']['consumed_decisions']['event'] = 'supported'
        write(author['editorial']['manifest'], manifest); author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
        self.save_author_plan(self.child, author, plan)
        native = read(self.child / 'native-identity.json')
        native['audit']['candidates'].append({'scene': 'COMPARE_Y', 'kind': 'supported'})
        write(self.child / 'native-identity.json', native); self.write_readbacks()
        with self.assertRaisesRegex(ValueError, 'Plans differ beyond'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_replay_still_refuses_to_hide_its_last_necessary_source_reading(self):
        self.background_only_scene(kind='replay', policy='visible')
        for folder in (self.parent, self.child):
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene['reading_events'][0]['end'] = plan['worlds']['toy']['blocks'][1]['end']
            self.save_author_plan(folder, author, plan)
        self.bind_parent_parts(); self.write_readbacks()
        with self.assertRaisesRegex(ValueError, 'hide necessary reading'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_locate_title_deletion_uses_full_scene_lifetime_and_preserves_query_carry(self):
        self.locate_title_only()
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['template_repairs'], [])
        self.assertEqual(report['removed_native_layers'], ['TASK_TITLE_COMPARE_Y'])
        self.assertEqual(report['background_isolation_scope'], [])
        self.assertEqual(report['affected_frame_ranges'], [{'scene': 'COMPARE_Y', 'start': 71, 'end': 121,
            'repairs': ['hide_locate_screen_title']}])
        old, new, _ = reuse._context(self.parent, self.child)
        self.assertEqual(old['layers']['CARRIED_QUERY_COMPARE_Y'], new['layers']['CARRIED_QUERY_COMPARE_Y'])
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); reuse.validate_reused_part(self.child, row, row['path'])

    def test_locate_title_cannot_claim_the_comparison_first_read_depart_outpoint(self):
        self.locate_title_only()
        path = self.parent / 'native-audit.json'; audit = read(path)
        next(l for l in audit['layers'] if l['name'] == 'TASK_TITLE_COMPARE_Y')['outPoint'] = 3.25
        write(path, audit)
        with self.assertRaisesRegex(ValueError, 'actual bounded authored native title'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_locate_title_repair_cannot_change_query_reading_camera_or_carry_observations(self):
        self.locate_title_only()
        paths = [self.child / name for name in ('AV_AUTHOR.json', 'AV_PLAN.json', 'EPISODE_SCRIPT.md',
                                               'native-identity.json', 'native-audit.json')]
        original = {p: p.read_bytes() for p in paths}
        for edit in [lambda a, p: p['scenes'][2]['locator'].update(identity='Beta'),
                     lambda a, p: p['scenes'][2]['reading_events'][0].update(end_time=4.125),
                     lambda a, p: p['scenes'][2].update(return_start=4.7)]:
            for path, content in original.items():
                path.write_bytes(content)
            author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
            edit(author, plan); self.save_author_plan(self.child, author, plan)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)
        for edit in [lambda a: next(l for l in a['layers'] if l['name'] == 'CARRIED_QUERY_COMPARE_Y').update(text='Beta'),
                     lambda a: next(l for l in a['layers'] if l['name'] == 'CARRIED_QUERY_COMPARE_Y').update(outPoint=5.25),
                     lambda a: next(l for l in a['layers'] if l['name'] == 'CARRIED_QUERY_COMPARE_Y')['position'][0][1].__setitem__(0, 9),
                     lambda a: a['reading_camera_and_focus']['keys'][0].update(aperture=65)]:
            for path, content in original.items():
                path.write_bytes(content)
            audit = read(self.child / 'native-audit.json'); edit(audit); write(self.child / 'native-audit.json', audit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)
        for path, content in original.items():
            path.write_bytes(content)
        native = read(self.child / 'native-identity.json'); native['audit']['query_carries'][0]['origin'][0] = 9
        write(self.child / 'native-identity.json', native)
        with self.assertRaisesRegex(ValueError, 'build layout'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_replay_title_only_repair_preserves_first_depart_lifetime_and_existing_isolation(self):
        self.replay_title_only()
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['template_repairs'], [])
        self.assertEqual(report['removed_native_layers'], ['TASK_TITLE_COMPARE_Y'])
        self.assertEqual([r['field'] for r in report['display_repairs']], ['screen_title'])
        self.assertEqual(report['affected_frame_ranges'], [{'scene': 'COMPARE_Y', 'start': 71, 'end': 121,
            'repairs': ['hide_comparison_screen_title']}])
        self.assertEqual(len(report['background_isolation_readbacks']['parent']), 2)
        self.assertEqual(len(report['background_isolation_readbacks']['child']), 2)
        self.assertEqual(read(self.child / 'AV_PLAN.json')['scenes'][2]['kind'], 'replay')
        self.assertEqual(read(self.child / 'native-identity.json')['audit']['candidates'], [])
        for path in (self.child / 'native-master-parts').glob('part-*.json'):
            row = read(path); reuse.validate_reused_part(self.child, row, row['path'])

    def test_replay_title_cannot_use_locate_full_scene_outpoint(self):
        self.replay_title_only()
        path = self.parent / 'native-audit.json'; audit = read(path)
        next(l for l in audit['layers'] if l['name'] == 'TASK_TITLE_COMPARE_Y')['outPoint'] = 5
        write(path, audit)
        with self.assertRaisesRegex(ValueError, 'actual bounded authored native title'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_replay_title_only_repair_rejects_kind_decision_cue_phase_and_clock_drift(self):
        self.replay_title_only()
        original = {p: p.read_bytes() for p in self.child.rglob('*') if p.is_file()}
        def scene_fields(author, plan, **values):
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene.update(values)
        edits = [lambda a, p: scene_fields(a, p, kind='compare'),
                 lambda a, p: scene_fields(a, p, event='supported'),
                 lambda a, p: scene_fields(a, p, replay_of='ANOTHER_COMPARISON'),
                 lambda a, p: scene_fields(a, p, extract_start=4.3),
                 lambda a, p: scene_fields(a, p, settled=4.6),
                 lambda a, p: scene_fields(a, p, return_start=4.7),
                 lambda a, p: scene_fields(a, p, end=5.125),
                 lambda a, p: p['cues'][0].update(start=3.6),
                 lambda a, p: p['segments'][0].update(voice_start=3.6)]
        for edit in edits:
            for path, content in original.items():
                path.write_bytes(content)
            author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
            edit(author, plan); self.save_author_plan(self.child, author, plan); self.write_readbacks()
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_background_repair_still_refuses_unknown_candidate_visibility_or_noncomparison(self):
        self.background_only_scene(policy='unknown_hidden_candidate')
        with self.assertRaisesRegex(ValueError, 'visible-to-isolate'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        for folder in (self.parent, self.child):
            self.change_scene(folder, lambda s: s.update(candidate_reading_policy='visible'))
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            author['scenes'][2]['kind'] = plan['scenes'][2]['kind'] = 'task'
            self.save_author_plan(folder, author, plan)
        self.bind_parent_parts(); self.write_readbacks()
        with self.assertRaisesRegex(ValueError, 'extracted candidate comparisons'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_background_policy_cannot_be_claimed_without_the_actual_consumer(self):
        self.set_template_snapshot(self.child, self.template)
        with self.assertRaisesRegex(ValueError, 'exact approved native consumer'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_title_only_repair_preserves_old_consumer_without_background_receipts(self):
        self.reset_child()
        author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
        author['scenes'][2].pop('comparison_background_policy')
        plan['scenes'][2].pop('comparison_background_policy')
        plan['editorial_consumption']['rows'][2].pop('comparison_background_policy')
        manifest = read(author['editorial']['manifest'])
        manifest['scenes']['COMPARE_Y']['consumed_decisions'].pop('comparison_background_policy')
        write(author['editorial']['manifest'], manifest); author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
        self.save_author_plan(self.child, author, plan); self.set_template_snapshot(self.child, self.template)
        for path in self.child.glob('COMPARISON_BACKGROUND_NATIVE_*.json'):
            path.unlink()
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual(report['background_isolation_scope'], [])
        self.assertEqual(report['display_repairs'][0]['field'], 'screen_title')

    def test_other_fully_bound_plan_changes_cannot_hide_inside_display_repair(self):
        edits = [lambda p: p['scenes'][2].update(end=5.125),
                 lambda p: p['scenes'][2]['reading_events'][0].update(end_time=4.125),
                 lambda p: p['scenes'][2]['attention_events'][0].update(time=3.75),
                 lambda p: p['layout'].update(column=1500),
                 lambda p: p['worlds']['toy']['blocks'][0].update(text='Different source.'),
                 lambda p: p['segments'][0].update(voice_start=3.75),
                 lambda p: p['cues'][0].update(start=3.75),
                 lambda p: p.update(unknown_pixel_decision=True)]
        for edit in edits:
            self.reset_child(); self.mutate_plan(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_author_source_host_and_complete_copy_changes_are_not_hash_only_exceptions(self):
        for edit in [lambda a: a.update(host={'backend': 'unreviewed'}),
                     lambda a: a['voices'][0].update(text='Changed actual spoken copy.'),
                     lambda a: a['scenes'][2]['attention'][0].update(phrase='cheaper')]:
            self.reset_child()
            author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
            edit(author); self.save_author_plan(self.child, author, plan)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_changed_fields_need_exact_plan_author_and_new_editorial_mirrors(self):
        for edit in [lambda p: p['editorial_consumption']['rows'][2].pop('screen_title'),
                     lambda p: p['editorial_consumption']['rows'][2].pop('comparison_background_policy'),
                     lambda p: p['editorial_consumption']['rows'][2].update(screen_title='Relation'),
                     lambda p: p['scenes'][2].update(screen_title='Different title')]:
            self.reset_child(); self.mutate_plan(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_new_manifest_must_explicitly_consume_each_repaired_field(self):
        for key in ('screen_title', 'comparison_background_policy'):
            self.reset_child()
            author, plan = read(self.child / 'AV_AUTHOR.json'), read(self.child / 'AV_PLAN.json')
            manifest = read(author['editorial']['manifest']); manifest['scenes']['COMPARE_Y']['consumed_decisions'].pop(key)
            write(author['editorial']['manifest'], manifest); author['editorial']['sha256'] = sha256(author['editorial']['manifest'])
            self.save_author_plan(self.child, author, plan)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'manifest must consume'):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_old_explicit_visible_and_correct_title_mirrors_remain_compatible(self):
        self.display(self.parent, screen_title='Relation', comparison_background_policy='visible')
        self.bind_parent_parts()
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent, self.child)['reused_frames'], 144)

    def test_title_rewording_unknown_or_reverse_background_policy_is_rejected(self):
        for decision in ({'screen_title': 'New wording'}, {'comparison_background_policy': 'hide_all'},
                         {'comparison_background_policy': 'visible'}):
            self.reset_child(); self.display(self.child, **decision)
            # The last case leaves a spurious changed policy mirror on an
            # unchanged field; it cannot become a permitted metadata delta.
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_unaffected_native_text_geometry_lifetime_camera_and_build_audit_must_match(self):
        for edit in [lambda a: a['layers'][0].update(font='DifferentFont'),
                     lambda a: a['layers'][1]['position'][1][1].__setitem__(0, 8),
                     lambda a: a['layers'][2].update(outPoint=5.25),
                     lambda a: a['reading_camera_and_focus']['keys'][0].update(aperture=65)]:
            self.reset_child(); audit = read(self.child / 'native-audit.json'); edit(audit)
            write(self.child / 'native-audit.json', audit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)
        self.reset_child()
        native = read(self.child / 'native-identity.json'); native['audit']['camera'][0]['position'][0] = 90
        write(self.child / 'native-identity.json', native)
        with self.assertRaisesRegex(ValueError, 'build layout'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_removed_layer_must_be_exact_title_with_its_actual_text_and_lifetime(self):
        for folder, edit in [(self.child, lambda a: a['layers'].pop()),
                             (self.parent, lambda a: a['layers'][4].update(text='Some unrelated layer')),
                             (self.parent, lambda a: a['layers'][4].update(outPoint=5.25))]:
            # First mutation drops a different child layer; the other two
            # mutations alter the historical title observation in the parent.
            self.reset_child()
            original = (folder / 'native-audit.json').read_bytes()
            audit = read(folder / 'native-audit.json'); edit(audit); write(folder / 'native-audit.json', audit)
            try:
                with self.assertRaises(ValueError):
                    reuse.reuse_unchanged_parts(self.parent, self.child)
            finally:
                (folder / 'native-audit.json').write_bytes(original)

    def test_proxy_and_master_readbacks_are_required_and_cannot_change_plan_or_scope(self):
        cid = read(self.child / 'native-identity.json')['master_comp_id']
        path = self.child / f'COMPARISON_BACKGROUND_NATIVE_{cid}.json'
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'readback is missing'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        for edit in [lambda r: r.update(plan_sha256='0' * 64),
                     lambda r: r['rows'][0].update(scene='ANOTHER_SCENE'),
                     lambda r: r['rows'].append(deepcopy(r['rows'][0])),
                     lambda r: r.update(human_visual_review='APPROVED'),
                     lambda r: r['rows'][0]['hidden'][0].update(layer='toy-source-0')]:
            self.reset_child(); receipt = read(path); edit(receipt); write(path, receipt)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_actual_opacity_reading_samples_must_be_complete_finite_and_correct(self):
        cid = read(self.child / 'native-identity.json')['comp_id']
        path = self.child / f'COMPARISON_BACKGROUND_NATIVE_{cid}.json'
        for edit in [lambda r: r['rows'][0]['hidden'][0].update(quiet=6),
                     lambda r: r['rows'][0]['hidden'][0].update(restored=0),
                     lambda r: r['rows'][0]['hidden'][0].update(before=float('nan')),
                     lambda r: r['rows'][0]['reading'].clear(),
                     lambda r: r['rows'][0]['reading'][0].update(opacity=0),
                     lambda r: r['rows'][0]['reading'][0].update(time=4.25)]:
            self.reset_child(); receipt = read(path); edit(receipt)
            # Deliberately bypass the production writer's NaN prohibition to
            # exercise validation of an externally tampered receipt as bytes.
            path.write_text(json.dumps(receipt), encoding='utf-8')
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_required_last_reading_cannot_be_hidden_even_with_forged_pass_samples(self):
        for folder in (self.parent, self.child):
            author, plan = read(folder / 'AV_AUTHOR.json'), read(folder / 'AV_PLAN.json')
            end = plan['worlds']['toy']['blocks'][1]['end']
            for scene in (author['scenes'][2], plan['scenes'][2]):
                scene['reading_events'][0]['end'] = end
            self.save_author_plan(folder, author, plan)
        self.bind_parent_parts(); self.write_readbacks()
        with self.assertRaisesRegex(ValueError, 'hide necessary reading'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_whole_scene_and_one_frame_neighbors_are_excluded_dynamically(self):
        for path in (self.parent / 'native-master-parts').glob('part-*'):
            path.unlink()
        intervals = [(0, 71), (71, 72), (72, 120), (120, 121), (121, 240)]
        for i, (start, end) in enumerate(intervals):
            self.make_part(self.parent, i, start, end)
        report = reuse.reuse_unchanged_parts(self.parent, self.child)
        self.assertEqual([(r['start'], r['end']) for r in report['reused_parts']], [(0, 71), (121, 240)])
        self.assertEqual([(r['start'], r['end']) for r in report['excluded_parts']], intervals[1:4])

    def test_complete_parent_receipts_and_nested_provenance_remain_required(self):
        receipt = self.parent / 'native-master-parts/part-0000.json'
        original = receipt.read_bytes(); row = read(receipt)
        row.update(new_native_render=False, reuse={'schema': reuse.SCHEMA})
        write(receipt, row)
        with self.assertRaisesRegex(ValueError, 'Explicit local'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        receipt.write_bytes(original); receipt.unlink()
        with self.assertRaisesRegex(ValueError, 'lacks a completed receipt'):
            reuse.reuse_unchanged_parts(self.parent, self.child)
        receipt.with_suffix('.mp4').unlink()
        with self.assertRaisesRegex(ValueError, 'gap-free'):
            reuse.reuse_unchanged_parts(self.parent, self.child)

    def test_resume_rechecks_opacity_receipts_and_keeps_mutable_child_aep_separate(self):
        reuse.reuse_unchanged_parts(self.parent, self.child)
        row = read(self.child / 'native-master-parts/part-0000.json')
        (self.child / 'media/MAIN_FILM.aep').write_bytes(b'SYNTHETIC legitimate later save')
        reuse.validate_reused_part(self.child, row, row['path'])
        cid = read(self.child / 'native-identity.json')['comp_id']
        path = self.child / f'COMPARISON_BACKGROUND_NATIVE_{cid}.json'
        receipt = read(path); receipt['rows'][0]['hidden'][0]['quiet'] = .001; write(path, receipt)
        with self.assertRaises(ValueError):
            reuse.validate_reused_part(self.child, row, row['path'])


if __name__ == '__main__':
    unittest.main()
