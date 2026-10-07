"""Add a replaceable voice-delivery/v1 take to an internal Student POV preview.

The consumer has no speech-model imports. New voices do not inherit listening,
editorial, teaching or public-release approval from picture preparation.
"""
import argparse
from array import array
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

from creative_os.hero import file_sha
from scripts.voice_delivery import asset, validate as validate_delivery
from video_contracts import read, sha, write
from .student_picture import preflight as picture_preflight, client_for, audit as audit_picture
from .student_picture import inspect_preview_media
from .music import verify_gain_keys


def bind_voice(spec, delivery_path, placements, protected_silence):
    delivery_path = Path(delivery_path).resolve(); delivery = validate_delivery(delivery_path)
    slots = spec['direction']['voice_slots']; clips = delivery['clips']
    if ([c['id'] for c in clips] != [s['scene_id'] for s in slots]
            or [p['id'] for p in placements] != [c['id'] for c in clips]):
        raise ValueError('Voice must cover the exact spoken scenes once and in order')
    duration = spec['direction']['canvas']['duration']; voices = []; previous = 0
    for clip, slot, placement in zip(clips, slots, placements):
        text = asset(delivery_path.parent, clip['transcript']).read_text(encoding='utf-8-sig')
        if text != slot['text']:
            raise ValueError('Voice transcript differs from the exact frozen Copy')
        start = placement['start']
        if type(start) not in (int, float) or not math.isfinite(start):
            raise ValueError('Voice placement must be finite')
        end = start + clip['duration_seconds']
        if not previous <= start < end <= duration:
            raise ValueError('Voice must not overlap, truncate or exceed the picture')
        if any(start < s['end'] and s['start'] < end for s in protected_silence):
            raise ValueError('Voice cannot erase the protected payoff silence')
        path = asset(delivery_path.parent, clip['audio'])
        with wave.open(str(path), 'rb') as media:
            if (media.getframerate(), media.getnchannels(), media.getsampwidth()) != (48000, 1, 2):
                raise ValueError('Native voice handoff requires 48 kHz mono PCM16')
            if media.getnframes() % 2000 or abs(start*24-round(start*24)) > 1e-7:
                raise ValueError('Pad tail silence to whole video frames; never truncate speech to fit')
        voices.append({'id': clip['id'], 'path': str(path), 'sha256': clip['audio_sha256'],
            'text': text, 'text_sha': sha(text), 'source_voice_slot_sha': sha(slot),
            'start': start, 'end': end, 'duration': clip['duration_seconds'],
            'level_db': 0, 'listening_review': 'PENDING'})
        previous = end
    plan = {'kind': 'student_pov_trial_voice', 'spec_sha': spec['spec_sha'],
        'final_copy_sha': spec['copy_lock']['final_copy_sha'], 'duration': duration,
        'delivery': str(delivery_path), 'delivery_sha': file_sha(delivery_path), 'voices': voices,
        'protected_silence': protected_silence, 'voice_status': 'GENERATED_TRIAL',
        'listening_review': 'PENDING', 'user_voice_ready_signal_received': False,
        'final_voice_accepted': False, 'sample_delivery_allowed': False, 'public_render_ready': False}
    plan['voice_plan_sha'] = sha(plan)
    return plan


def preflight(request):
    prepared = read(request['prepared_request'])
    spec, picture, audio = picture_preflight(prepared); plan = read(request['voice_plan'])
    if (plan['voice_plan_sha'] != sha({k: v for k, v in plan.items() if k != 'voice_plan_sha'})
            or plan['delivery_sha'] != file_sha(plan['delivery'])
            or plan['protected_silence'] != audio['silence_candidates']):
        raise ValueError('Trial voice input or silence binding changed')
    rebound = bind_voice(spec, plan['delivery'],
        [{'id': v['id'], 'start': v['start']} for v in plan['voices']], audio['silence_candidates'])
    if plan != rebound:
        raise ValueError('Trial voice must retain its exact Copy, placement and pending release state')
    return prepared, spec, picture, audio, plan


