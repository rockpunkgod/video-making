"""Regression of actual author decisions, not creative ratings or real exam data."""
from copy import deepcopy
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from video_contracts import write
from ae_production.authored_episode import compile_clock, checked_author, current_folder, script_text, check_script, select_takes
from scripts.voice_delivery import describe_clip, validate as validate_voice, sha256
from ae_production.authored_native import validate_edit, measured_audio_delay
from voicepacks.tools.align_delivery import spans


def clock_input():
    voices=[{'id':'one','text':'Inspect first. Compare next.'},{'id':'two','text':'Second question.'}]
    scenes=[]
    for i,v in enumerate(voices):
        scenes.append({'id':f's{i}','kind':'compare','world':'w','voice_ids':[v['id']],
                       'recognition_seconds':1,'travel_seconds':1,'post_seconds':1,'voice_pre':.5,
                       'candidate':'A','event':'supported','source_refs':[{'quote':'unchanged source'}],
                       'terminal_refs':[{'candidate':'A','effect':'retain'}],'attention':[],
                       'audience_intent':'Inspect the source before comparing.'})
    clips={v['id']:{'audio_sha256':v['id'],'duration_seconds':8} for v in voices}
    aligned={v['id']:{'transcript':v['text'],'audio_sha256':v['id'],'cues':[{
        'text':v['text'],'text_start':0,'text_end':len(v['text']),'start':.1,'end':7.8,
        'display_lines':[v['text']]}]} for v in voices}
    return {'format':{'fps':24},'voices':voices,'scenes':scenes},clips,aligned


