"""P3 internal shot handoff. Projects frozen objects; never authors teaching facts."""
from copy import deepcopy
import math
import re

from ae_production.candidate_motion import audit_candidate_events
from video_contracts import pointer, sha
from .typeset import digest


def number(value, label, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError('Invalid ' + label)
    return value


def resolve(ref, bundles):
    value = pointer(bundles[ref['asset_id']], ref['pointer'])
    if sha(value) != ref['sha']:
        raise ValueError('Frozen reference changed')
    return value


def validate_shot_script(script, bundles, layouts, style):
    """No self-hash or approval field needed for drafts. Source bindings remain required."""
    if script['schema'] != 'shot-script/v1':
        raise ValueError('Unsupported shot contract')
    fps = number(script['fps'], 'fps', 1)
    if fps != style['coordinates']['fps']:
        raise ValueError('Frame rate must match supplied style')
    duration = number(script['duration'], 'duration', 1/fps)
    objects = {}
    for obj in script['objects']:
        if obj['id'] in objects:
            raise ValueError('Duplicate source object')
        source = resolve(obj['source_ref'], bundles)
        if not isinstance(source, str) or obj['text'] != source:
            raise ValueError('Source object must contain exact frozen text')
        plan = layouts[obj['layout_id']]
        if (plan['schema'] != 'typeset-plan/v1' or plan['source_sha256'] != digest(source.encode('utf-8'))
                or plan['style_sha256'] != sha(style)):
            raise ValueError('Layout bound to different source or style')
        expected = [(m.group(), m.start(), m.end()) for m in re.finditer(r'\S+', source)]
        if [(w['text'], w['start'], w['end']) for w in plan['words']] != expected:
            raise ValueError('Original word coverage changed')
        for word in plan['words']:
            for key in ('x', 'y', 'w', 'size'):
                number(word[key], 'glyph '+key, -1e9 if key in ('x', 'y') else 0)
        from .semantic_text_layout import focus_windows
        if plan['focus_windows'] != focus_windows(plan['words'], style['layout']['focus_max_lines']):
            raise ValueError('Focus windows changed')
        objects[obj['id']] = obj
    targets = {}
    for target in script['targets']:
        if target['id'] in targets or target['object_id'] not in objects:
            raise ValueError('Duplicate or dangling target')
        text = objects[target['object_id']]['text']
        a, b = target['range']
        if (type(a) is not int or type(b) is not int or not 0 <= a < b <= len(text)
                or text[a:b] != target['text']):
            raise ValueError('Target must be an exact original slice')
        targets[target['id']] = target
    events = script.get('candidate_events', [])
    answers = script.get('answers', [])
    audited = audit_candidate_events(events, bundles, answers)
    for event in events:
        if event['confirmation_start'] > duration:
            raise ValueError('Candidate event outside shot')
    if any(a['time'] > duration for a in answers):
        raise ValueError('Answer outside shot')
    world = 'reading'; world_until = 0; lifted = set(); busy = {}; last = -1
    action_ids = set(); linked = set()
    for action in script['actions']:
        if action['id'] in action_ids:
            raise ValueError('Duplicate action id')
        action_ids.add(action['id'])
        at = number(action['at'], 'action time')
        kind = action['action']
        config = style['motion']['actions']
        if kind not in ('locate', 'lift', 'compare', 'eliminate', 'return', 'dim_world', 'brighten_world'):
            raise ValueError('Unsupported action')
        frames = (style['depth']['light_dark']['dim_transition_frames'] if kind in ('dim_world','brighten_world')
                  else config[kind]['frames'])
        if type(frames) is not int or frames < 1:
            raise ValueError('Positive integer action frames required')
        end = at + frames/fps
        if at < last or end > duration:
            raise ValueError('Actions must be ordered and inside shot')
        last = at
        ids = action.get('targets', [])
        if len(ids) != len(set(ids)) or any(i not in targets for i in ids):
            raise ValueError('Dangling or repeated action target')
        if kind in ('dim_world', 'brighten_world'):
            desired = 'thinking' if kind == 'dim_world' else 'reading'
            if ids or world == desired or at < world_until or (desired == 'reading' and
                    (lifted or any(t > at for t in busy.values()))):
                raise ValueError('Invalid light/dark transition or return unfinished')
            world = desired; world_until = end
        else:
            if not ids or any(at < busy.get(i, 0) for i in ids):
                raise ValueError('Missing target or overlapping target movement')
            if kind == 'lift':
                if world != 'thinking' or any(i in lifted for i in ids):
                    raise ValueError('Lift requires thinking state and original glyph')
                lifted.update(ids)
            if kind in ('compare', 'return') and any(i not in lifted for i in ids):
                raise ValueError('Compare/return requires lifted originals')
            if kind == 'return':
                lifted.difference_update(ids)
            if kind == 'eliminate':
                index = action['candidate_event_index']
                if type(index) is not int or not 0 <= index < len(events) or index in linked:
                    raise ValueError('Elimination needs one unique audited event')
                event = events[index]
                if event['effect'] != 'eliminate' or abs(at-event['decision_start']) > 1e-8 or abs(end-event['decision_end']) > 1e-8:
                    raise ValueError('Elimination must match audited timing')
                for tid in ids:
                    obj = objects[targets[tid]['object_id']]
                    ref = obj['source_ref']
                    if (ref['asset_id'] != event['source_refs'][0]['asset_id'] or
                            ref['pointer'] != '/source_snapshot/options/'+event['candidate'] or
                            targets[tid]['range'] != [0, len(obj['text'])]):
                        raise ValueError('Eliminate the whole frozen option, not another object')
                linked.add(index)
            busy.update({i: end for i in ids})
    if linked != {i for i,e in enumerate(events) if e['effect'] == 'eliminate'}:
        raise ValueError('Every elimination must be visible')
    return dict(status='PASS', candidate_audit=audited, public_render_ready=False,
                scope='internal_mechanical_handoff_not_teaching_or_visual_approval')


def compile_shot_script(script, bundles, layouts, style):
    audit = validate_shot_script(script, bundles, layouts, style)
    actions = []
    for action in script['actions']:
        row = deepcopy(action)
        kind = action['action']
        row['parameters'] = deepcopy(style['depth']['light_dark'] if kind in ('dim_world','brighten_world')
                                    else style['motion']['actions'][kind])
        frames = row['parameters'].get('frames', row['parameters'].get('dim_transition_frames'))
        row['end'] = row['at'] + frames/script['fps']
        if kind == 'lift':
            row['depth_parameters'] = deepcopy(style['depth']['light_dark'])
        actions.append(row)
    return dict(schema='shot-handoff/v1', script=deepcopy(script), actions=actions,
                layouts=deepcopy(layouts), style=deepcopy(style), audit=audit,
                geometry='PROVISIONAL_REQUIRES_AE_MEASUREMENT', native_render_status='NOT_RUN',
                public_render_ready=False)
