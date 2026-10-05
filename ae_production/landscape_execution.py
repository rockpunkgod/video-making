"""V9 uses the existing official bridge, with frozen-input checks before AE operations."""
import json
from pathlib import Path
from video_contracts import ROOT, sha, write
from .landscape import TEMPLATE, validate_landscape
from .execution import mutation_call


def build(client, contract, package, manifest, statuses, delivery, output_dir, project_path):
    validate_landscape(contract, package, manifest, statuses, delivery)
    out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    project=Path(project_path).resolve()
    # Official checkpoints save the active project. Detach first so historical AEP bytes stay untouched.
    detach='(function(){var target=new File('+json.dumps(project.as_posix())+');if(!app.project.file||app.project.file.fsName!==target.fsName){if(target.exists)throw new Error("Existing other project; open it explicitly or use a new path");app.project.save(target);}return JSON.stringify({project:app.project.file.fsName});})();'
    write(out/'detach-result.json',mutation_call(client,'ae_exec',{'code':detach},out,60))
    path=out/'landscape-render-contract.json';write(path,contract)
    code='var V9_CONTRACT_PATH='+json.dumps(path.as_posix())+';\n'
    code+='var V9_PROJECT_PATH='+json.dumps(project.as_posix())+';\n'+TEMPLATE.read_text(encoding='utf-8')
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':300,'checkpoint_label':'V9-before-build'},out,330)
    write(out/'build-result.json',result);identity=json.loads(result['content'])
    if not identity.get('ok') or identity['render_id']!=contract['render_id']:raise ValueError('AE identity mismatch; reconcile before retry')
    write(out/'build-identity.json',identity);return identity


def audit(client, comp_id, contract, output_dir):
    samples=[min(s['end']-1/24,s['hold_start']+.25) for s in contract['shot_plan']['shots']]
    code='var V9_COMP_ID='+str(int(comp_id))+';var V9_SAMPLE_TIMES='+json.dumps(samples)+';\n'
    code+=(ROOT/'ae/templates/landscape-audit.jsx').read_text(encoding='utf-8')
    result=json.loads(client.call('ae_exec',{'code':code})['content']);write(Path(output_dir)/'landscape-audit.json',result)
    expected={'METHOD_TAG':contract['method_tags'],'TRACE':'INTERNAL_CREATIVE_PREVIEW / SCRATCH VO / '+contract['render_id'].split(':')[1][:12]}
    for i,s in enumerate(contract['shot_plan']['shots']):
        expected['SHOT_'+str(i)]=str(i+1).zfill(2)+' / '+str(len(contract['shot_plan']['shots'])).zfill(2)
        expected.update({c['component_id']:''.join(c['layout']['lines']) for c in s['components']})
        if s['structure'] and s['structure']['kind']=='rewire':
            expected.update({s['shot_id']+'_SLOT_'+str(k):v for k,v in enumerate(s['structure']['slot_labels'])})
    expected.update({c['cue_id']:''.join(c['lines']) for c in contract['shot_plan']['captions']})
    actual={r['name']:r for r in result['rows']};clean=lambda s:s.replace('\r','').replace('\n','')
    if set(actual)!=set(expected) or any(clean(actual[k]['text'])!=clean(v) for k,v in expected.items()):raise ValueError('Actual AE text drift')
    if any(r['font']!=contract['shot_plan']['design']['font']['postscript'] for r in actual.values()):raise ValueError('Font substitution')
    ds=contract['shot_plan']['design'];sizes={k:ds['typography']['Metadata']['size'] for k in expected}
    for s in contract['shot_plan']['shots']:
        sizes.update({c['component_id']:ds['typography'][c['layout']['style_token']]['size'] for c in s['components']})
    sizes.update({c['cue_id']:ds['typography']['Subtitle']['size'] for c in contract['shot_plan']['captions']})
    if any(actual[k]['size']!=v for k,v in sizes.items()) or result['effectLayers'] or not result['motionBlur'] or result['shutterAngle']!=180:
        raise ValueError('Actual typography/effect/motion policy drift')
    if not result['valid'] or (result['width'],result['height'],result['fps'])!=(1920,1080,24) or not result['audioEnabled']:raise ValueError('Native landscape audit failed')
    result['text_binding_valid']=True;write(Path(output_dir)/'landscape-audit.json',result);return result


def verify(client, comp_id, contract):
    # Return original JSON text. A JS parse/stringify round trip rounds long fractional timestamps.
    code="""(function(){var cp=AEMCP.compById(%s),f=cp.layer('RENDER_CONTRACT').source.file;f.encoding='UTF-8';f.open('r');var text=f.read();f.close();return JSON.stringify({binding:JSON.parse(cp.comment),contract_text:text,audio:cp.layer('INTERNAL_SCRATCH_VOICE').source.file.fsName});})();""" % int(comp_id)
    result=json.loads(client.call('ae_exec',{'code':code})['content'])
    if sha(json.loads(result['contract_text']))!=sha(contract) or any(result['binding'][k]!=contract[k] for k in ('render_id','package_id','package_sha','delivery_sha','template_version')) or Path(result['audio']).resolve()!=Path(contract['audio']['path']).resolve():raise ValueError('AE dependency drift')


def render(client, contract, package, manifest, statuses, delivery, comp_id, output_dir):
    validate_landscape(contract,package,manifest,statuses,delivery);verify(client,comp_id,contract)
    out=Path(output_dir).resolve();video=out/'INTERNAL_CREATIVE_PREVIEW.mp4'
    if video.exists():raise ValueError('Use a new revision instead of overwriting a preview')
    audit(client,comp_id,contract,out)
    layers=client.call('ae_read',{'target':'layers','comp':{'id':str(comp_id)},'page':{'limit':200}})
    expr=client.call('ae_validateExpressions',{'comp_id':str(comp_id),'layer_ids':[l['stackIndex'] for l in layers['layers'] if l['name']!='RENDER_CONTRACT'],'sample_times':[1,contract['canvas']['duration']/2],'max_results':1000})
    write(out/'expression-audit.json',expr)
    if not expr.get('valid') or expr.get('truncated'):raise ValueError('Expression audit incomplete')
    code='var V9_COMP_ID='+str(int(comp_id))+';var V9_OUTPUT='+json.dumps(video.as_posix())+';\n'
    code+="""(function(){var cp=AEMCP.compById(V9_COMP_ID);for(var i=1;i<=app.project.renderQueue.numItems;i++){var x=app.project.renderQueue.item(i);if(x.render&&x.status===RQItemStatus.QUEUED)throw new Error('Queued render conflict');}var rq=app.project.renderQueue.items.add(cp),om=rq.outputModule(1),preset=null;for(var i=0;i<om.templates.length;i++)if(om.templates[i].indexOf('H.264')===0&&om.templates[i].indexOf('15')!==-1){preset=om.templates[i];break;}if(!preset){rq.remove();throw new Error('Native H.264 unavailable');}om.applyTemplate(preset);om.file=new File(V9_OUTPUT);rq.timeSpanStart=0;rq.timeSpanDuration=cp.duration;app.project.save();app.project.renderQueue.render();return JSON.stringify({ok:rq.status===RQItemStatus.DONE,file:om.file.fsName,preset:preset});})();"""
    result=mutation_call(client,'ae_exec',{'code':code,'timeout_sec':600,'checkpoint_label':'V9-before-render'},out,630)
    write(out/'render-result.json',result)
    if not json.loads(result['content']).get('ok') or not video.exists() or not video.stat().st_size:raise ValueError('Native render incomplete')
    return video
