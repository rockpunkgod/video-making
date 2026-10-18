"""Reuse native bytes across exact template repairs or source-anchor repairs.

This module never opens Adobe, renders, trims, re-encodes, or grants review
approval. Unknown plan/native/source differences fail closed. A reused receipt
names the actual parent media and retains its original renderer provenance.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess

from video_contracts import read, sha, write
from scripts.voice_delivery import sha256
from .authored_episode import delivery_path, grid, script_text


SCHEMA = 'native-parts-reuse/v1'
PROOF = 'NATIVE_PARTS_REUSE.json'
# Reviewed consumer: source attention writes only the bounded extraction clones;
# it resets every clone at each event. Unknown templates need a new proof review.
# This historical digest does not follow a mutable checkout's default template.
SOURCE_ATTENTION_TEMPLATE_SHA256 = '8a88fbcf5632df8011cd142ca9d1581638d452c42fc5d3e8448ae852b905228b'
# .gitattributes writes the same reviewed template with canonical LF in Git.
# These are two exact byte representations, never a normalization-based gate.
SOURCE_ATTENTION_TEMPLATE_LF_SHA256 = 'dbaeb64316c635ab25e27e8656cce54a852e927944d106410b4efa337af95670'
SOURCE_ATTENTION_TEMPLATE_SHA256_ALLOWLIST = frozenset({
    SOURCE_ATTENTION_TEMPLATE_SHA256, SOURCE_ATTENTION_TEMPLATE_LF_SHA256})
ATTENTION_OPERATION = 'authored_attention_and_reading_visibility_repair'
DISPLAY_OPERATION = 'authored_title_and_background_isolation_repair'
# One independently reviewed single-line patch, with exact same-EOL pairs.
# A checkout, a normalized digest, or an arbitrary additional template edit
# cannot extend this list. Historical source-attention proofs stay unchanged.
BACKGROUND_TEMPLATE_SHA256 = 'd3db205fbf96ae61e284ec85ecf0ec076ca175f1cf536b6fcbe154282c0b0937'
BACKGROUND_TEMPLATE_LF_SHA256 = '12e07dc2cf419409928dd0e1662c3e07bead7b41e9f4ab4b813b283c87d522c4'
BACKGROUND_TEMPLATE_PAIRS = {
    SOURCE_ATTENTION_TEMPLATE_SHA256: BACKGROUND_TEMPLATE_SHA256,
    SOURCE_ATTENTION_TEMPLATE_LF_SHA256: BACKGROUND_TEMPLATE_LF_SHA256}
BACKGROUND_OLD = (b'  for(var j=0;j<w.blocks.length;j++){var row=w.blocks[j],selected=false;'
    b'for(var k=0;k<ex.blocks.length;k++)if(row.id===ex.blocks[k].id)selected=true;'
    b'if(!selected){ease(tr(row.layer,"ADBE Opacity"),s.extract_start,100);'
    b'ease(tr(row.layer,"ADBE Opacity"),s.settled,6);'
    b'ease(tr(row.layer,"ADBE Opacity"),s.return_start,6);'
    b'ease(tr(row.layer,"ADBE Opacity"),b-1/24,100);}}')
BACKGROUND_NEW = (b'  for(var j=0;j<w.blocks.length;j++){var row=w.blocks[j],selected=false;'
    b'for(var k=0;k<ex.blocks.length;k++)if(row.id===ex.blocks[k].id)selected=true;'
    b'if(!selected){if(s.comparison_background_policy==="isolate_selected_passage"){'
    b'var lastRead=s.reading_events[s.reading_events.length-1];'
    b'if(!lastRead||row.start<lastRead.end&&row.end>lastRead.start)'
    b'throw Error("Background isolation would hide necessary reading");'
    b'ease(tr(row.layer,"ADBE Opacity"),Math.max(s.candidate_arrive,lastRead.end_time-.3),100);'
    b'ease(tr(row.layer,"ADBE Opacity"),lastRead.end_time,0);'
    b'ease(tr(row.layer,"ADBE Opacity"),Math.max(s.return_start,b-.35),0);'
    b'ease(tr(row.layer,"ADBE Opacity"),b-1/24,100);}else{'
    b'ease(tr(row.layer,"ADBE Opacity"),s.extract_start,100);'
    b'ease(tr(row.layer,"ADBE Opacity"),s.settled,6);'
    b'ease(tr(row.layer,"ADBE Opacity"),s.return_start,6);'
    b'ease(tr(row.layer,"ADBE Opacity"),b-1/24,100);}}}')
MAX_REUSE_DEPTH = 16
LIGHT_OLD = b'choice.motionBlur=false;'
LIGHT_NEW = LIGHT_OLD + b'style(choice,s.oriented,ink,null,null);'
TITLE_OLD = (b'var title=overlay("TASK_TITLE_"+s.id,heading,72,24,28,1120,muted,a,b);'
             b'titles.push(title);')
TITLE_NEW = (b'var title=overlay("TASK_TITLE_"+s.id,heading,72,24,28,1120,muted,a,b);'
             b'if((s.kind==="compare"||s.kind==="replay")&&s.motion_treatment!=="in_place_check"'
             b'&&s.reading_events.length){var titleEnd=Math.max(a+.25,s.reading_events[0].depart);'
             b'title.outPoint=Math.min(b,titleEnd);ease(tr(title,"ADBE Opacity"),'
             b'Math.max(a,titleEnd-.2),100);ease(tr(title,"ADBE Opacity"),titleEnd,0);}'
             b'titles.push(title);')


def _bound_file(path, digest, bindings):
    path = Path(path).resolve()
    if not isinstance(digest, str) or sha256(path) != digest:
        raise ValueError('Bound native reuse input changed: ' + str(path))
    previous = bindings.setdefault(str(path), digest)
    if previous != digest:
        raise ValueError('One reuse input has contradictory digests')
    return path


def _inside(folder, relative):
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder) or path == folder:
        raise ValueError('Native snapshot or receipt escapes its revision')
    return path


def _record(path, bindings):
    path = Path(path).resolve()
    _bound_file(path, sha256(path), bindings)
    return read(path)


def _native_layers(audit):
    layers = audit['layers']
    by_id = {r['id']: r['name'] for r in layers}
    if len(by_id) != len(layers) or len({r['name'] for r in layers}) != len(layers):
        raise ValueError('Unique native layer identities required')
    result = {}
    for row in layers:
        value = deepcopy(row)
        value.pop('id')
        parent = value.get('parent')
        if parent is not None:
            if parent not in by_id:
                raise ValueError('Native layer has no bound parent')
            value['parent'] = by_id[parent]
        result[row['name']] = value
    return result


def _revision(folder):
    folder = Path(folder).resolve()
    bindings = {}
    plan = _record(folder / 'AV_PLAN.json', bindings)
    author = _record(folder / 'AV_AUTHOR.json', bindings)
    native = _record(folder / 'native-identity.json', bindings)
    snapshots = _record(folder / 'NATIVE_SOURCES.json', bindings)
    audit = _record(folder / 'native-audit.json', bindings)
    _bound_file(folder / 'AV_AUTHOR.json', plan['author_sha256'], bindings)
    _bound_file(folder / 'AV_PLAN.json', native['plan_sha256'], bindings)
    if (plan['format'] != {'width': 1920, 'height': 1080, 'fps': 24}
            or plan['master_format'] != {'width': 3840, 'height': 2160, 'fps': 24}
            or type(plan['frames']) is not int or plan['frames'] <= 0
            or not math.isfinite(plan['duration'])
            or abs(plan['duration'] * 24 - plan['frames']) > 1e-6
            or native['frames'] != plan['frames']
            or abs(native['duration'] * 24 - plan['frames']) > 1e-6
            or [native['width'], native['height']] != [1920, 1080]
            or any(type(native[k]) is not int or native[k] <= 0 for k in ('comp_id', 'master_comp_id'))
            or native['comp_id'] == native['master_comp_id']):
        raise ValueError('Complete native proxy and 4K24 master identities required')
    if (plan['public_render_ready'] is not False
            or native['media_role'] != 'EDITORIAL_PROXY'):
        raise ValueError('Reuse cannot acquire publication or format authority')
    project = (folder / 'media/MAIN_FILM.aep').resolve()
    if (Path(native['project_path']).resolve() != project
            or Path(audit['project']).resolve() != project or not project.is_file()
            or [audit['width'], audit['height'], audit['fps']] != [1920, 1080, 24]
            or abs(audit['duration'] * 24 - plan['frames']) > 1e-6):
        raise ValueError('Actual saved native project/readback identity required')
    master = audit['unrendered_master']
    if ([master['width'], master['height'], master['fps']] != [3840, 2160, 24]
            or abs(master['duration'] * 24 - plan['frames']) > 1e-6
            or audit['reading_rig_sha256'] != native['reading_rig_sha256']):
        raise ValueError('Native master and reading-rig observations differ')
    if set(snapshots) != {'template', 'reading_rig'}:
        raise ValueError('Exact native template and reading-rig snapshots required')
    sources = {}
    for key, field in [('template', 'template_sha256'), ('reading_rig', 'reading_rig_sha256')]:
        row = snapshots[key]
        if row['sha256'] != native[field]:
            raise ValueError('Native source snapshot differs from executed identity')
        sources[key] = _bound_file(_inside(folder, row['path']), row['sha256'], bindings).read_bytes()
    script = (folder / 'EPISODE_SCRIPT.md').read_text('utf-8')
    if script != script_text(author) or sha(script) != plan['complete_copy_sha256']:
        raise ValueError('Exact production copy export required for reuse')
    _record_path = folder / 'EPISODE_SCRIPT.md'
    _bound_file(_record_path, sha256(_record_path), bindings)
    delivery_file = delivery_path(folder, author)
    _bound_file(delivery_file, plan['voice_delivery_sha256'], bindings)
    delivery = read(delivery_file)
    clips = {c['id']: c for c in delivery['clips']}
    if len(clips) != len(delivery['clips']):
        raise ValueError('Duplicate complete take identity')
    alignment = _record(folder / 'VOICE_ALIGNMENT.json', bindings)
    _bound_file(folder / 'VOICE_ALIGNMENT.json', plan['alignment_sha256'], bindings)
    if alignment['delivery_sha256'] != plan['voice_delivery_sha256']:
        raise ValueError('Alignment belongs to another complete delivery')
    chunking = _record(folder / 'READING_CHUNKS.json', bindings)
    if chunking != plan['article_chunking']:
        raise ValueError('Native reading groups differ from the plan')
    _bound_file(folder / 'ARTICLE_CHUNKS.json', chunking['input_sha256'], bindings)
    for path, digest in author['input_files'].items():
        _bound_file(path, digest, bindings)
    normalized = deepcopy(plan)
    # These exact envelope fields bind actual files above; they are not pixels.
    for key in ('revision', 'author_sha256', 'voice_delivery_sha256', 'alignment_sha256',
                'complete_copy_sha256', 'copy_review'):
        normalized.pop(key, None)
    normalized['editorial_consumption'].pop('manifest_sha256', None)
    source_files = {}
    for world, value in normalized['worlds'].items():
        if set(value['source']) != {'bundle', 'status'} or value['source'] != author['sources'][world]:
            raise ValueError('World source paths differ from the actual author')
        source_files[world] = {}
        for role, path in value['source'].items():
            digest = sha256(path)
            _bound_file(path, digest, bindings)
            source_files[world][role] = digest
        value['source'] = source_files[world]
    expected_text = {v['id']: v['text'] for v in author['voices']}
    seen = set()
    for segment in normalized['segments']:
        voice = segment['voice']; ident = segment['id']
        if (ident in seen or ident not in clips or segment['text'] != expected_text.get(ident)
                or segment.get('time_stretch') is not False or segment.get('truncated') is not False):
            raise ValueError('Unchanged complete takes and production copy required')
        seen.add(ident); clip = clips[ident]
        for path_key, digest_key in [('path', 'sha256'), ('padded_path', 'padded_sha256'),
                                     ('original_path', 'audio_sha256')]:
            _bound_file(voice[path_key], voice[digest_key], bindings)
            voice[path_key] = {'sha256': voice[digest_key]}
        for path_key, digest_key in [('audio', 'audio_sha256'), ('transcript', 'transcript_sha256')]:
            if voice[digest_key] != clip[digest_key]:
                raise ValueError('Take or transcript differs from delivery')
            _bound_file(delivery_file.parent / clip[path_key], clip[digest_key], bindings)
            voice[path_key] = {'sha256': clip[digest_key]}
    if seen != set(clips) or seen != set(expected_text):
        raise ValueError('Every complete take must remain in the timeline')
    for music in normalized.get('music', []):
        for key, digest_key in [('source_path', 'file_sha'), ('clip_path', 'clip_sha')]:
            if key in music:
                _bound_file(music[key], music[digest_key], bindings)
                music[key] = {'sha256': music[digest_key]}
    alignment = deepcopy(alignment); alignment.pop('delivery_sha256')
    return {'folder': folder, 'plan': plan, 'author': author, 'native': native, 'audit': audit,
            'sources': sources, 'bindings': bindings, 'normalized': normalized,
            'alignment': alignment, 'layers': _native_layers(audit), 'project': project}


def _unique(rows, key, label):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate ' + label)
    return result


def _spoken_time(revision, scene, anchor):
    if not isinstance(anchor, str) or not anchor:
        raise ValueError('A real spoken source-attention anchor is required')
    voices = _unique(revision['author']['voices'], 'id', 'authored voice')
    aligned = _unique(revision['alignment']['clips'], 'id', 'aligned take')
    segments = _unique(revision['plan']['segments'], 'id', 'placed take')
    for ident in scene['voice_ids']:
        voice, segment, measured = voices[ident], segments[ident], aligned[ident]
        if (segment['scene_id'] != scene['id'] or segment['text'] != voice['text']
                or measured['transcript'] != voice['text']
                or measured['audio_sha256'] != segment['voice']['audio_sha256']
                or measured['transcript_sha256'] != segment['voice']['transcript_sha256']):
            raise ValueError('Source anchor requires its actual unchanged complete take')
        at = voice['text'].find(anchor)
        if at >= 0:
            matches = [c for c in measured['cues'] if c['text_start'] <= at < c['text_end']]
            if len(matches) != 1:
                raise ValueError('Ambiguous measured source-attention anchor')
            cue = matches[0]
            if (voice['text'][cue['text_start']:cue['text_end']] != cue['text']
                    or not 0 <= cue['start'] < cue['end'] <= measured['duration_seconds'] + .001):
                raise ValueError('Measured source anchor does not match the actual spoken cue')
            return grid(segment['voice_start'] + cue['start'], 24)
    raise ValueError('Source-attention anchor is absent from the scene complete takes')


def _author_for_attention(revision, changes, visibility):
    """Remove only bound envelope paths and the specifically proved anchors."""
    value = deepcopy(revision['author']); value.pop('revision')
    scenes = _unique(value['scenes'], 'id', 'author scene')
    for change in changes:
        scenes[change['scene']]['attention'][change['index']]['anchor'] = '<BOUND_SOURCE_ANCHOR>'
    for change in visibility:
        scenes[change['scene']].pop('candidate_reading_policy', None)
    value['sources'] = {w: r['source'] for w, r in revision['normalized']['worlds'].items()}
    # These are path-only declarations. The plan already verifies every original,
    # converted, padded take and transcript byte and every placement/voice field.
    value['voice_delivery'] = '<BOUND_COMPLETE_TAKES>'
    if 'alignment_source' in value:
        path = Path(value['alignment_source']).resolve()
        measured = _record(path, revision['bindings']); measured.pop('delivery_sha256')
        if measured != revision['alignment']:
            raise ValueError('Alignment source changed beyond its delivery envelope')
        value['alignment_source'] = {'alignment_semantic_sha256': sha(measured)}
        # Only the explicitly declared alignment source may change an input key.
        inputs = value['input_files']; matches = [p for p in inputs if Path(p).resolve() == path]
        if len(matches) != 1:
            raise ValueError('Explicit alignment source must retain its exact input binding')
        inputs.pop(matches[0])
        value['alignment_source_input'] = {'alignment_semantic_sha256': sha(measured)}
    if 'editorial' not in value:
        raise ValueError('Source-anchor repair requires the real editorial manifest')
    editorial = value['editorial']
    if set(editorial) != {'schema', 'manifest', 'sha256'} or editorial['schema'] != 'authored-editorial/v1':
        raise ValueError('Exact authored editorial manifest identity required')
    manifest_path = _bound_file(editorial['manifest'], editorial['sha256'], revision['bindings'])
    manifest = read(manifest_path)
    if manifest.get('authority') != 'internal_ai_editorial_only' or manifest.get('human_approved') is not False:
        raise ValueError('Native reuse cannot acquire human editorial approval')
    if set(manifest['scenes']) != set(scenes):
        raise ValueError('Editorial manifest must cover the exact author scenes')
    for path, digest in manifest['source_files'].items():
        _bound_file(path, digest, revision['bindings'])
    for sid, decisions in manifest['scenes'].items():
        for key, decision in decisions['consumed_decisions'].items():
            if decision != revision['author']['scenes'][list(scenes).index(sid)].get(key):
                raise ValueError('Editorial author decision was not consumed: ' + sid)
    for change in changes:
        decisions = manifest['scenes'][change['scene']]['consumed_decisions']
        if 'attention' not in decisions:
            raise ValueError('Editorial manifest must consume the changed attention anchor')
        decisions['attention'][change['index']]['anchor'] = '<BOUND_SOURCE_ANCHOR>'
    for change in visibility:
        sid = change['scene']; decisions = manifest['scenes'][sid]['consumed_decisions']
        if (revision['author']['scenes'][list(scenes).index(sid)].get('candidate_reading_policy') == 'quiet_source_until_read'
                and decisions.get('candidate_reading_policy') != 'quiet_source_until_read'):
            raise ValueError('Editorial manifest must consume the repaired candidate reading policy')
        decisions.pop('candidate_reading_policy', None)
    value['editorial'] = {'schema': editorial['schema'], 'manifest_semantics': manifest}
    return value


def _attention_difference(old, new):
    """Prove the complete plan delta, including its authored/editorial mirrors."""
    before, after = deepcopy(old['normalized']), deepcopy(new['normalized'])
    old_scenes = _unique(before['scenes'], 'id', 'plan scene')
    new_scenes = _unique(after['scenes'], 'id', 'plan scene')
    authors = [_unique(r['author']['scenes'], 'id', 'author scene') for r in (old, new)]
    mirrors = [_unique(p['editorial_consumption']['rows'], 'scene', 'editorial scene')
               for p in (before, after)]
    if any(set(rows) != set(old_scenes) for rows in (new_scenes, *authors, *mirrors)):
        raise ValueError('Complete author/plan/editorial scene inventories must agree')
    changes, visibility = [], []
    for sid, previous in old_scenes.items():
        current = new_scenes[sid]
        for index, scene in enumerate((previous, current)):
            if (scene.get('attention', []) != authors[index][sid].get('attention', [])
                    or mirrors[index][sid].get('attention') != scene.get('attention_events', [])):
                raise ValueError('Plan source attention and editorial mirror disagree: ' + sid)
            policy = scene.get('candidate_reading_policy', 'visible')
            if (policy != authors[index][sid].get('candidate_reading_policy', 'visible')
                    or mirrors[index][sid].get('candidate_reading_policy') != policy):
                raise ValueError('Plan candidate reading policy and editorial mirror disagree: ' + sid)
        if previous == current:
            continue
        if (previous.get('kind') not in ('compare', 'replay')
                or previous.get('motion_treatment') != 'critical_comparison'):
            raise ValueError('Source-anchor repair is limited to extracted comparison scenes')
        policy_changed = previous.get('candidate_reading_policy', 'visible') != current.get('candidate_reading_policy', 'visible')
        if policy_changed:
            if (previous['kind'] != 'compare' or not previous.get('reading_events')
                    or previous.get('candidate_reading_policy', 'visible') != 'visible'
                    or current.get('candidate_reading_policy') != 'quiet_source_until_read'):
                raise ValueError('Only visible-to-quiet candidate reading policy is allowed')
            visibility.append({'scene': sid, 'from': 'visible', 'to': 'quiet_source_until_read'})
            current.pop('candidate_reading_policy', None)
            if 'candidate_reading_policy' in previous:
                current['candidate_reading_policy'] = previous['candidate_reading_policy']
            mirrors[1][sid]['candidate_reading_policy'] = mirrors[0][sid]['candidate_reading_policy']
        arrays = [s.get(k, []) for s in (previous, current) for k in ('attention', 'attention_events')]
        if any(len(rows) != len(arrays[0]) for rows in arrays):
            raise ValueError('Source-anchor repair cannot add, remove or reorder attention')
        scene_changes = []
        for i, (a, e, b, f) in enumerate(zip(*arrays)):
            if (set(a) != {'anchor', 'phrase', 'target'} or set(b) != set(a)
                    or set(e) != {*a, 'time'} or set(f) != {*b, 'time'}
                    or {k: v for k, v in e.items() if k != 'time'} != a
                    or {k: v for k, v in f.items() if k != 'time'} != b):
                raise ValueError('Exact source-attention event/author mirrors required')
            if a == b and e == f:
                continue
            if (a['target'] != 'source' or b['target'] != 'source'
                    or a['phrase'] != b['phrase'] or a['anchor'] == b['anchor']):
                raise ValueError('Only a source attention anchor may change')
            for revision, scene, event in ((old, previous, e), (new, current, f)):
                t = event['time']
                if (type(t) not in (int, float) or not math.isfinite(t)
                        or not scene['start'] <= t < scene['end']
                        or abs(t - _spoken_time(revision, scene, event['anchor'])) > 1e-8):
                    raise ValueError('Source attention time must equal its real complete-take cue')
            old_frame = round(max(e['time'], previous['settled']) * 24)
            new_frame = round(max(f['time'], current['settled']) * 24)
            if old_frame == new_frame:
                raise ValueError('Source anchor still lands at the same effective native frame')
            change = {'scene': sid, 'index': i, 'phrase': a['phrase'],
                      'old_anchor': a['anchor'], 'new_anchor': b['anchor'],
                      'old_time': e['time'], 'new_time': f['time'],
                      'old_effective_frame': old_frame, 'new_effective_frame': new_frame}
            scene_changes.append(change)
            b['anchor'] = a['anchor']; f.update(anchor=e['anchor'], time=e['time'])
            mirrors[1][sid]['attention'][i].update(anchor=e['anchor'], time=e['time'])
        if not scene_changes and not policy_changed:
            raise ValueError('Plans differ beyond source attention anchors')
        # Every source event resets all clones, even clones without that phrase.
        # Coincident source events therefore erase one another across the group.
        actual = next(s for s in new['plan']['scenes'] if s['id'] == sid)
        frames = [round(max(e['time'], actual['settled']) * 24)
                  for e in actual['attention_events'] if e['target'] == 'source']
        if scene_changes and len(frames) != len(set(frames)):
            raise ValueError('Coincident source attention remains in the repaired scene')
        changes.extend(scene_changes)
    if (not changes and not visibility) or before != after or old['alignment'] != new['alignment']:
        raise ValueError('Plans differ beyond bound source attention anchors and times')
    if _author_for_attention(old, changes, visibility) != _author_for_attention(new, changes, visibility):
        raise ValueError('Author differs beyond the bound source attention anchors')
    return changes, visibility, before


def _source_attention_layers(revision, scenes):
    """Check observed geometry/text/lifetime; SourceText keyframes are not read back."""
    result = set()
    for scene in scenes:
        if not 0 <= scene['start'] < scene['extract_start'] <= scene['settled'] < scene['end'] <= revision['plan']['duration']:
            raise ValueError('Source attention requires bounded scene extraction lifetime')
        excerpt = revision['plan']['excerpts'][scene['excerpt']]
        blocks = _unique(revision['plan']['worlds'][excerpt['world']]['blocks'], 'id', 'source block')
        refs = [r for r in scene['source_refs'] if r['world'] == excerpt['world'] and r['pointer'] == '/passage']
        selected = [bid for bid in excerpt['block_ids'] if any(
            r['start'] < blocks[bid]['end'] and r['end'] > blocks[bid]['start'] for r in refs)]
        group = 'SOURCE_LIFT_' + scene['id']; prefix = 'EXTRACT_' + scene['id'] + '_'
        names = {prefix + bid for bid in selected}
        if (not selected or group not in revision['layers']
                or {n for n in revision['layers'] if n.startswith(prefix)} != names):
            raise ValueError('Source attention must target its actual bound extraction group')
        for name in names | {group}:
            layer = revision['layers'][name]
            if (layer.get('threeD') is not True
                    or abs(layer.get('inPoint', -1) - scene['extract_start']) > 1e-6
                    or abs(layer.get('outPoint', -1) - scene['end']) > 1e-6
                    or layer.get('parent') != (None if name == group else group)):
                raise ValueError('Source attention extraction escapes its scene lifetime')
        for bid in selected:
            if revision['layers'][prefix + bid].get('text', '').replace('\r', '\n') != blocks[bid]['text']:
                raise ValueError('Source attention extraction text changed')
        for event in scene['attention_events']:
            if event['target'] == 'source' and not any(event['phrase'] in blocks[bid]['text'] for bid in selected):
                raise ValueError('Source attention phrase is absent from its actual extraction')
        result |= names | {group}
    return result


def _native_observations(revision):
    value = deepcopy(revision['audit']); value.pop('project'); value.pop('layers')
    master = value['unrendered_master']
    if 'comment' in master:
        expected = {'revision': revision['plan']['revision'],
                    'author_sha256': revision['plan']['author_sha256'],
                    'role': 'UNRENDERED_4K_MASTER', 'plan_sha256': revision['native']['plan_sha256']}
        if json.loads(master['comment']) != expected:
            raise ValueError('Native master comment is not bound to this complete plan')
        master['comment'] = {'role': expected['role']}
    by_id = {r['id']: r['name'] for r in revision['audit']['layers']}
    comp_ids = {revision['native']['comp_id']: 'EDITORIAL_PROXY',
                revision['native']['master_comp_id']: 'NATIVE_4K_MASTER'}

    def normalize(item):
        if isinstance(item, list):
            return [normalize(v) for v in item]
        if isinstance(item, dict):
            return {k: (comp_ids[v] if k in ('comp_id', 'comp') and type(v) is int and v in comp_ids
                        else by_id[v] if k in ('layer_id', 'group_id', 'source_layer_id') and type(v) is int and v in by_id
                        else normalize(v)) for k, v in item.items()}
        return item
    return normalize(value)


def _reading_visibility_layers(revision, scenes):
    result = set()
    for scene in scenes:
        name = 'CANDIDATE_FLIGHT_' + scene['id']
        if name not in revision['layers']:
            raise ValueError('Reading visibility repair requires its actual candidate clone')
        layer = revision['layers'][name]
        if (layer.get('threeD') is not True or layer.get('parent') is not None
                or not scene['start'] <= scene['candidate_start'] < scene['end']
                or abs(layer.get('inPoint', -1) - scene['candidate_start']) > 1e-6
                or abs(layer.get('outPoint', -1) - scene['end']) > 1e-6
                or not scene['start'] <= scene['reading_events'][0]['arrival']
                       < scene['reading_events'][-1]['end_time'] < scene['end']):
            raise ValueError('Candidate reading visibility escapes its scene lifetime')
        result.add(name)
    return result


def _display_requested(old, new):
    def decisions(revision):
        return [(s['id'], s.get('screen_title', s.get('title')),
                 s.get('comparison_background_policy', 'visible')) for s in revision['plan']['scenes']]
    return (decisions(old) != decisions(new)
            or new['native']['template_sha256'] in BACKGROUND_TEMPLATE_PAIRS.values())


def _display_difference(old, new):
    """Remove only explicitly consumed title hides and background isolation."""
    plans = [deepcopy(r['normalized']) for r in (old, new)]
    scenes = [_unique(p['scenes'], 'id', 'plan scene') for p in plans]
    authors = [_unique(r['author']['scenes'], 'id', 'author scene') for r in (old, new)]
    mirrors = [_unique(p['editorial_consumption']['rows'], 'scene', 'editorial scene') for p in plans]
    if any(set(rows) != set(scenes[0]) for rows in (*scenes[1:], *authors, *mirrors)):
        raise ValueError('Complete author/plan/editorial scene inventories must agree')
    changes = []
    for sid, previous in scenes[0].items():
        current = scenes[1][sid]
        for key in ('screen_title', 'comparison_background_policy'):
            def effective(scene):
                return (scene.get(key, scene.get('title')) if key == 'screen_title'
                        else scene.get(key, 'visible'))
            a, b = effective(previous), effective(current)
            for i, scene in enumerate((previous, current)):
                if effective(scene) != effective(authors[i][sid]):
                    raise ValueError('Authored display decision and plan disagree: ' + sid)
                if key in mirrors[i][sid] and mirrors[i][sid][key] != effective(scene):
                    raise ValueError('Display decision and editorial mirror disagree: ' + sid)
            if a == b:
                continue
            if (previous.get('kind') != 'compare' or current.get('kind') != 'compare'
                    or previous.get('motion_treatment') != 'critical_comparison'):
                raise ValueError('Display repair is limited to extracted candidate comparisons')
            if key == 'screen_title':
                if (not isinstance(a, str) or not a or b != ''
                        or current.get(key) != '' or authors[1][sid].get(key) != ''):
                    raise ValueError('Only a nonempty-to-empty screen title repair is allowed')
                reason = 'hide_comparison_screen_title'
            else:
                if (a != 'visible' or b != 'isolate_selected_passage'
                        or not current.get('reading_events')
                        or current.get('candidate_reading_policy') != 'quiet_source_until_read'):
                    raise ValueError('Only visible-to-isolate comparison background repair is allowed')
                reason = 'isolate_nonselected_comparison_background'
            if key not in mirrors[1][sid] or mirrors[1][sid][key] != b:
                raise ValueError('Repaired display decision needs an explicit editorial mirror: ' + sid)
            changes.append({'scene': sid, 'field': key, 'from': a, 'to': b, 'repair': reason})
            current.pop(key, None)
            if key in previous:
                current[key] = previous[key]
            mirrors[1][sid].pop(key, None)
            if key in mirrors[0][sid]:
                mirrors[1][sid][key] = mirrors[0][sid][key]
    if not changes or plans[0] != plans[1] or old['alignment'] != new['alignment']:
        raise ValueError('Plans differ beyond bound title hiding and background isolation')
    # The common helper binds all complete takes, source files and the actual
    # manifest before removing any declared repair. It grants no human review.
    values = [_author_for_attention(r, [], []) for r in (old, new)]
    for change in changes:
        sid, key = change['scene'], change['field']
        for i, value in enumerate(values):
            scene = _unique(value['scenes'], 'id', 'author scene')[sid]
            decisions = value['editorial']['manifest_semantics']['scenes'][sid]['consumed_decisions']
            if i == 1 and (key not in decisions or decisions[key] != change['to']):
                raise ValueError('Editorial manifest must consume the repaired display decision: ' + sid)
            scene.pop(key, None); decisions.pop(key, None)
    if values[0] != values[1]:
        raise ValueError('Author differs beyond bound title hiding and background isolation')
    return changes, plans[0]


def _background_scope(revision):
    """Derive the exact patched consumer's original passage targets and times."""
    rows = []
    for scene in revision['plan']['scenes']:
        if scene.get('comparison_background_policy') != 'isolate_selected_passage':
            continue
        if (scene['kind'] != 'compare' or scene.get('motion_treatment') != 'critical_comparison'
                or scene.get('candidate_reading_policy') != 'quiet_source_until_read'
                or not scene.get('reading_events')):
            raise ValueError('Background isolation requires a quiet extracted comparison reading')
        excerpt = revision['plan']['excerpts'][scene['excerpt']]
        blocks = revision['plan']['worlds'][excerpt['world']]['blocks']
        by_id = _unique(blocks, 'id', 'source block')
        refs = [r for r in scene['source_refs'] if r['world'] == excerpt['world'] and r['pointer'] == '/passage']
        selected = {bid for bid in excerpt['block_ids'] if any(
            r['start'] < by_id[bid]['end'] and r['end'] > by_id[bid]['start'] for r in refs)}
        hidden = [b for b in blocks if b['visible'] and b['id'] not in selected]
        last = scene['reading_events'][-1]
        if (not selected or not hidden or any(not by_id[bid]['visible'] for bid in selected)
                or any(b['start'] < last['end'] and b['end'] > last['start'] for b in hidden)):
            raise ValueError('Background isolation would hide necessary reading or lacks bound targets')
        quiet_at = last['end_time']; restore_at = max(scene['return_start'], scene['end'] - .35)
        times = [scene['start'], scene['candidate_arrive'], quiet_at, scene['settled'],
                 restore_at, scene['end'], scene['extract_start']]
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
                or not 0 <= scene['start'] <= scene['candidate_arrive'] < quiet_at
                    <= scene['settled'] <= restore_at < scene['end'] - 1 / 24
                    < scene['end'] <= revision['plan']['duration']
                or not quiet_at < scene['extract_start'] <= scene['settled']):
            raise ValueError('Background opacity repair escapes its comparison lifetime')
        readings = []
        for event in scene['reading_events']:
            a, b = event['arrival'], event['end_time']
            if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (a, b))
                    or not scene['start'] <= a < b <= quiet_at):
                raise ValueError('Necessary reading does not precede background isolation')
            layers = [block['id'] for block in blocks if block['visible']
                      and block['start'] < event['end'] and block['end'] > event['start']]
            if not layers:
                raise ValueError('Necessary reading lacks its actual source layers')
            if (b > max(scene['candidate_arrive'], quiet_at - .3)
                    and any(name in {block['id'] for block in hidden} for name in layers)):
                raise ValueError('Background fade would hide an unfinished necessary reading')
            readings.append({'time': (a + b) / 2, 'layers': layers})
        for block in [b for b in blocks if b['visible']]:
            layer = revision['layers'].get(block['id'], {})
            if (layer.get('parent') is not None or layer.get('threeD') is not True
                    or layer.get('text', '').replace('\r', '\n') != block['text']
                    or layer.get('inPoint', float('inf')) > scene['start']
                    or layer.get('outPoint', -1) < scene['end']):
                raise ValueError('Background isolation requires its actual original passage layers')
        rows.append({'scene': scene['id'], 'hidden': [b['id'] for b in hidden],
                     'fade_start': max(scene['candidate_arrive'], quiet_at - .3),
                     'quiet_at': quiet_at, 'settled': scene['settled'],
                     'restore_at': restore_at, 'end': scene['end'], 'readings': readings})
    return rows


