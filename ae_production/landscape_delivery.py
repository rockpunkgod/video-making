"""Collect frozen inputs and measured voice dependencies without changing render identity."""
from copy import deepcopy
from pathlib import Path
import shutil
from video_contracts import sha, write
from .landscape import validate_landscape, build_landscape_contract


def collect(contract, package, manifest, statuses, delivery, preview, output_dir):
    validate_landscape(contract,package,manifest,statuses,delivery)
    out=Path(output_dir).resolve()
    if out.exists():raise ValueError('Delivery directory already exists; preserve previous delivery')
    out.mkdir(parents=True);audio_dir=out/'audio';audio_dir.mkdir()
    track=deepcopy(contract['narration_track'])
    for t in track['units']:
        dest=audio_dir/(t['unit_id']+'.wav');shutil.copyfile(t['audio_path'],dest);t['audio_path']=str(dest)
    audio=deepcopy(contract['audio']);dest=out/'scratch-voice.wav';shutil.copyfile(audio['path'],dest);audio['path']=str(dest)
    relocated=build_landscape_contract(package,manifest,statuses,delivery,track,contract['shot_plan'],audio,
        contract['audio_cue_sheet'],contract['revision'])
    if relocated['render_id']!=contract['render_id']:raise ValueError('Diagnostic relocation changed render identity')
    for name,value in [('video-package',package),('manifest',manifest),('delivery-copy',delivery),
                       ('statuses',statuses),('landscape-render-contract',relocated),('narration-track',track),
                       ('shot-plan',contract['shot_plan']),('audio-cue-sheet',contract['audio_cue_sheet'])]:write(out/(name+'.json'),value)
    shutil.copyfile(preview,out/'INTERNAL_CREATIVE_PREVIEW.mp4')
    request={'package':str(out/'video-package.json'),'manifest':str(out/'manifest.json'),'delivery':str(out/'delivery-copy.json'),
             'contract':str(out/'landscape-render-contract.json'),'statuses':{}}
    for aid,st in statuses.items():
        status_path=out/('status-'+sha(aid)[:12]+'.json');write(status_path,st);request['statuses'][aid]=str(status_path)
    write(out/'replay-request.json',request)
    return relocated
