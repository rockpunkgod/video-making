"""Synthetic editorial proxies; no real exam, semantic or human acceptance."""
from copy import deepcopy
import unittest

from ae_production.experience_proof import (check_objects, check_passage_decisions, checked_reference,
                                          check_replays, check_method_binding)
from video_contracts import sha


class ExperienceProofTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {'asset_id': 'synthetic', 'payload': {'passage': 'A clear bounded clue.',
            'questions': [{'question_id': 'q', 'options': {'A': 'wrong', 'B': 'supported'}}],
            'review': {'decisions': [
                {'question_id': 'q', 'candidate': 'A', 'effect': 'eliminate', 'method_id': None,
                 'basis': 'direct_text_review', 'rationale': 'Synthetic reviewed contrast'},
                {'question_id': 'q', 'candidate': 'B', 'effect': 'retain', 'method_id': None,
                 'basis': 'direct_text_review', 'rationale': 'Synthetic reviewed support'}]}}}
        self.events = [{'source_ref': self.ref(f'/payload/review/decisions/{i}'),
                        'compare_start': i*3, 'decision_start': i*3+1,
                        'decision_end': i*3+2, 'confirmation_start': i*3+2.5} for i in range(2)]
        self.object = {'id': 'clue', 'source_ref': self.ref('/payload/passage'), 'range': [2, 7],
                       'text': 'clear', 'authority_refs': [self.ref('/payload/review/decisions/0')]}

    def ref(self, path):
        from video_contracts import pointer
        return {'asset_id': 'synthetic', 'pointer': path, 'sha': sha(pointer(self.bundle, path))}

    def test_real_current_transition_closes_only_after_both_comparisons(self):
        result = check_passage_decisions(self.events, self.bundle, 'q', {'candidate': 'B', 'time': 6})
        self.assertEqual(result[0]['before'], ['A', 'B'])
        self.assertEqual(result[-1]['after'], ['B'])

    def test_supported_clue_does_not_alone_authorize_final_answer(self):
        with self.assertRaises(ValueError):
            check_passage_decisions(self.events[1:], self.bundle, 'q', {'candidate': 'B', 'time': 6})

    def test_replay_cannot_be_counted_as_another_decision(self):
        duplicate = deepcopy(self.events[0]); duplicate.update(compare_start=6,decision_start=7,decision_end=8,confirmation_start=9)
        with self.assertRaises(ValueError):
            check_passage_decisions(self.events+[duplicate], self.bundle, 'q')

    def test_cross_question_decision_rejected(self):
        self.bundle['payload']['review']['decisions'][0]['question_id']='another'
        self.events[0]['source_ref']=self.ref('/payload/review/decisions/0')
        with self.assertRaises(ValueError): check_passage_decisions(self.events, self.bundle, 'q')

    def test_direct_review_cannot_be_relabelled_as_method_success(self):
        self.bundle['payload']['review']['decisions'][0]['method_id']='synthetic-method'
        self.events[0]['source_ref']=self.ref('/payload/review/decisions/0')
        with self.assertRaises(ValueError): check_passage_decisions(self.events, self.bundle, 'q')

    def test_new_word_cannot_enter_display_through_motion(self):
        check_objects([self.object],self.bundle)
        self.object['text']='decisive'
        with self.assertRaises(ValueError): check_objects([self.object],self.bundle)

    def test_correct_lexical_range_is_not_permission_without_authority(self):
        self.object['authority_refs']=[]
        with self.assertRaises(ValueError): check_objects([self.object],self.bundle)

    def test_stale_or_foreign_reference_rejected(self):
        reference=self.ref('/payload/passage')
        self.bundle['payload']['passage']='A changed clue.'
        with self.assertRaises(ValueError): checked_reference(reference,self.bundle)
        reference=self.ref('/payload/passage'); reference['asset_id']='foreign'
        with self.assertRaises(ValueError): checked_reference(reference,self.bundle)

    def test_result_cannot_precede_observation(self):
        self.events[0]['decision_start']=0
        with self.assertRaises(ValueError): check_passage_decisions(self.events,self.bundle,'q')

    def replay_plan(self):
        self.bundle['kind']='frozen_reviewed_passage'
        return {'question_id':'q','fps':24,'frame_count':240,'candidate_events':self.events,
                'replays':[{'kind':'observation_only','frame_range':[144,216],
                            'authority_ref':self.events[0]['source_ref'],'before':['B'],'after':['B']}]}

    def test_observational_replay_does_not_revive_excluded_option(self):
        plan=self.replay_plan();check_replays(plan,self.bundle)
        plan['replays'][0].update(before=['A','B'],after=['A','B'])
        with self.assertRaises(ValueError):check_replays(plan,self.bundle)

    def test_replay_cannot_hide_an_additional_judgement_inside_its_window(self):
        plan=self.replay_plan();plan['replays'][0]['frame_range']=[96,216]
        with self.assertRaises(ValueError):check_replays(plan,self.bundle)

    def test_replay_must_bind_in_range_integer_frames(self):
        plan=self.replay_plan();plan['replays'][0]['frame_range']=[144,241]
        with self.assertRaises(ValueError):check_replays(plan,self.bundle)

    def test_proxy_cannot_change_frozen_method_version_or_role(self):
        self.bundle.update(kind='frozen_reviewed_passage')
        self.bundle['payload']['methods']=[{'method_id':'synthetic-method','version':'1','primary_role':'locator'}]
        plan={'method_id':'synthetic-method','method_version':'1','method_role':'locator'}
        check_method_binding(plan,self.bundle)
        plan['method_role']='decider'
        with self.assertRaises(ValueError):check_method_binding(plan,self.bundle)
        plan.update(method_role='locator',method_version='2')
        with self.assertRaises(ValueError):check_method_binding(plan,self.bundle)

    def test_action_selection_cannot_borrow_another_displayed_method_or_asset(self):
        self.bundle['methods']=[{'method_id':'synthetic-method','version':'1','primary_role':'reducer'}]
        plan={'method_id':'synthetic-method','method_version':'1','method_role':'reducer',
              'selection':{'asset_id':'synthetic','method_id':'synthetic-method'}}
        check_method_binding(plan,self.bundle)
        plan['selection']['method_id']='other-method'
        with self.assertRaises(ValueError):check_method_binding(plan,self.bundle)
        plan['selection'].update(method_id='synthetic-method',asset_id='foreign')
        with self.assertRaises(ValueError):check_method_binding(plan,self.bundle)


if __name__=='__main__': unittest.main()