def inspect_timeline(state, settings, sequence_id, picture, audio, plan):
    if (state['id'] != sequence_id or state.get('pagination', {}).get('truncated')
            or abs(state['end'] - plan['duration']) > 1/48000
            or [settings[k] for k in ('frameSizeHorizontal', 'frameSizeVertical', 'timebase', 'audioSampleRateHz')]
            != [1920, 1080, '10584000000', 48000] or settings['audioChannelCount'] != 2):
        raise ValueError('Native voiced preview sequence identity/profile changed')
    expected_video = {0: [(picture['output'], 0, plan['duration'])]}
    expected_audio = {0: [(v['path'], v['start'], v['end']) for v in plan['voices']],
                      1: [(audio['music']['clip_path'], 0, plan['duration'])]}
    observed = []
    for kind, expected in (('videoTracks', expected_video), ('audioTracks', expected_audio)):
        if len(state[kind]) <= max(expected):
            raise ValueError('Native voiced preview required track missing')
        for i, track in enumerate(state[kind]):
            clips = track['clips']; targets = expected.get(i, [])
            if len(clips) != len(targets):
                raise ValueError('Native voiced preview clip coverage differs')
            for clip, (path, start, end) in zip(clips, targets):
                if (clip['name'] != Path(path).name or abs(clip['start']-start) > 1/48000
                        or abs(clip['end']-end) > 1/48000
                        or abs(clip['duration']-(end-start)) > 1/48000):
                    raise ValueError('Native voice placement or source duration changed')
                observed.append((clip, path, end-start))
    return observed


def native_audit(client, request):
    prepared, spec, picture, audio, plan = preflight(request)
    identity = read(Path(request['output']) / 'identity.json')
    project = client.call('get_project_info')
    expected = [picture['output'], audio['music']['clip_path']] + [v['path'] for v in plan['voices']]
    if (Path(project['path']).resolve() != Path(request['project']).resolve()
            or project['numSequences'] != 1 or project['numItems'] != len(expected)+1):
        raise ValueError('Active native trial project changed')
    state = client.call('get_active_sequence'); settings = client.call('get_sequence_settings')
    observed = inspect_timeline(state, settings, identity['sequence_id'], picture, audio, plan)
    items = client.call('list_project_items'); entries = items['items'] if isinstance(items, dict) else items
    media = [i for i in entries if i.get('mediaPath')]
    if len(media) != len(expected):
        raise ValueError('Unexpected source media in the native voiced preview')
    for path in expected:
        found = [i for i in media if Path(i['mediaPath']).resolve() == Path(path).resolve()]
        if len(found) != 1 or identity['item_ids'][Path(path).name] != found[0]['nodeId']:
            raise ValueError('Native source binding changed')
    props = []
    for clip, path, length in observed:
        p = client.call('get_clip_properties', {'node_id': clip['nodeId']})
        if (abs(p['inPoint']) > 1/48000 or abs(p['outPoint']-length) > 1/48000
                or abs(p['duration']-length) > 1/48000 or p['isSpeedReversed']):
            raise ValueError('Native voiced preview source range or speed changed')
        props.append(p)
    prop = prepared['music_property']
    keys = client.call('get_keyframes', {'node_id': state['audioTracks'][1]['clips'][0]['nodeId'], **prop})
    verify_gain_keys(keys, audio['music']['gain_keys'])
    voice_levels = []
    for clip in state['audioTracks'][0]['clips']:
        values = client.call('get_effect_properties', {'node_id': clip['nodeId'], 'effect_name': prop['effect_name']})
        level = next(p for p in values['properties'] if p['displayName'] == prop['property_name'])
        keyframes = client.call('get_keyframes', {'node_id': clip['nodeId'], **prop})
        if (abs(float(level['value'])-10**(-15/20)) > 1e-6 or keyframes.get('isTimeVarying')
                or keyframes.get('keyframes')):
            raise ValueError('Native trial voice must retain flat 0 dB without time automation')
        voice_levels.append(values)
    result = {'kind': 'internal_voiced_preview', 'spec_sha': spec['spec_sha'],
        'voice_plan_sha': plan['voice_plan_sha'], 'final_copy_sha': plan['final_copy_sha'],
        'project': request['project'], 'project_sha': file_sha(request['project']),
        'timeline': state, 'settings': settings, 'media_items': media,
        'clip_properties': props, 'music_keyframes': keys, 'voice_levels': voice_levels,
        'voice_status': 'GENERATED_TRIAL', 'listening_review': 'PENDING',
        'timing_alignment': 'actual_WAV_duration_and_native_placement_checked',
        'caption_alignment': 'PENDING', 'human_taste_review': 'PENDING',
        'user_voice_ready_signal_received': False, 'final_voice_accepted': False,
        'sample_delivery_allowed': False, 'teaching_release': 'HOLD',
        'source_display_release': 'HOLD', 'music_license_gate': 'HOLD',
        'editorial_release': 'HOLD', 'public_render_ready': False}
    write(Path(request['output']) / 'voiced-preview-audit.json', result)
    return result


