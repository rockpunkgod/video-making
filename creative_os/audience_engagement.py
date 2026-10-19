"""Audience Engagement Design: editorial viewing intentions over frozen episodes."""
from copy import deepcopy
from video_contracts import sha, validate
from creative_os.episode import validate_episode
from pathlib import Path
import math
import re

from video_contracts import pointer
from scripts.voice_delivery import sha256

VERSION = '0.1.0'
V2 = '0.2.0'
FUNCTION_TASKS = {
    'PROBLEM': '辨认当前真实题目要解决的问题',
    'CURIOSITY': '带着当前题目的疑问继续观看',
    'ORIENTATION': '确定当前题面、目标与观察位置',
    'SEARCH': '跟随高手寻找下一条有据的信息',
    'RECOGNITION': '辨认当前定位对象是否命中',
    'ANTICIPATION': '利用已见信息期待下一次判断',
    'COMPARISON': '比较已经展示的有据对象',
    'DISCOVERY': '观察当前实际动作带来的新信息',
    'PAYOFF': '接收当前实际输出范围内的认知收益',
    'PROGRESSION': '发现下一题不同的观看理由',
    'RECALL': '回忆本期共同的动作特征',
}
VIEWER_FIELDS = {'current_problem', 'information_already_seen', 'current_attention_object',
                 'viewer_expectation', 'viewer_task', 'unresolved_question', 'next_information_gain'}
EDITORIAL_SIGNALS = {'hook_link_clear', 'payoff_leaked', 'reading_space', 'motion_without_gain',
                     'repeated_explanation', 'method_name_dominates', 'voice_over_hold',
                     'information_overload'}

HOOK_VERSION = '1.0.0'
HOOK_PHASES = ['enter', 'surface_align', 'relation_displace', 'unresolved_hold', 'match_into_task']


def authored_body_binding(author):
    """Bind an opening to the actual episode, not a similarly named old cut."""
    hook_ids = set(author.get('audience_hook', {}).get('voice_ids', []))
    return {'scene_order': [s['id'] for s in author['scenes']],
            'scenes_sha': sha(author['scenes']),
            'copy_sha': sha([v for v in author['voices'] if v['id'] not in hook_ids]),
            'sources_sha': sha({w: {k: sha256(p) for k, p in paths.items()}
                                for w, paths in author['sources'].items()})}


def hook_migration_status(author):
    if 'audience_hook' not in author:
        return {'status': 'HISTORICAL_UNMIGRATED', 'contract_version': None,
                'new_production_allowed': False, 'human_review': 'PENDING',
                'public_render_ready': False}
    return {'status': 'USER_DECISION_PRESENT_REQUIRES_VALIDATION',
            'contract_version': author['audience_hook'].get('contract_version'),
            'human_review': 'PENDING', 'public_render_ready': False}


def timed_scene_rows(plan):
    """A teaser is explicit media scope, never the first question's fact/answer."""
    rows=list(plan['scenes'])
    if 'audience_hook' in plan:
        h=plan['audience_hook'];d=h['decision']
        rows=[{'id':h['scene_id'],'kind':'audience_hook','start':h['start'],'end':h['end'],
               'title':'开场：相同的词，为什么不能选？',
               'source_refs':d['source_refs'],'audience_intent':d['pain_point']['description'],
               'world':None,'voice_ids':h['voice_ids']}]+rows
    return rows


def require_hook_decision(author, folder=None, *, operation=None):
    """Historical inspection/cached films survive; fresh production must migrate."""
    if 'audience_hook' in author:
        return
    # A marker file is not provenance. Historical replay requires the unchanged
    # saved author, measured plan and native project, and never permits a build.
    if folder is not None and operation not in {'voice','align','prepare','build'}:
        from video_contracts import read
        folder=Path(folder)
        try:
            a=read(folder/'AV_AUTHOR.json');p=read(folder/'AV_PLAN.json');n=read(folder/'native-identity.json')
            saved=Path(n['project_path'])
            saved_binding=read(folder/'RESTORED_HOSTS.json')['saved_current_projects']['after_effects']
            if (a==author and p['author_sha256']==sha256(folder/'AV_AUTHOR.json')
                    and n['plan_sha256']==sha256(folder/'AV_PLAN.json') and saved.is_file()
                    and Path(saved_binding['path']).resolve()==saved.resolve()
                    and saved_binding['sha256']==sha256(saved)
                    and p['alignment_sha256']==sha256(folder/'VOICE_ALIGNMENT.json')
                    and p['voice_delivery_sha256']==sha256(folder/a['voice_delivery'])):
                return
        except (FileNotFoundError,KeyError,ValueError,TypeError):
            pass
    raise ValueError('CREATIVE_DECISION_REQUIRED: FREE_SHOWCASE needs the user-specified Audience Hook v1; no automatic creative fallback')


