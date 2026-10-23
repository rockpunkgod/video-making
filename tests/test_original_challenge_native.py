"""Synthetic readback contracts only; no mock is a claim of actual Adobe execution."""
from copy import deepcopy
import math
import unittest
from pathlib import Path
import tempfile
import json
import shutil
import subprocess

from ae_production.challenge_original import (POLICY, original_challenge_scope,
    NEUTRAL_TEXT_EFFECT_VALUES, original_challenge_readback_code,
    original_challenge_readback, validate_original_challenges)
from video_contracts import read, sha
from ae_production.authored_native import expected_camera_events


class OriginalChallengeNative(unittest.TestCase):
    def setUp(self):
        self.p = {'world_order': ['one', 'two'], 'worlds': {}, 'audience_challenges': {'rows': []}}
        self.n = {'comp_id': 1, 'master_comp_id': 2, 'audit': {'sources': [], 'audience_challenges': []}}
        for wi, world in enumerate(self.p['world_order']):
            base = wi*10000; sid = 'SC01' if wi == 0 else 'SC09'; start = wi*10
            q = {'question_id': world+'-Q1', 'passage': 'First words.\nNext phrase.',
                 'stem': 'What is the task?', 'options': {c: c+' complete original claim.' for c in 'ABCD'}}
            blocks = [
                {'id': world+'-source-0', 'start': 0, 'end': 12, 'text': 'First words.', 'visible': True,
                 'reading_chunks': [{'id': world+':0:5', 'start': 0, 'end': 5, 'text': 'First'},
                                    {'id': world+':6:12', 'start': 6, 'end': 12, 'text': 'words.'}]},
                {'id': world+'-source-12', 'start': 12, 'end': 13, 'text': '\n', 'visible': False, 'reading_chunks': []},
                {'id': world+'-source-13', 'start': 13, 'end': 25, 'text': 'Next phrase.', 'visible': True,
                 'reading_chunks': [{'id': world+':13:25', 'start': 13, 'end': 25, 'text': 'Next phrase.'}]}]
            self.p['worlds'][world] = {'question': q, 'source': {'bundle': world+'-frozen.json'}, 'blocks': blocks}
            challenge = {'scene': sid, 'world': world, 'question_id': q['question_id'], 'start': start,
                         'end': start+3, 'handoff_end': start+3.8, 'start_frame': start*24, 'end_frame': start*24+72}
            self.p['audience_challenges']['rows'].append(challenge)
            native = {'scene_id': sid, 'world': world, 'question_id': q['question_id'],
                      'start': start, 'end': start+3, 'handoff_end': start+3.8, 'frames': 72,
                      'article_layers': [], 'article_chunks': [], 'article_width': 170, 'article_height': 21,
                      'source_identity': POLICY}
            native['original_glyphs'] = [{'name': world+suffix, 'source_layer_id': 300+base+index,
                'exact_text': text} for index, (suffix, text) in enumerate(
                    [('_QUESTION', q['stem'])]+[('_OPTION_'+c, c+'   '+q['options'][c]) for c in 'ABCD'])]
            for bi, block in enumerate(b for b in blocks if b['visible']):
                layer_id = 100+wi*10+bi; pos = [base+2250, 40+bi*100, 100]
                self.n['audit']['sources'].append({'id': block['id'], 'layer_id': layer_id,
                    'text': block['text'], 'position': pos})
                native['article_layers'].append(block['id'])
                for chunk in block['reading_chunks']:
                    native['article_chunks'].append({**deepcopy(chunk), 'chunk_id': chunk['id'],
                        'source_layer': block['id'], 'source_layer_id': layer_id,
                        'animator': 'CHALLENGE_FOLD_'+sid+'_'+str(len(native['article_chunks'])),
                        'range': [chunk['start']-block['start'], chunk['end']-block['start']],
                        'delta': [50, 40, 0], 'source_position': pos, 'challenge_position': [base+40, 132, 0],
                        'scale': 1700/46, 'baseline': [base+40+len(native['article_chunks'])*60, 149, 0], 'width': 50})
            self.n['audit']['audience_challenges'].append(native)
        self.rows = self.model_rows()

    def model_rows(self):
        result = []
        for cid in [1, 2]:
            for s in original_challenge_scope(self.p, self.n):
                article = []; chunks = []; glyphs = []; base = s['base']
                for source in s['sources']:
                    article.append({'name': source['name'], 'id': source['proxy_id']+(1000 if cid == 2 else 0),
                        'text': source['text'], 'comment': {'kind': 'original_passage', 'field': 'passage',
                            'source': source['source'], 'start': source['start'], 'end': source['end'], 'exact_text': source['text']},
                        'font_size': 46, 'original_font_size': 46, 'enabled': True, 'guide': False, 'three_d': True, 'in_point': 0,
                        'out_point': 30, 'neutral': 1,
                        'source_text_events': [{'time': s['start'], 'text': source['text'], 'neutral': 1, 'font_size': 46}],
                        'text_expression': '',
                        'fold_names': [c['animator'] for c in s['chunks'] if c['source_layer'] == source['name']]})
                for chunk in s['chunks']:
                    source = next(a for a in article if a['name'] == chunk['source_layer'])
                    chunks.append({'name': chunk['animator'], 'source_id': source['id'], 'range': chunk['range'],
                        'enabled': True, 'units': 2, 'smoothness': 0, 'delta': chunk['delta'], 'expression_error': '',
                        'selector_count': 1, 'property_names': ['ADBE Text Position 3D']})
                for gi, name in enumerate(s['glyph_names']):
                    glyphs.append({'name': name, 'id': 200+cid*100+s['base']+gi, 'text': s['glyph_texts'][gi],
                        'enabled': True, 'guide': False, 'three_d': True, 'in_point': 0, 'out_point': 30, 'neutral': 1,
                        'source_text_events': [{'time': s['start'], 'text': s['glyph_texts'][gi], 'neutral': 1,
                                                'font_size': 50 if gi == 0 else 46}], 'text_expression': ''})
                def article_state(source, progress=0):
                    begin = [base+40, 132, 0]+[1700/46]*3; end = source['position']+[100]*3
                    return [a+(b-a)*progress for a, b in zip(begin, end)]+[100, 1, 0]
                def glyph_state(index, progress=0):
                    begin = [base+(830 if index else 820), 300+(index-1)*58 if index else 192, s['question_plane_z']]+[38]*3
                    end = [base+(90 if index else 80), 230+(index-1)*80 if index else 95, 0]+[100]*3
                    return [a+(b-a)*progress for a, b in zip(begin, end)]+[100, 1, 0]
                samples = [{'frame': f, 'article': [article_state(a) for a in s['sources']],
                    'glyphs': [glyph_state(i) for i in range(5)], 'chunks': [100]*len(chunks),
                    'camera': [base+640, 320, -1550, base+640, 320, 0, 0], 'badge_opacity': 100}
                    for f in range(s['start_frame'], s['end_frame'])]
                times = [s['end']+i/24 for i in range(math.ceil(.8*24))]+[s['handoff_end']]
                handoff = []
                for time in times:
                    progress = (time-s['end'])/.8
                    handoff.append({'time': time, 'article': [article_state(a, progress) for a in s['sources']],
                        'glyphs': [glyph_state(i, progress) for i in range(5)], 'chunks': [100*(1-progress)]*len(chunks)})
                result.append({'comp_id': cid, 'scene': s['scene'], 'article_layers': article, 'chunks': chunks,
                    'glyphs': glyphs, 'samples': samples, 'handoff': handoff, 'extra_challenge_passage_layers': [],
                    'badge': {'text': '想先自己做？可暂停', 'spoken': False, 'enabled': True, 'guide': False,
                              'in_point': s['start'], 'out_point': s['end']}})
        return result

    def validate(self): return validate_original_challenges(self.p, self.n, self.rows)

    def test_model_contract_pass_is_explicitly_not_native_execution_or_perception(self):
        result = self.validate()
        self.assertEqual(result['source_identity'], POLICY)
        self.assertEqual(result['normal_speed_review'], 'UNOBSERVED')
        self.assertEqual(result['mobile_legibility'], 'UNOBSERVED')
        self.assertEqual(result['listening_review'], 'UNOBSERVED')

    def test_separate_question_plane_preserves_all_glyphs_and_continuous_return(self):
        for row in self.n['audit']['audience_challenges']:
            row['question_plane_z'] = -3
        self.rows = self.model_rows()
        self.validate()
        self.rows[0]['samples'][0]['glyphs'][0][2] = 0
        with self.assertRaisesRegex(ValueError, 'stem/options'):
            self.validate()
        self.n['audit']['audience_challenges'][0]['question_plane_z'] = -30
        with self.assertRaisesRegex(ValueError, 'question depth'):
            self.model_rows()

    def test_both_compositions_and_each_question_are_required(self):
        self.rows.pop()
        with self.assertRaisesRegex(ValueError, 'both native compositions'): self.validate()

    def test_all_72_frames_required_not_boundary_only(self):
        self.rows[0]['samples'].pop(35)
        with self.assertRaisesRegex(ValueError, '72 frame times'): self.validate()

    def test_disabled_original_fold_cannot_pass_by_reporting_amount_100(self):
        self.assertTrue(all(sample['chunks'][0] == 100 for sample in self.rows[0]['samples']))
        self.rows[0]['chunks'][0]['enabled'] = False
        with self.assertRaisesRegex(ValueError, 'sense-group selector'): self.validate()

    def test_missing_fold_enabled_state_does_not_reuse_a_legacy_pass(self):
        self.rows[0]['chunks'][0].pop('enabled')
        with self.assertRaisesRegex(ValueError, 'sense-group selector'): self.validate()

    def test_native_reader_samples_the_real_fold_animator_enabled_flag(self):
        code = original_challenge_readback_code(self.p, self.n)
        self.assertIn('enabled:an.enabled', code)

    def test_missing_middle_chunk_cannot_hide_in_self_declared_build_manifest(self):
        self.n['audit']['audience_challenges'][0]['article_chunks'].pop(1)
        with self.assertRaisesRegex(ValueError, 'every original layer and sense group'): self.validate()

    def test_plan_missing_article_words_is_independently_rejected(self):
        self.p['worlds']['one']['blocks'][0]['reading_chunks'].pop(1)
        with self.assertRaisesRegex(ValueError, 'omit words'): self.validate()

    def test_recreated_article_layer_is_forbidden(self):
        self.rows[0]['extra_challenge_passage_layers'] = ['CHALLENGE_PASSAGE_SC01']
        with self.assertRaisesRegex(ValueError, 'duplicate passage'): self.validate()

    def test_each_original_proxy_id_and_separate_master_id_are_checked(self):
        self.rows[0]['article_layers'][0]['id'] += 100
        with self.assertRaisesRegex(ValueError, 'proxy original'): self.validate()

    def test_changed_master_source_link_does_not_borrow_proxy_identity(self):
        self.rows[2]['chunks'][0]['source_id'] = self.rows[0]['article_layers'][0]['id']
        with self.assertRaisesRegex(ValueError, 'sense-group selector'): self.validate()

    def test_master_cannot_report_proxy_ids_or_replace_question_glyph_id(self):
        self.rows[2]['article_layers'][0]['id'] = self.rows[0]['article_layers'][0]['id']
        with self.assertRaisesRegex(ValueError, 'own real native layer IDs'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['glyphs'][1]['id'] += 1000
        with self.assertRaisesRegex(ValueError, 'question proxy identity'): self.validate()

    def test_source_text_and_source_comment_must_remain_exact(self):
        self.rows[0]['article_layers'][0]['comment']['exact_text'] = 'Rewritten.'
        with self.assertRaisesRegex(ValueError, 'Actual original article text'): self.validate()

    def test_hidden_original_or_wrong_compact_scale_during_any_frame_rejected(self):
        self.rows[0]['samples'][38]['article'][0][3] = 100
        with self.assertRaisesRegex(ValueError, 'article is hidden'): self.validate()

    def test_all_chunk_amounts_must_be_100_during_window(self):
        self.rows[1]['samples'][24]['chunks'][1] = 0
        with self.assertRaisesRegex(ValueError, 'every sense group'): self.validate()

    def test_bad_selector_range_units_smoothness_or_extra_properties_rejected(self):
        for key, value in [('range', [0, 1]), ('units', 1), ('smoothness', 100),
                           ('property_names', ['ADBE Text Fill Color']), ('selector_count', 2)]:
            with self.subTest(key=key):
                original = deepcopy(self.rows); self.rows[0]['chunks'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'sense-group selector'): self.validate()
                self.rows = original

    def test_extra_fold_animator_cannot_move_unbound_words(self):
        self.rows[0]['article_layers'][0]['fold_names'].append('CHALLENGE_FOLD_SC01_extra')
        with self.assertRaisesRegex(ValueError, 'Actual original article'): self.validate()

    def test_question_no_answer_highlight_or_nonfold_emphasis(self):
        self.rows[0]['samples'][10]['glyphs'][3][8] = 100
        with self.assertRaisesRegex(ValueError, 'judgement-emphasized'): self.validate()

    def test_base_ink_color_and_fixed_camera_aperture_are_checked(self):
        self.rows[0]['samples'][20]['article'][0][7] = 0
        with self.assertRaisesRegex(ValueError, 'judgement-emphasized'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['samples'][20]['camera'][-1] = 14
        with self.assertRaisesRegex(ValueError, 'neutral fixed camera'): self.validate()

    def test_keyed_base_color_or_source_text_expression_cannot_hide_between_frames(self):
        self.rows[0]['article_layers'][0]['source_text_events'].append(
            {'time': 1.01, 'text': 'First words.', 'neutral': 0, 'font_size': 46})
        with self.assertRaisesRegex(ValueError, 'base text or color changes'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['glyphs'][1]['text_expression'] = 'invented answer'
        with self.assertRaisesRegex(ValueError, 'base text or color changes'): self.validate()

    def test_fractional_source_text_event_boundary_allows_json_float_noise_only(self):
        event = self.rows[1]['article_layers'][0]['source_text_events'][0]
        event['time'] -= 1e-12
        self.validate()
        event['time'] -= 1/24
        with self.assertRaisesRegex(ValueError, 'base text or color changes'): self.validate()

    def test_complete_options_and_screen_only_badge_are_required(self):
        self.rows[0]['glyphs'][4]['text'] = 'D'
        with self.assertRaisesRegex(ValueError, 'all four options'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['badge']['spoken'] = True
        with self.assertRaisesRegex(ValueError, 'screen-only'): self.validate()

    def test_handoff_cannot_disappear_or_pop_back_at_end(self):
        self.rows[0]['handoff'][5]['article'][0][6] = 0
        with self.assertRaisesRegex(ValueError, 'cannot disappear'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['handoff'][1]['article'][0][0] = 2250
        with self.assertRaisesRegex(ValueError, 'jumps, reverses'): self.validate()

    def test_deliberate_fast_depth_leg_is_continuous_without_relaxing_lateral_motion(self):
        # Actual 55%-influence 0.12s Bezier depth samples from the observed R02
        # readback. This fixture checks that timing contract, not Adobe itself.
        depth = [0, 20.5026302961963, 85.0281691574579]
        for row in self.rows:
            for index, sample in enumerate(row['handoff']):
                z = depth[index] if index < len(depth) else 100
                for state in sample['article']: state[2] = z
        self.validate()
        self.rows[0]['handoff'][1]['article'][0][2] = 100
        with self.assertRaisesRegex(ValueError, 'jumps, reverses'): self.validate()
        self.rows[0]['handoff'][1]['article'][0][2] = depth[1]
        self.rows[0]['handoff'][1]['article'][0][0] = 2250
        with self.assertRaisesRegex(ValueError, 'jumps, reverses'): self.validate()

    def test_fast_depth_leg_still_rejects_reversal_overshoot_and_disappearance(self):
        for depth in ([-1, 85], [20, 101], [85, 20]):
            original = deepcopy(self.rows)
            self.rows[0]['handoff'][1]['article'][0][2] = depth[0]
            self.rows[0]['handoff'][2]['article'][0][2] = depth[1]
            with self.assertRaisesRegex(ValueError, 'jumps, reverses'): self.validate()
            self.rows = original

    def test_every_chunk_must_return_to_zero_and_every_original_to_native_pose(self):
        self.rows[0]['handoff'][-1]['chunks'][1] = 1
        with self.assertRaisesRegex(ValueError, 'fully return'): self.validate()
        self.rows = self.model_rows(); self.rows[0]['handoff'][-1]['article'][0][0] -= .1
        with self.assertRaisesRegex(ValueError, 'returned article'): self.validate()

    def test_native_layout_overflow_and_nonfinite_values_rejected(self):
        self.n['audit']['audience_challenges'][0]['article_width'] = 761
        with self.assertRaisesRegex(ValueError, 'overflows'): self.validate()

    def test_source_whitespace_cannot_collapse_to_joined_sense_groups(self):
        chunks = self.n['audit']['audience_challenges'][0]['article_chunks']
        chunks[1]['baseline'][0] = chunks[0]['baseline'][0]+chunks[0]['width']
        with self.assertRaisesRegex(ValueError, 'visible whitespace'): self.validate()

    def test_layout_size_claim_cannot_understate_actual_fold_bounds(self):
        self.n['audit']['audience_challenges'][0]['article_width'] = 100
        with self.assertRaisesRegex(ValueError, 'overflows'): self.validate()

    def test_available_challenge_baseline_stays_above_caption_boundary(self):
        built = self.n['audit']['audience_challenges'][0]
        built['article_chunks'][-1]['baseline'][1] = 604
        built['article_height'] = 476
        self.validate()
        built['article_chunks'][-1]['baseline'][1] = 605
        built['article_height'] = 477
        with self.assertRaisesRegex(ValueError, 'layout changed'): self.validate()

    def test_challenge_camera_replaces_only_interior_original_keys(self):
        def event(time, aperture=14): return {'time': time, 'aperture': aperture, 'target': [1, 2, 3]}
        before = event(.5); start = event(1); original_interior = event(2)
        old_end = event(4); old_late = event(4.5); land = event(4.8); after = event(5)
        new_end = event(4, 0)
        audit = {'camera': [before, start, original_interior, old_end, old_late, land, after, new_end],
                 'audience_challenges': [{'start': 1, 'end': 4, 'handoff_end': 4.8}]}
        expected = expected_camera_events(audit)
        self.assertEqual(list(expected), [.5, 1, 4.8, 5, 4])
        self.assertIs(expected[4], new_end)
        self.assertNotIn(2, expected); self.assertNotIn(4.5, expected)
        self.assertIs(expected[1], start); self.assertIs(expected[4.8], land)

    def test_removed_or_unrelated_extra_native_camera_key_remains_unbound(self):
        audit = {'camera': [{'time': 1, 'aperture': 14}, {'time': 2, 'aperture': 14},
                            {'time': 4, 'aperture': 0}, {'time': 4.8, 'aperture': 14}],
                 'audience_challenges': [{'start': 1, 'end': 4, 'handoff_end': 4.8}]}
        expected = expected_camera_events(audit)
        # The production audit requires one remaining expected match for every
        # real native key. Filtering the old history grants neither extra key.
        for unexpected in (2, 8):
            self.assertFalse(any(abs(e['time']-unexpected)<.0001 for e in expected.values()))
        self.n['audit']['audience_challenges'][0]['article_width'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'overflows'): self.validate()

    def test_compact_scale_uses_actual_preserved_source_font_not_a_fixed_font_assumption(self):
        source = self.n['audit']['audience_challenges'][0]['article_layers'][0]
        for chunk in self.n['audit']['audience_challenges'][0]['article_chunks']:
            if chunk['source_layer'] == source: chunk['scale'] = 1700/40
        for row in self.rows:
            if row['scene'] != 'SC01': continue
            original = row['article_layers'][0]
            original['font_size'] = original['original_font_size'] = 40
            original['source_text_events'][0]['font_size'] = 40
            for sample in row['samples']: sample['article'][0][3:6] = [1700/40]*3
            for sample in row['handoff']:
                progress = (sample['time']-3)/.8
                sample['article'][0][3:6] = [1700/40+(100-1700/40)*progress]*3
        self.validate()
        self.rows[0]['samples'][20]['article'][0][3] = 1700/46
        with self.assertRaisesRegex(ValueError, 'article is hidden'): self.validate()

    def test_raw_evidence_is_preserved_before_failed_validation_without_retry(self):
        observed = deepcopy(self.rows); observed[0]['chunks'][0]['units'] = 1
        with tempfile.TemporaryDirectory() as directory:
            class SyntheticHost:
                folder = Path(directory)
                calls = 0
                def js(self, code):
                    self.calls += 1
                    return observed
            host = SyntheticHost()
            with self.assertRaisesRegex(ValueError, 'sense-group selector'):
                original_challenge_readback(host, self.p, self.n)
            packet = read(Path(directory)/'ORIGINAL_CHALLENGE_NATIVE_RAW.json')
            self.assertEqual(packet['rows'], observed)
            self.assertEqual(packet['plan_content_sha'], sha(self.p))
            self.assertEqual(packet['kind'], 'RAW_NATIVE_ORIGINAL_CHALLENGE_NOT_YET_VALIDATED')
            self.assertEqual(host.calls, 1)

    def test_raw_only_mode_does_not_promote_unvalidated_observations(self):
        observed = deepcopy(self.rows); observed[0]['chunks'][0]['delta'] = [999, 999, 0]
        class SyntheticHost:
            def js(self, code): return observed
        packet = original_challenge_readback(SyntheticHost(), self.p, self.n, raw_only=True)
        self.assertNotIn('status', packet)
        self.assertEqual(packet['normal_speed_review'], 'UNOBSERVED')

    @unittest.skipUnless(shutil.which('node'), 'JavaScript runtime unavailable; this is not an Adobe substitute')
    def test_actual_reader_js_distinguishes_default_100_selector_from_effective_emphasis(self):
        code = original_challenge_readback_code(self.p, self.n)
        helper = code[code.index('function neutralEffect('):code.index('\nfunction active(')]
        cases = [
            ['ADBE Text Scale 3D', [100, 100, 100], '', True],
            ['ADBE Text Scale 3D', [104, 104, 100], '', False],
            ['ADBE Text Fill Color', [.09, .13, .16, 1], '', True],
            ['ADBE Text Fill Color', [.10, .37, .57, 1], '', False],
            ['ADBE Text Opacity', 100, '', True], ['ADBE Text Opacity', 0, '', False],
            ['Unknown modified effect', 0, '', False],
            ['ADBE Text Scale 3D', [100, 100, 100], 'Actual expression failure', False]]
        script = 'var neutralEffects='+json.dumps(NEUTRAL_TEXT_EFFECT_VALUES)+';'+helper+'\n'
        script += 'var cases='+json.dumps(cases)+';var out=cases.map(function(c){return neutralEffect({matchName:c[0],expressionError:c[2],valueAtTime:function(){return c[1];}},1);});process.stdout.write(JSON.stringify(out));'
        run = subprocess.run([shutil.which('node'), '-e', script], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout), [case[-1] for case in cases])


if __name__ == '__main__': unittest.main()
