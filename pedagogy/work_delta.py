"""Compile reviewed work dispositions; never invent a learner baseline."""
from copy import deepcopy
import re

from video_contracts import pointer, sha
from .policy import claim_lint

UNSUPPORTED_SAVINGS = ('time_saved', 'reading_removed', 'vocabulary_removed',
                       'measured_cognitive_load_gain', 'whole_question_shortcut')


def _binding(support):
    return {key: deepcopy(support[key]) for key in
            ('source_refs', 'action_artifact_refs', 'evidence_refs', 'review_refs')}


def _step(row, support, work_id):
    return {'work_id': work_id, 'text': row['text'], **_binding(support),
            'scope': row.get('scope', 'current_reviewed_work_scope'),
            'reopen_on_upstream_change': True}


def _path_ids(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('bound_paths_required')
    ids = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('text'), str)
                or not row['text'].strip() or not isinstance(row.get('work_ids'), list)
                or not row['work_ids'] or any(not isinstance(w, str) or not w.strip()
                                             for w in row['work_ids'])
                or len(set(row['work_ids'])) != len(row['work_ids'])):
            raise ValueError('bound_path_work_ids_required')
        ids.extend(row['work_ids'])
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_path_work_ids')
    return ids


def _rows_by_id(rows):
    if not isinstance(rows, list):
        raise ValueError('bound_work_steps_required')
    result = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('work_id'), str)
                or not row['work_id'].strip() or not isinstance(row.get('text'), str)
                or not row['text'].strip() or row['work_id'] in result):
            raise ValueError('unique_bound_work_steps_required')
        result[row['work_id']] = row
    return result


def _check_record(record, base):
    required = {'scope', 'payoff_type', 'baseline_path', 'method_path', 'removed_steps',
                'remaining_steps', 'cognitive_work', 'reduction', 'allowed_claim',
                'evidence_pointers', 'output_anchors', 'first_action_transferable'}
    if not isinstance(record, dict) or required - set(record):
        raise ValueError('incomplete_reviewed_work_delta')
    before, after = _path_ids(record['baseline_path']), _path_ids(record['method_path'])
    dispositions = record['cognitive_work']
    if not isinstance(dispositions, dict) or set(dispositions) != {'removed', 'deferred', 'still_required'}:
        raise ValueError('three_explicit_work_dispositions_required')
    for values in dispositions.values():
        if (not isinstance(values, list) or any(not isinstance(w, str) or not w.strip() for w in values)
                or len(values) != len(set(values))):
            raise ValueError('invalid_work_dispositions')
    removed, deferred, remaining = (set(dispositions[k]) for k in ('removed', 'deferred', 'still_required'))
    if removed & deferred or removed & remaining or deferred & remaining:
        raise ValueError('removed_deferred_required_must_be_distinct')
    removed_rows = _rows_by_id(record['removed_steps'])
    remaining_rows = _rows_by_id(record['remaining_steps'])
    if (removed != set(removed_rows) or not removed or not removed <= set(before)
            or removed & set(after) or not set(before) <= removed | deferred | remaining
            or not set(after) <= remaining or set(remaining_rows) != deferred | remaining):
        raise ValueError('work_delta_does_not_conserve_reviewed_work')
    reduction = record['reduction']
    if not isinstance(reduction, dict) or not {'before', 'after', 'unit', 'before_ids', 'after_ids'} <= set(reduction):
        raise ValueError('structural_reduction_required')
    for key in ('before_ids', 'after_ids'):
        values = reduction[key]
        if (not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values)
                or len(values) != len(set(values))):
            raise ValueError('unique_reduction_objects_required')
    if (type(reduction['before']) is not int or type(reduction['after']) is not int
            or not reduction['before'] > reduction['after'] > 0
            or reduction['before'] != len(reduction['before_ids'])
            or reduction['after'] != len(reduction['after_ids'])
            or not set(reduction['after_ids']) <= set(reduction['before_ids'])):
        raise ValueError('structural_reduction_not_supported')
    anchors = record['output_anchors']; outputs = base['answer_scope']['actual_outputs']
    if not isinstance(anchors, list) or not anchors:
        raise ValueError('actual_output_anchors_required')
    for anchor in anchors:
        try:
            index = anchor['output_index']
            if type(index) is not int or not 0 <= index < len(outputs):
                raise ValueError('output_index')
            if sha(pointer(outputs[index], anchor['pointer'])) != anchor['sha']:
                raise ValueError('output_sha')
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ValueError('actual_output_anchor_changed') from error
    role, kind = base['role'], record['payoff_type']
    decisions = [o for o in outputs if isinstance(o, dict) and o.get('kind') == 'candidate_decision']
    if kind == 'TYPE_A':
        if role != 'decider' or not decisions or any(o.get('effect') != 'eliminate' for o in decisions):
            raise ValueError('local_elimination_requires_actual_decider')
        if reduction['unit'] == 'candidate':
            domain = set(base['original_question'].get('options', {}))
            excluded = {o['candidate'] for o in decisions}
            if set(reduction['before_ids']) != domain or set(reduction['after_ids']) != domain - excluded:
                raise ValueError('candidate_delta_does_not_match_actual_output')
    elif kind == 'TYPE_B':
        retained = [o.get('remaining_candidates', o.get('retained_candidates'))
                    for o in outputs if isinstance(o, dict)]
        if role != 'reducer' or set(reduction['after_ids']) not in [set(v) for v in retained if isinstance(v, list)]:
            raise ValueError('partition_is_not_candidate_elimination')
    elif kind == 'TYPE_C':
        kinds = {o.get('kind') for o in outputs if isinstance(o, dict)}
        if role not in ('locator', 'interpreter', 'framework') or not (
                kinds & {'located_evidence', 'interpretation', 'framework_card', 'route_selection'}
                or base['input_binding']['transport'] == 'reviewed_passage'):
            raise ValueError('auxiliary_structure_output_required')
        if role == 'framework' and 'route_selection' in kinds and removed & {
                'word_form', 'derivation', 'number', 'possessive', 'gerund_check', 'context_check'}:
            raise ValueError('route_does_not_remove_form_or_context_checks')
    else:
        raise ValueError('unknown_payoff_type')
    scope = record['scope']
    if (not isinstance(scope, dict) or scope.get('stage') not in ('current_action', 'current_candidate')
            or scope.get('claim_scope') in ('final_answer', 'whole_question')):
        raise ValueError('bounded_payoff_is_not_answer_completion')
    if record['first_action_transferable'] is not True:
        raise ValueError('first_action_transferability_not_supported')
    claim = record['allowed_claim']
    if (not isinstance(claim, str) or not claim.strip() or claim_lint(claim, role)
            or re.search(r'\d+\s*[%％]|百分之', claim)
            or any(term in claim for term in ('省一半时间', '不用背单词', '全文不用看', '直接秒选'))):
        raise ValueError('unsupported_savings_cannot_be_allowed_claim')
    return before, after, removed_rows, remaining_rows


