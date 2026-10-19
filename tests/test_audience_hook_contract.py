"""Synthetic contract controls; these never certify creative or listening review."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from video_contracts import sha, write
from scripts.voice_delivery import sha256
from creative_os.audience_engagement import (HOOK_PHASES, authored_body_binding,
    validate_authored_hook, require_hook_decision, timed_scene_rows)
from ae_production.authored_episode import compile_clock, shift_body_clock, compile_visual_states
from tests.test_authored_episode import clock_input
from ae_production.authored_native import validate_hook_readback


class HookContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        folder=Path(self.temp.name)
        passage='They attend workshops.';option='Lead workshops.'
        def ref(pointer,text,lo=0,hi=None):
            hi=len(text) if hi is None else hi
            return dict(world='second',pointer=pointer,start=lo,end=hi,quote=text[lo:hi])
        refs=[ref('/passage',passage),ref('/options/A',option)]
        anchors=[ref('/passage',passage,12,21),ref('/options/A',option,5,14)]
        action=dict(method_id='INTERPRET_SOURCE',method_version='7.0',state='produced',
            review_status='reviewed',stop_applied=False,stop_rule_check={'stopped':False},
            output={'kind':'interpretation'},evidence=[{'field':'passage','start':0,'end':len(passage)}])
        terminal={'candidate':'A','effect':'eliminate'}
        self.bundles={'second':{'source_snapshot':{'passage':passage,'options':{'A':option}},
            'analysis':{'execution_trace':[action],'question_verification':{'candidate_bindings':[terminal]}}}}
        action_ref={'world':'second','pointer':'/execution_trace/0','sha':sha(action)}
        scenes=[dict(id='early',kind='compare',world='first',voice_ids=['body'],event='eliminate'),
            dict(id='contrast',kind='compare',world='first',voice_ids=['body'],event='supported'),
            dict(id='next',kind='task',world='second',voice_ids=['body']),
            dict(id='payoff',kind='compare',world='second',voice_ids=['body'],candidate='A',event='eliminate',
                 source_refs=refs,action_refs=[action_ref],terminal_refs=[terminal],attention=[{'phrase':'attend'},{'phrase':'Lead'}]),
            dict(id='recall',kind='recap',world='second',voice_ids=['body'])]
        instruction=folder/'user.txt';quotes=['Why can shared terms mislead?','Inspect the relation.']
        instruction.write_text('\n'.join(quotes),encoding='utf-8')
        self.author={'scenes':scenes,'voices':[{'id':'hook'+str(i),'text':t} for i,t in enumerate(quotes)]+
            [{'id':'body','text':'Same meaning: inspect the relation.'}], 'sources':{},
            'input_files':{str(instruction):sha256(instruction)}}
        for world in ('first','second'):
            source=folder/(world+'.json');write(source,{'synthetic':world})
            self.author['sources'][world]={'bundle':str(source),'status':str(source)}
        stop=sha(action['stop_rule_check'])
        self.author['audience_hook']={
            'contract_version':'1.0.0','scene_id':'opening','presentation':'abstract_opening_teaser',
            'pain_point':{'id':'role-confusion','description':'Shared terms hide changed actions.','source_refs':refs},
            'confusion_trigger':{'kind':'shared_term_relation_mismatch','source_scene_id':'payoff','anchor_refs':anchors},
            'method_trigger':{'label':'Same meaning','method_id':'INTERPRET_SOURCE','method_version':'7.0',
                'action_ref':action_ref,'claim_scope':'interpretation','stop_rule_sha':stop},
            'visual_conflict':{'preset':'surface_overlap_relation_displacement','phases':HOOK_PHASES,
                'anchor_refs':anchors,'visible_text':['workshops','workshops'],'relation_labels':False},
            'promised_payoff':{'scope':'candidate_elimination','candidate':'A','result':'eliminate',
                'scene_sha':sha(scenes[3]),'source_refs':refs,'action_refs':[action_ref],
                'terminal_refs':[terminal],'stop_rule_sha':stop},
            'source_refs':refs,'payoff_scene_id':'payoff',
            'spoiler_boundary':{'withhold_candidate':True,'withhold_relation_labels':True,'withhold_verdict':True,
                'opening_visible_text':['workshops','workshops'],'scope':'teaser_not_first_question_fact'},
            'approved_copy_binding':{'path':str(instruction),'sha256':sha256(instruction),'quotes':quotes,
                'text_sha':sha(quotes),'authority':'explicit_user_instruction','status':'USER_SPECIFIED',
                'scope':'hook_copy_and_specified_visual_only'},'voice_ids':['hook0','hook1'],
            'retention':{'first_payoff_scene_id':'early','first_payoff_scope':'partial_candidate_check',
                'first_payoff_sha':sha(scenes[0]),'reverse_contrast_scene_id':'contrast',
                'progression_scene_id':'next','progression_scene_sha':sha(scenes[2]),
                'final_recall_scene_id':'recall','final_recall_scene_sha':sha(scenes[4])},
            'timing':{'voice_pre':.35,'voice_gap':.12,'unresolved_min':.6,'handoff_seconds':.85}}
        self.author['audience_hook']['body_binding']=authored_body_binding(self.author)

    def validate(self):return validate_authored_hook(self.author,self.bundles)

    def test_positive_generic_method_keeps_human_and_public_pending(self):
        result=self.validate();self.assertEqual(result['status'],'BOUND_USER_SPECIFIED')
        self.assertEqual(result['human_review'],'PENDING');self.assertFalse(result['public_render_ready'])

    def test_missing_new_hook_is_a_creative_decision_gap(self):
        self.author.pop('audience_hook')
        self.assertEqual(self.validate()['status'],'HISTORICAL_UNMIGRATED')
        with self.assertRaisesRegex(ValueError,'CREATIVE_DECISION_REQUIRED'):require_hook_decision(self.author)

    def test_fake_historical_marker_cannot_authorize_fresh_production(self):
        self.author.pop('audience_hook');folder=Path(self.temp.name)
        write(folder/'native-identity.json',{})
        for operation in ('script','voice','align','prepare','build'):
            with self.subTest(operation=operation),self.assertRaisesRegex(ValueError,'CREATIVE_DECISION_REQUIRED'):
                require_hook_decision(self.author,folder,operation=operation)

    def test_legacy_build_entry_cannot_bypass_hook_migration(self):
        from unittest.mock import patch
        from tests.test_adaptive_native_frames import adapter
        with patch.object(adapter,'client') as adobe:
            with self.assertRaisesRegex(ValueError,'CREATIVE_DECISION_REQUIRED'):
                adapter.build(Path(self.temp.name))
            adobe.assert_not_called()

    def test_incomplete_contract_rejected(self):
        self.author['audience_hook'].pop('pain_point')
        with self.assertRaisesRegex(ValueError,'CREATIVE_DECISION_REQUIRED'):self.validate()

    def test_wrong_method_or_stop_scope_rejected(self):
        h=self.author['audience_hook'];h['method_trigger']['method_id']='ANOTHER_METHOD'
        with self.assertRaisesRegex(ValueError,'Stop scope'):self.validate()
        h['method_trigger']['method_id']='INTERPRET_SOURCE';h['method_trigger']['claim_scope']='answer'
        with self.assertRaisesRegex(ValueError,'Stop scope'):self.validate()

    def test_local_elimination_cannot_promise_whole_answer(self):
        self.author['audience_hook']['promised_payoff']['scope']='whole_question_answer'
        with self.assertRaises(ValueError):self.validate()

    def test_visible_payoff_and_self_approval_rejected(self):
        h=self.author['audience_hook'];h['visual_conflict']['relation_labels']=True
        with self.assertRaises(ValueError):self.validate()
        h['visual_conflict']['relation_labels']=False;h['approved_copy_binding']['status']='APPROVED'
        with self.assertRaises(ValueError):self.validate()

    def test_body_copy_and_order_changes_invalidate_binding(self):
        self.author['voices'][-1]['text']+=' Changed.'
        with self.assertRaisesRegex(ValueError,'Stale Hook'):self.validate()
        self.author['audience_hook']['body_binding']=authored_body_binding(self.author)
        self.author['scenes'].reverse()
        with self.assertRaisesRegex(ValueError,'Stale Hook'):self.validate()

    def test_instruction_bytes_are_not_an_approval_boolean(self):
        p=Path(self.author['audience_hook']['approved_copy_binding']['path']);p.write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'instruction binding'):self.validate()

    def test_clock_translation_preserves_characters_and_full_takes(self):
        a,clips,aligned=clock_input();clock=compile_clock(a,clips,aligned)
        clock['scenes'][0]['reading_events']=[dict(start=3,end=12,depart=1,arrival=2,end_time=3)]
        shifted=shift_body_clock(clock,7.25)
        self.assertEqual(shifted['scenes'][0]['reading_events'][0]['start'],3)
        self.assertEqual(shifted['scenes'][0]['reading_events'][0]['arrival'],9.25)
        self.assertEqual(shifted['segments'][0]['voice'],clock['segments'][0]['voice'])
        self.assertEqual(shifted['frames'],clock['frames']+174)

    def test_thinking_only_after_source_reading_with_real_extraction(self):
        a={'visual_states':{'synthetic':'test'}}
        clock={'scenes':[{'id':'read','motion_treatment':'in_place_check'},
            {'id':'think','motion_treatment':'critical_comparison','extract_start':10,'settled':12,'return_start':15,'end':17}]}
        result=compile_visual_states(a,clock)
        self.assertEqual([r['scene_id'] for r in result['thinking_windows']],['think'])
        self.assertEqual(result['normal_speed_review'],'UNOBSERVED')

    def test_paper_and_article_credit_cannot_be_invented(self):
        import zipfile
        from xml.sax.saxutils import escape
        from ae_production.authored_episode import validate_source_attribution
        folder=Path(self.temp.name);path=folder/'paper.docx'
        lines=['Synthetic trial paper','A','Workshop article','Synthetic source text.',
               '21. What happens?','Attend sessions.']
        xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join(
            '<w:p><w:r><w:t>'+escape(line)+'</w:t></w:r></w:p>' for line in lines)+'</w:body></w:document>'
        with zipfile.ZipFile(path,'w') as z:z.writestr('word/document.xml',xml)
        a={'scenes':[{'id':'task','kind':'task','world':'trial'}],
           'input_files':{str(path):sha256(path)},'source_attribution':{'trial':{
            'source_path':str(path),'source_sha256':sha256(path),'paper_heading_quotes':[lines[0]],
            'paper_display':lines[0],'article_anchor':lines[2],'article_display':lines[2],
            'scene_id':'task','reading_section':'A','question_number':21,'question_id':'synthetic-trial-Q21'}}}
        b={'trial':{'source_snapshot':{'question_id':'synthetic-trial-Q21','passage':lines[2]+'\n'+lines[3],
            'stem':'What happens?','options':{'A':lines[5]}}}}
        self.assertEqual(validate_source_attribution(a,b)['status'],'SOURCE_BOUND')
        a['source_attribution']['trial']['article_display']='Invented article'
        with self.assertRaises(ValueError):validate_source_attribution(a,b)
        a['source_attribution']['trial']['article_display']=lines[2]
        a['source_attribution']['trial']['paper_display']='Invented exam'
        with self.assertRaises(ValueError):validate_source_attribution(a,b)

    def native_fixture(self):
        h={'decision_sha':sha(self.author['audience_hook']),'decision':self.author['audience_hook'],
           'end':8.25,'phases':{'surface_align':[2,3],'relation_displace':[3,4],
                              'unresolved_hold':[4,7],'match_into_task':[7,8.25]}}
        objects=[]
        def obj(name):
            row={'name':'AUDIENCE_HOOK_'+name,'outPoint':8.25,'final_opacity':0,'stack_index':len(objects)+1}
            objects.append(row);return row
        for k,ref in enumerate(h['decision']['confusion_trigger']['anchor_refs']):
            name='second-source-0' if k==0 else 'second_OPTION_A'
            obj('ANCHOR_'+str(k)).update(text='workshops',threeD=True,
                comment={'source_ref':ref,'decision_sha':h['decision_sha'],'source_layer_name':name},
                source_layer_exists=True,source_contains_anchor=True,source_comment={'start':0},aligned=[490,275,0],glyph_bottoms=[100]*4)
        for k in (0,1):
            for j in (0,1):obj('ROLE_'+str(k)+'_'+str(j)).update(aligned=[100*j,0,0],
                displaced=[100*j,80*k,0],held=[100*j,80*k,0])
            obj('RELATION_'+str(k)).update(path_enter=[[0,200],[50,210],[100,200]],
                path_aligned=[[0,200],[50,210],[100,200]],
                path_displaced=[[0,200+80*k],[50,210],[100,200+80*k]],
                path_held=[[0,200+80*k],[50,210],[100,200+80*k]])
        obj('SPACE')
        n={'comp_id':1,'master_comp_id':2,'audit':{'audience_hook':{'decision_sha':h['decision_sha'],
            'range':[0,8.25],'phases':deepcopy(h['phases']),'original_task_start':8.25,
            'objects':[o['name'] for o in objects]}}}
        samples=[{'time':frame/24,'cover':100 if frame<175 else 50,'foreground':50 if frame<175 else 0}
                 for frame in range(168,198)]
        return {'audience_hook':h},n,[{'comp_id':i,'objects':deepcopy(objects),'camera_at_body':[640,320,-1550],
                                     'handoff_visibility':deepcopy(samples)} for i in (1,2)]

    def test_actual_native_geometry_is_required_for_both_comps(self):
        p,n,rows=self.native_fixture();result=validate_hook_readback(p,n,rows)
        self.assertEqual(result['normal_speed_review'],'UNOBSERVED')
        rows[1]['objects'].pop()
        with self.assertRaisesRegex(ValueError,'inventory'):validate_hook_readback(p,n,rows)

    def test_wrong_native_source_text_rejected(self):
        p,n,rows=self.native_fixture();rows[0]['objects'][0]['text']='answer'
        with self.assertRaisesRegex(ValueError,'source-exact'):validate_hook_readback(p,n,rows)

    def test_original_word_hidden_by_background_rejected(self):
        p,n,rows=self.native_fixture();rows[0]['objects'][0]['stack_index']=100
        with self.assertRaisesRegex(ValueError,'background'):validate_hook_readback(p,n,rows)

    def test_relation_line_crossing_glyphs_rejected(self):
        p,n,rows=self.native_fixture()
        edge=next(o for o in rows[0]['objects'] if o['name']=='AUDIENCE_HOOK_RELATION_0')
        edge['path_enter'][1][1]=90
        with self.assertRaisesRegex(ValueError,'clear space'):validate_hook_readback(p,n,rows)

    def test_opening_ghost_over_first_question_rejected(self):
        p,n,rows=self.native_fixture();rows[0]['handoff_visibility'][-1]['foreground']=20
        with self.assertRaisesRegex(ValueError,'overlaps'):validate_hook_readback(p,n,rows)

    def test_nonmoving_relation_is_not_native_consumption(self):
        p,n,rows=self.native_fixture()
        role=next(o for o in rows[0]['objects'] if o['name']=='AUDIENCE_HOOK_ROLE_1_0')
        role['displaced']=role['aligned']
        with self.assertRaisesRegex(ValueError,'displacement'):validate_hook_readback(p,n,rows)

    def test_unsettled_hold_and_camera_cut_rejected(self):
        p,n,rows=self.native_fixture()
        role=next(o for o in rows[0]['objects'] if o['name']=='AUDIENCE_HOOK_ROLE_1_0')
        role['held']=[300,400,10]
        with self.assertRaisesRegex(ValueError,'hold'):validate_hook_readback(p,n,rows)
        role['held']=deepcopy(role['displaced']);rows[1]['camera_at_body']=[900,320,-1550]
        with self.assertRaisesRegex(ValueError,'camera'):validate_hook_readback(p,n,rows)


if __name__=='__main__':unittest.main()