def assemble(request):
    prepared, spec, picture, audio, plan = preflight(request)
    project = Path(request['project']).resolve(); out = Path(request['output']).resolve()
    if project.exists():
        raise ValueError('Preserve existing trial projects; inspect before resuming')
    before = audit_picture(prepared); old_sha = before['project_sha']
    out.mkdir(parents=True, exist_ok=True); client = client_for(prepared); log = []

    def mutate(name, inputs):
        preflight(request); write(out / 'pending-mutation.json', {'tool': name, 'inputs': inputs})
        try:
            result = client.call(name, inputs)
        except Exception:
            write(out / 'uncertain-mutation.json', {'tool': name, 'inputs': inputs,
                'next_action': 'inspect_native_state_before_retry'})
            raise
        log.append({'tool': name, 'inputs': inputs, 'result': result})
        write(out / 'edit-receipts.json', log)
        return result

    mutate('save_project_as', {'path': str(project)})
    if Path(client.call('get_project_info')['path']).resolve() != project:
        raise ValueError('Save As did not switch to the dedicated trial project')
    mutate('import_media', {'file_paths': [v['path'] for v in plan['voices']], 'suppress_ui': True})
    items = client.call('list_project_items'); entries = items['items'] if isinstance(items, dict) else items
    paths = [picture['output'], audio['music']['clip_path']] + [v['path'] for v in plan['voices']]
    ids = {}
    for path in paths:
        hits = [i for i in entries if i.get('mediaPath') and Path(i['mediaPath']).resolve() == Path(path).resolve()]
        if len(hits) != 1: raise ValueError('Native source identity is ambiguous')
        ids[Path(path).name] = hits[0]['nodeId']
    identity = {'project': str(project), 'sequence_id': client.call('get_active_sequence')['id'],
                'item_ids': ids, 'voice_plan_sha': plan['voice_plan_sha']}
    write(out / 'identity.json', identity)
    for voice in plan['voices']:
        mutate('overwrite_clip', {'item_id': ids[Path(voice['path']).name], 'start_seconds': voice['start'],
                                 'track_index': 0, 'audio_track_index': 0})
    state = client.call('get_active_sequence'); prop = prepared['music_property']
    for clip in state['audioTracks'][0]['clips']:
        mutate('set_effect_property', {'node_id': clip['nodeId'], **prop, 'value': 10**(-15/20)})
    mutate('rename_track', {'track_type': 'audio', 'track_index': 0, 'name': 'VO — newest model trial'})
    mutate('set_playhead_position', {'time_seconds': 0}); mutate('save_project', {})
    if file_sha(prepared['project']) != old_sha:
        raise ValueError('Original picture preparation project changed')
    write(out / 'prior-project-binding.json', {'path': prepared['project'], 'sha256': old_sha, 'unchanged': True})
    return native_audit(client, request)


def audit(request):
    return native_audit(client_for(read(request['prepared_request'])), request)


