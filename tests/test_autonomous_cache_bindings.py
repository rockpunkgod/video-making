"""Real file/ledger binding controls with synthetic bytes; no Adobe or media QA."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production import autonomous_episode as autonomous
from scripts.voice_delivery import sha256
from video_contracts import read,write


class RestoredProjectCacheBindings(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name)/'episode';self.folder.mkdir()
        media=self.folder/'media';media.mkdir()
        self.aep=media/'MAIN_FILM.aep';self.pr=media/'MAIN_FILM.prproj'
        self.aep.write_bytes(b'SYNTHETIC saved native project')
        self.pr.write_bytes(b'SYNTHETIC package-time Premiere project')
        self.movie=media/'synthetic.bin';self.movie.write_bytes(b'SYNTHETIC binding test, not media')
        write(self.folder/'AV_AUTHOR.json',{'revision':'synthetic'})
        self.plan={'revision':'synthetic','frames':24,'voice_delivery_sha256':'voice',
                   'complete_copy_sha256':'copy','segments':[]}
        write(self.folder/'AV_PLAN.json',self.plan)
        self.receipt={'plan_sha256':sha256(self.folder/'AV_PLAN.json'),
                      'output':str(self.movie),'sha256':sha256(self.movie),'project_sha256':sha256(self.pr)}
        write(self.folder/'PR_EXPORT_RECEIPT.json',self.receipt)
        self.qa={'plan_sha256':sha256(self.folder/'AV_PLAN.json'),'same_revision':'synthetic',
            'frames':24,'voice_delivery_sha256':'voice','complete_copy_sha256':'copy','full_decode':'PASS',
            'formal_4k_rendered':True,'media_role':'NATIVE_4K_MASTER','complete_takes':[],
            'video_payload_and_timestamps_unchanged':True,'audio_payload_unchanged':True,
            'public_render_ready':False,'media':str(self.movie),'sha256':sha256(self.movie),
            'native_project_sha256':sha256(self.aep),'premiere_project_sha256':sha256(self.pr)}
        write(self.folder/'MASTER_DELIVERY_QA.json',self.qa)
        for name in ('PR_SEQUENCE.json','PR_TIMELINE.json','PR_SETTINGS.json'):
            write(self.folder/name,{})
        result={'after_effects':{'restored':True},'premiere':{'opened':True,'verified':True}}
        write(self.folder/'AUTONOMOUS_RUN.json',{'stages':{'restore':{
            'author_sha256':sha256(self.folder/'AV_AUTHOR.json'),'result':result}}})
        self.pr.write_bytes(b'SYNTHETIC final saved Premiere metadata')
        write(self.folder/'RESTORED_HOSTS.json',{'results':result,'saved_current_projects':{
            'after_effects':{'path':str(self.aep.resolve()),'sha256':sha256(self.aep)},
            'premiere':{'path':str(self.pr.resolve()),'sha256':sha256(self.pr)}}})
        mocked=patch('ae_production.authored_native.current_native',return_value=({},self.plan,{}))
        mocked.start();self.addCleanup(mocked.stop)
        host=patch('ae_production.authored_native.Host',side_effect=AssertionError('cache verification must not open Adobe'))
        host.start();self.addCleanup(host.stop)

    def validate(self):
        autonomous.validate_cached_stage(self.folder,'premiere')
        autonomous.validate_cached_stage(self.folder,'package-master')
        autonomous.validate_cached_stage(self.folder,'restore')

    def test_final_same_author_saved_metadata_is_accepted_without_rewriting_history(self):
        originals={n:sha256(self.folder/n) for n in ('MASTER_DELIVERY_QA.json','PR_EXPORT_RECEIPT.json')}
        self.validate()
        self.assertNotEqual(sha256(self.pr),self.receipt['project_sha256'])
        for name,digest in originals.items():
            self.assertEqual(sha256(self.folder/name),digest)

    def test_changed_project_path_even_with_matching_bytes_is_rejected(self):
        foreign=self.folder/'foreign.prproj';foreign.write_bytes(self.pr.read_bytes())
        restored=read(self.folder/'RESTORED_HOSTS.json')
        restored['saved_current_projects']['premiere'].update(path=str(foreign.resolve()),sha256=sha256(foreign))
        write(self.folder/'RESTORED_HOSTS.json',restored)
        for op in ('premiere','package-master','restore'):
            with self.subTest(op=op),self.assertRaises(ValueError):
                autonomous.validate_cached_stage(self.folder,op)

    def test_relative_path_cannot_substitute_for_exact_final_project(self):
        restored=read(self.folder/'RESTORED_HOSTS.json')
        restored['saved_current_projects']['premiere']['path']='media/MAIN_FILM.prproj'
        write(self.folder/'RESTORED_HOSTS.json',restored)
        with self.assertRaises(ValueError):self.validate()

    def test_different_author_cannot_authorize_final_saved_bytes(self):
        index=read(self.folder/'AUTONOMOUS_RUN.json')
        index['stages']['restore']['author_sha256']='a different author'
        write(self.folder/'AUTONOMOUS_RUN.json',index)
        with self.assertRaises(ValueError):self.validate()

    def test_missing_or_incomplete_restore_does_not_authorize_changed_project(self):
        original=read(self.folder/'AUTONOMOUS_RUN.json')
        for mutate in (lambda i:i['stages'].pop('restore'),
                       lambda i:i['stages']['restore']['result'].pop('after_effects'),
                       lambda i:i['stages']['restore']['result']['after_effects'].update(restored=False),
                       lambda i:i['stages']['restore']['result']['premiere'].update(verified=False)):
            index=deepcopy(original);mutate(index);write(self.folder/'AUTONOMOUS_RUN.json',index)
            with self.subTest(index=index),self.assertRaises(ValueError):self.validate()

    def test_restore_file_must_match_completed_stage_and_bind_both_projects(self):
        original=read(self.folder/'RESTORED_HOSTS.json')
        for mutate in (lambda r:r['results']['premiere'].update(verified=False),
                       lambda r:r['saved_current_projects'].pop('after_effects')):
            record=deepcopy(original);mutate(record);write(self.folder/'RESTORED_HOSTS.json',record)
            with self.subTest(record=record),self.assertRaises(ValueError):self.validate()

    def test_changes_after_the_final_saved_snapshot_are_rejected(self):
        self.pr.write_bytes(b'UNEXPECTED later edit')
        with self.assertRaises(ValueError):self.validate()

    def test_original_package_bytes_need_no_restore_exception(self):
        self.pr.write_bytes(b'SYNTHETIC package-time Premiere project')
        (self.folder/'RESTORED_HOSTS.json').unlink();(self.folder/'AUTONOMOUS_RUN.json').unlink()
        autonomous.validate_cached_stage(self.folder,'premiere')
        autonomous.validate_cached_stage(self.folder,'package-master')


class ProductionWorktreeLedger(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.main,self.worktree=self.root/'main',self.root/'integration'
        self.main.mkdir();self.worktree.mkdir()
        self.folder=self.worktree/'local-data/free-showcase/episode';self.folder.mkdir(parents=True)
        self.expected=self.worktree/'local-data/audience-learning'
        self.listing=b''.join(b'worktree '+str(p).encode('utf-8')+b'\0HEAD synthetic\0\0' for p in (self.main,self.worktree))
        self.media=self.folder/'synthetic.bin';self.media.write_bytes(b'SYNTHETIC no media claims')
        self.author={'revision':'synthetic','product':'FREE_SHOWCASE','sources':{},'teaching_focus':{}}
        self.plan={'revision':'synthetic','format':{'fps':24},'duration':1,'frames':24,
                   'voice_delivery_sha256':'voice','complete_copy_sha256':'copy','segments':[],
                   'scenes':[{'id':'S1','start':0,'end':1,'audience_intent':'SYNTHETIC task'}]}
        write(self.folder/'AV_PLAN.json',self.plan)
        self.qa={'media':str(self.media),'sha256':sha256(self.media),'same_revision':'synthetic','frames':24,
                 'plan_sha256':sha256(self.folder/'AV_PLAN.json'),
                 'voice_delivery_sha256':'voice','complete_copy_sha256':'copy'}
        write(self.folder/'MASTER_DELIVERY_QA.json',self.qa)
        self.observation={'human_approved':False,'media_sha256':self.qa['sha256'],
            'continuous_coverage':[],'video_observed':False,'audio_observed':False,'issues':[{
                'issue_id':'SYNTHETIC-ONE','media_sha256':self.qa['sha256'],'scene':'S1','range':[0,.5],
                'observed_fact':'SYNTHETIC structural control','severity':'minor','responsible_module':'layout',
                'revision':'SYNTHETIC suggested change','recheck':'PENDING','observation_kind':'engineering_measurement'}]}
        for mocked in (
            patch.object(autonomous,'ROOT',self.main),
            patch.object(autonomous.subprocess,'check_output',return_value=self.listing),
            patch('ae_production.authored_native.plan',return_value=(self.author,self.plan)),
            patch.object(autonomous,'actual_scene_map',return_value={'path':'SYNTHETIC mapping'}),
            patch.object(autonomous,'script_text',return_value='SYNTHETIC exact copy'),
            patch.object(autonomous,'job',return_value=self.observation),
            patch.object(autonomous,'review_page')):
            mocked.start();self.addCleanup(mocked.stop)

    def test_new_review_uses_actual_worktree_ledger_and_resumes_from_main(self):
        result=autonomous.review(self.folder)
        self.assertEqual(result['ledger_root'],str(self.expected.resolve()))
        self.assertEqual(len(result['ledger_records']),1)
        self.assertTrue((self.expected/'audience.sqlite3').is_file())
        self.assertFalse((self.main/'local-data/audience-learning').exists())
        self.assertEqual(autonomous.review(self.folder),result)

    def test_descriptive_acceptance_cannot_break_resume_or_duplicate_the_ledger(self):
        from content_os.engagement_learning import AudienceLearning
        self.observation['user_acceptance']={'copy':'REVIEWED','film':'PENDING'}
        result=autonomous.review(self.folder)
        self.assertEqual(result['user_acceptance'],'PENDING')
        self.assertFalse(result['human_approved']);self.assertFalse(result['public_render_ready'])
        original=(self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes()
        self.assertEqual(autonomous.review(self.folder),result)
        self.assertEqual((self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes(),original)
        self.assertEqual(len(AudienceLearning(self.expected).records()),1)
        self.assertEqual(self.observation['user_acceptance'],{'copy':'REVIEWED','film':'PENDING'})

    def test_changed_actual_observation_still_requires_a_new_cut(self):
        from content_os.engagement_learning import AudienceLearning
        autonomous.review(self.folder)
        original=deepcopy(self.observation)
        cached=(self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes()
        for mutate in (lambda o:o['issues'][0].update(observed_fact='CHANGED actual observation'),
                       lambda o:o['issues'][0].update(range=[0,.75]),
                       lambda o:o.update(audio_observed=True),
                       lambda o:o.update(continuous_coverage=[[0,1]])):
            self.observation.clear();self.observation.update(deepcopy(original));mutate(self.observation)
            with self.assertRaisesRegex(ValueError,'Preserve the existing independent observation'):
                autonomous.review(self.folder)
            self.assertEqual((self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes(),cached)
            self.assertEqual(len(AudienceLearning(self.expected).records()),1)

    def test_cached_host_acceptance_and_publication_values_cannot_be_upgraded(self):
        original=autonomous.review(self.folder)
        for key,value in [('user_acceptance','APPROVED'),('human_approved',True),('public_render_ready',True)]:
            changed=deepcopy(original);changed[key]=value
            write(self.folder/'INTERNAL_MEDIA_REVIEW.json',changed)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Preserve the existing independent observation'):
                autonomous.review(self.folder)

    def test_missing_required_or_additional_observed_fact_cannot_resume(self):
        from content_os.engagement_learning import AudienceLearning
        self.observation['perception_scope']='SYNTHETIC explicit additional fact'
        autonomous.review(self.folder)
        original=deepcopy(self.observation)
        cached=(self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes()
        for key in ('issues','continuous_coverage','perception_scope'):
            self.observation.clear();self.observation.update(deepcopy(original));self.observation.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):
                autonomous.review(self.folder)
            self.assertEqual((self.folder/'INTERNAL_MEDIA_REVIEW.json').read_bytes(),cached)
            self.assertEqual(len(AudienceLearning(self.expected).records()),1)

    def test_legacy_review_without_ledger_path_resumes_in_its_original_worktree(self):
        legacy=autonomous.review(self.folder);legacy.pop('ledger_root')
        write(self.folder/'INTERNAL_MEDIA_REVIEW.json',legacy)
        self.assertEqual(autonomous.review(self.folder),legacy)
        self.assertFalse((self.main/'local-data/audience-learning').exists())

    def test_another_registered_worktree_or_arbitrary_ledger_cannot_replace_original(self):
        original=autonomous.review(self.folder)
        for path in (self.main/'local-data/audience-learning',self.root/'foreign/local-data/audience-learning'):
            result={**original,'ledger_root':str(path.resolve())}
            write(self.folder/'INTERNAL_MEDIA_REVIEW.json',result)
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'outside its production worktree'):
                autonomous.review(self.folder)
            self.assertFalse(path.exists())

    def test_unregistered_production_cannot_choose_any_ledger(self):
        main_only=b'worktree '+str(self.main).encode('utf-8')+b'\0HEAD synthetic\0\0'
        with patch.object(autonomous.subprocess,'check_output',return_value=main_only):
            with self.assertRaisesRegex(ValueError,'registered worktree'):
                autonomous.review(self.folder)
        self.assertFalse(self.expected.exists())

    def test_missing_original_cache_ledger_is_not_recreated_as_an_empty_database(self):
        result=autonomous.review(self.folder)
        (self.expected/'audience.sqlite3').unlink()
        with self.assertRaisesRegex(ValueError,'ledger is missing'):
            autonomous.review(self.folder)
        self.assertFalse((self.expected/'audience.sqlite3').exists())


if __name__=='__main__':unittest.main()
