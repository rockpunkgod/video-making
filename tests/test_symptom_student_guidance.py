"""Obstacle guidance controls, not real trigger precision or learning results."""
import subprocess
import sys
import unittest

from core.registry import ROOT, Registry
from core.matcher import symptom_route, match_methods
from renderers.symptom import render_symptom


class SymptomGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=Registry()

    def test_natural_word_order_variants_route_to_interpreter(self):
        for text in ('看不懂长句','长句看不懂','看不懂句子','句子看不懂','找不到句子主干'):
            with self.subTest(text=text):
                routes=symptom_route('阅读理解',text,self.registry)
                self.assertEqual([row['method_id'] for row in routes],['R11'])
                self.assertEqual(routes[0]['confidence'],'low')

    def test_explicit_denied_obstacle_does_not_override_positive_obstacle(self):
        routes=symptom_route('阅读理解','不是找不到原文，而是看不懂长句',self.registry)
        self.assertEqual([row['method_id'] for row in routes],['R11'])

    def test_punctuation_preserves_specific_grammar_obstacle(self):
        routes=symptom_route('语法填空','不知道，谓语还是非谓语？',self.registry)
        self.assertEqual([row['method_id'] for row in routes],['G12'])

    def test_unspecific_student_request_clarifies_without_method_menu(self):
        text=render_symptom('阅读理解','不会',self.registry)
        self.assertIn('卡点说具体',text)
        self.assertNotIn(self.registry.methods['R12']['brand_name'],text)
        self.assertNotIn('先考虑',text)
        # Existing machine-facing default remains compatible.
        self.assertEqual(symptom_route('阅读理解','不会',self.registry)[0]['method_id'],'R12')

    def test_student_entry_projects_first_action_decision_and_stop_not_definition(self):
        text=render_symptom('阅读理解','看不懂长句',self.registry)
        method=self.registry.methods['R11']
        self.assertIn(method['four_step_card']['first_cut'].split('；')[0],text)
        self.assertIn(method['stop_rule'],text)
        self.assertIn('是否适用还要核题面',text)
        self.assertNotIn('阶段差异核当前与目标',text)
        self.assertNotIn('R11',text)
        self.assertIn('现在不报答案',text)

    def test_paragraph_scope_uses_paragraph_framework_not_whole_text(self):
        text=render_symptom('阅读理解','这段主旨二选一',self.registry)
        self.assertIn(self.registry.methods['R16']['brand_name'],text)
        self.assertNotIn(self.registry.methods['R09']['brand_name'],text)

    def test_role_boundaries_and_cross_type_isolation_remain(self):
        text=render_symptom('七选五','七个选项都能放',self.registry)
        self.assertIn('优先核查的候选范围',text)
        self.assertIn(self.registry.methods['F01']['four_step_card']['judge'],text)
        self.assertNotIn('长句拆骨',text)
        with self.assertRaisesRegex(ValueError,'Unsupported'): render_symptom('听力','不会',self.registry)

    def test_grammar_entry_reduces_knowledge_routes_not_answer_options(self):
        text=render_symptom('语法填空','有提示词不知道怎么变',self.registry)
        self.assertIn('下一知识节点',text)
        self.assertNotIn('优先核查的候选范围',text)

    def test_disjunctive_obstacles_are_not_treated_as_denial(self):
        routes=symptom_route('阅读理解','不是找不到原文就是看不懂长句',self.registry)
        self.assertEqual({row['method_id'] for row in routes},{'R12','R11'})
        text=render_symptom('阅读理解','不是找不到原文就是看不懂长句',self.registry)
        self.assertIn('卡点说具体',text)

    def test_cli_student_mode_is_plain_guidance_and_structured_mode_unchanged(self):
        result=subprocess.run([sys.executable,'-X','utf8','-m','answer_engine','symptom',
                  '阅读理解','看不懂长句','--renderer','student'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('第一刀',result.stdout)
        self.assertFalse(result.stdout.lstrip().startswith('['))


if __name__=='__main__': unittest.main()
