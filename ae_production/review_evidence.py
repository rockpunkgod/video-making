"""Portable evidence beside an existing authored output. No review or media changes."""
import bisect
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import wave

VERSION = 'video-review-evidence/v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()


def data_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def missing(reason):return {'value':None,'missing_reason':reason}
def ms(seconds):return None if seconds is None else float(seconds)*1000


def frame_floor(value):
    nearest=round(value)
    return nearest if abs(value-nearest)<1e-6 else math.floor(value)


def frame_ceil(value):
    nearest=round(value)
    return nearest if abs(value-nearest)<1e-6 else math.ceil(value)


def native_motion_script(comp_ids,focus):
    """Read existing keys/expressions; do not install properties or change the project."""
    code=r'''
var ids=__IDS__,focus=__FOCUS__,result=[];
function interp(v){var s=String(v);if(s===String(KeyframeInterpolationType.LINEAR))return 'LINEAR';if(s===String(KeyframeInterpolationType.BEZIER))return 'BEZIER';if(s===String(KeyframeInterpolationType.HOLD))return 'HOLD';return s;}
function eases(a){var r=[];for(var i=0;i<a.length;i++)r.push({speed:a[i].speed,influence_percent:a[i].influence});return r;}
function propertyState(p,duration,fps){
 var r={match_name:p.matchName,expression:p.expression||'',expression_enabled:p.expressionEnabled===true,expression_error:p.expressionError||'',keys:[],samples:[]};
 for(var k=1;k<=p.numKeys;k++){
  var q={time_ms:p.keyTime(k)*1000,source_frame_position:p.keyTime(k)*fps,value:p.keyValue(k),in_interpolation:interp(p.keyInInterpolationType(k)),out_interpolation:interp(p.keyOutInterpolationType(k)),in_ease:eases(p.keyInTemporalEase(k)),out_ease:eases(p.keyOutTemporalEase(k)),in_spatial_tangent:null,out_spatial_tangent:null};
  if(p.isSpatial){q.in_spatial_tangent=p.keyInSpatialTangent(k);q.out_spatial_tangent=p.keyOutSpatialTangent(k);}
  r.keys.push(q);
 }
 var a=p.numKeys?p.keyTime(1):0,b=p.numKeys?p.keyTime(p.numKeys):duration-1/fps,t=[Math.max(0,a-1/fps),a,(a+b)/2,b,Math.min(duration-1/fps,b+1/fps)],labels=['before','start','middle','end','after'];
 for(var i=0;i<t.length;i++)r.samples.push({phase:labels[i],time_ms:t[i]*1000,source_frame_position:t[i]*fps,value:p.valueAtTime(t[i],false)});
 return r;
}
for(var ci=0;ci<ids.length;ci++){
 var c=app.project.itemByID(ids[ci]),rows=[],words=[];
 for(var li=1;li<=c.numLayers;li++){
  var l=c.layer(li),tr=l.property('ADBE Transform Group'),r={id:l.id,name:l.name,parent_id:l.parent?l.parent.id:null,three_d:l.threeDLayer,enabled:l.enabled,guide:l.guideLayer,in_ms:l.inPoint*1000,out_ms:l.outPoint*1000,comment:l.comment,properties:{},anchor_point:null};
  if(tr){var anchor=tr.property('ADBE Anchor Point');if(anchor)r.anchor_point=anchor.value;
   var props=[['position','ADBE Position'],['scale','ADBE Scale'],['orientation','ADBE Orientation'],['rotation_x','ADBE Rotate X'],['rotation_y','ADBE Rotate Y'],['rotation_z','ADBE Rotate Z'],['opacity','ADBE Opacity']];
   for(var pi=0;pi<props.length;pi++){var p=tr.property(props[pi][1]);if(p&&(p.numKeys||p.expressionEnabled))r.properties[props[pi][0]]=propertyState(p,c.duration,c.frameRate);}
  }
  rows.push(r);
 }
 for(var wi=0;wi<focus.length;wi++){
  var f=focus[wi],l=c.layer(f.layer_name),an=l.property('ADBE Text Properties').property('ADBE Text Animators').property(f.animator),p=an.property('ADBE Text Animator Properties').property('ADBE Text Scale 3D'),t=[Math.max(0,f.time_start-1/c.frameRate),f.time_start,f.center,f.time_end,Math.min(c.duration-1/c.frameRate,f.time_end+1/c.frameRate)],samples=[];
  for(var ti=0;ti<t.length;ti++)samples.push({time_ms:t[ti]*1000,source_frame_position:t[ti]*c.frameRate,value:p.valueAtTime(t[ti],false)});
  words.push({scene_id:f.scene,window_id:f.window,chunk_id:f.chunk_id,element_id:l.id,element_name:l.name,animator_name:an.name,enabled:an.enabled,source_defined_range_ms:[f.time_start*1000,f.time_end*1000],expression:p.expression,expression_time_unit:'AE native seconds',expression_error:p.expressionError,samples:samples});
 }
 result.push({comp_id:c.id,width_px:c.width,height_px:c.height,fps:c.frameRate,duration_ms:c.duration*1000,layers:rows,focus_samples:words});
}
return result;
'''
    return code.replace('__IDS__',json.dumps(comp_ids)).replace('__FOCUS__',json.dumps(focus))


def capture_native_motion(host,folder,plan,native):
    rows=host.js(native_motion_script([native['comp_id'],native['master_comp_id']],native['audit'].get('word_focus',[])))
    result={'provenance':'NATIVE_ENGINE_READBACK_NOT_PIXEL_MOTION_MEASUREMENT',
        'captured_at_utc':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':file_sha(folder/'AV_PLAN.json'),'native_identity_sha256':file_sha(folder/'native-identity.json'),
        'project_path':str(host.project),'compositions':rows}
    result['parameters_sha256']=data_sha(result)
    write(folder/'EVIDENCE_NATIVE_MOTION.json',result)
    return result