def _background_readbacks(revision, scope):
    results = []
    if not scope:
        return results
    def close(value, expected):
        return (type(value) in (int, float) and math.isfinite(value)
                and abs(value - expected) <= .01)
    for cid in (revision['native']['comp_id'], revision['native']['master_comp_id']):
        path = _inside(revision['folder'], 'COMPARISON_BACKGROUND_NATIVE_' + str(cid) + '.json')
        if not path.is_file():
            raise ValueError('Required proxy/master background native readback is missing')
        receipt = _record(path, revision['bindings'])
        if (set(receipt) != {'rows', 'plan_sha256', 'human_visual_review'}
                or receipt['plan_sha256'] != revision['native']['plan_sha256']
                or receipt['human_visual_review'] != 'PENDING'
                or [r['scene'] for r in receipt['rows']] != [s['scene'] for s in scope]):
            raise ValueError('Background native readback must cover this exact plan and scene scope')
        for expected, actual in zip(scope, receipt['rows']):
            if (set(actual) != {'scene', 'hidden', 'reading'}
                    or [r['layer'] for r in actual['hidden']] != expected['hidden']):
                raise ValueError('Background native readback target inventory differs')
            for row in actual['hidden']:
                values = {'before': 100, 'quiet': 0, 'settled': 0, 'restore_start': 0, 'restored': 100}
                if set(row) != {'layer', *values} or any(not close(row[k], v) for k, v in values.items()):
                    raise ValueError('Actual background opacity was not isolated and restored')
            readings = [(r['time'], layer) for r in expected['readings'] for layer in r['layers']]
            if len(readings) != len(actual['reading']):
                raise ValueError('Background native readback dropped a necessary reading')
            for (time, layer), observed in zip(readings, actual['reading']):
                if (set(observed) != {'layer', 'time', 'opacity'} or observed['layer'] != layer
                        or type(observed['time']) not in (int, float)
                        or not math.isfinite(observed['time']) or abs(observed['time'] - time) > 1e-8
                        or not close(observed['opacity'], 100)):
                    raise ValueError('Background native readback hid or changed a necessary reading')
        results.append({'comp_id': cid, 'path': str(path), 'sha256': sha256(path),
                        'scope_sha256': sha(scope), 'observations_sha256': sha(receipt['rows'])})
    return results


