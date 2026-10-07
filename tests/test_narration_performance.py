"""SYNTHETIC performance controls; no real exam/voice/human credentials."""
import ast
from copy import deepcopy
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from pedagogy import compile_plan, copy_projection
from tests.test_mechanical_payoff import freeze
from tests.test_boundary_risk_review import synthetic_review
from tests.test_student_pov import reviewed_copy, ref, assets
from video_contracts import read, sha, write
from scripts.voice_delivery import describe_clip, sha256
from narration_performance.plan import build_plan, validate_plan, check_intent
from narration_performance.adapter import (take_requests, check_speed, generation_take,
                                          verify_realization, CAPABILITIES)
from narration_performance.timing import resolve_timing
from narration_performance.review import risk_qa, review_template, validate_human_review
from voicepacks.tools.generate_gpt_sovits import inference_request, main as producer_main


def synthetic_copy():
    bundle, status, selected = freeze()
    base = compile_plan(bundle, status, selected, mode='worked_example', generated_at='SYNTHETIC')
    pedagogy = compile_plan(bundle, status, selected, mode='worked_example', generated_at='SYNTHETIC',
                            boundary_review=synthetic_review(base, bundle))
    projection = copy_projection(pedagogy, bundle, status)
    copy = reviewed_copy(bundle, status, pedagogy, projection)
    return bundle, status, pedagogy, projection, copy


def synthetic_spec(copy):
    slots = [{'scene_id': s['scene_id'], 'text': s['vo'], 'start': 2+5*i, 'end': 6+5*i}
             for i,s in enumerate(s for s in copy['final_script'] if s['vo'])]
    return {'spec_sha': sha('SYNTHETIC picture'), 'copy_sha': copy['copy_sha'],
        'plan_sha': copy['source_pedagogy_plan']['plan_sha'], 'semantic_binding_sha': sha('SYNTHETIC truth'),
        'copy_lock': {'final_copy_sha': copy['final_copy_sha']},
        'direction': {'canvas': {'fps': 24, 'duration': 30}, 'voice_slots': slots,
                      'phases': {'stamp': 25}, 'silence_candidates': [
                          {'start': 17.1, 'end': 18, 'function': 'SYNTHETIC collapse settle'}]}}


def profile():
    return {'engine': 'gpt-sovits/v2ProPlus', 'text_split_method': 'cut3', 'fragment_interval': .28,
        'reference_language': 'ZH', 'acceptance': {'scope': 'SYNTHETIC OLD OUTPUT ONLY'},
        'settings': {'seed': 42, 'speed_factor': 1, 'top_k': 10, 'top_p': 1,
                     'temperature': .75, 'repetition_penalty': 1.15}}


def wav(path, rate=48000, frames=24000):
    with wave.open(str(path), 'wb') as audio:
        audio.setframerate(rate); audio.setnchannels(1); audio.setsampwidth(2)
        audio.writeframes(struct.pack('<h', 1234)*frames)


