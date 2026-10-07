"""Bound plan/validation/handoff; generation and native editing keep their existing entrypoints."""
import argparse
from pathlib import Path

from video_contracts import read, write
from .plan import build_plan, load_context, validate_plan
from .timing import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'validate', 'prepare', 'compare'))
    parser.add_argument('request')
    args = parser.parse_args(); path = Path(args.request).resolve(); request = read(path)
    if args.operation == 'compare':
        from .comparison import create_comparison
        create_comparison(request)
    elif args.operation == 'prepare':
        prepare(dict(request, context_file=str(path)))
    else:
        copy, spec = load_context(request)
        if args.operation == 'plan':
            target = Path(request['output']).resolve()
            if target.exists():
                raise FileExistsError('Preserve historical Performance Plans')
            result = build_plan(copy, spec, request.get('overrides'))
            validate_plan(result, copy, spec); write(target, result)
        else:
            validate_plan(read(request['performance_plan']), copy, spec)
    print('Narration performance engineering step complete; listening and release remain pending')


if __name__ == '__main__':
    main()