def probe_media(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_streams','-show_format','-of','json',str(path)]))


def frame_timestamps(path):
    result=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_frames','-show_entries','frame=best_effort_timestamp_time,best_effort_timestamp,duration_time,pkt_duration_time',
        '-of','json',str(path)]))
    return [{'frame_number':i,'timestamp_ms':ms(r.get('best_effort_timestamp_time')),
             'source_pts':r.get('best_effort_timestamp'),
             'duration_ms':ms(r.get('duration_time',r.get('pkt_duration_time')))}
            for i,r in enumerate(result.get('frames',[]))]


def _rate(value):
    try:
        f=Fraction(value)
        return {'numerator':f.numerator,'denominator':f.denominator,'fps':float(f)}
    except (ValueError,ZeroDivisionError,TypeError):return None


def _timebase(value):
    r=_rate(value)
    if r is None:return None
    return {'source_seconds_per_tick':{'numerator':r['numerator'],'denominator':r['denominator']},
            'tick_duration_ms':1000*r['numerator']/r['denominator']}


def metadata(media,probe,frames,folder,qa):
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next((s for s in probe['streams'] if s['codec_type']=='audio'),None)
    logs=[str(p.resolve()) for pattern in ('*RENDER*LOG.txt','*EXPORT*LOG.txt') for p in folder.glob(pattern)]
    vs=ms(video.get('start_time'));ass=ms(audio.get('start_time')) if audio else None
    return {'provenance':'FINAL_MP4_FFPROBE_MEASUREMENT','path':str(media),'file_size_bytes':media.stat().st_size,
        'sha256':file_sha(media),'container_duration_ms':ms(probe.get('format',{}).get('duration')),
        'video':{'width_px':video['width'],'height_px':video['height'],'frame_rate':_rate(video.get('r_frame_rate')),
            'average_frame_rate':_rate(video.get('avg_frame_rate')),'frame_count':len(frames) if frames else None,
            'frame_count_method':'decoded ffprobe -show_frames inventory' if frames else None,
            'frame_count_missing_reason':None if frames else 'ffprobe returned no decoded video frame inventory',
            'header_declared_frame_count':video.get('nb_frames'),'codec':video.get('codec_name'),
            'pixel_format':video.get('pix_fmt'),'color_space':video.get('color_space'),
            'color_range':video.get('color_range'),'color_primaries':video.get('color_primaries'),
            'color_transfer':video.get('color_transfer'),'duration_ms':ms(video.get('duration')),
            'start_ms':vs,'start_pts':video.get('start_pts'),'time_base':_timebase(video.get('time_base'))},
        'audio':None if audio is None else {'codec':audio.get('codec_name'),'sample_rate_hz':int(audio['sample_rate']),
            'channels':audio.get('channels'),'duration_ms':ms(audio.get('duration')),'start_ms':ass,
            'start_pts':audio.get('start_pts'),'time_base':_timebase(audio.get('time_base'))},
        'stream_start_offset_ms':None if vs is None or ass is None else ass-vs,
        'stream_offset_scope':'Container stream starts, not measured perceptual/lip sync',
        'acoustic_visual_sync_offset_ms':None,'acoustic_visual_sync_missing_reason':'No shared acoustic/visual calibration event is recorded',
        'render':{'final_output_exists':True,'package_full_decode_status':qa.get('full_decode'),
            'started_at_utc':None,'ended_at_utc':None,
            'clock_timestamp_missing_reason':'Existing renderer receipts do not record reliable render wall-clock start/end; file modification times are not substituted',
            'logs':logs},
        'extraction_tool':{'name':'ffprobe','version':subprocess.check_output(['ffprobe','-version'],text=True).splitlines()[0],
            'method':'Final MP4 -count_frames -show_streams -show_format; decoded frame PTS inventory from -show_frames'},
        'unavailable_stream_fields':{k:'FFprobe stream did not supply this field' for k in
            ('color_space','color_range','color_primaries','color_transfer') if video.get(k) is None}}


def _scene_rows(plan):
    rows=[]
    if plan.get('audience_hook'):
        h=plan['audience_hook'];rows.append({'id':h.get('scene_id','HOOK01'),'title':'Hook','start':h['start'],'end':h['end']})
    rows.extend(plan['scenes'])
    return rows


def _comment(layer):
    try:return json.loads(layer.get('comment','{}'))
    except (ValueError,TypeError):return {}


def _scene_id(layer,scene_ids):
    comment=_comment(layer)
    found=comment.get('scene_id',comment.get('scene'))
    if found in scene_ids:return found,'Native layer comment'
    for name in scene_ids:
        if re.search(r'(^|_)'+re.escape(name)+r'(_|$)',layer['name']):return name,'Exact existing scene token in native element name'
    return None,'Shared/global element; temporal links are listed without inferring a semantic owner'


