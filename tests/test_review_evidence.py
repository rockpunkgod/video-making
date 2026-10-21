"""Evidence export regression. Fixtures are not real-film acceptance or review."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave

from ae_production import review_evidence as e


class EvidenceContracts(unittest.TestCase):
    def test_units_keep_fractional_ms_and_rational_rate(self):
        self.assertAlmostEqual(e.ms(1/24),41.6666666667)
        self.assertEqual(e._rate('24000/1001'),{'numerator':24000,'denominator':1001,'fps':24000/1001})
        self.assertIsNone(e._rate('0/0'))
        self.assertIsNone(e.ms(None))
        self.assertEqual(e.frame_ceil(2692.000000000001),2692)
        self.assertEqual(e.frame_floor(2391.999999999999),2392)

    def test_native_collector_reads_without_writing_and_keeps_real_ease(self):
        script=e.native_motion_script([1,703],[])
        for token in ('keyInTemporalEase','keyOutTemporalEase','keyInSpatialTangent','valueAtTime','expression_error'):
            self.assertIn(token,script)
        for token in ('setValue','setValueAtTime','app.open','app.project.save','remove('):
            self.assertNotIn(token,script)

    def test_real_native_numeric_values_are_not_projected_or_rescaled(self):
        comp={'comp_id':703,'width_px':3840,'height_px':2160,'layers':[{
            'id':109,'name':'SOURCE_LIFT_SC03','parent_id':25,'three_d':True,
            'in_ms':1000,'out_ms':2000,'anchor_point':[0,0,0],
            'properties':{'position':{'keys':[
                {'time_ms':1000,'value':[12250,618.66,100],'out_ease':[{'speed':0,'influence_percent':33}]},
                {'time_ms':2000,'value':[12250,623.66,-340]}]}}}]}
        plan={'scenes':[{'id':'SC03','start':0,'end':3}]}
        row=e.motion(plan,{},comp,Path('.'),24)['events'][0]
        self.assertEqual(row['coordinate_system'],'AE_PARENT_LOCAL_3D')
        self.assertEqual(row['properties']['position']['keys'][0]['value'],[12250,618.66,100])
        self.assertEqual(row['start_frame'],24)
        self.assertEqual(row['duration_ms'],1000)
        self.assertIsNone(row['final_video_measured_trajectory'])

    def test_each_known_event_gets_contiguous_frame_sequence(self):
        event={'event_id':'lift','scene_id':'SC03','start_frame':24,'end_frame_exclusive':72,
            'important_for_frames':True,'properties':{'position':{'keys':[
                {'time_ms':1000,'value':[0,0,0]},{'time_ms':2000,'value':[50,0,0]}]}}}
        selected=e.choose_frames([], [event],100,24)
        continuous=[n for n,r in selected.items() if 'consecutive_9_frame_sequence' in r['purposes']]
        self.assertEqual(continuous,list(range(32,41)))
        self.assertTrue({23,24,48,71,72}<=set(selected))

    def test_no_invented_semantic_scene_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);e.write(p/'AV_PLAN.json',{})
            plan={'scenes':[{'id':'SC01','start':0,'end':1/24}], 'segments':[]}
            qa={'plan_sha256':e.file_sha(p/'AV_PLAN.json'),'frames':1}
            row=e.timeline(plan,qa,[{'timestamp_ms':0,'duration_ms':None}],[],{},p,24)['scenes'][0]
            self.assertIsNone(row['mapped_duration_ms'])
            self.assertIsNone(row['independently_measured_scene_boundaries_ms'])
            self.assertIsNone(row['plan_vs_independently_measured_scene_delta_ms'])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Requires existing ffmpeg/ffprobe')
class ActualEncodedFixture(unittest.TestCase):
    """Small real encoded fixture tests mechanics only; never replaces production validation."""
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.media=cls.root/'fixture.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=24:duration=1',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1','-c:v','libx264',
            '-pix_fmt','yuv420p','-c:a','aac','-shortest',str(cls.media)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def export(self):
        p=Path(tempfile.mkdtemp(dir=self.root));media=p/'media';media.mkdir()
        movie=media/'fixture.mp4';shutil.copy2(self.media,movie)
        voice=p/'VOICE.wav'
        subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vn','-ac','1','-c:a','pcm_s16le',str(voice)],check=True)
        project=media/'TEST.aep';project.write_bytes(b'UNIT FIXTURE, NOT ADOBE PRODUCTION')
        pr=media/'TEST.prproj';pr.write_bytes(b'UNIT FIXTURE, NOT ADOBE PRODUCTION')
        plan={'scenes':[{'id':'SC01','start':0,'end':1}], 'segments':[{
            'id':'V01','scene_id':'SC01','text':'fixture','voice_start':0,'voice_end':1,
            'voice':{'path':str(voice),'padded_path':str(voice)}}],
            'cues':[{'id':'C01','scene_id':'SC01','segment':'V01','text':'fixture','start':0,'end':1}]}
        e.write(p/'AV_PLAN.json',plan);e.write(p/'native-identity.json',{'comp_id':1})
        e.write(p/'PICTURE_RECEIPT.json',{'comp_id':1})
        e.write(p/'PR_TIMELINE.json',{'audioTracks':[{'clips':[{'name':voice.name,'start':0,'end':1,'nodeId':'n1'}]}]})
        qa={'media':str(movie),'sha256':e.file_sha(movie),'plan_sha256':e.file_sha(p/'AV_PLAN.json'),
            'frames':24,'native_project':str(project),'premiere_project':str(pr),'full_decode':'PASS'}
        return p,qa,Path(e.export_review_evidence(p,qa))

    def test_ffprobe_actual_frames_and_start_offsets(self):
        pts=e.frame_timestamps(self.media);probe=e.probe_media(self.media)
        meta=e.metadata(self.media,probe,pts,self.root,{'full_decode':'PASS'})
        self.assertEqual(meta['video']['frame_count'],24)
        self.assertEqual([meta['video']['width_px'],meta['video']['height_px']],[320,180])
        self.assertEqual(meta['video']['frame_rate']['fps'],24)
        self.assertAlmostEqual(pts[7]['timestamp_ms'],7/24*1000,places=3)
        self.assertIsNone(meta['acoustic_visual_sync_offset_ms'])

    def test_normal_export_is_generic_linked_and_idempotent(self):
        p,qa,manifest=self.export();m=e.read(manifest)
        self.assertEqual(e.validate_evidence(manifest)['status'],'PASS')
        self.assertEqual(e.export_review_evidence(p,qa),str(manifest))
        aud=e.read(manifest.parent/'audio_manifest.json')
        self.assertEqual(aud['events'][0]['caption_ids'],['C01'])
        self.assertEqual(aud['events'][0]['native_clip_range_ms'],[0,1000])
        self.assertEqual(aud['events'][0]['source_actual_parameters']['sample_rate_hz'],48000)
        self.assertIsNone(aud['events'][0]['native_gain_db'])
        self.assertIsInstance(aud['final_mix']['measurement']['integrated_loudness_lufs'],float)
        self.assertFalse(m['review_or_quality_scoring_performed'])

    def test_tampered_json_frame_source_audio_and_project_are_rejected(self):
        p,qa,manifest=self.export();m=e.read(manifest);base=manifest.parent
        index=e.read(base/'frame_index.json');aud=e.read(base/'audio_manifest.json')
        targets=[base/'motion_manifest.json',base/index['frames'][0]['file'],Path(aud['events'][0]['source_path']),
            base/m['source_snapshots'][0]['path'],base/index['thumbnail_index']['file']]
        for target in targets:
            original=target.read_bytes();target.write_bytes(original+b'TAMPER')
            with self.subTest(target=target),self.assertRaises((ValueError,json.JSONDecodeError)):
                e.validate_evidence(manifest)
            target.write_bytes(original)

    def test_stale_final_video_binding_is_rejected_before_output(self):
        p,qa,manifest=self.export();changed=copy.deepcopy(qa);changed['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'same-version'):e.export_review_evidence(p,changed)

    def test_existing_partial_evidence_is_not_overwritten(self):
        p,qa,manifest=self.export();manifest.rename(manifest.with_suffix('.retained'))
        with self.assertRaises(FileExistsError):e.export_review_evidence(p,qa)


if __name__=='__main__':unittest.main()
