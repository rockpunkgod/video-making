"""Pure, explicitly reviewed locating transport. Never selects or classifies words."""
from copy import deepcopy
from . import ROOT, _validator, sha, seal, verify_seal, declared_review_level, pointer
from .passage import require_current

VERSION = '0.1.0'


def source_binding(bundle, question_id):
    if question_id not in {q['question_id'] for q in bundle['payload']['questions']}:
        raise ValueError('Unknown stable question identity')
    return {'asset_id': bundle['asset_id'], 'semantic_binding_sha': bundle['semantic_binding_sha'],
            'passage_sha': sha(bundle['payload']['passage']),
            'source_sha': sha(bundle['payload']['source']),
            'review_sha': sha(bundle['payload']['review']), 'question_id': question_id}


def material(packet):
    return {k: packet[k] for k in ('binding', 'strategy', 'target', 'candidates', 'acquisition')}


def validate_packet(packet, bundle, status):
    require_current(bundle, status)
    path = ROOT / 'schemas/reviewed-locating-trace.json'
    _validator(str(path), path.stat().st_mtime_ns).validate(packet)
    binding = packet['binding']; qid = binding['question_id']
    if binding != source_binding(bundle, qid):
        raise ValueError('Locating source/question/review binding changed')
    review = packet['review']
    if (review['material_sha'] != sha(material(packet)) or review['status'] != 'reviewed'
            or declared_review_level(review) == 'unreviewed'):
        raise ValueError('Explicit upstream reviewed credential required')
    q = next(q for q in bundle['payload']['questions'] if q['question_id'] == qid)

    def span(s):
        if s['field'] not in ('passage', 'stem'): raise ValueError('Unknown source field')
        text = bundle['payload']['passage'] if s['field'] == 'passage' else q['stem']
        if (type(s['start']) is not int or type(s['end']) is not int or
                not 0 <= s['start'] < s['end'] <= len(text) or text[s['start']:s['end']] != s['quote']):
            raise ValueError('Exact half-open source span required')

    assertions = {a['ref']: a for a in review['assertions']}
    if review['reviewer_kind'] != 'human' and (review.get('independent_human_certified', False)
                                             or review.get('independent_human_review') == 'pass'):
        raise ValueError('AI review cannot claim human certification')
    if len(assertions) != len(review['assertions']):
        raise ValueError('Duplicate review assertion identity')

    def reviewed(ref, subject, value):
        a = assertions.get(ref)
        if (a is None or a['subject'] != subject or a['subject_sha'] != sha(value)
                or a['question_id'] != qid or not a['rationale'].strip() or not a['evidence']):
            raise ValueError('Missing, cross-question or unbound review assertion')
        for e in a['evidence']: span(e)

    target = packet['target']
    for key in ('retained_information', 'search_expression'):
        span(target[key])
        if target[key]['field'] != 'stem': raise ValueError('Question target must be original stem')
    reviewed(target['review_ref'], 'target', {k: v for k, v in target.items() if k != 'review_ref'})
    ids = set(); previous_end = -1; acquired = []
    for order, c in enumerate(packet['candidates']):
        span(c)
        if (c['field'] != 'passage' or c['question_id'] != qid or c['candidate_id'] in ids
                or c['scan_order'] != order or c['start'] < previous_end):
            raise ValueError('Unique own-question candidates in original reading order required')
        ids.add(c['candidate_id']); previous_end = c['end']
        reviewed(c['review_ref'], c['candidate_id'], {k: v for k, v in c.items() if k != 'review_ref'})
        if c['recognition_state'] in ('inspected_continue', 'acquired') and not c['attention_eligibility']:
            raise ValueError('Classification alone cannot grant attention eligibility')
        if c['recognition_state'] == 'not_eligible' and c['attention_eligibility']:
            raise ValueError('Contradictory attention qualification')
        if c['recognition_state'] == 'acquired': acquired.append(c)
    a = packet['acquisition']
    if len(acquired) > 1 or bool(acquired) != (a is not None):
        raise ValueError('Exactly one explicit acquired candidate or unresolved trajectory')
    if a is not None:
        c = acquired[0]
        if a['candidate_id'] != c['candidate_id'] or c != packet['candidates'][-1]:
            raise ValueError('Acquisition must end supplied search route')
        span(a['sentence']); span(a['evidence'])
        if (a['sentence']['field'] != 'passage' or a['evidence']['field'] != 'passage'
                or not a['sentence']['start'] <= a['evidence']['start'] <= c['start'] < c['end'] <= a['evidence']['end'] <= a['sentence']['end']
                or a['allowed_conclusion'] != 'locate_for_further_inspection'
                or pointer(bundle, a['source_evidence_ref']) != a['evidence']):
            raise ValueError('Acquisition cannot create evidence or answer authority')
        parts = a['source_evidence_ref'].split('/')
        if (len(parts) != 7 or parts[1:4] != ['payload', 'review', 'segments']
                or parts[5] != 'evidence' or not parts[4].isdigit() or not parts[6].isdigit()
                or pointer(bundle, '/'.join(parts[:5]))['question_id'] != qid):
            raise ValueError('Acquisition evidence must belong to this question review')
        reviewed(a['review_ref'], 'acquisition', {k: v for k, v in a.items() if k != 'review_ref'})
    return packet


def freeze(packet, bundle, status, generated_at):
    validate_packet(packet, bundle, status)
    payload = deepcopy(packet); digest = sha(payload)
    return seal({'kind': 'reviewed_locating_trace', 'schema_version': VERSION,
                 'artifact_id': 'locating-trace:' + digest, 'semantic_binding_sha': digest,
                 'payload': payload, 'generated_at': generated_at,
                 'semantic_review': {'level': declared_review_level(packet['review']),
                                     'independent_human_certified': False},
                 'public_render_ready': False})


def trace_status(trace, generated_at, effective_status='ACTIVE'):
    verify_seal(trace)
    if effective_status not in ('ACTIVE', 'WITHDRAWN', 'SUPERSEDED', 'STALE', 'BLOCKED'):
        raise ValueError('Unknown upstream state')
    return seal({'kind': 'locating_trace_status', 'artifact_id': trace['artifact_id'],
                 'semantic_binding_sha': trace['semantic_binding_sha'],
                 'review_sha': sha(trace['payload']['review']),
                 'effective_status': effective_status, 'generated_at': generated_at})


def require_trace(trace, trace_manifest, bundle, status):
    verify_seal(trace)
    validate_packet(trace['payload'], bundle, status)
    expected = freeze(trace['payload'], bundle, status, trace['generated_at'])
    if trace != expected: raise ValueError('Trace fingerprint or review projection changed')
    if trace_manifest is None: raise ValueError('Current locating review status required')
    verify_seal(trace_manifest)
    if trace_manifest != trace_status(trace, trace_manifest['generated_at']):
        raise ValueError('Locating review withdrawn, superseded or stale')
    return trace['payload']
