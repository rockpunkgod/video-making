"""Source-bound editorial resource allocation, never a second answer engine.

Difficulty scores are declared editorial hypotheses, not student measurements.
All terminal decisions continue to belong to the frozen whole-question review.
"""
from copy import deepcopy
import math

from video_contracts import pointer, sha

VERSION = 'critical_judgement_v1'
TREATMENTS = {'quick', 'brief', 'focus'}


def require_focus(author):
    if 'teaching_focus' not in author:
        raise ValueError('New production requires teaching_focus; historical inspection does not authorize a new build')


def validate_focus(author, bundles):
    require_focus(author)
    focus = author['teaching_focus']
    if set(focus) != {'version', 'questions'} or focus['version'] != VERSION or set(focus['questions']) != set(bundles):
        raise ValueError('Teaching focus must cover every frozen question')
    scenes = author['scenes']
    result = {}
    for world, q in focus['questions'].items():
        if set(q) != {'options', 'units'} or set(q['options']) != set(bundles[world]['source_snapshot']['options']):
            raise ValueError('Every option needs a treatment and complete verification reference')
        b = bundles[world]; units = {}; membership = set()
        checks = b['analysis']['question_verification']['review']['candidate_checks']
        for u in q['units']:
            if set(u) != {'id', 'candidates', 'difficulty_basis', 'challenge', 'judgement_change',
                          'method_action_ref', 'decisive_source_refs', 'ratings'}:
                raise ValueError('Unsupported critical judgement unit')
            if not u['id'] or u['id'] in units or not u['candidates'] or len(set(u['candidates'])) != len(u['candidates']):
                raise ValueError('Unique nonempty critical unit required; no fixed pair size')
            if not set(u['candidates']) <= set(q['options']):
                raise ValueError('Critical unit has an unknown option')
            # Observed student difficulty is intentionally not supported without
            # a separate reviewed observation contract. Never promote intuition.
            if u['difficulty_basis'] != 'EDITORIAL_HYPOTHESIS':
                raise ValueError('Student difficulty is not measured by this editorial contract')
            if not u['challenge'].strip() or not u['judgement_change'].strip():
                raise ValueError('A method needs an actual judgement difficulty and resulting change')
            ratings = u['ratings']
            if set(ratings) != {'difficulty', 'method_value', 'visual_payoff'} or any(
                    type(v) is not int or not 0 <= v <= 3 for v in ratings.values()):
                raise ValueError('Explicit provisional 0–3 editorial ratings required')
            if ratings['difficulty'] < 2 or ratings['method_value'] < 2:
                raise ValueError('Premium motion requires a difficult judgement with method value')
            ref = u['method_action_ref']
            if (set(ref) != {'world', 'pointer', 'sha'} or ref['world'] != world
                    or not ref['pointer'].startswith('/execution_trace/')):
                raise ValueError('Method value must bind a frozen execution')
            action = pointer(b['analysis'], ref['pointer'])
            if (sha(action) != ref['sha'] or action.get('review_status') != 'reviewed'
                    or action.get('state') != 'produced' or action.get('stop_applied') is not False
                    or not action.get('stop_rule_check')):
                raise ValueError('Method execution is stale, stopped or unreviewed')
            if not u['decisive_source_refs']:
                raise ValueError('Critical difference needs decisive source evidence')
            for r in u['decisive_source_refs']:
                if r['world'] != world or r['pointer'] != '/passage':
                    raise ValueError('Decisive evidence must be original passage text')
                value = pointer(b['source_snapshot'], r['pointer'])
                if (type(r['start']) is not int or type(r['end']) is not int
                        or not 0 <= r['start'] < r['end'] <= len(value)
                        or value[r['start']:r['end']] != r['quote']
                        or not any(e['field'] == 'passage' and e['start'] <= r['start'] < r['end'] <= e['end']
                                   for e in action['evidence'])):
                    raise ValueError('Decisive difference exceeds frozen method evidence')
            units[u['id']] = u; membership.update(u['candidates'])
            displayed = [r for s in scenes if s['world'] == world and s.get('candidate') in u['candidates']
                         and s['kind'] == 'compare' for r in s['source_refs']]
            for r in u['decisive_source_refs']:
                if not any(d['world'] == world and d['pointer'] == '/passage'
                           and d['start'] <= r['start'] < r['end'] <= d['end'] for d in displayed):
                    raise ValueError('A critical difference is hidden from the visible comparison')
        for candidate, opt in q['options'].items():
            if set(opt) != {'treatment', 'rationale', 'verification_ref'} or opt['treatment'] not in TREATMENTS or not opt['rationale'].strip():
                raise ValueError('Each option needs an explicit justified treatment')
            ref = opt['verification_ref']
            if set(ref) != {'pointer', 'sha'} or not ref['pointer'].startswith('/question_verification/review/candidate_checks/'):
                raise ValueError('All-option review must bind the original complete candidate check')
            check = pointer(b['analysis'], ref['pointer'])
            if check not in checks or check['candidate'] != candidate or sha(check) != ref['sha'] or not check['evidence'] or not check['backfill_check']:
                raise ValueError('All-option verification is missing or stale')
            if (opt['treatment'] == 'focus') != (candidate in membership):
                raise ValueError('Critical options cannot be silently skimmed; premium motion needs a critical unit')
            selected = [s for s in scenes if s['world'] == world and s.get('candidate') == candidate
                        and s.get('event') in ('eliminate', 'supported')]
            if len(selected) != 1:
                raise ValueError('Every verified option needs exactly one visible decision')
            s = selected[0]
            if opt['treatment'] == 'focus':
                related = [u for u in units.values() if candidate in u['candidates']]
                if not any(u['method_action_ref'] in s['action_refs'] for u in related):
                    raise ValueError('Critical scene did not consume its frozen method action')
            # The visible evidence cannot be removed merely to save time. The
            # full backstage check stays bound even when only a key span is shown.
            if not any(r['world'] == world and r['pointer'] == '/passage' for r in s['source_refs']):
                raise ValueError('A fast verdict still needs visible passage evidence')
        for s in scenes:
            if s['world'] == world and s['kind'] == 'replay' and s.get('candidate') not in membership:
                raise ValueError('Slow replay must serve a critical method judgement')
        result[world] = {'units': deepcopy(list(units.values())), 'verified_options': list(q['options']),
                         'focus_options': [c for c in q['options'] if c in membership],
                         'critical_option_pairs': [u['candidates'] for u in units.values() if len(u['candidates']) == 2],
                         'student_difficulty': 'UNMEASURED', 'semantic_review': 'PENDING'}
    return result


