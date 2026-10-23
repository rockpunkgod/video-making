"""Small, conservative CI selector; unknown changes retain full discovery.

The workflow always runs the original quick validation commands first. Only
these two leaf entry points have a reviewed affected-test mapping. Changes to
their consumers, tests, shared contracts, schemas, or CI itself run everything.
Use --tier full before delivery (workflow_dispatch also always selects full).
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_TESTS = (
    'tests.test_frozen_answer_consistency',
    'tests.test_frozen_answer_closure',
)
LEAF_TESTS = {
    'answer_engine/reviewed_locating_export.py': ('tests.test_locating_trace',),
    'answer_engine/method_application_export.py': (
        'tests.test_method_application', 'tests.test_cognitive_pov',
    ),
}


def read_changes(base, head, cwd=ROOT):
    """Use the PR merge base; include both sides of renames as delete/add.

    NUL separators preserve spaces and newlines in filenames. Missing history,
    malformed revisions or an unexpected Git status cannot select fewer tests.
    """
    if not all(re.fullmatch(r'[0-9a-fA-F]{40}', ref or '') for ref in (base, head)):
        raise ValueError('Missing or invalid PR commit SHA')
    result = subprocess.run(
        ['git', 'diff', '--name-status', '-z', '--no-renames', base + '...' + head, '--'],
        cwd=cwd, check=True, capture_output=True,
    )
    fields = result.stdout.decode('utf-8').split('\0')
    if fields[-1] != '' or len(fields[:-1]) % 2:
        raise ValueError('Unexpected Git name-status output')
    return list(zip(fields[:-1:2], fields[1:-1:2]))


def select_plan(changes, event='pull_request', tier='auto', diff_error=None):
    paths = [path for _, path in changes]
    reason = None
    if tier == 'full':
        reason = 'Explicit full regression requested'
    elif event != 'pull_request':
        reason = 'Main pushes, manual runs and unknown events require full regression'
    elif diff_error:
        reason = 'Cannot establish changed paths: ' + diff_error
    elif not changes:
        reason = 'No changed paths established; use full regression'
    elif any(status != 'M' or path not in LEAF_TESTS for status, path in changes):
        reason = 'Unmapped, shared, added, deleted or renamed path requires full regression'
    if reason:
        return {'tier': 'full', 'reason': reason, 'changed_paths': paths,
                'test_modules': [],
                'command': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']}
    modules = sorted(set(BOUNDARY_TESTS).union(
        *(LEAF_TESTS[path] for _, path in changes)))
    return {'tier': 'affected', 'reason': 'Only reviewed leaf entry points changed; frozen boundaries included',
            'changed_paths': paths, 'test_modules': modules,
            'command': [sys.executable, '-m', 'unittest', *modules, '-v']}


def write_report(report, path):
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tier', choices=('auto', 'full'), default='auto')
    parser.add_argument('--event', default=os.environ.get('CI_EVENT_NAME', 'local'))
    parser.add_argument('--base', default=os.environ.get('CI_BASE_SHA'))
    parser.add_argument('--head', default=os.environ.get('CI_HEAD_SHA'))
    parser.add_argument('--report')
    parser.add_argument('--plan-only', action='store_true', help='Print selection without claiming tests ran')
    args = parser.parse_args(argv)
    changes, diff_error = [], None
    if args.event == 'pull_request' and args.tier != 'full':
        try:
            changes = read_changes(args.base, args.head)
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            diff_error = str(exc)
    report = select_plan(changes, args.event, args.tier, diff_error)
    report.update(event=args.event, base=args.base, head=args.head,
                  state='planned' if args.plan_only else 'running', exit_code=None)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    write_report(report, args.report)
    if args.plan_only:
        return 0
    try:
        result = subprocess.run(report['command'], cwd=ROOT, check=False)
        code = result.returncode
        report.update(state='passed' if code == 0 else 'failed', exit_code=code)
    except OSError as exc:
        code = 1
        report.update(state='failed_to_start', exit_code=code, error=str(exc))
    write_report(report, args.report)
    print('Regression tier: {tier}; state: {state}; exit: {exit_code}'.format(**report), flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write('\nRegression tier: **{tier}**. Result: **{state}** (exit {exit_code}).\n'
                          .format(**report))
            summary.write('\n' + report['reason'] + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
