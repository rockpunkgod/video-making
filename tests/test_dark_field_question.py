"""Synthetic checks: frozen semantics, protected speech, and voice-only handoff."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET

import numpy as np
from creative_os.dark_field_question import integrate
from premiere_production.episode_audio import interchange
from scripts.dark_question_audio import voice_only
from scripts.voice_delivery import sha256


def fixture():
    return dict(fps=24,duration=70,duration_frames=1680,style={'synthetic':True},
        source={'answer':None},projections=[{'text':'synthetic exact evidence'}],
        voices=[dict(id=k,start_frame=i*140,end_frame=i*140+n,text=k,audio_sha256=k)
                for i,(k,n) in enumerate(zip(('A01','A02','A03','A04','A05','A06'),(109,98,63,61,82,117)))],
        candidate_events=[{'candidate':'D','effect':'eliminate'}],replay={},public_render_ready=False)


class QuestionTests(unittest.TestCase):
    def test_retiming_preserves_frozen_inputs_and_samples(self):
        current=fixture();before=deepcopy(current);baseline=dict(deepcopy(current),proof={'accepted':True})
        p=integrate(baseline,current)
        self.assertEqual(current,before)
        for key in ('style','source','projections'):self.assertEqual(p[key],current[key])
        self.assertEqual({v['id']:v['audio_sha256'] for v in p['voices']},
                         {v['id']:v['audio_sha256'] for v in current['voices']})
        self.assertFalse(p['replay']['changes_candidate_state'])
        self.assertFalse(p['integration']['master_render_allowed'])

    def test_changed_frozen_input_rejects_reuse(self):
        current=fixture();old=deepcopy(current);current['source']['answer']='X'
        with self.assertRaises(ValueError):integrate(old,current)

    def test_short_voice_cannot_silently_miss_its_lift(self):
        current=fixture();current['voices'][2]['end_frame']=current['voices'][2]['start_frame']+10
        with self.assertRaises(ValueError):integrate(deepcopy(current),current)

    def test_voice_mix_is_sample_exact_and_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sample.wav';data=np.arange(4000,dtype='<i2')
            with wave.open(str(path),'wb') as out:
                out.setparams((1,2,48000,0,'NONE','not compressed'));out.writeframes(data.tobytes())
            clip=dict(id='synthetic',path=str(path),audio_sha256=sha256(path),start_frame=24,end_frame=26)
            plan=dict(fps=24,duration_frames=1680,voices=[clip])
            samples,_=voice_only(plan)
            self.assertTrue(np.array_equal(samples[48000:52000],data))
            self.assertEqual(np.count_nonzero(samples[:48000]),0)
            plan['voices'].append(deepcopy(clip))
            with self.assertRaises(ValueError):voice_only(plan)

    def test_premiere_voice_only_handoff_contains_no_music_or_sfx_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'edit.xml';p=fixture()
            for v in p['voices']:v['path']=str(Path(folder)/(v['id']+'.wav'))
            interchange(p,Path(folder)/'picture.mp4',{},path,include_original_cues=False)
            root=ET.parse(path)
            self.assertEqual(len(root.findall('.//audio/track')),1)
            self.assertEqual(len(root.findall('.//audio/track/clipitem')),6)


if __name__=='__main__':unittest.main()
