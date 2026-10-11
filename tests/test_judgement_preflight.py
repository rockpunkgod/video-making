"""Synthetic-only checks; a sentence review cannot license new word operations."""
from copy import deepcopy
import unittest

from video_contracts import sha, pointer
from ae_production.judgement_preflight import (
    inspect_phrase_requests, bind_existing_scenes, excerpt_boundaries, candidate_prefix)


class PhraseRequestTests(unittest.TestCase):
    def setUp(self):
        text = 'Readers use existing hours differently.'
        evidence = {'field': 'passage', 'start': 0, 'end': len(text), 'quote': text}
        action = {'execution_id': 'synthetic-action', 'review_status': 'reviewed', 'evidence': [evidence],
                  'output': {'kind': 'candidate_decision', 'candidate': 'B',
                             'effect': 'eliminate', 'relation_index': 0}}
        relation = {'candidate': 'B', 'effect': 'eliminate', 'review_status': 'reviewed', 'evidence': [evidence]}
        self.bundle = {'source_snapshot': {'question_id': 'synthetic-q', 'passage': text,
            'options': {'A': 'synthetic A', 'B': 'synthetic B', 'C': 'synthetic C'},
            'relations': [relation], 'action_executions': [action]},
            'reviews': [{'artifact_id': 'review:synthetic', 'sha': 'synthetic-review-sha', 'level': 'ai_reviewed',
                         'record': {'own_execution_ids': ['synthetic-action'],
                                    'checks': {k: True for k in ('trigger','action','evidence','role','stop')}}}],
            'lifecycle': {'reviews': [{'artifact_id': 'review:synthetic', 'status': 'active'}]}}
        self.event = {'scene_id': 'B06', 'question_id': 'synthetic-q', 'candidate': 'B', 'effect': 'eliminate',
            'compare_start': 1, 'decision_start': 2, 'decision_end': 3, 'confirmation_start': 4,
            'source_refs': [{'asset_id': 'synthetic', 'pointer': '/source_snapshot/action_executions/0', 'sha': sha(action)},
                            {'asset_id': 'synthetic', 'pointer': '/source_snapshot/relations/0', 'sha': sha(relation)}]}
        self.operations = [{'operation_id': 'synthetic-focus', 'proposed_operation': 'isolate reviewed word group',
            'selection': {'source_ref': {'asset_id': 'synthetic', 'pointer': '/source_snapshot/passage', 'sha': sha(text)},
                          'field': 'passage', 'start': 12, 'end': 26, 'quote': 'existing hours'}}]

    def inspect(self):
        return inspect_phrase_requests({'synthetic': self.bundle}, self.event, self.operations)

    def test_exact_lexical_range_does_not_upgrade_sentence_review(self):
        before = sha(self.bundle)
        result = self.inspect()
        self.assertEqual(result['operations'][0]['lexical_range'], 'PASS')
        self.assertEqual(result['operations'][0]['operation_authorization'], 'MISSING')
        self.assertEqual(result['status'], 'HOLD_MISSING_FINE_ANNOTATION')
        self.assertFalse(result['teaching_review_created'])
        self.assertFalse(result['public_render_ready'])
        self.assertEqual(sha(self.bundle), before)
        self.assertEqual(result, self.inspect())

    def test_word_range_or_source_tampering_rejected(self):
        self.operations[0]['selection']['end'] += 1
        with self.assertRaises(ValueError): self.inspect()
        self.operations[0]['selection']['end'] -= 1
        self.bundle['source_snapshot']['passage'] += ' Changed.'
        with self.assertRaisesRegex(ValueError, 'Changed'): self.inspect()

    def test_cross_question_and_wrong_field_rejected(self):
        self.operations[0]['selection']['source_ref']['asset_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'Cross-question'): self.inspect()
        self.operations[0]['selection']['source_ref']['asset_id'] = 'synthetic'
        self.operations[0]['selection']['field'] = 'option:B'
        with self.assertRaisesRegex(ValueError, 'field'): self.inspect()

    def test_unreviewed_or_withdrawn_action_cannot_support_request(self):
        self.bundle['lifecycle']['reviews'][0]['status'] = 'withdrawn'
        with self.assertRaisesRegex(ValueError, 'Active review'): self.inspect()

    def test_prefix_is_computed_from_prior_actions(self):
        first = deepcopy(self.bundle['source_snapshot']['action_executions'][0])
        first['execution_id'] = 'synthetic-before'
        first['output']['candidate'] = 'A'
        self.bundle['source_snapshot']['action_executions'].append(first)
        event = {**self.event, 'scene_id': 'B05', 'candidate': 'A',
                 'compare_start': 0, 'decision_start': .1, 'decision_end': .2, 'confirmation_start': .3,
                 'source_refs': [{'asset_id': 'synthetic', 'pointer': '/source_snapshot/action_executions/1', 'sha': sha(first)}]}
        result = candidate_prefix({'events': [event, self.event]}, {'synthetic': self.bundle}, 'B06')
        self.assertEqual(result['selected']['before'], ['B', 'C'])
        self.assertEqual(result['selected']['after'], ['C'])
        self.assertEqual(len(result['prefix_event_refs']), 1)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        from tests.test_audience_engagement import AudienceEngagementTests
        AudienceEngagementTests.setUpClass()
        fixture = AudienceEngagementTests('test_deterministic_source_bound_plan_not_public_or_measured')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.episode, self.statuses, self.editorial = fixture.episode, fixture.statuses, fixture.direction
        self.mapping, scenes, nodes = {}, [], []
        for q in self.episode['questions']:
            self.mapping[q['question_id']] = {}
            for b in q['narrative_beats']:
                sid = str(len(scenes))
                self.mapping[q['question_id']][b['beat_id']] = [sid]
                scenes.append({'scene_id': sid, 'time_range': [0, 1], 'source_refs': b['source_refs']})
                nodes.append({'node_id': sid, 'in_point': 0, 'out_point': 1, 'source_refs': b['source_refs']})
        self.native = {'scenes': scenes, 'public_render_ready': False}
        self.spec = {'canvas': {'duration': 1}, 'nodes': nodes, 'spec_sha': 'synthetic-spec'}

    def handoff(self):
        from creative_os.audience_engagement import design_engagement, director_handoff
        projected, audit = bind_existing_scenes(self.episode, self.native, self.spec, self.mapping)
        plan = design_engagement(self.episode, self.statuses, self.editorial)
        return director_handoff(plan, self.episode, self.statuses, self.editorial, projected, self.mapping)

    def test_complete_binding_is_planned_and_does_not_mutate_old_direction(self):
        before = sha(self.native)
        result = self.handoff()
        self.assertEqual(result['actual_media_mapping'], 'UNAVAILABLE')
        self.assertEqual(len(result['rows']), sum(len(q['narrative_beats']) for q in self.episode['questions']))
        self.assertEqual(sha(self.native), before)
        self.assertFalse(result['public_render_ready'])

    def test_missing_beat_or_dangling_scene_fails(self):
        q = next(iter(self.mapping)); b = next(iter(self.mapping[q]))
        original = self.mapping[q].pop(b)
        with self.assertRaisesRegex(ValueError, 'Every source beat'): self.handoff()
        self.mapping[q][b] = ['nonexistent']
        with self.assertRaises(KeyError): self.handoff()
        self.mapping[q][b] = original

    def test_cross_question_scene_fails(self):
        qs = list(self.mapping)
        self.mapping[qs[0]][next(iter(self.mapping[qs[0]]))] = next(iter(self.mapping[qs[1]].values()))
        with self.assertRaisesRegex(ValueError, 'Cross-question'): self.handoff()

    def test_missing_native_source_or_duplicate_identity_fails(self):
        self.spec['nodes'] = []
        with self.assertRaisesRegex(ValueError, 'no corresponding source'): self.handoff()
        self.native['scenes'].append(deepcopy(self.native['scenes'][0]))
        with self.assertRaisesRegex(ValueError, 'Unique'): self.handoff()

    def test_invalid_common_source_is_not_an_authorized_intersection(self):
        self.native['scenes'][0]['source_refs'][0]['sha'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'Changed frozen'): self.handoff()

    def test_valid_source_without_shared_beat_reference_fails(self):
        bundle = self.episode['questions'][0]['package']['source_items'][0]
        path = '/source_snapshot/question_id'
        ref = {'asset_id': bundle['asset_id'], 'pointer': path, 'sha': sha(pointer(bundle, path))}
        self.native['scenes'][0]['source_refs'] = [ref]
        self.spec['nodes'][0]['source_refs'] = [ref]
        with self.assertRaisesRegex(ValueError, 'no shared bound source'): self.handoff()

    def test_duplicate_scene_assignment_is_rejected(self):
        q = next(iter(self.mapping)); b = next(iter(self.mapping[q]))
        self.mapping[q][b] *= 2
        with self.assertRaisesRegex(ValueError, 'unique existing'): self.handoff()


class ExcerptTests(unittest.TestCase):
    def test_context_retains_full_voice_and_does_not_claim_actual_media(self):
        direction = {'scenes': [{'scene_id': 'B06', 'time_range': [10, 20]}],
                     'events': [{'scene_id': 'B05', 'compare_start': 5},
                                {'scene_id': 'B07', 'compare_start': 22, 'decision_start': 27}]}
        voice = {'id': 'synthetic-B06', 'start': 10.1, 'end': 19.1, 'duration': 9}
        result = excerpt_boundaries(direction, [voice])
        self.assertEqual(result['context_original_frames'], [120, 576])
        self.assertEqual(result['actual_new_media_mapping'], 'UNAVAILABLE')
        voice['end'] = 20.1
        with self.assertRaisesRegex(ValueError, 'truncate'): excerpt_boundaries(direction, [voice])