def validate_authored_hook(author, bundles):
    """Validate user decisions inside Audience, without inventing a new Hook.

    Explicit source spans and frozen execution/terminal scopes are checked.
    Their hashes cannot certify teaching semantics, human identity or taste.
    The approval source is a bound external user instruction, never an agent's
    self-authored approval flag. The whole film remains unapproved.
    """
    h = author.get('audience_hook')
    if h is None:
        return hook_migration_status(author)
    from jsonschema import Draft202012Validator, ValidationError
    from video_contracts import ROOT, read
    schema = read(ROOT / 'video/schemas/audience-engagement-plan.json')
    try:
        Draft202012Validator({'$ref': '#/$defs/authored_hook_v1', '$defs': schema['$defs']}).validate(h)
    except ValidationError as exc:
        raise ValueError('CREATIVE_DECISION_REQUIRED: incomplete or unsupported Audience Hook v1: ' + exc.message) from exc
    if h['contract_version'] != HOOK_VERSION or h['presentation'] != 'abstract_opening_teaser':
        raise ValueError('Unsupported Audience Hook presentation/version')
    scenes = {s['id']: s for s in author['scenes']}
    if h['scene_id'] in scenes:
        raise ValueError('Opening teaser must not replace or impersonate an original task')
    if h['body_binding'] != authored_body_binding(author):
        raise ValueError('Stale Hook: episode source, scene order or exact body copy changed')
    if h['payoff_scene_id'] not in scenes:
        raise ValueError('Hook payoff scene does not exist')
    payoff = scenes[h['payoff_scene_id']]
    if h['source_refs'] != payoff['source_refs']:
        raise ValueError('Hook must bind the complete actual payoff source scope')

    def source(ref):
        text = pointer(bundles[ref['world']]['source_snapshot'], ref['pointer'])
        if (type(ref['start']) is not int or type(ref['end']) is not int
                or not 0 <= ref['start'] < ref['end'] <= len(text)
                or text[ref['start']:ref['end']] != ref['quote']):
            raise ValueError('Hook source span is absent or stale')
        return text

    for ref in h['source_refs']:
        source(ref)
    if not h['pain_point']['description'].strip() or not h['pain_point']['source_refs']:
        raise ValueError('Specific source-supported student difficulty required')
    # These are the three slogans explicitly excluded by the user contract.
    # Rejecting them is a narrow rule, not automatic semantic review of prose.
    slogan=re.sub(r'\s+','',h['pain_point']['description']).strip('。！？!?，,；;：:、\"“”\'‘’ ')
    if slogan in {'英语阅读太难了','今天教你快速提分','学会这个方法轻松拿分'}:
        raise ValueError('CREATIVE_DECISION_REQUIRED: generic slogan is not a specific source-supported difficulty')
    if any(r not in h['source_refs'] for r in h['pain_point']['source_refs']):
        raise ValueError('Student pain point has no evidence in its payoff')
    anchors = h['confusion_trigger']['anchor_refs']
    if len(anchors) != 2 or anchors[0] == anchors[1] or anchors[0]['quote'] != anchors[1]['quote']:
        raise ValueError('Surface-overlap opening needs two distinct exact shared-term anchors')
    if ({r['pointer'] for r in anchors}!={'/passage','/options/'+payoff['candidate']}
            or any(r['world']!=payoff['world'] for r in anchors)):
        raise ValueError('Shared-term conflict requires the actual passage and payoff option')
    for ref in anchors:
        source(ref)
        if not any(r['world'] == ref['world'] and r['pointer'] == ref['pointer']
                   and r['start'] <= ref['start'] < ref['end'] <= r['end'] for r in h['source_refs']):
            raise ValueError('Visual anchor is outside the bound payoff evidence')
        if not any(r['world']==ref['world'] and r['pointer']==ref['pointer']
                   and r['start']<=ref['start']<ref['end']<=r['end'] for r in h['pain_point']['source_refs']):
            raise ValueError('Student difficulty must cover both sides of the actual shared-term conflict')
    if h['confusion_trigger']['source_scene_id'] != payoff['id']:
        raise ValueError('Confusion and payoff must concern the same actual task')
    mt = h['method_trigger']; ref = mt['action_ref']
    if ref not in payoff['action_refs']:
        raise ValueError('Hook method does not match the later actual action')
    action = pointer(bundles[ref['world']]['analysis'], ref['pointer'])
    if (sha(action) != ref['sha'] or action.get('state') != 'produced'
            or action.get('review_status') != 'reviewed' or action.get('stop_applied') is not False
            or not action.get('stop_rule_check')
            or mt['method_id'] != action['method_id']
            or mt['method_version'] != action['method_version']
            or mt['claim_scope'] != action['output']['kind']
            or mt['stop_rule_sha'] != sha(action['stop_rule_check'])):
        raise ValueError('Hook method trigger exceeds the effective frozen execution/Stop scope')
    for r in (r for r in h['source_refs'] if r['pointer'] == '/passage'):
        if not any(e['field'] == 'passage' and e['start'] <= r['start']
                   and r['end'] <= e['end'] for e in action['evidence']):
            raise ValueError('Hook pain point falls outside the method application evidence')
    promise = h['promised_payoff']
    if (promise['scene_sha'] != sha(payoff) or promise['source_refs'] != payoff['source_refs']
            or promise['action_refs'] != payoff['action_refs']
            or promise['terminal_refs'] != payoff['terminal_refs']
            or promise['stop_rule_sha'] != mt['stop_rule_sha']
            or promise['candidate'] != payoff.get('candidate')
            or promise['result'] != payoff.get('event')):
        raise ValueError('Hook promise is not the actual bound judgment')
    allowed = {'eliminate': 'candidate_elimination', 'supported': 'candidate_support', 'final': 'whole_question_answer'}
    if promise['scope'] != allowed.get(payoff.get('event')):
        raise ValueError('Hook overclaims an answer beyond its actual payoff')
    terminal = bundles[payoff['world']]['analysis']['question_verification']['candidate_bindings']
    if any(r not in terminal for r in promise['terminal_refs']):
        raise ValueError('Hook result lacks frozen whole-question verification')
    if payoff['event'] == 'final' and len(promise['terminal_refs']) != len(terminal):
        raise ValueError('Answer promise needs complete independent terminal closure')
    visual = h['visual_conflict']; spoiler = h['spoiler_boundary']
    visible = [r['quote'] for r in anchors]
    if (visual['preset'] != 'surface_overlap_relation_displacement'
            or visual['phases'] != HOOK_PHASES or visual['anchor_refs'] != anchors
            or visual['visible_text'] != visible or visual['relation_labels'] is not False
            or spoiler != {'withhold_candidate': True, 'withhold_relation_labels': True,
                           'withhold_verdict': True, 'opening_visible_text': visible,
                           'scope': 'teaser_not_first_question_fact'}):
        raise ValueError('Opening leaks its payoff or changes the user-specified visual conflict')
    approval = h['approved_copy_binding']; path = Path(approval['path'])
    if (not path.is_absolute() or author['input_files'].get(str(path)) != approval['sha256']
            or sha256(path) != approval['sha256']):
        raise ValueError('CREATIVE_DECISION_REQUIRED: explicit user instruction binding is missing/stale')
    if (approval['authority'] != 'explicit_user_instruction' or approval['status'] != 'USER_SPECIFIED'
            or approval['scope'] != 'hook_copy_and_specified_visual_only'):
        raise ValueError('Unconfirmed creativity cannot be self-approved by an agent')
    voices = {v['id']: v['text'] for v in author['voices']}
    copy = [voices[vid] for vid in h['voice_ids']]
    if mt['label'] not in ''.join(voices[vid] for vid in payoff['voice_ids']):
        raise ValueError('Hook method name differs from its actual point-of-use payoff')
    if (copy != approval['quotes'] or sha(copy) != approval['text_sha']
            or any(t not in path.read_text('utf-8-sig') for t in copy)):
        raise ValueError('Hook copy is not the exact externally specified wording')
    forbidden = [x['phrase'] for x in payoff.get('attention', [])]
    if any(token and token in ''.join(copy + visible) for token in forbidden):
        raise ValueError('Opening prematurely discloses the decisive role relation')
    if any(re.search(r'(?<![A-Za-z])[A-D](?![A-Za-z])', t) for t in copy + visible):
        raise ValueError('Opening prematurely discloses candidate letters')
    retention = h['retention']; order = [s['id'] for s in author['scenes']]
    if any(retention[k] not in scenes for k in ('first_payoff_scene_id', 'progression_scene_id', 'final_recall_scene_id')):
        raise ValueError('Audience progression scene does not exist')
    early = scenes[retention['first_payoff_scene_id']]
    first_check = next(s for s in author['scenes'] if s.get('event') in ('eliminate', 'supported'))
    progression = scenes[retention['progression_scene_id']]
    recall = scenes[retention['final_recall_scene_id']]
    reverse = scenes.get(retention.get('reverse_contrast_scene_id'))
    if (early != first_check or retention['first_payoff_scope'] != 'partial_candidate_check'
            or retention['first_payoff_sha'] != sha(early)
            or progression['kind'] != 'task' or progression['world'] != payoff['world']
            or retention['progression_scene_sha'] != sha(progression)
            or recall['kind'] != 'recap' or retention['final_recall_scene_sha'] != sha(recall)
            or not order.index(early['id']) < order.index(progression['id'])
                   < order.index(payoff['id']) < order.index(recall['id'])):
        raise ValueError('Hook/first payoff/progression/final recall chain is absent or stale')
    if reverse is not None and (reverse['world'] == payoff['world'] or not reverse.get('event')
            or not order.index(early['id']) <= order.index(reverse['id']) < order.index(progression['id'])):
        raise ValueError('Reverse contrast must be an earlier real judgment on the other question')
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in h['timing'].values()):
        raise ValueError('Opening requires finite positive production timing')
    return {'status': 'BOUND_USER_SPECIFIED', 'contract_version': HOOK_VERSION,
            'decision_sha': sha(h), 'approval_scope': approval['scope'],
            'teaching_semantics': 'FROZEN_SCOPE_NOT_NEWLY_CERTIFIED',
            'human_review': 'PENDING', 'public_render_ready': False}
