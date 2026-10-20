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
from creative_os.teaching_focus import require_focus, validate_focus, direct_scene, resource_report
from ae_production.article_chunking import chunk_stage, current_chunks, bind_worlds

CURRENT = ROOT / 'local-data/free-showcase/PRODUCTION_INDEX.json'
AUTHOR = 'AV_AUTHOR.json'
AUTHOR_KEYS = {'revision','product','format','media_role','public_render_ready','copy_review',
               'sources','input_files','voices','scenes','excerpts','producer','host',
               'voice_delivery','voice_inputs','music','teaching_focus','editorial','layout','alignment_source',
               'copy_review_evidence','audience_hook','source_attribution','visual_states','replay_policy','audience_challenges'}
KINDS = {'task', 'locate', 'compare', 'answer', 'replay', 'recap'}
SHOT_KEYS = {'id', 'kind', 'world', 'voice_ids', 'title', 'excerpt', 'candidate',
             'event', 'replay_of', 'source_refs', 'action_refs', 'terminal_refs',
             'recognition_seconds', 'travel_seconds', 'post_seconds', 'voice_pre',
             'candidate_anchor', 'event_anchor', 'attention', 'locator',
             'audience_intent', 'pre_excerpt', 'secondary_excerpt', 'secondary_anchor', 'recap_worlds',
             'candidate_entry_seconds', 'choreography', 'reading_path', 'voice_placements', 'screen_title',
             'candidate_reading_policy', 'comparison_background_policy', 'extraction_policy'}

MOTION_KEYS = {'orient_seconds', 'candidate_read_seconds', 'candidate_travel_seconds',
               'source_read_seconds', 'extract_seconds', 'comparison_seconds',
               'decision_seconds', 'result_seconds', 'return_seconds'}


def validate_copy_review(author):
    """Verify the external exact-copy receipt and its actual per-scene source.

    This reads bound evidence only; it never creates a review or upgrades film,
    listening, student or publication authority. Legacy pending labels retain
    their previous meaning, including historical inputs without a review label.
    """
    status=author.get('copy_review','PENDING')
    if not isinstance(status,str):raise ValueError('Explicit copy review status required')
    if status!='USER_REVIEWED_EXACT_COPY':
        if 'PENDING' not in status.upper():raise ValueError('Unrecognized or unsupported copy review claim')
        return {'copy_review':status,'user_reviewed':False,'scope':'exact_spoken_copy_only'}
    evidence=author.get('copy_review_evidence')
    if not isinstance(evidence,dict) or set(evidence)!={'path','sha256'}:
        raise ValueError('User-reviewed copy requires a bound external copy-review receipt')

    def bound(path,digest):
        if not isinstance(path,str) or not Path(path).is_absolute():
            raise ValueError('Copy-review evidence requires exact absolute paths')
        resolved=Path(path).resolve()
        matches=[d for p,d in author.get('input_files',{}).items() if Path(p).resolve()==resolved]
        if len(matches)!=1 or matches[0]!=digest or sha256(resolved)!=digest:
            raise ValueError('Copy-review source or receipt binding changed')
        return resolved

    receipt=read(bound(evidence['path'],evidence['sha256']))
    required={'schema':'explicit-user-copy-review/v1',
        'authority':'explicit_current_chat_user_copy_review','reviewer_kind':'external_human',
        'scope':'exact_spoken_copy_only','user_reviewed':True,'film_accepted':False,
        'listening_accepted':False,'public_render_ready':False}
    if any(receipt.get(k)!=v or (type(v) is bool and type(receipt.get(k)) is not bool)
           for k,v in required.items()):
        raise ValueError('External user copy review must retain its exact-copy-only scope')
    source=bound(receipt['source_markdown'],receipt['source_markdown_sha256'])
    normalize=lambda text:re.sub(r'\s+','',text.strip())
    hook=author.get('audience_hook')
    heading_ids=r'(?:SC|HOOK)[0-9]+[A-Za-z0-9_-]*'
    if hook:heading_ids+='|'+re.escape(hook['scene_id'])
    source_rows=[];current=None;body=[]
    for line in source.read_text('utf-8-sig').splitlines():
        if re.match(r'^#{1,6}[ \t]+',line):
            if current is not None:
                source_rows.append({'scene':current,'text':normalize('\n'.join(body))})
            current=None;body=[]
            match=re.match(r'^#{2,3}[ \t]+('+heading_ids+r')(?=[ \t·:：—|｜]|$)',line)
            if match:current=match.group(1)
        elif current is not None:
            body.append(line)
    if current is not None:source_rows.append({'scene':current,'text':normalize('\n'.join(body))})
    voices={v['id']:v['text'] for v in author['voices']}
    if len(voices)!=len(author['voices']):raise ValueError('Duplicate exact-copy voice identity')
    rows=[];used=[]
    reviewed_scenes=([{'id':hook['scene_id'],'voice_ids':hook['voice_ids']}] if hook else [])+author['scenes']
    for scene in reviewed_scenes:
        ids=scene['voice_ids']
        if any(vid not in voices or not isinstance(voices[vid],str) for vid in ids):
            raise ValueError('Reviewed scene must retain its complete authored voices')
        used.extend(ids)
        rows.append({'scene':scene['id'],'text':normalize(''.join(voices[vid] for vid in ids))})
    if (not source_rows or len({r['scene'] for r in source_rows})!=len(source_rows)
            or any(not r['text'] for r in source_rows) or source_rows!=rows
            or len(used)!=len(set(used)) or set(used)!=set(voices)):
        raise ValueError('User-reviewed scene order or exact spoken copy differs from its external source')
    digest=sha(rows)
    if receipt.get('reviewed_copy_sha256')!=digest:
        raise ValueError('User-reviewed complete copy digest differs from the actual source')
    return {'copy_review':status,'user_reviewed':True,'scope':'exact_spoken_copy_only',
            'reviewed_copy_sha256':digest,'film_accepted':False,'listening_accepted':False,
            'public_render_ready':False}


