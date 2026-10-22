from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production.authored_native import require_pre_package_answers, package
from ae_production.authored_episode import compile_clock, shift_body_clock
from scripts.voice_delivery import sha256
from video_contracts import write, read
import test_authored_episode as clock_fixtures


class PrePackageQuestions(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);self.p=Path(tmp.name)
        (self.p/'media').mkdir()
        for name in ('AV_PLAN.json','picture.mp4','media/PR_NATIVE_EXPORT.mp4','response.txt'):
            (self.p/name).write_text('Synthetic unit fixture, not media or human-review evidence.',encoding='utf-8')
        write(self.p/'MASTER_PICTURE_RECEIPT.json',{'output':str(self.p/'picture.mp4'),'sha256':sha256(self.p/'picture.mp4')})
        self.r={'schema':'pre-package-questions/v1','status':'ANSWERED',
                'plan_sha256':sha256(self.p/'AV_PLAN.json'),'picture_sha256':sha256(self.p/'picture.mp4'),
                'premiere_export_sha256':sha256(self.p/'media/PR_NATIVE_EXPORT.mp4'),
                'questions':{k:{'respondent_role':v,'respondent':'TEST_ONLY','human':True,
                    'performed_required_test':True,'recorded_at':'TEST_ONLY',
                    'answer':'Synthetic response for validation only.',
                    'evidence':{'path':str(self.p/'response.txt'),'sha256':sha256(self.p/'response.txt')}}
                    for k,v in [('student_full_view','high_school_student'),('author_audio_only','author'),('phone_pause','phone_viewer')]}}
        self.path=self.p/'PRE_PACKAGE_QUESTIONS.json'

    def test_master_stops_before_native_or_encoding_work(self):
        with patch('ae_production.authored_native.current_native') as native:
            with self.assertRaisesRegex(ValueError,'HOLD'):package(self.p,master=True)
            native.assert_not_called()

    def test_actual_answers_are_bound_to_all_current_inputs(self):
        write(self.path,self.r);require_pre_package_answers(self.p)
        (self.p/'media/PR_NATIVE_EXPORT.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'another edit'):require_pre_package_answers(self.p)

    def test_pending_ai_unperformed_or_missing_questions_are_rejected(self):
        from copy import deepcopy
        for field,value in [('answer','PENDING'),('human',False),('performed_required_test',False),('respondent','')]:
            r=deepcopy(self.r);r['questions']['phone_pause'][field]=value;write(self.path,r)
            with self.assertRaisesRegex(ValueError,'HOLD'):require_pre_package_answers(self.p)
        r=deepcopy(self.r);r['questions'].pop('student_full_view');write(self.path,r)
        with self.assertRaisesRegex(ValueError,'three questions'):require_pre_package_answers(self.p)

    def test_changed_original_response_is_rejected(self):
        write(self.path,self.r);(self.p/'response.txt').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'evidence'):require_pre_package_answers(self.p)


class VisualTiming(unittest.TestCase):
    def test_method_starts_after_action_and_holds_before_fade_without_editing_takes(self):
        a,c,l=clock_fixtures.ClockConsumption().motion_input();before=compile_clock(a,c,l)
        a['scenes'][0]['method_signal']={'text':'换词不换义','position_px':[1920,720],
            'font_size_px':72,'hold_frames':48,'fade_frames':12}
        p=compile_clock(a,c,l);s=p['scenes'][0]
        self.assertEqual(s['method_signal_start'],s['decision_end'])
        self.assertAlmostEqual(s['method_signal_release']-s['method_signal_start'],2)
        self.assertAlmostEqual(s['method_signal_end']-s['method_signal_release'],.5)
        self.assertEqual(before['segments'][0],p['segments'][0])
        shifted=shift_body_clock(p,7)
        self.assertEqual(shifted['scenes'][0]['method_signal_start'],s['method_signal_start']+7)

    def test_judge_hold_does_not_shorten_reading_or_takes(self):
        a,c,l=clock_fixtures.ClockConsumption().motion_input();before=compile_clock(a,c,l)
        a['scenes'][0]['judge_hold_frames']=24
        p=compile_clock(a,c,l);s=p['scenes'][0]
        self.assertAlmostEqual(s['return_start']-s['decision_end'],1)
        self.assertEqual(s['reading_events'],before['scenes'][0]['reading_events'])
        self.assertEqual(p['segments'][0],before['segments'][0])
