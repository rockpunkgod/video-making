"""Independent publication keys bound to final copy and actual source display."""
from copy import deepcopy
from video_contracts import pointer, sha, status_matches, validate
from .candidates import teaching_release, engineering_gate
from .director import copy_payload, resolve_claims, output_text, NON_TEACHING_COPY, excerpt_text


def display_payload(package):
    display = package['source_display']
    return {'displayed_excerpt_ids': display['displayed_excerpt_ids'], 'excerpts': display['excerpts'],
            'displayed_text_sha': display['displayed_text_sha'], 'displayed_image_sha': display['displayed_image_sha'],
            'images': display['images'], 'attribution_text': display['attribution_text']}


def displayed_text(package):
    return [{'scene_id': s['scene_id'], 'on_screen': s['on_screen'], 'method_visual': s['method_visual']}
            for s in package['semantic_scenes']]


def validate_package(package):
    validate('video-package', package)
    candidate = {'source_items': package['source_items'], 'selections': package['selections'], 'claims': package['claims'],
                 'content_scope': package['content']['content_scope']}
    bundles = resolve_claims(candidate)
    claims = {c['claim_id']: c for c in package['claims']}
    if len(claims) != len(package['claims']):
        raise ValueError('Duplicate claim id')
    for c in claims.values():
        if c['claim_id'] != 'claim:' + sha({k: v for k, v in c.items() if k != 'claim_id'}):
            raise ValueError('Claim identity mismatch')
    for sel in package['selections']:
        b = bundles[sel['asset_id']]
        gate = engineering_gate(b, sel, package['content']['content_scope'], None)
        if any(k != 'current_upstream_valid' and v['status'] != 'PASS' for k, v in gate['checks'].items()):
            raise ValueError('Package selection no longer satisfies frozen engineering gate')
        mine = [c for c in claims.values() if c['asset_id'] == sel['asset_id'] and c['method_id'] == sel['method_id']]
        required = {'core_action', 'stop_rule', 'method_name', 'actual_action', 'action_stop'}
        scope = package['content']['content_scope']
        if scope == 'full_solution': required.add('answer')
        if scope == 'boundary_demo': required.add('boundary')
        if scope == 'anti_rule_demo': required.update(('counterexample', 'wrong_instinct'))
        if not required <= {c['kind'] for c in mine}:
            raise ValueError('Required teaching claims removed')
        for action_id in sel['action_ids']:
            for kind in ('actual_action', 'action_stop'):
                if not any(c['kind'] == kind and any(pointer(b, r['pointer'])['execution_id'] == action_id for r in c['action_artifact_refs']) for c in mine):
                    raise ValueError('Selected action or boundary omitted')
    if len({s['scene_id'] for s in package['semantic_scenes']}) != len(package['semantic_scenes']):
        raise ValueError('Duplicate scene id')
    if [s['order'] for s in package['semantic_scenes']] != list(range(len(package['semantic_scenes']))):
        raise ValueError('Scene order mismatch')
    for s in package['semantic_scenes']:
        cs = [claims[c] for c in s['claim_refs']]
        if any(c['purpose'] == 'challenge' for c in cs):
            raise ValueError('Challenge solution leaked into scene')
        if cs:
            if len(cs) != 1 or s['spoken_text'] != cs[0]['text']:
                raise ValueError('Scene changed bound claim')
            allowed_screen = {cs[0]['text']}
            if s['method_visual'] is not None:
                c = cs[0]
                action = pointer(bundles[c['asset_id']], c['action_artifact_refs'][0]['pointer'])
                if s['method_visual'] != action['output']:
                    raise ValueError('Visual changed action output')
                allowed_screen.add(output_text(action['output']))
            if s['on_screen']['primary_text'] not in allowed_screen or s['on_screen']['secondary_text']:
                raise ValueError('Screen copy changed teaching claim')
        elif s['evidence_refs']:
            texts = [excerpt_text(bundles[r['asset_id']], r) for r in s['evidence_refs']]
            if s['on_screen']['primary_text'] != '\n'.join(texts) or s['spoken_text'] or s['on_screen']['secondary_text'] or s['method_visual'] is not None:
                raise ValueError('Evidence display changed source quote')
        elif (s['spoken_text'] not in NON_TEACHING_COPY or s['on_screen']['primary_text'] != s['spoken_text']
              or s['on_screen']['secondary_text'] or s['method_visual'] is not None):
            raise ValueError('Unbound scene copy')
    used = {r for s in package['semantic_scenes'] for r in s['claim_refs']}
    required_kinds = {'core_action', 'actual_action', 'method_name', 'stop_rule', 'action_stop'}
    if package['content']['content_scope'] == 'full_solution':
        required_kinds.add('answer')
    if package['content']['content_scope'] == 'boundary_demo':
        required_kinds.add('boundary')
    if package['content']['content_scope'] == 'anti_rule_demo':
        required_kinds.update(('counterexample', 'wrong_instinct'))
    if any(c['claim_id'] not in used for c in package['claims'] if c['kind'] in required_kinds and c['purpose'] != 'challenge'):
        raise ValueError('Required teaching action or boundary omitted')
    for c in package['claims']:
        if c['kind'] == 'actual_action' and c['purpose'] != 'challenge' and not any(
            c['claim_id'] in s['claim_refs'] and s['method_visual'] is not None for s in package['semantic_scenes']):
            raise ValueError('Actual action output omitted')
    if package['content']['content_scope'] == 'method_action_demo' and any(s['scene_type'] == 'VERDICT' for s in package['semantic_scenes']):
        raise ValueError('Helper action cannot become final verdict')
    if package['voiceover'] != [{'scene_id': s['scene_id'], 'text': s['spoken_text']} for s in package['semantic_scenes']]:
        raise ValueError('Voiceover/scene divergence')
    if package['content']['primary_hook'] != package['semantic_scenes'][0]['spoken_text'] or package['content']['cta'] != package['semantic_scenes'][-1]['spoken_text']:
        raise ValueError('Hook/CTA divergence')
    display = package['source_display']
    if display['displayed_text_sha'] != sha(displayed_text(package)) or display['displayed_image_sha'] != sha(display['images']):
        raise ValueError('Source display fingerprint mismatch')
    if display['images']:
        raise ValueError('Image display requires a future checked image adapter')
    if display['displayed_excerpt_ids'] != [e['excerpt_id'] for e in display['excerpts']]:
        raise ValueError('Excerpt identity mismatch')
    for e in display['excerpts']:
        r = e['ref']
        if e['text'] != excerpt_text(bundles[r['asset_id']], r):
            raise ValueError('Source excerpt drift')
    if package['copy_lock']['final_copy_sha'] != sha(copy_payload(package)):
        raise ValueError('Final copy lock mismatch')
    elapsed = 0
    if len(package['timeline']) != len(package['semantic_scenes']):
        raise ValueError('Incomplete timeline')
    for t, s in zip(package['timeline'], package['semantic_scenes']):
        if t['scene_id'] != s['scene_id'] or t['start'] != elapsed or t['end'] != elapsed + s['duration_estimate']:
            raise ValueError('Invalid timing')
        elapsed = t['end']
    if elapsed != package['production']['actual_estimated_duration']:
        raise ValueError('Total duration mismatch')
    if package['pilot_status']['engineering'] == 'PASS' and elapsed > package['production']['duration_target']:
        raise ValueError('Unsafe short-format timing')
    return True