USER_REPLAY_OMISSION_QUOTE = '目前的节奏可以把慢放删掉'


def validate_replay_policy(author,folder=None):
    """Bind the explicit omission request; retain the historical one-replay rule.

    The source is the host's external capture of this user instruction. A policy
    label or an author-generated artifact cannot approve its own omission, and
    this narrow permission grants no copy, sensory or publication approval.
    """
    count=sum(scene['kind']=='replay' for scene in author['scenes'])
    if 'replay_policy' not in author:
        if count!=1:
            raise ValueError('Main film must contain the one authored focused replay unless explicitly omitted by the user')
        return {'expected_replays':1,'mode':'legacy_one_focused_replay'}
    policy=author['replay_policy']
    if (not isinstance(policy,dict) or set(policy)!={'mode','source','quote'}
            or policy['mode']!='omitted_by_user' or policy['quote']!=USER_REPLAY_OMISSION_QUOTE):
        raise ValueError('Explicit bound user replay omission policy required')
    evidence=policy['source']
    if not isinstance(evidence,dict) or set(evidence)!={'path','sha256'}:
        raise ValueError('Replay omission requires the exact external request source binding')
    path=evidence['path']
    if not isinstance(path,str) or not Path(path).is_absolute():
        raise ValueError('Replay omission request requires an absolute external source path')
    source=Path(path).resolve()
    if (source.suffix.lower() not in ('.md','.txt')
            or source.name.upper() in ('AV_AUTHOR.JSON','AV_PLAN.JSON','EPISODE_SCRIPT.MD')
            or folder is not None and source.is_relative_to(Path(folder).resolve())):
        raise ValueError('Replay omission cannot be authorized by its own production artifacts')
    matches=[digest for name,digest in author.get('input_files',{}).items() if Path(name).resolve()==source]
    if (len(matches)!=1 or matches[0]!=evidence['sha256'] or not source.is_file()
            or sha256(source)!=evidence['sha256']):
        raise ValueError('Replay omission request source binding changed or is missing')
    if USER_REPLAY_OMISSION_QUOTE not in source.read_text('utf-8-sig'):
        raise ValueError('Replay omission source does not contain the exact current user instruction')
    if count!=0:
        raise ValueError('The explicit user replay omission must produce zero replay scenes')
    return {'expected_replays':0,'mode':'omitted_by_user','source_sha256':evidence['sha256'],
            'scope':'replay_omission_only','human_approved':False,'public_render_ready':False}


