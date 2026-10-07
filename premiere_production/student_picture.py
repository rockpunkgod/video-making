"""Prepare a native editing project while reserving an empty final-voice track.

This entry point deliberately has no sample export operation. Final audio,
alignment, listening, and user delivery remain a subsequent task.
"""
import argparse
import json
from pathlib import Path
import subprocess
import wave

from video_contracts import read, sha, write
from creative_os.hero import file_sha
from ae_production.student_picture import preflight as picture_preflight, TEMPLATE
from .mcp import PremiereMcpClient
from .music import apply_music
from .router import BackendRouter


def preflight(request):
    production = read(request['production']); spec = picture_preflight(production)
    receipt = read(request['picture_receipt']); audio = read(request['audio_plan'])
    duration = spec['direction']['canvas']['duration']
    if (receipt['spec_sha'] != spec['spec_sha'] or receipt['audio'] is not False
            or receipt['renderer'] != 'native_AE_TIFF' or receipt['duration'] != duration
            or receipt['sample_delivery_allowed'] is not False
            or receipt['public_render_ready'] is not False
            or receipt['template_sha'] != file_sha(TEMPLATE)
            or receipt['project_sha'] != file_sha(receipt['project'])
            or receipt['output_sha'] != file_sha(receipt['output'])):
        raise ValueError('Current picture preparation/media binding changed')
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                               '-of', 'json', receipt['output']], encoding='utf-8'))
    streams = info['streams']
    if (len(streams) != 1 or streams[0]['codec_type'] != 'video'
            or [streams[0][k] for k in ('width', 'height', 'r_frame_rate')] != [1920, 1080, '24/1']
            or abs(float(streams[0]['duration'])-duration) > 1e-4):
        raise ValueError('Picture-only media does not match the preparation profile')
    if (audio['audio_plan_sha'] != sha({k: v for k, v in audio.items() if k != 'audio_plan_sha'})
            or audio['spec_sha'] != spec['spec_sha'] or audio['duration'] != duration
            or audio['final_copy_sha'] != spec['copy_lock']['final_copy_sha']
            or audio['voice']['status'] != 'AWAITING_USER_AUDIO' or audio['voice']['path'] is not None
            or audio['voice']['audio_track_index'] != 0 or audio['music']['audio_track_index'] != 1
            or audio['sample_delivery_allowed'] is not False or audio['public_render_ready'] is not False):
        raise ValueError('Picture preparation must retain the empty final-voice gate')
    music = audio['music']
    if file_sha(music['source_path']) != music['file_sha'] or file_sha(music['clip_path']) != music['clip_sha']:
        raise ValueError('Local piano recording binding changed')
    with wave.open(music['clip_path'], 'rb') as media:
        if ((media.getframerate(), media.getnchannels(), media.getsampwidth()) != (48000, 2, 2)
                or media.getnframes() != round(duration * 48000)):
            raise ValueError('Music bed duration/sample profile changed')
    return spec, receipt, audio


def inspect_timeline(state, settings, identity, receipt, audio):
    if (state['id'] != identity['sequence_id'] or abs(state['end']-audio['duration']) > 1e-4 or
            [settings[k] for k in ('frameSizeHorizontal', 'frameSizeVertical', 'timebase', 'audioSampleRateHz')]
            != [1920, 1080, '10584000000', 48000] or settings['audioChannelCount'] != 2):
        raise ValueError('Prepared Premiere sequence identity/profile changed')
    video = [c for t in state['videoTracks'] for c in t['clips']]
    sound = [(i, c) for i, t in enumerate(state['audioTracks']) for c in t['clips']]
    if (len(video) != 1 or len(state['videoTracks'][0]['clips']) != 1 or len(sound) != 1
            or sound[0][0] != 1 or state['audioTracks'][0]['clips']):
        raise ValueError('Picture preparation requires one picture, one piano bed, and empty A1')
    for clip, kind in ((video[0], 'picture'), (sound[0][1], 'music')):
        path = receipt['output'] if kind == 'picture' else audio['music']['clip_path']
        if (clip['name'] != Path(path).name or abs(clip['start']) > 1e-5
                or abs(clip['end']-audio['duration']) > 1e-4
                or abs(clip['duration']-audio['duration']) > 1e-4):
            raise ValueError('Prepared clip source or timing changed')
    return sound[0][1]['nodeId']