ENGAGEMENT = {'curiosity', 'orientation', 'anticipation', 'attention', 'recognition', 'release', 'recall'}
PLAYBACK = {'continuous_fast', 'guided_inline', 'local_replay', 'read_hold', 'payoff_hold', 'settled'}
ACTIONS = {'watch', 'read', 'predict', 'compare', 'recall'}
ENERGY = {'quiet', 'building', 'peak', 'release'}
GAINS = {'locate':'evidence_found', 'interpret':'relation_clarified',
         'group':'grouping_only', 'reduce':'candidate_eliminated',
         'verify':'candidate_checked','answer':'answer_resolved'}

def design_engagement(episode, statuses, direction):
    """No new teaching claims, synthetic audience results or publication approvals."""
    audit = validate_episode(episode, statuses)
    if audit['engineering_status'] == 'BLOCKED':
        raise ValueError('Withdrawn or invalid episode')
    version = direction.get('schema_version')
    v2 = version == V2
    if version not in (VERSION, V2) or direction.get('content_profile') != 'FREE_SHOWCASE':
        raise ValueError('Unsupported audience design/profile')
    questions, chosen = episode['questions'], direction.get('questions', [])
    if [q['question_id'] for q in questions] != [d.get('question_id') for d in chosen]:
        raise ValueError('Original episode order/identity must remain unchanged')
    opening = direction.get('opening', {})
    if not questions or opening.get('question_id') != questions[0]['question_id']:
        raise ValueError('Opening must start on the original first question')
    if opening.get('beat_id') != questions[0]['narrative_beats'][0]['beat_id'] or questions[0]['narrative_beats'][0]['function'] != 'original_task':
        raise ValueError('Hook must start at first original task, not reveal')
    if opening.get('hook_strategy') not in ('actual_problem','visible_contradiction','unexpected_action','question_gap'):
        raise ValueError('Invalid hook strategy')
    if opening.get('promise_scope') not in ('none',questions[0]['payoff']['result_scope']):
        raise ValueError('Hook overclaims first question result')
    out, risks = [], []
    for index,(question,d) in enumerate(zip(questions,chosen)):
        if d.get('speed_strategy') not in ('selected_replay','guided_inline','continuous_fast','mixed'):
            raise ValueError('Unsupported speed strategy')
        if d.get('novelty') not in ('none','new_evidence','new_obstacle','different_application','audience_participation'):
            raise ValueError('Unsupported novelty declaration')
        if d.get('payoff_scope') != question['payoff']['result_scope']:
            raise ValueError('Payoff scope cannot be promoted')
        beats=d.get('beats',[])
        source=question['narrative_beats']
        if [b.get('beat_id') for b in beats] != [b['beat_id'] for b in source]:
            raise ValueError('Beats must retain exact source order')
        merged=[]
        if len({s['beat_id'] for s in source}) != len(source):
            raise ValueError('Question beat identities must be unique')
        for b,s in zip(beats,source):
            if b.get('engagement_function') not in (FUNCTION_TASKS if v2 else ENGAGEMENT) or b.get('playback') not in PLAYBACK or b.get('viewer_action') not in ACTIONS or b.get('energy') not in ENERGY or type(b.get('fresh_information')) is not bool:
                raise ValueError('Invalid editorial beat control')
            fields = {'beat_id','engagement_function','playback','viewer_action','energy','fresh_information'}
            if v2:
                fields |= {'viewer_state', 'editorial_signals'}
                state = b.get('viewer_state', {})
                if set(state) != VIEWER_FIELDS or any(not isinstance(state[k], str) or not state[k].strip()
                        for k in VIEWER_FIELDS - {'information_already_seen'}):
                    raise ValueError('Complete editorial viewer state and viewing task required')
                seen = state['information_already_seen']
                if not isinstance(seen, list) or len(seen) != len(set(seen)) or not set(seen) <= {x['beat_id'] for x in source[:len(merged)]}:
                    raise ValueError('Viewer information must refer only to earlier beats in this question')
                signals = b.get('editorial_signals', {})
                if set(signals) != EDITORIAL_SIGNALS or any(type(x) is not bool for x in signals.values()):
                    raise ValueError('Explicit editorial risk signals required; these are not measurements')
            if set(b) != fields:
                raise ValueError('Unexpected free-form or unsupported editorial field')
            if (s['function']=='payoff') != (b['engagement_function']==('PAYOFF' if v2 else 'release')):
                raise ValueError('Release must coincide with supported payoff')
            if s['function']=='original_task' and b['playback']=='local_replay':
                raise ValueError('Original task cannot start with replay')
            merged.append({**deepcopy(b),'function':s['function'],
                'viewer_sees':s['viewer_sees'],'source_refs':deepcopy(s['source_refs']),
                'bound_source_beat_sha':sha(s)})
        if d['speed_strategy']=='continuous_fast' and any(b['playback']=='local_replay' for b in beats):
            raise ValueError('Continuous fast cannot contain replay')
        if d['speed_strategy']=='selected_replay' and not any(b['playback']=='local_replay' and b['fresh_information'] for b in beats):
            risks.append('REPLAY_WITHOUT_NEW_INFORMATION:'+question['question_id'])
        if not any(b['playback']=='read_hold' for b in beats): risks.append('READING_SPACE_REVIEW:'+question['question_id'])
        if not any(b['playback']=='payoff_hold' for b in beats): risks.append('PAYOFF_HOLD_REVIEW:'+question['question_id'])
        if len({b['energy'] for b in beats})==1: risks.append('FLAT_ENERGY:'+question['question_id'])
        if index and d['novelty']=='none': risks.append('REPETITIVE_QUESTION:'+question['question_id'])
        out.append({'question_id':question['question_id'],
            'editorial_role':question['editorial_role'],'speed_strategy':d['speed_strategy'],
            'novelty':d['novelty'],'payoff_scope':d['payoff_scope'],
            'payoff_gain':GAINS[d['payoff_scope']],
            'payoff_action_refs':deepcopy(question['payoff']['action_refs']),
            'payoff_output_shas':list(question['payoff']['output_shas']),'beats':merged})
    if not any(b['viewer_action'] in ('predict','compare','recall') for q in out for b in q['beats']):
        risks.append('VIEWER_AGENCY_UNDERUSED')
    if len({tuple((b['playback'],b['energy']) for b in q['beats']) for q in out})==1:
        risks.append('REPEATED_RHYTHM')
    result = {'schema_version':version,'kind':'audience_engagement_design',
        'content_profile':'FREE_SHOWCASE','episode_sha':sha(episode),
        'direction_sha':sha(direction),'source_audit_sha':sha(audit),
        'opening':deepcopy(opening),'questions':out,
        'method_recall_sha':sha(episode['method_recall']),
        'quality_audit':{'risk_flags':risks,'scope':'editorial_hypothesis_not_human_taste'},
        'director_handoff':{'timing':'use_actual_native_and_voice_receipts',
            'scope':'editorial_intent_not_new_teaching_fact'},
        'human_review':'PENDING','propagation_metrics':'UNKNOWN',
        'learner_comprehension':'NOT_ASSESSED',
        'consumption_allowed':audit['engineering_status']=='PASS',
        'public_render_ready':False}
    if v2:
        result['quality_audit']['issues'] = engagement_issues(episode, out, risks)
        result['viewer_state_scope'] = 'EDITORIAL_DESIGN_NOT_MEASURED_PSYCHOLOGY'
        result['director_handoff']['playback_adapter'] = {
            'continuous_fast': 'Fast Pass', 'local_replay': 'Local Replay',
            'guided_inline': 'Guided Inline', 'read_hold': 'Observation Hold',
            'payoff_hold': 'Payoff Hold', 'settled': 'settled existing native motion'}
        result['director_handoff']['clocks'] = ['Action', 'Attention', 'Comprehension']
        validate('audience-engagement-plan', result)
    return result


