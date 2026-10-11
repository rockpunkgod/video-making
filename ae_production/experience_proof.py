"""Read-only checks for authored editorial proxies, not a director or renderer.

Lexical ranges locate existing text. They do not grant semantic annotation rights
or certify whether a viewer understands the comparison.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

from ae_production.candidate_motion import audit_candidate_events
from content_os.candidates import engineering_gate, source_gate
from video_contracts import pointer, read, sha, status_matches, write
from video_contracts.passage import require_current


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def checked_reference(ref, bundle):
    if ref['asset_id'] != bundle['asset_id']:
        raise ValueError('Cross-asset reference')
    value = pointer(bundle, ref['pointer'])
    if sha(value) != ref['sha']:
        raise ValueError('Changed frozen reference')
    return value


def check_objects(objects, bundle):
    identities = set()
    for obj in objects:
        if obj['id'] in identities:
            raise ValueError('Duplicate visual identity')
        identities.add(obj['id'])
        source = checked_reference(obj['source_ref'], bundle)
        start, end = obj['range']
        if (not isinstance(source, str) or type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(source) or source[start:end] != obj['text']):
            raise ValueError('Displayed text must be an exact frozen range')
        if not obj['authority_refs']:
            raise ValueError('Missing explicit display/action authority')
        for ref in obj['authority_refs']:
            checked_reference(ref, bundle)


def check_method_binding(plan, bundle):
    methods = (bundle['payload']['methods'] if bundle.get('kind') == 'frozen_reviewed_passage'
               else bundle['methods'])
    matching = [m for m in methods if m['method_id'] == plan['method_id']]
    if (len(matching) != 1 or matching[0]['version'] != plan['method_version']
            or matching[0]['primary_role'] != plan['method_role']):
        raise ValueError('Frozen method version or role changed')
    if bundle.get('kind') != 'frozen_reviewed_passage':
        selection = plan['selection']
        if selection['asset_id'] != bundle['asset_id'] or selection['method_id'] != plan['method_id']:
            raise ValueError('Selected action and displayed method must share the binding')


def check_passage_decisions(events, bundle, question_id, answer=None):
    payload = bundle['payload']
    question = next(q for q in payload['questions'] if q['question_id'] == question_id)
    states, used, last = set(question['options']), set(), 0
    result = []
    for event in events:
        ref = event['source_ref']
        if not ref['pointer'].startswith('/payload/review/decisions/'):
            raise ValueError('Use existing upstream direct decisions')
        decision = checked_reference(ref, bundle)
        if (decision['question_id'] != question_id or decision['basis'] != 'direct_text_review'
                or decision['method_id'] is not None or ref['pointer'] in used):
            raise ValueError('Borrowed, relabelled or repeated direct judgement')
        times = [event[k] for k in ('compare_start', 'decision_start', 'decision_end', 'confirmation_start')]
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
                or not last <= times[0] < times[1] < times[2] <= times[3]):
            raise ValueError('Observe before judgement and confirmation')
        before = sorted(states)
        if decision['candidate'] not in states or decision['effect'] not in ('eliminate', 'retain'):
            raise ValueError('Invalid current candidate')
        if decision['effect'] == 'eliminate':
            states.remove(decision['candidate'])
        used.add(ref['pointer']); last = times[2]
        result.append({'decision_ref': ref, 'before': before, 'after': sorted(states)})
    if answer is not None:
        required = {f'/payload/review/decisions/{i}' for i, d in enumerate(payload['review']['decisions'])
                    if d['question_id'] == question_id}
        retained = {d['candidate'] for d in payload['review']['decisions']
                    if d['question_id'] == question_id and d['effect'] == 'retain'}
        if required != used or states != retained or states != {answer['candidate']} or answer['time'] < last:
            raise ValueError('Final answer needs all own direct comparisons')
    return result


def check_replays(plan, bundle):
    for replay in plan['replays']:
        if replay['kind'] != 'observation_only' or replay['before'] != replay['after']:
            raise ValueError('Replay cannot apply another judgement')
        checked_reference(replay['authority_ref'], bundle)
        start, end = replay['frame_range']
        if (type(start) is not int or type(end) is not int or
                not 0 <= start < end <= plan['frame_count']):
            raise ValueError('Replay needs a valid actual frame range')
        live = set(next(q['options'] for q in bundle['payload']['questions'] if q['question_id'] == plan['question_id'])
                   if bundle.get('kind') == 'frozen_reviewed_passage' else bundle['source_snapshot']['options'])
        for event in plan['candidate_events']:
            if start / plan['fps'] <= event['decision_start'] < end / plan['fps']:
                raise ValueError('Observation-only replay cannot contain a new candidate event')
            if event['decision_end'] <= start / plan['fps']:
                decision = checked_reference(event['source_ref'], bundle) if 'source_ref' in event else event
                if decision['effect'] == 'eliminate': live.remove(decision['candidate'])
        if replay['before'] != sorted(live):
            raise ValueError('Replay cannot revive an already excluded candidate')


def validate_proof(plan):
    if (plan['kind'] != 'experience_first_editorial_proxy' or plan['public_render_ready'] is not False
            or plan['human_experience_review'] != 'PENDING' or plan['native_glyph_certified'] is not False):
        raise ValueError('An editorial proxy cannot sign human or release acceptance')
    if plan['plan_sha'] != sha({k: v for k, v in plan.items() if k != 'plan_sha'}):
        raise ValueError('Authored plan changed')
    if ((plan['width'], plan['height'], plan['fps']) != (1920, 1080, 24)
            or type(plan['frame_count']) is not int or plan['frame_count'] <= 0):
        raise ValueError('This proof needs explicit 1080p24 frame bounds')
    for entry in plan['input_files']:
        if file_sha(entry['path']) != entry['sha256']:
            raise ValueError('Provided input changed: ' + entry['path'])
    bundle, status = read(plan['bundle_path']), read(plan['status_path'])
    check_method_binding(plan, bundle)
    if bundle.get('kind') == 'frozen_reviewed_passage':
        require_current(bundle, status)
        decisions = check_passage_decisions(plan['candidate_events'], bundle,
                                           plan['question_id'], plan.get('answer_event'))
    else:
        if not status_matches(bundle, status) or source_gate([bundle])['internal_use'] != 'PASS':
            raise ValueError('Current source not usable for internal proof')
        selection = plan['selection']
        if engineering_gate(bundle, selection, 'method_action_demo', status)['status'] != 'PASS':
            raise ValueError('Selected existing action is not eligible')
        if bundle['source_snapshot']['question_id'] != plan['question_id']:
            raise ValueError('Wrong question identity')
        decisions = audit_candidate_events(plan['candidate_events'], {bundle['asset_id']: bundle})['events']
        partition = plan.get('partition')
        if partition:
            action = checked_reference(partition['action_ref'], bundle)
            output = action['output']
            if output['kind'] != 'candidate_partition' or output['groups'] != partition['groups']:
                raise ValueError('Regrouping cannot invent or change frozen groups')
            ids = [c for group in partition['groups'] for c in group['candidates']]
            if len(ids) != len(set(ids)) or set(ids) != set(bundle['source_snapshot']['options']):
                raise ValueError('A partition must retain every original candidate exactly once')
        if plan.get('answer_event') is not None:
            raise ValueError('Bounded method samples do not acquire final-answer authority')
    check_objects(plan['objects'], bundle)
    check_replays(plan, bundle)
    return {'status': 'PASS', 'question_id': plan['question_id'], 'plan_sha': plan['plan_sha'],
            'candidate_states': decisions, 'partition': plan.get('partition'),
            'status_source': 'explicit_supplied_manifest_not_live_external_monitor',
            'native_glyph_certified': False, 'human_experience_review': 'PENDING',
            'public_render_ready': False}


def verify_media(plan, receipt):
    result = validate_proof(plan)
    movie = Path(receipt['path'])
    if receipt['plan_sha'] != plan['plan_sha'] or file_sha(movie) != receipt['sha256']:
        raise ValueError('Media/plan receipt changed')
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(movie)], text=True))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if (stream['width'], stream['height'], stream['avg_frame_rate'], int(stream['nb_read_frames'])) != (
            1920, 1080, '24/1', plan['frame_count']):
        raise ValueError('Proxy size, fps or decoded frame count mismatch')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(movie), '-f', 'null', '-'], check=True)
    return {**result, 'media': receipt, 'decode': 'PASS'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan'); parser.add_argument('--media-receipt'); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Use a new verification receipt')
    plan = read(args.plan)
    write(output, verify_media(plan, read(args.media_receipt)) if args.media_receipt else validate_proof(plan))