def _display_build_observations(revision):
    identity = deepcopy(revision['native'])
    count = identity.pop('layers', len(revision['layers']))
    if count != len(revision['layers']):
        raise ValueError('Native build layer count differs from actual readback')
    build_audit = identity.pop('audit', {})
    if 'captions' in build_audit:
        # This template records the real layer ID under `captions[].id`, not
        # under `layer_id`. Deleting one earlier title renumbers those IDs.
        # Resolve only this known record, and only against the exact authored
        # cue and its actually observed native text, comment and lifetime.
        cues = revision['plan']['cues']
        _unique(cues, 'id', 'aligned caption cue')
        if len(build_audit['captions']) != len(cues):
            raise ValueError('Native caption build audit dropped an exact aligned cue')
        by_id = {row['id']: row for row in revision['audit']['layers']}
        names = set()
        for row, cue in zip(build_audit['captions'], cues):
            name = 'CAPTION_' + cue['id']
            layer = by_id.get(row.get('id'), {})
            comment = {'kind': 'audio_aligned_exact_caption', 'segment': cue['segment'],
                       'text': cue['text'], 'start': row.get('start'), 'end': row.get('end')}
            if (set(row) != {'id', 'text', 'start', 'end'} or type(row['id']) is not int
                    or layer.get('name') != name or name in names
                    or layer.get('threeD') is not False or layer.get('parent') is not None
                    or layer.get('text') != '\r'.join(cue['display_lines'])
                    or json.loads(layer.get('comment', '{}')) != comment
                    or row['text'] != cue['text']
                    # AE's JSON serialization rounds binary floats to about
                    # 15 digits. This only binds a readback to its plan cue;
                    # parent/child readback times remain compared exactly.
                    or any(type(row[k]) not in (int, float) or not math.isfinite(row[k])
                           or abs(row[k] - cue[k]) > 1e-9 for k in ('start', 'end'))
                    or any(type(t) not in (int, float) or not math.isfinite(t)
                           for t in (cue['start'], cue['end'], layer.get('inPoint'), layer.get('outPoint')))
                    or not 0 <= cue['start'] < cue['end'] <= revision['plan']['duration']
                    or abs(layer['inPoint'] - cue['start']) > .0001
                    or abs(layer['outPoint'] - cue['end']) > .0001):
                raise ValueError('Caption ID must bind its exact aligned native caption layer')
            names.add(name); row['id'] = name
        actual = {l['name'] for l in revision['audit']['layers']
                  if l['name'].startswith('CAPTION_') and isinstance(l.get('text'), str)}
        if actual != names:
            raise ValueError('Native caption layer inventory differs from exact aligned cues')
    for key in ('project_path', 'comp_id', 'master_comp_id', 'plan_sha256', 'template_sha256'):
        identity.pop(key)
    shadow = {**revision, 'audit': {'project': str(revision['project']),
        'layers': revision['audit']['layers'], 'unrendered_master': revision['audit']['unrendered_master'],
        'build_audit': build_audit, 'native_identity': identity}}
    return _native_observations(shadow)


