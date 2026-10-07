"""Opt-in visual direction from current frozen choreography and experience."""
from copy import deepcopy

from video_contracts import sha, seal
from method_choreography import validate_choreography
from method_choreography.synthetic import validate_synthetic_peel
from .policy import VERSION, SCHEMA, HUMAN_DIMENSIONS, policy, semantic_payload
from .visual import (
    source_ref, visual_catalog, direct_states, direct_transitions, direct_shots, carry_and_restore,
)
from .qa import audit_direction


def compile_direction(choreography, experience, plan, copy_handoff, motion_handoff,
                      bundle, status, *, application=None, diagnostic=False):
    if type(diagnostic) is not bool:
        raise ValueError('Explicit diagnostic choice required')
    gate = validate_choreography(choreography, experience, plan, copy_handoff, motion_handoff,
                                 bundle, status, application=application)
    if choreography['compilation_status'] != 'PASS':
        raise ValueError('Failed choreography cannot acquire visual direction')
    if not gate['consumption_allowed'] and not diagnostic:
        raise ValueError('Current READY choreography required; HOLD permits explicit diagnosis only')
    return _direct(choreography, experience, gate['consumption_allowed'] and not diagnostic,
                   diagnostic=diagnostic, synthetic_window=None)


def compile_synthetic_direction(choreography, fixture, *, restore=True, test_window_seconds=30):
    if (type(test_window_seconds) not in (int, float)
            or not 20 <= test_window_seconds <= 40):
        raise ValueError('Synthetic 20–40 second planning window required')
    validate_synthetic_peel(choreography, fixture, restore=restore)
    return _direct(choreography, None, False, diagnostic=True,
                   synthetic_window=test_window_seconds, synthetic_restore=restore)


