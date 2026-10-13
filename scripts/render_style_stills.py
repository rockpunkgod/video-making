"""P1 draft: render native static style selections from an existing frozen case."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from video_contracts import read,write,status_matches
from content_os.candidates import engineering_gate,source_gate
from ae_production.candidate_motion import audit_candidate_events
from ae_production.bridge import JunkdogeClient
from ae_production.execution import mutation_call


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def case_data(plan_path):
    plan=read(plan_path);bundle=read(plan['bundle_path']);status=read(plan['status_path'])
    if not status_matches(bundle,status) or source_gate([bundle])['internal_use']!='PASS':
        raise ValueError('Existing supplied frozen source is not usable internally')
    if engineering_gate(bundle,plan['selection'],'method_action_demo',status)['status']!='PASS':
        raise ValueError('Selected frozen action is not eligible')
    audit_candidate_events(plan['candidate_events'],{bundle['asset_id']:bundle})
    snapshot=bundle['source_snapshot'];selection=plan['selection']
    if snapshot['question_id']!='gaokao-2021-I-q26' or selection['method_id']!='R02':
        raise ValueError('P1 template is for the existing r02 real-case selection only')
    action=next(a for a in snapshot['action_executions'] if a['execution_id'] in selection['action_ids'])
    if action['output'].get('candidate')!='D' or action['output'].get('effect')!='eliminate':
        raise ValueError('The selected static judgment must be the reviewed D elimination')
    evidence=next(e for e in action['evidence'] if e['field']=='passage' and 'each pianist' in e['quote'])
    a,b=evidence['start'],evidence['end']
    if snapshot['passage'][a:b]!=evidence['quote']:raise ValueError('Frozen evidence range mismatch')
    method=next(m for m in bundle['methods'] if m['method_id']==selection['method_id'])
    memory='先看谁干的，把三格对一下。'
    if memory not in method.get('entry_copy',''):raise ValueError('Existing method memory copy required')
    words=[dict(text=m.group(),start=m.start(),end=m.end()) for m in re.finditer(r'\S+',snapshot['passage'])]
    return dict(asset_id=bundle['asset_id'],question_id=snapshot['question_id'],stem=snapshot['stem'],
                options=snapshot['options'],passage=snapshot['passage'],words=words,
                evidence=evidence,action=action,memory=memory,
                source_paths=[str(plan_path),plan['bundle_path'],plan['status_path']],
                frozen_role=action['role'],answer_displayed=False,public_render_ready=False)


def build(plan_path,output,recovery_id=None):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'local-data'):raise ValueError('Real images stay local')
    if output.exists() and not recovery_id:raise ValueError('Use a fresh output folder')
    case=case_data(Path(plan_path).resolve());output.mkdir(parents=True,exist_ok=bool(recovery_id))
    style=read(ROOT/'ae/design/style-v1.json')
    request=dict(style=style,case=case,project=str(output/'STYLE_V1_STILLS.aep'),output=str(output))
    write(output/'request.json',request)
    before={p:digest(p) for p in case['source_paths']};write(output/'source_before.json',before)
    client=JunkdogeClient();client.initialize()
    state=json.loads(client.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty,items:app.project.numItems,rendering:app.project.renderQueue.rendering}) // '+str(time.time_ns())})['content'])
    if state['rendering'] or (state['dirty'] and state['items']>0 and not recovery_id):raise ValueError('Preserve current native edits')
    # Preserve a saved project or the owned empty font-probe session, rather
    # than silently overwriting any user's project.
    if (state['path'] or state['dirty']) and not recovery_id:
        saved=mutation_call(client,'ae_exec',{'code':'app.project.save(new File('+json.dumps((output/'previous-session.aep').as_posix())+'));JSON.stringify({saved:true});','undo_group_name':'Preserve current session before P1 stills','checkpoint_label':'before-P1-static'},output,90)
        write(output/'session-preserved.json',saved)
    code='var STYLE_STILLS_RECOVERY='+('true' if recovery_id else 'false')+';var STYLE_STILLS_REQUEST='+json.dumps((output/'request.json').as_posix())+';\n'+(ROOT/'ae/templates/stills/style-v1-stills.jsx').read_text(encoding='utf-8')
    arguments=dict(code=code,undo_group_name='style-v1 static selection',checkpoint_label='before-style-v1-stills',timeout_sec=120)
    if recovery_id:arguments.update(recoveryId=recovery_id,retryMode='continue')
    result=mutation_call(client,'ae_execRecover' if recovery_id else 'ae_exec',arguments,output,150)
    actual=json.loads(result['content']);write(output/'native-layout.json',actual)
    for frame in actual['frames']:
        if frame['font_errors']:raise ValueError('Native font substitution')
        if frame['focus_lines']>9:raise ValueError('Focus window too long')
        if frame['overflow']:raise ValueError('Native text overflow')
    return actual


def render(output):
    output=Path(output).resolve();request=read(output/'request.json');actual=read(output/'native-layout.json')
    if not output.is_relative_to(ROOT/'local-data'):
        raise ValueError('Real images stay local')
    project=Path(request['project']).resolve()
    if not project.is_relative_to(output):
        raise ValueError('Native static project must stay inside its output directory')
    # Use the same pure frozen reader, not a solver or fresh review.
    case_data(Path(request['case']['source_paths'][0]))
    before=read(output/'source_before.json')
    if any(digest(p)!=h for p,h in before.items()):raise ValueError('Frozen input changed')
    client=JunkdogeClient();client.initialize()
    for frame in actual['frames']:
        path=output/(frame['name']+'.png')
        native=output/(frame['name']+'-native')
        if not path.exists():
            native.mkdir(exist_ok=False)
        # This host does not reliably write Advanced-3D saveFrameToPng output.
        # Render one native TIFF through the existing render queue instead.
        code='''(function(){var expected=new File(%s),c=AEMCP.compById(%d);
          if(!app.project.file||app.project.file.fsName.toLowerCase()!=expected.fsName.toLowerCase())throw Error('Different active project; reconcile before rendering');
          if(!c||c.name!=%s)throw Error('Different native composition');
          if(app.project.renderQueue.rendering)throw Error('Busy');
          c.renderer='ADBE Advanced 3d';c.openInViewer();app.project.save(expected);
          for(var i=1;i<=app.project.renderQueue.numItems;i++)app.project.renderQueue.item(i).render=false;
          var r=app.project.renderQueue.items.add(c);r.timeSpanStart=0;r.timeSpanDuration=1/24;r.render=true;
          var o=r.outputModule(1),t=null;for(i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('TIFF')>=0)t=o.templates[i];
          if(!t)throw Error('Native TIFF output missing');o.applyTemplate(t);o.file=new File(%s);
          app.project.renderQueue.render();var status=r.status;r.remove();app.project.save(expected);
          return JSON.stringify({name:c.name,queue_status:status,template:t});})();''' % (
            json.dumps(project.as_posix()),frame['comp_id'],
            json.dumps(frame['name']),json.dumps((native/'FRAME_[#####].tif').as_posix()))
        if not path.exists():
            result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':120,'undo_group_name':'Render one P1 native still','checkpoint_label':'P1-'+frame['name']},output,150)
            write(native/'queue-receipt.json',result)
            tiffs=list(native.glob('*.tif'))
            if len(tiffs)!=1:raise ValueError('One actual native frame required')
            with Image.open(tiffs[0]) as image:
                decoded=image.convert('RGB');decoded.save(path)
                if Image.open(path).convert('RGB').tobytes()!=decoded.tobytes():raise ValueError('Native PNG pixel conversion changed')
        with Image.open(path) as image:
            if image.size!=(1920,1080):raise ValueError('Native 1080p static required')
            image.convert('RGB').resize((1280,720),Image.Resampling.LANCZOS).save(output/(frame['name']+'-720.png'))
            # Letterbox on the requested phone viewport; preserve full 16:9.
            phone=Image.new('RGB',(844,390),'#20211F');small=image.convert('RGB');small.thumbnail((844,390),Image.Resampling.LANCZOS);phone.paste(small,((844-small.width)//2,(390-small.height)//2));phone.save(output/(frame['name']+'-phone.png'))
        print('Rendered',frame['name'],flush=True)
    after={p:digest(p) for p in before};write(output/'source_after.json',after)
    if after!=before:raise ValueError('Frozen asset altered')
    primary=actual['frames'][:10];sheet=Image.new('RGB',(1920,540*5),'#F2F0EA')
    for i,frame in enumerate(primary):
        with Image.open(output/(frame['name']+'.png')) as im:thumb=im.convert('RGB').resize((960,540),Image.Resampling.LANCZOS)
        sheet.paste(thumb,((i%2)*960,(i//2)*540))
    sheet.save(output/'P0_CONTACT_SHEET.jpg',quality=94)
    write(output/'render-summary.json',dict(frames=len(actual['frames']),resolution=[1920,1080],
          frozen_inputs_unchanged=True,native_tiff_to_png_pixels_equal=True,motion_tested=False,public_render_ready=False,style_selected=False))
    return dict(frames=len(actual['frames']),contact_sheet=str(output/'P0_CONTACT_SHEET.jpg'))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('plan');b.add_argument('output');b.add_argument('--recovery-id')
    r=sub.add_parser('render');r.add_argument('output')
    args=p.parse_args();print(json.dumps(build(args.plan,args.output,args.recovery_id) if args.command=='build' else render(args.output),ensure_ascii=False)[:700])
