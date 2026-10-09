"""Read-only case projection extracted from the existing case adapter; no solver."""
import hashlib
from pathlib import Path
from video_contracts import sha
from video_contracts.passage import require_current

QUESTION='gaokao-2025-I-q33'
SEGMENTS=('s06','s07','s08','s09','s10')


def file_sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def project(bundle,status):
    require_current(bundle,status);p=bundle['payload'];r=p['review']
    qi,q=next((i,q) for i,q in enumerate(p['questions']) if q['question_id']==QUESTION)
    actions=[(i,a) for i,a in enumerate(r['method_actions']) if a['question_id']==QUESTION]
    if len(actions)!=1 or actions[0][1]['action_id']!='q33-R11-action':
        raise ValueError('Consume the existing single-action trace; review new assets separately')
    ai,a=actions[0];mi,m=next((i,m) for i,m in enumerate(p['methods']) if m['method_id']==a['method_id'])
    if a['role']!='interpreter' or a['answer'] is not None or a['method_version']!=m['version']:
        raise ValueError('An interpreter cannot acquire an answer or another method version')
    segments=[s for s in r['segments'] if s['question_id']==QUESTION]
    if tuple(s['segment_id'] for s in segments)!=SEGMENTS:
        raise ValueError('Preserve complete reviewed evidence, comparison, closure and boundary')
    decisions=[(i,d) for i,d in enumerate(r['decisions']) if d['question_id']==QUESTION]
    if len(decisions)!=4 or any(d['basis']!='direct_text_review' or d['method_id'] is not None for _,d in decisions):
        raise ValueError('Closure belongs to existing direct review, not a method')
    retained=[d['candidate'] for _,d in decisions if d['effect']=='retain']
    if len(retained)!=1:raise ValueError('Explicit unique reviewed result required')
    return {'asset_id':bundle['asset_id'],'semantic_binding_sha':bundle['semantic_binding_sha'],
        'source_sha':sha(p['source']),'question':q,'question_pointer':'/payload/questions/'+str(qi),
        'action':a,'action_pointer':'/payload/review/method_actions/'+str(ai),
        'method':m,'method_pointer':'/payload/methods/'+str(mi),'segments':segments,
        'decisions':[{'index':i,**d} for i,d in decisions],'review_sha':sha(r),
        'answer':retained[0],'method_count':1,'strict_two_method_relay':'HOLD',
        'source_status':p['source'],'review_level':bundle['semantic_review'],
        'passage':p['passage'],'public_render_ready':False}