def inspect_rendered_voice(output, plan):
    """Check actual encoded voice presence; not pronunciation or listening QA."""
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output), '-vn',
        '-ar', '48000', '-ac', '1', '-f', 's16le', 'pipe:1'])
    decoded = array('h'); decoded.frombytes(data)
    if sys.byteorder != 'little': decoded.byteswap()
    rows = []
    for voice in plan['voices']:
        with wave.open(voice['path'], 'rb') as media:
            source = array('h'); source.frombytes(media.readframes(media.getnframes()))
        if sys.byteorder != 'little': source.byteswap()
        start = round(voice['start']*48000)
        # Native AAC can retain a codec-frame priming offset (1024 samples on
        # this host). Search only within one video frame; never accept arbitrary
        # relocation of a line as proof that it exists somewhere in the file.
        coarse = source[::64]
        norm_coarse = math.sqrt(math.fsum(x*x for x in coarse))
        def score(offset):
            begin = start+offset
            if begin < 0 or begin+len(source) > len(decoded): return -2
            candidate = decoded[begin:begin+len(source):64]
            norm = math.sqrt(math.fsum(x*x for x in candidate))
            return (math.fsum(x*y for x,y in zip(coarse,candidate))/(norm_coarse*norm)
                    if norm_coarse*norm else -2)
        center = max((i*64 for i in range(-31,32)), key=score)
        if score(center) < 0:
            raise ValueError('Encoded preview is missing, muting or shifting the bound voice')
        offset = max((i for i in range(center-63,center+64) if -2000 <= i <= 2000), key=score)
        observed = decoded[start+offset:start+offset+len(source)]
        if len(observed) != len(source): raise ValueError('Encoded preview truncated the actual voice')
        a, b = source[::8], observed[::8]
        norm_a = math.sqrt(math.fsum(x*x for x in a)); norm_b = math.sqrt(math.fsum(x*x for x in b))
        similarity = math.fsum(x*y for x, y in zip(a, b))/(norm_a*norm_b) if norm_a*norm_b else 0
        gain = norm_b/norm_a if norm_a else 0
        if similarity < .9 or not .2 <= gain <= 2:
            raise ValueError('Encoded preview is missing, muting or shifting the bound voice')
        rows.append({'id': voice['id'], 'start': voice['start'], 'waveform_correlation': similarity,
                     'decoded_relative_gain': gain, 'codec_offset_samples': offset,
                     'codec_offset_seconds': offset/48000})
    if max(r['codec_offset_samples'] for r in rows)-min(r['codec_offset_samples'] for r in rows) > 16:
        raise ValueError('Encoded voice lines have inconsistent timing offsets')
    return {'status': 'PASS_encoded_bound_voice_presence', 'voices': rows,
            'scope': 'signal_presence_not_pronunciation_or_listening_approval'}


def export(request):
    captured = audit(request); prepared, spec, picture, audio, plan = preflight(request)
    output = Path(request['video_output']).resolve(); preset = Path(request['export_preset']).resolve()
    if output.suffix.lower() != '.mp4' or Path(request['output']).resolve() not in output.parents:
        raise ValueError('Trial output must be a local MP4 in its own production directory')
    if output.exists(): raise ValueError('Preserve existing preview exports')
    if file_sha(preset) != request['export_preset_sha']:
        raise ValueError('Voiced preview export preset changed')
    client = client_for(prepared)
    validation = client.call('validate_export_preset', {'preset_path': str(preset)})
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output.with_suffix('.preflight.json'), dict(captured, preset_validation=validation))
    inputs = {'output_path': str(output), 'preset_path': str(preset), 'range': 'entire',
              'overwrite': False, 'timeout_minutes': 15}
    write(output.with_suffix('.pending.json'), {'tool': 'export_sequence', 'inputs': inputs})
    try:
        native = client.call('export_sequence', inputs, timeout=960)
    except Exception:
        write(output.with_suffix('.uncertain.json'), {'tool': 'export_sequence', 'inputs': inputs,
            'next_action': 'inspect_native_state_and_output_before_retry'})
        raise
    if sha(audit(request)) != sha(captured):
        raise ValueError('Voiced preview native state changed during export')
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-show_format', '-of', 'json', str(output)], encoding='utf-8'))
    inspect_preview_media(info, plan['duration'])
    result = dict(captured, output=str(output), output_sha=file_sha(output), native_export=native,
        media=info, encoded_voice_check=inspect_rendered_voice(output, plan),
        preview_export_performed=True, sample_export_performed=False)
    write(output.with_suffix('.receipt.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('assemble', 'audit', 'export')); parser.add_argument('request')
    args = parser.parse_args(); result = globals()[args.operation](read(args.request))
    print('Internal trial voice preview ready; listening and release reviews pending', flush=True)


if __name__ == '__main__': main()
