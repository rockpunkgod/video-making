"""Synthetic transport controls; no real question or human certification."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from video_contracts import sha
from tests.test_judgement_preflight import PhraseRequestTests
from content_os.phrase_review import freeze_phrase_review, bounded_plan
from ae_production.phrase_consumer import consume_phrase_review


class PhraseReviewTests(unittest.TestCase):
    def setUp(self):
        fixture = PhraseRequestTests('test_exact_lexical_range_does_not_upgrade_sentence_review')
        fixture.setUp()
        self.bundle = fixture.bundle
        action = self.bundle['source_snapshot']['action_executions'][0]
        action.update(method_id='R06', role='decider', stop_applied=False)
        fixture.event['source_refs'][0]['sha'] = sha(action)
        fixture.operations[0]['scene_id'] = 'B06'
        self.bundle.update(content_sha='synthetic-content', semantic_binding_sha='synthetic-semantic',
                           binding_fingerprint={'synthetic': 'fingerprint'}, evaluation_phase='post_reveal')
        self.request = fixture.inspect()
        self.bundles = {'synthetic': self.bundle}
        self.statuses = {'synthetic': {'effective_status': 'ACTIVE', 'lifecycle': {
            'actions': [{'artifact_id': action['execution_id'], 'status': 'active'}],
            'decisions': [{'artifact_id': 'relation:0', 'status': 'active'}],
            'reviews': [{'artifact_id': 'review:synthetic', 'status': 'active'}]}}}
        # Bundle-schema tests live in video_contracts; this fixture isolates the
        # new transport while still exercising real action/range/review checks.
        status_check = patch('content_os.phrase_review.status_matches', return_value=True)
        self.status_check = status_check.start(); self.addCleanup(status_check.stop)
        row = self.request['operations'][0]; selection = row['selection']; text = self.bundle['source_snapshot']['passage']
        decision = {'operation_id': row['operation_id'], 'selection': deepcopy(selection),
            'proposed_operation_sha': sha(row['proposed_operation']),
            'evidence_container_refs': row['evidence_container_refs'],
            'disposition': 'SUPPORTED_WITH_CONSTRAINTS', 'semantic_role': 'synthetic context',
            'judgement': 'Synthetic reviewed grouping, conditional on the full source sentence.',
            'basis': 'Exact synthetic action and relation evidence.',
            'allowed_use': 'Focus this range without changing its subject.',
            'prohibited_inferences': ['Do not infer an opposite factual claim.'],
            'execution': {'primitives': ['focus_in_context'], 'relation_ref': self.request['relation_ref'],
                'keep_context': [{**selection, 'start': 0, 'end': len(text), 'quote': text}]}}
        self.authored = {'revision_id': 'synthetic-r1', 'reviewer': 'synthetic-ai-host',
            'reviewer_kind': 'ai_host', 'independent_human_certified': False,
            'review_note': 'Synthetic semantic judgement supplied explicitly.', 'decisions': [decision]}
        self.review, self.state = self.freeze()
        self.plan = bounded_plan(self.review)

    def freeze(self):
        return freeze_phrase_review(self.request, self.bundles, self.statuses, self.authored)

    def consume(self):
        return consume_phrase_review(self.request, self.review, self.state, self.bundles, self.statuses, self.plan)

    def reseal_state(self):
        self.state['status_sha'] = sha({k: v for k, v in self.state.items() if k != 'status_sha'})

    def test_exact_current_review_does_not_modify_request_or_bundle(self):
        before = sha([self.request, self.bundle])
        result = self.consume()
        self.assertEqual(result['gate'], 'READY_FOR_BOUNDED_G2')
        self.assertFalse(result['independent_human_certified'])
        self.assertFalse(result['public_render_ready'])
        self.assertEqual(self.request['status'], 'HOLD_MISSING_FINE_ANNOTATION')
        self.assertEqual(before, sha([self.request, self.bundle]))
        self.status_check.assert_called_with(self.bundle, self.statuses['synthetic'])

    def test_partial_semantic_support_is_hold_not_boolean_unlock(self):
        self.authored['decisions'][0]['disposition'] = 'HOLD'
        self.review, self.state = self.freeze(); self.plan = bounded_plan(self.review)
        result = self.consume()
        self.assertEqual(result['gate'], 'HOLD')
        self.assertEqual(result['accepted_operation_ids'], [])

    def test_withdrawn_phrase_operation_and_whole_review_hold(self):
        for field in ('operation', 'review'):
            original = deepcopy(self.state)
            if field == 'operation': self.state['operation_states'][0]['status'] = 'withdrawn'
            else: self.state['effective_status'] = 'WITHDRAWN'
            self.reseal_state()
            self.assertEqual(self.consume()['gate'], 'HOLD')
            self.state = original

    def test_changed_current_status_cannot_reuse_prior_review(self):
        self.statuses['synthetic']['changed_at'] = 'new-upstream-revision'
        with self.assertRaisesRegex(ValueError, 'binding'): self.consume()

    def test_current_action_relation_and_review_withdrawals_block(self):
        for key in ('actions', 'decisions', 'reviews'):
            self.statuses['synthetic']['lifecycle'][key][0]['status'] = 'withdrawn'
            with self.assertRaises(ValueError): self.consume()
            self.statuses['synthetic']['lifecycle'][key][0]['status'] = 'active'

    def test_same_label_different_action_or_relation_is_rejected(self):
        for key in ('action_ref', 'relation_ref'):
            original = self.request[key]['sha']; self.request[key]['sha'] = 'wrong-exact-source'
            with self.assertRaises(ValueError): self.consume()
            self.request[key]['sha'] = original

    def test_renderer_extra_primitive_or_changed_range_is_rejected(self):
        for mutate in (lambda p: p['operations'][0]['execution']['primitives'].append('answer_unlock'),
                       lambda p: p['operations'][0]['selection'].update(start=0),
                       lambda p: p.update(approved=True)):
            old = deepcopy(self.plan); mutate(self.plan)
            with self.assertRaisesRegex(ValueError, 'Renderer plan'): self.consume()
            self.plan = old

    def test_empty_context_range_is_rejected(self):
        context = self.authored['decisions'][0]['execution']['keep_context'][0]
        context['start'] = context['end']
        with self.assertRaisesRegex(ValueError, 'Context'): self.freeze()

    def test_context_from_different_source_ref_is_rejected(self):
        context = self.authored['decisions'][0]['execution']['keep_context'][0]
        self.bundle['alternate_passage'] = self.bundle['source_snapshot']['passage']
        context['source_ref'] = {**context['source_ref'], 'pointer': '/alternate_passage'}
        with self.assertRaisesRegex(ValueError, 'Context'): self.freeze()

    def test_human_credential_and_public_upgrade_are_rejected(self):
        self.authored['independent_human_certified'] = True
        with self.assertRaisesRegex(ValueError, 'AI host'): self.freeze()
        self.review['public_render_ready'] = True
        self.review['review_sha'] = sha({k: v for k, v in self.review.items() if k != 'review_sha'})
        with self.assertRaises(ValueError): self.consume()


if __name__ == '__main__':
    unittest.main()
