"""Read-only production checks for the bounded R06 judgement revision.

This module reports missing annotation authorization. It does not manufacture
annotations, reviews or a new teaching gate, and contains no Adobe executor.
"""
from copy import deepcopy

from video_contracts import pointer, sha
from .candidate_motion import audit_candidate_events


def bound_value(bundles, ref):
    value = pointer(bundles[ref['asset_id']], ref['pointer'])
    if sha(value) != ref['sha']:
        raise ValueError('Changed frozen source reference')
    return value


def candidate_prefix(spec, bundles, scene_id):
    """Derive an excerpt's start state from the whole ordered action prefix."""
    audit = audit_candidate_events(spec['events'], bundles, spec.get('answer_confirmations', ()))
    rows = [row for row in audit['events'] if row['scene_id'] == scene_id]
    if len(rows) != 1:
        raise ValueError('Exactly one selected candidate event required')
    event = next(e for e in spec['events'] if e['scene_id'] == scene_id)
    index = spec['events'].index(event)
    return {'whole_sequence_audit': audit, 'selected': rows[0],
            'prefix_event_refs': [sha(e) for e in spec['events'][:index]],
            'selected_event_sha': sha(event), 'final_answer_at_selected_event': False}


def inspect_phrase_requests(bundles, event, operations):
    """Locate proposed ranges inside reviewed evidence, without authorizing them.

    Exact lexical ranges are necessary but not a reviewed semantic partition.
    R06 has no current accepted fine-annotation transport. Upstream responses
    need contract review before they can enable a renderer; no boolean override.
    """
    if not operations or len({x['operation_id'] for x in operations}) != len(operations):
        raise ValueError('Unique explicit proposed operations required')
    bundle = bundles[event['source_refs'][0]['asset_id']]
    actions = [(ref, bound_value(bundles, ref)) for ref in event['source_refs']
               if ref['pointer'].startswith('/source_snapshot/action_executions/')]
    if len(actions) != 1:
        raise ValueError('One frozen candidate action required')
    action_ref, action = actions[0]
    relation_index = action['output']['relation_index']
    relation_path = '/source_snapshot/relations/' + str(relation_index)
    relation_refs = [r for r in event['source_refs'] if r['pointer'] == relation_path]
    if len(relation_refs) != 1:
        raise ValueError('Exact reviewed relation binding required')
    relation_ref = relation_refs[0]
    relation = bound_value(bundles, relation_ref)
    if action.get('review_status') != 'reviewed' or relation.get('review_status') != 'reviewed':
        raise ValueError('Reviewed action and relation required')
    if any(relation[k] != action['output'][k] for k in ('candidate', 'effect')):
        raise ValueError('Relation and candidate output disagree')
    active = {r['artifact_id'] for r in bundle['lifecycle']['reviews'] if r['status'] == 'active'}
    reviews = [r for r in bundle['reviews'] if r['artifact_id'] in active
               and r['level'] != 'unreviewed'
               and action['execution_id'] in r['record'].get('own_execution_ids', [])
               and all(r['record'].get('checks', {}).get(k) is True
                       for k in ('trigger', 'action', 'evidence', 'role', 'stop'))]
    if not reviews:
        raise ValueError('Active review bound to this action required')
    rows = []
    for operation in operations:
        selection = operation['selection']
        ref = selection['source_ref']
        if ref['asset_id'] != action_ref['asset_id']:
            raise ValueError('Cross-question phrase request')
        source = bound_value(bundles, ref)
        start, end = selection['start'], selection['end']
        if (not isinstance(source, str) or type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(source)
                or source[start:end] != selection['quote']):
            raise ValueError('Exact original phrase range required')
        field = selection['field']
        expected = '/source_snapshot/passage' if field == 'passage' else (
            '/source_snapshot/options/' + field[7:] if field.startswith('option:') else None)
        if ref['pointer'] != expected:
            raise ValueError('Evidence field and source pointer disagree')
        containers = []
        for i, evidence in enumerate(relation['evidence']):
            if (evidence['field'] == field and evidence['start'] <= start < end <= evidence['end']
                    and source[evidence['start']:evidence['end']] == evidence['quote']
                    and evidence in action['evidence']):
                containers.append({'asset_id': ref['asset_id'],
                    'pointer': relation_path + '/evidence/' + str(i), 'sha': sha(evidence)})
        if not containers:
            raise ValueError('Phrase is outside this action/relation evidence')
        rows.append({**deepcopy(operation), 'lexical_range': 'PASS',
                     'evidence_container_refs': containers,
                     'existing_review_scope': 'ACTION_AND_SENTENCE_RELATION',
                     'operation_authorization': 'MISSING',
                     'required_response': 'explicit reviewed range, operation and relation binding'})
    return {'kind': 'upstream_annotation_request', 'request_sha': sha(operations),
            'question_id': event['question_id'], 'action_ref': action_ref,
            'relation_ref': relation_ref, 'review_refs': [
                {'artifact_id': r['artifact_id'], 'sha': r['sha'], 'level': r['level']} for r in reviews],
            'operations': rows, 'status': 'HOLD_MISSING_FINE_ANNOTATION',
            'teaching_review_created': False, 'public_render_ready': False}