def fake_generation(root, plan):
    """Explicit simulation of provider receipts, never actual engine/listening proof."""
    root.mkdir(exist_ok=True)
    base = inference_request(profile(), 'SYNTHETIC', 'SYNTHETIC.wav', 'SYNTHETIC reference')
    rows = take_requests(plan, profile(), base); clips=[]; refs=[]; takes=[]
    generation = {'engine': profile()['engine'], 'profile_sha256': sha('SYNTHETIC profile'),
        'assets_sha256': {'models/gpt.ckpt': sha('SYNTHETIC GPT'), 'models/sovits.pth': sha('SYNTHETIC SoVITS'),
                         'reference/reference.wav': sha('SYNTHETIC reference')},
        'inference_parameters': {k:v for k,v in base.items() if k not in ('text','ref_audio_path','prompt_text')},
        'takes': takes, 'listening_review': 'PENDING', 'public_render_ready': False}
    (root / 'receipts').mkdir()
    for row in rows:
        name=row['id']; wav(root / (name+'.wav'), rate=32000, frames=16000)
        (root / (name+'.txt')).write_text(row['request']['text'], encoding='utf-8')
        clip=describe_clip(root,name,name+'.wav',name+'.txt'); clips.append(clip)
        parameters={k:v for k,v in row['request'].items() if k not in ('text','ref_audio_path','prompt_text')}
        receipt=generation_take(row,clip,row['request']['text'],generation['profile_sha256'],
            generation['assets_sha256'],plan['performance_sha'],parameters)
        path=root / 'receipts' / (name+'.json'); write(path,receipt)
        refs.append({'take_id':name,'scene_id':row['scene_id'],'receipt':'receipts/'+name+'.json',
                     'receipt_sha256':sha256(path),'take_receipt_sha':receipt['take_receipt_sha']})
        takes.append({'id':name,'duration_seconds':.5,'inference_parameters':parameters})
    write(root / 'delivery.json',{'schema':'voice-delivery/v1','clips':clips})
    write(root / 'generation.json',generation)
    realized={'schema':'narration-performance-realization/v1','version':'0.1.0',
        'performance_sha':plan['performance_sha'],'binding':plan['binding'],
        'profile_sha256':generation['profile_sha256'],'assets_sha256':generation['assets_sha256'],
        'engine_capabilities':CAPABILITIES,'takes':refs,'delivery_sha256':sha256(root/'delivery.json'),
        'generation_sha256':sha256(root/'generation.json'),'listening_review':'PENDING',
        'final_voice_accepted':False,'sample_delivery_allowed':False,'public_render_ready':False}
    realized['realization_sha']=sha(realized); write(root/'performance-realization.json',realized)
    return rows, clips, generation, realized


class PerformanceFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, cls.status, cls.pedagogy, cls.projection, cls.copy = synthetic_copy()

    def setUp(self):
        self.spec=synthetic_spec(self.copy); self.plan=build_plan(self.copy,self.spec)


class PerformancePlanTests(PerformanceFixture):
    def test_plan_is_deterministic_and_preserves_all_teaching_inputs(self):
        before=sha([self.bundle,self.status,self.pedagogy,self.projection,self.copy,self.spec])
        self.assertEqual(self.plan,build_plan(self.copy,self.spec))
        validate_plan(self.plan,self.copy,self.spec)
        self.assertEqual(before,sha([self.bundle,self.status,self.pedagogy,self.projection,self.copy,self.spec]))
        for name in ('script_sha','final_copy_sha','source_analysis_sha'):
            self.assertEqual(self.plan['binding'][name],self.copy[name])

    def test_copy_change_invalidates_old_plan(self):
        changed=reviewed_copy(self.bundle,self.status,self.pedagogy,self.projection,
            draft_lines={'pain':{'text':'SYNTHETIC different question-facing expression',
                                  'pedagogy_refs':[ref(self.pedagogy,'/symptom')]}})
        spec=synthetic_spec(changed)
        with self.assertRaises(ValueError): validate_plan(self.plan,changed,spec)

    def test_transcript_even_resealed_cannot_be_rewritten(self):
        broken=deepcopy(self.plan); broken['clips'][0]['transcript']='SYNTHETIC new teaching sentence'
        broken['clips'][0]['transcript_sha']=sha(broken['clips'][0]['transcript'])
        broken.pop('performance_id'); broken.pop('performance_sha')
        broken['performance_sha']=sha(broken); broken['performance_id']='narration-performance:'+broken['performance_sha']
        with self.assertRaisesRegex(ValueError,'binding'): validate_plan(broken,self.copy,self.spec)

    def test_performance_change_has_separate_hash_not_teaching_hash(self):
        changed=build_plan(self.copy,self.spec,{self.plan['clips'][0]['id']:{'intent':{'pace':.6}}})
        self.assertNotEqual(self.plan['performance_sha'],changed['performance_sha'])
        self.assertEqual(self.plan['binding'],changed['binding'])
        self.assertEqual(self.plan['binding']['teaching_semantic_sha'],self.spec['semantic_binding_sha'])

    def test_forbidden_tones_and_new_claim_fields_fail(self):
        for intent in ({'tone':'sad'},{'tone':'cinematic_narrator'},{'answer':'SYNTHETIC'},
                       {'fragment_interval':.1},{'text_split_method':'cut0'}):
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                build_plan(self.copy,self.spec,{self.plan['clips'][0]['id']:{'intent':intent}})

    def test_emphasis_can_only_point_to_existing_lexical_content(self):
        for emphasis in (['SYNTHETIC invented phrase'],[None],['原文','原文']):
            with self.assertRaises(ValueError):
                build_plan(self.copy,self.spec,{self.plan['clips'][0]['id']:{'intent':{'emphasis':emphasis}}})

    def test_invalid_pause_or_unit_interval_rejected(self):
        for key,value in [('pause_before_ms',-1),('pause_after_ms',2001),('pause_after_ms',True),
                          ('pause_before_ms',.5),('pace',float('nan')),('energy',1.1),('certainty',None)]:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                build_plan(self.copy,self.spec,{self.plan['clips'][0]['id']:{'intent':{key:value}}})

    def test_silent_collapse_stop_stamp_remain_silent(self):
        self.assertEqual({s['cognitive_function'] for s in self.plan['silent_beats']},{'collapse','stop','stamp'})
        silent=self.plan['silent_beats'][0]['scene_id']
        with self.assertRaisesRegex(ValueError,'silent'): build_plan(self.copy,self.spec,{silent:{'take_count':1}})

    def test_multitake_only_actual_key_beats_and_maximum_three(self):
        focus=next(c['id'] for c in self.plan['clips'] if c['cognitive_function']=='focus')
        with self.assertRaises(ValueError): build_plan(self.copy,self.spec,{focus:{'take_count':2}})
        with self.assertRaises(ValueError): build_plan(self.copy,self.spec,{self.plan['clips'][0]['id']:{'take_count':4}})
        self.assertEqual(sum(c['take_policy']['count'] for c in self.plan['clips']),7)

    def test_g01_hold_is_not_upgraded(self):
        b,s,p,cp=assets('G01',with_payoff=False,mode='worked_example')
        c=reviewed_copy(b,s,p,cp)
        self.assertEqual(c['availability']['status'],'HOLD')
        before=sha([b,s,p,c])
        with self.assertRaisesRegex(ValueError,'HOLD'): build_plan(c,synthetic_spec(c))
        self.assertEqual(before,sha([b,s,p,c]))

    def test_no_truth_core_registry_solver_or_model_runtime_import(self):
        for path in (Path(__file__).resolve().parents[1]/'narration_performance').glob('*.py'):
            imports=[]
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node,ast.ImportFrom): imports.append(node.module or '')
                elif isinstance(node,ast.Import): imports += [x.name for x in node.names]
            self.assertFalse(any(x.startswith(('core','answer_engine','torch','TTS_infer_pack')) for x in imports))


