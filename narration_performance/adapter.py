"""Honest GPT-SoVITS capability projection; no model imports or emotion API."""
from copy import deepcopy
import math

from video_contracts import sha
from .plan import check_intent

CAPABILITIES = {'tone': 'indirect_reference_only_not_used_in_v0.1', 'energy': 'unsupported',
    'pace': 'bounded_inference_speed_factor', 'certainty': 'unsupported', 'emphasis': 'unsupported',
    'pause': 'premiere', 'reference_bank': 'reserved_not_enabled'}
SPEED_MIN, SPEED_MAX = .96, 1.05


def speed_for(pace):
    return round(max(SPEED_MIN, min(SPEED_MAX, 1 + (pace - .5) * .25)), 4)


def check_speed(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not SPEED_MIN <= value <= SPEED_MAX:
        raise ValueError('Performance speed_factor must be finite within 0.96..1.05')


def take_requests(plan, profile, base_request):
    """Only supported controls vary; Profile tail repair always stays exact."""
    if profile['engine'] != 'gpt-sovits/v2ProPlus':
        raise ValueError('This optional adapter requires the current GPT-SoVITS backend')
    check_speed(base_request['speed_factor'])
    seed = base_request['seed']
    if type(seed) is not int or seed < 0:
        raise ValueError('Performance trials require an explicit nonnegative seed')
    rows = []
    for clip in plan['clips']:
        check_intent(clip['intent'], clip['transcript'])
        for index in range(clip['take_policy']['count']):
            take_id = clip['id'] + '-take-' + 'ABC'[index]
            # A follows the conservative pace map. B is a constant-speed fallback
            # for listening; C repeats mapped pace with another explicit seed.
            speed = 1.0 if index == 1 else speed_for(clip['intent']['pace'])
            check_speed(speed)
            request = dict(base_request, text=clip['transcript'], speed_factor=speed, seed=seed+index)
            for key in ('text_split_method', 'fragment_interval', 'ref_audio_path', 'prompt_text', 'prompt_lang'):
                if request[key] != base_request[key]:
                    raise ValueError('Performance may not silently override Profile tail or reference controls')
            realization = {key: {'status': 'UNREALIZED', 'reason': 'No direct reliable backend control; no reference change'}
                           for key in ('tone', 'energy', 'certainty', 'emphasis')}
            realization['pace'] = {'status': 'APPROXIMATED', 'control': 'speed_factor', 'value': speed,
                'reason': 'Inference control applied; perceived delivery and identity require listening'}
            for key in ('pause_before_ms', 'pause_after_ms'):
                realization[key] = {'status': 'UNREALIZED', 'reason': 'Pending fresh Premiere timing; not inserted by TTS'}
            rows.append({'id': take_id, 'scene_id': clip['scene_id'], 'request': request,
                'intent': deepcopy(clip['intent']), 'intent_realization': realization,
                'sampling_note': 'Seed variation is sampling diversity, never emotional control',
                'listening_review': 'PENDING'})
    return rows


def generation_take(row, audio, transcript, profile_sha, assets_sha, performance_sha, parameters):
    """One independent receipt per Take, outside voice-delivery/v1."""
    result = {'schema': 'narration-performance-take/v1', 'take_id': row['id'], 'scene_id': row['scene_id'],
        'performance_sha': performance_sha, 'profile_sha': profile_sha, 'assets_sha256': deepcopy(assets_sha),
        'audio_sha256': audio['audio_sha256'], 'transcript_sha256': audio['transcript_sha256'],
        'transcript_sha': sha(transcript), 'duration_seconds': audio['duration_seconds'],
        'performance_intent': deepcopy(row['intent']), 'engine_realization': deepcopy(row['intent_realization']),
        'engine_capabilities': deepcopy(CAPABILITIES), 'inference_parameters': deepcopy(parameters),
        'speed_factor_applied': True, 'postproduction_time_stretch': False,
        'sampling_note': row['sampling_note'], 'listening_review': 'PENDING',
        'final_voice_accepted': False, 'sample_delivery_allowed': False, 'public_render_ready': False}
    result['take_receipt_sha'] = sha(result)
    return result


def verify_take(receipt, row, clip, plan, generation):
    expected_params = {k: v for k, v in row['request'].items() if k not in ('text', 'ref_audio_path', 'prompt_text')}
    transcript = next(c['transcript'] for c in plan['clips'] if c['scene_id'] == row['scene_id'])
    expected = generation_take(row, clip, transcript, generation['profile_sha256'],
        generation['assets_sha256'], plan['performance_sha'], expected_params)
    if receipt != expected:
        raise ValueError('Take receipt changed audio, transcript, reference, controls or pending listening state')


def verify_realization(plan, delivery_path):
    from pathlib import Path
    from scripts.voice_delivery import asset, sha256, validate
    from video_contracts import read
    root = Path(delivery_path).resolve().parent
    delivery = validate(delivery_path)
    generation = read(root / 'generation.json')
    realized = read(root / 'performance-realization.json')
    if (realized.get('realization_sha') != sha({k: v for k, v in realized.items() if k != 'realization_sha'})
            or realized['performance_sha'] != plan['performance_sha'] or realized['binding'] != plan['binding']
            or realized['delivery_sha256'] != sha256(delivery_path)
            or realized['generation_sha256'] != sha256(root / 'generation.json')
            or realized['profile_sha256'] != generation['profile_sha256']
            or realized['assets_sha256'] != generation['assets_sha256']
            or realized['engine_capabilities'] != CAPABILITIES):
        raise ValueError('Performance realization or generation binding changed')
    for field in ('final_voice_accepted', 'sample_delivery_allowed', 'public_render_ready'):
        if realized[field] is not False:
            raise ValueError('A generated Take cannot inherit acceptance or release')
    if realized['listening_review'] != 'PENDING' or generation['listening_review'] != 'PENDING':
        raise ValueError('New Take listening must remain PENDING')
    base = dict(generation['inference_parameters'], ref_audio_path='HASH_BOUND_REFERENCE',
                prompt_text='HASH_BOUND_REFERENCE_TEXT')
    rows = take_requests(plan, {'engine': generation['engine']}, base)
    if ([c['id'] for c in delivery['clips']] != [r['id'] for r in rows]
            or [c['take_id'] for c in realized['takes']] != [r['id'] for r in rows]
            or [t['id'] for t in generation['takes']] != [r['id'] for r in rows]):
        raise ValueError('Performance Take IDs and voice-delivery clips do not align')
    receipts = {}
    for row, clip, ref, generated in zip(rows, delivery['clips'], realized['takes'], generation['takes']):
        path = asset(root, ref['receipt'])
        receipt = read(path)
        if (ref['receipt_sha256'] != sha256(path) or ref['take_receipt_sha'] != receipt['take_receipt_sha']
                or ref['scene_id'] != row['scene_id'] or clip['listening_review'] != 'PENDING'
                or asset(root, clip['transcript']).read_text(encoding='utf-8-sig') != row['request']['text']):
            raise ValueError('Take transcript, receipt or listening binding changed')
        verify_take(receipt, row, clip, plan, generation)
        if (generated['inference_parameters'] != receipt['inference_parameters']
                or generated['duration_seconds'] != clip['duration_seconds']):
            raise ValueError('Generation receipt differs from actual Take controls or duration')
        receipts[row['id']] = receipt
    return delivery, generation, realized, receipts
