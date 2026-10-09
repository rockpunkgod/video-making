"""Explicitly synthetic reviewed traces; no English effectiveness certification."""
from copy import deepcopy
import unittest
from jsonschema import ValidationError
from video_contracts import sha, seal
from video_contracts.passage import export_bundle, status_manifest, material as passage_material
from video_contracts.locating_trace import source_binding, material, freeze, trace_status, require_trace
from creative_os.locating_attention import build_plan, timing, map_span
from tests.test_reviewed_passage import fixture as passage_fixture


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


if __name__=='__main__':unittest.main()
