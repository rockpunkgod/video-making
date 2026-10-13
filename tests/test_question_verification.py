"""Program controls, not learner trials or English method validation."""
from copy import deepcopy
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from jsonschema.exceptions import ValidationError
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry
from core.question_verification import material_fingerprint
from core.evidence import validate_graph
from renderers import render
from tests.test_execution import action
from tests.test_execution import fixture


class QuestionVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry()
        cls.engine=QuestionAnalyzer(cls.registry)

    def question(self):
        text='alpha beta gamma'
        span={'field':'passage','start':0,'end':len(text),'quote':text}
        q={'question_id':'synthetic-whole-question','question_type':'阅读理解',
           'task_type':'word_meaning','stem':'Synthetic program question, not teaching evidence',
           'passage':text,'options':{'A':'alpha','B':'beta','C':'gamma'},
           'requested_chain':['R03'],'observations':[
               {'method_id':'R03','evidence':[span],'reviewed':True}],
           'action_executions':[action('interpret','R03','interpreter',
               {'kind':'interpretation','parts':[{'name':'synthetic sense',
                'value':'synthetic interpretation','evidence':[span]}]},evidence=[span])]}
        q['question_verification_review']={
            'schema_version':'1.0.0','review_id':'synthetic-terminal-review',
            'question_id':q['question_id'],'task_type':q['task_type'],
            'source_commit':self.registry.index['source_baseline']['commit'],
            'material_sha256':material_fingerprint(q),'reviewer':'synthetic-program-reviewer',
            'review_status':'reviewed','source_section_ids':self.registry.methods['R03']['section_ids'],
            'input_artifact_ids':['interpret'],'concrete_action':'Synthetic compare complete options with interpreted passage',
            'stop_rule_check':'Synthetic stop when support or a competing claim is unresolved',
            'stop_applied':False,'candidate_checks':[
                {'candidate':c,'claim':v,'effect':'retain' if c=='A' else 'eliminate',
                 'evidence':[span],'decision_rule_check':'Synthetic own-candidate relation '+c,
                 'backfill_check':'Synthetic whole-claim backfill '+c,'backfill_verdict':'supports'} for c,v in q['options'].items()]}
        return q

    def test_legitimate_terminal_stage_does_not_change_interpreter_role(self):
        q=self.question(); before=deepcopy(q)
        result=self.engine.analyze(q)
        self.assertEqual(result['answer'],'A')
        self.assertTrue(result['answer_verification']['closed'])
        self.assertEqual(result['candidate_analysis'],[])
        self.assertEqual([x['method_id'] for x in result['method_chain']],['R03'])
        self.assertEqual(result['method_chain'][0]['role'],'interpreter')
        self.assertEqual(result['execution_trace'][0]['output']['kind'],'interpretation')
        self.assertEqual(result['question_verification']['state'],'reviewed')
        self.assertEqual(q,before)
        for kind in ('structured','student','legacy-wechat','content-export'):
            self.assertTrue(render(result,kind,self.registry))
        self.assertIn('不是辅助方法直接定案',render(result,'student',self.registry))

    def relation_question(self):
        q=self.question(); q.update(question_type='七选五',requested_chain=['F07'])
        q['observations'][0]['method_id']='F07'
        span=q['observations'][0]['evidence'][0]
        q['action_executions']=[action('check-'+c,'F07','verifier',{
            'kind':'verification_result','scope':'candidate_relation_check','candidate':c,
            'claim':claim,'target_execution_ids':[],'evidence':[span],
            'relation_check':'Synthetic two-sided relation '+c,
            'backfill_check':'Synthetic backfill '+c,
            'verdict':'supports' if c=='A' else 'rejects'},evidence=[span])
            for c,claim in q['options'].items()]
        review=q['question_verification_review']
        review.update(material_sha256=material_fingerprint(q),
            input_artifact_ids=[x['execution_id'] for x in q['action_executions']],
            source_section_ids=self.registry.methods['F07']['section_ids'])
        return q

    def test_relation_verifiers_support_terminal_without_becoming_deciders(self):
        q=self.relation_question(); support=deepcopy(q); support.pop('question_verification_review')
        self.assertIsNone(self.engine.analyze(support)['answer'])
        result=self.engine.analyze(q)
        self.assertEqual(result['answer'],'A'); self.assertEqual(result['candidate_analysis'],[])
        self.assertEqual(result['method_chain'][0]['role'],'verifier')
        self.assertFalse(any(n['type'] in {'decision','verification'} for n in result['evidence_graph']['nodes']))
        for mode in ('structured','student','legacy-wechat','content-export'): render(result,mode,self.registry)

    def test_relation_checks_cannot_borrow_another_candidate_or_omit_one(self):
        q=self.relation_question(); q['question_verification_review']['input_artifact_ids'].pop()
        with self.assertRaisesRegex(ValueError,'bypass an existing'): self.engine.analyze(q)
        q=self.relation_question(); q['question_verification_review']['input_artifact_ids'].pop()
        q['action_executions'].pop()
        with self.assertRaisesRegex(ValueError,'cannot alone decide'): self.engine.analyze(q)
        q=self.relation_question(); q['action_executions'][0]['output']['claim']='partial'
        with self.assertRaisesRegex(ValueError,'own complete option'): self.engine.analyze(q)

    def test_local_relation_rejection_is_not_global_failure_but_cannot_retain(self):
        q=self.relation_question(); q['action_executions'][0]['output']['verdict']='rejects'
        with self.assertRaisesRegex(ValueError,'contradicts its own'): self.engine.analyze(q)
        q=self.relation_question(); q['action_executions'][1]['output']['verdict']='unresolved'
        r=self.engine.analyze(q); self.assertIsNone(r['answer'])
        self.assertIn('B',r['answer_verification']['unresolved_candidates'])

    def test_relation_scope_is_explicit_and_legacy_empty_targets_remain_invalid(self):
        q=self.relation_question(); q['action_executions'][0]['output'].pop('scope')
        with self.assertRaises(ValidationError): self.engine.analyze(q)

    def test_relation_check_requires_concrete_own_passage_support(self):
        for mutation in ('blank','option_only','foreign','outside'):
            q=self.relation_question(); x=q['action_executions'][0]; out=x['output']
            if mutation=='blank': out['relation_check']=' '
            elif mutation=='foreign': out['candidate']='X'
            elif mutation=='option_only': out['evidence']=[{'field':'option:A','start':0,'end':5,'quote':'alpha'}]
            else: x['evidence']=[{'field':'passage','start':0,'end':5,'quote':'alpha'}]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.engine.analyze(q)

    def test_relation_projection_scope_and_candidate_edges_are_bound(self):
        result=self.engine.analyze(self.relation_question())
        for mutation in ('scope','candidate','edge'):
            changed=deepcopy(result); x=changed['execution_trace'][0]
            node=next(n for n in changed['evidence_graph']['nodes'] if n['id']==x['artifact_node_id'])
            if mutation=='scope':node.pop('verification_scope')
            elif mutation=='candidate':node['candidate']='B'
            else:
                target=changed['question_verification']['candidate_bindings'][1]['review_node_id']
                changed['evidence_graph']['edges'].append({'from':x['artifact_node_id'],'to':target,'type':'supports'})
            for mode in ('structured','student','legacy-wechat','content-export'):
                with self.subTest(mutation=mutation,mode=mode),self.assertRaises(ValueError):render(changed,mode,self.registry)

    def test_relation_projected_quote_cannot_be_forged_by_rehashing_output(self):
        from core.execution import artifact_fingerprint
        result=self.engine.analyze(self.relation_question())
        # A serialized artifact has no Python object aliases to action spans.
        # Mutate only exported output evidence, as in the real peer reproducer.
        changed=json.loads(json.dumps(result)); x=changed['execution_trace'][0]
        x['output']['evidence'][0]['quote']='FABRICATED CURRENT PASSAGE QUOTE'
        fingerprint=artifact_fingerprint(x['output'])
        artifact=next(n for n in changed['evidence_graph']['nodes'] if n['id']==x['artifact_node_id'])
        artifact['artifact_fingerprint']=fingerprint
        changed['question_verification']['consumed_artifacts'][0]['output_sha256']=fingerprint
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'own concrete evidence'):
                render(changed,mode,self.registry)

    def test_relation_projected_subspan_is_recovered_from_covering_action_quote(self):
        q=self.relation_question()
        q['action_executions'][0]['output']['evidence']=[{'field':'passage','start':6,'end':10,'quote':'beta'}]
        result=self.engine.analyze(q)
        for mode in ('structured','student','legacy-wechat','content-export'):render(result,mode,self.registry)

    def test_interpretation_quote_also_cannot_be_forged_by_rehashing_output(self):
        from core.execution import artifact_fingerprint
        changed=json.loads(json.dumps(self.engine.analyze(self.question())))
        x=changed['execution_trace'][0]
        x['output']['parts'][0]['evidence'][0]['quote']='FORGED INTERPRETATION QUOTE'
        fingerprint=artifact_fingerprint(x['output'])
        next(n for n in changed['evidence_graph']['nodes'] if n['id']==x['artifact_node_id'])['artifact_fingerprint']=fingerprint
        changed['question_verification']['consumed_artifacts'][0]['output_sha256']=fingerprint
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'own concrete evidence'):
                render(changed,mode,self.registry)

    def test_legacy_input_still_has_no_terminal_field_or_answer(self):
        q=self.question(); q.pop('question_verification_review')
        result=self.engine.analyze(q)
        self.assertNotIn('question_verification',result)
        self.assertIsNone(result['answer'])

    def test_unreviewed_or_stopped_terminal_cannot_close(self):
        for key,value in [('review_status','unreviewed'),('stop_applied',True)]:
            q=self.question(); q['question_verification_review'][key]=value
            result=self.engine.analyze(q)
            self.assertIsNone(result['answer'])
            self.assertFalse(result['content_eligible'])
            self.assertTrue(all(c['effect']=='undetermined' for c in result['question_verification']['candidate_bindings']))
            self.assertFalse(any(n['type']=='question_decision' for n in result['evidence_graph']['nodes']))

    def test_each_rival_must_be_checked_not_only_supported_or_remaining_one(self):
        q=self.question(); q['question_verification_review']['candidate_checks'].pop()
        with self.assertRaisesRegex(ValueError,'every candidate'): self.engine.analyze(q)
        q=self.question(); q['question_verification_review']['candidate_checks'][0]['effect']='undetermined'
        result=self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'],['A'])

    def test_multiple_retained_candidates_are_not_resolved_by_brand(self):
        q=self.question(); q['question_verification_review']['candidate_checks'][1]['effect']='retain'
        self.assertIsNone(self.engine.analyze(q)['answer'])

    def test_failed_or_unresolved_backfill_withholds_candidate_and_answer(self):
        for verdict in ('rejects','unresolved'):
            q=self.question(); q['question_verification_review']['candidate_checks'][1]['backfill_verdict']=verdict
            result=self.engine.analyze(q)
            self.assertIsNone(result['answer'])
            self.assertEqual(result['answer_verification']['unresolved_candidates'],['B'])

    def test_prior_source_epoch_cannot_approve_current_terminal(self):
        q=self.question(); q['question_verification_review']['source_commit']='b04ebc26d7fa096404111a0bb12f6c77cc8525b9'
        with self.assertRaisesRegex(ValueError,'binding differs'): self.engine.analyze(q)

    def test_duplicate_or_foreign_candidate_is_rejected(self):
        for candidate in ('A','X'):
            q=self.question(); q['question_verification_review']['candidate_checks'][1]['candidate']=candidate
            with self.assertRaisesRegex(ValueError,'every candidate'): self.engine.analyze(q)

    def test_original_material_task_and_full_claim_binding(self):
        for key,value in [('passage','changed source'),('task_type','detail'),('question_id','other')]:
            q=self.question(); q[key]=value
            with self.assertRaises(ValueError): self.engine.analyze(q)
        q=self.question(); q['question_verification_review']['candidate_checks'][0]['claim']='partial'
        with self.assertRaisesRegex(ValueError,'complete option'): self.engine.analyze(q)

    def test_each_candidate_needs_exact_passage_evidence(self):
        q=self.question(); c=q['question_verification_review']['candidate_checks'][1]
        c['evidence']=[{'field':'option:B','start':0,'end':4,'quote':'beta'}]
        with self.assertRaisesRegex(ValueError,'own passage'): self.engine.analyze(q)
        q=self.question(); q['question_verification_review']['candidate_checks'][1]['evidence'][0]['quote']='fabricated'
        with self.assertRaisesRegex(ValueError,'fabricated'): self.engine.analyze(q)

    def test_missing_unreviewed_or_stopped_upstream_is_not_consumable(self):
        q=self.question(); q['question_verification_review']['input_artifact_ids']=['missing']
        with self.assertRaisesRegex(ValueError,'produced earlier'): self.engine.analyze(q)
        for key,value in [('review_status','unreviewed'),('stop_applied',True)]:
            q=self.question(); q['action_executions'][0][key]=value
            if key=='stop_applied': q['action_executions'][0]['output']=None
            with self.assertRaisesRegex(ValueError,'produced earlier'): self.engine.analyze(q)

    def test_location_alone_is_not_terminal_evidence(self):
        q=self.question(); x=q['action_executions'][0]; span=x['evidence'][0]
        q['requested_chain']=['R13']; q['observations'][0]['method_id']='R13'
        x.update(method_id='R13',role='locator',output={'kind':'located_evidence','spans':[span]})
        q['question_verification_review']['source_section_ids']=self.registry.methods['R13']['section_ids']
        with self.assertRaisesRegex(ValueError,'cannot alone decide'): self.engine.analyze(q)

    def test_fake_source_section_and_blank_instructions_are_rejected(self):
        q=self.question(); q['question_verification_review']['source_section_ids']=['invented']
        with self.assertRaisesRegex(ValueError,'consumed current methods'): self.engine.analyze(q)
        q=self.question(); q['question_verification_review']['concrete_action']=' '
        with self.assertRaisesRegex(ValueError,'concrete'): self.engine.analyze(q)

    def test_graph_cannot_attach_another_candidates_review_to_decision(self):
        r=self.engine.analyze(self.question()); graph=deepcopy(r['evidence_graph'])
        bindings=r['question_verification']['candidate_bindings']
        edge=next(e for e in graph['edges'] if e['to']==bindings[0]['decision_node_id'])
        edge['from']=bindings[1]['review_node_id']
        with self.assertRaisesRegex(ValueError,'own reviewed candidate'): validate_graph(graph)

    def test_graph_requires_direct_own_passage_and_interpretation(self):
        result=self.engine.analyze(self.question())
        target=result['question_verification']['candidate_bindings'][0]['review_node_id']
        for kind in ('source_evidence','action_artifact','candidate_claim'):
            graph=deepcopy(result['evidence_graph']); nodes={n['id']:n for n in graph['nodes']}
            graph['edges']=[e for e in graph['edges'] if not (e['to']==target and nodes[e['from']]['type']==kind)]
            with self.assertRaisesRegex(ValueError,'own claim, passage'): validate_graph(graph)

    def test_serialized_result_cannot_change_answer_or_review_effect(self):
        result=self.engine.analyze(self.question())
        for mode in ('structured','student','content-export'):
            changed=deepcopy(result); changed['answer']='B'
            with self.assertRaisesRegex(ValueError,'aggregation'): render(changed,mode,self.registry)
            changed=deepcopy(result)
            changed['question_verification']['review']['candidate_checks'][0]['effect']='eliminate'
            with self.assertRaisesRegex(ValueError,'payload differs'): render(changed,mode,self.registry)

    def test_terminal_decisions_do_not_add_brand_decider_credit_to_paper(self):
        result=PaperAnalyzer(self.engine).analyze({'paper_id':'synthetic-paper','questions':[self.question()]})
        self.assertEqual(result['method_coverage']['R03']['reviewed_decision_question_ids'],[])

    def test_projection_cannot_drop_claim_or_upstream_artifact(self):
        result=self.engine.analyze(self.question())
        changed=deepcopy(result)
        changed['question_verification']['review']['candidate_checks'][0]['claim']='partial claim'
        with self.assertRaisesRegex(ValueError,'payload differs'): render(changed,'student',self.registry)
        changed=deepcopy(result)
        changed['question_verification']['consumed_artifacts'][0]['output_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'artifact projection'): render(changed,'student',self.registry)

    def terminal_over_prior_decisions(self):
        q=fixture(); q['task_type']='detail'
        q['question_verification_review']=deepcopy(self.question()['question_verification_review'])
        review=q['question_verification_review']
        review.update(question_id=q['question_id'],task_type=q['task_type'],
                      material_sha256=material_fingerprint(q),input_artifact_ids=['meaning'],
                      source_section_ids=self.registry.methods['R11']['section_ids'])
        review['candidate_checks']=review['candidate_checks'][:2]
        for c in review['candidate_checks']: c['claim']=q['options'][c['candidate']]
        return q

    def test_terminal_backfill_failure_vetoes_previously_closed_method_answer(self):
        q=self.terminal_over_prior_decisions()
        legacy=deepcopy(q); legacy.pop('question_verification_review')
        self.assertEqual(self.engine.analyze(legacy)['answer'],'A')
        q['question_verification_review']['candidate_checks'][1]['backfill_verdict']='unresolved'
        result=self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertEqual(result['answer_verification']['unresolved_candidates'],['B'])

    def test_terminal_conflict_with_method_decision_is_rejected(self):
        q=self.terminal_over_prior_decisions()
        q['question_verification_review']['candidate_checks'][1]['effect']='retain'
        with self.assertRaisesRegex(ValueError,'conflicts with'): self.engine.analyze(q)

    def test_failed_upstream_verification_cannot_be_bypassed(self):
        q=self.terminal_over_prior_decisions()
        q['action_executions'][-1]['output']['verdict']='rejects'
        with self.assertRaisesRegex(ValueError,'failed upstream'): self.engine.analyze(q)

    def test_projection_cannot_delete_a_rival_then_recompute_answer(self):
        from core.question_verification import apply_question_verification
        result=self.engine.analyze(self.question())
        terminal=result['question_verification']
        terminal['review']['candidate_checks'].pop(1)
        terminal['candidate_bindings'].pop(1)
        apply_question_verification(result,terminal)
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.assertRaisesRegex(ValueError,'payload differs'): render(result,mode,self.registry)

    def test_projection_cannot_change_original_material_fingerprint(self):
        result=self.engine.analyze(self.question())
        result['question_verification']['review']['material_sha256']='0'*64
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.assertRaisesRegex(ValueError,'original material'): render(result,mode,self.registry)

    def test_projection_cannot_remove_terminal_report_but_keep_answer(self):
        result=self.engine.analyze(self.question())
        result.pop('question_verification')
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.assertRaisesRegex(ValueError,'drop its projected review'): render(result,mode,self.registry)

    def test_schema_rebuild_preserves_review_interfaces_and_private_case_contract(self):
        from scripts.build_schemas import build
        from core.registry import ROOT
        names=['question-input','question-analysis','evidence-graph','question-verification-review','case']
        expected={name:json.loads((ROOT/'schemas'/(name+'.json')).read_bytes()) for name in names}
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)
            with patch('scripts.build_schemas.ROOT',temporary): build()
            for name in names:
                self.assertEqual(json.loads((temporary/'schemas'/(name+'.json')).read_bytes()),expected[name],name)

    def test_projection_rechecks_stop_on_an_unconsumed_valid_upstream_action(self):
        q=self.question(); result=self.engine.analyze(q)
        q.pop('question_verification_review')
        stopped=deepcopy(q['action_executions'][0])
        stopped.update(execution_id='probe-stop',stop_applied=True,output=None)
        q['action_executions'].append(stopped)
        control=self.engine.analyze(q)
        stop_trace=deepcopy(control['execution_trace'][-1])
        extra_ids=set(stop_trace['evidence_ids']+[stop_trace['action_node_id']])
        rename={nid:'stop-'+nid for nid in extra_ids}
        for n in control['evidence_graph']['nodes']:
            if n['id'] in extra_ids:
                n=deepcopy(n); n['id']=rename[n['id']]; result['evidence_graph']['nodes'].append(n)
        for e in control['evidence_graph']['edges']:
            if e['to'] in extra_ids or e['from'] in extra_ids:
                e=deepcopy(e); e['from']=rename.get(e['from'],e['from']); e['to']=rename.get(e['to'],e['to'])
                result['evidence_graph']['edges'].append(e)
        stop_trace['evidence_ids']=[rename[nid] for nid in stop_trace['evidence_ids']]
        stop_trace['action_node_id']=rename[stop_trace['action_node_id']]
        result['execution_trace'].append(stop_trace)
        result['method_chain']=control['method_chain']
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.assertRaisesRegex(ValueError,'bypass stopped'): render(result,mode,self.registry)


if __name__=='__main__': unittest.main()
