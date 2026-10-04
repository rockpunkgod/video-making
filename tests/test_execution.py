"""Program-only action pipeline fixtures, not fabricated exam/learner results."""
from copy import deepcopy
import json
import unittest
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.evidence import validate_graph
from core.registry import Registry, validate_schema
from renderers import render


def span(text='alpha beta gamma'):
    return {'field':'passage','start':0,'end':len(text),'quote':text}


def action(eid,mid,role,output,inputs=None,evidence=None):
    return {'execution_id':eid,'method_id':mid,'method_version':'1.1.0','role':role,'input_artifact_ids':inputs or [],'concrete_action':'program-only observable action '+eid,
            'evidence':evidence or [span()],'decision_rule_check':'synthetic structural check, not English semantics','stop_rule_check':'synthetic stop observation','stop_applied':False,
            'reviewer':'synthetic-program-fixture-not-a-learner','review_status':'reviewed','output':output}


def fixture():
    mids=['R12','R11','R01','R17']
    q={'question_id':'program-only-typed-pipeline','question_type':'阅读理解','task_type':'detail','stem':'program fixture, NOT a real English question','passage':'alpha beta gamma','options':{'A':'alpha','B':'beta'},'requested_chain':mids,
       'observations':[{'method_id':m,'evidence':[span()],'reviewed':True} for m in mids],
       'relations':[{'method_id':'R01','candidate':c,'effect':effect,'claim':'program branch '+c,'evidence':[span()],'decision_rule_check':'program-only relation','stop_rule_check':'program-only stop','verification':'program-only backfill','reviewer':'synthetic-fixture','review_status':'reviewed'} for c,effect in [('A','retain'),('B','eliminate')]]}
    q['action_executions']=[
        action('loc','R12','locator',{'kind':'located_evidence','spans':[span('alpha')]}),
        action('meaning','R11','interpreter',{'kind':'interpretation','parts':[{'name':'program component','value':'program interpretation, not teaching proof','evidence':[span('alpha')]}]},['loc']),
        action('choice-A','R01','decider',{'kind':'candidate_decision','candidate':'A','effect':'retain','relation_index':0},['meaning']),
        action('choice-B','R01','decider',{'kind':'candidate_decision','candidate':'B','effect':'eliminate','relation_index':1},['meaning']),
        action('verify-A','R17','verifier',{'kind':'verification_result','candidate':'A','target_execution_ids':['choice-A'],'verdict':'supports'},['choice-A']),
    ]
    return q


class ExecutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.analyzer=QuestionAnalyzer(cls.r)

    def test_plans_do_not_fabricate_artifacts(self):
        q=fixture(); q.pop('action_executions')
        out=self.analyzer.analyze(q)
        self.assertEqual(out['schema_version'],'1.7.0'); self.assertEqual(out['execution_trace'],[])
        self.assertTrue(all(not s['execution_ids'] and s['state']!='executed' for s in out['method_chain']))
        self.assertTrue(out['answer_verification']['closed'])  # old reviewed relations stay compatible

    def test_serialized_contract_lists_do_not_mutate_shared_runtime_rules(self):
        q=fixture(); out=self.analyzer.analyze(q)
        out['method_chain'][0]['output_artifact_types'].append('candidate_decision')
        with self.assertRaisesRegex(ValueError,'contract'): render(out,'structured',self.r)
        fresh=self.analyzer.analyze(q)
        self.assertEqual(fresh['method_chain'][0]['output_artifact_types'],['located_evidence'])

    def test_locator_interpreter_decider_verifier_use_named_artifacts(self):
        out=self.analyzer.analyze(fixture()); validate_schema('question-analysis',out)
        self.assertEqual([x['state'] for x in out['execution_trace']],['produced']*5)
        self.assertEqual([s['state'] for s in out['method_chain']],['executed']*4)
        self.assertEqual(out['execution_trace'][1]['input_artifact_ids'],['loc'])
        self.assertEqual(len([n for n in out['evidence_graph']['nodes'] if n['type']=='action_artifact']),5)
        self.assertEqual(out['answer'],'A')

    def test_missing_circular_and_forward_references_are_rejected(self):
        for refs in [['absent'],['meaning'],['choice-A']]:
            q=fixture(); q['action_executions'][1]['input_artifact_ids']=refs
            with self.subTest(refs=refs),self.assertRaisesRegex(ValueError,'earlier'): self.analyzer.analyze(q)

    def test_duplicate_execution_and_input_ids_are_rejected(self):
        q=fixture(); q['action_executions'][1]['execution_id']='loc'
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.analyzer.analyze(q)
        q=fixture(); q['action_executions'][1]['input_artifact_ids']=['loc','loc']
        with self.assertRaisesRegex(ValueError,'Repeated'): self.analyzer.analyze(q)

    def test_interpreter_cannot_consume_an_answer_as_source(self):
        q=fixture(); q['action_executions']=q['action_executions'][:1]+q['action_executions'][2:3]+q['action_executions'][1:2]
        q['action_executions'][1]['input_artifact_ids']=['loc']; q['action_executions'][2]['input_artifact_ids']=['choice-A']
        with self.assertRaisesRegex(ValueError,'Incompatible'): self.analyzer.analyze(q)

    def test_unreviewed_output_is_withheld_and_not_consumable(self):
        q=fixture(); q['action_executions']=q['action_executions'][:1]; q['action_executions'][0]['review_status']='unreviewed'
        out=self.analyzer.analyze(q)
        self.assertIsNone(out['execution_trace'][0]['output']); self.assertEqual(out['execution_trace'][0]['state'],'unreviewed')
        q['action_executions'].append(fixture()['action_executions'][1])
        with self.assertRaisesRegex(ValueError,'earlier'): self.analyzer.analyze(q)

    def test_incomplete_input_withholds_outputs(self):
        q=fixture(); q.pop('options'); q['action_executions']=q['action_executions'][:3]
        out=self.analyzer.analyze(q)
        self.assertEqual([x['state'] for x in out['execution_trace']],['produced','produced','incomplete_input'])
        self.assertIsNone(out['execution_trace'][2]['output'])
        self.assertIsNone(out['answer'])

    def test_stop_has_no_output_and_cannot_feed_next_action(self):
        q=fixture(); q['action_executions']=q['action_executions'][:2]
        q['action_executions'][1].update(stop_applied=True,output=None)
        out=self.analyzer.analyze(q)
        self.assertEqual(out['execution_trace'][1]['state'],'stopped'); self.assertEqual(out['method_chain'][1]['state'],'stopped')
        self.assertIn('不消费该步输出',out['next_action'])
        q['action_executions'].append(fixture()['action_executions'][2])
        with self.assertRaisesRegex(ValueError,'earlier'): self.analyzer.analyze(q)
        q=fixture(); q['action_executions'][0]['stop_applied']=True
        with self.assertRaisesRegex(ValueError,'Stopped'): self.analyzer.analyze(q)

    def test_stopped_decider_cannot_simultaneously_decide(self):
        q=fixture(); q['action_executions']=q['action_executions'][:3]
        q['action_executions'][-1].update(stop_applied=True,output=None)
        with self.assertRaisesRegex(ValueError,'Stopped decider'): self.analyzer.analyze(q)

    def test_version_trigger_role_and_requested_plan_are_enforced(self):
        for change in ['version','trigger','role','plan']:
            q=fixture()
            if change=='version': q['action_executions'][0]['method_version']='1.0.0'
            elif change=='trigger': q['observations'][0]['reviewed']=False
            elif change=='role': q['action_executions'][0]['role']='decider'
            else: q['requested_chain']=q['requested_chain'][1:]
            with self.subTest(change=change),self.assertRaises(ValueError): self.analyzer.analyze(q)

    def test_foreign_spans_and_uncovered_output_spans_are_rejected(self):
        q=fixture(); q['action_executions'][0]['output']['spans'][0]['quote']='fabricated'
        with self.assertRaisesRegex(ValueError,'fabricated'): self.analyzer.analyze(q)
        q=fixture(); q['action_executions'][0]['evidence']=[span('alpha')]; q['action_executions'][0]['output']['spans']=[span()]
        with self.assertRaisesRegex(ValueError,'own action evidence'): self.analyzer.analyze(q)

    def test_own_relation_is_required_not_lucky_candidate(self):
        for change in ['candidate','index','effect','review','evidence']:
            q=fixture(); x=q['action_executions'][2]
            if change=='candidate': x['output']['candidate']='B'
            elif change=='index': x['output']['relation_index']=99
            elif change=='effect': x['output']['effect']='eliminate'
            elif change=='review': q['relations'][0]['review_status']='unreviewed'
            else: x['evidence']=[span('alpha')]
            with self.subTest(change=change),self.assertRaises(ValueError): self.analyzer.analyze(q)

    def test_verifier_targets_same_candidate_and_failed_check_withholds_answer(self):
        q=fixture(); q['action_executions'][-1]['output']['candidate']='B'
        with self.assertRaisesRegex(ValueError,'same candidate'): self.analyzer.analyze(q)
        for verdict in ['rejects','unresolved']:
            q=fixture(); q['action_executions'][-1]['output']['verdict']=verdict
            out=self.analyzer.analyze(q)
            self.assertIsNone(out['answer']); self.assertFalse(out['answer_verification']['closed']); self.assertFalse(out['content_eligible'])
            self.assertEqual(PaperAnalyzer(self.analyzer).analyze({'paper_id':'program','questions':[q]})['recommendations'],[])

    def test_partition_covers_all_candidates_without_elimination(self):
        q=fixture(); q.update(question_type='七选五',requested_chain=['F01'],relations=[],observations=[{'method_id':'F01','evidence':[span()],'reviewed':True}])
        q['action_executions']=[action('partition','F01','reducer',{'kind':'candidate_partition','axis':'program actor grouping','groups':[{'label':'one','candidates':['A']},{'label':'two','candidates':['B']}]})]
        out=self.analyzer.analyze(q); self.assertIsNone(out['answer']); self.assertEqual(out['candidate_analysis'],[])
        self.assertIn('分组不排除',render(out,'student',self.r))
        for groups in [[{'label':'one','candidates':['A']}],[{'label':'one','candidates':['A','B','A']}],[{'label':'one','candidates':['A','C']}]]:
            bad=deepcopy(q); bad['action_executions'][0]['output']['groups']=groups
            with self.assertRaisesRegex(ValueError,'exactly once'): self.analyzer.analyze(bad)
        q['action_executions'][0]['output']={'kind':'candidate_decision','candidate':'A','effect':'retain','relation_index':0}
        with self.assertRaisesRegex(ValueError,'overclaims|partition'): self.analyzer.analyze(q)

    def test_text_grouping_and_expanding_verifier_remain_auxiliary(self):
        q=fixture(); q.update(requested_chain=['R07','R17'],relations=[],observations=[{'method_id':m,'evidence':[span()],'reviewed':True} for m in ['R07','R17']])
        q['action_executions']=[action('text-group','R07','reducer',{'kind':'text_groups','groups':[{'label':'program parallel items','spans':[span('alpha')]}]}),
                                action('expand','R17','verifier',{'kind':'located_evidence','spans':[span()]})]
        out=self.analyzer.analyze(q); self.assertIsNone(out['answer']); self.assertEqual([x['state'] for x in out['execution_trace']],['produced','produced'])

    def test_secondary_decider_is_a_distinct_execution_not_framework_output(self):
        q=fixture(); q.update(question_type='完形填空',requested_chain=['C01'],observations=[{'method_id':'C01','evidence':[span()],'reviewed':True}])
        for rel in q['relations']: rel.update(method_id='C01',execution_role='decider')
        q['action_executions']=[action('cloze-framework','C01','framework',{'kind':'framework_card','fields':[{'name':n,'value':'program-only framework value','evidence':[span()]} for n in ['current_blank_role','recent_clue','expansion_gate','backfill_check']]}),
                                action('cloze-choice-A','C01','decider',{'kind':'candidate_decision','candidate':'A','effect':'retain','relation_index':0},['cloze-framework'])]
        out=self.analyzer.analyze(q)
        self.assertEqual([s['role'] for s in out['method_chain']],['framework','decider'])
        self.assertEqual([x['role'] for x in out['execution_trace']],['framework','decider'])

    def test_R09_produces_only_three_field_skeleton_not_entry_list(self):
        q=fixture(); q.update(task_type='main_idea',requested_chain=['R09'],relations=[],observations=[{'method_id':'R09','evidence':[span()],'reviewed':True}])
        q['action_executions']=[action('skeleton','R09','framework',{'kind':'framework_card','fields':[{'name':n,'value':'program-only field value','evidence':[span()]} for n in ['object','core_judgement','text_task']]})]
        out=self.analyzer.analyze(q); self.assertIsNone(out['answer'])
        without_options=deepcopy(q); without_options.pop('options')
        partial=self.analyzer.analyze(without_options)
        self.assertEqual(partial['execution_trace'][0]['state'],'produced'); self.assertIsNone(partial['answer'])
        self.assertEqual(partial['review_scope'],'external_action_review')
        q['action_executions'][0]['output']['fields'][0]['name']='repeated_words'
        with self.assertRaisesRegex(ValueError,'R09'): self.analyzer.analyze(q)

    def test_grammar_route_requires_separately_reviewed_function(self):
        q=fixture(); s={**span(),'field':'stem'}
        q.update(question_type='语法填空',stem='alpha beta gamma',given_word='program-hint',requested_chain=['G01'],relations=[],observations=[{'method_id':m,'evidence':[s],'reviewed':True} for m in ['G01','G09']])
        q['action_executions']=[action('route','G01','framework',{'kind':'route_selection','node_ids':['with_hint','noun']},evidence=[s])]
        self.assertEqual(self.analyzer.analyze(q)['execution_trace'][0]['state'],'produced')
        q['observations'].pop()
        with self.assertRaisesRegex(ValueError,'separately reviewed'): self.analyzer.analyze(q)

    def test_route_does_not_hide_competing_function_and_C01_cannot_omit_actions(self):
        q=fixture(); s={**span(),'field':'stem'}
        q.update(question_type='语法填空',stem='alpha beta gamma',given_word='program-hint',requested_chain=['G01'],relations=[],observations=[{'method_id':m,'evidence':[s],'reviewed':True} for m in ['G01','G09','G12']])
        q['action_executions']=[action('route','G01','framework',{'kind':'route_selection','node_ids':['with_hint','noun']},evidence=[s])]
        with self.assertRaisesRegex(ValueError,'competing'): self.analyzer.analyze(q)
        q['action_executions'][0]['output']['node_ids'].append('verb')
        self.assertIsNone(self.analyzer.analyze(q)['answer'])
        q=fixture(); q.update(question_type='完形填空',requested_chain=['C01'],relations=[],observations=[{'method_id':'C01','evidence':[span()],'reviewed':True}])
        q['action_executions']=[action('incomplete-framework','C01','framework',{'kind':'framework_card','fields':[{'name':'current_blank_role','value':'program-only value','evidence':[span()]}]})]
        with self.assertRaisesRegex(ValueError,'C01 framework'): self.analyzer.analyze(q)

    def test_graph_artifact_needs_own_action_and_trigger(self):
        out=self.analyzer.analyze(fixture()); g=deepcopy(out['evidence_graph'])
        action_id=out['execution_trace'][1]['action_node_id']; signal_ids={n['id'] for n in g['nodes'] if n['type']=='question_signal' and n.get('method_id')=='R11'}
        g['edges']=[e for e in g['edges'] if not(e['to']==action_id and e['from'] in signal_ids)]
        with self.assertRaisesRegex(ValueError,'trigger'): validate_graph(g)

    def test_renderers_preserve_trace_and_reject_detached_payloads(self):
        out=self.analyzer.analyze(fixture()); exported=json.loads(render(out,'content-export',self.r))
        self.assertEqual(exported['export_schema_version'],'1.7.0'); self.assertEqual(exported['execution_trace'],out['execution_trace'])
        self.assertEqual(exported['method_chain'],out['method_chain']); self.assertIn('实际动作',render(out,'student',self.r))
        for mutation in ['value','node','chain','state','inputs','evidence']:
            bad=deepcopy(out)
            if mutation=='value': bad['execution_trace'][1]['output']['parts'][0]['value']='detached new interpretation'
            elif mutation=='node': bad['execution_trace'][1]['artifact_node_id']=bad['execution_trace'][0]['artifact_node_id']
            elif mutation=='chain': bad['method_chain'][1]['execution_ids']=[]
            elif mutation=='state': bad['method_chain'][1]['state']='planned'
            elif mutation=='inputs': bad['execution_trace'][2]['input_artifact_ids']=['loc']
            else: bad['execution_trace'][1]['evidence_ids']=[]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): render(bad,'content-export',self.r)


if __name__=='__main__': unittest.main()