def script_text(author):
    """One exact copy view for the user and the existing voice producer."""
    voices = {v['id']: v['text'] for v in author['voices']}
    review='用户已独立审阅（仅此逐字稿）' if author['copy_review']=='USER_REVIEWED_EXACT_COPY' else author['copy_review']
    if author['copy_review']=='PENDING_MERGED_COPY_REVIEW_BODY_ALREADY_USER_REVIEWED_HOOK_USER_SPECIFIED':
        review='正文已独立审阅；开场采用用户指定原文；合并稿待独立审阅'
    if author['copy_review']=='PENDING_USER_REVIEW_AFTER_REQUESTED_REPLAY_REMOVAL':
        review='保留口播沿用已审文字；删除慢看后的重组稿待独立审阅'
    lines = ['# 英语有画说 · ' + author['revision'] + ' 完整文案',
             '文案状态：' + review,
             '段落标签不读入旁白。文案审阅与画面、听感、整片认可分别记录。', '']
    if 'audience_hook' in author:
        lines += ['## ' + author['audience_hook']['scene_id'] + ' · 开场：相同的词，为什么不能选？', '']
        for vid in author['audience_hook']['voice_ids']:
            lines += [voices[vid], '']
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


def production_folder_allowed(folder):
    """Keep private production in this repo, including its indexed worktree.

    A local integration can retain its original absolute media bindings. Only
    the exact current index destination in a Git-registered worktree may cross
    ROOT; an arbitrary supplied path never gains that exception.
    """
    p=Path(folder).resolve()
    if p.is_relative_to((ROOT/'local-data').resolve()):return True
    if not CURRENT.exists() or p!=Path(read(CURRENT)['revision']).resolve():return False
    try:
        raw=subprocess.check_output(['git','-C',str(ROOT),'worktree','list','--porcelain','-z'])
    except (FileNotFoundError,subprocess.CalledProcessError):return False
    roots=[Path(row[len(b'worktree '):].decode('utf-8')).resolve()
           for row in raw.split(b'\0') if row.startswith(b'worktree ')]
    return any(p.is_relative_to((r/'local-data').resolve()) for r in roots)


def current_folder():
    if not CURRENT.exists():
        raise FileNotFoundError('Current private production index unavailable; supply an actual revision')
    p = Path(read(CURRENT)['revision']).resolve()
    if not production_folder_allowed(p) or not (p / AUTHOR).exists():
        raise ValueError('Current revision must contain the actual private author input')
    return p


