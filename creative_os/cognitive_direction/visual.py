"""Deterministic attention and information-space intents, never glyph geometry."""
from copy import deepcopy

from video_contracts import sha
from method_choreography.compiler import reference


def source_ref(choreography, path):
    return reference('method_choreography', choreography['choreography_id'], choreography, path)


def visual_catalog(choreography):
    return [{
        'object_id': o['object_id'],
        'visual_object_id': 'visual:' + sha([
            o['object_id'], o['origin_object_id'], o['source_content_sha'],
        ])[:24],
        'origin_object_id': o['origin_object_id'],
        'source_content_sha': o['source_content_sha'],
        'kind': o['kind'], 'protected': o['protected'],
        'reversibility': o['reversibility'],
        'display_policy': 'exact_reality_source' if o['kind'].startswith('original_question_')
            or o['kind'] == 'synthetic_annotated_span' else 'exact_permitted_evidence'
            if o['kind'] == 'evidence' or o['kind'].startswith('reviewed_span_')
            else 'structural_only_no_new_text',
        'source_refs': deepcopy(o['source_refs']),
        'source_object_ref': source_ref(choreography, '/object_catalog/' + str(i)),
    } for i, o in enumerate(choreography['object_catalog'])]


def _traits(state, op, previous_scope):
    stage = state['stage']
    if stage == 'problem':
        return 'REALITY', 'pain', 'dense', 'wide'
    if stage == 'collapse':
        return 'REDUCE', 'collapse', 'compressed', 'medium'
    if stage == 'stop':
        return 'STOP', 'stop', 'sealed', previous_scope
    if stage == 'memory':
        return 'MEMORY', 'stamp', 'focused', 'close'
    states = {
        'scan': ('SEARCH', 'searching', 'wide'),
        'jump': ('FOCUS', 'focused', 'close'),
        'anchor': ('ANCHOR', 'focused', 'close'),
        'lock': ('RESOLUTION', 'resolved', previous_scope),
        'return': ('FULL_SCOPE', 'focused', 'wide'),
        'peel': ('ISOLATE', 'isolated', 'close'),
        'mute': ('FOCUS', 'focused', 'close'),
        'fold': ('ISOLATE', 'isolated', 'close'),
        'tighten': ('STRUCTURE', 'compressed', 'close'),
        'reveal': ('STRUCTURE', 'focused', 'close'),
        'restore': ('FULL_SCOPE', 'dense', 'wide'),
        'align': ('COMPARE', 'aligned', 'medium'),
        'overlay': ('COMPARE', 'aligned', 'medium'),
        'split': ('COMPARE', 'split', 'medium'),
        'extrude': ('ISOLATE', 'isolated', 'close'),
        'reveal_difference': ('COMPARE', 'isolated', 'close'),
        'connect': ('STRUCTURE', 'aligned', 'close'),
        'detach': ('ISOLATE', 'isolated', 'close'),
        'rewire': ('TRANSFORM', 'aligned', 'close'),
        'reverse': ('TRANSFORM', 'split', 'close'),
        'reconnect': ('STRUCTURE', 'aligned', 'close'),
        'float': ('SEARCH', 'searching', 'wide'),
        'attract': ('STRUCTURE', 'focused', 'medium'),
        'regroup': ('STRUCTURE', 'aligned', 'medium'),
        'cluster': ('STRUCTURE', 'aligned', 'medium'),
        'separate': ('STRUCTURE', 'split', 'medium'),
        'settle': ('RESOLUTION', 'resolved', previous_scope),
        'extract': ('ISOLATE', 'isolated', 'focus'),
        'branch': ('STRUCTURE', 'split', 'medium'),
        'route': ('STRUCTURE', 'aligned', 'medium'),
        'resolve': ('RESOLUTION', 'resolved', previous_scope),
        'seal': ('STOP', 'sealed', previous_scope),
    }
    cognitive, composition, scope = states[op['verb']]
    return cognitive, 'focus' if stage == 'attention' else 'action', composition, scope