class PerformanceProducerTests(PerformanceFixture):
    def test_supported_controls_only_and_tail_settings_unchanged(self):
        base=inference_request(profile(),'SYNTHETIC','SYNTHETIC.wav','SYNTHETIC')
        rows=take_requests(self.plan,profile(),base)
        for row in rows:
            self.assertEqual(row['request']['text_split_method'],'cut3')
            self.assertEqual(row['request']['fragment_interval'],.28)
            self.assertNotIn('tone',row['request']); self.assertNotIn('emphasis',row['request'])
            self.assertEqual(row['intent_realization']['tone']['status'],'UNREALIZED')
            self.assertEqual(row['intent_realization']['certainty']['status'],'UNREALIZED')
            check_speed(row['request']['speed_factor'])

    def test_speed_out_of_range_never_accepted(self):
        for value in (.95,1.051,float('nan'),True,'1.0'):
            with self.assertRaises(ValueError): check_speed(value)

    def test_root_and_legacy_tail_conflict_still_fails(self):
        for control,value in [('split_method','cut0'),('fragment_interval',.1)]:
            p=profile(); p['settings'][control]=value
            with self.assertRaisesRegex(ValueError,'Conflicting'): inference_request(p,'SYNTHETIC','SYNTHETIC.wav','SYNTHETIC')

    def test_reference_change_requires_new_receipt_and_stays_pending(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); rows,clips,g,_=fake_generation(root,self.plan)
            original=read(root/'receipts'/ (rows[0]['id']+'.json'))
            changed_assets={**g['assets_sha256'],'reference/reference.wav':sha('SYNTHETIC another reference')}
            newer=generation_take(rows[0],clips[0],rows[0]['request']['text'],g['profile_sha256'],changed_assets,
                self.plan['performance_sha'],original['inference_parameters'])
            self.assertNotEqual(original['take_receipt_sha'],newer['take_receipt_sha'])
            self.assertEqual(newer['listening_review'],'PENDING')
            self.assertFalse(newer['final_voice_accepted'])

    def test_old_accepted_profile_never_accepts_new_takes(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); rows,clips,g,r=fake_generation(root,self.plan)
            verify_realization(self.plan,root/'delivery.json')
            for row in rows:
                receipt=read(root/'receipts'/(row['id']+'.json'))
                self.assertEqual(receipt['listening_review'],'PENDING')
                for field in ('final_voice_accepted','sample_delivery_allowed','public_render_ready'):
                    self.assertFalse(receipt[field])

    def test_wrong_delivery_id_or_receipt_cannot_be_consumed(self):
        for mutation in ('id','receipt','text','accepted'):
            with self.subTest(mutation=mutation), TemporaryDirectory() as folder:
                root=Path(folder); rows,clips,g,r=fake_generation(root,self.plan)
                if mutation=='id':
                    d=read(root/'delivery.json'); d['clips'][0]['id']='SYNTHETIC-other-scene'; write(root/'delivery.json',d)
                elif mutation=='receipt':
                    path=root/'receipts'/(rows[0]['id']+'.json'); value=read(path)
                    value['engine_realization']['tone']['status']='APPLIED'; write(path,value)
                elif mutation=='text': (root/clips[0]['transcript']).write_text('SYNTHETIC changed',encoding='utf-8')
                else:
                    r['final_voice_accepted']=True; r['realization_sha']=sha({k:v for k,v in r.items() if k!='realization_sha'})
                    write(root/'performance-realization.json',r)
                with self.assertRaises(ValueError): verify_realization(self.plan,root/'delivery.json')

    def test_producer_preserves_old_take_directory(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); write(root/'clips.json',[{'id':'SYNTHETIC','text':'SYNTHETIC unchanged'}])
            old=root/'old'; old.mkdir(); (old/'keep.wav').write_bytes(b'SYNTHETIC old bytes')
            argv=['producer','--pack',str(root/'pack'),'--runtime',str(root/'runtime'),
                  '--clips-file',str(root/'clips.json'),'--output',str(old)]
            with patch('sys.argv',argv), self.assertRaises(FileExistsError): producer_main()
            self.assertEqual((old/'keep.wav').read_bytes(),b'SYNTHETIC old bytes')


class PerformanceTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        *_,cls.copy=synthetic_copy()

    def setUp(self):
        temp=TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root=Path(temp.name)
        self.spec=synthetic_spec(self.copy); self.plan=build_plan(self.copy,self.spec); self.clips=[]
        for c in self.plan['clips']:
            wav(self.root/(c['id']+'.wav'))
            (self.root/(c['id']+'.txt')).write_text(c['transcript'],encoding='utf-8')
            self.clips.append(describe_clip(self.root,c['id'],c['id']+'.wav',c['id']+'.txt'))
        self.path=self.root/'delivery.json'; write(self.path,{'schema':'voice-delivery/v1','clips':self.clips})

    def test_protected_payoff_silence_and_silent_stop_hold(self):
        timing=resolve_timing(self.plan,self.spec,self.path)
        for c in timing['clips']:
            for s in timing['protected_silence']:
                self.assertFalse(c['start']<s['end'] and s['start']<c['end'])
        self.assertGreaterEqual(timing['stop_hold_seconds_before_stamp'],.5)
        self.assertFalse(timing['prior_timing_approval_reused'])
        self.assertEqual(timing,resolve_timing(self.plan,self.spec,self.path))

    def test_voice_or_stop_never_truncated_to_fit(self):
        before=(self.root/(self.clips[-1]['audio'])).read_bytes()
        self.spec['direction']['voice_slots'][-1]['end']=18.1
        with self.assertRaisesRegex(ValueError,'RETIMING_REQUIRED'): resolve_timing(self.plan,self.spec,self.path)
        self.assertEqual(before,(self.root/(self.clips[-1]['audio'])).read_bytes())

    def test_audio_duration_change_creates_new_timing_and_caption_cues(self):
        old=resolve_timing(self.plan,self.spec,self.path)
        wav(self.root/self.clips[0]['audio'],frames=26000)
        self.clips[0]=describe_clip(self.root,self.clips[0]['id'],self.clips[0]['audio'],self.clips[0]['transcript'])
        write(self.path,{'schema':'voice-delivery/v1','clips':self.clips})
        new=resolve_timing(self.plan,self.spec,self.path)
        self.assertNotEqual(old['timing_sha'],new['timing_sha'])
        self.assertNotEqual(old['caption_cues'][0]['end'],new['caption_cues'][0]['end'])
        self.assertEqual(old['binding'],new['binding'])
        for k in ('final_voice_accepted','sample_delivery_allowed','public_render_ready'): self.assertFalse(new[k])

    def test_transcript_or_missing_stop_slot_rejected(self):
        write(self.path,{'schema':'voice-delivery/v1','clips':self.clips[:-1]})
        with self.assertRaisesRegex(ValueError,'IDs'): resolve_timing(self.plan,self.spec,self.path)


