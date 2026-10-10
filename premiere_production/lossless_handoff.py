"""Keep an already-final picture and native editorial audio without re-encoding.

Caller must verify its native timeline is an unchanged full-length picture.
This checks stream preservation, not editing intent or publication approval.
"""
import json
import subprocess
from pathlib import Path

from content_os.showcase import file_sha
from video_contracts import sha


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)]))['streams']


def packet_binding(path, selector):
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', selector,
        '-show_packets', '-show_data_hash', 'sha256', '-show_entries',
        'packet=pts_time,dts_time,duration_time,data_hash', '-of', 'json', str(path)]))['packets']
    if not data or any('data_hash' not in p for p in data):
        raise ValueError('Missing encoded packet identity')
    return {'count': len(data), 'sha': sha(data)}


def rec709_binding(path):
    frame = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-read_intervals', '%+#1', '-show_frames', '-show_entries',
        'frame=color_range,color_space,color_primaries,color_transfer',
        '-of', 'json', str(path)]))['frames'][0]
    keys = ('color_range', 'color_space', 'color_primaries', 'color_transfer')
    if [frame.get(k) for k in keys] != ['tv', 'bt709', 'bt709', 'bt709']:
        raise ValueError('Final picture requires explicit limited Rec.709 metadata')
    return {k: frame[k] for k in keys}


def assemble(picture, editorial_export, target, expected_frames):
    picture, editorial_export, target = map(lambda p: Path(p).resolve(),
        (picture, editorial_export, target))
    if target.exists() or target in (picture, editorial_export):
        raise FileExistsError('Preserve existing source and delivery revisions')
    if not isinstance(expected_frames, int) or isinstance(expected_frames, bool) or expected_frames <= 0:
        raise ValueError('Explicit positive frame count required')
    inputs = {str(p): file_sha(p) for p in (picture, editorial_export)}
    duration = expected_frames / 24
    p_streams, e_streams = probe(picture), probe(editorial_export)
    if len(p_streams) != 1 or p_streams[0]['codec_type'] != 'video':
        raise ValueError('An isolated final picture is required')
    video = p_streams[0]
    editorial_v = [s for s in e_streams if s['codec_type'] == 'video']
    editorial_a = [s for s in e_streams if s['codec_type'] == 'audio']
    if len(editorial_v) != 1 or len(editorial_a) != 1 or len(e_streams) != 2:
        raise ValueError('One native editorial video and audio stream required')
    for v in (video, editorial_v[0]):
        if [v['width'], v['height'], v['r_frame_rate'], int(v['nb_frames'])] != [3840, 2160, '24/1', expected_frames]:
            raise ValueError('Whole 4K/24 picture coverage differs')
        if abs(float(v['duration']) - duration) > 1/48000:
            raise ValueError('Picture duration differs')
    audio = editorial_a[0]
    if (audio['codec_name'], int(audio['sample_rate']), audio['channels']) != ('aac', 48000, 2):
        raise ValueError('Native stereo 48 kHz AAC editorial required')
    if abs(float(audio['duration']) - duration) > 1024/48000:
        raise ValueError('Native editorial audio duration differs')
    color = rec709_binding(picture)
    original_video = packet_binding(picture, 'v:0')
    original_audio = packet_binding(editorial_export, 'a:0')
    target.parent.mkdir(parents=True, exist_ok=True)
    command = ['ffmpeg', '-v', 'error', '-n', '-i', str(picture),
        '-i', str(editorial_export), '-map', '0:v:0', '-map', '1:a:0',
        '-c', 'copy', '-movflags', '+faststart+write_colr', str(target)]
    subprocess.run(command, check=True)
    if original_video != packet_binding(target, 'v:0') or original_audio != packet_binding(target, 'a:0'):
        raise ValueError('Encoded payload or packet timing changed; inspect rejected output')
    if rec709_binding(target) != color:
        raise ValueError('Final Rec.709 binding changed')
    if any(file_sha(p) != digest for p, digest in inputs.items()):
        raise ValueError('Input changed during handoff')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'], check=True)
    return {'schema': 'lossless-picture-editorial-handoff/v1', 'inputs': inputs,
        'output': str(target), 'output_sha': file_sha(target), 'command': command,
        'frames': expected_frames, 'duration': duration, 'decoded_color': color,
        'video_packets': original_video, 'audio_packets': original_audio,
        'encoded_payload_and_timestamps': 'UNCHANGED', 'full_decode': 'PASS',
        'human_taste_review': 'PENDING', 'listening_review': 'PENDING',
        'final_voice_accepted': False, 'public_render_ready': False}
