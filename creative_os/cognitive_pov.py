"""Swiss Cognitive POV: attention drives one continuous source space.

Only the object-slot routing pilot is implemented. The six physics families are
an extensible vocabulary, not six semantic solvers or a stock animation library.
"""
from collections import defaultdict
from copy import deepcopy

from video_contracts import sha
from video_contracts.method_application import require_current_application
from .hero import validate_excerpt, file_sha
from .semantic_text_layout import layout_words, bind_words

VERSION = '0.1.0'
PHYSICS = {
    'navigation': ['scan', 'jump', 'anchor', 'lock'],
    'reduction': ['peel', 'mute', 'tighten', 'reveal', 'restore'],
    'comparison': ['align', 'overlay', 'split', 'reveal_difference'],
    'relationship': ['connect', 'detach', 'rewire', 'lock'],
    'classification': ['float', 'attract', 'regroup', 'settle'],
    'routing': ['extract', 'branch', 'route', 'seal'],
}
PAPER = '#FAF8F2'; INK = '#243530'; ACCENT = '#527B65'; MUTED = '#77827A'


def build_spec(application, bundle, status, package, manifest, statuses, full, excerpt, fonts):
    require_current_application(application, bundle, status)
    validate_excerpt(excerpt, full, package, manifest, statuses)
    p = application['payload']; annotation = p['annotation']; action = p['actual_action']
    if (action['output']['kind'] != 'route_selection'
            or action['output']['node_ids'][-1] != 'noun'):
        raise ValueError('This pilot implements a bound noun-node route only')
    by_span = {s['span_id']: s for s in annotation['spans']}
    roles = defaultdict(list)
    for s in annotation['spans']: roles[s['semantic_role']].append(s['span_id'])
    if any(len(roles[r]) != 1 for r in ('predicate', 'determiner', 'slot', 'hint')):
        raise ValueError('Object-slot pilot needs explicit predicate/determiner/slot/hint spans')
    if any(s['semantic_role'] not in ('context', 'temporal_clause')
           for s in annotation['spans'] if s['span_id'] in annotation['deferred_span_ids']):
        raise ValueError('Only explicitly reviewed context can leave the focal plane')
    if not any(r['from_span_id'] == roles['predicate'][0]
               and set(r['to_span_ids']) == {roles['determiner'][0], roles['slot'][0]}
               for r in annotation['relations']):
        raise ValueError('The object relation must come from the own upstream action')
    for unit in excerpt['units']:
        if (unit['asset_id'] != bundle['asset_id'] or unit['method_id'] != p['method']['method_id']
                or unit['role'] != action['role']
                or {'asset_id':bundle['asset_id'], 'pointer':'/analysis/execution_trace/'+str(annotation['action_index'])}
                   not in unit['action_artifact_refs']):
            raise ValueError('Copy borrows another method, action or asset')
    font_bindings = {key: {'path':str(path), 'sha256':file_sha(path)} for key,path in fonts.items()}
    source = p['question']['passage']; size = 46
    words = bind_words(layout_words(source, fonts['english'], size, 1560, 180, 160),
                       annotation['spans'],fonts['english'])
    selected = [w for w in words if w['span_id']]
    top = min(w['y'] for w in selected); bottom = max(w['y'] for w in selected)
    focus_y = (top + bottom) / 2
    # One optical axis, zero rotation. Z represents reading scope, not spectacle.
    camera = dict(zoom=1440, depth_of_field=False, rotation=[0,0,0],
        position=[[0,[960,(160+max(w['y'] for w in words))/2,-3100]],
                  [2.5,[960,(160+max(w['y'] for w in words))/2,-3100]],
                  [4.5,[960,focus_y,-1760]], [5.4,[960,focus_y,-1760]],
                  [6.9,[960,focus_y,-1320]], [9.8,[960,focus_y,-1320]],
                  [10.6,[960,focus_y,-1150]], [12.4,[960,focus_y,-1150]],
                  [14.0,[960,focus_y,-1860]], [20,[960,focus_y,-1860]]],
        focus_scope=[dict(start=0,end=2.5,scope='whole_task'),
                     dict(start=2.5,end=5.4,scope='bound_region'),
                     dict(start=5.4,end=9.8,scope='current_clause'),
                     dict(start=9.8,end=12.4,scope='object_relation'),
                     dict(start=12.4,end=20,scope='context_and_stop')])
    retained = [w for w in selected if w['span_id'] in annotation['reduced_span_ids']]
    from PIL import ImageFont
    font = ImageFont.truetype(fonts['english'],size); space = font.getlength(' ')
    core_width = sum(w['w'] for w in retained) + (len(retained)-1)*space
    cursor = 960-core_width/2; destinations={}
    for w in retained:
        destinations[w['start']] = [cursor,focus_y,0]; cursor += w['w']+space
    nodes=[dict(node_id='original-instruction',kind='text',space='screen',
        text=p['question']['stem'],field='stem',start=0,end=len(p['question']['stem']),span_id=None,
        size=26,font='NotoSansSC-Regular',color=INK,position=[100,45,0],
        in_point=0,out_point=3.0,tracks={'opacity':[[0,100],[2.5,100],[3.0,0]]})]
    static_lines=defaultdict(list)
    for word in words:
        if word['span_id'] is None:
            static_lines[word['line']].append(word); continue
        deferred = word['span_id'] in annotation['deferred_span_ids']
        initial=[word['x'],word['y'],0]; final=destinations.get(word['start'],
                    [word['x'],word['y']-24,430])
        nodes.append(dict(node_id='word-'+str(word['start']),kind='text',space='world',
            text=word['text'],field='passage',start=word['start'],end=word['end'],
            span_id=word['span_id'],size=size,font='Georgia',color=INK,
            position=initial,tracks={'position':[[0,initial],[7.3,initial],[9.3,final],
                                               [12.4,final],[14,initial],[20,initial]],
                'opacity':[[0,100],[7.3,100],[9.3,14 if deferred else 100],
                           [12.4,14 if deferred else 100],[14,100],[20,100]],
                'blur':[[0,0],[7.3,0],[9.3,7 if deferred else 0],
                        [12.4,7 if deferred else 0],[14,0],[20,0]]}))
    # Non-target runs are plain original text. Their source offsets are retained;
    # no scene clears or new infographic replaces the task.
    for line,ws in static_lines.items():
        runs=[]
        for w in ws:
            if not runs or source[runs[-1][-1]['end']:w['start']].strip(): runs.append([])
            runs[-1].append(w)
        for ri,run in enumerate(runs):
            start=run[0]['start']; end=run[-1]['end']
            nodes.append(dict(node_id='source-'+str(line)+'-'+str(ri),kind='text',space='world',
                text=source[start:end],field='passage',start=start,end=end,span_id=None,
                size=size,font='Georgia',color=INK,position=[run[0]['x'],run[0]['y'],0],
                tracks={'opacity':[[0,100],[2.5,100],[4.5,4],[14,4],[20,4]],
                        'position':[[0,[run[0]['x'],run[0]['y'],0]],
                                    [2.5,[run[0]['x'],run[0]['y'],0]],
                                    [4.5,[run[0]['x'],run[0]['y'],650]],
                                    [20,[run[0]['x'],run[0]['y'],650]]]}))
    screen=[]
    placements = [
        [(3.0,6.0,136,117,34),(9.7,12.4,710,708,60)],
        [(11.2,14.0,136,792,59),(12.3,14.0,136,865,38),(17.2,20,136,110,32)],
        [(14.0,20,136,760,54),(14.0,20,570,784,36),
         (14.7,20,136,851,34),(15.4,20,136,910,32)],
    ]
    if len(excerpt['units']) != 3:
        raise ValueError('The bounded route pilot expects its three existing copy units')
    for unit,positions in zip(excerpt['units'],placements):
        lines=unit['on_screen_copy'].splitlines()
        if len(lines)!=len(positions): raise ValueError('Frozen screen copy needs a new reviewed layout')
        for i,(text,place) in enumerate(zip(lines,positions)):
            start,end,x,y,fs=place
            screen.append(dict(node_id=unit['unit_id']+'-'+str(i),kind='text',space='screen',
                text=text,unit_id=unit['unit_id'],claim_refs=unit['source_claim_refs'],
                size=fs,font='NotoSansSC-Regular',color=ACCENT if i==0 else INK,
                position=[x,y,0],in_point=start,out_point=end,
                tracks={'opacity':[[start,0],[start+.25,100],[end,100]]}))
    # A source-bound relation grows directly under the tightened object group.
    objects = [w for w in retained if w['span_id'] in (roles['determiner'][0],roles['slot'][0])]
    left=min(destinations[w['start']][0] for w in objects)
    right=max(destinations[w['start']][0]+w['w'] for w in objects)
    relation=dict(node_id='object-relation',kind='line',space='world',position=[left,focus_y+20,0],
        width=right-left,stroke=3,color=ACCENT,relation_index=0,in_point=9.3,out_point=12.4,
        tracks={'width':[[9.3,0],[9.9,right-left],[12.4,right-left]]})
    events=[dict(start=2.5,end=4.5,operation='jump',family='navigation',targets=list(by_span)),
            dict(start=5.4,end=6.9,operation='anchor',family='navigation',targets=[roles['slot'][0]]),
            dict(start=7.3,end=9.3,operation='peel',family='reduction',targets=annotation['deferred_span_ids'],reversible=True),
            dict(start=7.3,end=9.3,operation='tighten',family='reduction',targets=annotation['reduced_span_ids']),
            dict(start=9.3,end=9.9,operation='connect',family='relationship',targets=[roles['determiner'][0],roles['slot'][0]]),
            dict(start=11.2,end=12.0,operation='route',family='routing',targets=[roles['slot'][0]],output=deepcopy(action['output'])),
            dict(start=12.4,end=14.0,operation='restore',family='reduction',targets=list(by_span),reversible=True)]
    spec=dict(version=VERSION,kind='swiss_cognitive_pov',profile='object_slot_routing',
        application_sha=application['semantic_binding_sha'],parent_asset_id=bundle['asset_id'],
        parent_semantic_sha=bundle['semantic_binding_sha'],source_sha=application['source_sha'],
        package_id=package['package_id'],manifest_sha=sha(manifest),
        copy_lock={'final_copy_sha':excerpt['delivery_copy_sha'], 'polished_from_sha':None,
                   'editorial_review_sha':None},canvas=dict(width=1920,height=1080,fps=24,duration=20),
        palette=dict(paper=PAPER,ink=INK,accent=ACCENT),fonts=font_bindings,camera=camera,
        nodes=nodes+screen+[relation],events=events,holds=[[0,2.5],[18,20]],
        original_first=True,reality_layer_persistent=True,full_solution=False,
        independent_human_certified=False,human_taste_review='PENDING',public_render_ready=False)
    spec['spec_sha']=sha(spec); return spec


def validate_spec(spec, application, bundle, status, package, manifest, statuses, full, excerpt):
    expected=build_spec(application,bundle,status,package,manifest,statuses,full,excerpt,
                        {k:v['path'] for k,v in spec['fonts'].items()})
    if spec != expected:
        raise ValueError('Cognitive motion specification, semantic targets or copy changed')
    return True
