"""Synthetic program checks only, never learner/exam effectiveness evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from scripts.collect_action_reviews import (collect, load_metadata, review_action, public_metadata,
    collect_chain, load_chain_metadata, collect_withdrawal, load_withdrawal)
from core.review_withdrawal import fingerprint
from scripts.ingest_exam_sources import freeze_json, sha
from tests.test_execution import action, span, seven_chain_fixture


def fixture():
    original = {'question_id': 'program-only-q1', 'question_type': '七选五',
                'stem': 'program-only synthetic partition, not an exam',
                'passage': 'alpha beta gamma', 'options': {'A': 'alpha', 'B': 'beta'},
                'task_type': 'program-only'}
    question = deepcopy(original)
    question.update({'requested_chain': ['F01'],
        'observations': [{'method_id': 'F01', 'evidence': [span()], 'reviewed': True}],
        'action_executions': [action('partition-' + axis, 'F01', 'reducer',
            {'kind': 'candidate_partition', 'axis': axis,
             'groups': [{'label': 'program-only same group', 'candidates': ['A', 'B']}]})
            for axis in ('sentence', 'actor', 'time')]})
    mechanical = {'exam_id': 'program-only', 'pass': 'blind', 'inputs': {'questions': [original]}}
    request = {'exam_id': 'program-only', 'stage': 'post_reveal_action_review',
        'reviewer': 'synthetic-program-not-a-learner', 'reviewer_kind': 'AI', 'method_id': 'F01',
        'mechanical_prediction_sha256': 'synthetic-unbound-until-file-frozen', 'question': question,
        'semantic_review': {k: 'program-only role review, not English certification' for k in
            ('trigger', 'action', 'evidence', 'output', 'stop', 'transfer', 'practical_benefit', 'limitations')}}
    request['semantic_review']['proposed_case_type'] = None
    return request, mechanical


def bounded_fixture():
    request,mechanical=fixture()
    original=mechanical['inputs']['questions'][0]
    original['question_type']='阅读理解'
    question=deepcopy(original)
    question.update(requested_chain=['R02'],
        observations=[{'method_id':'R02','evidence':[span()],'reviewed':True}],
        relations=[{'method_id':'R02','candidate':'B','effect':'eliminate','claim':'program-only mismatch',
            'evidence':[span()],'decision_rule_check':'program-only relation check',
            'stop_rule_check':'program-only bounded stop','verification':'program-only recheck',
            'reviewer':'synthetic-program-fixture','review_status':'reviewed'}],
        action_executions=[action('reject-B','R02','decider',{'kind':'candidate_decision',
            'candidate':'B','effect':'eliminate','relation_index':0})])
    request.update(method_id='R02',stage='post_reveal_bounded_action_review',question=question)
    return request,mechanical


class ActionReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = QuestionAnalyzer(Registry())

    def test_own_artifacts_do_not_require_or_imply_answer(self):
        request, mechanical = fixture(); before = deepcopy((request, mechanical))
        report = review_action(request, mechanical, self.analyzer)
        metadata = public_metadata(report)
        self.assertEqual(metadata['produced_action_count'], 3)
        self.assertTrue(metadata['answer_withheld'])
        self.assertFalse(metadata['whole_question_content_eligible'])
        self.assertEqual(metadata['registry_updates'], 0)
        self.assertIsNone(metadata['case_type'])
        self.assertNotIn('alpha', json.dumps(metadata))
        self.assertEqual((request, mechanical), before)

    def test_timing_and_complete_role_review_required(self):
        request, mechanical = fixture(); request['stage'] = 'blind'
        with self.assertRaisesRegex(ValueError, 'post-reveal'):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture(); request['semantic_review']['stop'] = ''
        with self.assertRaisesRegex(ValueError, 'Nonempty'):
            review_action(request, mechanical, self.analyzer)

    def test_material_and_task_are_immutable(self):
        for field in ('passage', 'task_type'):
            request, mechanical = fixture(); request['question'][field] = 'replacement'
            with self.assertRaisesRegex(ValueError, 'changed'):
                review_action(request, mechanical, self.analyzer)

    def test_decisions_missing_actions_and_bad_partitions_rejected(self):
        request, mechanical = fixture(); request['question']['relations'] = [{'effect': 'retain'}]
        with self.assertRaises(ValueError):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture(); request['question']['action_executions'] = []
        with self.assertRaisesRegex(ValueError, 'actual own'):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture()
        request['question']['action_executions'][0]['output']['groups'][0]['candidates'] = ['A']
        with self.assertRaisesRegex(ValueError, 'every option'):
            review_action(request, mechanical, self.analyzer)

    def test_freeze_binding_and_metadata_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); request, mechanical = fixture()
            prediction = root / 'predictions/program-only/blind.json'; freeze_json(prediction, mechanical)
            request['mechanical_prediction_sha256'] = sha(prediction.read_bytes())
            request_path = root / 'action-reviews/program-only/F01.request.json'
            freeze_json(request_path, request)
            with self.assertRaisesRegex(ValueError, 'existing reveal'):
                collect(root, request_path)
            freeze_json(root / 'results/program-only/reveal.json', {'stage': 'synthetic-program-reveal'})
            metadata = collect(root, request_path)
            self.assertEqual(collect(root, request_path), metadata)
            self.assertEqual(load_metadata(root, 'program-only'), [metadata])
            changed = deepcopy(request); changed['mechanical_prediction_sha256'] = 'wrong'
            other = root / 'action-reviews/program-only/F01.changed.json'; freeze_json(other, changed)
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                collect(root, other)
            # Derived metadata refuses a changed original request, not just source drift.
            request_path.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'request binding'):
                load_metadata(root, 'program-only')

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                collect(directory, Path(directory).parent / 'outside.json')
            root = Path(directory); request, _ = fixture()
            for relative in ('action-reviews/F01.request.json',
                             'action-reviews/wrong-exam/F01.request.json'):
                path = root / relative; freeze_json(path, request)
                with self.assertRaisesRegex(ValueError, 'own exam directory'):
                    collect(root, path)
        with self.assertRaises(ValueError):
            load_metadata('.', '../outside')


class BoundedActionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.analyzer=QuestionAnalyzer(Registry())

    def test_own_single_rejection_is_valid_without_whole_question_success(self):
        request,mechanical=bounded_fixture(); before=deepcopy(request)
        report=review_action(request,mechanical,self.analyzer)
        self.assertEqual(report['primary_role'],'decider')
        self.assertEqual(report['analysis']['candidate_analysis'][0]['candidate'],'B')
        self.assertEqual(report['analysis']['candidate_analysis'][0]['effect'],'eliminate')
        self.assertIsNone(report['analysis']['answer'])
        self.assertEqual(report['analysis']['answer_verification']['unresolved_candidates'],['A'])
        self.assertEqual(public_metadata(report)['produced_action_count'],1)
        self.assertNotIn('alpha',json.dumps(public_metadata(report)))
        self.assertEqual(request,before)

    def test_missing_own_action_cannot_be_replaced_by_extra_relation(self):
        request,mechanical=bounded_fixture()
        extra=deepcopy(request['question']['relations'][0]); extra.update(candidate='A',effect='undetermined')
        request['question']['relations'].append(extra)
        with self.assertRaisesRegex(ValueError,'exactly one own typed'):
            review_action(request,mechanical,self.analyzer)

    def test_bounded_stage_never_accepts_whole_answer_or_changed_material(self):
        request,mechanical=bounded_fixture()
        extra=deepcopy(request['question']['relations'][0]); extra.update(candidate='A',effect='retain')
        request['question']['relations'].append(extra)
        request['question']['action_executions'].append(action('retain-A','R02','decider',
            {'kind':'candidate_decision','candidate':'A','effect':'retain','relation_index':1}))
        with self.assertRaisesRegex(ValueError,'whole-question closure'):
            review_action(request,mechanical,self.analyzer)
        request,mechanical=bounded_fixture(); request['question']['passage']='changed'
        with self.assertRaisesRegex(ValueError,'changed'):
            review_action(request,mechanical,self.analyzer)

    def test_helper_role_cannot_be_relabelled_as_bounded_decider(self):
        request,mechanical=fixture(); request['stage']='post_reveal_bounded_action_review'
        with self.assertRaisesRegex(ValueError,'primary decider'):
            review_action(request,mechanical,self.analyzer)

    def test_duplicate_action_and_foreign_relation_rejected(self):
        request,mechanical=bounded_fixture()
        duplicate=deepcopy(request['question']['action_executions'][0]); duplicate['execution_id']='again-B'
        request['question']['action_executions'].append(duplicate)
        with self.assertRaisesRegex(ValueError,'exactly one own typed'):
            review_action(request,mechanical,self.analyzer)
        request,mechanical=bounded_fixture(); request['question']['relations'][0]['method_id']='R01'
        with self.assertRaises(ValueError):
            review_action(request,mechanical,self.analyzer)

    def test_bounded_record_freeze_and_replay_keep_stage_and_case_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); request,mechanical=bounded_fixture()
            prediction=root/'predictions/program-only/blind.json'; freeze_json(prediction,mechanical)
            request['mechanical_prediction_sha256']=sha(prediction.read_bytes())
            freeze_json(root/'results/program-only/reveal.json',{'stage':'synthetic-program-reveal'})
            path=root/'action-reviews/program-only/R02.request.json'; freeze_json(path,request)
            metadata=collect(root,path)
            self.assertEqual(load_metadata(root,'program-only'),[metadata])
            self.assertEqual(metadata['stage'],'post_reveal_bounded_action_review')
            self.assertEqual(metadata['case_slots_filled'],0)
            self.assertTrue(metadata['answer_withheld'])

    def frozen_own_action(self,root):
        request,mechanical=bounded_fixture()
        prediction=root/'predictions/program-only/blind.json'; freeze_json(prediction,mechanical)
        request['mechanical_prediction_sha256']=sha(prediction.read_bytes())
        freeze_json(root/'results/program-only/reveal.json',{'stage':'synthetic-program-reveal'})
        path=root/'action-reviews/program-only/R02.request.json'; freeze_json(path,request)
        collect(root,path)
        source=root/'action-reviews/program-only/R02-program-only-q1.review.json'
        report=json.loads(source.read_bytes())
        finding={'question_id':report['question_id'],'input_sha256':fingerprint(report['question']),
            'analysis_sha256':fingerprint(report['analysis']),'review_stage':'post_reveal',
            'reviewer':'synthetic-program-not-a-learner','reviewer_kind':'AI','reason':'program-only negative check',
            'withdrawn_relation_indexes':[0],'withdrawn_execution_ids':['reject-B'],
            'failure_categories':['semantic_review_problem']}
        negative={'exam_id':'program-only','method_id':'R02','source_action_review_sha256':sha(source.read_bytes()),
                  'finding':finding}
        finding_path=root/'action-reviews/program-only/negative.json'; freeze_json(finding_path,negative)
        return request,source,finding_path,negative

    def test_negative_own_review_actually_removes_output_without_overwriting_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _,source,path,_=self.frozen_own_action(root); before=source.read_bytes()
            collect_withdrawal(root,path)
            self.assertEqual(source.read_bytes(),before)
            current=load_metadata(root,'program-only')[0]
            self.assertEqual(current['produced_action_count'],0)
            self.assertTrue(current['withdrawal_applied'])
            result=json.loads(source.with_name(source.stem+'-withdrawal.json').read_bytes())
            self.assertEqual(result['analysis']['execution_trace'],[])
            self.assertEqual(result['analysis']['answer_verification']['unresolved_candidates'],['A','B'])
            self.assertIsNone(result['analysis']['answer'])

    def test_replacement_requires_bound_withdrawal_then_counts_only_new_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); request,source,negative,_=self.frozen_own_action(root)
            revised=deepcopy(request); revised['supersedes_action_review_sha256']=sha(source.read_bytes())
            revised['question']['action_executions'][0]['concrete_action']='separately reviewed program action'
            path=root/'action-reviews/program-only/R02.revised.request.json'; freeze_json(path,revised)
            with self.assertRaisesRegex(ValueError,'separately named'):
                collect(root,path)
            with self.assertRaises(FileNotFoundError): collect(root,path,revision='corrected')
            before=source.read_bytes(); collect_withdrawal(root,negative)
            metadata=collect(root,path,revision='corrected')
            self.assertEqual(collect(root,path,revision='corrected'),metadata)
            with self.assertRaisesRegex(ValueError,'already superseded'):
                collect(root,path,revision='fork')
            self.assertFalse((root/'action-reviews/program-only/R02-program-only-q1-fork.review.json').exists())
            self.assertEqual(load_metadata(root,'program-only'),[metadata])
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(metadata['produced_action_count'],1)
            self.assertEqual(metadata['case_slots_filled'],0)

    def test_negative_binding_and_unnamed_replacement_are_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _,_,path,negative=self.frozen_own_action(root)
            changed=deepcopy(negative); changed['finding']['input_sha256']='wrong'
            wrong=root/'action-reviews/program-only/wrong.json'; freeze_json(wrong,changed)
            with self.assertRaisesRegex(ValueError,'exact input'):
                collect_withdrawal(root,wrong)
            changed=deepcopy(negative); changed['method_id']='R01'
            wrong=root/'action-reviews/program-only/wrong-method.json'; freeze_json(wrong,changed)
            with self.assertRaisesRegex(ValueError,'identity'):
                collect_withdrawal(root,wrong)

    def test_valid_withdrawal_copied_to_another_report_cannot_withdraw_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _,source,path,_=self.frozen_own_action(root)
            collect_withdrawal(root,path)
            other=source.with_name('unrelated.review.json')
            changed=json.loads(source.read_bytes()); changed['reviewer']='another synthetic reviewer'
            freeze_json(other,changed)
            original=json.loads(source.with_name(source.stem+'-withdrawal.json').read_bytes())
            freeze_json(other.with_name(other.stem+'-withdrawal.json'),original)
            with self.assertRaisesRegex(ValueError,'exact source action'):
                load_withdrawal(root,other)


class ChainReviewTest(unittest.TestCase):
    """Frozen dependency controls, not evidence that an English claim is true."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        question=seven_chain_fixture()
        original={k:v for k,v in question.items() if k not in
                  {'requested_chain','observations','relations','action_executions'}}
        mechanical={'exam_id':'program-only','pass':'blind','inputs':{'questions':[original]}}
        prediction=self.root/'predictions/program-only/blind.json'; freeze_json(prediction,mechanical)
        freeze_json(self.root/'results/program-only/reveal.json',{'stage':'synthetic-program-reveal'})
        parent,_=fixture(); parent['mechanical_prediction_sha256']=sha(prediction.read_bytes())
        parent['question']={**original,'requested_chain':['F01'],
            'observations':question['observations'][:1],'action_executions':question['action_executions'][:3]}
        path=self.root/'action-reviews/program-only/F01.request.json'; freeze_json(path,parent)
        collect(self.root,path)
        parent_report=self.root/'action-reviews/program-only/F01-program-only-typed-pipeline.review.json'
        registry=Registry(); mids=['F01','F05','F11','F06']
        self.request={'exam_id':'program-only','stage':'post_reveal_chain_review',
            'reviewer':'synthetic-program-not-a-learner','reviewer_kind':'AI',
            'mechanical_prediction_sha256':sha(prediction.read_bytes()),
            'upstream_action_review_sha256':sha(parent_report.read_bytes()),'question':question,
            'semantic_review':{'method_chain':mids,'method_versions':{m:registry.methods[m]['version'] for m in mids},
                'scope':'Synthetic dependency test only',**{m:{'role':registry.methods[m]['primary_role'],
                'action':'program-only observed action','stop':'program-only stop check'} for m in mids}}}

    def run_request(self,request=None,name='request.json'):
        path=self.root/'chain-reviews/program-only'/name
        freeze_json(path,request or self.request)
        return collect_chain(self.root,path)

    def test_frozen_chain_replays_without_public_source_payload(self):
        before=deepcopy(self.request); metadata=self.run_request()
        self.assertEqual(metadata['produced_action_count'],7)
        self.assertEqual(load_chain_metadata(self.root,'program-only'),[metadata])
        self.assertEqual(self.run_request(),metadata)
        self.assertEqual(self.request,before)
        self.assertNotIn('alpha',json.dumps(metadata))
        self.assertNotIn('answer',metadata)
        self.assertEqual(metadata['case_slots_filled'],0)

    def test_current_review_with_unresolved_competitor_withholds_answer(self):
        request=deepcopy(self.request)
        request['question']['relations'][1]['effect']='undetermined'
        request['question']['action_executions'][5]['output']['effect']='undetermined'
        metadata=self.run_request(request)
        self.assertTrue(metadata['answer_withheld']); self.assertFalse(metadata['structural_closure'])

    def test_timing_source_and_parent_bindings_rejected(self):
        for field,value in [('stage','blind'),('mechanical_prediction_sha256','wrong'),
                            ('upstream_action_review_sha256','wrong')]:
            request=deepcopy(self.request); request[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.run_request(request,name=field+'.json')

    def test_original_grouping_and_source_fields_cannot_be_rewritten(self):
        for field in ['passage','task_type','group','trigger']:
            request=deepcopy(self.request); question=request['question']
            if field=='group': question['action_executions'][0]['concrete_action']='replacement'
            elif field=='trigger': question['observations'][0]['reviewed']=False
            else: question[field]='replacement'
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'changed|preserve'):
                self.run_request(request,name=field+'.json')

    def test_own_review_is_not_replaced_by_method_list(self):
        for field in ['F05','method_versions','scope']:
            request=deepcopy(self.request); request['semantic_review'].pop(field)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'own|scope'):
                self.run_request(request,name=field+'.json')

    def test_interpretation_must_consume_every_frozen_axis(self):
        request=deepcopy(self.request); request['question']['action_executions'][3]['input_artifact_ids'].pop()
        with self.assertRaisesRegex(ValueError,'all frozen'):
            self.run_request(request)

    def test_legacy_competitor_relation_cannot_replace_its_own_action(self):
        request=deepcopy(self.request)
        request['question']['action_executions'].pop(5)
        # Legacy compatibility intentionally still closes this input; the new
        # typed chain review must not count that as every own action executing.
        self.assertEqual(QuestionAnalyzer(Registry()).analyze(request['question'])['answer'],'A')
        with self.assertRaisesRegex(ValueError,'every candidate exactly once'):
            self.run_request(request)

    def test_duplicate_candidate_actions_do_not_fake_complete_coverage(self):
        request=deepcopy(self.request)
        duplicate=deepcopy(request['question']['action_executions'][4])
        duplicate['execution_id']='duplicate-choice-A'
        request['question']['action_executions'].insert(5,duplicate)
        with self.assertRaisesRegex(ValueError,'every candidate exactly once'):
            self.run_request(request)

    def test_replay_drift_and_request_path_escape_rejected(self):
        self.run_request()
        path=self.root/'chain-reviews/program-only/request.json'
        changed=deepcopy(self.request); changed['semantic_review']['scope']='changed review'
        path.write_text(json.dumps(changed),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'drift'):
            load_chain_metadata(self.root,'program-only')
        with self.assertRaisesRegex(ValueError,'private'):
            collect_chain(self.root,self.root/'outside.json')

    def test_old_version_is_preserved_not_replayed_as_current_success(self):
        self.run_request()
        current=self.root/'chain-reviews/program-only/program-only-typed-pipeline.review.json'
        historical=json.loads(current.read_bytes())
        old_request=deepcopy(self.request)
        old_request['semantic_review']['method_versions']['F05']='1.1.0'
        old_request['question']['action_executions'][3]['method_version']='1.1.0'
        old_path=self.root/'chain-reviews/program-only/old.request.json'; freeze_json(old_path,old_request)
        historical.update(method_versions=old_request['semantic_review']['method_versions'],
            request_sha256=sha(old_path.read_bytes()),request_artifact=old_path.relative_to(self.root).as_posix())
        old_report=self.root/'chain-reviews/program-only/program-only-typed-pipeline-old.review.json'
        freeze_json(old_report,historical); before=old_report.read_bytes()
        result=load_chain_metadata(self.root,'program-only')
        self.assertEqual(result[0]['method_versions']['F05'],'1.2.0')
        self.assertEqual(result[0]['superseded_artifact_count'],1)
        self.assertEqual(old_report.read_bytes(),before)
        current.unlink()  # Synthetic temporary fixture only.
        with self.assertRaisesRegex(ValueError,'current chain review'):
            load_chain_metadata(self.root,'program-only')

    def test_repeated_current_revision_cannot_count_twice(self):
        self.run_request()
        path=self.root/'chain-reviews/program-only/request.json'
        collect_chain(self.root,path,revision='duplicate')
        with self.assertRaisesRegex(ValueError,'Exactly one'):
            load_chain_metadata(self.root,'program-only')

    def test_partially_withdrawn_grouping_cannot_feed_old_chain(self):
        source=self.root/'action-reviews/program-only/F01-program-only-typed-pipeline.review.json'
        report=json.loads(source.read_bytes())
        finding={'question_id':report['question_id'],'input_sha256':fingerprint(report['question']),
            'analysis_sha256':fingerprint(report['analysis']),'review_stage':'post_reveal',
            'reviewer':'synthetic-program-not-a-learner','reviewer_kind':'AI','reason':'program-only grouping flaw',
            'withdrawn_relation_indexes':[],'withdrawn_execution_ids':['group-actor'],
            'failure_categories':['semantic_review_problem']}
        negative={'exam_id':'program-only','method_id':'F01','source_action_review_sha256':sha(source.read_bytes()),
                  'finding':finding}
        path=self.root/'action-reviews/program-only/negative-group.json'; freeze_json(path,negative)
        collect_withdrawal(self.root,path)
        metadata=load_metadata(self.root,'program-only')[0]
        self.assertEqual(metadata['produced_action_count'],2)  # Still-valid dimensions stay visible.
        self.assertTrue(metadata['withdrawal_applied'])
        with self.assertRaisesRegex(ValueError,'withdrawn or superseded'):
            self.run_request()
