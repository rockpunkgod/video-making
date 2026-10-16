"""Consume the current author's decisions through the existing episode entry.

This is the portable part of the former private AV-plan author. Facts remain
in supplied frozen bundles; the author supplies copy, source ranges and shots.
There is no question solver, automatic creative approval or new runtime.
"""
from copy import deepcopy
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

from video_contracts import ROOT, read, write, sha, pointer, verify_bundle, status_matches
from scripts.voice_delivery import validate as validate_voice, asset, sha256, pad_to_video_frame

CURRENT = ROOT / 'local-data/free-showcase/PRODUCTION_INDEX.json'
AUTHOR = 'AV_AUTHOR.json'
KINDS = {'task', 'locate', 'compare', 'answer', 'replay', 'recap'}
SHOT_KEYS = {'id', 'kind', 'world', 'voice_ids', 'title', 'excerpt', 'candidate',
             'event', 'replay_of', 'source_refs', 'action_refs', 'terminal_refs',
             'recognition_seconds', 'travel_seconds', 'post_seconds', 'voice_pre',
             'candidate_anchor', 'event_anchor', 'attention', 'locator',
             'audience_intent', 'pre_excerpt', 'secondary_excerpt', 'secondary_anchor', 'recap_worlds',
             'candidate_entry_seconds'}


def current_folder():
    if not CURRENT.exists():
        raise FileNotFoundError('Current private production index unavailable; supply an actual revision')
    p = Path(read(CURRENT)['revision']).resolve()
    if not p.is_relative_to((ROOT / 'local-data').resolve()) or not (p / AUTHOR).exists():
        raise ValueError('Current revision must contain the actual private author input')
    return p


def checked_author(folder):
    a = read(folder / AUTHOR)
    if a['product'] != 'FREE_SHOWCASE' or a['public_render_ready'] is not False:
        raise ValueError('This consumer is an internal FREE_SHOWCASE rough-cut adapter')
    if a['media_role'] != 'EDITORIAL_PROXY' or a['format'] != {'width': 1920, 'height': 1080, 'fps': 24}:
        raise ValueError('Unsupported production profile; do not silently substitute a proxy')
    for p, digest in a['input_files'].items():
        if sha256(p) != digest:
            raise ValueError('Bound input changed: ' + p)
    bundles = {}
    for world, paths in a['sources'].items():
        b, st = read(paths['bundle']), read(paths['status'])
        verify_bundle(b)
        if not status_matches(b, st):
            raise ValueError('Supplied current status does not authorize ' + world)
        bundles[world] = b
    if len(bundles) < 2 or len({b['source_snapshot']['question_id'] for b in bundles.values()}) != len(bundles):
        raise ValueError('The main film requires distinct, source-bound questions')
    voices = {v['id']: v for v in a['voices']}
    if len(voices) != len(a['voices']):
        raise ValueError('Duplicate voice identity')
    used, decided, finals, ids, replay_count = [], {}, set(), set(), 0
    for s in a['scenes']:
        if set(s) - SHOT_KEYS:
            raise ValueError('Unsupported author decision: ' + str(sorted(set(s) - SHOT_KEYS)))
        if s['kind'] not in KINDS or s['id'] in ids or s['world'] not in bundles:
            raise ValueError('Unsupported or repeated scene identity')
        ids.add(s['id']); used.extend(s['voice_ids'])
        if not s['audience_intent'].strip():
            raise ValueError('The author must specify the concrete viewing purpose')
        for name in ('recognition_seconds', 'travel_seconds', 'post_seconds', 'voice_pre'):
            if type(s[name]) not in (int, float) or not math.isfinite(s[name]) or s[name] < 0:
                raise ValueError('Invalid authored timing: ' + name)
        lead=s.get('candidate_entry_seconds',0)
        if (type(lead) not in (int,float) or not math.isfinite(lead) or lead<0
                or lead and (lead<2.1 or s['kind']!='compare' or s.get('pre_excerpt') or s.get('secondary_excerpt') or s.get('candidate_anchor'))):
            raise ValueError('Unsupported candidate recognition route')
        for ref in s['source_refs']:
            q = bundles[ref['world']]['source_snapshot']; text = pointer(q, ref['pointer'])
            if text[ref['start']:ref['end']] != ref['quote']:
                raise ValueError('Source span changed in ' + s['id'])
        for attention in s.get('attention',[]):
            if set(attention)!={'anchor','phrase','target'} or attention['target'] not in ('source','candidate'):
                raise ValueError('Unsupported attention decision')
            if attention['target']=='source':
                phrases=[a['excerpts'][s[key]]['quote'] for key in ('excerpt','secondary_excerpt') if s.get(key)]
            else:
                phrases=[bundles[s['world']]['source_snapshot']['options'][s['candidate']]]
            if not any(attention['phrase'] in text for text in phrases):raise ValueError('Attention phrase is not in its bound source')
        for ref in s['action_refs']:
            actual = pointer(bundles[ref['world']]['analysis'], ref['pointer'])
            if sha(actual) != ref['sha']:
                raise ValueError('Frozen action changed')
        world = s['world']; b = bundles[world]
        terminal = {x['candidate']: x for x in b['analysis']['question_verification']['candidate_bindings']}
        for ref in s['terminal_refs']:
            if ref != terminal.get(ref['candidate']):
                raise ValueError('Candidate terminal must match the supplied frozen analysis')
        if s.get('event'):
            candidate = s['candidate']; event = s['event']
            if event == 'final':
                if set(decided.get(world, {})) != set(b['source_snapshot']['options']):
                    raise ValueError('Final answer before complete candidate checks')
                if terminal[candidate]['effect'] != 'retain' or set(x['candidate'] for x in s['terminal_refs']) != set(terminal):
                    raise ValueError('Final answer lacks complete frozen closure')
                finals.add(world)
            else:
                effect = 'retain' if event == 'supported' else 'eliminate' if event == 'eliminate' else None
                if effect != terminal[candidate]['effect'] or s['terminal_refs'] != [terminal[candidate]]:
                    raise ValueError('Authored event exceeds frozen candidate scope')
                if candidate in decided.setdefault(world, {}):
                    raise ValueError('Candidate decision executed twice')
                decided[world][candidate] = effect
        if s['kind'] == 'replay':
            replay_count += 1
            if world not in finals or s.get('event') or s['replay_of'] not in ids - {s['id']}:
                raise ValueError('A replay recalls an earlier completed comparison; it cannot reset candidates')
        if s['kind'] == 'locate':
            loc = s['locator']; q = b['source_snapshot']
            for field, span in (('stem', loc['stem_span']), ('passage', loc['passage_span'])):
                if q[field][span[0]:span[1]] != loc['identity']:
                    raise ValueError('Locator identity must occur in the exact supplied source')
            if not loc['block_span'][0] <= loc['passage_span'][0] < loc['passage_span'][1] <= loc['block_span'][1]:
                raise ValueError('Locator target outside the authorized block')
    if set(used) != set(voices) or len(used) != len(set(used)):
        raise ValueError('Every exact voice take must have one scene placement')
    if finals != set(bundles) or replay_count != 1:
        raise ValueError('Main film must close each question and contain the one authored focused replay')
    return a, bundles