def direct_scene(author, shot):
    """Consume the allocation in the actual clock, preserving reading and takes."""
    s = deepcopy(shot)
    if 'teaching_focus' not in author:
        return s  # read/replay compatibility; new production entry requires it
    q = author['teaching_focus']['questions'][s['world']]
    if s['kind'] not in ('compare', 'replay'):
        return s
    treatment = q['options'][s['candidate']]['treatment']
    s['teaching_treatment'] = treatment
    s['critical_units'] = [u['id'] for u in q['units'] if s['candidate'] in u['candidates']]
    if treatment != 'focus':
        s['motion_treatment'] = 'in_place_check'
        m = s['choreography']
        # Remove the expensive extraction/flight, not the evidence reading.
        m.update(orient_seconds=.9, candidate_read_seconds=.8 if treatment == 'quick' else 1.2,
                 candidate_travel_seconds=0, extract_seconds=0,
                 comparison_seconds=.65 if treatment == 'quick' else 1.0,
                 decision_seconds=.4, result_seconds=.4, return_seconds=.6)
        if 'evidence_hold_frames' in s.get('light_presentation',{}):
            if not s.get('reading_path'):raise ValueError('Light evidence hold needs an actual source reading window')
            s['reading_path'][-1]['read_seconds']=s['light_presentation']['evidence_hold_frames']/author['format']['fps']
    else:
        s['motion_treatment'] = 'critical_comparison'
        from content_os.scoring import teaching_value_points
        value = max(teaching_value_points(u)
                    for u in q['units'] if s['candidate'] in u['candidates'])
        s['choreography']['comparison_seconds'] = max(s['choreography']['comparison_seconds'], 1.6 + value/10)
    return s