def _display_context(old, new):
    before, after = old['sources']['template'], new['sources']['template']
    old_sha, new_sha = old['native']['template_sha256'], new['native']['template_sha256']
    same_known = (before == after and old_sha in (
        *SOURCE_ATTENTION_TEMPLATE_SHA256_ALLOWLIST, *BACKGROUND_TEMPLATE_PAIRS.values()))
    exact_patch = (BACKGROUND_TEMPLATE_PAIRS.get(old_sha) == new_sha
                   and before.count(BACKGROUND_OLD) == 1 and BACKGROUND_NEW not in before
                   and after == before.replace(BACKGROUND_OLD, BACKGROUND_NEW))
    if not same_known and not exact_patch:
        raise ValueError('Only the exact approved background template byte patch permits display repair')
    if old['sources']['reading_rig'] != new['sources']['reading_rig']:
        raise ValueError('Changed reading rig cannot reuse native frames')
    changes, common = _display_difference(old, new)
    background_changes = [c for c in changes if c['field'] == 'comparison_background_policy']
    if background_changes and new_sha not in BACKGROUND_TEMPLATE_PAIRS.values():
        raise ValueError('Background repair requires its exact approved native consumer')
    titles = [c for c in changes if c['field'] == 'screen_title']
    removed = {'TASK_TITLE_' + c['scene'] for c in titles}
    if set(old['layers']) - removed != set(new['layers']) or not removed <= old['layers'].keys():
        raise ValueError('Only the explicitly hidden native title layers may be removed')
    for change in titles:
        scene = next(s for s in old['plan']['scenes'] if s['id'] == change['scene'])
        layer = old['layers']['TASK_TITLE_' + scene['id']]
        end = (min(scene['end'], max(scene['start'] + .25, scene['reading_events'][0]['depart']))
               if scene.get('reading_events') else scene['end'])
        if (layer.get('text') != change['from'] or layer.get('parent') is not None
                or abs(layer.get('inPoint', -1) - scene['start']) > 1e-6
                or abs(layer.get('outPoint', -1) - end) > 1e-6):
            raise ValueError('Hidden title must be the actual bounded authored native title')
    for name in set(old['layers']) - removed:
        if old['layers'][name] != new['layers'][name]:
            raise ValueError('Actual native geometry, text, font or lifetime changed: ' + name)
    observations = _native_observations(old)
    if observations != _native_observations(new):
        raise ValueError('Native camera, reading or other observed properties changed')
    # The build's own full layout/reading audit also remains exact after IDs
    # are mapped to the actual layer names. Only the removed title count varies.
    build_observations = [_display_build_observations(r) for r in (old, new)]
    if build_observations[0] != build_observations[1]:
        raise ValueError('Native build layout, camera or reading observations changed')
    old_scope, new_scope = _background_scope(old), _background_scope(new)
    readbacks = {'parent': _background_readbacks(old, old_scope),
                 'child': _background_readbacks(new, new_scope)}
    ids = {c['scene'] for c in changes}
    affected = []
    for scene in old['plan']['scenes']:
        if scene['id'] not in ids:
            continue
        lo, hi = scene['start'], scene['end']
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (lo, hi))
                or not 0 <= lo < hi <= old['plan']['duration']):
            raise ValueError('Finite comparison scene bounds are required')
        affected.append({'scene': scene['id'], 'start': max(0, math.floor(lo * 24) - 1),
                         'end': min(old['plan']['frames'], math.ceil(hi * 24) + 1),
                         'repairs': [c['repair'] for c in changes if c['scene'] == scene['id']]})
    bindings = {**old['bindings'], **new['bindings']}
    _bound_file(old['project'], sha256(old['project']), bindings)
    return old, new, {'schema': SCHEMA, 'operation': DISPLAY_OPERATION,
        'parent': str(old['folder']), 'folder': str(new['folder']), 'input_files': bindings,
        'plan_semantic_sha256': sha(common), 'alignment_semantic_sha256': sha(old['alignment']),
        'unaffected_native_layers_sha256': sha({k: v for k, v in old['layers'].items() if k not in removed}),
        'native_observations_sha256': sha(observations), 'native_build_observations_sha256': sha(build_observations[0]),
        'template_repairs': ['opt_in_comparison_background_isolation'] if exact_patch else [],
        'display_repairs': changes, 'background_isolation_scope': new_scope,
        'background_isolation_readbacks': readbacks, 'removed_native_layers': sorted(removed),
        'excluded_native_layers': sorted(removed | {n for s in new_scope if s['scene'] in ids for n in s['hidden']}),
        'affected_frame_ranges': affected, 'scene_boundary_guard_frames': 1,
        'opacity_readback': 'BOUND_PROXY_AND_MASTER_SAMPLES; ALL_KEYS_NOT_OBSERVED; EXACT_TEMPLATE_AND_PLAN_BOUND_WRITES',
        'live_native_validation': 'CALLER_CURRENT_NATIVE_AND_AUDIT_REQUIRED_NO_ADOBE_IN_THIS_MODULE',
        'new_native_render': False, 'human_approved': False, 'public_render_ready': False}


