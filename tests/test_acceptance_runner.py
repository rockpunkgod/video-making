"""Synthetic runner controls only; never a real full-suite or learner acceptance.

Nested one-case suites and in-memory Registry/snapshot/CLI declarations exercise
the runner. Report files and protected existing files use real temporary I/O.
"""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import run_acceptance as runner


class AcceptanceRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory(prefix='synthetic-acceptance-runner-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'repo'
        self.root.mkdir()
        self.protected={
            'docs/final-acceptance.md':b'SYNTHETIC current acceptance must survive\r\n',
            'docs/source-alignment-2026-10-13.md':b'SYNTHETIC current handoff must survive\r\n',
            'evaluation/reports/engineering-acceptance.json':b'{"synthetic_existing":true}\r\n',
        }
        for relative,raw in self.protected.items():
            path=self.root/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
        pending=self.root/'evaluation/datasets/real-observations.pending.json'
        pending.parent.mkdir(parents=True)
        pending.write_bytes(b'[]\n')
        self.registry=SimpleNamespace(
            index={'source_baseline':{'commit':'a'*40}},
            methods={
                'synthetic-A':{'question_type':'synthetic-reading','method_type':'method',
                               'maturity_status':'candidate','practical_value':'Useful','student_ready':True},
                'synthetic-B':{'question_type':'synthetic-reading','method_type':'sub_action',
                               'maturity_status':'draft','practical_value':'Useful','student_ready':False},
                'synthetic-C':{'question_type':'synthetic-writing','method_type':'method',
                               'maturity_status':'candidate','practical_value':'Useful','student_ready':1},
            },
            validate=Mock(return_value={'status':'PASS','methods':3}),
            case_coverage=Mock(return_value={'scope':'SYNTHETIC empty coverage','methods':[]}),
        )
        self.patch=patch.object(runner,'ROOT',self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def assert_protected_bytes(self):
        for relative,raw in self.protected.items():
            self.assertEqual((self.root/relative).read_bytes(),raw)

    def test_new_destination_is_unique_private_and_preserves_existing_paths(self):
        first=runner.new_destination()
        second=runner.new_destination()
        self.assertNotEqual(first,second)
        self.assertTrue(first.is_relative_to(self.root/'local-data'))
        self.assertTrue(second.is_relative_to(self.root/'local-data'))
        named=runner.new_destination('local-data/nested/new-synthetic-run')
        marker=named/'retained.bin';marker.write_bytes(b'SYNTHETIC prior evidence')
        with self.assertRaisesRegex(ValueError,'already exists'):
            runner.new_destination(named)
        self.assertEqual(marker.read_bytes(),b'SYNTHETIC prior evidence')
        self.assert_protected_bytes()

    def test_public_root_existing_file_and_escaped_destinations_are_rejected(self):
        for target in ('local-data','docs/new-run','docs/final-acceptance.md',
                       'local-data/../../escaped','../outside',self.root.parent/'outside'):
            with self.subTest(target=str(target)),self.assertRaises(ValueError):
                runner.new_destination(target)
        existing=self.root/'local-data/existing-file'
        existing.parent.mkdir(exist_ok=True)
        existing.write_bytes(b'prior file')
        with self.assertRaisesRegex(ValueError,'already exists'):
            runner.new_destination(existing)
        self.assertEqual(existing.read_bytes(),b'prior file')
        self.assertFalse((self.root.parent/'escaped').exists())
        self.assert_protected_bytes()

    def test_registry_description_uses_actual_counts_without_upstream_clean_claim(self):
        description=runner.describe_registry(self.registry)
        self.assertEqual(description['source_commit'],'a'*40)
        self.assertEqual(description['method_count'],3)
        self.assertEqual(description['method_migration'],{'synthetic-reading':2,'synthetic-writing':1})
        self.assertEqual(description['method_types'],{'method':2,'sub_action':1})
        self.assertEqual(description['maturity_counts'],{'candidate':2,'draft':1})
        self.assertEqual(description['practical_value_counts'],{'Useful':3})
        self.assertEqual(description['student_ready_count'],1)
        self.assertEqual(description['source_repository_unchanged'],'not_verified_by_this_runner')
        self.registry.methods.pop('synthetic-B')
        self.assertEqual(runner.describe_registry(self.registry)['method_count'],2)

    def report_fixture(self):
        return {**runner.describe_registry(self.registry),
                'started_at':'2099-02-03T04:05:06+00:00',
                'final_status':'FAILED','engineering_status':'FAIL',
                'after_refactor':{'tests_run':7,'failures':2,'errors':1,'skipped':3},
                'evaluation_status':'pending_real_participant_validation'}

    def test_render_report_preserves_dynamic_failures_skips_and_unassessed_gates(self):
        report=self.report_fixture();text=runner.render_report(report)
        self.assertIn('2099-02-03T04:05:06+00:00',text)
        for key,value in report['after_refactor'].items():
            self.assertIn('"'+key+'": '+str(value),text)
        self.assertIn('FAILED',text)
        self.assertIn('synthetic-reading',text)
        self.assertIn('pending_real_participant_validation',text)
        self.assertIn('| G14 | FAIL |',text)
        for gate in set(range(1,17))-{14}:
            self.assertIn('| G'+str(gate)+' | NOT_REASSESSED_BY_RUNNER |',text)
        self.assertNotIn('| G1 | PASS |',text)
        report.update(final_status='PARTIAL',engineering_status='PASS')
        text=runner.render_report(report)
        self.assertIn('| G14 | PASS |',text)
        self.assertIn('PARTIAL',text)
        self.assertIn('"skipped": 3',text)

    def synthetic_suite(self,outcome):
        class SyntheticCase(unittest.TestCase):
            def runTest(self):
                if outcome=='fail':self.fail('SYNTHETIC deliberate runner failure')
                if outcome=='skip':self.skipTest('SYNTHETIC deliberate runner skip')
                self.assertTrue(True,'SYNTHETIC one-case suite, not full acceptance')
        return unittest.TestSuite([SyntheticCase()])

    def execute_synthetic_run(self,*,outcome='pass',snapshots=None,smoke=None):
        base={'synthetic_snapshot':'unchanged'}
        if snapshots is None:snapshots=[deepcopy(base) for _ in range(3)]
        if smoke is None:smoke=[{'command':['SYNTHETIC smoke'],'exit_code':0,'stdout':'synthetic','stderr':''}]
        with ExitStack() as stack:
            stack.enter_context(patch.object(runner,'Registry',return_value=self.registry))
            snapshot=stack.enter_context(patch.object(runner,'regression_snapshot',side_effect=snapshots))
            discover=stack.enter_context(patch.object(runner.unittest.defaultTestLoader,'discover',
                                          return_value=self.synthetic_suite(outcome)))
            generate=stack.enter_context(patch.object(runner,'generate',return_value={'generated_assets':'PASS'}))
            cli=stack.enter_context(patch.object(runner,'cli_smoke',return_value=smoke))
            report=runner.run('local-data/synthetic-run')
        destination=Path(report['output_directory'])
        self.assertTrue(destination.is_relative_to(self.root/'local-data'))
        self.assertEqual(json.loads((destination/'engineering-acceptance.json').read_bytes()),report)
        self.assertEqual(json.loads((destination/'snapshot-before.json').read_bytes()),snapshots[0])
        self.assertEqual((destination/'final-acceptance.md').read_text(encoding='utf-8'),runner.render_report(report))
        self.assertEqual(report['after_refactor']['tests_run'],1)
        self.assertIn('registry',report['after_refactor'])
        self.assertIn('generated',report['after_refactor'])
        self.assertEqual(report['real_record_count'],0)
        self.assertFalse(report['current_public_reports_modified'])
        self.assertEqual(report['source_repository_unchanged'],'not_verified_by_this_runner')
        self.assert_protected_bytes()
        discover.assert_called_once_with(str(self.root/'tests'),top_level_dir=str(self.root/'tests'))
        return report,destination,cli,generate,snapshot

    def test_lightweight_success_writes_private_evidence_without_replacing_current_reports(self):
        report,destination,cli,generate,snapshot=self.execute_synthetic_run()
        self.assertEqual(report['engineering_status'],'PASS')
        self.assertEqual(report['final_status'],'PARTIAL')
        self.assertTrue(report['after_refactor']['material_stable'])
        self.assertEqual(report['method_count'],3)
        self.assertEqual(report['after_refactor']['cli_commands_run'],1)
        self.assertEqual(report['after_refactor']['registry'],{'status':'PASS','methods':3})
        self.assertEqual(report['after_refactor']['generated'],{'generated_assets':'PASS'})
        self.assertIn('SyntheticCase',(destination/'tests.log').read_text(encoding='utf-8'))
        cli.assert_called_once_with();generate.assert_called_once_with(check=True)
        self.assertEqual(snapshot.call_count,3)

    def test_failure_is_retained_and_prevents_cli_and_generation(self):
        report,destination,cli,generate,_=self.execute_synthetic_run(outcome='fail')
        self.assertEqual(report['engineering_status'],'FAIL')
        self.assertEqual(report['final_status'],'FAILED')
        self.assertEqual(report['after_refactor']['failures'],1)
        self.assertEqual(report['after_refactor']['cli_commands_run'],0)
        self.assertEqual(report['after_refactor']['registry'],{})
        self.assertEqual(report['after_refactor']['generated'],{})
        self.assertEqual(json.loads((destination/'cli-smoke.json').read_bytes()),[])
        self.assertIn('SYNTHETIC deliberate runner failure',(destination/'tests.log').read_text(encoding='utf-8'))
        cli.assert_not_called();generate.assert_not_called()
        with self.assertRaisesRegex(ValueError,'already exists'):
            runner.run('local-data/synthetic-run')

    def test_skips_remain_visible_and_never_become_whole_goal_pass(self):
        report,destination,_,_,_=self.execute_synthetic_run(outcome='skip')
        self.assertEqual(report['after_refactor']['skipped'],1)
        self.assertEqual(report['after_refactor']['skipped_tests'][0]['reason'],'SYNTHETIC deliberate runner skip')
        self.assertEqual(report['final_status'],'PARTIAL')
        text=(destination/'final-acceptance.md').read_text(encoding='utf-8')
        self.assertIn('"skipped": 1',text)
        self.assertIn('| G15 | NOT_REASSESSED_BY_RUNNER |',text)

    def test_material_change_during_suite_rejects_pass_without_running_cli(self):
        report,_,cli,generate,_=self.execute_synthetic_run(
            snapshots=[{'synthetic_snapshot':'before'},{'synthetic_snapshot':'changed'}])
        self.assertEqual(report['engineering_status'],'FAIL')
        self.assertFalse(report['after_refactor']['material_stable'])
        cli.assert_not_called();generate.assert_not_called()

    def test_material_change_during_cli_rejects_otherwise_passing_suite(self):
        report,_,cli,_,_=self.execute_synthetic_run(
            snapshots=[{'synthetic_snapshot':'before'},{'synthetic_snapshot':'before'},
                       {'synthetic_snapshot':'changed'}])
        self.assertEqual(report['engineering_status'],'FAIL')
        self.assertFalse(report['after_refactor']['material_stable'])
        cli.assert_called_once_with()

    def test_nonzero_cli_rejects_pass_and_preserves_exact_command_evidence(self):
        failed=[{'command':['SYNTHETIC failing smoke'],'exit_code':9,'stdout':'SYNTHETIC stdout','stderr':'SYNTHETIC stderr'}]
        report,destination,_,_,_=self.execute_synthetic_run(smoke=failed)
        self.assertEqual(report['engineering_status'],'FAIL')
        self.assertEqual(report['final_status'],'FAILED')
        self.assertTrue(report['after_refactor']['successful'])
        self.assertEqual(report['after_refactor']['cli_failures'],1)
        self.assertEqual(json.loads((destination/'cli-smoke.json').read_bytes()),failed)


if __name__=='__main__':unittest.main()