def _subject(choreography, state):
    c = state['consequence']
    if state['stage'] in ('collapse', 'stop') and c['active_candidate_objects']:
        # The remaining set is the subject, never a spotlight on one survivor.
        return list(c['active_candidate_objects'])
    candidates = c['foreground_objects']
    if state['stage'] == 'memory' and choreography['memory_closure']:
        candidates = choreography['memory_closure']['remembered_objects']
    return [oid for oid in candidates if state['object_states'][oid] not in ('remove', 'defer')]


def _space(state, catalog, focus):
    layers = {p: [] for p in (
        'foreground', 'reading_plane', 'supporting_plane', 'background_plane', 'latent_plane',
    )}
    placements = []
    for obj in catalog:
        oid = obj['object_id']; disposition = state['object_states'][oid]
        if disposition == 'defer':
            plane, visibility, treatment = 'latent_plane', 'retained_recoverable', 'deferred_recoverable'
        elif oid in focus:
            plane, visibility = 'foreground', 'readable'
            treatment = 'neutral_open' if disposition == 'unresolved' else 'source_focus'
        elif oid in state['reality_objects']:
            plane, visibility, treatment = 'reading_plane', 'readable', 'source_anchor'
        elif obj['protected'] or oid in state['consequence']['unresolved_objects'] or disposition == 'unresolved':
            plane, visibility = 'supporting_plane', 'readable'
            treatment = 'neutral_open' if oid in state['consequence']['unresolved_objects'] or disposition == 'unresolved' else 'source_support'
        elif disposition == 'remove':
            # An eligibility/work record may leave the active set; its source is retained.
            plane, visibility, treatment = 'supporting_plane', 'inactive_record', 'reviewed_inactive_record'
        elif oid in state['consequence']['background_objects']:
            plane, visibility, treatment = 'background_plane', 'ambient_recoverable', 'reversible_background'
        else:
            plane, visibility, treatment = 'supporting_plane', 'readable', 'source_support'
        layers[plane].append(oid)
        placements.append({
            'object_id': oid, 'visual_object_id': obj['visual_object_id'], 'plane': plane,
            'source_disposition': disposition, 'visibility': visibility,
            'treatment': treatment, 'content_policy': 'exact_source_reference',
        })
    return layers, placements


