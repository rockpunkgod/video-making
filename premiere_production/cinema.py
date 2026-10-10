"""Native editorial conformance; no teaching or listening certification."""
import json
import math
import ntpath
from pathlib import Path
import subprocess
from .student_voice import inspect_rendered_voice


def resolve_media(items, paths):
    """Resolve actual local paths, never ambiguous duplicate display names."""
    result = {}
    for identity, path in paths.items():
        target = ntpath.normcase(ntpath.normpath(str(path)))
        if not ntpath.isabs(target) or target.startswith('\\\\'):
            raise ValueError('Explicit local absolute media path required')
        matches = [x for x in items if x.get('type') == 'clip'
                   and ntpath.normcase(ntpath.normpath(x.get('mediaPath', ''))) == target]
        if len(matches) != 1 or not matches[0].get('nodeId'):
            raise ValueError('Missing or ambiguous native media path: ' + identity)
        result[identity] = matches[0]['nodeId']
    return result


def reconcile_open(expected_path, fresh_project):
    if ntpath.normcase(ntpath.normpath(fresh_project['path'])) != ntpath.normcase(ntpath.normpath(str(expected_path))):
        raise ValueError('Open outcome still unknown; do not replay mutation')
    return {'status': 'CONFIRMED_CURRENT_PROJECT', 'scope': 'fresh host readback; not retroactive tool success'}


def audit_timeline(sequence, settings, voices, expected_duration):
    for voice in voices:
        if any(type(voice.get(k)) not in (int, float) or not math.isfinite(voice[k])
               for k in ('start', 'end')) or not 0 <= voice['start'] < voice['end'] <= expected_duration:
            raise ValueError('Explicit finite narration coordinates required')
    if sequence.get('pagination', {}).get('truncated') is not False:
        raise ValueError('Complete native timeline readback required')
    if sequence['id'] != settings['id']:
        raise ValueError('Sequence changed between reads')
    if (settings['frameSizeHorizontal'], settings['frameSizeVertical'], settings['audioSampleRateHz']) != (3840, 2160, 48000):
        raise ValueError('4K / 48kHz native sequence required')
    if abs(settings['videoFrameRate']['seconds']-1/24) > 1e-10 or abs(sequence['end']-expected_duration) > 1e-6:
        raise ValueError('Frame rate or complete duration changed')
    actual = sequence['audioTracks'][0]['clips']
    if len(actual) != len(voices):
        raise ValueError('Missing or additional narration')
    for expected in voices:
        matches = [x for x in actual if x['name'] == expected.get('native_name', expected['id'])]
        if len(matches) != 1:
            raise ValueError('Unique narration identity required')
        observed = matches[0]
        for key in ('start', 'end'):
            if not math.isfinite(observed[key]) or abs(observed[key]-expected[key]) > 1e-6:
                raise ValueError('Narration shifted or truncated')
    return {'status': 'PASS_NATIVE_TIMELINE', 'voice_count': len(voices), 'human_review': 'PENDING'}


def audit_encoded(output, voice_plan, duration):
    output = Path(output)
    if not output.is_file():
        raise ValueError('Native export missing')
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
        '-show_streams', '-show_format', '-of', 'json', str(output)], encoding='utf-8'))
    video = [s for s in info['streams'] if s['codec_type'] == 'video']
    audio = [s for s in info['streams'] if s['codec_type'] == 'audio']
    if len(video) != 1 or len(audio) != 1:
        raise ValueError('Exactly one video and audio stream required')
    v, a = video[0], audio[0]
    if (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) != (3840, 2160, '24/1', round(duration*24)):
        raise ValueError('Encoded picture does not match native timeline')
    if int(a['sample_rate']) != 48000 or a['channels'] != 2 or abs(float(v['duration'])-duration) > 1/24000:
        raise ValueError('Encoded audio format or picture duration changed')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
    return {'status': 'PASS_ENCODED_CONFORMANCE', 'media': info,
        'voice_presence': inspect_rendered_voice(output, voice_plan),
        'listening_review': 'PENDING', 'public_render_ready': False}
