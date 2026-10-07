"""Deterministic state, object and signature lint; not cinema or teaching review."""
from .registry import registry, signature_matches


def audit_choreography(value):
    physics, _, _ = registry()
    errors, risks = [], []
    states=value['states'];objects=value['object_catalog'];ops=value['operations']
    by_object={o['object_id']:o for o in objects};by_state={s['state_id']:s for s in states}
    by_op={o['operation_id']:o for o in ops};relations={r['relation_id']:r for r in value['relation_catalog']}
    if len(by_object)!=len(objects) or not objects:errors.append('UNIQUE_SOURCE_OBJECTS_REQUIRED')
    if len(by_state)!=len(states) or len(by_op)!=len(ops):errors.append('DUPLICATE_STATE_OR_OPERATION')
    if len(states)!=len(ops)+1 or len(value['state_transitions'])!=len(ops):errors.append('INCOMPLETE_STATE_CHAIN')
    for obj in objects:
        if not obj['source_refs']:errors.append('OBJECT_SOURCE_REQUIRED')
        if obj['protected'] and obj['state'] in ('background','defer','remove'):errors.append('PROTECTED_OBJECT_MUTATION')
        if obj['state']=='defer' and obj['reversibility']!='reversible':errors.append('DEFER_MUST_BE_REVERSIBLE')
    reality=value['attention_entry']['from_scope'] if value['source']['kind']!='synthetic_contract_test' else states[0]['reality_objects']
    catalog_unresolved={o['object_id'] for o in objects if o['state']=='unresolved'}
    protected={o['object_id'] for o in objects if o['protected']}
    for state in states:
        ids=set(state['present_objects']); dispositions=state['object_states'];c=state['consequence']
        if set(dispositions)!=set(by_object) or not ids<=set(by_object):errors.append('STATE_OBJECT_SET_CHANGED')
        if not state['reality_layer_present'] or not set(reality)<=ids:risks.append('DETACHED_INFOGRAPH_RISK')
        if not protected<=ids:errors.append('PROTECTED_OBJECT_DISAPPEARED')
        if any(dispositions.get(o) in ('background','defer','remove') for o in protected):errors.append('PROTECTED_OBJECT_MUTATION')
        if any(dispositions.get(o) in ('remove','resolved') for o in catalog_unresolved):errors.append('UNRESOLVED_OBJECT_RESOLVED')
        if not catalog_unresolved<=set(c['unresolved_objects']) or not catalog_unresolved<=ids:
            errors.append('UNRESOLVED_OBJECT_HIDDEN')
        for key in ('active_scope','foreground_objects','background_objects','active_candidate_objects','unresolved_objects','settle_allowed_objects'):
            if not set(c[key])<=set(by_object):errors.append('DANGLING_CONSEQUENCE_OBJECT')
        if any(not set(group)<=set(by_object) for group in c['structural_groups']):errors.append('DANGLING_STRUCTURE_GROUP')
        if set(c['background_objects'])&protected:errors.append('PROTECTED_OBJECT_BACKGROUNDED')
        if set(c['settle_allowed_objects'])&catalog_unresolved:errors.append('UNRESOLVED_CANNOT_SETTLE_AS_DECIDED')
        if c['active_candidate_count'] is not None and c['active_candidate_count']!=len(c['active_candidate_objects']):
            errors.append('CANDIDATE_COUNT_MISMATCH')
    fields={'attention_change':('active_scope','foreground_objects','memory_action_recalled'),
        'scope_change':('active_scope',),'relation_change':('relation_state',),
        'candidate_change':('active_candidate_objects','active_candidate_count'),
        'structure_change':('route_node_ids','structural_groups'),'stop_state':('stop_reached',)}
    genuine=0
    for i, transition in enumerate(value['state_transitions']):
        if (transition['from_state'] not in by_state or transition['to_state'] not in by_state
                or transition['operation_id'] not in by_op):
            errors.append('DANGLING_STATE_TRANSITION');continue
        before=by_state[transition['from_state']];after=by_state[transition['to_state']];op=by_op[transition['operation_id']]
        if i>=len(states)-1 or before['state_id']!=states[i]['state_id'] or after['state_id']!=states[i+1]['state_id']:
            errors.append('STATE_CHAIN_REORDERED')
        targets=set(op['target_objects'])
        if not targets or not targets<=set(by_object) or not set(op['preserved_objects'])<=set(by_object):
            errors.append('DANGLING_OPERATION_OBJECT')
        if op['verb'] not in physics['families'].get(op['family'],[]):errors.append('UNKNOWN_COGNITIVE_OPERATION')
        if op['temporal_character'] not in physics['temporal_characters']:errors.append('CONCRETE_TIMING_FORBIDDEN')
        if not op['source_refs'] or op['original_content_mutation_allowed']:errors.append('OPERATION_BINDING_OR_CONTENT_MUTATION')
        carried=set(before['present_objects'])&set(after['present_objects'])
        if not carried or not transition['carry_objects']:risks.append('PRESENTATION_RESET_RISK')
        if not set(transition['carry_objects'])<=carried:errors.append('BROKEN_LOGICAL_CARRY')
        changed={oid for oid in set(before['object_states'])&set(after['object_states'])
                 if before['object_states'][oid]!=after['object_states'][oid]}
        if not changed<=targets:errors.append('UNDECLARED_OBJECT_TRANSFORMATION')
        for oid in changed:
            obj=by_object[oid];new=after['object_states'][oid]
            if new=='remove' and (obj['state']!='remove' or not value['collapse']['supported']):errors.append('UNSUPPORTED_REMOVAL')
            if obj['state']=='defer' and new=='remove':errors.append('DEFERRED_IS_NOT_REMOVED')
            if before['object_states'][oid]=='defer' and new in ('preserve','focus') and op['verb']!='restore':
                errors.append('RESTORE_OPERATION_REQUIRED')
        if op['reversibility']=='irreversible':
            if (not changed or any(by_object[o]['state']!='remove' for o in changed)
                    or op['validity_scope']!='within_current_reviewed_state_reopen_on_upstream_change'):
                errors.append('UNSUPPORTED_IRREVERSIBLE_ACTION')
        if op['verb'] in ('detach','rewire','reverse','reconnect'):
            relation=relations.get(op['relation_id'])
            if not relation or not relation['rewire_supported'] or not targets&set(relation['target_objects']):
                errors.append('REWIRE_REQUIRES_EXISTING_RELATION')
        actual_changes=[]
        for kind,keys in fields.items():
            if any(before['consequence'][k]!=after['consequence'][k] for k in keys):actual_changes.append(kind)
        if changed:
            if any(by_object[o]['source_work_id'] is not None for o in changed):actual_changes.append('work_change')
            if any(by_object[o]['kind'].startswith('reviewed_span_') for o in changed):actual_changes.append('structure_change')
        # A phase tag alone cannot make an information-space transformation.
        if not actual_changes or set(actual_changes)=={'relation_change'}:
            risks.append('DECORATIVE_CHOREOGRAPHY');errors.append('DECORATIVE_CHOREOGRAPHY')
        else:genuine+=1
        if not set(op['cognitive_changes'])<=set(actual_changes):errors.append('DECLARED_CHANGE_NOT_REALIZED')
    lineage={o['object_id']:o for o in value['object_lineage']}
    if set(lineage)!=set(by_object):errors.append('OBJECT_LINEAGE_MISSING')
    for oid, row in lineage.items():
        if oid not in by_object:continue
        obj=by_object[oid]
        expected=[{'state_id':s['state_id'],'disposition':s['object_states'][oid],
            'content_sha':obj['source_content_sha']} for s in states if oid in s['present_objects']]
        if (row['states']!=expected or row['source_content_sha']!=obj['source_content_sha']
                or row['origin_object_id']!=obj['origin_object_id']):errors.append('OBJECT_LINEAGE_CONTENT_DRIFT')
    collapse=value['collapse'];payoff=value['payoff_event'];stop=value['stop']
    if (not collapse['supported'] and payoff is not None) or (collapse['supported'] and (
            collapse['transition'] is None or not collapse['before_ref'] or not collapse['after_ref']
            or not collapse['work_delta_ref'])):errors.append('FAKE_COLLAPSE_OR_PAYOFF')
    if payoff is not None and (not payoff['supported'] or payoff['payoff_scope']!=collapse['scope']
            or payoff['from_state']!=collapse['transition']['from_state']
            or payoff['to_state']!=collapse['transition']['to_state']):errors.append('PAYOFF_SCOPE_UPGRADE')
    if collapse['decision_completion'] and (value['resolution']['output_role']!='decider' or not value['final_answer_allowed']):
        errors.append('DECISION_COMPLETION_NOT_ALLOWED')
    if value['resolution']['may_output_final_answer']!=value['final_answer_allowed']:errors.append('ANSWER_PERMISSION_UPGRADE')
    if value['final_answer_allowed'] and value['resolution']['output_role']!='decider':errors.append('FINAL_ANSWER_LOCK_NOT_ALLOWED')
    if stop is None or stop['reached_state'] not in by_state or not by_state[stop['reached_state']]['consequence']['stop_reached']:
        errors.append('STOP_MISSING')
    elif (not catalog_unresolved<=set(stop['unresolved_objects']) or stop['scope']!=value['resolution']['scope']
            or not stop['boundary_coverage_ref'] or (not value['final_answer_allowed'] and not stop['prohibited_transition'])):
        errors.append('STOP_SCOPE_OR_UNRESOLVED_LOST')
    if value['memory_closure'] is not None:
        memory=value['memory_closure'];core=value['intervention']['transitions']
        if not core or memory['state_id'] not in by_state or states.index(by_state[memory['state_id']])<=max(
                states.index(by_state[t['to_state']]) for t in core):errors.append('METHOD_STAMP_BEFORE_CORE_ACTION')
    synthetic=value['source']['kind']=='synthetic_contract_test'
    distinctive=signature_matches(value['binding']['method_id'],ops) if not synthetic else None
    if not synthetic and (value['signature']['method_id']!=value['binding']['method_id'] or not distinctive):
        risks.append('SIGNATURE_DISTINCTIVENESS_FAIL')
    if genuine==0 or 'DECORATIVE_CHOREOGRAPHY' in risks or 'PRESENTATION_RESET_RISK' in risks:
        risks.append('PPT_MOTION_RISK')
    if value['human_taste_review']!='PENDING' or value['public_render_ready'] is not False:errors.append('AUTOMATIC_HUMAN_OR_PUBLIC_APPROVAL')
    audit={'object_lineage_preserved':'OBJECT_LINEAGE_CONTENT_DRIFT' not in errors and 'OBJECT_LINEAGE_MISSING' not in errors,
        'reversibility_preserved':not any(e in errors for e in ('UNSUPPORTED_IRREVERSIBLE_ACTION','DEFERRED_IS_NOT_REMOVED','DEFER_MUST_BE_REVERSIBLE')),
        'unresolved_preserved':not any(e in errors for e in ('UNRESOLVED_OBJECT_RESOLVED','UNRESOLVED_OBJECT_HIDDEN','STOP_SCOPE_OR_UNRESOLVED_LOST')),
        'scope_preserved':not any(e in errors for e in ('PAYOFF_SCOPE_UPGRADE','STOP_SCOPE_OR_UNRESOLVED_LOST','ANSWER_PERMISSION_UPGRADE')),
        'stop_preserved':'STOP_MISSING' not in errors and 'STOP_SCOPE_OR_UNRESOLVED_LOST' not in errors,
        'reality_layer_persistent':'DETACHED_INFOGRAPH_RISK' not in risks,
        'carry_preserved':'PRESENTATION_RESET_RISK' not in risks and 'BROKEN_LOGICAL_CARRY' not in errors,
        'genuine_state_transition_count':genuine, 'signature_distinctiveness':distinctive,
        'brand_principles':value['signature']['brand_principles'], 'deterministic_lint_only':True,
        'semantic_truth_certification':False,'actual_visual_review':'PENDING','human_taste_review':'PENDING'}
    return audit,sorted(set(risks)),sorted(set(errors))
