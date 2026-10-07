"""State choreography from frozen experience, never parsing, teaching or rendering."""
from copy import deepcopy

from video_contracts import pointer, sha, seal
from video_contracts.method_application import require_current_application
from student_pov import validate_experience
from .registry import VERSION, registry
from .audit import audit_choreography


def reference(origin, artifact_id, value, path):
    return {'origin': origin, 'artifact_id': artifact_id, 'pointer': path, 'sha': sha(pointer(value, path))}


def choreography_semantics(value):
    return {k:v for k,v in value.items() if k not in
            ('choreography_id', 'choreography_sha', 'generated_at', 'content_sha', 'envelope_sha')}


def _catalog(plan, bundle, application):
    structure = plan['cognitive_structure']
    catalog = []
    def convert(ref):
        if ref['asset_id'] == bundle['asset_id']:
            source, origin = bundle, 'frozen_asset'
        elif application is not None and ref['asset_id'] == application['application_id']:
            source, origin = application, 'method_application'
        else:
            raise ValueError('Object source requires its own current frozen artifact')
        value = pointer(source, ref['pointer'])
        if sha(value) != ref['sha']: raise ValueError('Carried object text/content changed')
        return {'origin':origin, 'artifact_id':ref['asset_id'], 'pointer':ref['pointer'], 'sha':ref['sha']}, value
    for obj in structure['objects']:
        pairs = [convert(ref) for ref in obj['source_refs']]
        catalog.append({**deepcopy(obj), 'origin':'pedagogy_cognitive_structure',
            'origin_object_id':obj['object_id'], 'source_refs':[p[0] for p in pairs],
            'source_content_sha':sha([p[1] for p in pairs])})
    span_map = {}
    if application is not None:
        annotation = application['payload']['annotation']
        for i, span in enumerate(annotation['spans']):
            path = '/payload/annotation/spans/' + str(i)
            ref = reference('method_application', application['application_id'], application, path)
            existing = next((o for o in catalog if ref in o['source_refs']), None)
            if existing:
                span_map[span['span_id']] = existing['object_id']; continue
            oid = 'application-span:' + sha([application['semantic_binding_sha'],span['span_id']])[:24]
            deferred = span['span_id'] in annotation['deferred_span_ids']
            catalog.append({'object_id':oid, 'kind':'reviewed_span_'+span['semantic_role'],
                'source_work_id':None, 'source_refs':[ref], 'before_state':'preserve',
                'state':'defer' if deferred else 'focus',
                'protected':span['span_id'] in annotation['protected_span_ids'],
                'reversibility':'reversible' if deferred else 'not_applicable',
                'restore_state':'preserve' if deferred else None,
                'validity_scope':'selected_question_and_actual_action',
                'origin':'frozen_method_application', 'origin_object_id':span['span_id'],
                'source_content_sha':sha([span])})
            span_map[span['span_id']] = oid
    return catalog, span_map


