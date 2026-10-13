"""Compile a learner path from current Pedagogy 0.4, never teaching truth.

The old Copy producer remains independent. This contract assigns encounters,
source objects, words and silence proposals; it assigns no audiovisual timing.
"""
from copy import deepcopy
import re

from pedagogy import validate_plan, validate_handoff
from video_contracts import ROOT, _validator, pointer, seal, sha, verify_seal
from .realization import question_screen
from .experience_qa import audit_experience

VERSION = '0.4.0'
FUNCTIONS = ('pain', 'interrupt', 'orient', 'focus', 'action', 'tension',
             'collapse', 'payoff', 'stop', 'stamp')
STAGES = ('PAIN', 'INTERRUPT', 'ORIENT', 'FOCUS', 'ACT', 'TENSION',
          'COLLAPSE', 'PAYOFF', 'STOP', 'MEMORY')
OPTION_DEFAULTS = {'include_orient': False, 'include_tension': True,
                   'merge_collapse_payoff': True, 'payoff_delivery': 'silent',
                   'silence_functions': []}


def pedagogy_ref(plan, path):
    return {'plan_id': plan['plan_id'], 'pointer': path, 'sha': sha(pointer(plan, path))}


def experience_semantics(value):
    return {k: v for k,v in value.items() if k not in
            ('experience_id', 'experience_sha', 'generated_at', 'content_sha', 'envelope_sha')}


def final_payload(value):
    return {k: value[k] for k in ('beats', 'experience_curve', 'reality_layer', 'collapse',
            'stop', 'memory_closure', 'silence_candidates', 'work_delta', 'answer_permission')}


def _expanded_motion(handoff):
    catalog = handoff['reference_catalog']
    def expand(value):
        if isinstance(value, dict):
            if set(value) == {'catalog_ref'}: return deepcopy(catalog[value['catalog_ref']])
            return {k: expand(v) for k,v in value.items()}
        if isinstance(value, list): return [expand(v) for v in value]
        return value
    return expand(handoff['cognitive_structure'])


def _source_view(copy, motion, plan, bundle, status, allow_held_plan):
    gate = validate_plan(plan, bundle, status, required_version=VERSION)
    if plan['mode'] not in ('first_touch', 'worked_example'):
        raise ValueError('Experience v0.4 currently supports first_touch / bounded worked_example only')
    if gate['consumption_allowed']:
        if copy is None or motion is None:
            raise ValueError('Current v0.4 Copy and Motion handoffs are required')
        validate_handoff(copy, plan, bundle, status, required_version=VERSION)
        validate_handoff(motion, plan, bundle, status, required_version=VERSION)
        if copy['kind'] != 'pedagogy_copy_projection' or motion['kind'] != 'pedagogy_motion_projection':
            raise ValueError('Explicit Copy and Motion handoff roles required')
        view = {k: deepcopy(copy[k]) for k in ('learning_unit', 'primary_action', 'original_question',
                'original_question_refs', 'method_stamp', 'work_delta', 'payoff', 'must_obtain',
                'evidence_refs', 'remaining_object_ids', 'answer_permission', 'do_not_say')}
        view['cognitive_structure'] = _expanded_motion(motion)
        source = {'status': 'CURRENT_HANDOFFS_VERIFIED', 'copy_content_sha': copy['content_sha'],
                  'motion_content_sha': motion['content_sha'], 'current_upstream_verified': True}
    else:
        if not allow_held_plan or copy is not None or motion is not None:
            raise ValueError('HOLD allows only an explicit diagnostic Plan view; no fabricated handoffs')
        # This is a named diagnostic input, not a sealed/approved Handoff.
        # Only already compiled public fields are projected. It never grants
        # consumption or adds a missing Baseline, Payoff or disclosure review.
        view = {'learning_unit': deepcopy(plan['first_touch']), 'primary_action': deepcopy(plan['primary_action']),
            'original_question': deepcopy(plan['original_question']),
            'original_question_refs': deepcopy(plan['original_question_refs']),
            'method_stamp': deepcopy(plan['method_stamp']), 'work_delta': deepcopy(plan['work_delta']),
            'payoff': {k: deepcopy(plan['payoff'][k]) for k in
                       ('structural_before', 'structural_after', 'allowed_claim', 'payoff_scope')},
            'must_obtain': deepcopy(plan['boundary_presentations']),
            'evidence_refs': deepcopy(plan.get('boundary_delivery', {}).get('focus_evidence_refs', plan['evidence_refs'])),
            'remaining_object_ids': deepcopy(plan['student_model']['uncertainty_remaining']),
            'answer_permission': {'answer': None, 'may_output_final_answer': False},
            'do_not_say': deepcopy(plan['payoff']['forbidden_claims']),
            'cognitive_structure': deepcopy(plan['cognitive_structure'])}
        source = {'status': 'DIAGNOSTIC_UPSTREAM_HOLD', 'copy_content_sha': None,
                  'motion_content_sha': None, 'current_upstream_verified': True}
    return view, source, gate


