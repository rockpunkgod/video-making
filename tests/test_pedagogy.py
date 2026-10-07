"""Synthetic program controls; no invented real exam/learner evidence."""
from copy import deepcopy
from pathlib import Path
import ast
import json
import tempfile
import unittest
from unittest.mock import patch

from answer_engine.frozen_export import FrozenAssetExporter
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from tests.test_execution import fixture, action, span, seven_chain_fixture
from video_contracts import ROOT, pointer, seal, sha, write
from pedagogy import (compile_plan, validate_plan, inspect_historical,
                      copy_projection, motion_projection, validate_handoff)
from pedagogy.compiler import plan_semantics
from pedagogy.matrix import golden_matrix
from pedagogy.policy import disclosure, claim_lint


def reseal_plan(plan):
    plan = deepcopy(plan)
    plan['plan_sha'] = sha(plan_semantics(plan))
    plan['plan_id'] = 'pedagogy:' + plan['plan_sha']
    return seal(plan)


class PedagogyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.engine = QuestionAnalyzer(cls.registry)

    def assets(self, mid='R12', case=None, unknown_boundary=False, risk=None, defer_caveats=True):
        q = fixture()
        if mid == 'F01':
            q = seven_chain_fixture()
            ids = ['group-sentence']
        elif mid == 'G01':
            q.update(question_type='语法填空', stem='SYNTHETIC slot (program-hint)',
                given_word='program-hint', requested_chain=['G01'], relations=[],
                observations=[{'method_id': m, 'evidence': [span()], 'reviewed': True}
                              for m in ['G01', 'G09']])
            q['action_executions'] = [action('route', 'G01', 'framework',
                {'kind': 'route_selection', 'node_ids': ['with_hint', 'noun']})]
            ids = ['route']
        else:
            ids = ['loc']
        method_stop = self.registry.methods[mid]['stop_rule']
        for a in q['action_executions']:
            if a['method_id'] == mid:
                a['stop_rule_check'] = 'SYNTHETIC current action Stop' if unknown_boundary else method_stop
        analysis = self.engine.analyze(q)
        review = {'question_id': q['question_id'], 'input_sha256': sha(q),
            'analysis_sha256': sha(analysis), 'reviewer_kind': 'AI',
            'reviewer': 'SYNTHETIC PROGRAM CONTROL ONLY', 'evaluation_phase': 'post_reveal',
            'method_id': mid, 'method_version': self.registry.methods[mid]['version']}
        if case:
            review['case_type'] = case
            if case in ('counterexample', 'boundary'):
                review['reviewed_claims'] = {case: 'SYNTHETIC reviewed ' + case + ' assertion'}
        methods = [deepcopy(self.registry.methods[m]) for m in analysis['method_versions']]
        mi = next(i for i, m in enumerate(methods) if m['method_id'] == mid)
        # Explicit SYNTHETIC risk credentials keep the positive test genuinely
        # within the budget. No real asset receives these fabricated controls.
        if defer_caveats:
            annotations = []
            for field in ('anti_rule', 'failure_cases', 'cannot_replace'):
                value = methods[mi][field]
                paths = [(field, value)] if isinstance(value, str) else [
                    (field + '/' + str(i), text) for i, text in enumerate(value)]
                for suffix, text in paths:
                    annotations.append({'source_pointer': '/methods/' + str(mi) + '/' + suffix,
                        'item_sha': sha(text),
                        'risk': {'frequency': 'low', 'severity': 'low', 'current_relevance': 'low'},
                        'rationale': 'SYNTHETIC risk control ONLY; not a real disclosure assessment'})
            if 'stop' in methods[mi].get('four_step_card', {}):
                annotations.append({'source_pointer': '/methods/' + str(mi) + '/four_step_card/stop',
                    'item_sha': sha(methods[mi]['four_step_card']['stop']),
                    'risk': {'frequency': 'low', 'severity': 'low', 'current_relevance': 'low'},
                    'rationale': 'SYNTHETIC risk control ONLY; not a real disclosure assessment'})
            review['pedagogy_risk_annotations'] = annotations
        if risk:
            review.setdefault('pedagogy_risk_annotations', []).append({'source_pointer': '/methods/' + str(mi) + '/stop_rule',
                'item_sha': sha(method_stop), 'risk': risk,
                'rationale': 'SYNTHETIC disclosure assessment; not a real risk measurement'})
        req = {'question': q, 'analysis': analysis, 'methods': methods, 'reviews': [review],
            'withdrawals': [], 'evaluation_phase': 'post_reveal',
            'source': {'usage_status': 'internal_only', 'redistribution_status': 'unconfirmed',
                       'source_reference': 'SYNTHETIC PROGRAM ONLY', 'attribution_text': 'SYNTHETIC'}}
        exporter = FrozenAssetExporter()
        return exporter.export(req, 'synthetic'), exporter.status(req, 'synthetic'), {'method_id': mid, 'action_ids': ids}

    def plan(self, mid='R12', **kwargs):
        b, s, selection = self.assets(mid)
        if mid == 'R12':
            kwargs.setdefault('fields', {'memory_phrase': '/methods/0/four_step_card/first_cut'})
        return compile_plan(b, s, selection, generated_at='one', **kwargs), b, s

    def test_readonly_repeat_hash_and_core_import_isolation(self):
        b, s, selection = self.assets()
        before = sha([b, s])
        tracked = [p for folder in ('core', 'method-registry', 'renderers', 'cases')
                   for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        material = {str(p): p.read_bytes() for p in tracked}
        with patch.object(QuestionAnalyzer, 'analyze', side_effect=AssertionError('must not solve')):
            a = compile_plan(b, s, selection, generated_at='one')
            c = compile_plan(b, s, selection, generated_at='two')
            validate_plan(a, b, s)
        self.assertEqual(before, sha([b, s]))
        self.assertEqual(a['plan_sha'], c['plan_sha'])
        self.assertEqual(a['content_sha'], c['content_sha'])
        self.assertNotEqual(a['envelope_sha'], c['envelope_sha'])
        self.assertEqual(material, {str(p): p.read_bytes() for p in tracked})
        for p in (ROOT / 'pedagogy').glob('*.py'):
            tree = ast.parse(p.read_text(encoding='utf-8'))
            names = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(name.startswith(('core', 'renderers', 'answer_engine')) for name in names))

    def test_first_touch_four_parts_and_guard_stay_bound(self):
        p, b, s = self.plan()
        self.assertEqual(p['availability']['status'], 'READY')
        self.assertEqual(len(p['boundaries']['tell_now']), 1)
        self.assertTrue(p['symptom'] and p['first_signal'] and p['first_action'] and p['memory_phrase'])
        self.assertEqual(p['role'], 'locator')
        self.assertEqual(p['answer_scope']['upstream_answer'], b['analysis']['answer'])
        self.assertIsNone(p['answer_scope']['answer'])
        self.assertFalse(p['answer_scope']['may_output_final_answer'])
        self.assertEqual(p['semantic_review']['level'], 'ai_reviewed')
        self.assertFalse(p['semantic_review']['independent_human_certified'])
        self.assertFalse(p['public_render_ready'])
        self.assertFalse(p['compression_audit']['semantic_truth_certification'])
        self.assertEqual(p['truth_guard']['method_maturity'], b['methods'][0]['status'])
        self.assertTrue(validate_plan(p, b, s)['consumption_allowed'])

    def test_resealed_answer_role_stop_evidence_certainty_and_claim_edits_fail(self):
        p, b, s = self.plan()
        edits = [lambda v: v['answer_scope'].update(answer='A'),
                 lambda v: v.update(role='decider'),
                 lambda v: v['boundaries'].update(tell_now=[]),
                 lambda v: v['evidence_refs'].append({'asset_id': b['asset_id'], 'pointer': '/unowned', 'sha': '0' * 64}),
                 lambda v: v['working_rule'].update(certainty='certain'),
                 lambda v: v['truth_guard'].update(method_maturity='validated'),
                 lambda v: v['semantic_review'].update(level='human_certified', independent_human_certified=True),
                 lambda v: v['first_action'].update(text='找到原句就能选答案'),
                 lambda v: v['public_claims'][0].update(text='做到这里答案就是A')]
        for edit in edits:
            candidate = deepcopy(p)
            edit(candidate)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_plan(reseal_plan(candidate), b, s)

    def test_unknown_caveat_remains_now_and_overload_blocks_handoff(self):
        b, s, selection = self.assets(unknown_boundary=True, defer_caveats=False)
        p = compile_plan(b, s, selection, fields={'memory_phrase': '/methods/0/four_step_card/first_cut'})
        self.assertEqual(p['availability']['status'], 'HOLD')
        self.assertEqual(p['cognitive_load']['status'], 'PEDAGOGY_OVERLOAD')
        self.assertGreaterEqual(len(p['boundaries']['tell_now']), 2)
        self.assertEqual(p['boundaries']['tell_later'], [])
        self.assertIn('PEDAGOGY_OVERLOAD:primary_boundary', p['availability']['blockers'])
        self.assertEqual(p['public_claims'], [])
        with self.assertRaises(ValueError):
            copy_projection(p, b, s)

    def test_bound_low_risk_can_defer_but_cannot_erase(self):
        risk = {'frequency': 'low', 'severity': 'low', 'current_relevance': 'low'}
        b, s, selection = self.assets(unknown_boundary=True, risk=risk)
        p = compile_plan(b, s, selection, fields={'memory_phrase': '/methods/0/four_step_card/first_cut'})
        self.assertEqual(p['availability']['status'], 'READY')
        self.assertTrue(any(r['pointer'].endswith('/stop_rule')
                            for item in p['boundaries']['tell_later'] for r in item['source_refs']))
        self.assertTrue(p['boundaries']['tell_later'][0]['risk_assessment_refs'])
        self.assertTrue(any(x['still_exists'] and x['disclosure_tier'] == 'TELL_LATER'
                            for x in p['compression_audit']['omitted']))
        v = deepcopy(p)
        v['boundaries']['tell_later'] = []
        with self.assertRaises(ValueError):
            validate_plan(reseal_plan(v), b, s)

    def test_risk_finite_unknown_and_severe_rare_are_conservative(self):
        for relevance in ('low', 'medium', 'high', 'unknown'):
            tier, _ = disclosure({'frequency': 'unknown', 'severity': 'unknown', 'current_relevance': relevance})
            self.assertEqual(tier, 'TELL_NOW')
        tier, _ = disclosure({'frequency': 'low', 'severity': 'high', 'current_relevance': 'low'})
        self.assertEqual(tier, 'TELL_NOW')
        with self.assertRaises(ValueError):
            disclosure({'frequency': 'medium', 'severity': 8.73, 'current_relevance': 'low'})

    def test_engine_metadata_is_not_a_student_rule(self):
        p, b, s = self.plan()
        self.assertTrue(p['boundaries']['engine_only'])
        self.assertFalse(any('R12' in c['text'] or 'review:' in c['text'] for c in p['public_claims']))
        v = deepcopy(p)
        v['first_action']['text'] = 'decider / review:internal'
        with self.assertRaises(ValueError):
            validate_plan(reseal_plan(v), b, s)

    def test_no_counterexample_transfer_boundary_or_hard_without_real_bound_case(self):
        for mode in ('counterexample', 'transfer', 'boundary', 'hard_case'):
            p, b, s = self.plan(mode=mode)
            with self.subTest(mode=mode):
                self.assertEqual(p['availability']['status'], 'UNAVAILABLE_EVIDENCE_GAP')
                self.assertEqual(p['public_claims'], [])
                with self.assertRaises(ValueError):
                    motion_projection(p, b, s)

    def test_explicit_synthetic_case_modes_are_supported_without_answer_upgrade(self):
        for mode, kind in [('counterexample', 'counterexample'), ('boundary', 'boundary'),
                           ('transfer', 'transfer'), ('hard_case', 'hard')]:
            b, s, selection = self.assets(case=kind)
            p = compile_plan(b, s, selection, mode=mode)
            with self.subTest(mode=mode):
                self.assertEqual(p['availability']['status'], 'READY')
                self.assertFalse(p['answer_scope']['may_output_final_answer'])
                self.assertTrue(validate_plan(p, b, s)['consumption_allowed'])
                if kind in ('boundary', 'counterexample'):
                    self.assertTrue(any(x['kind'] == 'case' for x in p['student_steps']))

    def test_reducer_cannot_claim_decision_and_g01_cannot_claim_a_word(self):
        for mid, text in [('F01', '做到这里答案就是A'), ('G01', '所以填具体词X')]:
            p, b, s = self.plan(mid, mode='worked_example')
            with self.subTest(mid=mid):
                self.assertEqual(p['availability']['status'], 'READY')
                self.assertIsNone(p['answer_scope']['answer'])
                self.assertTrue(claim_lint(text, p['role']))
                v = deepcopy(p)
                v['judgment_point']['text'] = text
                with self.assertRaises(ValueError):
                    validate_plan(reseal_plan(v), b, s)

    def test_borrowed_method_assertion_dangling_evidence_and_free_copy_rejected(self):
        b, s, selection = self.assets()
        with self.assertRaises(ValueError):
            compile_plan(b, s, selection, fields={'first_action': '/methods/1/core_action'})
        with self.assertRaises(ValueError):
            compile_plan(b, s, selection, fields={'first_action': {'text': 'new rule'}})
        for path in ('/methods/0/primary_role', '/methods/0/version', '/methods/0/brand_name'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                compile_plan(b, s, selection, fields={'first_action': path})
        with self.assertRaises(ValueError):
            compile_plan(b, s, selection, extra_boundary_refs=['/analysis/answer'])
        with self.assertRaises(ValueError):
            compile_plan(b, s, {'method_id': 'R12', 'action_ids': ['meaning']})

    def test_current_status_missing_withdrawn_or_rights_changed_blocks_reload(self):
        p, b, s = self.plan()
        self.assertFalse(inspect_historical(p)['consumption_allowed'])
        for state in ('WITHDRAWN', 'SUPERSEDED', 'STALE', 'BLOCKED', 'INCOMPLETE'):
            changed = seal({**s, 'effective_status': state})
            with self.subTest(state=state), self.assertRaises(ValueError):
                copy_projection(p, b, changed)
        with self.assertRaises(ValueError):
            validate_plan(p, b, None)
        changed = seal({**s, 'source_sha': '0' * 64})
        with self.assertRaises(ValueError):
            validate_plan(p, b, changed)

    def test_handoff_is_lightweight_bound_and_resealed_copy_edits_fail(self):
        p, b, s = self.plan()
        for factory in (copy_projection, motion_projection):
            handoff = factory(p, b, s)
            self.assertEqual(handoff['plan_sha'], p['plan_sha'])
            self.assertNotIn('methods', handoff)
            self.assertNotIn('analysis', handoff)
            self.assertFalse(handoff['public_render_ready'])
            self.assertEqual(validate_handoff(handoff, p, b, s)['status'], 'PASS')
            changed = deepcopy(handoff)
            changed['first_action' if factory is copy_projection else 'action_object']['text'] = 'new teaching rule'
            with self.assertRaises(ValueError):
                validate_handoff(seal(changed), p, b, s)

    def test_six_by_three_matrix_never_fills_missing_methods(self):
        b, s, selection = self.assets('G01')
        matrix = golden_matrix([{'bundle': b, 'status': s, 'selection': selection}])
        self.assertEqual(len(matrix['rows']), 18)
        self.assertTrue(all(r['status'] == 'UNAVAILABLE_EVIDENCE_GAP'
                            for r in matrix['rows'] if r['method_id'] != 'G01'))
        self.assertEqual(next(r['status'] for r in matrix['rows']
            if r['method_id'] == 'G01' and r['mode'] == 'boundary'), 'UNAVAILABLE_EVIDENCE_GAP')
        self.assertFalse(matrix['public_render_ready'])

    def test_raw_analysis_is_not_a_frozen_input_and_invalid_duration_is_blocked(self):
        b, s, selection = self.assets()
        with self.assertRaises(Exception):
            compile_plan(b['analysis'], s, selection)
        for target in (True, 0, -1, float('inf'), float('nan')):
            with self.subTest(target=target), self.assertRaises(ValueError):
                compile_plan(b, s, selection, duration_target=target)

    def test_student_model_stop_covers_every_required_current_boundary(self):
        b, s, selection = self.assets('G01', unknown_boundary=True)
        p = compile_plan(b, s, selection, mode='worked_example')
        self.assertEqual(p['student_model']['stop'], p['boundaries']['tell_now'])
        self.assertGreaterEqual(len(p['student_model']['stop']), 2)
        self.assertTrue(any(x['current_action_stop'] for x in p['student_model']['stop']))
        altered = deepcopy(p)
        altered['student_model']['stop'] = [x for x in altered['student_model']['stop']
                                            if not x['current_action_stop']]
        with self.assertRaises(ValueError):
            validate_plan(reseal_plan(altered), b, s)
        cp = copy_projection(p, b, s)
        self.assertEqual(cp['student_model']['stop'], cp['must_show_boundary'])

    def test_all_existing_caveats_default_to_unknown_now_without_opt_in(self):
        b, s, selection = self.assets('G01', defer_caveats=False)
        fields = {'memory_phrase': '/methods/0/four_step_card/first_cut'}
        p = compile_plan(b, s, selection, fields=fields)
        self.assertEqual(p['availability']['status'], 'HOLD')
        self.assertEqual(p['cognitive_load']['status'], 'PEDAGOGY_OVERLOAD')
        expected = {'/methods/0/anti_rule', '/methods/0/four_step_card/stop'}
        expected |= {'/methods/0/' + key + '/' + str(i)
                     for key in ('failure_cases', 'cannot_replace') for i in range(len(b['methods'][0][key]))}
        ledger = {ref['pointer']: row for row in p['teaching_risk']['items'] for ref in row['source_refs']}
        self.assertTrue(expected <= set(ledger))
        for path in expected:
            self.assertEqual(ledger[path]['risk'], {'frequency': 'unknown', 'severity': 'unknown', 'current_relevance': 'unknown'})
            self.assertEqual(ledger[path]['tier'], 'TELL_NOW')
            self.assertEqual(ledger[path]['assessment_refs'], [])
            item = next(x for x in p['boundaries']['tell_now'] if any(r['pointer'] == path for r in x['source_refs']))
            self.assertTrue(pointer(b, path))
            self.assertEqual(item['text'], pointer(b, path).replace('G01', '').replace('word_answer', '填词答案').strip())
        with self.assertRaises(ValueError):
            copy_projection(p, b, s)
        worked = compile_plan(b, s, selection, mode='worked_example')
        self.assertTrue(validate_plan(worked, b, s)['consumption_allowed'])
        self.assertEqual(worked['student_model']['stop'], worked['boundaries']['tell_now'])

    def test_risk_ledger_retains_each_source_when_identical_caveats_merge(self):
        p, b, s = self.plan()
        student_ids = {x['item_id'] for tier in ('tell_now', 'tell_later') for x in p['boundaries'][tier]}
        self.assertTrue(all(row['item_id'] in student_ids for row in p['teaching_risk']['items']))
        stop_paths = {'/methods/0/stop_rule', '/analysis/execution_trace/0/stop_rule_check'}
        ledger_paths = {r['pointer'] for row in p['teaching_risk']['items'] for r in row['source_refs']}
        self.assertTrue(stop_paths <= ledger_paths)
        b, s, selection = self.assets(case='boundary')
        case_plan = compile_plan(b, s, selection, mode='boundary')
        self.assertTrue(any(r['pointer'].endswith('/reviewed_claims/boundary')
            for row in case_plan['teaching_risk']['items'] for r in row['source_refs']))

    def test_legacy_contract_is_inspectable_but_requires_new_projection_to_consume(self):
        p, b, s = self.plan()
        legacy = deepcopy(p)
        legacy.update(schema_version='0.1.0', compiler_version='0.1.0', policy_version='0.1.0')
        legacy['student_model']['stop'] = deepcopy(legacy['student_model']['stop'][0])
        for row in legacy['teaching_risk']['items']:
            row.pop('source_refs')
        legacy = reseal_plan(legacy)
        self.assertEqual(inspect_historical(legacy)['contract_status'], 'LEGACY_CONTRACT')
        self.assertFalse(inspect_historical(legacy)['consumption_allowed'])
        with self.assertRaisesRegex(ValueError, 'Historical Pedagogy contract'):
            validate_plan(legacy, b, s)
        with self.assertRaises(ValueError):
            copy_projection(legacy, b, s)
        self.assertEqual(p['schema_version'], '0.2.0')
        self.assertNotEqual(p['plan_sha'], legacy['plan_sha'])
        self.assertTrue(validate_plan(p, b, s)['consumption_allowed'])
        self.assertEqual(copy_projection(p, b, s)['schema_version'], '0.2.0')


if __name__ == '__main__':
    unittest.main()
