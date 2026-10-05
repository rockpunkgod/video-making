"""Bound excerpts for V9.1; full delivery remains intact and replayable.

The hero is an explicitly scoped excerpt, not a full teaching solution. Binding
lint and AI host fidelity review never grant human or public approval.
"""
from copy import deepcopy
import hashlib
import re
from pathlib import Path

from video_contracts import ROOT, sha
from .delivery import semantic_guard, copy_sha, screen_sha

TEMPLATE = ROOT / 'ae/templates/cinematic-hero-v0.4.jsx'
VERSION = '0.4.0'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_excerpt(excerpt, full_delivery, package, manifest, statuses):
    semantic_guard(full_delivery, package, manifest, statuses)
    # Reuse every existing unit-level check without weakening full claim coverage.
    combined = deepcopy(excerpt)
    supplemental = deepcopy(full_delivery['units'])
    if set(u['unit_id'] for u in supplemental) & set(u['unit_id'] for u in excerpt['units']):
        raise ValueError('Excerpt unit IDs must be distinct from the full script')
    combined['units'] += supplemental
    combined['delivery_copy_sha'] = copy_sha(combined)
    combined['screen_copy_sha'] = screen_sha(combined)
    if excerpt['delivery_copy_sha'] != copy_sha(excerpt) or excerpt['screen_copy_sha'] != screen_sha(excerpt):
        raise ValueError('Excerpt copy drift')
    result = semantic_guard(combined, package, manifest, statuses)
    selected = {r for u in excerpt['units'] for r in u['source_claim_refs']}
    # Stop claims are mandatory even for a short action excerpt.
    required = {r for scene in package['semantic_scenes'] if scene['scene_type'] == 'STOP_RULE'
                for r in scene['claim_refs']}
    if not required <= selected:
        raise ValueError('Excerpt omits a frozen Stop Rule')
    return {'status': result['status'], 'scope': 'bounded_action_excerpt',
            'selected_claim_refs': sorted(selected),
            'omitted_claim_refs': sorted({c['claim_id'] for c in package['claims']} - selected),
            'full_solution': False, 'independent_human_certified': False}


def build_contract(package, manifest, statuses, full_delivery, excerpt, design, nodes, beats, duration, revision=1):
    scope = validate_excerpt(excerpt, full_delivery, package, manifest, statuses)
    if not 10 <= duration <= 15 or round(duration * 24) != duration * 24:
        raise ValueError('Hero must occupy 10–15 seconds on the 24fps grid')
    units = {u['unit_id']: u for u in excerpt['units']}
    if design.get('motion_identity'):
        from .motion_identity import validate_identity
        validate_identity(design['motion_identity'], nodes, units, duration)
    rendered_screen = {key: [] for key in units}
    if not nodes or len({n['node_id'] for n in nodes}) != len(nodes):
        raise ValueError('Unique visual nodes required')
    for node in nodes:
        if node['kind'] not in ('text', 'shape'):
            raise ValueError('Unknown native visual node kind')
        if node['kind'] == 'text':
            unit = units[node['unit_id']]
            sources = [unit['on_screen_copy']] + [e['text'] for e in unit['visual_excerpts']]
            if not node['text'] or not any(node['text'] in text for text in sources):
                raise ValueError('Screen text lacks its own bound unit/source excerpt')
            if not any(node['text'] in e['text'] for e in unit['visual_excerpts']):
                rendered_screen[node['unit_id']].append(node['text'])
        for group in ('structural', 'depth', 'accent'):
            if any(not e.get('reason') for e in node.get('effects', {}).get(group, [])):
                raise ValueError('Every effect requires a director reason')
        if len(node.get('effects', {}).get('accent', [])) > 1:
            raise ValueError('Accent budget exceeded')
        for track in node.get('tracks', {}).values():
            times = [k[0] for k in track]
            if times != sorted(set(times)) or any(t < 0 or t > duration for t in times):
                raise ValueError('Invalid motion timeline')
    compact = lambda text: re.sub(r'\s', '', text)
    if any(compact(''.join(rendered_screen[key])) != compact(unit['on_screen_copy'])
           for key, unit in units.items()):
        raise ValueError('Screen projection drops or rearranges protected copy fragments')
    if sum(len(n.get('effects', {}).get('accent', [])) for n in nodes) > 1:
        raise ValueError('Hero accent budget exceeded')
    if not beats or beats[0]['start'] != 0 or beats[-1]['end'] != duration:
        raise ValueError('Complete beat coverage required')
    for i, beat in enumerate(beats):
        if beat['end'] <= beat['start'] or (i and beats[i - 1]['end'] != beat['start']):
            raise ValueError('Beat gap/overlap')
    if not any(b['phase'] == 'HOLD' and b['end'] - b['start'] >= .5 for b in beats):
        raise ValueError('A genuine hold is mandatory')
    for beat in (b for b in beats if b['phase'] == 'HOLD'):
        for node in nodes:
            if node.get('out_point', duration) <= beat['start'] or node.get('in_point', 0) >= beat['end']:
                continue
            for track in node.get('tracks', {}).values():
                if any(a[1] != b[1] and a[0] < beat['end'] and b[0] > beat['start']
                       for a,b in zip(track, track[1:])):
                    raise ValueError('Declared HOLD contains changing motion')
            reveal = node.get('reveal')
            if reveal and reveal[0] < beat['end'] and reveal[1] > beat['start']:
                raise ValueError('Declared HOLD contains a reveal')
    contract = {
        'version': VERSION, 'revision': revision, 'usage': 'INTERNAL_CREATIVE_PREVIEW',
        'package_id': package['package_id'], 'package_sha': sha(package),
        'manifest_sha': sha(manifest), 'status_input_shas': {k: sha(v) for k, v in statuses.items()},
        'full_delivery_sha': sha(full_delivery), 'excerpt_sha': sha(excerpt),
        'scope': scope, 'canvas': {'width': 1920, 'height': 1080, 'fps': 24, 'duration': duration},
        'template_version': VERSION, 'template_sha': file_sha(TEMPLATE),
        'design': deepcopy(design), 'nodes': deepcopy(nodes), 'beats': deepcopy(beats),
        'copy_lock': {'final_copy_sha': sha([excerpt['delivery_copy_sha'], excerpt['screen_copy_sha']]),
                      'polished_from_sha': None, 'editorial_review_sha': None},
        'human_taste_review': 'PENDING', 'public_render_ready': False,
    }
    contract['render_contract_sha'] = sha(contract)
    return contract


