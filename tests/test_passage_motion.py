"""Synthetic checks for phrase-bound motion and accepted voice reference drift."""
from pathlib import Path
import tempfile
import unittest
from video_contracts import write
from creative_os.hero import file_sha
from creative_os.passage_motion import resolve_motion,validate_motion,time_expression
from scripts.generate_anchored_passage_voice import reference_binding


class PassageMotionTests(unittest.TestCase):
    def test_motion_uses_exact_copy_and_preserves_native_animation_speed(self):
        with tempfile.TemporaryDirectory() as folder:
            text='先看证据，再看条件，最后得到结果。'
            write(Path(folder)/'s01/asr.json',{'audio_sha':'synthetic','rows':[{'words':[
                {'word':c,'start':i*.3,'end':(i+1)*.3} for i,c in enumerate(text)]}]})
            plan={'plan_sha':'synthetic-plan','scenes':[{'segment_id':'s01','duration':8,'voice_start':.4,
                'voice':{'text':text,'duration':6,'sha256':'synthetic'},'kind':'closure','screen':'合成结果',
                'annotations':[{'quote':'synthetic evidence'},{'quote':'synthetic condition'}]}]}
            anchors={'s01':['证据','条件','结果']}
            motion=resolve_motion(plan,anchors,folder,'presentation')
            validate_motion(motion,plan,folder)
            events=motion['scenes']['s01'];self.assertEqual([e['native_start'] for e in events],[.5,1.25,2])
            self.assertTrue(all(b['start']-a['start']>=.75 for a,b in zip(events,events[1:])))
            self.assertTrue(time_expression(events).startswith('PTS+if('))
            self.assertNotIn('*PTS',time_expression(events))
            with self.assertRaises(ValueError):resolve_motion(plan,{'s01':['无依据','条件','结果']},folder,'presentation')
            motion['scenes']['s01'][0]['start']+=1
            with self.assertRaises(ValueError):validate_motion(motion,plan,folder)

    def test_reordering_cannot_drop_or_invent_an_event(self):
        with tempfile.TemporaryDirectory() as folder:
            write(Path(folder)/'s/asr.json',{'audio_sha':'synthetic','rows':[]})
            plan={'plan_sha':'x','scenes':[{'segment_id':'s','voice':{'sha256':'synthetic'},
                'annotations':[{'quote':'example'}],'kind':'closure'}]}
            with self.assertRaises(ValueError):resolve_motion(plan,{'s':['a','b']},folder,'p',{'s':['verdict','verdict']})

    def test_reference_or_model_drift_fails_before_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Path(folder);audio=r/'reference.wav';audio.write_bytes(b'synthetic-only')
            (r/'model.safetensors').write_bytes(b'not-a-real-model');write(r/'config.json',{'tts_model_type':'base'})
            request={'reference':{'audio':str(audio),'audio_sha':file_sha(audio),'text':'合成参考'},
                     'model':str(r),'settings':{'seed':1}}
            a=reference_binding(request);request['settings']['seed']=2
            self.assertNotEqual(a,reference_binding(request))
            write(r/'config.json',{'tts_model_type':'voice_design'})
            with self.assertRaises(ValueError):reference_binding(request)
            write(r/'config.json',{'tts_model_type':'base'});audio.write_bytes(b'changed')
            with self.assertRaises(ValueError):reference_binding(request)
