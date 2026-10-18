"""Opt-in Audience -> authored Adaptive event contract; no geometry or truth producer.

All times are planned seconds on the existing 24 fps spec. A successful compile
is code verification only, never an Adobe receipt or an actual-media anchor.
"""
from copy import deepcopy
import math
import hashlib
from pathlib import Path

from video_contracts import read, sha, pointer
from creative_os.audience_engagement import director_handoff
from .candidate_motion import audit_candidate_events
from .judgement_preflight import bind_existing_scenes

VERSION = '0.1.0'


def _range(value, limit):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(t) not in (int, float) or not math.isfinite(t) for t in value)
            or not 0 <= value[0] < value[1] <= limit):
        raise ValueError('Finite positive planned range within parent required')
    return value


def _index(rows, key):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate ' + key)
    return result


def compile_adapter(plan, episode, statuses, audience_direction, native_direction,
                    beat_scenes, spec, bindings, transitions=(), voices=()):
    """Validate explicit beat/scene/event/object bindings without retiming inputs.

    bindings: selected scene + source beat + attention/reading windows + object
    IDs + optional candidate event ID. Unselected beats remain suggestions.
    transitions: adjacent question payoff -> next obstacle -> next gain beat IDs;
    all prose is projected from the already validated Viewer States.
    """
    if spec.get('spec_sha') != sha({k: v for k, v in spec.items() if k != 'spec_sha'}):
        raise ValueError('Changed native spec')
    # Reuse the existing full-source/object-lifetime projection, not a new mapper.
    projected, _ = bind_existing_scenes(episode, native_direction, spec, beat_scenes)
    handoff = director_handoff(plan, episode, statuses, audience_direction, projected, beat_scenes)
    if plan.get('schema_version') != '0.2.0' or plan.get('consumption_allowed') is not True:
        raise ValueError('Current consumable Audience v0.2 required')
    scenes = _index(projected['scenes'], 'scene_id')
    nodes = _index(spec['nodes'], 'node_id')
    events = _index(spec.get('events', []), 'scene_id')
    bundles = {b['asset_id']: b for q in episode['questions'] for b in q['package']['source_items']}
    candidate_audit = audit_candidate_events(spec.get('events', []), bundles,
                                            spec.get('answer_confirmations', ()))
    candidate_rows = _index(candidate_audit['events'], 'scene_id')
    duration = spec['canvas']['duration']
    rows = {(r['question_id'], r['beat_id']): r for r in handoff['rows']}
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('Explicit selected scene bindings required')
    selected, checks, preview_times = set(), [], []
    for binding in bindings:
        if set(binding) != {'question_id', 'beat_id', 'scene_id', 'object_ids',
                            'attention_range', 'reading_range', 'candidate_event_id'}:
            raise ValueError('Unexpected or missing adapter binding fields')
        key = (binding['question_id'], binding['beat_id'])
        row = rows[key]; sid = binding['scene_id']; scene = scenes[sid]
        if sid not in row['scene_ids'] or sid in selected:
            raise ValueError('Scene must have one explicit source beat binding')
        selected.add(sid)
        window = _range(scene['time_range'], duration)
        attention = _range(binding['attention_range'], window[1])
        reading = _range(binding['reading_range'], window[1])
        if min(attention[0], reading[0]) < window[0] or attention[0] > reading[0]:
            raise ValueError('Orient attention before reading within the selected scene')
        objects = binding['object_ids']
        if not objects or len(objects) != len(set(objects)):
            raise ValueError('Unique attended object IDs required')
        refs = {sha(r) for r in row['engagement_intent']['source_refs']}
        for ident in objects:
            node = nodes[ident]
            if (not refs & {sha(r) for r in node['source_refs']}
                    or node['in_point'] > attention[0] or node['out_point'] < max(attention[1], reading[1])):
                raise ValueError('Attended object must retain beat source and full window lifetime')
            for ref in node['source_refs']:
                bundle = bundles[ref['asset_id']]
                if sha(pointer(bundle, ref['pointer'])) != ref['sha']:
                    raise ValueError('Changed attended object source')
                if bundle['source_snapshot']['question_id'] != key[0]:
                    raise ValueError('Cross-question attended object')
        event_id = binding['candidate_event_id']
        event, candidate = None, None
        if event_id is not None:
            event = events[event_id]
            times = [event[k] for k in ('compare_start', 'decision_start', 'decision_end', 'confirmation_start')]
            if (event_id != sid or event['question_id'] != key[0]
                    or not window[0] <= times[0] < times[1] < times[2] <= times[3] < window[1]
                    or reading[0] < times[0] or reading[1] > times[1]):
                raise ValueError('Read comparison before decision in the bound event scene')
            candidate = candidate_rows[event_id]
        elif sid in events:
            raise ValueError('Candidate scene cannot omit its actual event binding')
        # A deliberate read/payoff hold must be quiet and settled. Other reading
        # windows can carry authored guidance; they are never called silent holds.
        intent = row['engagement_intent']
        quiet = intent['playback'] in ('read_hold', 'payoff_hold')
        if quiet:
            if any(v['start'] < reading[1] and v['end'] > reading[0] for v in voices):
                raise ValueError('Authored voice overlaps quiet observation/payoff hold')
            tracks = [spec['camera']['position']]
            tracks += [n['tracks'][k] for n in (nodes[i] for i in objects)
                       for k in ('position', 'scale', 'opacity') if k in n['tracks']]
            if not all(_settled(track, reading) for track in tracks):
                raise ValueError('Reading hold requires settled authored camera and objects')
        preview_times.extend([reading[0], (reading[0] + reading[1]) / 2])
        if event:
            preview_times.extend([event['decision_start'], event['confirmation_start']])
        checks.append({'question_id': key[0], 'beat_id': key[1], 'scene_id': sid,
            'viewer_task': intent['viewer_state']['viewer_task'],
            'unresolved_question': intent['viewer_state']['unresolved_question'],
            'next_information_gain': intent['viewer_state']['next_information_gain'],
            'object_ids': deepcopy(objects), 'attention_range': attention,
            'reading_range': reading, 'quiet_hold': quiet,
            'action_range': [event['decision_start'], event['decision_end']] if event else None,
            'confirmation_time': event['confirmation_start'] if event else None,
            'candidate_projection': deepcopy(candidate),
            'planned_event_sha': sha(event) if event else None,
            'visibility': 'OBJECT_AND_KEYFRAME_CHECK_ONLY_HUMAN_PENDING'})
    progressions = _progressions(plan, scenes, beat_scenes, transitions)
    return {'schema_version': VERSION, 'kind': 'audience_adaptive_adapter',
        'episode_sha': sha(episode), 'statuses_sha': sha(statuses),
        'handoff_sha': sha(handoff), 'spec_sha': spec['spec_sha'],
        'voices_sha': sha(voices), 'bindings_sha': sha(bindings),
        'transitions_sha': sha(transitions), 'selected_scenes': checks,
        'unselected_handoff_rows': [deepcopy(r) for r in handoff['rows']
            if not set(r['scene_ids']) <= selected],
        'progressions': progressions, 'preview_times': sorted(set(preview_times)),
        'timing_basis': 'PLANNED_NATIVE_SPEC_NOT_ACTUAL_EXPORT',
        'code_verification': 'PASS', 'native_execution': 'NOT_ASSESSED',
        'actual_media_mapping': 'UNAVAILABLE', 'human_review': 'PENDING',
        'public_render_ready': False}