def motion(plan,native,comp,folder,fps):
    events=[];scene_ids=[s['id'] for s in _scene_rows(plan)]
    if comp:
        for layer in comp['layers']:
            props=layer.get('properties',{})
            if not props:continue
            keys=[k for prop in props.values() for k in prop['keys']]
            start=min((k['time_ms'] for k in keys),default=layer['in_ms'])
            end=max((k['time_ms'] for k in keys),default=layer['out_ms'])
            sid,association=_scene_id(layer,scene_ids)
            units={k:('percent' if k in ('scale','opacity') else 'degrees' if k.startswith('rotation') or k=='orientation' else 'AE composition coordinate units (px), not projected screen px') for k in props}
            events.append({'event_id':'native:'+str(comp['comp_id'])+':'+str(layer['id']),
                'scene_id':sid,'scene_association':association,'element_id':layer['id'],'element_name':layer['name'],
                'type':'AE_NATIVE_TRANSFORM','provenance':'NATIVE_ENGINE_READBACK',
                'start_ms':start,'end_ms':end,'duration_ms':end-start,
                'start_frame':max(0,frame_floor(start*fps/1000)),'end_frame_exclusive':frame_ceil(end*fps/1000),
                'properties':props,'property_units':units,'anchor_point':layer.get('anchor_point'),
                'native_temporal_ease_speed_unit':'Corresponding AE property units per second; native speed is retained, key/sample times are ms',
                'easing_definition_kind':'AE native KeyframeEase speed/influence plus spatial tangents; no CSS cubic-bezier control parameters are configured',
                'coordinate_system':'AE_PARENT_LOCAL_3D' if layer.get('parent_id') else 'AE_WORLD_3D' if layer.get('three_d') else 'AE_COMPOSITION_2D',
                'coordinate_reference':{'comp_id':comp['comp_id'],'composition_size_px':[comp['width_px'],comp['height_px']],
                    'parent_element_id':layer.get('parent_id')},
                'source_definition':{'path':str((folder/'native-source/authored-episode.jsx').resolve()),
                    'native_snapshot_locator':{'comp_id':comp['comp_id'],'layer_id':layer['id']}},
                'important_for_frames':sid is not None,
                'final_video_measured_trajectory':None,
                'trajectory_missing_reason':'No object tracking is performed on final pixels; native values and source-linked final frames are provided'})
        grouped=defaultdict(list)
        for f in comp.get('focus_samples',[]):grouped[(f['scene_id'],f['window_id'])].append(f)
        for (sid,window),chunks in grouped.items():
            start=min(x['source_defined_range_ms'][0] for x in chunks);end=max(x['source_defined_range_ms'][1] for x in chunks)
            events.append({'event_id':'focus:'+window,'scene_id':sid,'element_id':chunks[0]['element_id'],
                'element_name':chunks[0]['element_name'],'related_element_ids':sorted({x['element_id'] for x in chunks}),
                'type':'AE_SENSE_GROUP_FOCUS','start_ms':start,'end_ms':end,'duration_ms':end-start,
                'start_frame':frame_floor(start*fps/1000),'end_frame_exclusive':frame_ceil(end*fps/1000),
                'provenance':'SOURCE_DEFINED_INTERVAL_WITH_NATIVE_RUNTIME_SAMPLES',
                'properties':{'scale':{'unit':'percent','chunks':chunks}},'coordinate_system':'ORIGINAL_SOURCE_TEXT_CHARACTER_RANGE',
                'source_definition':{'path':str((folder/'native-source/reading-focus.jsx').resolve())},
                'important_for_frames':True,'independently_measured_active_range_ms':None,
                'active_range_missing_reason':'Expression-defined interval is retained separately from sampled runtime scale'})
    else:
        # Historical productions remain exportable: report the actual saved
        # readback, retaining unknown easing rather than manufacturing it.
        legacy=folder/'NATIVE_READBACK.json'
        if legacy.exists():
            data=read(legacy)
            for layer in data['layers']:
                props={k:v for k,v in layer.items() if k in ('position','scale','orientation') and isinstance(v,list) and v}
                if not props:continue
                sid,why=_scene_id(layer,scene_ids);times=[k[0] for value in props.values() for k in value]
                events.append({'event_id':'legacy-native:'+str(layer['id']),'scene_id':sid,'element_id':layer['id'],
                    'element_name':layer['name'],'type':'SAVED_NATIVE_KEY_READBACK','provenance':'NATIVE_ENGINE_READBACK_HISTORICAL',
                    'start_ms':ms(min(times)),'end_ms':ms(max(times)),'duration_ms':ms(max(times)-min(times)),
                    'start_frame':frame_floor(min(times)*fps),'end_frame_exclusive':frame_ceil(max(times)*fps),
                    'properties':{k:{'keys':[{'time_ms':ms(t),'source_frame_position':t*fps,'value':v} for t,v in values],
                        'easing':None,'easing_missing_reason':'Historical native readback did not capture interpolation/ease'} for k,values in props.items()},
                    'coordinate_system':'AE_PARENT_LOCAL_3D' if layer.get('parent') else 'AE_WORLD_3D',
                    'coordinate_reference':{'composition_size_px':[data['width'],data['height']],'parent_element_id':layer.get('parent')},
                    'important_for_frames':sid is not None,'scene_association':why})
    for r in plan.get('audience_challenges',{}).get('rows',[]):
        events.append({'event_id':'challenge:'+r['scene'],'scene_id':r['scene'],'element_id':'CHALLENGE_PAUSE_'+r['scene'],
            'type':'CHALLENGE_AND_CONTINUOUS_HANDOFF','provenance':'PLAN_CONFIGURATION',
            'start_ms':ms(r['start']),'end_ms':ms(r['handoff_end']),'duration_ms':ms(r['handoff_end']-r['start']),
            'start_frame':r['start_frame'],'end_frame_exclusive':frame_ceil(r['handoff_end']*fps),
            'configured_pause_end_ms':ms(r['end']),'configured_pause_frames':r['frames'],
            'properties':{},'important_for_frames':True,'source_definition':{'path':str(folder/'AV_PLAN.json'),'pointer':'/audience_challenges/rows'}})
    for r in plan.get('symbol_recipes',{}).get('rows',[]):
        events.append({'event_id':'recipe:'+r['symbol_id'],'scene_id':r['scene_id'],'element_id':r['symbol_id'],
            'type':r['recipe_id'],'provenance':'PLAN_CONFIGURATION_WITH_SEPARATE_NATIVE_ELEMENT_READBACK',
            'start_ms':ms(r['start']),'end_ms':ms(r['end']),'duration_ms':ms(r['end']-r['start']),
            'start_frame':r['start_frame'],'end_frame_exclusive':r['end_frame'],
            'configured_curve':r['parameters']['curve'],'configured_space':r['parameters']['space'],
            'coordinate_system':'RECIPE_LOCAL_LOGICAL_PX_FROM_CONFIGURED_ORIGIN_NOT_VIDEO_SCREEN_PX',
            'properties':{},'phases':[{'name':x['phase'],'start_ms':ms(x['start']),'end_ms':ms(x['end'])} for x in r['phases']],
            'source_definition':{'path':str(folder/'AV_PLAN.json'),'pointer':'/symbol_recipes/rows/'+str(plan['symbol_recipes']['rows'].index(r))},
            'native_element_event_ids':[e['event_id'] for e in events if e.get('element_name','').startswith('SYMBOL_') and r['symbol_id'] in e.get('element_name','')],
            'important_for_frames':True})
    for event in events:
        event['scene_ids']=[s['id'] for s in _scene_rows(plan) if ms(s['start'])<event['end_ms'] and event['start_ms']<ms(s['end'])]
        event['related_event_ids']=[x['event_id'] for x in events if x is not event and x['scene_id']==event['scene_id'] and x['start_ms']<event['end_ms'] and event['start_ms']<x['end_ms']]
    # Reuse existing specialized readbacks. Numeric samples remain engine
    # observations, never final-pixel trajectory measurements.
    if comp:
        challenge=folder/'CHALLENGE_NATIVE_READBACK.json'
        if challenge.exists():
            for r in read(challenge).get('rows',[]):
                event=next((x for x in events if x['event_id']=='challenge:'+r['scene']),None)
                if r['comp_id']!=comp['comp_id'] or not event:continue
                event['native_readback']={'provenance':'EXISTING_NATIVE_ENGINE_SAMPLES',
                    'source_path':str(challenge),'element_state_columns':['position_x_px','position_y_px','position_z_px',
                        'scale_x_percent','scale_y_percent','scale_z_percent','opacity_percent','neutral_base_ink_boolean','active_non_neutral_animator_percent'],
                    'coordinate_system':'AE_LAYER_PARENT_LOCAL_OR_COMPOSITION',
                    'article_elements':[{'element_id':l['id'],'name':l['name']} for l in r['article_layers']],
                    'question_option_elements':[{'element_id':l['id'],'name':l['name']} for l in r['glyphs']],
                    'fold_character_ranges':r['chunks'],
                    'camera_columns':['position_x_px','position_y_px','position_z_px','point_of_interest_x_px',
                        'point_of_interest_y_px','point_of_interest_z_px','aperture_px'],
                    'samples':[{'time_ms':ms(s['time']),'source_frame_position':s['time']*fps,
                        **{k:v for k,v in s.items() if k not in ('time',)}} for s in r['samples']+r['handoff']]}
        symbols=folder/'SYMBOL_NATIVE_READBACK.json'
        if symbols.exists():
            for r in read(symbols).get('rows',[]):
                event=next((x for x in events if x['event_id']=='recipe:'+r['symbol_id']),None)
                if r['comp_id']!=comp['comp_id'] or not event:continue
                definition=next(x for x in plan['symbol_recipes']['rows'] if x['symbol_id']==r['symbol_id'])
                event['native_glyph_samples']=[{'element_id':g['id'],'name':g['name'],
                    'source_element_id':g['source_id'],'source_ref':g['comment']['source_ref'],
                    'coordinate_system':'AE_WORLD_3D','position_unit':'px (AE world units, not projected screen px)',
                    'initial_position':g['start'],'settled_position':g['locked'],'return_position':g['return'],
                    'sample_time_basis':'Existing cognitive_symbol_review collector: start+(phase[1].end-start)*k/16',
                    'runtime_position_samples':[{'time_ms':ms(definition['start']+(definition['phases'][1]['end']-definition['start'])*k/16),
                        'value':v} for k,v in enumerate(g['travel_samples'])],
                    'font':g['font'],'font_size_ae_px':g['font_size'],'scale_percent':g['locked_scale']}
                    for g in r.get('glyphs',[])]
    return {'time_unit':'ms','frame_numbering':'zero-based; end_frame_exclusive','events':events,
        'scope':'Existing configured events and actual native property readbacks; not automatic motion diagnosis',
        'unidentified_events':missing('Events not represented by existing native/configuration metadata are not automatically recognized')}


