"""Synthetic geometry and final-cut controls; not English or taste certification."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from answer_engine.frozen_export import FrozenAssetExporter
from answer_engine.method_application_export import FrozenMethodApplicationExporter
from creative_os.cognitive_pov import build_spec, validate_spec
from premiere_production.cognitive import check_timeline, caption_cues
from tests.test_execution import fixture, action
from video_contracts import sha, seal


class CognitivePovTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = Path('C:/Windows/Fonts/georgia.ttf')
        if not cls.font.exists():
            cls.font = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        q = fixture(); text = 'lead read your ____ (seed) until leave'
        region = dict(field='passage',start=0,end=len(text),quote=text)
        q.update(question_type='语法填空',passage=text,stem='SYNTHETIC slot (seed)',given_word='seed',relations=[],
            requested_chain=['G01'],observations=[dict(method_id=mid,evidence=[region],reviewed=True)
                                                for mid in ('G01','G09')])
        row = action('route','G01','framework',dict(kind='route_selection',node_ids=['with_hint','noun']),evidence=[region])
        row['decision_rule_check'] = 'SYNTHETIC explicit predicate, determiner, slot, hint and temporal assertions'
        q['action_executions'] = [row]
        registry = Registry(); analysis = QuestionAnalyzer(registry).analyze(q)
        request = dict(question=q,analysis=analysis,
            methods=[deepcopy(registry.methods[mid]) for mid in analysis['method_versions']],
            reviews=[dict(question_id=q['question_id'],input_sha256=sha(q),analysis_sha256=sha(analysis),
                reviewer='SYNTHETIC PROGRAM ONLY',reviewer_kind='AI',evaluation_phase='post_reveal')],
            withdrawals=[],evaluation_phase='post_reveal',
            source=dict(usage_status='internal_only',redistribution_status='unconfirmed',
                        source_reference='SYNTHETIC',attribution_text='SYNTHETIC'))
        exporter = FrozenAssetExporter(); cls.bundle = exporter.export(request); cls.status = exporter.status(request)
        spans = []; cursor = 0
        for sid,literal,role in [('lead','lead ','context'),('predicate','read ','predicate'),
                ('determiner','your ','determiner'),('slot','____ ','slot'),('hint','(seed) ','hint'),
                ('time','until leave','temporal_clause')]:
            spans.append(dict(span_id=sid,field='passage',start=cursor,end=cursor+len(literal),quote=literal,
                semantic_role=role,assertion=dict(field='decision_rule_check',quote=row['decision_rule_check'])))
            cursor += len(literal)
        annotation = dict(action_index=0,review_indices=[0],source_region=region,spans=spans,
            reduced_span_ids=['predicate','determiner','slot','hint'],deferred_span_ids=['lead','time'],
            protected_span_ids=['predicate','determiner','slot'],
            relations=[dict(from_span_id='predicate',to_span_ids=['determiner','slot'],
                assertion=dict(field='decision_rule_check',quote=row['decision_rule_check']))])
        cls.application = FrozenMethodApplicationExporter().export(cls.bundle,cls.status,annotation,'synthetic')
        cls.package = {'package_id':'SYNTHETIC-package'}
        cls.excerpt = {'delivery_copy_sha':sha('SYNTHETIC copy'), 'units':[
            dict(unit_id='unit-'+str(i),asset_id=cls.bundle['asset_id'],method_id='G01',role='framework',
                action_artifact_refs=[dict(asset_id=cls.bundle['asset_id'],pointer='/analysis/execution_trace/0')],
                source_claim_refs=['SYNTHETIC-claim'],on_screen_copy='\n'.join('SYNTHETIC line '+str(j) for j in range(n)))
            for i,n in enumerate((2,3,4))]}

    def args(self, excerpt=None, status=None):
        return (self.application,self.bundle,self.status if status is None else status,
                self.package,{}, {},{},self.excerpt if excerpt is None else excerpt)

    def spec(self):
        if not self.font.exists(): self.skipTest('No local measurement font')
        # Copy review is covered by Hero contract tests. Isolate the native
        # annotation-to-motion contract here; upstream validity remains real.
        with patch('creative_os.cognitive_pov.validate_excerpt'):
            return build_spec(*self.args(),dict(english=str(self.font),chinese=str(self.font)))

    def test_deterministic_original_space_and_reversible_source(self):
        before = sha([self.application,self.bundle,self.status,self.excerpt])
        first = self.spec(); second = self.spec()
        self.assertEqual(first,second)
        self.assertEqual(before,sha([self.application,self.bundle,self.status,self.excerpt]))
        self.assertTrue(first['original_first'] and first['reality_layer_persistent'])
        self.assertEqual(first['camera']['rotation'],[0,0,0])
        self.assertFalse(first['camera']['depth_of_field'])
        self.assertFalse(first['full_solution'] or first['public_render_ready'])
        self.assertEqual(first['human_taste_review'],'PENDING')
        for node in first['nodes']:
            if node.get('span_id'):
                self.assertEqual(node['out_point'] if 'out_point' in node else 20,20)
                self.assertEqual(node['tracks']['position'][0][1],node['tracks']['position'][-1][1])
                self.assertEqual(node['tracks']['opacity'][0][1],node['tracks']['opacity'][-1][1])

    def test_camera_role_stop_and_target_drift_rejected_even_after_hash_reseal(self):
        spec = self.spec()
        for edit in (lambda s:s['camera'].update(rotation=[0,15,0]),
                     lambda s:s['nodes'].pop(),
                     lambda s:s['events'][0].update(targets=['unowned']),
                     lambda s:s['nodes'][0].update(text='SYNTHETIC answer invented')):
            changed = deepcopy(spec); edit(changed)
            changed['spec_sha'] = sha({k:v for k,v in changed.items() if k!='spec_sha'})
            with patch('creative_os.cognitive_pov.validate_excerpt'),self.assertRaises(ValueError):
                validate_spec(changed,*self.args())
        for role in ('decider','reducer'):
            excerpt = deepcopy(self.excerpt);excerpt['units'][0]['role']=role
            with patch('creative_os.cognitive_pov.validate_excerpt'),self.assertRaises(ValueError):
                build_spec(*self.args(excerpt),dict(english=str(self.font),chinese=str(self.font)))

    def test_withdrawn_upstream_cannot_generate_an_old_visual(self):
        status = seal(dict(self.status,effective_status='WITHDRAWN'))
        with patch('creative_os.cognitive_pov.validate_excerpt'),self.assertRaises(ValueError):
            build_spec(*self.args(status=status),dict(english=str(self.font),chinese=str(self.font)))


class CognitiveEditorialTests(unittest.TestCase):
    def fixture(self):
        spec = dict(id='SYNTHETIC',pagination={'truncated':False},end=20,
            videoTracks=[dict(clips=[dict(nodeId='v',name='motion.mp4',start=0,duration=20)])],
            audioTracks=[dict(clips=[dict(nodeId='a',name='voice.wav',start=6.5,duration=10.48)]),
                         dict(clips=[dict(nodeId='m',name='music.wav',start=0,duration=20)])])
        settings = dict(id='SYNTHETIC',frameSizeHorizontal=1920,frameSizeVertical=1080,
            timebase='10584000000',audioSampleRateHz=48000,audioChannelCount=2)
        receipt = dict(output='motion.mp4')
        audio = dict(voice=dict(path='voice.wav',start=6.5,end=16.98),music=dict(clip_path='music.wav'))
        return spec,settings,'SYNTHETIC',receipt,audio,dict(motion='v',voice='a',music='m')

    def test_native_audio_end_must_preserve_samples_and_not_frame_truncate(self):
        args = self.fixture();self.assertEqual(len(check_timeline(*args)),3)
        bad = deepcopy(args);bad[0]['audioTracks'][0]['clips'][0]['duration']=251/24
        with self.assertRaises(ValueError):check_timeline(*bad)
        bad = deepcopy(args);bad[0]['audioTracks'].append(dict(clips=[dict(name='extra.wav',start=0,duration=20)]))
        with self.assertRaises(ValueError):check_timeline(*bad)
        bad = deepcopy(args);bad[0]['pagination']['truncated']=True
        with self.assertRaises(ValueError):check_timeline(*bad)

    def test_srt_parser_preserves_chinese_and_literal_copy(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'SYNTHETIC.srt'
            path.write_text('1\n00:00:06,500 --> 00:00:07,500\nSYNTHETIC 停。\n',encoding='utf-8-sig')
            self.assertEqual(caption_cues(path),[dict(start=6.5,end=7.5,text='SYNTHETIC 停。')])
            path.write_text('1\nnot SRT\nSYNTHETIC\n',encoding='utf-8')
            with self.assertRaises(ValueError):caption_cues(path)