def _settled(track, window):
    """Conservative: no changing key segment may intersect the reading window.

    Equal bracketing keys are accepted. This does not certify native ease handles,
    occlusion, focus or legibility; those still require native readback and review.
    """
    if (not isinstance(track, list) or not track
            or any(not isinstance(k, list) or len(k) != 2
                   or type(k[0]) not in (int, float) or not math.isfinite(k[0]) for k in track)
            or any(a[0] >= b[0] for a, b in zip(track, track[1:]))):
        raise ValueError('Explicit ordered authored keys required for settled hold')
    return all(a[1] == b[1] for a, b in zip(track, track[1:])
               if a[0] < window[1] and b[0] > window[0])


def _progressions(plan, scenes, mapping, transitions):
    questions = plan['questions']; output = []; used = set()
    for transition in transitions:
        if set(transition) != {'from_question_id', 'to_question_id', 'payoff_beat_id',
                               'obstacle_beat_id', 'gain_beat_id'}:
            raise ValueError('Only source beat references allowed in progression')
        before, after = transition['from_question_id'], transition['to_question_id']
        index = [q['question_id'] for q in questions].index(before)
        if index + 1 >= len(questions) or questions[index+1]['question_id'] != after or before in used:
            raise ValueError('Progression must join adjacent original questions once')
        used.add(before); a, b = questions[index:index+2]
        beats_a = _index(a['beats'], 'beat_id'); beats_b = _index(b['beats'], 'beat_id')
        payoff = beats_a[transition['payoff_beat_id']]
        obstacle = beats_b[transition['obstacle_beat_id']]; gain = beats_b[transition['gain_beat_id']]
        if (payoff['function'] != 'payoff' or b['novelty'] == 'none'
                or not gain['fresh_information'] or b['beats'].index(gain) <= b['beats'].index(obstacle)):
            raise ValueError('Earned payoff, new obstacle and later fresh gain required')
        def start_end(qid, beat):
            ranges = [scenes[s]['time_range'] for s in mapping[qid][beat['beat_id']]]
            return min(r[0] for r in ranges), max(r[1] for r in ranges)
        if (start_end(before, payoff)[1] > start_end(after, obstacle)[0]
                or start_end(after, obstacle)[1] > start_end(after, gain)[0]):
            raise ValueError('Payoff must precede next obstacle and its information gain')
        output.append({**deepcopy(transition), 'earned_gain': a['payoff_gain'],
            'next_viewer_task': obstacle['viewer_state']['viewer_task'],
            'open_question': obstacle['viewer_state']['unresolved_question'],
            'promised_gain': gain['viewer_state']['next_information_gain'],
            'novelty': b['novelty'], 'status': 'PLANNED_EDITORIAL_NOT_MEASURED',
            'automatic_duration_extension': False})
    return output


def consume_request(request, episode, statuses):
    """Optional native-request integration; paths must be in existing input SHA set.

    The saved adapter output is compared to a fresh compilation at every current()
    check. No self-sealed JSON or old status list is sufficient for acceptance.
    """
    if 'audience_adapter' not in request:
        return None
    config = request['audience_adapter']
    names = {'plan', 'audience_direction', 'native_direction', 'beat_scenes',
             'bindings', 'transitions', 'compiled'}
    if not isinstance(config, dict) or set(config) != names:
        raise ValueError('Complete explicit audience_adapter paths required')
    protected = {Path(p).resolve() for p in request['input_files']}
    if any(Path(config[k]).resolve() not in protected for k in names):
        raise ValueError('Audience adapter inputs must be SHA-bound input_files')
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest
           for p, digest in request['input_files'].items()):
        raise ValueError('Changed SHA-bound adapter input')
    values = {k: read(config[k]) for k in names}
    expected = compile_adapter(values['plan'], episode, statuses,
        values['audience_direction'], values['native_direction'], values['beat_scenes'],
        request['spec'], values['bindings'], values['transitions'], request['voices'])
    if expected != values['compiled']:
        raise ValueError('Stale or tampered Audience Adaptive compilation')
    return expected
