"""P4 regressions: upstream/copy binding, honest closure and exact PCM placement."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np
from creative_os.episode_build import build_episode, reference, frames, caption_parts
from premiere_production.episode_audio import prepare_audio, interchange
from scripts.voice_delivery import describe_clip
from video_contracts import write, read


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.font=next((p for p in (Path('C:/Windows/Fonts/georgia.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')) if p.exists()),None)
        if self.font is None:self.skipTest('Measurement font unavailable')
        a=dict(execution_id='remove-a',output=dict(kind='candidate_decision',candidate='A',effect='eliminate'),
               evidence=[dict(field='passage',start=0,end=5,quote='Alpha')])
        b=dict(execution_id='retain-b',output=dict(kind='candidate_decision',candidate='B',effect='retain'),evidence=deepcopy(a['evidence']))
        self.bundle=dict(asset_id='synthetic',source_snapshot=dict(question_id='synthetic-q',stem='Synthetic question?',passage='Alpha beta gamma.',options=dict(A='First',B='Second'),action_executions=[a,b]),
                         analysis=dict(answer='B',answer_verification=dict(closed=True,candidate_coverage_complete=True,unique_supported_candidate=True)))
        write(self.root/'bundle.json',self.bundle);write(self.root/'status.json',dict(effective_status='ACTIVE'))
        write(self.root/'copy.json',[dict(scene_id='V',vo=['Synthetic transcript.'])])
        write(self.root/'style.json',dict(coordinates=dict(fps=24),type_scale=dict(caption=36,option=44,lifted_block=52,focus_text=46,focus_line_height=62),
            layout=dict(focus_width=1560,focus_max_lines=9),motion=dict(actions=dict(eliminate=dict(frames=10)))))
        self.samples=np.array([1000,-1000,0,32767,-32768]*2400,dtype='<i2')
        with wave.open(str(self.root/'V.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(self.samples.tobytes())
        (self.root/'V.txt').write_text('Synthetic transcript.',encoding='utf-8')
        write(self.root/'delivery.json',dict(schema='voice-delivery/v1',clips=[describe_clip(self.root,'V','V.wav','V.txt')]))
        self.request=dict(style=str(self.root/'style.json'),font=str(self.font),authored_copy=str(self.root/'copy.json'),voice_delivery=str(self.root/'delivery.json'),sources=dict(Q=dict(bundle=str(self.root/'bundle.json'),status=str(self.root/'status.json'))),edit=[])
        for i in range(2):self.request['edit'].append(dict(id=str(i),source='Q',kind='comparison',display_refs=[reference(self.bundle,'/source_snapshot/stem'),reference(self.bundle,'/source_snapshot/options/'+'AB'[i])],voice_ids=['V'] if i==0 else [],action_index=i,lead=2,minimum_seconds=3))
        self.request['edit'].append(dict(id='answer',source='Q',kind='result',display_refs=[reference(self.bundle,'/source_snapshot/options/B')],answer='B',minimum_seconds=2))

    def build(self,request=None):
        with patch('creative_os.episode_build.status_matches',return_value=True):return build_episode(request or self.request)

    def test_repeatable_and_no_input_mutation(self):
        before=deepcopy(self.request);p=self.build();self.assertEqual(p,self.build());self.assertEqual(before,self.request)
        self.assertFalse(p['public_render_ready']);self.assertFalse(p['final_voice_accepted']);self.assertEqual(p['voices'][0]['listening_review'],'PENDING')

    def test_old_status_blocks(self):
        for status in ('WITHDRAWN','SUPERSEDED','STALE','BLOCKED'):
            write(self.root/'status.json',dict(effective_status=status))
            with self.assertRaises(ValueError):self.build()

    def test_voice_and_copy_must_be_exact(self):
        write(self.root/'copy.json',[dict(scene_id='V',vo=['Different transcript.'])])
        with self.assertRaises(ValueError):self.build()

    def test_display_reference_drift(self):
        request=deepcopy(self.request);request['edit'][0]['display_refs'][0]['sha']='bad'
        with self.assertRaises(ValueError):self.build(request)

    def test_another_options_text_cannot_use_this_actions_evidence(self):
        request=deepcopy(self.request);request['edit'][0]['display_refs'][1]=reference(self.bundle,'/source_snapshot/options/B')
        with self.assertRaises(ValueError):self.build(request)

    def test_answer_closure_cannot_be_invented(self):
        b=deepcopy(self.bundle);b['analysis']['answer_verification']['closed']=False;write(self.root/'bundle.json',b)
        with self.assertRaises(ValueError):self.build()

    def test_voice_reuse_and_scene_reuse_fail(self):
        for field,value in [('voice_ids',['V']),('id','0')]:
            request=deepcopy(self.request);request['edit'][1][field]=value
            with self.assertRaises(ValueError):self.build(request)

    def test_replay_reuses_action_without_counting_another_decision(self):
        request=deepcopy(self.request);fast=deepcopy(request['edit'][0]);fast.update(id='fast',voice_ids=[])
        request['edit'][0]['replay_of']='fast';request['edit'].insert(0,fast)
        p=self.build(request);self.assertEqual(len(p['candidate_audit']['events']),2)
        self.assertTrue(p['scenes'][1]['replay_does_not_change_candidate_state'])
        request['edit'][1]['replay_of']='missing'
        with self.assertRaises(ValueError):self.build(request)

    def test_negative_nonfinite_timing_rejected(self):
        for value in (-1,float('nan'),True):
            with self.assertRaises(ValueError):frames(value)

    def test_caption_split_preserves_every_character(self):
        text='First part. Next part — with unchanged punctuation.'
        pieces=caption_parts(text,self.font,36,width=300)
        self.assertGreater(len(pieces),1);self.assertEqual(''.join(pieces),text)

    def test_pcm_reference_does_not_change_speech_samples(self):
        p=self.build();receipt=prepare_audio(p,self.root/'sound')
        with wave.open(receipt['files']['VOICE_REFERENCE.wav']['path'],'rb') as f:data=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
        a=p['voices'][0]['start_frame']*2000
        np.testing.assert_array_equal(data[a:a+len(self.samples)],self.samples)
        self.assertFalse(receipt['public_render_ready'])

    def test_interchange_keeps_separate_source_voice(self):
        p=self.build();receipt=prepare_audio(p,self.root/'sound');xml=self.root/'edit.xml'
        interchange(p,self.root/'picture.mp4',receipt,xml)
        text=xml.read_text(encoding='utf-8');self.assertIn('V.wav',text);self.assertIn('48000',text)
        self.assertNotIn('REVIEW_MIX.wav',text)


if __name__=='__main__':unittest.main()