def publication_check(package, statuses):
    from .lifecycle import refresh
    p = refresh(package, statuses)
    try:
        validate_package(p)
        current = all(status_matches(b, statuses[b['asset_id']]) for b in p['source_items'])
    except (ValueError, KeyError):
        current = False
    teaching = teaching_release({'source_items': p['source_items'], 'selections': p['selections'], 'content_scope': p['content']['content_scope']})
    p['review']['teaching_review'] = [{'asset_id': b['asset_id'], 'review_id': r['artifact_id'], 'review_sha': r['sha']}
        for b in p['source_items'] for r in b['reviews'] if r['level'] in ('human_reviewed', 'human_certified') and r['record'].get('release_review')]
    source = p['review']['source_review'] or {}
    editorial = p['review']['editorial_review'] or {}
    source_pass = (source.get('reviewer_kind') == 'human' and source.get('status') == 'pass'
        and source.get('display_sha') == sha(display_payload(p))
        and source.get('source_bindings') == {b['asset_id']: statuses.get(b['asset_id'], {}).get('source_sha') for b in p['source_items']}
        and bool(source.get('reviewer')) and bool(source.get('review_id')))
    editorial_pass = (editorial.get('reviewer_kind') == 'human' and editorial.get('status') == 'pass'
        and editorial.get('final_copy_sha') == p['copy_lock']['final_copy_sha']
        and editorial.get('final_copy_sha') == sha(copy_payload(p))
        and editorial.get('display_sha') == sha(display_payload(p))
        and editorial.get('teaching_bindings') == {b['asset_id']: b['semantic_binding_sha'] for b in p['source_items']}
        and p['copy_lock']['editorial_review_sha'] == sha(editorial)
        and all(editorial.get('checks', {}).get(k) == 'pass' for k in
                ('teaching_consistency', 'role', 'evidence', 'stop_rule', 'hook', 'subtitle', 'source_display', 'challenge_no_leak'))
        and bool(editorial.get('reviewer')) and bool(editorial.get('review_id')))
    inv = p['invalidation']
    p['pilot_status'].update(semantic_release=teaching if current and not inv['teaching_stale'] else 'PENDING',
                            source_release='PASS' if current and source_pass and not inv['source_release_stale'] else 'PENDING',
                            editorial_release='PASS' if current and editorial_pass and not inv['editorial_stale'] else 'PENDING')
    p['render_ready_for_publication'] = (current and p['pilot_status']['engineering'] == 'PASS'
        and all(p['pilot_status'][k] == 'PASS' for k in ('semantic_release', 'source_release', 'editorial_release')))
    if p['render_ready_for_publication']:
        p['status'] = 'locked'
    elif p['status'] == 'locked':
        p['status'] = 'editorial_review'
    return p