def validate_source_attribution(author, bundles):
    """Bind screen credits to the supplied paper itself, not a diagnostic ID."""
    import zipfile
    import xml.etree.ElementTree as ET
    rows=author['source_attribution']
    if set(rows)!=set(bundles):raise ValueError('Every question needs its own paper attribution')
    for world,row in rows.items():
        path=Path(row['source_path'])
        if (row['source_sha256']!=sha256(path)
                or author['input_files'].get(str(path))!=row['source_sha256']):
            raise ValueError('Paper attribution source changed: '+world)
        if path.suffix.lower()!='.docx':raise ValueError('Unsupported attribution source format')
        with zipfile.ZipFile(path) as archive:
            root=ET.fromstring(archive.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        lines=[''.join(t.text or '' for t in p.findall('.//w:t',ns))
               for p in root.findall('.//w:p',ns)]
        headings=[line.strip() for line in lines if line.strip()]
        if (not row['paper_heading_quotes'] or row['paper_heading_quotes'][0]!=headings[0]
                or any(quote not in headings[:8] for quote in row['paper_heading_quotes'])):
            raise ValueError('Paper name must come from the original paper heading')
        original=' '.join(' '.join(lines).split())
        q=bundles[world]['source_snapshot']
        for quote in row['paper_heading_quotes']+[row['article_anchor'],q['stem']]+list(q['options'].values()):
            if ' '.join(quote.split()) not in original:
                raise ValueError('Attribution does not match the actual paper/question: '+world)
        if row['article_anchor'] not in q['passage']:
            raise ValueError('Article attribution differs from the frozen passage')
        if row['article_anchor'] not in lines:
            raise ValueError('Article credit must use a real heading or section line')
        article_index=lines.index(row['article_anchor'])
        sections=[line for line in lines[:article_index] if line in ('A','B','C','D')]
        if not sections or sections[-1]!=row['reading_section']:
            raise ValueError('Article credit points to another reading section')
        scene=next(s for s in author['scenes'] if s['world']==world)
        if row['scene_id']!=scene['id'] or scene['kind']!='task':
            raise ValueError('Paper attribution must introduce its actual question')
        # The frozen identity retains the original number even when Word uses
        # automatic list numbering, which is absent from paragraph text.
        number_matches=q['question_id'].endswith('-Q'+str(row['question_number']))
        if (row['question_id']!=q['question_id'] or not number_matches
                or row['reading_section'] not in lines):
            raise ValueError('Attribution question identity changed')
        article_names={row['article_anchor'],
            '无总标题的文章（'+row['article_anchor']+' 小节）',
            '无总标题的产品介绍文章（'+row['article_anchor']+' 小节）'}
        if (row['paper_display']!=' · '.join(row['paper_heading_quotes'])
                or row['article_display'] not in article_names):
            raise ValueError('Screen paper name must retain the verified heading')
    return {'status':'SOURCE_BOUND','worlds':list(rows),'official_source_certified':False}


def checked_author(folder):
    a = read(folder / AUTHOR)
    if set(a)-AUTHOR_KEYS:raise ValueError('Unsupported production input: '+str(sorted(set(a)-AUTHOR_KEYS)))
    validate_copy_review(a)
    if a['product'] != 'FREE_SHOWCASE' or a['public_render_ready'] is not False:
        raise ValueError('This consumer is an internal FREE_SHOWCASE rough-cut adapter')
    if a['media_role'] != 'EDITORIAL_PROXY' or a['format'] != {'width': 1920, 'height': 1080, 'fps': 24}:
        raise ValueError('Unsupported production profile; do not silently substitute a proxy')
    if 'layout' in a:
        if set(a['layout'])!={'passage_width','reading_distance','stage_distance'} or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in a['layout'].values()):
            raise ValueError('Explicit finite column and camera layout required')
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
    if 'source_attribution' in a:
        validate_source_attribution(a, bundles)
    if 'visual_states' in a:
        thinking={'environment':'#17181A','reality':'dimmed_and_blurred',
                  'extracted_words':'sharp_foreground'}
        historical={'paper':'#F2F0EA','ink':'#20211F','reality':'full_brightness'}
        preserved={'mode':'preserve_existing','paper_rgb':[.955,.946,.92],
                   'ink_rgb':[.09,.13,.16],'environment_rgb':[.91,.905,.88],
                   'reality':'unchanged'}
        if a['visual_states'] not in ({'reading':historical,'thinking':thinking},
                                      {'reading':preserved,'thinking':thinking}):
            raise ValueError('Reading/Thinking State differs from the explicit user definition')
    voices = {v['id']: v for v in a['voices']}
    if any('choreography' in s for s in a['scenes']) and not all('choreography' in s for s in a['scenes']):
        raise ValueError('Current film cannot silently mix explicit and historical motion timing')
    if len(voices) != len(a['voices']):
        raise ValueError('Duplicate voice identity')
    used, decided, finals, ids, replay_count = list(a.get('audience_hook',{}).get('voice_ids',[])), {}, set(), set(), 0
    for s in a['scenes']:
        if set(s) - SHOT_KEYS:
            raise ValueError('Unsupported author decision: ' + str(sorted(set(s) - SHOT_KEYS)))
        if s['kind'] not in KINDS or s['id'] in ids or s['world'] not in bundles:
            raise ValueError('Unsupported or repeated scene identity')
        ids.add(s['id']); used.extend(s['voice_ids'])
        if not s['audience_intent'].strip():
            raise ValueError('The author must specify the concrete viewing purpose')
        if s.get('candidate_reading_policy','visible') not in ('visible','quiet_source_until_read'):
            raise ValueError('Unsupported source/candidate reading policy')
        extraction=s.get('extraction_policy')
        if extraction is not None and (extraction!='highlight_then_extract'
                or s['kind']!='compare' or not s.get('reading_path')
                or not s.get('choreography') or not any(x['target']=='source' for x in s.get('attention',[]))):
            raise ValueError('Direct extraction requires a comparison, source reading and exact source highlights')
        background=s.get('comparison_background_policy','visible')
        if background not in ('visible','isolate_selected_passage'):
            raise ValueError('Unsupported comparison background policy')
        if background=='isolate_selected_passage' and (s['kind'] not in ('compare','replay')
                or not s.get('choreography') or not s.get('reading_path')):
            raise ValueError('Background isolation requires an explicit comparison reading path')
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
    if finals != set(bundles):
        raise ValueError('Main film must close each question with its complete frozen candidate checks')
    validate_replay_policy(a,folder)
    if 'teaching_focus' in a:
        validate_focus(a, bundles)
    if 'editorial' in a:
        from ae_production.authored_editorial import validate_editorial
        validate_editorial(a,bundles)
    if 'audience_hook' in a:
        from creative_os.audience_engagement import validate_authored_hook
        validate_authored_hook(a,bundles)
    if 'audience_challenges' in a:
        from creative_os.audience_engagement import validate_authored_challenges
        validate_authored_challenges(a,bundles,folder)
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


