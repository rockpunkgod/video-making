"""Prepare the R06 B06 G0/G1 handoff. No Adobe writes or media rendering.

Authored, real-case inputs and outputs stay in ignored local-data. Missing fine
annotation is an intentional G1 HOLD (exit 2), not permission to improvise G2.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from video_contracts import read, write, sha
from content_os.showcase import file_sha
from creative_os.audience_engagement import design_engagement, director_handoff
from ae_production.judgement_preflight import (
    candidate_prefix, inspect_phrase_requests, bind_existing_scenes, excerpt_boundaries)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def protected_files():
    names = git('ls-files', '-z', '--', 'answer_engine', 'method-registry', 'cases').split('\0')
    return {name: file_sha(ROOT / name) for name in names if name}


def prepare(request_path, output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / 'local-data').resolve()):
        raise ValueError('Real-case handoff must stay in ignored local-data')
    if output.exists():
        raise FileExistsError('Preserve revisions; choose a new output folder')
    before = protected_files()
    request = read(request_path)
    folder = Path(request['baseline_folder']).resolve()
    module = importlib.util.spec_from_file_location('existing_adaptive_executor',
        ROOT / 'ae/experiments/adaptive-episode/run.py')
    native = importlib.util.module_from_spec(module)
    module.loader.exec_module(native)
    parent = native.current(folder)
    episode = read(parent['episode_plan'])
    direction = read(folder / 'DIRECTION_REALIZED.json')
    statuses = {k: read(v) for k, v in parent['statuses'].items()}
    bundles = {b['asset_id']: b for q in episode['questions'] for b in q['package']['source_items']}
    render = read(folder / 'NATIVE_RENDER_RECEIPT.json')
    picture = read(folder / 'PICTURE_RECEIPT.json')
    identity = read(folder / 'native-identity.json')
    audit = read(folder / 'native-audit.json')
    motion = read(folder / 'native-motion-audit.json')
    if (file_sha(render['native_project']) != render['project_sha']
            or file_sha(picture['output']) != picture['output_sha']
            or picture['native_receipt_sha'] != sha(render)):
        raise ValueError('Native project/media receipt binding changed')
    if (identity['spec_sha'] != parent['spec']['spec_sha']
            or render['spec_sha'] != parent['spec']['spec_sha']
            or audit['comp_id'] != identity['comp_id'] or motion['errors']
            or picture['frames'] != round(parent['spec']['canvas']['duration'] * 24)
            or render['canvas'] != [3840, 2160, 24]):
        raise ValueError('Baseline native identity/audit/timing invalid')
    actual = {n['name']: n for n in audit['objects']}
    for node in parent['spec']['nodes']:
        obj = actual[node['node_id']]
        if (obj['text'].replace('\r', '\n') != node['text'] or obj['font'] != node['font']
                or json.loads(obj['comment'])['source_refs'] != node['source_refs']):
            raise ValueError('Saved native glyph/source audit differs from spec')
    streams = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-of', 'json', picture['output']]))['streams']
    video = next(s for s in streams if s['codec_type'] == 'video')
    if [video['width'], video['height'], video['r_frame_rate']] != [3840, 2160, '24/1']:
        raise ValueError('Baseline encoded media is not 4K24')
    for voice in parent['voices']:
        if sha(voice['text']) != voice['transcript_sha']:
            raise ValueError('Frozen transcript SHA changed')
        with wave.open(voice['path'], 'rb') as wav:
            if ((wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) != (48000, 2, 1)
                    or abs(wav.getnframes()/48000 - voice['duration']) > 1/48000):
                raise ValueError('Bound voice format/duration changed')
    audio = read(request['audio_editorial'])
    for item in audio['sources'] + [audio['music']]:
        if file_sha(item['path']) != item['sha256']:
            raise ValueError('Baseline music source changed')

    prefix = candidate_prefix(parent['spec'], bundles, 'B06')
    if prefix['selected']['before'] != ['B', 'C', 'D'] or prefix['selected']['after'] != ['C', 'D']:
        raise ValueError('B06 candidate prefix changed; reselect the production object')
    event = next(e for e in parent['spec']['events'] if e['scene_id'] == 'B06')
    annotations = inspect_phrase_requests(bundles, event, request['phrase_operations'])
    projected, scene_audit = bind_existing_scenes(episode, direction, parent['spec'], request['beat_scenes'])
    audience = design_engagement(episode, statuses, request['audience_direction'])
    handoff = director_handoff(audience, episode, statuses, request['audience_direction'],
                               projected, request['beat_scenes'])
    boundaries = excerpt_boundaries(direction, parent['voices'])
    files = dict(parent['input_files'])
    extra = [folder / 'native-request.json', render['native_project'], picture['output'],
        request['audio_editorial'], request['premiere_project'], audio['music']['path'],
        *[v['path'] for v in parent['voices']], *[v['path'] for v in audio['sources']],
        *[folder / name for name in ('PICTURE_RECEIPT.json', 'NATIVE_RENDER_RECEIPT.json',
          'native-identity.json', 'native-audit.json', 'native-motion-audit.json', 'REVIEW_SUBTITLES.srt')]]
    files.update({str(Path(p).resolve()): file_sha(p) for p in extra})
    concurrent = {p: file_sha(ROOT / p) for p in request['preserve_worktree_paths']}
    # Parent identity describes only the old production, not the new direction.
    old_sha = sha({'input_files': files, 'native_spec_sha': parent['spec']['spec_sha']})
    files[str(Path(request_path).resolve())] = file_sha(request_path)
    new_sha = sha({'parent_revision_sha': old_sha, 'request_sha': sha(request),
                   'handoff_sha': sha(handoff), 'annotation_request_sha': sha(annotations)})
    index = {'kind': 'r06_b06_production_index', 'revision_id': request['revision_id'],
        'repository_head': git('rev-parse', 'HEAD'),
        'parent_revision_sha': old_sha, 'new_revision_sha': new_sha,
        'new_revision_scope': 'PRODUCTION_PLAN_NOT_RENDERED_MEDIA',
        'original_episode_sha': sha(episode), 'original_direction_sha': sha(direction),
        'input_files': files, 'protected_teaching_files': before,
        'preserved_concurrent_worktree_files': concurrent,
        'changed_scenes': ['B06'], 'join_scenes': ['B05', 'B07'],
        'affected_events': [event], 'affected_voice_slots': ['B06-prepare', 'B06-confirm'],
        'affected_subtitles': ['B06-prepare', 'B06-confirm'],
        'retained_assets': 'all original files; unchanged B05/B07; same frozen voice/music takes',
        'recheck': ['new native spec/glyph/motion/frame receipts', 'local joins',
                    'voice placement and captions', 'actual-media mapping', 'human visual review'],
        'host_ownership': {'mutation_owner': '/root', 'revision': request['revision_id'],
            'lock_directory': str(ROOT / 'local-data/adobe-host-ownership'),
            'state': 'NOT_ACQUIRED_G1_HOLD', 'native_host_writes': 0},
        'feedback': request['feedback'],
        'gates': {'G0': 'PASS_BASELINE_BINDINGS', 'G1': 'HOLD_MISSING_FINE_ANNOTATION',
                  'director_handoff': 'PASS_PLANNED_ONLY', 'G2': 'NOT_STARTED', 'G3': 'NOT_SUBMITTED'},
        'actual_media_mapping': 'UNAVAILABLE', 'human_review': 'PENDING',
        'public_render_ready': False}
    artifacts = {'PRODUCTION_INDEX.json': index, 'CANDIDATE_PREFIX.json': prefix,
        'ANNOTATION_REQUEST.json': annotations, 'DIRECTOR_PROJECTION.json': projected,
        'AUDIENCE_DIRECTION.json': request['audience_direction'], 'AUDIENCE_ENGAGEMENT_PLAN.json': audience,
        'DIRECTOR_HANDOFF.json': handoff, 'SCENE_CONTENT_AUDIT.json': scene_audit,
        'BEAT_SCENES.json': request['beat_scenes'], 'EXCERPT_BOUNDARIES.json': boundaries,
        'AV_CUE_SHEET.json': request['av_cues']}
    if protected_files() != before or any(file_sha(p) != digest for p, digest in files.items()):
        raise ValueError('Input changed during preparation')
    output.mkdir(parents=True)
    for name, value in artifacts.items():
        write(output / name, value)
    for name, value in request['documents'].items():
        if Path(name).name != name or not name.endswith('.md'):
            raise ValueError('Local document filename required')
        (output / name).write_text(value.rstrip() + '\n', encoding='utf-8')
    write(output / 'PREPARATION_RECEIPT.json', {'input_request_sha': file_sha(request_path),
        'new_revision_sha': new_sha, 'artifacts': {p.name: file_sha(p) for p in sorted(output.iterdir())},
        'protected_input_hashes_unchanged': True, 'native_host_writes': 0,
        'g1_status': index['gates']['G1'], 'g2_started': False, 'public_render_ready': False})
    return {'output': str(output), 'G0': 'PASS', 'G1': index['gates']['G1'],
            'mapped_beats': len(handoff['rows']), 'phrase_requests': len(annotations['operations']),
            'G2': 'NOT_STARTED', 'public_render_ready': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = prepare(args.request, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(2)  # Explicit G1 HOLD. This entry point does not execute G2.