def direct_states(choreography, experience, catalog):
    by_op = {o['operation_id']: o for o in choreography['operations']}
    incoming = {t['to_state']: t for t in choreography['state_transitions']}
    states = []
    for i, source in enumerate(choreography['states']):
        tr = incoming.get(source['state_id']); op = by_op[tr['operation_id']] if tr else None
        scope_before = states[-1]['camera_scope'] if states else 'wide'
        cognitive, function, character, scope = _traits(source, op, scope_before)
        focus = _subject(choreography, source)
        layers, placements = _space(source, catalog, focus)
        c = source['consequence']
        stop = source['stage'] in ('stop', 'memory')
        collapse = source['stage'] == 'collapse' and choreography['collapse']['supported']
        relation_reveal = (op is not None and op['verb'] == 'rewire'
                           and 'structure_change' in op['cognitive_changes'])
        if stop:
            energy, driver = 'low', 'settle'
        elif collapse:
            energy, driver = 'high', 'supported_collapse'
        elif relation_reveal:
            energy, driver = 'high', 'relation_reveal'
        else:
            energy = 'medium'
            driver = 'full_reality' if op is None else (
                'attention_change' if source['stage'] == 'attention' else 'manipulation')
        pause = (source['stage'] in ('problem', 'attention', 'collapse', 'stop', 'memory')
                 or relation_reveal or (op and op['verb'] in ('tighten', 'route', 'lock')))
        axis = ('local_candidate_group' if collapse else 'aligned_current_output' if source['stage'] == 'stop'
                else 'remembered_first_action' if source['stage'] == 'memory'
                else 'isolated_source_relation' if op and op['verb'] == 'detach'
                else 'shared_source_coordinates' if op and op['family'] in ('comparison', 'relationship')
                else 'supplied_core_reading' if op and op['verb'] == 'tighten'
                else 'source_reading')
        negative = 'expanded' if stop or collapse else 'contracting' if character == 'compressed' else 'controlled'
        density = 'low' if stop or collapse or character == 'compressed' else 'high' if character == 'dense' else 'medium'
        refs = [source_ref(choreography, '/states/' + str(i))]
        if experience is not None:
            refs.extend(reference('student_experience', experience['experience_id'], experience, '/beats/' + str(j))
                        for j, beat in enumerate(experience['beats']) if beat['cognitive_function'] == function)
        tags = [cognitive]
        if i == 0: tags.append('FULL_SCOPE')
        if c['unresolved_objects']: tags.append('UNRESOLVED')
        if collapse and choreography['payoff_event']: tags.append('PAYOFF')
        if source['stage'] == 'stop' and c['output_encountered']: tags.append('RESOLUTION')
        states.append({
            'state_id': source['state_id'], 'source_state_ref': refs[0], 'source_refs': refs,
            'cognitive_state': cognitive, 'cognitive_tags': tags, 'cognitive_function': function,
            'reality_scope': deepcopy(source['reality_objects']),
            'active_objects': deepcopy(source['present_objects']), 'focus_objects': focus,
            'background_objects': layers['background_plane'] + layers['latent_plane'],
            'unresolved_objects': deepcopy(c['unresolved_objects']),
            'resolved_objects': deepcopy(c['settle_allowed_objects']),
            'carry_objects': deepcopy(tr['carry_objects']) if tr else deepcopy(source['reality_objects']),
            'camera_scope': scope, 'spatial_layers': layers, 'object_placements': placements,
            'composition_intent': {
                'character': character, 'subject_objects': focus,
                'source_groups': deepcopy(c['structural_groups']),
                'candidate_objects': deepcopy(c['active_candidate_objects']),
                'candidate_count': c['active_candidate_count'],
                'latent_objects': deepcopy(layers['latent_plane']),
                'reading_axis': axis, 'negative_space': negative, 'density': density,
                'framing': 'retained_source_field' if i == 0 else 'controlled_asymmetry',
            },
            'focus_intent': {
                'dominant_subject': focus, 'one_logical_subject': True,
                'means': ['contrast_hierarchy', 'negative_space', 'semantic_depth', 'motion_cessation'],
                'winner_treatment': False,
            },
            'visual_energy': energy, 'energy_driver': driver,
            'energy_source_ref': source_ref(choreography, '/operations/' + str(i - 1)) if op else refs[0],
            'pause_frame_required': bool(pause),
            'rhythm': ['READ', 'HOLD'] if i == 0 else ['SETTLE', 'READ', 'HOLD'] if stop
                      else ['TRANSFORM', 'SETTLE', 'READ', 'HOLD'] if pause
                      else ['MOVE', 'SETTLE', 'READ'],
            'settle': {
                'required': bool(pause), 'grid': 'shared_source_alignment',
                'motion': 'stopped_during_read', 'unique_focus': True,
                'scope': choreography['resolution']['scope'],
                'unresolved_remains_open': True,
            },
        })
    return states