def reuse_alignment(folder,author):
    """Reuse measured cues only for byte-identical complete takes and copy."""
    source=Path(author['alignment_source']);old=read(source)
    delivery_file=delivery_path(folder,author);delivery=validate_voice(delivery_file)
    expected={v['id']:v['text'] for v in author['voices']}
    prior={x['id']:x for x in old['clips']}
    missing=set(expected)-set(prior)
    if (old['model']!=author['producer']['alignment_model']
            or missing and missing!=set(author.get('audience_hook',{}).get('voice_ids',[]))):
        raise ValueError('Alignment source uses other voices or model')
    changed=set()
    for c in delivery['clips']:
        if c['id'] in missing:continue
        row=prior[c['id']]
        if (row['audio_sha256']!=c['audio_sha256'] or row['transcript']!=expected[c['id']]
                or row['transcript_sha256']!=c['transcript_sha256']
                or abs(row['duration_seconds']-c['duration_seconds'])>1/48000):
            changed.add(c['id'])
    missing |= changed
    reused=set(expected)-missing
    result=deepcopy(old);result['delivery_sha256']=sha256(delivery_file)
    # A requested scene deletion reuses the surviving complete takes; removed
    # takes and their cues must not leak into the new measured clock.
    result['clips']=[deepcopy(prior[c['id']]) for c in delivery['clips'] if c['id'] in reused]
    measured=None
    if missing:
        directory=folder/'alignment-new-input';request=directory/'delivery.json'
        selected=[c for c in delivery['clips'] if c['id'] in missing]
        if not request.exists():
            directory.mkdir(exist_ok=False);rows=[]
            for c in selected:
                wav=c['id']+'.wav';text=c['id']+'.txt'
                shutil.copyfile(asset(delivery_file.parent,c['audio']),directory/wav)
                shutil.copyfile(asset(delivery_file.parent,c['transcript']),directory/text)
                rows.append(describe_clip(directory,c['id'],wav,text,c['listening_review']))
            write(request,{'schema':'voice-delivery/v1','clips':rows,
                'producer':'new or revised complete authored takes only'})
        subset=validate_voice(request)
        if {c['id']:c['audio_sha256'] for c in subset['clips']}!={c['id']:c['audio_sha256'] for c in selected}:
            raise ValueError('New or revised alignment subset changed')
        measured=folder/'NEW_VOICE_ALIGNMENT.json'
        if not measured.exists():
            subprocess.run([author['producer']['python'],'-X','utf8',str(ROOT/'voicepacks/tools/align_delivery.py'),
                str(request),'--model',author['producer']['alignment_model'],'--output',str(measured)],check=True)
        fresh=read(measured)
        if (fresh['delivery_sha256']!=sha256(request) or fresh['model']!=old['model']
                or {x['id'] for x in fresh['clips']}!=missing):
            raise ValueError('Measurement is not the actual complete new delivery')
        combined={**prior,**{x['id']:x for x in fresh['clips']}}
        result['clips']=[combined[c['id']] for c in delivery['clips']]
        result['human_listening_review']='PENDING'
        result['alignment_provenance']={'reused_complete_takes':len(reused),'newly_measured_complete_takes':len(missing),
            'new_measurement':str(measured),'new_measurement_sha256':sha256(measured),
            'reused_source':str(source),'reused_source_sha256':sha256(source),'not_a_listening_review':True}
    dest=folder/'VOICE_ALIGNMENT.json'
    if dest.exists() and read(dest)!=result:raise ValueError('Preserve existing alignment; inspect a new revision')
    write(dest,result);write(folder/'ALIGNMENT_REUSE_RECEIPT.json',{
        'source':str(source),'source_sha256':sha256(source),'delivery_sha256':sha256(delivery_file),
        'complete_identical_takes':len(reused),'copy_identical':not changed,'new_listening_review':False,
        **({'newly_measured_complete_takes':len(missing),'new_measurement_sha256':sha256(measured)} if missing else {})})
    return {'alignment':str(dest),'reused_identical_complete_takes':len(reused),
            **({'newly_measured_complete_takes':len(missing)} if missing else {})}


