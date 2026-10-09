"""Presentation-only projection of reviewed spans onto supplied native geometry."""
import importlib.util
import math
from video_contracts import ROOT, sha
from video_contracts.locating_trace import require_trace

_spec = importlib.util.spec_from_file_location('locating_recognition_clock',
    ROOT/'ae/experiments/method-relay-dual-pass/recognition_timing.py')
timing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(timing)


def map_span(span, words, passage):
    rows = sorted((w for w in words if w['start'] < span['end'] and span['start'] < w['end']),
                  key=lambda w: w['start'])
    if (not rows or rows[0]['start'] != span['start'] or rows[-1]['end'] != span['end']
            or any(passage[w['start']:w['end']] != w['text'] for w in rows)):
        raise ValueError('Exact whole original-word mapping required; no string search or expansion')
    return rows


def native_geometry(request, audit):
    """Project actual sourceRect readback, not estimated font metrics."""
    if (audit['spec_sha'] != request['spec_sha'] or audit['canvas'][:3] != [3840,2160,24]
            or audit['initial_handles'] != audit['handles']):
        raise ValueError('Bound original native objects at full 4K required')
    by_id = {w['id']: w for w in request['words']}; result = []
    for w in audit['words']:
        original = by_id.get(w['id'])
        if (original is None or any(w[k] != original[k] for k in ('start','end','text','text_sha'))
                or w['source_sha'] != request['source']['passage_sha'] or w['source_text_keys'] != 0
                or w['parent'] is not None or w['anchor'] != [0,0,0]):
            raise ValueError('Native source object identity or text changed')
        r=w['rect']; p=w['position']; s=w['scale']
        low=[p[0]+r['left']*s[0]/100,p[1]+r['top']*s[1]/100,p[2]]
        high=[low[0]+r['width']*s[0]/100,low[1]+r['height']*s[1]/100,p[2]]
        result.append({k:w[k] for k in ('id','start','end','text','layer_id')} | {
            'line':original['line'],'min':low,'max':high,'center':[(a+b)/2 for a,b in zip(low,high)]})
    if len(result)!=len(by_id) or len({w['id'] for w in result})!=len(by_id):
        raise ValueError('Complete native word inventory required')
    return {'passage_sha':request['source']['passage_sha'],'spec_sha':request['spec_sha'],
            'native_audit_sha':sha(audit),'words':sorted(result,key=lambda w:w['start']),
            'native_readback':True}


def build_plan(trace, trace_status, bundle, status, geometry, frame_range, recognition_frames=None,
               confirm_frames=24, lift_frames=24):
    packet=require_trace(trace,trace_status,bundle,status)
    if not geometry.get('native_readback') or geometry['passage_sha']!=packet['binding']['passage_sha']:
        raise ValueError('Matching actual native geometry required')
    passage=bundle['payload']['passage']; words=geometry['words']
    if not words or words[0]['start']!=0: raise ValueError('Scan must enter original first line')
    ids=[c['candidate_id'] for c in packet['candidates'] if c['attention_eligibility']
         and c['recognition_state']!='not_eligible']
    selected=[c for c in packet['candidates'] if c['candidate_id'] in ids]
    if recognition_frames is None: recognition_frames={i:7 for i in ids}
    if set(recognition_frames)!=set(ids): raise ValueError('Explicit recognition duration for every candidate')
    targets=[]; policies={}; previous=words[0]['center']
    for c in selected:
        mapped=map_span(c,words,passage)
        low=[min(w['min'][a] for w in mapped) for a in range(3)]
        high=[max(w['max'][a] for w in mapped) for a in range(3)]
        center=[(a+b)/2 for a,b in zip(low,high)]
        # Editorial spatial rule, never inferred semantic difficulty.
        distance=math.dist(previous,center)
        transfer=max(4,math.ceil(distance/90))
        if transfer>240: raise ValueError('Route needs explicit longer director window')
        policies[c['candidate_id']]={'transfer':transfer,'activation':5,
            'recognition':recognition_frames[c['candidate_id']],'retirement':3}
        targets.append({'candidate_id':c['candidate_id'],'word_ids':[w['id'] for w in mapped],
            'layer_ids':[w['layer_id'] for w in mapped], 'span':{k:c[k] for k in ('field','start','end','quote')},
            'min':low,'max':high,'center':center,'line_ids':sorted({w['line'] for w in mapped}),
            'recognition_state':c['recognition_state']})
        previous=center
    acquired=packet['acquisition']['candidate_id'] if packet['acquisition'] else None
    clock=timing.schedule(ids,acquired,frame_range,event_policies=policies)
    # Put unallocated time into real approach rather than waiting before search.
    if ids and clock['remaining_frames']:
        extra=clock['remaining_frames']; per,rem=divmod(extra,len(ids))
        for j,i in enumerate(ids): policies[i]['transfer']+=per+(j<rem)
        clock=timing.schedule(ids,acquired,frame_range,event_policies=policies)
    events=[]
    for e,t in zip(clock['events'],targets):
        stages={'approach':e['transfer'],'decelerate':[max(e['transfer'][0],e['transfer'][1]-3),e['transfer'][1]],
            'focus_enter':e['activation'],'highlight_activate':e['activation'],'recognition_hold':e['recognition']}
        if 'retirement' in e: stages.update(highlight_retire=e['retirement'],continue_scan=e['retirement'])
        else: stages['acquire']=e['recognition']
        for name,frames in stages.items(): events.append({'event':name,'frames':frames,**t})
    handoff=None
    if acquired:
        if any(type(v) is not int or v<1 for v in (confirm_frames,lift_frames)):
            raise ValueError('Explicit positive confirmation and lift duration required')
        a=packet['acquisition']; mapped=map_span(a['sentence'],words,passage); end=frame_range[1]
        handoff={'sentence_ids':[w['id'] for w in mapped], 'sentence_layer_ids':[w['layer_id'] for w in mapped],
            'sentence_confirm':[end,end+confirm_frames],
            'handoff_to_lift':[end+confirm_frames,end+confirm_frames+lift_frames],
            'source_evidence_ref':a['source_evidence_ref']}
    payload={'kind':'locating_attention_plan','version':'0.1.0','mode':'guided','fps':24,
        'trace_sha':trace['semantic_binding_sha'],'geometry_sha':sha(geometry),
        'source_binding':packet['binding'],'clock':clock,'targets':targets,'events':events,'handoff':handoff,
        'first_source_center':words[0]['center'],'outcome':clock['outcome'],
        'filtered_candidates':[{'candidate_id':c['candidate_id'],'reason':'not_attention_eligible'}
            for c in packet['candidates'] if c['candidate_id'] not in ids],
        'entry':'original_first_line','highlight':'transient_filled','magnification':'baseline_locked_existing',
        'authority':'presentation_only','human_visual_review':'PENDING','public_render_ready':False}
    return {**payload,'plan_sha':sha(payload)}
