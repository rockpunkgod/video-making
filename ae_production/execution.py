"""Explicit contract revalidation, public MCP build/read/preview/checkpoint loop."""
import json
from http.client import HTTPException
from pathlib import Path
from video_contracts import ROOT, sha, write
from .contract import validate_contract,template_path
from .bridge import BridgeError


def mutation_call(client,tool,arguments,output_dir,timeout):
    """Preserve the official error/recovery evidence; never retry implicitly."""
    write(Path(output_dir)/'last-mutation-request.json',{'tool':tool,'arguments':arguments})
    try:
        return client.call(tool,arguments,timeout=timeout)
    except BridgeError as error:
        try: detail=json.loads(str(error))
        except ValueError: detail={'error':str(error),'state':'uncertain'}
        write(Path(output_dir)/'last-mutation-failure.json',{'tool':tool,'result':detail})
        raise
    except (OSError, HTTPException) as error:
        # A closed transport can mean the native host exited after applying part
        # of the operation. Persist uncertainty; never infer that nothing ran.
        write(Path(output_dir)/'last-mutation-failure.json',{
            'tool':tool,'result':{'error_type':type(error).__name__,'state':'uncertain',
                                 'next_action':'inspect_native_state_before_retry'}})
        raise


def build_in_ae(client,contract,package,manifest,statuses,output_dir):
    validate_contract(contract,package,manifest,statuses)
    output_dir=Path(output_dir).resolve(); output_dir.mkdir(parents=True,exist_ok=True)
    path=output_dir/'render-contract.json'; write(path,contract)
    code='var V8_CONTRACT_PATH='+json.dumps(path.as_posix(),ensure_ascii=True)+';\n'
    code+='var V8_PROJECT_PATH='+json.dumps((output_dir/'method-demo.aep').as_posix(),ensure_ascii=True)+';\n'
    code+=template_path(contract['template_version']).read_text(encoding='utf-8')
    write(output_dir/'build-request.json',{'tool':'ae_exec','arguments':{'code':code,'undo_group_name':'V8 METHOD_DEMO_MASTER','timeout_sec':120}})
    result=mutation_call(client,'ae_exec',{'code':code,'undo_group_name':'V8 METHOD_DEMO_MASTER','timeout_sec':120,
                               'checkpoint_label':'before-'+contract['render_id']},output_dir,150)
    write(output_dir/'build-result.json',result)
    content=result.get('content')
    built=json.loads(content) if isinstance(content,str) else content
    if not isinstance(built,dict) or built.get('render_id')!=contract['render_id']:
        raise ValueError('AE build identity missing; reconcile before retrying')
    write(output_dir/'build-identity.json',built)
    return built


def checkpoint(client,contract,output_dir):
    result=client.call('ae_checkpoint',{'action':'create','label':contract['render_id']})
    write(Path(output_dir)/'checkpoint.json',{'render_id':contract['render_id'],'package_id':contract['package_id'],
          'template_version':contract['template_version'],'result':result})
    return result


def verify_composition(client,comp_id,contract):
    code='''(function(){var cp=AEMCP.compById(%s); var file=cp.layer('RENDER_CONTRACT').source.file;
      file.encoding='UTF-8';file.open('r');var content=file.read();file.close();
      return JSON.stringify({comment:cp.comment,contract_text:content});})();''' % int(comp_id)
    actual=json.loads(client.call('ae_exec',{'code':code})['content'])
    binding=json.loads(actual['comment']);loaded=json.loads(actual['contract_text'])
    if sha(loaded)!=sha(contract) or any(binding[k]!=contract[k] for k in ('render_id','package_id','package_sha','template_version')):
        raise ValueError('Actual AE composition / data binding mismatch')