def _line(plan, path):
    value = pointer(plan, path)
    text = value['text'] if isinstance(value, dict) else value
    if not isinstance(text, str) or not text.strip(): return None
    return {'text': text, 'pedagogy_refs': [pedagogy_ref(plan, path)], 'wording': 'literal_projection'}


def _options(options):
    options = deepcopy(options or {})
    if not isinstance(options, dict) or set(options) - set(OPTION_DEFAULTS):
        raise ValueError('Experience options cannot contain Creative or voice-engine parameters')
    result = {**deepcopy(OPTION_DEFAULTS), **options}
    for key in ('include_orient', 'include_tension', 'merge_collapse_payoff'):
        if type(result[key]) is not bool: raise ValueError('Explicit experience choices required')
    if result['payoff_delivery'] not in ('silent', 'literal'):
        raise ValueError('Payoff delivery is silent or the literal allowed claim')
    silence = result['silence_functions']
    if (not isinstance(silence, list) or any(not isinstance(f,str) for f in silence)
            or len(silence) != len(set(silence)) or any(f not in ('collapse', 'payoff', 'stop') for f in silence)):
        raise ValueError('Silence may only propose supported settling beats')
    return result


def _drafts(plan, view, drafts):
    drafts = deepcopy(drafts or {})
    allowed = {'pain': ('/first_touch/pain', '/original_question'),
        'interrupt': ('/first_touch/first_signal', '/primary_action/instruction'),
        'orient': ('/first_touch/first_signal', '/primary_action/instruction', '/student_model/attention'),
        'focus': ('/first_touch/first_signal', '/student_model/attention'),
        'action': ('/primary_action/instruction',), 'payoff': ('/payoff/allowed_claim',),
        'stop': ('/boundary_presentations', '/answer_scope', '/stop_state'),
        'memory': ('/first_touch/memory_phrase', '/primary_action/instruction')}
    if not isinstance(drafts, dict) or set(drafts) - set(allowed):
        raise ValueError('Draft cannot replace Work Delta, Evidence, objects, Role or Stop')
    for function, line in drafts.items():
        if (not isinstance(line, dict) or set(line) != {'text', 'pedagogy_refs'}
                or not isinstance(line['text'], str) or not line['text'].strip()
                or not isinstance(line['pedagogy_refs'], list) or not line['pedagogy_refs']):
            raise ValueError('Every draft needs text and exact visible Pedagogy references')
        if function == 'memory' and view['learning_unit']['memory_phrase'] is None:
            raise ValueError('Memory cannot invent an absent upstream phrase')
        for ref in line['pedagogy_refs']:
            if not isinstance(ref,dict): raise ValueError('Exact Pedagogy reference required')
            path = ref.get('pointer', '')
            if not isinstance(path,str): raise ValueError('Exact visible pointer required')
            try: actual = pedagogy_ref(plan, path)
            except (KeyError,IndexError,TypeError,ValueError): actual = None
            if not any(path == p or path.startswith(p + '/') for p in allowed[function]) or ref != actual:
                raise ValueError('Draft references an unapproved field or changed Pedagogy')
        required = {'action': '/primary_action/instruction', 'payoff': '/payoff/allowed_claim',
                    'memory': '/first_touch/memory_phrase'}.get(function)
        if required and not any(r['pointer'] == required for r in line['pedagogy_refs']):
            raise ValueError('Draft must bind its assigned primary action / claim / memory')
        if function == 'payoff' and view['payoff']['allowed_claim'] is None:
            raise ValueError('Unsupported payoff cannot acquire a line or scene')
        if function == 'orient' and not view['cognitive_structure']['focus_objects']:
            raise ValueError('Orient requires upstream focus objects')
        if function == 'interrupt':
            # The Handoff has no generic Anti-rule authoring channel. A negative
            # directive must already exist, not be inferred from a nice hook.
            if not any(isinstance(pointer(plan, r['pointer']), dict)
                and re.match(r'^(?:先别|不要|别)', pointer(plan, r['pointer']).get('text', ''))
                for r in line['pedagogy_refs']):
                raise ValueError('Interrupt cannot create a new Anti-rule')
        line['wording'] = 'review_candidate'
    return drafts


