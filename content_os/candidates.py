from copy import deepcopy
from video_contracts import sha, status_matches, verify_bundle, validate

SCOPES = ('full_solution', 'method_action_demo', 'boundary_demo', 'anti_rule_demo', 'challenge', 'method_comparison')
RELEASE_CHECKS = {
    'full_solution': {'answer', 'candidate_closure', 'decisive_evidence', 'method_attribution', 'role', 'stop_rule'},
    'method_action_demo': {'trigger', 'action', 'output', 'role', 'stop_rule'},
    'boundary_demo': {'apparent_applicability', 'stop_reason', 'decisive_boundary', 'role', 'stop_rule'},
    'anti_rule_demo': {'counterexample', 'boundary_evidence', 'role', 'stop_rule'},
    'challenge': {'trigger', 'action', 'output', 'role', 'stop_rule'},
    'method_comparison': {'trigger', 'action', 'output', 'role', 'stop_rule', 'comparison_basis'},
}


def reference(bundle, path):
    return {'asset_id': bundle['asset_id'], 'pointer': path}


def matching_reviews(bundle, selection):
    """Only active credentials covering the selected method may support its claims."""
    active = {r['artifact_id'] for r in bundle['lifecycle']['reviews'] if r['status'] == 'active'}
    version = bundle['binding_fingerprint']['method_versions'].get(selection['method_id'])
    result = []
    for index, r in enumerate(bundle['reviews']):
        record = r['record']
        mid = record.get('method_id', record.get('release_review', {}).get('method_id'))
        if (r['artifact_id'] in active and r['level'] != 'unreviewed'
            and (mid is None or mid == selection['method_id'])
            and record.get('method_version', version) == version):
            result.append((index, r))
    return result


def source_gate(bundles):
    states = [b['source'].get('usage_status', 'unknown') for b in bundles]
    internal_allowed = {'internal_only', 'user_supplied_local_research', 'public_excerpt_review_required', 'public_excerpt_approved', 'public_full_approved'}
    return {'internal_use': 'PASS' if all(x in internal_allowed for x in states) else 'BLOCKED',
            'public_usage_status': 'review_required', 'status': 'PENDING',
            'human_review_required': True, 'source_states': states}


def engineering_gate(bundle, selection, scope, status):
    a = bundle['analysis']; method = selection['method_id']
    steps = [x for x in a['method_chain'] if x['method_id'] == method]
    active = {x['artifact_id'] for x in bundle['lifecycle']['actions'] if x['status'] == 'active'}
    requested = selection.get('action_ids', [])
    actions = [x for x in a['execution_trace'] if x['execution_id'] in requested]
    node_ids = {x['id'] for x in a['evidence_graph']['nodes'] if x['type'] == 'source_evidence'}
    own_reviews = matching_reviews(bundle, selection)
    checks = {
        'original_question_frozen': sha(bundle['source_snapshot']) == bundle['binding_fingerprint']['question_snapshot_sha'],
        'source_snapshot_bound': bool(bundle['source_snapshot']),
        'review_bound_to_exact_question': bool(own_reviews),
        'review_present': bool(own_reviews),
        'method_version_bound': method in bundle['binding_fingerprint']['method_versions'],
        'method_role_explicit': bool(steps) and all(x['role'] in ('locator', 'interpreter', 'reducer', 'decider', 'verifier', 'framework') for x in steps),
        'actual_action_recorded': bool(requested) and len(set(requested)) == len(requested) and len(actions) == len(requested)
                                  and all(x['method_id'] == method and x['execution_id'] in active for x in actions),
        'evidence_refs_present': bool(actions) and all(x['evidence_ids'] and set(x['evidence_ids']) <= node_ids for x in actions),
        'stop_rule_present': bool(steps) and all(x['stop_rule'].strip() for x in steps),
        'review_not_withdrawn': bundle['state']['effective_status'] == 'ACTIVE' and not bundle['withdrawals'],
        'current_upstream_valid': status is not None and status_matches(bundle, status),
    }
    if scope == 'full_solution':
        checks['answer_closed'] = a['answer'] is not None and a['answer_verification']['closed'] is True
        checks['candidate_closure'] = bool(a['candidate_analysis']) and not a['answer_verification'].get('unresolved_candidates')
        checks['answer_attribution_recorded'] = any(x.get('output', {}).get('kind') == 'candidate_decision'
            and x['output'].get('candidate') == a['answer'] and x['output'].get('effect') == 'retain' for x in actions)
    if scope in ('boundary_demo', 'anti_rule_demo'):
        # These are explicit upstream claim credentials, not guesses from method prose.
        key = 'boundary' if scope == 'boundary_demo' else 'counterexample'
        checks['reviewed_' + key] = any(isinstance(r['record'].get('reviewed_claims', {}).get(key), str)
                                      and r['record']['reviewed_claims'][key].strip() for _, r in own_reviews)
    blockers = [k for k, v in checks.items() if not v]
    return {'status': 'PASS' if not blockers else 'BLOCKED' if bundle['state']['effective_status'] in ('WITHDRAWN', 'BLOCKED', 'SUPERSEDED', 'STALE') else 'HOLD',
            'checks': {k: {'status': 'PASS' if v else 'FAIL', 'reason': k, 'refs': [bundle['asset_id']]} for k, v in checks.items()},
            'blockers': blockers, 'warnings': ['Engineering checks are not semantic certification']}


