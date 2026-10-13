"""Candidate source/schema regression, not full-rule or learner validation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.registry import ROOT, Registry
from scripts.stage_answer_alignment import stage, CORRECTIONS, FIRST_CUTS
from scripts.plan_answer_alignment import TARGET
from core.matcher import match_methods
from core.passage_lesson import validate_order


class AlignmentStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=TemporaryDirectory()
        cls.original_live_commit=Registry().index['source_baseline']['commit']
        cls.report=stage(Path(cls.temporary.name))
        cls.path=Path(cls.report['path'])
        with patch('core.registry.ROOT',cls.path): cls.candidate=Registry()

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def test_complete_source_binding_but_no_acceptance_claim(self):
        self.assertEqual(self.report['source_and_schema_validation']['methods'],82)
        self.assertEqual(self.candidate.index['source_baseline']['commit'],TARGET)
        self.assertFalse(self.report['runtime_switched'])
        self.assertFalse(self.report['release_promotion_applied'])
        self.assertEqual(self.report['student_acceptance'],'pending')
        self.assertEqual(Registry().index['source_baseline']['commit'],self.original_live_commit)

    def test_versions_change_without_rewriting_historical_rules(self):
        live=Registry(snapshot_commit=self.report['from_commit'])
        for mid,m in self.candidate.methods.items():
            self.assertNotEqual(m['version'],live.methods[mid]['version'])
            self.assertEqual(m['primary_role'],live.methods[mid]['primary_role'])
            self.assertEqual(m['output_type'],live.methods[mid]['output_type'])
        self.assertEqual(Registry(snapshot_commit=self.report['from_commit']).methods['R06']['method_type'],'method')
        self.assertEqual(self.candidate.methods['R06']['method_type'],'internal_rule')

    def test_bad_aliases_are_not_copied_to_new_epoch(self):
        for mid,bad in [('R12','定位阅读法'),('R13','顺藤摸瓜'),('R14','顺藤摸瓜'),
                        ('R15','顺藤摸瓜'),('R16','中心思想'),('R17','左顾右盼')]:
            m=self.candidate.methods[mid]
            self.assertNotIn(bad,m['source_name'])
            self.assertTrue(all(bad not in a for a in m['aliases']))
        self.assertEqual(self.candidate.methods['A03']['source_name'],'基础句式锚定法')
        self.assertEqual(self.candidate.methods['A04']['source_name'],'复杂句式模块法')
        self.assertEqual(self.candidate.methods['A05']['source_name'],'长句翻译重构法')

    def test_distinct_course_names_retain_real_definitions_without_activation(self):
        identity=self.candidate.course_identity('顺藤摸瓜（记叙文细节的原命名）')
        self.assertIn('记叙文细节题',identity['full_source'])
        self.assertFalse(identity['identity']['equivalent_to_existing_brand'])
        center=self.candidate.course_identity('中心思想（8.7讲义原名，强版本未激活）')
        self.assertFalse(center['identity']['source_activation'])
        self.assertIn('强版本未验收',center['full_source'])
        with self.assertRaisesRegex(ValueError,'exact course identity'):
            self.candidate.course_identity('顺藤摸瓜=名词追踪')

    def test_corrected_entry_fields_have_one_shared_action_and_stop(self):
        for mid,(_,action,judge,stop) in CORRECTIONS.items():
            with self.subTest(mid=mid):
                m=self.candidate.methods[mid]
                self.assertEqual(m['core_action'],action)
                self.assertEqual(m['four_step_card']['first_cut'],FIRST_CUTS.get(mid,action))
                self.assertEqual(m['practicality_gate']['action'],action)
                self.assertEqual(m['four_step_card']['stop'],stop)
                self.assertEqual(m['practicality_gate']['stop'],stop)
                self.assertFalse(m['student_ready'])

    def test_changed_entries_do_not_keep_old_ready_flags(self):
        for m in self.candidate.methods.values():
            if m['source_alignment']['source_content_changed']:
                self.assertFalse(m['student_ready'])
        self.assertEqual(len(self.report['student_short_form_review_required']),53)
        self.assertEqual(set(self.report['student_short_form_drafts']),{'R01','R02','R06','R09','F01','G01'})

    def test_retired_risk_is_removed_only_in_candidate(self):
        risk='APPLICATION-TRAINING-WORDCOUNT-TENSION'
        self.assertNotIn(risk,{r['risk_id'] for r in self.candidate.risks})
        if self.original_live_commit==self.report['from_commit']:
            self.assertIn(risk,{r['risk_id'] for r in Registry().risks})
        self.assertIn(risk,{r['risk_id'] for r in Registry(snapshot_commit=self.report['from_commit']).risks})

    def test_old_public_course_examples_are_not_current_release_credit(self):
        with patch('core.registry.ROOT',self.path):
            inventory=self.candidate.case_inventory()
            coverage=self.candidate.case_coverage()
            examples=[c for c in inventory.values() if c['status']=='verified_course_example']
            self.assertEqual(len(examples),7)
            self.assertTrue(all(not self.candidate.case_is_current(c) for c in examples))
            self.assertTrue(all(c['source_commit']==self.report['from_commit'] for c in examples))
            self.assertTrue(all(not s['current_epoch_credit'] for m in coverage['methods'] for s in m['slots']))

    def test_paragraph_diagnosis_new_epoch_and_old_full_text_rule_stay_distinct(self):
        q={'question_type':'阅读理解','task_type':'paragraph_main_idea','stem':'Which paragraph summary?',
           'observations':[{'method_id':'R06','reviewed':True,
                            'evidence':[{'field':'stem','start':0,'end':5,'quote':'Which'}]}]}
        self.assertIn('R06',[m['method_id'] for m in match_methods(q,self.candidate)])
        with self.assertRaisesRegex(ValueError,'Full-text method'):
            match_methods(q,Registry(snapshot_commit=self.report['from_commit']))

    def test_auxiliary_fields_do_not_preserve_retired_algorithms(self):
        self.assertNotIn('最多',self.candidate.methods['W05']['visual_formula'])
        self.assertNotIn('挖空复现',self.candidate.methods['A06']['visual_formula'])
        self.assertNotIn('不看选项',self.candidate.methods['R09']['challenge_prompt'])
        self.assertNotIn('同一四格',self.candidate.methods['W03']['transfer_pattern'])
        self.assertIn('decision_tree',self.candidate.methods['G01']['full'])
        self.assertNotIn('原空号走两遍',self.candidate.methods['C01']['full']['source_boundary'])

    def test_cloze_layered_stop_matches_current_source_in_live_and_staged_cards(self):
        for registry in (Registry(),self.candidate):
            for mid in ('C01','C02'):
                with self.subTest(registry=registry.asset_root,method=mid):
                    card=registry.methods[mid]
                    self.assertEqual(card['levels']['L3'],card['stop_rule'])
                    self.assertIn('不强制原空号',card['levels']['L3'])
                    self.assertNotIn('原空号走两遍',card['levels']['L3'])
                    self.assertNotIn('按原空号先做',card['levels']['L3'])

    def test_cloze_generated_resource_uses_current_layered_stop(self):
        import yaml
        for root in (ROOT,self.path):
            for folder in ('gaokao-english','gaokao-objective'):
                cards=yaml.safe_load((root/folder/'generated-methods.yaml').read_bytes())['methods']
                for card in cards:
                    if card['method_id'] in ('C01','C02'):
                        self.assertEqual(card['levels']['L3'],card['stop_rule'])

    def test_staged_cloze_patch_does_not_reuse_archived_prepatch_identity(self):
        from core.registry import load
        from scripts.stage_answer_alignment import SOURCE_PATCH_VERSIONS
        self.assertEqual(SOURCE_PATCH_VERSIONS, {'C01': '1.2.1', 'C02': '1.2.1'})
        for mid in ('C01', 'C02'):
            staged = self.candidate.methods[mid]
            archived = load('method-registry/history/' + mid + '/1.2.0.yaml')
            self.assertEqual(archived['version'], '1.2.0')
            self.assertNotEqual(staged['version'], archived['version'])
            self.assertNotEqual(staged['levels']['L3'], archived['levels']['L3'])
            self.assertEqual(staged['version'], Registry().methods[mid]['version'])
            self.assertEqual(staged['source_alignment']['state'], 'staged_not_live')
            self.assertFalse(staged['student_ready'])
            self.assertEqual(staged['status'], 'candidate')
        old = Registry(snapshot_commit=self.report['from_commit'])
        for mid in set(self.candidate.methods) - set(SOURCE_PATCH_VERSIONS):
            parts = old.methods[mid]['version'].split('.')
            parts[1] = str(int(parts[1]) + 1)
            parts[2] = '0'
            self.assertEqual(self.candidate.methods[mid]['version'], '.'.join(parts))

    def test_projection_does_not_expose_old_student_copy_or_merge_source_names(self):
        guide=(self.path/'student-guides/R09-三步压文.md').read_text(encoding='utf-8')
        self.assertIn('学生首次接触草稿',guide)
        self.assertIn('传播与实用性验收未通过',guide)
        self.assertIn('## 10 秒版',guide)
        self.assertNotIn('不看选项细节',guide)
        skill=(self.path/'gaokao-english/SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('课程原名和品牌名是同一方法',skill)
        self.assertIn('不能把独立课程原名静默合并',skill)
        self.assertTrue((self.path/'gaokao-english/generated-course-identities.yaml').exists())
        pending=(self.path/'student-guides/W03-剧情四格.md').read_text(encoding='utf-8')
        self.assertIn('新版入口复核中',pending)

    def test_all_changed_source_cards_receive_reviewed_boundary_profile(self):
        for m in self.candidate.methods.values():
            if m['source_alignment']['source_content_changed']:
                self.assertTrue(m['source_alignment']['correction_profile_applied'],m['method_id'])

    def test_staging_cannot_issue_a_live_epoch_status(self):
        from answer_engine.frozen_export import FrozenAssetExporter
        with self.assertRaisesRegex(ValueError,'Staged teaching rules'):
            FrozenAssetExporter().status_current_epoch({},self.candidate)

    def test_new_cloze_order_allows_evidence_driven_returns_without_fixed_rounds(self):
        # Synthetic source/order transport only, not English or learner proof.
        items={str(n):{'number':n,'question':{'question_id':str(n),'stem':'program'}} for n in [21,22,23]}
        evidence=[{'field':'stem','start':0,'end':7,'quote':'program'}]
        def visit(n,kind,outcome):
            return {'question_id':str(n),'pass':kind,'outcome':outcome,
                    'transition':'回到program，核本空自己的提示。','evidence':evidence,
                    'execution_ids':['stop' if outcome=='deferred' else 'produced']}
        analyses={qid:{'execution_trace':[{'execution_id':'stop','state':'stopped'},
                                         {'execution_id':'produced','state':'produced'}]} for qid in items}
        review={'reading_mode':None,'steps':[visit(22,1,'deferred'),visit(21,1,'solved'),
                                               visit(22,2,'deferred'),visit(22,2,'solved'),visit(23,1,'solved')]}
        self.assertTrue(validate_order('完形填空',items,review,analyses,self.candidate))
        with self.assertRaises(ValueError):
            validate_order('完形填空',items,review,analyses,Registry(snapshot_commit=self.report['from_commit']))
        review['steps'][3]['execution_ids']=[]
        with self.assertRaisesRegex(ValueError,'own produced evidence action'):
            validate_order('完形填空',items,review,analyses,self.candidate)

    def test_cloze_unresolved_visit_cannot_be_declared_complete(self):
        items={'21':{'number':21,'question':{'question_id':'21','stem':'program'}}}
        s={'question_id':'21','pass':1,'outcome':'deferred','transition':'先暂留program，缺本空提示。',
           'evidence':[{'field':'stem','start':0,'end':7,'quote':'program'}],'execution_ids':['stop']}
        analyses={'21':{'execution_trace':[{'execution_id':'stop','state':'stopped'}]}}
        self.assertFalse(validate_order('完形填空',items,{'reading_mode':None,'steps':[s]},analyses,self.candidate))

    def test_unbound_cloze_policy_cannot_override_old_course_contract(self):
        old=Registry(snapshot_commit=self.report['from_commit'])
        old.index['cloze_order_policy']='evidence_driven_visits'
        with self.assertRaisesRegex(ValueError,'exact source contract'):
            old.cloze_order_policy()


if __name__=='__main__': unittest.main()
