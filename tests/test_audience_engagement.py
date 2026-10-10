"""Synthetic controls for the audience-directed method episode. Not a taste test."""
from copy import deepcopy
import unittest

from tests.test_method_episode import MethodEpisodeTests
from video_contracts import seal
from creative_os.audience_engagement import design_engagement, validate_engagement

class AudienceEngagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): MethodEpisodeTests.setUpClass()

    def setUp(self):
        base=MethodEpisodeTests('test_two_independent_questions_no_public_self_approval')
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.episode,self.statuses=base.plan,base.statuses
        self.direction={'schema_version':'0.1.0','content_profile':'FREE_SHOWCASE',
            'opening':{'question_id':base.plan['questions'][0]['question_id'],
                'beat_id':base.plan['questions'][0]['narrative_beats'][0]['beat_id'],
                'hook_strategy':'actual_problem','promise_scope':'none'},'questions':[]}
        for index,q in enumerate(self.episode['questions']):
            beats=[]
            for b in q['narrative_beats']:
                f=b['function']
                beats.append({'beat_id':b['beat_id'],
                    'engagement_function':'release' if f=='payoff' else 'recognition',
                    'viewer_action':'compare' if f=='evidence_alignment' else 'read' if f=='observe' else 'watch',
                    'playback':'payoff_hold' if f=='payoff' else 'read_hold' if f=='observe' else
                        'local_replay' if index==0 and f=='evidence_alignment' else 'guided_inline',
                    'energy':'peak' if f=='payoff' else 'quiet' if f=='observe' else 'building',
                    'fresh_information':f in ('evidence_alignment','payoff')})
            self.direction['questions'].append({'question_id':q['question_id'],
                'speed_strategy':'selected_replay' if index==0 else 'guided_inline',
                'novelty':'none' if index==0 else 'new_evidence',
                'payoff_scope':q['payoff']['result_scope'],'beats':beats})

    def test_deterministic_source_bound_plan_not_public_or_measured(self):
        plan=design_engagement(self.episode,self.statuses,self.direction)
        self.assertEqual(plan,design_engagement(self.episode,self.statuses,self.direction))
        self.assertTrue(plan['consumption_allowed'])
        self.assertFalse(plan['public_render_ready'])
        self.assertEqual(plan['human_review'],'PENDING')
        self.assertEqual(plan['propagation_metrics'],'UNKNOWN')
        self.assertEqual(validate_engagement(plan,self.episode,self.statuses,self.direction)['status'],'PASS')

    def test_unearned_answer_in_hook_fails(self):
        self.direction['opening']['promise_scope']='answer'
        with self.assertRaisesRegex(ValueError,'overclaims'):
            design_engagement(self.episode,self.statuses,self.direction)

    def test_cross_question_reorder_and_payoff_promotion_fail(self):
        other=deepcopy(self.direction)
        other['questions'].reverse()
        with self.assertRaisesRegex(ValueError,'order'):
            design_engagement(self.episode,self.statuses,other)
        other=deepcopy(self.direction)
        other['questions'][1]['payoff_scope']='answer'
        with self.assertRaisesRegex(ValueError,'promoted'):
            design_engagement(self.episode,self.statuses,other)

    def test_reveal_cannot_precede_real_payoff(self):
        self.direction['questions'][0]['beats'][0]['engagement_function']='release'
        with self.assertRaisesRegex(ValueError,'Release'):
            design_engagement(self.episode,self.statuses,self.direction)

    def test_source_withdrawal_blocks_creative_consumption(self):
        statuses=deepcopy(self.statuses)
        asset=self.episode['questions'][0]['package']['source_items'][0]['asset_id']
        statuses[asset]['effective_status']='WITHDRAWN'
        statuses[asset]=seal(statuses[asset])
        with self.assertRaisesRegex(ValueError,'Withdrawn'):
            design_engagement(self.episode,statuses,self.direction)

    def test_changed_plan_and_self_signed_approval_fail_replay(self):
        plan=design_engagement(self.episode,self.statuses,self.direction)
        changed=deepcopy(self.direction)
        changed['questions'][0]['beats'][0]['energy']='quiet'
        with self.assertRaisesRegex(ValueError,'Stale'):
            validate_engagement(plan,self.episode,self.statuses,changed)
        wrong=deepcopy(plan);wrong['human_review']='PASS'
        with self.assertRaisesRegex(ValueError,'self-approved'):
            validate_engagement(wrong,self.episode,self.statuses,self.direction)

    def test_reading_and_participation_risks_are_advisory(self):
        for q in self.direction['questions']:
            for b in q['beats']:
                if b['playback']=='read_hold': b['playback']='guided_inline'
                if b['viewer_action']=='compare': b['viewer_action']='watch'
        result=design_engagement(self.episode,self.statuses,self.direction)
        self.assertTrue(any('READING_SPACE' in x for x in result['quality_audit']['risk_flags']))
        self.assertIn('VIEWER_AGENCY_UNDERUSED',result['quality_audit']['risk_flags'])
        self.assertTrue(result['consumption_allowed'])
        self.assertEqual(result['human_review'],'PENDING')

if __name__=='__main__': unittest.main()