def bind_existing_scenes(episode, direction, spec, mapping):
    """Normalize a separate handoff projection; never edit the old direction.

    Source-object lifetime evidence is not on-screen comprehension certification.
    director_handoff remains responsible for full beat coverage/intersections.
    """
    projected = deepcopy(direction)
    if direction.get('content_profile', 'FREE_SHOWCASE') != 'FREE_SHOWCASE':
        raise ValueError('R06 revision requires FREE_SHOWCASE')
    projected['parent_direction_sha'] = sha(direction)
    projected['episode_plan_sha'] = sha(episode)
    projected['content_profile'] = 'FREE_SHOWCASE'
    bundles = {b['asset_id']: b for q in episode['questions'] for b in q['package']['source_items']}
    asset_questions = {b['asset_id']: q['question_id'] for q in episode['questions']
                       for b in q['package']['source_items']}
    ids = [s['scene_id'] for s in projected['scenes']]
    if len(set(ids)) != len(ids):
        raise ValueError('Unique real native scene IDs required')
    evidence = []
    for scene in projected['scenes']:
        questions = {asset_questions[r['asset_id']] for r in scene['source_refs']}
        if len(questions) != 1:
            raise ValueError('Scene must belong to one original question')
        question_id = questions.pop()
        if scene.get('question_id', question_id) != question_id:
            raise ValueError('Native scene question identity changed')
        scene['question_id'] = question_id
        for ref in scene['source_refs']:
            bound_value(bundles, ref)
        start, end = scene['time_range']
        if not 0 <= start < end <= spec['canvas']['duration']:
            raise ValueError('Scene outside native composition')
        refs = {sha(r) for r in scene['source_refs']}
        nodes = [n['node_id'] for n in spec['nodes']
                 if n['in_point'] < end and n['out_point'] > start
                 and refs & {sha(r) for r in n['source_refs']}]
        if not nodes:
            raise ValueError('Scene has no corresponding source objects in native spec')
        evidence.append({'scene_id': scene['scene_id'], 'question_id': scene['question_id'],
                         'source_object_ids': nodes, 'planned_range': [start, end],
                         'check': 'BOUND_OBJECT_LIFETIME_NOT_PERCEPTUAL_VISIBILITY'})
    # Validate source refs on beats too, rather than accepting an arbitrary common
    # token merely because its dictionary hashes match on both sides.
    for q in episode['questions']:
        for beat in q['narrative_beats']:
            for ref in beat['source_refs']:
                if asset_questions[ref['asset_id']] != q['question_id']:
                    raise ValueError('Cross-question beat reference')
                bound_value(bundles, ref)
    projected.pop('direction_sha', None)
    projected['direction_sha'] = sha(projected)
    return projected, {'scenes': evidence, 'beat_scenes_sha': sha(mapping),
                       'native_spec_sha': spec['spec_sha'], 'human_visibility': 'PENDING'}


def excerpt_boundaries(direction, voices):
    """24 fps picture cuts, preserving exact audio sample timing inside them."""
    scenes = {s['scene_id']: s for s in direction['scenes']}
    events = {e['scene_id']: e for e in direction['events']}
    fps = 24
    def frame(value):
        result = round(value * fps)
        if abs(result / fps - value) > 1e-6:
            raise ValueError('Picture boundary is not on a 24 fps frame')
        return result
    pure = [frame(t) for t in scenes['B06']['time_range']]
    # Complete A comparison tail; C preparation plus a two-second entry hold.
    context = [frame(events['B05']['compare_start']), frame(events['B07']['compare_start']) + 48]
    if context[1] >= frame(events['B07']['decision_start']):
        raise ValueError('Context must end before the next candidate decision')
    for bounds in (pure, context):
        for voice in voices:
            if voice['start'] < bounds[1] / fps and voice['end'] > bounds[0] / fps:
                if voice['start'] < bounds[0] / fps or voice['end'] > bounds[1] / fps + 1e-6:
                    raise ValueError('Excerpt boundary would truncate a frozen voice clip')
    return {'fps': fps, 'range_convention': 'zero_based_end_exclusive',
            'pure_original_frames': pure, 'context_original_frames': context,
            'pure_in_context_frames': [x - context[0] for x in pure],
            'voice_positions': [{'id': v['id'], 'original_start_sample_48k': round(v['start'] * 48000),
                                 'context_start_sample_48k': round((v['start'] - context[0] / fps) * 48000),
                                 'duration_samples_48k': round(v['duration'] * 48000)}
                                for v in voices if v['start'] >= context[0] / fps
                                and v['end'] <= context[1] / fps],
            'timing_basis': 'PLANNED_FROM_BOUND_BASELINE_NOT_NEW_MEDIA',
            'actual_new_media_mapping': 'UNAVAILABLE'}
