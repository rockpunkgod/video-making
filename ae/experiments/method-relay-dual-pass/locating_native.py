"""Generate a guarded Guided-only patch for the existing native fulltext rig.

This adapter does not create source objects or authorize a render. A fresh copy
of the old project, matching native readback, current source and trace status
must be supplied. The actual AE result must be independently read back.
"""
from pathlib import Path
from creative_os.locating_attention import build_plan, native_geometry
from video_contracts import sha

HERE=Path(__file__).resolve().parent


def prepare(trace, trace_status, bundle, status, request, native_audit, frame_range,
            recognition_frames=None, entry_state=None):
    geometry=native_geometry(request,native_audit)
    plan=build_plan(trace,trace_status,bundle,status,geometry,frame_range,recognition_frames)
    if request['source']['asset_id']!=plan['source_binding']['asset_id']:
        raise ValueError('Wrong native project source')
    guided=request['director']['passes'][1]
    if frame_range[0]!=round(guided['scan'][0]*24) or frame_range[0]<=round(request['director']['passes'][0]['end']*24):
        raise ValueError('Patch starts at existing Guided scan; Fast protected')
    if plan['handoff']:
        # v0.1 preserves the old tail. Overflow explicitly requests retiming,
        # never silently shifts lock/lift or relaxes legacy request validation.
        if frame_range[1]!=round(guided['hit_settle_end']*24):
            raise ValueError('Acquired plan must meet existing hit endpoint; retime through a new request')
        target=plan['targets'][-1]
        if target['word_ids']!=request['hit_ids'] or plan['handoff']['sentence_ids']!=request['target_ids']:
            raise ValueError('Trace endpoint must bind exact existing hit and lift objects')
        plan['handoff']['sentence_confirm']=[round(x*24) for x in guided['lock']]
        plan['handoff']['handoff_to_lift']=[round(x*24) for x in guided['lift']]
    plan.pop('plan_sha');plan['plan_sha']=sha(plan)
    rows=[{'frame':frame_range[0],'center':plan['first_source_center']}]
    if entry_state is not None:
        if entry_state['base_spec_sha']!=request['spec_sha'] or entry_state['frame']!=frame_range[0]:
            raise ValueError('Current original native entry state required')
        rows[0]['center']=entry_state['focus']
    by_id={w['id']:w for w in geometry['words']}
    previous_line=0
    for index,(target,event) in enumerate(zip(plan['targets'],plan['clock']['events'])):
        first_line=target['line_ids'][0];start,end=event['transfer']
        route=[]
        for line in range(previous_line,first_line):
            members=[w for w in geometry['words'] if w['line']==line]
            route.extend([members[-1]['center'],[min(w['min'][0] for w in geometry['words'] if w['line']==line+1),
                                                next(w['center'][1] for w in geometry['words'] if w['line']==line+1),0]])
        if end-start<len(route)+3: raise ValueError('Actual reading route needs more transfer frames')
        for j,center in enumerate(route):rows.append({'frame':start+(end-start)*(j+1)/(len(route)+1),'center':center})
        drift=[0,0,0]
        if index+1<len(plan['targets']):
            next_center=plan['targets'][index+1]['center']
            delta=[b-a for a,b in zip(target['center'],next_center)]
            length=sum(v*v for v in delta)**.5
            if length: drift=[2*v/length for v in delta]
        rows.extend([{'frame':end,'center':[a-b for a,b in zip(target['center'],drift)]},
                     {'frame':event['recognition'][1],'center':[a+b for a,b in zip(target['center'],drift)]}])
        previous_line=target['line_ids'][-1]
    if not plan['targets']: rows.append({'frame':frame_range[1],'center':geometry['words'][-1]['center']})
    elif rows[-1]['frame']<frame_range[1]: rows.append({'frame':frame_range[1],'center':rows[-1]['center']})
    # Shared quintic Hermite clock: matching position, velocity and zero endpoint
    # acceleration. Interior route points carry velocity; recognition settles.
    for i,row in enumerate(rows):
        velocity=[0,0,0]
        if 0<i<len(rows)-1:
            a,b=rows[i-1],rows[i+1]
            for axis in range(3):
                left=(row['center'][axis]-a['center'][axis])/(row['frame']-a['frame'])
                right=(b['center'][axis]-row['center'][axis])/(b['frame']-row['frame'])
                if left*right>0: velocity[axis]=2*left*right/(left+right)
        row['velocity']=velocity
    attention=[]
    for group in native_audit.get('sentence_attention',[]):
        windows=[]
        for target,event in zip(plan['targets'],plan['clock']['events']):
            if not set(target['word_ids']).intersection(group['ids']):continue
            begin=max(frame_range[0],event['activation'][0]-8)/24
            end=(plan['handoff']['handoff_to_lift'][0] if target['recognition_state']=='acquired' else event['recognition'][1])/24
            finish=(plan['handoff']['handoff_to_lift'][1] if target['recognition_state']=='acquired' else event['retirement'][1]+7)/24
            if windows and begin<=windows[-1][2]:
                windows[-1][1]=max(windows[-1][1],end);windows[-1][2]=max(windows[-1][2],finish)
            else:windows.append([begin,end,finish,min(group['gain_cap'],.012)])
        attention.append({'ids':group['ids'],'windows':[w for w in group['windows'] if w[0]<frame_range[0]/24]+windows})
    payload={'kind':'locating_native_patch','version':'0.1.0','plan':plan,'rows':rows,
        'base_spec_sha':request['spec_sha'],'native_audit_sha':sha(native_audit),
        'geometry':geometry,'camera_style':request['camera_style'],'render_scale':request['render_scale'],
        'frame_range':frame_range,'fast_end_frame':round(request['director']['passes'][0]['end']*24),
        'entry_state':entry_state,'attention_groups':attention,
        'native_execution':'PENDING','human_visual_review':'PENDING','public_render_ready':False}
    return {**payload,'patch_sha':sha(payload)}


def script(patch, patch_path, destination):
    from json import dumps
    if patch['patch_sha']!=sha({k:v for k,v in patch.items() if k!='patch_sha'}):
        raise ValueError('Patch changed')
    if Path(destination).exists(): raise ValueError('Fresh native project required')
    return (HERE/'locating-native.jsx').read_text(encoding='utf-8').replace(
        'LOCATING_PATCH_PATH',dumps(Path(patch_path).as_posix())).replace(
        'LOCATING_DESTINATION',dumps(Path(destination).as_posix()))
