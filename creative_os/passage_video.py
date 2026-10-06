"""Long-form scene projection of frozen ANSWER copy, never authoring teaching."""
import math
from pathlib import Path
import re
from video_contracts import sha,read
from video_contracts.passage import require_current
from creative_os.hero import file_sha

VERSION='0.1.0'


def wrap(text, font, width):
    """Only line breaks are added. Word wrapping preserves all source characters."""
    lines=[]
    for paragraph in text.split('\n'):
        tokens=re.findall(r'(?:\d+(?:,\d+)*(?:\.\d+)?\s+(?:percent|milligrams)|\S+)\s*',paragraph) if ' ' in paragraph else list(paragraph)
        line=''
        for token in tokens:
            if line and font.getlength((line+token).rstrip())>width:
                lines.append(line.rstrip());line=token
            else:line+=token
        lines.append(line.rstrip())
    return '\n'.join(lines)


def scene_layout(bundle, segment, fonts, emphasis=()):
    from PIL import ImageFont
    p=bundle['payload'];q=next(q for q in p['questions'] if q['question_id']==segment['question_id'])
    source='\n'.join(e['quote'] for e in segment['evidence'] if e['field']=='passage')
    english=ImageFont.truetype(fonts['english'],42)
    chinese=ImageFont.truetype(fonts['chinese'],52)
    stemfont=ImageFont.truetype(fonts['chinese'],38)
    source_lines=wrap(source,english,1620)
    if len(source_lines.splitlines())>4: raise ValueError('Source excerpt too dense; revise upstream segment')
    stem=wrap(q['stem'],stemfont,1620)
    if len(stem.splitlines())>2: raise ValueError('Question exceeds persistent header')
    screen=wrap(segment['screen_text'],chinese,800)
    if len(screen.splitlines())>4: raise ValueError('Bound teaching text exceeds lower reading field')
    decisions=p['review']['decisions'];own=[decisions[i] for i in segment['decision_refs']]
    states={d['candidate']:d['effect'] for d in own}
    option_font=ImageFont.truetype(fonts['chinese'],30)
    options=[{'letter':k,'text':wrap(k+'  '+v,option_font,650),
              'state':states.get(k,'neutral') if segment['kind'] in ('comparison','closure') else 'neutral'}
             for k,v in q['options'].items()]
    if any(len(o['text'].splitlines())>2 for o in options): raise ValueError('Option too dense')
    annotations=[]
    for quote in emphasis:
        matches=[(i,line.index(quote),line) for i,line in enumerate(source_lines.splitlines()) if quote in line]
        if len(matches)!=1: raise ValueError('Highlight must identify one exact visible source span')
        row,start,line=matches[0]
        annotations.append({'line':row,'prefix':line[:start],'quote':quote})
    if len(annotations)>4: raise ValueError('Annotation motion budget exceeded')
    return {'segment_id':segment['segment_id'],'question_id':q['question_id'],'number':q['number'],
            'kind':segment['kind'],'heading':'2025 全国一卷 · 阅读 D · '+str(q['number'])+' 题',
            'stem':stem,'source':source_lines,'screen':screen,'options':options,
            'segment_sha':sha(segment),'annotations':annotations,'public_render_ready':False}


def prepare(bundle,status,voice_root,fonts,emphasis=None):
    require_current(bundle,status); scenes=[];at=0
    for segment in bundle['payload']['review']['segments']:
        receipt=read(Path(voice_root)/segment['segment_id']/'receipt.json')
        if receipt['text']!=segment['text'] or receipt['sha256']!=file_sha(receipt['path']):
            raise ValueError('Voice differs from frozen copy')
        if receipt.get('lesson_binding_sha')!=bundle['semantic_binding_sha']:
            raise ValueError('Voice belongs to a different lesson binding')
        scene=scene_layout(bundle,segment,fonts,(emphasis or {}).get(segment['segment_id'],[]))
        # Conservative full-source reading allowance is explicit; timing is an estimate.
        reading=len(re.findall(r'\S+',scene['source']))/2.5
        duration=math.ceil(max(receipt['duration']+1.25,reading+1)*24)/24
        scene.update(start=at,duration=duration,voice=receipt,voice_start=.4,
                     timing_kind='recorded_voice_plus_estimated_screen_reading')
        scenes.append(scene);at+=duration
    result={'version':VERSION,'kind':'internal_longform_passage','lesson_binding_sha':bundle['semantic_binding_sha'],
        'bundle_sha':sha(bundle),'source_sha':sha(bundle['payload']['source']),
        'copy_sha':sha(bundle['payload']['review']['segments']),'scenes':scenes,
        'canvas':{'width':1920,'height':1080,'fps':24,'duration':at},'fonts':fonts,'emphasis':emphasis or {},
        'font_shas':{k:file_sha(v) for k,v in fonts.items()},
        'public_render_ready':False,'human_editorial_review':'PENDING'}
    result['plan_sha']=sha(result);return result


def validate_plan(plan,bundle,status):
    require_current(bundle,status)
    unhashed={k:v for k,v in plan.items() if k!='plan_sha'}
    if sha(unhashed)!=plan['plan_sha'] or plan['lesson_binding_sha']!=bundle['semantic_binding_sha']:
        raise ValueError('Stale lesson plan')
    if plan['copy_sha']!=sha(bundle['payload']['review']['segments']) or plan['public_render_ready'] is not False:
        raise ValueError('Copy lock or internal usage drift')
    if plan['canvas']['width']!=1920 or plan['canvas']['height']!=1080 or plan['canvas']['fps']!=24:
        raise ValueError('Unexpected long-form canvas')
    if plan['font_shas']!={k:file_sha(v) for k,v in plan['fonts'].items()}:
        raise ValueError('Font changed')
    at=0;segments=bundle['payload']['review']['segments']
    if len(plan['scenes'])!=len(segments): raise ValueError('Incomplete passage')
    for scene,segment in zip(plan['scenes'],segments):
        expected=scene_layout(bundle,segment,plan['fonts'],plan['emphasis'].get(segment['segment_id'],[]))
        if any(scene[k]!=v for k,v in expected.items()): raise ValueError('Scene projection changed')
        voice=scene['voice']
        if (voice['text']!=segment['text'] or file_sha(voice['path'])!=voice['sha256']
                or voice.get('lesson_binding_sha')!=bundle['semantic_binding_sha']):
            raise ValueError('Voice changed')
        if (not math.isfinite(scene['duration']) or scene['voice_start']!=.4
                or abs(scene['duration']*24-round(scene['duration']*24))>1e-6
                or abs(scene['start']-at)>1e-7 or scene['duration']<voice['duration']+scene['voice_start']):
            raise ValueError('Invalid timing or clipped voice')
        at+=scene['duration']
    if abs(at-plan['canvas']['duration'])>1e-7: raise ValueError('Duration mismatch')