def _affected(plan):
    result = []
    seen = set()
    for scene in plan['scenes']:
        if scene['id'] in seen:
            raise ValueError('Duplicate scene identity')
        seen.add(scene['id'])
        reasons = []
        if scene.get('motion_treatment') == 'in_place_check' and (
                any(e['target'] == 'candidate' for e in scene.get('attention_events', []))
                or scene.get('event') == 'supported'):
            reasons.append('light_candidate_initial_ink')
        heading = scene.get('screen_title', scene.get('title'))
        if (heading and scene['kind'] in ('compare', 'replay')
                and scene.get('motion_treatment') != 'in_place_check' and scene.get('reading_events')):
            reasons.append('comparison_title_reading_fade')
        if reasons:
            lo, hi = scene['start'], scene['end']
            if (not all(type(t) in (int, float) and math.isfinite(t) for t in (lo, hi))
                    or not 0 <= lo < hi <= plan['duration']):
                raise ValueError('Finite scene bounds within the complete clock required')
            result.append({'scene': scene['id'], 'start': max(0, math.floor(lo * 24)),
                           'end': min(plan['frames'], math.ceil(hi * 24)), 'repairs': reasons})
    return result


def _context(parent, folder):
    old, new = _revision(parent), _revision(folder)
    if old['folder'] == new['folder']:
        raise ValueError('A new native revision is required')
    if _display_requested(old, new):
        return _display_context(old, new)
    if old['sources']['template'] == new['sources']['template']:
        if old['native']['template_sha256'] not in SOURCE_ATTENTION_TEMPLATE_SHA256_ALLOWLIST:
            raise ValueError('Unknown native source-attention template requires independent proof review')
        if old['sources']['reading_rig'] != new['sources']['reading_rig']:
            raise ValueError('Changed reading rig cannot reuse native frames')
        changes, visibility, common = _attention_difference(old, new)
        source_ids = {c['scene'] for c in changes}; visibility_ids = {c['scene'] for c in visibility}
        ids = source_ids | visibility_ids
        scenes = [s for s in old['plan']['scenes'] if s['id'] in ids]
        def affected_layers(revision):
            return (_source_attention_layers(revision, [s for s in revision['plan']['scenes'] if s['id'] in source_ids])
                    | _reading_visibility_layers(revision, [s for s in revision['plan']['scenes'] if s['id'] in visibility_ids]))
        excluded_layers = affected_layers(old)
        if excluded_layers != affected_layers(new):
            raise ValueError('Native source-attention target inventory changed')
        if set(old['layers']) != set(new['layers']):
            raise ValueError('Native layer inventory changed')
        # Current readback omits SourceText keys. All fields it DOES observe,
        # including the affected clones' text/geometry/font/lifetime, must match.
        # The fixed template and unchanged complete plan bound the hidden style
        # write to these scene-local clones. No part of this scene is reused.
        for name, layer in old['layers'].items():
            if layer != new['layers'][name]:
                raise ValueError('Actual native layer differs beyond source-attention key times: ' + name)
        observations = _native_observations(old)
        if observations != _native_observations(new):
            raise ValueError('Native camera, reading or other observed properties changed')
        affected = [{'scene': s['id'], 'start': max(0, math.floor(s['start'] * 24)),
                     'end': min(old['plan']['frames'], math.ceil(s['end'] * 24)),
                     'repairs': (['source_attention_anchor_cue_rebind'] if s['id'] in source_ids else [])
                                + (['quiet_candidate_during_source_reading'] if s['id'] in visibility_ids else [])}
                    for s in scenes]
        bindings = {**old['bindings'], **new['bindings']}
        _bound_file(old['project'], sha256(old['project']), bindings)
        return old, new, {'schema': SCHEMA, 'operation': ATTENTION_OPERATION,
            'parent': str(old['folder']), 'folder': str(new['folder']), 'input_files': bindings,
            'plan_semantic_sha256': sha(common), 'alignment_semantic_sha256': sha(old['alignment']),
            'unaffected_native_layers_sha256': sha({k: v for k, v in old['layers'].items() if k not in excluded_layers}),
            'native_observations_sha256': sha(observations),
            'template_repairs': [], 'source_attention_repairs': changes,
            'candidate_reading_visibility_repairs': visibility,
            'excluded_native_layers': sorted(excluded_layers), 'affected_frame_ranges': affected,
            'source_text_readback': 'KEYS_NOT_OBSERVED; FIXED_TEMPLATE_AND_EXACT_PLAN_DELTA_BOUND_SCENE_LOCAL_WRITES',
            'candidate_opacity_readback': 'KEYS_NOT_OBSERVED; FIXED_TEMPLATE_AND_BOUNDED_CANDIDATE_LIFETIME',
            'live_native_validation': 'CALLER_CURRENT_NATIVE_AND_AUDIT_REQUIRED_NO_ADOBE_IN_THIS_MODULE',
            'new_native_render': False, 'human_approved': False, 'public_render_ready': False}
    if old['normalized'] != new['normalized'] or old['alignment'] != new['alignment']:
        raise ValueError('Plans differ beyond bound revision paths and copy headers')
    before, after = old['sources']['template'], new['sources']['template']
    if (before.count(LIGHT_OLD) != 1 or LIGHT_NEW in before or before.count(TITLE_OLD) != 1
            or TITLE_NEW in before
            or after != before.replace(LIGHT_OLD, LIGHT_NEW).replace(TITLE_OLD, TITLE_NEW)):
        raise ValueError('Only the two exact approved native template repairs permit reuse')
    if old['sources']['reading_rig'] != new['sources']['reading_rig']:
        raise ValueError('Changed reading rig cannot reuse native frames')
    affected = _affected(old['plan'])
    if not affected:
        raise ValueError('No proved template repair influence was identified')
    excluded_layers = {'LIGHT_CANDIDATE_' + r['scene'] for r in affected
                       if 'light_candidate_initial_ink' in r['repairs']}
    excluded_layers |= {'TASK_TITLE_' + r['scene'] for r in affected
                        if 'comparison_title_reading_fade' in r['repairs']}
    if set(old['layers']) != set(new['layers']):
        raise ValueError('Native layer inventory changed')
    if not excluded_layers <= old['layers'].keys():
        raise ValueError('A repaired scene lacks its actual native target layer')
    for name, layer in old['layers'].items():
        if name not in excluded_layers and layer != new['layers'][name]:
            raise ValueError('Unaffected actual native layer differs: ' + name)
    bindings = {**old['bindings'], **new['bindings']}
    # The parent is historical and must stay immutable. The new AEP is saved
    # during each legitimate render, so its mutable bytes are not a part key.
    _bound_file(old['project'], sha256(old['project']), bindings)
    return old, new, {'schema': SCHEMA, 'operation': 'verified_parent_bytes_not_new_native_render',
        'parent': str(old['folder']), 'folder': str(new['folder']), 'input_files': bindings,
        'plan_semantic_sha256': sha(old['normalized']), 'alignment_semantic_sha256': sha(old['alignment']),
        'unaffected_native_layers_sha256': sha({k: v for k, v in old['layers'].items() if k not in excluded_layers}),
        'template_repairs': ['light_candidate_initial_ink', 'comparison_title_reading_fade'],
        'excluded_native_layers': sorted(excluded_layers), 'affected_frame_ranges': affected,
        'live_native_validation': 'CALLER_CURRENT_NATIVE_AND_AUDIT_REQUIRED_NO_ADOBE_IN_THIS_MODULE',
        'new_native_render': False, 'human_approved': False, 'public_render_ready': False}


