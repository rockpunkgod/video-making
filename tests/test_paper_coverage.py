"""Paper scan stage tests use existing course and synthetic program fixtures only."""
from copy import deepcopy
import unittest
from jsonschema import ValidationError
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.registry import Registry,validate_schema
from tests.test_engine import grammar_review
from tests.test_execution import fixture


class PaperCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.analyzer=PaperAnalyzer(QuestionAnalyzer(Registry()))

    def paper(self,*questions): return self.analyzer.analyze({'paper_id':'program-stage-audit','questions':list(questions)})

    def test_raw_suggestion_is_not_verified_or_typical(self):
        q=grammar_review(); q.pop('observations'); q.pop('relations')
        out=self.paper(q); stages=out['method_coverage']['G01']
        self.assertEqual(out['method_counts']['G01'],1)
        self.assertEqual(stages['potential_question_ids'],[q['question_id']])
        self.assertTrue(all(not value for key,value in stages.items() if key!='potential_question_ids'))
        self.assertEqual(out['typical_method_candidates'],[])

    def test_reviewed_decision_is_not_reported_as_produced_action(self):
        q=grammar_review(); out=self.paper(q); stages=out['method_coverage']['G09']
        self.assertEqual(stages['verified_trigger_question_ids'],[q['question_id']])
        self.assertEqual(stages['reviewed_decision_question_ids'],[q['question_id']])
        self.assertEqual(stages['produced_question_ids'],[])
        self.assertEqual(stages['case_candidate_question_ids'],[q['question_id']])
        self.assertEqual(out['typical_method_candidates'],['G09'])

    def test_closed_question_does_not_promote_unused_verified_helpers(self):
        q=fixture(); q.pop('action_executions'); out=self.paper(q)
        self.assertTrue(out['questions'][0]['content_eligible'])
        self.assertEqual(out['typical_method_candidates'],['R01'])
        for mid in ('R12','R11','R17'):
            self.assertEqual(out['method_coverage'][mid]['verified_trigger_question_ids'],[q['question_id']])
            self.assertEqual(out['method_coverage'][mid]['case_candidate_question_ids'],[])

    def test_produced_auxiliary_roles_can_be_case_candidates_not_deciders(self):
        q=fixture(); out=self.paper(q)
        for mid in ('R12','R11','R01','R17'):
            stages=out['method_coverage'][mid]
            self.assertEqual(stages['produced_question_ids'],[q['question_id']])
            self.assertEqual(stages['case_candidate_question_ids'],[q['question_id']])
            if mid!='R01': self.assertEqual(stages['reviewed_decision_question_ids'],[])
        self.assertEqual(out['typical_method_candidates'],['R01','R11','R12','R17'])

    def test_failed_verification_withdraws_all_case_candidates(self):
        q=fixture(); q['action_executions'][-1]['output']['verdict']='rejects'
        out=self.paper(q)
        self.assertEqual(out['recommendations'],[]); self.assertEqual(out['typical_method_candidates'],[])
        self.assertTrue(out['method_coverage']['R01']['reviewed_decision_question_ids'])
        self.assertTrue(all(not s['case_candidate_question_ids'] for s in out['method_coverage'].values()))

    def test_rank_uses_own_eligible_cases_not_raw_frequency(self):
        reviewed=grammar_review(); reviewed2=deepcopy(reviewed); reviewed2['question_id']='second-course-record'
        raw=[]
        for i in range(3):
            q=deepcopy(reviewed); q['question_id']='raw-program-'+str(i); q.pop('relations'); q.pop('observations'); raw.append(q)
        out=self.paper(reviewed,reviewed2,*raw)
        self.assertEqual(out['method_counts']['G01'],5)
        self.assertEqual(out['method_counts']['G09'],2)
        self.assertEqual(out['typical_method_candidates'],['G09'])
        self.assertEqual(out['method_coverage']['G09']['case_candidate_question_ids'],[reviewed['question_id'],reviewed2['question_id']])

    def test_later_stop_blocks_earlier_produced_helper_from_typical_rank(self):
        q=fixture(); first=deepcopy(q['action_executions'][0]); stopped=deepcopy(first)
        stopped.update(execution_id='loc-stop',input_artifact_ids=[],stop_applied=True,output=None)
        q['action_executions']=[first,stopped]; out=self.paper(q)
        self.assertTrue(out['questions'][0]['content_eligible'])
        self.assertEqual(out['method_coverage']['R12']['produced_question_ids'],[q['question_id']])
        self.assertEqual(out['method_coverage']['R12']['case_candidate_question_ids'],[])
        self.assertEqual(out['typical_method_candidates'],['R01'])

    def test_schema_keeps_legacy_projection_and_requires_new_version_stages(self):
        out=self.paper(grammar_review()); self.assertEqual(out['schema_version'],'1.1.0')
        legacy=deepcopy(out); legacy['schema_version']='1.0.0'; legacy.pop('method_coverage'); legacy.pop('typical_method_candidates')
        validate_schema('paper-analysis',legacy)
        legacy['schema_version']='1.1.0'
        with self.assertRaises(ValidationError): validate_schema('paper-analysis',legacy)


if __name__=='__main__': unittest.main()
