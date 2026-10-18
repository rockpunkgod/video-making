"""Truth and consumer regressions; these tests do not certify aesthetic quality."""
from copy import deepcopy
import unittest

from video_contracts import sha
from creative_os.teaching_focus import VERSION, validate_focus, direct_scene, resource_report, require_focus
from content_os.scoring import rank_teaching_focus
from creative_os.audience_engagement import critical_focus_handoff
from ae_production.authored_episode import compile_clock


def fixture():
    passage='Participants join workshops and explore fiction. They edit previous campers works.'
    evidence={'field':'passage','start':0,'end':len(passage),'quote':passage}
    action={'method_id':'R03','method_version':'test','review_status':'reviewed','state':'produced',
            'stop_applied':False,'stop_rule_check':'Preserve action and ownership.','evidence':[evidence]}
    checks=[{'candidate':c,'evidence':[evidence],'backfill_check':'Complete original claim checked.'} for c in 'ABCD']
    b={'source_snapshot':{'options':{c:c for c in 'ABCD'},'passage':passage},
       'analysis':{'execution_trace':[action],'question_verification':{'review':{'candidate_checks':checks}}}}
    ref={'world':'w','pointer':'/execution_trace/0','sha':sha(action)}
    source={'world':'w','pointer':'/passage',**{k:evidence[k] for k in ('start','end','quote')}}
    unit={'id':'different-action','candidates':['A','D'],'difficulty_basis':'EDITORIAL_HYPOTHESIS',
          'challenge':'Same noun, different action.','judgement_change':'Preserve the verb relation.',
          'method_action_ref':ref,'decisive_source_refs':[source],
          'ratings':{'difficulty':3,'method_value':3,'visual_payoff':2}}
    options={c:{'treatment':'focus' if c in 'AD' else 'quick','rationale':'Explicit editorial judgement.',
                'verification_ref':{'pointer':f'/question_verification/review/candidate_checks/{i}','sha':sha(checks[i])}}
             for i,c in enumerate('ABCD')}
    scenes=[];voices=[];clips={};aligned={}
    for c in 'BCAD':
        text='Check '+c+'.';voices.append({'id':c,'text':text})
        clips[c]={'audio_sha256':c,'duration_seconds':2}
        aligned[c]={'transcript':text,'audio_sha256':c,'cues':[{'text':text,'text_start':0,'text_end':len(text),
                   'start':0,'end':1.8,'display_lines':[text]}]}
        scenes.append({'id':c,'kind':'compare','world':'w','candidate':c,'event':'supported' if c=='D' else 'eliminate',
            'voice_ids':[c],'voice_pre':.3,'voice_placements':{c:'comparison'},'source_refs':[source],
            'action_refs':[ref],'terminal_refs':[{'candidate':c,'effect':'retain' if c=='D' else 'eliminate'}],
            'attention':[],'reading_path':[],
            'choreography':{'orient_seconds':1,'candidate_read_seconds':2,'candidate_travel_seconds':2,
                'source_read_seconds':2,'extract_seconds':2,'comparison_seconds':2,'decision_seconds':1,
                'result_seconds':1,'return_seconds':1}})
    a={'format':{'fps':24},'scenes':scenes,'voices':voices,
       'teaching_focus':{'version':VERSION,'questions':{'w':{'options':options,'units':[unit]}}}}
    return a,{'w':b},clips,aligned


