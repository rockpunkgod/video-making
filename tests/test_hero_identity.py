"""Synthetic binding and production controls, without real questions/media."""
from copy import deepcopy
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import Mock, patch
from video_contracts import sha, seal
from tests.test_ae_production import AEProductionTest
from creative_os.delivery import make_delivery, attach_fidelity_review, CHECKS
from creative_os.hero import build_contract, validate_contract, validate_handoff, render_receipt, require_approved_direction, file_sha
from creative_os.motion_identity import bind_identity, validate_identity, registry, creative_review, CREATIVE_DIMENSIONS
from premiere_production.router import BackendRouter
from premiere_production.music import gain_envelope, recording_manifest, verify_gain_keys
from premiere_production.editorial import bind_final_display, validate_audio_plan, validate_audio_timeline
from ae_production.hero_execution import audit


class HeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AEProductionTest.setUpClass()
        cls.package,cls.manifest,cls.statuses=AEProductionTest.package,AEProductionTest.manifest,AEProductionTest.statuses

    def setUp(self):
        specs=[{'unit_id':f'full-{i}', 'scene_id':s['scene_id'], 'intent':'core',
                'source_claim_refs':s['claim_refs'], 'spoken_copy':'当前动作，不定答案。',
                'on_screen_copy':'当前动作\n不定答案', 'protected_terms':['不定答案']}
               for i,s in enumerate(self.package['semantic_scenes']) if s['claim_refs']]
        self.full=make_delivery(self.package,self.manifest,self.statuses,specs)
        self.excerpt=make_delivery(self.package,self.manifest,self.statuses,
                                  [dict(s,unit_id=s['unit_id'].replace('full','hero')) for s in specs])
        for name in ('full','excerpt'):
            d=getattr(self,name)
            for u in d['units']:
                d=attach_fidelity_review(d,u['unit_id'],'SYNTHETIC HOST',{k:'Synthetic fidelity fixture, not teaching certification.' for k in CHECKS})
            setattr(self,name,d)
        self.nodes=[{'node_id':u['unit_id'], 'kind':'text', 'unit_id':u['unit_id'],
                     'text':u['on_screen_copy'], 'position':[128,128], 'effects':{}, 'tracks':{}}
                    for u in self.excerpt['units']]
        self.beats=[{'phase':'MOVE','start':0,'end':4}, {'phase':'HOLD','start':4,'end':12}]

    def build(self,**kw):
        args=dict(package=self.package,manifest=self.manifest,statuses=self.statuses,
                  full_delivery=self.full,excerpt=self.excerpt,design={},nodes=self.nodes,beats=self.beats,duration=12)
        args.update(kw);return build_contract(**args)

    def test_replay_preserves_frozen_inputs(self):
        before=sha([self.package,self.manifest,self.statuses]);self.assertEqual(self.build(),self.build())
        self.assertEqual(before,sha([self.package,self.manifest,self.statuses]))
        self.assertFalse(self.build()['public_render_ready'])

    def test_screen_fragment_cannot_drop_negation(self):
        nodes=deepcopy(self.nodes);nodes[0]['text']='当前动作'
        with self.assertRaisesRegex(ValueError,'projection'):self.build(nodes=nodes)

    def test_missing_stop_excerpt_is_blocked(self):
        hero=deepcopy(self.excerpt);hero['units']=[u for u in hero['units'] if not any(c in {r for s in self.package['semantic_scenes'] if s['scene_type']=='STOP_RULE' for r in s['claim_refs']} for c in u['source_claim_refs'])]
        from creative_os.delivery import copy_sha,screen_sha
        hero['delivery_copy_sha']=copy_sha(hero);hero['screen_copy_sha']=screen_sha(hero)
        with self.assertRaisesRegex(ValueError,'Stop Rule'):self.build(excerpt=hero)

    def test_false_hold_is_blocked(self):
        nodes=deepcopy(self.nodes);nodes[0]['tracks']={'opacity':[[4,0],[5,100]]}
        with self.assertRaisesRegex(ValueError,'HOLD'):self.build(nodes=nodes)

    def test_withdrawn_status_blocks_new_operation(self):
        rc=self.build();statuses=deepcopy(self.statuses)
        for k,v in statuses.items():v['effective_status']='WITHDRAWN';statuses[k]=seal(v)
        with self.assertRaises(ValueError):validate_contract(rc,self.package,self.manifest,statuses,self.full,self.excerpt)

    def test_metadata_status_refresh_does_not_change_visual_binding(self):
        rc=self.build();statuses=deepcopy(self.statuses)
        for k,v in statuses.items():v['generated_at']='2026-10-06T00:00:00Z';statuses[k]=seal(v)
        validate_contract(rc,self.package,self.manifest,statuses,self.full,self.excerpt)

    def test_handoff_file_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d)/'synthetic.aep';output=Path(d)/'synthetic.mp4';project.write_bytes(b'synthetic');output.write_bytes(b'synthetic')
            rc=self.build();receipt=render_receipt(rc,'synthetic',project,output,{'width':1920,'height':1080,'fps':24,'duration':12})
            validate_handoff(receipt,rc,project);output.write_bytes(b'tampered')
            with self.assertRaises(ValueError):validate_handoff(receipt,rc,project)

    def test_ai_and_old_copy_cannot_approve_full_production(self):
        rc=self.build()
        for review in ({'status':'APPROVED_DIRECTION','reviewer_kind':'ai_host','reviewer':'test','render_contract_sha':rc['render_contract_sha']},
                       {'status':'APPROVED_DIRECTION','reviewer_kind':'human','reviewer':'test','render_contract_sha':'old'}):
            with self.assertRaises(ValueError):require_approved_direction(review,rc)