class ClockConsumption(unittest.TestCase):
    def motion_input(self):
        a,c,l=clock_input()
        for s in a['scenes']:
            s['choreography']={'orient_seconds':1.8,'candidate_read_seconds':2,
                'candidate_travel_seconds':2.6,'source_read_seconds':2.2,'extract_seconds':2.4,
                'comparison_seconds':3.2,'decision_seconds':1.2,'result_seconds':1.6,'return_seconds':2.4}
            s['reading_path']=[{'start':0,'end':6,'quote':'Source','phrase':'',
                                'mode':'scan','move_seconds':2,'read_seconds':4}]
        return a,c,l

    def test_slow_reading_propagates_to_camera_take_caption_and_decision(self):
        a,c,l=self.motion_input();before=compile_clock(a,c,l)
        a['scenes'][0]['reading_path'][0]['read_seconds']+=3
        after=compile_clock(a,c,l)
        for field in ('settled','extract_start','event_time','end'):
            self.assertAlmostEqual(after['scenes'][0][field]-before['scenes'][0][field],3)
        self.assertAlmostEqual(after['segments'][0]['voice_start']-before['segments'][0]['voice_start'],3)
        self.assertAlmostEqual(after['cues'][0]['start']-before['cues'][0]['start'],3)
        self.assertEqual(after['candidate_events'][0]['refs'],before['candidate_events'][0]['refs'])
        self.assertEqual(after['scenes'][0]['source_refs'],before['scenes'][0]['source_refs'])
        self.assertEqual(after['scenes'][0]['candidate_arrive'],before['scenes'][0]['candidate_arrive'])

    def test_candidate_read_and_movement_are_distinct_consumed_intervals(self):
        a,c,l=self.motion_input();before=compile_clock(a,c,l)
        a['scenes'][0]['choreography']['candidate_read_seconds']+=2
        after=compile_clock(a,c,l);s=after['scenes'][0]
        self.assertAlmostEqual(s['candidate_start']-before['scenes'][0]['candidate_start'],2)
        self.assertAlmostEqual(s['candidate_arrive']-s['candidate_start'],2.625)
        self.assertGreater(s['event_time'],s['settled'])
        self.assertGreaterEqual(s['extract_start']-s['source_arrive'],2.2)
        self.assertGreater(s['return_start'],s['decision_end'])
        self.assertEqual(after['segments'][0]['voice'],before['segments'][0]['voice'])

    def test_full_copy_export_cannot_mask_changed_spoken_words(self):
        a,_,_=clock_input();a.update(revision='synthetic',copy_review='PENDING')
        for s in a['scenes']:s['title']='Synthetic chapter'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'EPISODE_SCRIPT.md').write_text(script_text(a),encoding='utf-8');check_script(p,a)
            a['voices'][0]['text']='Different exact words.'
            with self.assertRaisesRegex(ValueError,'missing or stale'):check_script(p,a)

    def test_recognition_hold_moves_the_actual_lift_and_candidate(self):
        a,c,l=clock_input();old=compile_clock(a,c,l);a['scenes'][0]['recognition_seconds']=3
        new=compile_clock(a,c,l)
        self.assertEqual(new['scenes'][0]['extract_start']-old['scenes'][0]['extract_start'],2)
        self.assertEqual(new['scenes'][0]['settled']-old['scenes'][0]['settled'],2)
        self.assertEqual(new['scenes'][0]['candidate_start']-old['scenes'][0]['candidate_start'],2)
        self.assertEqual(old['candidate_events'],new['candidate_events'])
        self.assertEqual(old['cues'],new['cues'])
        self.assertEqual(a['scenes'][0]['source_refs'],new['scenes'][0]['source_refs'])

    def test_complete_take_duration_moves_later_scene_captions_and_decision(self):
        a,c,l=clock_input();old=compile_clock(a,c,l);c['one']['duration_seconds']+=2
        new=compile_clock(a,c,l)
        self.assertEqual(new['segments'][1]['voice_start']-old['segments'][1]['voice_start'],2)
        self.assertEqual(new['cues'][1]['start']-old['cues'][1]['start'],2)
        self.assertEqual(new['candidate_events'][0]['time']-old['candidate_events'][0]['time'],2)
        self.assertEqual(new['candidate_events'][0]['refs'],old['candidate_events'][0]['refs'])
        self.assertFalse(new['segments'][0]['time_stretch'])
        self.assertFalse(new['segments'][0]['truncated'])

    def test_original_candidate_recognition_changes_order_without_retiming_voice(self):
        a,c,l=clock_input();old=compile_clock(a,c,l)
        a['scenes'][0]['candidate_entry_seconds']=2.75;new=compile_clock(a,c,l)
        self.assertLess(new['scenes'][0]['candidate_start']+.8,new['scenes'][0]['extract_start'])
        self.assertEqual(new['scenes'][0]['extract_start']-old['scenes'][0]['extract_start'],2.75)
        self.assertEqual(new['cues'],old['cues'])
        self.assertEqual(new['segments'],old['segments'])
        self.assertEqual(new['candidate_events'],old['candidate_events'])

    def test_copy_change_cannot_reuse_old_take_alignment(self):
        a,c,l=clock_input();a['voices'][0]['text']='Changed copy.'
        with self.assertRaisesRegex(ValueError,'another take or transcript'):compile_clock(a,c,l)

    def test_new_take_cannot_reuse_old_alignment(self):
        a,c,l=clock_input();c['one']['audio_sha256']='new take'
        with self.assertRaisesRegex(ValueError,'another take or transcript'):compile_clock(a,c,l)

    def test_replay_hold_moves_following_scene_without_repeating_decision(self):
        a,c,l=clock_input();replay=deepcopy(a['scenes'][0])
        replay.update(id='recall',kind='replay',replay_of='s0',voice_ids=['recall'],terminal_refs=[])
        replay.pop('event');a['voices'].append({'id':'recall','text':a['voices'][0]['text']})
        c['recall']=deepcopy(c['one']);l['recall']=deepcopy(l['one'])
        a['scenes'].insert(1,replay);old=compile_clock(a,c,l)
        replay['post_seconds']+=3;new=compile_clock(a,c,l)
        self.assertEqual(new['scenes'][2]['start']-old['scenes'][2]['start'],3)
        self.assertEqual(new['cues'][-1]['start']-old['cues'][-1]['start'],3)
        self.assertEqual(len(new['candidate_events']),2)
        self.assertEqual(new['candidate_events'][1]['refs'],old['candidate_events'][1]['refs'])
        self.assertEqual(new['scenes'][1]['source_refs'],old['scenes'][1]['source_refs'])

    def test_missing_spoken_cue_is_not_silently_ignored(self):
        a,c,l=clock_input();a['scenes'][0]['candidate_anchor']='Absent phrase'
        with self.assertRaisesRegex(ValueError,'absent'):compile_clock(a,c,l)

    def test_decision_cannot_precede_visible_comparison(self):
        a,c,l=clock_input();a['scenes'][0]['event_anchor']='Inspect'
        with self.assertRaisesRegex(ValueError,'visible comparison'):compile_clock(a,c,l)

    def test_caption_must_cover_exact_source_characters(self):
        a,c,l=clock_input();l['one']['cues'][0]['text']='Invented subtitle'
        with self.assertRaisesRegex(ValueError,'spoken transcript'):compile_clock(a,c,l)


class AuthorBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.author={'product':'FREE_SHOWCASE','format':{'width':1920,'height':1080,'fps':24},'media_role':'EDITORIAL_PROXY',
                     'public_render_ready':False,'input_files':{},'sources':{},'voices':[],'scenes':[]}
        self.bundles={}
        for world in ('first','second'):
            terms=[{'candidate':c,'effect':'retain' if c=='A' else 'eliminate'} for c in 'ABCD']
            b={'source_snapshot':{'question_id':world,'stem':'Find Widget','passage':'Widget has one documented benefit.','options':{c:c for c in 'ABCD'}},
               'analysis':{'question_verification':{'candidate_bindings':terms}}}
            path=self.folder/(world+'.json');write(path,b);self.bundles[world]=b
            status=self.folder/(world+'-status.json');write(status,{})
            self.author['sources'][world]={'bundle':str(path),'status':str(status)}
            for index,t in enumerate(terms+[None]):
                sid=world+str(index);self.author['voices'].append({'id':sid,'text':'Synthetic test copy.'})
                s={'id':sid,'kind':'answer' if t is None else 'compare','world':world,'voice_ids':[sid],
                   'audience_intent':'Synthetic source comparison','recognition_seconds':1,'travel_seconds':1,'voice_pre':1,'post_seconds':1,
                   'source_refs':[{'world':world,'pointer':'/passage','start':0,'end':6,'quote':'Widget'}],
                   'action_refs':[],'candidate':t['candidate'] if t else 'A','event':('supported' if t['effect']=='retain' else 'eliminate') if t else 'final',
                   'terminal_refs':[t] if t else terms}
                self.author['scenes'].append(s)
            if world=='first':
                replay=deepcopy(self.author['scenes'][-1]);replay.update(id='replay',kind='replay',replay_of='first0',voice_ids=['replay'],terminal_refs=[])
                replay.pop('event');self.author['scenes'].append(replay);self.author['voices'].append({'id':'replay','text':'Recall only.'})
        # Core frozen validation has its own real contract tests. These controls
        # isolate the consumer's additional boundaries using synthetic bundles.
        self.v=patch('ae_production.authored_episode.verify_bundle');self.v.start();self.addCleanup(self.v.stop)
        self.s=patch('ae_production.authored_episode.status_matches',return_value=True);self.status=self.s.start();self.addCleanup(self.s.stop)

    def check(self):
        write(self.folder/'AV_AUTHOR.json',self.author);return checked_author(self.folder)

    def test_default_pointer_rejects_unscoped_folder(self):
        self.check();index=self.folder/'index.json';write(index,{'revision':str(self.folder)})
        with patch('ae_production.authored_episode.CURRENT',index),patch('ae_production.authored_episode.ROOT',self.folder.parent.parent):
            with self.assertRaisesRegex(ValueError,'actual private author'):current_folder()

    def test_default_pointer_selects_the_current_author(self):
        current=self.folder/'local-data'/'film';current.mkdir(parents=True)
        write(current/'AV_AUTHOR.json',self.author)
        index=self.folder/'index.json';write(index,{'revision':str(current)})
        with patch('ae_production.authored_episode.CURRENT',index),patch('ae_production.authored_episode.ROOT',self.folder):
            self.assertEqual(current_folder(),current.resolve())

    def test_unknown_director_decision_is_explicitly_rejected(self):
        self.author['scenes'][0]['invented_effect']=True
        with self.assertRaisesRegex(ValueError,'Unsupported author decision'):self.check()

    def test_changed_source_word_is_rejected(self):
        self.author['scenes'][0]['source_refs'][0]['quote']='Gadget'
        with self.assertRaisesRegex(ValueError,'Source span changed'):self.check()

    def test_revoked_status_stops_consumption(self):
        self.status.return_value=False
        with self.assertRaisesRegex(ValueError,'current status'):self.check()

    def test_missing_candidate_check_cannot_be_hidden_by_final(self):
        self.author['scenes'][1].pop('event')
        with self.assertRaisesRegex(ValueError,'complete candidate checks'):self.check()

    def test_replay_cannot_execute_another_decision(self):
        replay=next(s for s in self.author['scenes'] if s['kind']=='replay');replay['event']='supported'
        replay['terminal_refs']=[self.bundles['first']['analysis']['question_verification']['candidate_bindings'][0]]
        with self.assertRaisesRegex(ValueError,'executed twice'):self.check()


