"""SYNTHETIC experience controls; no real learner, voice or teaching Review."""
import ast
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_mechanical_payoff as decisions
from tests import test_student_pov as copy_fixtures
from tests.test_boundary_risk_review import synthetic_review
from video_contracts import ROOT,read,write,seal,sha
from pedagogy import compile_plan,copy_projection,motion_projection
from student_pov import realize,realize_experience,validate_experience,validate_copy,inspect_historical
from student_pov.experience import experience_semantics,final_payload,pedagogy_ref
from student_pov.experience_qa import audit_experience,tone_lint
from student_pov.__main__ import main


def reseal(value):
    value=deepcopy(value); value['script_sha']=sha(value['beats']); value['final_copy_sha']=sha(final_payload(value))
    value['experience_sha']=sha(experience_semantics(value)); value['experience_id']='student-experience:'+value['experience_sha']
    return seal(value)


def credential(value):
    return {'schema_version':'0.4.0','status':'pass','reviewer':'SYNTHETIC external Copy check, not a learner',
        'reviewer_kind':'ai_host','source_plan_sha':value['source_pedagogy_plan']['plan_sha'],
        'script_sha':value['script_sha'],'final_copy_sha':value['final_copy_sha'],
        'checks':{'semantic_fidelity':'pass','natural_speech':'pass','layer_division':'pass'}}


class StudentExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle,cls.status,cls.selection=decisions.freeze()
        base=compile_plan(cls.bundle,cls.status,cls.selection,mode='worked_example',generated_at='SYNTHETIC')
        cls.plan=compile_plan(cls.bundle,cls.status,cls.selection,mode='worked_example',generated_at='SYNTHETIC',
            boundary_review=synthetic_review(base,cls.bundle),contract_version='0.4.0')
        cls.copy=copy_projection(cls.plan,cls.bundle,cls.status); cls.motion=motion_projection(cls.plan,cls.bundle,cls.status)

    def experience(self,**kwargs):
        return realize_experience(self.copy,self.motion,self.plan,self.bundle,self.status,**kwargs)

    def view(self):
        view=deepcopy(self.copy); view['cognitive_structure']=deepcopy(self.plan['cognitive_structure'])
        return view

    def line(self,text,path): return {'text':text,'pedagogy_refs':[pedagogy_ref(self.plan,path)]}

    def test_current_source_and_plan_changes_invalidate_experience(self):
        v=self.experience(); request=decisions.request(options={'A':'SYNTHETIC changed literal',
            'B':'SYNTHETIC beta','C':'SYNTHETIC gamma','D':'SYNTHETIC delta'})
        b,s,_=decisions.freeze(request)
        with self.assertRaises(ValueError): validate_experience(v,self.copy,self.motion,self.plan,b,s)
        changed=deepcopy(self.plan); changed['primary_action']['instruction']['text']='SYNTHETIC forged instruction'
        with self.assertRaises(ValueError): validate_experience(v,self.copy,self.motion,changed,self.bundle,self.status)

    def test_upstream_withdrawal_blocks_current_consumer_but_history_remains_readable(self):
        v=self.experience(); status=seal({**deepcopy(self.status),'effective_status':'WITHDRAWN'})
        self.assertFalse(inspect_historical(v)['consumption_allowed'])
        with self.assertRaises(ValueError): validate_experience(v,self.copy,self.motion,self.plan,self.bundle,status)

    def test_same_plan_generates_stable_curve_and_hashes(self):
        a=self.experience(); b=self.experience(); self.assertEqual(a,b)
        self.assertEqual(a['compilation_status'],'PASS'); self.assertEqual(len(a['beats']),6)
        self.assertEqual([r['stage'] for r in a['experience_curve']],['PAIN','FOCUS','ACT','TENSION','COLLAPSE','PAYOFF','STOP','MEMORY'])
        self.assertFalse(a['timing']['absolute_timing_assigned'])
        plan=compile_plan(self.bundle,self.status,self.selection,mode='worked_example',generated_at='other transport',
            boundary_review=self.plan['replay_request']['boundary_review'],contract_version='0.4.0')
        c=copy_projection(plan,self.bundle,self.status); m=motion_projection(plan,self.bundle,self.status)
        again=realize_experience(c,m,plan,self.bundle,self.status)
        self.assertEqual(a['experience_sha'],again['experience_sha']); self.assertNotEqual(a['envelope_sha'],again['envelope_sha'])

    def test_g01_unsupported_payoff_has_no_scene_and_remains_hold(self):
        b,s,old,_=copy_fixtures.assets('G01',with_payoff=False,mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',contract_version='0.4.0')
        v=realize_experience(None,None,p,b,s,allow_held_plan=True)
        self.assertEqual(v['availability']['status'],'HOLD'); self.assertEqual(v['experience_kind'],'action_demo')
        self.assertFalse(v['collapse']['supported']); self.assertIsNone(v['collapse']['scope'])
        self.assertNotIn('PAYOFF',[r['stage'] for r in v['experience_curve']]); self.assertNotIn('COLLAPSE',[r['stage'] for r in v['experience_curve']])
        self.assertIn('PAYOFF_UNSUPPORTED',v['availability']['gaps']); self.assertEqual(v['work_delta']['removed_work'],[])
        self.assertFalse(validate_experience(v,None,None,p,b,s)['consumption_allowed'])
        with self.assertRaises(ValueError): realize_experience(None,None,p,b,s)

    def test_r02_local_four_to_three_never_outputs_final_answer(self):
        v=self.experience(); self.assertEqual(v['collapse']['scope'],'candidate_set')
        self.assertEqual(v['collapse']['before_state']['objects'],['A','B','C','D'])
        self.assertEqual(v['collapse']['after_state']['objects'],['A','B','C'])
        self.assertFalse(v['answer_permission']['may_output_final_answer']); self.assertIsNone(v['answer_permission']['answer'])
        v['collapse']['scope']='whole_question'
        with self.assertRaises(ValueError): validate_experience(reseal(v),self.copy,self.motion,self.plan,self.bundle,self.status)

    def test_deferred_and_required_work_are_preserved(self):
        b,s,old,_=copy_fixtures.assets(mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',fields=old['replay_request']['fields'],contract_version='0.4.0')
        c=copy_projection(p,b,s); m=motion_projection(p,b,s); v=realize_experience(c,m,p,b,s)
        self.assertEqual(v['work_delta']['deferred_work'],['word_form'])
        self.assertIn('context_check',v['work_delta']['still_required_work'])
        self.assertEqual(v['stop']['deferred_work'],v['work_delta']['deferred_work'])
        for field in ('deferred_work','still_required_work'):
            changed=deepcopy(v); changed['work_delta'][field]=[]
            with self.subTest(field=field),self.assertRaises(ValueError): validate_experience(reseal(changed),c,m,p,b,s)

    def test_unresolved_candidates_cannot_disappear_from_screen_semantics(self):
        v=self.experience(); self.assertTrue(v['stop']['unresolved'])
        v['beats'][-1]['screen']['object_ids']=[]
        audit,_,errors=audit_experience(v,self.view(),self.plan)
        self.assertFalse(audit['unresolved_preserved']); self.assertIn('UNRESOLVED_OBJECTS_HIDDEN',errors)
        with self.assertRaises(ValueError): validate_experience(reseal(v),self.copy,self.motion,self.plan,self.bundle,self.status)

    def test_interrupt_cannot_create_new_anti_rule(self):
        with self.assertRaisesRegex(ValueError,'Anti-rule'):
            self.experience(draft_lines={'interrupt':self.line('先别读全文。','/primary_action/instruction')})
        self.assertNotIn('INTERRUPT',[r['stage'] for r in self.experience()['experience_curve']])

    def test_orient_uses_visible_allowed_fields_only(self):
        v=self.experience(options={'include_orient':True})
        self.assertIn('ORIENT',[r['stage'] for r in v['experience_curve']])
        with self.assertRaises(ValueError): self.experience(draft_lines={'orient':self.line('SYNTHETIC backend','/truth_guard')})
        v=self.experience(draft_lines={'orient':self.line('看这个对象。','/student_model/attention')})
        self.assertTrue(any(b['cognitive_function']=='orient' and b['vo'] for b in v['beats']))

    def test_action_has_exact_primary_binding(self):
        v=self.experience(); action=next(b for b in v['beats'] if b['cognitive_function']=='action')
        self.assertEqual(v['first_action'],self.plan['primary_action'])
        self.assertIn(pedagogy_ref(self.plan,'/primary_action/instruction'),action['vo']['pedagogy_refs'])
        with self.assertRaises(ValueError): self.experience(draft_lines={'action':self.line('看这里。','/first_touch/first_signal')})

    def test_first_touch_cannot_have_competing_primary_actions(self):
        b,s,sel=decisions.freeze(decisions.request(second='R02')); sel['action_ids'].append('synthetic-cut-C')
        p=compile_plan(b,s,sel,contract_version='0.4.0')
        with self.assertRaisesRegex(ValueError,'one primary action'):
            realize_experience(None,None,p,b,s,allow_held_plan=True)

    def test_tension_requires_real_unresolved_state(self):
        v=self.experience(); action=next(b for b in v['beats'] if b['cognitive_function']=='action')
        self.assertEqual(action['experience']['tension_state']['unresolved_objects'],v['stop']['unresolved'])
        view=self.view(); view['cognitive_structure']['objects']=[o for o in view['cognitive_structure']['objects'] if o['state']!='unresolved']
        _,_,errors=audit_experience(v,view,self.plan); self.assertIn('TENSION_REQUIRES_UNRESOLVED_SOURCE',errors)

    def test_collapse_requires_observed_plan_frames_and_bound_reduction(self):
        v=self.experience(); self.assertTrue(v['collapse']['learner_visible'])
        v['beats'][0]['screen']['structural_state']=None
        audit,_,errors=audit_experience(v,self.view(),self.plan)
        self.assertFalse(audit['collapse_visible_in_plan']); self.assertIn('COLLAPSE_STRUCTURE_NOT_ENCOUNTERED',errors)

    def test_payoff_line_requires_allowed_claim(self):
        with self.assertRaises(ValueError): self.experience(draft_lines={'payoff':self.line('只少了一项。','/primary_action/instruction')})
        v=self.experience(options={'payoff_delivery':'literal'})
        beat=next(b for b in v['beats'] if b['cognitive_function']=='collapse')
        self.assertEqual(beat['vo']['text'],self.copy['payoff']['allowed_claim']['text'])

    def test_fake_payoff_and_unsupported_savings_fail(self):
        for text in ('答案出来了。','所以选C。','这一题不用读全文。','省一半时间。'):
            v=self.experience(draft_lines={'payoff':self.line(text,'/payoff/allowed_claim')})
            with self.subTest(text=text): self.assertEqual(v['availability']['status'],'FAIL')

    def test_vo_screen_duplication_is_lint_not_self_certification(self):
        v=self.experience(draft_lines={'memory':self.line(self.plan['first_touch']['memory_phrase']['text'],'/first_touch/memory_phrase')})
        self.assertTrue(v['experience_audit']['vo_screen_duplication']); self.assertIn('screen_voice_duplication',v['ai_tone_lint']['flags'])
        self.assertEqual(v['availability']['status'],'HOLD')

    def test_internal_method_codes_fail_on_vo(self):
        v=self.experience(draft_lines={'action':self.line('R02，先做这一步。','/primary_action/instruction')})
        self.assertIn('INTERNAL_METHOD_CODE_ON_CONSUMER_SURFACE',v['availability']['issues'])

    def test_internal_role_and_expert_chain_cannot_be_narrated(self):
        for text in ('先调用reducer。','现在进入interpret阶段。','检查Review和Evidence。'):
            v=self.experience(draft_lines={'action':self.line(text,'/primary_action/instruction')})
            with self.subTest(text=text): self.assertEqual(v['availability']['status'],'FAIL')

    def test_method_stamp_follows_first_effective_action(self):
        v=self.experience(); self.assertEqual(v['beats'][-1]['cognitive_function'],'stamp')
        self.assertEqual(v['memory_closure']['first_action_ref'],pedagogy_ref(self.plan,'/primary_action'))
        self.assertIsNone(v['experience_audit']['method_named_before_understood'])
        v['beats'].insert(0,v['beats'].pop())
        _,_,errors=audit_experience(v,self.view(),self.plan); self.assertIn('METHOD_NAME_BEFORE_ACTION',errors)

    def test_silence_cannot_hide_required_spoken_tell_now(self):
        v=self.experience(); view=self.view(); item=view['must_obtain'][0]
        item['spoken_readout_required']=True; item['delivery_form']='spoken'
        v['stop']['boundary_presentations']=deepcopy(view['must_obtain'])
        _,_,errors=audit_experience(v,view,self.plan)
        self.assertIn('SILENCE_MASKS_REQUIRED_SPOKEN_BOUNDARY',errors)
        self.assertTrue(all(s['absolute_timing_assigned'] is False for s in v['silence_candidates']))

    def test_stop_scope_and_coverage_cannot_be_changed(self):
        v=self.experience(); self.assertEqual(v['stop']['scope'],'candidate_set')
        action=next(b for b in v['beats'] if b['cognitive_function']=='action')
        self.assertEqual(action['boundary_ids'],[self.copy['must_obtain'][0]['item_id']])
        self.assertIsNone(next(b for b in v['beats'] if b['cognitive_function']=='stop')['vo'])
        v['stop']['scope']='whole_question'
        with self.assertRaises(ValueError): validate_experience(reseal(v),self.copy,self.motion,self.plan,self.bundle,self.status)

    def test_action_demo_can_omit_payoff_without_omitting_output_or_stop(self):
        b,s,old,_=copy_fixtures.assets('G01',with_payoff=False,mode='worked_example')
        p=compile_plan(b,s,old['replay_request']['selection'],mode='worked_example',contract_version='0.4.0')
        v=realize_experience(None,None,p,b,s,allow_held_plan=True)
        self.assertEqual(v['compilation_status'],'PASS'); self.assertEqual(v['experience_kind'],'action_demo')
        self.assertTrue(v['stop']['current_output']); self.assertTrue(v['experience_audit']['stop_preserved'])

    def test_human_taste_and_public_release_never_self_pass(self):
        v=self.experience(); self.assertEqual(v['human_taste_review'],{'status':'PENDING','self_signed':False})
        self.assertFalse(v['public_render_ready']); self.assertEqual(v['release_state'],self.plan['release_state'])
        v['human_taste_review']['status']='PASS'
        with self.assertRaises(ValueError): inspect_historical(reseal(v))

    def test_truth_registry_and_frozen_inputs_are_unchanged(self):
        paths=[p for folder in ('answer_engine','core','method-registry','pedagogy') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        before={p:p.read_bytes() for p in paths}; frozen=sha([self.bundle,self.status,self.plan,self.copy,self.motion])
        self.experience(); self.assertEqual(frozen,sha([self.bundle,self.status,self.plan,self.copy,self.motion]))
        self.assertEqual(before,{p:p.read_bytes() for p in paths})

    def test_no_ae_or_tts_engine_options_or_runtime_imports(self):
        for key in ('camera','blur','z','speed_factor','pitch','reference','emotion'):
            with self.subTest(key=key),self.assertRaises(ValueError): self.experience(options={key:1})
        for name in ('experience.py','experience_qa.py'):
            tree=ast.parse((ROOT/'student_pov'/name).read_text(encoding='utf-8'))
            imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertFalse(any(n.startswith(('answer_engine','core','creative_os','ae_production','premiere_production','voicepacks','narration_performance')) for n in imports))

    def test_legacy_03_stays_readable_and_cannot_be_relabelled_as_04(self):
        b,s,p,c=copy_fixtures.assets(mode='worked_example'); old=realize(c,p,b,s)
        self.assertEqual(old['schema_version'],'0.3.0'); self.assertFalse(inspect_historical(old)['consumption_allowed'])
        self.assertEqual(validate_copy(old,c,p,b,s)['status'],'PASS')
        with self.assertRaises(ValueError): validate_copy(old,c,p,b,s,required_version='0.4.0')
        old['schema_version']='0.4.0'
        with self.assertRaises(ValueError): inspect_historical(seal(old))

    def test_new_binding_does_not_inherit_old_copy_approval(self):
        v=self.experience(); review=credential(v); accepted=self.experience(copy_review=review)
        self.assertEqual(accepted['availability']['status'],'READY')
        self.assertEqual(accepted['human_taste_review']['status'],'PENDING')
        for field,value in [('schema_version','0.3.0'),('source_plan_sha','0'*64),('final_copy_sha','0'*64)]:
            old=deepcopy(review); old[field]=value
            with self.subTest(field=field): self.assertEqual(self.experience(copy_review=old)['availability']['status'],'HOLD')

    def test_editing_words_or_encounter_order_invalidates_approval(self):
        v=self.experience(); review=credential(v)
        changed=self.experience(copy_review=review,options={'include_orient':True})
        self.assertEqual(changed['availability']['status'],'HOLD'); self.assertNotEqual(v['script_sha'],changed['script_sha'])
        changed=self.experience(copy_review=review,draft_lines={'action':self.line('只做这个动作。','/primary_action/instruction')})
        self.assertEqual(changed['availability']['status'],'HOLD')

    def test_over_structured_copy_is_flagged_without_absolute_ban(self):
        v=self.experience(draft_lines={'pain':self.line('首先，看这道题。','/first_touch/pain'),
            'action':self.line('其次，照这个动作做。','/primary_action/instruction')})
        self.assertIn('over_structured',v['ai_tone_lint']['flags']); self.assertEqual(v['availability']['status'],'HOLD')
        v=self.experience(draft_lines={'action':self.line('首先对这两处。','/primary_action/instruction')})
        self.assertNotIn('over_structured',v['ai_tone_lint']['flags'])

    def test_merged_and_separate_payoff_preserve_same_work_and_scope(self):
        a=self.experience(); b=self.experience(options={'merge_collapse_payoff':False})
        self.assertEqual(a['work_delta'],b['work_delta']); self.assertEqual(a['stop'],b['stop'])
        self.assertEqual(len(a['beats'])+1,len(b['beats'])); self.assertEqual(a['collapse']['scope'],b['collapse']['scope'])

    def test_cli_compile_validate_inspect_and_history_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,value in [('plan',self.plan),('projection',self.copy),('motion_projection',self.motion),('bundle',self.bundle),('status',self.status)]:
                write(root/(name+'.json'),value)
            request={k:k+'.json' for k in ('plan','projection','motion_projection','bundle','status')}
            request.update(contract_version='0.4.0',output='experience.json'); write(root/'request.json',request)
            with patch('sys.argv',['student_pov','realize',str(root/'request.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            original=(root/'experience.json').read_bytes()
            with patch('sys.argv',['student_pov','realize',str(root/'request.json')]),self.assertRaises(ValueError): main()
            self.assertEqual(original,(root/'experience.json').read_bytes())
            request['copy']='experience.json'; write(root/'validate.json',request)
            with patch('sys.argv',['student_pov','validate',str(root/'validate.json')]),contextlib.redirect_stdout(io.StringIO()): main()
            write(root/'inspect.json',{'copy':'experience.json'})
            with patch('sys.argv',['student_pov','inspect',str(root/'inspect.json')]),contextlib.redirect_stdout(io.StringIO()): main()

    def test_wrong_or_missing_current_handoff_never_opens_consumer_gate(self):
        with self.assertRaises(ValueError): realize_experience(None,None,self.plan,self.bundle,self.status,allow_held_plan=True)
        with self.assertRaises(ValueError): realize_experience(self.motion,self.copy,self.plan,self.bundle,self.status)
        bad=deepcopy(self.motion); bad['reference_catalog'].pop(next(iter(bad['reference_catalog'])))
        with self.assertRaises(ValueError): realize_experience(self.copy,seal(bad),self.plan,self.bundle,self.status)


if __name__=='__main__': unittest.main()
