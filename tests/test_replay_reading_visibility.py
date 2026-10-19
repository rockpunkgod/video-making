"""Actual replay opacity evidence stays distinct from video or listening review."""
from copy import deepcopy
import json
import shutil
import subprocess
import unittest

from ae_production.authored_native import (
    CANDIDATE_READING_VISIBILITY_POLICY,
    REPLAY_READING_VISIBILITY_POLICY,
    replay_reading_visibility_readback,
    replay_reading_visibility_rows,
    validate_replay_reading_visibility,
)


class ReplayReadingVisibilityTests(unittest.TestCase):
    def fixture(self):
        p={'format':{'fps':24},'duration':10,'candidate_events':[],
           'worlds':{'toy':{'question':{'options':{'A':'It costs less.'}}}},
           'scenes':[{'id':'RECHECK','kind':'replay','world':'toy','candidate':'A',
             'start':2,'candidate_start':2.2,'settled':6,'end':8,'terminal_refs':[],
             'reading_events':[{'depart':3,'arrival':3.2,'end_time':4},
                               {'depart':4,'arrival':4.2,'end_time':5.5}]}]}
        n={'comp_id':1,'master_comp_id':2,'plan_sha256':'f'*64,
           'audit':{'replay_reading_visibility_policy':REPLAY_READING_VISIBILITY_POLICY}}
        spec=replay_reading_visibility_rows(p)[0]
        keys=[{'time':time,'value':value,'in_type':'BEZIER','out_type':'BEZIER',
               'in_ease':[0,55],'out_ease':[0,55]} for time,value in spec['required_keys']]
        # An earlier elimination's inherited keys are real source lineage,
        # not a reason to assume this recalled clone used to have no keys.
        keys=[{'time':0,'value':100},{'time':1,'value':38}]+keys
        row={'scene':spec['scene'],'layer':spec['layer'],'threeD':True,'parent':None,
             'enabled':True,'guide_layer':False,'text':spec['source_text'],
             'source_layer':spec['source_layer'],'source_text':spec['source_text'],'source_id':12,
             'comment':{'kind':'recalled_candidate','candidate':'A','scene':spec['scene'],
                        'source_layer_id':12,'terminal_refs':[]},
             'inPoint':spec['inPoint'],'outPoint':spec['outPoint'],
             'opacity_expression':'','opacity_expression_error':'','opacity_keys':keys,
             'hidden':[{'time':time,'opacity':0} for time in spec['hidden_times']],
             'readings':[{**sample,'opacity':0} for sample in spec['reading_samples']],
             'before':{'time':spec['fade_start'],'opacity':100},
             'restored':{'time':spec['restored_at'],'opacity':100}}
        return p,n,[{**deepcopy(row),'comp_id':comp_id} for comp_id in (1,2)]

    def generic_fixture(self):
        p,n,rows=self.fixture();p['duration']=50
        n['audit']={'candidate_reading_visibility_policy':CANDIDATE_READING_VISIBILITY_POLICY}
        original_scene=deepcopy(p['scenes'][0]);original_rows=deepcopy(rows)
        for index in range(4):
            shift=(index+1)*8;scene=deepcopy(original_scene);scene_id='COMPARE_'+str(index)
            scene.update(id=scene_id,kind='compare',motion_treatment='critical_comparison',event='eliminate')
            for key in ('start','candidate_start','settled','end'):scene[key]+=shift
            for event in scene['reading_events']:
                for key in ('depart','arrival','end_time'):event[key]+=shift
            p['scenes'].append(scene);p['candidate_events'].append({'scene':scene_id,'event':'eliminate'})
            for original in original_rows:
                row=deepcopy(original);row.update(scene=scene_id,layer='CANDIDATE_FLIGHT_'+scene_id)
                row['comment'].update(kind='whole_candidate_with_attached_identity',scene=scene_id)
                row['inPoint']+=shift;row['outPoint']+=shift
                for key in row['opacity_keys'][2:]:key['time']+=shift
                for field in ('hidden','readings'):
                    for sample in row[field]:sample['time']+=shift
                for field in ('before','restored'):row[field]['time']+=shift
                rows.append(row)
        return p,n,rows

    def test_both_native_comps_and_inherited_keys_pass_with_perception_unobserved(self):
        p,n,rows=self.fixture();result=validate_replay_reading_visibility(p,n,rows)
        self.assertEqual(result['status'],'PASS_REPLAY_QUIET_NATIVE_PARAMETERS')
        self.assertEqual(result['normal_speed_review'],'UNOBSERVED')
        self.assertEqual(result['listening_review'],'UNOBSERVED')
        self.assertFalse(result['public_render_ready'])
        self.assertEqual(result['rows'][0]['opacity_keys'][1]['value'],38)

    def test_missing_duplicate_or_wrong_scene_comp_inventory_is_rejected(self):
        p,n,rows=self.fixture()
        for changed in ([],rows[:1],[rows[0],rows[0]],rows+[rows[1]]):
            with self.subTest(count=len(changed)),self.assertRaisesRegex(ValueError,'coverage'):
                validate_replay_reading_visibility(p,n,changed)
        rows[1]['scene']='UNRELATED'
        with self.assertRaisesRegex(ValueError,'coverage'):validate_replay_reading_visibility(p,n,rows)

    def test_all_hidden_frames_and_every_necessary_reading_are_required(self):
        for field in ('hidden','readings'):
            p,n,rows=self.fixture();rows[1][field].pop()
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'coverage'):
                validate_replay_reading_visibility(p,n,rows)
        p,n,rows=self.fixture();rows[0]['readings'][3]['reading']=0
        with self.assertRaisesRegex(ValueError,'sample clock'):validate_replay_reading_visibility(p,n,rows)

    def test_visible_candidate_during_reading_or_camera_travel_fails(self):
        for field in ('hidden','readings'):
            p,n,rows=self.fixture();rows[0][field][-1]['opacity']=38
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'opacity'):
                validate_replay_reading_visibility(p,n,rows)
        p,n,rows=self.fixture();rows[0]['restored']['opacity']=0
        with self.assertRaisesRegex(ValueError,'restoration'):validate_replay_reading_visibility(p,n,rows)

    def test_four_exact_key_clocks_and_values_cannot_be_rebound(self):
        for change in ('time','value'):
            p,n,rows=self.fixture();rows[0]['opacity_keys'][2][change]+=.1 if change=='time' else -.1
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'four exact'):
                validate_replay_reading_visibility(p,n,rows)

    def test_hidden_interval_cannot_have_an_early_restore_key_even_if_samples_claim_zero(self):
        p,n,rows=self.fixture()
        rows[0]['opacity_keys'].insert(-2,{'time':5.8,'value':100})
        with self.assertRaisesRegex(ValueError,'before extraction settles'):
            validate_replay_reading_visibility(p,n,rows)

    def test_nonfinite_or_expression_driven_opacity_is_rejected(self):
        for field in ('key','sample','lifetime'):
            p,n,rows=self.fixture()
            if field=='key':rows[0]['opacity_keys'][2]['value']=float('nan')
            elif field=='sample':rows[0]['hidden'][0]['opacity']=float('nan')
            else:rows[0]['outPoint']=float('nan')
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_replay_reading_visibility(p,n,rows)
        p,n,rows=self.fixture();rows[0]['opacity_expression']='100'
        with self.assertRaisesRegex(ValueError,'without an expression'):
            validate_replay_reading_visibility(p,n,rows)

    def test_actual_temporal_easing_is_required_for_the_four_keys(self):
        for field,value in [('in_type','HOLD'),('out_ease',[20,55]),('in_ease',[0,90])]:
            p,n,rows=self.fixture();rows[1]['opacity_keys'][3][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'temporal easing'):
                validate_replay_reading_visibility(p,n,rows)

    def test_candidate_source_identity_and_visible_native_lifetime_are_bound(self):
        changes=[('source_text','Wrong option'),('text','Missing option identity'),
                 ('inPoint',2.5),('threeD',False),('guide_layer',True),('enabled',False)]
        for field,value in changes:
            p,n,rows=self.fixture();rows[0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'identity or lifetime'):
                validate_replay_reading_visibility(p,n,rows)
        p,n,rows=self.fixture();rows[0]['comment']['source_layer_id']=99
        with self.assertRaisesRegex(ValueError,'identity or lifetime'):
            validate_replay_reading_visibility(p,n,rows)

    def test_native_master_duplicate_preserves_proxy_comment_but_has_its_own_source_id(self):
        for fixture in (self.fixture,self.generic_fixture):
            p,n,rows=fixture()
            for row in rows:
                if row['comp_id']==n['master_comp_id']:row['source_id']=247
            with self.subTest(policy=n['audit']):
                result=validate_replay_reading_visibility(p,n,rows)
                self.assertEqual(len(result['rows']),len(rows))
                self.assertTrue(all(row['comment']['source_layer_id']==12 for row in rows))
                self.assertTrue(all(row['source_id']==247 for row in rows if row['comp_id']==n['master_comp_id']))

    def test_master_comment_cannot_replace_proxy_provenance_with_its_new_or_wrong_id(self):
        for forged_comment_id in (247,99):
            p,n,rows=self.generic_fixture()
            for row in rows:
                if row['comp_id']==n['master_comp_id']:row['source_id']=247
            master=next(row for row in rows if row['comp_id']==n['master_comp_id'])
            master['comment']['source_layer_id']=forged_comment_id
            with self.subTest(comment_id=forged_comment_id),self.assertRaisesRegex(ValueError,'identity or lifetime'):
                validate_replay_reading_visibility(p,n,rows)

    def test_reading_boundaries_and_no_new_candidate_decision_are_enforced(self):
        p,n,rows=self.fixture();p['scenes'][0]['reading_events'][-1]['end_time']=6.1
        with self.assertRaisesRegex(ValueError,'necessary reading'):replay_reading_visibility_rows(p)
        p,n,rows=self.fixture();p['scenes'][0]['settled']=float('nan')
        with self.assertRaisesRegex(ValueError,'nonfinite'):replay_reading_visibility_rows(p)
        p,n,rows=self.fixture();p['candidate_events']=[{'scene':'RECHECK','event':'eliminate'}]
        with self.assertRaisesRegex(ValueError,'candidate decision'):replay_reading_visibility_rows(p)

    def test_historical_marker_absence_is_read_only_and_unknown_policy_fails(self):
        p,n,rows=self.fixture()
        class NoNativeCall:
            def js(self,code):raise AssertionError('Historical policy must not call Adobe')
        n['audit']={}
        self.assertIsNone(replay_reading_visibility_readback(NoNativeCall(),p,n))
        n['audit']['replay_reading_visibility_policy']='UNREVIEWED_FALLBACK'
        with self.assertRaisesRegex(ValueError,'Unknown native'):
            replay_reading_visibility_readback(NoNativeCall(),p,n)
        n['audit']['replay_reading_visibility_policy']=REPLAY_READING_VISIBILITY_POLICY
        p['scenes'][0]['kind']='compare'
        self.assertEqual(replay_reading_visibility_readback(NoNativeCall(),p,n)['status'],
                         'NOT_APPLICABLE_NO_REPLAY_READING')

    def test_readback_requests_real_property_keys_and_samples_in_both_comps(self):
        p,n,rows=self.fixture()
        class NativeRows:
            def js(self,code):self.code=code;return rows
        host=NativeRows();result=replay_reading_visibility_readback(host,p,n)
        self.assertEqual(result['status'],'PASS_REPLAY_QUIET_NATIVE_PARAMETERS')
        self.assertIn('ids=[1, 2]',host.code)
        self.assertIn('op.keyTime(k)',host.code)
        self.assertIn('op.keyInTemporalEase(k)',host.code)
        self.assertIn('op.valueAtTime(t,false)',host.code)
        self.assertNotIn('__SHOTS__',host.code)
        # AE's ExtendScript parser actually misclassified native BEZIER with
        # a nested ternary, despite the same expression working under Node.
        # Keep this host-specific regression active even without Node.
        enum_helper=host.code.split('function interpolation(v){',1)[1].split('    function easing',1)[0]
        self.assertNotIn('?',enum_helper)
        self.assertIn('var value=String(v);',enum_helper)
        for constant,label in [('Bezier','BEZIER'),('Hold','HOLD'),('Linear','LINEAR')]:
            self.assertRegex(enum_helper,r"if\s*\(value===interpolation"+constant+r"\)\s*return\s*'"+label+r"';")
        self.assertIn("return 'UNKNOWN';",enum_helper)

    def test_generic_policy_requires_all_five_comparison_and_replay_scenes(self):
        p,n,rows=self.generic_fixture();result=validate_replay_reading_visibility(p,n,rows)
        self.assertEqual(result['status'],'PASS_CANDIDATE_QUIET_NATIVE_PARAMETERS')
        self.assertEqual(len(result['rows']),10)
        self.assertEqual(len(replay_reading_visibility_rows(p,CANDIDATE_READING_VISIBILITY_POLICY)),5)
        self.assertEqual(result['rows'][2]['layer'],'CANDIDATE_FLIGHT_COMPARE_0')
        for dropped in (rows[:2],rows[:-1]):
            with self.subTest(count=len(dropped)),self.assertRaisesRegex(ValueError,'coverage'):
                validate_replay_reading_visibility(p,n,dropped)

    def test_generic_policy_still_rejects_visible_comparison_and_wrong_clone_identity(self):
        p,n,rows=self.generic_fixture();rows[-1]['readings'][0]['opacity']=38
        with self.assertRaisesRegex(ValueError,'opacity'):validate_replay_reading_visibility(p,n,rows)
        p,n,rows=self.generic_fixture();rows[2]['comment']['kind']='recalled_candidate'
        with self.assertRaisesRegex(ValueError,'identity or lifetime'):
            validate_replay_reading_visibility(p,n,rows)

    def test_light_checks_and_comparisons_without_reading_have_no_fictitious_scope(self):
        p,n,rows=self.generic_fixture()
        light=deepcopy(p['scenes'][1]);light.update(id='LIGHT',motion_treatment='in_place_check')
        empty=deepcopy(p['scenes'][1]);empty.update(id='NO_READING',reading_events=[])
        p['scenes'] += [light,empty]
        self.assertEqual(len(validate_replay_reading_visibility(p,n,rows)['rows']),10)
        light['motion_treatment']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'Unbound native'):replay_reading_visibility_rows(p,CANDIDATE_READING_VISIBILITY_POLICY)

    def test_unknown_generic_or_ambiguous_native_markers_do_not_call_host(self):
        p,n,rows=self.generic_fixture()
        class NoNativeCall:
            def js(self,code):raise AssertionError('Unknown policy must not call Adobe')
        n['audit']['candidate_reading_visibility_policy']='UNCONFIRMED'
        with self.assertRaisesRegex(ValueError,'Unknown native'):
            replay_reading_visibility_readback(NoNativeCall(),p,n)
        n['audit']['candidate_reading_visibility_policy']=CANDIDATE_READING_VISIBILITY_POLICY
        n['audit']['replay_reading_visibility_policy']=REPLAY_READING_VISIBILITY_POLICY
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            replay_reading_visibility_readback(NoNativeCall(),p,n)

    @unittest.skipUnless(shutil.which('node'),'Node is needed for the mutable host enum regression')
    def test_native_enum_objects_are_snapshotted_before_another_enum_getter_can_mutate_them(self):
        p,n,rows=self.fixture()
        class NativeRows:
            def js(self,code):self.code=code;return rows
        host=NativeRows();replay_reading_visibility_readback(host,p,n)
        functions=host.code.split('    function easing',1)[0]
        # This adversarial model protects immediate string snapshots. It does
        # not reproduce AE's separate, actually observed ternary parser bug.
        code=r'''var shared={code:'',toString:function(){return this.code;}},KeyframeInterpolationType={};
        [['BEZIER','6613'],['HOLD','6614'],['LINEAR','6612']].forEach(function(pair){
          Object.defineProperty(KeyframeInterpolationType,pair[0],{get:function(){shared.code=pair[1];return shared;}});
        });'''+functions+r'''
        var result=[];['6613','6614','6612','UNKNOWN'].forEach(function(value){shared.code=value;result.push(interpolation(shared));});
        process.stdout.write(JSON.stringify(result));'''
        output=subprocess.check_output([shutil.which('node'),'-e',code],text=True)
        self.assertEqual(json.loads(output),['BEZIER','HOLD','LINEAR','UNKNOWN'])


if __name__=='__main__':unittest.main()
