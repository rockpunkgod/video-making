"""Explicit frozen-file inputs; authoring and copy-bound review remain separate steps."""
import argparse
from pathlib import Path
from video_contracts import read, write, sha
from .timing import narration_track, cue_sheet, mix_scratch
from .director import build_shot_plan
from .delivery import semantic_guard, human_voice_critic
from ae_production.landscape import build_landscape_contract, validate_landscape


def inputs(request):
    # No Registry, source Markdown or solver imports; status paths are mandatory.
    package=read(request['package']);manifest=read(request['manifest'])
    statuses={key:read(path) for key,path in request['statuses'].items()}
    delivery=read(request['delivery'])
    semantic_guard(delivery,package,manifest,statuses)
    return package,manifest,statuses,delivery


def prepare(request):
    p,m,s,d=inputs(request);out=Path(request['output_dir']).resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'landscape-render-contract.json').exists() or (out/'scratch-voice.wav').exists():
        raise ValueError('Use a new output directory for a new revision')
    track=narration_track(d,request['recordings'],provider=request.get('voice_provider','provided_internal_scratch_audio'),
                          sentence_boundaries={k:read(v) for k,v in request.get('sentence_boundaries',{}).items()})
    plan=build_shot_plan(p,m,s,d,track);sheet=cue_sheet(d,track);audio=mix_scratch(track,sheet,out/'scratch-voice.wav')
    contract=build_landscape_contract(p,m,s,d,track,plan,audio,sheet,revision=request.get('revision',1))
    for name,value in [('delivery-copy',d),('narration-track',track),('shot-plan',plan),('audio-cue-sheet',sheet),
                       ('landscape-render-contract',contract),('semantic-guard',semantic_guard(d,p,m,s)),('human-voice-critique',human_voice_critic(d))]:
        write(out/(name+'.json'),value)
    write(out/'creative-manifest.json',{'version':'0.1.0','package_sha':sha(p),'manifest_sha':sha(m),
          'delivery_sha':sha(d),'copy_lock':contract['copy_lock'],'render_id':contract['render_id'],
          'template_sha':contract['template_sha'],'schema_shas':contract['schema_shas'],
          'status_input_shas':contract['status_input_shas'],'request':request,'public_render_ready':False})
    return {'render_id':contract['render_id'],'output_dir':str(out)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','validate','build','render']);parser.add_argument('request')
    args=parser.parse_args();r=read(args.request)
    if args.command=='prepare':result=prepare(r)
    else:
        p,m,s,d=inputs(r);contract=read(r['contract']);validate_landscape(contract,p,m,s,d)
        if args.command=='validate':result={'valid':True,'public_render_ready':False}
        else:
            from ae_production.bridge import JunkdogeClient
            from ae_production import landscape_execution as execution
            client=JunkdogeClient();client.initialize()
            if args.command=='build':result=execution.build(client,contract,p,m,s,d,r['output_dir'],r['project_path'])
            else:result={'video':str(execution.render(client,contract,p,m,s,d,r['comp_id'],r['output_dir']))}
    print(result)


if __name__=='__main__':main()
