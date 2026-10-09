"""Synthetic assembly checks: no real exam text or teaching credential."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]/'ae/experiments/reading-d-dual-pass'
previous_path=sys.path[:]
previous_run=sys.modules.get('run')
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('reading_d_integration_test',HERE/'integration.py')
integration=importlib.util.module_from_spec(spec)
try:spec.loader.exec_module(integration)
finally:
    sys.path[:]=previous_path
    if previous_run is None:sys.modules.pop('run',None)
    else:sys.modules['run']=previous_run


class ReadingDAssemblyTests(unittest.TestCase):
    def frozen_fixture(self):
        return {'asset_id':'synthetic','semantic_binding_sha':'synthetic-binding',
                'semantic_review':{'level':'ai_reviewed'},'payload':{
                    'review':{'method_actions':[{'question_id':integration.project.__globals__['QUESTION'],
                        'action_id':'q33-R11-action','method_id':'synthetic-method',
                        'role':'interpreter','answer':None,'method_version':'1'}],
                        'segments':[{'question_id':integration.project.__globals__['QUESTION'],'segment_id':s}
                                    for s in integration.project.__globals__['SEGMENTS']],
                        'decisions':[{'question_id':integration.project.__globals__['QUESTION'],
                            'candidate':str(i),'effect':'retain' if i==0 else 'reject',
                            'basis':'direct_text_review','method_id':None} for i in range(4)]},
                    'questions':[{'question_id':integration.project.__globals__['QUESTION']}],
                    'methods':[{'method_id':'synthetic-method','version':'1'}],
                    'source':{'synthetic':True},'passage':'SYNTHETIC ONLY'}}

    def test_interpreter_cannot_acquire_answer_permission(self):
        for field,value in [('role','decider'),('answer','0')]:
            b=self.frozen_fixture();b['payload']['review']['method_actions'][0][field]=value
            with patch.dict(integration.project.__globals__,{'require_current':lambda *_:None}):
                with self.assertRaises(ValueError):integration.project(b,{})

    def test_direct_review_closure_is_not_method_credit(self):
        b=self.frozen_fixture()
        with patch.dict(integration.project.__globals__,{'require_current':lambda *_:None}):
            p=integration.project(b,{})
            self.assertEqual(p['strict_two_method_relay'],'HOLD')
            self.assertFalse(p['public_render_ready'])
            b['payload']['review']['decisions'][0]['method_id']='synthetic-method'
            with self.assertRaises(ValueError):integration.project(b,{})

    def test_original_reading_and_approved_locating_are_complete(self):
        rows=integration.segments()
        self.assertEqual(integration.validate_timeline(rows),94)
        locating=[s for s in rows if s['id'].endswith('_LOCATE')]
        self.assertEqual([(s['source_start'],s['source_end']) for s in locating],[(0,7),(8,20)])
        self.assertEqual(rows[0]['end'],8)

    def test_direct_source_frames_keep_output_to_source_mapping(self):
        n={'source_comp_id':1,'comp_id':42}
        for output,source in [(192,0),(360,20),(840,8),(1128,40),(2252,86+20/24)]:
            m=integration.render_mapping(output,n)
            self.assertEqual(m['comp'],1)
            self.assertAlmostEqual(m['source_start'],source)
            self.assertEqual(m['native_count'],m['logical_count'])
        self.assertEqual(integration.render_mapping(768,n)['comp'],42)

    def test_only_the_declared_constant_source_question_is_held(self):
        n={'source_comp_id':1,'comp_id':42};m=integration.render_mapping(0,n)
        self.assertEqual((m['native_count'],m['logical_count'],m['source_start']),(1,192,0))
        with self.assertRaises(ValueError):integration.render_mapping(4,n)

    def test_batch_changes_never_cross_scene_or_change_source_time(self):
        n={'source_comp_id':1,'comp_id':42}
        m=integration.render_mapping(352,n,32)
        self.assertEqual((m['native_count'],m['logical_count']),(8,8))
        self.assertAlmostEqual(m['source_start'],160/24)
        for size in (0,33,True,1.5):
            with self.assertRaises(ValueError):integration.render_mapping(192,n,size)

    def test_speed_change_or_missing_tail_is_rejected(self):
        for field in ('source_end','end'):
            changed=deepcopy(integration.segments());changed[-1][field]-=1
            with self.assertRaises(ValueError):integration.validate_timeline(changed)

    def test_screen_parts_keep_their_actual_source_segment(self):
        source={'segments':[{'segment_id':'SYNTHETIC-'+str(i),'screen_text':'synthetic'+str(i)+'\npart'+str(i)} for i in range(5)]}
        result=integration.screen_projections(source)
        self.assertEqual(result[2]['segment_ref'],result[3]['segment_ref'])
        self.assertEqual(result[2]['segment_ref'],'SYNTHETIC-2')
        self.assertEqual(result[4]['segment_ref'],'SYNTHETIC-3')
        self.assertEqual(result[5]['segment_ref'],'SYNTHETIC-4')
        self.assertNotEqual(result[2]['text_sha'],result[3]['text_sha'])

    def test_real_data_output_cannot_escape_ignored_case_directory(self):
        with self.assertRaises(ValueError):integration.local(Path.cwd()/'public-case')

    def test_replay_uses_the_bound_executed_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);latest=folder/'latest.jsx';latest.write_text('new implementation')
            snapshot=folder/'executed-template.jsx';snapshot.write_text('executed implementation')
            r={'template':str(latest),'template_sha':integration.file_sha(snapshot)}
            self.assertEqual(integration.template_path(folder,r),snapshot)
            snapshot.write_text('tampered')
            with self.assertRaises(ValueError):integration.template_path(folder,r)

    def test_parallel_resume_audit_checks_every_frame_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/str(k) for k in range(17)]
            for p in paths:p.write_bytes(p.name.encode())
            checks=[(p,integration.file_sha(p)) for p in paths]
            integration.verify_frame_files(checks)
            paths[-1].write_bytes(b'tampered')
            with self.assertRaises(ValueError):integration.verify_frame_files(checks)

    def test_fixed_option_choreography_rejects_revised_review_decisions(self):
        source={'answer':'A','decisions':[{'candidate':letter,'effect':'retain' if letter=='A' else 'eliminate'}
                for letter in 'ABCD']}
        integration.validate_director_decisions(source)
        for field in ('answer','effect'):
            changed=deepcopy(source)
            if field=='answer':changed['answer']='B'
            else:changed['decisions'][1]['effect']='unresolved'
            with self.assertRaises(ValueError):integration.validate_director_decisions(changed)

    def test_original_question_and_options_cannot_drift_from_frozen_question(self):
        source={'semantic_binding_sha':'synthetic','question':{'stem':'Synthetic question',
                'options':{'A':'Synthetic option'}}}
        original={'source':deepcopy(source),'question_parts':[{'start':0,'end':18,'text':'Synthetic question'}]}
        integration.validate_original_question(original,source)
        for target in ('stem','option','part'):
            changed=deepcopy(original)
            if target=='stem':changed['source']['question']['stem']='Different'
            elif target=='option':changed['source']['question']['options']['A']='Different'
            else:changed['question_parts'][0]['text']='Different'
            with self.assertRaises(ValueError):integration.validate_original_question(changed,source)

    def test_native_layer_lifetime_cannot_end_before_application(self):
        integration.validate_layer_lifetimes([{'in_point':0,'out_point':87}],87)
        for layers in ([],[{'in_point':0,'out_point':20}],[{'in_point':1,'out_point':87}],[{}]):
            with self.assertRaises(ValueError):integration.validate_layer_lifetimes(layers,87)

    def test_display_cues_cannot_rewrite_literal_evidence(self):
        source={'semantic_binding_sha':'synthetic','passage':'synthetic evidence',
                'segments':[{'segment_id':'s','evidence':[{'field':'passage','start':0,'end':18}]}]}
        units=[{'id':'evidence','span':[0,18]}]
        cues={'source_binding':'synthetic','cues':[{'unit_id':'evidence','span':[0,9],
              'text':'synthetic','text_sha':integration.sha('synthetic'),
              'review_refs':['s'],'windows':[[21,21.5]]}]}
        self.assertEqual(integration.validate_display_cues(cues,source,units),cues['cues'])
        for field,value in [('text','invented'),('review_refs',['absent']),('windows',[[1,2]])]:
            changed=deepcopy(cues);changed['cues'][0][field]=value
            with self.assertRaises(ValueError):integration.validate_display_cues(changed,source,units)

    def test_inherited_native_frames_require_accepted_lineage_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'delivery/q33-r6';frames=source/'native-frames'
            frames.mkdir(parents=True);movie=source/'synthetic.mp4';movie.write_bytes(b'synthetic movie')
            manifest={}
            for index in range(192,480):
                path=frames/('FRAME_'+str(index).zfill(5)+'.tif');path.write_bytes(str(index).encode())
                manifest[path.name]=integration.file_sha(path)
            integration.write(source/'native-frame-shas.json',manifest)
            receipt={'patch_sha':'synthetic-patch','frames':[192,480],'native_canvas':[3840,2160,24],
                     'frame_manifest_sha':integration.sha(manifest),
                     'movie':{'path':str(movie),'sha256':integration.file_sha(movie)}}
            integration.write(source/'render-receipt.json',receipt)
            r={'locating_config':str(root/'plan/config.json'),'patch_sha':'synthetic-patch',
               'accepted_movie_sha':integration.file_sha(movie)}
            m=integration.render_mapping(840,{'source_comp_id':1,'comp_id':42})
            paths,proof=integration.inherited_guided(r,m)
            self.assertEqual(proof['source_frames'],[192,196])
            paths[0].write_bytes(b'tampered')
            with self.assertRaises(ValueError):integration.inherited_guided(r,m)


if __name__=='__main__':unittest.main()
