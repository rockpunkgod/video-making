"""CI selection must fail closed when change scope cannot be established."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import ci_regression as ci


class CIRegressionTests(unittest.TestCase):
    def setUp(self):
        # Synthetic failure receipts must not append fake results to a real CI summary.
        summary = patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''})
        summary.start()
        self.addCleanup(summary.stop)

    def test_known_leaf_changes_include_consumers_and_frozen_boundaries(self):
        plan = ci.select_plan([('M', path) for path in ci.LEAF_TESTS])
        self.assertEqual(plan['tier'], 'affected')
        self.assertEqual(set(plan['test_modules']), {
            *ci.BOUNDARY_TESTS, 'tests.test_locating_trace',
            'tests.test_method_application', 'tests.test_cognitive_pov',
        })

    def test_unknown_shared_ci_and_test_changes_force_full_even_with_known_leaf(self):
        for path in ('new-module.py', 'schemas/question-input.json',
                     'video/schemas/example.json', 'video_contracts/answer_consistency.py',
                     '.github/workflows/validate.yml', 'scripts/ci_regression.py',
                     'tests/test_method_application.py', 'requirements-dev.txt', 'docs/example.md'):
            with self.subTest(path=path):
                plan = ci.select_plan([('M', next(iter(ci.LEAF_TESTS))), ('M', path)])
                self.assertEqual(plan['tier'], 'full')
                self.assertEqual(plan['command'][1:], ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])

    def test_add_delete_rename_or_unknown_status_cannot_select_affected(self):
        for status in ('A', 'D', 'R100', 'T', 'U', '?'):
            with self.subTest(status=status):
                self.assertEqual(ci.select_plan([(status, next(iter(ci.LEAF_TESTS)))])['tier'], 'full')

    def test_main_manual_local_empty_and_diff_failure_force_full(self):
        changes = [('M', next(iter(ci.LEAF_TESTS)))]
        for event in ('push', 'workflow_dispatch', 'local', 'unknown'):
            self.assertEqual(ci.select_plan(changes, event)['tier'], 'full')
        self.assertEqual(ci.select_plan(changes, tier='full')['tier'], 'full')
        self.assertEqual(ci.select_plan([])['tier'], 'full')
        self.assertEqual(ci.select_plan(changes, diff_error='missing history')['tier'], 'full')

    def test_missing_history_plans_full_without_running_tests(self):
        with patch.object(ci, 'read_changes', side_effect=ValueError('missing history')), \
                patch.object(ci.subprocess, 'run') as run:
            self.assertEqual(ci.main(['--event', 'pull_request', '--plan-only']), 0)
            run.assert_not_called()

    def test_diff_uses_merge_base_and_preserves_unusual_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            def git(*args):
                return subprocess.run(['git', *args], cwd=folder, check=True,
                                      capture_output=True, text=True).stdout.strip()
            git('init', '-b', 'main')
            git('config', 'user.name', 'Synthetic CI test')
            git('config', 'user.email', 'synthetic@example.invalid')
            path = Path(folder) / 'space name.txt'
            path.write_text('base', encoding='utf-8')
            git('add', '.'); git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD')
            git('checkout', '-b', 'feature')
            path.write_text('feature', encoding='utf-8')
            git('commit', '-am', 'feature')
            head = git('rev-parse', 'HEAD')
            git('checkout', 'main')
            (Path(folder) / 'base-only.txt').write_text('not part of PR', encoding='utf-8')
            git('add', '.'); git('commit', '-m', 'base advances')
            self.assertEqual(ci.read_changes(git('rev-parse', 'HEAD'), head, folder), [('M', 'space name.txt')])
            self.assertEqual(ci.read_changes(base, base, folder), [])

    def test_bad_revisions_never_reach_git(self):
        with patch.object(ci.subprocess, 'run') as run:
            for ref in (None, '', '--output=bad', 'main'):
                with self.assertRaises(ValueError):
                    ci.read_changes(ref, 'a' * 40)
            run.assert_not_called()

    def test_failure_is_propagated_and_receipt_cannot_claim_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'receipt.json'
            with patch.object(ci.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)):
                self.assertEqual(ci.main(['--tier', 'full', '--report', str(report)]), 7)
            receipt = json.loads(report.read_text('utf-8'))
            self.assertEqual((receipt['tier'], receipt['state'], receipt['exit_code']), ('full', 'failed', 7))

    def test_plan_only_receipt_never_claims_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'receipt.json'
            with patch.object(ci.subprocess, 'run') as run:
                self.assertEqual(ci.main(['--tier', 'full', '--plan-only', '--report', str(report)]), 0)
                run.assert_not_called()
            receipt = json.loads(report.read_text('utf-8'))
            self.assertEqual((receipt['state'], receipt['exit_code']), ('planned', None))


if __name__ == '__main__':
    unittest.main()
