"""Audience experience and measured narration timing on existing native assets.

This is an editorial contract, not a teaching compiler or solver. Real recipes,
copy reviews, object IDs and media remain local. Existing source modules stay
unchanged; public and human-review gates cannot be released by this adapter.
"""
import hashlib
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading_pacing as pacing
from video_contracts import sha

FPS = 24


def reference(document, pointer):
    value = document
    for key in pointer.lstrip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return {'pointer': pointer, 'value_sha': sha(value)}


def validate_copy(script, source, review):
    if script.get('source_binding') != source['semantic_binding_sha']:
        raise ValueError('Copy must bind the exact current frozen source')
    seen = set()
    for row in script['clips']:
        if not row['id'] or row['id'] in seen or not row['text'].strip():
            raise ValueError('Unique nonempty cognitive voice slots required')
        seen.add(row['id'])
        if not row['source_refs']:
            raise ValueError('Every new line requires explicit source references')
        for ref in row['source_refs']:
            if reference(source, ref['pointer']) != ref:
                raise ValueError('Source reference changed')
        if row['authority'] not in ('existing_action', 'direct_text_review', 'locating_trace',
                                    'question', 'editorial_navigation', 'existing_boundary'):
            raise ValueError('No new teaching authority')
        if row.get('answer_claim') and row['authority'] != 'direct_text_review':
            raise ValueError('Location and interpretation cannot acquire answer permission')
        if not row.get('reading_task') or not row.get('beat_id'):
            raise ValueError('A clip must serve an identified audience task')
    if (review.get('script_sha') != sha(script) or
            review.get('status') != 'approved_for_internal_scratch' or
            not review.get('reviewer') or review.get('reviewer_kind') != 'ai_host' or
            review.get('human_review') != 'PENDING' or
            review.get('public_render_ready') is not False):
        raise ValueError('Exact editorial scratch review required; it is not teaching certification')
    return script


def validate_experience(beats, source, events):
    seen = set()
    for beat in beats:
        if beat['beat_id'] in seen or beat['pass'] not in ('fast', 'guided', 'entry', 'rewind', 'memory'):
            raise ValueError('Unique audience beat and supported pass required')
        seen.add(beat['beat_id'])
        for ref in beat['source_refs']:
            if reference(source, ref['pointer']) != ref:
                raise ValueError('Audience contract cannot become a fact source')
        if not beat['source_refs'] or not beat['source_event_refs']:
            raise ValueError('Existing source/event lineage required')
        for ref in beat['source_event_refs']:
            if reference(events, ref['pointer']) != ref:
                raise ValueError('Native event binding changed')
        if not beat['viewer_state']['current_goal'] or not beat['presentation']['reading_task']:
            raise ValueError('No taskless holds')
        if not beat['learning']['boundary_preserved']:
            raise ValueError('Preserve the frozen scope')
        if beat['pass'] == 'guided' and not beat.get('what_guided_adds'):
            raise ValueError('Guided replay needs distinct decision/reading value')
        clocks = beat['clocks']
        for key in ('action', 'attention', 'comprehension'):
            a, b = clocks[key]
            if type(a) is not int or type(b) is not int or not 0 <= a <= b:
                raise ValueError('Versioned integer frame clocks required')
    return beats


def fit_voice(mapping, placements, durations, safe_holds, fps=FPS):
    """Add only settled native holds when complete speech outlasts a beat.

    Placements use historical frame indices. Measured WAV duration is never
    shortened, sped up or used to overwrite an already occupied voice slot.
    """
    mapping = list(mapping)
    result, insertions = [], []
    for slot in sorted(placements, key=lambda x: x['base_start_frame']):
        identity = slot['id']
        measured = durations[identity]
        if type(measured) not in (int, float) or not math.isfinite(measured) or measured <= 0:
            raise ValueError('Measured complete speech duration required')
        a, b = slot['base_start_frame'], slot['base_end_frame']
        if not 0 <= a < b <= max(mapping) + 1:
            raise ValueError('Voice slot outside historical picture')
        start = mapping.index(a)
        end = next((n for n, i in enumerate(mapping) if i == b), len(mapping))
        speech_frames = math.ceil(measured * fps - 1e-8)
        tail = slot.get('settle_frames', 12)
        if type(tail) is not int or tail < 0:
            raise ValueError('Nonnegative cognitive settle required')
        extra = max(0, speech_frames + tail - (end - start))
        if extra:
            hold = slot['safe_hold_frame']
            if hold not in safe_holds or not a <= hold < b:
                raise ValueError('A verified stationary hold inside the beat is required')
            at = max(n for n, i in enumerate(mapping) if i == hold) + 1
            mapping[at:at] = [hold] * extra
            # Earlier placements cannot straddle a later inserted hold.
            if any(r['end_frame'] > at for r in result):
                raise ValueError('New hold would invalidate preceding voice placement')
            insertions.append({'voice_id': identity, 'source_frame': hold, 'frames': extra,
                               'reason': 'complete measured speech and cognitive settle'})
            end += extra
        if result and result[-1]['end_frame'] > start:
            raise ValueError('Cognitive voice beats cannot overlap')
        result.append({'id': identity, 'start_frame': start, 'end_frame': start + speech_frames,
                       'slot_end_frame': end, 'duration_seconds': measured,
                       'speech_tempo_changed': False, 'speech_cut': False})
    return mapping, result, insertions


def verify_stationary(frames, frame):
    from PIL import Image
    files = [Path(frames) / f'FRAME_{i:05}.tif' for i in (frame - 1, frame, frame + 1)]
    pixels = [hashlib.sha256(Image.open(f).convert('RGB').tobytes()).hexdigest() for f in files]
    if len(set(pixels)) != 1:
        raise ValueError('Do not freeze a moving or changing evidence frame')
    return {'source_frame': frame, 'neighbours': [frame - 1, frame, frame + 1], 'rgb_sha': pixels[0]}