def _probe_master(path, frames):
    data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
        '-show_streams', '-of', 'json', str(path)]))
    rows = [s for s in data['streams'] if s['codec_type'] == 'video']
    if (len(rows) != 1 or len(data['streams']) != 1 or rows[0]['codec_name'] != 'h264'
            or [rows[0]['width'], rows[0]['height'], rows[0]['r_frame_rate'],
                rows[0]['avg_frame_rate'], int(rows[0]['nb_read_frames'])]
               != [3840, 2160, '24/1', '24/1', frames]
            or abs(float(rows[0]['duration']) - frames / 24) > 1 / 24000):
        raise ValueError('Parent media is not the exact complete native 4K24 part')
    return {k: rows[0][k] for k in ('codec_name', 'width', 'height', 'r_frame_rate',
                                  'avg_frame_rate', 'nb_read_frames', 'duration')}


def _parent_part(old, path, bindings, *, probe=True, trail=()):
    path = Path(path).resolve()
    if path.parent != (old['folder'] / 'native-master-parts').resolve():
        raise ValueError('Parent receipt must remain inside native-master-parts')
    row = _record(path, bindings)
    if (row.get('done') is not True
            or row.get('comp_id') != old['native']['master_comp_id']
            or row.get('plan_sha256') != old['native']['plan_sha256']
            or row.get('native_identity_sha256') != sha256(old['folder'] / 'native-identity.json')
            or type(row.get('start')) is not int or type(row.get('end')) is not int
            or not 0 <= row['start'] < row['end'] <= old['plan']['frames']):
        raise ValueError('Parent part lacks its completed original native master identity')
    media = Path(row['path']).resolve()
    nested = 'reuse' in row or row.get('new_native_render') is False
    if media.suffix.lower() != '.mp4' or (not nested and media.parent != path.parent):
        raise ValueError('Parent native media path must remain in its bound parts directory')
    chain = None
    if nested:
        verified = _validate_reused_part(old['folder'], row, media, bindings, trail)
        chain = verified['provenance_chain']
    elif row.get('rendered_in_revision', old['plan']['revision']) != old['plan']['revision']:
        raise ValueError('Original native renderer revision provenance is contradictory')
    _bound_file(media, row['sha256'], bindings)
    shape = _probe_master(media, row['end'] - row['start']) if probe else None
    item = {'receipt': str(path), 'receipt_sha256': sha256(path),
            'media': str(media), 'media_sha256': row['sha256'],
            'start': row['start'], 'end': row['end'], 'probe': shape}
    if chain is not None:
        item['reuse_chain'] = chain
    return row, item


