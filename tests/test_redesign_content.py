"""Synthetic transport checks and source immutability, not learner certification."""
from copy import deepcopy
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from answer_engine.frozen_export import FrozenAssetExporter
from creative_os.moves import load_catalog, student_cards, validate_catalog
from scripts.move_hit_rate import prepare_samples, summarize
from student_pov.experience_qa import tone_lint
from student_pov.qa import frozen_answer_binding, lint_copy
from student_pov.speech import narration_coverage, speech_lint
from tests.test_execution import fixture
from video_contracts import sha


class RedesignContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.catalog = load_catalog(registry=cls.registry)
        q = fixture()
        q['options']['C'] = q['options'].pop('A')
        for relation in q['relations']:
            if relation['candidate'] == 'A':
                relation['candidate'] = 'C'
        for action in q['action_executions']:
            if action['output'].get('candidate') == 'A':
                action['output']['candidate'] = 'C'
        analysis = QuestionAnalyzer(cls.registry).analyze(q)
        cls.request = {'question': q, 'analysis': analysis,
            'methods': [deepcopy(cls.registry.methods[mid]) for mid in analysis['method_versions']],
            'reviews': [{'question_id': q['question_id'], 'input_sha256': sha(q),
                'analysis_sha256': sha(analysis), 'reviewer_kind': 'AI',
                'reviewer': 'SYNTHETIC CONTENT TEST', 'evaluation_phase': 'post_reveal'}],
            'withdrawals': [], 'evaluation_phase': 'post_reveal',
            'source': {'usage_status': 'internal_only', 'redistribution_status': 'redistribution_not_verified',
                       'source_reference': 'synthetic test', 'attribution_text': 'SYNTHETIC'}}
        cls.exporter = FrozenAssetExporter()
        cls.bundle = cls.exporter.export(cls.request)
        cls.status = cls.exporter.status(cls.request)

    def beats(self, text):
        return [{'vo': {'text': text}, 'screen': {'copy': []}}]

    def test_closed_frozen_answer_can_be_spoken_without_promoting_release(self):
        binding = frozen_answer_binding(self.bundle, self.status)
        _, errors = tone_lint(self.beats('所以选 C。'), 'decider', False,
                            frozen_bundle=self.bundle, frozen_status=self.status)
        self.assertEqual(binding['answer'], 'C')
        self.assertFalse(binding['public_render_ready'])
        self.assertEqual(errors, [])

    def test_wrong_answer_and_marketing_still_fail(self):
        for text in ('所以选 A。', '我选 A。', '答案是 A。', '就是 A。', '一招秒杀，所以选 C。'):
            _, errors = tone_lint(self.beats(text), 'decider', False,
                                frozen_bundle=self.bundle, frozen_status=self.status)
            self.assertTrue(errors)

    def test_compiler_explicit_full_solution_preserves_frozen_answer(self):
        from pedagogy import compile_plan, validate_plan
        selection = frozen_answer_binding(self.bundle, self.status)['selections'][0]
        before = sha(self.bundle)
        legacy = compile_plan(self.bundle, self.status, selection, mode='worked_example')
        self.assertFalse(legacy['answer_scope']['may_output_final_answer'])
        plan = compile_plan(self.bundle, self.status, selection, mode='worked_example',
                            answer_scope='full_solution')
        self.assertEqual(plan['answer_scope']['answer'], 'C')
        self.assertTrue(plan['answer_scope']['may_output_final_answer'])
        self.assertEqual(validate_plan(plan, self.bundle, self.status)['status'], 'PASS')
        self.assertFalse(plan['public_render_ready'])
        self.assertEqual(before, sha(self.bundle))
        from tests.test_pedagogy import reseal_plan
        forged = deepcopy(plan)
        forged['answer_scope']['answer'] = 'B'
        with self.assertRaises(ValueError):
            validate_plan(reseal_plan(forged), self.bundle, self.status)

    def test_compiler_does_not_borrow_closure_from_unselected_actions(self):
        from pedagogy import compile_plan
        selection = frozen_answer_binding(self.bundle, self.status)['selections'][0]
        partial = {**selection, 'action_ids': selection['action_ids'][:1]}
        for chosen, current, mode in ((partial, self.status, 'worked_example'),
                                     (selection, None, 'worked_example'),
                                     (selection, self.status, 'first_touch')):
            with self.assertRaises(ValueError):
                compile_plan(self.bundle, current, chosen, mode=mode, answer_scope='full_solution')

    def test_answer_binding_does_not_override_role_of_helper_action(self):
        self.assertIn('role_overclaim', lint_copy('找到这里就能选。', 'locator', True))
        _, errors = tone_lint(self.beats('所以选 C。'), 'reducer', False)
        self.assertIn('ANSWER_SCOPE_OVERCLAIM', errors)

    def test_unclosed_or_missing_current_status_cannot_claim_answer(self):
        with self.assertRaises(ValueError):
            frozen_answer_binding(self.bundle, None)
        request = deepcopy(self.request)
        request['question']['relations'] = []
        request['question']['action_executions'] = request['question']['action_executions'][:1]
        request['analysis'] = QuestionAnalyzer(self.registry).analyze(request['question'])
        request['reviews'][0]['input_sha256'] = sha(request['question'])
        request['reviews'][0]['analysis_sha256'] = sha(request['analysis'])
        bundle = self.exporter.export(request)
        with self.assertRaises(ValueError):
            frozen_answer_binding(bundle, self.exporter.status(request))

    def test_method_name_position_and_reminders_are_editorial(self):
        self.assertNotIn('method_name_before_value', lint_copy('今天学习一个方法。', 'decider', False))
        flags, errors = tone_lint(self.beats('现在还不能选。'), 'decider', False)
        self.assertIn('redundant_result_reminder', flags)
        self.assertEqual(errors, [])

    def test_catalog_does_not_modify_truth_or_silently_merge_roles(self):
        before = sha(self.registry.methods)
        validate_catalog(self.catalog, registry=self.registry)
        self.assertEqual(before, sha(self.registry.methods))
        title = next(row for row in self.catalog['entries'] if row['name'] == '标题放回全文')
        self.assertEqual({row['method_id']: row['role'] for row in title['methods']},
                         {'R16': 'framework', 'R09': 'framework', 'R06': 'decider'})
        self.assertEqual(self.catalog['tiers']['R06'], 'sub_action')
        self.assertEqual(self.catalog['tiers']['G09'], 'knowledge')
        self.assertFalse(self.catalog['runtime_aliases_changed'])

    def test_stale_catalog_field_binding_is_rejected(self):
        value = deepcopy(self.catalog)
        value['entries'][0]['field_bindings']['action_3s'][0]['sha'] = '0' * 64
        with self.assertRaises(ValueError):
            validate_catalog(value, registry=self.registry)

    def test_student_cards_only_contain_five_fields_and_display_names(self):
        cards = student_cards(self.catalog)
        self.assertEqual(len(cards), 20)
        for path, text in cards.items():
            self.assertNotRegex(path, r'[RFCGAW]\d{2}')
            self.assertNotIn('student_ready', text)
            self.assertNotIn('validated', text)
            self.assertNotIn('Registry', text)

    def samples(self):
        inventory = []
        for category in {row['question_type'] for row in self.catalog['entries'] if row['first_batch']}:
            for index in range(10):
                q = {'question_id': f'synthetic-{category}-{index}', 'question_type': category,
                     'stem': 'SYNTHETIC transport only'}
                inventory.append({'question_id': q['question_id'], 'question_type': category,
                    'exam_id': str(index), 'question_sha': sha(q), 'question': q,
                    'input_file': 'synthetic', 'input_file_sha': '0' * 64,
                    'input_index': index, 'source_sha': '0' * 64})
        return prepare_samples(self.catalog, inventory)

    def test_unknown_statistics_do_not_turn_into_zero_or_ready(self):
        report = summarize(self.catalog, self.samples(), verify_sources=False)
        for row in report['moves']:
            self.assertEqual(row['evaluation']['sampled'], 10)
            self.assertIsNone(row['evaluation']['hits'])
            self.assertIsNone(row['evaluation']['hit_rate'])
            self.assertEqual(row['filming_state'], 'HOLD_MISSING_ANNOTATIONS')

    def test_sample_binding_and_human_audit_expire_on_change(self):
        samples = self.samples()
        sample = samples['samples'][0]
        sample['annotation'] = {'applicable': True, 'hit': True, 'annotator': 'SYNTHETIC AI',
            'kind': 'ai', 'evidence_refs': ['synthetic'], 'notes': 'Synthetic audit binding test'}
        sample['human_audit'] = {'reviewer': 'SYNTHETIC HUMAN', 'annotation_sha': sha(sample['annotation']),
                                'agrees': True, 'notes': 'Synthetic only'}
        sample['annotation']['hit'] = False
        with self.assertRaises(ValueError):
            summarize(self.catalog, samples, verify_sources=False)
        samples = self.samples()
        samples['samples'][0]['source']['question']['stem'] = 'changed'
        with self.assertRaises(ValueError):
            summarize(self.catalog, samples, verify_sources=False)

    def test_speech_lint_reports_style_without_rewriting_source(self):
        text = '这是一句带着许多修饰而且还在不断往后解释的长句；继续解释。'
        report = speech_lint(text)
        self.assertFalse(report['natural_speech_certified'])
        self.assertEqual({row['code'] for row in report['warnings']},
                         {'SPOKEN_SENTENCE_OVER_18', 'SEMICOLON_IN_SPEECH'})

    def test_voice_coverage_uses_union_and_exposes_long_silence(self):
        report = narration_coverage([[0, 3], [2, 5], [12, 15]], 15)
        self.assertEqual(report['voiced_seconds'], 8)
        self.assertIn('SILENCE_OVER_6_SECONDS', report['warnings'])
        self.assertFalse(report['actual_delivery_pass'])
        estimated = narration_coverage([[0, 10]], 15, timing_basis='estimated')
        self.assertFalse(estimated['actual_delivery_pass'])
        with self.assertRaises(ValueError):
            narration_coverage([[0, 16]], 15)


if __name__ == '__main__':
    unittest.main()
