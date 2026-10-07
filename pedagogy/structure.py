"""Source-bound cognitive objects, not English parsing or motion choreography."""
from copy import deepcopy

from video_contracts import sha
from video_contracts.method_application import require_current_application

STATES = ('focus', 'preserve', 'background', 'defer', 'remove', 'unresolved', 'resolved', 'protected')
COLLECTIONS = ('reality_objects', 'focus_objects', 'preserved_objects', 'backgroundable_objects',
               'removable_objects', 'deferred_objects', 'output_objects', 'stop_objects')


def validate_structure(structure):
    """Finite state/binding lint only; no semantic or perceptual certification."""
    allowed = {'objects', *COLLECTIONS, 'relations', 'attention_transition', 'source_binding',
               'projection_kind', 'syntax_recognition_performed', 'semantic_truth_certification'}
    if set(structure) != allowed or structure['syntax_recognition_performed'] is not False \
            or structure['semantic_truth_certification'] is not False:
        raise ValueError('Cognitive structure must not contain choreography or new teaching assertions')
    objects = structure['objects']; by_id = {o['object_id']: o for o in objects}
    if not objects or len(by_id) != len(objects):
        raise ValueError('Unique cognitive object IDs required')
    keys = {'object_id', 'kind', 'source_work_id', 'source_refs', 'before_state', 'state', 'protected',
            'reversibility', 'restore_state', 'validity_scope'}
    for obj in objects:
        if (set(obj) != keys or obj['state'] not in STATES or obj['before_state'] not in STATES
                or not obj['source_refs'] or type(obj['protected']) is not bool
                or obj['reversibility'] not in ('reversible', 'irreversible', 'not_applicable')):
            raise ValueError('Invalid source-bound cognitive object state')
        if obj['protected'] and obj['state'] in ('remove', 'defer', 'background'):
            raise ValueError('Protected object cannot disappear or be deferred')
        if obj['state'] in ('defer', 'background') and (
                obj['reversibility'] != 'reversible' or obj['restore_state'] not in ('preserve', 'focus')):
            raise ValueError('Deferred/background object must have a reversible restoration')
        if obj['state'] == 'remove' and (obj['reversibility'] != 'irreversible'
                or obj['validity_scope'] != 'within_current_reviewed_state_reopen_on_upstream_change'):
            raise ValueError('Removal must be bounded to the currently reviewed state')
    for key in COLLECTIONS:
        ids = structure[key]
        if len(ids) != len(set(ids)) or not set(ids) <= set(by_id):
            raise ValueError('Dangling or duplicate cognitive structure membership')
    if set(structure['removable_objects']) != {o['object_id'] for o in objects if o['state'] == 'remove'}:
        raise ValueError('Only actually removed objects may be removable')
    if set(structure['deferred_objects']) != {o['object_id'] for o in objects if o['state'] == 'defer'}:
        raise ValueError('Deferred objects cannot be relabelled removable')
    if set(structure['backgroundable_objects']) != {o['object_id'] for o in objects if o['state'] == 'background'}:
        raise ValueError('Background state must be explicit and reversible')
    if any(by_id[o]['protected'] for o in structure['removable_objects']):
        raise ValueError('Protected objects cannot be removable')
    transition = structure['attention_transition']
    if set(transition) != {'from_scope', 'to_scope', 'reversibility', 'source_refs'} \
            or transition['reversibility'] != 'reversible' or not transition['source_refs']:
        raise ValueError('Attention transition must describe source scopes, never AE parameters')
    if not set(transition['from_scope'] + transition['to_scope']) <= set(by_id):
        raise ValueError('Attention transition has dangling source objects')
    for relation in structure['relations']:
        if (set(relation) != {'kind', 'from_objects', 'to_objects', 'source_refs'}
                or not relation['source_refs']
                or not set(relation['from_objects'] + relation['to_objects']) <= set(by_id)):
            raise ValueError('Cognitive relations must bind existing objects and source assertions')
    return structure


