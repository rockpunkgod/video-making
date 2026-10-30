"""Editorial compatibility controls, not claims about a real pupil."""
from copy import deepcopy
from pathlib import Path
import re
import unittest
import yaml

from core.registry import ROOT, Registry
from scripts.generate_assets import build


class BeginnerEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry()
        cls.assets=build(cls.registry)

    def test_all_82_have_real_entry_instead_of_placeholder(self):
        self.assertEqual(len(self.registry.methods),82)
        for mid,m in self.registry.methods.items():
            guide=self.assets[f'student-guides/{mid}-{m["brand_name"]}.md']
            self.assertNotIn('新版入口复核中',guide)
            for section in ['先做这一小步','如果卡住','四步实战卡','10 秒版','30 秒版','90 秒版','反例与挑战']:
                self.assertIn(section,guide,(mid,section))
            support=m['full']['beginner_support']
            for key in ['first_micro_action','prerequisite','if_stuck','example','micro_action_is_not_completion']:
                self.assertTrue(support[key],(mid,key))
                self.assertIn(support[key],guide)

    def test_editorial_revision_does_not_change_semantic_contract(self):
        # This assertion belongs to the copy-only October28 revision. The
        # later source migration has separate explicit compatibility controls.
        registry=Registry(snapshot_commit='1c388a0596b13935ae7c6a1af00834915a8efa33')
        protected=['method_id','brand_name','source_name','aliases','version','question_type',
                   'method_type','role','primary_role','secondary_roles','output_type',
                   'core_action','decision_rule','verification','stop_rule','section_ids',
                   'source_references','cases','status','maturity_status','practical_value',
                   'first_use_test','evaluation','role_correctness','short_version_safety']
        for mid,m in registry.methods.items():
            original=yaml.safe_load((ROOT/f'method-registry/history/{mid}/editorial-before-20261028.yaml').read_text(encoding='utf-8'))
            for key in protected:
                self.assertEqual(m.get(key),original.get(key),(mid,key))
            self.assertEqual(m['full']['presentation_revision'],'2026-10-28.2')
            self.assertEqual(m['full']['summary'],m['core_action']+' '+m['decision_rule'])
            self.assertEqual(m['full']['source_boundary'],m['stop_rule'])

    def test_no_readiness_or_empirical_promotion_from_copy_rewrite(self):
        for mid,m in self.registry.methods.items():
            self.assertFalse(m['student_ready'],mid)
            self.assertEqual(m['status'],'candidate')
            self.assertEqual(m['practical_value'],'Useful')
            self.assertEqual(m['first_use_test']['final_result'],'pending_real_student_test')
            if 'short_version_safety' in m:
                self.assertTrue(all(x['safe_for_release']=='untested' for x in m['short_version_safety']))
            else:
                # Optional metrics absent before this copy-only change must
                # stay absent, not turn into manufactured "passed" records.
                original=yaml.safe_load((ROOT/f'method-registry/history/{mid}/editorial-before-20261028.yaml').read_text(encoding='utf-8'))
                self.assertNotIn('short_version_safety',original)

    def test_short_forms_are_authored_not_action_rule_concatenation(self):
        for mid,m in self.registry.methods.items():
            self.assertNotEqual(m['compact']['10s'],m['core_action']+' '+m['decision_rule'],mid)
            self.assertIn('例如',m['compact']['30s'],mid)
            self.assertIn(m['full']['beginner_support']['short_stop'],m['compact']['30s'])
            for text in [m['entry_copy'],*m['compact'].values()]:
                self.assertIsNone(re.search(r'\b(?:locate|interpret|reduce|decide|verify)\b',text),mid)

    def test_f01_no_difference_means_record_not_omit(self):
        m=self.registry.methods['F01']
        self.assertIn('无区别也记录',m['compact']['10s'])
        self.assertIn('无区分度',m['compact']['30s'])
        self.assertNotIn('维度如实跳过',m['compact']['30s'])
        self.assertIn('三维各一次',m['compact']['30s'])
        self.assertEqual(m['secondary_roles'],[])

    def test_w03_versions_are_teacher_layer_not_beginner_challenge(self):
        m=self.registry.methods['W03']
        guide=self.assets['student-guides/W03-剧情四格.md']
        visible=re.sub(r'<details>.*?</details>','',guide,flags=re.S)
        visible=re.sub(r'<!--.*?-->','',visible,flags=re.S)
        for marker in ['寒8','寒14','PTSD英文','另一版哪两个']:
            self.assertNotIn(marker,visible)
        self.assertIn('寒14',m['decision_rule'])
        self.assertIn('未知',m['challenge_prompt'])
        self.assertIn('教师备查',guide)

    def test_r01_common_two_option_symptom_is_not_a_mandatory_count(self):
        m=self.registry.methods['R01']
        self.assertIn('不是必须',m['four_step_card']['start'])
        self.assertIn('共同核心',m['four_step_card']['start'])
        self.assertIn('间接',m['compact']['10s'])

    def test_r09_and_g01_do_not_turn_framework_into_answer(self):
        for mid in ['R09','G01']:
            m=self.registry.methods[mid]
            self.assertEqual(m['primary_role'],'framework')
            self.assertTrue(any(x in m['compact']['10s'] for x in ['不是答案','不填答案']))
        r09=self.registry.methods['R09']['compact']['90s']
        for marker in ['实际题干','有效首尾','中间段首','全文']:
            self.assertIn(marker,r09)

    def test_admin_state_is_inspectable_but_not_visible_student_copy(self):
        for mid,m in self.registry.methods.items():
            text=self.assets[f'student-guides/{mid}-{m["brand_name"]}.md']
            self.assertIn('当前 student_ready=false',text)
            visible=re.sub(r'<!--.*?-->','',text,flags=re.S)
            self.assertNotIn('student_ready',visible)
            self.assertNotIn('生成来源：Registry',visible)

    def test_legacy_distinct_stops_both_survive_optional_display_adapter(self):
        old=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')
        method=old.methods['G01']
        self.assertNotEqual(method['stop_rule'],method['four_step_card']['stop'])
        guide=build(old)['student-guides/G01-先判空位.md']
        self.assertIn(method['stop_rule'],guide)
        self.assertIn(method['four_step_card']['stop'],guide)

    def test_optional_support_does_not_remove_challenge_for_static_ready_display(self):
        # Synthetic display branch only, never mutate a live readiness flag.
        from unittest.mock import patch
        method=deepcopy(self.registry.methods['R01'])
        method['student_ready']=True
        with patch.dict(self.registry.methods,{'R01':method}):
            guide=build(self.registry)['student-guides/R01-选项加戏.md']
        self.assertIn(method['challenge_prompt'],guide)
        self.assertFalse(self.registry.methods['R01']['student_ready'])

    def test_navigation_exposes_micro_action_without_changing_legacy_yaml_action(self):
        routes=yaml.safe_load(self.assets['references/student-symptoms.yaml'])['routes']
        for row in routes:
            m=self.registry.methods[row['method_id']]
            self.assertEqual(row['first_action'],m['core_action'])
            self.assertIn(m['full']['beginner_support']['first_micro_action'],self.assets['references/student-symptoms.md'])

    def test_result_phrase_is_a_noun_phrase_not_a_broken_verb_join(self):
        for mid,m in self.registry.methods.items():
            for text in [m['entry_copy'],m['compact']['90s']]:
                self.assertNotIn('得到的只判断',text,mid)
                self.assertIn('这一步得到的是',text.replace('这一步得到的只是','这一步得到的是'),mid)

    def test_action_has_a_sentence_boundary_before_result(self):
        for mid,m in self.registry.methods.items():
            text=m['compact']['90s']
            prefix=text.split('这一步得到的',1)[0]
            self.assertTrue(prefix.endswith(('。','？','！','.','!','?')),mid)


if __name__=='__main__':
    unittest.main()
