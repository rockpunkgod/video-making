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
    # Camera transports the reading band, not every glyph-centre/return-sweep
    # excursion. It shares candidate event times with focus but has its own
    # monotone longitudinal curve. Recognition keeps a small forward drift.
    camera_rows=[{'frame':frame_range[0],'center':rows[0]['center'][:]}]
    for index,(target,event) in enumerate(zip(plan['targets'],plan['clock']['events'])):
        y=max(camera_rows[-1]['center'][1],target['center'][1])
        next_y=plan['targets'][index+1]['center'][1] if index+1<len(plan['targets']) else y
        drift=min(2,max(0,next_y-y)/4)
        camera_rows.extend([
            {'frame':event['transfer'][1],'center':[rows[0]['center'][0],max(camera_rows[-1]['center'][1],y-drift),0]},
            {'frame':event['recognition'][1],'center':[rows[0]['center'][0],y+drift,0]}])
    if not plan['targets']:
        camera_rows.append({'frame':frame_range[1],'center':[rows[0]['center'][0],max(rows[0]['center'][1],rows[-1]['center'][1]),0]})
    elif camera_rows[-1]['frame']<frame_range[1]:
        camera_rows.append({'frame':frame_range[1],'center':camera_rows[-1]['center'][:]})
    for i,row in enumerate(camera_rows):
        row['velocity']=[0,0,0]
        if 0<i<len(camera_rows)-1:
            a,b=camera_rows[i-1],camera_rows[i+1]
            left=(row['center'][1]-a['center'][1])/(row['frame']-a['frame'])
            right=(b['center'][1]-row['center'][1])/(b['frame']-row['frame'])
            if left*right>0:row['velocity'][1]=min(2*left*right/(left+right),1.5*min(left,right))
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
    payload={'kind':'locating_native_patch','version':'0.1.1','plan':plan,'rows':rows,'camera_rows':camera_rows,
        'base_spec_sha':request['spec_sha'],'native_audit_sha':sha(native_audit),
        'geometry':geometry,'camera_style':request['camera_style'],'render_scale':request['render_scale'],
        'frame_range':frame_range,'fast_end_frame':round(request['director']['passes'][0]['end']*24),
        'entry_state':entry_state,'attention_groups':attention,
        'focus_entry':({'frames':[round(guided['enter_start']*24),frame_range[0]],
                        'from':native_audit['geometry']['whole']['center'],'to':rows[0]['center']}
                       if entry_state is not None and 'enter_start' in guided and 'geometry' in native_audit else None),
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


def focus_at(patch, time):
    """Reference for native readback, not substitute rendered evidence."""
    frame=time*24;entry=patch.get('focus_entry')
    if entry and entry['frames'][0]<=frame<entry['frames'][1]:
        u=(frame-entry['frames'][0])/(entry['frames'][1]-entry['frames'][0])
        q=u**3*(10+u*(-15+6*u))
        return [a*(1-q)+b*q for a,b in zip(entry['from'],entry['to'])]
    return path_at(patch['rows'],frame)


def camera_at(patch,time):
    """Independent transport curve on the same recognition clock."""
    return path_at(patch.get('camera_rows',patch['rows']),time*24)


def path_at(rows,frame):
    if frame<=rows[0]['frame']:return rows[0]['center']
    for a,b in zip(rows,rows[1:]):
        if frame<=b['frame']:
            d=b['frame']-a['frame'];u=(frame-a['frame'])/d
            q=6*u**5-15*u**4+10*u**3;h0=u-6*u**3+8*u**4-3*u**5;h1=-4*u**3+7*u**4-3*u**5
            return [x*(1-q)+y*q+va*d*h0+vb*d*h1
                    for x,y,va,vb in zip(a['center'],b['center'],a['velocity'],b['velocity'])]
    return rows[-1]['center']


def validate_motion(patch, actual):
    import math
    if (actual['patch_binding'].get('locating_patch_sha')!=patch['patch_sha']
            or actual['canvas']!=[3840,2160,24] or any(actual['errors'])):
        raise ValueError('Native binding, canvas or expressions invalid')
    frame_rows={round(r['time']*24):r for r in actual['rows']}
    required=set(range(patch['frame_range'][0],patch['frame_range'][1]+1))
    if not required<=set(frame_rows):raise ValueError('Every scan frame needs native readback')
    max_error=0
    for frame in sorted(required):
        row=frame_rows[frame];expected=focus_at(patch,frame/24)
        error=math.dist(row['focus'],expected);max_error=max(error,max_error)
        if error>.05 or not math.isfinite(row['focus_distance']) or row['focus_distance']<=0:
            raise ValueError('Focus trajectory mismatch or invalid depth of field')
        if patch.get('entry_state'):
            e=patch['entry_state'];origin=patch['rows'][0]['center']
            transport=camera_at(patch,frame/24)
            camera=[e['camera'][0],transport[1]+e['camera'][1]-origin[1],e['camera'][2]]
            look=[e['look'][0],transport[1]+e['look'][1]-origin[1],e['look'][2]]
            if math.dist(row['camera'],camera)>.05 or math.dist(row['look'],look)>.05:
                raise ValueError('Camera transport does not match the recognition clock')
            vector=[x-y for x,y in zip(look,camera)];length=math.dist(vector,[0,0,0])
            distance=sum((f-c)*v/length for f,c,v in zip(expected,camera,vector))
            if abs(distance-row['focus_distance'])>.05:
                raise ValueError('Camera depth of field not bound to current attention target')
        for t,e in zip(patch['plan']['targets'],patch['plan']['clock']['events']):
            mark=next(m for m in row['marks'] if m['name']=='LOCATING_TRANSIENT_'+t['candidate_id'])
            palette=patch['plan'].get('highlight_palette')
            if palette:
                color=palette['acquired'] if t['recognition_state']=='acquired' and frame>=e['recognition'][1] else palette['comparison']
                if (math.dist(mark['color'][:3],color)>.001
                        or math.dist(row['question_color'][:3],palette['question'])>.001
                        or mark['index']<=max(actual['source_indices'])
                        or mark['position'][2]<=max(w['max'][2] for w in patch['geometry']['words'])):
                    raise ValueError('Highlight palette or behind-ink placement invalid')
            retirement=e.get('retirement',[e['recognition'][1]+6,e['recognition'][1]+9])
            if frame<e['activation'][0] or frame>=retirement[1]:
                if abs(mark['opacity'])>.001:raise ValueError('Early or lingering highlight')
            if e['activation'][1]<=frame<e['recognition'][1] and mark['opacity']<84:
                raise ValueError('Recognition highlight missing')
    speeds=[(frame_rows[b]['camera'][1]-frame_rows[a]['camera'][1])*24
            for a,b in zip(sorted(required),sorted(required)[1:])]
    if patch.get('camera_rows') and any(v<-.05 for v in speeds):
        raise ValueError('Camera transport reverses between recognition events')
    # Small finite differences approximate boundary velocities. The reference
    # shares endpoint velocity and zero acceleration analytically; allow tiny
    # high-speed third-order sampling error, not an observable stop/start jump.
    jumps=[];dt=1/2400
    for b in actual['boundaries']:
        for prop in ('focus','camera','look'):
            # The two curves have different joins. A focus row-return knot is
            # an interior point of camera transport, not a camera boundary.
            # AE quantizes fractional valueAtTime queries; dividing its small
            # positional rounding by dt would invent a camera velocity jump.
            knots=patch['rows'] if prop=='focus' else patch.get('camera_rows',patch['rows'])
            times=[r['frame']/24 for r in knots]
            if prop=='focus' and patch.get('focus_entry'):times.append(patch['focus_entry']['frames'][0]/24)
            if not any(abs(b['time']-t)<1e-7 for t in times):continue
            left=[(x-y)/dt for x,y in zip(b['at'][prop],b['before'][prop])]
            right=[(x-y)/dt for x,y in zip(b['after'][prop],b['at'][prop])]
            jump=math.dist(left,right);jumps.append(jump)
            if jump>max(10,.01*max(math.dist(left,[0,0,0]),math.dist(right,[0,0,0]))):
                raise ValueError('Native motion velocity discontinuity')
    if patch['plan']['handoff']:
        expected=dict(zip(patch['plan']['handoff']['sentence_ids'],patch['plan']['handoff']['sentence_layer_ids']))
        if {w['id']:w['layer_id'] for w in actual['lift']}!=expected:
            raise ValueError('Lift replaced original sentence objects')
    return {'status':'NATIVE_SCAN_READBACK_PASS','frame_count':len(required),
            'max_focus_position_error':max_error,'max_sampled_velocity_jump':max(jumps,default=0),
            'camera_min_frame_speed':min(speeds,default=0),'camera_max_frame_speed':max(speeds,default=0),
            'human_visual_review':'PENDING','public_render_ready':False}