def resource_report(author, plan):
    """Measure the compiled clock. Density is a diagnostic, not a speed target."""
    from content_os.scoring import teaching_value_points
    omission=None
    if 'replay_policy' in author:
        # Import only at consumption time: authored_episode already uses this
        # module. A source-bound user omission may miss the share target; it
        # cannot fabricate an improvement, shorten reading or add padding.
        from ae_production.authored_episode import validate_replay_policy
        omission=validate_replay_policy(author)
        if omission['mode']!='omitted_by_user' or omission['expected_replays']!=0:
            raise ValueError('Only the validated user replay omission can override the attention-share target')
    rows = []
    if not any(q['units'] for q in author['teaching_focus']['questions'].values()):
        raise ValueError('A method-led main film needs at least one real critical method judgement')
    for world, q in author['teaching_focus']['questions'].items():
        seconds = {'quick': 0., 'brief': 0., 'focus': 0.}; options = []
        for s in plan['scenes']:
            if s['world'] != world or s['kind'] not in ('compare', 'replay'):
                continue
            expected = direct_scene(author, next(x for x in author['scenes'] if x['id'] == s['id']))
            for k in ('motion_treatment', 'teaching_treatment', 'critical_units', 'choreography'):
                if s.get(k) != expected[k]:
                    raise ValueError('Teaching allocation was bypassed in the compiled scene: '+s['id'])
            duration = s['end'] - s['start']
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Invalid resource clock')
            seconds[s['teaching_treatment']] += duration
            options.append({'scene': s['id'], 'candidate': s['candidate'], 'kind': s['kind'],
                            'treatment': s['teaching_treatment'], 'seconds': round(duration, 4),
                            'motion': s['motion_treatment']})
        total = sum(seconds.values()); share = seconds['focus']/total if total else 0
        points = sum(teaching_value_points(u) for u in q['units'])
        if q['units'] and share <= .5 and omission is None:
            raise ValueError('Critical judgements do not receive most comparison/replay time; revise copy or selection, never speed up evidence')
        rows.append({'world': world, 'options': options, 'seconds': seconds, 'critical_attention_share': share,
                     'teaching_value_density': points/total if total else None,
                     'density_basis': 'PROVISIONAL_EDITORIAL_POINTS_PER_COMPILED_SECOND_NOT_LEARNING_OUTCOME',
                     'verified_options': list(q['options'])})
        if omission is not None:
            rows[-1].update(target_met=share>.5,target_applies=bool(q['units']),
                            user_authorized_replay_omission=True)
    result={'version': VERSION, 'questions': rows, 'target_episode_seconds': [300, 480],
            'duration_note': 'WITHIN_TARGET' if 300 <= plan['duration'] <= 480 else 'OUTSIDE_TARGET_REVIEW_SELECTION_NO_PADDING',
            'actual_media_review': 'PENDING', 'student_results': 'UNMEASURED', 'public_render_ready': False}
    if omission is not None:
        result['user_authorized_replay_omission']={
            'mode':omission['mode'],'source_sha256':omission['source_sha256'],
            'scope':'REPLAY_OMITTED_ACTUAL_SHARE_REPORTED_TARGET_NOT_WAIVED_AS_MET',
            'target_met':all(row['target_met'] for row in rows if row['target_applies']),
            'timing_adjustment':'NONE_NO_PADDING_OR_REPLAY_ADDED'}
    return result
