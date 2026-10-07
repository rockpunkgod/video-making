"""Frozen method application transport; no inference, Registry or solver imports.

Semantic span roles must cite an assertion in the existing reviewed action.
This is deterministic binding lint, not semantic truth certification.
"""
from copy import deepcopy

from . import ROOT, _validator, sha, seal, verify_seal, status_matches, review_semantics, REVIEW_LEVELS

VERSION = '0.1.0'
ROLES = ('context', 'predicate', 'determiner', 'slot', 'hint', 'temporal_clause',
         'core', 'modifier', 'condition', 'negation', 'scope', 'comparison')
ASSERTIONS = ('concrete_action', 'decision_rule_check', 'stop_rule_check')


def _schema(name, value):
    from jsonschema import ValidationError
    path = ROOT / 'schemas' / (name + '.json')
    try:
        _validator(str(path), path.stat().st_mtime_ns).validate(value)
    except ValidationError as error:
        raise ValueError('Invalid method application: ' + error.message) from error


def export_application(bundle, status, annotation, generated_at):
    """Project a selected actual action and explicitly bound semantic annotations.

    Does not create a Review. Assertions and review credentials are copied from
    the frozen upstream action. An annotation cannot substitute for that review.
    """
    _schema('method-application-input', annotation)
    if status is None or not status_matches(bundle, status):
        raise ValueError('Current ACTIVE frozen upstream status required')
    if bundle['source'].get('usage_status') not in ('internal_only', 'permitted'):
        raise ValueError('Source does not permit internal production')
    index = annotation['action_index']
    actions = bundle['analysis']['execution_trace']
    if not 0 <= index < len(actions):
        raise ValueError('Dangling actual action')
    action = actions[index]
    active = {a['artifact_id'] for a in bundle['lifecycle']['actions']
              if a['status'] == 'active'}
    if (action['execution_id'] not in active or action['state'] != 'produced'
            or action['review_status'] != 'reviewed' or action.get('stop_applied')):
        raise ValueError('Actual action is not active and usable')
    method = next(m for m in bundle['methods'] if m['method_id'] == action['method_id'])
    if (action['method_version'] != method['version']
            or action['role'] != method['primary_role']):
        raise ValueError('Method role/version binding changed')
    if not action.get('output') or not action.get('stop_rule_check'):
        raise ValueError('Actual output and Stop Rule required')
    # This lane deliberately freezes bounded auxiliary actions. A final answer
    # cannot be introduced by a layout annotation or inferred from a hint.
    if action['role'] not in ('framework', 'locator', 'interpreter'):
        raise ValueError('Method application pilot requires a bounded auxiliary action')
    if action['output']['kind'] == 'word_answer' or action.get('answer') is not None:
        raise ValueError('Bounded action cannot certify a final answer')
    review_refs = []
    for ri in annotation['review_indices']:
        if not 0 <= ri < len(bundle['reviews']):
            raise ValueError('Dangling upstream review')
        review = bundle['reviews'][ri]
        if review['level'] == 'unreviewed':
            raise ValueError('Explicit upstream review credential required')
        if not any(r['artifact_id'] == review['artifact_id'] and r['status'] == 'active'
                   for r in bundle['lifecycle']['reviews']):
            raise ValueError('Withdrawn review cannot support an application')
        review_refs.append({'pointer': '/reviews/' + str(ri),
                            'artifact_id': review['artifact_id'], 'sha': review['sha'],
                            'semantic_sha': review['semantic_sha'],
                            'level': review['level']})
    region = annotation['source_region']
    if region not in action['evidence']:
        raise ValueError('Reading region must be an exact existing action evidence span')
    field = region['field']
    source = bundle['source_snapshot'].get(field)
    if (not isinstance(source, str) or source[region['start']:region['end']] != region['quote']):
        raise ValueError('Frozen reading region mismatch')
    spans = annotation['spans']
    by_id = {s['span_id']: s for s in spans}
    if len(by_id) != len(spans):
        raise ValueError('Unique semantic span IDs required')
    cursor = region['start']
    for span in spans:
        if (span['field'] != field or span['start'] != cursor or span['end'] <= cursor
                or source[span['start']:span['end']] != span['quote']):
            raise ValueError('Spans must partition the exact original reading region in order')
        cursor = span['end']
        assertion = span['assertion']
        if assertion['quote'] not in action[assertion['field']]:
            raise ValueError('Semantic role lacks its own existing action assertion')
    if cursor != region['end']:
        raise ValueError('Semantic partition silently drops source content')
    reduced = annotation['reduced_span_ids']; deferred = annotation['deferred_span_ids']
    protected = annotation['protected_span_ids']
    if (len(set(reduced)) != len(reduced) or len(set(deferred)) != len(deferred)
            or set(reduced) & set(deferred) or set(reduced + deferred) != set(by_id)
            or not set(protected) <= set(reduced)):
        raise ValueError('Every span must remain in a protected or reversible state')
    if reduced != [s['span_id'] for s in spans if s['span_id'] in reduced]:
        raise ValueError('Reduced layout changes source reading order')
    if any(by_id[s]['semantic_role'] in ('condition', 'negation', 'scope', 'comparison')
           for s in deferred):
        raise ValueError('Decisive conditions and scope cannot be peeled away')
    for relation in annotation['relations']:
        if (relation['from_span_id'] not in by_id
                or not set(relation['to_span_ids']) <= set(by_id)
                or relation['assertion']['quote'] not in action[relation['assertion']['field']]):
            raise ValueError('Relation lacks an own-action semantic binding')
    payload = dict(question=deepcopy(bundle['source_snapshot']),
        method={k: deepcopy(method[k]) for k in ('method_id', 'version', 'primary_role',
                                               'brand_name', 'stop_rule') if k in method},
        actual_action=deepcopy(action), annotation=deepcopy(annotation), review_refs=review_refs)
    semantic = deepcopy(payload)
    for ref in semantic['review_refs']: ref.pop('sha')
    binding = sha(review_semantics(semantic))
    level = max((r['level'] for r in review_refs), key=REVIEW_LEVELS.index)
    result = seal(dict(schema_version=VERSION, kind='frozen_method_application',
        application_id='application:' + binding, semantic_binding_sha=binding,
        parent_asset_id=bundle['asset_id'], parent_semantic_sha=bundle['semantic_binding_sha'],
        source=deepcopy(bundle['source']), source_sha=sha(bundle['source']), payload=payload,
        semantic_review={'level':level,'independent_human_certified':level=='human_certified'},
        validation_kind='deterministic_binding_lint_not_semantic_truth_certification',
        generated_at=generated_at, public_render_ready=False))
    _schema('frozen-method-application', result)
    return result


def require_current_application(application, bundle, status):
    _schema('frozen-method-application', application)
    verify_seal(application)
    expected = export_application(bundle, status, application['payload']['annotation'],
                                  application['generated_at'])
    if application != expected:
        raise ValueError('Method application or upstream bindings changed')
