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
    def load(key):
        return read(path.parent / request[key])
    if args.command == 'inspect':
        result = inspect_historical(load('copy'))
        print('Historical integrity PASS; current upstream not verified; consumption blocked ('
              + result['contract_status'] + ')')
        return
    plan, projection, bundle, status = (load(k) for k in ('plan', 'projection', 'bundle', 'status'))
    if args.command == 'validate':
        result = validate_copy(load('copy'), projection, plan, bundle, status)
        print('Current binding PASS; consumption ' + ('allowed' if result['consumption_allowed'] else 'blocked'))
    else:
        output = path.parent / request['output']
        if output.exists():
            raise ValueError('Preserve historical Student POV outputs')
        copy = realize(projection, plan, bundle, status,
            draft_lines=load('draft_lines') if request.get('draft_lines') else None,
            copy_review=load('copy_review') if request.get('copy_review') else None)
        validate_copy(copy, projection, plan, bundle, status)
        write(output, copy)
        print('Student POV Copy: ' + copy['availability']['status'] + '; public release remains false')


if __name__ == '__main__':
    main()