def inspect_media_items(items, identity, receipt, audio):
    entries = items['items'] if isinstance(items, dict) else items
    media = [i for i in entries if i.get('mediaPath')]
    expected = {'picture': receipt['output'], 'music': audio['music']['clip_path']}
    # Only these two sources may exist in this dedicated preparation project.
    # A reused project containing another take or nested sequence is refused.
    if len(media) != 2:
        raise ValueError('Unexpected source or voice media in the prepared project')
    for kind, path in expected.items():
        found = [i for i in media if i['nodeId'] == identity['item_ids'][kind]
                 and Path(i['mediaPath']).resolve() == Path(path).resolve()]
        if len(found) != 1:
            raise ValueError('Native prepared project media binding changed')
    return media


def client_for(request):
    client = PremiereMcpClient(request['endpoint'], Path(request['token_file']).read_text().strip())
    client.initialize()
    return client


def assemble(request):
    spec, receipt, audio = preflight(request)
    out = Path(request['output']).resolve(); out.mkdir(parents=True, exist_ok=True)
    project = Path(request['project']).resolve()
    if project.exists():
        raise ValueError('Preserve existing native editing projects; inspect before resuming')
    client = client_for(request); before = client.call('get_project_info')
    old = Path(before['path']); old_sha = file_sha(old)
    write(out / 'prior-project-binding.json', {'path': str(old), 'sha256': old_sha})
    connection = client.call('verify_premiere_connection', {'backend': 'cep'})
    if connection.get('overall') != 'ready':
        raise ValueError('Current native Premiere connection is not ready')
    log = []

    def mutate(tool, inputs):
        preflight(request)
        write(out / 'pending-mutation.json', {'tool': tool, 'inputs': inputs})
        try:
            result = client.call(tool, inputs)
        except Exception:
            write(out / 'uncertain-mutation.json', {'tool': tool, 'inputs': inputs,
                'next_action': 'inspect_native_state_before_retry'})
            raise
        log.append({'tool': tool, 'inputs': inputs, 'result': result})
        write(out / 'edit-receipts.json', log)
        return result

    mutate('create_project', {'path': str(project)})
    current = client.call('get_project_info')
    if Path(current['path']).resolve() != project:
        raise ValueError('New Premiere project identity missing')
    mutate('create_sequence', {'name': 'STUDENT_POV_PICTURE_AWAITING_VOICE',
                              'preset_path': request['sequence_preset']})
    sequence = client.call('get_active_sequence'); seq = sequence['id']
    mutate('import_media', {'file_paths': [receipt['output'], audio['music']['clip_path']], 'suppress_ui': True})
    items = client.call('list_project_items'); entries = items['items'] if isinstance(items, dict) else items
    ids = {}
    for kind, path in [('picture', receipt['output']), ('music', audio['music']['clip_path'])]:
        hits = [i for i in entries if i.get('mediaPath') and Path(i['mediaPath']).resolve() == Path(path).resolve()]
        if len(hits) != 1:
            raise ValueError('Prepared project media identity ambiguous: ' + kind)
        ids[kind] = hits[0]['nodeId']
    identity = {'project': str(project), 'sequence_id': seq, 'item_ids': ids,
                'spec_sha': spec['spec_sha'], 'voice_status': 'AWAITING_USER_AUDIO'}
    write(out / 'identity.json', identity)
    mutate('overwrite_clip', {'item_id': ids['picture'], 'start_seconds': 0, 'track_index': 0, 'audio_track_index': 0})
    mutate('overwrite_clip', {'item_id': ids['music'], 'start_seconds': 0, 'track_index': 0, 'audio_track_index': 1})
    mutate('rename_track', {'track_type': 'audio', 'track_index': 0, 'name': 'VO — waiting for final audio'})
    mutate('rename_track', {'track_type': 'audio', 'track_index': 1, 'name': 'Piano — provisional mix'})
    for name, time in spec['direction']['phases'].items():
        if name != 'end':
            mutate('add_marker', {'time_seconds': time, 'name': name,
                'comments': 'Picture timing estimate. Retiming awaits final voice.', 'color': 6})
    for slot in spec['direction']['voice_slots']:
        mutate('add_marker', {'time_seconds': slot['start'], 'name': 'VO_PENDING ' + slot['scene_id'],
            'comments': slot['text'], 'duration_seconds': slot['end']-slot['start'], 'color': 4})
    state = client.call('get_active_sequence'); settings = client.call('get_sequence_settings')
    music_node = inspect_timeline(state, settings, identity, receipt, audio)
    prop = request['music_property']
    write(out / 'music-properties-before.json', client.call('get_effect_properties',
        {'node_id': music_node, 'effect_name': prop['effect_name']}))
    router = BackendRouter(client, preferred='cep')
    try:
        automation = apply_music(router, seq, music_node, prop['effect_name'], prop['property_name'], audio['music']['gain_keys'])
    finally:
        write(out / 'music-edit-receipts.json', router.receipts)
    write(out / 'music-automation.json', dict(automation, property_binding=prop, node_id=music_node))
    mutate('set_playhead_position', {'time_seconds': 0})
    mutate('save_project', {})
    if file_sha(old) != old_sha:
        raise ValueError('Previous delivery project changed')
    return audit(request)