def timeline(plan,qa,frames,events,native,folder,fps):
    rows=[]
    for s in _scene_rows(plan):
        first=round(s['start']*fps);last=round(s['end']*fps)
        start=frames[first]['timestamp_ms'] if first<len(frames) else None
        end=(frames[last]['timestamp_ms'] if last<len(frames) else
             frames[-1]['timestamp_ms']+frames[-1]['duration_ms'] if frames[-1]['duration_ms'] is not None else
             ms(qa.get('video',{}).get('duration'))) if frames else None
        associated=[e for e in events if s['id'] in e['scene_ids']]
        rows.append({'scene_id':s['id'],'shot_id':None,'shot_id_missing_reason':'Existing producer uses scenes, not a distinct shot entity',
            'title':s.get('title'),'planned_range_ms':[ms(s['start']),ms(s['end'])],
            'start_frame':first,'end_frame_exclusive':last,'mapped_video_frame_range_ms':[start,end],
            'mapped_duration_ms':None if start is None or end is None else end-start,
            'mapping_basis':'Existing planned scene frame range mapped to final decoded frame PTS; no semantic boundary detection',
            'mapped_pts_minus_plan_ms':None if start is None else start-ms(s['start']),
            'independently_measured_scene_boundaries_ms':None,
            'actual_boundary_missing_reason':'MP4 does not label scenes and this exporter does not infer cuts or evaluate content',
            'plan_vs_independently_measured_scene_delta_ms':None,
            'mapping_reliable':qa.get('plan_sha256')==file_sha(folder/'AV_PLAN.json') and qa.get('frames')==len(frames) and start is not None,
            'mapping_limit':'Reliable production frame correspondence, not proof of visual/semantic scene boundaries',
            'source_files':[str(folder/'AV_PLAN.json'),qa.get('native_project'),qa.get('premiere_project')],
            'element_ids':sorted({str(e['element_id']) for e in associated}),
            'motion_event_ids':[e['event_id'] for e in associated],
            'voice_event_ids':[v['id'] for v in plan['segments'] if v['scene_id']==s['id']],
            'caption_ids':[c['id'] for c in plan.get('cues',[]) if c.get('scene_id',c.get('scene'))==s['id']],
            'music_event_ids':['music:'+str(i) for i,m in enumerate(plan.get('music',[])) if m.get('timeline_start',0)<s['end'] and s['start']<m.get('timeline_start',0)+m['duration']],
            'sfx_event_ids':[]})
    return {'time_unit':'ms','scenes':rows,'separate_shot_system_created':False}


