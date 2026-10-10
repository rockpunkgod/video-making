"""SYNTHETIC TEST ONLY. Lifecycle controls, not audience/teaching results."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests import test_audience_engagement as fixtures
from creative_os.audience_engagement import design_engagement, validate_engagement, EDITORIAL_SIGNALS, FUNCTION_TASKS
from content_os.engagement_learning import (AudienceLearning, initial_rubric, inspect_final_cut,
    learning_template, bind_media_beats, validate_mapping)
from content_os.showcase import file_sha
from video_contracts import sha, validate, seal


class _Clock(datetime):
    current = datetime(2026, 10, 1, tzinfo=timezone.utc)
    @classmethod
    def now(cls, tz=None): return cls.current if tz is None else cls.current.astimezone(tz)


class LearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.AudienceEngagementTests.setUpClass()

    def setUp(self):
        fixture = fixtures.AudienceEngagementTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.episode, self.statuses, self.direction = fixture.episode, fixture.statuses, fixture.direction
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.loop=AudienceLearning(self.root/'local-data'/'audience-learning',synthetic=True)
        _Clock.current=datetime(2026,10,1,tzinfo=timezone.utc)
        self.addCleanup(patch.stopall)
        patch('content_os.engagement_learning.datetime',_Clock).start()
        patch('content_os.engagement_learning.now',lambda:_Clock.current.isoformat()).start()
        self.media_patch=patch('content_os.engagement_learning.inspect_media',return_value={
            'status':'PASS','duration':30,'width':3840,'height':2160,'fps':'24/1','audio_streams':1,'full_decode':True})
        self.probe=self.media_patch.start()
        self.frames_patch=patch('content_os.engagement_learning.encoded_frames',return_value=720)
        self.frames_patch.start()
        self.media=self.root/'synthetic.mp4'; self.media.write_bytes(b'SYNTHETIC TEST ONLY')
        self.copy={'copy':'SYNTHETIC TEST ONLY'}; self.timeline=self.native_timeline(30)
        asset=self.root/'asset.txt';asset.write_text('SYNTHETIC TEST ONLY',encoding='utf-8')
        binding={'path':str(asset),'sha256':file_sha(asset)}
        self.assets={k:[binding] for k in ('subtitles','voice','music_sfx','native_receipts')}
        self.inspection=inspect_final_cut(self.episode,self.statuses,self.copy,self.timeline,self.assets,self.media)
        q=self.episode['questions'][1]
        self.spec={'experiment_id':'synthetic-experiment','episode_id':'synthetic-episode','platform':'bilibili','cut_version':'r1',
            'rubric_version':initial_rubric()['rubric_version'],'author':'synthetic-editor','post_data_seen':False,
            'title_version':'t1','cover_version':'c1','description_version':'d1','hypotheses':[{
                'hypothesis_id':'H1','claim':'减少重复解释可能改善继续观看意愿',
                'affected_question':q['question_id'],'affected_beat':q['narrative_beats'][0]['beat_id'],
                'expected_advantage':'第二题更有新鲜感','possible_failure':'新证据过快无法跟上',
                'evidence_to_collect':['真实观众关于重复与看不懂的反馈']} ]}

    def native_timeline(self,duration):
        return {'sequence':{'id':'synthetic-sequence','end':duration,'pagination':{'truncated':False},
                    'audioTracks':[{'clips':[]}],'videoTracks':[{'clips':[{'nodeId':'synthetic-master',
                        'mediaPath':str(self.media),'start':0,'end':duration}]}]},
            'settings':{'id':'synthetic-sequence','frameSizeHorizontal':3840,'frameSizeVertical':2160,
                'audioSampleRateHz':48000,'videoFrameRate':{'seconds':1/24}},'voices':[]}

    def freeze(self, final=True):
        return self.loop.freeze(self.spec,self.episode,self.statuses,self.copy,self.timeline,
            inspection=self.inspection if final else None)

    def publish(self, ident):
        _Clock.current+=timedelta(seconds=1)
        return self.loop.publish(ident,{'platform_post_id':self.spec['episode_id'],'published_at':_Clock.current.isoformat(),
            'publication_url':'https://example.invalid/SYNTHETIC','registrar':'synthetic-editor','actual_publication':True,
            'media_sha':file_sha(self.media),'title_version':'t1','cover_version':'c1','description_version':'d1'})

    def observation(self, pub):
        record=self.loop.get(pub,'publication');start=datetime.fromisoformat(record['published_at'])
        _Clock.current=start+timedelta(days=3)
        return {'source':'SYNTHETIC TEST ONLY manual','collected_at':_Clock.current.isoformat(),
            'window_start':start.isoformat(),'window_end':_Clock.current.isoformat(),'window_label':'T+3',
            'platform':'bilibili','cut_version':'r1','is_real_observation':False,
            'metrics':{'views':{'value':20,'numerator':20,'denominator':None,'unit':'count'},'saves':None},
            'retention_curve':None,'traffic_source':None}

    def retro(self, obs):
        return self.loop.retrospective(obs,{'H1':{'status':'INCONCLUSIVE','reason':'总播放量无法判断第二题效果',
            'evidence_refs':['metric:views'],'next_director_edit':'下一期只压缩已知解释并继续记录反馈'}})

    def second_retro(self, *, same_sources=False):
        if not same_sources:
            from tests import test_video_os as video_fixtures
            from content_os.candidates import make_candidate
            from content_os.director import build_draft, finalize_copy
            from content_os.polisher import IdentityPolisher, polish
            control=video_fixtures.VideoOSTest();control.setUp()
            control.req['question']['question_id']='synthetic-third-problem'
            control.req['question']['stem']+=' independent third synthetic task'
            control.req['analysis']=control.engine.analyze(control.req['question'])
            control.req['reviews'][0].update(question_id=control.req['question']['question_id'],
                input_sha256=sha(control.req['question']),analysis_sha256=sha(control.req['analysis']))
            bundle,statuses=control.assets()
            candidate=make_candidate([bundle],[{'asset_id':bundle['asset_id'],'method_id':'R12','action_ids':['loc']}],statuses)
            self.episode=deepcopy(self.episode);self.statuses={**self.statuses,**statuses}
            question=self.episode['questions'][1]
            question['question_id']=bundle['source_snapshot']['question_id']
            question['package']=finalize_copy(polish(build_draft(candidate,self.statuses),IdentityPolisher()))
            ref={'asset_id':bundle['asset_id'],'pointer':'/source_snapshot/stem','sha':sha(bundle['source_snapshot']['stem'])}
            for beat in question['narrative_beats']:beat['source_refs']=[deepcopy(ref)]
            action=bundle['analysis']['execution_trace'][0]
            question['payoff']['action_refs']=[{'asset_id':bundle['asset_id'],'pointer':'/analysis/execution_trace/0','sha':sha(action)}]
            question['payoff']['output_shas']=[sha(action['output'])]
            self.spec['hypotheses'][0]['affected_question']=question['question_id']
        self.spec['episode_id']='synthetic-episode-2';self.spec['experiment_id']='synthetic-experiment-2'
        self.media=self.root/'synthetic-second.mp4'
        if self.inspection['media_audit']['duration'] == 30:
            self.media.write_bytes(b'SYNTHETIC TEST ONLY SECOND EPISODE')
        else:
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=white:s=3840x2160:r=24',
                '-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.125','-c:v','libx264','-preset','ultrafast',
                '-threads','2','-pix_fmt','yuv420p','-c:a','aac',str(self.media)],check=True)
        self.timeline=self.native_timeline(self.inspection['media_audit']['duration'])
        self.inspection=inspect_final_cut(self.episode,self.statuses,self.copy,self.timeline,self.assets,self.media)
        pred=self.freeze();pub=self.publish(pred);obs=self.loop.performance(pub,self.observation(pub))
        return self.retro(obs)

    def proposal(self, retros, kind='CREATIVE_PATTERN'):
        rubric=initial_rubric();rubric['rubric_version']='free-engagement-0.2.1'
        rubric['dimensions']['Question Novelty']['definition']+='；独立检查后续题的新信息'
        return {'rule_kind':kind,'rule':'后续题优先展示新的证据困难','source':'synthetic retrospective',
            'applicable_conditions':'已建立共同方法预期的多题影片','proposer':'synthetic-editor',
            'supporting_retros':retros,'opposing_retros':[],'change_log':['细化后续题评价'],
            'new_rubric':rubric if kind=='EVALUATION_RULE' else None}

    def review(self, proposal_id):
        proposal=self.loop.get(proposal_id,'proposal')
        return {'reviewer':'synthetic-independent-human','reviewer_kind':'human','origin':'external_human','status':'pass',
            'reviewed_at':_Clock.current.isoformat(),'evidence_notes':'SYNTHETIC TEST ONLY review',
            'effective_version':proposal['new_rubric']['rubric_version'] if proposal['new_rubric'] else 'pattern-1',
            'overfit_check':'不将描述性吻合当作因果','holdout_plan':'用未来未参与调整的作品验证',
            'replay':{i:{'comparable':True,'old_evaluation':'重复风险','new_evaluation':'关注新困难','reason':'定性复看'}
                for i in proposal['supporting_retros']+proposal['opposing_retros']},'bindings':{'proposal_sha':sha(proposal)}}

    def v2_direction(self):
        d=deepcopy(self.direction);d['schema_version']='0.2.0'
        stages={'original_task':'PROBLEM','observe':'ORIENTATION','first_action':'SEARCH','attention':'RECOGNITION',
                'evidence_alignment':'COMPARISON','judgement':'DISCOVERY','payoff':'PAYOFF','closure':'RECALL'}
        for q,source in zip(d['questions'],self.episode['questions']):
            seen=[]
            for b,s in zip(q['beats'],source['narrative_beats']):
                b['engagement_function']=stages[s['function']]
                b['viewer_state']={k:'编辑任务' for k in ('current_problem','current_attention_object','viewer_expectation',
                    'viewer_task','unresolved_question','next_information_gain')}
                b['viewer_state']['information_already_seen']=list(seen);seen.append(b['beat_id'])
                b['editorial_signals']={k:k in ('reading_space','hook_link_clear') for k in EDITORIAL_SIGNALS}
        return d

    def test_end_to_end_synthetic_prediction_publish_retro_pattern_handoff(self):
        # This lifecycle runs against actual encoded 4K24 bytes, not an inspection stub.
        self.media_patch.stop();self.frames_patch.stop();self.media.unlink();self.timeline=self.native_timeline(.125)
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=3840x2160:r=24',
            '-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.125','-c:v','libx264','-preset','ultrafast',
            '-threads','2','-pix_fmt','yuv420p','-c:a','aac',str(self.media)],check=True)
        self.inspection=inspect_final_cut(self.episode,self.statuses,self.copy,self.timeline,self.assets,self.media)
        source_inputs=[self.episode,self.statuses];before=sha(source_inputs);ident=self.freeze();frozen=deepcopy(self.loop.get(ident))
        pub=self.publish(ident);obs=self.loop.performance(pub,self.observation(pub));retro=self.retro(obs)
        other=self.second_retro();proposal=self.loop.propose_rule(self.proposal([retro,other]))
        self.loop.activate_rule(proposal,self.review(proposal))
        candidates=self.loop.director_candidates();self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]['future_validation'],'PENDING_HOLDOUT')
        self.assertEqual(self.loop.get(ident),frozen);self.assertEqual(sha(source_inputs),before)
        self.assertTrue(all(r['payload']['data_label']=='SYNTHETIC TEST ONLY' for r in self.loop.records()))
        self.assertTrue(all(r['payload']['public_render_ready'] is False for r in self.loop.records()))

    def test_actual_curve_maps_only_observed_samples_and_missing_curve_is_unavailable(self):
        pred=self.freeze();pub=self.publish(pred);obs=self.observation(pub)
        obs['retention_curve']={'source':'SYNTHETIC TEST ONLY','time_basis':'MEDIA_SECONDS','media_sha':file_sha(self.media),
            'points':[{'second':1,'rate':.8,'numerator':8,'denominator':10}]}
        ident=self.loop.performance(pub,obs)
        self.assertEqual(len(self.loop.get(ident)['retention_curve']['points']),1)
        obs['retention_curve']['points'][0]['second']=31
        with self.assertRaisesRegex(ValueError,'beyond'):self.loop.performance(pub,obs)

    def test_frozen_prediction_db_refuses_update_delete_and_changed_version(self):
        ident=self.freeze()
        with self.assertRaisesRegex(ValueError,'immutable'): self.freeze()
        with self.loop.connect() as con:
            with self.assertRaises(sqlite3.IntegrityError): con.execute('UPDATE records SET payload=? WHERE id=?',('{}',ident))
            with self.assertRaises(sqlite3.IntegrityError): con.execute('DELETE FROM records WHERE id=?',(ident,))
        self.spec['cut_version']='r2'; self.media.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Stale'): self.freeze()

    def test_planning_no_media_no_publish_or_inherited_final_score(self):
        pred=self.freeze(final=False)
        self.assertEqual(self.loop.get(pred)['prediction_status'],'PRE_PRODUCTION_HYPOTHESIS')
        with self.assertRaisesRegex(ValueError,'Planning'): self.publish(pred)
        result=inspect_final_cut(self.episode,self.statuses,self.copy,self.timeline,self.assets,self.root/'absent.mp4')
        self.assertEqual(result['status'],'PENDING')
        review={'reviewer':'AI','reviewer_kind':'AI','review_version':'1','reviewed_at':_Clock.current.isoformat(),
            'stage':'FINAL_CUT','watched_final':False,'human_credential':None,'dimensions':{k:{'grade':5,'evidence':'SYNTHETIC',
                'recommended_edit':'待真实影片','timecode':'00:00','timecode_basis':'PLANNED'} for k in initial_rubric()['dimensions']}}
        score=self.loop.get(self.loop.score(pred,review,inspection=result),'score')
        self.assertEqual(score['status'],'PENDING');self.assertEqual(score['human_taste'],'PENDING')
        self.assertTrue(all(r['grade']=='PENDING' for r in score['review']['dimensions'].values()))

    def test_blind_closed_after_any_platform_publication_or_known_data(self):
        ident=self.freeze();self.publish(ident);self.spec['cut_version']='r2';self.spec['platform']='douyin'
        with self.assertRaisesRegex(ValueError,'already published'):self.freeze()
        self.spec['episode_id']='other';self.spec['post_data_seen']=True
        with self.assertRaisesRegex(ValueError,'Known'):self.freeze()
        self.spec['post_data_seen']=False;self.spec['million_views_probability']=.8
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.freeze()

    def test_csv_missing_is_unknown_and_retention_unavailable(self):
        pred=self.freeze();pub=self.publish(pred);meta=self.observation(pub);meta.pop('metrics')
        csvfile=self.root/'metrics.csv';csvfile.write_text('metric,value,numerator,denominator,unit\nviews,20,20,,count\nsaves,,,,count\n',encoding='utf-8')
        obsid=self.loop.import_csv(pub,csvfile,meta);obs=self.loop.get(obsid)
        self.assertIsNone(obs['metrics']['saves']);self.assertIn('saves',obs['missing_fields'])
        self.assertEqual(self.loop.get(self.retro(obsid))['beat_analysis'],'UNAVAILABLE')
        self.assertEqual(learning_template('q')['retention'],'UNKNOWN')

    def test_csv_file_hash_cannot_replace_missing_source(self):
        pred=self.freeze();pub=self.publish(pred);meta=self.observation(pub);meta.pop('metrics')
        csvfile=self.root/'no-source.csv'
        csvfile.write_text('metric,value,numerator,denominator,unit\nviews,20,20,,count\n',encoding='utf-8')
        for source in ('','   ',None):
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'source'):
                self.loop.import_csv(pub,csvfile,{**meta,'source':source})

    def test_retrospective_cannot_override_frozen_hypothesis_or_identity(self):
        pred=self.freeze();original=deepcopy(self.loop.get(pred));pub=self.publish(pred)
        obs=self.loop.performance(pub,self.observation(pub))
        judgement={'status':'INCONCLUSIVE','reason':'总播放量不能验证具体片段',
            'evidence_refs':['metric:views'],'next_director_edit':'继续收集实际观看反馈'}
        for key,value in (('frozen_hypothesis',{'claim':'改写原始判断'}),('hypothesis_id','H-other')):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'field'):
                self.loop.retrospective(obs,{'H1':{**judgement,key:value}})
        self.assertEqual(self.loop.get(pred),original)
        self.assertEqual(self.loop.get(self.retro(obs))['rows'][0]['frozen_hypothesis'],original['hypotheses'][0])

    def test_renamed_recut_episode_is_not_cross_episode_evidence(self):
        pred=self.freeze();pub=self.publish(pred);obs=self.loop.performance(pub,self.observation(pub));retro=self.retro(obs)
        # Change packaging and export bytes, while retaining the same source problems.
        self.episode['viewer_question']='Same problems, new opening'
        self.episode['method_recall']='Same problems, new ending'
        other=self.second_retro(same_sources=True)
        proposal=self.loop.propose_rule(self.proposal([retro,other]))
        self.assertEqual(self.loop.get(proposal)['state'],'SINGLE_EPISODE_OBSERVATION')
        with self.assertRaisesRegex(ValueError,'Single'):
            self.loop.activate_rule(proposal,self.review(proposal))
        self.assertEqual(self.loop.director_candidates(),[])

    def test_performance_rejects_sources_times_platform_version_window_ratios(self):
        pred=self.freeze();pub=self.publish(pred);original=self.observation(pub)
        for key,value in [('source',''),('collected_at','2026-10-02'),('platform','douyin'),('cut_version','r2'),
                          ('window_label','T+7'),('is_real_observation',True)]:
            obs=deepcopy(original);obs[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.loop.performance(pub,obs)
        obs=deepcopy(original);obs['metrics']['completion_rate']={'value':.5,'numerator':9,'denominator':10,'unit':'ratio'}
        with self.assertRaisesRegex(ValueError,'ratio'):self.loop.performance(pub,obs)
        obs=deepcopy(original);obs['metrics']['views']['value']=float('nan')
        with self.assertRaises(ValueError):self.loop.performance(pub,obs)

    def test_single_episode_cannot_activate_and_ai_cannot_sign(self):
        ident=self.freeze();pub=self.publish(ident);obs=self.loop.performance(pub,self.observation(pub));retro=self.retro(obs)
        proposal=self.loop.propose_rule(self.proposal([retro]));review=self.review(proposal)
        with self.assertRaisesRegex(ValueError,'Single'):self.loop.activate_rule(proposal,review)
        review['reviewer_kind']='AI'
        with self.assertRaisesRegex(ValueError,'Independent'):self.loop.activate_rule(proposal,review)
        self.assertEqual(self.loop.director_candidates(),[])

    def test_rubric_history_and_scores_not_rewritten(self):
        pred=self.freeze();original=self.loop.get(pred);pub=self.publish(pred)
        obs=self.loop.performance(pub,self.observation(pub));retro=self.retro(obs);other=self.second_retro()
        proposal=self.loop.propose_rule(self.proposal([retro,other],'EVALUATION_RULE'))
        self.loop.activate_rule(proposal,self.review(proposal))
        self.assertEqual(self.loop.get(pred),original)
        self.spec['episode_id']='third';self.spec['experiment_id']='third'
        with self.assertRaisesRegex(ValueError,'currently effective'):self.freeze()
        self.spec['rubric_version']='free-engagement-0.2.1';self.media=self.root/'third.mp4';self.media.write_bytes(b'SYNTHETIC THIRD')
        self.timeline=self.native_timeline(30)
        self.inspection=inspect_final_cut(self.episode,self.statuses,self.copy,self.timeline,self.assets,self.media);self.freeze()

    def test_feedback_separates_comments_teaching_candidates_and_human_taste(self):
        pred=self.freeze();h=self.spec['hypotheses'][0]
        item={'feedbacker':'synthetic-viewer','text':'第二题哪里需要再看一次？','experience_issue':'未跟上',
            'question_id':h['affected_question'],'beat_id':h['affected_beat'],'media_sha':file_sha(self.media),
            'channel':'EDITORIAL_SCREENING','watched_final':True,'confirmed_summary':False,'rechecked':False,'teaching_issue':True}
        record=self.loop.get(self.loop.feedback(pred,item));self.assertEqual(record['result_kind'],'teaching_issue_candidate')
        self.assertEqual(record['human_taste'],'PENDING')
        item['channel']='PLATFORM_COMMENT'
        with self.assertRaisesRegex(ValueError,'requires actual'):self.loop.feedback(pred,item)
        item['channel']='EDITORIAL_SCREENING';item['watched_final']=False
        with self.assertRaises(ValueError):self.loop.feedback(pred,item)

    def test_v2_viewer_states_structural_suggestions_and_v01_compatibility(self):
        original=sha([self.episode,self.statuses]);d=self.v2_direction()
        d['questions'][1]['novelty']='none';d['questions'][1]['beats'][2]['editorial_signals']['repeated_explanation']=True
        plan=design_engagement(self.episode,self.statuses,d);validate('audience-engagement-plan',plan)
        self.assertTrue(any(i['issue']['type']=='REPEATED_EXPLANATION' and i['recommended_edit'] for i in plan['quality_audit']['issues']))
        self.assertEqual(plan['human_review'],'PENDING');self.assertEqual(sha([self.episode,self.statuses]),original)
        self.assertEqual(design_engagement(self.episode,self.statuses,self.direction)['schema_version'],'0.1.0')
        d['questions'][0]['beats'][0]['viewer_state']['information_already_seen']=['future']
        with self.assertRaisesRegex(ValueError,'earlier'):design_engagement(self.episode,self.statuses,d)

    def test_old_engagement_fails_on_episode_stop_or_order_change(self):
        plan=design_engagement(self.episode,self.statuses,self.direction)
        for edit in ('recall','order','stop','role'):
            changed=deepcopy(self.episode)
            if edit=='recall': changed['method_recall']='changed'
            if edit=='order':changed['questions'].reverse()
            if edit=='stop': changed['questions'][0]['narrative_beats'][-1]['viewer_sees']='changed stop display'
            if edit=='role': changed['questions'][0]['editorial_role']='variation'
            with self.subTest(edit=edit),self.assertRaises(ValueError):validate_engagement(plan,changed,self.statuses,self.direction)

    def test_schema_initial_rubric_and_ledger_path_scope(self):
        validate('audience-rubric',initial_rubric())
        pred=self.freeze();validate('audience-experiment',self.loop.get(pred))
        pub=self.publish(pred);obs=self.loop.performance(pub,self.observation(pub));validate('audience-performance',self.loop.get(obs))
        with self.assertRaises(ValueError):AudienceLearning(self.root/'answer_engine')

    def test_native_mapping_rejects_estimates_stale_media_and_modified_ranges(self):
        patch('content_os.engagement_learning.subprocess.check_output',return_value=json.dumps(
            {'streams':[{'r_frame_rate':'24/1','nb_read_frames':'720'}]})).start()
        d=self.v2_direction();plan=design_engagement(self.episode,self.statuses,d)
        sequence={'id':'sequence','end':30,'pagination':{'truncated':False},'audioTracks':[{'clips':[]}],
            'videoTracks':[{'clips':[{'nodeId':'master','mediaPath':str(self.media),'start':0,'end':30}]}]}
        settings={'id':'sequence','frameSizeHorizontal':3840,'frameSizeVertical':2160,
            'audioSampleRateHz':48000,'videoFrameRate':{'seconds':1/24}}
        ranges=[{'question_id':q['question_id'],'beat_id':b['beat_id'],'start_frame':i*24,
            'end_frame':(i+1)*24,'native_clip_id':'master'} for i,(q,b) in enumerate((q,b) for q in plan['questions'] for b in q['beats'])]
        bindings={'episode_sha':sha(self.episode),'engagement_plan_sha':sha(plan),'native_timeline_sha':sha(sequence),
            'settings_sha':sha(settings),'media_sha':file_sha(self.media),'ranges_sha':sha(ranges)}
        credential={'reviewer':'synthetic-human','review_id':'test','reviewed_at':_Clock.current.isoformat(),
            'evidence_notes':'SYNTHETIC actual anchors','reviewer_kind':'human','origin':'external_human','status':'pass',
            'watched_final':True,'bindings':bindings}
        mapping=bind_media_beats(plan,self.episode,self.statuses,d,self.media,sequence,settings,[],ranges,credential)
        self.assertTrue(validate_mapping(mapping,plan,self.episode,sequence,settings,self.media))
        changed=deepcopy(sequence);changed['end']=31
        with self.assertRaisesRegex(ValueError,'Stale'):validate_mapping(mapping,plan,self.episode,changed,settings,self.media)
        tampered=deepcopy(mapping);tampered['ranges'][0]['actual_media']['end_frame']=99
        with self.assertRaises(ValueError):validate_mapping(tampered,plan,self.episode,sequence,settings,self.media)
        # Recomputing a JSON seal cannot rebind the human-reviewed frame anchors.
        tampered=seal(tampered)
        with self.assertRaisesRegex(ValueError,'anchor'):
            validate_mapping(tampered,plan,self.episode,sequence,settings,self.media)
        anchors=deepcopy(mapping);anchors['frame_anchors'][0]['end_frame']=99
        with self.assertRaisesRegex(ValueError,'anchor'):
            validate_mapping(seal(anchors),plan,self.episode,sequence,settings,self.media)
        pred=self.freeze();pub=self.publish(pred);observation=self.observation(pub)
        observation['retention_curve']={'source':'SYNTHETIC TEST ONLY','time_basis':'MEDIA_SECONDS',
            'media_sha':file_sha(self.media),'points':[
                {'second':.5,'rate':.8,'numerator':8,'denominator':10},
                {'second':1.5,'rate':.7,'numerator':7,'denominator':10}]}
        observed=self.loop.performance(pub,observation)
        result=self.loop.get(self.loop.beat_retrospective(observed,mapping,plan,self.episode,
            self.statuses,d,sequence,settings,self.media))
        self.assertEqual([p['second'] for p in result['rows'][0]['observed_samples']],[.5])
        self.assertEqual([p['second'] for p in result['rows'][1]['observed_samples']],[1.5])
        self.assertEqual(result['rows'][2]['status'],'UNAVAILABLE')
        self.assertTrue(all(r['causal_attribution']=='NOT_ESTABLISHED' for r in result['rows']))
        credential['watched_final']=False
        with self.assertRaisesRegex(ValueError,'human'):bind_media_beats(plan,self.episode,self.statuses,d,self.media,sequence,settings,[],ranges,credential)

    def test_rejected_independent_review_is_retained_without_activating(self):
        pred=self.freeze();pub=self.publish(pred);obs=self.loop.performance(pub,self.observation(pub));retro=self.retro(obs)
        proposal=self.loop.propose_rule(self.proposal([retro]));review=self.review(proposal);review['status']='reject'
        ident=self.loop.record_rule_review(proposal,review)
        self.assertEqual(self.loop.get(ident)['review']['status'],'reject')
        self.assertEqual(self.loop.director_candidates(),[])

    def test_director_handoff_preserves_native_direction_and_rejects_other_episode(self):
        from creative_os.audience_engagement import director_handoff
        d=self.v2_direction();plan=design_engagement(self.episode,self.statuses,d)
        scenes=[];assignments={}
        for q in self.episode['questions']:
            assignments[q['question_id']]={}
            for b in q['narrative_beats']:
                ident=q['question_id']+':'+b['beat_id']
                scenes.append({'scene_id':ident,'question_id':q['question_id'],'source_refs':b['source_refs'],'time_range':[0,1]})
                assignments[q['question_id']][b['beat_id']]=[ident]
        native={'episode_plan_sha':sha(self.episode),'content_profile':'FREE_SHOWCASE','scenes':scenes}
        before=sha(native);handoff=director_handoff(plan,self.episode,self.statuses,d,native,assignments)
        self.assertEqual(sha(native),before);self.assertEqual(handoff['actual_media_mapping'],'UNAVAILABLE')
        native['scenes'][0]['question_id']='other'
        with self.assertRaisesRegex(ValueError,'Cross-question'):director_handoff(plan,self.episode,self.statuses,d,native,assignments)


class ActualMediaTests(unittest.TestCase):
    def test_existing_showcase_inspector_decodes_real_4k24_audio_and_rejects_picture_only(self):
        from content_os.showcase import inspect_media
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'synthetic.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=3840x2160:r=24',
                '-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.125','-c:v','libx264','-preset','ultrafast',
                '-threads','2','-pix_fmt','yuv420p','-c:a','aac',
                '-metadata','title=英语有画说',str(target)],check=True)
            self.assertTrue(inspect_media(target)['full_decode'])
            picture=Path(folder)/'picture.mp4'
            subprocess.run(['ffmpeg','-v','error','-i',str(target),'-an','-c:v','copy',str(picture)],check=True)
            with self.assertRaisesRegex(ValueError,'audio'):inspect_media(picture)


if __name__=='__main__':unittest.main()
