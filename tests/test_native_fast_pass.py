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
        base[2]['opacity']={'keys':deepcopy(self.spec['projections'][0]['opacity'])}
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
    def test_world_handoff_cannot_delete_source_or_accept_invalid_opacity(self):
        for rows in ([[0,100],[5,0]],[[0,100],[5,101]],[[0,100],[5,float('nan')]],
                     [[0,100],[5,True]],[[0,100],[0,4],[5,100]]):
            with self.assertRaises(ValueError):native.validate_world_visibility(rows,5)
        native.validate_world_visibility([[0,100],[1,4],[4,4],[5,100]],5)
    def test_native_handoff_requires_actual_authored_opacity(self):
        track=[[0,100],[1,4],[5,100]]
        self.spec['columns'][0]['words'][0]['opacity_track']=track;self.seal()
        raw=self.native_readback()
        for comp in raw['compositions'].values():comp['layers'][0]['opacity']={'keys':deepcopy(track)}
        self.assertTrue(native.check_native_audit(self.spec,raw)['camera_only_control'])
        # Both cameras can match one another while both violate the spec.
        for comp in raw['compositions'].values():comp['layers'][0]['opacity']['keys'][1][1]=24
        with self.assertRaisesRegex(ValueError,'visibility differs'):native.check_native_audit(self.spec,raw)
    def test_projection_must_match_the_authored_visibility_in_both_variants(self):
        raw=self.native_readback()
        for comp in raw['compositions'].values():comp['layers'][2]['opacity']['keys'][0][1]=50
        with self.assertRaisesRegex(ValueError,'projection changed'):native.check_native_audit(self.spec,raw)
    def test_comparison_requires_bound_native_baselines_and_uniform_size(self):
        self.spec['text_alignment']='shared_baseline'
        self.spec['comparison_layout']=[{'id':'row','baseline_y':20,'font_size':40,'settled_at':4,'projection_ids':['p1']}]
        self.seal();self.check();raw=self.native_readback()
        for comp in raw['compositions'].values():
            for layer in comp['layers'][:2]:layer['anchor']={'value':[0,0,0],'keys':[]}
            comp['comparison_rows']=[{'id':'row','words':[{'id':'p1','position':[2,40,-4],
                'anchor':[0,0,0],'effective_font_size':80}]}]
        self.assertTrue(native.check_native_audit(self.spec,raw)['camera_only_control'])
        for comp in raw['compositions'].values():comp['comparison_rows'][0]['words'][0]['position'][1]=42
        with self.assertRaisesRegex(ValueError,'baseline or type size'):native.check_native_audit(self.spec,raw)
    def test_comparison_cannot_borrow_another_projection_or_repeat_a_row_word(self):
        self.spec['text_alignment']='shared_baseline'
        row={'id':'row','baseline_y':20,'font_size':40,'settled_at':4,'projection_ids':['missing']}
        self.spec['comparison_layout']=[row];self.seal()
        with self.assertRaisesRegex(ValueError,'row binding'):self.check()
        row['projection_ids']=['p1'];self.spec['comparison_layout'].append(deepcopy(row));self.seal()
        with self.assertRaisesRegex(ValueError,'multiple comparison rows'):self.check()

if __name__=='__main__':unittest.main()
