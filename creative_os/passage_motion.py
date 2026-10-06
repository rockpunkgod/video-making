"""Hold native scenes until the bound phrase is spoken; do not slow animations."""
import math
from pathlib import Path
from video_contracts import read,sha
from .passage_delivery import timing_centres


def resolve_motion(plan,anchors,voice_root,presentation_sha,orders=None):
    scenes={}
    for scene in plan['scenes']:
        sid=scene['segment_id'];voice=scene['voice'];diagnostic=read(Path(voice_root)/sid/'asr.json')
        if diagnostic['audio_sha']!=voice['sha256']:raise ValueError('Motion uses stale audio timing')
        phrases=anchors[sid]
        count=len(scene['annotations'])+(scene['kind']=='closure')
        if len(phrases)!=count or count>4:raise ValueError('Motion anchor/event count mismatch')
        expected=['source_'+str(i) for i in range(len(scene['annotations']))]+(['verdict'] if scene['kind']=='closure' else [])
        order=(orders or {}).get(sid,expected)
        if sorted(order)!=sorted(expected):raise ValueError('Motion order must preserve each bound event exactly once')
        authored,centres=timing_centres(voice['text'],diagnostic,voice['duration'])
        events=[];previous=-.25
        for i,phrase in enumerate(phrases):
            if voice['text'].count(phrase)!=1:raise ValueError('Motion phrase must be one exact frozen narration span: '+phrase)
            position=voice['text'].index(phrase)
            index=next(k for k,(at,_) in enumerate(authored) if at>=position)
            estimate=centres[index]+scene['voice_start']
            # Native events are 18 frames apart, each animation lasts 12 frames.
            native=.5+i*.75;latest=scene['duration']-.75-(count-1-i)*.75
            target=math.ceil(max(previous+.75,min(estimate,latest))*24)/24
            if target>latest+1e-7:raise ValueError('Narration cannot safely fit this motion clock')
            events.append({'native_start':native,'start':target,'phrase':phrase,
                'voice_text_span':[position,position+len(phrase)],'timing':'ASR_anchor_estimate',
                'purpose':order[i],
                'quote':scene['annotations'][int(order[i].split('_')[1])]['quote'] if order[i]!='verdict' else scene['screen']})
            previous=target
        scenes[sid]=events
    result={'version':'0.2.0','plan_sha':plan['plan_sha'],'presentation_sha':presentation_sha,
            'anchors':anchors,'orders':orders or {},'scenes':scenes,'public_render_ready':False}
    result['motion_sha']=sha(result);return result


def validate_motion(motion,plan,voice_root):
    expected=resolve_motion(plan,motion['anchors'],voice_root,motion['presentation_sha'],motion['orders'])
    if expected!=motion:raise ValueError('Stale motion or unsupported annotation')


def time_expression(events):
    expression='PTS';previous_delay=0
    for event in events:
        delay=event['start']-event['native_start'];extra=delay-previous_delay
        if extra<-.000001:raise ValueError('Native animation cannot be accelerated or reversed')
        expression+=f"+if(gte(T,{event['native_start']}),{max(0,extra):.9f}/TB,0)"
        previous_delay=delay
    return expression
