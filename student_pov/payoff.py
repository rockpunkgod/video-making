"""Bound path comparison and work reduction, not inferred student behavior."""
from copy import deepcopy
from video_contracts import pointer, sha


def supported_payoff(plan, projection):
    support = projection['payoff_structure'].get('reviewed_support')
    if support is None:
        return None, ['PAYOFF_UNSUPPORTED:missing_reviewed_baseline_and_removed_work']
    record = deepcopy(support['record'])
    required = {'scope', 'payoff_type', 'baseline_path', 'method_path', 'removed_steps',
                'remaining_steps', 'cognitive_work', 'reduction', 'allowed_claim',
                'cognitive_relief_line', 'evidence_pointers', 'first_action_transferable', 'output_anchors'}
    if required - set(record):
        return None, ['PAYOFF_UNSUPPORTED:incomplete_reviewed_path_comparison']
    errors = []
    baseline, method = record['baseline_path'], record['method_path']
    if not baseline or not method or not record['removed_steps']:
        errors.append('no_actual_removed_work')
    def ids(rows):
        if not isinstance(rows, list) or any(not isinstance(r, dict)
                or not isinstance(r.get('text'), str) or not r['text'].strip()
                or not isinstance(r.get('work_ids'), list) for r in rows):
            raise ValueError('Paths need explicit reviewed text and work IDs')
        return {w for row in rows for w in row['work_ids']}
    try:
        before_work, after_work = ids(baseline), ids(method)
    except ValueError:
        return None, ['PAYOFF_UNSUPPORTED:unbound_path_steps']
    work = record['cognitive_work']
    if not isinstance(work, dict) or set(work) != {'removed', 'deferred', 'still_required'}:
        return None, ['PAYOFF_UNSUPPORTED:cognitive_work_dispositions_required']
    if any(not isinstance(v, list) or len(v) != len(set(v)) for v in work.values()):
        return None, ['PAYOFF_UNSUPPORTED:invalid_work_dispositions']
    removed, deferred, required_work = (set(work[k]) for k in ('removed', 'deferred', 'still_required'))
    if removed & deferred or removed & required_work:
        errors.append('deferred_or_required_work_mislabeled_removed')
    removed_ids = {r.get('work_id') for r in record['removed_steps']}
    if not removed or removed != removed_ids or not removed <= before_work or removed & after_work:
        errors.append('removed_steps_not_supported_by_paths')
    if not required_work >= after_work:
        errors.append('remaining_method_work_hidden')
    remaining_ids = {r.get('work_id') for r in record['remaining_steps']}
    if not remaining_ids >= deferred | required_work:
        errors.append('deferred_or_still_required_steps_not_recorded')
    reduction = record['reduction']
    if not isinstance(reduction, dict) or not {'before', 'after', 'unit', 'before_ids', 'after_ids'} <= set(reduction):
        return None, ['PAYOFF_UNSUPPORTED:actual_reduction_shape_required']
    if (type(reduction['before']) is not int or type(reduction['after']) is not int
            or not reduction['before'] > reduction['after'] > 0
            or reduction['before'] != len(set(reduction['before_ids']))
            or reduction['after'] != len(set(reduction['after_ids']))
            or not set(reduction['after_ids']) <= set(reduction['before_ids'])):
        errors.append('no_structural_complexity_drop')
    role = plan['role']
    outputs = plan['answer_scope']['actual_outputs']
    anchors = record['output_anchors']
    if not isinstance(anchors, list) or not anchors:
        errors.append('actual_output_anchors_required')
    else:
        for anchor in anchors:
            try:
                index = anchor['output_index']
                if type(index) is not int or not 0 <= index < len(outputs):
                    raise ValueError('output index')
                value = pointer(outputs[index], anchor['pointer'])
                if sha(value) != anchor['sha']:
                    raise ValueError('output hash')
            except (KeyError, IndexError, ValueError, TypeError):
                errors.append('dangling_or_mutated_actual_output_anchor')
    kinds = {o.get('kind') for o in outputs if isinstance(o, dict)}
    ptype = record['payoff_type']
    if ptype == 'TYPE_A':
        decisions = [o for o in outputs if isinstance(o, dict) and o.get('kind') == 'candidate_decision']
        if role != 'decider' or not decisions or any(o.get('effect') not in ('retain', 'eliminate') for o in decisions):
            errors.append('direct_decision_requires_actual_decider_output')
        if record['scope'].get('claim_scope') == 'final_answer' and not plan['answer_scope']['may_output_final_answer']:
            errors.append('local_decision_is_not_final_answer_permission')
        if reduction['unit'] == 'candidate' and decisions:
            actual_candidates = set(plan['original_question'].get('options', {}))
            removed_candidates = {o['candidate'] for o in decisions if o['effect'] == 'eliminate'}
            if (set(reduction['before_ids']) != actual_candidates
                    or set(reduction['after_ids']) != actual_candidates - removed_candidates):
                errors.append('candidate_drop_does_not_match_actual_decision')
    elif ptype == 'TYPE_B':
        if role != 'reducer':
            errors.append('candidate_collapse_requires_reducer')
        # A partition of all candidates does not prove any candidate exited.
        # Only explicit remaining/retained candidates in an actual frozen output
        # count. Current Core partitions alone will truthfully remain HOLD.
        retained = [o.get('remaining_candidates', o.get('retained_candidates'))
                    for o in outputs if isinstance(o, dict)]
        retained = [x for x in retained if isinstance(x, list)]
        if not retained or set(reduction['after_ids']) not in [set(x) for x in retained]:
            errors.append('partition_is_not_candidate_elimination')
    elif ptype == 'TYPE_C':
        if role not in ('locator', 'interpreter', 'framework'):
            errors.append('reading_or_structure_collapse_requires_auxiliary_role')
        if not kinds & {'located_evidence', 'interpretation', 'framework_card', 'route_selection'} and not (
                plan['input_binding']['transport'] == 'reviewed_passage' and role in ('locator', 'interpreter')):
            errors.append('no_compatible_actual_structure_output')
        if role == 'framework' and 'route_selection' in kinds:
            forbidden = {'word_form', 'derivation', 'number', 'possessive', 'gerund_check', 'context_check'}
            if removed & forbidden:
                errors.append('route_does_not_remove_form_or_context_checks')
    else:
        errors.append('unknown_payoff_type')
    if not isinstance(record['allowed_claim'], str) or not record['allowed_claim'].strip():
        errors.append('allowed_claim_required')
    if not isinstance(record['first_action_transferable'], bool):
        errors.append('transferable_first_action_must_be_explicit')
    if record['scope'].get('stage') not in ('current_action', 'current_candidate'):
        errors.append('explicit_bounded_work_scope_required')
    line = record['cognitive_relief_line']
    if not isinstance(line, str) or not line.strip():
        errors.append('bound_cognitive_relief_line_required')
    if isinstance(line, str) and any(word in line for word in ('不用认识', '不用背单词', '不用词汇')):
        words = record.get('vocabulary_shortcut', {})
        if (not words.get('scope_label') or not words.get('word_evidence_pointers')
                or not set(words['word_evidence_pointers']) <= set(record['evidence_pointers'])
                or not any(scope in line for scope in ('这一题', '这一步', '当前判断'))):
            errors.append('vocabulary_shortcut_needs_specific_scope_and_word_evidence')
        if '做阅读不用背单词' in line or '阅读不用词汇' in line:
            errors.append('vocabulary_shortcut_generalization')
    if errors:
        return None, ['PAYOFF_UNSUPPORTED:' + e for e in sorted(set(errors))]
    return {**record, 'source_payoff_refs': deepcopy(support['source_refs']),
            'evidence_refs': deepcopy(support['evidence_refs']),
            'action_artifact_refs': deepcopy(support['action_artifact_refs'])}, []
