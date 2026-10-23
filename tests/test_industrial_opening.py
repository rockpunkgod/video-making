"""B+ opens on real task scenes; no new renderer or human creative credit."""
from copy import deepcopy
import unittest
from creative_os.audience_engagement import validate_original_task_opening,require_hook_decision


class IndustrialOpening(unittest.TestCase):
    def setUp(self):
        self.author={'production_policy':'industrial_bplus_v1',
            'audience_opening':{'strategy':'original_task','scene_id':'task','payoff_scene_id':'check',
                                'viewing_question':'What does this number count?'},
            'scenes':[{'id':'task','kind':'task','world':'exam','voice_ids':['intro'],'source_refs':['actual task']},
                      {'id':'check','kind':'compare','world':'exam','event':'eliminate',
                       'source_refs':['source'], 'action_refs':['action'],'terminal_refs':['terminal']}]}

    def test_existing_task_consumer_has_no_user_approval_claim(self):
        result=validate_original_task_opening(self.author)
        self.assertEqual(result['status'],'BOUND_AUTHOR_ORIGINAL_TASK')
        self.assertEqual(result['human_review'],'PENDING')
        require_hook_decision(self.author,operation='prepare')

    def test_missing_payoff_or_another_question_cannot_authorize_opening(self):
        for field,value in [('world','other'),('event','locate'),('terminal_refs',[]),('action_refs',[])]:
            a=deepcopy(self.author);a['scenes'][1][field]=value
            with self.assertRaises(ValueError):validate_original_task_opening(a)

    def test_legacy_missing_hook_still_rejected(self):
        self.author.pop('production_policy')
        with self.assertRaises(ValueError):require_hook_decision(self.author,operation='build')

    def test_opening_digest_changes_with_actual_task(self):
        before=validate_original_task_opening(self.author)
        self.author['scenes'][0]['source_refs']=['changed actual task']
        self.assertNotEqual(before['opening_scene_sha'],validate_original_task_opening(self.author)['opening_scene_sha'])