def apply_reviews(package, statuses, source=None, editorial=None):
    from .lifecycle import refresh
    p = refresh(package, statuses)
    validate_package(p)
    if not all(status_matches(b, statuses[b['asset_id']]) for b in p['source_items']):
        raise ValueError('Cannot approve stale upstream')
    if source is not None:
        p['review']['source_review'] = deepcopy(source)
        p['source_display']['release_review_id'] = source.get('review_id')
        p['invalidation']['source_release_stale'] = False
    if editorial is not None:
        p['review']['editorial_review'] = deepcopy(editorial)
        p['copy_lock']['editorial_review_sha'] = sha(editorial)
        p['invalidation']['editorial_stale'] = False
    return publication_check(p, statuses)


def ae_contract(package, statuses, internal=False):
    p = publication_check(package, statuses)
    validate_package(p)
    if not all(status_matches(b, statuses[b['asset_id']]) for b in p['source_items']):
        raise ValueError('AE handoff requires current upstream')
    if p['invalidation']['teaching_stale'] or p['pilot_status']['engineering'] != 'PASS':
        raise ValueError('AE handoff requires Engineering Pilot PASS')
    if not internal and not p['render_ready_for_publication']:
        raise ValueError('PUBLIC_RENDER_READY requires three independent releases')
    bundles = {b['asset_id']: b for b in p['source_items']}
    used_claims = {c for s in p['semantic_scenes'] for c in s['claim_refs']}
    refs = {sha(r): r for s in p['semantic_scenes'] for r in s['evidence_refs']}
    evidence = [{'ref': r, 'text': excerpt_text(bundles[r['asset_id']], r)} for r in refs.values()]
    methods = []
    for sel in p['selections']:
        if sel.get('purpose') == 'challenge':
            continue
        b = bundles[sel['asset_id']]
        m = next(m for m in b['methods'] if m['method_id'] == sel['method_id'])
        step = next(s for s in b['analysis']['method_chain'] if s['method_id'] == sel['method_id'])
        methods.append({'asset_id': b['asset_id'], 'method_id': m['method_id'], 'version': m['version'],
                        'brand_name': m['brand_name'], 'role': step['role']})
    return {'schema_version': '0.1.0', 'package_id': p['package_id'], 'package_sha': sha(p),
            'usage': 'internal_engineering_only' if internal else 'public_render',
            'public_render_ready': not internal and p['render_ready_for_publication'],
            'canvas': {'width': 1080, 'height': 1920, 'safe_inset': 96},
            'scenes': p['semantic_scenes'], 'timeline': p['timeline'], 'source_display': p['source_display'],
            'claims': [c for c in p['claims'] if c['claim_id'] in used_claims], 'evidence': evidence, 'methods': methods,
            'copy_lock': p['copy_lock']}
