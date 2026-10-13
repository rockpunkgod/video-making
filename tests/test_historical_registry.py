from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import shutil
import json

from core.registry import ROOT, Registry
from core.analyzer import QuestionAnalyzer

BASELINE='b04ebc26d7fa096404111a0bb12f6c77cc8525b9'


class HistoricalRegistryTests(unittest.TestCase):
    def test_history_loads_all_original_assets(self):
        history=Registry(snapshot_commit=BASELINE)
        self.assertTrue(history.is_historical)
        self.assertEqual(history.index['source_baseline']['commit'],BASELINE)
        self.assertEqual(history.validate()['methods'],82)
        self.assertEqual(history.methods['R06']['version'],'1.1.0')
        self.assertEqual(history.methods['R06']['method_type'],'method')

    def test_history_replays_without_current_card_changes(self):
        history=Registry(snapshot_commit=BASELINE)
        question={'question_id':'history-structural-replay','question_type':'阅读理解',
                  'stem':'Which title fits?','task_type':'title',
                  'passage':'Structural transport fixture, not a real learner study.',
                  'options':{'A':'One','B':'Two','C':'Three','D':'Four'}}
        frozen=QuestionAnalyzer(history).analyze(question)
        current=Registry()
        current.methods['R09']['core_action']='Different current action for isolation test only.'
        self.assertEqual(QuestionAnalyzer(history).analyze(question),frozen)
        self.assertNotEqual(QuestionAnalyzer(current).analyze(question),frozen)

    def test_bad_or_missing_revision_is_rejected(self):
        for value in ('../../outside','b04ebc2','A'*40):
            with self.assertRaisesRegex(ValueError,'full historical source commit'):
                Registry(snapshot_commit=value)
        with self.assertRaisesRegex(ValueError,'snapshot is missing'):
            Registry(snapshot_commit='0'*40)

    def test_changed_historical_bytes_are_rejected(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            target=root/'provenance/runtime-snapshots'/BASELINE
            shutil.copytree(ROOT/'provenance/runtime-snapshots'/BASELINE,target)
            (target/'method-registry/reading.yaml').write_bytes(b'tampered')
            with patch('core.registry.ROOT',root):
                with self.assertRaisesRegex(ValueError,'Historical runtime asset changed'):
                    Registry(snapshot_commit=BASELINE)

    def test_historical_registry_does_not_follow_current_assets(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            target=root/'provenance/runtime-snapshots'/BASELINE
            shutil.copytree(ROOT/'provenance/runtime-snapshots'/BASELINE,target)
            shutil.copytree(ROOT/'schemas',root/'schemas')
            (root/'method-registry').mkdir()
            (root/'method-registry/reading.yaml').write_bytes(b'current-invalid')
            with patch('core.registry.ROOT',root):
                history=Registry(snapshot_commit=BASELINE)
                self.assertIn('R01',history.methods)
                self.assertTrue(history.case_inventory())

    def test_incomplete_historical_asset_manifest_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            target=root/'provenance/runtime-snapshots'/BASELINE
            shutil.copytree(ROOT/'provenance/runtime-snapshots'/BASELINE,target)
            manifest_path=target/'snapshot-manifest.json'
            manifest=json.loads(manifest_path.read_bytes())
            manifest['runtime_assets']=[row for row in manifest['runtime_assets']
                                        if row['path']!='method-registry/reading.yaml']
            manifest_path.write_bytes(json.dumps(manifest).encode())
            with patch('core.registry.ROOT',root):
                with self.assertRaisesRegex(ValueError,'asset is not bound'):
                    Registry(snapshot_commit=BASELINE)


if __name__=='__main__':
    unittest.main()
