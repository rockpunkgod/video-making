"""Synthetic partial-edit recovery; no Adobe or listening claims."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import wave

from ae_production.authored_native import Host,partial_edit,verify_prior_production
from premiere_production.mcp import PremiereMcpError
from scripts.voice_delivery import sha256
from video_contracts import write


class AuthoredPremiereResume(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.audio=Path(self.temp.name)/'synthetic-frame.wav'
        with wave.open(str(self.audio),'wb') as w:
            w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*48000)
        self.plan={'duration':5,'segments':[{'id':'s1','voice_start':2,'voice':{'padded_path':str(self.audio)}}]}
        self.timeline={'frameSizeHorizontal':3840,'frameSizeVertical':2160,
            'videoTracks':[{'clips':[{'name':'picture.mp4','start':0,'duration':5,'inPoint':0}]}],
            'audioTracks':[{'index':0,'clips':[{'name':self.audio.name,'start':2,'duration':1}]}]}

    def test_completed_take_is_recovered_without_reinsertion(self):
        self.assertEqual(partial_edit(self.plan,self.timeline,'picture.mp4',(3840,2160)),{'s1'})
        self.timeline['audioTracks'][0]['clips']=[]
        self.assertEqual(partial_edit(self.plan,self.timeline,'picture.mp4',(3840,2160)),set())

    def test_duplicate_trimmed_foreign_and_wrong_track_audio_are_rejected(self):
        for mutate in (lambda t:t['audioTracks'][0]['clips'].append(deepcopy(t['audioTracks'][0]['clips'][0])),
                       lambda t:t['audioTracks'][0]['clips'][0].update(duration=.99),
                       lambda t:t['audioTracks'][0]['clips'][0].update(name='foreign.wav'),
                       lambda t:t['audioTracks'][0].update(index=1)):
            t=deepcopy(self.timeline);mutate(t)
            with self.assertRaises(ValueError):partial_edit(self.plan,t,'picture.mp4',(3840,2160))

    def test_changed_or_truncated_picture_is_rejected(self):
        for mutate in (lambda t:t.update(pagination={'truncated':True}),
                       lambda t:t['videoTracks'][0]['clips'][0].update(duration=4.9),
                       lambda t:t.update(frameSizeHorizontal=1920)):
            t=deepcopy(self.timeline);mutate(t)
            with self.assertRaises(ValueError):partial_edit(self.plan,t,'picture.mp4',(3840,2160))

    def test_timeout_repeats_only_read_after_observed_host_activation(self):
        call=Mock(side_effect=[PremiereMcpError('get_project_info timed out'),
                              {'path':str(Path(self.temp.name)/'saved.prproj'),'activeSequence':{'id':'s'}}])
        h=SimpleNamespace(native_name='Adobe Premiere Pro',kind='premiere',pid=42,hwnd=123,c=SimpleNamespace(call=call))
        with patch('ae_production.authored_native.process',return_value={'Id':42}), \
                patch('ae_production.authored_native.activate_observed_host') as activate:
            result=Host.identity(h)
        activate.assert_called_once_with(42,123)
        self.assertEqual(result['target_id'],'sequence:s')
        self.assertEqual([x.args for x in call.call_args_list],[('get_project_info',),('get_project_info',)])

    def test_actual_before_session_bindings_replace_no_missing_private_baseline(self):
        root=Path(self.temp.name);prior=root/'prior.prproj';prior.write_bytes(b'SYNTHETIC PRIOR PROJECT')
        write(root/'SESSION_BEFORE.json',{'identity':{'project_path':''},'sha256':None})
        write(root/'PR_SESSION_BEFORE.json',{'identity':{'project_path':str(prior)},'sha256':sha256(prior)})
        author={'input_files':{str(self.audio):sha256(self.audio)}}
        result=verify_prior_production(root,author)
        self.assertEqual(result['additional_historical_collection'],'NOT_CAPTURED_NOT_INVENTED')
        self.assertFalse((root/'BASELINE_PROTECTION.json').exists())
        prior.write_bytes(b'MODIFIED')
        with self.assertRaisesRegex(ValueError,'Protected prior production'):
            verify_prior_production(root,author)

    def test_missing_actual_host_snapshot_is_not_silently_accepted(self):
        with self.assertRaisesRegex(FileNotFoundError,'before-session'):
            verify_prior_production(Path(self.temp.name),{'input_files':{}})


if __name__=='__main__':unittest.main()