def audio_probe(path):
    if Path(path).suffix.lower()=='.wav':
        with wave.open(str(path),'rb') as w:return {'sample_rate_hz':w.getframerate(),'channels':w.getnchannels(),'duration_ms':1000*w.getnframes()/w.getframerate()}
    p=probe_media(path);a=next(s for s in p['streams'] if s['codec_type']=='audio')
    return {'sample_rate_hz':int(a['sample_rate']),'channels':a['channels'],'duration_ms':ms(a.get('duration'))}


def wave_levels(path):
    import numpy as np
    peak=0;energy=0.;count=0
    with wave.open(str(path),'rb') as w:
        if w.getsampwidth()!=2:return {'sample_peak_dbfs':None,'rms_dbfs':None,'missing_reason':'PCM measurement supports16-bit source only'}
        while True:
            block=w.readframes(65536)
            if not block:break
            x=np.frombuffer(block,dtype='<i2').astype(np.float64)/32768
            peak=max(peak,float(np.max(np.abs(x))));energy+=float(np.dot(x,x));count+=len(x)
    return {'sample_peak_dbfs':20*math.log10(peak) if peak else None,
        'rms_dbfs':10*math.log10(energy/count) if count and energy else None,
        'headroom_db':-20*math.log10(peak) if peak else None,
        'algorithm':'16-bit PCM normalized by32768; sample max and unweighted RMS, not perceptual loudness',
        'silence_missing_reason':None if peak else 'All samples zero; logarithmic dB is negative infinity, represented as null'}


def audio(plan,qa,folder,out,media):
    timeline_path=folder/'PR_TIMELINE.json';native=read(timeline_path) if timeline_path.exists() else {}
    clips=[c for t in native.get('audioTracks',[]) for c in t.get('clips',[])]
    rows=[]
    for s in plan['segments']:
        path=Path(s['voice']['path']);matches=[c for c in clips if c['name']==Path(s['voice']['padded_path']).name]
        clip=matches[0] if len(matches)==1 else None
        rows.append({'event_id':s['id'],'role':'narration','scene_id':s['scene_id'],'text':s['text'],
            'source_path':str(path),'source_sha256':file_sha(path),'source_actual_parameters':audio_probe(path),
            'timeline_asset':{'path':s['voice']['padded_path'],'sha256':file_sha(s['voice']['padded_path']),
                'actual_parameters':audio_probe(s['voice']['padded_path']),
                'scope':'Existing complete take padded to timeline frame boundary; original take above remains separate'},
            'planned_range_ms':[ms(s['voice_start']),ms(s['voice_end'])],
            'native_clip_range_ms':None if clip is None else [ms(clip['start']),ms(clip['end'])],
            'native_clip_node_id':None if clip is None else clip.get('nodeId'),
            'native_clip_duration_ms':None if clip is None else ms(clip['end']-clip['start']),
            'native_start_minus_plan_ms':None if clip is None else ms(clip['start']-s['voice_start']),
            'native_gain_db':None,'native_gain_missing_reason':'Existing voice timeline receipt does not capture clip volume',
            'fade_in_ms':None,'fade_out_ms':None,'fade_missing_reason':'No separate voice fade event captured',
            'final_mix_independently_detected_onset_ms':None,
            'onset_missing_reason':'No source separation/onset detector; native placement and package complete-take checks are provided separately',
            'package_alignment_check':next((x for x in qa.get('complete_takes',[]) if x['id']==s['id']),None),
            'source_levels':wave_levels(path),
            'caption_ids':[c['id'] for c in plan.get('cues',[]) if c.get('segment',c.get('segment_id',c.get('voice_id')))==s['id']],
            'native_placement_missing_reason':None if clip else 'No unique matching clip in the saved Premiere timeline',
            'timeline_source':str(timeline_path) if timeline_path.exists() else None})
    automation=read(folder/'MUSIC_NATIVE_AUTOMATION.json') if (folder/'MUSIC_NATIVE_AUTOMATION.json').exists() else None
    for i,m in enumerate(plan.get('music',[])):
        path=Path(m['clip_path']);matches=[c for c in clips if c['name']==path.name];clip=matches[0] if len(matches)==1 else None
        actual=[]
        if automation and len(plan.get('music',[]))==1:
            for k in automation['native_readback'].get('keyframes',[]):
                actual.append({'clip_relative_ms':ms(k['time']),'stored_media_time_ms':ms(k.get('mediaSeconds')),
                    'native_stored_value':k['value'],'native_unit':'Premiere Internal Volume scalar',
                    'derived_level_db':20*math.log10(k['value'])+15 if k['value']>0 else None})
        rows.append({'event_id':'music:'+str(i),'role':'music','scene_id':None,
            'source_path':str(path),'source_sha256':file_sha(path),'source_actual_parameters':audio_probe(path),
            'planned_range_ms':[ms(m.get('timeline_start',0)),ms(m.get('timeline_start',0)+m['duration'])],
            'native_clip_range_ms':None if clip is None else [ms(clip['start']),ms(clip['end'])],
            'native_clip_duration_ms':None if clip is None else ms(clip['end']-clip['start']),
            'fade_in_ms':None,'fade_out_ms':None,
            'fade_missing_reason':'Gain automation is supplied as actual native keys; no separately labelled fade event exists',
            'configured_gain_keys':[{'clip_relative_ms':ms(k['time_seconds']),'level_db':k['level_db']} for k in m['gain_keys']],
            'native_volume_keys':actual,'native_volume_conversion':'dB=20*log10(stored_scalar)+15; existing premiere_production.music convention, not measured loudness',
            'final_mix_independently_detected_onset_ms':None,'onset_missing_reason':'Overlapping mix is not source-separated',
            'rights_status':m.get('status')})
    for r in rows:
        interval=r.get('native_clip_range_ms');r['overlapping_audio_event_ids']=[x['event_id'] for x in rows if x is not r and interval and x.get('native_clip_range_ms') and interval[0]<x['native_clip_range_ms'][1] and x['native_clip_range_ms'][0]<interval[1]]
        r['visual_event_ids']=[]
        r['visual_association_basis']='Temporal overlap of native audio range and recorded motion range; not a sound-effect trigger assertion'
    mixed=out/'review_audio/final_mix.wav';mixed.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(media),'-map','0:a:0','-vn','-c:a','pcm_s16le',str(mixed)],check=True)
    measured=wave_levels(mixed)
    log=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(media),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True).stderr
    loud=re.findall(r'Integrated loudness:\s+I:\s+([-\d.]+) LUFS',log)
    peak=re.findall(r'True peak:\s+Peak:\s+([-\d.]+) dBFS',log)
    measured.update(integrated_loudness_lufs=float(loud[-1]) if loud else None,
        true_peak_dbfs=float(peak[-1]) if peak else None,loudness_algorithm='FFmpeg ebur128=peak=true',
        loudness_missing_reason=None if loud else 'No integrated summary returned by ebur128')
    (out/'review_audio/measurement_log.txt').write_text(log,encoding='utf-8')
    return {'time_unit':'ms','events':rows,'captions':[{'caption_id':c['id'],'text':c.get('text',c.get('display_lines')),
        'configured_range_ms':[ms(c['start']),ms(c['end'])],
        'voice_event_id':c.get('segment',c.get('segment_id',c.get('voice_id'))),
        'provenance':'COMPILED_CAPTION_CONFIGURATION'} for c in plan.get('cues',[])],
        'final_mix':{'path':mixed.relative_to(out).as_posix(),'sha256':file_sha(mixed),'measurement':measured,
            'actual_parameters':audio_probe(mixed),'source_video_sha256':file_sha(media)},
        'sfx_events':[],'sfx_coverage':'No new SFX model; unclassified native clips are listed below',
        'unclassified_native_clips':[{'name':c['name'],'native_range_ms':[ms(c['start']),ms(c['end'])]} for c in clips if c['name'] not in {Path(s['voice']['padded_path']).name for s in plan['segments']}|{Path(m['clip_path']).name for m in plan.get('music',[])}],
        'perceptual_review_performed':False}


