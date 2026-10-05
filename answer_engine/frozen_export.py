"""Read-only projection of explicitly supplied ANSWER artifacts. Never solves."""
from copy import deepcopy
from pathlib import Path

from core.registry import validate_schema
from core.evidence import validate_graph
from video_contracts import VERSION, now, read, seal, sha, semantic_payload, presentation_payload, validate, verify_bundle, review_semantics
from video_contracts import declared_review_level

PHASES = ('blind', 'host_review', 'reveal', 'post_reveal')
ROLES = {'locator', 'interpreter', 'reducer', 'decider', 'verifier', 'framework'}


def load_request(path):
    """Only explicit files, resolved relative to the request; no directory scan."""
    path = Path(path)
    request = read(path)
    def resolve(value):
        if isinstance(value, dict) and set(value) == {'file', 'sha256'}:
            artifact = read(path.parent / value['file'])
            if sha(artifact) != value['sha256']:
                raise ValueError('Explicit input hash mismatch: ' + value['file'])
            return artifact
        if isinstance(value, list):
            return [resolve(x) for x in value]
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        return value
    return resolve(request)


def review_level(record):
    """Identity is an upstream assertion, never inferred from prose or quality."""
    return declared_review_level(record)


class FrozenAssetExporter:
    def export(self, request, generated_at=None):
        req = deepcopy(request)
        allowed = {'question', 'analysis', 'methods', 'reviews', 'withdrawals', 'source',
                   'evaluation_phase', 'current', 'provenance', 'history'}
        if set(req) - allowed:
            raise ValueError('Unknown export request fields')
        q, a = req['question'], req['analysis']
        validate_schema('question-input', q)
        validate_schema('question-analysis', a)
        validate_graph(a['evidence_graph'], q)
        if q['question_id'] != a['question_id'] or q['question_type'] != a['question_type']:
            raise ValueError('Question/analysis identity mismatch')
        phase = req['evaluation_phase']
        if phase not in PHASES:
            raise ValueError('Unknown evaluation phase')
        methods = req['methods']
        if len({m['method_id'] for m in methods}) != len(methods):
            raise ValueError('Duplicate method')
        by_method = {m['method_id']: m for m in methods}
        for m in methods:
            validate_schema('method-card', m)
        for step in a['method_chain']:
            mid = step['method_id']
            m = by_method[mid]
            if a['method_versions'][mid] != m['version']:
                raise ValueError('Method version does not match frozen analysis')
            if step['role'] not in {m['primary_role'], *m.get('secondary_roles', [])}:
                raise ValueError('Method role mismatch')
        # Reuse structural validation, with only supplied frozen methods, not Registry.
        from core.execution import validate_execution_trace
        from types import SimpleNamespace
        validate_execution_trace(a, SimpleNamespace(methods=by_method))
        qsha, asha = sha(q), sha(a)
        review_records = []
        for record in req.get('reviews', []):
            # Existing bounded-action review files embed the exact question and analysis.
            embedded = record.get('question') == q and record.get('analysis') == a
            explicit = record.get('input_sha256') == qsha and record.get('analysis_sha256') == asha
            if not (embedded or explicit):
                raise ValueError('Review must bind exact question AND frozen analysis')
            review_phase = record.get('evaluation_phase')
            if review_phase is None:
                stage = record.get('stage', record.get('review_timing', ''))
                review_phase = 'post_reveal' if stage.startswith('post_reveal') else stage
            if review_phase not in PHASES or PHASES.index(review_phase) > PHASES.index(phase):
                raise ValueError('Review crosses evaluation phase boundary')
            if record.get('question_id') != q['question_id']:
                raise ValueError('Review question mismatch')
            rsha = sha(review_semantics(record))
            rid = record.get('artifact_id', 'review:' + rsha)
            # Retain the actual credential; producer does not synthesize certification.
            review_records.append({'artifact_id': rid, 'sha': sha(record), 'semantic_sha': rsha, 'level': review_level(record),
                                   'phase': review_phase, 'record': record})
        if len({r['artifact_id'] for r in review_records}) != len(review_records):
            raise ValueError('Duplicate review id')
        if phase == 'blind' and (a['answer'] is not None or a['answer_verification']['closed']):
            raise ValueError('Blind export cannot expose an answer')
        withdrawals = []
        for record in req.get('withdrawals', []):
            finding = record.get('withdrawal', record)
            if finding.get('question_id') != q['question_id']:
                raise ValueError('Withdrawal question mismatch')
            if finding.get('input_sha256') != qsha or finding.get('analysis_sha256') != asha:
                raise ValueError('Withdrawal must target this exact historical snapshot')
            if phase != 'post_reveal':
                raise ValueError('Withdrawal crosses evaluation phase boundary')
            withdrawals.append({'artifact_id': 'withdrawal:' + sha(record), 'sha': sha(record), 'record': finding})
        lifecycle = self._lifecycle(q, a, review_records, withdrawals)
        incomplete = []
        if not review_records or all(r['level'] == 'unreviewed' for r in review_records):
            incomplete.append('No explicitly typed bound review')
        if not a['execution_trace']:
            incomplete.append('No actual action record')
        effective = 'WITHDRAWN' if withdrawals else 'INCOMPLETE' if incomplete else 'ACTIVE'
        current = req.get('current', {})
        reasons = [w['record']['reason'] for w in withdrawals] + incomplete
        if not withdrawals:
            if current.get('question_snapshot_sha', qsha) != qsha:
                effective = 'STALE'; reasons.append('Current question snapshot changed')
            if any(current.get('method_versions', {}).get(m['method_id'], m['version']) != m['version'] for m in methods):
                effective = 'SUPERSEDED'; reasons.append('Explicit current method version changed')
        levels = ['unreviewed', 'ai_reviewed', 'human_reviewed', 'human_certified']
        level = max((r['level'] for r in review_records), key=levels.index, default='unreviewed')
        historical = []
        for old in req.get('history', []):
            verify_bundle(old)
            if old['source_snapshot']['question_id'] != q['question_id']:
                raise ValueError('History belongs to another question')
            if PHASES.index(old['evaluation_phase']) > PHASES.index(phase):
                raise ValueError('Historical artifact crosses evaluation phase boundary')
            historical.append({'asset_id': old['asset_id'], 'content_sha': old['content_sha'],
                               'evaluation_phase': old['evaluation_phase'],
                               'reviews': old['reviews'], 'withdrawals': old['withdrawals'], 'lifecycle': old['lifecycle'],
                               'effective_status': old['state']['effective_status']})
        bundle = {
            'schema_version': VERSION, 'asset_id': 'answer:' + q['question_id'] + ':' + sha([qsha, asha, [(m['method_id'], m['version']) for m in methods]]),
            'generated_at': generated_at or now(), 'source_snapshot': q, 'source': req['source'],
            'analysis': a, 'methods': methods, 'reviews': review_records, 'withdrawals': withdrawals,
            'lifecycle': lifecycle, 'evaluation_phase': phase,
            'history': historical,
            'answer_visible_in_this_bundle': a['answer'] is not None,
            'semantic_review': {'level': level, 'independent_human_certified': level == 'human_certified',
                                'reviewer_type': 'ai_host' if level == 'ai_reviewed' else 'human' if level.startswith('human') else 'unknown'},
            'binding_fingerprint': {'question_snapshot_sha': qsha, 'analysis_sha': asha,
                'method_versions': {m['method_id']: m['version'] for m in methods},
                'evidence_graph_sha': sha(a['evidence_graph']), 'execution_trace_sha': sha(a['execution_trace']),
                'active_review_set_sha': sha([r for r in lifecycle['reviews'] if r['status'] == 'active']),
                'active_action_set_sha': sha([r for r in lifecycle['actions'] if r['status'] == 'active'])},
            'state': {'effective_status': effective, 'blocking_reasons': reasons,
                      'warnings': ['Projection is not independent semantic certification']},
            'provenance': req.get('provenance', {})}
        bundle['semantic_binding_sha'] = sha(semantic_payload(bundle))
        bundle['presentation_sha'] = sha(presentation_payload(bundle))
        bundle = seal(bundle)
        validate('frozen-asset-bundle', bundle)
        return bundle

    def _lifecycle(self, q, a, reviews, withdrawals):
        relations = q.get('relations', [])
        actions = a['execution_trace']
        action_ids = {x['execution_id'] for x in actions}
        invalid_actions, invalid_relations, causes = set(), set(), {}
        for w in withdrawals:
            f = w['record']
            ids = set(f.get('withdrawn_execution_ids', []))
            indices = set(f.get('withdrawn_relation_indexes', []))
            if not ids <= action_ids or any(type(i) is not int or i < 0 or i >= len(relations) for i in indices):
                raise ValueError('Unknown withdrawal target')
            if not ids and not indices:
                raise ValueError('Empty withdrawal')
            invalid_actions |= ids; invalid_relations |= indices
            for target in ids | {'relation:' + str(i) for i in indices}:
                causes[target] = {'why': f['reason'], 'which_parent': w['artifact_id'],
                                  'withdrawal_artifact_id': w['artifact_id'], 'withdrawal_sha': w['sha']}
        changed = True
        while changed:
            changed = False
            for x in actions:
                eid, output = x['execution_id'], x.get('output') or {}
                parents = x['input_artifact_ids'] + output.get('target_execution_ids', [])
                if output.get('kind') == 'candidate_decision':
                    parents += ['relation:' + str(output['relation_index'])]
                bad = next((p for p in parents if p in causes), None)
                if bad and eid not in invalid_actions:
                    invalid_actions.add(eid); causes[eid] = {**causes[bad], 'which_parent': bad}; changed = True
                if eid in invalid_actions and output.get('kind') == 'candidate_decision':
                    i = output['relation_index']
                    if i not in invalid_relations:
                        invalid_relations.add(i); causes['relation:' + str(i)] = {**causes[eid], 'which_parent': eid}; changed = True
        return {
            'reviews': [{'artifact_id': r['artifact_id'], 'status': 'withdrawn' if withdrawals else 'active',
                         'withdrawal_refs': [w['artifact_id'] for w in withdrawals]} for r in reviews],
            'actions': [{'artifact_id': x['execution_id'], 'status': 'blocked' if x['execution_id'] in invalid_actions else
                         'active' if x['state'] == 'produced' else 'blocked',
                         'parent_artifacts': x['input_artifact_ids'], 'cause': causes.get(x['execution_id'])} for x in actions],
            'decisions': [{'artifact_id': 'relation:' + str(i), 'status': 'withdrawn' if i in invalid_relations else
                           'active' if r.get('review_status') == 'reviewed' else 'blocked',
                           'cause': causes.get('relation:' + str(i))} for i, r in enumerate(relations)],
            'evidence': [{'artifact_id': n['id'], 'status': 'active'} for n in a['evidence_graph']['nodes'] if n['type'] == 'source_evidence']}

    def status(self, request, generated_at=None):
        b = self.export(request, generated_at)
        result = seal({'schema_version': VERSION, 'asset_id': b['asset_id'], 'generated_at': b['generated_at'],
            'semantic_binding_sha': b['semantic_binding_sha'], 'source_sha': sha(b['source']),
            'presentation_sha': b['presentation_sha'],
            'question': {'snapshot_sha': b['binding_fingerprint']['question_snapshot_sha'], 'status': b['state']['effective_status']},
            'method_versions': b['binding_fingerprint']['method_versions'], 'lifecycle': b['lifecycle'],
            'effective_status': b['state']['effective_status'], 'invalidation_reasons': b['state']['blocking_reasons']})
        validate('artifact-status-manifest', result)
        return result