def audit_layout(client,comp_id,output_dir,contract=None):
    code='var V8_COMP_ID='+str(int(comp_id))+';\n'+(ROOT/'ae/templates/layout-audit.jsx').read_text(encoding='utf-8')
    result=client.call('ae_exec',{'code':code})
    result=json.loads(result['content']); write(Path(output_dir)/'layout-audit.json',result)
    if not result['valid']: raise ValueError('layout_overflow: real AE bounds / font audit failed')
    if contract is not None:
        expected={}
        for i,s in enumerate(contract['scenes']):
            v02=contract['template_version']=='0.2.0'
            expected['PROGRESS_'+str(i)]=str(i+1).zfill(2)+' / '+(str(len(contract['scenes'])).zfill(2) if v02 else s['scene_type'])
            for c in s['components']:
                key=c['component_id'];expected[key]=''.join(c['layout']['lines'])
                if c['component_type']=='OPTION_CARD':expected[key+'_ID']=c['content']['candidate']
                if v02 and c['component_type']=='OPTION_GROUP_GRID':expected[key+'_UNIVERSE']='   '.join(cid for g in c['content']['groups'] for cid in g['candidates'])
                if v02 and (c['component_type']=='STOP_RULE_CARD' or c['component_type']=='DECISION_PATH' and c['content']['terminal']):expected[key+'_TERMINAL']=contract['design']['localized_labels']['stop']
                if c['component_type']=='DECISION_PATH' and not c['content']['terminal']:expected[key+'_CONNECT']='↓'
                if c['component_type']=='RELATION_COMPARE' and c['content'].get('chain_length') and c['content']['column']<c['content']['chain_length']-1:expected[key+'_ARROW']='→'
                if v02 and c['component_type']=='RELATION_COMPARE' and c['content'].get('chain_length'):expected[key+'_SLOT']=contract['design']['localized_labels']['relation_slots'][c['content']['column']]
                if v02 and c['component_type']=='CANDIDATE_VERDICT' and c['content']['effect']=='eliminate' and c['content']['whole_question_answer'] is False:expected[key+'_LOCAL_LABEL']=contract['design']['localized_labels']['local_eliminate']+' '+c['content']['candidate']
        expected.update({cue['cue_id']:''.join(cue['lines']) for cue in contract['subtitles']})
        expected.update(METHOD_TAG=' + '.join((m['brand']+' · ' if contract['template_version']=='0.2.0' else '')+m['method_id']+' / '+m['role'] for m in contract['methods']),
                        INTERNAL_ENGINEERING_PREVIEW='INTERNAL_ENGINEERING_PREVIEW',
                        TRACE='RENDER '+contract['render_id'].split(':')[1][:12]+' / TEMPLATE '+contract['template_version'])
        if contract['source_tags']:expected['SOURCE_TAG']=contract['source_tags']
        actual={r['name']:r for r in result['rows']}
        clean=lambda t:t.replace('\r','').replace('\n','')
        if set(actual)!=set(expected) or any(clean(actual[k]['text'])!=clean(t) for k,t in expected.items()):
            raise ValueError('Actual AE text differs from bound contract projection')
        if any(r['font']!=contract['design']['font']['postscript'] for r in actual.values()):
            raise ValueError('Actual AE font substitution')
        result['text_binding_valid']=True;write(Path(output_dir)/'layout-audit.json',result)
    return result


def render_internal_preview(client,contract,package,manifest,statuses,comp_id,output_dir,recovery_id=None):
    validate_contract(contract,package,manifest,statuses)
    output_dir=Path(output_dir).resolve(); video=output_dir/'INTERNAL_ENGINEERING_PREVIEW.mp4'
    if video.exists(): raise ValueError('Preview already exists; use a new output directory')
    verify_composition(client,comp_id,contract)
    layers=client.call('ae_read',{'target':'layers','comp':{'id':str(comp_id)},'page':{'limit':200}})
    ids=[l['stackIndex'] for l in layers['layers'] if l['name']!='RENDER_CONTRACT']
    expr=client.call('ae_validateExpressions',{'comp_id':str(comp_id),'layer_ids':ids,'sample_times':[1,contract['canvas']['duration']/2],'max_results':1000})
    write(output_dir/'render-expression-check.json',expr)
    if not expr.get('valid') or expr.get('truncated'):raise ValueError('Expression validation failed or incomplete')
    audit_layout(client,comp_id,output_dir,contract)
    if contract['design_system_version']=='0.2.0':
        from .visual_qa import actual_visual_qa
        actual_visual_qa(client,comp_id,contract,output_dir)
    code='var V8_COMP_ID='+str(int(comp_id))+'; var V8_OUTPUT='+json.dumps(video.as_posix(),ensure_ascii=True)+';\n'
    code+='''(function(){
      var comp=AEMCP.compById(V8_COMP_ID);
      for(var i=1;i<=app.project.renderQueue.numItems;i++){
        var existing=app.project.renderQueue.item(i);
        if(existing.render && existing.status===RQItemStatus.QUEUED && existing.comp.id!==comp.id) throw new Error('Unrelated queued render must be handled separately');
        if(existing.comp.id===comp.id && existing.status===RQItemStatus.QUEUED){existing.remove();i--;}
        else if(existing.status===RQItemStatus.DONE && existing.comp.comment.indexOf('"render_id":"render:')!==-1){existing.remove();i--;}
      }
      var rq=app.project.renderQueue.items.add(comp),om=rq.outputModule(1),preset=null;
      for(var i=0;i<om.templates.length;i++){if(om.templates[i].indexOf('H.264')===0 && om.templates[i].indexOf('15')!==-1){preset=om.templates[i];break;}}
      if(!preset){rq.remove();throw new Error('ae_bridge_gap: native H.264 preset unavailable');}
      om.applyTemplate(preset);om.file=new File(V8_OUTPUT);rq.timeSpanStart=0;rq.timeSpanDuration=comp.duration;
      app.project.save();app.project.renderQueue.render();
      return JSON.stringify({ok:rq.status===RQItemStatus.DONE,status:String(rq.status),file:om.file.fsName,comp_id:String(comp.id),preset:preset});
    })();'''
    # AE renderQueue.render() resets the Undo stack; an outer Undo group causes a modal mismatch warning.
    if recovery_id:
        result=mutation_call(client,'ae_execRecover',{'code':code,'recoveryId':recovery_id,'retryMode':'continue'},output_dir,630)
    else:
        result=mutation_call(client,'ae_exec',{'code':code,'checkpoint_label':'before-render-'+contract['render_id'],'timeout_sec':600},output_dir,630)
    write(output_dir/'render-result.json',{'render_id':contract['render_id'],'package_id':contract['package_id'],
          'template_version':contract['template_version'],'template_sha':contract['template_sha'],'result':result})
    data=json.loads(result['content'])
    if not data.get('ok') or not video.exists() or video.stat().st_size==0: raise ValueError('AE render did not produce a complete video')
    return video
