"""Synthetic media checks; no real question, recording or licensing fixture."""
import tempfile
from pathlib import Path
import unittest
from copy import deepcopy
from unittest.mock import patch
from video_contracts import sha,write
from video_contracts.passage import export_bundle,status_manifest
from creative_os.hero import file_sha
from creative_os.passage_video import prepare,validate_plan
from creative_os.passage_delivery import caption_cues,write_ass,verified_head
from tests.test_reviewed_passage import fixture
from premiere_production.passage import check_sequence


class PassageDeliveryTests(unittest.TestCase):
    def test_premiere_does_not_accept_extra_or_truncated_media(self):
        sequence={'id':'synthetic','pagination':{'truncated':False},'end':12,
            'videoTracks':[{'clips':[{'start':0,'duration':12}]}],
            'audioTracks':[{'clips':[{'start':0,'duration':12}]}]}
        settings={'id':'synthetic','frameSizeHorizontal':1920,'frameSizeVertical':1080,
            'timebase':'10584000000','audioSampleRateHz':48000,'audioChannelCount':2}
        check_sequence(sequence,settings,'synthetic',12)
        changed=deepcopy(sequence);changed['audioTracks'][0]['clips'][0]['duration']=11
        with self.assertRaises(ValueError):check_sequence(changed,settings,'synthetic',12)
        changed=deepcopy(sequence);changed['videoTracks'].append({'clips':[{'start':0,'duration':12}]})
        with self.assertRaises(ValueError):check_sequence(changed,settings,'synthetic',12)
        with self.assertRaises(ValueError):check_sequence(sequence,settings,'different',12)

    def test_asr_cannot_rewrite_authored_copy(self):
        text='这是合成字幕，保留原句。'
        asr={'rows':[{'words':[{'word':c,'start':i/4,'end':(i+1)/4}
                              for i,c in enumerate('这是合成字母保留原句')]}]}
        cues=caption_cues(text,asr,4,max_chars=7)
        self.assertEqual(''.join(c['text'] for c in cues),text)
        self.assertTrue(all(0<=c['start']<c['end']<=4 for c in cues))
        self.assertTrue(all(a['end']<=b['start'] for a,b in zip(cues,cues[1:])))

    def test_unrelated_asr_is_not_used(self):
        asr={'rows':[{'words':[{'word':'unrelated','start':0,'end':1}]}]}
        with self.assertRaises(ValueError):caption_cues('合成中文',asr,2)

    def test_ass_control_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                write_ass(Path(folder)/'test.ass',[{'start':0,'end':1,'text':'{injected}'}])

    def test_changed_native_hold_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/'synthetic';f.write_bytes(b'not-real-media')
            scene={'segment_id':'synthetic','segment_sha':'bound','duration':10}
            head={'scene_sha':sha(dict(scene,duration=24)),'segment_sha':'bound',
                  'static_hold_verified':True,'video':str(f),'video_sha':file_sha(f),
                  'hold_frame':str(f),'hold_sha':file_sha(f)}
            verified_head(scene,head);f.write_bytes(b'changed')
            with self.assertRaises(ValueError):verified_head(scene,head)

    @patch('creative_os.passage_video.scene_layout')
    def test_plan_checks_voice_status_timing_fonts(self,layout):
        # Mock only typography; exercise real frozen review, hashes and file bindings.
        layout.side_effect=lambda b,s,f,e:{'segment_id':s['segment_id'],'source':'synthetic'}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);b=export_bundle(fixture(),'one');status=status_manifest(b,'one')
            media=root/'voice.wav';media.write_bytes(b'synthetic-voice-bytes')
            font=root/'font';font.write_bytes(b'synthetic-font')
            for s in b['payload']['review']['segments']:
                write(root/s['segment_id']/'receipt.json',{'text':s['text'],'path':str(media),
                     'sha256':file_sha(media),'duration':5,'lesson_binding_sha':b['semantic_binding_sha']})
            plan=prepare(b,status,root,{'chinese':str(font)})
            validate_plan(plan,b,status)
            with self.assertRaises(ValueError):validate_plan(plan,b,status_manifest(b,'two','WITHDRAWN'))
            for change in ('binding','overlap','negative_offset'):
                p=deepcopy(plan)
                if change=='binding':p['scenes'][0]['voice']['lesson_binding_sha']='other'
                elif change=='overlap':p['scenes'][1]['start']=0
                else:p['scenes'][0]['voice_start']=-2
                p['plan_sha']=sha({k:v for k,v in p.items() if k!='plan_sha'})
                with self.assertRaises(ValueError):validate_plan(p,b,status)
            font.write_bytes(b'font-updated')
            with self.assertRaises(ValueError):validate_plan(plan,b,status)
