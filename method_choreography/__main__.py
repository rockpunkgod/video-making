"""Explicit input files only; no Adobe, voice, source discovery or overwrites."""
import argparse
from pathlib import Path
from video_contracts import read,write
from . import compile_choreography,validate_choreography,inspect_choreography,project_choreography,analyze_legacy


def main():
    parser=argparse.ArgumentParser(description='Method Choreography v0.1 state contract')
    parser.add_argument('command',choices=('compile','validate','inspect','project','analyze-legacy'))
    parser.add_argument('request')
    args=parser.parse_args();path=Path(args.request);request=read(path)
    allowed={'choreography'} if args.command=='inspect' else {
        'experience','plan','copy_handoff','motion_handoff','bundle','status','application','choreography',
        'output','diagnostic','copy','projection'}
    if set(request)-allowed:raise ValueError('Unknown request field; visual/voice parameters belong downstream')
    def load(key):return read(path.parent/request[key]) if request.get(key) else None
    if args.command=='inspect':
        result=inspect_choreography(load('choreography'));print(result['status']+'; consumption blocked');return
    if args.command=='analyze-legacy':
        result=analyze_legacy(*(load(k) for k in ('copy','plan','projection','bundle','status')))
    else:
        inputs=[load(k) for k in ('experience','plan','copy_handoff','motion_handoff','bundle','status')]
        application=load('application')
        if args.command=='validate':
            gate=validate_choreography(load('choreography'),*inputs,application=application)
            print('Current bindings PASS; consumption '+('allowed' if gate['consumption_allowed'] else 'blocked'));return
        diagnostic=request.get('diagnostic',False)
        if args.command=='compile':
            result=compile_choreography(*inputs,application=application,diagnostic=diagnostic)
            validate_choreography(result,*inputs,application=application)
        else:result=project_choreography(load('choreography'),*inputs,application=application,diagnostic=diagnostic)
    output=path.parent/request['output']
    if output.exists():raise ValueError('Preserve existing choreography and historical approvals')
    write(output,result)
    print(result.get('availability',{}).get('status',result.get('status','HOLD'))+'; public release false')


if __name__=='__main__':main()
