"""Visual alternatives over an already validated frozen Hero.

Only presentation changes. Text, claim/unit ownership, phase timings and
settle distances remain inherited; each result goes through the full gate.
"""
from copy import deepcopy

from .hero import build_contract, validate_contract


def make_direction(base, profile, package, manifest, statuses, full, excerpt, revision):
    validate_contract(base, package, manifest, statuses, full, excerpt)
    design = deepcopy(base['design'])
    design.update({k: deepcopy(profile[k]) for k in
                   ('id', 'name', 'background', 'ink', 'secondary', 'accent', 'latin_font', 'composition')})
    design['direction_profile'] = deepcopy(profile)
    nodes = deepcopy(base['nodes'])
    old_ink = base['design']['ink']
    main_ids = {'SLOT_CARRY', 'NOUN_NODE', 'STOP_EVENT', 'METHOD_STAMP', 'METHOD_ID',
                'FORWARD_STOP', 'SEAL_UPPER', 'SEAL_LOWER'}
    evidence_ids = {n['node_id'] for n in nodes if n['node_id'].startswith('EVIDENCE_')}
    for node in nodes:
        identity = node['node_id']
        if node['kind'] == 'text':
            node['color'] = profile['ink'] if node['color'] == old_ink else profile['secondary']
            if identity in evidence_ids:
                node['font'] = profile['latin_font']
            if identity == 'HOOK':
                node['size'] = profile['hook_size']
            elif identity == 'NOUN_NODE':
                node['size'] = profile['noun_size']
            elif identity == 'STOP_EVENT':
                node['size'] = profile['stop_size']
        elif node.get('fill'):
            node['fill'] = profile['accent']

        def offset_at(time):
            if identity.startswith('BOUNDARY_'):
                return profile['boundary_offset']
            if identity in main_ids:
                if identity in {'METHOD_STAMP', 'METHOD_ID'}:
                    return [profile['main_offset'][0], 0]
                # Source underline must stay aligned with the source until extraction.
                return ([0, 0] if identity == 'SLOT_CARRY' and time <= 3.25
                        else profile['main_offset'])
            if identity in evidence_ids or identity == 'EVIDENCE_DEVELOP':
                # Retain extracted objects in the same shifted spatial field.
                return (profile['main_offset'] if identity in
                        {'EVIDENCE_BLANK', 'EVIDENCE_FOLLOW', 'EVIDENCE_YOUR'} and time >= 4.05
                        else profile.get('evidence_offset', [0, 0]))
            if identity == 'FUNCTION':
                return profile['main_offset'] if time >= 6 else [0, 0]
            return [0, 0]

        dx, dy = offset_at(0)
        node['position'] = [node['position'][0] + dx, node['position'][1] + dy]
        for time_value in node.get('tracks', {}).get('position', []):
            dx, dy = offset_at(time_value[0])
            time_value[1] = [time_value[1][0] + dx, time_value[1][1] + dy]
        if identity in {'EVIDENCE_FOLLOW', 'EVIDENCE_YOUR'}:
            # Clear the extraction lane before the moving blank crosses it.
            # The faint retained source remains, but has already settled above.
            for name in ('position', 'scale', 'opacity'):
                for key in node.get('tracks', {}).get(name, []):
                    if key[0] == 4.25:
                        key[0] = 3.55
        if identity == 'FUNCTION' and profile.get('margin_rule'):
            node['position'][0] += 48
            for key in node.get('tracks', {}).get('position', []):
                if key[0] < 6:
                    key[1][0] += 48
        # Move the initial underline with the initial evidence in the blueprint.
        if identity == 'SLOT_CARRY' and profile.get('evidence_offset'):
            dx, dy = profile['evidence_offset']
            node['position'][0] += dx
            node['position'][1] += dy
            for time_value in node['tracks']['position']:
                if time_value[0] <= 3.25:
                    time_value[1][0] += dx
                    time_value[1][1] += dy

    def graphic(identity, position, size, fill, reason):
        return {'node_id': identity, 'kind': 'shape', 'position': position, 'size': size,
                'fill': fill, 'motion_blur': False,
                'effects': {'structural': [{'kind': 'reading_field', 'reason': reason}],
                            'depth': [], 'accent': []}}
    if profile.get('caption_footer'):
        # Added first: later text/shape layers stay above this static reading surface.
        height = profile.get('caption_footer_height', 200)
        nodes.insert(0, graphic('CAPTION_READING_SURFACE', [960, 1080 - height / 2], [1920, height],
                                '#F2F0EA', 'Retain contrast for the unchanged native dark subtitles'))
    if profile.get('margin_rule'):
        rule = graphic('MARGIN_RULE', [1048, 560], [1, 600],
                       '#CCC4B8', 'Separate route and bound margin notes after source extraction')
        start, end = profile.get('margin_rule_reveal', [4.25, 4.75])
        rule['in_point'] = start
        rule['tracks'] = {'opacity': [[start, 0], [end, 100]]}
        nodes.insert(0, rule)
    return build_contract(package, manifest, statuses, full, excerpt, design, nodes,
                          base['beats'], base['canvas']['duration'], revision)


def main():
    import argparse
    from pathlib import Path
    from video_contracts import read, write
    parser = argparse.ArgumentParser(description='Generate frozen Hero visual alternatives')
    parser.add_argument('request')
    request = read(parser.parse_args().request)
    root = Path(request['output'])
    if root.exists():
        raise ValueError('Use a new direction revision; do not overwrite history')
    profiles = read(request['profiles'])['directions']
    ids = [p['id'] for p in profiles]
    if not ids or len(ids) != len(set(ids)) or any(
            not identity or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in identity)
            for identity in ids):
        raise ValueError('Unique safe direction IDs required')
    args = [read(request[k]) for k in ('package', 'manifest')]
    args += [{k: read(v) for k, v in request['statuses'].items()},
             read(request['full_delivery']), read(request['excerpt'])]
    base = read(request['base_contract'])
    # Validate every result before creating any output directory.
    variants = [make_direction(base, profile, *args, request['revision']) for profile in profiles]
    for identity, contract in zip(ids, variants):
        write(root / identity / 'render-contract.json', contract)
    print('Prepared', len(variants), 'frozen visual alternatives')


if __name__ == '__main__':
    main()
