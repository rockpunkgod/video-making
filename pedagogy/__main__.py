"""Standalone additive CLI. Requests name every input; no Registry discovery."""
import argparse
from pathlib import Path

from video_contracts import read, write
from .compiler import compile_plan
from .handoff import copy_projection, motion_projection
from .matrix import golden_matrix
from .validation import validate_plan


def _load(request_path):
    path = Path(request_path)
    request = read(path)
    def load(key):
        return read(path.parent / request[key])
    return path, request, load


def _save(path, value):
    if path.exists():
        raise ValueError('Preserve historical pedagogy outputs; choose a new output path')
    write(path, value)


def main():
    parser = argparse.ArgumentParser(description='Read-only frozen Pedagogy Compiler')
    parser.add_argument('command', choices=('compile', 'validate', 'handoff', 'matrix'))
    parser.add_argument('request')
    args = parser.parse_args()
    path, request, load = _load(args.request)
    if args.command == 'matrix':
        assets = []
        for row in request['assets']:
            assets.append({**row, 'bundle': read(path.parent / row['bundle']),
                            'status': read(path.parent / row['status'])})
        _save(path.parent / request['output'], golden_matrix(assets))
        print('Golden matrix written; unavailable modes retain explicit evidence gaps')
        return
    bundle, status = load('bundle'), load('status')
    if args.command == 'compile':
        allowed = {'bundle', 'status', 'selection', 'mode', 'audience', 'channel',
                   'duration_target', 'fields', 'extra_boundary_refs', 'boundary_review', 'output'}
        if set(request) - allowed:
            raise ValueError('Unknown compile request field')
        kwargs = {k: request[k] for k in ('mode', 'audience', 'channel', 'duration_target',
                                         'fields', 'extra_boundary_refs') if k in request}
        if 'boundary_review' in request:
            kwargs['boundary_review'] = load('boundary_review')
        plan = compile_plan(bundle, status, request['selection'], **kwargs)
        validate_plan(plan, bundle, status)
        _save(path.parent / request['output'], plan)
        print('PedagogyPlan: ' + plan['availability']['status'] + '; public release remains HOLD')
    elif args.command == 'validate':
        print(validate_plan(load('plan'), bundle, status)['status'])
    else:
        plan = load('plan')
        outputs = [(path.parent / request['copy_output'], copy_projection(plan, bundle, status)),
                   (path.parent / request['motion_output'], motion_projection(plan, bundle, status))]
        if any(p.exists() for p, _ in outputs):
            raise ValueError('Preserve historical handoffs; choose new output paths')
        for destination, value in outputs:
            _save(destination, value)
        print('Frozen Copy/Motion projections written; current-status revalidation is required')


if __name__ == '__main__':
    main()
