"""Independent V9 profile; the historical vertical builder remains unchanged."""
from copy import deepcopy
import hashlib
from jsonschema import Draft202012Validator
from video_contracts import ROOT, read, sha
from creative_os.delivery import semantic_guard, human_voice_critic
from creative_os.director import build_shot_plan
from creative_os.timing import validate_track, audio_info, cue_sheet, track_payload

TEMPLATE=ROOT/'ae/templates/cinematic-landscape-master-v0.3.jsx'

def schema_check(name,value):
    Draft202012Validator(read(ROOT/'creative/schemas'/f'{name}.json')).validate(value)

def build_landscape_contract(package,manifest,statuses,delivery,track,plan,audio,sheet,revision=1,check=True):
    semantic_guard(delivery,package,manifest,statuses);validate_track(track,delivery)
    if any(not u['audio_path'] or u['duration_kind']!='measured_scratch_tts_not_human_recording' for u in track['units']):
        raise ValueError('Render requires measured scratch audio for every delivery unit')
    if human_voice_critic(delivery)['status']=='AI_TONE_WARNING':raise ValueError('AI tone warning')
    expected=build_shot_plan(package,manifest,statuses,delivery,track,plan['design'])
    if expected!=plan:raise ValueError('Shot plan changed outside director')
    if cue_sheet(delivery,track)!=sheet:raise ValueError('Audio cue sheet drift')
    if (audio_info(audio['path'])!={k:audio[k] for k in ('duration','sample_rate','frames','sha256')}
        or audio['audio_timing_sha']!=track['audio_timing_sha'] or audio['cue_sheet_sha']!=sha(sheet)):
        raise ValueError('Final scratch audio binding drift')
    if abs(audio['duration']-plan['duration'])>1/audio['sample_rate']:raise ValueError('Audio duration drift')
    template_sha=hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    # JSON formatting and platform line endings are not schema semantics.
    schemas={p.name:sha(read(p)) for p in (ROOT/'creative/schemas').glob('*.json')}
    lock={k:delivery[k] for k in ('teaching_semantic_sha','delivery_copy_sha','screen_copy_sha')}
    lock.update(audio_timing_sha=track['audio_timing_sha'],editorial_review_sha=None)
    # Paths are transport diagnostics. Identity uses measured audio and canonical timing contents.
    identity={'package_sha':sha(package),'delivery_sha':sha(delivery),'plan_sha':sha(plan),'audio_timing':sha(track_payload(track)),
              'audio_sha':audio['sha256'],'cue_sheet_sha':sha(sheet),'template_sha':template_sha,'schemas':schemas,'revision':revision}
    tags=[]
    for sel in package['selections']:
        b=next(b for b in package['source_items'] if b['asset_id']==sel['asset_id'])
        m=next(m for m in b['methods'] if m['method_id']==sel['method_id'])
        role=next(s['role'] for s in b['analysis']['method_chain'] if s['method_id']==sel['method_id'])
        tags.append(m['brand_name']+' · '+m['method_id']+' / '+role)
    result={'schema_version':'0.1.0','version':'0.3.0','render_id':'render:'+sha(identity),'package_id':package['package_id'],
        'package_sha':sha(package),'manifest_sha':sha(manifest),'delivery_id':delivery['delivery_id'],'delivery_sha':sha(delivery),
        'shot_plan':deepcopy(plan),'shot_plan_sha':sha(plan),'narration_track':deepcopy(track),'audio':deepcopy(audio),'audio_cue_sheet':deepcopy(sheet),
        'copy_lock':lock,'canvas':{**plan['design']['canvas'],'duration':plan['duration']},'template_family':'CINEMATIC_LANDSCAPE_MASTER',
        'template_version':'0.3.0','template_sha':template_sha,'usage':'INTERNAL_CREATIVE_PREVIEW','public_render_ready':False,
        'status_input_shas':{k:sha(v) for k,v in statuses.items()},'upstream_bindings':{b['asset_id']:b['semantic_binding_sha'] for b in package['source_items']},
        'schema_shas':schemas,'revision':revision,'method_tags':' + '.join(tags),
        'review_status':{'teaching':'PENDING','source':'PENDING','editorial':'PENDING','human_taste':'PENDING'}}
    for name,value in [('delivery-copy',delivery),('narration-track',track),('shot-plan',plan),('landscape-render-contract',result)]:schema_check(name,value)
    if check:validate_landscape(result,package,manifest,statuses,delivery)
    return result

def validate_landscape(contract,package,manifest,statuses,delivery):
    expected=build_landscape_contract(package,manifest,statuses,delivery,contract['narration_track'],contract['shot_plan'],
        contract['audio'],contract['audio_cue_sheet'],contract['revision'],check=False)
    expected['status_input_shas']=contract['status_input_shas']
    if expected!=contract:raise ValueError('Landscape contract changed or stale')
    return True