class TeachingFocus(unittest.TestCase):
    def test_sizes_one_two_and_many_are_valid_without_inventing_a_pair(self):
        for candidates in (['D'],['A','D'],['A','B','D']):
            a,b,_,_=fixture();q=a['teaching_focus']['questions']['w'];q['units'][0]['candidates']=candidates
            for c,o in q['options'].items():o['treatment']='focus' if c in candidates else 'brief'
            result=validate_focus(a,b)['w']
            self.assertEqual(result['critical_option_pairs'],[candidates] if len(candidates)==2 else [])

    def test_no_critical_unit_is_valid_for_a_genuinely_simple_transfer(self):
        a,b,_,_=fixture();q=a['teaching_focus']['questions']['w'];q['units']=[]
        for o in q['options'].values():o['treatment']='quick'
        self.assertEqual(rank_teaching_focus(a,b)['rows'][0]['selection_role'],'QUICK_TRANSFER_ONLY')

    def test_fast_options_still_require_complete_backstage_review(self):
        a,b,_,_=fixture();del a['teaching_focus']['questions']['w']['options']['B']
        with self.assertRaisesRegex(ValueError,'Every option'):validate_focus(a,b)

    def test_stale_verification_is_rejected_even_for_fast_option(self):
        a,b,_,_=fixture();b['w']['analysis']['question_verification']['review']['candidate_checks'][1]['backfill_check']='Changed'
        with self.assertRaisesRegex(ValueError,'stale'):validate_focus(a,b)

    def test_editorial_difficulty_cannot_be_promoted_to_student_measurement(self):
        a,b,_,_=fixture();a['teaching_focus']['questions']['w']['units'][0]['difficulty_basis']='OBSERVED_STUDENTS'
        with self.assertRaisesRegex(ValueError,'not measured'):validate_focus(a,b)

    def test_unsupported_or_hidden_decisive_evidence_is_rejected(self):
        for defect in ('false_quote','hidden'):
            a,b,_,_=fixture()
            if defect=='false_quote':a['teaching_focus']['questions']['w']['units'][0]['decisive_source_refs'][0]['quote']='Unsupported'
            else:
                for s in a['scenes']:s['source_refs']=[]
            with self.assertRaises(ValueError):validate_focus(a,b)

    def test_method_action_cannot_change_or_be_omitted(self):
        a,b,_,_=fixture();b['w']['analysis']['execution_trace'][0]['stop_applied']=True
        with self.assertRaisesRegex(ValueError,'stale'):validate_focus(a,b)
        a,b,_,_=fixture();a['scenes'][-1]['action_refs']=[]
        with self.assertRaisesRegex(ValueError,'consume'):validate_focus(a,b)

    def test_difficult_option_cannot_be_downgraded_for_pacing(self):
        a,b,_,_=fixture();a['teaching_focus']['questions']['w']['options']['A']['treatment']='quick'
        with self.assertRaisesRegex(ValueError,'skimmed'):validate_focus(a,b)

    def test_light_consumer_changes_real_clock_preserves_every_take_and_verdict(self):
        a,b,c,l=fixture();validate_focus(a,b);new=compile_clock(a,c,l)
        old=deepcopy(a);del old['teaching_focus'];before=compile_clock(old,c,l)
        self.assertLess(new['duration'],before['duration'])
        self.assertEqual([s['voice'] for s in new['segments']],[s['voice'] for s in before['segments']])
        self.assertEqual([e['refs'] for e in new['candidate_events']],[e['refs'] for e in before['candidate_events']])
        self.assertEqual(new['scenes'][0]['settled'],new['scenes'][0]['extract_start'])
        self.assertGreater(new['scenes'][2]['settled'],new['scenes'][2]['extract_start'])
        self.assertGreater(resource_report(a,new)['questions'][0]['critical_attention_share'],.5)

    def test_reading_windows_are_never_sped_up_by_resource_allocation(self):
        a,_,_,_=fixture();s=a['scenes'][0];s['reading_path']=[{'read_seconds':6,'move_seconds':2,'quote':'Exact'}]
        self.assertEqual(direct_scene(a,s)['reading_path'],s['reading_path'])
        self.assertEqual(direct_scene(a,s)['choreography']['source_read_seconds'],s['choreography']['source_read_seconds'])

    def test_bypassing_motion_allocation_is_detected(self):
        a,_,c,l=fixture();p=compile_clock(a,c,l);p['scenes'][0]['motion_treatment']='critical_comparison'
        with self.assertRaisesRegex(ValueError,'bypassed'):resource_report(a,p)

    def test_uniform_resource_treatment_cannot_pass_a_critical_film(self):
        a,_,c,l=fixture();p=compile_clock(a,c,l)
        p['scenes'][0]['end']=p['scenes'][0]['start']+1000
        with self.assertRaisesRegex(ValueError,'most comparison'):resource_report(a,p)

    def test_audience_handoff_does_not_fake_a_two_candidate_state(self):
        a,_,c,l=fixture();p=compile_clock(a,c,l);r=critical_focus_handoff(a,p)['rows'][0]
        self.assertEqual(r['candidate_states_before'],{'A':'unchecked','B':'eliminate','C':'eliminate','D':'unchecked'})
        self.assertEqual(r['difficulty_basis'],'EDITORIAL_HYPOTHESIS')

    def test_new_production_cannot_omit_focus(self):
        with self.assertRaisesRegex(ValueError,'requires teaching_focus'):require_focus({})


if __name__=='__main__':unittest.main()