def direct_transitions(choreography, states, catalog, policy):
    result = []
    by_object = {o['object_id']: o for o in catalog}
    for i, (tr, op) in enumerate(zip(choreography['state_transitions'], choreography['operations'])):
        before, after = states[i:i + 2]
        source_before, source_after = choreography['states'][i:i + 2]
        a, b = source_before['consequence'], source_after['consequence']
        if a['active_scope'] != b['active_scope']:
            reason = 'attention_scope_changed'
        elif before['focus_objects'] != after['focus_objects']:
            reason = 'logical_object_changed'
        elif (a['structural_groups'] != b['structural_groups'] or a['route_node_ids'] != b['route_node_ids']):
            reason = 'spatial_relation_readability'
        else:
            reason = None
        camera = 'hold'
        if reason and after['cognitive_state'] != 'STOP':
            camera = {'anchor': 'snap_to_anchor', 'scan': 'traverse', 'jump': 'traverse',
                      'overlay': 'depth_focus', 'peel': 'spatial_carry', 'fold': 'spatial_carry',
                      'extract': 'spatial_carry', 'restore': 'spatial_carry'}.get(op['verb'], 'reframe')
        if camera == 'hold':
            # A fixed camera cannot silently change its abstract distance.
            after['camera_scope'] = before['camera_scope']
        common = [o for o in before['focus_objects'] if o in after['focus_objects'] and o in tr['carry_objects']]
        candidate_universe = [o['object_id'] for o in catalog if o['kind'] == 'original_question_options']
        continuity = next(iter(common or candidate_universe or before['reality_scope']), None)
        if continuity not in tr['carry_objects']:
            continuity = next(iter(tr['carry_objects']), None)
        camera_intent = {
            'strategy': camera, 'from_scope': before['camera_scope'], 'to_scope': after['camera_scope'],
            'reason': reason if camera != 'hold' else None,
            'attention_objects': deepcopy(after['focus_objects']),
            'source_transition_ref': source_ref(choreography, '/state_transitions/' + str(i)),
        }
        collapse = (choreography['collapse']['supported']
                    and choreography['collapse']['transition']['operation_id'] == op['operation_id'])
        relation = op['verb'] == 'rewire' and op['relation_id'] is not None
        accent = None
        if collapse or relation:
            accent = {
                'kind': 'collapse_punctuation' if collapse else 'relation_reveal',
                'source_event_ref': source_ref(choreography, '/payoff_event' if collapse else '/operations/' + str(i)),
                'objects': deepcopy(after['focus_objects']),
            }
        mode = 'logic_match_cut' if collapse and choreography['payoff_event'] else 'continuous_transformation'
        depth = ['semantic_layer_separation', 'attention_depth_hierarchy'] if op['family'] in (
            'reduction', 'comparison', 'relationship', 'routing') and op['verb'] not in ('seal', 'lock') else []
        deferred = [o['object_id'] for o in catalog if source_after['object_states'][o['object_id']] == 'defer']
        restored = [oid for oid in source_before['present_objects']
                    if source_before['object_states'][oid] == 'defer'
                    and source_after['object_states'][oid] in ('preserve', 'focus')]
        result.append({
            'from_state': tr['from_state'], 'to_state': tr['to_state'], 'operation_id': op['operation_id'],
            'cognitive_operation': {'family': op['family'], 'verb': op['verb']},
            'source_operation_ref': source_ref(choreography, '/operations/' + str(i)),
            'camera_intent': camera_intent,
            'spatial_intent': {
                'kind': policy['operation_intents'][op['family']][op['verb']],
                'target_objects': deepcopy(op['target_objects']),
                'deferred_objects': deferred, 'deferred_treatment': 'suspend_recoverably',
                'restored_objects': restored, 'same_source_space': True,
            },
            'continuity_object': continuity,
            'continuity_visual_id': by_object[continuity]['visual_object_id'] if continuity else None,
            'carry_objects': deepcopy(tr['carry_objects']),
            'mode': mode, 'cut_reason': 'payoff_punctuation' if mode == 'logic_match_cut' else None,
            'visual_accent': accent, 'depth_intents': depth,
            'settle_required': after['pause_frame_required'],
            'temporal_character': op['temporal_character'],
            'composition_consequence': {
                'before_sha': sha(before['composition_intent']), 'after_sha': sha(after['composition_intent']),
                'significant': collapse or 'structure_change' in op['cognitive_changes'] or 'scope_change' in op['cognitive_changes'],
                'source_change_kinds': deepcopy(op['cognitive_changes']),
            },
        })
    return result


