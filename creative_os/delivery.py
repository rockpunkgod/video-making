"""Bound wording, explicit internal fidelity review and deterministic expansion lint.

These checks are not a semantic truth certification. Rewrites require a copy-bound
host review; public teaching certification remains exclusively upstream.
"""
from copy import deepcopy
import re
from typing import Protocol
from video_contracts import sha, pointer
from content_os.director import resolve_claims, claim_guard
from content_os.release import ae_contract, validate_package

VERSION = '0.1.0'
CHECKS = ('claim_coverage', 'evidence_coverage', 'role_preservation',
          'certainty_preservation', 'quantifier_preservation',
          'causality_preservation', 'stop_preservation')
CLICHES = ('首先', '其次', '此外', '值得注意的是', '从本质上来看', '这意味着',
           '换句话说', '由此可见', '不难发现', '显而易见', '这就是为什么',
           '我们可以看到', '让我们来看一下')
SLANG = ('家人们', '兄弟们', '绝绝子', '太离谱了', '这波', '狠狠拿捏')


class HumanVoiceWriter(Protocol):
    def write(self, delivery_request: dict) -> dict: ...


class AstraHumanVoiceAdapter:
    """Injected transport only. There is no built-in or simulated Astra API."""
    def __init__(self, transport=None): self.transport = transport
    def write(self, delivery_request):
        if self.transport is None: raise ValueError('astra_transport_unavailable')
        return self.transport(deepcopy(delivery_request))


class FixtureHumanVoiceWriter:
    def __init__(self, response): self.response = deepcopy(response)
    def write(self, delivery_request): return deepcopy(self.response)


def teaching_sha(package):
    return sha({'bindings': {b['asset_id']: b['semantic_binding_sha'] for b in package['source_items']},
                'claims': package['claims'], 'selections': package['selections'],
                'roles': [{k: s[k] for k in ('method_id', 'role')} for b in package['source_items']
                          for s in b['analysis']['method_chain']],
                'scene_semantics': [{k: s[k] for k in ('scene_id', 'claim_refs', 'evidence_refs', 'method_visual')}
                                    for s in package['semantic_scenes']]})


def copy_sha(delivery):
    return sha([{k: u[k] for k in ('unit_id', 'scene_id', 'spoken_copy', 'on_screen_copy', 'tone')}
                for u in delivery['units']])


def screen_sha(delivery):
    return sha([{'unit_id': u['unit_id'], 'text': u['on_screen_copy']} for u in delivery['units']])


def meaning_sha(unit):
    return sha({k: unit[k] for k in ('unit_id', 'scene_id', 'intent', 'source_claim_refs', 'source_meaning', 'evidence_refs',
                                    'action_artifact_refs', 'review_refs', 'role',
                                    'protected_terms', 'prohibited_implications', 'visual_excerpts')})


def unit_copy_sha(unit):
    return sha({k: unit[k] for k in ('spoken_copy', 'on_screen_copy')})


def sentence_bindings(unit):
    return [{'text': text, 'source_claim_refs': deepcopy(unit['source_claim_refs']),
             'evidence_refs': deepcopy(unit['evidence_refs'])}
            for text in re.findall(r'[^。！？]+[。！？]?|[。！？]', unit['spoken_copy'])]


def make_delivery(package, manifest, statuses, specs):
    """Bind editor-supplied units without changing one byte of the frozen package."""
    validate_package(package); ae_contract(package, statuses, internal=True)
    if manifest['package_sha'] != sha(package): raise ValueError('Frozen manifest mismatch')
    bundles = resolve_claims(package); claims = {c['claim_id']: c for c in package['claims']}
    scenes = {s['scene_id']: s for s in package['semantic_scenes']}
    units = []
    for i, spec in enumerate(specs):
        refs = spec['source_claim_refs']
        if not refs or len(set(refs)) != len(refs) or spec['scene_id'] not in scenes:
            raise ValueError('Unit needs unique claim refs and a frozen scene')
        source = [claims[r] for r in refs]
        methods = {(c['asset_id'], c['method_id']) for c in source}
        if len(methods) != 1: raise ValueError('Cross-method delivery unit')
        aid, mid = next(iter(methods))
        role = next(s['role'] for s in bundles[aid]['analysis']['method_chain'] if s['method_id'] == mid)
        def unique(key):
            values = [r for c in source for r in c[key]]
            return list({sha(r): deepcopy(r) for r in values}.values())
        u = {'unit_id': spec.get('unit_id', f'unit-{i+1:03d}'), 'scene_id': spec['scene_id'],
             'source_claim_refs': deepcopy(refs), 'evidence_refs': unique('evidence_refs'),
             'action_artifact_refs': unique('action_artifact_refs'), 'review_refs': unique('review_refs'),
             'method_id': mid, 'asset_id': aid, 'role': role, 'intent': spec['intent'],
             'source_meaning': [{'claim_id': c['claim_id'], 'text': c['text']} for c in source],
             'spoken_copy': spec['spoken_copy'], 'on_screen_copy': spec['on_screen_copy'],
             'protected_terms': deepcopy(spec.get('protected_terms', [])),
             'prohibited_implications': ['new_teaching_judgment', 'whole_answer_from_bounded_action',
                                         'certainty_or_quantifier_expansion', 'omitted_stop'],
             'tone': spec.get('tone', 'direct_restrained'), 'pause_after': spec.get('pause_after', 0.35),
             'breath': spec.get('breath', 'natural_clause_break'),
             'emphasis': deepcopy(spec.get('emphasis', [])),
             'visual_excerpts': deepcopy(spec.get('visual_excerpts', [])), 'fidelity_review': None}
        u['sentence_bindings'] = sentence_bindings(u); units.append(u)
    result = {'schema_version': VERSION, 'version': VERSION, 'delivery_id': 'delivery:' + sha([sha(package), specs]),
              'package_id': package['package_id'], 'package_sha': sha(package), 'manifest_sha': sha(manifest),
              'teaching_semantic_sha': teaching_sha(package), 'provider': 'agent_authored_internal',
              'units': units, 'delivery_copy_sha': None, 'screen_copy_sha': None,
              'editorial_review_sha': None, 'public_render_ready': False}
    result['delivery_copy_sha'] = copy_sha(result); result['screen_copy_sha'] = screen_sha(result)
    return result