def engagement_issues(episode, questions, risks):
    """Actionable structural suggestions. No aesthetic PASS or new teaching facts."""
    issues = []
    def add(kind, qid, bid, reason, cost, edit):
        issues.append({'issue': {'episode_id': sha(episode), 'question_id': qid,
                                'beat_id': bid, 'type': kind},
            'reason': reason, 'viewer_cost': cost, 'recommended_edit': edit,
            'source_constraints': '保留当前题目必要 Evidence、Review、动作范围与 Stop；仅修改表现设计',
            'status': 'EDITORIAL_SUGGESTION'})
    controls = {
        'payoff_leaked': ('EARLY_PAYOFF', '在有据动作落点前泄露收益', '削弱信息期待', '将揭晓移到既有 payoff beat'),
        'motion_without_gain': ('MOTION_WITHOUT_GAIN', '运动没有新增信息', '注意力负担', '稳定焦点，删除无信息运动'),
        'repeated_explanation': ('REPEATED_EXPLANATION', '重复已经建立的动作解释', '缺乏新的观看理由', '压缩重复解释，转向本题新的证据关系'),
        'method_name_dominates': ('METHOD_NAME_DOMINATES', '方法名称压过题目叙事', '当前任务不清晰', '缩短方法标签，恢复真实题目与实际动作'),
        'voice_over_hold': ('VOICE_OVER_HOLD', '必要停留时仍持续解释', '无法参与阅读或判断', '移开重复口播，保留必要静默'),
        'information_overload': ('INFORMATION_OVERLOAD', '重要信息难以接收', '辨认负担', '分步呈现既有信息，保持原题必要上下文'),
    }
    for q in questions:
        for b in q['beats']:
            signals = b['editorial_signals']
            for signal, (kind, reason, cost, edit) in controls.items():
                if signals[signal]: add(kind, q['question_id'], b['beat_id'], reason, cost, edit)
            if not signals['reading_space'] and b['viewer_action'] in ('read', 'compare'):
                add('READING_SPACE_REVIEW', q['question_id'], b['beat_id'], '阅读或比较没有明确空间', '可能无法跟上', '在既有 Observation Hold 留出稳定阅读时间')
            if not signals['hook_link_clear'] and b['function'] == 'original_task':
                add('HOOK_LINK_UNCLEAR', q['question_id'], b['beat_id'], 'Hook 与当前题目关联不明', '不知道为什么继续看', '用当前真实任务明确观看动机')
            if b['playback'] == 'local_replay' and not b['fresh_information']:
                add('REPLAY_WITHOUT_NEW_INFORMATION', q['question_id'], b['beat_id'], '回看没有新判断信息', '机械重复', '缩短或取消回看，保留必要 Evidence')
    for flag in risks:
        kind, _, qid = flag.partition(':')
        add(kind, qid or None, None, '现有结构审计提示 ' + kind, '需要编辑检查观看成本',
            'REPETITIVE_QUESTION' == kind and '把焦点转向后续题目的新困难或证据路径' or '检查相关节奏、稳定停留与参与任务')
    return issues

