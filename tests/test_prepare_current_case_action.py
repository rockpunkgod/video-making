"""Synthetic preparation safety tests, not real Case certification."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.registry import Registry
from core.real_cases import digest, material
from scripts.prepare_current_case_action import prepare
from tests import test_option_only_partition as partition_tests


class CurrentCasePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def packet(self, change=None, registered_version='1.1.0'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        question = partition_tests.OptionOnlyPartitionTests().question()
        frozen = material(question)
        request = {'question_id': question['question_id'],
                   'canonical_question_id': question['question_id'], 'method_id': 'F01',
                   'method_version': '1.1.0', 'case_type': 'canonical',
                   'source': {'exam_id': 'synthetic-paper'},
                   'blind': {'path': 'blind.json', 'sha256': 'b'*64},
                   'reveal': {'path': 'reveal.json', 'sha256': 'c'*64},
                   'action': {'path': 'old-action.json', 'sha256': 'd'*64},
                   'case_review': {'path': 'old-review.json', 'sha256': 'e'*64}}
        request_raw = json.dumps(request).encode()
        (root/'old-request.json').write_bytes(request_raw)
        request_ref = {'path': 'old-request.json', 'sha256': digest(request_raw)}
        record = {'case_id': 'synthetic-existing-case', 'registration_request_ref': request_ref,
                  'registration_key': [question['question_id'], 'F01', 'canonical', registered_version]}
        old_action = {'question': {'action_executions': [{'execution_id': 'old-execution'}]}}
        if change:
            change(question)
        (root/'new-input.json').write_text(json.dumps(question), encoding='utf-8')
        catalog = {'revision': 1, 'sha256': 'f'*64, 'cases': [{'path': 'existing-case.json'}]}
        for target, result in [
            ('Registry', self.registry), ('load_catalog', catalog), ('_runtime_contexts', {}),
            ('_validate_request', (None, frozen, None))]:
            mock = patch('scripts.prepare_current_case_action.'+target, return_value=result)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch('scripts.prepare_current_case_action.artifact',
                     side_effect=lambda dataset, ref: record if ref['path']=='existing-case.json' else old_action)
        mock.start()
        self.addCleanup(mock.stop)
        return root, request_raw, catalog

    def test_new_packet_does_not_register_or_rewrite_history(self):
        root, raw, catalog = self.packet()
        before = deepcopy(catalog)
        report = prepare(root, 'old-request.json', 'new-input.json', 'current-packet')
        self.assertEqual((root/'old-request.json').read_bytes(), raw)
        self.assertEqual(catalog, before)
        action = json.loads((root/'current-packet/action.json').read_text(encoding='utf-8'))
        pending = json.loads((root/'current-packet/pending-request.json').read_text(encoding='utf-8'))
        self.assertIsNone(action['analysis']['answer'])
        self.assertEqual(action['phase'], 'post_reveal_current_source_action_not_new_blind')
        self.assertEqual(report['new_blind_sample_count'], 0)
        self.assertEqual(report['new_unique_question_count'], 0)
        self.assertFalse(report['registration_applied'])
        self.assertNotIn('case_review', pending)
        self.assertEqual(pending['method_version'], self.registry.methods['F01']['version'])
        self.assertEqual(pending['source_commit'], self.registry.index['source_baseline']['commit'])
        self.assertEqual(pending['source_commit'], action['source_commit'])

    def test_original_material_change_is_rejected_without_output(self):
        root, _, _ = self.packet(lambda q: q.update(passage='replaced source'))
        with self.assertRaisesRegex(ValueError, 'preserve all frozen'):
            prepare(root, 'old-request.json', 'new-input.json', 'current-packet')
        self.assertFalse((root/'current-packet').exists())

    def test_old_execution_identity_cannot_be_reversioned(self):
        root, _, _ = self.packet(lambda q: q['action_executions'][0].update(execution_id='old-execution'))
        with self.assertRaisesRegex(ValueError, 'distinct new action identity'):
            prepare(root, 'old-request.json', 'new-input.json', 'current-packet')

    def test_wrong_version_is_not_automatically_updated(self):
        root, _, _ = self.packet(lambda q: q['action_executions'][0].update(method_version='1.1.0'))
        with self.assertRaisesRegex(ValueError, 'newly authored executions'):
            prepare(root, 'old-request.json', 'new-input.json', 'current-packet')

    def test_existing_packet_is_never_overwritten(self):
        root, _, _ = self.packet()
        (root/'current-packet').mkdir()
        with self.assertRaisesRegex(ValueError, 'without overwriting'):
            prepare(root, 'old-request.json', 'new-input.json', 'current-packet')

    def test_destination_cannot_escape_private_dataset(self):
        root, _, _ = self.packet()
        with self.assertRaisesRegex(ValueError, 'private output directory'):
            prepare(root, 'old-request.json', 'new-input.json', '../escaped-packet')

    def test_existing_current_version_credit_is_not_prepared_again(self):
        root, _, _ = self.packet(registered_version=self.registry.methods['F01']['version'])
        with self.assertRaisesRegex(ValueError, 'already registered'):
            prepare(root, 'old-request.json', 'new-input.json', 'current-packet')
        self.assertFalse((root/'current-packet').exists())


if __name__ == '__main__':
    unittest.main()
