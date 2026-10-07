"""SYNTHETIC direction contracts and negative controls, never a taste certificate."""
import ast
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from video_contracts import ROOT, read, write, sha, seal
from student_pov import realize_experience
from method_choreography import compile_choreography, compile_synthetic_peel
from tests import test_method_choreography as sources
from creative_os.cognitive_direction import (
    compile_direction, compile_synthetic_direction, inspect_direction, validate_direction,
    validate_synthetic_direction, project_direction, project_synthetic_direction, validate_projection,
)
from creative_os.cognitive_direction.policy import semantic_payload, policy, HUMAN_DIMENSIONS
from creative_os.cognitive_direction.qa import audit_direction
from creative_os.cognitive_direction.__main__ import main


def reseal(value):
    value = deepcopy(value)
    value['direction_sha'] = sha(semantic_payload(value))
    value['direction_id'] = 'direction:' + value['direction_sha']
    return seal(value)


class CognitiveDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources.MethodChoreographyTests.setUpClass()
        cls.sources = [sources.MethodChoreographyTests.experience, sources.MethodChoreographyTests.plan, sources.MethodChoreographyTests.copy, sources.MethodChoreographyTests.motion, sources.MethodChoreographyTests.bundle, sources.MethodChoreographyTests.status]
        cls.choreography = sources.MethodChoreographyTests.value
        cls.value = compile_direction(cls.choreography, *cls.sources)
        g, e, p, b, s, app = sources.MethodChoreographyTests().g01()
        cls.g01_choreography = g; cls.g01_sources = [e, p, None, None, b, s]; cls.g01_application = app
        cls.g01 = compile_direction(g, *cls.g01_sources, application=app, diagnostic=True)
        cls.fixture = sources.MethodChoreographyTests.fixture; cls.peel = sources.MethodChoreographyTests.peel
        cls.synthetic = compile_synthetic_direction(cls.peel, cls.fixture)

    def validate(self, value=None):
        return validate_direction(self.value if value is None else value, self.choreography, *self.sources)

    def edit_audit(self, edit, value=None, choreography=None):
        result = deepcopy(self.value if value is None else value); edit(result)
        return audit_direction(result, self.choreography if choreography is None else choreography)

    def test_current_choreography_plan_student_and_copy_sha_bound(self):
        binding = self.value['binding']
        self.assertEqual(binding['choreography_sha'], self.choreography['choreography_sha'])
        self.assertEqual(binding['student_experience_sha'], sources.MethodChoreographyTests.experience['experience_sha'])
        self.assertEqual(binding['student_script_sha'], sources.MethodChoreographyTests.experience['script_sha'])
        self.assertEqual(binding['student_final_copy_sha'], sources.MethodChoreographyTests.experience['final_copy_sha'])
        self.assertEqual(binding['pedagogy_plan_sha'], sources.MethodChoreographyTests.plan['plan_sha'])
        self.assertEqual(binding['legacy_cognitive_pov_version'], '0.1.0')
        self.assertEqual(self.value['compilation_status'], 'PASS')
        self.assertEqual(self.validate()['status'], 'PASS')
        self.assertTrue(self.validate()['consumption_allowed'])

    def test_choreography_change_invalidates_old_direction_even_after_reseal(self):
        changed = deepcopy(self.choreography)
        changed['operations'][0]['verb'] = 'jump'
        with self.assertRaises(ValueError):
            validate_direction(self.value, changed, *self.sources)
        changed = deepcopy(self.value); changed['binding']['choreography_sha'] = '0' * 64
        with self.assertRaises(ValueError): self.validate(reseal(changed))

    def test_student_experience_change_invalidates_old_direction(self):
        experience = realize_experience(sources.MethodChoreographyTests.copy, sources.MethodChoreographyTests.motion, sources.MethodChoreographyTests.plan, sources.MethodChoreographyTests.bundle, sources.MethodChoreographyTests.status,
                                       options={'merge_collapse_payoff': False})
        with self.assertRaises(ValueError):
            validate_direction(self.value, self.choreography, experience, *self.sources[1:])

    def test_copy_semantics_and_teaching_inputs_unchanged(self):
        before = sha([self.choreography, *self.sources])
        compile_direction(self.choreography, *self.sources)
        self.validate(); project_direction(self.value, self.choreography, *self.sources, diagnostic=True)
        self.assertEqual(before, sha([self.choreography, *self.sources]))
        self.assertFalse(self.value['source']['new_teaching_text_created'])
        self.assertFalse(self.value['source']['text_parsing_performed'])

    def test_current_status_missing_withdrawn_or_rights_changed_blocks(self):
        for status in [None, seal({**deepcopy(sources.MethodChoreographyTests.status), 'effective_status': 'WITHDRAWN'}),
                       seal({**deepcopy(sources.MethodChoreographyTests.status), 'source_sha': '0' * 64})]:
            with self.subTest(status=status is None), self.assertRaises((ValueError, TypeError)):
                validate_direction(self.value, self.choreography, *self.sources[:-1], status)
        self.assertFalse(inspect_direction(self.value)['consumption_allowed'])

    def test_reality_and_original_question_are_persistent(self):
        reality = set(self.value['reality_layer']['object_ids'])
        self.assertTrue(reality)
        self.assertTrue(self.value['reality_layer']['upper_anchor_objects'])
        for state in self.value['states']:
            self.assertEqual(reality, set(state['reality_scope']))
            self.assertTrue(reality <= set(state['active_objects']))
        for shot in self.value['shots']: self.assertEqual(reality, set(shot['reality_layer']))

    def test_whole_screen_reset_is_detected(self):
        _, risks, _ = self.edit_audit(lambda v: v['transitions'][0].update(carry_objects=[]))
        self.assertIn('PRESENTATION_RESET_RISK', risks)
        self.assertIn('PPT_RISK_08', risks)
        _, risks, _ = self.edit_audit(lambda v: v['shots'][0].update(whole_screen_reset=True))
        self.assertIn('PPT_RISK_02', risks)

    def test_detached_infograph_is_detected(self):
        _, risks, _ = self.edit_audit(lambda v: v['states'][2].update(reality_scope=[]))
        self.assertIn('DETACHED_INFOGRAPH_RISK', risks)

    def test_visual_id_and_source_content_continue_across_shots(self):
        for row in self.value['visual_lineage']:
            self.assertEqual(len(row['encounters']), len(self.value['states']))
            self.assertEqual({e['visual_object_id'] for e in row['encounters']}, {row['visual_object_id']})
            self.assertEqual({e['content_sha'] for e in row['encounters']}, {row['source_content_sha']})
        for tr in self.value['transitions']:
            self.assertIn(tr['continuity_object'], tr['carry_objects'])
        self.assertLess(len(self.value['shots']), len(self.value['states']))

    def test_changed_logic_carry_text_or_identity_is_detected(self):
        _, _, errors = self.edit_audit(lambda v: v['visual_lineage'][0]['encounters'][1].update(content_sha='0'*64))
        self.assertIn('VISUAL_LINEAGE_DRIFT', errors)
        _, _, errors = self.edit_audit(lambda v: v['object_catalog'][0].update(source_content_sha='0'*64))
        self.assertIn('LOGICAL_CARRY_CONTENT_CHANGED', errors)

    def test_camera_moves_have_actual_attention_or_readability_cause(self):
        self.assertTrue(self.value['audit']['camera_bound_to_attention'])
        self.assertGreater(self.value['audit']['camera_move_count'], 0)
        for tr in self.value['transitions']:
            if tr['camera_intent']['strategy'] != 'hold':
                self.assertIn(tr['camera_intent']['reason'], policy()[0]['camera_reasons'])
        self.assertEqual(self.value['states'][0]['camera_scope'], 'wide')
        self.assertNotEqual(self.value['states'][1]['camera_scope'], 'wide')

    def test_camera_cannot_move_on_unchanged_stop_attention(self):
        def edit(v):
            next(t for t in v['transitions'] if t['cognitive_operation']['verb'] == 'lock')['camera_intent'].update(
                strategy='reframe', reason='attention_scope_changed')
        _, risks, errors = self.edit_audit(edit)
        self.assertIn('CAMERA_MOVE_WITHOUT_COGNITIVE_REASON', errors)
        self.assertIn('DEMO_RISK_01', risks)

    def test_held_camera_cannot_silently_change_scope(self):
        def edit(v): v['transitions'][0]['camera_intent'].update(strategy='hold')
        _, _, errors = self.edit_audit(edit)
        self.assertIn('CAMERA_SCOPE_CHANGED_WHILE_HELD', errors)

    def test_unresolved_candidates_cannot_get_winner_visual_treatment(self):
        candidate = self.choreography['states'][-1]['consequence']['active_candidate_objects'][0]
        def edit(v):
            next(p for p in v['states'][-1]['object_placements'] if p['object_id'] == candidate)['treatment'] = 'winner_spotlight'
        _, _, errors = self.edit_audit(edit)
        self.assertIn('UNRESOLVED_FINAL_VISUAL_TREATMENT', errors)
        _, _, errors = self.edit_audit(lambda v: v['states'][-1]['focus_intent'].update(winner_treatment=True))
        self.assertIn('UNRESOLVED_FINAL_VISUAL_TREATMENT', errors)

    def test_local_four_to_three_changes_composition_and_retains_three(self):
        collapse = self.choreography['collapse']['transition']
        before, after = [next(s for s in self.value['states'] if s['state_id'] == collapse[k])
                         for k in ['from_state', 'to_state']]
        self.assertEqual(before['composition_intent']['candidate_count'], 4)
        self.assertEqual(after['composition_intent']['candidate_count'], 3)
        self.assertEqual(len(after['focus_objects']), 3)
        self.assertTrue(set(after['focus_objects']) <= set(after['unresolved_objects']))
        self.assertNotEqual(before['composition_intent']['negative_space'], after['composition_intent']['negative_space'])
        self.assertNotEqual(before['composition_intent']['reading_axis'], after['composition_intent']['reading_axis'])
        self.assertEqual(after['composition_intent']['character'], 'compressed')
        self.assertTrue(after['pause_frame_required'])
        self.assertFalse(self.value['final_answer_allowed'])

    def test_collapse_without_composition_consequence_is_rejected(self):
        def edit(v):
            index = next(i for i,s in enumerate(v['states']) if s['cognitive_state'] == 'REDUCE')
            v['states'][index]['composition_intent'] = deepcopy(v['states'][index-1]['composition_intent'])
            v['transitions'][index-1]['composition_consequence']['after_sha'] = sha(v['states'][index]['composition_intent'])
        _, _, errors = self.edit_audit(edit)
        self.assertIn('SIGNIFICANT_ACTION_WITHOUT_COMPOSITION_CONSEQUENCE', errors)
        self.assertIn('COLLAPSE_COMPOSITION_CONSEQUENCE_MISSING', errors)

    def test_g01_hold_stays_action_demo_without_final_resolution(self):
        value = self.g01
        self.assertEqual(value['compilation_status'], 'PASS')
        self.assertEqual(value['availability']['status'], 'HOLD')
        self.assertEqual(value['experience_kind'], 'action_demo')
        self.assertIn('PAYOFF_UNSUPPORTED', value['availability']['gaps'])
        self.assertFalse(value['collapse']['supported'])
        self.assertIsNone(value['payoff_event_ref'])
        self.assertFalse(value['stop']['final_answer_treatment'])
        self.assertTrue(all(t['visual_accent'] is None for t in value['transitions']))
        self.assertTrue(all(s['visual_energy'] != 'high' for s in value['states']))

    def test_g01_fake_collapse_climax_is_detected(self):
        def edit(v):
            v['transitions'][1]['visual_accent'] = {'kind':'collapse_punctuation','source_event_ref':v['stop']['source_ref'],'objects':[]}
            v['states'][2]['visual_energy'] = 'high'
        _, risks, errors = self.edit_audit(edit, self.g01, self.g01_choreography)
        self.assertIn('UNEARNT_VISUAL_ACCENT', risks)
        self.assertIn('UNSUPPORTED_PAYOFF_ACCENT', errors)

    def test_deferred_object_has_reversible_latent_plane_and_restore_path(self):
        for path in self.g01['restore_paths']:
            self.assertEqual(path['status'], 'available_not_executed')
            self.assertEqual(path['restore_operation_ids'], [])
            self.assertEqual(path['return_plane'], 'reading_plane')
        self.assertEqual({p['object_id'] for p in self.g01['restore_paths']},
                         {o['object_id'] for o in self.g01_choreography['object_catalog'] if o['state'] == 'defer'})

    def test_deferred_object_cannot_be_hard_deleted(self):
        def edit(v):
            next(p for p in v['states'][2]['object_placements'] if p['source_disposition'] == 'defer')['visibility'] = 'destroyed'
        _, _, errors = self.edit_audit(edit, self.g01, self.g01_choreography)
        self.assertIn('DEFERRED_OBJECT_HARD_DELETED', errors)

    def test_protected_object_cannot_move_to_background(self):
        oid = next(o['object_id'] for o in self.value['object_catalog'] if o['protected'])
        def edit(v):
            s = v['states'][1]
            for group in s['spatial_layers'].values():
                if oid in group: group.remove(oid)
            s['spatial_layers']['background_plane'].append(oid)
        _, _, errors = self.edit_audit(edit)
        self.assertIn('PROTECTED_OBJECT_BACKGROUNDED', errors)

    def test_synthetic_peel_has_same_objects_tighten_and_restore(self):
        value = self.synthetic
        self.assertTrue(value['audit']['reversibility_preserved'])
        self.assertEqual([r['status'] for r in value['restore_paths']], ['restored_same_object']*2)
        self.assertEqual(value['states'][3]['composition_intent']['character'], 'compressed')
        self.assertEqual(value['states'][4]['camera_scope'], 'wide')
        self.assertEqual(value['states'][4]['composition_intent']['latent_objects'], [])
        self.assertFalse(value['collapse']['supported'])
        self.assertIsNone(value['memory_closure'])
        self.assertFalse(validate_synthetic_direction(value, self.peel, self.fixture)['consumption_allowed'])

    def test_synthetic_peel_can_stop_with_work_only_deferred(self):
        source = compile_synthetic_peel(self.fixture, restore=False)
        value = compile_synthetic_direction(source, self.fixture, restore=False)
        self.assertEqual(len(value['stop']['deferred_objects']), 2)
        self.assertEqual([r['status'] for r in value['restore_paths']], ['available_not_executed']*2)
        self.assertFalse(value['collapse']['supported'])

    def test_synthetic_changed_annotation_cannot_reuse_old_direction(self):
        changed = deepcopy(self.fixture); changed['objects'][0]['text'] = 'SYNTHETIC CHANGED CORE'
        with self.assertRaises(ValueError): validate_synthetic_direction(self.synthetic, self.peel, changed)

    def test_twenty_to_forty_second_energy_window_is_not_flat_or_forced_high(self):
        self.assertEqual(self.synthetic['timing_context']['duration_seconds'], 30)
        energies = [s['visual_energy'] for s in self.synthetic['states']]
        self.assertGreater(len(set(energies)), 1)
        self.assertNotIn('high', energies)
        self.assertFalse(self.synthetic['timing_context']['absolute_timing_assigned'])
        for seconds in [19, 41, float('nan'), True]:
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                compile_synthetic_direction(self.peel, self.fixture, test_window_seconds=seconds)

    def test_arbitrary_visual_energy_change_is_detected(self):
        _, risks, errors = self.edit_audit(lambda v: v['states'][0].update(visual_energy='high'))
        self.assertIn('ENERGY_INTENT_DRIFT', errors)
        self.assertIn('UNEARNT_VISUAL_ACCENT', risks)

    def test_accent_requires_own_cognitive_event(self):
        def edit(v): v['transitions'][0]['visual_accent'] = {
            'kind':'collapse_punctuation','source_event_ref':v['stop']['source_ref'],'objects':[]}
        _, risks, errors = self.edit_audit(edit)
        self.assertIn('UNEARNT_VISUAL_ACCENT', risks)
        self.assertIn('UNSUPPORTED_PAYOFF_ACCENT', errors)

    def test_depth_is_semantic_and_budgeted(self):
        self.assertTrue(all(len(t['depth_intents']) <= 2 for t in self.value['transitions']))
        self.assertTrue(any(s['spatial_layers']['foreground'] and s['spatial_layers']['reading_plane']
                            for s in self.value['states'][1:]))
        changed = deepcopy(self.value); changed['transitions'][0]['depth_intents'] = ['x','y','z']
        with self.assertRaises(ValueError): inspect_direction(reseal(changed))

    def test_method_stamp_only_after_core_action_and_not_internal_id(self):
        self.assertFalse(self.value['method_stamp']['show_internal_method_id'])
        self.assertEqual(self.value['method_stamp']['style'], 'small_editorial_metadata')
        _, _, errors = self.edit_audit(lambda v: v['method_stamp'].update(state_id=v['states'][0]['state_id']))
        self.assertIn('METHOD_STAMP_BEFORE_ACTION_OR_LOGO', errors)

    def test_memory_thumbnail_only_references_existing_allowed_content(self):
        memory = self.value['memory_closure']['mental_thumbnail']
        self.assertEqual(memory['memory_phrase_ref'], self.choreography['memory_closure']['memory_phrase_ref'])
        self.assertFalse(memory['new_teaching_text_created'])
        changed = deepcopy(self.value); changed['memory_closure']['mental_thumbnail']['text'] = 'WHO ACTION OBJECT'
        with self.assertRaises(ValueError): inspect_direction(reseal(changed))
        changed = deepcopy(self.value); changed['memory_closure']['mental_thumbnail']['memory_phrase_ref']['sha'] = '0'*64
        with self.assertRaises(ValueError): self.validate(reseal(changed))

    def test_stop_seals_only_current_operation_with_unresolved_visible(self):
        stop = self.value['stop']
        self.assertEqual(stop['scope'], self.choreography['stop']['scope'])
        self.assertEqual(stop['unresolved_objects'], self.choreography['stop']['unresolved_objects'])
        state = next(s for s in self.value['states'] if s['state_id'] == stop['state_id'])
        self.assertEqual(state['cognitive_state'], 'STOP')
        self.assertEqual(state['visual_energy'], 'low')
        self.assertTrue(state['pause_frame_required'])
        _, _, errors = self.edit_audit(lambda v: v['stop'].update(final_answer_treatment=True))
        self.assertIn('STOP_VISUAL_SCOPE_UPGRADED', errors)

    def test_shots_are_multi_state_attention_encounters_not_pages(self):
        self.assertTrue(any(len(s['source_states']) > 1 for s in self.value['shots']))
        self.assertEqual([sid for s in self.value['shots'] for sid in s['source_states']],
                         [s['state_id'] for s in self.value['states']])
        self.assertTrue(all(s['independent_title_ref'] is None and not s['card_panel_intent'] for s in self.value['shots']))

    def test_pause_frames_have_swiss_settle_and_read_phase(self):
        for state in self.value['states'][1:]:
            if state['pause_frame_required']:
                self.assertTrue({'SETTLE','READ','HOLD'} <= set(state['rhythm']))
                self.assertEqual(state['settle']['grid'], 'shared_source_alignment')
        _, _, errors = self.edit_audit(lambda v: v['states'][-1].update(rhythm=['MOVE']))
        self.assertIn('PAUSE_FRAME_WITHOUT_SWISS_SETTLE', errors)

    def test_anti_ppt_title_panel_and_entrance_risks_detected(self):
        def edit(v): v['shots'][0].update(independent_title_ref='fake',card_panel_intent=True,entry_only_motion=True,step_label_ref='step')
        _, risks, _ = self.edit_audit(edit)
        for risk in ['PPT_RISK_01','PPT_RISK_03','PPT_RISK_05','PPT_RISK_06']: self.assertIn(risk, risks)

    def test_flat_scope_density_and_space_are_risks(self):
        def edit(v):
            for s in v['states']:
                s['camera_scope'] = 'medium'; s['composition_intent']['density'] = 'medium'
                for plane in s['spatial_layers']: s['spatial_layers'][plane] = []
                s['spatial_layers']['reading_plane'] = s['active_objects'][:]
        _, risks, _ = self.edit_audit(edit)
        for risk in ['PPT_RISK_04','PPT_RISK_09','PPT_RISK_10']: self.assertIn(risk, risks)

    def test_anti_ae_demo_orbit_rotation_blur_and_cut_are_rejected(self):
        def edit(v):
            v['transitions'][0]['camera_intent'].update(orbit=True,rotation=45,blur=9)
            v['transitions'][0].update(mode='flashy_cut',cut_reason='eight_seconds_elapsed')
        _, risks, errors = self.edit_audit(edit)
        for risk in ['DEMO_RISK_02','DEMO_RISK_03','DEMO_RISK_04','DEMO_RISK_07']: self.assertIn(risk, risks)
        self.assertIn('AE_TTS_OR_NEW_TEXT_FIELD_FORBIDDEN', errors)

    def test_schema_rejects_ae_frames_glyph_or_tts_parameters(self):
        for key, payload in [('keyframes',[]),('Z',-280),('x',90),('speed_factor',1.02),('tone','focused'),('music','Chopin')]:
            changed = deepcopy(self.value); changed['transitions'][0][key] = payload
            with self.subTest(key=key), self.assertRaises(ValueError): inspect_direction(reseal(changed))

    def test_direction_runtime_does_not_import_execution_solver_or_voice(self):
        forbidden = ('ae_production','premiere_production','narration_performance','voicepacks','core','answer_engine')
        for path in (ROOT/'creative_os/cognitive_direction').glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                names = [node.module] if isinstance(node, ast.ImportFrom) and node.module else [n.name for n in node.names] if isinstance(node, ast.Import) else []
                self.assertFalse(any(name.split('.')[0] in forbidden for name in names), str(path))

    def test_human_review_and_public_status_cannot_be_self_approved(self):
        self.assertEqual(self.value['human_direction_review'], {k:'PENDING' for k in HUMAN_DIMENSIONS})
        self.assertFalse(self.value['execution_allowed'] or self.value['public_render_ready'])
        self.assertFalse(self.value['unsupported_capabilities']['current_native_ae_contract_compatible'])
        for edit in [lambda v: v['human_direction_review'].update(pov_present='PASS'), lambda v: v.update(public_render_ready=True)]:
            changed = deepcopy(self.value); edit(changed)
            with self.assertRaises(ValueError): inspect_direction(reseal(changed))

    def test_bound_coarse_relation_reports_missing_endpoint_geometry(self):
        gaps = self.value['unsupported_capabilities']['layout_capability_gap']
        self.assertTrue(gaps)
        self.assertEqual(gaps[0]['code'], 'RELATION_ENDPOINT_SPANS_UNAVAILABLE')
        self.assertEqual(gaps[0]['not_generated'], 'actor_endpoint_graph')
        self.assertFalse(gaps[0]['blocking_current_coarse_plan'])

    def test_diagnostic_hold_projection_cannot_become_consumable(self):
        with self.assertRaises(ValueError):
            compile_direction(self.g01_choreography, *self.g01_sources, application=self.g01_application)
        held = compile_direction(self.choreography, *self.sources, diagnostic=True)
        with self.assertRaises(ValueError): project_direction(held, self.choreography, *self.sources)
        projection = project_direction(held, self.choreography, *self.sources, diagnostic=True)
        self.assertFalse(projection['consumption_allowed'] or projection['execution_allowed'])
        self.assertTrue(projection['diagnostic_only'])
        self.assertEqual(validate_projection(projection, held, self.choreography, *self.sources)['status'], 'PASS')
        changed = deepcopy(projection); changed['consumption_allowed'] = True
        with self.assertRaises(ValueError): validate_projection(seal(changed), held, self.choreography, *self.sources)

    def test_synthetic_handoff_is_always_non_executable(self):
        projection = project_synthetic_direction(self.synthetic, self.peel, self.fixture)
        self.assertFalse(projection['consumption_allowed'] or projection['execution_allowed'])
        self.assertEqual(validate_projection(projection, self.synthetic, self.peel, fixture=self.fixture)['status'], 'PASS')

    def test_repeated_direction_and_core_hash_are_deterministic(self):
        repeated = compile_direction(self.choreography, *self.sources)
        self.assertEqual(self.value, repeated)
        later = deepcopy(self.value); later['generated_at'] = 'SYNTHETIC LATER'
        self.assertEqual(sha(semantic_payload(later)), self.value['direction_sha'])
        self.assertNotEqual(seal(later)['envelope_sha'], self.value['envelope_sha'])

    def test_cli_synthetic_history_no_overwrite_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); write(root/'fixture.json', self.fixture); write(root/'choreography.json', self.peel)
            request = {'choreography':'choreography.json','fixture':'fixture.json','output':'direction.json'}
            write(root/'request.json',request)
            argv = ['cognitive_direction','compile-synthetic',str(root/'request.json')]
            with patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()): main()
            before = (root/'direction.json').read_bytes()
            with patch('sys.argv',argv),self.assertRaises(ValueError): main()
            self.assertEqual(before,(root/'direction.json').read_bytes())
            request.update(output='new.json', speed_factor=1.04); write(root/'request.json',request)
            with patch('sys.argv',argv),self.assertRaises(ValueError): main()
            self.assertFalse((root/'new.json').exists())


if __name__ == '__main__': unittest.main()