def direct_shots(states, transitions, policy):
    groups = [[]]
    for i, state in enumerate(states):
        if i and transitions[i - 1]['mode'] == 'logic_match_cut': groups.append([])
        groups[-1].append(state)
    shots = []
    for i, group in enumerate(groups):
        ids = [s['state_id'] for s in group]
        ops = [t for t in transitions if t['to_state'] in ids]
        grammar = ['semantic_carry']
        if any(s['cognitive_state'] == 'ANCHOR' for s in group): grammar.append('evidence_develop')
        if any(s['composition_intent']['character'] in ('aligned', 'compressed') for s in group): grammar.append('magnetic_alignment')
        if any(s['pause_frame_required'] for s in group): grammar.append('micro_lock')
        if any(s['cognitive_state'] == 'STOP' for s in group): grammar.append('boundary_seal')
        if any(s['camera_scope'] in ('close', 'focus') for s in group): grammar.append('focus_breathing')
        shots.append({
            'shot_id': 'attention-shot-' + str(i + 1).zfill(3), 'source_states': ids,
            'shot_function': 'continuous_attention_encounter',
            'reality_layer': deepcopy(group[0]['reality_scope']),
            'composition_intent': [{'state_id': s['state_id'], **deepcopy(s['composition_intent'])} for s in group],
            'camera_intent': [deepcopy(t['camera_intent']) for t in ops],
            'focus_intent': [{'state_id': s['state_id'], **deepcopy(s['focus_intent'])} for s in group],
            'depth_intent': [{'state_id': s['state_id'], 'spatial_layers': deepcopy(s['spatial_layers'])} for s in group],
            'motion_grammar': grammar, 'pause_frame_required': any(s['pause_frame_required'] for s in group),
            'rhythm': [{'state_id': s['state_id'], 'phases': deepcopy(s['rhythm'])} for s in group],
            'effect_budget': deepcopy(policy['effect_budget']),
            'effect_intents': [
                {'operation_id': t['operation_id'], 'structural': t['spatial_intent']['kind'],
                 'source_operation_ref': deepcopy(t['source_operation_ref']),
                 'depth': deepcopy(t['depth_intents']), 'accent': deepcopy(t['visual_accent'])}
                for t in ops
            ],
            'independent_title_ref': None, 'step_label_ref': None, 'card_panel_intent': False,
            'entry_only_motion': False, 'whole_screen_reset': False,
        })
    return shots


def carry_and_restore(choreography, states, catalog):
    lineage, restore = [], []
    for obj in catalog:
        oid = obj['object_id']
        encounters = []
        for state in states:
            placement = next(p for p in state['object_placements'] if p['object_id'] == oid)
            encounters.append({
                'state_id': state['state_id'], 'visual_object_id': obj['visual_object_id'],
                'plane': placement['plane'], 'source_disposition': placement['source_disposition'],
                'content_sha': obj['source_content_sha'],
            })
        row = {k: obj[k] for k in ('object_id', 'visual_object_id', 'origin_object_id', 'source_content_sha')}
        lineage.append({**row, 'source_lineage_ref': source_ref(choreography, '/object_lineage/' + str(len(lineage))),
                        'encounters': encounters})
        deferred = [s['state_id'] for s in encounters if s['source_disposition'] == 'defer']
        if deferred:
            restored = [op['operation_id'] for op in choreography['operations']
                        if op['verb'] == 'restore' and oid in op['target_objects']]
            restore.append({**row, 'from_plane': 'latent_plane', 'return_plane': 'reading_plane',
                            'spatial_intent': 'same_object_restore', 'deferred_state_ids': deferred,
                            'restore_operation_ids': restored,
                            'status': 'restored_same_object' if restored else 'available_not_executed'})
    return lineage, restore
