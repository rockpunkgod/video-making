from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import yaml
from jsonschema import ValidationError
from core.registry import ROOT,Registry,validate_schema,load
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.matcher import symptom_route
from core.evidence import validate_graph,check_span
from renderers import render
from scripts.generate_assets import generate
from evaluation.harness import evaluate,failure_types,metrics,validate_records

def span(field,text): return {'field':field,'start':0,'end':len(text),'quote':text}
def grammar_review():
    # Existing course example, NOT an invented exam or a real participant trial.
    raw = load('cases/G01/canonical/case.yaml')['question']
    s=span('stem',raw)
    return {'question_id':'course-protect','question_type':'语法填空','task_type':'word_form','stem':raw,'given_word':'protect','observations':[{'method_id':'G09','evidence':[s],'reviewed':True}],
            'relations':[{'method_id':'G09','candidate':'protection','effect':'retain','claim':'environmental 修饰名词，空位为 promote 的宾语中心','evidence':[s],'decision_rule_check':'修饰位置与宾语中心支持名词派生','stop_rule_check':'不是动词位置，不能进谓语/非谓语路线','verification':'回填 environmental protection，中心名词与句法功能相符','reviewer':'fixture-not-human-study','review_status':'reviewed'}]}

def record(i=0,**changes):
    measure={'accuracy':True,'time_seconds':20,'candidates_remaining':2,'evidence_span':3,'hesitation_count':1,'unresolved':False}
    r={'record_id':str(i),'participant_id':'synthetic-'+str(i),'method_id':'R01','method_version':'1.1.0','question_id':'fixture-'+str(i),'dataset_id':'synthetic-contract-test','origin':'synthetic','phase':'blind','compact_version':'90s','case_type':'positive_trigger','applicable':True,'triggered':True,'action_success':True,'evidence_success':True,'stop_required':False,'stopped':False,'boundary_detected':False,'observed_first_action':'synthetic 拆 A+B','observed_evidence':'synthetic 观察，不是学生原话','stop_rule_observation':'synthetic 无需停','participant_restatement':'synthetic 只查B','notes':'仅程序分支测试，不是试题或真人数据','resolved':True,'standalone':True,'assisted':False,'role_overclaim':False,'answer_backfit':False,'execution_breakdown':False,'recall_success':True,'natural_restatement':True,'baseline':measure,'method':dict(measure),'communication_freeze_id':'synthetic-freeze','assignment':'randomized','evaluator_id':'synthetic-fixture'}
    r.update(declared_primary_role='decider',observed_actual_role='decider')
    r.update(changes); return r

class RegistryEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry()
    def test_all_methods_and_sources_validate(self): self.assertEqual(self.r.validate()['methods'],82)
    def test_all_source_documents_preserved(self):
        for d in self.r.sources['documents']:
            self.assertEqual(self.r.document(d['path']),(ROOT/'provenance/ANSWER'/d['path']).read_text(encoding='utf-8'))
    def test_generated_assets_have_no_drift(self): self.assertEqual(generate(True)['generated_assets'],'PASS')
    def test_unique_ids_indexed_once(self): self.assertEqual(set(self.r.methods),set(self.r.index['methods']))
    def test_six_types_with_gaps_not_fake_cases(self):
        self.assertEqual(len({m['question_type'] for m in self.r.methods.values()}),6)
        for m in self.r.methods.values():
            self.assertEqual(m['maturity_status'],'candidate')
            self.assertEqual(m['practical_value'],'Useful')
            for p in m['cases'].values():
                c=load(p)
                if c['status']=='evidence_gap': self.assertIsNone(c['question'])
    def test_json_schema_rejects_invalid_role(self):
        m=deepcopy(self.r.methods['F01']); m['primary_role']='answer_magic'
        with self.assertRaises(ValidationError): validate_schema('method-card',m)
    def test_json_schema_rejects_empty_stop(self):
        m=deepcopy(self.r.methods['R01']); m['stop_rule']=''
        with self.assertRaises(ValidationError): validate_schema('method-card',m)
    def test_all_anti_rules_bound_to_real_sections(self):
        for x in load('references/anti-rules.yaml')['rules']:
            self.assertTrue(x['related_methods'] and x['counterexample'] and x['boundary'])
            for mid in x['related_methods']: self.assertIn(mid,self.r.methods)
            for sid in x['source_evidence']: self.assertIn(sid,self.r.sources['sections'])
    def test_original_and_new_version_both_exist(self):
        for mid in self.r.index['golden_methods']:
            self.assertEqual(load('method-registry/history/'+mid+'/1.0.0.yaml')['version'],'1.0.0')
            self.assertEqual(self.r.methods[mid]['version'],'1.1.0')

class AnalyzerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=QuestionAnalyzer(cls.r)
    def test_raw_question_abstains_without_semantic_review(self):
        q=grammar_review(); q.pop('relations'); q.pop('observations')
        out=self.a.analyze(q)
        self.assertIsNone(out['answer']); self.assertEqual(out['status'],'needs_evidence')
    def test_existing_course_example_review_creates_trace(self):
        out=self.a.analyze(grammar_review())
        self.assertEqual(out['answer'],'protection')
        self.assertEqual(out['review_scope'],'external_semantic_review')
        self.assertTrue(any(n['type']=='verification' for n in out['evidence_graph']['nodes']))
    def test_unreviewed_relation_cannot_answer(self):
        q=grammar_review(); q['relations'][0]['review_status']='unreviewed'
        self.assertIsNone(self.a.analyze(q)['answer'])
    def test_missing_reviewed_trigger_rejects_answer_backfit(self):
        q=grammar_review(); q['observations'][0]['reviewed']=False
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_fabricated_quote_rejected(self):
        q=grammar_review(); q['relations'][0]['evidence'][0]['quote']='invented'
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_out_of_bounds_span_rejected(self):
        q=grammar_review(); q['observations'][0]['evidence'][0]['end']+=10
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_answer_key_not_accepted_as_input(self):
        q=grammar_review(); q['answer']='protection'
        with self.assertRaises(ValidationError): self.a.analyze(q)
    def test_auxiliary_method_cannot_decide(self):
        q=grammar_review(); q['observations'][0]['method_id']='G01'; q['relations'][0]['method_id']='G01'
        with self.assertRaisesRegex(ValueError,'overreach'): self.a.analyze(q)
    def test_verifier_cannot_decide(self):
        q=grammar_review(); q['observations'][0]['method_id']='G14'; q['relations'][0]['method_id']='G14'
        with self.assertRaisesRegex(ValueError,'overreach'): self.a.analyze(q)
    def test_cross_type_method_rejected(self):
        q=grammar_review(); q['observations'][0]['method_id']='F01'
        with self.assertRaisesRegex(ValueError,'Cross-type'): self.a.analyze(q)
    def test_unknown_method_rejected(self):
        q=grammar_review(); q['observations'][0]['method_id']='Z99'
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_contradictory_review_rejected(self):
        q=grammar_review(); r=deepcopy(q['relations'][0]); r['effect']='eliminate'; q['relations'].append(r)
        with self.assertRaisesRegex(ValueError,'Contradictory'): self.a.analyze(q)
    def test_eliminating_item_does_not_prove_remaining(self):
        q=grammar_review(); q['options']={'protection':'protection','protect':'protect'}
        q['relations'][0].update(candidate='protect',effect='eliminate')
        self.assertIsNone(self.a.analyze(q)['answer'])
    def test_multiple_retained_items_abstain(self):
        q=grammar_review(); r=deepcopy(q['relations'][0]); r['candidate']='other'; q['relations'].append(r)
        self.assertIsNone(self.a.analyze(q)['answer'])
    def test_main_idea_method_not_on_detail_task(self):
        q={'question_id':'q','question_type':'阅读理解','stem':'detail','task_type':'detail','observations':[{'method_id':'R06','evidence':[span('stem','detail')],'reviewed':True}]}
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_paragraph_scope_not_full_text_coverage(self):
        out=self.a.analyze({'question_id':'q','question_type':'阅读理解','stem':'mainly','task_type':'paragraph_main_idea'})
        self.assertNotIn('R06',[x['method_id'] for x in out['method_matches']])
    def test_unknown_type_abstains(self):
        out=self.a.analyze({'question_id':'q','question_type':'未知','stem':'unclear'})
        self.assertEqual(out['status'],'unsupported_type')
    def test_writing_no_fake_score(self):
        out=self.a.analyze({'question_id':'q','question_type':'读后续写','stem':'continue'})
        self.assertEqual(out['status'],'incomplete_input'); self.assertIsNone(out['answer'])
    def test_composer_has_explicit_io(self):
        out=self.a.analyze(grammar_review())
        for step in out['method_chain']: self.assertTrue(step['input'] and step['output'] and step['action'])
    def test_composer_rejects_unmatched_chain(self):
        q=grammar_review(); q['requested_chain']=['R01']
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_composer_rejects_repeated_method(self):
        q=grammar_review(); q['requested_chain']=['G01','G01']
        with self.assertRaises(ValueError): self.a.analyze(q)
    def test_undeclared_secondary_decider_rejected(self):
        q=grammar_review(); q['observations'][0]['method_id']='G01'; q['relations'][0].update(method_id='G01',execution_role='decider')
        with self.assertRaisesRegex(ValueError,'Undeclared'): self.a.analyze(q)
    def test_symptom_router_returns_action_not_only_name(self):
        out=symptom_route('语法填空','有提示词但不确定空位需要什么',self.r)
        self.assertIn('G08',[x['method_id'] for x in out]); self.assertTrue(all(x['action'] and x['stop_rule'] for x in out))
    def test_paper_correctness_gates_demo_recommendation(self):
        raw=grammar_review(); raw['question_id']='unreviewed'; raw.pop('relations'); raw.pop('observations')
        p=PaperAnalyzer(self.a).analyze({'paper_id':'course-fixture','questions':[grammar_review(),raw]})
        self.assertEqual(p['recommendations'],['course-protect']); self.assertEqual(p['evidence_complete_count'],1)
    def test_paper_duplicate_question_rejected(self):
        with self.assertRaises(ValueError): PaperAnalyzer(self.a).analyze({'paper_id':'q','questions':[grammar_review(),grammar_review()]})
    def test_provider_interface_still_enforces_schema(self):
        with self.assertRaises(ValidationError): QuestionAnalyzer(self.r,lambda q,r:{**q,'answer_key':'A'}).analyze(grammar_review())
    def test_decision_graph_without_relation_rejected(self):
        g={'nodes':[{'id':'a','type':'decision','label':'C'}],'edges':[]}
        with self.assertRaises(ValueError): validate_graph(g)
    def test_graph_cycles_rejected(self):
        g={'nodes':[{'id':'a','type':'relation','label':'x'},{'id':'b','type':'relation','label':'y'}],'edges':[{'from':'a','to':'b','type':'supports'},{'from':'b','to':'a','type':'supports'}]}
        with self.assertRaises(ValueError): validate_graph(g)
    def test_graph_dangling_edges_rejected(self):
        with self.assertRaises(ValueError): validate_graph({'nodes':[],'edges':[{'from':'a','to':'b','type':'supports'}]})
    def test_all_renderers_keep_answer_and_trace(self):
        out=self.a.analyze(grammar_review())
        for kind in ['structured','content-export']:
            projected=json.loads(render(out,kind,self.r)); self.assertEqual(projected['answer'],out['answer'])
            self.assertEqual(projected['evidence_graph'],out['evidence_graph'])
        for kind in ['student','legacy-wechat']: self.assertIn('protection',render(out,kind,self.r))
    def test_content_export_never_claims_release(self):
        out=json.loads(render(self.a.analyze(grammar_review()),'content-export',self.r))
        self.assertEqual(out['safe_for_release'],'untested')
    def test_core_has_no_presentation_templates(self):
        for p in (ROOT/'core').glob('*.py'):
            for marker in ['同学你好','B站标题','商业 CTA']:
                self.assertNotIn(marker,p.read_text(encoding='utf-8'))

