"""Synthetic checks for failure modes observed in native production."""
import copy
import unittest
from premiere_production.cinema import resolve_media, reconcile_open, audit_timeline


class NativeCinemaTests(unittest.TestCase):
    def test_display_name_cannot_select_offline_unc_drive(self):
        items=[dict(type='clip',nodeId='bad',mediaPath=r'\\\E:\private\x.wav'),dict(type='clip',nodeId='good',mediaPath=r'E:\private\x.wav')]
        self.assertEqual(resolve_media(items,{'voice':r'E:\private\x.wav'}),{'voice':'good'})

    def test_duplicate_real_paths_require_disambiguation(self):
        items=[dict(type='clip',nodeId=n,mediaPath=r'E:\private\x.wav') for n in ('a','b')]
        with self.assertRaises(ValueError):resolve_media(items,{'voice':r'E:\private\x.wav'})

    def test_timeout_requires_fresh_expected_project(self):
        with self.assertRaises(ValueError):reconcile_open(r'E:\owned.prproj',{'path':r'E:\unrelated.prproj'})
        self.assertEqual(reconcile_open(r'E:\owned.prproj',{'path':r'e:\owned.prproj'})['status'],'CONFIRMED_CURRENT_PROJECT')

    def fixtures(self):
        sequence=dict(id='synthetic',end=3,pagination={'truncated':False},audioTracks=[{'clips':[dict(name='voice',start=1,end=2)]}])
        settings=dict(id='synthetic',frameSizeHorizontal=3840,frameSizeVertical=2160,audioSampleRateHz=48000,videoFrameRate={'seconds':1/24})
        return sequence,settings,[dict(id='voice',start=1,end=2)]

    def test_clipped_stop_is_rejected(self):
        s,t,v=self.fixtures();s['audioTracks'][0]['clips'][0]['end']=1.9
        with self.assertRaises(ValueError):audit_timeline(s,t,v,3)

    def test_paged_snapshot_is_not_complete(self):
        s,t,v=self.fixtures();s['pagination']['truncated']=True
        with self.assertRaises(ValueError):audit_timeline(s,t,v,3)

    def test_host_sequence_change_is_rejected(self):
        s,t,v=self.fixtures();t['id']='different'
        with self.assertRaises(ValueError):audit_timeline(s,t,v,3)

    def test_valid_native_readback_is_not_human_approval(self):
        s,t,v=self.fixtures();self.assertEqual(audit_timeline(s,t,v,3)['human_review'],'PENDING')

    def test_missing_frame_conversion_is_rejected(self):
        s,t,v=self.fixtures();del v[0]['start']
        with self.assertRaises(ValueError):audit_timeline(s,t,v,3)

    def test_explicit_native_extension_is_supported(self):
        s,t,v=self.fixtures();s['audioTracks'][0]['clips'][0]['name']='voice.wav';v[0]['native_name']='voice.wav'
        self.assertEqual(audit_timeline(s,t,v,3)['voice_count'],1)
