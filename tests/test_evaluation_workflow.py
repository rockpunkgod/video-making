"""Synthetic program lineage tests, never saved as real learner data/results.

Changing the caller's origin flag to real tests the trust-boundary branch only;
none of these fabricated metadata records can establish teaching effectiveness.
"""
from copy import deepcopy
import unittest
from core.registry import load
from evaluation.harness import COMMUNICATION_CHECKS,PRACTICALITY_CHECKS,evaluate,load_records,validate_plan
from core.registry import ROOT

def observation(i,phase,version,kind='positive_trigger',person=None):
    applicable=kind in {'positive_trigger','transfer'}; stop=kind in {'boundary','counterexample'}
    measurement={'accuracy':True,'time_seconds':20,'candidates_remaining':2,'evidence_span':3,'hesitation_count':1,'unresolved':False}
    result={'record_id':'program-'+str(i),'participant_id':person or 'program-person-'+str(i),'method_id':'R01','method_version':'1.1.0','question_id':'program-'+phase+'-'+kind,'dataset_id':'synthetic-protocol-fixture','origin':'synthetic','phase':phase,'compact_version':version,'case_type':kind,'applicable':applicable,'triggered':applicable,'action_success':True,'evidence_success':True,'stop_required':stop,'stopped':stop,'boundary_detected':stop,'resolved':applicable,'standalone':applicable,'assisted':False,'role_overclaim':False,'answer_backfit':False,'execution_breakdown':False,'recall_success':True,'natural_restatement':True,'baseline':measurement,'method':{**measurement,'time_seconds':10},'communication_freeze_id':'program-freeze','assignment':'randomized','evaluator_id':'program-fixture-not-a-study','observed_first_action':'synthetic program action','observed_evidence':'synthetic metadata, not English exam evidence','stop_rule_observation':'synthetic branch','participant_restatement':'synthetic fixture, not learner speech','notes':'PROGRAM ONLY, not actual participants or teaching results','declared_primary_role':'decider','observed_actual_role':'decider','observed_at':{'communication':'2026-01-02T00:00:00Z','first_use':'2026-01-05T00:00:00Z','blind':'2026-01-06T00:00:00Z'}[phase]}
    return result

def design():
    rows=[observation(0,'communication','90s'),observation(1,'first_use','90s')]
    i=2
    for version in ['10s','30s','90s']:
        for person in range(2):
            for kind in ['positive_trigger','negative_trigger','counterexample','boundary','transfer']:
                rows.append(observation(i,'blind',version,kind,'program-'+version+'-'+str(person))); i+=1
    plan=load('evaluation/plan.example.json')
    plan.update(dataset_id='synthetic-protocol-fixture',communication_freeze_id='program-freeze',minimum_participants_per_version=2,frozen_before_data_collection=True)
    plan['workflow']={'study_frozen_at':'2026-01-01T00:00:00Z','communication_frozen_at':'2026-01-03T00:00:00Z','practicality_reviewed_at':'2026-01-04T00:00:00Z','communication_record_ids':['program-0'],'communication_checks':{k:True for k in COMMUNICATION_CHECKS},'practicality_checks':{k:True for k in PRACTICALITY_CHECKS},'demonstration_item_ids':['program-demo-not-a-test'],'reviewer':'synthetic-program-fixture','evidence_notes':'Synthetic parser/control test, not a real audit or teaching trial.'}
    return rows,plan

def declared_real(rows):
    # Exercise external caller metadata, NOT a conversion of synthetic evidence
    # into usable real results. Never persist or cite the returned metrics.
    return [{**row,'origin':'real'} for row in rows]

