"""Measured voice timing in the existing picture; never trim or stretch speech."""
from copy import deepcopy
import math
from pathlib import Path
import shutil
import subprocess

from scripts.voice_delivery import asset, describe_clip, pad_to_video_frame, sha256, validate
from video_contracts import read, sha, write
from .adapter import verify_realization
from .plan import load_context, validate_plan


def resolve_timing(performance, spec, delivery_path):
    delivery_path = Path(delivery_path).resolve(); delivery = validate(delivery_path)
    if [c['id'] for c in delivery['clips']] != [c['id'] for c in performance['clips']]:
        raise ValueError('Selected voice-delivery IDs must match the Performance Plan exactly')
    slots = spec['direction']['voice_slots']; fps = spec['direction']['canvas']['fps']
    if [s['scene_id'] for s in slots] != [c['scene_id'] for c in performance['clips']]:
        raise ValueError('Current Voice Slot coverage changed')
    duration = spec['direction']['canvas']['duration']; protected = spec['direction']['silence_candidates']
    rows = []; previous_end = 0; previous_after = 0
    for clip, direction, slot in zip(delivery['clips'], performance['clips'], slots):
        transcript = asset(delivery_path.parent, clip['transcript']).read_text(encoding='utf-8-sig')
        if transcript != direction['transcript'] or sha(transcript) != direction['transcript_sha']:
            raise ValueError('Performance rendering changed the exact transcript')
        intent = direction['intent']
        start = max(slot['start'] + intent['pause_before_ms']/1000, previous_end + previous_after)
        start = math.ceil(start*fps-1e-8)/fps
        # Existing cognitive silence takes precedence; pauses coalesce instead
        # of stacking another wait on top of an already protected silence.
        for silence in sorted(protected, key=lambda s: s['start']):
            if start < silence['end'] and silence['start'] < start + clip['duration_seconds']:
                start = math.ceil(silence['end']*fps-1e-8)/fps
        end = start + clip['duration_seconds']
        if end > slot['end'] + 1e-7 or end + intent['pause_after_ms']/1000 > duration + 1e-7:
            raise ValueError('RETIMING_REQUIRED: voice/Stop cannot fit its visual window; never truncate or stretch')
        rows.append({'id': clip['id'], 'scene_id': direction['scene_id'], 'start': start, 'end': end,
            'duration': clip['duration_seconds'], 'audio_sha256': clip['audio_sha256'],
            'transcript_sha': sha(transcript), 'window': [slot['start'], slot['end']],
            'window_lead_ms': round((start-slot['start'])*1000, 3),
            'pause_before_ms_actual': round((start-previous_end)*1000, 3),
            'pause_before_ms_intent': intent['pause_before_ms'], 'pause_after_ms_intent': intent['pause_after_ms'],
            'pause_realization': 'APPROXIMATED_frame_quantized_minimum_with_existing_visual_silence'})
        previous_end, previous_after = end, intent['pause_after_ms']/1000
    for index, row in enumerate(rows):
        next_start = rows[index+1]['start'] if index+1 < len(rows) else duration
        row['pause_after_ms_actual'] = round((next_start-row['end'])*1000, 3)
    stop_events = [s for s in performance['silence_events'] if s['event'] == 'boundary_seal']
    stamp = spec['direction']['phases']['stamp']
    stop_hold = stamp-rows[-1]['end']
    if stop_events and stop_hold + 1e-7 < max(s['duration_seconds'] for s in stop_events):
        raise ValueError('RETIMING_REQUIRED: silent Stop hold cannot be erased')
    result = {'schema': 'narration-performance-timing/v1', 'performance_sha': performance['performance_sha'],
        'binding': deepcopy(performance['binding']), 'delivery_sha256': sha256(delivery_path), 'fps': fps,
        'duration': duration, 'clips': rows, 'protected_silence': deepcopy(protected),
        'stop_hold_seconds_before_stamp': round(stop_hold, 6), 'picture_retimed': False,
        'timing_status': 'FRESH_MEASURED_CLIPS_FIT_EXISTING_PICTURE',
        'caption_cues': [{'scene_id': c['scene_id'], 'start': r['start'], 'end': r['end'],
                         'text': c['transcript'], 'transcript_sha': c['transcript_sha']}
                        for c,r in zip(performance['clips'], rows)],
        'caption_timing_scope': 'whole_clip_measured_not_word_alignment_not_rendered_new_captions',
        'prior_timing_approval_reused': False, 'editorial_review': 'PENDING', 'listening_review': 'PENDING',
        'final_voice_accepted': False, 'sample_delivery_allowed': False, 'public_render_ready': False}
    result['timing_sha'] = sha(result)
    return result


