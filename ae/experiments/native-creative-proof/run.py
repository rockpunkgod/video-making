"""One custom SYNTHETIC AE proof, deliberately separate from production entrypoints."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from video_contracts import read, sha, write
from ae_production.bridge import JunkdogeClient
from ae_production.execution import mutation_call

HERE = Path(__file__).resolve().parent


def file_sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def validate_scene(scene):
    if (scene['kind'] != 'synthetic_ae_visual_research' or scene['method_id'] is not None
            or scene['not_a_teaching_asset'] is not True
            or any(scene[k] is not False for k in ('production_eligible','public_render_ready'))
            or any(v is not False for v in scene['claims'].values())):
        raise ValueError('Independent explicitly non-teaching SYNTHETIC input required')
    position = 0; ids = set()
    for obj in scene['objects']:
        if (obj['id'] in ids or obj['start'] != position or obj['end'] <= position
                or scene['sentence'][obj['start']:obj['end']] != obj['text']
                or obj['role'] not in ('core','supplied_modifier')):
            raise ValueError('Exact ordered source partition and unique identities required')
        ids.add(obj['id']); position = obj['end']
        if obj['role'] == 'supplied_modifier':
            if obj['protected'] or obj['disposition'] != 'deferred' or obj['restore_to'] != 'original_source_position':
                raise ValueError('Protected source cannot be peeled or deferred source destroyed')
    if position != len(scene['sentence']) or ''.join(o['text'] for o in scene['objects']) != scene['sentence']:
        raise ValueError('All original characters must survive')
    cores = {o['id'] for o in scene['objects'] if o['role'] == 'core' and o['protected']}
    if len(cores) != 3 or any(o['attachment'] not in cores for o in scene['objects'] if o['role'] == 'supplied_modifier'):
        raise ValueError('This custom proof requires three protected cores and supplied attachments')
    return scene


def validate_presentation(presentation, scene):
    """A small presentation overlay, never an alternative source of text or roles."""
    required={'id','duration','time_map','voice_starts','parks','carrier_rest_opacity',
              'text_rest_opacity','context_rest_opacity','side_rest_opacity'}
    attached=presentation.get('id') in ('SYNTHETIC-ATTACHMENT-LAYOUT-R5','SYNTHETIC-ATTACHMENT-LAYOUT-R5-FAST')
    if attached:required=(required-{'parks'})|{'attachment_layout'}
    if set(presentation)!=required or presentation['id'] not in ('SYNTHETIC-RHYTHM-TEXTURE-R4','SYNTHETIC-ATTACHMENT-LAYOUT-R5','SYNTHETIC-ATTACHMENT-LAYOUT-R5-FAST'):
        raise ValueError('Use the explicit synthetic presentation contract')
    def finite(value):
        return type(value) in (int,float) and math.isfinite(value)
    duration=presentation['duration']
    if not finite(duration) or not 20<=duration<=30 or abs(duration*24-round(duration*24))>1e-6:
        raise ValueError('Presentation duration must fit this proof on video frames')
    rows=presentation['time_map']
    if (not isinstance(rows,list) or len(rows)<2
            or any(not isinstance(row,list) or len(row)!=2 or not all(map(finite,row)) for row in rows)
            or rows[0]!=[0,0] or rows[-1]!=[scene['canvas']['duration'],duration]
            or any(b[0]<=a[0] or b[1]<=a[1] for a,b in zip(rows,rows[1:]))):
        raise ValueError('Presentation timing must be finite and strictly monotonic')
    starts=presentation['voice_starts']
    if (set(starts)!={v['id'] for v in scene['voice']}
            or any(not finite(v) or not 0<=v<duration or abs(v*24-round(v*24))>1e-6 for v in starts.values())
            or len(set(starts.values()))!=len(starts)):
        raise ValueError('Only existing exact voice slots may be placed, on video frames')
    if attached:
        layout=presentation['attachment_layout']
        limits={'scale_percent':(60,90),'baseline_gap':(60,160),
                'connector_hold_seconds':(.3,1),'connector_fade_seconds':(.15,.8)}
        if (not isinstance(layout,dict) or set(layout)!=set(limits)
                or any(not finite(layout[k]) or not lo<=layout[k]<=hi for k,(lo,hi) in limits.items())):
            raise ValueError('Finite bounded visual layout only; attachment endpoints come from the frozen scene')
    else:
        parks=presentation['parks']
        if set(parks)!={o['id'] for o in scene['objects'] if o['role']=='supplied_modifier'}:
            raise ValueError('Only supplied deferred modifiers may be parked')
        for positions in parks.values():
            if (set(positions)!={'via','rest'} or any(not isinstance(v,list) or len(v)!=3
                    or not all(map(finite,v)) or any(abs(n)>5000 for n in v) for v in positions.values())):
                raise ValueError('Park geometry must be finite local research coordinates')
    if any(not finite(presentation[k]) or not 0<=presentation[k]<=100 for k in required if k.endswith('_opacity')):
        raise ValueError('Presentation opacity must be in 0..100')
    return presentation


def canvas_duration(request):
    return request.get('presentation',{}).get('duration',request['scene']['canvas']['duration'])


def presentation_time(request,time):
    if 'presentation' not in request:return time
    rows=request['presentation']['time_map']
    for a,b in zip(rows,rows[1:]):
        if time<=b[0]:return a[1]+(time-a[0])*(b[1]-a[1])/(b[0]-a[0])
    return rows[-1][1]


def voice_slots(request):
    slots=[dict(v) for v in request['scene']['voice']]
    if 'presentation' in request:
        for slot in slots:slot['start']=request['presentation']['voice_starts'][slot['id']]
    return sorted(slots,key=lambda v:v['start'])


def make_request(output, revision, presentation=None):
    from PIL import ImageFont
    scene = validate_scene(read(HERE/'synthetic-scene.json'))
    font = ImageFont.truetype(scene['font']['english_file'], scene['font']['size'])
    x=170; layout=[]
    for obj in scene['objects']:
        width=float(font.getlength(obj['text']))
        layout.append(dict(obj,x=x,width=width,text_sha=sha(obj['text'])))
        x+=width
    if x>1780: raise ValueError('Full original sentence exceeds its reading area')
    request={'scene':scene,'scene_sha':sha(scene),'revision':revision,'layout':layout,
             'template_sha':file_sha(HERE/'build.jsx'),
             'fonts_sha':{k:file_sha(scene['font'][k+'_file']) for k in ('english','chinese')},
             'project':str(output/'NATIVE_CREATIVE_PROOF.aep')}
    if presentation is not None:
        request['presentation']=validate_presentation(presentation,scene)
    request['spec_sha']=sha({k:v for k,v in request.items() if k!='project'})
    return request


def current(output):
    request=read(output/'build-request.json')
    validate_scene(request['scene'])
    if 'presentation' in request:validate_presentation(request['presentation'],request['scene'])
    # A later visual revision must not prevent replay of a preserved older one.
    expected=sha({k:v for k,v in request.items() if k not in ('project','spec_sha')})
    if (request['spec_sha'] != expected or request['scene_sha'] != sha(request['scene'])
            or file_sha(output/'executed-template.jsx') != request['template_sha']
            or any(file_sha(request['scene']['font'][k+'_file']) != v
                   for k,v in request['fonts_sha'].items())):
        raise ValueError('Frozen research input, font or executed script changed')
    by_id={obj['id']:obj for obj in request['scene']['objects']}
    if (set(by_id) != {obj['id'] for obj in request['layout']}
            or any(obj['text_sha'] != sha(obj['text'])
                   or any(obj[k] != by_id[obj['id']][k] for k in by_id[obj['id']])
                   for obj in request['layout'])):
        raise ValueError('Source partition and layout binding differ')
    return request


def client():
    c=JunkdogeClient();c.initialize();c.call('ae_skillUse',{'name':'ae-execution-guide'});return c


def research_output(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'local-data'):
        raise ValueError('Native research artifacts must remain in ignored local-data')
    return output


def require_research_project(c):
    """Official checkpoints save the loaded project. Never checkpoint an old input."""
    result=c.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null});'})
    path=json.loads(result['content'])['path']
    if path and not Path(path).resolve().is_relative_to(ROOT/'local-data'/'ae-native-creative-proof'):
        raise ValueError('Open a blank project or a dedicated research project first; old AEP cannot be checkpointed')
    return path


def build(output, revision, recovery_id=None, rhythm_r4=False, attachment_r5=False, attachment_r5_fast=False):
    output=research_output(output)
    if sum((rhythm_r4,attachment_r5,attachment_r5_fast))>1:raise ValueError('Select one explicit visual revision')
    overlay='attachment-r5-fast.json' if attachment_r5_fast else 'attachment-r5.json' if attachment_r5 else 'rhythm-r4.json' if rhythm_r4 else None
    request=make_request(output,revision,read(HERE/overlay) if overlay else None)
    c=client();require_research_project(c)
    output.mkdir(parents=True,exist_ok=False)
    write(output/'build-request.json',request)
    (output/'executed-template.jsx').write_bytes((HERE/'build.jsx').read_bytes())
    write(output/'native-project-before.json',c.call('ae_read',{'target':'project'}))
    code='var NCP_REQUEST='+json.dumps((output/'build-request.json').as_posix())+';\n'+(HERE/'build.jsx').read_text(encoding='utf-8')
    arguments={'code':code,'undo_group_name':'Native physical cognition '+revision,
        'checkpoint_label':'before-native-peel-'+revision,'timeout_sec':180}
    tool='ae_exec'
    if recovery_id:
        tool='ae_execRecover';arguments.update(recoveryId=recovery_id,retryMode='continue')
    result=mutation_call(c,tool,arguments,output,210)
    write(output/'build-result.json',result);identity=json.loads(result['content'])
    if identity['spec_sha']!=request['spec_sha']:raise ValueError('Missing native identity')
    write(output/'identity.json',identity);audit(output)
    return identity


def validate_control_source(source, request, picture):
    """Reject stale or cross-bound snapshots before contacting the native host."""
    expected_project = (Path(source) / 'PROJECT_B.aep').resolve()
    if (picture['kind'] != 'synthetic_native_AE_visual_research'
            or picture['spec_sha'] != request['spec_sha']
            or picture['scene_sha'] != request['scene_sha'] or picture['variant'] != 'B'
            or picture['production_eligible'] is not False
            or picture['public_render_ready'] is not False
            or Path(picture['project']).resolve() != expected_project
            or file_sha(expected_project) != picture['project_sha256']):
        raise ValueError('Use the preserved native B project with its exact binding')


def fork_controls(output, source, recovery_id=None):
    """Import the immutable final B project into a clean render session.

    Imported completed diagnostic queue copies are validated and removed in
    the new project. Source bytes and semantic/script bindings remain unchanged.
    """
    output=research_output(output);source=research_output(source)
    request=current(source);picture=read(source/'render-receipt-B.json')
    validate_control_source(source,request,picture)
    c=client()
    before=json.loads(c.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty,items:app.project.numItems});'})['content'])
    if before['path'] or (not recovery_id and (before['dirty'] or before['items'])):
        raise ValueError('Open a clean blank AE project for the isolated control render')
    request=dict(request,project=str(output/'NATIVE_CREATIVE_PROOF.aep'))
    if recovery_id:
        if current(output)!=request:raise ValueError('Recovery must preserve the original frozen import request')
        shutil.copy2(output/'last-mutation-failure.json',output/'fork-first-failure.json')
        shutil.copy2(output/'last-mutation-request.json',output/'fork-first-request.json')
    else:
        output.mkdir(parents=True,exist_ok=False)
        write(output/'build-request.json',request)
        (output/'executed-template.jsx').write_bytes((source/'executed-template.jsx').read_bytes())
    write(output/'native-project-before.json',before)
    code='''(function(){if(!RECOVER){if(app.project.numItems!==0||app.project.dirty)throw new Error('Clean blank project required');app.project.importFile(new ImportOptions(new File(SOURCE)));}else if(app.project.file)throw new Error('Expected reconciled unsaved imported project');var found=[];for(var i=1;i<=app.project.numItems;i++){var p=app.project.item(i);if(!(p instanceof CompItem)||!p.comment)continue;var b=JSON.parse(p.comment);if(b.spec_sha===BINDING&&!b.variant)found.push(p);}if(found.length!==1||app.project.renderQueue.rendering)throw new Error('Ambiguous imported scene or active render');var removed=0;for(var i=1;i<=app.project.renderQueue.numItems;i++){var q=app.project.renderQueue.item(i),b=JSON.parse(q.comp.comment);if(q.status!==RQItemStatus.DONE||b.kind!=='synthetic_ae_visual_research'||b.scene_sha!==SCENE)throw new Error('Unrecognized imported render queue');}while(app.project.renderQueue.numItems){app.project.renderQueue.item(app.project.renderQueue.numItems).remove();removed++;}var cp=found[0];app.project.save(new File(DEST));cp.openInViewer();return JSON.stringify({ok:true,comp_id:cp.id,scene_sha:JSON.parse(cp.comment).scene_sha,spec_sha:JSON.parse(cp.comment).spec_sha,renderer:cp.renderer,project:app.project.file.fsName,render_queue_items:app.project.renderQueue.numItems,imported_completed_queue_copies_removed:removed});})();'''
    code=code.replace('SOURCE',json.dumps(Path(picture['project']).as_posix())).replace('BINDING',json.dumps(request['spec_sha'])).replace('DEST',json.dumps(Path(request['project']).as_posix()))
    code=code.replace('RECOVER','true' if recovery_id else 'false').replace('SCENE',json.dumps(request['scene_sha']))
    arguments={'code':code,'undo_group_name':'Import immutable B for native controls','timeout_sec':120};tool='ae_exec'
    if recovery_id:tool='ae_execRecover';arguments.update(recoveryId=recovery_id,retryMode='continue')
    result=mutation_call(c,tool,arguments,output,150)
    native=json.loads(result['content']);write(output/'identity.json',native)
    write(output/'fork-receipt.json',{'source_project':picture['project'],
        'source_project_sha256':picture['project_sha256'],'source_spec_sha':picture['spec_sha'],
        'native':result,'source_bytes_unchanged':file_sha(picture['project'])==picture['project_sha256']})
    if file_sha(picture['project'])!=picture['project_sha256'] or native['spec_sha']!=request['spec_sha']:
        raise ValueError('Import changed the source snapshot or binding')
    audit(output);return native


def audit(output, comp_id=None, variant='B'):
    request=current(output);comp_id=comp_id or read(output/'identity.json')['comp_id']
    code='''(function(){var cp=AEMCP.compById(COMP),a={binding:JSON.parse(cp.comment),renderer:cp.renderer,active_camera:cp.activeCamera.name,canvas:[cp.width,cp.height,cp.frameRate,cp.duration],motion_blur:cp.motionBlur,shutter:cp.shutterAngle,layers:[]};function track(p){var r=[];for(var k=1;k<=p.numKeys;k++)r.push([p.keyTime(k),p.keyValue(k)]);return r;}for(var i=1;i<=cp.numLayers;i++){var l=cp.layer(i),t=l.transform,r={id:l.id,name:l.name,parent:l.parent?l.parent.name:null,threeD:l.threeDLayer,motionBlur:l.motionBlur,position:track(t.position),opacity:track(t.opacity)};if(l instanceof TextLayer){var p=l.property('Source Text'),d=p.value,b=l.sourceRectAtTime(0,false);r.text=d.text;r.font=d.font;r.size=d.fontSize;r.source_text_keys=p.numKeys;r.source_text_expression=p.expressionEnabled;r.bounds={left:b.left,top:b.top,width:b.width,height:b.height};r.origin=l.comment?JSON.parse(l.comment):null;}if(l.threeDLayer){r.yRotation=track(t.yRotation);r.zRotation=track(t.zRotation);}if(l instanceof CameraLayer){var o=l.property('ADBE Camera Options Group');r.poi=track(t.pointOfInterest);r.dof=o.property('ADBE Camera Depth of Field').value;r.aperture=o.property('ADBE Camera Aperture').value;r.focus_expression=o.property('ADBE Camera Focus Distance').expression;r.focus_samples=[];for(var j=0;j<7;j++){var tm=[0,5.4,7.7,11.8,14.5,20.6,25][j];r.focus_samples.push([tm,o.property('ADBE Camera Focus Distance').valueAtTime(tm,false)]);}}a.layers.push(r);}return JSON.stringify(a);})();'''.replace('COMP',str(int(comp_id)))
    code=code.replace('[0,5.4,7.7,11.8,14.5,20.6,25]',json.dumps([
        presentation_time(request,t) for t in [0,5.4,7.7,11.8,14.5,20.6,25]]))
    c=client();result=json.loads(c.call('ae_exec',{'code':code})['content'])
    by={l['name']:l for l in result['layers']}
    if (result['canvas'] != [1920,1080,24,canvas_duration(request)] or result['renderer']!='ADBE Advanced 3d'
            or result['binding']['spec_sha']!=request['spec_sha']):raise ValueError('Native profile or binding changed')
    for obj in request['layout']:
        actual=by[obj['id']]
        if (actual['text']!=obj['text'] or actual['font']!=request['scene']['font']['english']
                or actual['source_text_keys'] or actual['source_text_expression']
                or actual['origin']['text_sha']!=obj['text_sha'] or not actual['threeD']):
            raise ValueError('Original source identity or lexical content changed')
        if any(actual['origin'].get(k)!=obj[k] for k in ('start','end','protected')):
            raise ValueError('Original protected span changed')
        if obj['role']=='supplied_modifier' and actual['parent']!='HINGE_'+obj['id']:
            raise ValueError('Attachment pivot was replaced')
    camera=by['GUIDED_CAMERA']
    if variant=='B' and (camera['dof']!=1 or not camera['focus_expression'] or len(camera['poi'])<4):
        raise ValueError('Physical camera/focus absent')
    if any(v<=0 for _,v in camera['focus_samples']):raise ValueError('Focus behind camera')
    if variant=='B' and 'attachment_layout' in request.get('presentation',{}):
        code='var NCP_REQUEST='+json.dumps((output/'build-request.json').as_posix())+';var NCP_COMP='+str(int(comp_id))+';\n'+(HERE/'attachment-audit.jsx').read_text(encoding='utf-8')
        measured=json.loads(c.call('ae_exec',{'code':code})['content'])
        verify_attachment_layout(request,measured)
        result['attachment_layout']=measured
    write(output/('native-audit-'+variant+'.json'),result)
    return result


def verify_attachment_layout(request,measured):
    """Actual native geometry check; it does not certify a grammar relationship."""
    layout=request['presentation']['attachment_layout']
    supplied={o['id']:o for o in request['layout'] if o['role']=='supplied_modifier'}
    if (measured['kind']!='supplied_synthetic_visual_attachment'
            or measured['spec_sha']!=request['spec_sha'] or measured['scene_sha']!=request['scene_sha']):
        raise ValueError('Different native attachment layout binding')
    seen=set()
    for row in measured['samples']:
        obj=supplied.get(row['object_id']);phase=row['phase']
        if (obj is None or (row['object_id'],phase) in seen or row['anchor_id']!=obj['attachment']
                or row['connector']!={'origin':request['scene_sha'],'anchor_id':obj['attachment'],
                    'object_id':obj['id'],'kind':'supplied_synthetic_visual_attachment'}):
            raise ValueError('Connector must keep its original supplied endpoints')
        seen.add((obj['id'],phase))
        if phase=='original':
            if (any(abs(a-b)>1e-4 for a,b in zip(row['pivot'],[obj['x'],540,0]))
                    or abs(row['scale_percent']-100)>1e-4 or row['connector_opacity']!=0):
                raise ValueError('Original reading state changed')
        elif phase in ('park','final','follow'):
            gap=(-1 if obj['id']=='aside-time' else 1)*layout['baseline_gap']
            if (abs(row['center_error'])>.01 or abs(row['baseline_gap']-gap)>.01
                    or abs(row['pivot'][2])>.01 or abs(row['scale_percent']-layout['scale_percent'])>.01
                    or abs(row['y_rotation'])>.01 or abs(row['z_rotation'])>.01):
                raise ValueError('Parked text must follow and align with its supplied object')
            if phase=='final' and (row['connector_opacity']!=0
                    or abs(row['text_opacity']-request['presentation']['text_rest_opacity'])>.01):
                raise ValueError('Final reading hierarchy or connector fade failed')
            if phase in ('park','follow') and row['connector_opacity']<=0:
                raise ValueError('Temporary relation cue was not visible at landing')
        else:raise ValueError('Unknown geometry audit phase')
    expected={(obj,phase) for obj in supplied for phase in ('original','park','final')}|{('aside-time','follow')}
    if seen!=expected:raise ValueError('Incomplete native attachment/follow audit')


def variants(output):
    request=current(output);source=read(output/'identity.json')['comp_id']
    if (output/'variants.json').exists():raise FileExistsError('Preserve existing native variants')
    c=client();require_research_project(c)
    code='var NCP_COMP='+str(int(source))+';\n'+(HERE/'variants.jsx').read_text(encoding='utf-8')
    (output/'executed-variants.jsx').write_bytes((HERE/'variants.jsx').read_bytes())
    result=mutation_call(c,'ae_exec',{'code':code,'checkpoint_label':'before-native-controls',
        'undo_group_name':'Synthetic baseline, fixed camera, restoration','timeout_sec':120},output,150)
    write(output/'variants-result.json',result);native=json.loads(result['content'])
    write(output/'variants.json',{'spec_sha':request['spec_sha'],'template_sha':file_sha(HERE/'variants.jsx'),**native})
    verify_restoration(request,native)
    for name,comp in native['comp_ids'].items():audit(output,comp,name)
    return native


def verify_restoration(request,native):
    restored={o['object_id']:o for o in native['restored']}
    if len(native['restored'])!=len(request['layout']) or set(restored)!={o['id'] for o in request['layout']}:
        raise ValueError('Restore test lost an original object')
    for source in request['layout']:
        actual=restored[source['id']]
        expected_parent='HINGE_'+source['id'] if source['role']=='supplied_modifier' else None
        if (actual['text']!=source['text'] or actual['parent']!=expected_parent
                or len(actual['position'])!=3
                or any(abs(a-b)>1e-5 for a,b in zip(actual['position'],[source['x'],540,0]))
                or abs(actual['y_rotation'])>1e-5):
            raise ValueError('Original source position or attachment failed restoration')


def validate_render_range(label,start,duration,comp_duration=27):
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*',label):raise ValueError('Use a safe variant label')
    if (not all(math.isfinite(v) for v in (start,duration)) or start<0 or duration<=0
            or start+duration>comp_duration
            or any(abs(v*24-round(v*24))>1e-6 for v in (start,duration))):
        raise ValueError('Render interval must fit the bound comp on exact frame boundaries')


def preview(output):
    request=current(output);comp=read(output/'identity.json')['comp_id'];folder=output/'previews'
    folder.mkdir(exist_ok=False);times=[0,4.5,6.5,7.7,8.6,10.5,12.4,14.3,15.8,17.7,19.5,21.3,24.5,26.5]
    times=[presentation_time(request,time) for time in times]
    c=client();check_expressions(c,output,comp)
    result=c.call('ae_previewFrame',{'comp_id':str(comp),'times':times,'layout':'grid','grid_max_side':2048,'out_dir':str(folder)},timeout=180)
    write(output/'preview-receipt.json',{'spec_sha':request['spec_sha'],'native':result})
    return result


def check_expressions(c,output,comp):
    request=current(output)
    layers=c.call('ae_read',{'target':'layers','comp':{'id':str(comp)},'page':{'limit':200}})
    result=c.call('ae_validateExpressions',{'comp_id':str(comp),
        'layer_ids':[l['stackIndex'] for l in layers['layers']],
        'sample_times':[presentation_time(request,t) for t in [0,5.4,7.9,14.6,20.6,25]],'max_results':1000})
    if not result.get('valid') or result.get('truncated'):
        raise ValueError('Native focus expression failed or was incompletely checked')
    write(output/('expressions-'+str(comp)+'.json'),result)
    return result


def render(output, comp_id=None, label='B', start=0, duration=None, recovery_id=None, single_frame=False):
    request=current(output);comp_id=comp_id or read(output/'identity.json')['comp_id']
    if duration is None:duration=canvas_duration(request)-start
    validate_render_range(label,start,duration,canvas_duration(request))
    audit(output,comp_id,label)
    target=output/('NATIVE_'+label+'.mp4');frames=output/('native-tiff-'+label)
    if target.exists() or frames.exists():raise FileExistsError('Preserve native renders')
    c=client();require_research_project(c);check_expressions(c,output,comp_id);frames.mkdir()
    code='''(function(){var q=null;for(var j=1;j<=app.project.renderQueue.numItems;j++){var e=app.project.renderQueue.item(j);if(e.render&&e.status===RQItemStatus.QUEUED)throw new Error('Unrelated queued render');if(RECOVER&&e.comp.id===COMP&&!e.outputModule(1).file&&!e.render)q=e;}var cp=AEMCP.compById(COMP);if(!q)q=app.project.renderQueue.items.add(cp);var o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('TIFF')!==-1){preset=o.templates[i];break;}if(!preset)throw new Error('Native TIFF sequence unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=DURATION;app.project.save();var before=(new Date()).getTime();app.project.renderQueue.render();var elapsed=(new Date()).getTime()-before;app.project.save();return JSON.stringify({ok:q.status===RQItemStatus.DONE,preset:preset,render_ms:elapsed,comp_id:cp.id,start:START,duration:DURATION,renderer:cp.renderer});})();'''
    code=code.replace('COMP',str(int(comp_id))).replace('DEST',json.dumps((frames/'FRAME_[#####].tif').as_posix())).replace('START',str(start)).replace('DURATION',str(duration)).replace('RECOVER','true' if recovery_id else 'false')
    if single_frame:
        code=code.replace('app.project.renderQueue.render();',
            'if(typeof app.setMultiFrameRenderingConfig!=="function")throw new Error("Native single-frame control unavailable");app.setMultiFrameRenderingConfig(false,100);app.project.renderQueue.render();')
    arguments={'code':code,'checkpoint_label':'before-native-render-'+label,'timeout_sec':600};tool='ae_exec'
    if recovery_id:tool='ae_execRecover';arguments.update(recoveryId=recovery_id,retryMode='continue')
    write(output/('render-request-'+label+'.json'),{'tool':tool,'arguments':arguments})
    result=mutation_call(c,tool,arguments,output,630)
    write(output/('native-render-'+label+'.json'),result);native=json.loads(result['content'])
    snapshot=output/('PROJECT_'+label+'.aep')
    if snapshot.exists():raise FileExistsError('Preserve render project snapshots')
    shutil.copy2(request['project'],snapshot)
    paths=sorted(frames.glob('*.tif'));expected=round(duration*24)
    matches=[re.fullmatch(r'(.*?)(\d+)(\.tif)',p.name) for p in paths]
    if not native['ok'] or len(paths)!=expected or any(m is None for m in matches):raise ValueError('Native sequence incomplete')
    first=int(matches[0][2]);pattern=frames/(matches[0][1]+'%0'+str(len(matches[0][2]))+'d.tif')
    if [int(m[2]) for m in matches]!=list(range(first,first+expected)):raise ValueError('Native frame gaps')
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','24','-start_number',str(first),'-i',str(pattern),'-frames:v',str(expected),'-an','-c:v','libx264','-threads','4','-crf','16','-pix_fmt','yuv420p',str(target)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    # Exact-byte archival avoids exhausting this machine's limited free disk.
    # Only this run's generated TIFFs are removed, after every archived SHA verifies.
    archive=output/('NATIVE_TIFF_'+label+'.zip');manifest={p.name:file_sha(p) for p in paths}
    if archive.exists():raise FileExistsError('Preserve native frame archives')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        for name,expected_sha in manifest.items():
            with z.open(name) as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=expected_sha:
                    raise ValueError('Native frame archive failed exact-byte verification')
    write(output/('native-frame-shas-'+label+'.json'),manifest)
    for p in paths:
        if p.resolve().parent != frames.resolve() or not p.resolve().is_relative_to(ROOT/'local-data'):
            raise ValueError('Generated frame escaped the research directory')
    for p in paths:p.unlink()
    receipt={'kind':'synthetic_native_AE_visual_research','spec_sha':request['spec_sha'],'scene_sha':request['scene_sha'],
        'variant':label,'renderer':native['renderer'],'native_render_ms':native['render_ms'],'frames':expected,
        'start':start,'duration':duration,'canvas_duration':canvas_duration(request),
        'single_frame_rendering_requested':single_frame,
        'project':str(snapshot),'project_sha256':file_sha(snapshot),
        'working_project':request['project'],
        'output':str(target),'output_sha256':file_sha(target),
        'native_tiff_archive':str(archive),'archive_sha256':file_sha(archive),
        'native_frame_manifest_sha256':file_sha(output/('native-frame-shas-'+label+'.json')),'audio':False,
        'production_eligible':False,'human_viewing_review':'PENDING','public_render_ready':False}
    write(output/('render-receipt-'+label+'.json'),receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('build','fork','audit','preview','variants','render'))
    parser.add_argument('output');parser.add_argument('--revision',default='r1')
    visual=parser.add_mutually_exclusive_group()
    visual.add_argument('--rhythm-r4',action='store_true',help='Use the explicit Astra rhythm / texture presentation overlay')
    visual.add_argument('--attachment-r5',action='store_true',help='Park supplied fragments above/below their frozen visual anchors')
    visual.add_argument('--attachment-r5-fast',action='store_true',help='Same vertical layout with faster peeling; preserve reading and final holds')
    parser.add_argument('--recovery-id',help='Exact official ID after native-state reconciliation; never guessed')
    parser.add_argument('--comp-id',type=int);parser.add_argument('--label',default='B')
    parser.add_argument('--start',type=float,default=0);parser.add_argument('--duration',type=float)
    parser.add_argument('--single-frame',action='store_true',help='Use verified native per-script single-frame rendering after a reconciled MFR stall')
    parser.add_argument('--source',help='Existing immutable B revision for the fork operation')
    args=parser.parse_args();output=research_output(args.output)
    if args.operation=='build':result=build(output,args.revision,args.recovery_id,args.rhythm_r4,args.attachment_r5,args.attachment_r5_fast)
    elif args.operation=='fork':
        if not args.source:parser.error('fork requires --source')
        result=fork_controls(output,args.source,args.recovery_id)
    elif args.operation=='render':result=render(output,args.comp_id,args.label,args.start,args.duration,args.recovery_id,args.single_frame)
    else:result=globals()[args.operation](output)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