def validate_engagement(plan, episode, statuses, direction):
    expected=design_engagement(episode,statuses,direction)
    if plan != expected: raise ValueError('Stale, tampered or self-approved audience plan')
    return {'status':'PASS','consumption_allowed':expected['consumption_allowed'],
            'human_review':'PENDING','public_render_ready':False}


def critical_focus_handoff(author, clock):
    """Consume real candidate states; expectation comes from a bound difference."""
    rows=[]
    for world,q in author['teaching_focus']['questions'].items():
        decisions={}
        for s in clock['scenes']:
            if s['world']!=world:continue
            for ident in s.get('critical_units',[]):
                unit=next(u for u in q['units'] if u['id']==ident)
                rows.append({'scene':s['id'],'unit':ident,'challenge':unit['challenge'],
                    'candidate_states_before':{c:decisions.get(c,'unchecked') for c in q['options']},
                    'focus_candidates':unit['candidates'],'method_action_ref':unit['method_action_ref'],
                    'decisive_source_refs':unit['decisive_source_refs'],'payoff':unit['judgement_change'],
                    'difficulty_basis':unit['difficulty_basis'],'invented_suspense':False,
                    'planned_range':[s['start'],s['end']]})
            if s.get('event') in ('eliminate','supported'):decisions[s['candidate']]=s['event']
    result = {'kind':'critical_judgement_handoff','rows':rows,'actual_media_mapping':'PENDING',
            'human_review':'PENDING','public_render_ready':False}
    if 'audience_hook' in author:
        result['hook']=deepcopy(clock['audience_hook'])
    return result


