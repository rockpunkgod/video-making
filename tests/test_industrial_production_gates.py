"""B+ orchestration/evidence controls; synthetic fixtures are not production QA."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ae_production import autonomous_episode as auto
from ae_production import authored_native as native
from scripts.voice_delivery import sha256
from video_contracts import read,write


class CreativeReviewControls(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)
        self.author={'production_policy':'industrial_bplus_v1','revision':'synthetic',
            'audience_opening':{'strategy':'original_task'},'scenes':[], 'sources':{}}
        self.author_id={'provider':'OpenAI','model':'actual_model_not_exposed','agent_id':'author'}
        self.reviewer={'provider':'OpenAI','model':'actual_model_not_exposed','agent_id':'independent'}
        write(self.folder/'AV_AUTHOR.json',self.author)
        write(self.folder/'AUTHORING_RECEIPT.json',{'author_sha256':sha256(self.folder/'AV_AUTHOR.json'),
              'author_identity':self.author_id,'notes':'SENTINEL SELF EVALUATION NOT FOR BLIND PASS'})
        mocked=patch.object(auto,'checked_author',return_value=(self.author,{}));mocked.start();self.addCleanup(mocked.stop)

    def respond(self,request,**changes):
        response={'request_sha':request['request_sha'],'human_approved':False,'identity':self.reviewer,
                  'status':'PASS','findings':[],'dispositions':[]}
        response.update(changes);write(request['response'],response)

    def test_blind_packet_excludes_self_evaluation_and_cross_is_bound(self):
        blind=auto.creative_review(self.folder);packet=read(blind['request'])['packet']
        self.assertNotIn('SENTINEL',str(packet));self.assertNotIn('AUTHORING_RECEIPT',str(packet))
        self.assertIn('audience_opening',packet['presentation'])
        self.respond(blind)
        cross=auto.creative_review(self.folder)
        self.assertEqual(cross['role'],'independent_creative_cross')
        self.assertIn('SENTINEL',read(cross['request'])['packet']['authoring_notes'])
        self.respond(cross)
        result=auto.require_creative_review(self.folder)
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['cross_provider'])
        self.assertFalse(result['human_approved'])
        self.assertEqual(auto.require_creative_review(self.folder),result)

    def test_author_cannot_self_review_or_change_identity_during_cross(self):
        blind=auto.creative_review(self.folder);self.respond(blind,identity=self.author_id)
        with self.assertRaisesRegex(ValueError,'own independent reviewer'):auto.creative_review(self.folder)
        self.respond(blind);cross=auto.creative_review(self.folder)
        self.respond(cross,identity={**self.reviewer,'agent_id':'unbound second reviewer'})
        with self.assertRaisesRegex(ValueError,'same independent reviewer'):auto.creative_review(self.folder)

    def test_changed_author_or_forged_completion_cannot_authorize_build(self):
        write(self.folder/'CREATIVE_REVIEW.json',{'status':'PASS','human_approved':False})
        with self.assertRaisesRegex(ValueError,'completed independent'):auto.require_creative_review(self.folder)
        write(self.folder/'AV_AUTHOR.json',{**self.author,'revision':'changed'})
        with self.assertRaisesRegex(ValueError,'current authoring receipt'):auto.creative_review(self.folder)

    def test_changed_blind_response_invalidates_cross_job(self):
        blind=auto.creative_review(self.folder);self.respond(blind)
        cross=auto.creative_review(self.folder);self.respond(cross)
        self.respond(blind,findings=[{'scene':'SC01','issue':'different fact'}])
        changed=auto.creative_review(self.folder)
        self.assertEqual(changed['status'],'NEEDS_HOST_AGENT')
        self.assertNotEqual(cross['request_sha'],changed['request_sha'])

    def test_author_request_uses_optional_bplus_hook_authority_only(self):
        policy=self.folder/'FREE_SHOWCASE_POLICY.md';policy.write_text('synthetic policy',encoding='utf-8')
        brief=self.folder/'BRIEF.json';spec={'schema':'autonomous-episode-brief/v1','product':'FREE_SHOWCASE',
              'asset_pool':[],'style_inputs':[],'production_policy':'industrial_bplus_v1'}
        write(brief,spec)
        with patch.object(auto,'ROOT',self.folder):
            result=auto.request_author(self.folder,brief)
        requirements=' '.join(read(result['request'])['packet']['requirements'])
        self.assertIn('user_recording',requirements);self.assertIn('production_risk',requirements)
        self.assertIn('original_task',requirements)
        legacy=self.folder/'legacy';legacy.mkdir();write(brief,{k:v for k,v in spec.items() if k!='production_policy'})
        self.assertEqual(auto.request_author(legacy,brief)['status'],'CREATIVE_DECISION_REQUIRED')

    def test_pending_human_voice_stops_before_align_or_adobe(self):
        operations=[]
        def dispatch(op,folder,**kwargs):
            operations.append(op)
            return {'status':'PENDING_HUMAN_VO'} if op=='voice' else {'status':'PASS'}
        with patch.object(auto,'dispatch',side_effect=dispatch),patch.object(auto,'complete_chunks',return_value={'status':'PASS'}),patch.object(auto,'creative_review',return_value={'status':'PASS'}):
            result=auto.run(self.folder)
        self.assertEqual(result['status'],'PENDING_HUMAN_VO')
        self.assertEqual(operations,['check','script','voice'])
        self.assertEqual(read(self.folder/'AUTONOMOUS_RUN.json')['active_stage'],'voice')


class NativeProductionGates(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.folder=Path(temp.name)
        self.author={'production_policy':'industrial_bplus_v1','revision':'synthetic',
            'production_risk':{'requires_native_sample':False,'reason':'Synthetic mature rig','scene_ids':[]}}
        self.plan={'frames':24,'voice_delivery_sha256':'voice-sha','complete_copy_sha256':'copy-sha',
                   'scenes':[{'id':'SC01','start':0,'end':1}],'segments':[]}
        write(self.folder/'AV_AUTHOR.json',self.author);write(self.folder/'AV_PLAN.json',self.plan)
        write(self.folder/'native-identity.json',{'comp_id':1,'master_comp_id':2})
        self.media=self.folder/'synthetic-not-media.mp4';self.media.write_bytes(b'NOT MEDIA: metadata control fixture')
        part={'done':True,'start':0,'end':24,'comp_id':1,'plan_sha256':sha256(self.folder/'AV_PLAN.json'),
              'native_identity_sha256':sha256(self.folder/'native-identity.json'),'path':str(self.media),'sha256':sha256(self.media)}
        self.picture={'output':str(self.media),'sha256':sha256(self.media),'frames':24,'comp_id':1,
                      'plan_sha256':part['plan_sha256'],'parts':[part]}
        write(self.folder/'PICTURE_RECEIPT.json',self.picture)
        project=native.premiere_path(self.folder,'MAIN_FILM.prproj',False);project.write_bytes(b'SYNTHETIC PR PROJECT')
        write(self.folder/'PR_EXPORT_RECEIPT.json',{'plan_sha256':part['plan_sha256'],'output':str(self.media),
            'sha256':sha256(self.media),'project_sha256':sha256(project)})
        write(self.folder/'PR_TIMELINE.json',{})
        self.qa={'plan_sha256':part['plan_sha256'],'same_revision':'synthetic','voice_delivery_sha256':'voice-sha',
            'complete_copy_sha256':'copy-sha','frames':24,'full_decode':'PASS','formal_4k_rendered':False,
            'video_payload_and_timestamps_unchanged':True,'audio_payload_unchanged':True,
            'media':str(self.media),'sha256':sha256(self.media)}
        write(self.folder/'DELIVERY_QA.json',self.qa)
        evidence=self.folder/'observation.txt';evidence.write_text('SYNTHETIC OBSERVATION FIXTURE',encoding='utf-8')
        self.observation={'identity':{'provider':'OpenAI','model':'actual_model_not_exposed','agent_id':'reviewer'},
            'author_sha256':sha256(self.folder/'AV_AUTHOR.json'),'plan_sha256':part['plan_sha256'],
            'voice_delivery_sha256':'voice-sha','media_sha256':sha256(self.media),'status':'PASS',
            'video_observed':True,'audio_observed':True,'playback_rate':1,'continuous_coverage':[[0,1]],
            'continuous_video_review_completed':True,'complete_listening_review_completed':True,
            'observation_evidence':{'path':str(evidence),'sha256':sha256(evidence)}}
        write(self.folder/'INTERNAL_MEDIA_REVIEW_ROUGH.json',self.observation)
        for mocked in [patch.object(auto,'require_creative_review',return_value={'author_identity':{'agent_id':'author'}}),
                       patch('scripts.voice_delivery.validate_user_recordings'),patch.object(native,'delivery_path',return_value=self.folder/'delivery.json'),
                       patch.object(native,'validate_edit')]:
            mocked.start();self.addCleanup(mocked.stop)

    def gate(self,kind='rough'):return native.require_industrial_review(self.folder,self.author,self.plan,kind)

    def test_stale_plan_voice_and_metadata_only_review_are_rejected_before_probe(self):
        with patch.object(native,'probe',side_effect=AssertionError('must reject before media access')):
            for key,value in [('plan_sha256','stale'),('voice_delivery_sha256','old-voice'),('audio_observed',False),('playback_rate',2),('playback_rate',True),('observation_evidence',{})]:
                with self.subTest(key=key,value=value):
                    write(self.folder/'INTERNAL_MEDIA_REVIEW_ROUGH.json',{**self.observation,key:value})
                    with self.assertRaises(ValueError):self.gate()

    def test_forged_pass_and_frame_count_cannot_turn_invalid_bytes_into_real_media(self):
        # Real ffprobe must reject the bytes even though every synthetic receipt says PASS.
        with self.assertRaises(subprocess.CalledProcessError):self.gate()

    def test_stale_rough_picture_or_native_part_cannot_promote(self):
        for changed in [{**self.picture,'plan_sha256':'stale'}, {**self.picture,'parts':[]},
                        {**self.picture,'parts':[{**self.picture['parts'][0],'native_identity_sha256':'stale'}]}]:
            write(self.folder/'PICTURE_RECEIPT.json',changed)
            with self.assertRaises(ValueError):self.gate()

    def test_partial_or_self_review_cannot_promote(self):
        for change in [{'continuous_coverage':[[0,.4],[.5,1]]},{'continuous_coverage':[[0,.9]]},
                       {'identity':{**self.observation['identity'],'agent_id':'author'}}]:
            write(self.folder/'INTERNAL_MEDIA_REVIEW_ROUGH.json',{**self.observation,**change})
            with self.assertRaises(ValueError):self.gate()

    def test_silent_risk_sample_does_not_claim_listening_or_require_voice(self):
        self.author['production_risk']={'requires_native_sample':True,'reason':'new motion','scene_ids':['SC01']}
        write(self.folder/'PROOF_PICTURE_RECEIPT.json',self.picture)
        observation={**self.observation,'audio_observed':False,'complete_listening_review_completed':False}
        write(self.folder/'NATIVE_SAMPLE_REVIEW.json',observation)
        with (patch('scripts.voice_delivery.validate_user_recordings',side_effect=AssertionError('silent sample has no human voice')),
             patch.object(native,'probe',return_value={'streams':[{'codec_type':'video','width':640,'height':360,'r_frame_rate':'24/1','nb_read_frames':'24'}]}),
             patch.object(native.subprocess,'run')):
            result=self.gate('sample')
        self.assertFalse(result['audio_observed'])

    def test_missing_risk_sample_blocks_full_render_before_adobe(self):
        self.author['production_risk']={'requires_native_sample':True,'reason':'new motion','scene_ids':['SC01']}
        with patch.object(native,'current_native',return_value=(self.author,self.plan,{})),patch.object(native,'Host',side_effect=AssertionError('must not contact Adobe')):
            with self.assertRaises(FileNotFoundError):native.render(self.folder)

    def test_master_uses_distinct_pr_paths_and_keeps_rough_receipts(self):
        original=sha256(self.folder/'PR_EXPORT_RECEIPT.json')
        write(self.folder/'MASTER_PICTURE_RECEIPT.json',{'synthetic':True})
        self.assertEqual(native.premiere_path(self.folder,'PR_EXPORT_RECEIPT.json').name,'PR_MASTER_EXPORT_RECEIPT.json')
        self.assertEqual(native.premiere_path(self.folder,'MAIN_FILM.prproj').name,'MAIN_FILM_MASTER.prproj')
        self.assertEqual(native.premiere_path(self.folder,'PR_EXPORT_RECEIPT.json',False),self.folder/'PR_EXPORT_RECEIPT.json')
        self.assertEqual(sha256(self.folder/'PR_EXPORT_RECEIPT.json'),original)

    def test_late_risk_proof_uses_original_frames_and_separate_cache(self):
        self.author.update(host={'render_backend':'interactive'},production_risk={
            'requires_native_sample':True,'reason':'late scene motion','scene_ids':['SC05']})
        self.plan.update(frames=240,scenes=[{'id':'SC01','start':0,'end':1},
            {'id':'SC02','start':1,'end':2},{'id':'SC03','start':2,'end':3},
            {'id':'SC04','start':3,'end':4},{'id':'SC05','start':4,'end':6}])
        write(self.folder/'AV_PLAN.json',self.plan)
        self.assertEqual(native.proof_frame_range(self.author,self.plan),(96,144))
        self.assertEqual(native.proof_frame_range({},self.plan),(0,72))
        directory=self.folder/'native-proof-parts';directory.mkdir()
        part_file=directory/'part-0000.mp4';part_file.write_bytes(b'SYNTHETIC CACHED NATIVE PART')
        part={**self.picture['parts'][0],'start':96,'end':144,'path':str(part_file),
            'sha256':sha256(part_file),'plan_sha256':sha256(self.folder/'AV_PLAN.json')}
        write(part_file.with_suffix('.json'),part)
        target=self.folder/'media/PROOF_PICTURE_1080.mp4';target.write_bytes(b'SYNTHETIC CONCATENATED PART')
        write(self.folder/'PROOF_PICTURE_RECEIPT.json',{'output':str(target),'sha256':sha256(target),
            'start_frame':96,'frames':48,'parts':[part],'comp_id':1,'plan_sha256':part['plan_sha256']})
        # A full-render cache remains independent of the selected late interval.
        full=self.folder/'native-parts';full.mkdir();(full/'unrelated.txt').write_text('preserve',encoding='utf-8')
        with (patch.object(native,'current_native',return_value=(self.author,self.plan,{'comp_id':1})),
              patch.object(native,'require_industrial_review'),patch.object(native,'audit'),
              patch.object(native,'Host') as host,patch.object(native,'require_disk'),
              patch.object(native,'probe',return_value={'streams':[{'codec_type':'video','width':1920,
                  'height':1080,'r_frame_rate':'24/1','nb_read_frames':'48'}]}),
              patch.object(native.subprocess,'run',side_effect=AssertionError('cached proof must not encode again'))):
            result=native.render(self.folder,proof=True)
        host.return_value.mutation_js.assert_not_called()
        self.assertEqual(result['source_frame_range'],[96,144])
        receipt=read(self.folder/'PROOF_PICTURE_RECEIPT.json')
        self.assertEqual((receipt['start_frame'],receipt['frames']),(96,48))
        self.assertEqual(receipt['scene_ids'],['SC05'])
        self.assertFalse((self.folder/'PROOF_AV_RECEIPT.json').exists())
        self.assertEqual((full/'unrelated.txt').read_text(encoding='utf-8'),'preserve')

    def test_rough_package_after_master_keeps_master_caption_and_delay_receipts(self):
        self.author['copy_review']='PENDING'
        self.plan.update(subtitle_mode='premiere_sidecar',cues=[],copy_review='PENDING')
        write(self.folder/'AV_PLAN.json',self.plan)
        self.picture['plan_sha256']=sha256(self.folder/'AV_PLAN.json')
        write(self.folder/'PICTURE_RECEIPT.json',self.picture)
        write(self.folder/'MASTER_PICTURE_RECEIPT.json',{'synthetic':'already exists'})
        (self.folder/'EPISODE_SUBTITLES.srt').write_text('SYNTHETIC SRT',encoding='utf-8')
        for name in ('MASTER_SUBTITLE_DELIVERY.json','MASTER_NATIVE_AUDIO_DELAY.json'):
            write(self.folder/name,{'synthetic':'preserved master receipt'})
        before={name:sha256(self.folder/name) for name in ('MASTER_SUBTITLE_DELIVERY.json','MASTER_NATIVE_AUDIO_DELAY.json')}
        for name in ('PR_NATIVE_EXPORT.mp4','PR_MASTER_NATIVE_EXPORT.mp4','MAIN_FILM_EDITORIAL_PROXY.mp4','MAIN_FILM.aep'):
            (self.folder/'media'/name).write_bytes(('SYNTHETIC '+name).encode())
        streams={'streams':[{'codec_type':'video','width':1920,'height':1080,'r_frame_rate':'24/1','nb_read_frames':'24'},
                            {'codec_type':'audio','codec_name':'aac','sample_rate':'48000','time_base':'1/48000'}]}
        with ExitStack() as stack:
            for mocked in [patch.object(native,'current_native',return_value=(self.author,self.plan,{})),
                patch.object(native,'require_industrial_review'),patch.object(native,'probe',return_value=streams),
                patch.object(native.subprocess,'check_output',return_value=b'\0\0'),patch.object(native.subprocess,'run'),
                patch.object(native,'measured_audio_delay',return_value=(0,[])),patch.object(native,'packet_binding',return_value='synthetic packets'),
                patch.object(native,'audio_packet_rows',return_value=[]),patch.object(native,'verify_prior_production',return_value={}),
                patch('ae_production.review_evidence.export_review_evidence',return_value='synthetic evidence')]:stack.enter_context(mocked)
            native.package(self.folder,master=False)
        self.assertEqual({name:sha256(self.folder/name) for name in before},before)
        self.assertEqual(read(self.folder/'NATIVE_AUDIO_DELAY.json')['native_export_sha256'],sha256(self.folder/'media/PR_NATIVE_EXPORT.mp4'))
        receipt=read(self.folder/'SUBTITLE_DELIVERY.json')
        self.assertEqual(receipt['premiere_readback'],str(self.folder/'PR_CAPTIONS.json'))
        self.assertEqual(receipt['video'],str(self.folder/'media/MAIN_FILM_EDITORIAL_PROXY.mp4'))


class UnifiedEntryStages(unittest.TestCase):
    def test_unified_entry_forwards_bplus_stage_and_run_rejects_legacy_policy(self):
        entry=Path(__file__).resolve().parents[1]/'ae/experiments/adaptive-episode/run.py'
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for stage in ('creative-review','premiere-rough','review-rough'):
                with (patch.object(sys,'argv',[str(entry),'autonomous',str(folder),'--through',stage]),
                      patch('ae_production.authored_episode.production_folder_allowed',return_value=True),
                      patch.object(auto,'run',return_value={'status':'SYNTHETIC'}) as execute):
                    runpy.run_path(str(entry),run_name='__main__')
                self.assertEqual(execute.call_args.args[2],stage)
            write(folder/'AV_AUTHOR.json',{'revision':'legacy'})
            with self.assertRaisesRegex(ValueError,'production policy'):auto.run(folder,through='creative-review')


if __name__=='__main__':unittest.main()
