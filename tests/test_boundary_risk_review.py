"""SYNTHETIC disclosure controls; no real risk frequency or teaching Review."""
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_mechanical_payoff as fixtures
from tests import test_student_pov as copy_fixtures
from video_contracts import pointer, read, seal, sha, write
from pedagogy import compile_plan, copy_projection, validate_plan, validate_handoff, inspect_historical
from pedagogy.boundary_review import inventory
from pedagogy.__main__ import main
from student_pov import realize, validate_copy
from student_pov.qa import planned_scene_observations


def synthetic_review(base, bundle):
    rows = inventory(base, bundle)
    current = [r for r in rows if r['current_action_stop'] or r['source_ref']['pointer'].endswith(
        ('/stop_rule', '/anti_rule', '/cannot_replace/2'))]
    literal = next(r for r in current if r['source_ref']['pointer'].endswith('/anti_rule'))
    coverage = []
    for row in current:
        mechanism = 'bounded_candidate_state' if row['current_action_stop'] or \
            row['source_ref']['pointer'].endswith('/cannot_replace/2') else 'reviewed_equivalent'
        if row == literal:
            mechanism = 'literal_display'
        coverage.append({'source_ref': row['source_ref'], 'range': [0, len(row['text'])],
            'mechanism': mechanism, 'rationale': 'SYNTHETIC case-bound coverage, not a real semantic Review'})
    return seal({'schema_version': '0.1.0', 'kind': 'pedagogy_boundary_risk_review', 'status': 'pass',
        'reviewer': 'SYNTHETIC DISCLOSURE CONTROL ONLY', 'reviewer_kind': 'ai_host',
        'independent_human_teaching_certified': False, 'empirical_frequency_established': False,
        'binding': {'source_plan_shas': [base['plan_sha']], 'input_binding': base['input_binding'],
                    'source_analysis_sha': base['source_analysis_sha'],
                    'truth_guard_sha': sha(base['truth_guard']), 'boundary_inventory_sha': sha(rows)},
        'entries': [{'source_ref': r['source_ref'],
            'risk': {'frequency': 'unknown', 'severity': 'high',
                     'current_relevance': 'high' if r in current else 'low'},
            'frequency_basis': 'SYNTHETIC; no student data',
            'current_applicability': 'triggered' if r in current else 'not_exercised',
            'omission_risk': 'SYNTHETIC wrong branch or unsupported final-answer claim',
            'rationale': 'SYNTHETIC explicit branch review; unknown frequency is not low',
            'assessment_refs': base['truth_guard']['action_refs'] + base['truth_guard']['review_refs'],
            'decision': 'TELL_NOW' if r in current else 'TELL_LATER',
            'deferred_until': None if r in current else 'SYNTHETIC other decision branch'} for r in rows],
        'presentations': [{'group_id': 'synthetic-comparison-boundary',
            'member_refs': [r['source_ref'] for r in current], 'literal_ref': literal['source_ref'],
            'literal_range': [0, len(literal['text'])], 'scene': 'action',
            'rationale': 'SYNTHETIC combine bound guards, not a free paraphrase', 'coverage': coverage}],
        'delivery': {'focus_evidence_refs': base['evidence_refs'], 'bounded_candidate_state': True},
        'generated_at': 'SYNTHETIC'})


class BoundaryRiskReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, cls.status, cls.selection = fixtures.freeze()
        cls.base = compile_plan(cls.bundle, cls.status, cls.selection, mode='worked_example', generated_at='one')
        cls.review = synthetic_review(cls.base, cls.bundle)

    def reviewed(self, review=None, **kwargs):
        return compile_plan(self.bundle, self.status, self.selection, mode='worked_example',
            generated_at='one', boundary_review=self.review if review is None else review, **kwargs)

    def test_unknown_frequency_is_preserved_and_current_stop_is_covered_not_deleted(self):
        before = sha([self.bundle, self.status, self.base, self.review])
        p = self.reviewed()
        self.assertEqual(len(p['boundaries']['tell_now']), 1)
        self.assertEqual(len(p['boundaries']['tell_later']), 5)
        self.assertTrue(p['boundaries']['tell_now'][0]['current_action_stop'])
        self.assertEqual(p['truth_guard'], self.base['truth_guard'])
        self.assertEqual(p['answer_scope'], self.base['answer_scope'])
        self.assertEqual(p['payoff'], self.base['payoff'])
        self.assertEqual(p['semantic_review'], self.base['semantic_review'])
        self.assertTrue(all(i['risk']['frequency'] == 'unknown' for i in p['teaching_risk']['items']))
        self.assertFalse(p['semantic_review']['independent_human_certified'])
        self.assertFalse(p['public_render_ready'])
        self.assertEqual(before, sha([self.bundle, self.status, self.base, self.review]))
        self.assertEqual(validate_plan(p, self.bundle, self.status)['status'], 'PASS')

    def test_no_review_keeps_original_hash_and_conservative_tiers(self):
        repeated = compile_plan(self.bundle, self.status, self.selection, mode='worked_example', generated_at='one')
        self.assertEqual(self.base, repeated)
        self.assertEqual({row['text'] for row in repeated['boundaries']['tell_now']},
                         {row['text'] for row in inventory(self.base,self.bundle)})
        self.assertNotIn('boundary_delivery', repeated)

    def test_wrong_scope_hash_source_and_missing_entry_are_rejected(self):
        for edit in [lambda r: r['binding'].update(source_plan_shas=['0' * 64]),
                     lambda r: r['binding'].update(truth_guard_sha='0' * 64),
                     lambda r: r['entries'].pop(),
                     lambda r: r['entries'][0]['source_ref'].update(sha='0' * 64),
                     lambda r: r['entries'][0].update(assessment_refs=[{'asset_id': 'other-method',
                         'pointer': '/methods/0', 'sha': '0' * 64}])]:
            r = deepcopy(self.review); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.reviewed(seal(r))

    def test_current_stop_cannot_be_later_and_later_needs_assessed_applicability(self):
        stop_index = next(i for i, row in enumerate(inventory(self.base, self.bundle)) if row['current_action_stop'])
        later_index = next(i for i, e in enumerate(self.review['entries']) if e['decision'] == 'TELL_LATER')
        for edit in [lambda r: r['entries'][stop_index].update(decision='TELL_LATER', deferred_until='later'),
                     lambda r: r['entries'][later_index]['risk'].update(current_relevance='unknown'),
                     lambda r: r['entries'][later_index]['risk'].update(severity='unknown'),
                     lambda r: r['entries'][later_index].update(current_applicability='conditional')]:
            r = deepcopy(self.review); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.reviewed(seal(r))

    def test_clause_holes_overlap_and_invented_literal_cannot_hide_current_stop(self):
        for edit in [lambda r: r['presentations'][0]['coverage'].pop(),
                     lambda r: r['presentations'][0]['coverage'].append(deepcopy(r['presentations'][0]['coverage'][0])),
                     lambda r: r['presentations'][0].update(literal_range=[0, 999999]),
                     lambda r: r['presentations'][0]['coverage'][0].update(mechanism='literal_display'),
                     lambda r: r['delivery'].update(bounded_candidate_state=False)]:
            r = deepcopy(self.review); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.reviewed(seal(r))

    def test_nonowned_evidence_and_unapproved_review_are_rejected(self):
        for edit in [lambda r: r['delivery'].update(focus_evidence_refs=[self.base['truth_guard']['method_ref']]),
                     lambda r: r.update(status='changes_requested'),
                     lambda r: r.update(independent_human_teaching_certified=True),
                     lambda r: r['entries'][0]['risk'].update(frequency='low')]:
            r = deepcopy(self.review); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.reviewed(seal(r))

    def test_composite_stop_has_no_assessment_holes_and_cannot_be_only_backend_metadata(self):
        index = next(i for i, row in enumerate(inventory(self.base, self.bundle)) if row['current_action_stop'])
        text = pointer(self.bundle, self.review['entries'][index]['source_ref']['pointer'])
        r = deepcopy(self.review)
        r['entries'][index]['clause_assessments'] = [{'range': [0, len(text)],
            'risk': r['entries'][index]['risk'], 'decision': 'TELL_NOW',
            'rationale': 'SYNTHETIC exact composite range'}]
        self.reviewed(seal(r))
        r['entries'][index]['clause_assessments'][0]['range'][1] -= 1
        with self.assertRaises(ValueError):
            self.reviewed(seal(r))
        r = deepcopy(self.review)
        for c in r['presentations'][0]['coverage']:
            if c['source_ref'] == r['entries'][index]['source_ref']:
                c['mechanism'] = 'upstream_revalidation'
        with self.assertRaises(ValueError):
            self.reviewed(seal(r))

    def test_hash_repeat_and_upstream_withdrawal_replay(self):
        one = self.reviewed()
        two = compile_plan(self.bundle, self.status, self.selection, mode='worked_example',
                           boundary_review=self.review, generated_at='two')
        self.assertEqual(one['plan_sha'], two['plan_sha'])
        self.assertEqual(one['content_sha'], two['content_sha'])
        self.assertNotEqual(one['envelope_sha'], two['envelope_sha'])
        transported = deepcopy(self.review); transported['generated_at'] = 'new review transport time'
        same = self.reviewed(seal(transported))
        self.assertEqual(one['plan_sha'], same['plan_sha'])
        self.assertNotEqual(one['envelope_sha'], same['envelope_sha'])
        cp = copy_projection(one, self.bundle, self.status)
        changed = deepcopy(self.status); changed['effective_status'] = 'WITHDRAWN'
        with self.assertRaises(ValueError):
            validate_handoff(cp, one, self.bundle, seal(changed))
        changed = deepcopy(one); changed['boundary_delivery']['focus_evidence_refs'].clear()
        changed = copy_fixtures.fixture_module.reseal_plan(changed)
        with self.assertRaises(ValueError):
            validate_plan(changed, self.bundle, self.status)
        historical = deepcopy(one); historical['boundary_delivery']['contract_version'] = '0.1.0'
        historical = copy_fixtures.fixture_module.reseal_plan(historical)
        self.assertEqual(inspect_historical(historical)['contract_status'], 'LEGACY_CONTRACT')
        with self.assertRaisesRegex(ValueError, 'Historical boundary delivery'):
            validate_plan(historical, self.bundle, self.status)

    def test_disclosure_does_not_automatically_unlock_other_modes_or_remove_case_gap(self):
        with self.assertRaises(ValueError):
            compile_plan(self.bundle, self.status, self.selection, mode='first_touch', boundary_review=self.review)
        case = compile_plan(self.bundle, self.status, self.selection, mode='transfer')
        r = synthetic_review(case, self.bundle)
        projected = compile_plan(self.bundle, self.status, self.selection, mode='transfer', boundary_review=r)
        self.assertEqual(projected['availability']['status'], 'UNAVAILABLE_EVIDENCE_GAP')
        self.assertIn('missing_reviewed_transfer_case', projected['availability']['gaps'])

    def test_copy_uses_reviewed_action_boundary_and_unresolved_state_without_reminder_vo(self):
        p = self.reviewed(); cp = copy_projection(p, self.bundle, self.status)
        c = realize(cp, p, self.bundle, self.status)
        action = next(s for s in c['final_script'] if s['cognitive_function'] == 'action')
        focus = next(s for s in c['final_script'] if s['cognitive_function'] == 'focus')
        stop = next(s for s in c['final_script'] if s['cognitive_function'] == 'stop')
        self.assertIn(p['boundaries']['tell_now'][0]['text'], action['screen_copy'])
        self.assertIn(p['boundaries']['tell_now'][0]['item_id'], action['tell_now_boundary_ids'])
        self.assertNotIn(p['boundaries']['tell_now'][0]['text'], focus['screen_copy'])
        self.assertIsNot(action['screen_copy'], focus['screen_copy'])
        self.assertEqual(stop['screen_copy'], ['A / B / C'])
        self.assertIsNone(stop['vo'])
        self.assertTrue(c['copy_audit']['student_pov_present'])
        self.assertEqual(validate_copy(c, cp, p, self.bundle, self.status)['status'], 'PASS')

    def test_boundary_id_without_actual_display_is_not_coverage(self):
        p = self.reviewed(); cp = copy_projection(p, self.bundle, self.status)
        c = realize(cp, p, self.bundle, self.status)
        sequence = deepcopy(c['final_script'])
        for row in sequence:
            if row['cognitive_function'] == 'action':
                row['screen_copy'].remove(p['boundaries']['tell_now'][0]['text'])
        observed = planned_scene_observations(sequence, None,
            first_action_ref=copy_fixtures.ref(p, '/first_action'), payoff_ref=copy_fixtures.ref(p, '/payoff'),
            tell_now_ids=[p['boundaries']['tell_now'][0]['item_id']], tell_now_items=p['boundaries']['tell_now'])
        self.assertFalse(observed['student_pov_present'])

    def test_cli_loads_explicit_review_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, value in [('bundle', self.bundle), ('status', self.status), ('review', self.review)]:
                write(root / (name + '.json'), value)
            request = {'bundle': 'bundle.json', 'status': 'status.json', 'selection': self.selection,
                       'mode': 'worked_example', 'boundary_review': 'review.json', 'output': 'plan.json'}
            write(root / 'request.json', request)
            with patch('sys.argv', ['pedagogy', 'compile', str(root / 'request.json')]), contextlib.redirect_stdout(io.StringIO()):
                main()
            saved = read(root / 'plan.json')
            self.assertEqual(validate_plan(saved, self.bundle, self.status)['status'], 'PASS')
            with patch('sys.argv', ['pedagogy', 'compile', str(root / 'request.json')]), self.assertRaises(ValueError):
                main()
