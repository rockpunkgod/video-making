"""Explicit-file Student POV realization/revalidation. No external AI service."""
import argparse
from pathlib import Path
from video_contracts import read, write
from .realization import realize
from .validation import validate_copy, inspect_historical


def main():
    parser = argparse.ArgumentParser(description='Student POV Copy realization after approved Pedagogy')
    parser.add_argument('command', choices=('realize', 'validate', 'inspect'))
    parser.add_argument('request')
    args = parser.parse_args()
    path = Path(args.request); request = read(path)
    allowed = {'copy'} if args.command == 'inspect' else {'plan','projection','motion_projection',
        'bundle','status','copy','output','draft_lines','copy_review','contract_version','options','allow_held_plan'}
    if set(request) - allowed:
        raise ValueError('Unknown Student POV request field; Creative/voice control belongs downstream')
    def load(key):
        return read(path.parent / request[key])
    if args.command == 'inspect':
        result = inspect_historical(load('copy'))
        print('Historical integrity PASS; current upstream not verified; consumption blocked ('
              + result['contract_status'] + ')')
        return
    version = request.get('contract_version', '0.3.0')
    plan, bundle, status = (load(k) for k in ('plan', 'bundle', 'status'))
    projection = load('projection') if request.get('projection') else None
    motion = load('motion_projection') if request.get('motion_projection') else None
    if args.command == 'validate':
        result = validate_copy(load('copy'), projection, plan, bundle, status,
            motion_projection=motion, required_version=version)
        print('Current binding PASS; consumption ' + ('allowed' if result['consumption_allowed'] else 'blocked'))
    else:
        output = path.parent / request['output']
        if output.exists():
            raise ValueError('Preserve historical Student POV outputs')
        copy = realize(projection, plan, bundle, status,
            draft_lines=load('draft_lines') if request.get('draft_lines') else None,
            copy_review=load('copy_review') if request.get('copy_review') else None,
            contract_version=version, motion_projection=motion,
            options=request.get('options'), allow_held_plan=request.get('allow_held_plan', False))
        validate_copy(copy, projection, plan, bundle, status, motion_projection=motion, required_version=version)
        write(output, copy)
        print('Student POV Copy: ' + copy['availability']['status'] + '; public release remains false')


if __name__ == '__main__':
    main()
