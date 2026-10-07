"""SYNTHETIC work/state/compatibility controls, never real learner evidence."""
import ast
from copy import deepcopy
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tests import test_mechanical_payoff as decision_fixtures
from tests import test_student_pov as copy_fixtures
from tests.test_boundary_risk_review import synthetic_review
from tests import test_pedagogy as pedagogy_fixtures
from video_contracts import ROOT, pointer, read, seal, sha, write
from video_contracts.method_application import export_application
from pedagogy import compile_plan, validate_plan, inspect_historical, copy_projection, motion_projection, validate_handoff
from pedagogy import inspect_historical_handoff as inspect_any_handoff
from pedagogy.__main__ import main
from pedagogy.compiler import plan_semantics
from pedagogy.handoff_v04 import inspect_historical_handoff
from pedagogy.structure import validate_structure
from pedagogy.v04 import validate_compression_audit, _actions
from pedagogy.work_delta import project_work_delta
from pedagogy.sources import FrozenSource


def reseal(plan):
    value=deepcopy(plan); value['plan_sha']=sha(plan_semantics(value)); value['plan_id']='pedagogy:'+value['plan_sha']
    return seal(value)


def synthetic_spans(bundle, status, selection):
    """These role labels are input controls, not recognized English syntax."""
    ai=next(i for i,a in enumerate(bundle['analysis']['execution_trace']) if a['execution_id'] in selection['action_ids'])
    action=bundle['analysis']['execution_trace'][ai]; region=deepcopy(action['evidence'][0])
    spans=[]
    for name, role, start, end in [('subject','core',0,6),('modifier','modifier',6,11),
                                  ('predicate','predicate',11,13),('object','slot',13,16)]:
        spans.append({'span_id':'SYNTHETIC-'+name,'semantic_role':role,'field':'passage','start':start,'end':end,
            'quote':bundle['source_snapshot']['passage'][start:end],
            'assertion':{'field':'concrete_action','quote':action['concrete_action']}})
    annotation={'action_index':ai,'review_indices':[0],'source_region':region,'spans':spans,
        'reduced_span_ids':['SYNTHETIC-subject','SYNTHETIC-predicate','SYNTHETIC-object'],
        'deferred_span_ids':['SYNTHETIC-modifier'],'protected_span_ids':['SYNTHETIC-subject','SYNTHETIC-predicate'],
        'relations':[{'from_span_id':'SYNTHETIC-subject','to_span_ids':['SYNTHETIC-predicate','SYNTHETIC-object'],
                      'assertion':{'field':'concrete_action','quote':action['concrete_action']}}]}
    return export_application(bundle,status,annotation,'SYNTHETIC')


