"""Run current engineering checks into a new private, non-overwriting record.

This runner never publishes or replaces docs/final-acceptance.md. Human,
semantic and participant gates require separately reviewed evidence.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

from core.registry import ROOT, Registry
from core.release import regression_snapshot
from scripts.generate_assets import generate
from evaluation.harness import load_records


SMOKE_COMMANDS = (
    ('validate',), ('case-coverage',),
    ('analyze', 'examples/question-course.json', '--renderer', 'student'),
    ('analyze', 'examples/question-reviewed-course.json', '--renderer', 'content-export'),
    ('analyze', 'examples/question-action-course.json', '--renderer', 'content-export'),
    ('analyze', 'examples/question-lesson-course.json', '--renderer', 'legacy-wechat'),
    ('lesson', 'examples/passage-lesson.synthetic.json', '--renderer', 'legacy-wechat'),
    ('lesson', 'examples/passage-lesson.synthetic.json', '--renderer', 'content-export'),
    ('paper', 'examples/paper-course.json'),
    ('evaluate', 'evaluation/datasets/synthetic-observations.json'),
    ('evaluate', 'evaluation/datasets/real-observations.pending.json'),
    ('release-check', 'evaluation/release-review.example.json'),
    ('release-bindings', 'evaluation/release-review.example.json'),
) + tuple(
    ('analyze', example, '--renderer', renderer)
    for example in ('examples/writing-word-count.synthetic.json',
                    'examples/writing-image.synthetic.json',
                    'examples/writing-review.synthetic.json')
    for renderer in ('legacy-wechat', 'content-export')
)


def new_destination(output=None):
    private = (ROOT / 'local-data').resolve()
    if output is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        target = private / 'acceptance-runs' / (stamp + '-' + uuid4().hex[:8])
    else:
        requested = Path(output)
        target = (requested if requested.is_absolute() else ROOT / requested).resolve()
    if target == private or not target.is_relative_to(private):
        raise ValueError('Use a new output directory within local-data, not a current public entry')
    if target.exists():
        raise ValueError('Acceptance output already exists; preserve prior evidence')
    target.mkdir(parents=True, exist_ok=False)
    return target


def cli_smoke():
    rows = []
    for args in SMOKE_COMMANDS:
        process = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'answer_engine', *args],
                                 cwd=ROOT, capture_output=True, encoding='utf-8')
        rows.append({'command': ['python', '-m', 'answer_engine', *args],
                     'exit_code': process.returncode,
                     'stdout': process.stdout, 'stderr': process.stderr,
                     'scope': 'engineering example or pending-data check, not real learner evidence'})
    return rows


def describe_registry(registry):
    return {
        'source_commit': registry.index['source_baseline']['commit'],
        'method_count': len(registry.methods),
        'method_migration': dict(Counter(m['question_type'] for m in registry.methods.values())),
        'method_types': dict(Counter(m['method_type'] for m in registry.methods.values())),
        'maturity_counts': dict(Counter(m['maturity_status'] for m in registry.methods.values())),
        'practical_value_counts': dict(Counter(m['practical_value'] for m in registry.methods.values())),
        'student_ready_count': sum(m.get('student_ready') is True for m in registry.methods.values()),
        'source_repository_unchanged': 'not_verified_by_this_runner',
    }


def render_report(report):
    """Render observations only; never replay a canned historical completion narrative."""
    tests = report['after_refactor']
    sections = [
        '# Engineering acceptance run',
        '\n## 1. Final Status\n\n' + report['final_status'] +
        '。仅本次工程范围，不是全部目标完成。运行时间：' + report['started_at'],
        '\n## 2. Architecture\n\nRegistry → Analyzer / Composer → Evidence Graph → Renderer；'
        '本报告不以架构名称存在证明实际语义或教学效果。',
        '\n## 3. Completed Phases\n\n本次仅重跑 Phase 12 自动工程检查。'
        'Phase 0–11、13–14 的完整目标须逐项独立取证，不能从本次测试自动继承 PASS。',
        '\n## 4. Method Migration\n\n当前运行来源：`' + report['source_commit'] + '`。\n\n' +
        json.dumps({key: report[key] for key in ('method_migration', 'method_types',
                   'maturity_counts', 'practical_value_counts', 'student_ready_count')},
                   ensure_ascii=False, indent=2),
        '\n## 5. Tests\n\n' + json.dumps(tests, ensure_ascii=False, indent=2) +
        '\n\n逐项日志见 tests.log，CLI 实际输出见 cli-smoke.json。跳过不等于通过。'
        '不引用旧报告的测试数、固定旧日期或历史宿主认可。',
        '\n## 6. Evaluation Readiness\n\n' + report['evaluation_status'] +
        '。本次只运行合成/待测接口，不认证学生、盲测、Baseline收益或短版安全。',
        '\n## 7. Remaining Blockers\n\n完整源与英语语义、真实案例覆盖、整卷语义回归、'
        '旧宿主语义兼容及真实受试阶段链须分别审阅；本工具不自动填槽或升级方法。',
        '\n## 8. Final Acceptance\n\n仅 G14 的本次自动工程结果由下表记录；'
        '其他 Gate 不由本工具自动认证，应以当前独立逐项审计为准。\n\n'
        '| Gate | 本次证据状态 |\n|---|---|\n' + '\n'.join(
            '| G' + str(i) + ' | ' +
            (report['engineering_status'] if i == 14 else 'NOT_REASSESSED_BY_RUNNER') + ' |'
            for i in range(1, 17)),
    ]
    return '\n'.join(sections) + '\n'


def run(output=None):
    destination = new_destination(output)
    started = datetime.now(timezone.utc)
    registry = Registry()
    before = regression_snapshot(registry)
    (destination / 'snapshot-before.json').write_text(
        json.dumps(before, ensure_ascii=False, indent=2), encoding='utf-8')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'),
                                               top_level_dir=str(ROOT / 'tests'))
    with (destination / 'tests.log').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = regression_snapshot(Registry())
    stable = before == after
    validation, registry_validation, generated, smoke, validation_error = {}, {}, {}, [], None
    if result.wasSuccessful() and stable:
        try:
            registry_validation = registry.validate()
            generated = generate(check=True)
            validation = {**registry_validation, **generated}
            smoke = cli_smoke()
        except (ValueError, KeyError, OSError) as error:
            validation_error = str(error)
    successful = (result.wasSuccessful() and stable and bool(validation) and
                  validation_error is None and bool(smoke) and
                  all(row['exit_code'] == 0 for row in smoke))
    # A smoke command must not change source or tests after the initial check.
    stable = stable and before == regression_snapshot(Registry())
    successful = successful and stable
    report = describe_registry(registry)
    report.update({
        'started_at': started.isoformat(),
        'finished_at': datetime.now(timezone.utc).isoformat(),
        'duration_seconds': (datetime.now(timezone.utc) - started).total_seconds(),
        'final_status': 'PARTIAL' if successful else 'FAILED',
        'engineering_status': 'PASS' if successful else 'FAIL',
        'scope': 'current working tree engineering checks; not clean commit, semantic, participant or release certification',
        'output_directory': str(destination),
        'after_refactor': {
            'tests_run': result.testsRun, 'failures': len(result.failures),
            'errors': len(result.errors), 'skipped': len(result.skipped),
            'successful': result.wasSuccessful(),
            'skipped_tests': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
            'material_stable': stable, 'validation': validation,
            'registry': registry_validation, 'generated': generated,
            'validation_error': validation_error,
            'cli_commands_run': len(smoke),
            'cli_failures': sum(row['exit_code'] != 0 for row in smoke),
        },
        'evaluation_status': 'pending_real_participant_validation',
        'real_record_count': len(load_records(ROOT / 'evaluation/datasets/real-observations.pending.json')),
        'case_coverage': registry.case_coverage(),
        'current_public_reports_modified': False,
    })
    report.update(after)
    for name, value in (('engineering-acceptance.json', report), ('cli-smoke.json', smoke)):
        (destination / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (destination / 'final-acceptance.md').write_text(render_report(report), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='New private directory within local-data; never overwritten')
    args = parser.parse_args()
    value = run(args.output)
    print(json.dumps({key: value[key] for key in
                     ('final_status', 'engineering_status', 'output_directory', 'after_refactor')},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if value['engineering_status'] == 'PASS' else 1)
