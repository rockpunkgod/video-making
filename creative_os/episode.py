"""Small multi-question container over frozen packages, not a truth compiler."""
import re
from video_contracts import pointer, sha, status_matches, validate
from content_os.release import validate_package
from content_os.candidates import matching_reviews

STAGES = ('original_task', 'observe', 'first_action', 'attention', 'helper',
          'evidence_alignment', 'judgement', 'payoff', 'closure')


def validate_episode(plan, statuses):
    validate('method-episode-plan', plan)
    if [q['editorial_role'] for q in plan['questions']] != ['establish', 'variation'] + (
            ['amplification'] if len(plan['questions']) == 3 else []):
        raise ValueError('Episode requires Establish, Variation and optional Amplification order')
    method = plan['method']; ids, material_hashes, canonical_ids = set(), set(), set()
    rows = []
    for segment in plan['questions']:
        package = segment['package']; validate_package(package)
        bundles = {b['asset_id']: b for b in package['source_items']}
        primary = [s for s in package['selections'] if s['method_id'] == method['method_id']]
        if not primary:
            raise ValueError('Episode theme lacks an actual selected method action')
        helpers = {s['method_id'] for s in package['selections'] if s['method_id'] != method['method_id']}
        if helpers != set(segment['helper_methods']):
            raise ValueError('Participating helper methods must retain their attribution')
        own_question = set()
        for selection in primary:
            b = bundles[selection['asset_id']]
            if b['binding_fingerprint']['method_versions'][method['method_id']] != method['version']:
                raise ValueError('Episode mixes core method versions')
            own_question.add(b['source_snapshot']['question_id'])
        if own_question != {segment['question_id']} or segment['question_id'] in ids:
            raise ValueError('Duplicate or cross-question episode segment')
        ids.add(segment['question_id'])
        canonical = {r['record']['canonical_question_id'] for selection in primary
            for _, r in matching_reviews(bundles[selection['asset_id']], selection)
            if r['record'].get('canonical_question_id')}
        if len(canonical) > 1 or canonical & canonical_ids:
            raise ValueError('Source aliases cannot count as separate questions')
        canonical_ids.update(canonical)
        snapshot = next(b['source_snapshot'] for b in bundles.values() if b['source_snapshot']['question_id'] == segment['question_id'])
        def normalized(value):
            return {k: normalized(v) for k, v in value.items()} if isinstance(value, dict) else re.sub(r'\s+', ' ', value).strip()
        identity = sha({k: normalized(snapshot[k]) for k in ('stem', 'passage', 'options') if k in snapshot})
        if identity in material_hashes:
            raise ValueError('Repackaged same question cannot be a variation')
        material_hashes.add(identity)
        functions = [b['function'] for b in segment['narrative_beats']]
        if not all(stage in functions for stage in STAGES if stage != 'helper'):
            raise ValueError('Incomplete independent question narrative')
        if helpers and 'helper' not in functions:
            raise ValueError('Necessary helper narrative omitted')
        if any(functions.index(a) >= functions.index(b) for a, b in
               zip([s for s in STAGES if s != 'helper'], [s for s in STAGES if s != 'helper'][1:])):
            raise ValueError('Question narrative order invalid')
        for beat in segment['narrative_beats']:
            if not beat['source_refs']:
                raise ValueError('Question beat has no source')
            for ref in beat['source_refs']:
                bundle = bundles[ref['asset_id']]
                if (bundle['source_snapshot']['question_id'] != segment['question_id']
                    or sha(pointer(bundle, ref['pointer'])) != ref['sha']):
                    raise ValueError('Cross-question or changed beat evidence')
        action_refs = segment['payoff']['action_refs']
        if not action_refs:
            raise ValueError('Payoff needs an actual producing action')
        for ref in action_refs:
            b = bundles[ref['asset_id']]; action = pointer(b, ref['pointer'])
            selected = [s for s in package['selections'] if s['asset_id'] == b['asset_id']]
            if (sha(action) != ref['sha'] or not any(action['execution_id'] in s['action_ids'] for s in selected)
                or sha(action['output']) not in segment['payoff']['output_shas']):
                raise ValueError('Payoff changed or borrowed another action')
        if segment['payoff']['result_scope'] == 'answer' and package['content']['content_scope'] != 'full_solution':
            raise ValueError('Helper cannot close episode question as answer')
        current = all(b['asset_id'] in statuses and status_matches(b, statuses[b['asset_id']]) for b in bundles.values())
        invalid = any(statuses.get(b['asset_id'], {}).get('effective_status') in
                      ('WITHDRAWN', 'SUPERSEDED', 'STALE', 'BLOCKED') for b in bundles.values())
        rows.append({'question_id': segment['question_id'], 'current_upstream': current,
                     'state': 'BLOCKED_UPSTREAM' if invalid else 'VALID_INTERNAL' if current else 'HOLD_UPSTREAM',
                     'teaching_stale': invalid, 'package_sha': sha(package)})
    return {'schema_version': '1.0.0', 'episode_plan_sha': sha(plan), 'questions': rows,
        'engineering_status': 'BLOCKED' if any(q['teaching_stale'] for q in rows) else
                              'PASS' if all(q['current_upstream'] for q in rows) else 'HOLD',
        'public_render_ready': False, 'human_review': 'PENDING',
        'method_generalizability': 'NOT_ASSESSED'}


def publication_episode(plan, requests, statuses):
    """All questions must approve the SAME final episode, including its framing.

    A per-question derivative approval cannot be transplanted into this master.
    The full final copy includes theme/stamp/recall and is identical in all
    requests. Each question still has its own source/scope/claim credentials.
    """
    from content_os.showcase import decide
    audit = validate_episode(plan, statuses)
    if set(requests) != {q['question_id'] for q in plan['questions']}:
        raise ValueError('Every independent question needs its own publication request')
    copies, media, decisions = set(), set(), []
    for q in plan['questions']:
        request = requests[q['question_id']]
        if sha(request['package']) != sha(q['package']):
            raise ValueError('Episode question has changed since publication request')
        if request['media']['production_receipt_sha'] != sha(plan):
            raise ValueError('Publication must bind the exact episode arrangement')
        copies.add(sha(request['final_copy'])); media.add(request['media']['sha256'])
        decisions.append({'question_id': q['question_id'], 'decision': decide(request, statuses)})
    if len(copies) != 1 or len(media) != 1 or None in media:
        raise ValueError('Question approvals must bind the same actual full episode and copy')
    ready = audit['engineering_status'] == 'PASS' and all(
        q['decision']['public_render_ready'] for q in decisions)
    return {'schema_version': '1.0.0', 'policy': 'free_showcase_v1',
        'episode_plan_sha': sha(plan), 'questions': decisions,
        'state': 'APPROVED_FOR_PUBLIC_EXPORT' if ready else 'BLOCKED' if any(
            q['decision']['state'] == 'BLOCKED' for q in decisions) else 'INTERNAL_ONLY',
        'public_render_ready': ready, 'method_generalizability': 'NOT_ASSESSED'}
