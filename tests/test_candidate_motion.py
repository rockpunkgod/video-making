import unittest
from copy import deepcopy
from video_contracts import sha
from ae_production.candidate_motion import audit_candidate_events


class CandidateMotionTests(unittest.TestCase):
    def setUp(self):
        self.b={'source_snapshot':{'question_id':'synthetic-q','options':{'A':'a','B':'b'},'action_executions':[
            {'execution_id':'remove-a','output':{'kind':'candidate_decision','candidate':'A','effect':'eliminate'}},
            {'execution_id':'keep-b','output':{'kind':'candidate_decision','candidate':'B','effect':'retain'}}]},
            'analysis':{'answer':'B','answer_verification':{'closed':True,'candidate_coverage_complete':True,'unique_supported_candidate':True}}}
        self.events=[]
        for i,a in enumerate(self.b['source_snapshot']['action_executions']):
            self.events.append({'scene_id':str(i),'question_id':'synthetic-q','source_refs':[{'asset_id':'s','pointer':f'/source_snapshot/action_executions/{i}','sha':sha(a)}],
                'candidate':a['output']['candidate'],'effect':a['output']['effect'],
                'compare_start':i*5,'decision_start':i*5+1,'decision_end':i*5+2,'confirmation_start':i*5+3})
        self.answer={'candidate':'B','time':9,'source_ref':{'asset_id':'s','pointer':'/analysis/answer','sha':sha('B')}}

    def test_real_state_change_then_closed_answer(self):
        r=audit_candidate_events(self.events,{'s':self.b},[self.answer])
        self.assertEqual(r['events'][0]['after'],['B']);self.assertFalse(r['public_render_ready'])

    def test_animation_cannot_upgrade_retention_to_elimination(self):
        e=deepcopy(self.events);e[1]['effect']='eliminate'
        with self.assertRaises(ValueError):audit_candidate_events(e,{'s':self.b})

    def test_confirmation_cannot_precede_action(self):
        e=deepcopy(self.events);e[0]['confirmation_start']=.5
        with self.assertRaises(ValueError):audit_candidate_events(e,{'s':self.b})

    def test_changed_source_and_cross_question_fail(self):
        for field,value in [('question_id','other-q')]:
            e=deepcopy(self.events);e[0][field]=value
            with self.assertRaises(ValueError):audit_candidate_events(e,{'s':self.b})
        b=deepcopy(self.b);b['source_snapshot']['action_executions'][0]['output']['effect']='retain'
        with self.assertRaises(ValueError):audit_candidate_events(self.events,{'s':b})

    def test_no_premature_or_unsupported_answer(self):
        a=deepcopy(self.answer);a['time']=1
        with self.assertRaises(ValueError):audit_candidate_events(self.events,{'s':self.b},[a])
        b=deepcopy(self.b);b['analysis']['answer_verification']['closed']=False
        with self.assertRaises(ValueError):audit_candidate_events(self.events,{'s':b},[self.answer])

    def test_replay_cannot_double_count(self):
        with self.assertRaises(ValueError):audit_candidate_events(self.events+[self.events[0]],{'s':self.b})

    def test_remaining_candidate_does_not_replace_its_own_check(self):
        with self.assertRaises(ValueError):audit_candidate_events(self.events[:1],{'s':self.b},[self.answer])
