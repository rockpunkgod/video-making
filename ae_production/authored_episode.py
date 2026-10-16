"""Consume the current author's decisions through the existing episode entry.

This is the portable part of the former private AV-plan author. Facts remain
in supplied frozen bundles; the author supplies copy, source ranges and shots.
There is no question solver, automatic creative approval or new runtime.
"""
from copy import deepcopy
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import wave

from video_contracts import ROOT, read, write, sha, pointer, verify_bundle, status_matches
from scripts.voice_delivery import validate as validate_voice, asset, sha256, pad_to_video_frame, describe_clip

CURRENT = ROOT / 'local-data/free-showcase/PRODUCTION_INDEX.json'
AUTHOR = 'AV_AUTHOR.json'
AUTHOR_KEYS = {'revision','product','format','media_role','public_render_ready','copy_review',
               'sources','input_files','voices','scenes','excerpts','producer','host',
               'voice_delivery','voice_inputs','music'}
KINDS = {'task', 'locate', 'compare', 'answer', 'replay', 'recap'}
SHOT_KEYS = {'id', 'kind', 'world', 'voice_ids', 'title', 'excerpt', 'candidate',
             'event', 'replay_of', 'source_refs', 'action_refs', 'terminal_refs',
             'recognition_seconds', 'travel_seconds', 'post_seconds', 'voice_pre',
             'candidate_anchor', 'event_anchor', 'attention', 'locator',
             'audience_intent', 'pre_excerpt', 'secondary_excerpt', 'secondary_anchor', 'recap_worlds',
             'candidate_entry_seconds', 'choreography', 'reading_path', 'voice_placements', 'screen_title'}

MOTION_KEYS = {'orient_seconds', 'candidate_read_seconds', 'candidate_travel_seconds',
               'source_read_seconds', 'extract_seconds', 'comparison_seconds',
               'decision_seconds', 'result_seconds', 'return_seconds'}


def script_text(author):
    """One exact copy view for the user and the existing voice producer."""
    voices = {v['id']: v['text'] for v in author['voices']}
    lines = ['# 英语有画说 · ' + author['revision'] + ' 完整文案',
             '文案状态：' + author['copy_review'],
             '段落标签不读入旁白。文案审阅与画面、听感、整片认可分别记录。', '']
    for scene in author['scenes']:
        lines += ['## ' + scene['id'] + ' · ' + scene['title'], '']
        for vid in scene['voice_ids']:
            lines += [voices[vid], '']
    return '\n'.join(lines)


def script(folder):
    author, _ = checked_author(folder)
    output = folder / 'EPISODE_SCRIPT.md'
    output.write_text(script_text(author), encoding='utf-8')
    return {'revision': author['revision'], 'script': str(output),
            'complete_copy': script_text(author), 'copy_review': author['copy_review'],
            'handoff': 'Paste the complete copy in chat on every copy revision; exporting is not user approval.'}


def check_script(folder, author):
    output = folder / 'EPISODE_SCRIPT.md'
    if not output.exists() or output.read_text('utf-8') != script_text(author):
        raise ValueError('Full copy review export is missing or stale; run script and send the complete new copy to the user')


def current_folder():
    if not CURRENT.exists():
        raise FileNotFoundError('Current private production index unavailable; supply an actual revision')
    p = Path(read(CURRENT)['revision']).resolve()
    if not p.is_relative_to((ROOT / 'local-data').resolve()) or not (p / AUTHOR).exists():
        raise ValueError('Current revision must contain the actual private author input')
    return p


