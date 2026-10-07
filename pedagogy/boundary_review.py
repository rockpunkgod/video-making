"""Consume explicit Pedagogy risk reviews; never generate teaching reviews.

The default policy stays conservative. A case-bound external review may move
an unexercised branch to Later or cover a current Stop with existing evidence
and bounded output. This module validates bindings/coverage, not English truth.
"""
from copy import deepcopy

from video_contracts import ROOT, _validator, pointer, seal, sha, verify_seal
from . import policy

VERSION = '0.1.1'


def inventory(plan, bundle):
    rows = []
    boundaries = plan['boundaries']['tell_now'] + plan['boundaries']['tell_later']
    for risk in plan['teaching_risk']['items']:
        for ref in risk['source_refs']:
            item = next(b for b in boundaries if ref in b['source_refs'])
            rows.append({'source_ref': deepcopy(ref), 'text': pointer(bundle, ref['pointer']),
                         'current_action_stop': item['current_action_stop']})
    return rows


def _range(span, text):
    if (not isinstance(span, list) or len(span) != 2
            or any(isinstance(n, bool) or not isinstance(n, int) for n in span)
            or not 0 <= span[0] < span[1] <= len(text)):
        raise ValueError('Boundary coverage needs an exact, nonempty literal range')
    return range(*span)


