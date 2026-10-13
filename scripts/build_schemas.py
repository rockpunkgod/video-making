"""Build the checked-in Draft 2020-12 contracts (not a custom schema dialect)."""
from pathlib import Path
import json
from core.composer import ROLE_ARTIFACTS

ROOT = Path(__file__).resolve().parents[1]
STR = {'type':'string', 'minLength':1}
BOOL = {'type':'boolean'}
NUMBER = {'type':'number', 'minimum':0}
NULLSTR = {'type':['string','null']}
ROLES = ['locator','interpreter','reducer','decider','verifier','framework']
OUTPUTS = ['locate','interpret','reduce','decide','verify']
TYPES = ['阅读理解','七选五','完形填空','语法填空','应用文','读后续写']
def enum(values): return {'enum':values}
def array(item, minimum=0): return {'type':'array','items':item,'minItems':minimum}
def obj(props, required=None, extra=False):
    return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':extra}
def write(name, schema):
    schema = {'$schema':'https://json-schema.org/draft/2020-12/schema', '$id':f'https://answer.local/schemas/{name}.json', **schema}
    p = ROOT/'schemas'/f'{name}.json'
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build():
    from core.release import CHECKS
    release_hash={'type':['string','null'],'pattern':'^[0-9a-f]{64}$'}
    write('method-release',obj({'schema_version':enum(['1.0.0']),'method_id':STR,'method_version':STR,'target_maturity':enum(['draft','candidate','validated','stable','deprecated']),'target_practical_value':enum(['Useful','Efficient','Signature']),'approved':BOOL,'reviewer':NULLSTR,'reviewed_at':NULLSTR,'checks':obj({key:BOOL for key in CHECKS}),'evidence_refs':array(STR),'notes':STR,'inputs':obj({key:STR for key in ['records','plan','regression']}),'bindings':obj({key:release_hash for key in ['method_sha256','cases_sha256','records_sha256','plan_sha256','regression_sha256']}),'validated_review':NULLSTR}))
    source = obj({'repository':STR,'commit':{'type':'string','pattern':'^[0-9a-f]{40}$'},'path':STR,'heading':STR})
    steps = obj({key:STR for key in ['start','first_cut','judge','stop']})
    compact = obj({key:STR for key in ['10s','30s','90s']},extra=True)
    method = {key:STR for key in ['method_id','brand_name','source_name','core_action','decision_rule','verification','stop_rule','common_wrong_instinct','transfer_pattern','memory_line','anti_rule','visual_formula','challenge_prompt','change_reason','regression_result']}
    method.update({key:array(STR) for key in ['aliases','secondary_roles','student_symptoms','trigger_cues','failure_cases','counterexamples','can_follow','usually_before','usually_after','conflicts_with','cannot_replace','affected_cases','section_ids']})
    method.update(question_type=enum(TYPES),method_type=enum(['framework','method','sub_action','internal_rule','category','verification_rule']),primary_role=enum(ROLES),role=enum(ROLES),output_type=enum(OUTPUTS),version={'type':'string','pattern':r'^\d+\.\d+\.\d+$'},maturity_status=enum(['draft','candidate','validated','stable','deprecated']),status=enum(['draft','candidate','validated','stable','deprecated']),practical_value=enum(['Useful','Efficient','Signature']),usefulness_level=enum(['Useful','Efficient','Signature']),compact=compact,four_step_card=steps,source_references=array(source,1),full={'type':'object'},levels={'type':'object'},cases={'type':'object','minProperties':1,'additionalProperties':STR},practicality_gate={'type':'object'},first_use_test={'type':'object'},evaluation={'type':'object'})
    method_contract=obj(method,extra=True)
    method_contract['properties'].update(student_ready=BOOL,entry_copy=STR,static_design_review=obj({'status':enum(['source_bound_editorial_review','source_rebound_semantic_reacceptance_pending']),'source_section_ids':array(STR,1),'participant_validation':enum(['pending_real_participant_validation']),'example_scope':STR}))
    # Optional display metadata; existing and historical teaching cards need no migration.
    method_contract['properties'].update(tier=enum(['move','sub_action','knowledge']),
        move_card=obj({key:STR for key in ['trigger','action_3s','trap_name','counterexample','mantra']}))
    method_contract['allOf']=[{'if':{'properties':{'student_ready':{'const':True}},'required':['student_ready']},'then':{'required':['entry_copy']}}]
    write('method-card',method_contract)
    write('case',obj({'case_id':STR,'method_id':STR,'question_type':enum(TYPES),'source':{'type':['object','string']},'question':NULLSTR,'answer':NULLSTR,'trigger':STR,'evidence':array({'type':'object'}),'method_role':enum(ROLES),'expected_action':STR,'expected_output':enum(OUTPUTS),'stop_rule':STR,'case_type':enum(['canonical','counterexample','boundary','transfer','hard']),'status':enum(['verified_course_example','source_pattern_only','evidence_gap']),'notes':STR},extra=True))
    span = obj({'field':STR,'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},'quote':STR})
    relation = obj({'method_id':STR,'candidate':STR,'effect':enum(['retain','eliminate','undetermined']),'claim':STR,'evidence':array(span,1),'decision_rule_check':STR,'stop_rule_check':STR,'verification':STR,'reviewer':STR,'review_status':enum(['reviewed','unreviewed'])})
    relation['properties']['execution_role'] = enum(ROLES)
    grounded_text=obj({'name':STR,'value':STR,'evidence':array(span,1)})
    artifacts=[
        obj({'kind':enum(['located_evidence']),'spans':array(span,1)}),
        obj({'kind':enum(['interpretation']),'parts':array(grounded_text,1)}),
        obj({'kind':enum(['candidate_partition']),'axis':STR,'groups':array(obj({'label':STR,'candidates':array(STR,1)}),1)}),
        obj({'kind':enum(['text_groups']),'groups':array(obj({'label':STR,'spans':array(span,1)}),1)}),
        obj({'kind':enum(['route_selection']),'node_ids':array(STR,1)}),
        obj({'kind':enum(['framework_card']),'fields':array(grounded_text,1)}),
        obj({'kind':enum(['candidate_decision']),'candidate':STR,'effect':enum(['retain','eliminate','undetermined']),'relation_index':{'type':'integer','minimum':0}}),
        obj({'kind':enum(['verification_result']),'candidate':STR,'target_execution_ids':array(STR,1),'verdict':enum(['supports','rejects','unresolved'])}),
    ]
    artifact={'oneOf':artifacts}
    write('action-artifact',artifact)
    execution=obj({'execution_id':STR,'method_id':STR,'method_version':{'type':'string','pattern':r'^\d+\.\d+\.\d+$'},'role':enum(ROLES),'input_artifact_ids':array(STR),'concrete_action':STR,'evidence':array(span,1),'decision_rule_check':STR,'stop_rule_check':STR,'stop_applied':BOOL,'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'output':{'anyOf':[{'type':'null'},artifact]}})
    write('method-execution',execution)
    lesson_segment=obj({'segment_id':STR,'function':enum(['action','evidence','comparison','stop']),'method_id':STR,'text':STR,'evidence':array(span,1),'relation_indices':array({'type':'integer','minimum':0})})
    lesson_review=obj({'schema_version':enum(['1.0.0']),'question_type':enum(TYPES[:4]),'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'source_section_ids':array(STR,1),'segments':array(lesson_segment,1)})
    write('lesson-review',lesson_review)
    writing_section=obj({'key':enum(['overall','diagnostics','anchors','emotion','outline','revised_text','practice','materials']),'text':STR,'evidence':array(span,1)})
    correction=obj({'original':span,'replacement':STR,'reason':STR,'kind':enum(['error','optional'])})
    proposed_score=obj({'scale':enum([15,25]),'lower':{'type':'integer','minimum':0,'maximum':25},'upper':{'type':'integer','minimum':0,'maximum':25},'band':STR,'rationale':STR,'evidence':array(span,1),'source_section_id':STR,'handwriting_applied':BOOL,'original_handwriting_reference':NULLSTR})
    proposed_score['properties']['word_count_adjustment']=obj({'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'source_section_id':STR,'source_quote':STR,'word_count':{'type':'integer','minimum':0},'deduction_points':{'type':'integer','minimum':1,'maximum':25},'score_before':obj({'lower':{'type':'integer','minimum':0,'maximum':25},'upper':{'type':'integer','minimum':0,'maximum':25}}),'evidence':array(span,1),'rationale':STR})
    image_ref=obj({'image_id':STR,'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'box':{'type':'array','items':{'type':'integer','minimum':0},'minItems':4,'maxItems':4}})
    image_region=obj({**image_ref['properties'],'observed':STR,'communication_impact':STR})
    handwriting=obj({'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'original_handwriting':BOOL,'clear_image':BOOL,'affects_communication':{'type':['boolean','null']},'rationale':STR,'source_section_id':STR,'regions':array(image_region,1),'adjustment_kind':enum(['none','lower_one_band','discretionary_deduction']),'band_before':NULLSTR,'deduction_points':{'type':['integer','null'],'minimum':1,'maximum':25},'score_before':{'anyOf':[{'type':'null'},obj({'lower':{'type':'integer','minimum':0,'maximum':25},'upper':{'type':'integer','minimum':0,'maximum':25}})]}})
    writing_review=obj({'schema_version':enum(['1.0.0']),'question_type':enum(['应用文','读后续写']),'kind':enum(['guidance','correction']),'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'source_section_ids':array(STR,1),'student_text_complete':BOOL,'student_text_excludes_given_starters':BOOL,'sections':array(writing_section),'corrections':array(correction),'reviewed_student_spans':array(span),'proposed_score':{'anyOf':[{'type':'null'},proposed_score]}})
    writing_review['properties']['schema_version']=enum(['1.0.0','1.1.0','1.2.0'])
    handwriting['properties']['student_text_sha256']={'type':'string','pattern':'^[0-9a-f]{64}$'}
    handwriting['required'].append('student_text_sha256')
    writing_review['properties']['handwriting_review']={'anyOf':[{'type':'null'},handwriting]}
    write('writing-review',writing_review)
    write('question-input',obj({'question_id':STR,'question_type':enum(TYPES+['未知']),'task_type':STR,'passage':{'type':'string'},'stem':{'type':'string'},'options':{'type':'object','additionalProperties':STR},'student_symptoms':array(STR),'observations':array(obj({'method_id':STR,'evidence':array(span,1),'reviewed':BOOL})),'relations':array(relation),'given_word':{'type':['string','null']},'student_text':{'type':'string'},'continuation_starters':array(STR),'requested_chain':array(STR),'difficulty':enum(['easy','medium','hard','unknown']),'writing_review':writing_review,'action_executions':array(execution),'lesson_review':lesson_review},required=['question_id','question_type','stem'],extra=False))
    question_schema=json.loads((ROOT/'schemas/question-input.json').read_text(encoding='utf-8'))
    question_schema['properties']['original_images']=array(obj({'image_id':STR,'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'mime_type':enum(['image/png','image/jpeg']),'data_base64':{'type':'string','minLength':1,'maxLength':13981016}}))
    write('question-input',question_schema)
    artifact_kinds=sorted({kind for kinds in ROLE_ARTIFACTS.values() for kind in kinds})
    node = obj({'id':STR,'type':enum(['question_signal','source_evidence','candidate_claim','relation','method_action','decision','verification','action_artifact']),'label':STR,'span':span,'method_id':STR,'candidate':STR,'reviewed':BOOL,'execution_id':STR,'artifact_kind':enum(artifact_kinds),'artifact_fingerprint':{'type':'string','pattern':'^[0-9a-f]{64}$'}},required=['id','type','label'],extra=False)
    node['properties']['type']['enum'].append('image_evidence')
    node['properties']['image_ref']=image_ref
    edge = obj({'from':STR,'to':STR,'type':enum(['supports','contradicts','locates','expands','narrows','eliminates','verifies'])})
    graph = obj({'nodes':array(node),'edges':array(edge)})
    write('evidence-graph',graph)
    match = obj({'method_id':STR,'role':enum(ROLES),'confidence':enum(['low','medium','high']),'reason':STR,'trigger_verified':BOOL})
    chain = obj({'method_id':STR,'role':enum(ROLES),'input':STR,'output':enum(OUTPUTS),'action':STR,'stop_rule':STR,'state':enum(['planned','reviewed','executed','stopped']),'input_artifact_types':array(enum(artifact_kinds)),'output_artifact_types':array(enum(artifact_kinds),1),'execution_ids':array(STR)})
    demo = obj({key:NUMBER for key in ['method_clarity','contrast','visuality','transferability','trigger_clarity','evidence_visibility','compression','score']})
    analysis = obj({'schema_version':STR,'question_id':STR,'question_type':STR,'task_type':STR,'method_matches':array(match),'method_chain':array(chain),'trigger_evidence':array(span),'evidence_graph':graph,'candidate_analysis':array(obj({'candidate':STR,'effect':enum(['retain','eliminate','undetermined']),'claim':STR,'method_id':STR,'reviewer':STR,'evidence_ids':array(STR)})),'answer':NULLSTR,'answer_confidence':enum(['low','medium','high']),'student_symptoms':array(STR),'demonstration':demo,'status':enum(['needs_evidence','reviewed','unsupported_type','incomplete_input']),'limitations':array(STR),'next_action':STR,'stop_rule':STR,'review_scope':STR,'method_versions':{'type':'object','additionalProperties':STR},'content_eligible':BOOL,'difficulty':enum(['easy','medium','hard','unknown'])})
    analysis['properties']['answer_verification'] = obj({'retained_candidates':array(STR),'eliminated_candidates':array(STR),'unresolved_candidates':array(STR),'candidate_coverage_complete':BOOL,'unique_supported_candidate':BOOL,'closed':BOOL})
    analysis['required'].append('answer_verification')
    navigation=obj({'hint_branch':enum(['unknown','with_hint','without_hint']),'status':enum(['needs_hint_confirmation','needs_function_confirmation','navigation_planned']),'paths':array(array(STR,1)),'next_node':STR,'review_basis':enum(['reviewed_trigger_routing_only']),'limitations':array(STR,1)})
    analysis['properties']['grammar_navigation']={'anyOf':[{'type':'null'},navigation]}
    analysis['required'].append('grammar_navigation')
    feedback=obj({'review':writing_review,'scope':enum(['guidance','full_correction','partial_feedback','unreviewed']),'score_status':enum(['external_proposal_not_certified','withheld','not_requested']),'source_document':STR,'section_order':array(STR,1),'evidence_ids':array(STR),'limitations':array(STR,1)})
    feedback['properties'].update(image_manifest=array(obj({'image_id':STR,'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'mime_type':enum(['image/png','image/jpeg']),'width':{'type':'integer','minimum':1},'height':{'type':'integer','minimum':1}})),image_evidence_ids=array(STR),student_text_sha256={'type':'string','pattern':'^[0-9a-f]{64}$'})
    feedback['required']=list(feedback['properties'])
    analysis['properties']['writing_feedback']={'anyOf':[{'type':'null'},feedback]}
    analysis['required'].append('writing_feedback')
    executed=obj({**execution['properties'],'state':enum(['produced','stopped','unreviewed','incomplete_input']),'evidence_ids':array(STR),'action_node_id':NULLSTR,'artifact_node_id':NULLSTR,'scope':enum(['external_action_review_not_semantic_certification'])})
    analysis['properties']['execution_trace']=array(executed)
    analysis['required'].append('execution_trace')
    delivered_review=obj({**lesson_review['properties'],'segments':array(lesson_segment)})
    lesson=obj({'review':delivered_review,'scope':enum(['single_question_lesson','partial_delivery','unreviewed']),'evidence_ids':array(STR),'segment_bindings':array(obj({'segment_id':STR,'claim_node_id':STR,'relation_node_id':STR,'evidence_ids':array(STR,1)})),'grouping_execution_ids':array(STR),'limitations':array(STR,1)})
    analysis['properties']['lesson_feedback']={'anyOf':[{'type':'null'},lesson]}
    analysis['required'].append('lesson_feedback')
    write('question-analysis',analysis)
    paper=obj({'schema_version':enum(['1.0.0','1.1.0']),'paper_id':STR,'questions':array(analysis),'recommendations':array(STR),'method_counts':{'type':'object','additionalProperties':{'type':'integer','minimum':0}},'difficulty_counts':{'type':'object'},'evidence_complete_count':{'type':'integer','minimum':0},'case_candidates':array(STR),'limitations':array(STR)})
    stage_ids={**array(STR),'uniqueItems':True}
    paper['properties']['method_coverage']={'type':'object','additionalProperties':obj({key:stage_ids for key in ['potential_question_ids','verified_trigger_question_ids','produced_question_ids','reviewed_decision_question_ids','case_candidate_question_ids']})}
    paper['properties']['typical_method_candidates']={**array(STR),'uniqueItems':True}
    paper['allOf']=[{'if':{'properties':{'schema_version':enum(['1.1.0'])}},'then':{'required':['method_coverage','typical_method_candidates']}}]
    write('paper-analysis',paper)
    question_input=json.loads((ROOT/'schemas/question-input.json').read_text(encoding='utf-8'))
    order_step=obj({'question_id':STR,'pass':enum([1,2]),'outcome':enum(['solved','deferred']),'transition':STR,'evidence':array(span,1),'execution_ids':array(STR)})
    order_review=obj({'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'source_section_ids':array(STR,1),'reading_mode':enum(['original_order','central_task',None]),'steps':array(order_step,1)})
    numbered=obj({'number':{'type':'integer','minimum':1},'question':question_input})
    write('passage-lesson-input',obj({'lesson_id':STR,'question_type':enum(TYPES[:4]),'passage':STR,'material_complete':BOOL,'questions':array(numbered,1),'review':order_review}))
    write('passage-lesson-analysis',obj({'schema_version':enum(['1.0.0']),'lesson_id':STR,'question_type':enum(TYPES[:4]),'questions':array(obj({**numbered['properties'],'analysis':analysis}),1),'scope':enum(['whole_passage_delivery','partial_delivery']),'incomplete_question_ids':array(STR),'review':obj({**order_review['properties'],'steps':array(order_step)}),'answer_summary':array(obj({'number':{'type':'integer','minimum':1},'answer':STR})),'material_complete':BOOL,'limitations':array(STR,1)}))
    measurement = obj({'accuracy':BOOL,'time_seconds':NUMBER,'candidates_remaining':NUMBER,'evidence_span':NUMBER,'hesitation_count':NUMBER,'unresolved':BOOL})
    record = obj({'record_id':STR,'participant_id':STR,'method_id':STR,'method_version':STR,'question_id':STR,'dataset_id':STR,'origin':enum(['real','synthetic']),'phase':enum(['communication','first_use','blind']),'compact_version':enum(['10s','30s','90s','full']),'case_type':enum(['positive_trigger','negative_trigger','counterexample','boundary','transfer']),'applicable':BOOL,'triggered':BOOL,'action_success':BOOL,'evidence_success':BOOL,'stop_required':BOOL,'stopped':BOOL,'resolved':BOOL,'standalone':BOOL,'assisted':BOOL,'role_overclaim':BOOL,'answer_backfit':BOOL,'execution_breakdown':BOOL,'recall_success':BOOL,'natural_restatement':BOOL,'baseline':measurement,'method':measurement,'communication_freeze_id':STR,'assignment':enum(['randomized','counterbalanced','uncontrolled']),'evaluator_id':STR})
    record['properties'].update({key:STR for key in ['observed_first_action','observed_evidence','stop_rule_observation','participant_restatement','notes']})
    record['properties']['boundary_detected'] = BOOL
    record['properties']['declared_primary_role'] = enum(ROLES)
    record['properties']['observed_actual_role'] = enum(ROLES)
    record['required'] = list(record['properties'])
    record['properties']['observed_at'] = STR
    write('evaluation-record',record)
    rate = {'type':['number','null'],'minimum':0,'maximum':1}
    metrics = obj({key:rate for key in ['trigger_precision','trigger_recall','resolution_rate','standalone_rate','assist_rate','false_trigger_rate','transfer_rate','boundary_accuracy','role_overclaim_rate','stop_rule_failure_rate']})
    count=obj({'numerator':{'type':['integer','null'],'minimum':0},'denominator':{'type':'integer','minimum':0}})
    safety = obj({'version':STR,'false_trigger_rate':rate,'boundary_accuracy':rate,'role_overclaim_rate':rate,'stop_rule_failure_rate':rate,'action_failure_rate':rate,'evidence_failure_rate':rate,'metric_counts':{'type':'object','additionalProperties':count},'record_ids':array(STR),'safe_for_release':enum(['untested',False,True])})
    audit=obj({'ready_for_review':BOOL,'blocking_reasons':array(STR),'checks':{'type':'object','additionalProperties':BOOL},'record_ids':array(STR),'scope':STR})
    blind_audit=obj({'version':enum(['10s','30s','90s','full']),'ready_for_review':BOOL,'checks':{'type':'object','additionalProperties':BOOL},'blocking_reasons':array(STR),'metrics':obj({**metrics['properties'],'action_success':rate,'evidence_success':rate}),'metric_counts':{'type':'object','additionalProperties':count},'baseline_comparison':{'type':'object'},'record_ids':array(STR),'scope':STR})
    write('evaluation-result',obj({'schema_version':STR,'origin':enum(['real','synthetic','empty']),'record_count':{'type':'integer','minimum':0},'groups':array(obj({'method_id':STR,'method_version':STR,'dataset_id':STR,'communication_freeze_id':STR,'record_count':{'type':'integer','minimum':0},'design_audit':audit,'blind_acceptance_audit':array(blind_audit),'metrics':metrics,'baseline_comparison':{'type':'object'},'first_use':{'type':'object'},'communication':{'type':'object'},'short_version_safety':array(safety),'release_eligible':BOOL,'upgrade_eligible':enum(['none','review_for_Efficient','review_for_Signature']),'limitations':array(STR)})),'limitations':array(STR)}))

if __name__ == '__main__': build()
