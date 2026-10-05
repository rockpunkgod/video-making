"""One piano bed, explicit recording rights, and a small Premiere gain envelope."""
import math
from creative_os.hero import file_sha
from video_contracts import sha


LISTENING_QUESTIONS = (
    'Does music compete with voice?', 'Does it add texture?',
    'Does it feel pretentious?', 'Are Evidence/Stop transitions natural?',
    'Does removing it lose atmosphere?',
)


def recording_manifest(path, *, title, composer, performer, source,
                       license='unknown', license_evidence=None):
    evidence = license_evidence or []
    # A filename, composer, or caller boolean is never a recording license.
    return {'title': title, 'composer': composer, 'performer': performer,
            'recording_source': source, 'file_sha': file_sha(path),
            'license': license, 'license_evidence': evidence,
            'public_use_allowed': False, 'status': 'SCRATCH_MUSIC',
            'music_license_gate': 'HOLD', 'human_listening_review': 'PENDING',
            'listening_questions': list(LISTENING_QUESTIONS)}


def gain_envelope(anchors, duration, steps=6):
    """Sample slow cosine ramps in amplitude; native PR stores the resulting keys.

    Levels are an engineering starting point, never a human listening PASS.
    Times are clip-relative. The last key must be inside the visible clip.
    """
    if (len(anchors) < 2 or anchors[0][0] != 0 or anchors[-1][0] >= duration
            or not isinstance(steps, int) or steps < 1):
        raise ValueError('Envelope must start at zero and end inside the clip')
    if any(not math.isfinite(v) for pair in anchors for v in pair):
        raise ValueError('Finite music automation required')
    if any(a[0] >= b[0] for a, b in zip(anchors, anchors[1:])):
        raise ValueError('Music times must strictly increase')
    if any(t < 0 or db > 0 or db < -96 for t, db in anchors):
        raise ValueError('Background levels must be between -96 and 0 dB')
    keys = []
    for index, ((start, a), (end, b)) in enumerate(zip(anchors, anchors[1:])):
        for step in range(steps + 1):
            if index and not step:
                continue
            mix = (1 - math.cos(math.pi * step / steps)) / 2
            amplitude = (1-mix)*10**(a/20) + mix*10**(b/20)
            keys.append({'time_seconds': start+(end-start)*step/steps,
                         'level_db': 20*math.log10(amplitude)})
    return keys


def apply_music(router, sequence_id, node_id, effect_name, property_name, keys):
    """Use the upstream localized effect property; no private Adobe script bridge."""
    for key in keys:
        result = router.execute('add_keyframe', {
            'node_id': node_id, 'effect_name': effect_name, 'property_name': property_name,
            'time_seconds': key['time_seconds'],
            'value': 10 ** ((key['level_db'] - 15) / 20),
        }, sequence_id=sequence_id)
        if not result.get('stored') or result.get('keyframesOutsideVisibleRange'):
            raise ValueError('Music automation not verified within the visible clip')
    actual = router.execute('get_keyframes', {
        'node_id': node_id, 'effect_name': effect_name, 'property_name': property_name,
    }, sequence_id=sequence_id)
    return {'plan_sha': sha(keys), 'native_readback': actual,
            'human_listening_review': 'PENDING', 'public_render_ready': False}
