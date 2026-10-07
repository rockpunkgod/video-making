"""Synthetic path/copy controls. No actual baseline or learner data fabricated."""
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from answer_engine.frozen_export import FrozenAssetExporter
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from tests import test_pedagogy as fixture_module
from video_contracts import seal, sha, read, write, pointer
from pedagogy import compile_plan, copy_projection
from student_pov import realize, validate_copy, inspect_historical, suppression_qa
from student_pov.realization import copy_semantics, question_screen
from student_pov.payoff import supported_payoff
from student_pov.qa import planned_scene_observations
from student_pov.__main__ import main


def ref(plan, path):
    return {'plan_id': plan['plan_id'], 'pointer': path, 'sha': sha(pointer(plan, path))}


def reseal_copy(copy):
    copy = deepcopy(copy); copy['copy_sha'] = sha(copy_semantics(copy))
    copy['copy_id'] = 'student-pov:' + copy['copy_sha']
    return seal(copy)


def assets(mid='R12', with_payoff=True, change=None, mode='first_touch', question_change=None):
    helper = fixture_module.PedagogyTests(); helper.registry = Registry(); helper.engine = QuestionAnalyzer(helper.registry)
    b, s, selection = helper.assets(mid if mid in ('R12', 'G01', 'F01') else 'R12',
                                   question_change=question_change)
    if mid == 'R01':
        selection = {'method_id': 'R01', 'action_ids': ['choice-B']}
    action_index = next(i for i, a in enumerate(b['analysis']['execution_trace'])
                        if a['execution_id'] in selection['action_ids'])
    mi = next(i for i, m in enumerate(b['methods']) if m['method_id'] == mid)
    review = deepcopy(b['reviews'][0]['record'])
    review.update(method_id=mid, method_version=b['methods'][mi]['version'])
    if mid == 'R12':
        before, after, kind, anchor = ['alpha', 'beta', 'gamma'], ['alpha'], 'TYPE_C', '/spans/0/quote'
    elif mid == 'G01':
        before, after, kind, anchor = ['noun', 'verb', 'adjective'], ['noun'], 'TYPE_C', '/node_ids/1'
    elif mid == 'R01':
        before, after, kind, anchor = ['A', 'B'], ['A'], 'TYPE_A', '/candidate'
    else:
        before, after, kind, anchor = ['A', 'B'], ['A'], 'TYPE_B', '/groups/0/candidates'
    support = {'scope': {'question_id': b['source_snapshot']['question_id'], 'method_id': mid,
            'method_version': b['methods'][mi]['version'], 'action_ids': selection['action_ids'],
            'stage': 'current_candidate' if mid == 'R01' else 'current_action', 'claim_scope': 'local_candidate'},
        'payoff_type': kind,
        'baseline_path': [{'step_id': 'toy-before', 'text': 'SYNTHETIC baseline, not observed students',
                           'work_ids': ['toy-scan', 'toy-repeat']}],
        'method_path': [{'step_id': 'toy-after', 'text': 'SYNTHETIC current bounded operation', 'work_ids': ['toy-scan']}],
        'removed_steps': [{'work_id': 'toy-repeat', 'text': 'SYNTHETIC repeated work removed only in this toy scope'}],
        'remaining_steps': [{'work_id': 'toy-scan', 'text': 'SYNTHETIC current work still required'},
                            {'work_id': 'context_check', 'text': 'SYNTHETIC later context still required'},
                            {'work_id': 'word_form', 'text': 'SYNTHETIC word form deferred'}],
        'cognitive_work': {'removed': ['toy-repeat'], 'deferred': ['word_form'],
                           'still_required': ['toy-scan', 'context_check']},
        'reduction': {'before': len(before), 'after': len(after), 'unit': 'candidate' if mid == 'R01' else 'toy_structure',
                      'before_ids': before, 'after_ids': after},
        'allowed_claim': 'SYNTHETIC current operation only; no final answer claim',
        'cognitive_relief_line': 'SYNTHETIC one bounded operation is enough here',
        'evidence_pointers': ['/analysis/execution_trace/' + str(action_index) + '/evidence/0'],
        'first_action_transferable': True,
        'output_anchors': [{'output_index': 0, 'pointer': anchor,
            'sha': sha(pointer(b['analysis']['execution_trace'][action_index]['output'], anchor))}]}
    if change:
        change(support)
    if with_payoff:
        review['reviewed_payoff'] = support
    request = {k: deepcopy(b[k]) for k in ('methods', 'withdrawals', 'source', 'evaluation_phase')}
    request.update(question=deepcopy(b['source_snapshot']), analysis=deepcopy(b['analysis']), reviews=[review])
    exp = FrozenAssetExporter(); b, s = exp.export(request, 'synthetic'), exp.status(request, 'synthetic')
    fields = {'memory_phrase': '/methods/' + str(mi) + '/four_step_card/first_cut'} if mid == 'R12' else {}
    plan = compile_plan(b, s, selection, mode=mode, fields=fields, duration_target=1000)
    projection = copy_projection(plan, b, s)
    return b, s, plan, projection


