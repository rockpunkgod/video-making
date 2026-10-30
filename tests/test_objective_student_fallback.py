"""Student delivery boundary controls, not English or learner-outcome tests."""
from copy import deepcopy
import json
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from core.question_verification import material_fingerprint
from renderers import render
from tests.test_execution import fixture as execution_fixture
from tests.test_lesson_feedback import fixture as lesson_fixture
from tests import test_terminal_lesson as terminal_fixture


class ObjectiveStudentFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry()
        cls.engine=QuestionAnalyzer(cls.registry)

    def terminal_question(self):
        factory=terminal_fixture.TerminalLessonTests()
        factory.registry=self.registry
        return factory.question()

    def assert_incomplete(self,result):
        for kind in ('student','legacy-wechat'):
            body=render(result,kind,self.registry)
            self.assertEqual(body.count('同学'),1)
            self.assertIn('逐步讲解还没齐',body)
            self.assertIn('暂时不能给你完整解答',body)
            for marker in ('职责产物','外部审阅','审阅结果','置信度','method_id',
                           'reviewer','confidence','R01','R03','R09','整题核验',
                           '实际动作','骨架产物','最后这一题选','当前保留'):
                self.assertNotIn(marker,body)
        self.assertEqual(render(result,'student',self.registry),render(result,'legacy-wechat',self.registry))

    def test_missing_partial_and_unreviewed_lessons_cannot_substitute_audit_for_teaching(self):
        for state in ('missing','partial','unreviewed'):
            with self.subTest(state=state):
                q=self.terminal_question()
                if state=='missing': q.pop('lesson_review')
                elif state=='partial': q['lesson_review']['segments'].pop()
                else: q['lesson_review']['review_status']='unreviewed'
                result=self.engine.analyze(q)
                self.assertEqual(result['answer'],'A')
                self.assertTrue(result['answer_verification']['closed'])
                if state!='missing':
                    self.assertEqual(result['lesson_feedback']['review']['segments'],[])
                self.assert_incomplete(result)

    def test_complete_method_lesson_keeps_exact_segments_order_and_core_answer(self):
        q=lesson_fixture(self.registry)
        before=deepcopy(q)
        result=self.engine.analyze(q)
        expected='同学，我们来分析一下。\n\n'+'\n\n'.join(s['text'] for s in q['lesson_review']['segments'])+'\n\n最后这一题选A。'
        for kind in ('student','legacy-wechat'):
            self.assertEqual(render(result,kind,self.registry),expected)
        self.assertEqual(q,before)

    def test_complete_terminal_lesson_keeps_non_branded_comparison_unchanged(self):
        q=self.terminal_question()
        result=self.engine.analyze(q)
        expected='同学，我们来分析一下。\n\n'+'\n\n'.join(s['text'] for s in q['lesson_review']['segments'])+'\n\n最后这一题选A。'
        for kind in ('student','legacy-wechat'):
            self.assertEqual(render(result,kind,self.registry),expected)

    def test_internal_free_fields_remain_in_machine_exports_and_never_enter_student_text(self):
        q=self.terminal_question()
        q.pop('lesson_review')
        canary='INTERNAL R03 reviewer private-person confidence 0.99 DO NOT TEACH'
        q['student_symptoms']=[canary]
        action=q['action_executions'][0]
        for field in ('concrete_action','decision_rule_check','stop_rule_check','reviewer'):
            action[field]=canary
        action['output']['parts'][0].update(name=canary,value=canary)
        terminal=q['question_verification_review']
        for field in ('concrete_action','stop_rule_check','reviewer'):
            terminal[field]=canary
        for check in terminal['candidate_checks']:
            check.update(decision_rule_check=canary,backfill_check=canary)
        terminal['material_sha256']=material_fingerprint(q)
        result=self.engine.analyze(q)
        before=deepcopy(result)
        # These free diagnostic fields are deliberately retained for auditing.
        result['limitations'].append(canary)
        result['next_action']=canary
        for kind in ('student','legacy-wechat'):
            self.assertNotIn(canary,render(result,kind,self.registry))
        self.assert_incomplete(result)
        for kind in ('structured','content-export'):
            encoded=render(result,kind,self.registry)
            self.assertIn(canary,encoded)
            exported=json.loads(encoded)
            self.assertEqual(exported['answer'],before['answer'])
            self.assertEqual(exported['execution_trace'],before['execution_trace'])
            self.assertEqual(exported['question_verification'],before['question_verification'])

    def test_no_terminal_remains_unresolved_without_fabricated_candidate_teaching(self):
        q=self.terminal_question()
        q.pop('lesson_review')
        q.pop('question_verification_review')
        result=self.engine.analyze(q)
        self.assertIsNone(result['answer'])
        self.assertFalse(result['answer_verification']['closed'])
        self.assert_incomplete(result)
        for kind in ('student','legacy-wechat'):
            self.assertIn('决定答案的题面依据还没核清',render(result,kind,self.registry))
            self.assertNotIn('Synthetic',render(result,kind,self.registry))

    def test_stopped_action_hides_legacy_closed_answer_and_future_plan_without_changing_it(self):
        q=execution_fixture()
        q['action_executions']=q['action_executions'][:2]
        q['action_executions'][1].update(stop_applied=True,output=None)
        result=self.engine.analyze(q)
        self.assertEqual(result['answer'],'A')  # Legacy relations remain compatible.
        before=deepcopy(result)
        self.assert_incomplete(result)
        for kind in ('student','legacy-wechat'):
            body=render(result,kind,self.registry)
            self.assertIn('先停下来',body)
            self.assertIn('现在先不报答案',body)
            self.assertNotIn('先核对一个入口',body)
            self.assertNotIn('program-only observable action',body)
        self.assertEqual(result,before)

    def test_terminal_stop_also_requires_stopping_before_any_student_answer(self):
        q=self.terminal_question()
        q.pop('lesson_review')
        q['question_verification_review']['stop_applied']=True
        result=self.engine.analyze(q)
        self.assertEqual(result['question_verification']['state'],'stopped')
        self.assert_incomplete(result)
        self.assertIn('先停下来',render(result,'student',self.registry))

    def test_failed_or_unresolved_verification_does_not_offer_a_new_method(self):
        for verdict in ('rejects','unresolved'):
            with self.subTest(verdict=verdict):
                q=execution_fixture()
                q['action_executions'][-1]['output']['verdict']=verdict
                result=self.engine.analyze(q)
                self.assertIsNone(result['answer'])
                self.assert_incomplete(result)
                for kind in ('student','legacy-wechat'):
                    body=render(result,kind,self.registry)
                    self.assertIn('还没有通过核对',body)
                    self.assertNotIn('先核对一个入口',body)

    def test_all_objective_types_without_lesson_get_status_rather_than_unexecuted_methods(self):
        for question_type in ('阅读理解','七选五','完形填空','语法填空'):
            with self.subTest(question_type=question_type):
                q={'question_id':'synthetic-status-only','question_type':question_type,
                   'stem':'program-only input','passage':'alpha beta gamma'}
                result=self.engine.analyze(q)
                before=deepcopy(result)
                self.assert_incomplete(result)
                for kind in ('student','legacy-wechat'):
                    body=render(result,kind,self.registry)
                    self.assertIn('现在先不报答案',body)
                    self.assertNotIn('program-only input',body)
                    self.assertNotIn('第一刀',body)
                self.assertEqual(result,before)


if __name__=='__main__':
    unittest.main()