class EvaluationTest(unittest.TestCase):
    def test_empty_data_not_100_percent(self):
        out=evaluate([]); self.assertEqual(out['origin'],'empty'); self.assertEqual(out['groups'],[])
        self.assertTrue(all(v is None for v in metrics([])[0].values()))
    def test_synthetic_never_earns_upgrade(self):
        out=evaluate([record()])['groups'][0]
        self.assertFalse(out['release_eligible']); self.assertEqual(out['upgrade_eligible'],'none')
        self.assertTrue(all(x['safe_for_release']=='untested' for x in out['short_version_safety']))
    def test_rates_use_correct_denominators(self):
        rows=[record(),record(1,case_type='negative_trigger',applicable=False,triggered=True,resolved=False,standalone=False),record(2,triggered=False,resolved=False,standalone=False)]
        m,c=metrics(rows)
        self.assertEqual(m['trigger_precision'],0.5); self.assertEqual(m['trigger_recall'],0.5); self.assertEqual(m['false_trigger_rate'],1)
        self.assertEqual(c['trigger_precision'],{'numerator':1,'denominator':2})
    def test_boundary_needs_actual_recognition_not_lucky_stop(self):
        rows=[record(case_type='boundary',applicable=False,triggered=False,resolved=False,standalone=False,stop_required=True,stopped=True,boundary_detected=False)]
        self.assertEqual(metrics(rows)[0]['boundary_accuracy'],0)
    def test_first_use_records_failure_types(self):
        x=record(phase='first_use',action_success=False,answer_backfit=True)
        out=evaluate([x])['groups'][0]['first_use']
        self.assertEqual(out['failures'][0]['failure_type'],['wrong_first_action','answer_backfit'])
        self.assertEqual(out['final_result'],'pending_real_participant_validation')
    def test_baseline_gain_signs(self):
        x=record(); x['method']['time_seconds']=10; x['method']['accuracy']=False
        out=evaluate([x])['groups'][0]['baseline_comparison']
        self.assertEqual(out['time_seconds']['gain'],10); self.assertEqual(out['accuracy']['gain'],-1)
    def test_duplicate_records_rejected(self):
        with self.assertRaises(ValueError): evaluate([record(),record()])
    def test_mixed_real_synthetic_rejected(self):
        with self.assertRaises(ValueError): evaluate([record(),record(1,origin='real')])
    def test_real_without_frozen_plan_not_released(self):
        out=evaluate([record(origin='real')])['groups'][0]
        self.assertFalse(out['release_eligible']); self.assertEqual(out['upgrade_eligible'],'none')
    def test_plan_retrofitting_rejected(self):
        with self.assertRaises(ValueError): evaluate([record()],{'frozen_before_data_collection':False})
    def test_role_result_requires_resolution(self):
        with self.assertRaises(ValueError): validate_records([record(resolved=False)])
    def test_no_positive_trials_resolution_null(self):
        x=record(applicable=False,triggered=False,resolved=False,standalone=False)
        self.assertIsNone(metrics([x])[0]['resolution_rate'])
    def test_execution_breakdown_only_when_no_specific_failure(self):
        self.assertEqual(failure_types(record(action_success=False,execution_breakdown=True)),['wrong_first_action'])
    def test_role_mismatch_cannot_hide_in_flags(self):
        with self.assertRaises(ValueError): evaluate([record(observed_actual_role='reducer')])
    def test_nonfinite_measurement_rejected(self):
        x=record(); x['baseline']['time_seconds']=float('nan')
        with self.assertRaises(ValueError): evaluate([x])