def _overlaps(row, ranges):
    return [r['scene'] for r in ranges if row['start'] < r['end'] and row['end'] > r['start']]


def reuse_unchanged_parts(parent, folder):
    """Verify first, then write provenance-preserving child cache receipts.

    Parent media are referenced in place. Their disappearance or any changed
    parent/new input invalidates reuse, including on subsequent resume.
    """
    old, new, report = _context(parent, folder)
    eligible, excluded = [], []
    parent_parts = old['folder'] / 'native-master-parts'
    for media in parent_parts.glob('part-*.mp4'):
        if not media.with_suffix('.json').is_file():
            raise ValueError('Parent native media lacks a completed receipt')
    parts = [_parent_part(old, path, report['input_files']) for path in parent_parts.glob('part-*.json')]
    complete_parent = report['operation'] in (ATTENTION_OPERATION, DISPLAY_OPERATION)
    cursor = 0 if complete_parent else -1
    for row, item in sorted(parts, key=lambda pair: pair[0]['start']):
        if row['start'] < cursor:
            raise ValueError('Parent native part ranges overlap or run backwards')
        if complete_parent and row['start'] != cursor:
            raise ValueError('Source-anchor repair requires the complete gap-free parent native master')
        cursor = row['end']
        intersections = _overlaps(row, report['affected_frame_ranges'])
        (excluded if intersections else eligible).append({**item, 'affected_scenes': intersections})
    if complete_parent and cursor != old['plan']['frames']:
        raise ValueError('Source-anchor repair requires the complete parent native master')
    if not eligible:
        raise ValueError('No verified parent part lies outside the changed scenes')
    report.update(reused_parts=eligible, excluded_parts=excluded,
                  reused_frames=sum(r['end'] - r['start'] for r in eligible))
    proof_path = new['folder'] / PROOF
    directory = new['folder'] / 'native-master-parts'
    if proof_path.exists() and read(proof_path) != report:
        raise ValueError('Preserve the existing reuse proof; reviewed inputs changed')
    # Check every dependency again after potentially long media probing.
    for path, digest in report['input_files'].items():
        _bound_file(path, digest, {})
    rows = []
    for item in eligible:
        parent_row = read(item['receipt'])
        result = deepcopy(parent_row)
        result.update(path=item['media'], comp_id=new['native']['master_comp_id'],
            plan_sha256=new['native']['plan_sha256'],
            native_identity_sha256=sha256(new['folder'] / 'native-identity.json'),
            rendered_in_revision=parent_row.get('rendered_in_revision', old['plan']['revision']), new_native_render=False)
        result['reuse'] = {'schema': SCHEMA, 'proof': str(proof_path),
            'parent_receipt': item['receipt'], 'parent_receipt_sha256': item['receipt_sha256']}
        target = directory / Path(item['receipt']).name
        if target.exists():
            existing = read(target)
            expected = deepcopy(existing); expected.get('reuse', {}).pop('proof_sha256', None)
            if expected != result:
                raise ValueError('A different child native part already occupies this receipt')
        elif target.with_suffix('.mp4').exists():
            raise ValueError('Inspect unreceipted child media; never overwrite it during reuse')
        rows.append((target, result))
    if not proof_path.exists():
        write(proof_path, report)
    digest = sha256(proof_path)
    directory.mkdir(exist_ok=True)
    for target, result in rows:
        result['reuse']['proof_sha256'] = digest
        if target.exists() and read(target) != result:
            raise ValueError('Existing child receipt has a changed reuse proof')
        if not target.exists():
            write(target, result)
    return report