class PedagogyV04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle,cls.status,cls.selection=decision_fixtures.freeze()

    def plan(self,mode='first_touch',**kwargs):
        base=compile_plan(self.bundle,self.status,self.selection,mode=mode,generated_at='SYNTHETIC')
        review=synthetic_review(base,self.bundle)
        return compile_plan(self.bundle,self.status,self.selection,mode=mode,boundary_review=review,
                            generated_at='SYNTHETIC',contract_version='0.4.0',**kwargs)

    def test_v03_history_and_current_downstream_are_byte_compatible(self):
        old=compile_plan(self.bundle,self.status,self.selection,mode='worked_example',generated_at='SYNTHETIC')
        before=deepcopy(old); inspect=inspect_historical(old)
        self.assertEqual(inspect['contract_version'],'0.3.0'); self.assertFalse(inspect['consumption_allowed'])
        self.assertTrue(validate_plan(old,self.bundle,self.status)['consumption_allowed'])
        cp=copy_projection(old,self.bundle,self.status)
        self.assertEqual(cp['schema_version'],'0.3.0')
        self.assertFalse(inspect_any_handoff(cp)['consumption_allowed'])
        self.plan(); self.assertEqual(old,before)

    def test_v03_cannot_be_relabelled_or_consumed_as_v04(self):
        old=compile_plan(self.bundle,self.status,self.selection,mode='worked_example')
        with self.assertRaisesRegex(ValueError,'Historical Pedagogy contract'):
            validate_plan(old,self.bundle,self.status,required_version='0.4.0')
        old.update(schema_version='0.4.0',compiler_version='0.4.0')
        with self.assertRaises(ValueError): validate_plan(reseal(old),self.bundle,self.status)

    def test_repeat_hash_and_changed_frozen_asset_invalidates_v04(self):
        one=self.plan(); two=self.plan()
        self.assertEqual(one,two)
        req=decision_fixtures.request(); req['question']['options']['A']='SYNTHETIC revised A'
        b,s,_=decision_fixtures.freeze(req)
        with self.assertRaises(ValueError): validate_plan(one,b,s)
        self.assertFalse(inspect_historical(one)['current_upstream_verified'])

    def test_withdrawal_rights_and_dependency_changes_block_consumption(self):
        p=self.plan(); cp=copy_projection(p,self.bundle,self.status)
        for field,value in [('effective_status','WITHDRAWN'),('source_sha','0'*64),('semantic_binding_sha','0'*64)]:
            status=deepcopy(self.status); status[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): validate_handoff(cp,p,self.bundle,seal(status))
        for kind in ('actions','reviews','evidence','decisions'):
            status=deepcopy(self.status)
            aid=self.bundle['analysis']['execution_trace'][0]['evidence_ids'][0] if kind=='evidence' else status['lifecycle'][kind][0]['artifact_id']
            next(row for row in status['lifecycle'][kind] if row['artifact_id']==aid)['status']='withdrawn'
            with self.subTest(kind=kind),self.assertRaises(ValueError): validate_plan(p,self.bundle,seal(status))

    def test_first_touch_has_one_bound_primary_action_and_seven_parts(self):
        p=self.plan(); self.assertEqual(p['availability']['status'],'READY')
        self.assertEqual(p['primary_action_count'],1); self.assertEqual(p['supporting_actions'],[])
        self.assertEqual(set(p['first_touch']),{'pain','first_signal','first_action','judgment_point','immediate_output','stop','memory_phrase'})
        self.assertEqual(p['primary_action']['action_ref'],p['truth_guard']['action_refs'][0])
        self.assertFalse(p['first_touch_audit']['student_understanding_certified'])

    def test_multiple_independent_actions_cannot_be_hidden_as_supporting(self):
        b,s,selection=decision_fixtures.freeze(decision_fixtures.request(second='R02'))
        selection['action_ids'].append('synthetic-cut-C')
        p=compile_plan(b,s,selection,contract_version='0.4.0')
        self.assertEqual(p['primary_action_count'],2); self.assertIsNone(p['primary_action'])
        self.assertIn('FIRST_TOUCH_ONE_PRIMARY_ACTION_REQUIRED',p['availability']['blockers'])
        self.assertEqual(p['supporting_actions'],[])
        with self.assertRaises(ValueError): copy_projection(p,b,s)

    def test_supporting_action_classification_follows_frozen_dependencies(self):
        # A pure SYNTHETIC dependency graph, not a new English method contract.
        payload={'actions':[{'execution_id':'SYNTHETIC-support','input_artifact_ids':[], 'evidence':[], 'output':{}},
                            {'execution_id':'SYNTHETIC-primary','input_artifact_ids':['SYNTHETIC-support'], 'evidence':[], 'output':{}}]}
        source=SimpleNamespace(actions=payload['actions'],action_paths=['/actions/0','/actions/1'],
            ref=lambda path:{'asset_id':'SYNTHETIC','pointer':path,'sha':sha(pointer(payload,path))})
        primary,supporting,count=_actions(source,{'first_action':{'text':'SYNTHETIC first cut'}})
        self.assertEqual(count,1); self.assertEqual(primary['action_id'],'SYNTHETIC-primary')
        self.assertEqual([a['action_id'] for a in supporting],['SYNTHETIC-support'])
        p=self.plan(); changed=deepcopy(p)
        changed['supporting_actions']=[deepcopy(changed['primary_action'])]
        with self.assertRaises(ValueError): validate_plan(reseal(changed),self.bundle,self.status)

    def test_missing_baseline_is_null_hold_and_does_not_invent_savings(self):
        b,s,old,_=copy_fixtures.assets('G01',with_payoff=False,mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',contract_version='0.4.0')
        self.assertIsNone(p['work_delta']['baseline_work']); self.assertEqual(p['availability']['status'],'HOLD')
        self.assertIn('BASELINE_WORK_UNSUPPORTED',p['availability']['gaps'])
        self.assertIn('PAYOFF_UNSUPPORTED',p['availability']['gaps'])
        self.assertIn('COGNITIVE_RELIEF_UNAVAILABLE',p['availability']['gaps'])
        self.assertEqual(p['work_delta']['removed_work'],[])
        self.assertIsNone(p['payoff']['allowed_claim']); self.assertIsNone(p['payoff']['payoff_scope'])

    def test_removed_work_is_bound_and_local_candidate_delta_remains_four_to_three(self):
        p=self.plan(); d=p['work_delta']
        self.assertEqual([w['work_id'] for w in d['removed_work']],['current_candidate_check:D'])
        self.assertTrue(d['removed_work'][0]['source_refs']); self.assertTrue(d['removed_work'][0]['reopen_on_upstream_change'])
        self.assertEqual(d['deferred_work'],[])
        self.assertTrue({'current_candidate_check:A','current_candidate_check:B','current_candidate_check:C'} <= {w['work_id'] for w in d['still_required_work']})
        self.assertEqual(p['cognitive_load_projection']['before']['candidate_count'],4)
        self.assertEqual(p['cognitive_load_projection']['after']['candidate_count'],3)
        self.assertFalse(p['cognitive_load_projection']['psychological_measurement'])

    def test_deferred_work_cannot_be_promoted_to_removed(self):
        b,s,old,_=copy_fixtures.assets(mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',fields=old['replay_request']['fields'],contract_version='0.4.0')
        self.assertEqual([r['work_id'] for r in p['work_delta']['deferred_work']],['word_form'])
        work_objects=[o for o in p['cognitive_structure']['objects'] if o['kind']=='reviewed_work_unit']
        self.assertEqual(len(work_objects),len(p['work_delta']['removed_work'])+len(p['work_delta']['deferred_work'])+len(p['work_delta']['still_required_work']))
        word=next(o for o in work_objects if o['source_work_id']=='word_form')
        self.assertEqual(word['state'],'defer'); self.assertEqual(word['restore_state'],'preserve')
        changed=deepcopy(p); changed['work_delta']['removed_work']+=changed['work_delta']['deferred_work']; changed['work_delta']['deferred_work']=[]
        with self.assertRaises(ValueError): validate_plan(reseal(changed),b,s)
        base=deepcopy(old); base['payoff']['reviewed_support']['record']['cognitive_work']['removed'].append('word_form')
        delta,projection=project_work_delta(FrozenSource(b,s,old['replay_request']['selection']),base)
        self.assertIsNone(projection); self.assertEqual(delta['status'],'HOLD')

    def test_still_required_work_cannot_be_dropped_by_copy_or_motion(self):
        p=self.plan()
        for factory in (copy_projection,motion_projection):
            h=factory(p,self.bundle,self.status); h['work_delta']['still_required_work'].pop()
            with self.subTest(factory=factory),self.assertRaises(ValueError): validate_handoff(seal(h),p,self.bundle,self.status)

    def test_local_payoff_cannot_upgrade_to_whole_question_or_answer(self):
        p=self.plan(); self.assertEqual(p['payoff']['payoff_scope'],'candidate_set')
        for edit in [lambda v:v['payoff'].update(payoff_scope='whole_question'),
                     lambda v:v['cognitive_reduction'].update(decision_completion=True),
                     lambda v:v['answer_scope'].update(answer='A',may_output_final_answer=True)]:
            changed=deepcopy(p); edit(changed)
            with self.subTest(edit=edit),self.assertRaises(ValueError): validate_plan(reseal(changed),self.bundle,self.status)

    def test_reducer_partition_and_locator_never_gain_decision_completion(self):
        for mid in ('F01','R12'):
            b,s,old,_=copy_fixtures.assets(mid,mode='worked_example')
            p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',fields=old['replay_request']['fields'],contract_version='0.4.0')
            self.assertFalse(p['cognitive_reduction']['decision_completion']); self.assertFalse(p['answer_scope']['may_output_final_answer'])
            if mid=='F01': self.assertEqual(p['availability']['status'],'HOLD')
            else: self.assertEqual(p['payoff']['payoff_scope'],'evidence_scope')

    def test_tell_now_cannot_disappear_without_complete_coverage(self):
        p=self.plan(); self.assertTrue(p['boundary_presentations'])
        p['boundary_presentations'][0]['coverage']['parts'].pop()
        with self.assertRaises(ValueError): validate_plan(reseal(p),self.bundle,self.status)

    def test_semantic_stop_cannot_be_engine_only(self):
        p=self.plan(); stop=p['truth_guard']['action_stop_refs'][0]
        item=next(r for r in p['compression_audit']['item_bindings'] if r['source_ref']==stop)
        self.assertNotEqual(item['disposition'],'engine_only')
        changed=deepcopy(p); changed['boundaries']['engine_only'].append({'item_id':'fake-stop','field':'stop','disclosure_tier':'ENGINE_ONLY','reason':'hide'})
        with self.assertRaises(ValueError): validate_plan(reseal(changed),self.bundle,self.status)

    def test_merged_boundaries_have_review_binding_and_no_spoken_readout_requirement(self):
        p=self.plan(); presentation=p['boundary_presentations'][0]
        self.assertGreater(len(presentation['coverage']['source_items']),1)
        self.assertIn('pedagogy-boundary-review:',presentation['coverage']['review_ref']['asset_id'])
        self.assertFalse(presentation['spoken_readout_required'])
        p['boundary_presentations'][0]['coverage']['review_ref']['sha']='0'*64
        with self.assertRaises(ValueError): validate_plan(reseal(p),self.bundle,self.status)

    def test_protected_objects_cannot_be_removed_by_projection(self):
        p=self.plan(); structure=deepcopy(p['cognitive_structure'])
        obj=next(o for o in structure['objects'] if o['protected']); obj['state']='remove'
        with self.assertRaisesRegex(ValueError,'Protected'): validate_structure(structure)

    def test_synthetic_peel_defer_restore_preserves_subject_predicate_object(self):
        b,s,old,_=copy_fixtures.assets(mode='worked_example')
        selection=old['replay_request']['selection']; app=synthetic_spans(b,s,selection)
        p=compile_plan(b,s,selection,mode='worked_example',fields=old['replay_request']['fields'],structure_input=app,contract_version='0.4.0')
        structure=p['cognitive_structure']; self.assertFalse(structure['syntax_recognition_performed'])
        modifier=next(o for o in structure['objects'] if o['kind']=='reviewed_span_modifier')
        self.assertEqual(modifier['state'],'defer'); self.assertEqual(modifier['reversibility'],'reversible')
        self.assertEqual(modifier['restore_state'],'preserve'); self.assertNotIn(modifier['object_id'],structure['removable_objects'])
        self.assertTrue(any(o['kind']=='reviewed_span_predicate' and o['protected'] for o in structure['objects']))
        self.assertTrue(any(o['kind']=='reviewed_span_core' and o['protected'] for o in structure['objects']))
        self.assertTrue(any(o['kind']=='reviewed_span_slot' and o['state']=='focus' for o in structure['objects']))
        self.assertTrue(validate_plan(p,b,s)['consumption_allowed'])
        modifier['restore_state']=None
        with self.assertRaisesRegex(ValueError,'restoration'): validate_structure(structure)

    def test_synthetic_background_is_reversible_and_is_not_elimination(self):
        p=self.plan(); structure=deepcopy(p['cognitive_structure'])
        obj=next(o for o in structure['objects'] if o['kind']=='candidate_eligibility' and o['state']=='unresolved')
        structure['preserved_objects'].remove(obj['object_id']); structure['backgroundable_objects'].append(obj['object_id'])
        obj.update(state='background',reversibility='reversible',restore_state='preserve')
        validate_structure(structure)
        self.assertNotIn(obj['object_id'],structure['removable_objects'])
        obj['reversibility']='irreversible'
        with self.assertRaises(ValueError): validate_structure(structure)

    def test_attention_transition_and_motion_reject_ae_parameters_or_new_copy(self):
        p=self.plan(); structure=deepcopy(p['cognitive_structure'])
        structure['attention_transition']['camera_zoom']=115
        with self.assertRaisesRegex(ValueError,'AE parameters'): validate_structure(structure)
        h=motion_projection(p,self.bundle,self.status); h['new_teaching_text']='SYNTHETIC unsupported new rule'
        with self.assertRaises(ValueError): validate_handoff(seal(h),p,self.bundle,self.status)
        def has_text(value):
            if isinstance(value,dict): return 'text' in value or any(has_text(v) for v in value.values())
            if isinstance(value,list): return any(has_text(v) for v in value)
            return False
        self.assertFalse(has_text(motion_projection(p,self.bundle,self.status)))

    def test_compression_audit_conserves_every_source_item_and_rejects_loss(self):
        p=self.plan(); audit=p['compression_audit']; validate_compression_audit(audit)
        self.assertEqual(audit['omitted'],[])
        self.assertEqual(len(audit['source_truth_items']),len(audit['item_bindings']))
        changed=deepcopy(audit); changed['presented_now'].pop()
        with self.assertRaisesRegex(ValueError,'conserve'): validate_compression_audit(changed)
        changed=deepcopy(audit); changed['engine_only'].append(changed['presented_now'][0])
        with self.assertRaises(ValueError): validate_compression_audit(changed)

    def test_unsupported_savings_never_enter_allowed_claim(self):
        p=self.plan(); claim=p['payoff']['allowed_claim']['text']
        self.assertNotIn(claim,[r['claim_key'] for r in p['work_delta']['unsupported_savings']])
        base=compile_plan(self.bundle,self.status,self.selection,mode='worked_example')
        base['payoff']['reviewed_support']['record']['allowed_claim']='省一半时间'
        delta,projection=project_work_delta(FrozenSource(self.bundle,self.status,self.selection),base)
        self.assertIsNone(projection); self.assertIn('PAYOFF_UNSUPPORTED:unsupported_savings_cannot_be_allowed_claim',delta['gaps'])
        for claim in ('认知负荷下降37%','省50%时间'):
            base['payoff']['reviewed_support']['record']['allowed_claim']=claim
            delta,projection=project_work_delta(FrozenSource(self.bundle,self.status,self.selection),base)
            self.assertIsNone(projection)

    def test_human_taste_pending_and_all_release_gates_unchanged(self):
        p=self.plan(); self.assertEqual(p['human_pedagogy_taste']['status'],'PENDING')
        self.assertFalse(p['human_pedagogy_taste']['self_signed']); self.assertFalse(p['public_render_ready'])
        self.assertEqual(p['release_state'],{'teaching':'HOLD','source_display':'HOLD','editorial':'HOLD'})
        self.assertFalse(p['semantic_review']['independent_human_certified'])
        p['human_pedagogy_taste'].update(status='PASS',first_action_clear=True)
        with self.assertRaises(ValueError): validate_plan(reseal(p),self.bundle,self.status)

    def test_new_handoff_is_inspectable_but_requires_current_source_and_v04_adapter(self):
        p=self.plan()
        for factory in (copy_projection,motion_projection):
            handoff=factory(p,self.bundle,self.status)
            self.assertFalse(inspect_historical_handoff(handoff)['consumption_allowed'])
            self.assertEqual(validate_handoff(handoff,p,self.bundle,self.status,required_version='0.4.0')['status'],'PASS')
            self.assertNotIn('teaching_risk',handoff); self.assertNotIn('truth_guard',handoff)
            with self.assertRaises(ValueError): validate_handoff(handoff,p,self.bundle,self.status,required_version='0.3.0')
        motion=motion_projection(p,self.bundle,self.status)
        self.assertTrue(all(isinstance(w,str) for w in motion['work_delta']['still_required_work']))
        self.assertNotIn('displayed_expression',motion['boundary_obligations'][0]['coverage'])
        for rid,ref in motion['reference_catalog'].items(): self.assertEqual(rid,'ref:'+sha(ref)[:24])
        broken=deepcopy(motion); broken['reference_catalog'].pop(next(iter(broken['reference_catalog'])))
        with self.assertRaisesRegex(ValueError,'Dangling'): inspect_historical_handoff(seal(broken))
        broken=deepcopy(motion); next(iter(broken['reference_catalog'].values()))['sha']='0'*64
        with self.assertRaisesRegex(ValueError,'catalog hash'): inspect_historical_handoff(seal(broken))

    def test_v04_cli_compile_validate_handoff_inspect_and_no_history_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); mode='first_touch'
            base=compile_plan(self.bundle,self.status,self.selection,mode=mode)
            for name,value in [('bundle',self.bundle),('status',self.status),('review',synthetic_review(base,self.bundle))]:
                write(root/(name+'.json'),value)
            request={'bundle':'bundle.json','status':'status.json','selection':self.selection,'mode':mode,
                     'contract_version':'0.4.0','boundary_review':'review.json','output':'plan.json'}
            write(root/'request.json',request)
            with patch('sys.argv',['pedagogy','compile',str(root/'request.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            before=(root/'plan.json').read_bytes()
            with patch('sys.argv',['pedagogy','compile',str(root/'request.json')]),self.assertRaises(ValueError): main()
            self.assertEqual(before,(root/'plan.json').read_bytes())
            write(root/'handoff.json',{'bundle':'bundle.json','status':'status.json','plan':'plan.json','contract_version':'0.4.0','copy_output':'copy.json','motion_output':'motion.json'})
            with patch('sys.argv',['pedagogy','handoff',str(root/'handoff.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            write(root/'inspect.json',{'plan':'plan.json'})
            with patch('sys.argv',['pedagogy','inspect',str(root/'inspect.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            write(root/'inspect-handoff.json',{'handoff':'motion.json'})
            with patch('sys.argv',['pedagogy','inspect-handoff',str(root/'inspect-handoff.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            write(root/'validate.json',{'bundle':'bundle.json','status':'status.json','plan':'plan.json','contract_version':'0.4.0'})
            with patch('sys.argv',['pedagogy','validate',str(root/'validate.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            self.assertEqual(read(root/'copy.json')['schema_version'],'0.4.0')

    def test_generation_time_and_structural_transport_do_not_change_semantic_hash(self):
        p=self.plan(); request=p['replay_request']
        next_plan=compile_plan(self.bundle,self.status,self.selection,mode=p['mode'],boundary_review=request['boundary_review'],
                               generated_at='other time',contract_version='0.4.0')
        self.assertEqual(p['plan_sha'],next_plan['plan_sha']); self.assertNotEqual(p['envelope_sha'],next_plan['envelope_sha'])
        b,s,old,_=copy_fixtures.assets(mode='worked_example'); sel=old['replay_request']['selection']
        app=synthetic_spans(b,s,sel)
        one=compile_plan(b,s,sel,mode='worked_example',fields=old['replay_request']['fields'],structure_input=app,contract_version='0.4.0')
        app['generated_at']='new transport'; app=seal(app)
        two=compile_plan(b,s,sel,mode='worked_example',fields=old['replay_request']['fields'],structure_input=app,contract_version='0.4.0')
        self.assertEqual(one['plan_sha'],two['plan_sha'])

    def test_runtime_isolation_and_truth_inputs_registry_are_unchanged(self):
        protected=[p for folder in ('core','method-registry','answer_engine') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        before={str(p):p.read_bytes() for p in protected}; frozen=sha([self.bundle,self.status])
        p=self.plan(); validate_plan(p,self.bundle,self.status)
        self.assertEqual(frozen,sha([self.bundle,self.status]))
        self.assertEqual(before,{str(p):p.read_bytes() for p in protected})
        for path in (ROOT/'pedagogy').glob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            names=[node.module or '' for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
            self.assertFalse(any(n.startswith(('answer_engine','core','student_pov','ae_production','premiere_production','voicepacks','renderers')) for n in names))


if __name__=='__main__': unittest.main()