def choose_frames(scenes,events,count,fps):
    wanted=defaultdict(lambda:{'scene_ids':set(),'event_ids':set(),'purposes':set()})
    def add(f,sid,eid,purpose):
        f=max(0,min(count-1,int(f)));r=wanted[f]
        if sid:r['scene_ids'].add(sid)
        if eid:r['event_ids'].add(eid)
        r['purposes'].add(purpose)
    for s in scenes:
        a,b=s['start_frame'],s['end_frame_exclusive']
        for f in (a,(a+b)//2,b-1):add(f,s['scene_id'],None,'scene_key_frame')
    for e in events:
        if not e.get('important_for_frames'):continue
        a,b=e['start_frame'],e['end_frame_exclusive']
        for f in (a-1,a,(a+b)//2,b-1,b):add(f,e['scene_id'],e['event_id'],'before_middle_after')
        moving=[]
        for prop in e.get('properties',{}).values():
            for left,right in zip(prop.get('keys',[]),prop.get('keys',[])[1:]):
                if left['value']!=right['value']:moving.append(round((left['time_ms']+right['time_ms'])*fps/2000))
        centers=sorted(set(moving))[:3] or [(a+b)//2]
        if e.get('phases'):
            centers=sorted(set(centers+[round((p['start_ms']+p['end_ms'])*fps/2000) for p in e['phases']]))
        for center in centers:
            for f in range(center-4,center+5):add(f,e['scene_id'],e['event_id'],'consecutive_9_frame_sequence')
    return {f:{k:sorted(v) for k,v in r.items()} for f,r in sorted(wanted.items())}


def extract_frames(media,out,wanted,pts,metadata):
    from PIL import Image,ImageDraw
    directory=out/'review_frames';directory.mkdir()
    frames=list(wanted)
    select='+'.join('eq(n\\,'+str(n)+')' for n in frames)
    subprocess.run(['ffmpeg','-v','error','-n','-threads','2','-i',str(media),'-an',
        '-vf','select='+select+',scale=1280:-2','-fps_mode','passthrough','-start_number','0',
        str(directory/'frame-%06d.png')],check=True)
    actual=sorted(directory.glob('frame-*.png'))
    if len(actual)!=len(frames):raise ValueError('Final MP4 extraction did not produce every selected frame')
    rows=[]
    for path,frame in zip(actual,frames):
        with Image.open(path) as im:width,height=im.size
        rows.append({'file':path.relative_to(out).as_posix(),'sha256':file_sha(path),
            'frame_number':frame,'timestamp_ms':pts[frame]['timestamp_ms'],'source_pts':pts[frame]['source_pts'],
            'width_px':width,'height_px':height,'source_video_sha256':metadata['sha256'],
            'source':'DECODED_FINAL_MP4_FRAME_RESIZED_FOR_REVIEW',**wanted[frame]})
    scene_frames=[r for r in rows if 'scene_key_frame' in r['purposes']]
    columns=4;tw,th=320,202;sheet=Image.new('RGB',(columns*tw,math.ceil(len(scene_frames)/columns)*th),'#17181a');draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(scene_frames):
        with Image.open(out/r['file']) as im:im=im.convert('RGB');im.thumbnail((320,180));sheet.paste(im,((i%columns)*tw,(i//columns)*th))
        draw.text(((i%columns)*tw+5,(i//columns)*th+181),f"frame {r['frame_number']} | {r['timestamp_ms']:.3f} ms",fill='white')
    sheet.save(directory/'scene-index.jpg',quality=90)
    return {'time_unit':'ms','frame_numbering':'zero-based decoded presentation order','frames':rows,
        'thumbnail_index':{'file':'review_frames/scene-index.jpg','sha256':file_sha(directory/'scene-index.jpg'),
            'width_px':sheet.width,'height_px':sheet.height,'source_video_sha256':metadata['sha256'],
            'source_frame_numbers':[r['frame_number'] for r in scene_frames]},
        'coverage':'Every known scene and selected existing important events; no claim of automatic recognition of all visual motion',
        'frame_source_video_sha256':metadata['sha256']}


def validate_evidence(manifest_path):
    path=Path(manifest_path);root=path.parent;m=read(path)
    if file_sha(m['video']['path'])!=m['video']['sha256']:raise ValueError('Evidence video changed')
    docs={}
    for name,r in m['json_files'].items():
        target=root/r['path']
        if not target.resolve().is_relative_to(root.resolve()) or file_sha(target)!=r['sha256']:raise ValueError('Evidence JSON changed or escaped its output directory')
        docs[name]=read(target)
    def checked_relative(relative,expected):
        target=(root/relative).resolve()
        if not target.is_relative_to(root.resolve()) or file_sha(target)!=expected:
            raise ValueError('Evidence file changed or escaped its output directory: '+str(relative))
    for r in docs['frame_index']['frames']:
        if r['source_video_sha256']!=m['video']['sha256']:raise ValueError('Frame is not bound to the final movie')
        checked_relative(r['file'],r['sha256'])
    thumb=docs['frame_index']['thumbnail_index'];checked_relative(thumb['file'],thumb['sha256'])
    for r in m.get('source_snapshots',[]):
        checked_relative(r['path'],r['sha256'])
    a=docs['audio_manifest']['final_mix']
    checked_relative(a['path'],a['sha256'])
    for a in docs['audio_manifest']['events']:
        if file_sha(a['source_path'])!=a['source_sha256']:raise ValueError('Source audio changed')
        asset=a.get('timeline_asset')
        if asset and file_sha(asset['path'])!=asset['sha256']:raise ValueError('Consumed timeline audio changed')
    event_ids={e['event_id'] for e in docs['motion_manifest']['events']}
    scene_ids={s['scene_id'] for s in docs['timeline_manifest']['scenes']}
    audio_ids={a['event_id'] for a in docs['audio_manifest']['events']}
    for s in docs['timeline_manifest']['scenes']:
        if not set(s['motion_event_ids'])<=event_ids or not set(s['voice_event_ids']+s['music_event_ids'])<=audio_ids:
            raise ValueError('Scene links reference unknown motion/audio')
    for e in docs['motion_manifest']['events']:
        if not set(e.get('audio_event_ids',[]))<=audio_ids or not set(e.get('related_event_ids',[]))<=event_ids:
            raise ValueError('Motion links reference unknown events')
    for f in docs['frame_index']['frames']:
        if not set(f['event_ids'])<=event_ids or not set(f['scene_ids'])<=scene_ids:raise ValueError('Frame links reference an unknown scene/event')
    return {'status':'PASS','scope':'JSON/path/hash/cross-reference structure only; no quality judgment',
            'images':len(docs['frame_index']['frames'])+1,'frame_images':len(docs['frame_index']['frames']),
            'scenes':len(scene_ids),'events':len(event_ids)}


def export_review_evidence(folder,qa,probe_result=None):
    """Called by normal package after the existing actual same-version checks."""
    folder=Path(folder).resolve();media=Path(qa['media']).resolve();plan=read(folder/'AV_PLAN.json');native=read(folder/'native-identity.json')
    if qa['sha256']!=file_sha(media) or qa.get('plan_sha256')!=file_sha(folder/'AV_PLAN.json'):
        raise ValueError('Evidence requires the actual current same-version final MP4')
    snapshot=read(folder/'EVIDENCE_NATIVE_MOTION.json') if (folder/'EVIDENCE_NATIVE_MOTION.json').exists() else None
    if snapshot and (snapshot['plan_sha256']!=qa['plan_sha256'] or snapshot['native_identity_sha256']!=file_sha(folder/'native-identity.json')):
        raise ValueError('Native evidence snapshot belongs to another production')
    if snapshot and data_sha({k:v for k,v in snapshot.items() if k!='parameters_sha256'})!=snapshot['parameters_sha256']:
        raise ValueError('Native evidence parameter bytes changed')
    binding={'video':qa['sha256'],'plan':qa['plan_sha256'],'native':file_sha(folder/'native-identity.json'),
        'motion':None if snapshot is None else snapshot['parameters_sha256'],
        'premiere_timeline':file_sha(folder/'PR_TIMELINE.json') if (folder/'PR_TIMELINE.json').exists() else None}
    out=media.parent/'review_evidence'/(media.stem+'-'+data_sha(binding)[:12])
    manifest=out/'review_evidence_manifest.json'
    if manifest.exists():validate_evidence(manifest);return str(manifest)
    if out.exists():raise FileExistsError('Incomplete evidence directory retained for inspection: '+str(out))
    out.mkdir(parents=True)
    probe=probe_result or probe_media(media);pts=frame_timestamps(media)
    if not pts or len(pts)!=qa['frames'] or any(r['timestamp_ms'] is None for r in pts):
        raise ValueError('Current authored output requires a complete actual decoded frame-PTS inventory')
    meta=metadata(media,probe,pts,folder,qa);fps=meta['video']['frame_rate']['fps']
    picture=read(folder/('MASTER_PICTURE_RECEIPT.json' if qa.get('formal_4k_rendered') else 'PICTURE_RECEIPT.json'))
    meta['render'].update(picture_receipted_frames=picture.get('frames'),
        picture_completion_state=('ALL_NATIVE_PARTS_RECEIPTED_DONE' if all(r.get('done') is True for r in picture['parts']) else None)
            if picture.get('parts') else None,
        picture_completion_missing_reason=None if picture.get('parts') else 'Historical picture receipt has no individual part states')
    comp=next((c for c in snapshot['compositions'] if c['comp_id']==picture['comp_id']),None) if snapshot else None
    mot=motion(plan,native,comp,folder,fps);tim=timeline(plan,qa,pts,mot['events'],native,folder,fps)
    aud=audio(plan,qa,folder,out,media)
    for event in mot['events']:
        event['audio_event_ids']=[a['event_id'] for a in aud['events'] if a.get('native_clip_range_ms') and a['native_clip_range_ms'][0]<event['end_ms'] and event['start_ms']<a['native_clip_range_ms'][1]]
    for a in aud['events']:
        a['visual_event_ids']=[e['event_id'] for e in mot['events'] if a['event_id'] in e['audio_event_ids']]
    layers={l['name']:l for l in comp['layers']} if comp else {}
    for caption in aud['captions']:
        layer=layers.get('CAPTION_'+caption['caption_id'])
        caption['native_range_ms']=None if layer is None else [layer['in_ms'],layer['out_ms']]
        caption['native_element_id']=None if layer is None else layer['id']
        caption['native_missing_reason']=None if layer else 'No matching native layer readback for this output composition'
    wanted=choose_frames(tim['scenes'],mot['events'],len(pts),fps)
    index=extract_frames(media,out,wanted,pts,meta)
    docs={'video_metadata':meta,'timeline_manifest':tim,'motion_manifest':mot,'audio_manifest':aud,'frame_index':index}
    files={}
    for name,value in docs.items():
        dest=out/(name+'.json');write(dest,value);files[name]={'path':dest.name,'sha256':file_sha(dest)}
    snapshots=[]
    sources=[(role,Path(qa[role])) for role in ('native_project','premiere_project')]
    sources.extend((name,folder/name) for name in ('AV_AUTHOR.json','AV_PLAN.json','native-identity.json',
        'EVIDENCE_NATIVE_MOTION.json','PR_TIMELINE.json','MUSIC_NATIVE_AUTOMATION.json',
        'CHALLENGE_NATIVE_READBACK.json','SYMBOL_NATIVE_READBACK.json',
        'DIRECT_EXTRACTION_NATIVE_READBACK.json','READING_THINKING_NATIVE_READBACK.json',
        'READING_CONTINUITY_NATIVE_1.json','READING_CONTINUITY_NATIVE_703.json',
        'NATIVE_AUDIO_DELAY.json','EPISODE_SCRIPT.md','EPISODE_SUBTITLES.srt',
        'MASTER_DELIVERY_QA.json' if qa.get('formal_4k_rendered') else 'DELIVERY_QA.json',
        'MASTER_PICTURE_RECEIPT.json' if qa.get('formal_4k_rendered') else 'PICTURE_RECEIPT.json') if (folder/name).exists())
    sources.extend(('native_source',p) for p in sorted((folder/'native-source').glob('*.jsx')))
    for role,source in sources:
        target=out/'source_snapshots'/source.name;target.parent.mkdir(exist_ok=True)
        if qa.get(role+'_sha256') and file_sha(source)!=qa[role+'_sha256']:
            raise ValueError('Project changed since the same-version final package checks: '+role)
        shutil.copy2(source,target);snapshots.append({'role':role,'path':target.relative_to(out).as_posix(),
            'sha256':file_sha(target),'original_source_path':str(source),
            'normalization':'Verbatim source artifact with original fields/units; normalized manifests above use ms',
            'scope':'Exact bytes at evidence capture; later application Save may change original project metadata'})
    root=Path(__file__).resolve().parents[1]
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit=None
    tools={}
    for name in ('ffmpeg','ffprobe'):
        tools[name]=subprocess.check_output([name,'-version'],text=True).splitlines()[0]
    result={'evidence_version':VERSION,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'video':{'path':str(media),'sha256':qa['sha256']},'repository_commit':commit,
        'generation_binding':binding,'tools':tools,'python_version':sys.version.split()[0],
        'units':{'times':'ms; frame indices zero-based with exclusive end',
            'native_expressions':'Verbatim AE expression strings use original seconds, explicitly labelled; normalized event/key/sample times are ms',
            'spatial':'Each motion event records its coordinate system, reference and property units'},
        'json_files':files,'source_snapshots':snapshots,'image_directory':'review_frames',
        'image_count':len(index['frames'])+1,'frame_image_count':len(index['frames']),'scene_count':len(tim['scenes']),
        'scene_count_basis':'Existing scene units with final decoded-frame correspondence; not automatic visual cut detection',
        'animation_event_count':len(mot['events']),'audio_event_count':len(aud['events']),
        'animation_event_count_basis':'Unique event records for native animated layers, focus windows, challenges and recipes; overlapping representations are linked, not distinct-action claims',
        'parameter_completeness':{'final_video_parameters':'FFPROBE_MEASURED','motion':'NATIVE_ENGINE_READBACK' if comp else 'HISTORICAL_PARTIAL_READBACK',
            'scene_timing':'PLAN_FRAMES_MAPPED_TO_FINAL_MEASURED_PTS','audio_timing':'NATIVE_PREMIERE_CLIP_READBACK',
            'mixed_loudness':'FINAL_AUDIO_MEASURED','independent_scene_detection':None,'independent_object_tracking':None},
        'missing_parameters':[{'field':'independent_scene_boundaries','reason':'No scene detector or embedded semantic scene labels'},
            {'field':'final_pixel_object_trajectory','reason':'No object tracking; actual native properties and final frame sequences supplied'},
            {'field':'voice_native_gain','reason':'Existing voice timeline receipt does not capture volume'},
            {'field':'isolated_final_mix_voice_onset','reason':'No source separation/onset detection'},
            {'field':'render_wall_clock_start_end','reason':'Not recorded by existing renderer; file timestamps are not substituted'}],
        'generated_successfully':True,'structure_validation':{'status':'PENDING'},
        'review_or_quality_scoring_performed':False,'public_render_ready':False}
    write(manifest,result);result['structure_validation']=validate_evidence(manifest);write(manifest,result)
    write(folder/'REVIEW_EVIDENCE_RECEIPT.json',{'manifest':str(manifest),'sha256':file_sha(manifest),'video_sha256':qa['sha256']})
    return str(manifest)