def _relations(plan, bundle, application, span_map, pref, output):
    relations = []
    for i, row in enumerate(plan['cognitive_structure']['relations']):
        relations.append({'relation_id':'relation:'+sha(row)[:24], 'kind':row['kind'],
            'target_objects':list(dict.fromkeys(row['from_objects']+row['to_objects'])),
            'source_refs':[pref('/cognitive_structure/relations/'+str(i))],
            'rewire_supported':row['kind']=='explicit_frozen_span_relation',
            'endpoint_mapping':'frozen_object_endpoints'})
    # A reviewed relation assertion is a valid coarse relation target. It does
    # not magically provide actor/action/object spans or new diagram endpoints.
    for wi, work in enumerate(plan['work_delta']['removed_work']):
        for ref in work['source_refs']:
            if ref['asset_id'] != bundle['asset_id'] or not ref['pointer'].startswith('/source_snapshot/relations/'):
                continue
            value = pointer(bundle, ref['pointer'])
            if (sha(value) != ref['sha'] or value.get('method_id') != plan['method_id']
                    or value.get('review_status') != 'reviewed'
                    or value.get('candidate') != output.get('candidate')
                    or value.get('effect') != output.get('effect')
                    or ref['pointer'] != '/source_snapshot/relations/'+str(output.get('relation_index'))):
                raise ValueError('Relation must be explicitly bound to this reviewed action/output')
            target = [o['object_id'] for o in plan['cognitive_structure']['objects']
                      if o['source_work_id'] == work['work_id']]
            relations.append({'relation_id':'relation:'+sha(ref)[:24],
                'kind':'frozen_reviewed_relationship_assertion', 'target_objects':target,
                'source_refs':[{'origin':'frozen_asset','artifact_id':ref['asset_id'],
                    'pointer':ref['pointer'],'sha':ref['sha']}, pref('/work_delta/removed_work/'+str(wi)),
                    pref('/primary_action/output_ref')],
                'rewire_supported':True, 'endpoint_mapping':'assertion_only_no_actor_span_geometry'})
    if application is not None:
        for i, row in enumerate(application['payload']['annotation']['relations']):
            relations.append({'relation_id':'relation:'+sha([application['application_id'],i,row])[:24],
                'kind':'explicit_frozen_span_relation',
                'target_objects':[span_map[row['from_span_id']]]+[span_map[s] for s in row['to_span_ids']],
                'source_refs':[reference('method_application',application['application_id'],application,
                    '/payload/annotation/relations/'+str(i))],
                'rewire_supported':True, 'endpoint_mapping':'frozen_object_endpoints'})
    return relations


def _candidate_map(plan):
    result = {}
    for obj in plan['cognitive_structure']['objects']:
        if obj['kind'] != 'candidate_eligibility': continue
        refs = [r for r in obj['source_refs'] if r['pointer'].startswith('/source_snapshot/options/')]
        if len(refs) != 1: raise ValueError('Candidate must bind one exact original option')
        label = refs[0]['pointer'].removeprefix('/source_snapshot/options/').replace('~1','/').replace('~0','~')
        if label in result: raise ValueError('Duplicate candidate identity')
        result[label] = obj['object_id']
    return result


