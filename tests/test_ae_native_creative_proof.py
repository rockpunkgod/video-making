"""Research isolation, original objects and frozen replay; no AE success is mocked."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from video_contracts import sha,write

HERE=Path(__file__).resolve().parents[1]/'ae/experiments/native-creative-proof'
spec=importlib.util.spec_from_file_location('native_creative_proof',HERE/'run.py')
proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
with patch.object(sys,'path',[str(HERE)]+sys.path):
    guide_spec=importlib.util.spec_from_file_location('native_creative_guide',HERE/'guide.py')
    guide=importlib.util.module_from_spec(guide_spec);guide_spec.loader.exec_module(guide)


class NativeCreativeProofTests(unittest.TestCase):
    def setUp(self):
        self.scene=json.loads((HERE/'synthetic-scene.json').read_text(encoding='utf-8'))

    def test_rejects_teaching_or_public_eligibility(self):
        for field in ('method_id','production_eligible','public_render_ready'):
            scene=deepcopy(self.scene);scene[field]='R02' if field=='method_id' else True
            with self.subTest(field=field),self.assertRaises(ValueError):proof.validate_scene(scene)
        scene=deepcopy(self.scene);scene['claims']['answer_completion']=True
        with self.assertRaises(ValueError):proof.validate_scene(scene)

    def test_rejects_rewritten_source_and_lost_span(self):
        for mutate in (lambda s:s['objects'][1].update(text=' after lunch'),
                       lambda s:s['objects'].pop()):
            scene=deepcopy(self.scene);mutate(scene)
            with self.assertRaises(ValueError):proof.validate_scene(scene)

    def test_protected_core_cannot_be_peeled_or_deferred_destroyed(self):
        for change in ({'protected':True},{'disposition':'removed'},{'attachment':'unknown-source'},
                       {'restore_to':'replacement_sentence'}):
            scene=deepcopy(self.scene);scene['objects'][1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):proof.validate_scene(scene)

    def test_preexisting_project_refused_before_checkpoint(self):
        c=Mock();c.call.return_value={'content':json.dumps({'path':str(proof.ROOT/'local-data/old-picture.aep')})}
        with self.assertRaisesRegex(ValueError,'old AEP'):proof.require_research_project(c)
        self.assertEqual(c.call.call_count,1)
        self.assertNotIn('checkpoint_label',c.call.call_args.args[1])

    def test_outputs_cannot_enter_public_workflow_tree(self):
        with self.assertRaises(ValueError):proof.research_output(proof.ROOT/'ae/outputs')

    def test_render_range_rejects_nonfinite_outside_comp_and_partial_frame(self):
        for label,start,duration in (('../B',0,27),('B',float('nan'),27),('B',0,28),
                                     ('B',-1,8),('B',0,0),('B',0.01,8)):
            with self.subTest(interval=(label,start,duration)),self.assertRaises(ValueError):
                proof.validate_render_range(label,start,duration)
        proof.validate_render_range('C_FIXED_CAMERA',12.5,8)

    def presentation_fixture(self):
        presentation=json.loads((HERE/'rhythm-r4.json').read_text(encoding='utf-8'))
        proof.validate_presentation(presentation,self.scene)
        return {'scene':deepcopy(self.scene),'presentation':presentation}

    def test_rhythm_overlay_preserves_frozen_scene_and_all_original_words(self):
        request=self.presentation_fixture();frozen_sha=sha(request['scene'])
        self.assertEqual(proof.canvas_duration(request),22)
        self.assertEqual(proof.presentation_time(request,3),3.5)
        self.assertEqual(proof.presentation_time(request,27),22)
        slots=proof.voice_slots(request)
        self.assertEqual([v['id'] for v in slots],['orient','target-a','tighten','target-b','settle'])
        self.assertEqual({v['id']:v['text'] for v in slots},{v['id']:v['text'] for v in self.scene['voice']})
        self.assertEqual(sha(request['scene']),frozen_sha)
        self.assertEqual(proof.canvas_duration({'scene':self.scene}),27)
        self.assertEqual(proof.voice_slots({'scene':self.scene}),self.scene['voice'])

    def test_rhythm_overlay_rejects_new_semantics_core_parking_and_invalid_timing(self):
        base=self.presentation_fixture()['presentation']
        mutations=(lambda p:p.update(text='new conclusion'),
                   lambda p:p['parks'].update({'core-subject':p['parks']['aside-time']}),
                   lambda p:p['time_map'].__setitem__(3,[6.7,4.6]),
                   lambda p:p['time_map'].__setitem__(3,[float('nan'),5.5]),
                   lambda p:p['voice_starts'].update(settle=17.251),
                   lambda p:p['voice_starts'].update(new_voice=4),
                   lambda p:p.update(text_rest_opacity=101))
        for mutate in mutations:
            bad=deepcopy(base);mutate(bad)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):proof.validate_presentation(bad,self.scene)

    def test_render_interval_uses_actual_rhythm_duration(self):
        proof.validate_render_range('B',0,22,22)
        proof.validate_render_range('C_FIXED_CAMERA',3.5,7,22)
        with self.assertRaises(ValueError):proof.validate_render_range('B',0,27,22)

    def test_vertical_layout_keeps_r4_timing_voice_and_frozen_supplied_relations(self):
        r4=json.loads((HERE/'rhythm-r4.json').read_text(encoding='utf-8'))
        r5=json.loads((HERE/'attachment-r5.json').read_text(encoding='utf-8'))
        original=deepcopy(self.scene)
        proof.validate_presentation(r5,self.scene)
        self.assertEqual(r5['time_map'],r4['time_map'])
        self.assertEqual(r5['voice_starts'],r4['voice_starts'])
        self.assertEqual(proof.voice_slots({'scene':self.scene,'presentation':r5}),
                         proof.voice_slots({'scene':self.scene,'presentation':r4}))
        self.assertEqual(self.scene,original)

    def test_vertical_layout_cannot_supply_new_attachment_facts_or_unbounded_controls(self):
        base=json.loads((HERE/'attachment-r5.json').read_text(encoding='utf-8'))
        for change in ({'anchor_id':'core-verb'},{'scale_percent':101},{'baseline_gap':float('nan')},
                       {'connector_hold_seconds':-1},{'connector_fade_seconds':0}):
            bad=deepcopy(base);bad['attachment_layout'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):proof.validate_presentation(bad,self.scene)

    def test_faster_peeling_preserves_reading_holds_and_exact_voice_words(self):
        r5=json.loads((HERE/'attachment-r5.json').read_text(encoding='utf-8'))
        fast=json.loads((HERE/'attachment-r5-fast.json').read_text(encoding='utf-8'))
        proof.validate_presentation(fast,self.scene)
        normal={'scene':self.scene,'presentation':r5};quick={'scene':self.scene,'presentation':fast}
        for r in (normal,quick):
            self.assertEqual(proof.presentation_time(r,3),3.5)
            self.assertEqual(proof.canvas_duration(r)-proof.presentation_time(r,22.5),4.5)
        self.assertAlmostEqual(proof.presentation_time(quick,10.9)-proof.presentation_time(quick,5.6),3.5)
        self.assertAlmostEqual(proof.presentation_time(quick,17.5)-proof.presentation_time(quick,11.8),3.1)
        self.assertEqual(fast['attachment_layout'],r5['attachment_layout'])
        self.assertEqual({v['id']:v['text'] for v in proof.voice_slots(quick)},
                         {v['id']:v['text'] for v in proof.voice_slots(normal)})

    def test_actual_attachment_audit_rejects_misalignment_and_wrong_source_even_with_good_geometry(self):
        r5=json.loads((HERE/'attachment-r5.json').read_text(encoding='utf-8'))
        request={'presentation':r5,'scene_sha':sha(self.scene),'spec_sha':sha('SYNTHETIC audit binding'),
                 'layout':[dict(o,x=i*100) for i,o in enumerate(self.scene['objects'])]}
        samples=[]
        for obj in request['layout']:
            if obj['role']!='supplied_modifier':continue
            for phase in ('original','park','final')+ (('follow',) if obj['id']=='aside-time' else ()):
                samples.append({'object_id':obj['id'],'anchor_id':obj['attachment'],'phase':phase,
                    'connector':{'origin':request['scene_sha'],'anchor_id':obj['attachment'],
                        'object_id':obj['id'],'kind':'supplied_synthetic_visual_attachment'},
                    'pivot':[obj['x'],540,0],'scale_percent':100 if phase=='original' else 76,
                    'center_error':0,'baseline_gap':-96 if obj['id']=='aside-time' else 96,
                    'y_rotation':0,'z_rotation':0,'text_opacity':72,
                    'connector_opacity':62 if phase in ('park','follow') else 0})
        measured={'kind':'supplied_synthetic_visual_attachment','spec_sha':request['spec_sha'],
                  'scene_sha':request['scene_sha'],'samples':samples}
        proof.verify_attachment_layout(request,measured)
        for change in ({'center_error':4},{'anchor_id':'core-verb'},{'baseline_gap':-30}):
            bad=deepcopy(measured);bad['samples'][1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):proof.verify_attachment_layout(request,bad)

    def test_fixed_recordings_can_be_reordered_but_not_added_removed_or_duplicated(self):
        request=self.presentation_fixture();clips=[{'id':v['id']} for v in self.scene['voice']]
        pairs=guide.fixed_clips(request,{'clips':clips})
        self.assertEqual([clip['id'] for clip,slot in pairs],[v['id'] for v in proof.voice_slots(request)])
        for invalid in (clips[:-1],clips+[clips[0]],clips[:-1]+[{'id':'new-vo'}]):
            with self.assertRaises(ValueError):guide.fixed_clips(request,{'clips':invalid})

    def test_guide_placement_preserves_words_and_whole_clips_with_no_approval_inheritance(self):
        request=self.presentation_fixture()
        voices=[dict(v,text_sha=sha(v['text']),end=v['start']+1,duration=1,listening_review='PENDING')
                for v in proof.voice_slots(request)]
        guide.validate_placement(request,voices)
        for change in ({'text':'new shortcut'},{'id':'other-id'},{'listening_review':'ACCEPTED'},
                       {'duration':0.5},{'duration':float('nan')},{'end':23,'duration':5.75}):
            bad=deepcopy(voices);bad[-1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):guide.validate_placement(request,bad)
        bad=deepcopy(voices);bad[1].update(end=8.125,duration=4)
        with self.assertRaises(ValueError):guide.validate_placement(request,bad)

    def control_fixture(self, source):
        project=source/'PROJECT_B.aep'
        project.write_bytes(b'SYNTHETIC binding-test bytes, not a native AE project')
        request={'spec_sha':sha('SYNTHETIC-spec'),'scene_sha':sha(self.scene)}
        picture={'kind':'synthetic_native_AE_visual_research','variant':'B',
                 **request,'project':str(project),'project_sha256':proof.file_sha(project),
                 'production_eligible':False,'public_render_ready':False}
        return request,picture

    def test_control_import_rejects_cross_binding_and_release_upgrade(self):
        with TemporaryDirectory() as tmp:
            source=Path(tmp);request,picture=self.control_fixture(source)
            proof.validate_control_source(source,request,picture)
            for field,value in (('spec_sha',sha('other-spec')),('scene_sha',sha('other-scene')),
                                ('variant','A'),('kind','production'),
                                ('production_eligible',True),('public_render_ready',True)):
                changed=dict(picture,**{field:value})
                with self.subTest(field=field),self.assertRaises(ValueError):
                    proof.validate_control_source(source,request,changed)

    def test_control_import_rejects_tamper_and_other_project_with_identical_bytes(self):
        with TemporaryDirectory() as tmp:
            source=Path(tmp);request,picture=self.control_fixture(source)
            other=source/'historical-input.aep';other.write_bytes((source/'PROJECT_B.aep').read_bytes())
            with self.assertRaises(ValueError):
                proof.validate_control_source(source,request,dict(picture,project=str(other)))
            (source/'PROJECT_B.aep').write_bytes(b'changed snapshot')
            with self.assertRaises(ValueError):proof.validate_control_source(source,request,picture)

    def test_invalid_control_snapshot_never_dispatches_to_native_host(self):
        with TemporaryDirectory() as tmp:
            source=Path(tmp);request,picture=self.control_fixture(source)
            picture['scene_sha']=sha('different synthetic scene')
            with patch.object(proof,'research_output',side_effect=lambda p:Path(p)), \
                    patch.object(proof,'current',return_value=request), \
                    patch.object(proof,'read',return_value=picture), \
                    patch.object(proof,'client') as native:
                with self.assertRaises(ValueError):proof.fork_controls(source/'unused',source)
                native.assert_not_called()

    def test_restoration_rejects_same_text_at_wrong_attachment_or_position(self):
        layout=[dict(o,x=i*100) for i,o in enumerate(self.scene['objects'])]
        restored=[{'object_id':o['id'],'text':o['text'],'position':[o['x'],540,0],
                   'y_rotation':0,'parent':'HINGE_'+o['id'] if o['role']=='supplied_modifier' else None}
                  for o in layout]
        proof.verify_restoration({'layout':layout},{'restored':restored})
        for change in ({'position':[100,540,90]},{'parent':'HINGE_wrong'}, {'text':'replacement'}):
            bad=deepcopy(restored);bad[1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                proof.verify_restoration({'layout':layout},{'restored':bad})

    def test_historical_replay_uses_executed_snapshot_and_rejects_tamper(self):
        with TemporaryDirectory() as tmp:
            out=Path(tmp);font=out/'fixture-font';font.write_bytes(b'SYNTHETIC font')
            scene=deepcopy(self.scene)
            for k in ('english','chinese'):scene['font'][k+'_file']=str(font)
            executed=out/'executed-template.jsx';executed.write_text('// preserved old revision',encoding='utf-8')
            request={'scene':scene,'scene_sha':sha(scene),'revision':'SYNTHETIC-old',
                'layout':[dict(o,x=i*100,width=100,text_sha=sha(o['text'])) for i,o in enumerate(scene['objects'])],
                'template_sha':proof.file_sha(executed),
                'fonts_sha':{k:proof.file_sha(font) for k in ('english','chinese')},
                'project':str(out/'never-generated.aep')}
            request['spec_sha']=sha({k:v for k,v in request.items() if k!='project'})
            write(out/'build-request.json',request)
            self.assertEqual(proof.current(out),request)
            executed.write_text('// different animation',encoding='utf-8')
            with self.assertRaises(ValueError):proof.current(out)


if __name__=='__main__':unittest.main()