def apply_review(base, bundle, review):
    """Apply a supplied, sealed review after the ordinary source/status check.

    This is an additive contract: absent a review, existing Plan hashes and
    conservative disclosure remain unchanged. All source Stops stay in guard.
    """
    from jsonschema import ValidationError
    from .compiler import plan_semantics
    path = ROOT / 'schemas' / 'boundary-risk-review.json'
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(review)
    except ValidationError as error:
        raise ValueError('Invalid Boundary Risk Review: ' + error.message) from error
    verify_seal(review)
    if review['status'] != 'pass':
        raise ValueError('Boundary Risk Review is not approved for this internal projection')
    rows = inventory(base, bundle)
    binding = review['binding']
    if (base['plan_sha'] not in binding['source_plan_shas']
            or binding['input_binding'] != base['input_binding']
            or binding['source_analysis_sha'] != base['source_analysis_sha']
            or binding['truth_guard_sha'] != sha(base['truth_guard'])
            or binding['boundary_inventory_sha'] != sha(rows)):
        raise ValueError('Boundary Risk Review belongs to different frozen inputs or Plan')
    if [e['source_ref'] for e in review['entries']] != [r['source_ref'] for r in rows]:
        raise ValueError('Boundary Risk Review must account for every original boundary in order')
    original = {sha(r['source_ref']): r for r in rows}
    entries = {sha(e['source_ref']): e for e in review['entries']}
    own_refs = (base['source_refs'] + base['evidence_refs'] + base['truth_guard']['review_refs']
                + [r['source_ref'] for r in rows])
    # Evidence references are action-owned; presentation cannot borrow another
    # method's proof, and suppressed proof stays available in the full guard.
    focus = review['delivery']['focus_evidence_refs']
    if not focus or len({sha(r) for r in focus}) != len(focus) or any(
            r not in base['evidence_refs'] for r in focus):
        raise ValueError('Boundary delivery requires unique action-owned evidence')
    for entry, row in zip(review['entries'], rows):
        if not entry['assessment_refs'] or any(r not in own_refs for r in entry['assessment_refs']):
            raise ValueError('Boundary risk rationale needs this action/method/review evidence')
        if row['current_action_stop'] and entry['decision'] != 'TELL_NOW':
            raise ValueError('Current action Stop cannot be moved to Later')
        if entry['decision'] == 'TELL_LATER' and (
                entry['risk']['current_relevance'] != 'low'
                or entry['current_applicability'] != 'not_exercised'
                or entry['risk']['severity'] == 'unknown'):
            raise ValueError('Later requires explicit case-specific non-applicability and assessed severity')
        if 'clause_assessments' in entry:
            assessed = set()
            for clause in entry['clause_assessments']:
                extent = set(_range(clause['range'], row['text']))
                if assessed & extent:
                    raise ValueError('Composite boundary assessments cannot overlap')
                assessed.update(extent)
            if assessed != set(range(len(row['text']))):
                raise ValueError('Composite boundary assessment must cover its entire frozen text')
    bounded = review['delivery']['bounded_candidate_state']
    if bounded:
        support = base['payoff']['reviewed_support']
        if (not support or support.get('origin') != 'frozen_candidate_transition'
                or base['answer_scope']['may_output_final_answer']
                or base['answer_scope']['upstream_closed']):
            raise ValueError('Bounded-state coverage needs a valid unclosed candidate transition')
        state = support['record']['answer_scope']
        if state['closed'] or state['may_output_final_answer'] or not state['remaining_candidates']:
            raise ValueError('Current boundary cannot be covered by a final-answer display')
    groups, covered = [], set()
    original_items = base['boundaries']['tell_now'] + base['boundaries']['tell_later']
    review_asset = 'pedagogy-boundary-review:' + review['content_sha']
    if len({g['group_id'] for g in review['presentations']}) != len(review['presentations']):
        raise ValueError('Reviewed boundary presentation IDs must be unique')
    for index, group in enumerate(review['presentations']):
        member_keys = [sha(r) for r in group['member_refs']]
        if (len(member_keys) != len(set(member_keys)) or covered.intersection(member_keys)
                or any(k not in entries or entries[k]['decision'] != 'TELL_NOW' for k in member_keys)):
            raise ValueError('Each current boundary needs exactly one reviewed presentation')
        literal_key = sha(group['literal_ref'])
        if literal_key not in member_keys:
            raise ValueError('Boundary presentation must quote one of its own members')
        literal = original[literal_key]['text']
        _range(group['literal_range'], literal)
        a, b = group['literal_range']
        coverage = {k: set() for k in member_keys}
        for part in group['coverage']:
            key = sha(part['source_ref'])
            if key not in coverage:
                raise ValueError('Boundary coverage cites another presentation or method')
            extent = set(_range(part['range'], original[key]['text']))
            if extent & coverage[key]:
                raise ValueError('Boundary clauses cannot overlap or silently disappear')
            coverage[key].update(extent)
            mechanism = part['mechanism']
            if mechanism == 'literal_display' and not (key == literal_key and extent <= set(range(a, b))):
                raise ValueError('Literal coverage must actually be visible in the presented quote')
            if mechanism == 'bounded_candidate_state' and not bounded:
                raise ValueError('Output-scope clause lacks its bounded candidate display')
            if mechanism == 'evidence_focus' and group['scene'] not in ('focus', 'action'):
                raise ValueError('Evidence boundary must accompany the actual comparison')
        if any(coverage[k] != set(range(len(original[k]['text']))) for k in member_keys):
            raise ValueError('Every clause of each current boundary needs explicit coverage')
        for key in member_keys:
            if original[key]['current_action_stop'] and not any(
                    sha(c['source_ref']) == key and c['mechanism'] in (
                        'literal_display', 'evidence_focus', 'bounded_candidate_state')
                    for c in group['coverage']):
                raise ValueError('Current Stop needs visible evidence/output coverage, not only backend labels')
        template = next(i for i in original_items if group['literal_ref'] in i['source_refs'])
        item = deepcopy(template)
        item.update(item_id=group['group_id'], text=policy.surface_text(literal[a:b]),
            source_refs=deepcopy(group['member_refs']), projection_operation='reviewed_boundary_coverage_v1',
            current_action_stop=any(original[k]['current_action_stop'] for k in member_keys),
            risk={'frequency': 'unknown',
                  'severity': max((entries[k]['risk']['severity'] for k in member_keys),
                                  key=policy.RISK_LEVELS.index), 'current_relevance': 'high'},
            risk_assessment_refs=[{'asset_id': review_asset, 'pointer': '/presentations/' + str(index),
                                   'sha': sha(group)}],
            disclosure_tier='TELL_NOW', disclosure_reason=group['rationale'])
        groups.append(item)
        covered.update(member_keys)
    expected = {k for k, e in entries.items() if e['decision'] == 'TELL_NOW'}
    if covered != expected:
        raise ValueError('Review leaves a current boundary without its student presentation')
    result = deepcopy(base)
    later, risks = [], []
    for index, (entry, row) in enumerate(zip(review['entries'], rows)):
        ref = {'asset_id': review_asset, 'pointer': '/entries/' + str(index), 'sha': sha(entry)}
        key = sha(entry['source_ref'])
        item = next(i for i in original_items if entry['source_ref'] in i['source_refs'])
        if entry['decision'] == 'TELL_LATER':
            item = deepcopy(item)
            item.update(source_refs=[deepcopy(entry['source_ref'])], disclosure_tier='TELL_LATER',
                        risk=deepcopy(entry['risk']), risk_assessment_refs=[ref],
                        disclosure_reason=entry['rationale'])
            later.append(item)
        group_id = next((g['item_id'] for g in groups if entry['source_ref'] in g['source_refs']), item['item_id'])
        risks.append({'item_id': group_id, 'source_refs': [deepcopy(entry['source_ref'])],
                      'risk': deepcopy(entry['risk']), 'tier': entry['decision'],
                      'assessment_refs': [ref], 'reason': entry['rationale']})
    result['boundaries']['tell_now'] = groups
    result['boundaries']['tell_later'] = later
    result['student_model']['stop'] = deepcopy(groups)
    result['student_steps'] = [s for s in result['student_steps'] if s['kind'] != 'stop']
    if base['mode'] != 'first_touch':
        result['student_steps'] += [{'kind': 'stop', 'item': deepcopy(g)} for g in groups]
    omissions = [o for o in base['omitted_items'] if o['disclosure_tier'] != 'TELL_LATER']
    omissions += [dict(item_id=i['item_id'], reason=i['disclosure_reason'], disclosure_tier='TELL_LATER',
                       still_exists=True, source_refs=deepcopy(i['source_refs']),
                       risk_assessment_refs=deepcopy(i['risk_assessment_refs'])) for i in later]
    result['omitted_items'] = omissions
    result['compression_audit']['omitted'] = deepcopy(omissions)
    result['teaching_risk']['items'] = risks
    result['boundary_delivery'] = {
        'review_sha': review['content_sha'], 'contract_version': VERSION,
        'focus_evidence_refs': deepcopy(focus), 'bounded_candidate_state': bounded,
        'placements': [{'item_id': g['group_id'], 'scene': g['scene']} for g in review['presentations']],
        'original_boundary_count': len(rows), 'student_presentation_count': len(groups),
        'semantic_truth_certification': False}
    # Recompute budgets rather than simply clearing HOLD. Unrelated evidence
    # gaps, lints, and load failures retain exactly their original constraints.
    metrics = result['cognitive_load']['metrics']
    metrics['primary_boundary'] = len(groups)
    student_items = [result[k] for k in ('symptom', 'first_signal', 'first_action',
                                        'judgment_point', 'memory_phrase') if result[k]] + groups
    student_items += [s['item'] for s in result['student_steps']]
    excess = policy.overload(metrics, student_items) if base['mode'] == 'first_touch' else []
    result['cognitive_load'].update(exceeded=excess, status='PEDAGOGY_OVERLOAD' if excess
                                  else 'PASS' if base['mode'] == 'first_touch' else 'NOT_FIRST_TOUCH')
    availability = result['availability']
    availability['blockers'] = [b for b in availability['blockers'] if not b.startswith('PEDAGOGY_OVERLOAD:')]
    availability['blockers'] += ['PEDAGOGY_OVERLOAD:' + e for e in excess]
    availability['status'] = 'UNAVAILABLE_EVIDENCE_GAP' if availability['gaps'] else \
        'HOLD' if availability['blockers'] else 'READY'
    result['public_claims'] = deepcopy(student_items) if availability['status'] == 'READY' else []
    result['compression_audit']['included'] = [i['item_id'] for i in result['public_claims']]
    result['replay_request']['boundary_review'] = deepcopy(review)
    result['plan_sha'] = sha(plan_semantics(result))
    result['plan_id'] = 'pedagogy:' + result['plan_sha']
    return seal(result)
