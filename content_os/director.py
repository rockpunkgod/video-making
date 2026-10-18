"""Deterministic scene planning over bound claims. No English solving."""
from copy import deepcopy
import math
import re
from video_contracts import ROOT, now, pointer, read, sha, status_matches, validate, verify_bundle

SCENE_TYPES = ('HOOK', 'QUESTION', 'WRONG_INSTINCT', 'LOCATE', 'COMPARE', 'EVIDENCE', 'CORE_ACTION', 'METHOD_REVEAL', 'STOP_RULE', 'VERDICT', 'TRANSFER', 'CTA')
NON_TEACHING_COPY = {'只看这一步。', '一起核对这个动作。', '先看证据，再看动作。', '收藏这一步，使用时记得核对边界。', '请独立完成挑战，再核对方法边界。'}


def excerpt_text(bundle, ref):
    value = pointer(bundle, ref['pointer'])
    if isinstance(value, str) and (ref['pointer'] in ('/source_snapshot/stem', '/source_snapshot/passage') or ref['pointer'].startswith('/source_snapshot/options/')):
        return value
    if isinstance(value, dict) and value.get('type') == 'source_evidence':
        return value['span']['quote']
    raise ValueError('Display reference is not a frozen source excerpt')


def claim_guard(text, citations=()):
    """Deterministic claim lint, NOT semantic truth certification."""
    reasons = []
    for pattern in (r'99\s*%', r'今年必考|高考最难|全网都在做|最近爆火|全网热题|热门卷',
                    r'必对|必错|一定选|答案就出来|分完.*答案'):
        if re.search(pattern, text):
            reasons.append('unsupported_expression:' + pattern)
    if re.search(r'\d+(?:\.\d+)?\s*[%％]|\d+成学生', text) and not citations:
        reasons.append('statistic_without_citation')
    return {'status': 'FAIL' if reasons else 'PASS', 'reasons': reasons,
            'scope': 'deterministic_claim_lint_not_semantic_truth_certification'}


def resolve_claims(candidate):
    for bundle in candidate['source_items']:
        verify_bundle(bundle)
    bundles = {b['asset_id']: b for b in candidate['source_items']}
    selected = {(s['asset_id'], s['method_id']): set(s['action_ids']) for s in candidate['selections']}
    for c in candidate['claims']:
        b = bundles[c['asset_id']]
        if c['source_ref']['asset_id'] != c['asset_id'] or pointer(b, c['source_ref']['pointer']) != c['text']:
            raise ValueError('Claim text does not equal frozen source')
        method = c['method_id']
        if (b['asset_id'], method) not in selected:
            raise ValueError('Claim method not selected')
        path = c['source_ref']['pointer']
        parent = pointer(b, path.rsplit('/', 1)[0])
        if path.startswith(('/methods/', '/analysis/method_chain/', '/analysis/execution_trace/')) and parent.get('method_id') != method:
            raise ValueError('Claim text belongs to another method')
        kind = c['kind']
        if kind not in ('core_action', 'stop_rule', 'actual_action', 'action_stop', 'method_name', 'wrong_instinct', 'answer', 'boundary', 'counterexample'):
            raise ValueError('Unknown teaching claim kind')
        expected = {'core_action': ('/analysis/method_chain/', '/action'),
                    'stop_rule': ('/analysis/method_chain/', '/stop_rule'),
                    'actual_action': ('/analysis/execution_trace/', '/concrete_action'),
                    'action_stop': ('/analysis/execution_trace/', '/stop_rule_check'),
                    'method_name': ('/methods/', '/brand_name'),
                    'wrong_instinct': ('/methods/', '/common_wrong_instinct')}
        if kind in expected and not (path.startswith(expected[kind][0]) and path.endswith(expected[kind][1])):
            raise ValueError('Claim kind/source mismatch')
        if kind in ('actual_action', 'action_stop') and c['action_artifact_refs'] != [
            {'asset_id': b['asset_id'], 'pointer': path.rsplit('/', 1)[0]}]:
            raise ValueError('Action claim must bind its own producing artifact')
        if kind in ('boundary', 'counterexample') and not (
            path.startswith('/reviews/') and path.endswith('/record/reviewed_claims/' + kind)):
            raise ValueError('Boundary claim lacks its explicit reviewed source')
        if kind == 'answer' and (candidate.get('content_scope') != 'full_solution' or path != '/analysis/answer'
                                or not b['analysis']['answer_verification']['closed']):
            raise ValueError('Answer claim outside a closed full solution')
        if not c['action_artifact_refs'] or not c['evidence_refs'] or not c['review_refs']:
            raise ValueError('Claim binding incomplete')
        evidence_ids = set()
        for ref in c['action_artifact_refs']:
            if ref['asset_id'] != b['asset_id']:
                raise ValueError('Cross-asset action laundering')
            action = pointer(b, ref['pointer'])
            if action['method_id'] != method or action['execution_id'] not in selected[b['asset_id'], method]:
                raise ValueError('Cross-method action laundering')
            evidence_ids.update(action['evidence_ids'])
        for ref in c['evidence_refs']:
            if ref['asset_id'] != b['asset_id'] or pointer(b, ref['pointer'])['id'] not in evidence_ids:
                raise ValueError('Evidence is not bound to this claim action')
        for ref in c['review_refs']:
            from .candidates import matching_reviews
            sel = next(s for s in candidate['selections'] if s['asset_id'] == b['asset_id'] and s['method_id'] == method)
            allowed_reviews = {'/reviews/' + str(i) for i, _ in matching_reviews(b, sel)}
            if ref['asset_id'] != b['asset_id'] or ref['pointer'] not in allowed_reviews:
                raise ValueError('Invalid claim review')
    return bundles