def _validate_reused_part(folder, row, path, bindings, trail):
    folder = Path(folder).resolve(); path = Path(path).resolve()
    reuse = row.get('reuse', {})
    proof_path = _inside(folder, PROOF)
    if (not isinstance(reuse, dict) or row.get('new_native_render') is not False
            or reuse.get('schema') != SCHEMA or Path(reuse.get('proof', '')).resolve() != proof_path):
        raise ValueError('Explicit local native-part reuse proof required')
    if proof_path in trail or len(trail) >= MAX_REUSE_DEPTH:
        raise ValueError('Cyclic or excessive native-part reuse ancestry')
    trail = (*trail, proof_path)
    _bound_file(proof_path, reuse['proof_sha256'], bindings)
    report = read(proof_path)
    old, new, context = _context(report['parent'], folder)
    for key, value in context.items():
        if key == 'input_files':
            if any(report[key].get(p) != d for p, d in value.items()):
                raise ValueError('Reused native context binding changed')
        elif report.get(key) != value:
            raise ValueError('Reused native context no longer proves the same output')
    for file, digest in report['input_files'].items():
        _bound_file(file, digest, bindings)
    matches = [r for r in report['reused_parts'] if r['receipt'] == reuse['parent_receipt']]
    if len(matches) != 1:
        raise ValueError('Reused part is absent from the proved unchanged set')
    item = matches[0]
    if reuse['parent_receipt_sha256'] != item['receipt_sha256']:
        raise ValueError('Reused parent receipt identity changed')
    if item.get('affected_scenes') != []:
        raise ValueError('A reused part cannot include an affected scene')
    parent_row, checked = _parent_part(old, item['receipt'], bindings, probe=True, trail=trail)
    if checked != {k: v for k, v in item.items() if k != 'affected_scenes'}:
        raise ValueError('Reused parent media or observation changed')
    expected = deepcopy(parent_row)
    expected.update(path=item['media'], comp_id=new['native']['master_comp_id'],
        plan_sha256=new['native']['plan_sha256'],
        native_identity_sha256=sha256(folder / 'native-identity.json'),
        rendered_in_revision=parent_row.get('rendered_in_revision', old['plan']['revision']),
        new_native_render=False, reuse=reuse)
    if (row != expected or path != Path(item['media']).resolve()
            or _overlaps(row, report['affected_frame_ranges'])):
        raise ValueError('Reused native row exceeds its unchanged parent frame range')
    chain = [{'revision': new['plan']['revision'], 'plan_sha256': new['native']['plan_sha256'],
              'native_identity_sha256': sha256(folder / 'native-identity.json'),
              'proof': str(proof_path), 'proof_sha256': reuse['proof_sha256'],
              'operation': report['operation'], 'parent': report['parent'],
              'parent_receipt': item['receipt'], 'parent_receipt_sha256': item['receipt_sha256']}]
    chain.extend(checked.get('reuse_chain', []))
    return {'status': 'VERIFIED_PARENT_NATIVE_BYTES', 'new_native_render': False,
            'parent_receipt': item['receipt'], 'media_sha256': item['media_sha256'],
            'range': [row['start'], row['end']], 'proof_sha256': reuse['proof_sha256'],
            'provenance_chain': chain}


def validate_reused_part(folder, row, path):
    """Revalidate every original/proof/media dependency without touching Adobe.

    The caller separately validates current native identity and audit. The child
    AEP's metadata may legitimately change on saves; the historical parent AEPs
    and all proof-bound inputs must retain their exact bytes.
    """
    bindings = {}
    result = _validate_reused_part(folder, row, path, bindings, ())
    for file, digest in bindings.items():
        _bound_file(file, digest, {})
    return result