def _review_valid(review, plan, script_sha, final_copy_sha):
    return (isinstance(review, dict) and review.get('schema_version') == VERSION
        and review.get('source_plan_sha') == plan['plan_sha']
        and review.get('status') == 'pass' and review.get('script_sha') == script_sha
        and review.get('final_copy_sha') == final_copy_sha
        and isinstance(review.get('reviewer'), str) and bool(review['reviewer'].strip())
        and review.get('reviewer_kind') in ('ai_host', 'human')
        and all(review.get('checks', {}).get(k) == 'pass'
                for k in ('semantic_fidelity', 'natural_speech', 'layer_division')))


def realize_experience(copy_projection, motion_projection, plan, bundle, status, *,
                       draft_lines=None, copy_review=None, options=None, allow_held_plan=False):
    if type(allow_held_plan) is not bool: raise ValueError('Explicit diagnostic choice required')
    view, upstream, gate = _source_view(copy_projection, motion_projection, plan, bundle, status, allow_held_plan)
    if view['primary_action'] is None or plan['primary_action_count'] != 1:
        raise ValueError('Experience requires one primary action; independent actions cannot be hidden')
    choices = _options(options); drafts = _drafts(plan, view, draft_lines)
    structure = view['cognitive_structure']; objects = structure['objects']
    unresolved = [o['object_id'] for o in objects if o['state'] == 'unresolved']
    primary = view['primary_action']
    supported = (view['work_delta']['status'] == 'SUPPORTED_REVIEWED_STRUCTURE'
        and view['payoff']['allowed_claim'] is not None and view['payoff']['structural_before'] is not None
        and view['payoff']['structural_after'] is not None)
    functions = {'pain': _line(plan, '/first_touch/pain') if view['learning_unit']['pain'] else None,
        'interrupt': None, 'orient': None, 'focus': None,
        'action': _line(plan, '/primary_action/instruction') if primary else None,
        'payoff': _line(plan, '/payoff/allowed_claim') if supported and choices['payoff_delivery'] == 'literal' else None,
        'stop': None, 'memory': None}
    # Preserve an existing interrupt directive if the Handoff really provides it.
    signal = view['learning_unit']['first_signal']
    if signal and re.match(r'^(?:先别|不要|别)', signal['text']):
        functions['interrupt'] = _line(plan, '/first_touch/first_signal')
    functions.update(drafts)
    original = question_screen(view['original_question'])
    reality = {'question': deepcopy(view['original_question']), 'screen_copy': original,
        'field_refs': deepcopy(view['original_question_refs']), 'persistent': True,
        'fact_mutation_allowed': False, 'pedagogy_ref': pedagogy_ref(plan, '/original_question'),
        'visibility_review': 'PENDING'}
    binding = {'plan_id': plan['plan_id'], 'plan_sha': plan['plan_sha'],
               'pedagogy_contract': VERSION, 'analysis_sha': plan['source_analysis_sha']}
    attention = {'focus_objects': deepcopy(structure['focus_objects']),
        'background_objects': deepcopy(structure['backgroundable_objects']),
        'preserve_objects': deepcopy(structure['preserved_objects']), 'unresolved_objects': unresolved}
    work = {k: deepcopy(view['work_delta'][k]) for k in
            ('baseline_kind', 'baseline_measured', 'learner_transfer_validated', 'scope', 'status')}
    work['unsupported_savings'] = [r['claim_key'] for r in plan['work_delta']['unsupported_savings']]
    for key in ('baseline_work', 'removed_work', 'deferred_work', 'still_required_work'):
        rows = view['work_delta'][key]
        work[key] = None if rows is None else [row['work_id'] for row in rows]
    stop = {'current_output': deepcopy(view['learning_unit']['immediate_output']),
        'scope': view['payoff']['payoff_scope'] or 'method_action_demo', 'unresolved': unresolved,
        'deferred_work': deepcopy(work['deferred_work']), 'still_required_work': deepcopy(work['still_required_work']),
        'prohibited_next_inference': deepcopy(view['do_not_say']),
        'boundary_presentations': deepcopy(view['must_obtain']),
        'pedagogy_refs': [pedagogy_ref(plan, p) for p in
                          ('/boundary_presentations', '/answer_scope', '/work_delta', '/stop_state')]}
    focus = {'object_ids': deepcopy(structure['focus_objects']),
        'scope_before': deepcopy(structure['attention_transition']['from_scope']),
        'scope_after': deepcopy(structure['attention_transition']['to_scope']),
        'reason_ref': pedagogy_ref(plan, '/student_model/attention')}
    collapse = {'supported': supported, 'reduction_type': deepcopy(plan['cognitive_reduction']['types']),
        'before_state': deepcopy(view['payoff']['structural_before']),
        'after_state': deepcopy(view['payoff']['structural_after']), 'learner_visible': False,
        'scope': view['payoff']['payoff_scope'], 'work_delta_ref': pedagogy_ref(plan, '/work_delta'),
        'observation_scope': 'planned_screen_structure_not_rendered_or_psychological_measurement'}
    memory = {'first_action_ref': pedagogy_ref(plan, '/primary_action'),
        'memory_phrase': _line(plan, '/first_touch/memory_phrase') if view['learning_unit']['memory_phrase'] else None,
        'method_name': _line(plan, '/method_stamp') if view['method_stamp'] else None,
        'name_after_action_required': True, 'student_retention_certified': False}
    beats, curve = [], []
    def add(function, stages, before, after, paths, *, copy=None, frame=None, silence=None):
        refs = [pedagogy_ref(plan, p) for p in paths]
        bid = 'experience-' + str(len(beats) + 1).zfill(3)
        beat = {'beat_id': bid, 'cognitive_function': function, 'learner_state_before': before,
            'learner_state_after': after, 'vo': deepcopy(functions.get(function)),
            'screen': {'copy': deepcopy(copy or []), 'object_ids': deepcopy(attention['preserve_objects']),
                'structural_state': deepcopy(frame), 'reality_layer_ref': '/reality_layer'},
            'experience': {'attention_intent': deepcopy(attention),
                'tension_state': {'unresolved_objects': deepcopy(unresolved), 'source_refs': [pedagogy_ref(plan, '/student_model/uncertainty_remaining')]}
                    if 'TENSION' in stages else None,
                'reduction_state': deepcopy(collapse) if 'COLLAPSE' in stages else None,
                'payoff_state': {'scope': collapse['scope'], 'allowed_claim_ref': pedagogy_ref(plan, '/payoff/allowed_claim'),
                                 'supported': True} if 'PAYOFF' in stages else None,
                'unresolved_state': deepcopy(unresolved)},
            'delivery_intent': {'cognitive_state': after, 'speech_function': function,
                'desired_character': ['concise', 'alert', 'direct'], 'voice_execution': False},
            'silence_candidate': None, 'boundary_ids': [], 'source_binding': deepcopy(binding),
            'pedagogy_refs': refs}
        if silence:
            beat['silence_candidate'] = {'event': silence, 'duration_range_seconds': [0.3, 1.0],
                'cognitive_reason': 'let_the_bound_state_settle', 'pedagogy_refs': deepcopy(refs),
                'final_timing_owner': 'creative_or_premiere', 'absolute_timing_assigned': False}
        beats.append(beat)
        curve.extend({'stage': stage, 'beat_id': bid, 'pedagogy_refs': deepcopy(refs),
                      'observation_scope': 'planned_learner_path_only'} for stage in stages)
        return beat
    add('pain', ['PAIN'], 'encounter', 'blocked', ['/original_question', '/first_touch/pain'],
        frame=view['payoff']['structural_before'] if supported else None)
    if functions['interrupt']:
        add('interrupt', ['INTERRUPT'], 'blocked', 'interrupted', [r['pointer'] for r in functions['interrupt']['pedagogy_refs']])
    if choices['include_orient'] or functions['orient']:
        add('orient', ['ORIENT'], 'encounter', 'oriented', ['/first_touch/first_signal', '/student_model/attention'])
    evidence_copy = []
    for ref in view['evidence_refs']:
        evidence = pointer(bundle, ref['pointer'])
        evidence_copy.append({'text': evidence['quote'], 'pedagogy_refs': [pedagogy_ref(plan, '/evidence_refs')],
            'source_refs': [deepcopy(ref)], 'kind': 'literal_evidence'})
    add('focus', ['FOCUS'], 'oriented', 'focused', ['/student_model/attention', '/evidence_refs'], copy=evidence_copy)
    if primary:
        stages = ['ACT'] + (['TENSION'] if unresolved and choices['include_tension'] else [])
        add('action', stages, 'focused', 'acting', ['/primary_action', '/primary_simplification',
            '/student_model/uncertainty_remaining'], copy=evidence_copy)
    if supported:
        stages = ['COLLAPSE'] + (['PAYOFF'] if choices['merge_collapse_payoff'] else [])
        beat = add('collapse', stages, 'acting', 'reduced', ['/primary_simplification', '/work_delta', '/payoff'],
                   frame=view['payoff']['structural_after'], silence='collapse')
        if choices['merge_collapse_payoff']:
            beat['vo'] = deepcopy(functions['payoff'])
        else:
            add('payoff', ['PAYOFF'], 'reduced', 'settled', ['/payoff/allowed_claim', '/work_delta'], silence='payoff')
    stop_beat = add('stop', ['STOP'], 'reduced' if supported else 'acting', 'stopped',
                   ['/stop_state', '/answer_scope', '/boundary_presentations', '/work_delta'], silence='boundary_seal')
    if memory['memory_phrase'] and primary:
        screen = [{'text': memory['memory_phrase']['text'], 'pedagogy_refs': memory['memory_phrase']['pedagogy_refs'],
                   'source_refs': [], 'kind': 'memory'}]
        if memory['method_name']:
            screen.append({'text': memory['method_name']['text'], 'pedagogy_refs': memory['method_name']['pedagogy_refs'],
                           'source_refs': [], 'kind': 'method_name'})
        add('stamp', ['MEMORY'], 'stopped', 'remembered', ['/primary_action', '/first_touch/memory_phrase', '/method_stamp'], copy=screen)
        beats[-1]['vo'] = deepcopy(functions['memory'])
    # Coverage stays at the approved semantic beat, never appended as a new
    # reminder wall. Full original guards remain upstream, not extra VO.
    for i, presentation in enumerate(view['must_obtain']):
        target = next((b for b in beats if b['cognitive_function'] == presentation['scene']), None)
        if target is None: raise ValueError('Required boundary has no approved encounter beat')
        target['boundary_ids'].append(presentation['item_id'])
        ref = pedagogy_ref(plan, '/boundary_presentations/' + str(i))
        expression = presentation['coverage']['displayed_expression']
        spoken = presentation['spoken_readout_required'] or presentation['delivery_form'] == 'spoken'
        if spoken:
            if target['vo'] is not None and target['vo']['text'] != expression['text']:
                raise ValueError('Required spoken boundary cannot be replaced by action copy or silence')
            target['vo'] = {'text': expression['text'], 'pedagogy_refs': [ref], 'wording': 'literal_projection'}
        else:
            target['screen']['copy'].append({'text': expression['text'], 'pedagogy_refs': [ref],
                'source_refs': [deepcopy(p['source_ref']) for p in presentation['coverage']['parts']],
                'kind': 'reviewed_boundary'})
        target['pedagogy_refs'].append(ref)
    for beat in beats:
        if beat['cognitive_function'] in choices['silence_functions']:
            if beat['vo'] is not None:
                raise ValueError('Silence cannot suppress a required or explicitly proposed line')
        if functions.get(beat['cognitive_function']) is not None and beat['cognitive_function'] == 'focus':
            beat['vo'] = deepcopy(functions['focus'])
    result = {'schema_version': VERSION, 'kind': 'student_pov_experience',
        'source_pedagogy_plan': binding, 'upstream': upstream, 'method_id': plan['method_id'],
        'method_version': plan['method_version'], 'question_id': plan['question_id'], 'role': plan['role'],
        'mode': plan['mode'], 'experience_kind': 'cognitive_payoff' if supported else 'action_demo',
        'first_action': deepcopy(primary), 'focus': focus, 'work_delta': work, 'collapse': collapse,
        'stop': stop, 'memory_closure': memory, 'beats': beats, 'experience_curve': curve,
        'reality_layer': reality, 'answer_permission': deepcopy(view['answer_permission']),
        'silence_candidates': [{'beat_id': b['beat_id'], **deepcopy(b['silence_candidate'])}
                              for b in beats if b['silence_candidate']],
        'timing': {'owner': 'creative_or_premiere', 'absolute_timing_assigned': False,
                   'fixed_duration_fill': False, 'historical_timing_approval_inherited': False},
        'human_taste_review': {'status': 'PENDING', 'self_signed': False},
        'release_state': deepcopy(plan['release_state']), 'public_render_ready': False,
        'realization_request': {'draft_lines': {k:{p:v for p,v in line.items() if p != 'wording'}
                                               for k,line in drafts.items()},
            'copy_review': deepcopy(copy_review), 'options': choices, 'allow_held_plan': allow_held_plan},
        'generated_at': plan['generated_at']}
    audit, flags, errors = audit_experience(result, view, plan)
    result['collapse']['learner_visible'] = audit['collapse_visible_in_plan']
    for beat in beats:
        if beat['experience']['reduction_state'] is not None:
            beat['experience']['reduction_state']['learner_visible'] = audit['collapse_visible_in_plan']
    result['script_sha'] = sha(beats); result['final_copy_sha'] = sha(final_payload(result))
    reviewed = _review_valid(copy_review, plan, result['script_sha'], result['final_copy_sha'])
    gaps = []
    if not gate['consumption_allowed']: gaps += ['UPSTREAM_PEDAGOGY_HOLD'] + plan['availability']['gaps'] + plan['availability']['blockers']
    if not reviewed: gaps.append('FINAL_EXPERIENCE_COPY_REVIEW_REQUIRED')
    # A connective result reminder is an editorial warning, not a production hold.
    if set(flags) - {'redundant_result_reminder'}:
        gaps.append('EXPERIENCE_TONE_OR_DUPLICATION_REVIEW_REQUIRED')
    result['experience_audit'] = audit
    result['ai_tone_lint'] = {'flags': flags, 'deterministic_lint_only': True,
        'semantic_truth_certification': False, 'actual_delivery_review': 'PENDING'}
    result['copy_review_state'] = 'EXPLICIT_CURRENT_CREDENTIAL' if reviewed else 'PENDING'
    result['compilation_status'] = 'FAIL' if errors else 'PASS'
    result['availability'] = {'status': 'FAIL' if errors else 'HOLD' if gaps else 'READY',
                              'gaps': sorted(set(gaps)), 'issues': sorted(set(errors))}
    result['experience_sha'] = sha(experience_semantics(result))
    result['experience_id'] = 'student-experience:' + result['experience_sha']
    return seal(result)


