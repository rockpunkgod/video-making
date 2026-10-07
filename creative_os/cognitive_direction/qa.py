"""Deterministic direction lint; neither a rendered-frame nor human POV review."""
from video_contracts import sha
from .policy import HUMAN_DIMENSIONS, policy
from .visual import source_ref

FORBIDDEN_FIELDS = {
    'x', 'y', 'z', 'Z', 'position', 'opacity', 'blur', 'easing', 'keyframes', 'keyframe',
    'frame', 'frames', 'rotation', 'orbit', 'displacement', 'ae_effect', 'ae_layer',
    'speed_factor', 'tone', 'emotion', 'voice_take', 'pitch', 'tts', 'audio', 'music',
    'text', 'vo', 'new_claim', 'answer_text',
}


def _keys(value):
    if isinstance(value, dict):
        yield from value
        for item in value.values(): yield from _keys(item)
    elif isinstance(value, list):
        for item in value: yield from _keys(item)


def audit_direction(value, choreography, experience=None):
    rules, _ = policy()
    errors, risks = [], []
    catalog = {o['object_id']: o for o in value['object_catalog']}
    source_objects = {o['object_id']: o for o in choreography['object_catalog']}
    states = value['states']; source_states = choreography['states']
    transitions = value['transitions']; source_ops = choreography['operations']
    reality = set(choreography['states'][0]['reality_objects'])
    protected = {o['object_id'] for o in choreography['object_catalog'] if o['protected']}
    if len(catalog) != len(value['object_catalog']) or set(catalog) != set(source_objects):
        errors.append('LOGICAL_OBJECT_SET_CHANGED')
    if len({o['visual_object_id'] for o in catalog.values()}) != len(catalog):
        errors.append('VISUAL_IDENTITY_NOT_UNIQUE')
    if ([s['state_id'] for s in states] != [s['state_id'] for s in source_states]
            or len(transitions) != len(source_ops)):
        errors.append('COGNITIVE_STATE_ADDED_OR_REORDERED')
    if (not value['reality_layer']['persistent'] or not value['reality_layer']['first_encounter']
            or set(value['reality_layer']['object_ids']) != reality):
        risks.append('DETACHED_INFOGRAPH_RISK')
    for oid, obj in catalog.items():
        original = source_objects.get(oid)
        if original is None: continue
        if any(obj[k] != original[k] for k in (
                'origin_object_id', 'source_content_sha', 'source_refs', 'protected', 'reversibility', 'kind')):
            errors.append('LOGICAL_CARRY_CONTENT_CHANGED')
    for i, (state, original) in enumerate(zip(states, source_states)):
        ids = set(state['active_objects']); c = original['consequence']
        layers = state['spatial_layers']; placements = {p['object_id']: p for p in state['object_placements']}
        layered = [oid for group in layers.values() for oid in group]
        if (ids != set(original['present_objects']) or set(placements) != ids
                or len(layered) != len(set(layered)) or set(layered) != ids):
            errors.append('VISUAL_OBJECT_LOST_OR_DUPLICATED')
        if not reality <= ids or set(state['reality_scope']) != reality:
            risks.append('DETACHED_INFOGRAPH_RISK')
        if not ids: risks.append('PRESENTATION_RESET_RISK')
        background = set(layers['background_plane'] + layers['latent_plane'])
        if protected & background:
            errors.append('PROTECTED_OBJECT_BACKGROUNDED')
        if not set(c['unresolved_objects']) <= set(state['unresolved_objects']):
            errors.append('UNRESOLVED_OBJECT_HIDDEN')
        if set(state['resolved_objects']) != set(c['settle_allowed_objects']):
            errors.append('LOCAL_RESOLUTION_SCOPE_CHANGED')
        for key in ('focus_objects', 'carry_objects', 'background_objects', 'unresolved_objects', 'resolved_objects'):
            if not set(state[key]) <= ids: errors.append('DANGLING_DIRECTION_OBJECT')
        for oid, placement in placements.items():
            if oid not in catalog: continue
            if (placement['visual_object_id'] != catalog[oid]['visual_object_id']
                    or placement['source_disposition'] != original['object_states'][oid]
                    or oid not in layers.get(placement['plane'], [])):
                errors.append('VISUAL_LINEAGE_DRIFT')
            if oid in c['unresolved_objects'] and (placement['visibility'] != 'readable'
                    or placement['treatment'] != 'neutral_open' or placement['plane'] in ('latent_plane', 'background_plane')):
                errors.append('UNRESOLVED_FINAL_VISUAL_TREATMENT')
            if original['object_states'][oid] == 'defer' and (placement['plane'] != 'latent_plane'
                    or placement['visibility'] != 'retained_recoverable'):
                errors.append('DEFERRED_OBJECT_HARD_DELETED')
        if state['focus_intent']['winner_treatment']:
            errors.append('UNRESOLVED_FINAL_VISUAL_TREATMENT')
        comp = state['composition_intent']
        if (comp['candidate_objects'] != c['active_candidate_objects']
                or comp['candidate_count'] != c['active_candidate_count']
                or comp['source_groups'] != c['structural_groups']):
            errors.append('COMPOSITION_CHANGED_COGNITIVE_TRUTH')
        if state['source_state_ref'] != source_ref(choreography, '/states/' + str(i)):
            errors.append('SOURCE_STATE_BINDING_CHANGED')
        if state['pause_frame_required'] and (not state['settle']['required']
                or not {'SETTLE', 'READ', 'HOLD'} <= set(state['rhythm']) and i != 0
                or state['settle']['motion'] != 'stopped_during_read'
                or state['settle']['grid'] != 'shared_source_alignment'):
            errors.append('PAUSE_FRAME_WITHOUT_SWISS_SETTLE')
        allowed_energy = 'low' if original['stage'] in ('stop', 'memory') else 'high' if (
            original['stage'] == 'collapse' and choreography['collapse']['supported']
            or i and source_ops[i - 1]['verb'] == 'rewire'
            and source_ops[i - 1]['relation_id'] is not None) else 'medium'
        if state['visual_energy'] != allowed_energy:
            errors.append('ENERGY_INTENT_DRIFT')
            if state['visual_energy'] == 'high': risks.append('UNEARNT_VISUAL_ACCENT')
    lineage = {o['object_id']: o for o in value['visual_lineage']}
    if len(lineage) != len(value['visual_lineage']) or set(lineage) != set(catalog):
        errors.append('VISUAL_LINEAGE_MISSING')
    for oid, row in lineage.items():
        if oid not in catalog: continue
        obj = catalog[oid]
        if (row['visual_object_id'] != obj['visual_object_id']
                or row['source_content_sha'] != obj['source_content_sha']
                or row['origin_object_id'] != obj['origin_object_id']
                or len(row['encounters']) != len(states)):
            errors.append('VISUAL_LINEAGE_DRIFT')
        for encounter, state in zip(row['encounters'], states):
            placement = next((p for p in state['object_placements'] if p['object_id'] == oid), None)
            if (not placement or encounter['content_sha'] != obj['source_content_sha']
                    or encounter['visual_object_id'] != obj['visual_object_id']
                    or encounter['state_id'] != state['state_id']
                    or encounter['plane'] != placement['plane']
                    or encounter['source_disposition'] != placement['source_disposition']):
                errors.append('VISUAL_LINEAGE_DRIFT')
    deferred_ids = {p['object_id'] for s in states for p in s['object_placements'] if p['source_disposition'] == 'defer'}
    restores = {r['object_id']: r for r in value['restore_paths']}
    if set(restores) != deferred_ids: errors.append('RESTORE_PATH_MISSING')
    for oid, row in restores.items():
        obj = catalog.get(oid)
        if (not obj or obj['reversibility'] != 'reversible'
                or row['source_content_sha'] != obj['source_content_sha']
                or row['visual_object_id'] != obj['visual_object_id']):
            errors.append('RESTORE_PATH_CONTENT_DRIFT')
        actual = [op['operation_id'] for op in source_ops if op['verb'] == 'restore' and oid in op['target_objects']]
        if row['restore_operation_ids'] != actual: errors.append('FAKE_RESTORE_EVENT')
    camera_moves = 0; meaningful = 0
    for i, (tr, op) in enumerate(zip(transitions, source_ops)):
        before, after = states[i:i + 2]
        a, b = source_states[i]['consequence'], source_states[i + 1]['consequence']
        original = choreography['state_transitions'][i]
        if (tr['from_state'] != original['from_state'] or tr['to_state'] != original['to_state']
                or tr['operation_id'] != op['operation_id']
                or tr['cognitive_operation'] != {'family': op['family'], 'verb': op['verb']}
                or tr['spatial_intent']['target_objects'] != op['target_objects']):
            errors.append('OPERATION_BINDING_CHANGED')
        carry = set(tr['carry_objects'])
        if not carry or not carry <= set(before['active_objects']) & set(after['active_objects']):
            risks.extend(['PRESENTATION_RESET_RISK', 'PPT_RISK_02', 'PPT_RISK_08'])
        anchor = catalog.get(tr['continuity_object'])
        if (not anchor or tr['continuity_object'] not in carry
                or anchor['visual_object_id'] != tr['continuity_visual_id']):
            errors.append('LOGIC_MATCH_CARRY_BROKEN'); risks.append('PPT_RISK_08')
        camera = tr['camera_intent']
        if camera['strategy'] not in rules['camera_intents']:
            risks.append('DEMO_RISK_02'); errors.append('UNSUPPORTED_CAMERA_INTENT')
        causes = set()
        if a['active_scope'] != b['active_scope']: causes.add('attention_scope_changed')
        if (a['foreground_objects'] != b['foreground_objects']
                or a['active_candidate_objects'] != b['active_candidate_objects']
                or a['memory_action_recalled'] != b['memory_action_recalled']): causes.add('logical_object_changed')
        if (a['structural_groups'] != b['structural_groups']
                or a['route_node_ids'] != b['route_node_ids']): causes.add('spatial_relation_readability')
        if camera['strategy'] != 'hold':
            camera_moves += 1
            if camera['reason'] not in causes:
                errors.append('CAMERA_MOVE_WITHOUT_COGNITIVE_REASON'); risks.append('DEMO_RISK_01')
        elif camera['from_scope'] != camera['to_scope']:
            errors.append('CAMERA_SCOPE_CHANGED_WHILE_HELD')
        if camera['from_scope'] != before['camera_scope'] or camera['to_scope'] != after['camera_scope']:
            errors.append('CAMERA_SCOPE_CHAIN_BROKEN')
        consequence = tr['composition_consequence']
        if (consequence['before_sha'] != sha(before['composition_intent'])
                or consequence['after_sha'] != sha(after['composition_intent'])):
            errors.append('COMPOSITION_CONSEQUENCE_HASH_CHANGED')
        collapse = choreography['collapse']['supported'] and op['operation_id'] == choreography['collapse']['transition']['operation_id']
        if consequence['significant']:
            if before['composition_intent'] == after['composition_intent']:
                errors.append('SIGNIFICANT_ACTION_WITHOUT_COMPOSITION_CONSEQUENCE')
            else: meaningful += 1
        if collapse and (after['composition_intent']['subject_objects'] != b['active_candidate_objects']
                or after['composition_intent']['negative_space'] != 'expanded'
                or after['composition_intent']['reading_axis'] != 'local_candidate_group'
                or not after['pause_frame_required']):
            errors.append('COLLAPSE_COMPOSITION_CONSEQUENCE_MISSING')
        accent = tr['visual_accent']
        if accent is not None:
            relation = op['verb'] == 'rewire' and op['relation_id'] is not None
            if not collapse and not relation:
                errors.append('UNSUPPORTED_VISUAL_ACCENT'); risks.append('UNEARNT_VISUAL_ACCENT')
                risks.append('DEMO_RISK_05')
            if accent['kind'] == 'collapse_punctuation' and not collapse:
                errors.append('UNSUPPORTED_PAYOFF_ACCENT')
        if len(tr['depth_intents']) > 2: errors.append('DEPTH_BUDGET_EXCEEDED')
        if tr['mode'] != 'continuous_transformation' and tr['cut_reason'] not in rules['legal_cut_reasons']:
            errors.append('CUT_WITHOUT_COGNITIVE_REASON'); risks.append('DEMO_RISK_07')
        if tr['cut_reason'] == 'payoff_punctuation' and not collapse:
            errors.append('UNSUPPORTED_PAYOFF_CUT')
    covered = [sid for shot in value['shots'] for sid in shot['source_states']]
    if covered != [s['state_id'] for s in states]: errors.append('SHOT_STATE_COVERAGE_CHANGED')
    for shot in value['shots']:
        if shot['whole_screen_reset']: risks.extend(['PRESENTATION_RESET_RISK', 'PPT_RISK_02'])
        if shot['independent_title_ref'] is not None: risks.append('PPT_RISK_01')
        if shot['card_panel_intent']: risks.append('PPT_RISK_03')
        if shot['entry_only_motion']: risks.append('PPT_RISK_05')
        if shot['step_label_ref'] is not None: risks.append('PPT_RISK_06')
        if not set(shot['motion_grammar']) <= set(rules['brand_grammar_refs']): errors.append('BRAND_GRAMMAR_DRIFT')
        if shot['effect_budget'] != rules['effect_budget']: errors.append('EFFECT_BUDGET_CHANGED')
    if len(states) >= 4:
        if len({s['camera_scope'] for s in states}) == 1: risks.append('PPT_RISK_09')
        if len({s['composition_intent']['density'] for s in states}) == 1: risks.append('PPT_RISK_10')
        if all(sum(bool(v) for v in s['spatial_layers'].values()) <= 1 for s in states): risks.append('PPT_RISK_04')
    if experience is not None:
        compact = lambda text: ''.join(text.split())
        for beat in experience['beats']:
            vo = beat['vo']
            if vo and any(compact(vo['text']) == compact(line['text'])
                          for line in beat['screen']['copy']): risks.append('PPT_RISK_07')
    if (value['collapse']['supported'] != choreography['collapse']['supported']
            or (value['payoff_event_ref'] is not None) != (choreography['payoff_event'] is not None)):
        errors.append('UNSUPPORTED_PAYOFF_DIRECTION')
    stop = value['stop']; expected_stop = choreography['stop']
    if (stop['state_id'] != expected_stop['reached_state'] or stop['scope'] != expected_stop['scope']
            or stop['unresolved_objects'] != expected_stop['unresolved_objects']
            or stop['deferred_objects'] != expected_stop['deferred_objects']
            or not all(stop[k] for k in ('camera_settles', 'background_motion_stops', 'active_path_closes', 'unresolved_remains_visible'))
            or stop['final_answer_treatment']): errors.append('STOP_VISUAL_SCOPE_UPGRADED')
    if value['final_answer_allowed'] != choreography['final_answer_allowed']:
        errors.append('FINAL_ANSWER_PERMISSION_CHANGED')
    stamp = value['method_stamp']
    if stamp is not None:
        order = [s['state_id'] for s in states]
        core = choreography['intervention']['transitions']
        if (stamp['state_id'] not in order or not core
                or order.index(stamp['state_id']) <= max(order.index(t['to_state']) for t in core)
                or stamp['logo_reveal'] or stamp['show_internal_method_id']): errors.append('METHOD_STAMP_BEFORE_ACTION_OR_LOGO')
    expected_curve = [{'state_id': s['state_id'], 'energy': s['visual_energy'],
                       'driver': s['energy_driver'], 'source_ref': s['energy_source_ref']} for s in states]
    if value['visual_energy_curve'] != expected_curve: errors.append('ENERGY_CURVE_DRIFT')
    forbidden = set(_keys(value)) & FORBIDDEN_FIELDS
    if forbidden:
        errors.append('AE_TTS_OR_NEW_TEXT_FIELD_FORBIDDEN')
        if forbidden & {'orbit', 'rotation'}: risks.extend(['DEMO_RISK_02', 'DEMO_RISK_03'])
        if forbidden & {'blur', 'displacement'}: risks.append('DEMO_RISK_04')
    if (value['human_direction_review'] != {key: 'PENDING' for key in HUMAN_DIMENSIONS}
            or value['actual_visual_review'] != 'PENDING' or value['public_render_ready']
            or value['execution_allowed']): errors.append('AUTOMATIC_HUMAN_EXECUTION_OR_PUBLIC_APPROVAL')
    errors, risks = sorted(set(errors)), sorted(set(risks))
    audit = {
        'camera_bound_to_attention': not any(e.startswith('CAMERA_') for e in errors),
        'camera_move_count': camera_moves,
        'reality_continuity': 'DETACHED_INFOGRAPH_RISK' not in risks,
        'object_lineage_preserved': not any(e in errors for e in (
            'VISUAL_LINEAGE_DRIFT', 'VISUAL_LINEAGE_MISSING', 'LOGICAL_CARRY_CONTENT_CHANGED', 'LOGIC_MATCH_CARRY_BROKEN')),
        'reversibility_preserved': not any(e in errors for e in (
            'DEFERRED_OBJECT_HARD_DELETED', 'RESTORE_PATH_MISSING', 'RESTORE_PATH_CONTENT_DRIFT', 'FAKE_RESTORE_EVENT')),
        'composition_consequence_preserved': not any('COMPOSITION' in e for e in errors),
        'significant_composition_change_count': meaningful,
        'unresolved_preserved': not any(e in errors for e in ('UNRESOLVED_OBJECT_HIDDEN', 'UNRESOLVED_FINAL_VISUAL_TREATMENT')),
        'stop_scope_preserved': 'STOP_VISUAL_SCOPE_UPGRADED' not in errors,
        'visual_energy_bound': 'ENERGY_INTENT_DRIFT' not in errors and 'ENERGY_CURVE_DRIFT' not in errors,
        'anti_ppt_lint_pass': not any(r.startswith('PPT_') for r in risks),
        'anti_ae_demo_lint_pass': not any(r.startswith('DEMO_') for r in risks),
        'deterministic_lint_only': True, 'semantic_truth_certification': False,
        'actual_camera_readability': 'PENDING', 'actual_pause_frame_value': 'PENDING',
        'actual_swiss_identity': 'PENDING', 'human_direction_review': 'PENDING',
        'human_only_observations': ['DEMO_RISK_06', 'semantic_voice_screen_duplication', 'pov_present', 'payoff_impact'],
    }
    return audit, risks, errors
