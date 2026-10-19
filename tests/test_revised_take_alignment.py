"""Changed body takes must receive fresh measurements, never old cue reuse."""
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from ae_production.authored_episode import reuse_alignment
from scripts.voice_delivery import describe_clip, sha256
from video_contracts import read, write


class RevisedTakeAlignment(unittest.TestCase):
    def test_revised_body_take_is_measured_while_identical_take_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);voice=folder/'voice';voice.mkdir()
            clips=[]
            for vid,text in [('unchanged','Original.'),('body','New provenance.terms')]:
                with wave.open(str(voice/(vid+'.wav')),'wb') as stream:
                    stream.setparams((1,2,48000,0,'NONE','not compressed'))
                    stream.writeframes(b'\0\0'*48000)
                (voice/(vid+'.txt')).write_text(text,encoding='utf-8')
                clips.append(describe_clip(voice,vid,vid+'.wav',vid+'.txt'))
            write(voice/'delivery.json',{'schema':'voice-delivery/v1','clips':clips})
            def aligned(clip,text):
                return {**clip,'transcript':text,'cues':[{'text':text,'start':.1,'end':.9,
                    'text_start':0,'text_end':len(text)}]}
            unchanged=aligned(clips[0],'Original.')
            stale=aligned(clips[1],'Old copy.');stale['audio_sha256']='stale'
            source=folder/'previous.json';write(source,{'model':'synthetic','clips':[unchanged,stale]})
            author={'alignment_source':str(source),'voices':[{'id':c['id'],
                'text':(voice/c['transcript']).read_text('utf-8')} for c in clips],
                'producer':{'alignment_model':'synthetic','python':'not-executed'}}
            def measure(command,check):
                request=Path(command[4]);subset=read(request)
                self.assertEqual([c['id'] for c in subset['clips']],['body'])
                write(Path(command[-1]),{'delivery_sha256':sha256(request),'model':'synthetic',
                    'clips':[aligned(subset['clips'][0],'New provenance.terms')]})
            with patch('ae_production.authored_episode.subprocess.run',side_effect=measure) as worker:
                result=reuse_alignment(folder,author)
            worker.assert_called_once()
            self.assertEqual(result['reused_identical_complete_takes'],1)
            self.assertEqual(result['newly_measured_complete_takes'],1)
            measured=read(folder/'VOICE_ALIGNMENT.json')['clips']
            self.assertEqual(measured[0],unchanged)
            self.assertEqual(measured[1]['transcript'],'New provenance.terms')
            self.assertNotEqual(measured[1]['audio_sha256'],stale['audio_sha256'])
