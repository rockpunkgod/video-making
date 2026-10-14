"""SYNTHETIC contract tests, never teaching reviews or human cinema evidence."""
import ast
from copy import deepcopy
import contextlib
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_mechanical_payoff as decisions
from tests import test_student_pov as copies
from tests.test_boundary_risk_review import synthetic_review
from tests.test_pedagogy_v04 import synthetic_spans
from tests.test_student_experience import credential
from video_contracts import ROOT,read,write,sha,seal
from pedagogy import compile_plan,copy_projection,motion_projection
from student_pov import realize,realize_experience
from method_choreography import (compile_choreography,inspect_choreography,validate_choreography,
    project_choreography,compile_synthetic_peel,analyze_legacy)
from method_choreography.compiler import choreography_semantics
from method_choreography.synthetic import validate_synthetic_peel
from method_choreography.validation import validate_projection
from method_choreography.audit import audit_choreography
from method_choreography.registry import registry,signature_matches
from method_choreography.__main__ import main


def reseal(value):
    value=deepcopy(value);value['choreography_sha']=sha(choreography_semantics(value))
    value['choreography_id']='choreography:'+value['choreography_sha'];return seal(value)


class MethodChoreographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle,cls.status,cls.selection=decisions.freeze()
        base=compile_plan(cls.bundle,cls.status,cls.selection,mode='worked_example',generated_at='SYNTHETIC')
        cls.plan=compile_plan(cls.bundle,cls.status,cls.selection,mode='worked_example',generated_at='SYNTHETIC',
            boundary_review=synthetic_review(base,cls.bundle),contract_version='0.4.0')
        cls.copy=copy_projection(cls.plan,cls.bundle,cls.status);cls.motion=motion_projection(cls.plan,cls.bundle,cls.status)
        candidate=realize_experience(cls.copy,cls.motion,cls.plan,cls.bundle,cls.status)
        cls.experience=realize_experience(cls.copy,cls.motion,cls.plan,cls.bundle,cls.status,copy_review=credential(candidate))
        cls.value=compile_choreography(cls.experience,cls.plan,cls.copy,cls.motion,cls.bundle,cls.status)
        cls.fixture=read(ROOT/'creative/method-choreography/synthetic-peel.fixture.json')
        cls.peel=compile_synthetic_peel(cls.fixture)

    def validate(self,value=None,experience=None,status=None):
        return validate_choreography(self.value if value is None else value,
            self.experience if experience is None else experience,self.plan,self.copy,self.motion,self.bundle,
            self.status if status is None else status)

    def g01(self):
        b,s,old,_=copies.assets('G01',with_payoff=False,mode='worked_example')
        selection=old['replay_request']['selection'];app=synthetic_spans(b,s,selection)
        p=compile_plan(b,s,selection,mode='worked_example',contract_version='0.4.0',structure_input=app)
        e=realize_experience(None,None,p,b,s,allow_held_plan=True)
        value=compile_choreography(e,p,None,None,b,s,application=app,diagnostic=True)
        return value,e,p,b,s,app

    def audit_edit(self,edit,value=None):
        v=deepcopy(self.value if value is None else value);edit(v)
        return audit_choreography(v)

    def test_current_plan_and_experience_are_exactly_bound(self):
        b=self.value['binding'];self.assertEqual(b['pedagogy_plan_sha'],self.plan['plan_sha'])
        self.assertEqual(b['student_experience_sha'],self.experience['experience_sha'])
        self.assertEqual(b['student_final_copy_sha'],self.experience['final_copy_sha'])
        self.assertEqual(self.value['compilation_status'],'PASS');self.assertTrue(self.validate()['consumption_allowed'])

    def test_changed_frozen_teaching_source_invalidates_old_choreography(self):
        # Build a genuinely new synthetic source/analysis/credential together.
        # Mutating only the question must now fail at the upstream scope gate,
        # before a legitimate new frozen bundle can reach choreography checks.
        request=decisions.request(options={'A':'SYNTHETIC CHANGED SOURCE',
            'B':'SYNTHETIC beta','C':'SYNTHETIC gamma','D':'SYNTHETIC delta'})
        b,s,_=decisions.freeze(request)
        with self.assertRaises(ValueError):validate_choreography(self.value,self.experience,self.plan,self.copy,self.motion,b,s)

    def test_changed_question_cannot_freeze_unchanged_analysis(self):
        request=decisions.request();request['question']['options']['A']='SYNTHETIC CHANGED SOURCE'
        with self.assertRaisesRegex(ValueError,'Question signal scope differs'):
            decisions.freeze(request)

    def test_changed_plan_or_student_path_invalidates_old_choreography(self):
        p=deepcopy(self.plan);p['primary_action']['instruction']['text']='SYNTHETIC forged instruction'
        with self.assertRaises(ValueError):validate_choreography(self.value,self.experience,p,self.copy,self.motion,self.bundle,self.status)
        e=realize_experience(self.copy,self.motion,self.plan,self.bundle,self.status,options={'merge_collapse_payoff':False})
        with self.assertRaises(ValueError):self.validate(experience=e)

    def test_current_withdrawal_blocks_and_history_stays_readable(self):
        self.assertFalse(inspect_choreography(self.value)['consumption_allowed'])
        with self.assertRaises(ValueError):self.validate(status=seal({**deepcopy(self.status),'effective_status':'WITHDRAWN'}))
        with self.assertRaises(ValueError):validate_choreography(self.value,self.experience,self.plan,self.copy,self.motion,self.bundle,None)

    def test_each_operation_targets_existing_logical_objects(self):
        _,_,errors=self.audit_edit(lambda v:v['operations'][0]['target_objects'].append('some text'))
        self.assertIn('DANGLING_OPERATION_OBJECT',errors)

    def test_protected_source_cannot_be_removed_or_hidden(self):
        oid=next(o['object_id'] for o in self.value['object_catalog'] if o['protected'])
        _,_,errors=self.audit_edit(lambda v:v['states'][1]['object_states'].update({oid:'remove'}))
        self.assertIn('PROTECTED_OBJECT_MUTATION',errors)
        _,_,errors=self.audit_edit(lambda v:v['states'][1]['present_objects'].remove(oid))
        self.assertIn('PROTECTED_OBJECT_DISAPPEARED',errors)

    def test_deferred_span_cannot_be_irreversibly_removed(self):
        oid='synthetic-modifier-a'
        def edit(v):
            v['states'][1]['object_states'][oid]='remove';v['operations'][0]['reversibility']='irreversible'
        _,_,errors=self.audit_edit(edit,self.peel)
        self.assertIn('DEFERRED_IS_NOT_REMOVED',errors);self.assertIn('UNSUPPORTED_IRREVERSIBLE_ACTION',errors)

    def test_unresolved_candidates_cannot_be_resolved(self):
        oid=self.value['stop']['unresolved_objects'][0]
        _,_,errors=self.audit_edit(lambda v:v['states'][-1]['object_states'].update({oid:'resolved'}))
        self.assertIn('UNRESOLVED_OBJECT_RESOLVED',errors)

    def test_reducer_cannot_complete_decision(self):
        def edit(v):v['resolution']['output_role']='reducer';v['collapse']['decision_completion']=True
        _,_,errors=self.audit_edit(edit);self.assertIn('DECISION_COMPLETION_NOT_ALLOWED',errors)

    def test_locator_cannot_make_final_answer_lock(self):
        def edit(v):v['resolution']['output_role']='locator';v['resolution']['may_output_final_answer']=True;v['final_answer_allowed']=True
        _,_,errors=self.audit_edit(edit);self.assertIn('FINAL_ANSWER_LOCK_NOT_ALLOWED',errors)

    def test_local_four_to_three_preserves_remaining_unresolved(self):
        c=self.value['collapse'];a,b=[next(s for s in self.value['states'] if s['state_id']==c['transition'][k]) for k in ['from_state','to_state']]
        self.assertEqual(a['consequence']['active_candidate_count'],4);self.assertEqual(b['consequence']['active_candidate_count'],3)
        for oid in b['consequence']['active_candidate_objects']:
            self.assertEqual(b['object_states'][oid],'unresolved');self.assertIn(oid,self.value['stop']['unresolved_objects'])
        self.assertFalse(self.value['final_answer_allowed'])

    def test_g01_has_route_and_stop_but_never_fake_payoff(self):
        v,e,p,b,s,app=self.g01();self.assertEqual(v['compilation_status'],'PASS')
        self.assertEqual(v['availability']['status'],'HOLD');self.assertFalse(v['collapse']['supported']);self.assertIsNone(v['payoff_event'])
        self.assertTrue(signature_matches('G01',v['operations']));self.assertIn('PAYOFF_UNSUPPORTED',v['availability']['gaps'])
        self.assertFalse(validate_choreography(v,e,p,None,None,b,s,application=app)['consumption_allowed'])

    def test_g01_without_frozen_slot_annotation_reports_gap(self):
        v,e,p,b,s,app=self.g01()
        # The Plan itself binds the annotation; it cannot be silently omitted.
        with self.assertRaises(ValueError):compile_choreography(e,p,None,None,b,s,diagnostic=True)
        b,s,old,_=copies.assets('G01',with_payoff=False,mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',contract_version='0.4.0')
        e=realize_experience(None,None,p,b,s,allow_held_plan=True)
        v=compile_choreography(e,p,None,None,b,s,diagnostic=True)
        self.assertIn('ROUTING_SLOT_OR_EXISTING_ROUTE_UNAVAILABLE',v['availability']['gaps'])

    def test_collapse_exactly_binds_work_delta_and_reduction(self):
        c=self.value['collapse'];self.assertTrue(c['supported'])
        self.assertEqual(c['removed'],self.experience['work_delta']['removed_work'])
        self.assertEqual(c['deferred'],self.experience['work_delta']['deferred_work'])
        self.assertEqual(c['still_required'],self.experience['work_delta']['still_required_work'])
        self.assertEqual(c['work_delta_ref']['pointer'],'/work_delta')

    def test_fake_collapse_is_rejected(self):
        _,_,errors=self.audit_edit(lambda v:v['collapse'].update(before_ref=None))
        self.assertIn('FAKE_COLLAPSE_OR_PAYOFF',errors)
        changed=deepcopy(self.value);changed['collapse']['scope']='final_answer'
        with self.assertRaises(ValueError):self.validate(reseal(changed))

    def test_object_lineage_is_continuous_across_every_state(self):
        self.assertTrue(self.value['audit']['object_lineage_preserved'])
        for row in self.value['object_lineage']:
            self.assertEqual(len(row['states']),len(self.value['states']))
            self.assertEqual({s['content_sha'] for s in row['states']},{row['source_content_sha']})

    def test_carried_object_cannot_silently_change_content(self):
        _,_,errors=self.audit_edit(lambda v:v['object_lineage'][0]['states'][1].update(content_sha='0'*64))
        self.assertIn('OBJECT_LINEAGE_CONTENT_DRIFT',errors)
        v=deepcopy(self.value);v['object_catalog'][0]['source_content_sha']='0'*64
        with self.assertRaises(ValueError):self.validate(reseal(v))

    def test_relation_rewire_requires_own_existing_relation(self):
        self.assertTrue(any(r['kind']=='frozen_reviewed_relationship_assertion' for r in self.value['relation_catalog']))
        def edit(v):next(o for o in v['operations'] if o['verb']=='rewire')['relation_id']=None
        _,_,errors=self.audit_edit(edit);self.assertIn('REWIRE_REQUIRES_EXISTING_RELATION',errors)

    def test_peel_defers_tightens_and_restores_same_synthetic_spans(self):
        self.assertEqual([o['verb'] for o in self.peel['operations']],['peel','peel','tighten','restore','lock'])
        self.assertEqual(self.peel['states'][1]['object_states']['synthetic-modifier-a'],'defer')
        self.assertEqual(self.peel['states'][-1]['object_states']['synthetic-modifier-a'],'preserve')
        self.assertEqual(self.peel['states'][3]['consequence']['structural_groups'],[['synthetic-core-a','synthetic-core-b']])
        self.assertTrue(validate_synthetic_peel(self.peel,self.fixture)['status']=='PASS')
        self.assertEqual(self.peel['collapse']['removed'],[]);self.assertIsNone(self.peel['payoff_event'])

    def test_synthetic_peel_may_leave_reversible_deferral(self):
        v=compile_synthetic_peel(self.fixture,restore=False)
        self.assertEqual(v['stop']['deferred_objects'],['synthetic-modifier-a','synthetic-modifier-b'])
        self.assertTrue(v['audit']['reversibility_preserved'])
        self.assertFalse(validate_synthetic_peel(v,self.fixture,restore=False)['consumption_allowed'])

    def test_signature_label_swap_detects_physics_mismatch(self):
        self.assertTrue(signature_matches('R02',self.value['operations']));self.assertFalse(signature_matches('R01',self.value['operations']))
        _,risks,_=self.audit_edit(lambda v:v['binding'].update(method_id='G01'))
        self.assertIn('SIGNATURE_DISTINCTIVENESS_FAIL',risks)

    def test_detached_infograph_risk_is_detected(self):
        _,risks,_=self.audit_edit(lambda v:v['states'][1].update(reality_layer_present=False))
        self.assertIn('DETACHED_INFOGRAPH_RISK',risks)

    def test_whole_screen_reset_and_ppt_risks_are_detected(self):
        _,risks,_=self.audit_edit(lambda v:v['state_transitions'][0].update(carry_objects=[]))
        self.assertIn('PRESENTATION_RESET_RISK',risks);self.assertIn('PPT_MOTION_RISK',risks)

    def test_decorative_motion_has_no_cognitive_transition(self):
        def edit(v):v['states'][1]['consequence']=deepcopy(v['states'][0]['consequence'])
        _,risks,errors=self.audit_edit(edit)
        self.assertIn('DECORATIVE_CHOREOGRAPHY',risks);self.assertIn('DECORATIVE_CHOREOGRAPHY',errors)

    def test_relation_phase_label_alone_does_not_count_as_spatial_consequence(self):
        def edit(v):
            old=deepcopy(v['states'][1]['consequence'])
            old['relation_state']=v['states'][2]['consequence']['relation_state']
            v['states'][2]['consequence']=old
        _,risks,errors=self.audit_edit(edit)
        self.assertIn('DECORATIVE_CHOREOGRAPHY',risks);self.assertIn('DECLARED_CHANGE_NOT_REALIZED',errors)

    def test_r02_comparison_changes_bound_structure_without_actor_parsing(self):
        table={s['state_id']:s for s in self.value['states']}
        for tr in self.value['intervention']['transitions']:
            a,b=[table[tr[k]]['consequence'] for k in ['from_state','to_state']]
            self.assertNotEqual(a['structural_groups'],b['structural_groups'])
        self.assertFalse(self.value['source']['text_parsing_performed'])

    def test_schema_rejects_ae_tts_or_new_teaching_text(self):
        for key,value in [('camera',105),('speed_factor',1.04),('new_answer','B'),('music','Chopin')]:
            v=deepcopy(self.value);v['operations'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):inspect_choreography(reseal(v))
        self.assertFalse(self.value['source']['text_parsing_performed']);self.assertFalse(self.value['source']['new_teaching_text_created'])

    def test_temporal_signature_has_only_qualitative_characters(self):
        v=deepcopy(self.value);v['operations'][0]['temporal_character']='12 frames'
        with self.assertRaises(ValueError):inspect_choreography(reseal(v))
        self.assertTrue(all(set(t)=={'operation_id','character'} for t in self.value['temporal_signature']))

    def test_stop_cannot_be_omitted_or_upgraded(self):
        v=deepcopy(self.value);del v['stop']
        with self.assertRaises(ValueError):inspect_choreography(reseal(v))
        _,_,errors=self.audit_edit(lambda v:v['stop'].update(scope='full_solution'))
        self.assertIn('STOP_SCOPE_OR_UNRESOLVED_LOST',errors)

    def test_human_taste_and_all_public_gates_stay_pending(self):
        self.assertEqual(self.value['human_taste_review'],'PENDING');self.assertFalse(self.value['public_render_ready'])
        self.assertEqual(self.value['release_state'],{'teaching':'HOLD','source_display':'HOLD','editorial':'HOLD'})
        self.assertFalse(self.value['semantic_truth_certification'])

    def test_runtime_does_not_write_or_import_solver_adobe_or_voice(self):
        before=sha([self.bundle,self.status,self.plan,self.experience,self.copy,self.motion])
        self.validate();self.assertEqual(before,sha([self.bundle,self.status,self.plan,self.experience,self.copy,self.motion]))
        for path in (ROOT/'method_choreography').glob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'));imports=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):imports.extend(a.name.split('.')[0] for a in n.names)
                elif isinstance(n,ast.ImportFrom) and n.module:imports.append(n.module.split('.')[0])
            self.assertFalse(set(imports)&{'core','answer_engine','creative_os','ae_production','premiere_production','voicepacks','narration_performance'})

    def test_same_inputs_reproduce_complete_choreography_and_projection(self):
        other=compile_choreography(self.experience,self.plan,self.copy,self.motion,self.bundle,self.status)
        self.assertEqual(other,self.value)
        projection=project_choreography(self.value,self.experience,self.plan,self.copy,self.motion,self.bundle,self.status)
        self.assertTrue(projection['consumption_allowed'])
        self.assertTrue(validate_projection(projection,self.value,self.experience,self.plan,self.copy,self.motion,self.bundle,self.status)['consumption_allowed'])

    def test_transport_time_does_not_change_semantic_choreography_hash(self):
        p=compile_plan(self.bundle,self.status,self.selection,mode='worked_example',generated_at='OTHER SYNTHETIC TIME',
            boundary_review=self.plan['replay_request']['boundary_review'],contract_version='0.4.0')
        c=copy_projection(p,self.bundle,self.status);m=motion_projection(p,self.bundle,self.status)
        candidate=realize_experience(c,m,p,self.bundle,self.status)
        e=realize_experience(c,m,p,self.bundle,self.status,copy_review=credential(candidate))
        v=compile_choreography(e,p,c,m,self.bundle,self.status)
        self.assertEqual(self.value['choreography_sha'],v['choreography_sha'])
        self.assertNotEqual(self.value['envelope_sha'],v['envelope_sha'])

    def test_changed_rights_status_does_not_reuse_old_release(self):
        status=seal({**deepcopy(self.status),'source_sha':'0'*64})
        with self.assertRaises(ValueError):self.validate(status=status)
        with self.assertRaises(ValueError):project_choreography(self.value,self.experience,self.plan,self.copy,self.motion,self.bundle,status)

    def test_hold_requires_explicit_diagnostic_and_blocks_creative_production(self):
        e=realize_experience(self.copy,self.motion,self.plan,self.bundle,self.status)
        with self.assertRaises(ValueError):compile_choreography(e,self.plan,self.copy,self.motion,self.bundle,self.status)
        v=compile_choreography(e,self.plan,self.copy,self.motion,self.bundle,self.status,diagnostic=True)
        with self.assertRaises(ValueError):project_choreography(v,e,self.plan,self.copy,self.motion,self.bundle,self.status)
        pr=project_choreography(v,e,self.plan,self.copy,self.motion,self.bundle,self.status,diagnostic=True)
        self.assertFalse(pr['consumption_allowed']);self.assertTrue(pr['diagnostic_only'])

    def test_six_signatures_remain_specs_and_share_brand_grammar(self):
        physics,recipes,_=registry();self.assertEqual(len(physics['families']),6);self.assertEqual(len(recipes['recipes']),6)
        self.assertEqual({r['method_id'] for r in recipes['recipes'] if r['runtime']=='bound_v04_replay'},{'R02','G01'})
        self.assertEqual(self.value['signature']['brand_principles'],['focus','carry','transform','settle','seal'])

    def test_legacy_adapter_preserves_old_status_without_faking_upgrade(self):
        p=compile_plan(self.bundle,self.status,self.selection,mode='worked_example',generated_at='SYNTHETIC')
        c=copy_projection(p,self.bundle,self.status);v=realize(c,p,self.bundle,self.status)
        before=sha(v);report=analyze_legacy(v,p,c,self.bundle,self.status)
        self.assertEqual(before,sha(v));self.assertEqual(report['legacy_availability'],v['availability'])
        self.assertFalse(report['new_work_delta_created']);self.assertFalse(report['new_experience_created'])
        self.assertFalse(report['approval_inherited']);self.assertFalse(report['choreography_production_allowed'])

    def test_cli_compiles_validates_projects_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            for key,v in [('experience',self.experience),('plan',self.plan),('copy_handoff',self.copy),('motion_handoff',self.motion),('bundle',self.bundle),('status',self.status)]:write(path/(key+'.json'),v)
            req={k:k+'.json' for k in ['experience','plan','copy_handoff','motion_handoff','bundle','status']};req['output']='choreography.json'
            write(path/'request.json',req)
            with patch('sys.argv',['method_choreography','compile',str(path/'request.json')]),contextlib.redirect_stdout(io.StringIO()):main()
            req['choreography']='choreography.json';write(path/'request.json',req)
            with patch('sys.argv',['method_choreography','validate',str(path/'request.json')]),contextlib.redirect_stdout(io.StringIO()):main()
            with patch('sys.argv',['method_choreography','compile',str(path/'request.json')]),self.assertRaises(ValueError):main()
            req['output']='projection.json';write(path/'request.json',req)
            with patch('sys.argv',['method_choreography','project',str(path/'request.json')]),contextlib.redirect_stdout(io.StringIO()):main()
            self.assertTrue(read(path/'projection.json')['consumption_allowed'])


if __name__=='__main__':unittest.main()