def audit(request):
    spec, receipt, audio = preflight(request); out = Path(request['output']); identity = read(out / 'identity.json')
    client = client_for(request); project = client.call('get_project_info')
    if (Path(project['path']).resolve() != Path(request['project']).resolve()
            or project['numSequences'] != 1 or project['numItems'] != 3):
        raise ValueError('Open the prepared editing project before native inspection')
    state = client.call('get_active_sequence'); settings = client.call('get_sequence_settings')
    node = inspect_timeline(state, settings, identity, receipt, audio)
    items = client.call('list_project_items')
    media = inspect_media_items(items, identity, receipt, audio)
    properties = []
    for clip in (state['videoTracks'][0]['clips'][0], state['audioTracks'][1]['clips'][0]):
        p = client.call('get_clip_properties', {'node_id': clip['nodeId']})
        if (abs(p['inPoint']) > 1e-5 or abs(p['outPoint']-audio['duration']) > 1e-4
                or p['isSpeedReversed'] or abs(p['duration']-audio['duration']) > 1e-4):
            raise ValueError('Prepared source range or playback direction changed')
        properties.append(p)
    from .music import verify_gain_keys
    prop = request['music_property']
    actual = client.call('get_keyframes', {'node_id': node, **prop})
    verify_gain_keys(actual, audio['music']['gain_keys'])
    result = {'status': 'PICTURE_AND_MUSIC_PREPARED_VOICE_PENDING', 'spec_sha': spec['spec_sha'],
        'final_copy_sha': spec['copy_lock']['final_copy_sha'], 'project': request['project'],
        'project_sha': file_sha(request['project']), 'timeline': state, 'settings': settings,
        'media_items': media, 'clip_properties': properties,
        'music_keyframes': actual, 'voice_track_empty': True, 'caption_alignment': 'PENDING_FINAL_AUDIO',
        'user_voice_ready_signal_received': False, 'human_listening_review': 'PENDING',
        'sample_export_performed': False, 'sample_delivery_allowed': False, 'public_render_ready': False}
    write(out / 'preparation-receipt.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('assemble', 'audit')); parser.add_argument('request')
    args = parser.parse_args(); globals()[args.operation](read(args.request))
    print('Picture and piano prepared; final voice and sample delivery remain pending', flush=True)


if __name__ == '__main__':
    main()
