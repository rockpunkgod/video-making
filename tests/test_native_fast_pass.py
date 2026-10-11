"""Synthetic native authoring checks; never launches Adobe or certifies taste."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

from video_contracts import sha

path=Path(__file__).resolve().parents[1]/'ae/experiments/reality-cognitive-fast/run.py'
loader=importlib.util.spec_from_file_location('native_fast_checks',path)
native=importlib.util.module_from_spec(loader);loader.loader.exec_module(native)

class NativeFastPassTests(unittest.TestCase):
    def setUp(self):
        action={'execution_id':'synthetic-remove-a','output':{'kind':'candidate_decision','candidate':'A','effect':'eliminate'}}
        self.bundle={'asset_id':'s','source_snapshot':{'question_id':'q','options':{'A':'a','B':'b'},'action_executions':[action]}}
        ref={'asset_id':'s','pointer':'/source_snapshot/action_executions/0','sha':sha(action)}
        event={'scene_id':'s1','question_id':'q','source_refs':[ref],'candidate':'A','effect':'eliminate',
            'compare_start':1,'decision_start':2,'decision_end':3,'confirmation_start':4}
        source_ref={'asset_id':'s','pointer':'/source_snapshot/stem','sha':sha('Plain text')}
        self.parent={'plan_sha':'parent','method_id':'synthetic','selection':{'action_ids':['synthetic-remove-a']},
            'candidate_events':[event],'objects':[{'id':'source','text':'Plain text','range':[0,10],'source_ref':source_ref}]}
        self.spec={'kind':'reality_cognitive_native_fast_pass','parent_plan_sha':'parent','method_id':'synthetic',
            'selection':self.parent['selection'],'frames':120,'duration':5,'canvas':[3840,2160,24],'variants':['A','B'],
            'candidate_events':[event],'candidate_mask':[[0,3],[3,2],[5,2]],'answer_event':None,'replays':[],
            'human_review':'PENDING','public_render_ready':False,
            'columns':[{'object_id':'source','source_ref':source_ref,'words':[
                {'id':'w1','text':'Plain','range':[0,5]},{'id':'w2','text':'text','range':[6,10]}]}],
            'projections':[{'id':'p1','origin_word_id':'w1','path':[[0,'ORIGIN'],[5,[1,2,3]]],
                'opacity':[[0,0],[5,0]],'scale':[[0,[100]*3],[5,[100]*3]]}]}
        self.seal()
    def seal(self):
        self.spec.pop('spec_sha',None);self.spec['spec_sha']=sha(self.spec)
    def check(self):return native.validate_spec(self.spec,self.parent,self.bundle)
    def test_valid_existing_action_and_full_source(self):
        result=self.check();self.assertEqual(result['candidate_states'][0]['after'],['B'])
    def test_new_action_or_role_credit_cannot_be_borrowed(self):
        self.spec['candidate_events']=deepcopy(self.spec['candidate_events']);self.spec['candidate_events'][0]['candidate']='B';self.seal()
        with self.assertRaises(ValueError):self.check()
    def test_missing_source_word_rejected(self):
        self.spec['columns'][0]['words'].pop();self.seal()
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.check()
    def test_changed_word_or_orphan_projection_rejected(self):
        self.spec['projections'][0]['origin_word_id']='not-a-source';self.seal()
        with self.assertRaises(ValueError):self.check()
    def test_candidate_mask_cannot_announce_result_early(self):
        self.spec['candidate_mask'][1][0]=2;self.seal()
        with self.assertRaises(ValueError):self.check()
    def test_publication_answer_and_replay_are_not_earned(self):
        for key,value in [('public_render_ready',True),('answer_event',{'candidate':'B'}),('replays',[{}])]:
            s=deepcopy(self.spec);self.spec[key]=value;self.seal()
            with self.assertRaises(ValueError):self.check()
            self.spec=s
    def test_ambiguous_projection_time_rejected(self):
        self.spec['projections'][0]['opacity']=[[0,0],[0,100],[5,0]];self.seal()
        with self.assertRaises(ValueError):self.check()
    def native_readback(self):
        def world(name,text,identifier):return {'name':name,'layer_id':identifier,'text':text,'threeD':True,
            'sourceTextKeys':0,'sourceTextExpression':False,'position':{'value':[1,2,3],'keys':[]},'comment':''}
        base=[world('w1','Plain',1),world('w2','text',2),world('p1','Plain',3)]
        base[2]['position']={'value':[1,2,3],'keys':[[0,[1,2,3]]]}
        base[2]['comment']='{"origin_layer_id":1}'
        base.append({'name':'GUIDED_CAMERA','layer_id':4,'comment':'','focus_error':'','dof':1,
                     'focus':{'expression':'synthetic physical focus'},'position':{},'look':{}})
        comps={}
        for variant in ('A','B'):
            samples=[{'frame':n,'mask':3 if n<72 else 2,'camera':[0 if variant=='A' else n/100,0,-10],
                      'look':[0,0,0],'focus':10} for n in range(120)]
            comps[variant]={'canvas':[3840,2160,24,5],'layers':deepcopy(base),'samples':samples}
        return {'spec_sha':self.spec['spec_sha'],'compositions':comps}
    def test_native_control_allows_camera_motion_only(self):
        self.assertTrue(native.check_native_audit(self.spec,self.native_readback())['camera_only_control'])
    def test_native_control_rejects_other_visual_changes(self):
        raw=self.native_readback();raw['compositions']['B']['layers'][0]['text']='Rewritten'
        with self.assertRaises(ValueError):native.check_native_audit(self.spec,raw)
        raw=self.native_readback();raw['compositions']['B']['layers'][0]['opacity']={'value':50,'keys':[]}
        with self.assertRaisesRegex(ValueError,'more than camera'):native.check_native_audit(self.spec,raw)

if __name__=='__main__':unittest.main()
