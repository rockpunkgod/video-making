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
    source = obj({'repository':STR,'commit':{'type':'string','pattern':'^[0-9a-f]{40}$'},'path':STR,'heading':STR})
    steps = obj({key:STR for key in ['start','first_cut','judge','stop']})
    compact = obj({key:STR for key in ['10s','30s','90s']},extra=True)
    method = {key:STR for key in ['method_id','brand_name','source_name','core_action','decision_rule','verification','stop_rule','common_wrong_instinct','transfer_pattern','memory_line','anti_rule','visual_formula','challenge_prompt','change_reason','regression_result']}
    method.update({key:array(STR) for key in ['aliases','secondary_roles','student_symptoms','trigger_cues','failure_cases','counterexamples','can_follow','usually_before','usually_after','conflicts_with','cannot_replace','affected_cases','section_ids']})
    method.update(question_type=enum(TYPES),method_type=enum(['framework','method','sub_action','internal_rule','category','verification_rule']),primary_role=enum(ROLES),role=enum(ROLES),output_type=enum(OUTPUTS),version={'type':'string','pattern':r'^\d+\.\d+\.\d+$'},maturity_status=enum(['draft','candidate','validated','stable','deprecated']),status=enum(['draft','candidate','validated','stable','deprecated']),practical_value=enum(['Useful','Efficient','Signature']),usefulness_level=enum(['Useful','Efficient','Signature']),compact=compact,four_step_card=steps,source_references=array(source,1),full={'type':'object'},levels={'type':'object'},cases={'type':'object','minProperties':1,'additionalProperties':STR},practicality_gate={'type':'object'},first_use_test={'type':'object'},evaluation={'type':'object'})
    method_contract=obj(method,extra=True)
    method_contract['properties'].update(student_ready=BOOL,entry_copy=STR,static_design_review=obj({'status':enum(['source_bound_editorial_review']),'source_section_ids':array(STR,1),'participant_validation':enum(['pending_real_participant_validation']),'example_scope':STR}))
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
    writing_section=obj({'key':enum(['overall','diagnostics','anchors','emotion','outline','revised_text','practice','materials']),'text':STR,'evidence':array(span,1)})
    correction=obj({'original':span,'replacement':STR,'reason':STR,'kind':enum(['error','optional'])})
    proposed_score=obj({'scale':enum([15,25]),'lower':{'type':'integer','minimum':0,'maximum':25},'upper':{'type':'integer','minimum':0,'maximum':25},'band':STR,'rationale':STR,'evidence':array(span,1),'source_section_id':STR,'handwriting_applied':BOOL,'original_handwriting_reference':NULLSTR})
    writing_review=obj({'schema_version':enum(['1.0.0']),'question_type':enum(['应用文','读后续写']),'kind':enum(['guidance','correction']),'reviewer':STR,'review_status':enum(['reviewed','unreviewed']),'source_section_ids':array(STR,1),'student_text_complete':BOOL,'student_text_excludes_given_starters':BOOL,'sections':array(writing_section),'corrections':array(correction),'reviewed_student_spans':array(span),'proposed_score':{'anyOf':[{'type':'null'},proposed_score]}})
    write('writing-review',writing_review)
    write('question-input',obj({'question_id':STR,'question_type':enum(TYPES+['未知']),'task_type':STR,'passage':{'type':'string'},'stem':{'type':'string'},'options':{'type':'object','additionalProperties':STR},'student_symptoms':array(STR),'observations':array(obj({'method_id':STR,'evidence':array(span,1),'reviewed':BOOL})),'relations':array(relation),'given_word':{'type':['string','null']},'student_text':{'type':'string'},'continuation_starters':array(STR),'requested_chain':array(STR),'difficulty':enum(['easy','medium','hard','unknown']),'writing_review':writing_review,'action_executions':array(execution)},required=['question_id','question_type','stem'],extra=False))
    artifact_kinds=sorted({kind for kinds in ROLE_ARTIFACTS.values() for kind in kinds})
    node = obj({'id':STR,'type':enum(['question_signal','source_evidence','candidate_claim','relation','method_action','decision','verification','action_artifact']),'label':STR,'span':span,'method_id':STR,'candidate':STR,'reviewed':BOOL,'execution_id':STR,'artifact_kind':enum(artifact_kinds),'artifact_fingerprint':{'type':'string','pattern':'^[0-9a-f]{64}$'}},required=['id','type','label'],extra=False)
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
    analysis['properties']['writing_feedback']={'anyOf':[{'type':'null'},feedback]}
    analysis['required'].append('writing_feedback')
    executed=obj({**execution['properties'],'state':enum(['produced','stopped','unreviewed','incomplete_input']),'evidence_ids':array(STR),'action_node_id':NULLSTR,'artifact_node_id':NULLSTR,'scope':enum(['external_action_review_not_semantic_certification'])})
    analysis['properties']['execution_trace']=array(executed)
    analysis['required'].append('execution_trace')
    write('question-analysis',analysis)
    write('paper-analysis',obj({'schema_version':STR,'paper_id':STR,'questions':array(analysis),'recommendations':array(STR),'method_counts':{'type':'object','additionalProperties':{'type':'integer','minimum':0}},'difficulty_counts':{'type':'object'},'evidence_complete_count':{'type':'integer','minimum':0},'case_candidates':array(STR),'limitations':array(STR)}))
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
    write('evaluation-result',obj({'schema_version':STR,'origin':enum(['real','synthetic','empty']),'record_count':{'type':'integer','minimum':0},'groups':array(obj({'method_id':STR,'method_version':STR,'dataset_id':STR,'communication_freeze_id':STR,'record_count':{'type':'integer','minimum':0},'design_audit':audit,'metrics':metrics,'baseline_comparison':{'type':'object'},'first_use':{'type':'object'},'communication':{'type':'object'},'short_version_safety':array(safety),'release_eligible':BOOL,'upgrade_eligible':enum(['none','review_for_Efficient','review_for_Signature']),'limitations':array(STR)})),'limitations':array(STR)}))

if __name__ == '__main__': build()