class PerformanceListeningTests(unittest.TestCase):
    def setUp(self):
        self.comparison={'binding':{'final_copy_sha':sha('SYNTHETIC copy')},
            'outputs':{'A':{'audio_sha':sha('SYNTHETIC A')},'B':{'audio_sha':sha('SYNTHETIC B')}}}
        self.comparison['comparison_sha']=sha(self.comparison)

    def test_human_review_is_pending_not_self_signed_or_public_ready(self):
        review=review_template(self.comparison)
        self.assertEqual(validate_human_review(review,self.comparison)['status'],'PENDING')
        self.assertIsNone(review['preference']); self.assertEqual(len(review['questions']),12)
        for k in ('final_voice_accepted','sample_delivery_allowed','public_render_ready'): self.assertFalse(review[k])

    def complete(self):
        review=review_template(self.comparison); review.update(status='COMPLETED',reviewer='SYNTHETIC HUMAN ONLY',preference='B',no_melancholic_drift=True)
        for q in review['questions']: q['response']='SYNTHETIC external human response, not actual listening'
        review['anti_overacting']={k:False for k in review['anti_overacting']}
        return review

    def test_b_preference_does_not_release_final_voice_or_video(self):
        result=validate_human_review(self.complete(),self.comparison)
        self.assertEqual(result['status'],'B_PREFERRED_ELIGIBLE_FOR_SEPARATE_FREEZE')
        self.assertFalse(result['final_voice_accepted']); self.assertFalse(result['public_render_ready'])

    def test_stale_or_ai_review_rejected(self):
        review=self.complete(); review['reviewer_kind']='ai_host'
        with self.assertRaises(ValueError): validate_human_review(review,self.comparison)
        review=self.complete(); changed=deepcopy(self.comparison); changed['outputs']['B']['audio_sha']=sha('SYNTHETIC new B')
        changed['comparison_sha']=sha({k:v for k,v in changed.items() if k!='comparison_sha'})
        with self.assertRaisesRegex(ValueError,'stale'): validate_human_review(review,changed)

    def test_no_preference_or_overacting_stops_experiment(self):
        review=self.complete(); review['preference']='NO_CLEAR_PREFERENCE'
        self.assertTrue(validate_human_review(review,self.comparison)['status'].startswith('STOP_EXPERIMENT'))
        review=self.complete(); review['anti_overacting']['forced_deep_stop']=True
        self.assertEqual(validate_human_review(review,self.comparison)['status'],'FAIL_PERFORMANCE_DIRECTION')

    def test_melancholic_risk_with_unknown_tail_never_auto_edits_audio(self):
        clips=[]
        for i in range(2):
            clips.append({'id':str(i),'transcript':'SYNTHETIC', 'intent':{'tone':'restrained','energy':.3,'pace':.35,
                'certainty':.8,'emphasis':[],'pause_before_ms':1200,'pause_after_ms':500}})
        plan={'performance_sha':sha('SYNTHETIC'),'clips':clips}
        result=risk_qa(plan)
        self.assertEqual(result['risks'][0]['code'],'MELANCHOLIC_DRIFT_RISK')
        self.assertEqual(result['risks'][0]['falling_tail_evidence'],'UNKNOWN')
        self.assertFalse(result['automatic_audio_change'])
        self.assertEqual(result['no_melancholic_drift'],'PENDING_HUMAN_LISTENING')


if __name__ == '__main__': unittest.main()
