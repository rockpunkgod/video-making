"""Explicit synthetic Peel contract exercise. Never a new English method."""
from copy import deepcopy

from video_contracts import ROOT, _validator, sha, seal
from .registry import VERSION, registry
from .compiler import reference, finish


def compile_synthetic_peel(fixture,*,restore=True):
    path=ROOT/'creative/method-choreography/synthetic-peel-input.schema.json'
    try:_validator(str(path),path.stat().st_mtime_ns).validate(fixture)
    except Exception as error:raise ValueError('SYNTHETIC CONTRACT TEST input required') from error
    if type(restore) is not bool:raise ValueError('Explicit synthetic restore choice required')
    if len({o['object_id'] for o in fixture['objects']})!=len(fixture['objects']):raise ValueError('Unique synthetic object IDs required')
    physics,recipes,hashes=registry();fid=fixture['fixture_id']
    ref=lambda path:reference('synthetic',fid,fixture,path)
    core=[o['object_id'] for o in fixture['objects'] if o['role']=='core']
    modifiers=[o['object_id'] for o in fixture['objects'] if o['role']=='modifier']
    if not core or len(modifiers)!=2:raise ValueError('Synthetic Peel needs supplied core spans and two modifiers')
    catalog=[]
    for i,obj in enumerate(fixture['objects']):
        if obj['role']=='modifier' and obj['protected']:raise ValueError('Protected spans cannot be peeled')
        catalog.append({'object_id':obj['object_id'],'kind':'reviewed_span_'+obj['role'], 'source_work_id':None,
            'source_refs':[ref('/objects/'+str(i))], 'before_state':'preserve',
            'state':'defer' if obj['role']=='modifier' else 'protected', 'protected':obj['protected'],
            'reversibility':'reversible' if obj['role']=='modifier' else 'not_applicable',
            'restore_state':'preserve' if obj['role']=='modifier' else None,
            'validity_scope':'synthetic_contract_test_only','origin':'synthetic_contract_test',
            'origin_object_id':obj['object_id'],'source_content_sha':sha([obj])})
    ids=[o['object_id'] for o in catalog];protected=[o['object_id'] for o in catalog if o['protected']]
    initial={'state_id':'state-001','stage':'problem','object_states':{o:'preserve' for o in ids},
        'present_objects':deepcopy(ids),'reality_objects':deepcopy(ids),'reality_layer_present':True,
        'source_refs':[ref('/objects')], 'consequence':{'active_scope':deepcopy(ids),'foreground_objects':deepcopy(ids),
            'background_objects':[],'active_candidate_objects':[],'active_candidate_count':None,
            'relation_state':'not_applicable','route_node_ids':[],'structural_groups':[], 'unresolved_objects':[],
            'output_encountered':False,'stop_reached':False,'memory_action_recalled':False,
            're_layout_intent':'retain_source_space','settle_allowed_objects':[]}}
    states=[initial];ops=[];transitions=[]
    def step(verb,targets,dispositions,updates,changes,stage='intervention'):
        old=states[-1];new=deepcopy(old);new.update(state_id='state-'+str(len(states)+1).zfill(3),stage=stage)
        new['object_states'].update(dispositions);new['consequence'].update(updates)
        new['source_refs']=[ref('/objects')]
        op={'operation_id':'operation-'+str(len(ops)+1).zfill(3),'family':'navigation' if verb=='lock' else 'reduction',
            'verb':verb,'target_objects':deepcopy(targets),'preserved_objects':protected,
            'source_refs':[ref('/objects')],'relation_id':None,'reversibility':'not_applicable' if verb=='lock' else 'reversible',
            'validity_scope':'synthetic_contract_test_only','temporal_character':'held' if verb=='lock' else 'measured',
            'cognitive_changes':changes,'original_content_mutation_allowed':False}
        ops.append(op);states.append(new)
        transitions.append({'from_state':old['state_id'],'operation_id':op['operation_id'],'to_state':new['state_id'],
            'carry_objects':sorted(ids)})
        return transitions[-1]
    for i,oid in enumerate(modifiers):
        active=[o for o in ids if o not in modifiers[:i+1]]
        step('peel',[oid],{oid:'defer'},{'active_scope':active,'foreground_objects':active,
            'background_objects':modifiers[:i+1],'re_layout_intent':'suspend_supplied_modifier'},['attention_change','scope_change','structure_change'])
    tighten=step('tighten',core,{}, {'structural_groups':[core],'re_layout_intent':'supplied_core_tightens'},['structure_change'])
    if restore:
        step('restore',modifiers,{o:'preserve' for o in modifiers},{'active_scope':ids,'foreground_objects':ids,
            'background_objects':[],'structural_groups':[],'re_layout_intent':'restore_same_spans'},['attention_change','scope_change','structure_change'])
    stop_transition=step('lock',core,{}, {'stop_reached':True,'output_encountered':True},['stop_state'],'stop')
    result={'schema':'method-choreography/v1','schema_version':VERSION,'kind':'method_choreography',
        'binding':{'method_id':None,'method_version':None,'pedagogy_contract':None,'pedagogy_plan_sha':None,
            'student_contract':None,'student_experience_sha':None,'student_final_copy_sha':None,
            'copy_handoff_sha':None,'motion_handoff_sha':None,'method_application_sha':None,
            'parent_asset_id':fid,'parent_semantic_sha':sha(fixture),'analysis_sha':None,**hashes},
        'source':{'kind':'synthetic_contract_test','current_upstream_verified':False,'production_eligible':False,
            'new_teaching_text_created':False,'text_parsing_performed':False},'experience_kind':'action_demo',
        'signature':{'method_id':None,'signature_id':'synthetic_peel','motion_identity_version':VERSION,
            'brand_principles':physics['principles'],'brand_grammar_refs':recipes['brand_grammar_refs']},
        'problem_state':{'state_id':states[0]['state_id'],'learner_state_before':'synthetic_encounter','source_refs':[ref('/objects')]},
        'attention_entry':{'transition':transitions[0],'from_scope':ids,'to_scope':core,
            'focus_objects':core,'backgroundable_objects':modifiers,'source_refs':[ref('/objects')]},
        'intervention':{'transitions':transitions[:3],'primary_action_ref':ref('/scenario')},
        'object_catalog':catalog,'relation_catalog':[],'states':states,'operations':ops,'state_transitions':transitions,
        'object_lineage':[], 'collapse':{'supported':False,'reduction_type':['none'],'before_ref':None,'after_ref':None,
            'removed':[],'deferred':[],'still_required':[],'scope':None,'decision_completion':False,'transition':None,'work_delta_ref':ref('/scenario')},
        'resolution':{'state_id':stop_transition['to_state'],'output_role':'synthetic_contract_test',
            'current_output_ref':ref('/scenario'),'resolved_objects':[],'unresolved_objects':[],
            'allowed_claim_ref':None,'scope':'synthetic_contract_test_only','may_output_final_answer':False},
        'payoff_event':None, 'stop':{'reached_state':stop_transition['to_state'],'transition':stop_transition,
            'current_output_ref':ref('/scenario'),'scope':'synthetic_contract_test_only','unresolved_objects':[],
            'deferred_objects':[] if restore else modifiers,'prohibited_transition':[{'from_state':stop_transition['to_state'],
                'to':'final_answer','reason_ref':ref('/scenario')}], 'boundary_coverage_ref':ref('/objects'),'source_refs':[ref('/scenario')]},
        'memory_closure':None,'temporal_signature':[{'operation_id':o['operation_id'],'character':o['temporal_character']} for o in ops],
        'answer_permission_ref':ref('/scenario'),'final_answer_allowed':False,'human_taste_review':'PENDING',
        'semantic_truth_certification':False,'public_render_ready':False,
        'release_state':{'teaching':'HOLD','source_display':'HOLD','editorial':'HOLD'},
        'replay_request':{'diagnostic':True},'generated_at':'SYNTHETIC CONTRACT TEST'}
    finish(result,['SYNTHETIC_CONTRACT_TEST_ONLY'],[])
    return result


def validate_synthetic_peel(value,fixture,*,restore=True):
    from .validation import inspect_choreography
    inspect_choreography(value)
    if compile_synthetic_peel(fixture,restore=restore)!=value:raise ValueError('Synthetic spans or operations changed')
    return {'status':'PASS','consumption_allowed':False,'public_render_ready':False}