def voice(folder):
    a, _ = checked_author(folder)
    selected=delivery_path(folder,a)
    if selected.exists():
        delivery=validate_voice(selected)
        actual={x['id']:asset(selected.parent,x['transcript']).read_text('utf-8-sig').strip() for x in delivery['clips']}
        if actual!={v['id']:v['text'] for v in a['voices']}:raise ValueError('Selected voice copy is stale')
        return {'reused_complete_delivery':len(actual),'delivery':str(selected)}
    clips = folder / 'VOICE_INPUT.json'; rows = [{'id': v['id'], 'text': v['text']} for v in a['voices']]
    if clips.exists() and read(clips) != rows:
        raise ValueError('Changed copy needs a new voice delivery revision')
    if not clips.exists(): write(clips, rows)
    dest = folder / 'voice'
    if (dest / 'delivery.json').exists():
        delivery = validate_voice(dest / 'delivery.json')
        actual = {x['id']: asset(dest, x['transcript']).read_text('utf-8-sig').strip() for x in delivery['clips']}
        if actual != {x['id']: x['text'] for x in rows}: raise ValueError('Voice copy is stale')
        return {'reused_complete_delivery': len(rows)}
    p = a['producer']
    subprocess.run([p['python'], '-X', 'utf8', str(ROOT / 'voicepacks/tools/generate_gpt_sovits.py'),
                    '--pack', p['pack'], '--runtime', p['runtime'], '--clips-file', str(clips),
                    '--output', str(dest), '--offline'], check=True)
    return {'delivery': str(dest / 'delivery.json')}


def grid(t, fps=24):
    return math.ceil((t - 1e-8) * fps) / fps


def delivery_path(folder, author):
    result=(folder/author.get('voice_delivery','voice/delivery.json')).resolve()
    if not result.is_relative_to(folder.resolve()):raise ValueError('Selected voice delivery must belong to this revision')
    return result


