"""Deterministic visual constraints, not semantic truth or human taste certification."""
import json
from pathlib import Path
from video_contracts import ROOT,write


def luminance(hexcolor):
    channels=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
    return sum(a*b for a,b in zip(linear,(0.2126,0.7152,0.0722)))


def contrast(a,b):
    hi,lo=sorted((luminance(a),luminance(b)),reverse=True)
    return (hi+0.05)/(lo+0.05)


def contains(outer,inner):
    x,y,w,h=outer;a,b,c,d=inner
    return a>=x-0.01 and b>=y-0.01 and a+c<=x+w+0.01 and b+d<=y+h+0.01


def projection_qa(contract):
    if contract['design_system_version']!='0.2.0':return {'status':'historical_v0.1'}
    core=contract['actual_content_area'];failures=[]
    for scene in contract['scenes']:
        for c in scene['components']:
            l=c['layout']
            if not contains(core,[l['x'],l['y'],l['width'],l['height']]):failures.append({'component_id':c['component_id'],'reason':'platform_safe_core'})
    ds=contract['design'];colors=ds['colors']
    ratios={k:round(contrast(colors[k],colors['background']),3) for k in ('primary_text','secondary_text')}
    if min(ratios.values())<4.5:failures.append({'reason':'text_contrast'})
    if ds['motion']['overshoot'] or ds['art_direction']['background_motion']:failures.append({'reason':'unrestrained_motion'})
    if failures:raise ValueError('Visual constraint FAIL: '+json.dumps(failures))
    return {'status':'PASS','text_contrast':ratios,'safe_core':core,'platform_profile':contract['platform_profile']['platform'],
            'platform_ui_validation':'provisional_simulation','human_taste_review':'PENDING'}


def actual_visual_qa(client,comp_id,contract,output_dir):
    report=projection_qa(contract)
    code='var V8_COMP_ID='+str(int(comp_id))+';\n'+(ROOT/'ae/templates/visual-audit.jsx').read_text(encoding='utf-8')
    actual=json.loads(client.call('ae_exec',{'code':code})['content']);warnings=actual['style_drift_warnings']
    colors=contract['design']['colors'];allowed=[tuple(int(h[i:i+2],16)/255 for i in (1,3,5)) for h in colors.values()]
    paper=tuple(int(colors['background'][i:i+2],16)/255 for i in (1,3,5));fog=tuple(int(colors['evidence'][i:i+2],16)/255 for i in (1,3,5));amount=contract['design']['treatment']['evidence_tint']
    tint=tuple(round(255*(p*(1-amount)+f*amount))/255 for p,f in zip(paper,fog));allowed.append(tint)
    for row in actual['rows']:
        if not any(all(abs(a-b)<0.001 for a,b in zip(row['color'],option)) for option in allowed):warnings.append({'layer':row['name'],'reason':'random_color'})
    layout=json.loads((Path(output_dir)/'layout-audit.json').read_text(encoding='utf-8'))
    cap=contract['platform_profile']['caption_profile'];caption=[cap[k] for k in ('x','y','width','height')]
    for row in layout['rows']:
        if row['name'] in ('METHOD_TAG','TRACE','INTERNAL_ENGINEERING_PREVIEW','SOURCE_TAG') or row['name'].startswith('PROGRESS_'):continue
        box=[row[k] for k in ('x','y','width','height')]
        if not contains(caption if ':subtitle:' in row['name'] else contract['actual_content_area'],box):warnings.append({'layer':row['name'],'reason':'actual_pixel_safe_area'})
    actual.update(constraints=report,style_drift='FAIL' if warnings else 'PASS',human_taste_review='PENDING')
    write(Path(output_dir)/'visual-qa.json',actual)
    if warnings:raise ValueError('Actual visual constraint FAIL: '+json.dumps(warnings))
    return actual
