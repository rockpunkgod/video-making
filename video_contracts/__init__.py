"""Portable contracts shared by producers and consumers; no teaching imports."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
PHASES = ('blind', 'host_review', 'reveal', 'post_reveal')
REVIEW_LEVELS = ('unreviewed', 'ai_reviewed', 'human_reviewed', 'human_certified')


def declared_review_level(record):
    """Projection of the explicit credential, never a semantic judgement."""
    if not isinstance(record.get('reviewer'), str) or not record['reviewer'].strip():
        return 'unreviewed'
    kind = record.get('reviewer_kind')
    if kind in ('AI', 'ai_host', 'codex_ai_host_self_audit_not_independent_human'):
        return 'ai_reviewed'
    if kind == 'human' and record.get('independent_human_review') == 'pass':
        return 'human_certified' if record.get('independent_human_certified') is True else 'human_reviewed'
    return 'unreviewed'


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def validate(name, value):
    folder = ROOT / ('schemas' if name in ('frozen-asset-bundle', 'artifact-status-manifest') else 'video/schemas')
    path = folder / (name + '.json')
    _validator(str(path), path.stat().st_mtime_ns).validate(value)


@lru_cache(maxsize=16)
def _validator(path, modified):
    schema = read(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def seal(value):
    """Content excludes only transport metadata; envelope includes the timestamp."""
    value = deepcopy(value)
    value.pop('content_sha', None)
    value.pop('envelope_sha', None)
    value['content_sha'] = sha({k: v for k, v in value.items() if k not in ('generated_at', 'provenance')})
    value['envelope_sha'] = sha(value)
    return value


def verify_seal(value):
    if seal(value) != value:
        raise ValueError('Frozen envelope hash mismatch')


def pointer(value, ref):
    if not ref.startswith('/'):
        raise ValueError('Expected absolute JSON pointer')
    for part in ref[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def semantic_payload(bundle):
    # Explicit allowlist: metadata/paths/timestamps are not teaching inputs.
    method_keys = ('method_id', 'version', 'primary_role', 'secondary_roles', 'trigger_cues',
                   'core_action', 'decision_rule', 'verification', 'stop_rule', 'anti_rule',
                   'failure_cases', 'counterexamples', 'cannot_replace', 'full')
    return {**{k: bundle[k] for k in ('source_snapshot', 'analysis', 'withdrawals', 'lifecycle', 'evaluation_phase')},
            'methods': [{k: m[k] for k in method_keys if k in m} for m in bundle['methods']],
            'reviews': [{'artifact_id': r['artifact_id'], 'semantic_sha': r['semantic_sha'], 'level': r['level'],
                         'phase': r['phase']} for r in bundle['reviews']]}


def review_semantics(record):
    # This list is intentionally explicit; never guess that changed teaching text is a typo.
    diagnostic = {'generated_at', 'created_at', 'updated_at', 'provenance', 'diagnostic_path', 'debug'}
    if isinstance(record, dict):
        return {k: review_semantics(v) for k, v in record.items() if k not in diagnostic}
    if isinstance(record, list):
        return [review_semantics(v) for v in record]
    return record


def presentation_payload(bundle):
    keys = ('method_id', 'brand_name', 'common_wrong_instinct', 'student_symptoms', 'visual_formula', 'compact')
    return [{k: m[k] for k in keys if k in m} for m in bundle['methods']]


def verify_bundle(bundle):
    validate('frozen-asset-bundle', bundle)
    verify_seal(bundle)
    if sha(semantic_payload(bundle)) != bundle['semantic_binding_sha']:
        raise ValueError('Semantic binding mismatch')
    if sha(presentation_payload(bundle)) != bundle['presentation_sha']:
        raise ValueError('Presentation binding mismatch')
    q, a, fp = bundle['source_snapshot'], bundle['analysis'], bundle['binding_fingerprint']
    expected = {'question_snapshot_sha': sha(q), 'analysis_sha': sha(a),
                'method_versions': {m['method_id']: m['version'] for m in bundle['methods']},
                'evidence_graph_sha': sha(a['evidence_graph']), 'execution_trace_sha': sha(a['execution_trace']),
                'active_review_set_sha': sha([r for r in bundle['lifecycle']['reviews'] if r['status'] == 'active']),
                'active_action_set_sha': sha([r for r in bundle['lifecycle']['actions'] if r['status'] == 'active'])}
    if fp != expected:
        raise ValueError('Frozen fingerprint projection mismatch')
    for r in bundle['reviews']:
        record = r['record']
        exact = (record.get('question') == q and record.get('analysis') == a) or (
            record.get('input_sha256') == sha(q) and record.get('analysis_sha256') == sha(a))
        if (not exact or r['sha'] != sha(record) or r['semantic_sha'] != sha(review_semantics(record))
            or r['level'] != declared_review_level(record)):
            raise ValueError('Review credential projection mismatch')
        if PHASES.index(r['phase']) > PHASES.index(bundle['evaluation_phase']):
            raise ValueError('Review crosses evaluation phase boundary')
    level = max((r['level'] for r in bundle['reviews']), key=REVIEW_LEVELS.index, default='unreviewed')
    if (bundle['semantic_review']['level'] != level
        or bundle['semantic_review']['independent_human_certified'] != (level == 'human_certified')):
        raise ValueError('Semantic review summary does not match credentials')
    if bundle['answer_visible_in_this_bundle'] != (a['answer'] is not None):
        raise ValueError('Answer visibility projection mismatch')
    if bundle['evaluation_phase'] == 'blind' and (a['answer'] is not None or a['answer_verification']['closed']):
        raise ValueError('Blind bundle exposes an answer')
    for historical in bundle['history']:
        if PHASES.index(historical['evaluation_phase']) > PHASES.index(bundle['evaluation_phase']):
            raise ValueError('Historical artifact crosses evaluation phase boundary')


def status_matches(bundle, status):
    verify_bundle(bundle)
    validate('artifact-status-manifest', status)
    verify_seal(status)
    return (status['asset_id'] == bundle['asset_id']
            and status['semantic_binding_sha'] == bundle['semantic_binding_sha']
            and status['source_sha'] == sha(bundle['source'])
            and status['effective_status'] == 'ACTIVE')
