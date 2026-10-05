"""Build a visual contract from explicit read-only package inputs."""
import argparse
from pathlib import Path
from video_contracts import read, write
from .contract import build_contract, validate_contract


def main():
    ap=argparse.ArgumentParser(prog='ae-production'); sub=ap.add_subparsers(dest='command',required=True)
    for name in ('contract','validate','build','preview','render'):
        parser=sub.add_parser(name); parser.add_argument('request')
    args=ap.parse_args(); request_path=Path(args.request).resolve(); r=read(request_path)
    def load(key): return read(request_path.parent/r[key])
    package=load('package'); manifest=load('manifest'); raw=load('statuses')
    statuses=raw if isinstance(raw,dict) and 'asset_id' not in raw else {raw['asset_id']:raw}
    if args.command=='contract':
        result=build_contract(package,manifest,statuses,load('design') if r.get('design') else None,r.get('revision',1),platform_profile=r.get('platform_profile'))
        write(request_path.parent/r['output'],result); print(result['render_id'])
    elif args.command=='validate':
        validate_contract(load('contract'),package,manifest,statuses); print('AE contract PASS')
    else:
        from .bridge import JunkdogeClient
        from .execution import build_in_ae,checkpoint,audit_layout,verify_composition,render_internal_preview
        contract=load('contract'); validate_contract(contract,package,manifest,statuses)
        client=JunkdogeClient(r.get('endpoint','http://127.0.0.1:11488/mcp')); client.initialize()
        client.call('ae_skillUse',{'name':'ae-execution-guide'})
        out=(request_path.parent/r['output_dir']).resolve()
        if args.command=='build':
            before=client.call('ae_read',{'target':'project'});write(out/'read-before.json',before)
            identity=build_in_ae(client,contract,package,manifest,statuses,out)
            after=client.call('ae_read',{'target':'layers','comp':{'id':identity['comp_id']},'page':{'limit':200}})
            write(out/'read-after.json',after); print(identity['render_id'])
        else:
            identity=read(out/'build-identity.json')
            if identity['render_id']!=contract['render_id']: raise ValueError('AE composition binding mismatch')
            if args.command=='render':
                print(render_internal_preview(client,contract,package,manifest,statuses,identity['comp_id'],out,recovery_id=r.get('recovery_id')))
            else:
                verify_composition(client,identity['comp_id'],contract)
                layers=client.call('ae_read',{'target':'layers','comp':{'id':identity['comp_id']},'page':{'limit':200}})
                ids=[l['stackIndex'] for l in layers['layers'] if l['name']!='RENDER_CONTRACT']
                result=client.call('ae_validateExpressions',{'comp_id':identity['comp_id'],'layer_ids':ids,'sample_times':r.get('sample_times',[1]),'max_results':1000})
                write(out/'expressions.json',result)
                if not result.get('valid') or result.get('truncated'): raise ValueError('Expression validation incomplete')
                audit_layout(client,identity['comp_id'],out,contract)
                result=client.call('ae_previewFrame',{'comp_id':identity['comp_id'],'times':r.get('sample_times',[1]),'layout':'grid','out_dir':str(out/'frames')})
                write(out/'preview.json',result);checkpoint(client,contract,out);print(result['grid']['path'])
if __name__=='__main__': main()