def apply_writer(delivery, adapter: HumanVoiceWriter):
    result = adapter.write(deepcopy(delivery)); expected = deepcopy(delivery)
    if len(result.get('units', [])) != len(expected['units']): raise ValueError('Writer changed unit structure')
    for original, changed in zip(expected['units'], result['units']):
        for k in ('spoken_copy', 'on_screen_copy'):
            original[k] = changed[k]
    if expected != result: raise ValueError('Writer changed protected facts, references or policy')
    for u in result['units']:
        u['fidelity_review'] = None; u['sentence_bindings'] = sentence_bindings(u)
    result['delivery_copy_sha'] = copy_sha(result); result['screen_copy_sha'] = screen_sha(result)
    result['editorial_review_sha'] = None; result['public_render_ready'] = False
    result['delivery_id'] = 'delivery:' + sha([result['package_sha'], result['units']])
    return result


def attach_fidelity_review(delivery, unit_id, reviewer, rationale):
    """Explicit host review attestation, never an ANSWER Review or independent approval."""
    result = deepcopy(delivery); u = next(u for u in result['units'] if u['unit_id'] == unit_id)
    if not isinstance(reviewer, str) or not reviewer.strip() or set(rationale) != set(CHECKS) or not all(isinstance(v, str) and v.strip() for v in rationale.values()):
        raise ValueError('All seven fidelity dimensions need explicit rationale')
    u['fidelity_review'] = {'reviewer': reviewer, 'reviewer_kind': 'ai_host', 'independent': False,
        'status': 'usable_for_internal_creative_pilot', 'source_meaning_sha': meaning_sha(u),
        'unit_copy_sha': unit_copy_sha(u), 'checks': {k: {'status': 'pass', 'rationale': rationale[k]} for k in CHECKS}}
    return result


