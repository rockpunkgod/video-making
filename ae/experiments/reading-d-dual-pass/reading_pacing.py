"""Explicit settled-frame holds and literal frozen-copy review captions.

No interpolation, solving, new copy or inherited release approval. Recipes and
exam content remain in ignored local data; the historical assembly is unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from video_contracts import sha, read, write

FPS = 24


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def frame_map(count, holds):
    positions = {}
    for hold in holds:
        i, extra = hold['frame'], hold['extra_frames']
        if (type(i) is not int or type(extra) is not int or
                not 0 <= i < count or extra <= 0 or i in positions):
            raise ValueError('Unique in-range frame and positive integer hold required')
        if not hold.get('reason'):
            raise ValueError('Explicit reading reason required')
        positions[i] = extra
    return [i for i in range(count) for _ in range(1 + positions.get(i, 0))]


def caption_projection(rows, source, mapping):
    segments = {s['segment_id']: s for s in source['segments']}
    result = []
    for row in rows:
        segment = segments[row['segment_ref']]
        text = row['text']
        field = row['source_field']
        if field not in ('text', 'screen_text') or not text or text not in segment[field]:
            raise ValueError('Caption must be a literal frozen-copy span')
        a, b = row['base_start_frame'], row['base_end_frame']
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= max(mapping) + 1:
            raise ValueError('Caption frame range invalid')
        start = next(n for n, i in enumerate(mapping) if i == a)
        end = next((n for n, i in enumerate(mapping) if i == b), len(mapping))
        offset = segment[field].index(text)
        result.append(dict(row, start_frame=start, end_frame=end,
                           text_sha=sha(text), source_span=[offset, offset + len(text)],
                           source_field_sha=sha(segment[field]),
                           evidence_refs=segment.get('evidence', []),
                           action_refs=segment.get('action_refs', []),
                           decision_refs=segment.get('decision_refs', [])))
    result.sort(key=lambda r: r['start_frame'])
    if any(a['end_frame'] > b['start_frame'] for a, b in zip(result, result[1:])):
        raise ValueError('Review captions must not overlap')
    return result


def timestamp(frame, srt=False):
    ms = round(frame / FPS * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}' if srt else f'{h}:{m:02}:{s:02}.{ms // 10:02}'


def wrap(text, limit=26):
    # Formatting only; removing the inserted line break recovers exact text.
    if len(text) <= limit:
        return text
    cuts = [i + 1 for i, c in enumerate(text[:limit]) if c in '，。？；：']
    cut = cuts[-1] if cuts else limit
    return text[:cut] + '\n' + wrap(text[cut:], limit)


def write_captions(folder, rows):
    srt, events = [], []
    for n, r in enumerate(rows, 1):
        text = wrap(r['text'])
        srt.append(f"{n}\n{timestamp(r['start_frame'], True)} --> {timestamp(r['end_frame'], True)}\n{text}\n")
        safe = text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('\n', '\\N')
        events.append(f"Dialogue: 0,{timestamp(r['start_frame'])},{timestamp(r['end_frame'])},Review,,0,0,0,,{safe}")
    (folder / 'review.srt').write_text('\n'.join(srt), encoding='utf-8-sig')
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 3840
PlayResY: 2160
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Review,Noto Sans SC,64,&H002E2C28,&H002E2C28,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,360,360,58,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    (folder / 'review.ass').write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')


def local(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'local-data/reading-d-dual-pass'):
        raise ValueError('Real case output must stay in ignored local data')
    return path


def prepare(baseline, output, recipe):
    baseline, output = local(baseline), local(output)
    from integration import current
    current(baseline)
    if output.exists():
        raise ValueError('Use a fresh revision; never overwrite an accepted take')
    spec = read(baseline / 'integration.json')
    manifest = read(baseline / 'native-frame-shas.json')
    names = sorted(manifest)
    if names != [f'FRAME_{i:05}.tif' for i in range(round(spec['duration'] * FPS))]:
        raise ValueError('Complete historical native sequence required')
    frames = (baseline / 'native-frames').resolve()
    def verify(name):
        if file_sha(frames / name) != manifest[name]:
            raise ValueError('Native frame bytes changed')
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(verify, names))
    mapping = frame_map(len(names), recipe['holds'])
    proofs = []
    for hold in recipe['holds']:
        i = hold['frame']
        neighbours = [i - 1, i, i + 1]
        if min(neighbours) < 0 or max(neighbours) >= len(names):
            raise ValueError('Hold requires stationary neighbours')
        pixels = [hashlib.sha256(Image.open(frames / names[n]).convert('RGB').tobytes()).hexdigest()
                  for n in neighbours]
        if len(set(pixels)) != 1:
            raise ValueError(f'Hold frame {i} is not fully settled')
        proofs.append(dict(hold, neighbours=neighbours, rgb_sha=pixels[0]))
    rows = caption_projection(recipe['captions'], spec['source'], mapping)
    output.mkdir(parents=True)
    plan = dict(schema='reading-pacing/v1', fps=FPS, resolution=[3840, 2160],
                baseline=str(baseline), native_frames=str(frames), base_frame_count=len(names),
                duration=len(mapping) / FPS, frame_mapping=mapping, holds=proofs, captions=rows,
                source_binding=spec['source_binding'], integration_sha=file_sha(baseline / 'integration.json'),
                native_manifest_sha=sha(manifest), recipe_sha=sha(recipe),
                human_review='PENDING', audio_review='DEFERRED', captions_review='PENDING',
                final_voice_accepted=False, sample_delivery_allowed=False, public_render_ready=False)
    plan['plan_sha'] = sha(plan)
    write(output / 'pacing-plan.json', plan)
    write_captions(output, rows)
    write(output / 'caption-file-binding.json', {
        'ass_sha': file_sha(output / 'review.ass'), 'srt_sha': file_sha(output / 'review.srt')})
    # Source projection remains unmodified; it is not a new teaching review.
    write(output / 'frozen-source.json', spec['source'])
    return plan


def render(folder):
    folder = local(folder)
    plan = read(folder / 'pacing-plan.json')
    expected = plan.pop('plan_sha')
    if sha(plan) != expected:
        raise ValueError('Pacing plan changed')
    baseline = Path(plan['baseline'])
    from integration import current
    current(baseline)
    if file_sha(baseline / 'integration.json') != plan['integration_sha']:
        raise ValueError('Frozen baseline changed')
    manifest = read(baseline / 'native-frame-shas.json')
    if sha(manifest) != plan['native_manifest_sha']:
        raise ValueError('Native manifest changed')
    captions = read(folder / 'caption-file-binding.json')
    if (file_sha(folder / 'review.ass') != captions['ass_sha'] or
            file_sha(folder / 'review.srt') != captions['srt_sha']):
        raise ValueError('Caption file changed; regenerate a new bound take')
    # Hardlinks preserve exact native bytes without copying 100+ GB. All links
    # remain on the scratch volume of the original frame files.
    frames = Path(plan['native_frames'])
    linked = frames.parent.parent / folder.name / 'review-frames'
    linked.mkdir(parents=True, exist_ok=False)
    for n, i in enumerate(plan['frame_mapping']):
        source = frames / f'FRAME_{i:05}.tif'
        if i != plan['frame_mapping'][n - 1] or n == 0:
            if file_sha(source) != manifest[source.name]:
                raise ValueError('Changed native input before encoding')
        os.link(source, linked / f'FRAME_{n:05}.tif')
    movie = folder / 'Q33_READABLE_4K_SUBTITLED.mp4'
    if movie.exists():
        raise ValueError('Do not overwrite a rendered take')
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-threads', '1',
               '-filter_threads', '1', '-framerate', str(FPS), '-i', str(linked / 'FRAME_%05d.tif'),
               '-vf', 'ass=review.ass', '-an', '-c:v', 'libx264', '-threads', '4',
               '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(movie)]
    subprocess.run(command, cwd=folder, check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                       '-show_streams', '-of', 'json', str(movie)]))
    streams = probe['streams']
    if len(streams) != 1 or streams[0]['codec_type'] != 'video':
        raise ValueError('Silent picture review only')
    v = streams[0]
    if (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) != (
            3840, 2160, '24/1', len(plan['frame_mapping'])):
        raise ValueError('Encoded timing or resolution mismatch')
    subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(movie), '-f', 'null', '-'], check=True)
    receipt = dict(plan_sha=expected, movie=str(movie), movie_sha=file_sha(movie),
                   caption_ass_sha=file_sha(folder / 'review.ass'), caption_srt_sha=file_sha(folder / 'review.srt'),
                   frame_count=len(plan['frame_mapping']), duration=plan['duration'],
                   frame_origin='verified native TIFF; explicit stationary holds only',
                   full_decode='PASS', audio_streams=0, human_review='PENDING',
                   sample_delivery_allowed=False, public_render_ready=False)
    write(folder / 'render-receipt.json', receipt)
    return receipt


def build_native(folder, recovery_id=None):
    import time
    import integration
    from ae_production.execution import mutation_call
    folder = local(folder)
    plan = read(folder / 'pacing-plan.json')
    digest = plan.pop('plan_sha')
    if sha(plan) != digest:
        raise ValueError('Pacing plan changed')
    integration.current(Path(plan['baseline']))
    client = integration.relay.client()
    state = json.loads(client.call('ae_exec', {'code':
        'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty,rendering:app.project.renderQueue.rendering}) // ' + str(time.time_ns())})['content'])
    if (state['dirty'] and not recovery_id) or state['rendering']:
        raise ValueError('Preserve native session')
    template = Path(__file__).with_suffix('.jsx')
    code = 'var READING_RECOVERY=' + ('true' if recovery_id else 'false') + ';\nvar READING_PACING_PLAN=' + json.dumps((folder / 'pacing-plan.json').as_posix()) + ';\n' + template.read_text(encoding='utf-8')
    arguments = dict(code=code, undo_group_name='Reading holds and bound review captions',
                     checkpoint_label='before-readable-caption-take', timeout_sec=120)
    if recovery_id:
        arguments.update(recoveryId=recovery_id, retryMode='continue')
    result = mutation_call(client, 'ae_execRecover' if recovery_id else 'ae_exec', arguments, folder, 150)
    actual = json.loads(result['content'])
    if actual['canvas'] != [3840, 2160, 24, plan['duration']] or actual['remap_keys'] != len(plan['frame_mapping']):
        raise ValueError('Native timing mismatch')
    if len(actual['captions']) != len(plan['captions']):
        raise ValueError('Native captions missing')
    for native, caption in zip(actual['captions'], plan['captions']):
        if native['text'].replace('\r', '').replace('\n', '') != caption['text']:
            raise ValueError('Native lexical caption changed')
        if native['font'] != 'NotoSansSC-Regular' or native['bounds'][3] > 180:
            raise ValueError('Native font substitution or review zone overflow')
    audit_code = '''(function(){var f=new File(%s);f.encoding='UTF-8';f.open('r');var r=JSON.parse(f.read());f.close();
      var c=AEMCP.compById(%s),p=c.layer('UNCHANGED_NATIVE_PICTURE_WITH_READING_HOLDS').property('ADBE Time Remapping'),bad=0;
      for(var n=0;n<r.frame_mapping.length;n++)if(Math.round(p.valueAtTime(n/24,false)*24)!==r.frame_mapping[n])bad++;
      return JSON.stringify({frame_mapping_mismatches:bad,frame_count:r.frame_mapping.length,renderer:c.renderer});})(); // %s''' % (
        json.dumps((folder / 'pacing-plan.json').as_posix()), actual['comp_id'], time.time_ns())
    audit = json.loads(client.call('ae_exec', {'code': audit_code}, timeout=90)['content'])
    if audit['frame_mapping_mismatches'] or audit['renderer'] != 'ADBE Calder':
        raise ValueError('Actual native remapping differs from encoded frame plan')
    actual['frame_mapping_audit'] = audit
    actual.update(plan_sha=digest, template_sha=file_sha(template), project_sha=file_sha(actual['project']),
                  human_review='PENDING', native_caption_appearance_matches_encoded='NOT_CERTIFIED')
    write(folder / 'native-timing-receipt.json', actual)
    return actual


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare')
    a.add_argument('baseline'); a.add_argument('output'); a.add_argument('recipe')
    a = sub.add_parser('render'); a.add_argument('folder')
    a = sub.add_parser('build-native'); a.add_argument('folder'); a.add_argument('--recovery-id')
    args = p.parse_args()
    print(json.dumps(prepare(args.baseline, args.output, read(args.recipe)) if args.command == 'prepare'
                     else build_native(args.folder, args.recovery_id) if args.command == 'build-native'
                     else render(args.folder), ensure_ascii=False, default=str)[:1000])
