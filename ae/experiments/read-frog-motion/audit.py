"""Audit the realized A/B, independently of the rig's declared design intent."""
import json
import math
from pathlib import Path
import sys
from run import Trial, read, write, sha256

def run(folder):
    t=Trial(folder);n=t.native();i=t.i
    spec={'A':n['A_source'],'B':n['B_source'],'parent':i['native_master_id'],'wrappers':[n['A'],n['B']],
          'start':i['clip_start'],'frames':288,'chunks':n['rig']['chunks']}
    code=r'''
var S=SPEC,aa=app.project.itemByID(S.A),bb=app.project.itemByID(S.B),parent=app.project.itemByID(S.parent),result={wrappers:[],text:[],curves:[],chunks:[],errors:[],native_eases:[],A_parent_max_difference:0};
function err(prop){if(prop&&prop.canSetExpression&&prop.expressionEnabled&&prop.expressionError)result.errors.push(prop.expressionError);}
function scan(g){for(var j=1;j<=g.numProperties;j++){var p=g.property(j);if(p.propertyType===PropertyType.PROPERTY)err(p);else scan(p);}}
function delta(a,b){if(a instanceof Array){var m=0;for(var j=0;j<a.length;j++)m=Math.max(m,Math.abs(a[j]-b[j]));return m;}return Math.abs(a-b);}
for(var j=0;j<S.wrappers.length;j++){var c=app.project.itemByID(S.wrappers[j]),aud=[];for(var k=1;k<=c.numLayers;k++){var l=c.layer(k);if(l.source instanceof FootageItem&&l.source.hasAudio)aud.push({file:l.source.file.fsName,start:l.startTime,inPoint:l.inPoint,outPoint:l.outPoint});}result.wrappers.push({id:c.id,width:c.width,height:c.height,fps:c.frameRate,duration:c.duration,audio:aud});}
var names=['READING_CAMERA','READING_FOCUS','SOURCE_LIFT_SC03','CANDIDATE_FLIGHT_SC03','fitbit-source-291','EXTRACT_SC03_fitbit-source-291'];
for(var frame=0;frame<=S.frames;frame++){
 var at=S.start+frame/24,row={frame:frame,time:at,A:{},B:{}};
 for(var v=0;v<2;v++){var c=v?bb:aa,o=v?row.B:row.A;for(var j=0;j<names.length;j++){var l=c.layer(names[j]),p=l.transform.position,ori=l instanceof CameraLayer?l.transform.pointOfInterest:l.transform.orientation;o[names[j]]={position:p.valueAtTime(at,false),orientation:ori.valueAtTime(at,false),scale:l.transform.scale?l.transform.scale.valueAtTime(at,false):null};if(v===0){var pl=parent.layer(names[j]);result.A_parent_max_difference=Math.max(result.A_parent_max_difference,delta(p.valueAtTime(at,false),pl.transform.position.valueAtTime(at,false)),delta(ori.valueAtTime(at,false),(pl instanceof CameraLayer?pl.transform.pointOfInterest:pl.transform.orientation).valueAtTime(at,false)));}}}
 result.curves.push(row);
}
for(var j=1;j<=aa.numLayers;j++){var al=aa.layer(j);if(!(al instanceof TextLayer))continue;var bl=bb.layer(al.name),ad=al.property('Source Text').value,bd=bl.property('Source Text').value;result.text.push({name:al.name,A:ad.text,B:bd.text,fontA:ad.font,fontB:bd.font,inA:al.inPoint,inB:bl.inPoint,outA:al.outPoint,outB:bl.outPoint});}
for(var j=0;j<S.chunks.length;j++){var x=S.chunks[j],l=bb.layer(x.layer),anim=l.property('ADBE Text Properties').property('ADBE Text Animators').property(x.animator),sel=anim.property('ADBE Text Selectors').property(1),sc=anim.property('ADBE Text Animator Properties').property('ADBE Text Scale 3D'),row={text:l.property('Source Text').value.text.slice(x.start,x.end),start:sel.property('ADBE Text Index Start').value,end:sel.property('ADBE Text Index End').value,expression:sc.expression,values:[]};
 for(var k=-1;k<=33;k++){var at=x.center-x.attack+(x.attack+x.release)*k/32;row.values.push({time:at,value:sc.valueAtTime(at,false)});}row.peak=sc.valueAtTime(x.center,false);err(sc);result.chunks.push(row);}
var path=bb.layer('RF_CARRY_SCREEN_PATH').transform.position;for(var k=1;k<=path.numKeys;k++)result.native_eases.push({time:path.keyTime(k),value:path.keyValue(k),influence_in:path.keyInTemporalEase(k)[0].influence,influence_out:path.keyOutTemporalEase(k)[0].influence,speed_in:path.keyInTemporalEase(k)[0].speed,speed_out:path.keyOutTemporalEase(k)[0].speed,tangent_in:path.keyInSpatialTangent(k),tangent_out:path.keyOutSpatialTangent(k)});
for(var j=1;j<=bb.numLayers;j++)scan(bb.layer(j));
var opt=bb.layer('READING_CAMERA').property('ADBE Camera Options Group');result.optics={renderer:bb.renderer,motionBlur:bb.motionBlur,shutterAngle:bb.shutterAngle,shutterPhase:bb.shutterPhase,dof:opt.property('ADBE Camera Depth of Field').value,focus_expression:opt.property('ADBE Camera Focus Distance').expression};
return result;
'''.replace('SPEC',json.dumps(spec,ensure_ascii=False))
    r=t.h.js(code);write(t.folder/'NATIVE_AUDIT_READBACK.json',r)
    assert not r['errors'],r['errors']
    assert r['A_parent_max_difference']<.0001
    for c in r['wrappers']:
        assert [c['width'],c['height'],c['fps'],round(c['duration']*24)]==[3840,2160,24,288]
        assert len(c['audio'])==1
        a=c['audio'][0]
        assert Path(a['file']).resolve()==Path(i['voice']['voice']['path']).resolve()
        assert abs(a['start']-(i['voice']['voice_start']-i['clip_start']))<.0001
        assert abs(a['outPoint']-a['inPoint']-(i['voice']['voice_end']-i['voice']['voice_start']))<.0001
    for row in r['text']:
        assert row['A']==row['B'] and row['fontA']==row['fontB']
        assert abs(row['inA']-row['inB'])<.0001 and abs(row['outA']-row['outB'])<.0001
    for decl,actual in zip(n['rig']['chunks'],r['chunks']):
        assert [actual['text'],actual['start'],actual['end'],actual['expression']]==[decl['text'],decl['start'],decl['end'],decl['expression']]
        assert abs(actual['peak'][0]-104)<.0001 and abs(actual['peak'][1]-104)<.0001
        for sample in actual['values']:
            v=sample['value'];assert 100-1e-5<=v[0]<=104+1e-5 and abs(v[1]-v[0])<1e-5 and v[2]==100
        assert abs(actual['values'][0]['value'][0]-100)<1e-5 and abs(actual['values'][-1]['value'][0]-100)<1e-5
    assert r['native_eases'][0]['influence_out']==22 and r['native_eases'][1]['influence_in']==72
    assert r['optics']['dof'] and 'READING_FOCUS' in r['optics']['focus_expression']
    # Meaningful regression: moving the camera must not lose the remembered
    # option behind the caption band. Project its anchor from actual 3D values.
    def project(point,camera):
        import numpy as np
        pos=np.array(camera['position'],dtype=float);f=np.array(camera['orientation'],dtype=float)-pos;f/=np.linalg.norm(f)
        right=np.cross([0,1,0],f);right/=np.linalg.norm(right);up=np.cross(f,right)
        v=np.array(point)-pos;depth=float(v@f)
        return [1920+float(v@right)*4500/depth,1080+float(v@up)*4500/depth]
    ranges={}
    for variant in ('A','B'):
        q=[project(row[variant]['CANDIDATE_FLIGHT_SC03']['position'],row[variant]['READING_CAMERA']) for row in r['curves'][:-1]]
        ranges[variant]={'x_min':min(x[0] for x in q),'x_max':max(x[0] for x in q),'y_min':min(x[1] for x in q),'y_max':max(x[1] for x in q),'anchor_outside_reading_area_frames':sum(not(96<=x[0]<=3400 and 100<=x[1]<=1790) for x in q)}
    assert ranges['B']['anchor_outside_reading_area_frames']==0,ranges['B']
    # The final comparative layout is still, including camera, focus and all
    # moving logical objects; a text focus pulse is tracked independently.
    hold=[x for x in r['curves'] if x['time']>=i['source_scene']['settled']+1/24]
    max_hold=0
    for name in ('READING_CAMERA','READING_FOCUS','SOURCE_LIFT_SC03','CANDIDATE_FLIGHT_SC03'):
        for row in hold:
            for key in ('position','orientation'):
                max_hold=max(max_hold,max(abs(a-b) for a,b in zip(row['B'][name][key],hold[0]['B'][name][key])))
    assert max_hold<.002,max_hold
    report={'status':'PASS','native_identity_sha256':sha256(t.folder/'NATIVE_IDENTITY.json'),'format':[3840,2160,24],
        'A_matches_parent_native_transforms':True,'A_B_exact_text_fonts_and_disclosure_times':True,'same_intact_audio_take':True,
        'chunk_count':len(r['chunks']),'chunk_focus':'same time function within each exact chunk; sequential centers; 100–104%; no elastic overshoot',
        'expression_errors':[],'sampled_frames_per_variant':289,'candidate_anchor_screen_ranges':ranges,'settled_transform_max_drift':max_hold,
        'motion_blur_flag_is_not_pixel_confirmation':True,'human_motion_aesthetic_review':'PENDING','human_listening_review':'PENDING','teaching_scope':'existing supported A; no final answer','production_integration':'NOT_APPLIED'}
    write(t.folder/'NATIVE_QA.json',report);return report

if __name__=='__main__':print(json.dumps(run(sys.argv[1]),ensure_ascii=False))
