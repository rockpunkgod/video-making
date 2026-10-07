"""HOW IT FEELS after Pedagogy approval; never WHAT TO TEACH again."""
from copy import deepcopy
import re

from video_contracts import pointer, seal, sha
from pedagogy import validate_handoff
from .payoff import supported_payoff
from .qa import lint_copy, planned_scene_observations

VERSION = '0.2.0'
FUNCTIONS = ('pain', 'interrupt', 'focus', 'action', 'collapse', 'payoff', 'stop', 'stamp')
SIGNATURES = {'R01': 'overgrowth', 'R02': 'relation_rewire', 'R06': 'missing_mass',
              'R09': 'semantic_compression', 'F01': 'axis_regroup', 'G01': 'extract_route_seal'}
SILENCE_EVENTS = ('collapse', 'answer_lock', 'evidence_lock', 'boundary_seal',
                  'payoff', 'transformation')


def _ref(plan, path):
    return {'plan_id': plan['plan_id'], 'pointer': path, 'sha': sha(pointer(plan, path))}


def _line(plan, path, text=None):
    value = pointer(plan, path)
    if text is None:
        text = value['text'] if isinstance(value, dict) else value
    return {'text': text, 'pedagogy_refs': [_ref(plan, path)]}


def copy_semantics(copy):
    return {k: v for k, v in copy.items()
            if k not in ('copy_sha', 'copy_id', 'generated_at', 'content_sha', 'envelope_sha')}


def _reading_seconds(text):
    chinese = len(re.findall(r'[\u3400-\u9fff]', text))
    words = len(re.findall(r'[A-Za-z]+(?:[\x27-][A-Za-z]+)*', text))
    return chinese / 4 + words / 2.5


def _credential(review, script_sha, final_copy_sha):
    return (isinstance(review, dict) and review.get('status') == 'pass'
            and review.get('script_sha') == script_sha
            and review.get('final_copy_sha') == final_copy_sha
            and isinstance(review.get('reviewer'), str) and bool(review['reviewer'].strip())
            and review.get('reviewer_kind') in ('ai_host', 'human')
            and all(review.get('checks', {}).get(k) == 'pass'
                    for k in ('semantic_fidelity', 'natural_speech', 'layer_division')))


