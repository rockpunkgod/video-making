"""Audience Engagement Design: editorial viewing intentions over frozen episodes."""
from copy import deepcopy
from video_contracts import sha
from creative_os.episode import validate_episode

VERSION = '0.1.0'
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
    if direction.get('schema_version') != VERSION or direction.get('content_profile') != 'FREE_SHOWCASE':
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
        for b,s in zip(beats,source):
            if b.get('engagement_function') not in ENGAGEMENT or b.get('playback') not in PLAYBACK or b.get('viewer_action') not in ACTIONS or b.get('energy') not in ENERGY or type(b.get('fresh_information')) is not bool:
                raise ValueError('Invalid editorial beat control')
            if set(b) != {'beat_id','engagement_function','playback','viewer_action','energy','fresh_information'}:
                raise ValueError('Unexpected free-form or unsupported editorial field')
            if (s['function']=='payoff') != (b['engagement_function']=='release'):
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
    return {'schema_version':VERSION,'kind':'audience_engagement_design',
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

def validate_engagement(plan, episode, statuses, direction):
    expected=design_engagement(episode,statuses,direction)
    if plan != expected: raise ValueError('Stale, tampered or self-approved audience plan')
    return {'status':'PASS','consumption_allowed':expected['consumption_allowed'],
            'human_review':'PENDING','public_render_ready':False}
