"""Read the realized AEP, not merely the builder's intended parameters."""
from pathlib import Path
import json,sys
import numpy as np
from run import Trial,read,write,sha256

def check_native_curve_receipt(folder):
    p=Path(folder);n=read(p/'NATIVE_IDENTITY.json');b=read(p/'NATIVE_READBACK.json')['comps']['B']
    controllers={c['name']:c['position'] for c in b['controllers']}
    actual_by_name={'camera_attention':controllers['MQ_CAMERA_AIM'],'camera_offset':controllers['MQ_CAMERA_OFFSET'],'option_carry':controllers['MQ_OPTION_SCREEN'],'source_extract_and_return':b['liftPosition'],'source_follow_through':b['liftOrientation']}
    rows=[];boundary=[];quantized=[]
    for curve in n['rig']['native_curves']:
        if curve['name'] not in actual_by_name:continue
        actual=actual_by_name[curve['name']];assert len(actual)==len(curve['keys'])
        for index,(expected,k) in enumerate(zip(curve['keys'],actual)):
            time_delta=abs(expected['t']-k['t'])
            assert time_delta<1/(24*1024)
            if time_delta>1e-6:quantized.append({'curve':curve['name'],'requested':expected['t'],'native':k['t'],'delta_seconds':time_delta})
            assert np.max(np.abs(np.array(expected['v'])-np.array(k['v'])))<.001
            for side,field in [('incoming','influenceIn'),('outgoing','influenceOut')]:
                for e in k[side]:
                    # AE reports zero for the unused incoming speed at the
                    # first key. There is no preceding animated segment there.
                    if index==0 and side=='incoming' and e['speed']==0 and expected['speed']:
                        boundary.append({'curve':curve['name'],'time':k['t'],'native_unused_incoming_speed':0,'requested':expected['speed']})
                    else:assert abs(e['speed']-expected['speed'])<.001,(curve['name'],k['t'],side,e,expected)
                    assert abs(e['influence']-expected[field])<.001
            rows.append({'curve':curve['name'],'time':k['t'],'used_temporal_handles_match':True})
    result={'status':'PASS','native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'native_readback_sha256':sha256(p/'NATIVE_READBACK.json'),'keys_checked':len(rows),'keys':rows,'unused_boundary_handle_readback':boundary,'subframe_time_quantization':quantized,'scope':'Native position/orientation key values, times, used temporal speeds and influences; aesthetic judgment remains separate'}
    write(p/'NATIVE_CURVE_QA.json',result);return result

def main(folder):
    trial=Trial(folder);n=trial.native();i=trial.i;p=Path(folder)
    code=r'''
var ids=IDS,I=INPUT_DATA,answer={comps:{},errors:[]};
function keyInfo(p){var a=[];for(var k=1;k<=p.numKeys;k++){var ins=p.keyInTemporalEase(k),outs=p.keyOutTemporalEase(k),r={t:p.keyTime(k),v:p.keyValue(k),incoming:[],outgoing:[]};for(var j=0;j<ins.length;j++)r.incoming.push({speed:ins[j].speed,influence:ins[j].influence});for(var j=0;j<outs.length;j++)r.outgoing.push({speed:outs[j].speed,influence:outs[j].influence});if(p.propertyValueType===PropertyValueType.ThreeD_SPATIAL){r.spatialIn=p.keyInSpatialTangent(k);r.spatialOut=p.keyOutSpatialTangent(k);}a.push(r);}return a;}
function errors(g,path){for(var j=1;j<=g.numProperties;j++){var x=g.property(j);if(x.propertyType===PropertyType.PROPERTY){if(x.canSetExpression&&x.expressionEnabled&&x.expressionError)answer.errors.push({path:path+'/'+x.name,error:x.expressionError});}else errors(x,path+'/'+x.name);}}
for(var variant in ids){var c=app.project.itemByID(ids[variant]),o={width:c.width,height:c.height,fps:c.frameRate,renderer:c.renderer,motionBlur:c.motionBlur,shutter:c.shutterAngle,phase:c.shutterPhase,texts:[],frames:[],controllers:[],chunks:[],source_layers:[]};
 var cam=c.layer('READING_CAMERA'),f=c.layer('READING_FOCUS'),g=c.layer('SOURCE_LIFT_SC10'),ch=c.layer('CANDIDATE_FLIGHT_SC10'),q=c.layer('CARRIED_QUERY_SC09L'),source=c.layer('camp-source-781'),ex=c.layer('EXTRACT_SC10_camp-source-781');
 o.hierarchy={cameraParent:cam.parent?cam.parent.name:null,extractedParent:ex.parent?ex.parent.name:null,sourceComment:source.comment,extractComment:ex.comment,groupComment:g.comment,optionComment:ch.comment,originalSourcePosition:source.transform.position.value,cloneLocalPosition:ex.transform.position.value,cloneOut:ex.outPoint,sourceText:source.property('Source Text').value.text,extractedText:ex.property('Source Text').value.text,zoom:cam.cameraOption.zoom.value,depthOfField:cam.cameraOption.depthOfField.value,focusExpression:cam.cameraOption.focusDistance.expression};
 for(var j=1;j<=c.numLayers;j++){var l=c.layer(j);if(l.property('ADBE Text Properties')){var st=l.property('Source Text'),v=st.value,row={name:l.name,text:v.text,font:v.font,size:v.fontSize,inPoint:l.inPoint,outPoint:l.outPoint,keys:[]};for(var k=1;k<=st.numKeys;k++){var d=st.keyValue(k);row.keys.push([st.keyTime(k),d.text,d.font,d.fontSize]);}o.texts.push(row);var aa=l.property('ADBE Text Properties').property('ADBE Text Animators');for(var k=1;k<=aa.numProperties;k++)if(aa.property(k).name.indexOf('RF_CHUNK_')===0){var an=aa.property(k),sel=an.property('ADBE Text Selectors').property(1),sc=an.property('ADBE Text Animator Properties').property('ADBE Text Scale 3D');o.chunks.push({layer:l.name,name:an.name,start:sel.property('ADBE Text Index Start').value,end:sel.property('ADBE Text Index End').value,expression:sc.expression});}}
 if(l.name.indexOf('MQ_')===0)o.controllers.push({name:l.name,parent:l.parent?l.parent.name:null,position:keyInfo(l.transform.position)});
 if(l.name.indexOf('camp-source-')===0)o.source_layers.push({name:l.name,position:l.transform.position.value,scale:l.transform.scale.value,orientation:l.transform.orientation.value});
 }
 for(var fno=0;fno<I.clip_frames;fno++){var t=Math.min(I.clip_start+fno/24,I.last_source_time);o.frames.push({frame:fno,t:t,cam:cam.transform.position.valueAtTime(t,false),aim:cam.transform.pointOfInterest.valueAtTime(t,false),focus:f.transform.position.valueAtTime(t,false),lift:g.transform.position.valueAtTime(t,false),turn:g.transform.orientation.valueAtTime(t,false),choice:ch.transform.position.valueAtTime(t,false),choiceTurn:ch.transform.orientation.valueAtTime(t,false),query:q.transform.position.valueAtTime(t,false),aperture:cam.cameraOption.aperture.valueAtTime(t,false),sourceOpacity:source.transform.opacity.valueAtTime(t,false)});}
 if(variant==='B'){o.liftPosition=keyInfo(g.transform.position);o.liftOrientation=keyInfo(g.transform.orientation);o.chunkSamples=[];for(var ci=0;ci<CHUNKS.length;ci++){var ck=CHUNKS[ci],layer=c.layer(ck.layer),prop=layer.property('ADBE Text Properties').property('ADBE Text Animators').property(ck.animator).property('ADBE Text Animator Properties').property('ADBE Text Scale 3D');o.chunkSamples.push({text:layer.property('Source Text').value.text.slice(ck.start,ck.end),before:prop.valueAtTime(ck.center-.4,false),peak:prop.valueAtTime(ck.center,false),after:prop.valueAtTime(ck.center+.5,false)});}for(var j=1;j<=c.numLayers;j++)errors(c.layer(j),c.layer(j).name);}
 answer.comps[variant]=o;
}
answer.wrappers=[];for(var k=0;k<WRAPPERS.length;k++){var c=app.project.itemByID(WRAPPERS[k]),o={width:c.width,height:c.height,fps:c.frameRate,duration:c.duration,audio:[],source_times:[]};for(var j=1;j<=c.numLayers;j++){var l=c.layer(j);if(l.source&&l.source.file&&l.hasAudio)o.audio.push({path:l.source.file.fsName,start:l.startTime,end:l.outPoint});if(l.source instanceof CompItem){if(!l.timeRemapEnabled)throw Error('Missing terminal hold mapping');for(var f=0;f<I.clip_frames;f++)o.source_times.push(l.property('ADBE Time Remapping').valueAtTime(f/24,false));}}answer.wrappers.push(o);}return answer;
'''
    for token,value in [('INPUT_DATA',i),('CHUNKS',n['rig']['chunks']),('WRAPPERS',[n['A'],n['B']]),('IDS',{'parent':i['native_master_id'],'A':n['A_source'],'B':n['B_source']})]:code=code.replace(token,json.dumps(value,ensure_ascii=False))
    d=trial.h.js(code,timeout=240);write(p/'NATIVE_READBACK.json',d);check_native_curve_receipt(p);a=d['comps']['A'];b=d['comps']['B'];parent=d['comps']['parent']
    assert not d['errors'],d['errors']
    assert a['texts']==parent['texts']==b['texts'],'Exact native text/font/disclosure changed'
    assert a['source_layers']==b['source_layers']==parent['source_layers'],'Original source geometry changed'
    for key in ('cam','aim','focus','lift','turn','choice','choiceTurn','query'):
        assert np.max(np.abs(np.asarray([r[key] for r in a['frames']])-np.asarray([r[key] for r in parent['frames']])))<1e-7,('A differs from original',key)
    assert b['hierarchy']['cameraParent']=='MQ_CAMERA_RIG' and b['hierarchy']['extractedParent']=='SOURCE_LIFT_SC10'
    assert b['hierarchy']['depthOfField'] and 'READING_FOCUS' in b['hierarchy']['focusExpression']
    for key in ('sourceComment','extractComment','groupComment','optionComment','sourceText','extractedText'):
        assert b['hierarchy'][key]==a['hierarchy'][key],key
    assert b['hierarchy']['sourceText']==b['hierarchy']['extractedText']
    expected_chunk_count=17 if i.get('reading_focus_revision')==2 else 12
    assert len(b['chunks'])==len(n['rig']['chunks'])==expected_chunk_count
    for sample,expected in zip(b['chunkSamples'],n['rig']['chunks']):
        assert sample['text']==expected['text']
        assert np.max(np.abs(np.asarray(sample['peak'])-[104,104,100]))<1e-4
        assert sample['before']==sample['after']==[100,100,100]
    for w in d['wrappers']:
        assert [w['width'],w['height'],w['fps']]==[3840,2160,24] and abs(w['duration']-i['clip_frames']/24)<1e-6
        expected_times=np.minimum(i['clip_start']+np.arange(i['clip_frames'])/24,i['last_source_time'])
        assert len(w['source_times'])==i['clip_frames'] and np.max(np.abs(np.asarray(w['source_times'])-expected_times))<1e-5
        for take in i['voices']:
            found=[x for x in w['audio'] if Path(x['path']).resolve()==Path(take['voice']['path']).resolve()]
            assert len(found)==1 and abs(found[0]['start']-(take['voice_start']-i['clip_start']))<1e-5
    def project(row,point):
        c=np.asarray(row['cam'],float);f=np.asarray(row['aim'],float)-c;f/=np.linalg.norm(f);right=np.cross([0,1,0],f);right/=np.linalg.norm(right);up=np.cross(f,right);v=np.asarray(point,float)-c;z=np.dot(v,f);return [1920+np.dot(v,right)*b['hierarchy']['zoom']/z,1080+np.dot(v,up)*b['hierarchy']['zoom']/z]
    speeds={};metrics={}
    for tag,comp in [('A',a),('B',b)]:
        pts=np.asarray([r['cam'] for r in comp['frames']]);v=np.linalg.norm(np.diff(pts,axis=0),axis=1)*24
        speeds[tag]=v;selected=[r for r in comp['frames'] if i['source_scene']['candidate_start']<=r['t']<i['source_scene']['event_time']];xy=np.asarray([project(r,r['choice']) for r in selected]);metrics[tag]={'peak_camera_speed':float(v.max()),'option_anchor_outside_frame':int(np.sum((xy[:,0]<0)|(xy[:,0]>3840)|(xy[:,1]<0)|(xy[:,1]>2160)))}
    scan=[r for r in b['frames'] if r['t']<=155.25]
    assert np.ptp([r['aim'][0] for r in scan])<.001 and np.min(np.diff([r['aim'][1] for r in scan]))>=-.001,'Search reversed or shook laterally'
    continuous={}
    for t in (149.416666666667,153.625,165.625):
        k=round((t-i['clip_start'])*24);continuous[str(t)]={tag:float(speeds[tag][k-1:k+1].min()) for tag in ('A','B')}
        assert continuous[str(t)]['B']>20,'Unintended intermediate stop'
    quiet=[r for r in b['frames'] if 171<=r['t']<176.1666666]
    drift=max(float(np.ptp(np.asarray([r[key] for r in quiet]),axis=0).max()) for key in ('cam','aim','lift'))
    assert drift<.001,drift
    final=b['frames'][-1];assert abs(final['sourceOpacity']-100)<.001
    origin=np.asarray(b['hierarchy']['originalSourcePosition']);returned=np.asarray(final['lift'])+np.asarray(b['hierarchy']['cloneLocalPosition']);assert np.max(np.abs(returned-origin))<.001
    assert abs(b['hierarchy']['cloneOut']-i['last_source_time'])<1e-6
    # Post-decision motion and its event boundary remain the original authority.
    for ra,rb in zip(a['frames'],b['frames']):
        # At the exact event boundary AE's expression clock and native key
        # time differ by floating precision. 0.001 world units is subpixel;
        # later frames must still follow the unchanged elimination trajectory.
        if ra['t']>=i['source_scene']['event_time']:assert np.max(np.abs(np.asarray(ra['choice'])-rb['choice']))<.001
    table=[{'frame':j+1,'t':(j+1)/24,'A_speed':float(speeds['A'][j]),'B_speed':float(speeds['B'][j])} for j in range(len(speeds['A']))];write(p/'CAMERA_SPEEDS.json',table)
    result={'status':'PASS','native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'A_matches_original':True,'same_text_fonts_disclosure_and_original_objects':True,'same_complete_audio_takes':True,'native_3d_and_null_hierarchy':True,'chunk_count':expected_chunk_count,'expression_errors':d['errors'],'sampled_frames_per_variant':i['clip_frames'],'search_monotonic_vertical':True,'intermediate_camera_speed':continuous,'camera_metrics':metrics,'reading_position_drift':drift,'source_return_handoff':'same original position and full source opacity; clone ends at original handoff','decision':'existing A elimination, no final answer','human_aesthetic_review':'PENDING','human_listening_review':'PENDING','production_integration':'NOT_APPLIED'}
    write(p/'NATIVE_QA.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main(sys.argv[1])