def _direct(choreography, experience, eligible, *, diagnostic, synthetic_window, synthetic_restore=None):
    rules, policy_bindings = policy()
    catalog = visual_catalog(choreography)
    states = direct_states(choreography, experience, catalog)
    transitions = direct_transitions(choreography, states, catalog, rules)
    shots = direct_shots(states, transitions, rules)
    lineage, restores = carry_and_restore(choreography, states, catalog)
    memory = choreography['memory_closure']
    closure, stamp = None, None
    if memory is not None:
        closure = {
            'source_ref': source_ref(choreography, '/memory_closure'),
            'state_id': memory['state_id'],
            'mental_thumbnail': {
                'objects': deepcopy(memory['remembered_objects']),
                'action_pattern': deepcopy(memory['action_pattern']),
                'first_action_ref': deepcopy(memory['first_action_ref']),
                'memory_phrase_ref': deepcopy(memory['memory_phrase_ref']),
                'new_teaching_text_created': False, 'student_retention_certified': False,
            },
        }
        if memory['method_stamp_ref'] is not None:
            stamp = {
                'state_id': memory['state_id'], 'source_ref': deepcopy(memory['method_stamp_ref']),
                'after_operation_id': choreography['intervention']['transitions'][-1]['operation_id'],
                'style': 'small_editorial_metadata', 'show_internal_method_id': False,
                'logo_reveal': False,
            }
    gaps = []
    for i, relation in enumerate(choreography['relation_catalog']):
        if relation['endpoint_mapping'] == 'assertion_only_no_actor_span_geometry':
            gaps.append({
                'code': 'RELATION_ENDPOINT_SPANS_UNAVAILABLE',
                'source_ref': source_ref(choreography, '/relation_catalog/' + str(i)),
                'blocking_current_coarse_plan': False, 'not_generated': 'actor_endpoint_graph',
            })
    synthetic = choreography['source']['kind'] == 'synthetic_contract_test'
    source = deepcopy(choreography['source'])
    source['production_eligible'] = eligible
    source['kind'] = 'synthetic_contract_test' if synthetic else 'current_v04' if eligible else 'diagnostic_current_v04_hold'
    binding = {
        **deepcopy(choreography['binding']), **policy_bindings,
        'choreography_sha': choreography['choreography_sha'],
        'choreography_contract': choreography['schema_version'],
        'student_script_sha': experience['script_sha'] if experience is not None else None,
    }
    result = {
        'schema': SCHEMA, 'schema_version': VERSION, 'kind': 'cognitive_direction',
        'mother_direction': 'Swiss Cognitive POV', 'binding': binding, 'source': source,
        'experience_kind': 'action_demo' if not choreography['collapse']['supported'] else choreography['experience_kind'],
        'reality_layer': {
            'object_ids': deepcopy(choreography['states'][0]['reality_objects']),
            'source_ref': source_ref(choreography, '/states/0/reality_objects'),
            'persistent': True, 'first_encounter': True,
            'upper_anchor_objects': [o['object_id'] for o in catalog if o['kind'] == 'original_question_stem'],
        },
        'object_catalog': catalog, 'visual_lineage': lineage, 'restore_paths': restores,
        'states': states, 'transitions': transitions, 'shots': shots,
        'collapse': {
            'source_ref': source_ref(choreography, '/collapse'),
            'supported': choreography['collapse']['supported'],
            'scope': choreography['collapse']['scope'],
            'transition_operation_id': choreography['collapse']['transition']['operation_id']
                if choreography['collapse']['transition'] else None,
            'decision_completion': choreography['collapse']['decision_completion'],
        },
        'payoff_event_ref': source_ref(choreography, '/payoff_event') if choreography['payoff_event'] else None,
        'stop': {
            'source_ref': source_ref(choreography, '/stop'),
            'state_id': choreography['stop']['reached_state'],
            'scope': choreography['stop']['scope'],
            'unresolved_objects': deepcopy(choreography['stop']['unresolved_objects']),
            'deferred_objects': deepcopy(choreography['stop']['deferred_objects']),
            'current_output_ref': deepcopy(choreography['stop']['current_output_ref']),
            'boundary_coverage_ref': deepcopy(choreography['stop']['boundary_coverage_ref']),
            'prohibited_transition_ref': source_ref(choreography, '/stop/prohibited_transition'),
            'camera_settles': True, 'background_motion_stops': True,
            'active_path_closes': True, 'unresolved_remains_visible': True,
            'final_answer_treatment': False,
        },
        'memory_closure': closure, 'method_stamp': stamp,
        'visual_energy_curve': [{'state_id': s['state_id'], 'energy': s['visual_energy'],
                                 'driver': s['energy_driver'], 'source_ref': deepcopy(s['energy_source_ref'])}
                                for s in states],
        'timing_context': {
            'kind': 'synthetic_test_window' if synthetic else 'semantic_order_pending_execution',
            'duration_seconds': synthetic_window, 'absolute_timing_assigned': False,
            'historical_timing_approval_inherited': False, 'duration_fill': False,
        },
        'unsupported_capabilities': {
            'layout_capability_gap': gaps,
            'execution_capability_gap': ['DIRECTION_V02_AE_RIG_NOT_IMPLEMENTED', 'GLYPH_GEOMETRY_NOT_COMPUTED'],
            'current_native_ae_contract_compatible': False,
        },
        'human_direction_review': {name: 'PENDING' for name in HUMAN_DIMENSIONS},
        'semantic_truth_certification': False, 'actual_visual_review': 'PENDING',
        'release_state': deepcopy(choreography['release_state']),
        'final_answer_allowed': choreography['final_answer_allowed'],
        'execution_allowed': False, 'public_render_ready': False,
        'replay_request': {'diagnostic': diagnostic, 'synthetic_restore': synthetic_restore},
        'generated_at': choreography['generated_at'],
    }
    audit, risks, errors = audit_direction(result, choreography, experience)
    result['audit'] = audit; result['risks'] = risks
    missing = list(choreography['availability']['gaps'])
    if not eligible: missing.append('DIAGNOSTIC_ONLY_NOT_PRODUCTION_READY')
    result['compilation_status'] = 'FAIL' if errors else 'PASS'
    result['availability'] = {
        'status': 'FAIL' if errors else 'HOLD' if missing or risks or not eligible else 'READY',
        'gaps': sorted(set(missing)), 'issues': errors,
    }
    result['direction_sha'] = sha(semantic_payload(result))
    result['direction_id'] = 'direction:' + result['direction_sha']
    result = seal(result)
    from .validation import schema_check
    schema_check(result)
    return result
