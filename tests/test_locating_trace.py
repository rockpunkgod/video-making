"""Explicitly synthetic reviewed traces; no English effectiveness certification."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
import sys
import unittest
from jsonschema import ValidationError
from video_contracts import sha, seal
from video_contracts.passage import export_bundle, status_manifest, material as passage_material
from video_contracts.locating_trace import source_binding, material, freeze, trace_status, require_trace
from creative_os.locating_attention import build_plan, timing, map_span
from tests.test_reviewed_passage import fixture as passage_fixture
from video_contracts import write
from answer_engine.reviewed_locating_export import main as export_main
_native_spec=importlib.util.spec_from_file_location('locating_native_test',
    Path(__file__).resolve().parents[1]/'ae/experiments/method-relay-dual-pass/locating_native.py')
native=importlib.util.module_from_spec(_native_spec);_native_spec.loader.exec_module(native)


def fixture(acquired=True):
    p=passage_fixture();p['passage']='alpha beta alpha'
    p['review']['material_sha']=sha(passage_material(p))
    b=export_bundle(p,'original');s=status_manifest(b,'original')
    span=lambda start,end: {'field':'passage','start':start,'end':end,'quote':p['passage'][start:end]}
    target={'retained_information':{'field':'stem','start':0,'end':9,'quote':'Synthetic'},
        'search_expression':{'field':'stem','start':0,'end':9,'quote':'Synthetic'},
        'contextual_classification':'supplied_fixture_class','search_role':'fixture_only','review_ref':'t'}
    candidates=[{**span(0,5),'candidate_id':'first','scan_order':0,'question_id':'synthetic-1',
        'contextual_classification':'supplied_fixture_class','attention_eligibility':True,
        'recognition_state':'acquired' if acquired else 'inspected_continue','review_ref':'c1'}]
    if not acquired: candidates.append({**span(11,16),'candidate_id':'repeat','scan_order':1,
        'question_id':'synthetic-1','contextual_classification':'supplied_fixture_class',
        'attention_eligibility':True,'recognition_state':'unresolved','review_ref':'c2'})
    a={'candidate_id':'first','correspondence_basis':'Explicit synthetic assertion only',
       'sentence':span(0,5),'evidence':span(0,5),'source_evidence_ref':'/payload/review/segments/0/evidence/0',
       'allowed_conclusion':'locate_for_further_inspection','review_ref':'a'} if acquired else None
    packet={'binding':source_binding(b,'synthetic-1'), 'strategy':{'relation_category':'synthetic',
        'selection_rule':'Explicit fixture supplied, no NLP'},'target':target,'candidates':candidates,'acquisition':a,
        'review':{'reviewer':'SYNTHETIC AI ONLY','reviewer_kind':'ai_host','status':'reviewed',
                 'material_sha':'','request_ref':'synthetic-request','request_sha':sha('synthetic request'),
                 'independent_human_certified':False,'independent_human_review':'not_applicable','assertions':[]}}
    rebind(packet)
    words=[{'id':str(i),'layer_id':i+100,'start':start,'end':end,'text':p['passage'][start:end],
            'line':i//2,'min':[i*150,500+(i//2)*60,0],'max':[i*150+80,540+(i//2)*60,0],
            'center':[i*150+40,520+(i//2)*60,0]} for i,(start,end) in enumerate([(0,5),(6,10),(11,16)])]
    g={'passage_sha':sha(p['passage']),'native_readback':True,'native_audit_sha':sha('synthetic geometry'),
       'spec_sha':sha('synthetic spec'),'words':words}
    return packet,b,s,g


def rebind(packet):
    r=packet['review'];assertions=[]
    for subject,v in [('target',packet['target'])]+[(c['candidate_id'],c) for c in packet['candidates']]+(
            [('acquisition',packet['acquisition'])] if packet['acquisition'] else []):
        assertions.append({'ref':v['review_ref'],'subject':subject,
            'subject_sha':sha({k:x for k,x in v.items() if k!='review_ref'}),
            'question_id':packet['binding']['question_id'],'rationale':'Synthetic assertion, not real review',
            'evidence':[{'field':'passage','start':0,'end':5,'quote':'alpha'}]})
    r['assertions']=assertions;r['material_sha']=sha(material(packet))


class LocatingTraceTests(unittest.TestCase):
    def test_canonical_replay_and_ai_no_upgrade(self):
        p,b,s,g=fixture();before=deepcopy((p,b,s));a=freeze(p,b,s,'one');c=freeze(p,b,s,'two')
        self.assertEqual(a['semantic_binding_sha'],c['semantic_binding_sha'])
        self.assertNotEqual(a['envelope_sha'],c['envelope_sha'])
        self.assertEqual(before,(p,b,s));self.assertEqual(a['semantic_review']['level'],'ai_reviewed')
        self.assertFalse(a['semantic_review']['independent_human_certified'])
        self.assertFalse(a['public_render_ready'])

    def test_acquired_and_unresolved_different_structure(self):
        for hit in (True,False):
            p,b,s,g=fixture(hit);t=freeze(p,b,s,'one');ts=trace_status(t,'one')
            a=build_plan(t,ts,b,s,g,[252,354]);self.assertEqual(a,build_plan(t,ts,b,s,g,[252,354]))
            self.assertEqual(bool(a['handoff']),hit);self.assertEqual(len(a['targets']),1 if hit else 2)
            self.assertFalse(a['public_render_ready'])
            if not hit: self.assertNotIn('acquire',[e['event'] for e in a['events']])

    def test_bad_span_classification_only_and_cross_question(self):
        changes=[lambda p:p['candidates'][0].update(quote='wrong'),
            lambda p:p['candidates'][0].update(question_id='another'),
            lambda p:p['candidates'][0].update(attention_eligibility=False),
            lambda p:p['target']['search_expression'].update(field='other'),
            lambda p:p['binding'].update(question_id='another'),
            lambda p:p['review'].update(independent_human_certified=True)]
        for change in changes:
            p,b,s,g=fixture();change(p);rebind(p)
            with self.subTest(change=change),self.assertRaises((ValueError,ValidationError)):
                freeze(p,b,s,'one')

    def test_current_review_and_source_status_required(self):
        p,b,s,g=fixture();t=freeze(p,b,s,'one')
        for state in ('WITHDRAWN','SUPERSEDED','STALE','BLOCKED'):
            with self.subTest(state=state),self.assertRaises(ValueError):
                require_trace(t,trace_status(t,'two',state),b,s)
            with self.assertRaises(ValueError):freeze(p,b,status_manifest(b,'two',state),'one')
        with self.assertRaises(ValueError):require_trace(t,None,b,s)
        changed=deepcopy(b);changed['payload']['source']['redistribution_status']='withdrawn'
        changed=export_bundle(changed['payload'],'two')
        with self.assertRaises(ValueError):freeze(p,changed,status_manifest(changed,'two'),'one')

    def test_proposed_cannot_freeze_or_forge_correspondence(self):
        p,b,s,g=fixture();p['review']['status']='PROPOSED'
        with self.assertRaises(ValidationError):freeze(p,b,s,'one')
        p,b,s,g=fixture();p['review']['assertions'].pop()
        with self.assertRaises(ValueError):freeze(p,b,s,'one')

    def test_export_accepts_original_request_binding_without_new_source_field(self):
        p,b,s,g=fixture()
        request={'question_id':p['binding']['question_id'],
                 'binding':{k:p['binding'][k] for k in ('asset_id','semantic_binding_sha','passage_sha','review_sha')}}
        request['request_sha']=sha(request);p['review']['request_sha']=request['request_sha']
        with TemporaryDirectory() as temp:
            root=Path(temp)
            for name,v in [('review',p),('bundle',b),('status',s),('request',request)]:write(root/(name+'.json'),v)
            args=['export']+[str(root/(name+'.json')) for name in ('review','bundle','status')]+[str(root/'new'),'--request',str(root/'request.json')]
            with patch.object(sys,'argv',args):export_main()
            self.assertTrue((root/'new/trace.json').exists())
            with patch.object(sys,'argv',args),self.assertRaises(ValueError):export_main()

    def test_ai_cannot_claim_independent_human_review_pass(self):
        p,b,s,g=fixture();p['review']['independent_human_review']='pass'
        with self.assertRaises(ValueError):freeze(p,b,s,'one')

    def test_repeated_token_mapping_uses_offsets(self):
        p,b,s,g=fixture(False)
        self.assertEqual(map_span(p['candidates'][1],g['words'],b['payload']['passage'])[0]['id'],'2')
        c={'start':0,'end':10,'quote':'alpha beta'}
        self.assertEqual([w['id'] for w in map_span(c,g['words'],b['payload']['passage'])],['0','1'])
        with self.assertRaises(ValueError):map_span({'start':1,'end':5},g['words'],b['payload']['passage'])

    def test_no_auto_last_candidate_acquire_and_no_reorder(self):
        p,b,s,g=fixture(False);p['candidates'].reverse();rebind(p)
        with self.assertRaises(ValueError):freeze(p,b,s,'one')
        p,b,s,g=fixture(False);t=freeze(p,b,s,'one')
        with self.assertRaises(timing.RecognitionTimingOverflow):build_plan(t,trace_status(t,'one'),b,s,g,[0,10])

    def test_not_eligible_is_auditable_without_highlight(self):
        p,b,s,g=fixture(False)
        for c in p['candidates']: c.update(attention_eligibility=False,recognition_state='not_eligible')
        rebind(p);t=freeze(p,b,s,'one');a=build_plan(t,trace_status(t,'one'),b,s,g,[0,40])
        self.assertEqual(a['events'],[]);self.assertIsNone(a['handoff'])
        self.assertEqual(len(a['filtered_candidates']),2)

    def test_cross_question_evidence_even_when_quote_matches(self):
        p,b,s,g=fixture();other=deepcopy(b['payload']);q=deepcopy(other['questions'][0]);q.update(question_id='synthetic-2',number=2)
        other['questions'].append(q);r=other['review'];r['order'].append('synthetic-2')
        for d in deepcopy(r['decisions']): d['question_id']='synthetic-2';r['decisions'].append(d)
        for seg in deepcopy(r['segments']):
            seg.update(question_id='synthetic-2',segment_id='other-'+seg['segment_id'])
            seg['decision_refs']=[2,3] if seg['kind']=='comparison' else [];r['segments'].append(seg)
        r['material_sha']=sha(passage_material(other));b=export_bundle(other,'one');s=status_manifest(b,'one')
        p['binding']=source_binding(b,'synthetic-1');p['acquisition']['source_evidence_ref']='/payload/review/segments/3/evidence/0';rebind(p)
        with self.assertRaises(ValueError):freeze(p,b,s,'one')

    def test_native_adapter_preserves_bound_hit_and_tail(self):
        p,b,s,g=fixture();t=freeze(p,b,s,'one');ts=trace_status(t,'one')
        request={'spec_sha':sha('synthetic original'),'source':{'asset_id':b['asset_id'],
            'passage_sha':g['passage_sha']},'words':[], 'hit_ids':['0'],'target_ids':['0'],
            'render_scale':2,'camera_style':{},'director':{'passes':[{'end':7},
                {'scan':[10.5,14.75],'hit_settle_end':15,'lock':[15.5,16.5],'lift':[18.5,19.5]}]}}
        audit={'spec_sha':request['spec_sha'],'canvas':[3840,2160,24],
               'handles':{'0':100,'1':101,'2':102},'initial_handles':{'0':100,'1':101,'2':102},
               'words':[],'sentence_attention':[{'ids':['0'],'gain_cap':.004,
                   'windows':[[1.5,6,6.65,.004],[10.5,18.5,19.5,.004]]}]}
        for w in g['words']:
            original={k:w[k] for k in ('id','start','end','text','line')};original['text_sha']=sha(w['text']);request['words'].append(original)
            audit['words'].append({**original,'layer_id':w['layer_id'],'source_sha':g['passage_sha'],
                'source_text_keys':0,'parent':None,'anchor':[0,0,0],'position':w['min'],
                'scale':[100,100,100],'rect':{'left':0,'top':0,'width':80,'height':40}})
        a=native.prepare(t,ts,b,s,request,audit,[252,360])
        self.assertEqual(a,native.prepare(t,ts,b,s,request,audit,[252,360]))
        self.assertEqual(a['plan']['handoff']['handoff_to_lift'],[444,468])
        self.assertEqual(a['plan']['targets'][0]['word_ids'],['0'])
        self.assertEqual(a['attention_groups'][0]['windows'][0],[1.5,6,6.65,.004])
        self.assertEqual(a['rows'][0]['frame'],252)
        self.assertIn('camera_rows',a)
        self.assertEqual(a['plan']['highlight_palette']['question'],a['plan']['highlight_palette']['acquired'])
        self.assertNotEqual(a['plan']['highlight_palette']['comparison'],a['plan']['highlight_palette']['acquired'])
        camera_y=[native.camera_at(a,f/24)[1] for f in range(252,361)]
        self.assertTrue(all(y>=x-.00001 for x,y in zip(camera_y,camera_y[1:])))
        self.assertLessEqual(len(a['camera_rows']),len(a['rows']))
        bad=deepcopy(request);bad['hit_ids']=['2']
        with self.assertRaises(ValueError):native.prepare(t,ts,b,s,bad,audit,[252,360])
        with self.assertRaises(ValueError):native.prepare(t,ts,b,s,request,audit,[252,362])
        with TemporaryDirectory() as temp:
            path=Path(temp)/'new.aep';code=native.script(a,Path(temp)/'patch.json',path)
            self.assertNotIn('LOCATING_PATCH_PATH',code)
            self.assertIn('l.moveAfter(back)',code)
            self.assertIn('4*S',code)
            path.touch()
            with self.assertRaises(ValueError):native.script(a,Path(temp)/'patch.json',path)

    def test_reference_path_has_matching_endpoint_velocity(self):
        p={'rows':[{'frame':0,'center':[0,0,0],'velocity':[0,0,0]},
                   {'frame':12,'center':[50,20,0],'velocity':[2,1,0]},
                   {'frame':24,'center':[100,40,0],'velocity':[0,0,0]}]}
        dt=1e-5;a=native.focus_at(p,.5-dt);b=native.focus_at(p,.5);c=native.focus_at(p,.5+dt)
        for axis in range(3):self.assertAlmostEqual((b[axis]-a[axis])/dt,(c[axis]-b[axis])/dt,places=4)
        p['focus_entry']={'frames':[-12,0],'from':[-50,-20,0],'to':[0,0,0]}
        self.assertEqual(native.focus_at(p,-.5),[-50,-20,0])
        self.assertEqual(native.focus_at(p,0),[0,0,0])

    def test_native_readback_cannot_omit_frames_or_fake_camera_clock(self):
        import math
        p={'patch_sha':sha('synthetic native patch'),'rows':[
            {'frame':0,'center':[0,0,0],'velocity':[0,0,0]},
            {'frame':10,'center':[0,10,0],'velocity':[0,0,0]}],
            'frame_range':[0,10],'entry_state':{'focus':[0,0,0],'camera':[0,20,-100],'look':[0,10,0]},
            'plan':{'targets':[],'clock':{'events':[]},'handoff':None}}
        rows=[]
        for frame in range(11):
            f=native.focus_at(p,frame/24);cam=[0,f[1]+20,-100];look=[0,f[1]+10,0];v=[x-y for x,y in zip(look,cam)]
            rows.append({'time':frame/24,'focus':f,'camera':cam,'look':look,
                'focus_distance':sum((x-y)*z/math.dist(v,[0,0,0]) for x,y,z in zip(f,cam,v)),'marks':[]})
        a={'patch_binding':{'locating_patch_sha':p['patch_sha']},'canvas':[3840,2160,24],
           'rows':rows,'boundaries':[],'errors':[],'lift':[]}
        self.assertEqual(native.validate_motion(p,a)['frame_count'],11)
        for change in (lambda v:v['rows'].pop(),lambda v:v['rows'][4]['camera'].__setitem__(1,400),
                       lambda v:v['rows'][4].update(focus_distance=10000),
                       lambda v:v.update(canvas=[1920,1080,24])):
            bad=deepcopy(a);change(bad)
            with self.assertRaises(ValueError):native.validate_motion(p,bad)

    def test_camera_transport_does_not_copy_reading_return_excursions(self):
        p={'rows':[{'frame':0,'center':[0,0,0],'velocity':[0,0,0]},
                   {'frame':5,'center':[100,40,0],'velocity':[0,0,0]},
                   {'frame':10,'center':[0,35,0],'velocity':[0,0,0]},
                   {'frame':20,'center':[50,100,0],'velocity':[0,0,0]}],
           'camera_rows':[{'frame':0,'center':[0,0,0],'velocity':[0,0,0]},
                          {'frame':20,'center':[0,100,0],'velocity':[0,0,0]}]}
        ys=[native.camera_at(p,f/240)[1] for f in range(201)]
        self.assertTrue(all(b>=a for a,b in zip(ys,ys[1:])))
        self.assertNotEqual(native.camera_at(p,5/24)[1],native.focus_at(p,5/24)[1])

    def test_native_palette_and_behind_ink_are_enforced(self):
        palette={'question':[.95,.74,.43],'comparison':[.64,.79,.90],'acquired':[.95,.74,.43]}
        p={'patch_sha':sha('synthetic color proof'),'rows':[
            {'frame':0,'center':[0,0,0],'velocity':[0,0,0]},
            {'frame':10,'center':[0,0,0],'velocity':[0,0,0]}],
            'frame_range':[0,10],'entry_state':None,'geometry':{'words':[{'max':[1,1,0]}]},
            'plan':{'highlight_palette':palette,'targets':[{'candidate_id':'c','recognition_state':'acquired'}],
                'clock':{'events':[{'activation':[2,4],'recognition':[4,7]}]},'handoff':None}}
        rows=[]
        for f in range(11):
            color=palette['acquired'] if f>=7 else palette['comparison']
            rows.append({'time':f/24,'focus':[0,0,0],'camera':[0,0,-100],'focus_distance':100,
                'question_color':palette['question']+[1],
                'marks':[{'name':'LOCATING_TRANSIENT_c','opacity':0 if f<2 else 85,
                    'color':color+[1],'index':10,'position':[0,0,8]}]})
        a={'patch_binding':{'locating_patch_sha':p['patch_sha']},'canvas':[3840,2160,24],
            'rows':rows,'source_indices':[2,3,4],'boundaries':[],'errors':[],'lift':[]}
        self.assertEqual(native.validate_motion(p,a)['frame_count'],11)
        for change in (lambda x:x['rows'][8]['marks'][0].update(color=palette['comparison']),
                       lambda x:x['rows'][4]['marks'][0].update(index=1),
                       lambda x:x['rows'][4]['marks'][0].update(position=[0,0,-8]),
                       lambda x:x['rows'][4].update(question_color=palette['comparison'])):
            bad=deepcopy(a);change(bad)
            with self.assertRaises(ValueError):native.validate_motion(p,bad)


if __name__=='__main__':unittest.main()
