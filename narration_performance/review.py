"""Deterministic risk flags and externally answered A/B questions, never taste certification."""
from copy import deepcopy

from video_contracts import sha
from .plan import check_intent

LISTENING_QUESTIONS = (
    '哪版更像真人在带我做题？',
    'Hook 与普通解释是否能听出状态区别？',
    '搜索与判断过程是否有思考感？',
    'Payoff 有没有终于看清的释放感？',
    'Stop 有没有真正落下来？本片 Stop 无 VO，评价的是结果后的停顿。',
    '有没有表演过头？',
    '有没有播音腔？',
    '有没有 AI 念稿感？',
    '有没有悲伤纪录片感？',
    '中英混读与选项字母是否自然？',
    '尾音有没有再次出现不自然拖尾？',
    '闭眼只听声音，能否感觉思考状态在变化？',
)
OVERACTING_CHECKS = ('advertising_hook', 'shouted_payoff', 'forced_deep_stop', 'strong_emphasis_every_line',
    'excessive_pace_changes', 'emotion_over_logic', 'gain_as_main_expression', 'voice_competes_with_motion',
    'attention_moves_from_question_to_actor')


def risk_qa(plan, timing=None, falling_tails=None):
    """Range/combination lint. Unknown tail evidence never becomes a listening PASS."""
    falling_tails = falling_tails or {}; flags = []; risks = []; run = []
    times = {c['id']: c for c in timing['clips']} if timing else {}
    for clip in plan['clips']:
        intent = clip['intent']; check_intent(intent, clip['transcript'])
        actual = times.get(clip['id'], {})
        long_pause = max(intent['pause_before_ms'], intent['pause_after_ms'],
                         actual.get('pause_before_ms_actual', 0)) >= 1000
        tail = falling_tails.get(clip['id'])
        if tail not in (None, True, False):
            raise ValueError('Falling tail evidence must be unknown or explicit boolean observation')
        slow_low = intent['pace'] <= .42 and intent['energy'] <= .42 and long_pause
        if slow_low and tail is not False:
            run.append(clip['id'])
            if len(run) >= 2:
                risks.append({'code': 'MELANCHOLIC_DRIFT_RISK', 'clips': list(run),
                              'falling_tail_evidence': 'observed' if all(falling_tails.get(x) is True for x in run) else 'UNKNOWN'})
        else:
            run = []
    if all(c['intent']['emphasis'] for c in plan['clips']):
        flags.append('EMPHASIS_EVERY_VO_CLIP_REQUIRES_LISTENING')
    return {'schema': 'narration-performance-risk/v1', 'performance_sha': plan['performance_sha'],
        'scope': 'deterministic_intent_and_timing_lint_not_perceptual_certification',
        'flags': flags, 'risks': risks, 'no_melancholic_drift': 'PENDING_HUMAN_LISTENING',
        'anti_overacting': 'PENDING_HUMAN_LISTENING', 'automatic_audio_change': False,
        'public_render_ready': False}


def review_template(comparison):
    return {'schema': 'narration-performance-review/v1', 'comparison_sha': comparison['comparison_sha'],
        'binding': deepcopy(comparison['binding']), 'outputs': deepcopy(comparison['outputs']),
        'status': 'PENDING', 'reviewer_kind': 'human', 'reviewer': None, 'preference': None,
        'questions': [{'id': 'listen-' + str(i+1).zfill(2), 'question': q, 'response': None}
                      for i,q in enumerate(LISTENING_QUESTIONS)],
        'anti_overacting': {k: None for k in OVERACTING_CHECKS}, 'no_melancholic_drift': None,
        'performance_version_status': 'EXPERIMENT_NOT_FROZEN', 'next_action': 'AWAIT_A_B_LISTENING',
        'final_voice_accepted': False, 'sample_delivery_allowed': False, 'public_render_ready': False}


def validate_human_review(review, comparison):
    """Record a human preference only. Even a preference never releases final video."""
    if (review['comparison_sha'] != comparison['comparison_sha'] or review['binding'] != comparison['binding']
            or review['outputs'] != comparison['outputs']):
        raise ValueError('Human listening review is stale for these actual A/B outputs')
    if review['status'] == 'PENDING':
        if review != review_template(comparison):
            raise ValueError('Pending review cannot pretend a human answered it')
        return {'status': 'PENDING', 'performance_version_status': 'EXPERIMENT_NOT_FROZEN', 'public_render_ready': False}
    if (review['status'] != 'COMPLETED' or review['reviewer_kind'] != 'human'
            or not isinstance(review['reviewer'], str) or not review['reviewer'].strip()
            or review['preference'] not in ('A', 'B', 'NO_CLEAR_PREFERENCE')
            or [q['id'] for q in review['questions']] != ['listen-' + str(i+1).zfill(2) for i in range(12)]
            or [q['question'] for q in review['questions']] != list(LISTENING_QUESTIONS)
            or any(not isinstance(q['response'], str) or not q['response'].strip() for q in review['questions'])
            or set(review['anti_overacting']) != set(OVERACTING_CHECKS)
            or any(type(v) is not bool for v in review['anti_overacting'].values())
            or type(review['no_melancholic_drift']) is not bool
            or any(review[k] is not False for k in ('final_voice_accepted','sample_delivery_allowed','public_render_ready'))):
        raise ValueError('Human listening requires complete explicit answers; AI or old acceptance cannot substitute')
    if any(review['anti_overacting'].values()) or not review['no_melancholic_drift']:
        decision = 'FAIL_PERFORMANCE_DIRECTION'
    elif review['preference'] == 'B':
        decision = 'B_PREFERRED_ELIGIBLE_FOR_SEPARATE_FREEZE'
    else:
        decision = 'STOP_EXPERIMENT_DIAGNOSE_COPY_BACKEND_REFERENCE_OR_COMPLEXITY'
    return {'status': decision, 'review_sha': sha(review), 'final_voice_accepted': False,
            'sample_delivery_allowed': False, 'public_render_ready': False}