def validate_contract(contract, package, manifest, statuses, full_delivery, excerpt):
    expected = build_contract(package, manifest, statuses, full_delivery, excerpt,
                              contract['design'], contract['nodes'], contract['beats'],
                              contract['canvas']['duration'], contract['revision'])
    # Historical status snapshots remain provenance. Current validity is checked
    # above through semantic_guard; metadata-only manifest refresh is not a new cut.
    expected.pop('render_contract_sha')
    expected['status_input_shas'] = contract['status_input_shas']
    expected['render_contract_sha'] = sha(expected)
    if contract != expected:
        raise ValueError('Production contract stale or altered')


def render_receipt(contract, shot_id, project, output, measured):
    if (measured['width'], measured['height'], measured['fps']) != (1920, 1080, 24):
        raise ValueError('Rendered media profile mismatch')
    if abs(measured['duration'] - contract['canvas']['duration']) > 1 / 24:
        raise ValueError('Rendered duration mismatch')
    return {'shot_id': shot_id, 'source_package_id': contract['package_id'],
            'render_contract_sha': contract['render_contract_sha'], 'template_version': VERSION,
            'ae_project_sha': file_sha(project), 'output_sha': file_sha(output),
            'duration': measured['duration'], 'fps': measured['fps'],
            'output_path': str(Path(output).resolve()), 'public_render_ready': False}


def validate_handoff(receipt, contract, project=None):
    if (receipt['render_contract_sha'] != contract['render_contract_sha']
            or receipt['source_package_id'] != contract['package_id']
            or receipt['template_version'] != VERSION
            or receipt['output_sha'] != file_sha(receipt['output_path'])):
        raise ValueError('AE render handoff stale or tampered')
    if project is not None and receipt['ae_project_sha'] != file_sha(project):
        raise ValueError('AE project changed after render')
    if receipt.get('public_render_ready') is not False:
        raise ValueError('Internal handoff cannot grant public approval')
    if receipt['fps'] != contract['canvas']['fps'] or abs(receipt['duration'] - contract['canvas']['duration']) > 1/24:
        raise ValueError('AE handoff timing/profile mismatch')


def require_approved_direction(review, contract):
    if (review.get('status') != 'APPROVED_DIRECTION' or review.get('reviewer_kind') != 'human'
            or not review.get('reviewer') or review.get('render_contract_sha') != contract['render_contract_sha']):
        raise ValueError('Full production requires copy/visual-bound human APPROVED_DIRECTION')


def main():
    import argparse
    from video_contracts import read, write
    parser = argparse.ArgumentParser()
    parser.add_argument('request')
    args = parser.parse_args()
    request = read(args.request)
    contract = build_contract(
        read(request['package']), read(request['manifest']),
        {key: read(path) for key, path in request['statuses'].items()},
        read(request['full_delivery']), read(request['excerpt']),
        request['design'], request['nodes'], request['beats'], request['duration'], request.get('revision', 1))
    write(request['output'], contract)
    print(contract['render_contract_sha'])


if __name__ == '__main__':
    main()