def compile_clock(a, clips, aligned):
    """Actual complete takes determine the clock; author holds alter real events."""
    fps = a['format']['fps']; cursor = 0; scenes = []; segments = []; cues = []; events = []
    voice_by_id = {x['id']: x for x in a['voices']}
    for shot in a['scenes']:
        s = direct_scene(a, shot); s['start'] = cursor
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
                if s.get('extraction_policy')=='highlight_then_extract':
                    s['source_arrive']=s['extract_start']=visual
                    s['extraction_highlight_at']=grid(visual-.25,fps)
                    s['extraction_highlights']=[x['phrase'] for x in s['attention'] if x['target']=='source']
                else:
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
    clock = {'scenes': scenes, 'segments': segments, 'cues': cues, 'candidate_events': events,
             'duration': cursor, 'frames': round(cursor * fps)}
    return opening_clock(a, clips, aligned, clock) if 'audience_hook' in a else clock


SCENE_CLOCK_FIELDS = ('start','end','oriented','recognition_end','extract_start','settled',
    'candidate_start','candidate_arrive','source_arrive','voice_start','voice_end',
    'comparison_until','return_start','decision_end','event_time','secondary_at','extraction_highlight_at')


def shift_body_clock(clock, offset, fps=24):
    """Translate time, never source character offsets, clip length or reading duration."""
    result=deepcopy(clock)
    for scene in result['scenes']:
        for key in SCENE_CLOCK_FIELDS:
            if key in scene:scene[key]+=offset
        for event in scene.get('reading_events',[]):
            for key in ('depart','arrival','end_time'):event[key]+=offset
        for event in scene.get('attention_events',[]):event['time']+=offset
    for segment in result['segments']:
        segment['voice_start']+=offset;segment['voice_end']+=offset
    for cue in result['cues']:cue['start']+=offset;cue['end']+=offset
    for event in result['candidate_events']:event['time']+=offset
    result['duration']+=offset;result['frames']+=round(offset*fps)
    return result


