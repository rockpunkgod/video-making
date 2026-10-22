"""Recipe execution contracts; these tests do not certify motion or English meaning."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from creative_os.motion_identity import (SYMBOL_VERSION, compile_symbols,
    symbol_registry, validate_authored_symbols, validate_compiled_symbols)
from scripts.voice_delivery import sha256
from video_contracts import sha, write


class CognitiveSymbolRecipes(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.folder = self.base / 'production'; self.folder.mkdir()
        request = self.base / 'user.txt'
        request.write_text('VIDEO_EXPERIENCE_UPGRADE_V1 用户决定的两种有源视觉表达。', encoding='utf-8')
        self.request = request
        passage = 'The Atlas is cheaper than\nOrion and Vega. They take part in feedback workshops.'
        q = {'question_id': 'synthetic-Q1', 'passage': passage, 'stem': 'Which claim?',
             'options': {'A': 'It is more affordable.', 'B': 'Chair feedback workshops.', 'C': 'Other.', 'D': 'Another.'}}
        evidence = [{'field': 'passage', 'start': 0, 'end': len(passage), 'quote': passage}]
        action = {'execution_id': 'frozen-action', 'review_status': 'reviewed', 'state': 'produced',
                  'stop_applied': False, 'stop_rule_check': 'Check full action and comparator.',
                  'evidence': deepcopy(evidence), 'output': {'kind': 'interpretation', 'parts': [
                      {'name': 'verified comparison and roles', 'value': 'An upstream reviewed interpretation.',
                       'evidence': deepcopy(evidence)}]}}
        checks = [{'candidate': c, 'claim': q['options'][c], 'effect': effect,
                   'evidence': deepcopy(evidence), 'decision_rule_check': 'Bound complete judgement.',
                   'backfill_check': 'Bound original task.'} for c, effect in [('A', 'retain'), ('B', 'eliminate')]]
        terminals = [{'candidate': c, 'effect': effect, 'review_node_id': 'review-' + c}
                     for c, effect in [('A', 'retain'), ('B', 'eliminate')]]
        self.b = {'w': {'source_snapshot': q, 'analysis': {'execution_trace': [action], 'question_verification': {
            'state': 'reviewed', 'candidate_bindings': deepcopy(terminals), 'review': {'review_status': 'reviewed',
            'stop_applied': False, 'input_artifact_ids': ['frozen-action'], 'candidate_checks': checks}}}}}
        action_ref = {'world': 'w', 'pointer': '/execution_trace/0', 'sha': sha(action)}
        self.a = {'format': {'fps': 24}, 'sources': {'w': {'bundle': str(self.base / 'bundle.json')}},
                  'input_files': {str(request): sha256(request)}, 'scenes': []}
        self.clock = {'scenes': []}
        for index, (sid, candidate) in enumerate([('SC03', 'A'), ('SC10', 'B')]):
            scene = {'id': sid, 'kind': 'compare', 'world': 'w', 'candidate': candidate,
                     'event': 'supported' if candidate == 'A' else 'eliminate',
                     'source_refs': [self.ref('/passage', passage), self.ref('/options/' + candidate, q['options'][candidate])],
                     'action_refs': [deepcopy(action_ref)], 'terminal_refs': [deepcopy(terminals[index])]}
            self.a['scenes'].append(scene)
            self.clock['scenes'].append({**deepcopy(scene), 'start': index * 10, 'settled': index * 10 + 2,
                                        'event_time': index * 10 + 7 + 1 / 3, 'return_start': index * 10 + 8, 'end': index * 10 + 9})
        self.worlds = {'w': {'source': deepcopy(self.a['sources']['w']), 'question': deepcopy(q),
                            'blocks': [{'id': 'w-source-0', 'start': 0, 'end': len(passage), 'text': passage, 'visible': True}]}}
        semantic = self.instance('price', 'semantic_isomorphism', 'SC03', [
            ('subject', '/passage', 'Atlas'), ('referent', '/passage', 'Orion and Vega'),
            ('source_relation', '/passage', 'cheaper than'), ('candidate_relation', '/options/A', 'more affordable')], 0)
        roles = self.instance('roles', 'same_form_different_relation', 'SC10', [
            ('source_noun', '/passage', 'workshops'), ('candidate_noun', '/options/B', 'workshops'),
            ('source_action', '/passage', 'take part in'), ('candidate_action', '/options/B', 'Chair')], 1)
        self.a['cognitive_symbols'] = {'contract_version': SYMBOL_VERSION,
            'request_source': {'path': str(request), 'sha256': sha256(request)}, 'instances': [semantic, roles]}
        self.save_bundle()

    def save_bundle(self):
        path = Path(self.a['sources']['w']['bundle']); write(path, self.b['w'])
        self.a['input_files'][str(path)] = sha256(path)

    def ref(self, pointer, quote):
        if pointer == '/passage': text = self.b['w']['source_snapshot']['passage'] if hasattr(self, 'b') else 'The Atlas is cheaper than\nOrion and Vega. They take part in feedback workshops.'
        else:
            options = self.b['w']['source_snapshot']['options'] if hasattr(self, 'b') else {'A': 'It is more affordable.', 'B': 'Chair feedback workshops.'}
            text = options[pointer.split('/')[-1]]
        start = text.index(quote)
        return {'world': 'w', 'pointer': pointer, 'start': start, 'end': start + len(quote), 'quote': quote}

    def instance(self, ident, recipe, sid, inputs, check_index):
        scene = next(s for s in self.a['scenes'] if s['id'] == sid)
        check = self.b['w']['analysis']['question_verification']['review']['candidate_checks'][check_index]
        return {'symbol_id': ident, 'recipe_id': recipe, 'scene_id': sid, 'variant': 'lesson',
            'inputs': [{'object_id': ident + '-' + role, 'role': role, 'source_ref': self.ref(pointer, quote)}
                       for role, pointer, quote in inputs],
            'relation': {'type': 'same_price_relation' if recipe == 'semantic_isomorphism' else 'different_action_role',
                         'dimension': 'price' if recipe == 'semantic_isomorphism' else 'action_role',
                         'action_ref': deepcopy(scene['action_refs'][0]),
                         'verification_ref': {'pointer': '/question_verification/review/candidate_checks/' + str(check_index), 'sha': sha(check)},
                         'terminal_ref': deepcopy(scene['terminal_refs'][0])},
            'parameters': {'duration_seconds': 5, 'space': {'origin': [350, 250, -280], 'depth': -80},
                'font': {'family': 'ArialMT', 'size': 34, 'advance_factor': .58, 'line_height': 1.32},
                'layout': {'width': 1600, 'height': 640, 'min_gap': 24},
                'curve': 'smoothstep', 'mask': 'source_glyphs_only'}}

    def compile(self): return compile_symbols(self.a, self.b, self.clock, self.worlds, self.folder)
    def validate(self): return validate_authored_symbols(self.a, self.b, self.folder)

    def test_authored_phases_leave_stable_relation_recognition(self):
        self.a['cognitive_symbols']['instances'][1]['parameters']['phase_seconds']=[.8,1,.25]
        row=self.compile()['rows'][1]
        self.assertAlmostEqual(row['phases'][0]['end']-row['start'],19/24)
        self.assertAlmostEqual(row['phases'][1]['end']-row['phases'][0]['end'],1)
        self.assertGreater(row['end']-.45-row['phases'][2]['end'],.5)
        self.a['cognitive_symbols']['instances'][1]['parameters']['phase_seconds']=[2,2,1]
        with self.assertRaisesRegex(ValueError,'recognition'):self.compile()

    def test_noun_divergence_retains_shared_origin_and_eighteen_frame_hold(self):
        r=self.a['cognitive_symbols']['instances'][1]
        r['parameters'].update(composition='noun_divergence',surface_hold_frames=18,phase_seconds=[.25,.8,.25])
        self.clock['segments']=[{'scene_id':'SC10','voice_start':15.25,'voice_end':16.25}]
        row=self.compile()['rows'][1];positions=row['layout']['positions']
        inputs={i['role']:i['object_id'] for i in row['inputs']}
        self.assertEqual(positions[inputs['source_noun']],positions[inputs['candidate_noun']])
        self.assertLess(positions[inputs['source_noun']][0],positions[inputs['source_action']][0])
        self.assertNotEqual(positions[inputs['source_action']][1],positions[inputs['candidate_action']][1])
        self.assertAlmostEqual(row['phases'][1]['end']-row['phases'][0]['end'],19/24+18/24)
        self.assertEqual(row['states'][0]['state'],'apparent_identity_hold')
        self.assertEqual(row['states'][0]['frames'],18)
        self.clock['segments'][0]['voice_start']-=.1
        with self.assertRaisesRegex(ValueError,'875ms'):self.compile()

    def test_keyword_alignment_cannot_invent_a_source_term(self):
        r=self.a['cognitive_symbols']['instances'][0]
        r['parameters'].update(composition='keyword_equivalence',keyword_pair={'source_relation':'cheaper','candidate_relation':'affordable'},context_hold_seconds=2)
        self.compile()
        r['parameters']['keyword_pair']['source_relation']='free'
        with self.assertRaisesRegex(ValueError,'exact span'):self.compile()

    def add_hook(self):
        inputs = deepcopy(self.a['cognitive_symbols']['instances'][1]['inputs'][:2])
        anchors = [deepcopy(i['source_ref']) for i in inputs]
        hook = {'scene_id': 'HOOK01', 'visual_conflict': {'anchor_refs': anchors, 'relation_labels': False}}
        self.a['audience_hook'] = hook
        self.clock['audience_hook'] = {'scene_id': 'HOOK01', 'start': 0, 'end': 3, 'decision_sha': sha(hook),
            'phases': {'enter': [0, .5], 'surface_align': [.5, 1], 'relation_displace': [1, 1.5],
                       'unresolved_hold': [1.5, 2.5], 'match_into_task': [2.5, 3]}}
        instance = {'symbol_id': 'hook', 'recipe_id': 'same_form_different_relation', 'scene_id': 'HOOK01',
                    'variant': 'hook', 'inputs': inputs,
                    'relation': {'type': 'anonymous_relation_conflict', 'dimension': 'unresolved',
                                 'action_ref': None, 'verification_ref': None, 'terminal_ref': None},
                    'parameters': deepcopy(self.a['cognitive_symbols']['instances'][1]['parameters'])}
        instance['parameters']['duration_seconds'] = 3
        self.a['cognitive_symbols']['instances'].append(instance)
        return instance

    def test_legacy_missing_field_keeps_old_inputs_inert(self):
        self.assertIsNone(validate_authored_symbols({}, {}))
        self.assertIsNone(compile_symbols({}, {}, {}))
        self.assertIsNone(validate_compiled_symbols(None, {}, {}, {}))

    def test_registry_exposes_two_visual_only_native_recipes(self):
        catalog, recipes = symbol_registry()
        self.assertEqual(set(recipes), {'semantic_isomorphism', 'same_form_different_relation'})
        self.assertFalse(catalog['public_render_ready'])

    def test_compilation_binds_actual_source_ranges_and_frozen_judgements(self):
        before = deepcopy((self.a, self.b, self.clock, self.worlds)); result = self.compile()
        self.assertEqual(before, (self.a, self.b, self.clock, self.worlds))
        self.assertEqual([r['scene_id'] for r in result['rows']], ['SC03', 'SC10'])
        for row in result['rows']:
            self.assertEqual(row['end_frame'] - row['start_frame'], 120)
            self.assertEqual(row['inputs'][0]['source_object_id'], 'w-source-0')
            self.assertEqual(row['authority']['authority'], 'FROZEN_UPSTREAM_INTERPRETATION_AND_WHOLE_QUESTION_REVIEW')
            self.assertGreaterEqual(row['phases'][-1]['end'] - row['phases'][-1]['start'], 1)
        self.assertFalse(result['semantic_certification']); self.assertEqual(result['actual_native_consumption'], 'UNVERIFIED')

    def test_same_noun_exact_overlap_is_semantic_anchor_not_generic_overlap(self):
        row = self.compile()['rows'][1]; ids = [i['object_id'] for i in row['inputs'][:2]]
        self.assertEqual(row['layout']['positions'][ids[0]], row['layout']['positions'][ids[1]])
        self.assertNotEqual(row['layout']['positions'][row['inputs'][2]['object_id']], row['layout']['positions'][row['inputs'][3]['object_id']])

    def test_different_source_positions_and_depth_do_not_change_source_identity(self):
        first = self.compile()['rows'][0]
        p = self.a['cognitive_symbols']['instances'][0]['parameters']; p['space'] = {'origin': [-2000, 900, 120], 'depth': 420}
        changed = self.compile()['rows'][0]
        self.assertEqual(first['inputs'], changed['inputs']); self.assertNotEqual(first['layout']['positions'], changed['layout']['positions'])

    def test_different_durations_bind_existing_clock_without_retiming_takes(self):
        self.clock['scenes'][0]['event_time'] += 1
        self.clock['scenes'][0]['return_start'] += 1; self.clock['scenes'][0]['end'] += 1
        self.a['cognitive_symbols']['instances'][0]['parameters']['duration_seconds'] = 6
        self.assertEqual(self.compile()['rows'][0]['end_frame'] - self.compile()['rows'][0]['start_frame'], 144)
        self.a['cognitive_symbols']['instances'][0]['parameters']['duration_seconds'] = 4
        with self.assertRaisesRegex(ValueError, 'existing clock'): self.compile()

    def test_changed_font_metrics_are_bound_and_unreadable_sizes_rejected(self):
        p = self.a['cognitive_symbols']['instances'][0]['parameters']['font']; p.update(family='DifferentFace', size=42, advance_factor=.8)
        result = self.compile(); self.assertEqual(result['rows'][0]['parameters']['font']['family'], 'DifferentFace')
        p['size'] = 18
        with self.assertRaisesRegex(ValueError, 'font size'): self.compile()

    def test_long_source_text_overflow_refuses_card_or_shrinking_fallback(self):
        inst = self.a['cognitive_symbols']['instances'][0]
        inst['inputs'][2]['source_ref'] = self.ref('/passage', self.b['w']['source_snapshot']['passage'])
        with self.assertRaisesRegex(ValueError, 'exceeds readable layout'): self.compile()

    def test_multiline_source_preserves_original_line_breaks(self):
        inst = self.a['cognitive_symbols']['instances'][0]
        inst['inputs'][2]['source_ref'] = self.ref('/passage', 'cheaper than\nOrion and Vega')
        result = self.compile()['rows'][0]
        source = next(i for i in result['inputs'] if i['role'] == 'source_relation')
        self.assertEqual(source['source_ref']['quote'], 'cheaper than\nOrion and Vega')
        self.assertFalse(result['layout']['text_reflow'])

    def test_invalid_source_stale_action_and_missing_output_are_rejected(self):
        for mutation in ('source', 'action', 'output'):
            with self.subTest(mutation=mutation):
                original = deepcopy((self.a, self.b))
                if mutation == 'source': self.a['cognitive_symbols']['instances'][0]['inputs'][0]['source_ref']['quote'] = 'fiction'
                elif mutation == 'action': self.a['cognitive_symbols']['instances'][0]['relation']['action_ref']['sha'] = 'stale'
                else:
                    self.b['w']['analysis']['execution_trace'][0]['output']['parts'] = []
                    action = self.b['w']['analysis']['execution_trace'][0]
                    for scene in self.a['scenes']: scene['action_refs'][0]['sha'] = sha(action)
                    for i in self.a['cognitive_symbols']['instances']: i['relation']['action_ref']['sha'] = sha(action)
                    self.save_bundle()
                with self.assertRaises(ValueError): self.validate()
                self.a, self.b = original
                self.save_bundle()

    def test_wrong_relation_or_borrowed_candidate_check_cannot_self_authorize(self):
        inst = self.a['cognitive_symbols']['instances'][0]
        inst['relation']['type'] = 'different_action_role'
        with self.assertRaises(ValueError): self.validate()
        inst['relation']['type'] = 'same_price_relation'; inst['relation']['verification_ref'] = deepcopy(self.a['cognitive_symbols']['instances'][1]['relation']['verification_ref'])
        with self.assertRaisesRegex(ValueError, 'complete frozen candidate check'): self.validate()

    def test_stopped_unreviewed_or_unconsumed_interpretation_rejected(self):
        review = self.b['w']['analysis']['question_verification']['review']; review['input_artifact_ids'] = []
        self.save_bundle()
        with self.assertRaisesRegex(ValueError, 'unconsumed'): self.validate()

    def test_hook_uses_actual_anonymous_anchors_without_leaking_actions_or_answer(self):
        hook = self.add_hook(); result = self.compile()['rows'][-1]
        self.assertEqual(result['visible_relation_labels'], []); self.assertIsNone(result['verdict'])
        self.assertEqual([p['phase'] for p in result['phases']], ['surface_align', 'relation_displace', 'unresolved_hold', 'match_into_task'])
        self.assertEqual(result['phases'][0]['start'], .5)
        hook['relation']['terminal_ref'] = {'candidate': 'B', 'effect': 'eliminate'}
        with self.assertRaisesRegex(ValueError, 'Hook recipe'): self.compile()

    def test_hook_rejects_unbound_anchor_or_role_labels(self):
        self.add_hook(); self.a['audience_hook']['visual_conflict']['relation_labels'] = True
        with self.assertRaisesRegex(ValueError, 'Hook recipe'): self.validate()

    def test_recall_reuses_both_actual_relations_without_new_claims(self):
        self.a['scenes'].append({'id': 'SC15', 'kind': 'recap'})
        self.clock['scenes'].append({'id': 'SC15', 'kind': 'recap', 'start': 24, 'end': 36})
        originals = deepcopy(self.a['cognitive_symbols']['instances'])
        for index, source in enumerate(originals):
            recall = deepcopy(source); recall.update(symbol_id='recall-' + str(index), scene_id='SC15', variant='recall', recall_of=source['symbol_id'])
            recall['parameters']['duration_seconds'] = 6
            self.a['cognitive_symbols']['instances'].append(recall)
        result = self.compile(); self.assertEqual([r['recall_of'] for r in result['rows'][-2:]], ['price', 'roles'])
        self.a['cognitive_symbols']['instances'][-1]['inputs'][0]['source_ref']['quote'] = 'invented'
        with self.assertRaises(ValueError): self.compile()

    def test_changed_request_stale_plan_and_promoted_review_are_rejected(self):
        compiled = self.compile(); self.assertEqual(validate_compiled_symbols(compiled, self.a, self.b, self.clock, self.worlds, self.folder), compiled)
        compiled['normal_speed_review'] = 'PASSED'
        with self.assertRaisesRegex(ValueError, 'promoted review'): validate_compiled_symbols(compiled, self.a, self.b, self.clock, self.worlds, self.folder)
        self.request.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'request'): self.validate()

    def test_lost_native_source_block_or_source_identity_rejected(self):
        self.worlds['w']['blocks'][0]['end'] -= 10
        with self.assertRaisesRegex(ValueError, 'real original native source block'): self.compile()

    def test_invalid_geometry_and_effect_fallbacks_rejected(self):
        for key, bad in [('curve', 'bounce'), ('mask', 'opaque_card')]:
            inst = self.a['cognitive_symbols']['instances'][0]; original = inst['parameters'][key]; inst['parameters'][key] = bad
            with self.assertRaises(ValueError): self.validate()
            inst['parameters'][key] = original
        self.a['cognitive_symbols']['instances'][0]['parameters']['space']['depth'] = float('nan')
        with self.assertRaises(ValueError): self.validate()

    def test_missing_source_and_changed_bundle_bytes_cannot_be_relabelled_as_same_world(self):
        path = Path(self.a['sources']['w']['bundle']); path.unlink()
        with self.assertRaisesRegex(ValueError, 'source file is missing'): self.validate()
        self.save_bundle(); path.write_text('{"substituted":true}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'file bytes'): self.validate()

    def test_unreadable_vertical_overlap_is_rejected_before_native_build(self):
        inst = self.a['cognitive_symbols']['instances'][0]
        inst['inputs'][2]['source_ref'] = self.ref('/passage', 'cheaper than\nOrion and Vega')
        inst['parameters']['font'].update(size=100, line_height=1.7)
        inst['parameters']['layout'].update(width=2400, height=240)
        with self.assertRaisesRegex(ValueError, 'exceeds readable layout'): self.compile()

    def test_mutated_scene_clock_and_out_of_bounds_judgement_rejected(self):
        self.clock['scenes'][0]['candidate'] = 'D'
        with self.assertRaisesRegex(ValueError, 'actual authored scene'): self.compile()
        self.clock['scenes'][0]['candidate'] = 'A'; self.clock['scenes'][0]['event_time'] = 20
        with self.assertRaisesRegex(ValueError, 'overrun'): self.compile()

    def test_hook_cannot_silently_use_lesson_timing_or_reorder_existing_phases(self):
        self.add_hook(); self.clock['audience_hook']['phases']['surface_align'] = [0, 1]
        with self.assertRaisesRegex(ValueError, 'phase ranges'): self.compile()

    def test_existing_teaching_focus_director_transformation_is_not_bypassed(self):
        self.a['teaching_focus'] = {'fixture': 'actual allocation consumer is mocked at its boundary'}
        def existing_director(author, scene):
            result = deepcopy(scene)
            result['choreography'] = {'comparison_seconds': 3.1}
            result['motion_treatment'] = 'critical_comparison'
            return result
        for live in self.clock['scenes']:
            live['choreography'] = {'comparison_seconds': 3.1}; live['motion_treatment'] = 'critical_comparison'
        with patch('creative_os.teaching_focus.direct_scene', side_effect=existing_director) as consumer:
            self.compile(); self.assertEqual(consumer.call_count, 2)
            self.clock['scenes'][0]['choreography']['comparison_seconds'] = .1
            with self.assertRaisesRegex(ValueError, 'actual authored scene'): self.compile()


if __name__ == '__main__': unittest.main()