def compile_clock(a, clips, aligned):
    """Actual complete takes determine the clock; author holds alter real events."""
    fps = a['format']['fps']; cursor = 0; scenes = []; segments = []; cues = []; events = []
    voice_by_id = {x['id']: x for x in a['voices']}
    for shot in a['scenes']:
        s = deepcopy(shot); s['start'] = cursor
        lead=s.get('candidate_entry_seconds',0)
        s['recognition_end'] = grid(cursor + lead + s['recognition_seconds'], fps)
        s['extract_start'] = s['recognition_end']
        s['settled'] = grid(s['extract_start'] + s['travel_seconds'], fps)
        clock = grid(cursor + s['voice_pre'], fps); positions = []
        for vid in s['voice_ids']:
            v, c, align = voice_by_id[vid], clips[vid], aligned[vid]
            if align['transcript'] != v['text'] or align['audio_sha256'] != c['audio_sha256']:
                raise ValueError('Audio alignment belongs to another take or transcript')
            start = clock; end = start + c['duration_seconds']
            segments.append({**v, 'scene_id': s['id'], 'voice_start': start, 'voice_end': end,
                             'voice': deepcopy(c), 'time_stretch': False, 'truncated': False})
            for cue in align['cues']:
                if v['text'][cue['text_start']:cue['text_end']] != cue['text']:
                    raise ValueError('Caption text is not the spoken transcript')
                if not 0 <= cue['start'] < cue['end'] <= c['duration_seconds'] + .001:
                    raise ValueError('Caption outside complete take')
                cues.append({**cue, 'id': vid + '_' + str(len(cues)), 'scene_id': s['id'],
                             'segment': vid, 'start': start + cue['start'], 'end': start + cue['end']})
            positions.append((vid, start, end)); clock = grid(end + .12, fps)
        s['voice_start'] = positions[0][1]; s['voice_end'] = positions[-1][2]
        s['end'] = grid(max(s['voice_end'], s['settled']) + s['post_seconds'], fps)
        def anchor(phrase, fallback):
            if not phrase: return fallback
            for vid, start, _ in positions:
                at = voice_by_id[vid]['text'].find(phrase)
                if at >= 0:
                    matches = [c for c in aligned[vid]['cues'] if c['text_start'] <= at < c['text_end']]
                    if len(matches) != 1: raise ValueError('Ambiguous spoken anchor')
                    return grid(start + matches[0]['start'], fps)
            raise ValueError('Authored spoken anchor is absent: ' + phrase)
        s['candidate_start'] = grid(cursor+lead-1.6,fps) if lead else max(s['settled'] + .12, anchor(s.get('candidate_anchor'), s['settled'] + .12))
        s['attention_events'] = [{**x, 'time': anchor(x['anchor'], s['settled'])} for x in s.get('attention', [])]
        if s.get('secondary_excerpt'):
            s['secondary_at'] = anchor(s['secondary_anchor'], None)
        if s.get('event'):
            t = anchor(s.get('event_anchor'), grid(s['voice_end'] + .08, fps))
            if t < s['settled'] or t >= s['end'] - .5:
                raise ValueError('Decision requires visible comparison and time for its complete movement')
            if s['event']!='final' and t<s['candidate_start']+.8:
                raise ValueError('Candidate must arrive before its decision')
            s['event_time'] = t
            events.append({'scene': s['id'], 'world': s['world'], 'candidate': s['candidate'],
                           'kind': s['event'], 'time': t, 'refs': s['terminal_refs'],
                           'credit': 'whole_question_terminal_not_brand_method'})
        scenes.append(s); cursor = s['end']
    return {'scenes': scenes, 'segments': segments, 'cues': cues, 'candidate_events': events,
            'duration': cursor, 'frames': round(cursor * fps)}