def semantic_guard(delivery, package, manifest, statuses):
    ae_contract(package, statuses, internal=True); resolve_claims(package)
    if delivery['package_sha'] != sha(package) or delivery['manifest_sha'] != sha(manifest):
        raise ValueError('Frozen input changed; reauthor delivery')
    if delivery['teaching_semantic_sha'] != teaching_sha(package): raise ValueError('Teaching semantic change')
    if delivery['delivery_copy_sha'] != copy_sha(delivery) or delivery['screen_copy_sha'] != screen_sha(delivery):
        raise ValueError('Copy fingerprint drift')
    if delivery['public_render_ready'] is not False: raise ValueError('V9 internal-only')
    claims = {c['claim_id']: c for c in package['claims']}; covered = set(); rows = []
    if len({u['unit_id'] for u in delivery['units']}) != len(delivery['units']): raise ValueError('Duplicate delivery unit')
    for u in delivery['units']:
        cs = [claims[c] for c in u['source_claim_refs']]; covered.update(u['source_claim_refs'])
        if u['sentence_bindings'] != sentence_bindings(u): raise ValueError('Sentence provenance drift')
        if u['source_meaning'] != [{'claim_id': c['claim_id'], 'text': c['text']} for c in cs]: raise ValueError('Meaning drift')
        if {(c['asset_id'], c['method_id']) for c in cs} != {(u['asset_id'], u['method_id'])}:
            raise ValueError('Cross-method claim laundering')
        for key in ('evidence_refs', 'action_artifact_refs', 'review_refs'):
            if u[key] != list({sha(r): r for c in cs for r in c[key]}.values()): raise ValueError('Citation coverage drift')
        b = next(b for b in package['source_items'] if b['asset_id'] == u['asset_id'])
        role = next(s['role'] for s in b['analysis']['method_chain'] if s['method_id'] == u['method_id'])
        if u['role'] != role: raise ValueError('Role expansion')
        for excerpt in u['visual_excerpts']:
            ref = excerpt['ref']
            if ref['asset_id'] != u['asset_id']: raise ValueError('Cross-asset displayed excerpt')
            original = pointer(b, ref['pointer'])
            if isinstance(original, dict) and original.get('type') == 'source_evidence': original = original['span']['quote']
            if not isinstance(original, str): raise ValueError('Display needs literal source text')
            if (not 0 <= excerpt['start'] < excerpt['end'] <= len(original) or
                excerpt['text'] != original[excerpt['start']:excerpt['end']]): raise ValueError('Displayed excerpt drift')
            if ref['pointer'].startswith('/source_snapshot/options/'):
                candidates = {cid for r in u['action_artifact_refs']
                    for g in pointer(b, r['pointer'])['output'].get('groups', []) for cid in g['candidates']}
                if ref['pointer'].rsplit('/', 1)[-1] not in candidates: raise ValueError('Unbound option display')
            elif ref not in u['evidence_refs']: raise ValueError('Unbound evidence display')
        text = u['spoken_copy'] + '\n' + u['on_screen_copy']
        if not u['spoken_copy'].strip() or any(t not in text for t in u['protected_terms']): raise ValueError('Protected term omitted')
        if claim_guard(text, u['evidence_refs'])['status'] != 'PASS': raise ValueError('Unsupported delivery claim lint')
        if any(t in text for t in SLANG): raise ValueError('Brand slang forbidden')
        # Finite expansion rules, not general entailment. Negative boundary wording stays legal.
        positives = re.sub(r'[^。！？\n]*(?:不等于|不能|不证明|不代表|不得)[^。！？\n]*', '', text)
        if re.search(r'答案(?:就是|是|选)[A-G]|一定(?:选|对|错)|永远|所有题|只要.+就|必然|一定能', positives):
            raise ValueError('Certainty/quantifier/answer expansion')
        if role in ('reducer', 'framework', 'helper', 'locator') and re.search(r'得出答案|确定答案|定案了', positives):
            raise ValueError('Auxiliary role upgraded to answer')
        review = u['fidelity_review'] or {}
        if (review.get('source_meaning_sha') != meaning_sha(u) or review.get('unit_copy_sha') != unit_copy_sha(u)
            or review.get('status') != 'usable_for_internal_creative_pilot' or review.get('independent') is not False
            or review.get('reviewer_kind') != 'ai_host' or not review.get('reviewer')
            or set(review.get('checks', {})) != set(CHECKS)
            or not all(v.get('status') == 'pass' and v.get('rationale') for v in review['checks'].values())):
            raise ValueError('Copy-bound internal fidelity review missing/stale')
        rows.append({'unit_id': u['unit_id'], 'claim_refs': u['source_claim_refs'], 'checks': list(CHECKS), 'status': 'PASS_internal_binding_and_lint'})
    required = {c for s in package['semantic_scenes'] for c in s['claim_refs']}
    if not required <= covered: raise ValueError('Claim/Stop coverage incomplete')
    return {'status': 'PASS_internal', 'scope': 'deterministic_binding_and_expansion_lint_plus_explicit_host_review_not_truth_certification',
            'independent_human_certified': False, 'rows': rows}


def human_voice_critic(delivery):
    text = '\n'.join(u['spoken_copy'] for u in delivery['units'])
    counts = {s: text.count(s) for s in CLICHES}; hits = sum(counts.values())
    clauses = max(1, len(re.findall(r'[，。？！；\n]', text)))
    warning = hits >= 3 and hits / clauses >= 0.12
    index = 'HIGH' if hits / clauses > 0.25 else ('MEDIUM' if warning else 'LOW')
    return {'status': 'AI_TONE_WARNING' if warning else 'PASS_finite_tone_lint', 'artificial_polish_index': index,
            'cliche_counts': {k: v for k, v in counts.items() if v}, 'clause_count': clauses,
            'naturalness': 'PENDING_human_readthrough', 'ai_tone': index, 'lecture_tone': 'agent_review_required',
            'overpolished': index, 'teaching_fidelity': 'see_copy_bound_fidelity_review',
            'dimensions': ['Naturalness', 'Brevity', 'Rhythm', 'Specificity', 'Human cadence',
                           'AI cliché density', 'Lecture tone', 'Sales tone', 'Pretentiousness', 'Teaching fidelity'],
            'issues': ['AI_TONE_WARNING'] if warning else [], 'human_taste_review': 'PENDING'}


def invalidation(previous, delivery, audio_timing_sha):
    current = {'teaching_semantic_sha': delivery['teaching_semantic_sha'],
               'delivery_copy_sha': delivery['delivery_copy_sha'], 'screen_copy_sha': delivery['screen_copy_sha'],
               'audio_timing_sha': audio_timing_sha}
    teaching = previous.get('teaching_semantic_sha') != current['teaching_semantic_sha']
    copy = any(previous.get(k) != current[k] for k in ('delivery_copy_sha', 'screen_copy_sha'))
    timing = previous.get('audio_timing_sha') != current['audio_timing_sha']
    return {'copy_lock': current, 'teaching_stale': teaching, 'editorial_stale': teaching or copy,
            'render_stale': teaching or copy or timing, 'editorial_review_sha': None if teaching or copy else previous.get('editorial_review_sha'),
            'public_render_ready': False}
