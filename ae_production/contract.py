"""Render structure is a checked visual projection, never a teaching interpretation."""
from copy import deepcopy
from pathlib import Path
import hashlib
from content_os.release import ae_contract, validate_package
from video_contracts import ROOT, pointer, read, sha, status_matches
from .layout import LayoutOverflow, pages, slots, subtitle_cues
from .platforms import resolve_profile,intersection

COMPONENTS = ('TEXT_HERO', 'TEXT_TITLE', 'TEXT_BODY', 'METHOD_TAG', 'QUESTION_CARD',
              'OPTION_CARD', 'OPTION_GROUP_GRID', 'EVIDENCE_TEXT', 'EVIDENCE_HIGHLIGHT',
              'DECISION_PATH', 'RELATION_ARROW', 'STOP_RULE_CARD', 'PROGRESS_MARKER',
              'SUBTITLE_LINE', 'SOURCE_TAG', 'CANDIDATE_VERDICT', 'FRAMEWORK_CARD', 'RELATION_COMPARE')
TEMPLATE = 'METHOD_DEMO_MASTER'


def template_path(version):
    names={'0.1.0':'method-demo-master.jsx','0.2.0':'method-demo-master-v0.2.jsx'}
    if version not in names: raise ValueError('Unsupported visual version')
    return ROOT/'ae/templates'/names[version]


def reference(package, path):
    return {'pointer': path, 'value_sha': sha(pointer(package, path))}