def inspect_experience(value):
    from jsonschema import ValidationError
    path = ROOT / 'creative/copy-system/student-pov-experience.v0.4.schema.json'
    try: _validator(str(path), path.stat().st_mtime_ns).validate(value)
    except ValidationError as error: raise ValueError('Invalid Student POV Experience schema: ' + error.message) from error
    verify_seal(value)
    if value['experience_sha'] != sha(experience_semantics(value)) \
            or value['experience_id'] != 'student-experience:' + value['experience_sha']:
        raise ValueError('Experience semantic binding mismatch')
    if value['script_sha'] != sha(value['beats']) or value['final_copy_sha'] != sha(final_payload(value)):
        raise ValueError('Experience final copy lock mismatch')
    return {'status': 'HISTORICAL_ONLY', 'contract_status': 'CURRENT_CONTRACT',
        'contract_version': VERSION, 'current_contract_version': VERSION,
        'current_upstream_verified': False, 'consumption_allowed': False, 'public_render_ready': False}


def validate_experience(value, copy_projection, motion_projection, plan, bundle, status):
    inspect_experience(value)
    expected = realize_experience(copy_projection, motion_projection, plan, bundle, status, **value['realization_request'])
    if expected != value:
        raise ValueError('Experience differs from current Pedagogy, lexical content or approved learner path')
    return {'status': 'PASS', 'current_upstream_verified': True,
            'consumption_allowed': value['availability']['status'] == 'READY', 'public_render_ready': False}
