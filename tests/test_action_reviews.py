"""Synthetic program checks only, never learner/exam effectiveness evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from scripts.collect_action_reviews import collect, load_metadata, review_action, public_metadata
from scripts.ingest_exam_sources import freeze_json, sha
from tests.test_execution import action, span


def fixture():
    original = {'question_id': 'program-only-q1', 'question_type': '七选五',
                'stem': 'program-only synthetic partition, not an exam',
                'passage': 'alpha beta gamma', 'options': {'A': 'alpha', 'B': 'beta'},
                'task_type': 'program-only'}
    question = deepcopy(original)
    question.update({'requested_chain': ['F01'],
        'observations': [{'method_id': 'F01', 'evidence': [span()], 'reviewed': True}],
        'action_executions': [action('partition-' + axis, 'F01', 'reducer',
            {'kind': 'candidate_partition', 'axis': axis,
             'groups': [{'label': 'program-only same group', 'candidates': ['A', 'B']}]})
            for axis in ('sentence', 'actor', 'time')]})
    mechanical = {'exam_id': 'program-only', 'pass': 'blind', 'inputs': {'questions': [original]}}
    request = {'exam_id': 'program-only', 'stage': 'post_reveal_action_review',
        'reviewer': 'synthetic-program-not-a-learner', 'reviewer_kind': 'AI', 'method_id': 'F01',
        'mechanical_prediction_sha256': 'synthetic-unbound-until-file-frozen', 'question': question,
        'semantic_review': {k: 'program-only role review, not English certification' for k in
            ('trigger', 'action', 'evidence', 'output', 'stop', 'transfer', 'practical_benefit', 'limitations')}}
    request['semantic_review']['proposed_case_type'] = None
    return request, mechanical


class ActionReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = QuestionAnalyzer(Registry())

    def test_own_artifacts_do_not_require_or_imply_answer(self):
        request, mechanical = fixture(); before = deepcopy((request, mechanical))
        report = review_action(request, mechanical, self.analyzer)
        metadata = public_metadata(report)
        self.assertEqual(metadata['produced_action_count'], 3)
        self.assertTrue(metadata['answer_withheld'])
        self.assertFalse(metadata['whole_question_content_eligible'])
        self.assertEqual(metadata['registry_updates'], 0)
        self.assertIsNone(metadata['case_type'])
        self.assertNotIn('alpha', json.dumps(metadata))
        self.assertEqual((request, mechanical), before)

    def test_timing_and_complete_role_review_required(self):
        request, mechanical = fixture(); request['stage'] = 'blind'
        with self.assertRaisesRegex(ValueError, 'post-reveal'):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture(); request['semantic_review']['stop'] = ''
        with self.assertRaisesRegex(ValueError, 'Nonempty'):
            review_action(request, mechanical, self.analyzer)

    def test_material_and_task_are_immutable(self):
        for field in ('passage', 'task_type'):
            request, mechanical = fixture(); request['question'][field] = 'replacement'
            with self.assertRaisesRegex(ValueError, 'changed'):
                review_action(request, mechanical, self.analyzer)

    def test_decisions_missing_actions_and_bad_partitions_rejected(self):
        request, mechanical = fixture(); request['question']['relations'] = [{'effect': 'retain'}]
        with self.assertRaises(ValueError):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture(); request['question']['action_executions'] = []
        with self.assertRaisesRegex(ValueError, 'actual own'):
            review_action(request, mechanical, self.analyzer)
        request, mechanical = fixture()
        request['question']['action_executions'][0]['output']['groups'][0]['candidates'] = ['A']
        with self.assertRaisesRegex(ValueError, 'every option'):
            review_action(request, mechanical, self.analyzer)

    def test_freeze_binding_and_metadata_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); request, mechanical = fixture()
            prediction = root / 'predictions/program-only/blind.json'; freeze_json(prediction, mechanical)
            request['mechanical_prediction_sha256'] = sha(prediction.read_bytes())
            request_path = root / 'action-reviews/program-only/F01.request.json'
            freeze_json(request_path, request)
            with self.assertRaisesRegex(ValueError, 'existing reveal'):
                collect(root, request_path)
            freeze_json(root / 'results/program-only/reveal.json', {'stage': 'synthetic-program-reveal'})
            metadata = collect(root, request_path)
            self.assertEqual(collect(root, request_path), metadata)
            self.assertEqual(load_metadata(root, 'program-only'), [metadata])
            changed = deepcopy(request); changed['mechanical_prediction_sha256'] = 'wrong'
            other = root / 'action-reviews/program-only/F01.changed.json'; freeze_json(other, changed)
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                collect(root, other)
            # Derived metadata refuses a changed original request, not just source drift.
            request_path.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'request binding'):
                load_metadata(root, 'program-only')

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                collect(directory, Path(directory).parent / 'outside.json')
            root = Path(directory); request, _ = fixture()
            for relative in ('action-reviews/F01.request.json',
                             'action-reviews/wrong-exam/F01.request.json'):
                path = root / relative; freeze_json(path, request)
                with self.assertRaisesRegex(ValueError, 'own exam directory'):
                    collect(root, path)
        with self.assertRaises(ValueError):
            load_metadata('.', '../outside')