class EvaluationWorkflowTest(unittest.TestCase):
    def test_complete_declared_lineage_is_auditable_but_synthetic_never_upgrades(self):
        rows,plan=design(); group=evaluate(rows,plan)['groups'][0]
        self.assertTrue(group['design_audit']['ready_for_review'])
        self.assertFalse(group['release_eligible']); self.assertEqual(group['upgrade_eligible'],'none')
        self.assertTrue(all(s['safe_for_release']=='untested' for s in group['short_version_safety']))
        for s in group['short_version_safety']:
            for metric,counts in s['metric_counts'].items():
                self.assertEqual(s[metric],None if not counts['denominator'] else counts['numerator']/counts['denominator'])
            self.assertEqual(len(s['record_ids']),10)

    def test_positive_caller_flag_branch_requests_review_not_registry_promotion(self):
        rows,plan=design(); group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertTrue(group['release_eligible']); self.assertEqual(group['upgrade_eligible'],'review_for_Signature')
        self.assertIn('external audit',group['design_audit']['scope'])

    def test_other_study_communication_cannot_complete_blind_prerequisites(self):
        rows,plan=design(); rows[0]['dataset_id']='another-program-study'
        groups=evaluate(declared_real(rows),plan)['groups']
        self.assertEqual(len(groups),2)
        self.assertTrue(all(not g['release_eligible'] and g['upgrade_eligible']=='none' for g in groups))
        self.assertEqual(sum(g['record_count'] for g in groups),len(rows))

    def test_freeze_ids_are_not_mixed_even_with_same_method_version(self):
        rows,plan=design(); rows[1]['communication_freeze_id']='other-freeze'
        groups=evaluate(declared_real(rows),plan)['groups']
        self.assertEqual(len(groups),2)
        self.assertTrue(all(g['upgrade_eligible']=='none' for g in groups))

    def test_same_frozen_item_cannot_change_labels_between_versions(self):
        for field,value in [('case_type','transfer'),('applicable',False),('stop_required',True)]:
            rows,plan=design(); rows[2][field]=value
            if field=='applicable': rows[2].update(triggered=False,resolved=False,standalone=False)
            group=evaluate(declared_real(rows),plan)['groups'][0]
            self.assertIn('consistent_frozen_item_labels',group['design_audit']['blocking_reasons'])
            self.assertFalse(group['release_eligible']); self.assertEqual(group['upgrade_eligible'],'none')

    def test_committed_statistics_match_current_harness_without_real_data(self):
        for records,result in [('synthetic-observations.json','synthetic-contract-result.json'),('real-observations.pending.json','real-validation.pending.json')]:
            observations=load_records(ROOT/'evaluation'/'datasets'/records)
            self.assertEqual(evaluate(observations),load('evaluation/results/'+result))

    def test_missing_workflow_or_times_retains_statistics_without_release(self):
        for missing in ['workflow','time']:
            rows,plan=design()
            if missing=='workflow': plan.pop('workflow')
            else: rows[-1].pop('observed_at')
            group=evaluate(declared_real(rows),plan)['groups'][0]
            self.assertIsNotNone(group['metrics']['trigger_precision'])
            self.assertFalse(group['design_audit']['ready_for_review']); self.assertEqual(group['upgrade_eligible'],'none')

    def test_stage_order_cannot_be_backfilled_or_reversed(self):
        for field,value in [('study_frozen_at','2026-01-07T00:00:00Z'),('communication_frozen_at','2026-01-01T00:00:00Z'),('practicality_reviewed_at','2026-01-06T00:00:00Z')]:
            rows,plan=design(); plan['workflow'][field]=value
            group=evaluate(declared_real(rows),plan)['groups'][0]
            self.assertIn('phase_order',group['design_audit']['blocking_reasons']); self.assertFalse(group['release_eligible'])

    def test_failed_gate_or_first_use_blocks_efficiency_and_signature_review(self):
        for failure in ['communication','practicality','first_use']:
            rows,plan=design()
            if failure=='communication': plan['workflow']['communication_checks']['visual_action']=False
            elif failure=='practicality': plan['workflow']['practicality_checks']['stop']=False
            else: rows[1]['action_success']=False
            group=evaluate(declared_real(rows),plan)['groups'][0]
            self.assertEqual(group['upgrade_eligible'],'none'); self.assertFalse(group['release_eligible'])

    def test_freeze_artifact_must_point_to_its_actual_communication_records(self):
        rows,plan=design(); plan['workflow']['communication_record_ids']=['a-different-observation']
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertIn('communication_freeze_bound_to_observations',group['design_audit']['blocking_reasons'])

    def test_demo_and_first_use_items_cannot_reappear_as_unseen_tests(self):
        rows,plan=design(); plan['workflow']['demonstration_item_ids']=[rows[1]['question_id']]
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertIn('demonstration_not_reused_as_test',group['design_audit']['blocking_reasons'])
        rows,plan=design(); rows[2].update(participant_id=rows[1]['participant_id'],question_id=rows[1]['question_id'])
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertIn('first_use_item_not_repeated_blind',group['design_audit']['blocking_reasons'])

    def test_cross_phase_exposure_requires_learning_control(self):
        rows,plan=design(); rows[0]['participant_id']=rows[2]['participant_id']
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertIn('cross_phase_learning_control',group['design_audit']['blocking_reasons'])
        for x in rows:
            if x['phase']=='blind' and x['participant_id']==rows[0]['participant_id']: x['assignment']='counterbalanced'
        self.assertTrue(evaluate(declared_real(rows),plan)['groups'][0]['design_audit']['checks']['cross_phase_learning_control'])

    def test_plan_role_cannot_be_self_relabelled_away_from_registry(self):
        rows,plan=design()
        for x in rows: x.update(declared_primary_role='reducer',observed_actual_role='reducer')
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertIn('registry_version_role_binding',group['design_audit']['blocking_reasons'])

    def test_small_or_uncovered_blind_study_cannot_request_efficiency_review(self):
        rows,plan=design(); rows=rows[:3]
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertEqual(group['upgrade_eligible'],'none')

    def test_guessing_correctly_does_not_prove_method_resolution_or_short_safety(self):
        rows,plan=design(); rows[2]['action_success']=False
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertLess(group['metrics']['resolution_rate'],1)
        short=next(s for s in group['short_version_safety'] if s['version']=='10s')
        self.assertGreater(short['action_failure_rate'],0); self.assertFalse(short['safe_for_release'])
        self.assertFalse(group['release_eligible']); self.assertNotEqual(group['upgrade_eligible'],'review_for_Signature')

    def test_wrong_evidence_and_missing_compression_thresholds_cannot_release(self):
        rows,plan=design(); rows[2]['evidence_success']=False
        group=evaluate(declared_real(rows),plan)['groups'][0]
        self.assertFalse(next(s for s in group['short_version_safety'] if s['version']=='10s')['safe_for_release'])
        rows,plan=design(); plan.pop('max_action_failure_delta')
        self.assertTrue(all(s['safe_for_release']=='untested' for s in evaluate(declared_real(rows),plan)['groups'][0]['short_version_safety']))

    def test_bad_gain_types_and_sample_sizes_rejected(self):
        for value in [True,-1,0,float('nan'),float('inf'),'faster']:
            _,plan=design(); plan['minimum_efficiency_gain']={'time_seconds':value}
            with self.subTest(value=value),self.assertRaises(ValueError): validate_plan(plan)
        for value in [True,2.5,'10']:
            _,plan=design(); plan['minimum_participants_per_version']=value
            with self.subTest(value=value),self.assertRaises(ValueError): validate_plan(plan)

    def test_timestamps_require_timezone_and_actual_boolean_gate_fields(self):
        _,plan=design(); plan['workflow']['study_frozen_at']='2026-01-01T00:00:00'
        with self.assertRaisesRegex(ValueError,'timezone'): validate_plan(plan)
        _,plan=design(); plan['workflow']['practicality_checks']['action']=1
        with self.assertRaisesRegex(ValueError,'gate checks'): validate_plan(plan)

if __name__=='__main__': unittest.main()