def make_candidate(bundles, selections, statuses, scope='method_action_demo'):
    if scope not in SCOPES or not bundles or not selections:
        raise ValueError('Unsupported scope or empty selection')
    for b in bundles:
        verify_bundle(b)
    by_id = {b['asset_id']: b for b in bundles}
    if len(by_id) != len(bundles) or {s['asset_id'] for s in selections} != set(by_id):
        raise ValueError('Every source must have an explicit selection')
    if len({(s['asset_id'], s['method_id']) for s in selections}) != len(selections):
        raise ValueError('Duplicate method selection')
    if scope == 'method_comparison' and len({s['method_id'] for s in selections}) < 2:
        raise ValueError('Method comparison requires at least two methods')
    if scope == 'challenge' and (len(bundles) < 2 or {s.get('purpose') for s in selections} != {'teaching', 'challenge'}):
        raise ValueError('Challenge needs distinct teaching/challenge sources')
    gates, claims = [], []
    for sel in selections:
        b = by_id[sel['asset_id']]; mid = sel['method_id']; a = b['analysis']
        gate = engineering_gate(b, sel, scope, statuses.get(b['asset_id']))
        gates.append(gate)
        if gate['status'] != 'PASS':
            continue
        own_reviews = matching_reviews(b, sel)
        review_refs = [reference(b, '/reviews/' + str(i)) for i, _ in own_reviews]
        action_indexes = [i for i, x in enumerate(a['execution_trace']) if x['execution_id'] in sel['action_ids']]
        action_refs = [reference(b, '/analysis/execution_trace/' + str(i)) for i in action_indexes]
        evidence_ids = {eid for i in action_indexes for eid in a['execution_trace'][i]['evidence_ids']}
        evidence_refs = [reference(b, '/analysis/evidence_graph/nodes/' + str(i)) for i, n in enumerate(a['evidence_graph']['nodes']) if n['id'] in evidence_ids]
        def add(kind, text, path, local_actions=action_refs):
            if not isinstance(text, str) or not text.strip():
                return
            local_evidence = {eid for ref in local_actions for eid in a['execution_trace'][int(ref['pointer'].split('/')[-1])]['evidence_ids']}
            claim = {'text': text, 'kind': kind, 'method_id': mid, 'asset_id': b['asset_id'],
                     'source_ref': reference(b, path), 'action_artifact_refs': local_actions,
                     'evidence_refs': [ref for ref in evidence_refs if a['evidence_graph']['nodes'][int(ref['pointer'].split('/')[-1])]['id'] in local_evidence], 'review_refs': review_refs,
                     'purpose': sel.get('purpose', 'teaching')}
            claim['claim_id'] = 'claim:' + sha(claim)
            claims.append(claim)
        si = next(i for i, x in enumerate(a['method_chain']) if x['method_id'] == mid)
        mi = next(i for i, x in enumerate(b['methods']) if x['method_id'] == mid)
        step, method = a['method_chain'][si], b['methods'][mi]
        for kind, text, path in (
            ('core_action', step['action'], f'/analysis/method_chain/{si}/action'),
            ('stop_rule', step['stop_rule'], f'/analysis/method_chain/{si}/stop_rule'),
            ('method_name', method['brand_name'], f'/methods/{mi}/brand_name'),
            ('wrong_instinct', method.get('common_wrong_instinct'), f'/methods/{mi}/common_wrong_instinct')):
            add(kind, text, path)
        for i in action_indexes:
            x = a['execution_trace'][i]
            add('actual_action', x['concrete_action'], f'/analysis/execution_trace/{i}/concrete_action', [reference(b, f'/analysis/execution_trace/{i}')])
            add('action_stop', x['stop_rule_check'], f'/analysis/execution_trace/{i}/stop_rule_check', [reference(b, f'/analysis/execution_trace/{i}')])
        if scope == 'full_solution':
            add('answer', a['answer'], '/analysis/answer')
        if scope in ('boundary_demo', 'anti_rule_demo'):
            key = 'boundary' if scope == 'boundary_demo' else 'counterexample'
            for i, r in own_reviews:
                text = r['record'].get('reviewed_claims', {}).get(key)
                if text:
                    add(key, text, f'/reviews/{i}/record/reviewed_claims/{key}')
    gate_status = 'BLOCKED' if any(g['status'] == 'BLOCKED' for g in gates) else 'HOLD' if any(g['status'] != 'PASS' for g in gates) else 'PASS'
    source = source_gate(bundles)
    eligible = gate_status == 'PASS' and source['internal_use'] == 'PASS'
    levels = ['unreviewed', 'ai_reviewed', 'human_reviewed', 'human_certified']
    selection_levels = [max((r['level'] for _, r in matching_reviews(by_id[s['asset_id']], s)),
                            key=levels.index, default='unreviewed') for s in selections]
    level = min(selection_levels, key=levels.index)
    result = {'schema_version': '1.0.0', 'content_id': 'content:' + sha([selections, scope, [b['semantic_binding_sha'] for b in bundles]]),
              'content_scope': scope, 'source_items': deepcopy(bundles), 'selections': deepcopy(selections), 'claims': claims,
              'semantic_review': {'level': level, 'independent_human_certified': level == 'human_certified',
                  'reviewer_type': 'ai_host' if level == 'ai_reviewed' else 'human' if level.startswith('human') else 'unknown',
                  'status': 'usable_for_engineering_pilot' if eligible else 'blocked'},
              'teaching_engineering_gate': {'status': gate_status, 'items': gates},
              'engineering_pilot_eligible': eligible, 'source_use': source,
              'status': 'production_candidate' if eligible else 'blocked_teaching' if gate_status == 'BLOCKED' else 'review_required',
              'risk_flags': sorted(set((['upstream_review_ai_only'] if level == 'ai_reviewed' else []) + ['source_rights_unknown']
                  + (['answer_not_closed'] if any(not b['analysis']['answer_verification']['closed'] for b in bundles) else []))),
              'invalidation': {'teaching_stale': False, 'source_release_stale': False, 'editorial_stale': False, 'reasons': []}}
    validate('content-candidate', result)
    return result


def teaching_release(candidate):
    required = RELEASE_CHECKS[candidate['content_scope']]
    for sel in candidate['selections']:
        bundle = next(b for b in candidate['source_items'] if b['asset_id'] == sel['asset_id'])
        found = False
        for _, r in matching_reviews(bundle, sel):
            record = r['record']
            approval = record.get('release_review', {})
            if (r['level'] in ('human_reviewed', 'human_certified') and approval.get('status') == 'pass'
                and approval.get('content_scope') == candidate['content_scope']
                and approval.get('method_id') == sel['method_id']
                and set(sel['action_ids']) <= set(approval.get('action_ids', []))
                and required <= {k for k, v in approval.get('checks', {}).items() if v == 'pass'}):
                found = True
        if not found:
            return 'PENDING'
    return 'PASS'
