"""Deterministic learner-path and language lint, not Human Taste certification."""
import re

from .qa import answer_letters, frozen_answer_binding, lint_copy

STAGE_ORDER = ('PAIN', 'INTERRUPT', 'ORIENT', 'FOCUS', 'ACT', 'TENSION',
               'COLLAPSE', 'PAYOFF', 'STOP', 'MEMORY')
SIGNPOSTS = r'首先|其次|接下来|此外|因此我们可以看到|值得注意的是|由此可见|换句话说|综上'


def tone_lint(beats, role, may_answer, *, frozen_bundle=None, frozen_status=None,
              frozen_answer=None):
    """Literal evidence/question are protected source, not new copy claims."""
    flags, errors = [], []
    spoken = [b['vo']['text'] for b in beats if b['vo'] is not None]
    editable_screen = [line['text'] for b in beats for line in b['screen']['copy']
                       if line['kind'] in ('memory', 'method_name')]
    # A verbatim Stop may quote a prohibited inference in order to forbid it.
    # Do not lint that frozen negative statement as a new affirmative claim.
    # Its exact source, reviewed placement and coverage are audited separately.
    text = '\n'.join(spoken + editable_screen)
    if frozen_bundle is not None:
        frozen_answer = frozen_answer_binding(frozen_bundle, frozen_status)['answer']
        may_answer = True
    elif frozen_status is not None:
        raise ValueError('Status requires its exact frozen bundle')
    base = lint_copy(text, role, may_answer, frozen_answer=frozen_answer)
    if base:
        errors += ['COPY_LINT:' + flag for flag in base]
        if 'expert_chain_leakage' in base: flags.append('expert_backend_narration')
        if 'prohibited_or_generalized_claim' in base or 'unbound_statistic_or_heat_claim' in base:
            flags.append('marketing_hype')
    if re.search(r'(?<![A-Za-z0-9])[RFCGWS]\d{2}(?![A-Za-z0-9])', text):
        errors.append('INTERNAL_METHOD_CODE_ON_CONSUMER_SURFACE')
    if re.search(r'(?<![A-Za-z0-9_])(?:locator|interpreter|decider|reducer|verifier|framework|interpret|reduce|Evidence|Review|Registry|Artifact|Provenance)(?![A-Za-z0-9_])|调用.*(?:方法|阶段)|进入.*阶段', text, re.I):
        flags.append('expert_backend_narration'); errors.append('EXPERT_BACKEND_NARRATION')
    if not may_answer and (answer_letters(text) or re.search(r'答案(?:已经|直接|就)?(?:出来|确定)', text)):
        errors.append('ANSWER_SCOPE_OVERCLAIM'); flags.append('fake_payoff')
    if re.search(r'不用(?:读全文|阅读全文|读整篇|认识词|认识单词|背单词)|省(?:一半|\d+).*时间|秒选|秒杀', text):
        errors.append('UNSUPPORTED_SAVINGS_CLAIM'); flags.append('fake_payoff')
    if any(b['vo'] and any(b['vo']['text'].strip() == line['text'].strip()
           for line in b['screen']['copy']) for b in beats):
        flags.append('screen_voice_duplication')
    signposts = [len(re.findall(SIGNPOSTS, line)) for line in spoken]
    if sum(signposts) >= 3 or any(signposts[i] and signposts[i+1] for i in range(len(signposts)-1)):
        flags += ['over_structured', 'too_many_signposts', 'generic_transition']
    if any(len(re.findall(r'[\u3400-\u9fff]', line)) > 60 for line in spoken):
        flags.append('over_explained')
    if re.search(r'因此我们可以看到|综上所述|由此可见|进行.*分析|根据以上分析', '\n'.join(spoken)):
        flags += ['textbook_tone', 'robotic_logic']
    if re.search(r'我们可以看到|可以发现|这里说明', '\n'.join(spoken)):
        flags.append('redundant_explanation')
    if re.search(r'现在还不能选|另外(?:三个|几个).*(?:还得|还要|继续)|这里只负责', '\n'.join(spoken)):
        flags.append('redundant_result_reminder')
    return sorted(set(flags)), sorted(set(errors))