class ProductionControls(unittest.TestCase):
    def audio_fixture(self, directory):
        path=Path(directory)/'synthetic.wav';path.write_bytes(b'SYNTHETIC AUDIO')
        units=[{'unit_id':key,'spoken_copy':'SYNTHETIC '+key,'source_claim_refs':['synthetic-'+key]} for key in ('a','b')]
        voices=[{'unit_id':u['unit_id'],'path':str(path),'sha256':file_sha(path),
                 'spoken_copy_sha':sha(u['spoken_copy']),'source_claim_refs':u['source_claim_refs'],
                 'start':.2+i*.6,'end':.6+i*.6} for i,u in enumerate(units)]
        audio={'render_contract_sha':'synthetic','final_copy_sha':'synthetic','duration':2,'fps':24,
               'voice':voices,'sfx':{'path':str(path),'sha256':file_sha(path)}}
        contract={'render_contract_sha':'synthetic','copy_lock':{'final_copy_sha':'synthetic'},'canvas':{'duration':2,'fps':24}}
        return path,audio,contract,{'units':units}

    def test_audio_plan_requires_all_voice_units_and_rejects_sfx_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            path,audio,contract,hero=self.audio_fixture(d)
            validate_audio_plan(audio,contract,hero)
            for voices in ([],audio['voice'][:1],[audio['voice'][0],audio['voice'][0]]):
                changed=deepcopy(audio);changed['voice']=voices
                with self.assertRaisesRegex(ValueError,'every excerpt unit'):validate_audio_plan(changed,contract,hero)
            sfx=Path(d)/'sfx.wav';sfx.write_bytes(b'ORIGINAL');audio['sfx']={'path':str(sfx),'sha256':file_sha(sfx)};sfx.write_bytes(b'TAMPERED')
            with self.assertRaisesRegex(ValueError,'SFX changed'):validate_audio_plan(audio,contract,hero)

    def test_music_plan_cannot_retain_no_music_ducking_declaration(self):
        with tempfile.TemporaryDirectory() as d:
            path,audio,contract,hero=self.audio_fixture(d)
            audio['music']={'source_path':str(path),'file_sha':file_sha(path),'clip_path':str(path),'clip_sha':file_sha(path)}
            audio['ducking']={'status':'not_applicable'}
            with self.assertRaisesRegex(ValueError,'no-music'):validate_audio_plan(audio,contract,hero)

    def test_native_audio_timeline_rejects_extra_clip_or_moved_voice(self):
        with tempfile.TemporaryDirectory() as d:
            path,audio,contract,hero=self.audio_fixture(d)
            state={'audioTracks':[{'index':0,'clips':[{'name':path.name,'start':v['start'],'end':v['end']} for v in audio['voice']]},
                                  {'index':1,'clips':[{'name':path.name,'start':0,'end':2}]}]}
            validate_audio_timeline(state,audio)
            changed=deepcopy(state);changed['audioTracks'][0]['clips'][0]['start']+=.2
            with self.assertRaisesRegex(ValueError,'placement'):validate_audio_timeline(changed,audio)
            changed=deepcopy(state);changed['audioTracks'][0]['clips'].append(changed['audioTracks'][0]['clips'][0])
            with self.assertRaisesRegex(ValueError,'coverage'):validate_audio_timeline(changed,audio)

    def test_native_music_readback_must_match_every_planned_key(self):
        keys=[{'time_seconds':0,'level_db':-20},{'time_seconds':1,'level_db':-60}]
        actual={'isTimeVarying':True,'keyframes':[{'time':k['time_seconds'],'value':10**((k['level_db']-15)/20)} for k in keys]}
        verify_gain_keys(actual,keys)
        for changed in (dict(actual,keyframes=actual['keyframes'][:1]),
                        dict(actual,keyframes=actual['keyframes']+[actual['keyframes'][-1]])):
            with self.assertRaisesRegex(ValueError,'coverage'):verify_gain_keys(changed,keys)
        actual['keyframes'][-1]['value']*=2
        with self.assertRaisesRegex(ValueError,'time/level'):verify_gain_keys(actual,keys)

    def test_creative_review_does_not_create_human_approval(self):
        r=creative_review({'render_contract_sha':'synthetic'},{'final_copy_sha':'synthetic'},'synthetic',
                          {k:'Synthetic observation, pending human review.' for k in CREATIVE_DIMENSIONS})
        self.assertFalse(r['independent']);self.assertFalse(r['public_render_ready'])
        self.assertEqual(r['human_taste_review'],'PENDING')

    def test_creative_review_cannot_omit_recognition_dimensions(self):
        with self.assertRaises(ValueError):creative_review({'render_contract_sha':'synthetic'},{},'synthetic',{})

    def native_audit_fixture(self):
        node={'node_id':'SYNTHETIC','kind':'text','text':'SYNTHETIC','font':'SYNTHETIC_FONT','size':64,'position':[128,536],
              'tracks':{'position':[[0,[128,568]],[6.45,[128,541]]]}}
        rc={'render_contract_sha':'synthetic','nodes':[node],'canvas':{'duration':12}}
        first={'contract_text':json.dumps(rc),'binding':{'render_contract_sha':'synthetic'},
               'rows':[{'id':'SYNTHETIC','text':'SYNTHETIC','font':'SYNTHETIC_FONT','size':64}],
               'width':1920,'height':1080,'fps':24,'duration':12,'motionBlur':True,'shutter':180,'effects':[]}
        second=[{'id':'SYNTHETIC','tracks':{'position':[[0,[128,568,0]],[6.44999186197917,[128,541,0]]], 'opacity':[],'scale':[]},
                 'inPoint':0,'outPoint':12,'initialPosition':[128,568,0],'initialOpacity':100,'enabled':True}]
        return rc,first,second

    def test_native_ae_quantized_time_and_zero_z_are_accepted(self):
        rc,first,second=self.native_audit_fixture();c=Mock();c.call.side_effect=[{'content':json.dumps(first)},{'content':json.dumps(second)}]
        with tempfile.TemporaryDirectory() as d:self.assertEqual(len(audit(c,rc,1,d)['motion_keyframes']),1)

    def test_native_motion_and_hidden_stop_drift_are_rejected(self):
        for mutation in ('position','visibility'):
            rc,first,second=self.native_audit_fixture()
            if mutation=='position':second[0]['tracks']['position'][-1][1][1]=542
            else:second[0]['initialOpacity']=0
            c=Mock();c.call.side_effect=[{'content':json.dumps(first)},{'content':json.dumps(second)}]
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaisesRegex(ValueError,'drift'):audit(c,rc,1,d)

    def test_actual_caption_change_invalidates_final_copy_and_cannot_keep_review(self):
        with tempfile.TemporaryDirectory() as d:
            caption=Path(d)/'synthetic.srt';frame=Path(d)/'synthetic.frame'
            frame.write_bytes(b'SYNTHETIC FRAME')
            caption.write_text('1\n00:00:00,000 --> 00:00:01,000\n不定答案。\n',encoding='utf-8')
            hero={'units':[{'spoken_copy':'不定答案。','visual_excerpts':[]}]}
            m=bind_final_display({'final_copy_sha':'synthetic'},hero,caption,[frame],'SYNTHETIC')
            self.assertIsNone(m['copy_lock']['editorial_review_sha']);self.assertFalse(m['public_render_ready'])
            caption.write_text('1\n00:00:00,000 --> 00:00:01,000\n定答案。\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'captions differ'):bind_final_display(m,hero,caption,[frame],'SYNTHETIC')

    def test_motion_registry_refuses_teaching_fact_fields(self):
        grammar, signatures=registry();signatures['signatures'][0]['answer']='invented'
        with patch('creative_os.motion_identity.read',side_effect=[grammar,signatures]):
            with self.assertRaisesRegex(ValueError,'Teaching fact'):registry()

    def client(self):
        c=Mock();c.tools.return_value={'tools':[{'name':n} for n in ('get_active_sequence','save_project','get_capabilities','verify_premiere_connection')]}
        def call(n,*a):
            return {'get_capabilities':{'backends':{'cep':{},'uxp':{'compatible':True}}},
                    'verify_premiere_connection':{'overall':'ready','backend':'cep'},
                    'get_active_sequence':{'id':'actual'},'save_project':{'saved':True}}[n]
        c.call.side_effect=call;return c

    def test_static_uxp_compatibility_is_not_live_and_no_fallback(self):
        with self.assertRaises(ValueError):BackendRouter(self.client(),preferred='uxp')

    def test_wrong_sequence_blocks_mutation(self):
        c=self.client();r=BackendRouter(c)
        with self.assertRaises(ValueError):r.execute('save_project',{},sequence_id='other')
        self.assertFalse(any(call.args[0]=='save_project' for call in c.call.call_args_list))

    def test_uncertain_result_blocks_followup_mutation(self):
        c=self.client();r=BackendRouter(c);c.call.side_effect=TimeoutError('synthetic')
        with self.assertRaises(TimeoutError):r.execute('save_project',{})
        with self.assertRaises(ValueError):r.execute('save_project',{})
        self.assertEqual(r.receipts[-1]['result']['outcome'],'uncertain')

    def test_other_method_production_and_phase_swaps_are_blocked(self):
        with self.assertRaises(ValueError):bind_identity('F01',[],[],'carry')
        with self.assertRaises(ValueError):bind_identity('G01',[{'phase':'seal','start':0,'end':1}],[],'carry')

    def test_method_stamp_cannot_relabel_another_method(self):
        identity=bind_identity('G01',[{'phase':p,'start':i,'end':i+1} for i,p in enumerate(['extract','route','seal'])],['semantic_carry'],'carry')
        with self.assertRaises(ValueError):validate_identity(identity,[{'node_id':'carry','tracks':{'position':[[0,[0,0]],[1,[1,1]]]}}],{'u':{'method_id':'F01'}},12)

    def test_smooth_music_envelope_keeps_stop_and_stays_inside_clip(self):
        keys=gain_envelope([(0,-70),(1,-28),(7,-28),(8.5,-70),(9.7,-70),(11,-28),(14.7,-80)],14.75)
        self.assertTrue(all(k['level_db']==-70 for k in keys if 8.5<=k['time_seconds']<=9.7))
        self.assertLess(keys[-1]['time_seconds'],14.75)
        with self.assertRaises(ValueError):gain_envelope([(0,-20),(14.75,-70)],14.75)

    def test_composer_and_filename_never_grant_recording_rights(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'Chopin.mp3';p.write_bytes(b'synthetic')
            m=recording_manifest(p,title='Synthetic',composer='Chopin',performer='Synthetic',source='user')
            self.assertFalse(m['public_use_allowed']);self.assertEqual(m['music_license_gate'],'HOLD')
            self.assertEqual(m['human_listening_review'],'PENDING')


if __name__=='__main__':unittest.main()