def checked_author(folder):
    a = read(folder / AUTHOR)
    if set(a)-AUTHOR_KEYS:raise ValueError('Unsupported production input: '+str(sorted(set(a)-AUTHOR_KEYS)))
    if a['product'] != 'FREE_SHOWCASE' or a['public_render_ready'] is not False:
        raise ValueError('This consumer is an internal FREE_SHOWCASE rough-cut adapter')
    if a['media_role'] != 'EDITORIAL_PROXY' or a['format'] != {'width': 1920, 'height': 1080, 'fps': 24}:
        raise ValueError('Unsupported production profile; do not silently substitute a proxy')
    for p, digest in a['input_files'].items():
        if sha256(p) != digest:
            raise ValueError('Bound input changed: ' + p)
    for music in a.get('music',[]):
        if sha256(music['clip_path'])!=music['clip_sha'] or music.get('public_use_allowed') is not False:
            raise ValueError('Scratch music must retain its actual source and review scope')
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
    if any('choreography' in s for s in a['scenes']) and not all('choreography' in s for s in a['scenes']):
        raise ValueError('Current film cannot silently mix explicit and historical motion timing')
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
        timing_names=('voice_pre',) if 'choreography' in s else ('recognition_seconds','travel_seconds','post_seconds','voice_pre')
        for name in timing_names:
            if type(s[name]) not in (int, float) or not math.isfinite(s[name]) or s[name] < 0:
                raise ValueError('Invalid authored timing: ' + name)
        if 'choreography' in s:
            motion=s['choreography']
            if set(motion)!=MOTION_KEYS or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in motion.values()):
                raise ValueError('Unsupported or incomplete choreography')
            if any(k in s for k in ('recognition_seconds','travel_seconds','post_seconds','candidate_entry_seconds','candidate_anchor','pre_excerpt','secondary_excerpt')):
                raise ValueError('Replace historical timing overrides with the current reading path and voice placements')
            if s['kind']=='locate' and not s.get('reading_path'):
                raise ValueError('A locator needs an actual source reading path')
            for step in s.get('reading_path',[]):
                if set(step)!={'start','end','quote','move_seconds','read_seconds','mode','phrase'}:
                    raise ValueError('Unsupported reading path decision')
                q=bundles[s['world']]['source_snapshot']['passage']
                if (type(step['start']) is not int or type(step['end']) is not int or not 0<=step['start']<step['end']<=len(q)
                        or q[step['start']:step['end']]!=step['quote'] or step['phrase'] not in step['quote']):
                    raise ValueError('Reading path must use an exact source span')
                if step['mode'] not in ('scan','hit','scope') or any(type(step[k]) not in (int,float) or not math.isfinite(step[k]) or step[k]<=0 for k in ('move_seconds','read_seconds')):
                    raise ValueError('Invalid reading event')
            placements=s.get('voice_placements',{})
            if set(placements)-set(s['voice_ids']):raise ValueError('Voice placement has no complete take')
            for phase in placements.values():
                if phase not in ('candidate','comparison','start') and not (phase.startswith('reading:') and phase[8:].isdigit() and int(phase[8:])<len(s.get('reading_path',[]))):
                    raise ValueError('Unsupported spoken scene phase')
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
    check_script(folder, a)
    selected=delivery_path(folder,a)
    if selected.exists():
        delivery=validate_voice(selected)
        if a.get('voice_inputs') and delivery.get('selection_sha256')!=sha([(str(Path(p).resolve()),sha256(p)) for p in a['voice_inputs']]):
            raise ValueError('Selected producer takes changed; choose a new voice delivery revision')
        actual={x['id']:asset(selected.parent,x['transcript']).read_text('utf-8-sig').strip() for x in delivery['clips']}
        if actual!={v['id']:v['text'] for v in a['voices']}:raise ValueError('Selected voice copy is stale')
        return {'reused_complete_delivery':len(actual),'delivery':str(selected)}
    if a.get('voice_inputs'):
        return select_takes(folder,a)
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


