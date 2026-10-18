"""Audience Engagement Design: editorial viewing intentions over frozen episodes."""
from copy import deepcopy
from video_contracts import sha, validate
from creative_os.episode import validate_episode

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
    return {'kind':'critical_judgement_handoff','rows':rows,'actual_media_mapping':'PENDING',
            'human_review':'PENDING','public_render_ready':False}


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
