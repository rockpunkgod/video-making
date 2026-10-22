"""Synthetic orchestration controls; no actual media or teaching certification."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from video_contracts import read,write,sha
from scripts.voice_delivery import sha256
from ae_production.autonomous_episode import (job,consume_author_response,run,revise,complete_chunks,request_author)
from content_os.engagement_learning import AudienceLearning


class AutonomousControls(unittest.TestCase):
    def test_new_author_receives_bound_policy_and_changed_policy_invalidates_old_job(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);policy=f/'FREE_SHOWCASE_POLICY.md'
            policy.write_text('SYNTHETIC policy version one',encoding='utf-8')
            hook=f/'hook.json';write(hook,{'synthetic':True})
            brief=f/'brief.json';write(brief,{'schema':'autonomous-episode-brief/v1',
                'product':'FREE_SHOWCASE','asset_pool':[],'style_inputs':[],
                'audience_hook_decision':{'path':str(hook),'sha256':sha256(hook)}})
            with patch('ae_production.autonomous_episode.ROOT',f):
                first=request_author(f,brief)
                packet=read(first['request'])['packet']
                self.assertEqual(packet['input_files'][str(policy)],sha256(policy))
                self.assertIn('creative_compression_v2',' '.join(packet['requirements']))
                write(first['response'],{'request_sha':first['request_sha'],'human_approved':False})
                policy.write_text('SYNTHETIC policy version two',encoding='utf-8')
                second=request_author(f,brief)
            self.assertNotEqual(first['request_sha'],second['request_sha'])
            self.assertEqual(second['status'],'NEEDS_HOST_AGENT')
            self.assertFalse((f/'AV_AUTHOR.json').exists())

    def test_missing_host_agent_is_not_user_approval_or_fake_authorship(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)
            with patch('subprocess.run',side_effect=AssertionError('no configured command')):
                r=job(f,'language_author',{'source':'SYNTHETIC SOURCE'})
            self.assertEqual(r['status'],'NEEDS_HOST_AGENT')
            self.assertFalse(r['user_approval_required'])
            self.assertFalse((f/'AV_AUTHOR.json').exists())
            write(r['response'],{'request_sha':'stale','human_approved':False})
            with self.assertRaises(ValueError):job(f,'language_author',{'source':'SYNTHETIC SOURCE'})

    def test_bound_agent_reply_preserves_internal_authority(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);r=job(f,'creative_author',{'source':'SYNTHETIC SOURCE'})
            reply={'request_sha':r['request_sha'],'human_approved':False,'decision':'SYNTHETIC DECISION'}
            write(r['response'],reply)
            self.assertEqual(job(f,'creative_author',{'source':'SYNTHETIC SOURCE'}),reply)
            reply['human_approved']=True;write(r['response'],reply)
            with self.assertRaises(ValueError):job(f,'creative_author',{'source':'SYNTHETIC SOURCE'})

    def test_changed_response_cannot_damage_existing_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);original={'source':'SYNTHETIC ORIGINAL'}
            write(f/'EDITORIAL_MANIFEST.json',original)
            a={'copy_review':'PENDING','public_render_ready':False,'editorial':{'sha256':sha256(f/'EDITORIAL_MANIFEST.json')}}
            write(f/'AV_AUTHOR.json',a);before=sha256(f/'EDITORIAL_MANIFEST.json')
            response={'author':deepcopy(a),'editorial_manifest':{'source':'SYNTHETIC REPLACEMENT'}}
            with self.assertRaises(ValueError):consume_author_response(f,response)
            self.assertEqual(sha256(f/'EDITORIAL_MANIFEST.json'),before)
            self.assertEqual(read(f/'AV_AUTHOR.json'),a)

    def test_cached_build_without_native_outputs_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);write(f/'AV_AUTHOR.json',{'synthetic':True})
            write(f/'AUTONOMOUS_RUN.json',{'stages':{'build':{'author_sha256':sha256(f/'AV_AUTHOR.json'),'result':{'comp_id':1}}}})
            with patch('ae_production.autonomous_episode.STAGES',('build',)),patch('ae_production.authored_native.checked_author',return_value=({},{})),patch('ae_production.autonomous_episode.dispatch',side_effect=AssertionError('never replay')):
                with self.assertRaises(FileNotFoundError):run(f,through='build')

    def test_missing_chunks_resume_the_same_language_job(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);write(f/'AV_AUTHOR.json',{'synthetic':True})
            missing={'status':'NEEDS_LINGUISTIC_AUTHOR','source_packet':'SYNTHETIC PACKET'}
            with patch('ae_production.autonomous_episode.dispatch',return_value=missing),patch('ae_production.autonomous_episode.checked_author',return_value=({'sources':{'w':'SYNTHETIC'}},{})):
                pending=complete_chunks(f)
            self.assertEqual(pending['role'],'language_author')
            write(pending['response'],{'request_sha':pending['request_sha'],'human_approved':False,'article_chunks':{'synthetic':True}})
            with patch('ae_production.autonomous_episode.dispatch',side_effect=[missing,{'status':'COMPILED'}]),patch('ae_production.autonomous_episode.checked_author',return_value=({'sources':{'w':'SYNTHETIC'}},{})):
                self.assertEqual(complete_chunks(f)['status'],'COMPILED')
            self.assertEqual(read(f/'ARTICLE_CHUNKS.json'),{'synthetic':True})

    def test_no_observed_issue_does_not_create_an_unnecessary_revision(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'parent';f.mkdir();new=Path(t)/'child'
            write(f/'INTERNAL_MEDIA_REVIEW.json',{'media_sha256':'SYNTHETIC','issues':[]})
            write(f/'AUTONOMOUS_RUN.json',{'revisions':0})
            d=Path(t)/'decision.json';write(d,{'media_sha256':'SYNTHETIC','issue_ids':[]})
            with self.assertRaises(ValueError):revise(f,new,d)
            self.assertFalse(new.exists())

    def test_directed_revision_reply_reaches_the_author_consumer(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'parent';f.mkdir();new=Path(t)/'child'
            issue={'issue_id':'SYNTHETIC-ONE','responsible_module':'layout'}
            write(f/'INTERNAL_MEDIA_REVIEW.json',{'media_sha256':'SYNTHETIC','issues':[issue]})
            write(f/'AUTONOMOUS_RUN.json',{'revisions':0})
            d=Path(t)/'decision.json';write(d,{'media_sha256':'SYNTHETIC','issue_ids':['SYNTHETIC-ONE']})
            response={'request_sha':'SYNTHETIC','human_approved':False,'author':{'synthetic':True}}
            with patch('ae_production.autonomous_episode.job',return_value=response) as call,patch('ae_production.autonomous_episode.consume_author_response',return_value={'status':'AUTHORED'}) as consume:
                self.assertEqual(revise(f,new,d),{'status':'AUTHORED'})
                self.assertEqual(call.call_args.args[1],'directed_revision')
                consume.assert_called_once_with(new,response)
            self.assertEqual(read(new/'AUTONOMOUS_RUN.json')['revisions'],1)

    def test_explicit_internal_repair_budget_preserves_default_and_observed_issue_binding(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'parent';f.mkdir();new=Path(t)/'child'
            issue={'issue_id':'SYNTHETIC-ONE','responsible_module':'layout'}
            write(f/'INTERNAL_MEDIA_REVIEW.json',{'media_sha256':'SYNTHETIC','issues':[issue]})
            write(f/'AUTONOMOUS_RUN.json',{'revisions':3})
            d=Path(t)/'decision.json'
            request={'media_sha256':'SYNTHETIC','issue_ids':['SYNTHETIC-ONE']}
            write(d,request)
            with self.assertRaisesRegex(ValueError,'budget exhausted'):revise(f,new,d)
            self.assertFalse(new.exists())
            for limit in (True,0,-1,'4'):
                write(d,{**request,'max_directed_revisions':limit})
                with self.subTest(limit=limit),self.assertRaises(ValueError):revise(f,new,d)
            response={'status':'NEEDS_HOST_AGENT'}
            write(d,{**request,'max_directed_revisions':4,'issue_ids':['NOT_OBSERVED']})
            with self.assertRaisesRegex(ValueError,'No observed issue'):revise(f,new,d)
            self.assertFalse(new.exists())
            write(d,{**request,'max_directed_revisions':4})
            with patch('ae_production.autonomous_episode.job',return_value=response):
                self.assertEqual(revise(f,new,d),response)
            state=read(new/'AUTONOMOUS_RUN.json')
            self.assertEqual(state['revisions'],4)
            self.assertFalse(state['public_render_ready']);self.assertEqual(state['user_acceptance'],'PENDING')


class InternalMediaLedger(unittest.TestCase):
    def fixtures(self,root):
        media=root/'SYNTHETIC.bin';media.write_bytes(b'SYNTHETIC ENGINEERING CONTROL, NOT PLAYABLE MEDIA')
        plan={'revision':'synthetic','frames':24,'scenes':[{'id':'s1','start':0,'end':1}]}
        path=root/'AV_PLAN.json';write(path,plan)
        qa={'media':str(media),'sha256':sha256(media),'same_revision':'synthetic','frames':24,'plan_sha256':sha256(path)}
        issue={'issue_id':'synthetic-observation','media_sha256':qa['sha256'],'scene':'s1','range':[0,.5],
               'observed_fact':'SYNTHETIC structural test only','severity':'minor','responsible_module':'layout',
               'revision':'SYNTHETIC suggested change','recheck':'PENDING','observation_kind':'engineering_measurement'}
        return media,plan,path,qa,issue

    def test_internal_channel_does_not_create_a_human_or_platform_review(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);media,p,path,qa,issue=self.fixtures(root)
            ledger=AudienceLearning(root/'local-data/audience-learning',synthetic=True)
            ident=ledger.internal_ai_review(media,p,issue,qa=qa,plan_path=path)
            row=ledger.get(ident,'internal_ai_review')
            self.assertEqual(row['channel'],'internal_ai_review')
            self.assertFalse(row['human_confirmed']);self.assertFalse(row['platform_observation'])
            self.assertFalse(row['public_render_ready']);self.assertEqual(row['plan_sha256'],qa['plan_sha256'])
            self.assertFalse(any(r['kind'] in ('publication','performance','feedback') for r in ledger.records()))

    def test_stale_media_plan_and_outside_scene_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);media,p,path,qa,issue=self.fixtures(root)
            ledger=AudienceLearning(root/'local-data/audience-learning',synthetic=True)
            for mutate in (lambda q,i:q.update(same_revision='old'),lambda q,i:i.update(media_sha256='old'),lambda q,i:i.update(range=[0,2])):
                q=deepcopy(qa);i=deepcopy(issue);mutate(q,i)
                with self.assertRaises(ValueError):ledger.internal_ai_review(media,p,i,qa=q,plan_path=path)
            self.assertEqual(ledger.records(),[])

    def test_bounded_encoded_observation_cannot_become_a_whole_film_review(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);media,p,path,qa,issue=self.fixtures(root)
            ledger=AudienceLearning(root/'local-data/audience-learning',synthetic=True)
            qa.update(frames=12,source_frame_range=[0,12],source_fps=24)
            ident=ledger.internal_ai_review(media,p,issue,qa=qa,plan_path=path)
            self.assertFalse(ledger.get(ident)['whole_film_media'])
            issue['range']=[.5,.75]
            with self.assertRaisesRegex(ValueError,'bounded media'):
                ledger.internal_ai_review(media,p,issue,qa=qa,plan_path=path)
            qa['frames']=24
            with self.assertRaisesRegex(ValueError,'frame scope'):
                ledger.internal_ai_review(media,p,issue,qa=qa,plan_path=path)


class IndexedProductionWorktree(unittest.TestCase):
    def test_external_private_path_requires_both_exact_index_and_registered_worktree(self):
        from ae_production.authored_episode import production_folder_allowed
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';root.mkdir();other=Path(t)/'integration';other.mkdir()
            current=root/'index.json';destination=other/'local-data/episode'
            write(current,{'revision':str(destination)})
            listing=b'worktree '+str(other).encode('utf-8')+b'\0HEAD synthetic\0\0'
            with patch('ae_production.authored_episode.ROOT',root),patch('ae_production.authored_episode.CURRENT',current),patch('ae_production.authored_episode.subprocess.check_output',return_value=listing):
                self.assertTrue(production_folder_allowed(destination))
                self.assertFalse(production_folder_allowed(other/'local-data/arbitrary'))
                write(current,{'revision':str(other/'tracked/episode')})
                self.assertFalse(production_folder_allowed(other/'tracked/episode'))
                write(current,{'revision':str(destination)})
                with patch('ae_production.authored_episode.subprocess.check_output',return_value=b''):
                    self.assertFalse(production_folder_allowed(destination))


if __name__=='__main__':unittest.main()