def project_structure(source, base, delta, structure_input=None):
    objects, collections, relations = [], {k: [] for k in COLLECTIONS}, []

    def add(kind, refs, state='preserve', *, protected=False, before=None, reversible=False, work_id=None):
        oid = 'object:' + sha([kind, work_id, refs])[:24]
        if any(o['object_id'] == oid for o in objects):
            return oid
        objects.append({'object_id': oid, 'kind': kind, 'source_work_id': work_id, 'source_refs': deepcopy(refs),
            'before_state': before or state, 'state': state, 'protected': protected,
            'reversibility': 'reversible' if reversible else 'irreversible' if state == 'remove' else 'not_applicable',
            'restore_state': 'preserve' if reversible else None,
            'validity_scope': 'within_current_reviewed_state_reopen_on_upstream_change' if state == 'remove'
                             else 'selected_question_and_actual_action'})
        if state == 'focus': collections['focus_objects'].append(oid)
        if state in ('preserve', 'protected', 'unresolved', 'focus', 'resolved'):
            collections['preserved_objects'].append(oid)
        if state == 'background': collections['backgroundable_objects'].append(oid)
        if state == 'remove': collections['removable_objects'].append(oid)
        if state == 'defer': collections['deferred_objects'].append(oid)
        return oid

    for key, ref in base['original_question_refs'].items():
        if key in ('stem', 'passage', 'options', 'given_word'):
            collections['reality_objects'].append(add('original_question_' + key, [ref], 'protected', protected=True))
    focus_refs = base.get('boundary_delivery', {}).get('focus_evidence_refs', base['evidence_refs'])
    evidence_objects = {}
    for ref in base['evidence_refs']:
        evidence_objects[ref['pointer']] = add('evidence', [ref], 'focus' if ref in focus_refs else 'preserve', protected=True)
    output_objects = []
    for path in source.action_paths:
        output = add('actual_output', [source.ref(path + '/output')], 'resolved', protected=True)
        output_objects.append(output); collections['output_objects'].append(output)
        evidence = [oid for p, oid in evidence_objects.items() if p.startswith(path + '/evidence/')]
        relations.append({'kind': 'action_evidence_supports_actual_output', 'from_objects': evidence,
                          'to_objects': [output], 'source_refs': [source.ref(path)]})
    for ref in [base['truth_guard']['method_stop_ref'], *base['truth_guard']['action_stop_refs']]:
        collections['stop_objects'].append(add('stop_obligation', [ref], 'protected', protected=True))
    support = base['payoff']['reviewed_support']
    for field, state in (('removed_work', 'remove'), ('deferred_work', 'defer'), ('still_required_work', 'unresolved')):
        for work in delta[field]:
            add('reviewed_work_unit', work['source_refs'], state,
                protected=state == 'unresolved', before='preserve', reversible=state == 'defer', work_id=work['work_id'])
    if source.transport == 'frozen_asset' and base['answer_scope']['upstream_closed'] is False:
        add('unclosed_question_state', [source.ref('/analysis/answer_verification')], 'unresolved', protected=True)
    if delta['status'] == 'SUPPORTED_REVIEWED_STRUCTURE' and support['record']['reduction']['unit'] == 'candidate':
        record = support['record']; reduction = record['reduction']
        excluded = set(reduction['before_ids']) - set(reduction['after_ids'])
        for candidate in reduction['before_ids']:
            path = source.question_path + '/options/' + candidate.replace('~', '~0').replace('/', '~1')
            removed = candidate in excluded
            refs = [source.ref(path)] + deepcopy(support['source_refs'])
            oid = add('candidate_eligibility', refs, 'remove' if removed else 'unresolved', before='unresolved')
            if removed:
                relations.append({'kind': 'reviewed_local_candidate_elimination',
                    'from_objects': output_objects, 'to_objects': [oid], 'source_refs': deepcopy(support['source_refs'])})
    structural_binding = None
    if structure_input is not None:
        if source.transport != 'frozen_asset':
            raise ValueError('Frozen span application requires a frozen asset parent')
        require_current_application(structure_input, source.bundle, source.status)
        application = structure_input['payload']
        action = application['actual_action']
        if (action['execution_id'] not in source.selection['action_ids']
                or any(r['pointer'] not in source.review_paths for r in application['review_refs'])):
            raise ValueError('Structural annotations must belong to this selected action and Review')
        annotation = application['annotation']; spans = annotation['spans']
        protected = set(annotation['protected_span_ids'])
        deferred = set(annotation['deferred_span_ids'])
        span_ids = {}
        for i, span in enumerate(spans):
            ref = {'asset_id': structure_input['application_id'], 'pointer': '/payload/annotation/spans/' + str(i),
                   'sha': sha(span)}
            # Labels come from the explicitly bound frozen annotation. No parser
            # turns words into a subject/predicate/modifier in this compiler.
            span_ids[span['span_id']] = add('reviewed_span_' + span['semantic_role'], [ref],
                'defer' if span['span_id'] in deferred else 'focus', protected=span['span_id'] in protected,
                before='preserve', reversible=span['span_id'] in deferred)
        for i, relation in enumerate(annotation['relations']):
            ref = {'asset_id': structure_input['application_id'], 'pointer': '/payload/annotation/relations/' + str(i),
                   'sha': sha(relation)}
            relations.append({'kind': 'explicit_frozen_span_relation',
                'from_objects': [span_ids[relation['from_span_id']]],
                'to_objects': [span_ids[s] for s in relation['to_span_ids']], 'source_refs': [ref]})
        structural_binding = {'application_id': structure_input['application_id'],
                              'semantic_binding_sha': structure_input['semantic_binding_sha']}
    focus = collections['focus_objects']
    result = {'objects': objects, **collections, 'relations': relations,
        'attention_transition': {'from_scope': deepcopy(collections['reality_objects']),
            'to_scope': deepcopy(focus), 'reversibility': 'reversible', 'source_refs': deepcopy(focus_refs)},
        'source_binding': structural_binding, 'projection_kind': 'frozen_object_state_projection',
        'syntax_recognition_performed': False, 'semantic_truth_certification': False}
    return validate_structure(result)
