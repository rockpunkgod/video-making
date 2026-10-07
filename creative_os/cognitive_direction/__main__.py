"""Explicit frozen-file authoring/inspection only; no Adobe or voice operations."""
import argparse
from pathlib import Path

from video_contracts import read, write
from . import (
    compile_direction, compile_synthetic_direction, validate_direction,
    validate_synthetic_direction, inspect_direction, project_direction, project_synthetic_direction,
)


def main():
    parser = argparse.ArgumentParser(description='Cognitive Direction v0.2, intent only')
    parser.add_argument('command', choices=[
        'compile', 'validate', 'inspect', 'project',
        'compile-synthetic', 'validate-synthetic', 'project-synthetic',
    ])
    parser.add_argument('request')
    args = parser.parse_args(); request_path = Path(args.request).resolve()
    request = read(request_path)
    synthetic = args.command.endswith('-synthetic')
    shared = {'direction'} if args.command == 'inspect' else {'choreography'}
    allowed = set(shared)
    if synthetic:
        allowed.update({'fixture', 'restore', 'test_window_seconds'})
    elif args.command != 'inspect':
        allowed.update({
            'experience', 'plan', 'copy_handoff', 'motion_handoff', 'bundle', 'status', 'application', 'diagnostic',
        })
    if args.command.startswith('validate') or args.command.startswith('project'): allowed.add('direction')
    writing = args.command.startswith('compile') or args.command.startswith('project')
    if writing: allowed.add('output')
    if set(request) - allowed:
        raise ValueError('Unknown direction request field: ' + ', '.join(sorted(set(request) - allowed)))
    def path(key):
        return (request_path.parent / request[key]).resolve()
    def doc(key, optional=False):
        return None if optional and not request.get(key) else read(path(key))
    output = path('output') if writing else None
    if output is not None and output.exists():
        raise ValueError('Preserve direction history; choose a new output')
    if args.command == 'inspect':
        result = inspect_direction(doc('direction'))
    elif synthetic:
        choreography, fixture = doc('choreography'), doc('fixture')
        if args.command == 'compile-synthetic':
            result = compile_synthetic_direction(choreography, fixture, restore=request.get('restore', True),
                                                test_window_seconds=request.get('test_window_seconds', 30))
        else:
            function = validate_synthetic_direction if args.command == 'validate-synthetic' else project_synthetic_direction
            result = function(doc('direction'), choreography, fixture)
    else:
        sources = [doc(k, optional=k in ('copy_handoff', 'motion_handoff')) for k in (
            'choreography', 'experience', 'plan', 'copy_handoff', 'motion_handoff', 'bundle', 'status',
        )]
        kwargs = {'application': doc('application', optional=True)}
        if args.command == 'compile':
            result = compile_direction(*sources, **kwargs, diagnostic=request.get('diagnostic', False))
        else:
            function = validate_direction if args.command == 'validate' else project_direction
            if args.command == 'project': kwargs['diagnostic'] = request.get('diagnostic', False)
            result = function(doc('direction'), *sources, **kwargs)
    if writing:
        if args.command.startswith('compile') and result['compilation_status'] == 'FAIL':
            raise ValueError('Direction structural FAIL: ' + ', '.join(result['availability']['issues']))
        write(output, result)
        print({'output': str(output), 'status': 'PASS', 'public_render_ready': False})
    else:
        print(result)


if __name__ == '__main__': main()