class LegacyTest(unittest.TestCase):
    def test_all_skill_names_and_resources_available(self):
        for name in ['gaokao-english','gaokao-objective','gaokao-grammar-fill','gaokao-writing']:
            text=(ROOT/name/'SKILL.md').read_text(encoding='utf-8')
            front=yaml.safe_load(text.split('---',2)[1]); self.assertEqual(front['name'],name)
            self.assertTrue((ROOT/name/'generated-contract.md').is_file())
    def test_grammar_checker_preserved_exactly(self):
        self.assertEqual((ROOT/'gaokao-grammar-fill/scripts/check_lesson.py').read_bytes(),(ROOT/'provenance/ANSWER/gaokao-grammar-fill/scripts/check_lesson.py').read_bytes())
    def test_original_checker_still_loads_and_checks_facts(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('legacy_checker',ROOT/'gaokao-grammar-fill/scripts/check_lesson.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        facts=module.source_facts(load('cases/G01/canonical/case.yaml')['question'],'grammar-fill')
        self.assertIn('source_first_sentence',facts)
    def test_continuation_no_false_starter_penalty_preserved(self):
        text=Registry().document('gaokao-writing/references/continuation-writing-and-correction.md')
        self.assertIn('答卷不必抄',text); self.assertIn('不是官方单独扣分项',text)
    def test_writing_scales_separate(self):
        r=Registry()
        self.assertIn('15 分评分规范',r.full('A09')); self.assertIn('25 分评分规范',r.full('W15'))
    def test_cli_validation(self):
        proc=subprocess.run([sys.executable,'-m','answer_engine','validate'],cwd=ROOT,capture_output=True,encoding='utf-8')
        self.assertEqual(proc.returncode,0,proc.stderr); self.assertEqual(json.loads(proc.stdout)['status'],'PASS')

if __name__=='__main__': unittest.main()