def director_handoff(plan, episode, statuses, direction, native_direction, beat_scenes):
    """Bind suggestions to existing Adaptive scenes without executing motion.

    Scene positions remain PLANNED even if called 'realized' by the authoring
    file; only verified export anchors can produce actual_media frame ranges.
    """
    validate_engagement(plan, episode, statuses, direction)
    if native_direction.get('episode_plan_sha') != sha(episode) or native_direction.get('content_profile') != 'FREE_SHOWCASE':
        raise ValueError('Adaptive director must bind this FREE_SHOWCASE episode')
    scenes = {s['scene_id']:s for s in native_direction['scenes']}
    if len(scenes) != len(native_direction['scenes']): raise ValueError('Unique native scene ids required')
    if set(beat_scenes) != {q['question_id'] for q in plan['questions']}:
        raise ValueError('All episode questions need an explicit director handoff')
    rows = []
    for q in plan['questions']:
        assignments = beat_scenes[q['question_id']]
        if set(assignments) != {b['beat_id'] for b in q['beats']}:
            raise ValueError('Every source beat must retain a director handoff')
        for beat in q['beats']:
            ids = assignments[beat['beat_id']]
            if not ids or len(ids) != len(set(ids)): raise ValueError('Explicit unique existing scenes required')
            assigned = [scenes[ident] for ident in ids]
            for scene in assigned:
                if scene['question_id'] != q['question_id']:
                    raise ValueError('Cross-question director scene')
                if not {sha(r) for r in scene['source_refs']} & {sha(r) for r in beat['source_refs']}:
                    raise ValueError('Director scene has no shared bound source')
            rows.append({'question_id':q['question_id'], 'beat_id':beat['beat_id'],
                'scene_ids':ids, 'engagement_intent':deepcopy(beat),
                'timing_basis':'PLANNED_NATIVE_DIRECTION_NOT_ACTUAL_EXPORT',
                'planned_scene_ranges':[s['time_range'] for s in assigned],
                'runtime':'existing_adaptive_native_executor', 'status':'DIRECTOR_SUGGESTION'})
    return {'kind':'audience_director_handoff','schema_version':V2,
        'episode_sha':sha(episode),'engagement_plan_sha':sha(plan),
        'native_direction_sha':sha(native_direction),'rows':rows,
        'actual_media_mapping':'UNAVAILABLE','human_review':'PENDING','public_render_ready':False}