def compile_choreography(experience, plan, copy_handoff, motion_handoff, bundle, status, *,
                         application=None, diagnostic=False):
    if type(diagnostic) is not bool: raise ValueError('Explicit diagnostic choice required')
    gate = validate_experience(experience,copy_handoff,motion_handoff,plan,bundle,status)
    if not gate['consumption_allowed'] and not diagnostic:
        raise ValueError('Current READY Experience required; HOLD only permits explicit diagnostic replay')
    if experience['compilation_status'] != 'PASS':
        raise ValueError('Failed Experience cannot acquire choreography')
    physics, recipes, registry_binding = registry()
    recipe = next((r for r in recipes['recipes'] if r['method_id'] == plan['method_id']), None)
    if recipe is None or recipe['runtime'] != 'bound_v04_replay':
        raise ValueError('Only R02/G01 bounded replay is implemented; other signatures remain specifications')
    if application is not None:
        require_current_application(application,bundle,status)
        payload = application['payload']
        if (payload['method']['method_id'] != plan['method_id']
                or payload['method']['version'] != plan['method_version']
                or payload['actual_action']['execution_id'] != plan['primary_action']['action_id']
                or any('/reviews/'+r['pointer'].split('/')[-1] not in
                    [v['pointer'] for v in plan['truth_guard']['review_refs']] for r in application['payload']['review_refs'])):
            raise ValueError('Frozen application belongs to another action, method, version or Review')
    pref = lambda path:reference('pedagogy',plan['plan_id'],plan,path)
    eref = lambda path:reference('student_experience',experience['experience_id'],experience,path)
    structure = plan['cognitive_structure']
    objects, span_map = _catalog(plan,bundle,application)
    by_id = {o['object_id']:o for o in objects}
    output_ref = plan['primary_action']['output_ref']
    if output_ref['asset_id'] != bundle['asset_id']: raise ValueError('Own actual output required')
    output = pointer(bundle,output_ref['pointer'])
    relations = _relations(plan,bundle,application,span_map,pref,output)
    unresolved = [o['object_id'] for o in objects if o['state']=='unresolved']
    protected = [o['object_id'] for o in objects if o['protected']]
    reality = deepcopy(structure['reality_objects'])
    focus = deepcopy(structure['focus_objects'])
    candidates = _candidate_map(plan)
    collapse_source = experience['collapse']
    supported = collapse_source['supported'] and collapse_source['learner_visible']
    frames = [collapse_source['before_state'],collapse_source['after_state']]
    before_candidates, after_candidates = [], []
    if 'candidate_reduction' in plan['cognitive_reduction']['types'] and supported:
        try: before_candidates,after_candidates = [[candidates[label] for label in frame['objects']] for frame in frames]
        except KeyError as error: raise ValueError('Collapse has no bound candidate object') from error
    binding = {'method_id':plan['method_id'], 'method_version':plan['method_version'],
        'pedagogy_contract':'0.4.0', 'pedagogy_plan_sha':plan['plan_sha'],
        'student_contract':'0.4.0', 'student_experience_sha':experience['experience_sha'],
        'student_final_copy_sha':experience['final_copy_sha'],
        'copy_handoff_sha':None if copy_handoff is None else copy_handoff['content_sha'],
        'motion_handoff_sha':None if motion_handoff is None else motion_handoff['content_sha'],
        'method_application_sha':None if application is None else application['semantic_binding_sha'],
        'parent_asset_id':bundle['asset_id'], 'parent_semantic_sha':bundle['semantic_binding_sha'],
        'analysis_sha':plan['source_analysis_sha'], **registry_binding}
    source = {'kind':'current_v04' if gate['consumption_allowed'] else 'diagnostic_current_v04_hold',
        'current_upstream_verified':True, 'production_eligible':gate['consumption_allowed'] and not diagnostic,
        'new_teaching_text_created':False, 'text_parsing_performed':False}
    consequence = {'active_scope':deepcopy(structure['attention_transition']['from_scope']),
        'foreground_objects':deepcopy(reality), 'background_objects':[],
        'active_candidate_objects':before_candidates,
        'active_candidate_count':len(before_candidates) if before_candidates else None,
        'relation_state':'uncompared', 'route_node_ids':[], 'structural_groups':[], 'unresolved_objects':deepcopy(unresolved),
        'output_encountered':False, 'stop_reached':False, 'memory_action_recalled':False,
        're_layout_intent':'retain_source_space', 'settle_allowed_objects':[]}
    state = {'state_id':'state-001', 'stage':'problem', 'object_states':{
        o['object_id']:o['before_state'] for o in objects}, 'present_objects':list(by_id),
        'reality_objects':deepcopy(reality), 'reality_layer_present':True,
        'consequence':consequence, 'source_refs':[eref('/reality_layer'),eref('/beats/0'),pref('/cognitive_structure')]}
    states, operations, transitions = [state], [], []
    def step(family,verb,targets,refs,*,stage,changes,updates=None,dispositions=None,
             relation_id=None,reversibility='reversible',temporal='measured'):
        nonlocal state
        oid='operation-'+str(len(operations)+1).zfill(3)
        next_state=deepcopy(state);next_state.update(state_id='state-'+str(len(states)+1).zfill(3),stage=stage,source_refs=deepcopy(refs))
        next_state['consequence'].update(deepcopy(updates or {}))
        next_state['object_states'].update(deepcopy(dispositions or {}))
        operations.append({'operation_id':oid,'family':family,'verb':verb,'target_objects':list(dict.fromkeys(targets)),
            'preserved_objects':deepcopy(protected), 'source_refs':deepcopy(refs), 'relation_id':relation_id,
            'reversibility':reversibility, 'validity_scope':'within_current_reviewed_state_reopen_on_upstream_change'
                if reversibility=='irreversible' else 'selected_question_and_actual_action',
            'temporal_character':temporal, 'cognitive_changes':deepcopy(changes),
            'original_content_mutation_allowed':False})
        transitions.append({'from_state':state['state_id'],'operation_id':oid,'to_state':next_state['state_id'],
            'carry_objects':list(set(state['present_objects'])&set(next_state['present_objects']))})
        transitions[-1]['carry_objects'].sort()
        states.append(next_state);state=next_state
        return transitions[-1]
    attention_transition = step('navigation','anchor',focus,[pref('/cognitive_structure/attention_transition'),eref('/focus')],
        stage='attention',changes=['attention_change','scope_change'],updates={
            'active_scope':deepcopy(structure['attention_transition']['to_scope']),
            'foreground_objects':deepcopy(focus),'background_objects':deepcopy(structure['backgroundable_objects']),
            're_layout_intent':'focus_existing_objects'},temporal='quick')
    core_transitions=[];gaps=[]
    if plan['method_id']=='R02':
        relation=next((r for r in relations if r['rewire_supported'] and r['kind']=='frozen_reviewed_relationship_assertion'),None)
        if relation is None: gaps.append('REWIRE_REVIEWED_RELATION_UNAVAILABLE')
        else:
            # Exact frozen evidence field metadata separates the two supplied
            # comparison objects. This is not word/actor parsing. The reviewed
            # assertion remains coarse when no endpoint spans were supplied.
            source_evidence=[];candidate_evidence=[]
            for oid in focus:
                fields=[pointer(bundle,r['pointer']).get('field') for r in by_id[oid]['source_refs']
                        if r['origin']=='frozen_asset' and isinstance(pointer(bundle,r['pointer']),dict)]
                (candidate_evidence if 'option:'+output['candidate'] in fields else source_evidence).append(oid)
            candidate_objects=candidate_evidence or [candidates[output['candidate']]]
            targets=focus+candidate_objects+relation['target_objects']
            refs=[pref('/primary_action'),*deepcopy(relation['source_refs'])]
            groups=[ [source_evidence], [source_evidence,candidate_objects],
                [source_evidence,candidate_objects,relation['target_objects']],
                [relation['target_objects'],source_evidence+candidate_objects] ]
            for (family,verb,phase,temporal), grouping in zip([
                ('comparison','align','source_established','measured'),
                ('comparison','overlay','candidate_overlaid','searching'),
                ('relationship','detach','mismatch_isolated','measured'),
                ('relationship','rewire','reviewed_relation_revealed','sudden')],groups):
                foreground=list(dict.fromkeys(oid for group in grouping for oid in group))
                core_transitions.append(step(family,verb,targets,refs,stage='intervention',
                    changes=['relation_change','structure_change'],
                    updates={'relation_state':phase,'structural_groups':deepcopy(grouping),
                        'foreground_objects':foreground,'re_layout_intent':'compare_existing_relation'},
                    relation_id=relation['relation_id'],temporal=temporal))
    else:
        slots=[span_map[s['span_id']] for s in application['payload']['annotation']['spans'] if s['semantic_role']=='slot'] if application else []
        if len(slots)!=1 or output.get('kind')!='route_selection' or not output.get('node_ids'):
            gaps.append('ROUTING_SLOT_OR_EXISTING_ROUTE_UNAVAILABLE')
        else:
            origin=slots[0]
            refs=[pref('/primary_action'),*deepcopy(by_id[origin]['source_refs'])]
            core_transitions.append(step('routing','extract',[origin]+[o['object_id'] for o in objects if o['state']=='defer'],refs,stage='intervention',
                changes=['attention_change','scope_change'],updates={'active_scope':[origin],
                    'foreground_objects':[origin],'relation_state':'functional_slot_extracted',
                    'background_objects':[o['object_id'] for o in objects if o['state']=='defer'],
                    're_layout_intent':'retain_extracted_origin'},
                dispositions={o['object_id']:'defer' for o in objects if o['state']=='defer'},temporal='measured'))
            core_transitions.append(step('routing','route',[origin]+structure['output_objects'],
                refs+[pref('/primary_action/output_ref')],stage='intervention',changes=['relation_change','structure_change'],
                updates={'route_node_ids':deepcopy(output['node_ids']),'relation_state':'existing_route_reached',
                    'output_encountered':True},temporal='searching'))
    collapse_transition=None
    if supported:
        dispositions={o['object_id']:o['state'] for o in objects if o['state'] in ('remove','defer')}
        if not dispositions: gaps.append('COLLAPSE_HAS_NO_BOUND_DISPOSITION')
        else:
            collapse_transition=step('comparison','reveal_difference',list(dispositions),
                [pref('/primary_simplification'),pref('/work_delta'),pref('/cognitive_reduction'),eref('/collapse')],
                stage='collapse',changes=['work_change']+(['candidate_change'] if before_candidates else ['structure_change']),
                updates={'active_candidate_objects':after_candidates,
                    'active_candidate_count':len(after_candidates) if before_candidates else None,
                    'output_encountered':True,'re_layout_intent':'supported_structure_reduction'},
                dispositions=dispositions,reversibility='irreversible' if any(o['state']=='remove' for o in objects) else 'reversible',
                temporal='settling')
    stop_refs=[eref('/stop'),pref('/boundary_presentations'),pref('/answer_scope'),pref('/stop_state')]
    is_route=plan['method_id']=='G01' and bool(core_transitions)
    stop_targets=(slots if is_route else [])+structure['stop_objects']+structure['output_objects']
    stop_transition=step('routing' if is_route else 'navigation','seal' if is_route else 'lock',stop_targets,stop_refs,
        stage='stop',changes=['stop_state'],updates={'stop_reached':True,'output_encountered':True,
            'settle_allowed_objects':deepcopy(structure['output_objects'])+deepcopy(structure['stop_objects']),
            're_layout_intent':'preserve_open_unresolved_and_close_current_action'},temporal='held',reversibility='not_applicable')
    memory=None
    if experience['memory_closure']['memory_phrase'] is not None and core_transitions:
        memory_transition=step('navigation','return',focus,[eref('/memory_closure'),pref('/primary_action')],
            stage='memory',changes=['attention_change'],updates={'memory_action_recalled':True,
                'active_scope':deepcopy(focus),'foreground_objects':deepcopy(focus),
                're_layout_intent':'recall_first_action_not_logo'},temporal='settling')
        memory={'state_id':memory_transition['to_state'], 'action_pattern':[
            {'family':o['family'],'verb':o['verb']} for o in operations if o['operation_id'] in [t['operation_id'] for t in core_transitions]],
            'first_action_ref':pref('/primary_action'), 'remembered_objects':deepcopy(focus),
            'memory_phrase_ref':eref('/memory_closure/memory_phrase'),
            'method_stamp_ref':eref('/memory_closure/method_name') if experience['memory_closure']['method_name'] else None,
            'name_after_core_action':True, 'student_retention_certified':False}
    collapse={'supported':bool(supported and collapse_transition),
        'reduction_type':deepcopy(plan['cognitive_reduction']['types']),
        'before_ref':eref('/collapse/before_state') if supported else None,
        'after_ref':eref('/collapse/after_state') if supported else None,
        'removed':deepcopy(experience['work_delta']['removed_work']),
        'deferred':deepcopy(experience['work_delta']['deferred_work']),
        'still_required':deepcopy(experience['work_delta']['still_required_work']),
        'scope':collapse_source['scope'], 'decision_completion':plan['cognitive_reduction']['decision_completion'],
        'transition':collapse_transition, 'work_delta_ref':pref('/work_delta')}
    resolution={'state_id':stop_transition['to_state'], 'output_role':plan['role'],
        'current_output_ref':pref('/primary_action/output_ref'),
        'resolved_objects':deepcopy(structure['output_objects']), 'unresolved_objects':deepcopy(unresolved),
        'allowed_claim_ref':pref('/payoff/allowed_claim') if supported else None,
        'scope':experience['stop']['scope'], 'may_output_final_answer':experience['answer_permission']['may_output_final_answer']}
    payoff={'supported':True,'from_state':collapse_transition['from_state'],'to_state':collapse_transition['to_state'],
        'payoff_scope':collapse_source['scope'],'allowed_claim_ref':pref('/payoff/allowed_claim'),
        'source_refs':[pref('/payoff'),eref('/collapse')]} if collapse['supported'] else None
    result={'schema':'method-choreography/v1','schema_version':VERSION,'kind':'method_choreography',
        'binding':binding,'source':source,'experience_kind':experience['experience_kind'],
        'signature':{'method_id':plan['method_id'],'signature_id':recipe['signature_id'],
            'motion_identity_version':VERSION,'brand_principles':deepcopy(physics['principles']),
            'brand_grammar_refs':deepcopy(recipes['brand_grammar_refs'])},
        'problem_state':{'state_id':states[0]['state_id'],'learner_state_before':experience['beats'][0]['learner_state_before'],
            'source_refs':[eref('/beats/0'),pref('/symptom')]},
        'attention_entry':{'transition':attention_transition,'from_scope':deepcopy(structure['attention_transition']['from_scope']),
            'to_scope':deepcopy(structure['attention_transition']['to_scope']),'focus_objects':focus,
            'backgroundable_objects':deepcopy(structure['backgroundable_objects']),
            'source_refs':[pref('/cognitive_structure/attention_transition'),eref('/focus')]},
        'intervention':{'transitions':core_transitions,'primary_action_ref':pref('/primary_action')},
        'object_catalog':objects,'relation_catalog':relations,'states':states,'operations':operations,
        'state_transitions':transitions,'object_lineage':[], 'collapse':collapse,'resolution':resolution,'payoff_event':payoff,
        'stop':{'reached_state':stop_transition['to_state'],'transition':stop_transition,
            'current_output_ref':eref('/stop/current_output'),'scope':experience['stop']['scope'],
            'unresolved_objects':unresolved,'deferred_objects':[o['object_id'] for o in objects if o['state']=='defer'],
            'prohibited_transition':[{'from_state':stop_transition['to_state'],'to':'final_answer',
                'reason_ref':eref('/answer_permission')}] if not experience['answer_permission']['may_output_final_answer'] else [],
            'boundary_coverage_ref':eref('/stop/boundary_presentations'), 'source_refs':stop_refs},
        'memory_closure':memory,'temporal_signature':[{'operation_id':o['operation_id'],'character':o['temporal_character']} for o in operations],
        'answer_permission_ref':eref('/answer_permission'), 'final_answer_allowed':experience['answer_permission']['may_output_final_answer'],
        'human_taste_review':'PENDING','semantic_truth_certification':False,'public_render_ready':False,
        'release_state':deepcopy(experience['release_state']), 'replay_request':{'diagnostic':diagnostic},
        'generated_at':experience['generated_at']}
    finish(result,gaps,experience['availability']['gaps'])
    return result


def finish(result, gaps, upstream_gaps):
    result['object_lineage']=[{'object_id':o['object_id'],'origin_object_id':o['origin_object_id'],
        'source_content_sha':o['source_content_sha'],'states':[{'state_id':s['state_id'],
            'disposition':s['object_states'][o['object_id']],'content_sha':o['source_content_sha']}
            for s in result['states'] if o['object_id'] in s['present_objects']]} for o in result['object_catalog']]
    audit, risks, errors=audit_choreography(result)
    result['audit']=audit;result['risks']=risks
    if not result['source']['production_eligible']:gaps=list(gaps)+['DIAGNOSTIC_ONLY_NOT_PRODUCTION_READY']
    result['compilation_status']='FAIL' if errors else 'PASS'
    result['availability']={'status':'FAIL' if errors else 'HOLD' if gaps or upstream_gaps or risks else 'READY',
        'gaps':sorted(set(gaps+list(upstream_gaps))), 'issues':errors}
    result['choreography_sha']=sha(choreography_semantics(result))
    result['choreography_id']='choreography:'+result['choreography_sha']
    result.update(seal(result))
