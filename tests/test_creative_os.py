"""Synthetic frozen fixtures; no real questions, reviews or generated media in Git."""
from copy import deepcopy
from pathlib import Path
import array
import math
import shutil
import json
import tempfile
import unittest
import wave
from unittest.mock import Mock,patch
from video_contracts import read, ROOT, sha, seal
from tests import test_ae_production as baseline
from creative_os.delivery import (make_delivery,attach_fidelity_review,CHECKS,semantic_guard,apply_writer,
    FixtureHumanVoiceWriter,AstraHumanVoiceAdapter,copy_sha,screen_sha,human_voice_critic,invalidation)
from creative_os.timing import narration_track,validate_track,captions,cue_sheet,mix_scratch
from creative_os.director import build_shot_plan
from creative_os.lifecycle import refresh_creative
from ae_production.landscape import build_landscape_contract,validate_landscape


class CreativeOSTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.AEProductionTest.setUpClass()
        cls.package=baseline.AEProductionTest.package;cls.manifest=baseline.AEProductionTest.manifest
        cls.statuses=baseline.AEProductionTest.statuses
        cls.design=read(ROOT/'ae/design/legacy/swiss-cinematic-editorial-v0.3.json')
        cls.design['font']=deepcopy(baseline.AEProductionTest.design['font'])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        specs=[{'scene_id':s['scene_id'],'intent':'stop' if s['scene_type']=='STOP_RULE' else 'core',
                'source_claim_refs':s['claim_refs'],'spoken_copy':'请看当前动作。','on_screen_copy':'当前动作','pause_after':.5}
               for s in self.package['semantic_scenes'] if s['claim_refs']]
        self.delivery=make_delivery(self.package,self.manifest,self.statuses,specs)
        for u in self.delivery['units']:
            self.delivery=attach_fidelity_review(self.delivery,u['unit_id'],'SYNTHETIC HOST',{k:'Synthetic binding test, no teaching certification.' for k in CHECKS})
        recordings={}
        for u in self.delivery['units']:
            path=self.root/(u['unit_id']+'.wav')
            samples=array.array('h',(round(1000*math.sin(i*.05)) for i in range(16000*2)))
            with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(samples.tobytes())
            recordings[u['unit_id']]=path
        self.track=narration_track(self.delivery,recordings)

    def contract(self):
        plan=build_shot_plan(self.package,self.manifest,self.statuses,self.delivery,self.track,self.design)
        sheet=cue_sheet(self.delivery,self.track);audio=mix_scratch(self.track,sheet,self.root/'mix.wav')
        return build_landscape_contract(self.package,self.manifest,self.statuses,self.delivery,self.track,plan,audio,sheet)

    def reject(self,d):
        with self.assertRaises((ValueError,KeyError)):semantic_guard(d,self.package,self.manifest,self.statuses)

    def test_repeat_frozen_inputs_and_separate_copy_locks(self):
        before=sha([self.package,self.manifest,self.statuses]);a=self.contract();b=self.contract()
        self.assertEqual(a,b);self.assertEqual(before,sha([self.package,self.manifest,self.statuses]))
        self.assertFalse(a['public_render_ready']);self.assertEqual(a['canvas']['width'],1920)
        self.assertEqual(a['review_status']['human_taste'],'PENDING')

    def test_copy_edit_resets_host_review_and_preserves_teaching(self):
        response=deepcopy(self.delivery);response['units'][0]['spoken_copy']='先看这个动作。'
        result=apply_writer(self.delivery,FixtureHumanVoiceWriter(response))
        self.assertEqual(result['teaching_semantic_sha'],self.delivery['teaching_semantic_sha'])
        self.assertNotEqual(result['delivery_copy_sha'],self.delivery['delivery_copy_sha'])
        self.assertIsNone(result['units'][0]['fidelity_review']);self.reject(result)

    def test_writer_cannot_change_facts_or_fake_astra(self):
        with self.assertRaisesRegex(ValueError,'unavailable'):AstraHumanVoiceAdapter().write(self.delivery)
        response=deepcopy(self.delivery);response['units'][0]['role']='decider'
        with self.assertRaisesRegex(ValueError,'protected'):apply_writer(self.delivery,FixtureHumanVoiceWriter(response))

    def test_cross_method_dangling_ref_and_role(self):
        for field,value in [('method_id','R99'),('role','decider'),('evidence_refs',[{'asset_id':'wrong','pointer':'/wrong'}]),('source_claim_refs',['missing'])]:
            d=deepcopy(self.delivery);d['units'][0][field]=value;self.reject(d)

    def test_missing_stop_sentence_provenance_and_review(self):
        d=deepcopy(self.delivery);d['units']=d['units'][:-1];d['delivery_copy_sha']=copy_sha(d);d['screen_copy_sha']=screen_sha(d);self.reject(d)
        d=deepcopy(self.delivery);d['units'][0]['sentence_bindings']=[];self.reject(d)
        d=deepcopy(self.delivery);d['units'][0]['fidelity_review']['independent']=True;self.reject(d)

    def test_answer_and_quantifier_expansion_rejected(self):
        for text in ['答案就是A。','一定能得到答案。','所有题都这样。','家人们，这波稳赢。']:
            response=deepcopy(self.delivery);response['units'][0]['spoken_copy']=text
            d=apply_writer(self.delivery,FixtureHumanVoiceWriter(response))
            for u in d['units']:d=attach_fidelity_review(d,u['unit_id'],'TEST',{k:'Synthetic only.' for k in CHECKS})
            self.reject(d)

    def test_measured_audio_and_captions(self):
        self.assertEqual(self.track['units'][0]['estimated_or_recorded_duration'],2)
        cues=captions(self.delivery,self.track,self.design)
        self.assertEqual(''.join(c['text'] for c in cues),''.join(u['spoken_copy'] for u in self.delivery['units']))
        self.assertTrue(all(c['source_claim_refs'] for c in cues))
        with self.assertRaisesRegex(ValueError,'No audio'):narration_track(self.delivery)

    def test_audio_tamper_and_duration_drift(self):
        t=deepcopy(self.track);t['units'][0]['voice_end']+=.2
        from creative_os.timing import track_payload
        t['audio_timing_sha']=sha(track_payload(t))
        with self.assertRaises(ValueError):validate_track(t,self.delivery)
        path=Path(self.track['units'][0]['audio_path']);path.write_bytes(b'changed')
        with self.assertRaises((ValueError,EOFError,wave.Error)):validate_track(self.track,self.delivery)

    def test_audio_path_moves_do_not_change_timing_identity(self):
        t=deepcopy(self.track);old=Path(t['units'][0]['audio_path']);new=self.root/'moved.wav';shutil.copyfile(old,new)
        t['units'][0]['audio_path']=str(new);validate_track(t,self.delivery)
        self.assertEqual(t['audio_timing_sha'],self.track['audio_timing_sha'])

    def test_sentence_boundaries_match_copy_and_real_audio(self):
        recordings={t['unit_id']:t['audio_path'] for t in self.track['units']}
        boundaries={u['unit_id']:[{'type':'SentenceBoundary','offset':1000000,'duration':18000000,'text':u['spoken_copy']}] for u in self.delivery['units']}
        t=narration_track(self.delivery,recordings,sentence_boundaries=boundaries)
        self.assertTrue(all(c['alignment']=='tts_sentence_boundary' for c in captions(self.delivery,t,self.design)))
        boundaries[self.delivery['units'][0]['unit_id']][0]['text']='invented'
        with self.assertRaises(ValueError):narration_track(self.delivery,recordings,sentence_boundaries=boundaries)

    def test_timing_only_invalidates_render_not_editorial(self):
        lock={k:self.delivery[k] for k in ('teaching_semantic_sha','delivery_copy_sha','screen_copy_sha')}
        lock.update(audio_timing_sha=self.track['audio_timing_sha'],editorial_review_sha='approved_copy')
        inv=invalidation(lock,self.delivery,'new_voice');self.assertTrue(inv['render_stale']);self.assertFalse(inv['editorial_stale'])
        self.assertEqual(inv['editorial_review_sha'],'approved_copy')

    def test_withdrawal_propagates_and_missing_status_blocks(self):
        rc=self.contract();statuses=deepcopy(self.statuses)
        for k,s in statuses.items():s['effective_status']='WITHDRAWN';statuses[k]=seal(s)
        inv=refresh_creative(self.package,self.delivery,rc['copy_lock'],self.track['audio_timing_sha'],statuses)
        self.assertTrue(inv['invalidation']['teaching_stale']);self.assertTrue(inv['invalidation']['render_stale'])
        with self.assertRaises(ValueError):validate_landscape(rc,self.package,self.manifest,statuses,self.delivery)
        with self.assertRaises((ValueError,KeyError)):validate_landscape(rc,self.package,self.manifest,{},self.delivery)

    def test_contract_projection_cannot_be_edited(self):
        rc=self.contract();rc['shot_plan']['shots'][0]['components'][0]['text']='new fact'
        with self.assertRaises(ValueError):validate_landscape(rc,self.package,self.manifest,self.statuses,self.delivery)

    def test_collected_audio_replays_with_same_render_identity(self):
        from ae_production.landscape_delivery import collect
        rc=self.contract();preview=self.root/'mock.mp4';preview.write_bytes(b'SYNTHETIC transport fixture only')
        collected=collect(rc,self.package,self.manifest,self.statuses,self.delivery,preview,self.root/'delivery')
        self.assertEqual(rc['render_id'],collected['render_id'])
        self.assertNotEqual(rc['audio']['path'],collected['audio']['path'])
        validate_landscape(collected,self.package,self.manifest,self.statuses,self.delivery)

    def test_final_source_display_binds_screen_and_captions(self):
        a=self.contract()['shot_plan']['source_display']
        self.assertEqual(a['displayed_text_sha'],sha(a['displayed_text']))
        self.assertTrue(a['displayed_text']['components']);self.assertTrue(a['displayed_text']['captions'])
        d=deepcopy(self.delivery);d['units'][0]['on_screen_copy']='当前动作，先看。'
        d=apply_writer(self.delivery,FixtureHumanVoiceWriter(d))
        for u in d['units']:d=attach_fidelity_review(d,u['unit_id'],'TEST',{k:'Synthetic only.' for k in CHECKS})
        t=narration_track(d,{t['unit_id']:t['audio_path'] for t in self.track['units']})
        b=build_shot_plan(self.package,self.manifest,self.statuses,d,t,self.design)['source_display']
        self.assertNotEqual(a['displayed_text_sha'],b['displayed_text_sha'])

    def test_artificial_polish_warning_not_human_certification(self):
        d=deepcopy(self.delivery)
        for u in d['units']:u['spoken_copy']='首先，不难发现。其次，显而易见。此外，值得注意的是。'
        result=human_voice_critic(d);self.assertEqual(result['status'],'AI_TONE_WARNING');self.assertEqual(result['human_taste_review'],'PENDING')

    def test_build_detaches_before_checkpoint(self):
        from ae_production.landscape_execution import build
        rc=self.contract();client=Mock()
        client.call.side_effect=[{'content':'detached'},{'content':json.dumps({'ok':True,'render_id':rc['render_id']})}]
        build(client,rc,self.package,self.manifest,self.statuses,self.delivery,self.root/'ae',self.root/'new.aep')
        first,second=client.call.call_args_list
        self.assertIn('app.project.save(target)',first.args[1]['code']);self.assertNotIn('checkpoint_label',first.args[1])
        self.assertEqual(second.args[1]['checkpoint_label'],'V9-before-build')

    def test_missing_status_blocks_before_ae_mutation(self):
        from ae_production.landscape_execution import build
        rc=self.contract();client=Mock()
        with self.assertRaises((ValueError,KeyError)):
            build(client,rc,self.package,self.manifest,{},self.delivery,self.root/'ae',self.root/'new.aep')
        client.call.assert_not_called()

    def test_ae_verification_preserves_fractional_json_timestamps(self):
        from ae_production.landscape_execution import verify
        rc=self.contract();rc['diagnostic_test_timestamp']=61.333333333333336
        client=Mock();client.call.return_value={'content':json.dumps({'contract_text':json.dumps(rc),
            'binding':{k:rc[k] for k in ('render_id','package_id','package_sha','delivery_sha','template_version')},'audio':rc['audio']['path']})}
        verify(client,123,rc)
        self.assertIn('contract_text:text',client.call.call_args.args[1]['code'])

    def test_schema_reformatting_and_platform_line_endings_keep_render_identity(self):
        original=self.contract();schemas=self.root/'creative/schemas';schemas.mkdir(parents=True)
        for path in (ROOT/'creative/schemas').glob('*.json'):
            content=read(path);text=json.dumps(dict(reversed(list(content.items()))),ensure_ascii=False,indent=4)
            (schemas/path.name).write_bytes(text.replace('\n','\r\n').encode('utf-8'))
        with patch('ae_production.landscape.ROOT',self.root):relocated=self.contract()
        self.assertEqual(original['schema_shas'],relocated['schema_shas'])
        self.assertEqual(original['render_id'],relocated['render_id'])