def project_work_delta(source, base):
    """Only an existing reviewed record or exact candidate transition supplies savings."""
    method_work = [{'work_id': 'actual_action:' + source.selection['action_ids'][i],
                    'text': deepcopy(action[source.action_key]),
                    'source_refs': [source.ref(path + '/' + source.action_key)],
                    'action_artifact_refs': [source.ref(path)],
                    'evidence_refs': [source.ref(path + '/evidence/' + str(j)) for j in range(len(action['evidence']))],
                    'review_refs': [source.ref(p) for p in source.review_paths],
                    'output_ref': source.ref(path + '/output')}
                   for i, (path, action) in enumerate(zip(source.action_paths, source.actions))]
    # The source action ordering is authoritative, not the request ID order.
    for item, action in zip(method_work, source.actions):
        item['work_id'] = 'actual_action:' + action.get('execution_id', action.get('action_id'))
    result = {'baseline_work': None, 'method_work': method_work, 'removed_work': [],
              'deferred_work': [], 'still_required_work': [],
              'unsupported_savings': [{'claim_key': key, 'status': 'UNSUPPORTED'} for key in UNSUPPORTED_SAVINGS],
              'baseline_kind': None, 'baseline_measured': False, 'learner_transfer_validated': False,
              'scope': 'selected_question_and_actual_action', 'status': 'HOLD',
              'gaps': ['BASELINE_WORK_UNSUPPORTED', 'PAYOFF_UNSUPPORTED', 'COGNITIVE_RELIEF_UNAVAILABLE']}
    support = base['payoff']['reviewed_support']
    if support is None:
        return result, None
    record = support['record']
    try:
        _, _, removed, remaining = _check_record(record, base)
    except ValueError as error:
        result['gaps'].append('PAYOFF_UNSUPPORTED:' + str(error))
        return result, None
    work = record['cognitive_work']
    result.update(baseline_work=[_step(row, support, wid) for row in record['baseline_path'] for wid in row['work_ids']],
        removed_work=[_step(removed[wid], support, wid) for wid in work['removed']],
        deferred_work=[_step(remaining[wid], support, wid) for wid in work['deferred']],
        still_required_work=[_step(remaining[wid], support, wid) for wid in work['still_required']],
        baseline_kind=support['baseline_kind'], baseline_measured=support['baseline_measured'],
        learner_transfer_validated=False, status='SUPPORTED_REVIEWED_STRUCTURE', gaps=[])
    bound = _binding(support)
    kind = record['payoff_type']
    payoff_scope = 'candidate_set' if kind in ('TYPE_A', 'TYPE_B') and record['reduction']['unit'] == 'candidate' \
        else 'evidence_scope' if base['role'] == 'locator' else 'local'
    claim = {'text': record['allowed_claim'], **bound}
    projection = {'structural_before': {'objects': deepcopy(record['reduction']['before_ids']), **bound},
                  'structural_after': {'objects': deepcopy(record['reduction']['after_ids']), **bound},
                  'allowed_claim': claim, 'payoff_scope': payoff_scope,
                  'reduction_types': ['candidate_reduction'] if payoff_scope == 'candidate_set' else
                      ['scope_reduction'] if base['role'] == 'locator' else ['attention_reduction'],
                  'decision_completion': False, 'structural_reduction': deepcopy(record['reduction'])}
    return result, projection