def opening_clock(author, clips, aligned, body):
    """Consume the approved opening on the same actual take/caption/media clock."""
    h=author['audience_hook'];fps=author['format']['fps'];t=h['timing']
    cursor=grid(t['voice_pre'],fps);segments=[];cues=[]
    voices={v['id']:v for v in author['voices']}
    for vid in h['voice_ids']:
        v,c,align=voices[vid],clips[vid],aligned[vid]
        if align['transcript']!=v['text'] or align['audio_sha256']!=c['audio_sha256']:
            raise ValueError('Opening alignment belongs to another exact take')
        start=cursor;end=start+c['duration_seconds']
        segments.append({**v,'scene_id':h['scene_id'],'voice_start':start,'voice_end':end,
                         'voice':deepcopy(c),'time_stretch':False,'truncated':False})
        for i,cue in enumerate(align['cues']):
            if (v['text'][cue['text_start']:cue['text_end']]!=cue['text']
                    or not 0<=cue['start']<cue['end']<=c['duration_seconds']+.001):
                raise ValueError('Opening subtitle must bind exact complete spoken characters')
            cues.append({**cue,'id':vid+'_hook_'+str(i),'scene_id':h['scene_id'],
                         'segment':vid,'start':start+cue['start'],'end':start+cue['end']})
        cursor=grid(end+t['voice_gap'],fps)
    if not segments:raise ValueError('Opening needs its complete newly bound voices')
    # Only the given visible conflict is staged. No answer/role label is added.
    # One short alignment, a distinct relation displacement, an unresolved hold,
    # then the existing original task. No quota-driven duration padding.
    align_start=grid(max(1.4,segments[-1]['voice_start']+.3),fps)
    align_end=grid(align_start+.8,fps)
    displace_end=grid(align_end+1.05,fps)
    handoff_start=grid(max(segments[-1]['voice_end']+.15,displace_end+t['unresolved_min']),fps)
    end=grid(handoff_start+t['handoff_seconds'],fps)
    clock=shift_body_clock(body,end,fps)
    clock['segments']=segments+clock['segments'];clock['cues']=cues+clock['cues']
    actual={s['id']:s for s in clock['scenes']}
    r=h['retention'];payoff=actual[h['payoff_scene_id']];early=actual[r['first_payoff_scene_id']]
    clock['audience_hook']={'contract_version':h['contract_version'],'decision_sha':sha(h),
        'decision':deepcopy(h),'scene_id':h['scene_id'],'start':0,'end':end,
        'frames':round(end*fps),'body_offset_seconds':end,'body_offset_frames':round(end*fps),
        'phases':{'enter':[0,align_start],'surface_align':[align_start,align_end],
                  'relation_displace':[align_end,displace_end],
                  'unresolved_hold':[displace_end,handoff_start],
                  'match_into_task':[handoff_start,end]},
        'voice_ids':list(h['voice_ids']),'first_payoff_at':early['event_time'],
        'first_payoff_after_hook_seconds':early['event_time']-end,
        'main_payoff_at':payoff['event_time'],
        'progression_at':actual[r['progression_scene_id']]['start'],
        'final_recall_range':[actual[r['final_recall_scene_id']]['start'],actual[r['final_recall_scene_id']]['end']],
        'scope':'USER_SPECIFIED_INTENT_NOT_RETENTION_OR_HUMAN_APPROVAL',
        'normal_speed_review':'UNOBSERVED','listening_review':'UNOBSERVED','public_render_ready':False}
    return clock


