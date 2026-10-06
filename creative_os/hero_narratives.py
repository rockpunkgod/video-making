"""Alternative spatial narratives; typography is not a teaching identity.

Input remains a validated Hero. Every protected text fragment retains its
unit binding and order; only visual presentation and reading time change.
"""
from copy import deepcopy

from .hero import build_contract, validate_contract


DIRECTIONS = {
    'G_SOURCE_NOTES': ('原文批注', '#F5F1E8', '#272D29', '#697367'),
    'H_SINGLE_FOCUS': ('单焦点叙事', '#FAFAF7', '#182A35', '#789AAA'),
    'I_EVIDENCE_COMPARE': ('证据对照', '#EEF2F1', '#23312E', '#7F9B8C'),
}


def make_narrative(base, direction, package, manifest, statuses, full, excerpt, revision):
    validate_contract(base, package, manifest, statuses, full, excerpt)
    name, background, ink, accent = DIRECTIONS[direction]
    design = deepcopy(base['design'])
    # These proposals deliberately do not claim the registered extract/route/seal signature.
    design.pop('motion_identity', None)
    design.update(id=direction, name=name, background=background, ink=ink,
                  secondary='#64716C', accent=accent,
                  composition=direction, narrative_version='0.1.0',
                  motion_grammar='source_annotation' if direction.startswith('G_') else
                  'successive_focal_fields' if direction.startswith('H_') else 'persistent_evidence_and_boundary')
    nodes = [deepcopy(n) for n in base['nodes'] if n['kind'] == 'text']
    required = {'HOOK', 'FUNCTION', 'NOUN_NODE', 'STOP_EVENT', 'METHOD_STAMP', 'METHOD_ID',
                'EVIDENCE_PREFIX', 'EVIDENCE_FOLLOW', 'EVIDENCE_YOUR', 'EVIDENCE_BLANK',
                'EVIDENCE_GUIDE', 'EVIDENCE_TIME', 'BOUNDARY_FORM', 'BOUNDARY_GERUND',
                'BOUNDARY_G09', 'BOUNDARY_G09_ITEMS', 'BOUNDARY_HINT'}
    if {n['node_id'] for n in nodes} != required:
        raise ValueError('Narrative requires the exact validated Hero text roles')
    layouts = {
        'HOOK': (144, 120, 54, 0, 3.25),
        'EVIDENCE_PREFIX': (144, 270, 46, .5, 14.75),
        'EVIDENCE_FOLLOW': (144, 352, 64, .5, 14.75),
        'EVIDENCE_YOUR': (350, 352, 64, .5, 14.75),
        'EVIDENCE_BLANK': (545, 352, 60, .5, 14.75),
        'EVIDENCE_GUIDE': (930, 352, 54, .5, 14.75),
        'EVIDENCE_TIME': (1160, 352, 46, .5, 14.75),
        'FUNCTION': (545, 475, 54, 3.25, 9.25),
        'NOUN_NODE': (144, 610, 68, 5.25, 9.25),
        'STOP_EVENT': (555, 625, 46, 6, 9.25),
        'METHOD_STAMP': (144, 780, 30, 7.25, 14.75),
        'METHOD_ID': (320, 780, 30, 7.25, 14.75),
        'BOUNDARY_FORM': (144, 485, 64, 9.25, 14.75),
        'BOUNDARY_GERUND': (545, 495, 48, 9.25, 14.75),
        'BOUNDARY_G09': (144, 625, 34, 9.75, 14.75),
        'BOUNDARY_G09_ITEMS': (365, 625, 34, 9.75, 14.75),
        'BOUNDARY_HINT': (545, 785, 32, 10.25, 14.75),
    }
    if direction == 'H_SINGLE_FOCUS':
        for key in list(layouts):
            if key.startswith('EVIDENCE_'):
                x,y,size,start,_ = layouts[key]
                layouts[key] = (x,y+40,size,start,5.25)
        layouts.update(HOOK=(144,120,64,0,3.25), FUNCTION=(760,525,76,3.25,5.25),
                       NOUN_NODE=(670,300,148,5.25,9.25), STOP_EVENT=(740,545,78,6,9.25),
                       METHOD_STAMP=(780,755,32,7.25,9.25), METHOD_ID=(974,755,32,7.25,9.25),
                       BOUNDARY_FORM=(740,225,110,9.25,14.75),
                       BOUNDARY_GERUND=(565,430,72,9.25,14.75),
                       BOUNDARY_G09=(335,645,36,9.75,14.75),
                       BOUNDARY_G09_ITEMS=(555,645,36,9.75,14.75),
                       BOUNDARY_HINT=(580,765,38,10.25,14.75))
    elif direction == 'I_EVIDENCE_COMPARE':
        layouts.update(HOOK=(128,120,54,0,3.25),
                       EVIDENCE_PREFIX=(128,285,40,.5,14.75),
                       EVIDENCE_FOLLOW=(128,375,56,.5,14.75),
                       EVIDENCE_YOUR=(325,375,56,.5,14.75),
                       EVIDENCE_BLANK=(128,470,54,.5,14.75),
                       EVIDENCE_GUIDE=(480,475,44,.5,14.75),
                       EVIDENCE_TIME=(128,610,40,.5,14.75),
                       FUNCTION=(960,255,74,3.25,9.25),
                       NOUN_NODE=(960,440,100,5.25,9.25), STOP_EVENT=(960,620,56,6,9.25),
                       METHOD_STAMP=(128,780,30,7.25,14.75), METHOD_ID=(315,780,30,7.25,14.75),
                       BOUNDARY_FORM=(960,265,80,9.25,14.75),
                       BOUNDARY_GERUND=(960,405,48,9.25,14.75),
                       BOUNDARY_G09=(960,550,36,9.75,14.75),
                       BOUNDARY_G09_ITEMS=(960,630,27,9.75,14.75),
                       BOUNDARY_HINT=(960,770,32,10.25,14.75))
    for n in nodes:
        key = n['node_id']
        x,y,size,start,end = layouts[key]
        for field in ('tracks', 'reveal', 'opacity', 'effects'):
            n.pop(field, None)
        n.update(position=[x,y], size=size, tracking=0, color=ink, in_point=start, out_point=end,
                 motion_blur=False, effects={'structural': [{'kind':'reading_order',
                 'reason':'Expose bound information at its spoken phase; hold the source in place'}],
                 'depth':[], 'accent':[]})
        n['tracks'] = {'opacity': [[start,0], [start+.5,100]]}
        if key.startswith('EVIDENCE_'):
            n['font'] = 'Georgia' if direction == 'G_SOURCE_NOTES' else 'NotoSansSC-Regular'
        if key in ('METHOD_STAMP','METHOD_ID','BOUNDARY_G09','BOUNDARY_G09_ITEMS','BOUNDARY_HINT'):
            n['color'] = design['secondary']
    def rule(identity,position,size,start):
        return {'node_id':identity,'kind':'shape','position':position,'size':size,'fill':accent,
                'in_point':start,'out_point':14.75,'motion_blur':False,
                'tracks':{'opacity':[[start,0],[start+.5,100]]},
                'effects':{'structural':[{'kind':'reading_field','reason':'Separate evidence and judgment without implying a solution'}], 'depth':[], 'accent':[]}}
    if direction == 'G_SOURCE_NOTES':
        nodes.insert(0,rule('ANNOTATION_UNDERLINE',[726,433],[360,3],3.25))
    elif direction == 'I_EVIDENCE_COMPARE':
        nodes.insert(0,rule('EVIDENCE_DIVIDER',[842,490],[2,640],0))
    beats=[{'start':0,'end':8,'phase':'READ'}, {'start':8,'end':9.25,'phase':'HOLD'},
           {'start':9.25,'end':11.25,'phase':'READ'}, {'start':11.25,'end':14.75,'phase':'HOLD'}]
    return build_contract(package,manifest,statuses,full,excerpt,design,nodes,beats,14.75,revision)


def main():
    import argparse
    from pathlib import Path
    from video_contracts import read, write
    parser = argparse.ArgumentParser(description='Prepare three bound spatial narratives')
    parser.add_argument('request')
    request = read(parser.parse_args().request)
    root = Path(request['output'])
    if root.exists():
        raise ValueError('Use a new narrative revision; preserve prior artifacts')
    base = read(request['base_contract'])
    args = [read(request[k]) for k in ('package','manifest')]
    args += [{k:read(v) for k,v in request['statuses'].items()},
             read(request['full_delivery']),read(request['excerpt'])]
    variants = [make_narrative(base,d,*args,request['revision']) for d in DIRECTIONS]
    for direction,contract in zip(DIRECTIONS,variants):
        write(root / direction / 'render-contract.json',contract)
    print('Prepared three bound narrative alternatives; human review pending')


if __name__ == '__main__':
    main()