def prepare(request):
    """Select engineering candidates, resample/pad, and use the existing PR consumer."""
    from premiere_production.student_picture import preflight
    from premiere_production.student_voice import bind_voice
    copy, spec = load_context(request)
    performance = validate_plan(read(request['performance_plan']), copy, spec)
    prepared_spec, picture, music = preflight(read(request['prepared_request']))
    if prepared_spec != spec:
        raise ValueError('Performance and existing Premiere picture bindings differ')
    raw_path = Path(request['raw_delivery']).resolve()
    raw, generation, realization, receipts = verify_realization(performance, raw_path)
    baseline = read(request['baseline_generation'])
    if (generation['profile_sha256'] != baseline['profile_sha256']
            or generation['assets_sha256'] != baseline['assets_sha256']):
        raise ValueError('R02 A/B must retain baseline weights, reference and Profile')
    selected = request['selected_takes']
    if set(selected) != {c['id'] for c in performance['clips']}:
        raise ValueError('Every actual Voice Slot needs exactly one selected Take')
    by_id = {c['id']: c for c in raw['clips']}
    for clip in performance['clips']:
        take = selected[clip['id']]
        if take not in receipts or receipts[take]['scene_id'] != clip['scene_id']:
            raise ValueError('Selected Take belongs to another scene or is missing')
    out = Path(request['output']).resolve(); out.mkdir(parents=True, exist_ok=False)
    native = out / 'resampled'; native.mkdir()
    final = out / 'voice'; final.mkdir()
    clips, selections = [], []
    for direction in performance['clips']:
        take_id = selected[direction['id']]; raw_clip = by_id[take_id]
        name = direction['id']; source = asset(raw_path.parent, raw_clip['audio'])
        target = native / (name+'.wav'); padded = final / (name+'.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(source), '-ar', '48000',
                        '-ac', '1', '-c:a', 'pcm_s16le', str(target)], check=True)
        padding = pad_to_video_frame(target, padded)
        shutil.copyfile(asset(raw_path.parent, raw_clip['transcript']), final / (name+'.txt'))
        clips.append(describe_clip(final, name, name+'.wav', name+'.txt'))
        selections.append({'scene_id': name, 'take_id': take_id, 'source_audio_sha256': raw_clip['audio_sha256'],
            'take_receipt_sha': receipts[take_id]['take_receipt_sha'], 'padding': padding})
    write(final / 'delivery.json', {'schema': 'voice-delivery/v1', 'clips': clips})
    selection = {'schema': 'narration-performance-selection/v1', 'performance_sha': performance['performance_sha'],
        'raw_delivery_sha256': sha256(raw_path), 'realization_sha': realization['realization_sha'],
        'clips': selections, 'basis': 'ENGINEERING_CANDIDATE_NOT_HUMAN_PREFERENCE',
        'listening_review': 'PENDING', 'final_voice_accepted': False,
        'sample_delivery_allowed': False, 'public_render_ready': False}
    selection['selection_sha'] = sha(selection); write(out / 'selection.json', selection)
    timing = resolve_timing(performance, spec, final / 'delivery.json')
    voice = bind_voice(spec, final / 'delivery.json',
        [{'id': c['id'], 'start': c['start']} for c in timing['clips']], music['silence_candidates'])
    write(out / 'voice-plan.json', voice)
    write(out / 'performance-timing.json', timing)
    production = {key: request[key] for key in
                  ('prepared_request', 'project', 'video_output', 'export_preset', 'export_preset_sha')}
    production.update(output=str(out / 'premiere'), voice_plan=str(out / 'voice-plan.json'),
        performance_context=str(Path(request['context_file']).resolve()),
        performance_timing=str(out / 'performance-timing.json'), performance_selection=str(out / 'selection.json'))
    write(out / 'voice-preview-request.json', production)
    return production


def validate_handoff(production, voice, spec):
    """Optional independent sidecar: voice-delivery/v1 itself remains unchanged."""
    context = read(production['performance_context'])
    copy, current_spec = load_context(context)
    performance = validate_plan(read(context['performance_plan']), copy, current_spec)
    if current_spec != spec:
        raise ValueError('Performance sidecar changed production spec')
    raw_path = Path(context['raw_delivery']).resolve()
    raw, generation, realized, receipts = verify_realization(performance, raw_path)
    baseline = read(context['baseline_generation'])
    if generation['profile_sha256'] != baseline['profile_sha256'] or generation['assets_sha256'] != baseline['assets_sha256']:
        raise ValueError('A/B reference or model changed')
    selected = read(production['performance_selection'])
    if (selected['selection_sha'] != sha({k:v for k,v in selected.items() if k != 'selection_sha'})
            or selected['performance_sha'] != performance['performance_sha']
            or selected['raw_delivery_sha256'] != sha256(raw_path)
            or selected['realization_sha'] != realized['realization_sha']
            or selected['basis'] != 'ENGINEERING_CANDIDATE_NOT_HUMAN_PREFERENCE'
            or selected['listening_review'] != 'PENDING'
            or any(selected[k] is not False for k in ('final_voice_accepted','sample_delivery_allowed','public_render_ready'))):
        raise ValueError('Performance selection binding or pending state changed')
    if [s['scene_id'] for s in selected['clips']] != [c['id'] for c in performance['clips']]:
        raise ValueError('Selected scene IDs changed')
    raw_by_id = {c['id']: c for c in raw['clips']}
    for selected_clip, output_clip in zip(selected['clips'], voice['voices']):
        take_id = selected_clip['take_id']
        if (take_id != context['selected_takes'][selected_clip['scene_id']]
                or receipts[take_id]['scene_id'] != selected_clip['scene_id']
                or selected_clip['source_audio_sha256'] != raw_by_id[take_id]['audio_sha256']
                or selected_clip['take_receipt_sha'] != receipts[take_id]['take_receipt_sha']
                or selected_clip['padding']['output_sha256'] != output_clip['sha256']):
            raise ValueError('Selected voice differs from its actual generated Take')
    expected = resolve_timing(performance, spec, voice['delivery'])
    if read(production['performance_timing']) != expected:
        raise ValueError('Audio length changed; fresh performance timing required')
    if [(c['id'],c['start'],c['end']) for c in expected['clips']] != [(c['id'],c['start'],c['end']) for c in voice['voices']]:
        raise ValueError('Performance timing differs from native voice placement')
    return expected
