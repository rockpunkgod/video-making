"""One frozen full-passage location P0; no solver, method certification or VO."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import run as relay
from ae_production.execution import mutation_call
from video_contracts import read,sha,write
from video_contracts.passage import require_current

HERE=Path(__file__).resolve().parent


def project(bundle,status,question_id,question_cue,hit_cue):
    require_current(bundle,status);p=bundle['payload']
    qi,q=next((i,q) for i,q in enumerate(p['questions']) if q['question_id']==question_id)
    si,segment=next((i,s) for i,s in enumerate(p['review']['segments'])
                    if s['question_id']==question_id and s['kind']=='action' and s['fidelity_reviewed'] is True)
    e=segment['evidence'][0];text=p['passage'];start=e['start'];end=e['end']
    if e['field']!='passage' or text[start:end]!=e['quote'] or not 0<=start<end<=len(text):
        raise ValueError('Location endpoint must be an exact already reviewed evidence span')
    qs=q['stem'].index(question_cue);hs=text.index(hit_cue,start,end)
    return {'asset_id':bundle['asset_id'],'semantic_binding_sha':bundle['semantic_binding_sha'],
        'passage':text,'passage_sha':sha(text),'question':q,'question_pointer':'/payload/questions/'+str(qi),
        'question_cue':{'start':qs,'end':qs+len(question_cue),'text':question_cue},
        'hit_cue':{'start':hs,'end':hs+len(hit_cue),'text':hit_cue},
        'evidence':e,'evidence_pointer':'/payload/review/segments/'+str(si)+'/evidence/0',
        'review_sha':sha(p['review']),'review_level':bundle['semantic_review'],'source_status':p['source'],
        'authority':'editorial_framing_of_existing_frozen_evidence_not_new_R12_action',
        'answer':None,'method_certification':False,'public_render_ready':False}


def direction():
    def row(kind,offset,duration,times,lift):
        result={'kind':kind,'start':offset,'end':offset+duration,
                **{k:[offset+a,offset+b] for k,(a,b) in zip(('target','overview','scan','hit','lock','settle'),times)},
                'lift':[offset+lift[0],offset+lift[1]]}
        result['hit_settle_end']=result['hit'][0]+(4/24 if kind=='fast' else 6/24)
        result['hit_flash']=[result['hit_settle_end']+1/24,result['hit'][1]]
        result['source_reveal_end']=result['overview'][0]+.25
        result['enter_start']=sum(result['overview'])/2
        return result
    return {'version':'0.2.6','decision_author':'astra_creative_advice','second_reviewer':'root',
        'duration':20,'rewind':[7,8], 'passes':[
            row('fast',0,7,[(0,.75),(.75,1.5),(1.5,3.75),(3.75,4.25),(4.25,4.75),(4.75,6)],(6,6.65)),
            row('guided',8,12,[(0,1.25),(1.25,2.5),(2.5,6.75),(6.75,7.5),(7.5,8.5),(8.5,10.5)],(10.5,11.5))],
        'path_rule':'every_actual_line_from_P1_to_hit_no_keyword_camera_before_acquire',
        'synthetic_handoff':False,'peeling':False,'candidate_comparison':False}


def make_request(output,bundle_path,status_path,question_id,question_cue,hit_cue):
    from PIL import ImageFont
    source=project(read(bundle_path),read(status_path),question_id,question_cue,hit_cue)
    ep='C:/Windows/Fonts/georgia.ttf';cp='C:/Windows/Fonts/NotoSansSC-VF.ttf'
    fonts={False:ImageFont.truetype(ep,24),True:ImageFont.truetype(cp,24)}
    words=[];lines=[];x=320;y=353;line=[];paragraph=0;cursor=0
    for i,m in enumerate(re.finditer(r'\S+',source['passage'])):
        gap=source['passage'][cursor:m.start()];chinese=bool(re.search(r'[\u3400-\u9fff]',m[0]));width=float(fonts[chinese].getlength(m[0]));space=float(fonts[False].getlength(' '))
        if '\n' in gap or x+width>1600:
            if line:lines.append({'id':len(lines),'paragraph':paragraph,'word_ids':line});line=[]
            y+=31.5+(8 if '\n' in gap else 0);x=320
            if '\n' in gap:paragraph+=1
        word={'id':'source-word-'+str(i),'start':m.start(),'end':m.end(),'text':m[0],
              'gap_before':gap,'text_sha':sha(m[0]),'chinese':chinese,'position':[x,y,0],'line':len(lines)}
        words.append(word);line.append(word['id']);x+=width+space;cursor=m.end()
    if line:lines.append({'id':len(lines),'paragraph':paragraph,'word_ids':line})
    target=[w for w in words if w['start']>=source['evidence']['start'] and w['end']<=source['evidence']['end']]
    hit=[w for w in target if w['start']>=source['hit_cue']['start'] and w['end']<=source['hit_cue']['end']]
    if not target or not hit or ' '.join(w['text'] for w in hit)!=source['hit_cue']['text']:
        raise ValueError('This P0 needs complete literal words for its supplied hit')
    lift={};x=180;y=420
    for w in target:
        width=float(fonts[w['chinese']].getlength(w['text']))*32/24
        if x+width>1750:y+=45;x=180
        lift[w['id']]=[x,y,-140];x+=width+float(fonts[False].getlength(' '))*32/24
    qtext=source['question']['stem'];cue=source['question_cue'];question_parts=[]
    for id,start,end in (('QUESTION_PREFIX',0,cue['start']),('QUESTION_KEYWORD',cue['start'],cue['end']),('QUESTION_SUFFIX',cue['end'],len(qtext))):
        question_parts.append({'id':id,'start':start,'end':end,'text':qtext[start:end],'text_sha':sha(qtext[start:end]),
                               'position':[150+float(ImageFont.truetype(ep,34).getlength(qtext[:start])),203]})
    r={'kind':'frozen_full_passage_location_visual_research','version':'0.2.14','source':source,
        'canvas':[3840,2160,24,20],'render_scale':2,
        'motion_profile':{'version':'0.1.0','camera_lag_frames':{'fast':1,'guided':2},
            'departure_depth':24,'background_delay_frames':{'fast':1,'guided':2},
            'foreground_scale_delay_frames':{'fast':2,'guided':3},
            'scan_carry_influence':22,'bounce':False,'extra_zoom':False,
            'foreground_background':'transparent','background_clear':'fade_out_during_reflow'},
        'bundle_path':str(bundle_path),'status_path':str(status_path),
        'bundle_file_sha':relay.file_sha(bundle_path),'status_file_sha':relay.file_sha(status_path),
        'words':words,'trailing_space':source['passage'][cursor:],'lines':lines,'target_ids':[w['id'] for w in target],
        'question_parts':question_parts,'mind_view':{'keyword_only_during_scan':True,'question_anchor':'original_reading_position',
            'no_paraphrase':True,'no_step_labels':True,'no_visible_scan_cursor':True},
        'hit_ids':[w['id'] for w in hit],'scan_line_ids':list(range(hit[-1]['line']+1)),
        'lift_positions':lift,'director':direction(),'font':{'english':'Georgia','chinese':'NotoSansSC-Regular'},
        'camera_style':{'zoom':1950,'scan_depth':-1500,'reading_offset':30,'camera_tilt_offset':220,
                        'aperture':{'overview':0,'scan':1600,'hit':800,'lock':360,'lift':30},
                        'overview_top':340,'overview_bottom':960,'reader_length':80,'reader_stroke':2,'reader_opacity':0,
                        'foreground_screen_y':420,'background_top':590,'background_bottom':945,
                        'background_z':220,'background_max_word_scale':.68},
        'viewport_guards':{'PAPER_TOP_GUARD':{'top':-80,'bottom':330,'feather':35},
                           'PAPER_FOOT_GUARD':{'top':970,'bottom':1160,'feather':30}},
        'font_shas':{'english':relay.file_sha(ep),'chinese':relay.file_sha(cp)},
        'question_cue_geometry':{'x':150+float(ImageFont.truetype(ep,34).getlength(source['question']['stem'][:source['question_cue']['start']])),
                                 'width':float(ImageFont.truetype(ep,34).getlength(question_cue))},
        'project':str(output/'FULLTEXT_LOCATION.aep'),'template_sha':relay.file_sha(HERE/'fulltext-build.jsx'),
        'human_visual_review':'PENDING','final_voice_accepted':False,'production_eligible':False,'public_render_ready':False}
    r['spec_sha']=sha({k:v for k,v in r.items() if k not in ('project','bundle_path','status_path')})
    validate(r);return r


def validate(r):
    source=r['source'];text=source['passage']
    if (r['canvas']!=[3840,2160,24,20] or r['render_scale']!=2 or r['director']!=direction()
            or r['spec_sha']!=sha({k:v for k,v in r.items() if k not in ('project','bundle_path','status_path','spec_sha')})
            or (r.get('version')!='0.2.8' and r.get('motion_profile')!={'version':'0.1.0','camera_lag_frames':{'fast':1,'guided':2},
                'departure_depth':24,'background_delay_frames':{'fast':1,'guided':2},
                'foreground_scale_delay_frames':{'fast':2,'guided':3},
                'scan_carry_influence':22,'bounce':False,'extra_zoom':False,
                **({'sentence_occlusion':'unadorned_bound_paper_plane','geometry_sampling':'96hz_lift_only',
                    'plane_depth_offset':20} if r.get('version')=='0.2.13' else {}),
                **({'foreground_background':'transparent','background_clear':'fade_out_during_reflow'} if r.get('version')=='0.2.14' else {})})
            or r.get('version') not in ('0.2.8','0.2.9','0.2.13','0.2.14')
            or source['answer'] is not None or source['method_certification'] is not False
            or any(r[k] is not False for k in ('final_voice_accepted','production_eligible','public_render_ready'))):
        raise ValueError('Only frozen-source visual location, without answer or release promotion')
    reconstructed=''.join(w['gap_before']+w['text'] for w in r['words'])+r['trailing_space']
    if reconstructed!=text or any(text[w['start']:w['end']]!=w['text'] or sha(w['text'])!=w['text_sha'] for w in r['words']):
        raise ValueError('Every word and whitespace in every original paragraph must survive')
    by_id={w['id']:w for w in r['words']}
    cue=source['question_cue'];qtext=source['question']['stem'];parts=r['question_parts']
    if (''.join(p['text'] for p in parts)!=qtext or [p['id'] for p in parts]!=['QUESTION_PREFIX','QUESTION_KEYWORD','QUESTION_SUFFIX']
            or any(qtext[p['start']:p['end']]!=p['text'] or sha(p['text'])!=p['text_sha'] for p in parts)
            or parts[1]['start']!=cue['start'] or parts[1]['end']!=cue['end'] or parts[1]['text']!=cue['text']):
        raise ValueError('Working-memory cue must be the same exact original-question span, never a new summary')
    if (len(by_id)!=len(r['words']) or [i for line in r['lines'] for i in line['word_ids']]!=list(by_id)
            or r['scan_line_ids']!=list(range(by_id[r['hit_ids'][-1]]['line']+1))):
        raise ValueError('The scan must start at the actual first line, never jump to evidence')
    if ({i for i,w in by_id.items() if source['evidence']['start']<=w['start']<w['end']<=source['evidence']['end']}!=set(r['target_ids'])
            or set(r['lift_positions'])!=set(r['target_ids'])
            or text[by_id[r['target_ids'][0]]['start']:by_id[r['target_ids'][-1]]['end']]!=source['evidence']['quote']
            or {i for i,w in by_id.items() if source['hit_cue']['start']<=w['start']<w['end']<=source['hit_cue']['end']}!=set(r['hit_ids'])):
        raise ValueError('Lift the complete existing condition, never a rewritten core')


def current(output):
    r=read(output/'request.json');validate(r)
    if (relay.file_sha(r['bundle_path'])!=r['bundle_file_sha'] or relay.file_sha(r['status_path'])!=r['status_file_sha']
            or relay.file_sha(output/'executed-template.jsx')!=r['template_sha']
            or project(read(r['bundle_path']),read(r['status_path']),r['source']['question']['question_id'],
                       r['source']['question_cue']['text'],r['source']['hit_cue']['text'])!=r['source']):
        raise ValueError('Frozen source or current provided status changed')
    return r


def validate_native(r,n):
    if n.get('background_cutouts'):raise ValueError('Original source glyphs must not acquire editorial masks')
    if r.get('motion_profile',{}).get('foreground_background')=='transparent' and any(p.get('sentence_occlusion') for p in n['passes']):
        raise ValueError('Extracted sentence must have no paper plane')
    """Compare actual Adobe readback with frozen words, spans and same-object poses."""
    if (n['spec_sha']!=r['spec_sha'] or n['canvas']!=r['canvas'] or len(n['words'])!=len(r['words'])
            or n['renderer']!='ADBE Advanced 3d' or n['draft3d'] is not False or n['resolution_factor']!=[1,1]
            or any(w['source_text_keys'] or w['font_size']!=24 or not w['threeD'] for w in n['words'])
            or len({w['layer_id'] for w in n['words']})!=len(n['words']) or n['temporary_probes'] or n['handles']!=n['initial_handles']
            or n['new_method_certification'] is not False or n['public_render_ready'] is not False
            or [p['kind'] for p in n['passes']]!=[p['kind'] for p in r['director']['passes']]
            or n['annotation_layers'] or n['visible_attention_cursor']
            or any(p['visited_lines']!=r['scan_line_ids'] or p['pre_hit_mark']!=0
                   or p['peak_hit_mark']<20 or p['hit_mark']!=0 or p['lift_handles']!=n['handles'] for p in n['passes'])):
        raise ValueError('Native full-passage search, source identity or lock failed')
    actual={w['id']:w for w in n['words']}
    if set(actual)!=set(w['id'] for w in r['words']):raise ValueError('Native source word identity differs')
    # AE expression values and spatial interpolation differ by < 0.02 world px
    # in this native readback. Only geometry permits 0.05 px; text/spans stay exact.
    close=lambda a,b:len(a)==len(b) and all(abs(x-y)<.05 for x,y in zip(a,b))
    scale=r['render_scale'];physical=lambda values:[v*scale for v in values]
    width,height=r['canvas'][:2];center=[width/2,height/2]
    guards=n['viewport_guards']
    if set(guards)!=set(r['viewport_guards']):raise ValueError('Missing native paper edge coverage')
    for name,expected in r['viewport_guards'].items():
        a=guards[name]
        vertices=[[0,expected['top']*scale],[width,expected['top']*scale],[width,expected['bottom']*scale],[0,expected['bottom']*scale]]
        if (len(a['vertices'])!=4 or any(not close(actual,expected_vertex) for actual,expected_vertex in zip(a['vertices'],vertices))
                or a['feather']!=[0,expected['feather']*scale] or a['mask_keys'] or a['feather_keys']
                or a['mask_count']!=1 or a['mask_add'] is not True or a['inverted'] is not False
                or a['mask_opacity']!=100 or a['layer_opacity']!=100 or a['enabled'] is not True
                or a['threeD'] is not False or a['parent'] is not None or a['rotation']
                or not close(a['position'][:2],center) or any(a['position'][2:])
                or not close(a['anchor'][:2],center) or any(a['anchor'][2:])
                or not close(a['scale'][:2],[100,100]) or a['size']!=[width,height]
                or not close(a['color'],[.973,.969,.949])):
            raise ValueError('Feathered viewport guards must extend beyond the frame without text returning at its edges')
    question={p['id']:p for p in r['question_parts']};native_question={p['id']:p for p in n['question_parts']}
    if set(question)!=set(native_question) or n['question_handles']!=n['initial_question_handles']:
        raise ValueError('The retained cue must preserve its original question identity')
    for id,p in question.items():
        a=native_question[id]
        if (any(a[k]!=p[k] for k in ('text','start','end','text_sha')) or a['source_text_keys']
                or a['font_size']!=34 or not close(a['scale'],[100*scale,100*scale,100])
                or not close(a['position'][:2],physical(p['position'])) or any(a['position'][2:])):
            raise ValueError('The mental anchor cannot paraphrase or replace the frozen question')
    if n['option_texts']!={id:id+'. '+text for id,text in r['source']['question']['options'].items()}:
        raise ValueError('Original options cannot be rewritten or silently removed')
    for w in r['words']:
        a=actual[w['id']]
        if (any(a[k]!=w[k] for k in ('text','start','end','text_sha')) or a['source_sha']!=r['source']['passage_sha']
                or not close(a['position'],physical(w['position'])) or not close(a['anchor'],[0,0,0])
                or not close(a['scale'],[100*scale]*3) or a['parent'] is not None
                or any(a[k] for k in ('rotation','x_rotation','y_rotation'))):
            raise ValueError('Native literal text, source span or initial transform differs')
    def box(ids,lift=False):
        low=[math.inf]*3;high=[-math.inf]*3
        for id in ids:
            a=actual[id];rect=a['rect'];pos=physical(r['lift_positions'][id]) if lift else a['position'];glyph_scale=(32/24 if lift else 1)*scale
            for j,(v,size) in enumerate(((rect['left'],rect['width']),(rect['top'],rect['height']),(0,0))):
                low[j]=min(low[j],pos[j]+v*glyph_scale);high[j]=max(high[j],pos[j]+(v+size)*glyph_scale)
        return {'min':low,'max':high,'center':[(x+y)/2 for x,y in zip(low,high)]}
    geom=n['geometry']
    for key,ids,lift in (('whole',list(actual),False),('hit',r['hit_ids'],False),('scope',r['target_ids'],False),('lifted',r['target_ids'],True)):
        b=box(ids,lift)
        if any(not close(b[k],geom[key][k]) for k in b):raise ValueError('Recorded geometry differs from actual native glyphs')
    if len(geom['line_boxes'])!=len(r['lines']):raise ValueError('Missing native line geometry')
    for line,b in zip(r['lines'],geom['line_boxes']):
        computed=box(line['word_ids'])
        if any(not close(computed[k],b[k]) for k in computed):raise ValueError('Native reading line differs')
    column=geom['whole']['center'][0]
    style={k:(v if k in ('background_max_word_scale','reader_opacity') else
              {a:b*scale for a,b in v.items()} if k=='aperture' else v*scale) for k,v in r['camera_style'].items()}
    whole=geom['whole'];lifted=geom['lifted'];foreground_scale=style['zoom']/((1980-140)*scale)
    lift_look=[lifted['center'][0],lifted['center'][1]+(center[1]-style['foreground_screen_y'])/foreground_scale,-140*scale]
    background_projection=style['zoom']/(1980*scale+style['background_z'])
    background_word_scale=min(style['background_max_word_scale'],(style['background_bottom']-style['background_top'])/
                              ((whole['max'][1]-whole['min'][1])*background_projection))
    background_origin=lift_look[1]+(style['background_top']-center[1])/background_projection
    for p in n['passes']:
        for phase,expected in (('initial',{'QUESTION_PREFIX':100,'QUESTION_KEYWORD':100,'QUESTION_SUFFIX':100}),
                               ('scan',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':60,'QUESTION_SUFFIX':0}),
                               ('before_lift',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':60,'QUESTION_SUFFIX':0}),
                               ('lifted',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':0,'QUESTION_SUFFIX':0})):
            state=p['mental_state'][phase]
            if state['question_opacity']!=expected or any(v!=(100 if phase=='initial' else 0) for v in state['option_opacity'].values()):
                raise ValueError('Scan may retain only the exact extracted cue; evidence takes over during Lift')
        c=p['camera']
        if (c['dof']!=1 or c['aperture']!=style['aperture']['hit'] or c['zoom']!=style['zoom'] or c['focus_error']
                or not math.isfinite(c['focus_distance']) or c['focus_distance']<=0
                or p['apertures']!=style['aperture']):
            raise ValueError('Actual native reading focus is unavailable')
        if p['lift_focus']['error'] or not close(p['lift_focus']['actual_sentence_center'],p['lift_focus']['focus']):
            raise ValueError('Lift focus must follow the actual moving sentence, not its future destination')
        if (not close(p['mark_position'],[geom['hit']['center'][0],geom['hit']['center'][1],scale])
                or not close(p['mark_size'],[geom['hit']['max'][0]-geom['hit']['min'][0]+8*scale,geom['hit']['max'][1]-geom['hit']['min'][1]+8*scale])
                or p['mark_strokes']!=0):
            raise ValueError('Keyword feedback must be the original brief filled highlight, never an underline')
        if len(p['scan_samples'])!=len(r['scan_line_ids']):raise ValueError('Missing actual line visits')
        for index,sample in zip(r['scan_line_ids'],p['scan_samples']):
            b=geom['line_boxes'][index]
            if (not close([sample['reader'][1]],[b['max'][1]+6*scale]) or not b['min'][0]-.01<=sample['reader'][0]<=b['max'][0]+.01
                    or not close([sample['camera'][0],sample['look'][0]],[column+20*scale,column])
                    or not close(sample['focus'],[sample['reader'][0]+style['reader_length']/2,b['center'][1],0])
                    or sample['reader_opacity']!=0):
                raise ValueError('Scan must follow actual reading rows, not jump the camera sideways to evidence')
            forward=[a-b for a,b in zip(sample['look'],sample['camera'])];distance=math.sqrt(sum(v*v for v in forward))
            expected_focus=sum((a-b)*v/distance for a,b,v in zip(sample['focus'],sample['camera'],forward))
            if abs(sample['focus_distance']-expected_focus)>.01 or sample['aperture']!=style['aperture']['scan']:
                raise ValueError('Native lens focus must follow the current reading point, not the future hit')
        if set(a['id'] for a in p['positions'])!=set(actual):raise ValueError('Missing original object poses')
        for a in p['positions']:
            selected=a['id'] in r['lift_positions'];initial=actual[a['id']]['position']
            expected=physical(r['lift_positions'][a['id']]) if selected else [column+(initial[0]-column)*background_word_scale,
                       background_origin+(initial[1]-whole['min'][1])*background_word_scale,style['background_z']]
            if (not close(a['initial'],initial) or not close(a['restored'],initial) or not close(a['at_lift'],expected)
                    or a['pre_hit_opacity']!=100 or a['lift_opacity']!=(100 if selected else 28)
                    or not close(a['restored_scale'],[100*scale]*3)
                    or not close(a['lifted_scale'],[(100*32/24 if selected else 100*background_word_scale)*scale]*3)):
                raise ValueError('Full source cannot preselect evidence, substitute words or lose its rewind')


def validate_motion(r, rows):
    if len(rows)!=2:raise ValueError('Both passes need native physical-motion readback')
    for p,m in zip(r['director']['passes'],rows):
        a=m['foreground_original'];b=m['foreground_departure']
        if (m['kind']!=p['kind'] or abs(m['departure_time']-p['lift'][0]-(1 if p['kind']=='fast' else 2)/24)>.0001
                or any(abs(a[j]-b[j])>.05 for j in (0,1)) or abs(b[2]-a[2]+24*r['render_scale'])>.05
                or any(abs(x-y)>.05 for x,y in zip(m['background_original'],m['background_departure']))):
            raise ValueError('Original sentence must leave the plane before reflow or background retreat')
        if r.get('motion_profile',{}).get('sentence_occlusion') and m.get('sentence_plane_index',0)<=m.get('last_sentence_text_index',0):
            raise ValueError('Paper occlusion must be behind every original sentence layer')
        if r.get('motion_profile',{}).get('background_clear') and (m.get('background_opacity_before')!=28 or m.get('background_opacity_departure')!=0 or m.get('foreground_opacity_departure')!=100):
            raise ValueError('Only background may retire while transparent original sentence stays fully visible')
        carries=m['camera_carries']
        if not carries or any(not k['bezier'] or k['speed']<=0 or abs(k['influence']-22)>.01 for k in carries):
            raise ValueError('Reading camera must carry nonzero velocity through interior rows')


def validate_sentence_plane(r, passes):
    for row in passes:
        o=row.get('sentence_occlusion')
        if not o:raise ValueError('Missing native sentence occlusion')
        center=o['expected_center'];size=o['expected_bounds_size'];scale=r['render_scale']
        if (any(abs(o['position'][j]-center[j]-(r.get('motion_profile',{}).get('plane_depth_offset',2)*scale if j==2 else 0))>.05 for j in range(3))
                or any(abs(o['size'][j]-size[j]-8*scale)>.05 for j in range(2))
                or [o['opacity_before'],o['opacity_mid'],o['opacity_after']]!=[0,100,0]
                or o.get('enabled') is not (r['motion_profile']['sentence_occlusion']=='unadorned_bound_paper_plane') or o['position_error'] or o['size_error'] or o['stroke'] or o['effect_count'] or not o['threeD']
                or any(abs(a-b)>.0001 for a,b in zip(o['fill'],[.973,.969,.949]))):
            raise ValueError('Sentence paper must provide bound, temporary, unadorned occlusion')


def audit(output):
    r=current(output);c=relay.client();identity=read(output/'identity.json')
    if relay.file_sha(identity['data_file'])!=identity['native_data_sha']:
        raise ValueError('The original native geometry sidecar changed')
    code='var FULLTEXT_COMP='+str(identity['comp_id'])+';\n'+(HERE/'fulltext-audit.jsx').read_text(encoding='utf-8')
    n=json.loads(c.call('ae_exec',{'code':code})['content']);write(output/'native-audit.json',n);validate_native(r,n)
    if r.get('motion_profile'):validate_motion(r,n.get('motion',[]))
    if r.get('motion_profile',{}).get('sentence_occlusion'):validate_sentence_plane(r,n['passes'])
    expr=c.call('ae_validateExpressions',{'comp_id':str(identity['comp_id']),'sample_times':[3.75,14.75,18.875,19.5],'max_results':1500})
    write(output/'expressions.json',expr)
    if not expr.get('valid') or expr.get('truncated'):raise ValueError('Native expression validation incomplete')
    return n


def preview(output,without_guide=False):
    r=current(output);audit(output);c=relay.client();identity=read(output/'identity.json')
    suffix='-no-guide' if without_guide else '';folder=output/('previews'+suffix);folder.mkdir(exist_ok=True)
    enabled=None;prefix='AEMCP.compById('+str(identity['comp_id'])+').layer("READING_GUIDE")'
    if without_guide:
        enabled=json.loads(c.call('ae_exec',{'code':'JSON.stringify('+prefix+'.enabled);'})['content'])
        mutation_call(c,'ae_exec',{'code':prefix+'.enabled=false;"hidden for lens test";'},output,90)
    try:
        result=c.call('ae_previewFrame',{'comp_id':str(identity['comp_id']),
            'times':[.3,1,2.5,3.5,4,6.8,8.5,9.8,11,14.3,15.2,18.7083333333,18.875,19.0416666667,19.125,19.8],
            'layout':'grid','grid_max_side':2048,'out_dir':str(folder)},timeout=180)
        write(output/('preview'+suffix+'.json'),result)
    except Exception as error:
        write(output/('preview'+suffix+'-failure.json'),{'spec_sha':r['spec_sha'],
            'error_type':type(error).__name__,'error':str(error),'state':'uncertain',
            'next_action':'inspect_public_host_status_and_partial_frames_before_new_capture'})
        raise
    finally:
        if enabled is not None:
            mutation_call(c,'ae_exec',{'code':prefix+'.enabled='+json.dumps(enabled)+';JSON.stringify('+prefix+'.enabled);'},output,90)
    if without_guide:write(output/'guide-isolation.json',{'spec_sha':r['spec_sha'],'original_enabled':enabled,
        'restored_enabled':json.loads(c.call('ae_exec',{'code':'JSON.stringify('+prefix+'.enabled);'})['content']),
        'reason':'native DOF visibility check; not a new approved movie'})
    return {'spec_sha':r['spec_sha'],'capture':result}


def build(output,**kwargs):
    output=relay.local(output);output.mkdir(parents=True,exist_ok=False);r=make_request(output,**kwargs)
    write(output/'request.json',r);shutil.copy2(HERE/'fulltext-build.jsx',output/'executed-template.jsx');c=relay.client()
    before=json.loads(c.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty});'})['content'])
    old=relay.file_sha(before['path']) if before['path'] else None
    mutation_call(c,'ae_exec',{'code':'app.project.save(new File('+json.dumps((output/'SESSION_START.aep').as_posix())+'));"isolated";',
        'undo_group_name':'Isolate fulltext location P0'},output,90)
    if before['path'] and relay.file_sha(before['path'])!=old:raise ValueError('Historical project changed')
    write(output/'session-isolation.json',{'before':before,'original_sha':old})
    result=mutation_call(c,'ae_exec',{'code':'var FULLTEXT_REQUEST='+json.dumps((output/'request.json').as_posix())+';\n'+(output/'executed-template.jsx').read_text(encoding='utf-8'),
        'undo_group_name':'Frozen whole passage location P0','checkpoint_label':'before-fulltext-location','timeout_sec':180},output,210)
    write(output/'build-result.json',result);identity=json.loads(result['content']);identity['native_data_sha']=relay.file_sha(identity['data_file'])
    write(output/'identity.json',identity);return audit(output)


def validate_render_chunk(native, paths, start_frame, count, comp_id):
    """Bind each completed native time span before joining its frame sequence."""
    if (native.get('done') is not True or native.get('comp_id')!=comp_id
            or abs(native.get('start',-1)-start_frame/24)>.0001
            or abs(native.get('duration',-1)-count/24)>.0001 or len(paths)!=count):
        raise ValueError('Native chunk does not match its directed time span')
    numbers=[]
    for path in paths:
        match=re.fullmatch(r'FRAME_(\d{5})\.tif',path.name)
        if not match:raise ValueError('Unexpected native frame name')
        numbers.append(int(match[1]))
    if numbers!=list(range(numbers[0],numbers[0]+count)):
        raise ValueError('Native chunk has a frame gap')


def render(output):
    r=current(output);audit(output);identity=read(output/'identity.json');c=relay.client();folder=output/'native-frames'
    folder.mkdir(exist_ok=False)
    code='''(function(){var cp=AEMCP.compById(COMP);for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).render&&app.project.renderQueue.item(i).status===RQItemStatus.QUEUED)throw new Error('Unrelated queued render');var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var j=0;j<o.templates.length;j++)if(o.templates[j].indexOf('TIFF')!==-1){preset=o.templates[j];break;}if(!preset)throw new Error('Native TIFF required');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=5;app.project.save();app.setMultiFrameRenderingConfig(false,100);var begin=(new Date()).getTime();app.project.renderQueue.render();app.project.save();return JSON.stringify({done:q.status===RQItemStatus.DONE,comp_id:cp.id,start:q.timeSpanStart,duration:q.timeSpanDuration,preset:preset,render_ms:(new Date()).getTime()-begin});})();'''
    # Four contiguous native spans stay within the public execution timeout.
    # Render at full resolution; join frames without changing cadence or timing.
    segments=[]
    for first in (0,120,240,360):
        part=output/('native-part-'+str(first).zfill(5));part.mkdir(exist_ok=False)
        script=code.replace('COMP',str(identity['comp_id'])).replace('DEST',json.dumps((part/'FRAME_[#####].tif').as_posix())).replace('START',str(first/24))
        result=mutation_call(c,'ae_exec',{'code':script,'checkpoint_label':'before-fulltext-native-render-'+str(first),'timeout_sec':600},output,630)
        write(output/('native-render-'+str(first).zfill(5)+'.json'),result);segment=json.loads(result['content'])
        chunk_paths=sorted(part.glob('*.tif'));validate_render_chunk(segment,chunk_paths,first,120,identity['comp_id'])
        transfers=[(path,folder/('FRAME_'+str(first+i).zfill(5)+'.tif')) for i,path in enumerate(chunk_paths)]
        for source,target in transfers:
            if (source.resolve().parent!=part.resolve() or target.resolve().parent!=folder.resolve()
                    or not source.resolve().is_relative_to(relay.LOCAL) or not target.resolve().is_relative_to(relay.LOCAL)
                    or target.exists()):raise ValueError('Unsafe generated native frame transfer')
        for source,target in transfers:shutil.move(str(source),str(target))
        part.rmdir();segments.append(segment)
        write(output/'native-render-segments.json',segments)
        print(json.dumps({'native_frames_completed':first+120,'total_frames':480,'resolution':r['canvas'][:2]}),flush=True)
    native={'done':True,'comp_id':identity['comp_id'],'start':0,'duration':20,'preset':segments[0]['preset'],
            'render_ms':sum(s['render_ms'] for s in segments),'segments':segments,
            'batching_reason':'public_ae_exec_timeout_limit_600s; contiguous native 5s spans'}
    write(output/'native-render.json',{'ok':True,'contentType':'json','content':json.dumps(native)})
    paths=sorted(folder.glob('*.tif'))
    if [p.name for p in paths]!=['FRAME_'+str(i).zfill(5)+'.tif' for i in range(480)]:raise ValueError('Native frames incomplete')
    manifest={p.name:relay.file_sha(p) for p in paths};archive=output/'NATIVE_TIFF_FULLTEXT.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        for name,value in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=value:raise ValueError('Native archive verification failed')
    write(output/'native-frame-shas.json',manifest)
    import acquisition_ab as ab
    movies={}
    for name,start,count in (('FULLTEXT_LOCATION',0,480),('FULLTEXT_FAST',0,168),('FULLTEXT_GUIDED',192,288)):
        movies[name]=ab.encode_frames(folder,start,count,output/(name+'.mp4'),width=r['canvas'][0],height=r['canvas'][1])
    for p in paths:
        if p.resolve().parent!=folder.resolve() or not p.resolve().is_relative_to(relay.LOCAL):raise ValueError('Unsafe generated frame path')
    for p in paths:p.unlink()
    receipt={'kind':r['kind'],'spec_sha':r['spec_sha'],'semantic_binding_sha':r['source']['semantic_binding_sha'],
        'native':native,'project':r['project'],'project_sha':relay.file_sha(r['project']),
        'archive_sha':relay.file_sha(archive),'frame_manifest_sha':relay.file_sha(output/'native-frame-shas.json'),
        'request_sha':relay.file_sha(output/'request.json'),'audit_sha':relay.file_sha(output/'native-audit.json'),
        'executed_template_sha':relay.file_sha(output/'executed-template.jsx'),'movies':movies,'human_visual_review':'PENDING',
        'listening_review':'DEFERRED_BY_USER','synthetic_handoff':False,'new_method_certification':False,
        'final_voice_accepted':False,'production_eligible':False,'public_render_ready':False}
    write(output/'render-receipt.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('build','audit','preview','render'));p.add_argument('output')
    p.add_argument('--bundle',type=Path);p.add_argument('--status',type=Path);p.add_argument('--question');p.add_argument('--question-cue');p.add_argument('--hit-cue');p.add_argument('--without-guide',action='store_true');a=p.parse_args();out=relay.local(a.output)
    if a.operation=='build':result=build(out,bundle_path=a.bundle.resolve(),status_path=a.status.resolve(),question_id=a.question,question_cue=a.question_cue,hit_cue=a.hit_cue)
    elif a.operation=='preview':result=preview(out,without_guide=a.without_guide)
    else:result=globals()[a.operation](out)
    print(json.dumps({'kind':result.get('kind'),'spec_sha':result['spec_sha'],'saved':str(out)},ensure_ascii=True))
