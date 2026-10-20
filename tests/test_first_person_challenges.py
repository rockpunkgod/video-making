"""Literal-source and existing-clock controls, not native/readability approval."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from creative_os.audience_engagement import (CHALLENGE_PAUSE_TEXT,
    compile_authored_challenges, validate_authored_challenges, validate_compiled_challenges)
from scripts.voice_delivery import sha256
from video_contracts import sha, write


class FirstPersonChallenges(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name);self.folder=base/'production';self.folder.mkdir()
        self.request=base/'user.txt';self.request.write_text(
            '真实用户节选：每题开头完整原文、题干和四个选项。'+CHALLENGE_PAUSE_TEXT,encoding='utf-8')
        self.a={'format':{'fps':24},'sources':{},'scenes':[],'voices':[],
                'input_files':{str(self.request):sha256(self.request)}}
        self.b={};self.worlds={};self.clock={'scenes':[],'segments':[],'candidate_events':[]}
        for wi,world in enumerate(('first','second')):
            snapshot={'question_id':world+'-Q1','passage':'First line.\nSecond line.',
                      'stem':'What can they do?','options':{c:c+' original option.' for c in 'ABCD'}}
            bundle={'source_snapshot':snapshot,'analysis':{'fixture':'synthetic'}}
            path=base/(world+'.json');status=base/(world+'-status.json')
            write(path,bundle);write(status,{'fixture':'synthetic'})
            self.b[world]=bundle;self.a['sources'][world]={'bundle':str(path),'status':str(status)}
            bounds=[0,11,12,len(snapshot['passage'])]
            blocks=[{'id':world+'-source-'+str(lo),'start':lo,'end':hi,
                     'text':snapshot['passage'][lo:hi],
                     'visible':bool(snapshot['passage'][lo:hi].strip())}
                    for lo,hi in zip(bounds,bounds[1:])]
            self.worlds[world]={'question':deepcopy(snapshot),'blocks':blocks,
                                'source':deepcopy(self.a['sources'][world])}
            for k,kind in enumerate(('task','compare','answer')):
                sid=('SC01' if wi==0 else 'SC09') if k==0 else world+str(k)
                scene={'id':sid,'kind':kind,'world':world,'voice_ids':[sid],
                       'voice_pre':.35,'source_refs':[],'action_refs':[],'terminal_refs':[],
                       'attention':[],'reading_path':[]}
                if k:
                    scene.update(candidate='A',event='supported' if k==1 else 'final',
                                 terminal_refs=[{'candidate':'A','effect':'retain'}])
                self.append(scene,2+(wi*3+k)*8)
        self.append({'id':'recall','kind':'recap','world':'second','voice_ids':['recall'],
                     'voice_pre':.35,'source_refs':[],'action_refs':[],'terminal_refs':[]},50)
        lookup={s['id']:s for s in self.a['scenes']}
        hook={'scene_id':'hook','payoff_scene_id':'second1',
              'retention':{'first_payoff_scene_id':'first1','first_payoff_sha':sha(lookup['first1']),
                           'progression_scene_id':'SC09','progression_scene_sha':sha(lookup['SC09']),
                           'final_recall_scene_id':'recall','final_recall_scene_sha':sha(lookup['recall'])}}
        # This component fixture is not a synthetic grant of full Hook approval.
        self.a['audience_hook']=hook
        self.clock['audience_hook']={'scene_id':'hook','start':0,'end':2,
                                    'decision_sha':sha(hook),'decision':deepcopy(hook)}
        self.a['audience_challenges']={'contract_version':'FIRST_PERSON_CHALLENGE_V1','frames':72,
            'presentation':'full_source_question_split',
            'request_source':{'path':str(self.request),'sha256':sha256(self.request)},
            'pause_badge':{'text':CHALLENGE_PAUSE_TEXT,'screen_only':True},
            'questions':[{'world':'first','scene_id':'SC01'},{'world':'second','scene_id':'SC09'}]}

    def append(self,scene,start):
        self.a['scenes'].append(scene);text='Existing complete narration '+scene['id']+'.'
        self.a['voices'].append({'id':scene['id'],'text':text})
        live={**deepcopy(scene),'start':start,'end':start+8,'reading_events':[],
              'attention_events':[],'voice_start':start+.375,'voice_end':start+4.375}
        self.clock['scenes'].append(live)
        self.clock['segments'].append({'id':scene['id'],'scene_id':scene['id'],'text':text,
            'voice_start':start+.375,'voice_end':start+4.375,'truncated':False,'time_stretch':False,
            'voice':{'sha256':'synthetic-complete-take-'+scene['id']}})
        if scene.get('event'):
            live['event_time']=start+5
            self.clock['candidate_events'].append({'scene':scene['id'],'world':scene['world'],
                'kind':scene['event'],'candidate':scene['candidate'],'time':start+5,
                'refs':deepcopy(scene['terminal_refs'])})

    def compile(self):
        return compile_authored_challenges(self.a,self.b,self.clock,self.worlds,self.folder)

    def validate(self):return validate_authored_challenges(self.a,self.b,self.folder)

    def test_historical_missing_field_is_inert_without_new_clock_or_sources(self):
        a={};self.assertIsNone(validate_authored_challenges(a,{}))
        self.assertIsNone(compile_authored_challenges(a,{},{}))
        self.assertIsNone(validate_compiled_challenges(None,a,{},{}))

    def test_full_source_question_options_and_exactly_72_existing_frames(self):
        result=self.compile();self.assertEqual(len(result['rows']),2)
        for row,start in zip(result['rows'],(2,26)):
            snapshot=self.b[row['world']]['source_snapshot']
            self.assertEqual(row['start'],start);self.assertEqual(row['end'],start+3)
            self.assertEqual(row['end_frame']-row['start_frame'],72)
            self.assertEqual(''.join(b['text'] for b in row['blocks']),snapshot['passage'])
            self.assertEqual(row['stem'],snapshot['stem']);self.assertEqual(row['options'],snapshot['options'])
            self.assertEqual([r['pointer'] for r in row['source_refs']],
                ['/passage','/stem','/options/A','/options/B','/options/C','/options/D'])
            self.assertEqual(row['source_snapshot_sha'],sha(snapshot))
            self.assertEqual(row['pause_badge'],{'text':CHALLENGE_PAUSE_TEXT,'screen_only':True})

    def test_compilation_preserves_clock_complete_audio_and_all_original_inputs(self):
        before=deepcopy((self.a,self.b,self.clock,self.worlds));result=self.compile()
        self.assertEqual(before,(self.a,self.b,self.clock,self.worlds))
        self.assertEqual(self.clock['segments'][0]['voice_start'],2.375)
        self.assertEqual(result['timing_basis'],'EXISTING_SCENE_CLOCK_NO_INSERTED_TIME')
        self.assertEqual(result['actual_native_consumption'],'UNVERIFIED')
        self.assertEqual(result['normal_speed_review'],'UNOBSERVED')
        self.assertEqual(result['human_review'],'PENDING');self.assertIs(result['public_render_ready'],False)

    def test_payoff_progression_and_hook_use_existing_real_pointers(self):
        chain=self.compile()['audience_chain']
        self.assertEqual(chain['hook']['scene'],'hook')
        self.assertEqual(chain['first_payoff']['scene'],'first1')
        self.assertEqual(chain['hook_payoff']['scene'],'second1')
        self.assertEqual(chain['progression']['scene'],'SC09')
        self.assertEqual([q['final']['scene'] for q in chain['question_payoffs']],['first2','second2'])
        self.assertEqual(chain['final_recall']['scene'],'recall')

    def test_challenge_rows_contain_no_answer_selected_evidence_or_method_labels(self):
        for row in self.compile()['rows']:
            spoiler=row['spoiler_boundary']
            self.assertEqual(spoiler['highlighted_ranges'],[]);self.assertEqual(spoiler['method_labels'],[])
            self.assertEqual(spoiler['candidate_states'],dict.fromkeys('ABCD','unchecked'))
            self.assertIsNone(spoiler['verdict']);self.assertNotIn('answer',row)
            self.assertNotIn('payoff',row);self.assertNotIn('candidate',row)

    def test_only_explicit_presentation_frames_and_closed_decision_are_allowed(self):
        for field,value in [('frames',71),('frames',True),('presentation','highlight_selected_passage'),
                            ('contract_version','future'),('human_approved',True)]:
            with self.subTest(field=field):
                saved=deepcopy(self.a['audience_challenges']);self.a['audience_challenges'][field]=value
                with self.assertRaises(ValueError):self.validate()
                self.a['audience_challenges']=saved

    def test_changed_badge_and_spoken_badge_are_rejected(self):
        for badge in [{'text':'你可以暂停，自己先做一遍','screen_only':True},
                      {'text':CHALLENGE_PAUSE_TEXT,'screen_only':False},
                      {'text':CHALLENGE_PAUSE_TEXT,'screen_only':1}]:
            with self.subTest(badge=badge):
                self.a['audience_challenges']['pause_badge']=badge
                with self.assertRaises(ValueError):self.validate()
        self.a['audience_challenges']['pause_badge']={'text':CHALLENGE_PAUSE_TEXT,'screen_only':True}
        self.a['voices'][0]['text']+=CHALLENGE_PAUSE_TEXT
        with self.assertRaises(ValueError):self.validate()

    def test_request_needs_dual_byte_binding_and_exact_actual_user_excerpt(self):
        self.a['input_files'].clear()
        with self.assertRaises(ValueError):self.validate()
        self.a['input_files'][str(self.request)]='wrong'
        with self.assertRaises(ValueError):self.validate()
        self.a['input_files'][str(self.request)]=sha256(self.request)
        self.request.write_text('Different request.',encoding='utf-8')
        with self.assertRaises(ValueError):self.validate()
        digest=sha256(self.request);self.a['input_files'][str(self.request)]=digest
        self.a['audience_challenges']['request_source']['sha256']=digest
        with self.assertRaises(ValueError):self.validate()

    def test_own_production_artifact_is_not_the_external_user_capture(self):
        path=self.folder/'self-signed.txt';path.write_text(CHALLENGE_PAUSE_TEXT,encoding='utf-8')
        digest=sha256(path);self.a['input_files'][str(path)]=digest
        self.a['audience_challenges']['request_source']={'path':str(path),'sha256':digest}
        with self.assertRaises(ValueError):self.validate()

    def test_missing_duplicate_reordered_or_other_world_question_is_rejected(self):
        base=deepcopy(self.a['audience_challenges']['questions'])
        for questions in [base[:1],[base[0],base[0]],base[::-1],
                          [base[0],{'world':'other','scene_id':'SC09'}],
                          [base[0],{'world':'second','scene_id':'first1'}]]:
            with self.subTest(questions=questions):
                self.a['audience_challenges']['questions']=questions
                with self.assertRaises(ValueError):self.validate()

    def test_first_task_cannot_be_a_judgment_reading_or_highlight_scene(self):
        base=deepcopy(self.a['scenes'][0])
        for field,value in [('kind','compare'),('event','supported'),('candidate','A'),
                            ('terminal_refs',[{'candidate':'A'}]),('attention',[{'phrase':'line'}]),
                            ('reading_path',[{'start':0,'end':4}])]:
            with self.subTest(field=field):
                self.a['scenes'][0]=deepcopy(base);self.a['scenes'][0][field]=value
                with self.assertRaises(ValueError):self.validate()

    def test_source_and_prepared_world_must_be_the_complete_bound_question(self):
        for field in ('question','source','bundle','option'):
            with self.subTest(field=field):
                worlds=deepcopy(self.worlds);bundles=deepcopy(self.b)
                if field=='question':worlds['first']['question']=deepcopy(worlds['second']['question'])
                elif field=='source':worlds['first']['source']=deepcopy(worlds['second']['source'])
                elif field=='bundle':bundles['first']['analysis']['changed']=True
                else:bundles['first']['source_snapshot']['options'].pop('D')
                with self.assertRaises(ValueError):
                    compile_authored_challenges(self.a,bundles,self.clock,worlds,self.folder)

    def test_full_blocks_cannot_be_an_excerpt_or_reordered_duplicate_gap_or_changed_text(self):
        base=deepcopy(self.worlds)
        for change in ('excerpt','reorder','duplicate','gap','text','visibility'):
            with self.subTest(change=change):
                self.worlds=deepcopy(base);blocks=self.worlds['first']['blocks']
                if change=='excerpt':blocks.pop()
                elif change=='reorder':blocks.reverse()
                elif change=='duplicate':blocks[2]['id']=blocks[0]['id']
                elif change=='gap':blocks[2]['start']+=1
                elif change=='text':blocks[2]['text']='Different line.'
                else:blocks[0]['visible']=False
                with self.assertRaises(ValueError):self.compile()

    def test_window_must_fit_without_scene_extension_and_start_on_an_actual_frame(self):
        base=deepcopy(self.clock)
        for field,value in [('end',4.9),('start',2.01),('start',float('nan')),('end',float('inf'))]:
            with self.subTest(field=field):
                self.clock=deepcopy(base);self.clock['scenes'][0][field]=value
                with self.assertRaises(ValueError):self.compile()

    def test_task_shorter_than_3point8_seconds_cannot_spill_its_native_handoff(self):
        # A short complete synthetic take fits; the missing return space alone
        # must reject the task, even though all 72 challenge frames would fit.
        self.clock['segments'][0]['voice_end']=5
        self.clock['scenes'][0]['voice_end']=5
        for duration in (3,3.79):
            self.clock['scenes'][0]['end']=2+duration
            with self.subTest(duration=duration),self.assertRaisesRegex(ValueError,'0.8s handoff'):
                self.compile()
        self.clock['scenes'][0]['end']=5.8
        row=self.compile()['rows'][0]
        self.assertEqual(row['end'],5);self.assertEqual(row['handoff_end'],5.8)

    def test_existing_voice_cannot_move_gain_silence_be_truncated_or_replaced(self):
        base=deepcopy(self.clock)
        for field,value in [('voice_start',5),('text','Changed narration'),('truncated',True),
                            ('time_stretch',True),('voice_end',12)]:
            with self.subTest(field=field):
                self.clock=deepcopy(base);self.clock['segments'][0][field]=value
                with self.assertRaises(ValueError):self.compile()

    def test_measured_hook_translation_roundoff_keeps_the_same_audio_frame(self):
        self.clock['segments'][0]['voice_start']+=1e-12
        self.assertEqual(self.compile()['rows'][0]['frames'],72)
        self.clock['segments'][0]['voice_start']+=1/24
        with self.assertRaises(ValueError):self.compile()

    def test_early_judgment_and_mutated_payoff_world_candidate_or_terminal_ref_rejected(self):
        base=deepcopy(self.clock)
        for field,value in [('time',3),('world','second'),('candidate','D'),('kind','eliminate'),('refs',[])]:
            with self.subTest(field=field):
                self.clock=deepcopy(base);self.clock['candidate_events'][0][field]=value
                with self.assertRaises(ValueError):self.compile()

    def test_missing_or_duplicate_final_payoff_cannot_be_invented(self):
        self.clock['candidate_events'].pop()
        with self.assertRaises(ValueError):self.compile()

    def test_existing_hook_decision_handoff_and_progression_cannot_be_replaced(self):
        base=deepcopy(self.clock)
        for field,value in [('decision_sha','changed'),('end',1.5),('scene_id','invented')]:
            with self.subTest(field=field):
                self.clock=deepcopy(base);self.clock['audience_hook'][field]=value
                with self.assertRaises(ValueError):self.compile()
        self.clock=deepcopy(base)
        self.a['audience_hook']['retention']['progression_scene_id']='first1'
        self.clock['audience_hook']['decision']=deepcopy(self.a['audience_hook'])
        self.clock['audience_hook']['decision_sha']=sha(self.a['audience_hook'])
        with self.assertRaises(ValueError):self.compile()

    def test_compiled_changes_cannot_self_approve_or_trim_source_after_compilation(self):
        expected=self.compile()
        for change in ('passage','option','badge','leak','approve','integer_false'):
            with self.subTest(change=change):
                result=deepcopy(expected)
                if change=='passage':result['rows'][0]['passage']='First line.'
                elif change=='option':result['rows'][0]['options'].pop('D')
                elif change=='badge':result['rows'][0]['pause_badge']['text']='Pause now'
                elif change=='leak':result['rows'][0]['spoiler_boundary']['candidate_states']['A']='supported'
                elif change=='approve':result['human_review']='APPROVED'
                else:result['public_render_ready']=0
                with self.assertRaises(ValueError):
                    validate_compiled_challenges(result,self.a,self.b,self.clock,self.worlds,self.folder)

    def test_compiled_validation_rechecks_the_live_bound_user_source(self):
        result=self.compile()
        self.assertEqual(validate_compiled_challenges(result,self.a,self.b,self.clock,self.worlds,self.folder),result)
        self.request.write_text('revoked',encoding='utf-8')
        with self.assertRaises(ValueError):
            validate_compiled_challenges(result,self.a,self.b,self.clock,self.worlds,self.folder)


if __name__=='__main__':unittest.main()