def compile_visual_states(author, clock):
    return {'definition':deepcopy(author['visual_states']),
        'thinking_windows':[{'scene_id':s['id'],'enter':s['extract_start'],
            'settled':s['settled'],'release':s['return_start'],'end':s['end']-1/24}
            for s in clock['scenes'] if s.get('motion_treatment')=='critical_comparison'],
        'normal_speed_review':'UNOBSERVED'}


def prepare(folder):
    a, bundles = checked_author(folder)
    from creative_os.audience_engagement import require_hook_decision
    require_hook_decision(a,folder,operation='prepare')
    require_focus(a)
    check_script(folder, a)
    chunks = current_chunks(folder, bundles)
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
    bind_worlds(worlds, chunks)
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
    if 'audience_challenges' in a:
        from creative_os.audience_engagement import compile_authored_challenges
        plan['audience_challenges']=compile_authored_challenges(a,bundles,plan,worlds,folder)
    plan['article_chunking'] = chunks
    if 'source_attribution' in a:plan['source_attribution']=deepcopy(a['source_attribution'])
    if 'visual_states' in a:
        plan['visual_states']=compile_visual_states(a,plan)
    if 'layout' in a:plan['layout']=deepcopy(a['layout'])
    if all('choreography' in s for s in a['scenes']):
        plan['realization']='continuous_paper_scan'
    plan['copy_review']=a['copy_review']
    plan['complete_copy_sha256']=sha(script_text(a))
    plan['music']=deepcopy(a.get('music',[]))
    if 'audience_hook' in plan:
        for music in plan['music']:
            music['timeline_start']=music.get('timeline_start',0)+plan['audience_hook']['end']
    from content_os.scoring import rank_teaching_focus
    from creative_os.audience_engagement import critical_focus_handoff
    plan['teaching_focus']=deepcopy(a['teaching_focus'])
    plan['teaching_focus_sha']=sha(a['teaching_focus'])
    plan['teaching_resources']=resource_report(a,plan)
    plan['critical_engagement']=critical_focus_handoff(a,plan)
    if 'editorial' in a:
        from ae_production.authored_editorial import compile_editorial
        plan['editorial_consumption']=compile_editorial(a,plan,bundles)
    write(folder/'TEACHING_FOCUS_REPORT.json', {
        'selection':rank_teaching_focus(a,bundles), 'resources':plan['teaching_resources'],
        'audience_handoff':plan['critical_engagement'], 'policy_sha':plan['teaching_focus_sha']})
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
    from content_os.scoring import rank_teaching_focus
    chunks = current_chunks(folder,b) if (folder/'READING_CHUNKS.json').exists() else None
    from creative_os.audience_engagement import validate_authored_hook
    return {'revision': a['revision'], 'frozen_questions': len(b), 'scenes': len(a['scenes']),
            'audience_hook':validate_authored_hook(a,b),
            'article_chunking': {'articles':len(chunks['articles']), 'input_sha256':chunks['input_sha256']} if chunks else 'REQUIRED_BEFORE_NEW_PREPARE_OR_BUILD',
            'teaching_focus':validate_focus(a,b) if 'teaching_focus' in a else 'HISTORICAL_INPUT_NO_NEW_BUILD',
            'selection':rank_teaching_focus(a,b) if 'teaching_focus' in a else 'HISTORICAL',
            'copy_status': a['copy_review'], 'media_role': a['media_role'], 'public_render_ready': False}


def dispatch(operation, folder, **kwargs):
    if operation in ('script','voice','align','prepare','build'):
        a,_=checked_author(folder);require_focus(a)
        from creative_os.audience_engagement import require_hook_decision
        require_hook_decision(a,folder,operation=operation)
    if operation == 'script': return script(folder)
    if operation == 'check': return check(folder)
    if operation == 'chunks':
        _, bundles = checked_author(folder)
        return chunk_stage(folder, bundles)
    if operation == 'voice': return voice(folder)
    if operation == 'align':
        a, _ = checked_author(folder)
        if a.get('alignment_source'):return reuse_alignment(folder,a)
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
