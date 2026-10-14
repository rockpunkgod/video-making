"""P4 internal episode assembly from frozen bundles, authored copy and existing WAVs."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sys
import wave

from ae_production.candidate_motion import audit_candidate_events
from scripts.voice_delivery import asset, validate as validate_voice
from video_contracts import read, write, sha, pointer, status_matches
from .typeset import typeset

ROOT = Path(__file__).resolve().parents[1]


def reference(bundle, path):
    return dict(asset_id=bundle['asset_id'], pointer=path, sha=sha(pointer(bundle,path)))


def frames(seconds, fps=24):
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0:
        raise ValueError('Finite nonnegative timing required')
    return math.ceil(seconds*fps-1e-8)


def caption_parts(text,font_path,size,width=1650):
    """Display-only partition. Concatenation must reconstruct the exact transcript."""
    from PIL import ImageFont
    font=ImageFont.truetype(str(font_path),size); result=[]; current=''
    tokens=re.findall(r'[A-Za-z0-9]+(?:[’\'-][A-Za-z0-9]+)*|[^A-Za-z0-9]',text)
    for token in tokens:
        if current and font.getlength(current+token)>width:
            result.append(current);current=''
        current+=token
        if token in '。！？；':result.append(current);current=''
    if current:result.append(current)
    if ''.join(result)!=text:raise ValueError('Caption lexical drift')
    return result


def build_episode(request):
    """Consume an explicit edit list; select neither methods, evidence nor answers."""
    style = read(request['style']); fps=style['coordinates']['fps']
    if fps != 24:
        raise ValueError('Current voice frame padding requires 24 fps')
    bundles = {k:read(v['bundle']) for k,v in request['sources'].items()}
    statuses = {k:read(v['status']) for k,v in request['sources'].items()}
    for key,bundle in bundles.items():
        status=statuses[key]
        if not status_matches(bundle,status) or status['effective_status'] not in ('ACTIVE','INCOMPLETE'):
            raise ValueError('Current provided upstream status invalid: '+key)
    delivery_path=Path(request['voice_delivery']).resolve()
    delivery=validate_voice(delivery_path)
    clips={c['id']:c for c in delivery['clips']}
    authored=read(request['authored_copy'])
    exact={}
    for scene in authored:
        spoken=scene['vo']
        for index,text in enumerate(spoken):
            key=scene['scene_id'] if len(spoken)==1 else scene['scene_id']+('-prepare' if index==0 else '-confirm')
            exact[key]=text
    if set(clips)!=set(exact):
        raise ValueError('Delivery must match the exact authored voice slots')
    for key,c in clips.items():
        if asset(delivery_path.parent,c['transcript']).read_text(encoding='utf-8-sig')!=exact[key]:
            raise ValueError('Frozen copy differs from voice transcript')
        with wave.open(str(asset(delivery_path.parent,c['audio']))) as media:
            if (media.getframerate(),media.getnchannels(),media.getsampwidth())!=(48000,1,2) or media.getnframes()%2000:
                raise ValueError('Use existing 48 kHz PCM16 frame-padded voice handoff')
    result=[]; cursor=0; voices=[]; events=[]; answers=[]; used=set(); scene_ids=set(); decisions={}
    for item in request['edit']:
        if not item.get('id') or item['id'] in scene_ids:raise ValueError('Unique scene ids required')
        scene_ids.add(item['id'])
        row=deepcopy(item); b=bundles[item['source']]; row['asset_id']=b['asset_id']
        if item.get('pass_label') not in (None,'原速','慢放'):raise ValueError('Unsupported pass label')
        if item['kind'] not in ('question','evidence','comparison','result','recall','chapter'):
            raise ValueError('Unknown episode shot kind')
        texts=[]
        for ref in item['display_refs']:
            if ref['asset_id']!=b['asset_id'] or sha(pointer(b,ref['pointer']))!=ref['sha']:
                raise ValueError('Changed or cross-question display reference')
            value=pointer(b,ref['pointer'])
            if not isinstance(value,str):raise ValueError('Display refs must bind literal text')
            texts.append(value)
        row['display_texts']=texts
        row['start_frame']=cursor; local=frames(item.get('lead',.5))
        clip_ids=item.get('voice_ids',[])
        for key in clip_ids:
            if key in used or key not in clips:
                raise ValueError('Voice slot reused or missing')
            used.add(key); c=clips[key]
            voices.append(dict(id=key,path=str(asset(delivery_path.parent,c['audio'])),text=exact[key],
                audio_sha256=c['audio_sha256'],transcript_sha256=c['transcript_sha256'],
                start_frame=cursor+local,end_frame=cursor+local+frames(c['duration_seconds']),
                duration=c['duration_seconds'],listening_review='PENDING',
                caption_parts=caption_parts(exact[key],request.get('fallback_font',request['font']),style['type_scale']['caption'])))
            local+=frames(c['duration_seconds'])+frames(item.get('gap',.35))
        span=max(1,frames(item.get('minimum_seconds',2)),local+frames(item.get('tail',.7)))
        row['end_frame']=cursor+span
        if item['kind']=='evidence':
            source=b['source_snapshot']['passage']; a,z=item['range']
            if type(a) is not int or type(z) is not int or not 0<=a<z<=len(source):
                raise ValueError('Invalid original evidence slice')
            action=pointer(b,item['action_ref']['pointer'])
            if (not item['action_ref']['pointer'].startswith('/source_snapshot/action_executions/')
                    or item['action_ref']['asset_id']!=b['asset_id'] or sha(action)!=item['action_ref']['sha']):
                raise ValueError('Changed actual action')
            if not any(e['field']=='passage' and e['start']<=a<z<=e['end'] for e in action['evidence']):
                raise ValueError('Lift must be inside existing actual action evidence')
            row['excerpt']=source[a:z]
            row['layout']=typeset(source,request['font'],style,fallback_font_path=request.get('fallback_font'))
            hits=[w for w in row['layout']['words'] if w['start']<z and a<w['end']]
            if not hits:raise ValueError('Missing visible source glyphs')
            lo=hits[0]['line']; hi=hits[-1]['line']
            if hi-lo>=style['layout']['focus_max_lines']:raise ValueError('Evidence exceeds one readable focus window')
            row['focus_line_start']=max(0,lo-2)
            row['focus_line_end']=row['focus_line_start']+style['layout']['focus_max_lines']
            row['excerpt_layout']=typeset(row['excerpt'],request['font'],style,role='lifted_block',
                                         fallback_font_path=request.get('fallback_font'))
        if item['kind']=='comparison':
            index=item['action_index']; action=b['source_snapshot']['action_executions'][index]
            row['action_ref']=reference(b,f'/source_snapshot/action_executions/{index}')
            row['candidate']=action['output']['candidate']; row['effect']=action['output']['effect']
            if (len(item['display_refs'])<2 or item['display_refs'][1]['pointer']!=
                    '/source_snapshot/options/'+row['candidate']):
                raise ValueError('Comparison must display the exact candidate of its action')
            row['evidence']=deepcopy([e for e in action['evidence'] if e['field']=='passage'])
            source=b['source_snapshot']['passage']
            if not row['evidence'] or any(source[e['start']:e['end']]!=e['quote'] for e in row['evidence']):
                raise ValueError('Evidence quote differs from frozen original')
            # Confirming narration follows the visible judgement, never precedes it.
            confirmation=next(v for v in voices if v['id']==clip_ids[-1])['start_frame'] if clip_ids else cursor+span-frames(1)
            decision=confirmation-frames(.5)
            if decision<=cursor:raise ValueError('Comparison needs observation before judgement')
            event=dict(scene_id=item['id'],question_id=b['source_snapshot']['question_id'],
                source_refs=[row['action_ref']],candidate=row['candidate'],effect=row['effect'],
                compare_start=cursor/fps,decision_start=decision/fps,
                decision_end=(decision+style['motion']['actions']['eliminate']['frames'])/fps,
                confirmation_start=confirmation/fps)
            row['decision_frame']=decision-cursor
            if item.get('replay_of'):
                old=decisions.get(item['replay_of'])
                if not old or old!=row['action_ref']:raise ValueError('Replay must bind an earlier identical frozen action')
                row['replay_does_not_change_candidate_state']=True
            else:
                events.append(event);decisions[item['id']]=row['action_ref']
            # Use full literal evidence rows; no summary generated by the renderer.
            row['comparison_layouts']=[typeset(e['quote'],request['font'],style,role='option',
                                              fallback_font_path=request.get('fallback_font')) for e in row['evidence']]
        if item['kind']=='result' and item.get('answer'):
            ref=reference(b,'/analysis/answer')
            if item['answer']!=pointer(b,'/analysis/answer'):raise ValueError('Answer changed')
            answers.append(dict(candidate=item['answer'],time=cursor/fps,source_ref=ref))
        result.append(row);cursor+=span
    if used!=set(clips):raise ValueError('Every existing voice slot must appear once')
    checked=audit_candidate_events(events,{b['asset_id']:b for b in bundles.values()},answers)
    return dict(schema='episode-handoff/v1',fps=fps,duration_frames=cursor,duration=cursor/fps,
        style=style,scenes=result,voices=voices,candidate_audit=checked,answers=answers,
        bindings=dict(script_sha=sha(authored),style_sha=sha(style),request_sha=sha(request),
                      source_shas={k:sha(v) for k,v in bundles.items()},status_shas={k:sha(v) for k,v in statuses.items()}),
        listening_review='PENDING',final_voice_accepted=False,public_render_ready=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args(); plan=build_episode(read(args.request)); out=args.output.resolve()
    if not out.is_relative_to(ROOT/'local-data'):raise ValueError('Keep real source/media in ignored local-data')
    out.mkdir(parents=True,exist_ok=False);write(out/'EPISODE_HANDOFF.json',plan)
    data=dict(output=out.as_posix(),plan=plan)
    template=(ROOT/'ae/templates/episode-handoff.jsx').read_text(encoding='utf-8')
    (out/'build.jsx').write_text('var EPISODE_PREVIEW='+json.dumps(data,ensure_ascii=True)+';\n'+template,encoding='utf-8')
    render=(ROOT/'ae/templates/shot-handoff-render.jsx').read_text(encoding='utf-8')
    render=render.replace('P3_PREVIEW.aep','P4_EPISODE.aep').replace('P3_PREVIEW_4K.mp4','P4_PICTURE_1080.mp4').replace('P3_PREVIEW_4K','P4_INTERNAL_PICTURE').replace('40 Mbps','15 Mbps')
    (out/'render.jsx').write_text('var SHOT_PREVIEW_OUTPUT='+json.dumps(out.as_posix(),ensure_ascii=True)+';\n'+render,encoding='utf-8')
    print(out/'build.jsx')


if __name__=='__main__':main()