def reviewed_copy(b, s, plan, projection, draft_lines=None):
    draft = realize(projection, plan, b, s, draft_lines=draft_lines)
    review = {'status': 'pass', 'reviewer': 'SYNTHETIC COPY CREDENTIAL ONLY', 'reviewer_kind': 'ai_host',
        'script_sha': draft['script_sha'], 'final_copy_sha': draft['final_copy_sha'],
        'checks': {'semantic_fidelity': 'pass', 'natural_speech': 'pass', 'layer_division': 'pass'}}
    return realize(projection, plan, b, s, draft_lines=draft_lines, copy_review=review)


class StudentPOVTests(unittest.TestCase):
    def test_type_c_consumes_bound_payoff_and_keeps_required_work(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        self.assertEqual(copy['availability']['status'], 'READY')
        self.assertEqual(copy['payoff_type'], 'TYPE_C')
        self.assertEqual(copy['student_path_comparison']['support_origin'], 'explicit_reviewed_payoff')
        self.assertEqual(copy['student_path_comparison']['baseline_kind'], 'reviewed_path')
        self.assertFalse(copy['student_path_comparison']['baseline_measured'])
        self.assertFalse(copy['student_path_comparison']['learner_transfer_validated'])
        self.assertEqual(copy['cognitive_work']['removed'], ['toy-repeat'])
        self.assertEqual(copy['cognitive_work']['deferred'], ['word_form'])
        self.assertEqual(copy['payoff_validation']['output_type'], 'locator')
        self.assertEqual(copy['copy_audit']['human_taste_review'], 'PENDING')
        self.assertEqual(copy['copy_audit']['observation_scope'], 'planned_scene_structure_only')
        self.assertEqual(copy['copy_audit']['actual_visual_review'], 'PENDING')
        self.assertEqual(copy['copy_audit']['student_experience_review'], 'PENDING')
        self.assertTrue(copy['copy_audit']['payoff_supported'])
        self.assertTrue(copy['copy_audit']['cognitive_reduction_visible'])
        self.assertTrue(copy['copy_audit']['student_pov_present'])
        payoff, _ = supported_payoff(p, cp)
        scene_rows = deepcopy(copy['final_script'])
        collapse = next(row for row in scene_rows if row['cognitive_function'] == 'collapse')
        arguments = {'first_action_ref': ref(p, '/first_action'), 'payoff_ref': ref(p, '/payoff'),
                     'tell_now_ids': [x['item_id'] for x in p['boundaries']['tell_now']]}
        observed = planned_scene_observations(scene_rows, payoff, **arguments)
        self.assertTrue(observed['cognitive_reduction_visible'])
        self.assertEqual(observed['actual_visual_review'], 'PENDING')
        before_text = {row['text'] for row in payoff['baseline_path']}
        for row in scene_rows:
            row['screen_copy'] = [text for text in row['screen_copy'] if text not in before_text]
        self.assertFalse(planned_scene_observations(scene_rows, payoff, **arguments)['cognitive_reduction_visible'])
        collapse['removed_work'] = []
        self.assertFalse(planned_scene_observations(scene_rows, payoff, **arguments)['cognitive_reduction_visible'])
        scene_rows = [row for row in scene_rows if row['cognitive_function'] != 'action']
        self.assertFalse(planned_scene_observations(scene_rows, payoff, **arguments)['student_pov_present'])
        self.assertFalse(copy['public_render_ready'])
        self.assertEqual(validate_copy(copy, cp, p, b, s)['status'], 'PASS')
        self.assertLess(copy['timing']['estimated_duration_seconds'], 1000)

    def test_no_baseline_or_removed_work_means_hold_and_no_invented_relief(self):
        b, s, p, cp = assets(with_payoff=False)
        copy = realize(cp, p, b, s)
        self.assertEqual(copy['availability']['status'], 'HOLD')
        self.assertEqual(copy['student_path_comparison']['baseline_path'], [])
        self.assertEqual(copy['cognitive_work']['removed'], [])
        self.assertIsNone(copy['script']['cognitive_relief_line'])
        self.assertIsNone(copy['student_path_comparison']['support_origin'])
        self.assertIsNone(copy['student_path_comparison']['baseline_kind'])
        self.assertIsNone(copy['student_path_comparison']['baseline_measured'])
        self.assertEqual(copy['payoff_validation']['status'], 'PAYOFF_UNSUPPORTED')

    def test_mechanical_candidate_state_is_not_observed_or_transfer_certified(self):
        from tests.test_mechanical_payoff import freeze
        b, s, selected = freeze()
        p = compile_plan(b, s, selected, mode='worked_example', duration_target=1000)
        cp = copy_projection(p, b, s)
        copy = reviewed_copy(b, s, p, cp)
        self.assertEqual(copy['availability']['status'], 'READY')
        comparison = copy['student_path_comparison']
        self.assertEqual(comparison['support_origin'], 'frozen_candidate_transition')
        self.assertEqual(comparison['baseline_kind'], 'structural_candidate_state')
        self.assertFalse(comparison['baseline_measured'])
        self.assertFalse(comparison['learner_transfer_validated'])
        self.assertEqual(copy['cognitive_work']['removed'], ['current_candidate_check:D'])
        self.assertEqual(copy['payoff_type'], 'TYPE_A')
        self.assertTrue(copy['copy_audit']['cognitive_reduction_visible'])
        self.assertEqual(copy['copy_audit']['actual_visual_review'], 'PENDING')
        self.assertFalse(copy['script']['decision_state']['answer_scope']['may_output_final_answer'])
        self.assertFalse(copy['payoff_validation']['semantic_certification'])
        self.assertFalse(copy['public_render_ready'])
        for flag in ('baseline_measured', 'learner_transfer_validated'):
            changed = deepcopy(copy); changed['student_path_comparison'][flag] = True
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'schema'):
                inspect_historical(reseal_copy(changed))

    def test_original_question_precedes_focus_and_persists_with_exact_refs(self):
        b, s, p, cp = assets('G01')
        copy = reviewed_copy(b, s, p, cp)
        original = question_screen(p['original_question'])
        layer = copy['reality_layer']
        self.assertEqual(layer['question'], p['original_question'])
        self.assertEqual(layer['field_refs'], p['original_question_refs'])
        self.assertEqual(layer['screen_copy'], original)
        self.assertTrue(layer['persistent'])
        self.assertFalse(layer['fact_mutation_allowed'])
        self.assertEqual(layer['visibility_review'], 'PENDING')
        first = copy['final_script'][0]
        self.assertEqual(first['visual_state'], 'original_question')
        self.assertEqual(first['screen_copy'][:len(original)], original)
        self.assertIn(ref(p, '/original_question'), first['pedagogy_ref'])
        self.assertTrue(all(row['reality_layer_ref'] == '/reality_layer' for row in copy['final_script']))
        self.assertTrue(copy['copy_audit']['original_question_first'])
        self.assertIn(p['original_question']['given_word'], original)
        self.assertTrue(all(label + '. ' + text in original
                            for label, text in p['original_question']['options'].items()))
        self.assertEqual(copy['final_copy_sha'], sha({'script': copy['script'],
            'final_script': copy['final_script'], 'reality_layer': layer}))

    def test_resealed_question_or_persistence_edits_cannot_inherit_copy_approval(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        edits = [lambda v: v['reality_layer']['question'].update(passage='changed'),
                 lambda v: v['reality_layer'].update(persistent=False),
                 lambda v: v['reality_layer']['field_refs']['passage'].update(sha='0' * 64),
                 lambda v: v['final_script'][0].update(screen_copy=[]),
                 lambda v: v['final_script'][1].update(reality_layer_ref='/another-layer')]
        for edit in edits:
            changed = deepcopy(copy); edit(changed)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_copy(reseal_copy(changed), cp, p, b, s)

    def test_literal_source_statistics_are_displayed_without_new_copy_claims(self):
        text = 'SYNTHETIC original: 80% in a framework; R02 is a source label.'
        b, s, p, cp = assets(question_change=lambda q: q.update(passage=q['passage'] + '\n' + text))
        copy = reviewed_copy(b, s, p, cp)
        self.assertIn(text, copy['reality_layer']['question']['passage'])
        self.assertEqual(copy['availability']['status'], 'READY')
        self.assertEqual(copy['availability']['issues'], [])

    def test_original_task_change_requires_new_bound_final_copy_review(self):
        b, s, p, cp = assets()
        previous = reviewed_copy(b, s, p, cp)
        b, s, p, cp = assets(question_change=lambda q: q.update(stem=q['stem'] + ' SYNTHETIC task revision'))
        changed = realize(cp, p, b, s, copy_review=previous['realization_request']['copy_review'])
        self.assertNotEqual(previous['final_copy_sha'], changed['final_copy_sha'])
        self.assertEqual(changed['availability']['status'], 'HOLD')
        self.assertIn('FINAL_COPY_SEMANTIC_AND_NATURAL_SPEECH_REVIEW_REQUIRED', changed['availability']['gaps'])

    def test_copy_semantic_natural_speech_credential_missing_is_hold(self):
        b, s, p, cp = assets()
        copy = realize(cp, p, b, s)
        self.assertEqual(copy['availability']['status'], 'HOLD')
        self.assertIn('FINAL_COPY_SEMANTIC_AND_NATURAL_SPEECH_REVIEW_REQUIRED', copy['availability']['gaps'])

    def test_local_decider_does_not_inherit_core_final_answer_permission(self):
        b, s, p, cp = assets('R01', mode='worked_example')
        copy = reviewed_copy(b, s, p, cp)
        self.assertEqual(copy['availability']['status'], 'READY')
        self.assertEqual(copy['payoff_type'], 'TYPE_A')
        self.assertEqual(copy['role'], 'decider')
        self.assertFalse(copy['script']['decision_state']['answer_scope']['may_output_final_answer'])
        copy = realize(cp, p, b, s, draft_lines={'payoff_line': {'text': '答案出来了', 'pedagogy_refs': [ref(p, '/payoff')]}})
        self.assertEqual(copy['availability']['status'], 'FAIL')
        self.assertTrue(copy['payoff_validation']['overclaim'])

    def test_partition_does_not_create_a_fake_four_to_two_candidate_drop(self):
        b, s, p, cp = assets('F01', mode='worked_example')
        copy = realize(cp, p, b, s)
        self.assertEqual(copy['availability']['status'], 'HOLD')
        self.assertIn('PAYOFF_UNSUPPORTED:partition_is_not_candidate_elimination', copy['availability']['gaps'])
        copy = realize(cp, p, b, s, draft_lines={'payoff_line': {'text': '答案出来了', 'pedagogy_refs': [ref(p, '/payoff')]}})
        self.assertEqual(copy['availability']['status'], 'FAIL')

    def test_framework_keeps_real_role_and_defers_word_form(self):
        b, s, p, cp = assets('G01')
        copy = reviewed_copy(b, s, p, cp)
        self.assertEqual(copy['availability']['status'], 'READY')
        self.assertEqual(copy['payoff_validation']['output_type'], 'framework')
        self.assertIn('word_form', copy['cognitive_work']['deferred'])
        self.assertFalse(copy['script']['decision_state']['answer_scope']['may_output_final_answer'])
        copy = realize(cp, p, b, s, draft_lines={'cognitive_relief_line':
            {'text': '所以填具体词X', 'pedagogy_refs': [ref(p, '/payoff')]}})
        self.assertEqual(copy['availability']['status'], 'FAIL')

    def test_form_checks_cannot_be_reclassified_as_removed_by_a_route(self):
        def wrong(support):
            support['baseline_path'][0]['work_ids'].append('word_form')
            support['cognitive_work']['removed'].append('word_form')
            support['cognitive_work']['deferred'] = []
            support['removed_steps'].append({'work_id': 'word_form', 'text': 'SYNTHETIC bad permanent omission'})
        b, s, p, cp = assets('G01', change=wrong)
        copy = realize(cp, p, b, s)
        self.assertIn('PAYOFF_UNSUPPORTED:route_does_not_remove_form_or_context_checks', copy['availability']['gaps'])

    def test_bad_role_mapping_mutated_anchor_or_no_reduction_is_unsupported(self):
        changes = [lambda d: d.update(payoff_type='TYPE_A'),
                   lambda d: d['output_anchors'][0].update(sha='0' * 64),
                   lambda d: d['reduction'].update(after=d['reduction']['before'])]
        for change in changes:
            b, s, p, cp = assets(change=change)
            copy = realize(cp, p, b, s)
            with self.subTest(change=change):
                self.assertEqual(copy['availability']['status'], 'HOLD')
                self.assertEqual(copy['payoff_validation']['status'], 'PAYOFF_UNSUPPORTED')

    def test_required_boundaries_not_mutable_by_adapter_or_resealed_copy(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        self.assertEqual(copy['tell_now_boundaries'], p['boundaries']['tell_now'])
        with self.assertRaises(ValueError):
            realize(cp, p, b, s, draft_lines={'tell_now_boundaries': []})
        changed = deepcopy(copy); changed['tell_now_boundaries'] = []
        with self.assertRaises(ValueError):
            validate_copy(reseal_copy(changed), cp, p, b, s)
        changed = deepcopy(copy); changed['final_script'][-2]['screen_copy'] = []
        with self.assertRaises(ValueError):
            validate_copy(reseal_copy(changed), cp, p, b, s)
        changed = deepcopy(copy); changed['copy_audit']['actual_visual_review'] = 'PASS'
        with self.assertRaises(ValueError):
            validate_copy(reseal_copy(changed), cp, p, b, s)
        changed = deepcopy(copy); changed['copy_audit']['student_pov_present'] = False
        with self.assertRaises(ValueError):
            validate_copy(reseal_copy(changed), cp, p, b, s)

    def test_unsupported_vocabulary_shortcuts_and_backend_chain_fail(self):
        b, s, p, cp = assets()
        for text in ('做阅读不用背单词', '这几个词不用认识', '这一步不用认识alpha',
                     '定位，然后确认角色，再核对Evidence，边界检查，Review',
                     '今天学习R12定位方法'):
            copy = realize(cp, p, b, s, draft_lines={'cognitive_relief_line':
                {'text': text, 'pedagogy_refs': [ref(p, '/payoff')]}})
            with self.subTest(text=text):
                self.assertEqual(copy['availability']['status'], 'FAIL')

    def test_value_before_vocabulary_and_no_internal_numbers_on_surface(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        functions = [x['cognitive_function'] for x in copy['final_script']]
        self.assertGreater(functions.index('stamp'), functions.index('collapse'))
        self.assertGreater(functions.index('stamp'), functions.index('payoff'))
        self.assertNotEqual(len(copy['final_script']), 8)
        texts = [t for row in copy['final_script'] for t in [row['vo'] or '', *row['screen_copy']]]
        self.assertFalse(any('R12' in text for text in texts))
        self.assertEqual(copy['copy_audit']['screen_voice_duplication'], 'low')

    def test_silence_is_short_and_required_boundaries_stay_visible(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        self.assertTrue(copy['silence_candidates'])
        self.assertTrue(all(0.3 <= x['duration_seconds'] <= 1 for x in copy['silence_candidates']))
        seal_scene = next(x for x in copy['silence_candidates'] if x['event'] == 'boundary_seal')
        self.assertTrue(seal_scene['tell_now_visible'])

    def test_explanation_suppression_only_proposes_deleting_redundant_voice(self):
        b, s, p, cp = assets()
        lines = {'stop_vo': {'text': '先停', 'pedagogy_refs': [ref(p, '/boundaries/tell_now')]}}
        copy = reviewed_copy(b, s, p, cp, lines)
        coverage = [{'scene_id': row['scene_id'], 'visual_expressed': True,
            'motion_expressed': True, 'evidence_expressed': True, 'next_action_depends': False,
            'note': 'SYNTHETIC declared coverage, not auto-visual certification'} for row in copy['final_script']]
        before = sha(copy)
        qa = suppression_qa(copy, coverage)
        self.assertTrue(qa['redundant'])
        self.assertTrue(qa['protected_tell_now_scenes'])
        self.assertTrue(qa['existing_copy_approval_invalid_for_candidate'])
        stop = next(row for row in qa['final_script_candidate'] if row['cognitive_function'] == 'stop')
        self.assertEqual(stop['vo'], '先停')
        self.assertEqual(stop['screen_copy'], [b['text'] for b in p['boundaries']['tell_now']])
        self.assertEqual(before, sha(copy))

    def test_final_copy_change_invalidates_old_approval_and_current_status(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        request = copy['realization_request']
        changed = realize(cp, p, b, s, draft_lines={'pain':
            {'text': 'SYNTHETIC changed pain', 'pedagogy_refs': [ref(p, '/symptom')]}},
            copy_review=request['copy_review'])
        self.assertEqual(changed['availability']['status'], 'HOLD')
        self.assertNotEqual(changed['final_copy_sha'], copy['final_copy_sha'])
        with self.assertRaises(ValueError):
            validate_copy(copy, cp, p, b, seal({**s, 'effective_status': 'WITHDRAWN'}))

    def test_adapter_only_receives_small_frozen_projection(self):
        b, s, p, cp = assets()
        class FakeAdapter:
            def propose(self, value):
                self.value = deepcopy(value)
                return {'first_action': {'text': p['first_action']['text'],
                                         'pedagogy_refs': [ref(p, '/first_action')]}}
        adapter = FakeAdapter()
        copy = realize(cp, p, b, s, adapter=adapter)
        self.assertNotIn('methods', adapter.value)
        self.assertNotIn('analysis', adapter.value)
        self.assertEqual(copy['availability']['status'], 'HOLD')

    def test_cli_realizes_and_reloads_with_no_history_overwrite(self):
        b, s, p, cp = assets(with_payoff=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, value in [('bundle', b), ('status', s), ('plan', p), ('projection', cp)]:
                write(root / (name + '.json'), value)
            request = {k: k + '.json' for k in ('bundle', 'status', 'plan', 'projection')}
            request['output'] = 'copy.json'; write(root / 'request.json', request)
            with patch('sys.argv', ['student_pov', 'realize', str(root / 'request.json')]), contextlib.redirect_stdout(io.StringIO()):
                main()
            self.assertEqual(read(root / 'copy.json')['availability']['status'], 'HOLD')
            with patch('sys.argv', ['student_pov', 'realize', str(root / 'request.json')]), self.assertRaises(ValueError):
                main()

    def test_explicit_payoff_is_delivered_once_and_invalidates_prior_copy_review(self):
        b, s, p, cp = assets()
        previous = reviewed_copy(b, s, p, cp)
        line = {'text': 'SYNTHETIC alternate bounded payoff', 'pedagogy_refs': [ref(p, '/payoff')]}
        changed = realize(cp, p, b, s, draft_lines={'payoff_line': line},
            copy_review=previous['realization_request']['copy_review'])
        delivered = [row for row in changed['final_script'] if row['cognitive_function'] == 'payoff']
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]['vo'], line['text'])
        self.assertEqual(delivered[0]['pedagogy_ref'], line['pedagogy_refs'])
        self.assertEqual(changed['payoff_validation']['final_copy_claim'], line['text'])
        self.assertNotEqual(changed['final_copy_sha'], previous['final_copy_sha'])
        self.assertEqual(changed['availability']['status'], 'HOLD')
        self.assertEqual(reviewed_copy(b, s, p, cp, {'payoff_line': line})['availability']['status'], 'READY')

    def test_blank_action_and_backend_only_or_wrong_purpose_references_are_rejected(self):
        b, s, p, cp = assets()
        cases = [
            {'first_action': {'text': '', 'pedagogy_refs': [ref(p, '/first_action')]}},
            {'first_action': {'text': ' \n\t ', 'pedagogy_refs': [ref(p, '/first_action')]}},
            {'cognitive_relief_line': {'text': 'SYNTHETIC unsupported binding', 'pedagogy_refs': [ref(p, '/role')]}},
            {'payoff_line': {'text': 'SYNTHETIC unsupported binding', 'pedagogy_refs': [ref(p, '/first_action')]}},
            {'stop_vo': {'text': '先停', 'pedagogy_refs': [ref(p, '/first_signal')]}},
            {'pain': {'text': 'SYNTHETIC hidden backend', 'pedagogy_refs': [ref(p, '/truth_guard')]}},
        ]
        for lines in cases:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                realize(cp, p, b, s, draft_lines=lines)

    def test_every_baseline_work_item_needs_disposition_and_action_must_transfer(self):
        changes = [
            (lambda d: d['baseline_path'][0]['work_ids'].append('toy-hidden-work'), 'baseline_work_not_classified'),
            (lambda d: d.update(first_action_transferable=False), 'first_action_not_transferable'),
            (lambda d: d['remaining_steps'].append({'work_id': 'toy-unclassified', 'text': 'SYNTHETIC hidden remaining work'}),
             'deferred_or_still_required_steps_not_recorded'),
        ]
        for change, reason in changes:
            b, s, p, cp = assets(change=change)
            copy = reviewed_copy(b, s, p, cp)
            with self.subTest(reason=reason):
                self.assertEqual(copy['availability']['status'], 'HOLD')
                self.assertIn('PAYOFF_UNSUPPORTED:' + reason, copy['availability']['gaps'])

    def test_malformed_or_duplicate_work_identifiers_return_hold(self):
        changes = [
            (lambda d: d['baseline_path'][0].update(work_ids=[['nested']]), 'unbound_path_steps'),
            (lambda d: d['cognitive_work'].update(removed=['toy-repeat', 'toy-repeat']), 'invalid_work_dispositions'),
            (lambda d: d['remaining_steps'][0].update(work_id=[]), 'invalid_work_steps'),
            (lambda d: d['reduction'].update(before_ids=['alpha', 'alpha', 'gamma']), 'invalid_reduction_ids'),
        ]
        for change, reason in changes:
            b, s, p, cp = assets(change=change)
            copy = realize(cp, p, b, s)
            with self.subTest(reason=reason):
                self.assertEqual(copy['availability']['status'], 'HOLD')
                self.assertIn('PAYOFF_UNSUPPORTED:' + reason, copy['availability']['gaps'])

    def test_unbound_percentages_and_heat_do_not_pass_with_copy_credential(self):
        b, s, p, cp = assets()
        for text in ('80%的人都这样做', '这是全网热门的方法', '这个方法爆火了'):
            lines = {'pain': {'text': text, 'pedagogy_refs': [ref(p, '/symptom')]}}
            copy = reviewed_copy(b, s, p, cp, lines)
            with self.subTest(text=text):
                self.assertEqual(copy['availability']['status'], 'FAIL')
                self.assertIn('COPY_LINT:unbound_statistic_or_heat_claim', copy['availability']['issues'])

    def test_ready_schema_requires_action_and_visible_planned_reduction(self):
        b, s, p, cp = assets()
        copy = reviewed_copy(b, s, p, cp)
        for flag in ('first_action_preserved', 'cognitive_reduction_visible', 'student_pov_present',
                     'original_question_first'):
            changed = deepcopy(copy)
            changed['copy_audit'][flag] = False
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'schema'):
                inspect_historical(reseal_copy(changed))

    def test_legacy_copy_integrity_inspection_does_not_authorize_consumption(self):
        b, s, p, cp = assets()
        legacy = reviewed_copy(b, s, p, cp)
        legacy['schema_version'] = '0.1.0'
        legacy.pop('reality_layer')
        legacy['copy_audit'].pop('original_question_first')
        for key in ('support_origin', 'baseline_kind', 'baseline_measured', 'learner_transfer_validated'):
            legacy['student_path_comparison'].pop(key)
        for row in legacy['final_script']:
            row.pop('reality_layer_ref')
        for field in ('observation_scope', 'actual_visual_review', 'student_experience_review'):
            legacy['copy_audit'].pop(field)
        legacy['script_sha'] = sha(legacy['final_script'])
        legacy['final_copy_sha'] = sha({'script': legacy['script'], 'final_script': legacy['final_script']})
        legacy = reseal_copy(legacy)
        result = inspect_historical(legacy)
        self.assertEqual(result['contract_status'], 'LEGACY_CONTRACT')
        self.assertFalse(result['current_upstream_verified'])
        self.assertFalse(result['consumption_allowed'])
        with self.assertRaisesRegex(ValueError, 'Historical Student POV Copy contract'):
            validate_copy(legacy, cp, p, b, s)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / 'legacy.json', legacy)
            write(root / 'inspect.json', {'copy': 'legacy.json'})
            output = io.StringIO()
            with patch('sys.argv', ['student_pov', 'inspect', str(root / 'inspect.json')]), contextlib.redirect_stdout(output):
                main()
            self.assertIn('consumption blocked', output.getvalue())

    def test_v02_copy_is_historical_and_requires_original_question_regeneration(self):
        b, s, p, cp = assets()
        legacy = reviewed_copy(b, s, p, cp)
        legacy['schema_version'] = '0.2.0'
        legacy.pop('reality_layer')
        legacy['copy_audit'].pop('original_question_first')
        for key in ('support_origin', 'baseline_kind', 'baseline_measured', 'learner_transfer_validated'):
            legacy['student_path_comparison'].pop(key)
        for row in legacy['final_script']:
            row.pop('reality_layer_ref')
        legacy['script_sha'] = sha(legacy['final_script'])
        legacy['final_copy_sha'] = sha({'script': legacy['script'], 'final_script': legacy['final_script']})
        legacy = reseal_copy(legacy)
        result = inspect_historical(legacy)
        self.assertEqual(result['contract_status'], 'LEGACY_CONTRACT')
        self.assertFalse(result['consumption_allowed'])
        with self.assertRaisesRegex(ValueError, 'Historical Student POV Copy contract'):
            validate_copy(legacy, cp, p, b, s)


if __name__ == '__main__':
    unittest.main()