def copy_payload(package):
    return {'claims': package['claims'], 'content': package['content'],
            'semantic_scenes': package['semantic_scenes'], 'voiceover': package['voiceover'],
            'source_display': {k: v for k, v in package['source_display'].items() if k != 'release_review_id'}}


def output_text(output):
    if output['kind'] == 'candidate_partition':
        return '\n'.join(g['label'] + '：' + '、'.join(g['candidates']) for g in output['groups'])
    if output['kind'] == 'route_selection':
        return ' → '.join(output['node_ids'])
    if output['kind'] == 'candidate_decision':
        return output['candidate'] + '：' + output['effect']
    if output['kind'] == 'framework_card':
        return '\n'.join(p['name'] + '：' + p['value'] for p in output['fields'])
    return ''  # Structured output remains in method_visual; never invent an interpretation.


def build_draft(candidate, statuses, pattern_id='P02', duration_target=60):
    validate('content-candidate', candidate)
    if not candidate['engineering_pilot_eligible'] or candidate['invalidation']['teaching_stale']:
        raise ValueError('Candidate not eligible for Engineering Pilot')
    bundles = resolve_claims(candidate)
    from .candidates import make_candidate
    checked = make_candidate(candidate['source_items'], candidate['selections'], statuses, candidate['content_scope'])
    if not checked['engineering_pilot_eligible'] or checked['claims'] != candidate['claims']:
        raise ValueError('Candidate gate or claims no longer match frozen selections')
    if any(not status_matches(b, statuses[b['asset_id']]) for b in bundles.values()):
        raise ValueError('Current upstream validity check failed')
    pattern = read(ROOT / 'video/patterns' / (pattern_id + '.json'))
    if candidate['content_scope'] not in pattern['supported_scopes']:
        raise ValueError('Pattern does not support this scope')
    claims = deepcopy(candidate['claims'])
    available = {c['kind'] for c in claims}
    if not set(pattern['required_fields']) <= available:
        raise ValueError('Pattern required claims absent')
    if pattern_id == 'P04' and not any(c['purpose'] == 'challenge' for c in claims):
        raise ValueError('No independent challenge asset')
    scenes, excerpts = [], []
    def scene(kind, text, selected_claims=(), evidence_refs=(), visual=None, on_screen=None):
        if kind not in SCENE_TYPES:
            raise ValueError('Unknown scene type')
        # Bound quotes may contain an anti-rule being refuted; lint only generated copy.
        if not selected_claims and not evidence_refs and text not in NON_TEACHING_COPY:
            raise ValueError('Unbound generated teaching copy')
        scenes.append({'scene_id': f'scene-{len(scenes)+1:03d}', 'order': len(scenes), 'scene_type': kind,
            'spoken_text': text, 'on_screen': {'primary_text': text if on_screen is None else on_screen, 'secondary_text': ''},
            'claim_refs': [c['claim_id'] for c in selected_claims], 'evidence_refs': list(evidence_refs),
            'visual_intent': 'show_bound_information', 'method_visual': visual,
            'transition_intent': 'cut', 'duration_estimate': None})
    hook_claim = next(c for c in claims if c['kind'] == 'core_action' and c['purpose'] != 'challenge')
    scene('HOOK', hook_claim['text'], [hook_claim])
    for sel in candidate['selections']:
        b = bundles[sel['asset_id']]
        mine = [c for c in claims if c['asset_id'] == b['asset_id'] and c['method_id'] == sel['method_id']]
        if sel.get('purpose') == 'challenge':
            # Only prompt and evidence are visible; answer and action results stay out of copy.
            refs = [{'asset_id': b['asset_id'], 'pointer': '/source_snapshot/stem'}]
            if b['source_snapshot'].get('passage'):
                refs.append({'asset_id': b['asset_id'], 'pointer': '/source_snapshot/passage'})
            refs += [{'asset_id': b['asset_id'], 'pointer': '/source_snapshot/options/' + k.replace('~', '~0').replace('/', '~1')}
                     for k in b['source_snapshot'].get('options', {})]
            for ev in refs:
                excerpts.append({'excerpt_id': 'excerpt:' + sha(ev), 'ref': ev, 'text': excerpt_text(b, ev)})
            scene('QUESTION', '', evidence_refs=refs, on_screen='\n'.join(excerpt_text(b, ev) for ev in refs))
            scene('TRANSFER', '请独立完成挑战，再核对方法边界。')
            continue
        mapping = {c['kind']: c for c in mine}
        if pattern_id in ('P01', 'P03'):
            c = mapping['wrong_instinct']; scene('WRONG_INSTINCT', c['text'], [c])
        ev = mine[0]['evidence_refs'][0]
        node = pointer(b, ev['pointer']); text = node['span']['quote']
        excerpt = {'excerpt_id': 'excerpt:' + sha(ev), 'ref': ev, 'text': text}
        excerpts.append(excerpt)
        scene('EVIDENCE', '', evidence_refs=[ev], on_screen=text)
        c = mapping['core_action']; scene('CORE_ACTION', c['text'], [c])
        for c in [x for x in mine if x['kind'] == 'actual_action']:
            action = pointer(b, c['action_artifact_refs'][0]['pointer'])
            scene('COMPARE', c['text'], [c], c['evidence_refs'], action['output'], output_text(action['output']))
            from .course_mapping import action_visual_intent
            scenes[-1]['visual_intent'] = action_visual_intent(b, action)
        c = mapping['method_name']; scene('METHOD_REVEAL', c['text'], [c])
        for c in [x for x in mine if x['kind'] in ('stop_rule', 'action_stop', 'boundary', 'counterexample')]:
            scene('STOP_RULE', c['text'], [c])
        if candidate['content_scope'] == 'full_solution':
            c = mapping['answer']; scene('VERDICT', c['text'], [c])
    scene('CTA', '收藏这一步，使用时记得核对边界。')
    display = {'displayed_excerpt_ids': [x['excerpt_id'] for x in excerpts], 'excerpts': excerpts,
               'displayed_text_sha': sha([x['text'] for x in excerpts]), 'displayed_image_sha': sha([]),
               'images': [], 'attribution_text': '\n'.join(b['source'].get('attribution_text', '') for b in bundles.values()),
               'release_review_id': None}
    result = {'schema_version': '1.0.0', 'version': '0.1.0', 'content_id': candidate['content_id'],
        'package_id': 'package:' + sha([candidate['content_id'], claims, pattern, duration_target,
                                      candidate.get('content_score'), candidate.get('production_feasibility')]), 'status': 'draft',
        'source_items': deepcopy(candidate['source_items']), 'selections': deepcopy(candidate['selections']),
        'claims': claims, 'semantic_review': deepcopy(candidate['semantic_review']),
        'content': {'content_scope': candidate['content_scope'], 'pattern_id': pattern_id,
                    'primary_hook': scenes[0]['spoken_text'], 'alternate_hooks': [], 'cta': scenes[-1]['spoken_text']},
        'semantic_scenes': scenes, 'voiceover': [{'scene_id': s['scene_id'], 'text': s['spoken_text']} for s in scenes],
        'timeline': [], 'source_display': display,
        'production': {'duration_target': duration_target, 'actual_estimated_duration': None, 'aspect_ratio': '9:16',
                       'platform_profile': 'internal_engineering', 'template_family': 'semantic_contract_only', 'timing_version': '0.1.0'},
        'copy_lock': {'final_copy_sha': None, 'polished_from_sha': None, 'editorial_review_sha': None},
        'pilot_status': {'engineering': 'PENDING', 'semantic_release': 'PENDING', 'source_release': 'PENDING', 'editorial_release': 'PENDING'},
        'review': {'teaching_review': [], 'source_review': None, 'editorial_review': None},
        'render_ready_for_publication': False, 'invalidation': deepcopy(candidate['invalidation']),
        'manifest_ref': 'manifest.json', 'claim_guard': claim_guard(scenes[0]['spoken_text'])}
    validate('video-package', result)
    return result


