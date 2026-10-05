"""Shot choreography projected from bound delivery and already reviewed typed outputs."""
from copy import deepcopy
from video_contracts import ROOT, read, sha, pointer
from .delivery import semantic_guard, human_voice_critic
from .timing import validate_track, captions
from ae_production.layout import slots

VERSION = '0.1.0'


def build_shot_plan(package, manifest, statuses, delivery, track, design=None):
    semantic_guard(delivery, package, manifest, statuses); validate_track(track, delivery)
    if human_voice_critic(delivery)['status'] == 'AI_TONE_WARNING': raise ValueError('AI tone needs revision')
    ds = deepcopy(design or read(ROOT/'ae/design/swiss-cinematic-editorial-v0.3.json'))
    registered = read(ROOT/'ae/design/swiss-cinematic-editorial-v0.3.json')
    if {k: v for k, v in ds.items() if k != 'font'} != {k: v for k, v in registered.items() if k != 'font'}:
        raise ValueError('Versioned landscape design drift')
    bundles = {b['asset_id']: b for b in package['source_items']}; frozen = {s['scene_id']: s for s in package['semantic_scenes']}
    shots = []; source_display = []
    def text(cid, text, rect, token, refs, evs, level='micro', mode='reveal'):
        return {'component_id': cid, 'kind': 'TEXT', 'text': text, 'layout': slots(text, rect, token, ds),
                'source_claim_refs': deepcopy(refs), 'evidence_refs': deepcopy(evs),
                'motion': {'level': level, 'mode': mode}}
    for u, t in zip(delivery['units'], track['units']):
        sid = 'shot:'+u['unit_id']; b = bundles[u['asset_id']]; action = pointer(b, u['action_artifact_refs'][0]['pointer'])
        output = deepcopy(action['output']); refs = u['source_claim_refs']; evs = u['evidence_refs']; components = []
        intent = u['intent']; phases = ['establish', 'reveal', 'focus', 'settle', 'hold', 'exit']
        structure = None
        if intent == 'regroup':
            if output['kind'] != 'candidate_partition': raise ValueError('Regroup needs a reviewed partition')
            # This pilot deliberately consumes only its selected producing action, never other bundle actions.
            ids = [cid for g in output['groups'] for cid in g['candidates']]
            if len(ids) > 7 or len(output['groups']) != 1: raise ValueError('contract_change_proposal: regroup supports one bound group up to seven')
            components.append(text(sid+':heading', u['on_screen_copy'], [144,176,1632,192], 'Title', refs, evs))
            cards = []
            for i, cid in enumerate(ids):
                xx=144+(i%4)*420; yy=408+(i//4)*216
                extracts = [e for e in u['visual_excerpts'] if e.get('candidate') == cid]
                label = ' / '.join(e['text'] for e in extracts)
                cards.append({'candidate': cid, 'label': label, 'excerpts': extracts,
                              'from': [144+i*220,430], 'to': [xx,yy], 'start_offset': 0.7+i*0.055})
                components.append(text(sid+':candidate:'+cid, cid, [xx,yy,96,112], 'Title', refs, evs, 'structural', 'regroup'))
                if label: components.append(text(sid+':verb:'+cid,label,[xx+112,yy+20,496 if i==6 else 284,224],'Body',refs,evs,mode='after_settle'))
                source_display.extend(deepcopy(extracts))
            structure = {'kind': 'regroup', 'typed_output': output, 'cards': cards, 'group_label': output['groups'][0]['label'],
                         'settle_offset': 2.2, 'single_axis_only': True}
            phases = ['establish_identity_universe', 'reveal_axis', 'reflow_into_one_group', 'focus_no_discrimination', 'settle', 'hold', 'hard_cut']
        elif intent == 'routing':
            if output['kind'] != 'route_selection': raise ValueError('Routing needs bound route output')
            route = output['node_ids']
            # Labels are literal fragments of the same bound concrete action, not Registry lookups.
            label_rules = {'entry': '当前空', 'hint': '提示', 'with_hint': '未填结构', 'noun': '名词'}
            known = {'entry': '空位', 'hint': '有提示词', 'with_hint': '这个空需要什么？', 'noun': '名词节点'}
            if any(n not in known or label_rules[n] not in action['concrete_action'] for n in route):
                raise ValueError('contract_change_proposal: route label lacks bound concrete action')
            components.append(text(sid+':heading',u['on_screen_copy'],[144,184,1632,192],'Title',refs,evs))
            nodes=[]
            for i,n in enumerate(route):
                xx=144+i*420;nodes.append({'node_id':n,'label':known[n],'x':xx,'y':496,'activation_offset':.35+i*.7,'terminal':i==len(route)-1})
                components.append(text(sid+':node:'+n,known[n],[xx,496,360,192],'Title' if i==len(route)-1 else 'Body',refs,evs,'structural','routing'))
            structure={'kind':'routing','typed_output':output,'nodes':nodes,'settle_offset':3.25,'close_forward_space':True,'answer_produced':False}
            phases=['establish_empty_slot','expand_route','activate_nodes','lock_current_terminal','close_forward_space','hold','graphic_match_to_stop']
        elif intent == 'rewire':
            if output['kind'] != 'candidate_decision':raise ValueError('Rewire needs a bounded candidate decision')
            # Reuse the already frozen V8 relation projection: it binds exact substrings of concrete_action.
            from ae_production.contract import build_contract
            old=build_contract(package,manifest,statuses)
            relation=[c for s in old['scenes'] for c in s['components'] if c['component_type']=='RELATION_COMPARE']
            if not relation:raise ValueError('contract_change_proposal: no frozen relation operands')
            components.append(text(sid+':heading',u['on_screen_copy'],[144,160,1632,192],'Title',refs,evs))
            cells=[]
            for c in relation:
                row=c['content']['row']; col=c['content']['column'];xx=144+col*560;yy=384+row*248
                label=c['content']['text'];cells.append({'row':row,'column':col,'text':label,'x':xx,'y':yy,
                    'from_y':yy-(248 if row==1 else 0),'entry_offset':.25+col*.25+(2.2 if row==1 else 0)})
                components.append(text(sid+':relation:'+str(row)+':'+str(col),label,[xx,yy,512,216],'Body',refs,evs,'structural','rewire'))
            structure={'kind':'rewire','typed_output':output,'cells':cells,'slot_labels':['谁','做什么','对谁'],
                       'candidate':output['candidate'],'effect':output['effect'],'whole_question_answer':False,
                       'shift_offset':3.8,'settle_offset':4.65,'displacement_px':6}
            phases=['establish_source_relation','connect','overlay_candidate_relation','isolate_changed_connection','rewire_local_connection','settle_bounded_verdict','hold']
        elif intent == 'evidence' and u['visual_excerpts']:
            components.append(text(sid+':heading',u['on_screen_copy'],[144,168,1632,192],'Title',refs,evs))
            for i,e in enumerate(u['visual_excerpts']):
                if i>1:raise ValueError('Evidence shot overloaded')
                components.append(text(sid+':evidence:'+str(i),e['text'],[144+i*840,424,792,384],'Body',refs,[e['ref']],mode='evidence_focus'))
                source_display.append(deepcopy(e))
        else:
            token='Hero' if intent=='hook' else ('Title' if intent in ('stop','boundary','method') else 'Body')
            components.append(text(sid+':copy',u['on_screen_copy'],[144,288,1536,512],token,refs,evs))
            if intent in ('stop','boundary'):phases=['carry_forward_current_state','lock_boundary','settle','silence_hold','hard_cut']
        hold_from=max(1,structure['settle_offset'] if structure else .75)
        if t['end']-t['start'] < hold_from+.65:raise ValueError('Shot too short for choreography and stable reading')
        shots.append({'shot_id':sid,'unit_id':u['unit_id'],'scene_id':u['scene_id'],'intent':intent,
                      'start':t['start'],'end':t['end'],'voice_end':t['voice_end'],'phases':phases,
                      'hold_start':t['start']+hold_from,'exit':'graphic_match' if intent=='routing' else 'hard_cut',
                      'components':components,'structure':structure,'source_claim_refs':deepcopy(refs),
                      'evidence_refs':deepcopy(evs),'semantic_payload_sha':sha(frozen[u['scene_id']])})
    caption_cues=captions(delivery,track,ds)
    displayed_text={'components':[{'id':c['component_id'],'text':c['text']} for s in shots for c in s['components']],
                    'captions':[{'id':c['cue_id'],'text':c['text']} for c in caption_cues],
                    'method_tags':[{'method_id':sel['method_id'],
                        'brand_name':next(m['brand_name'] for m in bundles[sel['asset_id']]['methods'] if m['method_id']==sel['method_id']),
                        'role':next(s['role'] for s in bundles[sel['asset_id']]['analysis']['method_chain'] if s['method_id']==sel['method_id'])}
                        for sel in package['selections']]}
    return {'version':VERSION,'profile':'CINEMATIC_LANDSCAPE','design':ds,'design_sha':sha(ds),
            'delivery_copy_sha':delivery['delivery_copy_sha'],'screen_copy_sha':delivery['screen_copy_sha'],
            'teaching_semantic_sha':delivery['teaching_semantic_sha'],'audio_timing_sha':track['audio_timing_sha'],
            'duration':track['duration'],'shots':shots,'captions':caption_cues,
            'source_display':{'excerpts':source_display,'displayed_text':displayed_text,'displayed_text_sha':sha(displayed_text),
                              'display_projection_sha':sha({'design':ds,'shots':shots,'captions':caption_cues}),
                              'displayed_image_sha':sha([]),'attribution_text':package['source_display']['attribution_text'],
                              'release_review_id':None},'public_render_ready':False}