class Captions(unittest.TestCase):
    def test_split_preserves_exact_text_and_english_word(self):
        text='这句话用于验证字幕逐字保持不变，同时完整保留 Fitbit，不拆断英文单词。'
        ranges=spans(text)
        self.assertEqual(''.join(text[a:b] for a,b in ranges),text)
        self.assertTrue(any('Fitbit' in text[a:b] for a,b in ranges))

    def test_selected_delivery_reuses_whole_unchanged_take_and_explicit_retake(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def delivery(name,takes):
                out=root/name;out.mkdir();clips=[]
                for vid,word,sample in takes:
                    with wave.open(str(out/(vid+'.wav')),'wb') as w:
                        w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(sample.to_bytes(2,'little',signed=True)*4800)
                    (out/(vid+'.txt')).write_text(word,encoding='utf-8')
                    clips.append(describe_clip(out,vid,vid+'.wav',vid+'.txt'))
                write(out/'delivery.json',{'schema':'voice-delivery/v1','clips':clips});return out/'delivery.json'
            before=delivery('first',[('keep','Exact first words.',10),('retake','Exact second words.',20)])
            replacement=delivery('second',[('retake','Exact second words.',30)])
            author={'voice_delivery':'selected/delivery.json','voice_inputs':[str(before),str(replacement)],
                    'voices':[{'id':'keep','text':'Exact first words.'},{'id':'retake','text':'Exact second words.'}]}
            result=select_takes(root,author);validate_voice(result['delivery'])
            self.assertEqual(sha256(root/'selected/keep.wav'),sha256(root/'first/keep.wav'))
            self.assertEqual(sha256(root/'selected/retake.wav'),sha256(root/'second/retake.wav'))
            self.assertNotEqual(sha256(root/'selected/retake.wav'),sha256(root/'first/retake.wav'))
            self.assertEqual(result['new_copy_takes'],0)


class NativeEditorial(unittest.TestCase):
    def test_measured_aac_delay_does_not_accept_arbitrary_sync_error(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'complete.wav';x=np.random.default_rng(7).integers(-6000,6000,12000,dtype=np.int16)
            with wave.open(str(wav),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(x.tobytes())
            plan={'segments':[{'id':'take','voice_start':.5,'voice':{'path':str(wav)}}]}
            pcm=np.zeros(48000);pcm[25024:25024+len(x)]=x*.707
            delay,rows=measured_audio_delay(plan,pcm)
            self.assertEqual(delay,1024);self.assertEqual(rows[0]['complete_samples'],len(x))
            pcm=np.zeros(48000);pcm[24512:24512+len(x)]=x*.707
            with self.assertRaisesRegex(ValueError,'supported offset'):measured_audio_delay(plan,pcm)

    def test_native_edit_rejects_shifted_take_and_cut_picture(self):
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'take-frame.wav'
            with wave.open(str(wav),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(bytes(9600))
            plan={'duration':2,'segments':[{'id':'take','voice_start':.5,'voice':{'padded_path':str(wav)}}]}
            timeline={'frameSizeHorizontal':1920,'frameSizeVertical':1080,
                'videoTracks':[{'clips':[{'name':'picture.mp4','start':0,'duration':2,'inPoint':0}]}],
                'audioTracks':[{'clips':[{'name':wav.name,'start':.5,'duration':.1}]}]}
            validate_edit(plan,timeline,'picture.mp4')
            timeline['audioTracks'][0]['clips'][0]['start']=.6
            with self.assertRaisesRegex(ValueError,'placement changed'):validate_edit(plan,timeline,'picture.mp4')
            timeline['audioTracks'][0]['clips'][0]['start']=.5
            timeline['videoTracks'][0]['clips'][0]['inPoint']=.2
            with self.assertRaisesRegex(ValueError,'cut, shifted or replaced'):validate_edit(plan,timeline,'picture.mp4')

    def test_native_edit_checks_music_without_hiding_missing_voice(self):
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'take-frame.wav'
            with wave.open(str(wav),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(bytes(9600))
            plan={'duration':2,'segments':[{'id':'take','voice_start':.5,'voice':{'padded_path':str(wav)}}],
                  'music':[{'clip_path':'music.wav','audio_track_index':1,'timeline_start':0,'duration':1}]}
            timeline={'frameSizeHorizontal':1920,'frameSizeVertical':1080,
                'videoTracks':[{'clips':[{'name':'picture.mp4','start':0,'duration':2,'inPoint':0}]}],
                'audioTracks':[{'clips':[{'name':wav.name,'start':.5,'duration':.1}]},
                               {'clips':[{'name':'music.wav','start':0,'duration':1}]}]}
            validate_edit(plan,timeline,'picture.mp4')
            timeline['audioTracks'][1]['clips'][0]['start']=.1
            with self.assertRaisesRegex(ValueError,'music placement'):validate_edit(plan,timeline,'picture.mp4')
            timeline['audioTracks'][1]['clips'][0]['start']=0
            timeline['audioTracks'][0]['clips'][0]['name']='music.wav'
            with self.assertRaisesRegex(ValueError,'take placement'):validate_edit(plan,timeline,'picture.mp4')


if __name__=='__main__':unittest.main()