def prepare(folder):
    a, bundles = checked_author(folder)
    delivery_file = delivery_path(folder,a); delivery = validate_voice(delivery_file)
    aligned_path = folder / 'VOICE_ALIGNMENT.json'
    if not aligned_path.exists(): raise FileNotFoundError('Run align for the actual new voice delivery first')
    aligned = {x['id']: x for x in read(aligned_path)['clips']}
    clips = {}
    conversions_file=folder/'VOICE_RESAMPLE_RECEIPT.json'
    conversions=read(conversions_file) if conversions_file.exists() else {}
    for c in delivery['clips']:
        raw = asset(delivery_file.parent, c['audio']); target = folder / 'voice-48k' / (c['id'] + '.wav')
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            previous=conversions.get(c['id'])
            if not previous or previous['original_sha256']!=sha256(raw) or previous['converted_sha256']!=sha256(target):
                raise ValueError('Changed take requires a new converted audio revision: '+c['id'])
        else:
            subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(raw), '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(target)], check=True)
            conversions[c['id']]={'original_sha256':sha256(raw),'converted_sha256':sha256(target)}
            write(conversions_file,conversions)
        with wave.open(str(target)) as w:
            if abs(w.getnframes() / 48000 - c['duration_seconds']) > 1 / 48000:
                raise ValueError('Resampling changed the complete take duration')
        padded = target.with_name(c['id'] + '-frame.wav')
        if not padded.exists(): pad_to_video_frame(target, padded)
        clips[c['id']] = {**c, 'path': str(target), 'padded_path': str(padded), 'sha256': sha256(target),
                          'padded_sha256': sha256(padded), 'original_path': str(raw)}
    plan = compile_clock(a, clips, aligned)
    worlds = {}
    for name, b in bundles.items():
        q = b['source_snapshot']; passage = q['passage']; bounds = {0, len(passage)}
        for m in re.finditer(r'\n+', passage): bounds.update([m.start(), m.end()])
        for ex in a['excerpts'].values():
            if ex['world'] == name: bounds.update([ex['start'], ex['end']])
        bs = sorted(bounds)
        blocks = [{'id': name + '-source-' + str(lo), 'start': lo, 'end': hi,
                   'text': passage[lo:hi], 'visible': bool(passage[lo:hi].strip())} for lo, hi in zip(bs, bs[1:])]
        worlds[name] = {'question': q, 'blocks': blocks, 'source': a['sources'][name]}
    excerpts = deepcopy(a['excerpts'])
    for key, ex in excerpts.items():
        q = worlds[ex['world']]['question']
        if q['passage'][ex['start']:ex['end']] != ex['quote']: raise ValueError('Excerpt changed: ' + key)
        ex['block_ids'] = [b['id'] for b in worlds[ex['world']]['blocks'] if b['visible'] and b['start'] >= ex['start'] and b['end'] <= ex['end']]
    plan.update(revision=a['revision'], format=a['format'], master_format={'width':3840,'height':2160,'fps':24},
                media_role='EDITORIAL_PROXY', worlds=worlds, excerpts=excerpts, world_order=list(worlds),
                author_sha256=sha256(folder / AUTHOR), voice_delivery_sha256=sha256(delivery_file),
                alignment_sha256=sha256(aligned_path), public_render_ready=False,
                human_creative_review='PENDING', listening_review='PENDING', student_count=0)
    dest = folder / 'AV_PLAN.json'
    if dest.exists() and read(dest) != plan:
        if (folder / 'native-identity.json').exists():
            raise ValueError('Changed author/take requires a new production revision; existing native output is stale')
    write(dest, plan)
    def stamp(t):
        n=round(t*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
    (folder/'EPISODE_SUBTITLES.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n"+'\n'.join(c['display_lines']) for i,c in enumerate(plan['cues']))+'\n',encoding='utf-8')
    return {'actual_duration': plan['duration'], 'scenes': len(plan['scenes']), 'complete_takes': len(plan['segments']), 'frames': plan['frames']}


def check(folder):
    a, b = checked_author(folder)
    return {'revision': a['revision'], 'frozen_questions': len(b), 'scenes': len(a['scenes']),
            'copy_status': a['copy_review'], 'media_role': a['media_role'], 'public_render_ready': False}


def dispatch(operation, folder, **kwargs):
    if operation == 'check': return check(folder)
    if operation == 'voice': return voice(folder)
    if operation == 'align':
        a, _ = checked_author(folder)
        subprocess.run([a['producer']['python'], '-X', 'utf8', str(ROOT/'voicepacks/tools/align_delivery.py'),
                        str(delivery_path(folder,a)), '--model', a['producer']['alignment_model'],
                        '--output', str(folder/'VOICE_ALIGNMENT.json')], check=True)
        return {'alignment': str(folder/'VOICE_ALIGNMENT.json')}
    if operation == 'prepare': return prepare(folder)
    if operation == 'status':
        r=check(folder);r['existing']=[p.name for p in folder.iterdir() if p.name in ('AV_PLAN.json','native-identity.json','PICTURE_RECEIPT.json','PR_TIMELINE.json','DELIVERY_QA.json')];return r
    from ae_production.authored_native import execute
    return execute(operation, folder, **kwargs)