def build_contract(package, manifest, statuses, design=None, revision=1, _check=True, platform_profile=None):
    """Internal-only v0.1. Every scene, action, Stop and final-copy character is retained."""
    validate_package(package)
    if package['content']['content_scope']!='method_action_demo':
        raise ValueError('contract_change_proposal: METHOD_DEMO_MASTER supports method_action_demo only')
    if manifest['package_sha'] != sha(package) or manifest['package_id'] != package['package_id']:
        raise ValueError('Package Manifest binding mismatch')
    if manifest['final_copy_sha'] != package['copy_lock']['final_copy_sha']:
        raise ValueError('Manifest final copy binding mismatch')
    # Reuses upstream gates, without changing the input package or schema.
    ae_contract(package, statuses, internal=True)
    design = deepcopy(design or read(ROOT / 'ae/design/swiss-academic-motion.json'))
    version=design['version'];v02=version=='0.2.0'
    baseline=read(ROOT/('ae/design/swiss-academic-motion-v0.2.json' if v02 else 'ae/design/swiss-academic-motion.json'))
    template_path(version)
    frozen_keys=('canvas','grid','typography','motion','subtitles')+ (('colors','treatment','art_direction','cjk_typography','localized_labels') if v02 else ())
    if any(design[k]!=baseline[k] for k in frozen_keys):
        raise ValueError('Frozen design geometry / type scale / motion vocabulary changed')
    g = design['grid']; width = 1080 - 2*g['side_margin']
    profile=resolve_profile(platform_profile) if v02 else None
    core=intersection([g['side_margin'],g['top_safe'],width,g['content_bottom']-g['top_safe']],profile['safe_area_profile']['core']) if v02 else None
    if v02:width=core[2]
    subtitle_design=deepcopy(design)
    if v02:subtitle_design['subtitles']['width']=profile['caption_profile']['width']
    scenes, subtitles = [], []
    used_refs = {}
    def ref(path):
        r = reference(package, path); used_refs[path] = r; return r
    def component(kind, content, paths, bounds, token='Body', primitive='reveal'):
        if kind not in COMPONENTS: raise ValueError('Unknown component')
        m = design['motion']
        return {'component_type': kind, 'content': content, 'source_refs': [ref(p) for p in paths],
                'layout': slots(content.get('text', ''), bounds, token, design), 'style_token': token,
                'motion_primitive': {'type': primitive, 'duration_frames': m.get('rhythm_frames',{}).get(primitive,m['duration_frames']),
                                     'easing': m['easing'], 'delay_frames': m['delay_frames'], 'emphasis': 'information'}}
    bundles = {b['asset_id']: (i, b) for i, b in enumerate(package['source_items'])}
    claims = {c['claim_id']: c for c in package['claims']}
    selections = [s for s in package['selections'] if s.get('purpose') != 'challenge']
    methods = []
    for sel in selections:
        bi,b = bundles[sel['asset_id']]
        mi = next(i for i,m in enumerate(b['methods']) if m['method_id'] == sel['method_id'])
        si = next(i for i,m in enumerate(b['analysis']['method_chain']) if m['method_id'] == sel['method_id'])
        methods.append({'method_id': sel['method_id'], 'role': b['analysis']['method_chain'][si]['role'],
                        'brand': b['methods'][mi]['brand_name'],
                        'refs': [ref(f'/source_items/{bi}/methods/{mi}/brand_name'), ref(f'/source_items/{bi}/analysis/method_chain/{si}/role')]})
    for i,(scene, timing) in enumerate(zip(package['semantic_scenes'],package['timeline'])):
        base = f'/semantic_scenes/{i}'; text = scene['on_screen']['primary_text']
        reading_width=width-24 if v02 else width
        reading_token=('Hero' if v02 else 'Title') if scene['scene_type']=='HOOK' else ('Title' if v02 and scene['scene_type']=='METHOD_REVEAL' else 'Body')
        reading_height=824 if v02 and scene['scene_type']=='STOP_RULE' else 880
        chunks = pages(text, reading_width, reading_height, reading_token, design)
        variants = []
        visual = scene['method_visual']
        if visual:
            claim = claims[scene['claim_refs'][0]]; bi,b = bundles[claim['asset_id']]
            action_path = '/source_items/' + str(bi) + claim['action_artifact_refs'][0]['pointer']
            action = pointer(package,action_path)
            if visual['kind'] == 'candidate_partition':
                # Only the supplied axis is grouped. Never infer the other two classifications.
                cards = []
                for group in visual['groups']:
                    for cid in group['candidates']:
                        p=f'/source_items/{bi}/source_snapshot/options/{cid}'
                        cards.append((cid, pointer(package,p),p,group['label']))
                two_col = all(len(pages(t,(width-24)/2-56 if v02 else 408,236 if v02 else 192,'Body',design)) == 1 for _,t,_,_ in cards)
                limit = 6 if two_col else (3 if v02 else 4)
                for start in range(0,len(cards),limit):
                    subset = cards[start:start+limit]; comps=[]
                    label=visual['groups'][0]['label']
                    comps.append(component('OPTION_GROUP_GRID',{'text':label,'axis':visual['axis'],'groups':deepcopy(visual['groups'])},[base+'/method_visual'],[96,384 if v02 else 352,width,256]))
                    y=736 if v02 else 656
                    for n,(cid,t,p,_) in enumerate(subset):
                        cols=2 if two_col else 1; w=(width-24)/2 if cols==2 else width
                        xx=96+(n%cols)*(w+24); yy=y+(n//cols)*(240 if cols==2 else (224 if v02 else 192))
                        comps.append(component('OPTION_CARD',{'text':t,'candidate':cid},[p,base+'/method_visual'],[xx+56,yy,w-56,236 if v02 else 184],primitive='compare' if v02 else 'reveal'))
                    variants.append(('two-column' if two_col else 'single-column compact',comps))
            elif visual['kind'] == 'route_selection':
                # Node IDs and definitions are already frozen in the package's method card.
                method=next((m for m in b['methods'] if m['method_id']==claim['method_id']),None)
                mi=b['methods'].index(method); nodes=method.get('decision_tree',{}).get('nodes',[])
                if isinstance(nodes,dict): nodes=list(nodes.values())
                comps=[]
                for n,node_id in enumerate(visual['node_ids']):
                    ni=next((k for k,x in enumerate(nodes) if x.get('id')==node_id),None)
                    node=nodes[ni] if ni is not None else None
                    label=(node.get('label') or node.get('question') or node.get('name')) if node else node_id
                    paths=[base+'/method_visual']
                    # Labels not representable by an exact package pointer fall back to the ID.
                    nodebase=f'/source_items/{bi}/methods/{mi}/decision_tree/nodes/{ni}'
                    if node and isinstance(method.get('decision_tree',{}).get('nodes'),list):
                        key=next((k for k in ('label','question','name') if node.get(k)==label),None)
                        if key: paths.append(nodebase+'/'+key)
                    else:
                        label=node_id
                        # Visual names are literal excerpts from frozen cards / the bound action.
                        formula=method.get('visual_formula','')
                        proposed={'entry':'空位','hint':'有提示词？','with_hint':'这个位置需要什么？','noun':'名词节点'}.get(node_id)
                        if proposed and proposed in formula:
                            label=proposed; paths.append(f'/source_items/{bi}/methods/{mi}/visual_formula')
                        elif proposed and proposed in action['concrete_action']:
                            label=proposed; paths.append(action_path+'/concrete_action')
                    terminal=n==len(visual['node_ids'])-1
                    comps.append(component('DECISION_PATH',{'text':label,'node_id':node_id,'terminal':terminal},paths,[160,(448+n*192) if v02 else (352+n*232),width-64 if v02 else 760,136 if v02 else 160],token='Title' if v02 and terminal else 'Body',primitive='connect'))
                variants=[('vertical-path',comps)]
                evs=[('/source_items/'+str(bi)+r['pointer'],pointer(b,r['pointer'])) for r in claim['evidence_refs']]
                evs=[(p,v['span']['quote']) for p,v in evs if v.get('type')=='source_evidence']
                if evs:
                    ep,quote=max(evs,key=lambda e:len(e[1]))
                    proof=component('EVIDENCE_HIGHLIGHT',{'text':quote},[ep+'/span/quote'],[96,448,reading_width,768] if v02 else [96,1280,width,160],primitive='focus')
                    if v02:variants=[('bound-evidence',[proof]),('terminal-path',comps)]
                    else:comps.append(proof)
            elif visual['kind'] == 'candidate_decision':
                # The relation is referenced by the action's own index; no withdrawn review lookup.
                relations=b['analysis'].get('candidate_relations',[])
                if not relations: relations=b['analysis'].get('relations',[])
                idx=visual.get('relation_index'); comps=[]
                if idx is not None and idx < len(relations):
                    rp=f'/source_items/{bi}/analysis/' + ('candidate_relations' if 'candidate_relations' in b['analysis'] else 'relations') + f'/{idx}'
                    relation=relations[idx]
                    for n,(key,value) in enumerate(relation.items()):
                        if isinstance(value,str) and key not in ('candidate','method_id','id','relation_id','effect'):
                            for chunk in pages(value,width,384,'Body',design):
                                comps.append(component('RELATION_COMPARE',{'text':''.join(chunk),'field':key},[rp+'/'+key,base+'/method_visual'],[96,352,width,384],primitive='compare'))
                if not comps and '→' in action['concrete_action']:
                    import re
                    raw=action['concrete_action']
                    chains=re.findall(r'(?:画出|再对照)([^，；。]+→[^，；。]+)',raw)
                    if chains:
                        for row,chain in enumerate(chains[:2]):
                            cells=chain.split('→'); cw=(width-48)/3-8 if v02 else (width-96)/len(cells)
                            for col,value in enumerate(cells):
                                if row==1 and col==0 and value.startswith(visual['candidate']+'的'):
                                    value=value[len(visual['candidate'])+1:]
                                comps.append(component('RELATION_COMPARE',{'text':value,'row':row,'column':col,'chain_length':len(cells)},
                                    [action_path+'/concrete_action',base+'/method_visual'],[96+col*((width+24)/3 if v02 else (cw+48)),(480+row*512) if v02 else (416+row*384),cw,(448 if row==0 else 288) if v02 else 304],primitive='compare'))
                        variants.append(('relation-slots',comps+[component('CANDIDATE_VERDICT',{'text':text,'candidate':visual['candidate'],'effect':visual['effect'],'whole_question_answer':False},[base+'/method_visual',base+'/on_screen/primary_text'],[96,1360 if v02 else 1216,width,96 if v02 else 128],token='Metadata' if v02 else 'Body',primitive='eliminate')]))
                        evs=[('/source_items/'+str(bi)+r['pointer'],pointer(b,r['pointer'])) for r in claim['evidence_refs']]
                        evs=[(p,v['span']['quote']) for p,v in evs if v.get('type')=='source_evidence' and 'pianist' in v['span']['quote']]
                        if evs:
                            ep,quote=max(evs,key=lambda e:len(e[1]))
                            proof=[('bound-evidence',[component('EVIDENCE_HIGHLIGHT',{'text':''.join(ch)},[ep+'/span/quote'],[96,400,width,880],primitive='focus')]) for ch in pages(quote,width,880,'Body',design)]
                            variants=proof+variants
                        comps=[]
                if not comps and not variants:
                    # Exact action text is the bounded relation source, preserved without interpretation.
                    for chunk in pages(action['concrete_action'],width,768,'Body',design):
                        comps.append(component('RELATION_COMPARE',{'text':''.join(chunk),'relation_index':idx},[action_path+'/concrete_action',base+'/method_visual'],[96,352,width,768],primitive='compare'))
                for cmp in comps:
                    verdict=component('CANDIDATE_VERDICT',{'text':text,'candidate':visual['candidate'],'effect':visual['effect'],'whole_question_answer':False},[base+'/method_visual',base+'/on_screen/primary_text'],[96,1216,width,128],primitive='eliminate')
                    variants.append(('bounded-relation',[cmp,verdict]))
            elif visual['kind'] == 'framework_card':
                for f in visual['fields']:
                    variants.append(('framework-card',[component('FRAMEWORK_CARD',{'text':f['name']+'：'+f['value'],'field':f},[base+'/method_visual'],[96,352,width,880])]))
            else: raise ValueError('contract_change_proposal: unsupported typed output')
        else:
            kind={'HOOK':'TEXT_HERO','EVIDENCE':'EVIDENCE_TEXT','STOP_RULE':'STOP_RULE_CARD','METHOD_REVEAL':'TEXT_TITLE','QUESTION':'QUESTION_CARD'}.get(scene['scene_type'],'TEXT_BODY')
            token=reading_token if v02 else ('Title' if scene['scene_type'] in ('HOOK','METHOD_REVEAL') else 'Body')
            if v02 and kind=='TEXT_HERO':
                import re
                pauses=[m.end() for m in re.finditer('[：，；。]',text) if 6<=m.end()<=22]
                split=pauses[0] if pauses else (text.find('谁 →') if '谁 →' in text and 6<=text.find('谁 →')<=22 else None)
                if split and len(pages(text[:split],reading_width,352,'Hero',design))==1:
                    variants=[('literal-chinese-entry',[component(kind,{'text':text[:split]},[base+'/on_screen/primary_text'],[96,448,reading_width,352],'Hero'),component('TEXT_BODY',{'text':text[split:]},[base+'/on_screen/primary_text'],[96,824,reading_width,568],'Body')])]
                else:variants=[('reading-card',[component(kind,{'text':''.join(chunk)},[base+'/on_screen/primary_text'],[96,448,reading_width,880],token)]) for chunk in chunks]
            else:variants=[('stop-moment' if v02 and kind=='STOP_RULE_CARD' else 'reading-card',[component(kind,{'text':''.join(chunk)},[base+'/on_screen/primary_text'],[96,512 if v02 and kind=='STOP_RULE_CARD' else 400,reading_width,reading_height],token)]) for chunk in chunks]
        span=timing['end']-timing['start']
        if len(variants)>1 and span/len(variants)<2:
            raise LayoutOverflow('layout_overflow: insufficient scene duration for pages')
        for n,(variant,comps) in enumerate(variants):
            start=timing['start']+span*n/len(variants); end=timing['start']+span*(n+1)/len(variants)
            sid=scene['scene_id']+':page:'+str(n+1)
            for j,c in enumerate(comps):
                c['component_id']=sid+':'+str(j)
                if v02:c['layout']['x']+=core[0]-96
            scenes.append({'scene_id':sid,'package_scene_id':scene['scene_id'],'scene_type':scene['scene_type'],
                           'start':start,'end':end,'layout_variant':variant,'components':comps,
                           'claim_refs':deepcopy(scene['claim_refs']),'evidence_refs':deepcopy(scene['evidence_refs']),
                           'semantic_payload_sha':sha(scene),'spoken_text':scene['spoken_text'],
                           'typed_output':deepcopy(visual)})
        cues=subtitle_cues(scene['spoken_text'],timing['start'],timing['end'],scene['scene_id'],subtitle_design)
        for cue in cues: cue['source_ref']=ref(base+'/spoken_text')
        subtitles.extend(cues)
    template_sha=hashlib.sha256(template_path(version).read_bytes()).hexdigest()
    identity={'package_sha':sha(package),'design_sha':sha(design),'template_version':version,'template_sha':template_sha,'revision':revision}
    if v02:identity['projection_sha']=sha({'scenes':scenes,'subtitles':subtitles,'methods':methods,'source_tags':package['source_display']['attribution_text'],'platform_profile':profile})
    result={'schema_version':'0.1.0','render_id':'render:'+sha(identity),'package_id':package['package_id'],
            'package_sha':sha(package),'manifest_sha':sha(manifest),'final_copy_sha':package['copy_lock']['final_copy_sha'],
            'usage':'INTERNAL_ENGINEERING_PREVIEW','public_render_ready':False,
            'canvas':{**design['canvas'],'duration':package['production']['actual_estimated_duration'],'safe_area':deepcopy(g)},
            'design_system_version':design['version'],'design_sha':sha(design),'design':design,
            'template_family':TEMPLATE,'template_version':version,'template_sha':template_sha,'revision':revision,'methods':methods,
            'scenes':scenes,'subtitles':subtitles,'source_tags':package['source_display']['attribution_text'],
            'projection_refs':list(used_refs.values()),'upstream_bindings':{b['asset_id']:b['semantic_binding_sha'] for b in package['source_items']},
            'status_input_shas':{k:sha(v) for k,v in statuses.items()},
            'render_profile':{'fps':30,'voiceover':'text_timed_no_recording','watermark':True,'silent_preview':True}}
    if v02:
        result.update(platform_profile=profile,actual_content_area=core,cover_candidate={'hook_text':scenes[0]['components'][0]['content']['text'],'method_name':methods[0]['brand'],'focal_scene_id':scenes[0]['scene_id']})
        from .visual_qa import projection_qa
        projection_qa(result)
    if _check: validate_contract(result,package,manifest,statuses)
    return result


def validate_contract(contract,package,manifest,statuses):
    """Revalidate before every AE dispatch: old snapshot permits replay, never current render."""
    from jsonschema import Draft202012Validator
    Draft202012Validator(read(ROOT/'ae/schemas/render-contract.json')).validate(contract)
    validate_package(package)
    if contract['package_sha']!=sha(package) or contract['manifest_sha']!=sha(manifest) or manifest['package_sha']!=sha(package):
        raise ValueError('Render input hash mismatch')
    if contract['design_sha']!=sha(contract['design']): raise ValueError('Design hash mismatch')
    if any(not status_matches(b,statuses.get(b['asset_id'],{})) for b in package['source_items']):
        raise ValueError('Upstream no longer current')
    if package['invalidation']['teaching_stale'] or package['pilot_status']['engineering']!='PASS':
        raise ValueError('Package stale or not engineering eligible')
    for r in contract['projection_refs']:
        if sha(pointer(package,r['pointer']))!=r['value_sha']: raise ValueError('Visual source reference drift')
    for original,timing in zip(package['semantic_scenes'],package['timeline']):
        rendered=[s for s in contract['scenes'] if s['package_scene_id']==original['scene_id']]
        if not rendered or rendered[0]['start']!=timing['start'] or rendered[-1]['end']!=timing['end']:
            raise ValueError('Scene coverage lost')
        if any(a['end']!=b['start'] for a,b in zip(rendered,rendered[1:])): raise ValueError('Scene timing gap')
        if any(s['semantic_payload_sha']!=sha(original) or s['typed_output']!=original['method_visual'] or s['spoken_text']!=original['spoken_text'] for s in rendered):
            raise ValueError('Semantic visual projection drift')
        cues=[s for s in contract['subtitles'] if s['scene_id']==original['scene_id']]
        if ''.join(s['text'] for s in cues)!=original['spoken_text']: raise ValueError('Voiceover lost')
        if original['method_visual'] is None and ''.join(c['content']['text'] for s in rendered for c in s['components'])!=original['on_screen']['primary_text']:
            raise ValueError('Screen copy lost')
    expected=build_contract(package,manifest,statuses,contract['design'],contract['revision'],_check=False,platform_profile=contract.get('platform_profile'))
    # New current manifests may carry new envelope timestamps; all visual projection stays exact.
    expected['status_input_shas']=contract['status_input_shas']
    if expected!=contract: raise ValueError('Render projection changed outside the builder')
    return True