def reading_seconds(text):
    chinese = len(re.findall(r'[\u3400-\u9fff]', text))
    words = len(re.findall(r'[A-Za-z0-9]+(?:[’\x27-][A-Za-z0-9]+)*', text))
    return chinese / 4 + words / 2.5


def finalize_copy(package):
    package = deepcopy(package)
    from .release import displayed_text
    elapsed = 0
    timeline = []
    for s in package['semantic_scenes']:
        duration = max(2, math.ceil(max(reading_seconds(s['spoken_text']),
                           reading_seconds(s['on_screen']['primary_text'] + s['on_screen']['secondary_text'])) + 0.8))
        s['duration_estimate'] = duration
        timeline.append({'scene_id': s['scene_id'], 'start': elapsed, 'end': elapsed + duration})
        elapsed += duration
    targets = [t for t in (30, 60, 90) if t >= package['production']['duration_target'] and t >= elapsed]
    package['timeline'] = timeline
    package['production']['actual_estimated_duration'] = elapsed
    package['production']['duration_target'] = targets[0] if targets else package['production']['duration_target']
    package['status'] = 'final_draft' if targets else 'blocked'
    package['pilot_status']['engineering'] = 'PASS' if targets else 'FAIL'
    if not targets:
        package['invalidation']['reasons'].append('reject_short_format')
    package['copy_lock']['final_copy_sha'] = sha(copy_payload(package))
    package['copy_lock']['editorial_review_sha'] = None
    package['review']['editorial_review'] = None
    package['pilot_status']['editorial_release'] = 'PENDING'
    package['render_ready_for_publication'] = False
    package['source_display']['displayed_text_sha'] = sha(displayed_text(package))
    package['copy_lock']['final_copy_sha'] = sha(copy_payload(package))
    validate('video-package', package)
    return package


def manifest(package, candidate, pattern_id=None):
    pattern = read(ROOT / 'video/patterns' / ((pattern_id or package['content']['pattern_id']) + '.json'))
    result = {'schema_version': '1.0.0', 'package_id': package['package_id'], 'generated_at': now(),
            'candidate_sha': sha(candidate), 'package_sha': sha(package),
            'inputs': [{'asset_id': b['asset_id'], 'content_sha': b['content_sha'], 'semantic_binding_sha': b['semantic_binding_sha'],
                        'method_versions': b['binding_fingerprint']['method_versions'],
                        'review_ids': [r['artifact_id'] for r in b['reviews']]} for b in package['source_items']],
            'pattern_version': pattern['version'], 'pattern_sha': sha(pattern), 'rubric_version': 'gaokao_education_v1',
            'ranking_policy_version': '0.1.0', 'director_version': '0.1.0', 'timing_version': '0.1.0',
            'final_copy_sha': package['copy_lock']['final_copy_sha']}
    validate('package-manifest', result)
    return result