def audit_experience(value, view, plan):
    """Observe generated encounters; never infer comprehension or audiovisual quality."""
    beats = value['beats']; curve = value['experience_curve']
    errors = []
    ids = [b['beat_id'] for b in beats]
    if len(ids) != len(set(ids)): errors.append('DUPLICATE_BEAT_ID')
    stages = [r['stage'] for r in curve]
    if (any(s not in STAGE_ORDER for s in stages) or len(stages) != len(set(stages))
            or stages != sorted(stages, key=lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else -1)
            or any(r['beat_id'] not in ids or not r['pedagogy_refs'] for r in curve)):
        errors.append('INVALID_EXPERIENCE_CURVE')
    actions = [b for b in beats if b['cognitive_function'] == 'action']
    primary = view['primary_action']
    action_unique = len(actions) == 1 and primary is not None and value['first_action'] == primary
    action_visible = action_unique and actions[0]['vo'] is not None \
        and any(r['pointer'] == '/primary_action/instruction' for r in actions[0]['vo']['pedagogy_refs']) \
        and any(line['kind'] == 'literal_evidence' for line in actions[0]['screen']['copy'])
    if not action_unique: errors.append('ONE_PRIMARY_ACTION_REQUIRED')
    if not action_visible: errors.append('PRIMARY_ACTION_NOT_EXECUTABLE_IN_PLAN')
    structure = view['cognitive_structure']
    expected_focus = structure['attention_transition']
    focus_preserved = (value['focus']['object_ids'] == structure['focus_objects']
        and value['focus']['scope_before'] == expected_focus['from_scope']
        and value['focus']['scope_after'] == expected_focus['to_scope'])
    if not focus_preserved: errors.append('ATTENTION_SCOPE_CHANGED')
    unresolved = [o['object_id'] for o in structure['objects'] if o['state'] == 'unresolved']
    remaining_preserved = value['stop']['unresolved'] == unresolved and all(
        b['experience']['unresolved_state'] == unresolved and set(unresolved) <= set(b['screen']['object_ids'])
        for b in beats)
    if not remaining_preserved: errors.append('UNRESOLVED_OBJECTS_HIDDEN')
    work_preserved = True
    for key in ('baseline_work','removed_work','deferred_work','still_required_work'):
        rows = view['work_delta'][key]
        expected = None if rows is None else [r['work_id'] for r in rows]
        if value['work_delta'][key] != expected: work_preserved = False
    work_preserved = work_preserved and value['stop']['deferred_work'] == value['work_delta']['deferred_work'] \
        and value['stop']['still_required_work'] == value['work_delta']['still_required_work']
    if not work_preserved: errors.append('WORK_DISPOSITION_CHANGED')
    support = value['collapse']['supported']
    has_payoff = 'PAYOFF' in stages or any(b['cognitive_function'] == 'payoff' for b in beats)
    if has_payoff and (not support or view['payoff']['allowed_claim'] is None): errors.append('FAKE_PAYOFF')
    if any('TENSION' == row['stage'] for row in curve) and not unresolved:
        errors.append('TENSION_REQUIRES_UNRESOLVED_SOURCE')
    for beat in beats:
        tension = beat['experience']['tension_state']
        if tension and (not unresolved or tension['unresolved_objects'] != unresolved):
            errors.append('UNSUPPORTED_TENSION')
        if beat['experience']['payoff_state'] is not None and beat['experience']['payoff_state']['scope'] != view['payoff']['payoff_scope']:
            errors.append('PAYOFF_SCOPE_CHANGED')
        if beat['cognitive_function'] in ('payoff', 'collapse') and beat['vo'] is not None:
            if not any(r['pointer'] == '/payoff/allowed_claim' for r in beat['vo']['pedagogy_refs']):
                errors.append('PAYOFF_LINE_NOT_BOUND_TO_ALLOWED_CLAIM')
    before, after = view['payoff']['structural_before'], view['payoff']['structural_after']
    first_collapse = next((i for i,b in enumerate(beats) if b['cognitive_function'] == 'collapse'), None)
    visible = bool(support and first_collapse is not None and before is not None and after is not None
        and before['objects'] != after['objects'] and value['work_delta']['removed_work']
        and any(b['screen']['structural_state'] == before for b in beats[:first_collapse])
        and beats[first_collapse]['screen']['structural_state'] == after)
    if support and not visible: errors.append('COLLAPSE_STRUCTURE_NOT_ENCOUNTERED')
    if not support and any(b['cognitive_function'] == 'collapse' for b in beats): errors.append('UNSUPPORTED_COLLAPSE')
    scope_preserved = value['collapse']['scope'] == view['payoff']['payoff_scope'] \
        and value['stop']['scope'] == (view['payoff']['payoff_scope'] or 'method_action_demo') \
        and value['answer_permission'] == view['answer_permission']
    if not scope_preserved: errors.append('OUTPUT_SCOPE_CHANGED')
    boundary_ids = [item['item_id'] for item in view['must_obtain']]
    seen = [item for b in beats for item in b['boundary_ids']]
    stop_preserved = (value['stop']['current_output'] == view['learning_unit']['immediate_output']
        and value['stop']['boundary_presentations'] == view['must_obtain']
        and sorted(boundary_ids) == sorted(seen) and 'STOP' in stages)
    for item in view['must_obtain']:
        target = next((b for b in beats if item['item_id'] in b['boundary_ids']), None)
        if target is None or target['cognitive_function'] != item['scene']:
            stop_preserved = False; continue
        expression = item['coverage']['displayed_expression']['text']
        if item['spoken_readout_required'] or item['delivery_form'] == 'spoken':
            if target['vo'] is None or target['vo']['text'] != expression:
                stop_preserved = False; errors.append('SILENCE_MASKS_REQUIRED_SPOKEN_BOUNDARY')
        elif not any(line['text'] == expression and line['kind'] == 'reviewed_boundary'
                for line in target['screen']['copy']): stop_preserved = False
    if not stop_preserved: errors.append('REQUIRED_STOP_COVERAGE_MISSING')
    action_at = next((i for i,b in enumerate(beats) if b['cognitive_function'] == 'action'), None)
    named_at = next((i for i,b in enumerate(beats) if any(line['kind'] == 'method_name' for line in b['screen']['copy'])), None)
    early_name = named_at is not None and (action_at is None or named_at <= action_at)
    original_first = bool(beats and beats[0]['cognitive_function'] == 'pain'
        and value['reality_layer']['question'] == view['original_question']
        and value['reality_layer']['persistent'] is True and value['reality_layer']['fact_mutation_allowed'] is False
        and all(b['screen']['reality_layer_ref'] == '/reality_layer' for b in beats))
    if not original_first: errors.append('ORIGINAL_QUESTION_NOT_PRESERVED')
    flags, copy_errors = tone_lint(beats, plan['role'], view['answer_permission']['may_output_final_answer'],
                                  frozen_answer=view['answer_permission'].get('answer'))
    errors += copy_errors
    audit = {'first_action_visible': bool(action_visible), 'first_action_unique': bool(action_unique),
        'focus_scope_preserved': focus_preserved, 'payoff_supported': support,
        'payoff_scope_preserved': scope_preserved, 'collapse_visible_in_plan': visible,
        'stop_preserved': stop_preserved, 'unresolved_preserved': remaining_preserved,
        'work_dispositions_preserved': work_preserved, 'original_question_first': original_first,
        'vo_screen_duplication': 'screen_voice_duplication' in flags,
        'over_explained': 'over_explained' in flags,
        'method_named_before_action': early_name, 'method_named_before_understood': None,
        'unsupported_hype': bool(set(flags) & {'marketing_hype', 'fake_payoff'}),
        'observation_scope': 'planned_encounters_and_text_only', 'semantic_truth_certification': False,
        'actual_visual_review': 'PENDING', 'actual_voice_review': 'PENDING', 'human_taste_review': 'PENDING'}
    return audit, flags, sorted(set(errors))
