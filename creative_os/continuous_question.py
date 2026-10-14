"""Single-question grammar proof; frozen P4 inputs and existing exact WAVs only."""
import argparse
from copy import deepcopy
import json
import re
from pathlib import Path

from video_contracts import read, write, sha
from .episode_build import build_episode, reference, ROOT, caption_parts
from ae_production.candidate_motion import audit_candidate_events


def validate_projection(bundle, projection):
    action = bundle['source_snapshot']['action_executions'][projection['action_index']]
    source = bundle['source_snapshot']['passage']
    a, b = projection['range']
    if not (type(a) is int and type(b) is int and 0 <= a < b <= len(source)):
        raise ValueError('Invalid extraction range')
    if source[a:b] != projection['text'] or not any(
        e['field'] == 'passage' and e['start'] <= a < b <= e['end']
        for e in action['evidence']
    ):
        raise ValueError('Extraction must remain inside frozen action evidence')
    hits=[m for m in re.finditer(r'\S+',source) if a<=m.start() and m.end()<=b]
    if not hits or hits[0].start()!=a or hits[-1].end()!=b:
        raise ValueError('Native grammar lifts whole original glyph words only')
    return reference(bundle, '/source_snapshot/passage')


def prepare(request, direction):
    direction=deepcopy(direction)
    # Reuse status, exact-copy, delivery, action and closure checks of the existing chain.
    old = build_episode(request)
    bundle = read(request['sources'][direction['source']]['bundle'])
    asset = bundle['asset_id']
    snap = bundle['source_snapshot']
    event = next(e for e in old['candidate_audit']['events'] if e['action_id'] == direction['action_id'])
    if event['before'] != ['A','B','C','D'] or event['after'] != ['A','B','C']:
        raise ValueError('This bounded proof consumes the existing D elimination only')
    if direction['duration'] != 70 or direction['answer'] is not None:
        raise ValueError('No new answer or unbound timing in this proof')
    expected_voices={v for item in request['edit'] if item['source']==direction['source'] for v in item.get('voice_ids',[])}
    if set(direction['voice_slots'])!=expected_voices:
        raise ValueError('Single-question proof cannot borrow another question voice')
    if direction['voice_slots']!=dict(A01=.75,A02=5.5,A03=34,A04=42,A05=50,A06=57):
        raise ValueError('Voice slots must match this proof native cognitive beat timing')
    action_index=next(i for i,a in enumerate(snap['action_executions']) if a['execution_id']==direction['action_id'])
    action_ref=reference(bundle,f'/source_snapshot/action_executions/{action_index}')
    native_event=dict(scene_id='fast-D',question_id=snap['question_id'],source_refs=[action_ref],
        candidate='D',effect='eliminate',compare_start=19.5,decision_start=22,
        decision_end=22+10/24,confirmation_start=23)
    audited=audit_candidate_events([native_event],{asset:bundle})
    for p in direction['projections']:
        p['source_ref'] = validate_projection(bundle, p)
        p['action_ref'] = reference(bundle, '/source_snapshot/action_executions/'+str(p['action_index']))
    voices=[]
    for key, at in direction['voice_slots'].items():
        v = deepcopy(next(v for v in old['voices'] if v['id'] == key))
        v['start_frame']=round(at*24);v['end_frame']=v['start_frame']+round(v['duration']*24)
        v['caption_parts']=caption_parts(v['text'],request['fallback_font'],36,1650)
        voices.append(v)
    voices.sort(key=lambda v:v['start_frame'])
    if any(v['end_frame']>70*24 for v in voices) or any(
        b['start_frame']<a['end_frame'] for a,b in zip(voices,voices[1:])):
        raise ValueError('Voice overlap or truncation')
    method_index=next(i for i,m in enumerate(bundle['methods']) if m['method_id']=='R06')
    return dict(schema='continuous-question/v1',fps=24,duration=70,duration_frames=1680,
        source=snap,asset_id=asset,projections=direction['projections'],voices=voices,
        memory_line=bundle['methods'][method_index]['memory_line'],
        memory_ref=reference(bundle,f'/methods/{method_index}/memory_line'),
        renderer_fonts=dict(english='SourceSerif4-Regular',caption='NotoSansSC-Medium',decision='NotoSerifSC-Bold'),
        style=old['style'],binding=old['bindings'],candidate_audit=audited,candidate_events=[native_event],
        replay=dict(action_ref=action_ref,decision_start=56,confirmation_start=57,
                    changes_candidate_state=False),
        source_refs={key:reference(bundle,'/source_snapshot/'+key) for key in ('stem','passage','options')},
        answer=None,listening_review='PENDING',final_voice_accepted=False,public_render_ready=False)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('request',type=Path);cli.add_argument('direction',type=Path);cli.add_argument('output',type=Path)
    args=cli.parse_args();plan=prepare(read(args.request),read(args.direction))
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'local-data'):raise ValueError('Real data stays local')
    out.mkdir(parents=True,exist_ok=False);write(out/'PLAN.json',plan)
    grammar=(ROOT/'ae/lib/grammar.jsx').read_text(encoding='utf-8')
    template=(ROOT/'ae/templates/shot-grammar-v1.jsx').read_text(encoding='utf-8')
    (out/'build.jsx').write_text('var SG_INPUT='+json.dumps(dict(output=out.as_posix(),plan=plan),ensure_ascii=True)+';\n'+grammar+'\n'+template,encoding='utf-8')
    render=(ROOT/'ae/templates/shot-grammar-render.jsx').read_text(encoding='utf-8')
    (out/'render.jsx').write_text('var SHOT_PREVIEW_OUTPUT='+json.dumps(out.as_posix(),ensure_ascii=True)+';\n'+render,encoding='utf-8')
    print(json.dumps(dict(output=str(out)),ensure_ascii=True))


if __name__=='__main__':main()