def realize(projection, plan, bundle, status, *, draft_lines=None, copy_review=None, adapter=None):
    """Freeze a literal default or a bound natural-copy candidate.

    Adapters receive only the small projection. The runtime never supplies a
    Registry, solver, hidden truth files, or a choice of disclosure tiers.
    An adapter's new wording always needs an explicit final-copy credential.
    """
    validate_handoff(projection, plan, bundle, status)
    if projection['kind'] != 'pedagogy_copy_projection':
        raise ValueError('Student POV requires a Copy-facing projection')
    if adapter is not None:
        if draft_lines is not None:
            raise ValueError('Choose an adapter or explicit candidate lines')
        draft_lines = adapter.propose(deepcopy(projection))
    draft_lines = deepcopy(draft_lines or {})
    allowed_keys = {'pain', 'interrupt', 'focus', 'first_action', 'cognitive_relief_line',
                    'payoff_line', 'stop_vo', 'memory_phrase'}
    if not isinstance(draft_lines, dict) or set(draft_lines) - allowed_keys:
        raise ValueError('Candidate cannot replace boundaries, output, scope, Evidence or method stamp')
    visible_paths = ('/symptom', '/first_signal', '/first_action', '/judgment_point',
        '/memory_phrase', '/original_question', '/evidence_refs', '/public_claims', '/payoff',
        '/boundaries/tell_now', '/answer_scope', '/stop_state', '/student_model/see',
        '/student_model/think', '/student_model/do', '/student_model/check', '/student_model/stop')
    for row in draft_lines.values():
        if (not isinstance(row, dict) or set(row) != {'text', 'pedagogy_refs'}
                or not isinstance(row['text'], str) or not row['text'].strip()):
            raise ValueError('Copy candidate needs nonempty text and existing Pedagogy refs')
        if not row['pedagogy_refs']:
            raise ValueError('Every copy candidate needs a source Plan binding')
        for ref in row['pedagogy_refs']:
            if not any(ref['pointer'] == path or ref['pointer'].startswith(path + '/') for path in visible_paths):
                raise ValueError('Copy candidate cannot consume undisclosed or backend-only Plan fields')
            if ref != _ref(plan, ref['pointer']):
                raise ValueError('Copy candidate source Plan binding changed')
    mandatory_refs = {'first_action': '/first_action', 'memory_phrase': '/memory_phrase'}
    for key, required in mandatory_refs.items():
        if key in draft_lines and not any(r['pointer'] == required for r in draft_lines[key]['pedagogy_refs']):
            raise ValueError('Natural copy must preserve its assigned Pedagogy field')
    payoff_refs = {'/payoff', '/payoff/reviewed_support', '/payoff/reviewed_support/record',
                   '/payoff/reviewed_support/record/allowed_claim',
                   '/payoff/reviewed_support/record/cognitive_relief_line'}
    for key in ('cognitive_relief_line', 'payoff_line'):
        if key in draft_lines and not any(r['pointer'] in payoff_refs for r in draft_lines[key]['pedagogy_refs']):
            raise ValueError('Payoff copy must bind its reviewed payoff and allowed claim')
    if 'stop_vo' in draft_lines and not any(r['pointer'] in ('/boundaries/tell_now', '/stop_state', '/answer_scope')
            for r in draft_lines['stop_vo']['pedagogy_refs']):
        raise ValueError('Stop copy must bind the required boundary or bounded output state')
    payoff, payoff_gaps = supported_payoff(plan, projection)
    issues, gaps = [], list(payoff_gaps)
    if plan['mode'] == 'first_touch' and plan['cognitive_load']['metrics']['core_actions'] != 1:
        issues.append('FIRST_TOUCH_ONE_MAIN_ACTION_REQUIRED')
    script = {
        'pain': _line(plan, '/symptom') if plan['symptom'] else None,
        'interrupt': None,
        'focus': _line(plan, '/first_signal') if plan['first_signal'] else None,
        'first_action': _line(plan, '/first_action') if plan['first_action'] else None,
        'collapse': {'before': deepcopy(projection['payoff_structure']['before_complexity']),
            'after': deepcopy(projection['payoff_structure']['after_structure']),
            'allowed_claim': deepcopy(projection['payoff_structure']['allowed_claim']),
            'structural_reduction_supported': payoff is not None,
            'pedagogy_refs': [_ref(plan, '/payoff')]},
        'cognitive_relief_line': None, 'payoff_line': None,
        'decision_state': {'role': plan['role'], 'answer_scope': deepcopy(plan['answer_scope']),
                           'stop_state': deepcopy(plan['stop_state'])},
        'stop_line': {'text': None, 'boundaries': deepcopy(projection['must_show_boundary']),
                      'pedagogy_refs': [_ref(plan, '/boundaries/tell_now')]},
        'method_stamp': deepcopy(projection['method_stamp']),
        'memory_phrase': _line(plan, '/memory_phrase') if plan['memory_phrase'] else None}
    if payoff:
        prefix = '/payoff/reviewed_support/record/'
        script['collapse'].update(before=deepcopy(payoff['baseline_path']), after=deepcopy(payoff['method_path']),
                                 allowed_claim=_line(plan, prefix + 'allowed_claim'))
        script['cognitive_relief_line'] = _line(plan, prefix + 'cognitive_relief_line')
        script['payoff_line'] = deepcopy(script['cognitive_relief_line'])
        for key in ('interrupt', 'focus'):
            if isinstance(payoff.get(key + '_line'), str):
                script[key] = _line(plan, prefix + key + '_line')
    for key, row in draft_lines.items():
        if key == 'stop_vo':
            script['stop_line']['text'] = row['text']
            script['stop_line']['pedagogy_refs'] += row['pedagogy_refs']
        else:
            script[key] = deepcopy(row)
    # One short delivered payoff. A caller's explicit payoff_line wins; otherwise
    # the bound cognitive relief is the spoken choice, never a second narration.
    if 'payoff_line' not in draft_lines:
        script['payoff_line'] = deepcopy(script['cognitive_relief_line'])
    all_copy = '\n'.join(row['text'] for key, row in script.items()
                         if isinstance(row, dict) and isinstance(row.get('text'), str))
    issues += ['COPY_LINT:' + flag for flag in lint_copy(all_copy, plan['role'],
                                                       plan['answer_scope']['may_output_final_answer'])]
    if re.search(r'(?<![A-Za-z0-9])[RFCGWS]\d{2}(?![A-Za-z0-9])', all_copy):
        issues.append('INTERNAL_METHOD_CODE_ON_CONSUMER_SURFACE')
    # A shortcut is never supported merely because another line says it is scoped.
    if any(word in all_copy for word in ('不用认识', '不用背单词', '不用词汇')):
        shortcut = payoff.get('vocabulary_shortcut') if payoff else None
        if not shortcut or not shortcut.get('scope_label') or not shortcut.get('word_evidence_pointers'):
            issues.append('UNSUPPORTED_VOCABULARY_SHORTCUT')
        if not any(scope in all_copy for scope in ('这一题', '这一步', '当前判断')):
            issues.append('UNSCOPED_VOCABULARY_SHORTCUT')
    snippets = projection['evidence_snippets']
    evidence_text = [s['span']['quote'] for s in snippets]
    sequence = []
    def scene(function, vo, screen, refs, motion='none', removed=None, output=None,
              boundary_ids=None, silence=0.0):
        sequence.append({'scene_id': 'pov-' + str(len(sequence) + 1).zfill(3),
            'cognitive_function': function, 'vo': vo, 'screen_copy': screen,
            'visual_state': 'original_evidence' if function in ('pain', 'focus', 'action') else function,
            'student_attention': function, 'motion_function': motion,
            'evidence_ref': deepcopy(plan['evidence_refs']), 'pedagogy_ref': deepcopy(refs),
            'removed_work': deepcopy(removed or []), 'output_state': deepcopy(output),
            'silence_after': silence, 'tell_now_boundary_ids': list(boundary_ids or []),
            'notes': 'Deterministic source binding; semantic/natural speech and Human Taste review stay separate'})
    baseline_text = [r['text'] for r in payoff['baseline_path']] if payoff else []
    baseline_refs = [_ref(plan, '/payoff/reviewed_support/record/baseline_path')] if payoff else []
    if script['pain']:
        scene('pain', script['pain']['text'], evidence_text + baseline_text,
              script['pain']['pedagogy_refs'] + baseline_refs)
    elif payoff:
        scene('pain', None, evidence_text + baseline_text, baseline_refs)
    if script['interrupt']:
        scene('interrupt', script['interrupt']['text'], [], script['interrupt']['pedagogy_refs'])
    if script['focus']:
        scene('focus', script['focus']['text'], evidence_text, script['focus']['pedagogy_refs'], 'focus_existing_evidence')
    if script['first_action']:
        scene('action', script['first_action']['text'], evidence_text, script['first_action']['pedagogy_refs'],
              SIGNATURES.get(plan['method_id'], 'source_bound_action'))
    scene('collapse', None, [r['text'] for r in payoff['method_path']] if payoff else [],
          [_ref(plan, '/payoff')], 'supported_cognitive_reduction' if payoff else 'actual_output_only_no_payoff_claim',
          payoff['cognitive_work']['removed'] if payoff else [],
          plan['answer_scope']['actual_outputs'])
    # Bound scene builders do not need one scene per cognitive function. The
    # default groups visual Collapse with its short payoff/silence when possible.
    if payoff:
        sequence[-1]['silence_after'] = 0.5
        scene('payoff', script['payoff_line']['text'], [],
              script['payoff_line']['pedagogy_refs'], 'settle', silence=0.5)
    else:
        gaps.append('COGNITIVE_RELIEF_UNAVAILABLE')
    scene('stop', script['stop_line']['text'], [x['text'] for x in projection['must_show_boundary']],
          [_ref(plan, '/boundaries/tell_now'), _ref(plan, '/answer_scope')], 'boundary_seal',
          output=script['decision_state'],
          boundary_ids=[x['item_id'] for x in projection['must_show_boundary']], silence=0.5)
    if script['method_stamp']:
        screen = [script['method_stamp']['text']]
        if script['memory_phrase']:
            screen.append(script['memory_phrase']['text'])
        scene('stamp', None, screen, [_ref(plan, '/method_stamp'), _ref(plan, '/memory_phrase')], 'settle')
    cursor = 0.0
    for row in sequence:
        duration = max(1.2, _reading_seconds(row['vo'] or ''),
                       _reading_seconds('\n'.join(row['screen_copy'])))
        row['time_range'] = [round(cursor, 3), round(cursor + duration, 3)]
        cursor += duration + row['silence_after']
    silence = [{'scene_id': row['scene_id'], 'event': 'boundary_seal' if row['cognitive_function'] == 'stop'
        else row['cognitive_function'], 'duration_seconds': row['silence_after'],
        'purpose': 'let the supported state settle', 'tell_now_visible': bool(row['tell_now_boundary_ids']),
        'pedagogy_ref': deepcopy(row['pedagogy_ref'])} for row in sequence if row['silence_after']]
    if any(s['event'] not in SILENCE_EVENTS or not 0.3 <= s['duration_seconds'] <= 1 for s in silence):
        issues.append('INVALID_SILENCE_CANDIDATE')
    script_sha = sha(sequence)
    final_copy_sha = sha({'script': script, 'final_script': sequence})
    reviewed = _credential(copy_review, script_sha, final_copy_sha)
    if not reviewed:
        gaps.append('FINAL_COPY_SEMANTIC_AND_NATURAL_SPEECH_REVIEW_REQUIRED')
    duplicate = sum(bool(row['vo']) and row['vo'] in row['screen_copy'] for row in sequence)
    boilerplate = sum(bool(row['vo']) and bool(re.search(r'我们可以看到|可以发现|这里说明', row['vo'])) for row in sequence)
    audit = {'first_action_preserved': not bool(draft_lines.get('first_action')) or reviewed,
        'role_preserved': True, 'evidence_preserved': True, 'stop_preserved': True,
        'tell_now_preserved': True, 'payoff_supported': payoff is not None,
        **planned_scene_observations(sequence, payoff, first_action_ref=_ref(plan, '/first_action'),
            payoff_ref=_ref(plan, '/payoff'),
            tell_now_ids=[x['item_id'] for x in projection['must_show_boundary']]),
        'action_language_present': bool(re.search(r'看|圈|划|拆|比|对|找|砍|留|排|停', all_copy)),
        'ai_explanation_density': 'high' if boilerplate > 2 else 'medium' if boilerplate else 'low',
        'expert_chain_leakage': any('expert_chain' in s for s in issues),
        'screen_voice_duplication': 'high' if duplicate > 1 else 'medium' if duplicate else 'low',
        'unsupported_shortcut': any('SHORTCUT' in s for s in issues),
        'prohibited_claim_violation': any('COPY_LINT' in s for s in issues),
        'natural_speech_risk': 'low' if reviewed else 'high',
        'validation_kind': 'deterministic_claim_and_binding_lint_not_semantic_truth_certification',
        'semantic_copy_review': 'EXPLICIT_CREDENTIAL' if reviewed else 'PENDING',
        'human_taste_review': 'PENDING'}
    if duplicate:
        gaps.append('SCREEN_VOICE_DUPLICATION_REVIEW_REQUIRED')
    if not audit['student_pov_present']:
        gaps.append('STUDENT_ACTION_FOCUS_OR_STOP_MISSING')
    if payoff and not audit['cognitive_reduction_visible']:
        gaps.append('COGNITIVE_REDUCTION_NOT_VISIBLE_IN_PLAN')
    availability = 'FAIL' if issues else 'HOLD' if gaps else 'READY'
    comparison = {k: deepcopy(payoff[k]) if payoff else []
                  for k in ('baseline_path', 'method_path', 'removed_steps', 'remaining_steps')}
    copy = {'schema_version': VERSION, 'kind': 'student_pov_copy',
        'source_pedagogy_plan': {'plan_id': plan['plan_id'], 'plan_sha': plan['plan_sha']},
        'source_analysis_sha': plan['source_analysis_sha'], 'question_id': plan['question_id'],
        'method_id': plan['method_id'], 'method_version': plan['method_version'], 'role': plan['role'],
        'mode': plan['mode'], 'payoff_type': payoff['payoff_type'] if payoff else None,
        'student_path_comparison': comparison,
        'cognitive_work': deepcopy(payoff['cognitive_work']) if payoff else
            {'removed': [], 'deferred': [], 'still_required': []},
        'script': script, 'final_script': sequence, 'script_sha': script_sha, 'final_copy_sha': final_copy_sha,
        'silence_candidates': silence, 'tell_now_boundaries': deepcopy(projection['must_show_boundary']),
        'prohibited_claims': deepcopy(projection['do_not_say']), 'evidence_refs': deepcopy(plan['evidence_refs']),
        'source_refs': deepcopy(plan['source_refs']), 'copy_audit': audit,
        'payoff_validation': {'source_payoff_ref': _ref(plan, '/payoff'),
            'actual_reduction': deepcopy(payoff['reduction']) if payoff else None,
            'output_type': plan['role'], 'allowed_claim': payoff['allowed_claim'] if payoff else None,
            'final_copy_claim': script['payoff_line']['text'] if payoff else None,
            'overclaim': bool(issues), 'transferable_first_action': payoff['first_action_transferable'] if payoff else False,
            'status': 'PASS' if payoff and not issues else 'PAYOFF_UNSUPPORTED',
            'semantic_certification': False},
        'motion_copy_coordination': {'signature_family': SIGNATURES.get(plan['method_id']),
            'signature_is_not_teaching_evidence': True,
            'vo': 'thought, first action, current judgment, rhythm, supported payoff, Stop',
            'screen': 'original source, evidence, comparison objects, keywords, candidates, actual output',
            'motion': 'supported extraction, reorganization, scope reduction, relation change, Boundary Seal',
            'decorative_impact_allowed': False, 'method_stamp_position': 'after_value_and_stop'},
        'timing': {'estimated_duration_seconds': round(cursor, 3), 'estimate_version': 'zh4-en150-v1',
                   'fixed_duration_fill': False, 'duration_target': plan['duration_target'], 'status': 'ESTIMATE'},
        'availability': {'status': availability, 'gaps': sorted(set(gaps)), 'issues': sorted(set(issues))},
        'realization_request': {'draft_lines': draft_lines, 'copy_review': deepcopy(copy_review)},
        'teaching_issue_candidates': [{'kind': 'teaching_issue_candidate', 'reason': g,
            'source_payoff_ref': _ref(plan, '/payoff')} for g in payoff_gaps
             if 'missing_reviewed' not in g],
        'human_taste_review': {'status': 'PENDING', 'self_signed': False},
        'generated_at': plan['generated_at'], 'public_render_ready': False}
    copy['copy_sha'] = sha(copy_semantics(copy))
    copy['copy_id'] = 'student-pov:' + copy['copy_sha']
    return seal(copy)


class StudentPOVCopyLayer:
    def realize(self, projection, plan, *, bundle, status, **kwargs):
        return realize(projection, plan, bundle, status, **kwargs)
