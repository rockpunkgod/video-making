"""Role-specific observations over current frozen actions; never new teaching reviews."""
from copy import deepcopy
from statistics import mean

from pedagogy.sources import FrozenSource
from video_contracts import sha


def evaluate(bundle, status, selection, observation):
    source = FrozenSource(bundle, status, selection)
    role = source.method['primary_role']
    if source.transport != 'frozen_asset':
        raise ValueError('Role evaluation v0.2 requires a frozen asset')
    outputs = [a['output'] for a in source.actions]
    result = {'role': role, 'question_id': source.question['question_id'],
              'method_id': source.method['method_id'], 'selection': deepcopy(selection),
              'semantic_binding_sha': bundle['semantic_binding_sha'],
              'status_sha': status['content_sha'], 'observation_sha': sha(observation),
              'success': None, 'metrics': {}, 'semantic_certification': False,
              'public_render_ready': False}
    if role == 'locator':
        if set(observation) != {'required_evidence_refs'} or not observation['required_evidence_refs']:
            raise ValueError('Locator needs explicit downstream frozen evidence references')
        from video_contracts import pointer, review_semantics
        required = []
        for ref in observation['required_evidence_refs']:
            path = ref['pointer']
            import re
            match = re.fullmatch(r'/analysis/execution_trace/(\d+)/evidence/(\d+)', path)
            if not match or ref['asset_id'] != bundle['asset_id']:
                raise ValueError('Required evidence must belong to a frozen action')
            action = bundle['analysis']['execution_trace'][int(match.group(1))]
            # Validate the downstream action independently; same-word proximity is insufficient.
            FrozenSource(bundle, status, {'method_id': action['method_id'],
                                         'action_ids': [action['execution_id']]})
            value = pointer(bundle, path)
            if ref['sha'] != sha(review_semantics(value)):
                raise ValueError('Required evidence reference changed')
            required.append(value)
        spans = [span for output in outputs if output.get('kind') == 'located_evidence'
                 for span in output['spans']]
        if not spans:
            raise ValueError('Locator requires actual frozen location output')
        covered = sum(any(s['field'] == e['field'] and s['start'] <= e['start']
                          and s['end'] >= e['end'] for s in spans) for e in required)
        result['metrics'] = {'coverage': covered / len(required)}
        result['success'] = covered == len(required)
    elif role in ('reducer', 'decider'):
        if observation:
            raise ValueError('Candidate results come only from frozen actions')
        decisions = [o for o in outputs if o.get('kind') == 'candidate_decision']
        eliminated = {o['candidate'] for o in decisions if o['effect'] == 'eliminate'}
        retained = {o['candidate'] for o in decisions if o['effect'] == 'retain'}
        answer = source.upstream_answer
        wrong = answer in eliminated if source.upstream_closed and answer is not None else None
        result['metrics'] = {'eliminated_count': len(eliminated), 'wrong_elimination': wrong}
        if role == 'reducer' and not decisions:
            result['missing'] = 'grouping_or_routing_is_not_reviewed_candidate_elimination'
        elif wrong is None:
            result['missing'] = 'closed_frozen_answer_for_conflict_check'
        elif role == 'reducer':
            result['success'] = not wrong and bool(eliminated)
        else:
            options = set(source.question.get('options', {}))
            result['success'] = bool(options) and retained == {answer} and eliminated == options - {answer}
    elif role == 'verifier':
        # Independent reviewed injected-error ground truth is not yet a supported frozen transport.
        # Do not accept caller booleans as evidence of correct error detection.
        if observation:
            raise ValueError('Verifier injection evidence needs a reviewed upstream contract')
        result['missing'] = 'reviewed_injected_error_and_correct_control_assets'
    else:
        if observation:
            raise ValueError('Framework/interpreter observations require manual source review')
        result['missing'] = 'manual_downstream_call_or_interpretation_review'
    return result


def summarize(records):
    groups = {}
    for record in records:
        key = (record['method_id'], record['role'])
        groups.setdefault(key, []).append(record)
    output = []
    for (mid, role), rows in sorted(groups.items()):
        if len({r['question_id'] for r in rows}) != len(rows):
            raise ValueError('A question cannot be counted twice for one method')
        known = [r for r in rows if r['success'] is not None]
        metrics = {'evaluated': len(known), 'sampled': len(rows),
                   'success_rate': mean(r['success'] for r in known) if known else None}
        met = None
        if known and role == 'locator':
            metrics['mean_evidence_coverage'] = mean(r['metrics']['coverage'] for r in known)
            met = metrics['mean_evidence_coverage'] >= .8
        elif known and role == 'reducer':
            metrics['wrong_elimination_rate'] = mean(r['metrics']['wrong_elimination'] for r in known)
            metrics['mean_eliminated'] = mean(r['metrics']['eliminated_count'] for r in known)
            met = metrics['wrong_elimination_rate'] == 0 and metrics['mean_eliminated'] >= 1
        elif known and role == 'decider':
            met = metrics['success_rate'] >= .7
        output.append({'method_id': mid, 'role': role, **metrics,
                       'initial_line_met': met,
                       'status': 'HOLD_MISSING_OBSERVATIONS' if len(known) != len(rows) else
                                 'HOLD_SAMPLE_UNDER_TEN' if len(rows) < 10 else
                                 'HUMAN_REVIEW_REQUIRED' if met else 'CHECK_LINE_NOT_MET'})
    return {'version': 'role-evaluation/0.2.0', 'policy_status': 'provisional',
            'methods': output, 'public_render_ready': False, 'semantic_certification': False}