def select_takes(folder, author):
    """Explicit producer deliveries, exact-text reuse, later listed takes win.

    Missing copy alone goes back to the existing producer. Nothing is selected
    by an invented listening score and old/failed deliveries are not overwritten.
    """
    wanted={v['id']:v['text'] for v in author['voices']};chosen={}
    def add(path):
        path=Path(path).resolve();delivery=validate_voice(path)
        for c in delivery['clips']:
            if c['id'] in wanted and asset(path.parent,c['transcript']).read_text('utf-8-sig').strip()==wanted[c['id']]:
                if c['listening_review']=='REJECTED':continue
                chosen[c['id']]=(path,c)
    for path in author['voice_inputs']:add(path)
    missing=[v for v in author['voices'] if v['id'] not in chosen]
    if missing:
        name=sha(missing)[:16];request=folder/('VOICE_INPUT-'+name+'.json');dest=folder/('voice-generated-'+name)
        if not request.exists():write(request,missing)
        if not (dest/'delivery.json').exists():
            p=author['producer']
            subprocess.run([p['python'],'-X','utf8',str(ROOT/'voicepacks/tools/generate_gpt_sovits.py'),
                '--pack',p['pack'],'--runtime',p['runtime'],'--clips-file',str(request),'--output',str(dest),'--offline'],check=True)
        add(dest/'delivery.json')
    if set(chosen)!=set(wanted):raise ValueError('Producer did not deliver every exact requested take')
    output=delivery_path(folder,author);output.parent.mkdir(exist_ok=False);rows=[];origins=[]
    for vid in wanted:
        src,c=chosen[vid];wav=vid+'.wav';txt=vid+'.txt'
        shutil.copyfile(asset(src.parent,c['audio']),output.parent/wav)
        shutil.copyfile(asset(src.parent,c['transcript']),output.parent/txt)
        rows.append(describe_clip(output.parent,vid,wav,txt,c['listening_review']))
        origins.append({'id':vid,'delivery':str(src),'delivery_sha256':sha256(src),'audio_sha256':c['audio_sha256']})
    write(output,{'schema':'voice-delivery/v1','clips':rows,'producer':'existing producer, explicit complete-take selection','sources':origins,
                  'selection_sha256':sha([(str(Path(p).resolve()),sha256(p)) for p in author['voice_inputs']])})
    validate_voice(output)
    return {'delivery':str(output),'complete_takes':len(rows),'new_copy_takes':len(missing),'reused_exact_takes':len(rows)-len(missing)}


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
        motion=s.get('choreography')
        if motion:
            orient=grid(cursor+motion['orient_seconds'],fps)
            s['oriented']=orient
            visual=orient
            if s.get('candidate') and s['kind'] in ('compare','replay'):
                s['candidate_start']=grid(orient+motion['candidate_read_seconds'],fps)
                s['candidate_arrive']=grid(s['candidate_start']+motion['candidate_travel_seconds'],fps)
                visual=s['candidate_arrive']
            s['reading_events']=[]
            for step in s.get('reading_path',[]):
                arrival=grid(visual+step['move_seconds'],fps);end=grid(arrival+step['read_seconds'],fps)
                s['reading_events'].append({**step,'depart':visual,'arrival':arrival,'end_time':end})
                visual=end
            if s['kind'] in ('compare','replay'):
                s['source_arrive']=grid(visual+motion['orient_seconds'],fps)
                s['extract_start']=grid(s['source_arrive']+motion['source_read_seconds'],fps)
                s['settled']=grid(s['extract_start']+motion['extract_seconds'],fps)
                s['travel_seconds']=motion['extract_seconds']
            else:s['extract_start']=s['settled']=visual
            s['recognition_end']=s['extract_start']
        else:
            lead=s.get('candidate_entry_seconds',0)
            s['recognition_end']=grid(cursor+lead+s['recognition_seconds'],fps)
            s['extract_start']=s['recognition_end']
            s['settled']=grid(s['extract_start']+s['travel_seconds'],fps)
        clock = grid(cursor + s['voice_pre'], fps); positions = []
        for vid in s['voice_ids']:
            v, c, align = voice_by_id[vid], clips[vid], aligned[vid]
            if align['transcript'] != v['text'] or align['audio_sha256'] != c['audio_sha256']:
                raise ValueError('Audio alignment belongs to another take or transcript')
            if motion:
                phase=s.get('voice_placements',{}).get(vid,'comparison')
                cue=(cursor+s['voice_pre'] if phase=='start' else s['oriented'] if phase=='candidate' else
                     s['reading_events'][int(phase[8:])]['arrival'] if phase.startswith('reading:') else s['settled'])
                clock=max(clock,grid(cue,fps))
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
        s['end'] = grid(max(s['voice_end'], s['settled']) + s.get('post_seconds',0), fps)
        if motion:
            s['comparison_until']=grid(s['settled']+motion['comparison_seconds'],fps)
            s['return_start']=grid(max(s['voice_end']+motion['result_seconds'],s['comparison_until']),fps)
            s['end']=grid(s['return_start']+motion['return_seconds'],fps)
        def anchor(phrase, fallback):
            if not phrase: return fallback
            for vid, start, _ in positions:
                at = voice_by_id[vid]['text'].find(phrase)
                if at >= 0:
                    matches = [c for c in aligned[vid]['cues'] if c['text_start'] <= at < c['text_end']]
                    if len(matches) != 1: raise ValueError('Ambiguous spoken anchor')
                    return grid(start + matches[0]['start'], fps)
            raise ValueError('Authored spoken anchor is absent: ' + phrase)
        if not motion:s['candidate_start'] = grid(cursor+lead-1.6,fps) if lead else max(s['settled'] + .12, anchor(s.get('candidate_anchor'), s['settled'] + .12))
        elif 'candidate_start' not in s:s['candidate_start']=s['oriented']
        s['attention_events'] = [{**x, 'time': anchor(x['anchor'], s['settled'])} for x in s.get('attention', [])]
        if s.get('secondary_excerpt'):
            s['secondary_at'] = anchor(s['secondary_anchor'], None)
        if s.get('event'):
            t = anchor(s.get('event_anchor'), grid(s['voice_end'] + .08, fps))
            if motion:
                t=max(t,s['comparison_until'])
                s['decision_end']=grid(t+motion['decision_seconds'],fps)
                s['return_start']=grid(max(s['return_start'],s['decision_end']+motion['result_seconds']),fps)
                s['end']=grid(s['return_start']+motion['return_seconds'],fps)
            if t < s['settled'] or t >= s['end'] - .5:
                raise ValueError('Decision requires visible comparison and time for its complete movement')
            if s['event']!='final' and t<s.get('candidate_arrive',s['candidate_start']+.8):
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
    check_script(folder, a)
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
    if all('choreography' in s for s in a['scenes']):
        plan['realization']='continuous_paper_scan'
    plan['copy_review']=a['copy_review']
    plan['complete_copy_sha256']=sha(script_text(a))
    plan['music']=deepcopy(a.get('music',[]))
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
    if operation == 'script': return script(folder)
    if operation == 'check': return check(folder)
    if operation == 'voice': return voice(folder)
    if operation == 'align':
        a, _ = checked_author(folder)
        current=folder/'VOICE_ALIGNMENT.json'
        if current.exists() and read(current)['delivery_sha256']!=sha256(delivery_path(folder,a)):
            if (folder/'native-identity.json').exists():raise ValueError('Changed voice requires a new production revision')
            archive=folder/'alignment-history';archive.mkdir(exist_ok=True)
            dest=archive/(sha256(current)+'.json')
            if dest.exists():raise ValueError('Inspect already archived alignment before repeating')
            current.rename(dest)
        subprocess.run([a['producer']['python'], '-X', 'utf8', str(ROOT/'voicepacks/tools/align_delivery.py'),
                        str(delivery_path(folder,a)), '--model', a['producer']['alignment_model'],
                        '--output', str(folder/'VOICE_ALIGNMENT.json')], check=True)
        return {'alignment': str(folder/'VOICE_ALIGNMENT.json')}
    if operation == 'prepare': return prepare(folder)
    if operation == 'status':
        r=check(folder);r['existing']=[p.name for p in folder.iterdir() if p.name in ('AV_PLAN.json','native-identity.json','PICTURE_RECEIPT.json','PR_TIMELINE.json','DELIVERY_QA.json')];return r
    from ae_production.authored_native import execute
    return execute(operation, folder, **kwargs)
