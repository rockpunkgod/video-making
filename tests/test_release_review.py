"""Synthetic control tests only. No real observations, cases or approvals are saved.

In-memory origin/verified/approved flags exercise the external-declaration branch,
not authenticate people, course legality, statistical significance or teaching.
"""
from copy import deepcopy
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from core.registry import ROOT,Registry
from core.release import CHECKS,check_release,read_json,release_bindings,regression_snapshot,material_path
from tests.test_evaluation_workflow import design,declared_real


class ReleaseReviewTest(unittest.TestCase):
    def test_pending_template_is_not_a_release(self):
        r=Registry(); before=deepcopy(r.methods)
        out=check_release(r,read_json('evaluation/release-review.example.json'))
        self.assertFalse(out['ready_for_manual_release'])
        self.assertIn('five_verified_case_slots',out['blocking_reasons'])
        self.assertIn('real_evaluation_release_gate',out['blocking_reasons'])
        self.assertEqual(r.methods,before)

    def fixture(self,grade='Useful',state='validated'):
        r=Registry(); rows,plan=design(); rows=declared_real(rows)
        for row in rows: row['method_version']=r.methods[row['method_id']]['version']
        cases={path:{'status':'verified_course_example','question':'PROGRAM-ONLY metadata, not an exam or verified course case',
                     'method_id':'R01','method_version':r.methods['R01']['version'],
                     'source_commit':r.index['source_baseline']['commit']}
               for path in r.methods['R01']['cases'].values()}
        stack=ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(r,'case_inventory',return_value=cases))
        report={**regression_snapshot(r),'source_commit':r.index['source_baseline']['commit'],'after_refactor':{'tests_run':278,'failures':0,'errors':0,'registry':{'status':'PASS'},'generated':{'generated_assets':'PASS'}}}
        review=read_json('evaluation/release-review.example.json')
        review['method_version']=r.methods['R01']['version']
        review.update(target_maturity=state,target_practical_value=grade,approved=True,reviewer='PROGRAM-ONLY reviewer declaration',reviewed_at='2026-01-07T00:00:00Z',checks={key:True for key in CHECKS},evidence_refs=['PROGRAM-ONLY control metadata, not human evidence'])
        memory={review['inputs']['plan']:plan,review['inputs']['regression']:report}
        stack.enter_context(patch('core.release.read_json',side_effect=lambda path:deepcopy(memory[path])))
        stack.enter_context(patch('core.release.material_path',side_effect=lambda path:ROOT/path))
        stack.enter_context(patch('evaluation.harness.load_records',return_value=rows))
        review['bindings']=release_bindings(r,'R01',review['inputs'])
        return r,review,rows,plan,report,memory

    def test_explicit_bound_external_approval_can_pass_without_writing_cards(self):
        r,review,*_=self.fixture(); before=deepcopy(r.methods)
        out=check_release(r,review)
        self.assertTrue(out['ready_for_manual_release'],out)
        self.assertEqual(r.methods,before)
        self.assertIn('not authentication',out['scope'])

    def test_historical_case_epoch_cannot_release_current_method(self):
        r,review,*_=self.fixture()
        for case in r.case_inventory().values(): case['source_commit']='0'*40
        review['bindings']=release_bindings(r,'R01',review['inputs'])
        out=check_release(r,review)
        self.assertIn('five_verified_case_slots',out['blocking_reasons'])

    def test_unapproved_or_stale_method_case_data_plan_report_cannot_release(self):
        for mutation in ('approval','method','cases','records','plan','report'):
            r,review,rows,plan,report,memory=self.fixture()
            if mutation=='approval': review['approved']=False
            elif mutation=='method': r.methods['R01']['core_action']+=' PROGRAM CHANGE'
            elif mutation=='cases': next(iter(r.case_inventory().values()))['question']+=' PROGRAM CHANGE'
            elif mutation=='records': rows[0]['notes']+=' PROGRAM CHANGE'
            elif mutation=='plan': plan['rationale']+=' PROGRAM CHANGE'
            else: report['after_refactor']['failures']=1
            with self.subTest(mutation=mutation): self.assertFalse(check_release(r,review)['ready_for_manual_release'])

    def test_synthetic_data_and_missing_human_checks_block_even_matching_hashes(self):
        r,review,rows,*_=self.fixture()
        for row in rows: row['origin']='synthetic'
        review['bindings']=release_bindings(r,'R01',review['inputs'])
        self.assertIn('real_evaluation_release_gate',check_release(r,review)['blocking_reasons'])
        for row in rows: row['origin']='real'
        review['checks']['role_correctness']=False
        review['bindings']=release_bindings(r,'R01',review['inputs'])
        self.assertIn('human_common_checks',check_release(r,review)['blocking_reasons'])

    def test_efficiency_and_signature_still_need_explicit_human_reviews(self):
        for grade,key in [('Efficient','statistical_significance'),('Signature','visual_memory_speech'),('Signature','short_version_safety')]:
            r,review,*_=self.fixture(grade=grade)
            self.assertTrue(check_release(r,review)['ready_for_manual_release'])
            review['checks'][key]=False
            with self.subTest(grade=grade,key=key): self.assertFalse(check_release(r,review)['ready_for_manual_release'])

    def test_stable_requires_prior_validated_and_own_multiple_transfer_items(self):
        r,review,rows,plan,report,memory=self.fixture(state='stable')
        self.assertFalse(check_release(r,review)['ready_for_manual_release'])
        for x in rows:
            if x['phase']=='blind' and x['case_type']=='transfer': x['question_id']+='-'+x['participant_id'].rsplit('-',1)[-1]
        review['bindings']=release_bindings(r,'R01',review['inputs'])
        prior=deepcopy(review); prior.update(target_maturity='validated',reviewed_at='2026-01-06T12:00:00Z')
        review['validated_review']='evaluation/program-prior-not-saved.json'; memory[review['validated_review']]=prior
        self.assertTrue(check_release(r,review)['ready_for_manual_release'])
        review['checks']['stable_transfer']=False
        self.assertIn('stable_transfer_review',check_release(r,review)['blocking_reasons'])

    def test_applied_target_aliases_and_approval_date_cannot_be_changed(self):
        r,review,*_=self.fixture()
        self.assertIn('applied_state_matches_approval',check_release(r,review,applied=True)['blocking_reasons'])
        method=r.methods['R01']; method.update(status='validated',maturity_status='validated')
        self.assertTrue(check_release(r,review,applied=True)['ready_for_manual_release'])
        review['reviewed_at']='2025-01-01T00:00:00Z'
        self.assertIn('approval_after_observations',check_release(r,review)['blocking_reasons'])

    def test_external_absolute_or_missing_paths_are_rejected(self):
        for path in ('../outside.json',str(ROOT/'README.md'),'evaluation/no-such-artifact.json'):
            with self.subTest(path=path),self.assertRaises(ValueError): material_path(path)

    def test_registry_requires_review_and_rejects_invalid_review_index(self):
        r=Registry(); r.methods['R01'].update(status='validated',maturity_status='validated')
        with self.assertRaisesRegex(ValueError,'separately reviewed'): r.validate()
        r=Registry(); r.index['release_reviews']={'unknown':'review.json'}
        with self.assertRaisesRegex(ValueError,'review index'): r.validate()

    def test_role_output_mismatch_is_not_overridden_by_human_checks(self):
        for mid,output in [('R11','decide'),('R17','decide'),('R09','decide'),('R01','locate')]:
            r=Registry(); inventory=r.case_inventory(); r.methods[mid]['output_type']=output
            with self.subTest(mid=mid),self.assertRaisesRegex(ValueError,'Case slot.*mismatch'): r.validate()
            # Isolate the second guard from the earlier case-slot guard; no case files change.
            with patch.object(r,'case_inventory',return_value=inventory),self.assertRaisesRegex(ValueError,'method_overreach'): r.validate()
        r,review,rows,plan,report,memory=self.fixture()
        r.methods['R01']['output_type']='locate'
        report.update(regression_snapshot(r)); review['bindings']=release_bindings(r,'R01',review['inputs'])
        self.assertIn('primary_role_output_match',check_release(r,review)['blocking_reasons'])

    def test_registry_applied_review_cannot_borrow_another_method_or_target(self):
        r=Registry(); r.methods['R01'].update(status='validated',maturity_status='validated')
        r.index['release_reviews']={'R01':'evaluation/release-review.example.json'}
        with patch('core.release.read_json',return_value={'method_id':'R02'}):
            with self.assertRaisesRegex(ValueError,'method mismatch'): r.validate()
        with patch('core.release.read_json',return_value={'method_id':'R01'}),patch('core.release.check_release',return_value={'ready_for_manual_release':False,'blocking_reasons':['applied_state_matches_approval']}):
            with self.assertRaisesRegex(ValueError,'applied_state_matches_approval'): r.validate()
        with patch('core.release.read_json',return_value={'method_id':'R01'}),patch('core.release.check_release',return_value={'ready_for_manual_release':True}) as check:
            self.assertEqual(r.validate()['status'],'PASS')
            self.assertTrue(check.call_args.kwargs['applied'])

    def test_new_commands_are_read_only_and_hashes_do_not_approve_template(self):
        for command in ('release-check','release-bindings'):
            proc=subprocess.run([sys.executable,'-m','answer_engine',command,'evaluation/release-review.example.json'],cwd=ROOT,capture_output=True,encoding='utf-8')
            self.assertEqual(proc.returncode,0,proc.stderr); value=json.loads(proc.stdout)
            if command=='release-check': self.assertFalse(value['ready_for_manual_release'])
            else: self.assertTrue(all(isinstance(v,str) and len(v)==64 for v in value.values()))


if __name__=='__main__': unittest.main()
