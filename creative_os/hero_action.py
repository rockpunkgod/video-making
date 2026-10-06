"""Persistent source with bound, local annotation; no new teaching copy.

This layout consumes the reviewed consumer Hero roles. Its annotation references
identify visual targets, not an independent semantic certification.
"""
from copy import deepcopy

from .hero import build_contract, validate_contract


def make_action_hero(base, package, manifest, statuses, full, excerpt, revision):
    validate_contract(base, package, manifest, statuses, full, excerpt)
    nodes = [deepcopy(n) for n in base['nodes'] if n['kind'] == 'text']
    layouts = {
        'HOOK': (150, 65, 46, 0, 3.5),
        'EVIDENCE_PREFIX': (150, 155, 48, 0, 14.75),
        'EVIDENCE_FOLLOW': (150, 247, 72, 0, 14.75),
        'EVIDENCE_YOUR': (385, 247, 72, 0, 14.75),
        'EVIDENCE_BLANK': (625, 247, 68, 0, 14.75),
        'EVIDENCE_GUIDE': (1105, 255, 54, 0, 14.75),
        'EVIDENCE_TIME': (1360, 255, 46, 0, 14.75),
        'FUNCTION': (590, 405, 64, 3.5, 14.75),
        'NOUN_NODE': (150, 555, 88, 5.5, 9.25),
        'STOP_EVENT': (760, 565, 70, 6.5, 9.25),
        'METHOD_STAMP': (150, 760, 46, 7.25, 9.25),
        'BOUNDARY_FORM': (150, 555, 76, 9.25, 14.75),
        'BOUNDARY_GERUND': (750, 575, 54, 9.25, 14.75),
        'BOUNDARY_G09': (150, 700, 46, 9.75, 14.75),
        'BOUNDARY_G09_ITEMS': (420, 700, 46, 9.75, 14.75),
        'BOUNDARY_HINT': (150, 810, 46, 10.25, 14.75),
    }
    if {n['node_id'] for n in nodes} != set(layouts):
        raise ValueError('Persistent action requires the exact consumer Hero roles')
    design = deepcopy(base['design'])
    design.pop('motion_identity', None)
    design.update(id='J_SOURCE_ACTION', name='原句拆解', audience='consumer',
                  background='#FAF8F2', ink='#243530', secondary='#64716C',
                  accent='#527B65', motion_grammar='persistent_source_local_annotation',
                  narrative_version='0.2.0')
    for n in nodes:
        x, y, size, start, end = layouts[n['node_id']]
        for field in ('tracks', 'reveal', 'opacity', 'effects'):
            n.pop(field, None)
        source = n['node_id'].startswith('EVIDENCE_')
        n.update(position=[x, y], size=size, tracking=0,
                 font='Georgia' if source else 'NotoSansSC-Regular',
                 color=design['ink'], in_point=start, out_point=end,
                 motion_blur=False)
        if not source and start:
            n['tracks'] = {'opacity': [[start, 0], [start + .5, 100]]}
        if n['node_id'] in ('EVIDENCE_PREFIX', 'EVIDENCE_GUIDE', 'EVIDENCE_TIME', 'BOUNDARY_HINT'):
            n['color'] = design['secondary']
    by_id = {n['node_id']: n for n in nodes}
    graphics = []

    def line(identity, x, y, width, start, end, targets, thickness=4):
        # Width and center move together: the left endpoint stays on its source.
        graphics.append(dict(
            node_id=identity, kind='shape', position=[x, y], size=[1, thickness],
            fill=design['accent'], in_point=start, out_point=14.75, motion_blur=False,
            annotation_refs=targets,
            unit_refs=sorted({by_id[t]['unit_id'] for t in targets}),
            tracks={'width': [[start, [1, thickness]], [end, [width, thickness]]],
                    'position': [[start, [x, y]], [end, [x + (width - 1)/2, y]]]},
            effects={'structural': [{'kind': 'source_annotation',
                      'reason': 'Draw on the retained bound source; preserve its identity and reading order'}],
                     'depth': [], 'accent': []}))

    line('BLANK_CUE', 625, 323, 425, .5, 1.0, ['EVIDENCE_BLANK'])
    line('FOLLOW_CUE', 150, 333, 195, 1.75, 2.25, ['EVIDENCE_FOLLOW'])
    line('YOUR_CUE', 385, 333, 150, 2.5, 3, ['EVIDENCE_YOUR'])
    line('OBJECT_GROUP', 385, 360, 665, 3, 3.5,
         ['EVIDENCE_YOUR', 'EVIDENCE_BLANK', 'FUNCTION'], 3)
    for identity, x in [('GROUP_LEFT', 385), ('GROUP_RIGHT', 1050)]:
        graphics.append(dict(node_id=identity, kind='shape', position=[x, 351],
            size=[3, 18], fill=design['accent'], in_point=3.5, out_point=14.75,
            annotation_refs=['EVIDENCE_YOUR', 'EVIDENCE_BLANK'],
            tracks={'opacity': [[3.5, 0], [3.75, 100]]}, motion_blur=False))
    graphics.append(dict(node_id='GROUP_TO_FUNCTION', kind='shape', position=[718, 378],
        size=[3, 36], fill=design['accent'], in_point=3.5, out_point=14.75,
        annotation_refs=['EVIDENCE_YOUR', 'EVIDENCE_BLANK', 'FUNCTION'],
        tracks={'opacity': [[3.5, 0], [4, 100]]}, motion_blur=False))
    line('STOP_ANCHOR', 150, 674, 1040, 7, 7.5, ['NOUN_NODE', 'STOP_EVENT'], 3)
    graphics[-1]['out_point'] = 9.25
    beats = [{'start': 0, 'end': 8, 'phase': 'READ'},
             {'start': 8, 'end': 9.25, 'phase': 'HOLD'},
             {'start': 9.25, 'end': 11.25, 'phase': 'READ'},
             {'start': 11.25, 'end': 14.75, 'phase': 'HOLD'}]
    return build_contract(package, manifest, statuses, full, excerpt, design,
                          graphics + nodes, beats, 14.75, revision)


def main():
    import argparse
    from pathlib import Path
    from video_contracts import read, write
    parser = argparse.ArgumentParser(description='Prepare a persistent-source consumer Hero')
    parser.add_argument('request')
    request = read(parser.parse_args().request)
    output = Path(request['output'])
    if output.exists():
        raise ValueError('Preserve existing revision; choose a new output')
    result = make_action_hero(read(request['base_contract']), read(request['package']),
        read(request['manifest']), {k:read(v) for k,v in request['statuses'].items()},
        read(request['full_delivery']), read(request['excerpt']), request['revision'])
    write(output, result)
    print('Persistent-source contract prepared; human direction review pending')


if __name__ == '__main__':
    main()
