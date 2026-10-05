"""Visual specification binding. This registry has no teaching authority."""
from video_contracts import ROOT, read, sha

DIRECTORY = ROOT / 'creative/motion-identity'
CREATIVE_DIMENSIONS = ('Composition', 'Shot Variety', 'Graphic Continuity', 'Typography',
    'Motion Richness', 'Effect Restraint', 'Temporal Contrast', 'Depth', 'Human Voice',
    'AI Feel', 'Sound Rhythm', 'Cinematic Flow', 'Teaching Clarity',
    'Signature recognizability', 'Method-motion fidelity', 'Brand grammar consistency',
    'Mnemonic clarity', 'Motion distinctiveness', 'Motion-to-teaching alignment')


def registry():
    grammar = read(DIRECTORY / 'brand-motion-grammar.json')
    signatures = read(DIRECTORY / 'method-signatures.json')
    if any(r.get('authority') != 'visual_metaphor_only' for r in (grammar, signatures)):
        raise ValueError('Motion registry cannot supply teaching facts')
    forbidden = {'answer', 'answer_key', 'evidence', 'stop_rule', 'trigger',
                 'teaching_facts', 'applicability', 'teaching_review'}
    def inspect(value):
        if isinstance(value, dict):
            if forbidden & set(value):
                raise ValueError('Teaching fact fields are forbidden in the motion registry')
            for child in value.values(): inspect(child)
        elif isinstance(value, list):
            for child in value: inspect(child)
    inspect(grammar); inspect(signatures)
    return grammar, signatures


def bind_identity(method_id, phases, brand_motion, carry_node_id):
    grammar, signatures = registry()
    signature = next(s for s in signatures['signatures'] if s['method_id'] == method_id)
    if method_id != 'G01' or signature['production_status'] != 'hero_pilot_only':
        raise ValueError('V9.1 produces G01 Hero only; other methods are specifications')
    if [p['phase'] for p in phases] != signature['required_phases']:
        raise ValueError('Signature phases missing or reordered')
    if any(p['end'] <= p['start'] for p in phases) or any(a['end'] > b['start'] for a,b in zip(phases, phases[1:])):
        raise ValueError('Signature phase overlap/order invalid')
    if not set(brand_motion) <= {g['id'] for g in grammar['grammar']}:
        raise ValueError('Unknown brand grammar')
    return {'method_id': method_id, 'signature_id': signature['signature_id'],
            'phases': phases, 'brand_motion': brand_motion, 'carry_node_id': carry_node_id,
            'grammar_sha': sha(grammar), 'signatures_sha': sha(signatures),
            'scope': 'visual_motion_specification_not_teaching_certification',
            'recognition_review': 'PENDING_human_memory_test'}


def validate_identity(identity, nodes, units, duration):
    expected = bind_identity(identity['method_id'], identity['phases'],
                             identity['brand_motion'], identity['carry_node_id'])
    if expected != identity:
        raise ValueError('Motion registry changed; new visual revision required')
    if any(u['method_id'] != identity['method_id'] for u in units.values()):
        raise ValueError('Signature method differs from frozen claim bindings')
    carry = next(n for n in nodes if n['node_id'] == identity['carry_node_id'])
    if len(carry.get('tracks', {}).get('position', [])) < 2:
        raise ValueError('Semantic Carry requires the same moving object')
    if any(p['start'] < 0 or p['end'] > duration for p in identity['phases']):
        raise ValueError('Signature phase outside the Hero')


def identity_shot_plan(contract, excerpt):
    identity=contract['design']['motion_identity'];units=excerpt['units']
    validate_identity(identity,contract['nodes'],{u['unit_id']:u for u in units},contract['canvas']['duration'])
    shots=[]
    for i,phase in enumerate(identity['phases']):
        selected=units[:1] if phase['phase']=='extract' else (units[:2] if phase['phase']=='route' else units[1:])
        shots.append({'shot_id':'hero-'+phase['phase'],
            'semantic_scene_id':selected[0]['scene_id'],
            'source_claim_refs':sorted({r for u in selected for r in u['source_claim_refs']}),
            'start':0 if i==0 else phase['start'],
            'end':contract['canvas']['duration'] if i==len(identity['phases'])-1 else phase['end'],
            'signature_motion':{'method_id':identity['method_id'],'signature_id':identity['signature_id'],
                                'phase':phase['phase']},
            'brand_motion':{'extract':['evidence_develop','focus_breathing','semantic_carry','magnetic_alignment'],
                            'route':['semantic_carry','magnetic_alignment','micro_lock'],
                            'seal':['micro_lock','boundary_seal']}[phase['phase']],
            'effects':{'structural':'bound geometry, masks and persistent object movement',
                       'depth':['focus separation','motion blur'],'accent':[]}})
    return {'render_contract_sha':contract['render_contract_sha'],'shots':shots,
            'preferred_transition':'logic_match_cut','human_direction':'PENDING',
            'public_render_ready':False}


def creative_review(contract, copy_lock, video_sha, observations):
    if set(observations)!=set(CREATIVE_DIMENSIONS) or any(not str(v).strip() for v in observations.values()):
        raise ValueError('All creative and recognition dimensions need explicit observations')
    return {'render_contract_sha':contract['render_contract_sha'],'copy_lock':copy_lock,
            'video_sha':video_sha,'reviewer_kind':'ai_host','independent':False,
            'dimensions':{k:{'observation':observations[k],'human_status':'PENDING'} for k in CREATIVE_DIMENSIONS},
            'direction_status':'READY_FOR_HUMAN_DIRECTION_REVIEW',
            'human_taste_review':'PENDING','public_render_ready':False}
