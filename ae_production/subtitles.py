"""Independent subtitle output on the existing authored clock; no new renderer."""
from pathlib import Path
import shutil

from video_contracts import read, write
from scripts.voice_delivery import sha256


def inspect_mode(folder):
    folder=Path(folder);author=read(folder/'AV_AUTHOR.json')
    mode=author.get('subtitle_mode','burned_in')
    native=folder/'native-identity.json';readback=folder/'NATIVE_READBACK.json'
    actual=read(readback) if readback.exists() else None
    layers=[r for r in actual.get('layers',[]) if r['name'].startswith('CAPTION_') and r['name']!='CAPTION_SAFE_AREA'] if actual else None
    identity=read(native) if native.exists() else None
    current=(identity is not None and (folder/'AV_PLAN.json').exists()
        and identity.get('plan_sha256')==sha256(folder/'AV_PLAN.json')
        and read(folder/'AV_PLAN.json').get('author_sha256')==sha256(folder/'AV_AUTHOR.json'))
    return {'schema':'subtitle-mode-inspection/v1','revision':author['revision'],
        'configured_mode':mode,'native_caption_layer_count':len(layers) if layers is not None else None,
        'native_evidence':str(readback) if actual else None,'native_plan_binding_current':current,
        'native_mode':('burned_in' if layers else 'no_ae_caption_layers') if current and actual else None,
        'encoded_pixel_verification':None,'encoded_pixel_missing_reason':'This read-only command inspects saved engineering receipts; it does not infer text from encoded pixels',
        'premiere_caption_receipt':str(folder/'PR_CAPTIONS.json') if (folder/'PR_CAPTIONS.json').exists() else None,
        'srt_path':str(folder/'EPISODE_SUBTITLES.srt') if (folder/'EPISODE_SUBTITLES.srt').exists() else None}


def validate_native_captions(plan,layers):
    by_name={row['name']:row for row in layers}
    captions={name:row for name,row in by_name.items() if name.startswith('CAPTION_') and name!='CAPTION_SAFE_AREA'}
    if plan.get('subtitle_mode','burned_in')=='premiere_sidecar':
        if captions:raise ValueError('Sidecar revision still contains AE caption layers')
        return {'mode':'premiere_sidecar','native_caption_layers':0,'caption_content':'EXTERNAL_SRT'}
    if set(captions)!={'CAPTION_'+c['id'] for c in plan['cues']}:
        raise ValueError('Native caption inventory differs from the actual cue clock')
    for cue in plan['cues']:
        row=captions['CAPTION_'+cue['id']]
        if (row['text'].replace('\r','\n')!='\n'.join(cue['display_lines'])
                or abs(row['inPoint']-cue['start'])>1e-4 or abs(row['outPoint']-cue['end'])>1e-4):
            raise ValueError('Caption text or audio clock changed')
    return {'mode':'burned_in','native_caption_layers':len(captions)}


def deliver_sidecar(folder,video):
    folder=Path(folder);video=Path(video);plan=read(folder/'AV_PLAN.json')
    if plan.get('subtitle_mode')!='premiere_sidecar':return None
    source=folder/'EPISODE_SUBTITLES.srt';target=video.with_suffix('.srt')
    if target.exists() and sha256(target)!=sha256(source):
        raise FileExistsError('Inspect mismatched subtitle delivery; never overwrite another revision')
    if not target.exists():shutil.copyfile(source,target)
    receipt={'mode':'premiere_sidecar','video':str(video),'video_sha256':sha256(video),
        'srt':str(target),'srt_sha256':sha256(target),'plan_sha256':sha256(folder/'AV_PLAN.json'),
        'cue_count':len(plan['cues']),'picture_contains_captions':False,
        'picture_binding':'Native caption absence plus unchanged native picture packets in package QA',
        'premiere_readback':str(folder/'PR_CAPTIONS.json'),'timing_basis':'CURRENT_UNCHANGED_COMPLETE_TAKES',
        'future_recording_alignment':'NOT_APPLIED_NO_NEW_RECORDING_SUPPLIED'}
    write(folder/'SUBTITLE_DELIVERY.json',receipt)
    return receipt
