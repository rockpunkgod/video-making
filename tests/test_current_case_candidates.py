"""Synthetic indexing controls, not semantic or learner validation."""
import json
from unittest.mock import patch

from core.real_cases import digest
from scripts.collect_current_case_candidates import collect
from tests.test_current_question_review import CurrentQuestionReviewTests


class CurrentCaseCandidateTests(CurrentQuestionReviewTests):
    def replay_packet(self):
        root, question = self.packet()
        review = json.loads((root/'review.json').read_bytes())
        paper = {'paper_id': 'synthetic-index-paper', 'questions': [question]}
        raw = json.dumps(paper).encode()
        (root/'paper.json').write_bytes(raw)
        paper_ref = {'path': 'paper.json', 'sha256': digest(raw)}
        review['source_question_ref'] = dict(paper_ref, question_pointer='/questions/0')
        raw = json.dumps(review).encode()
        (root/'review.json').write_bytes(raw)
        binding = {'path': 'review.json', 'sha256': digest(raw), 'question_id': question['question_id']}
        replay = {'source_commit': self.registry.index['source_baseline']['commit'],
                  'paper_id': paper['paper_id'], 'paper_material_ref': paper_ref,
                  'independent_question_reviews': [binding]}
        return root, replay

    def run_collect(self, root, replay, output='candidates.json'):
        raw = json.dumps(replay).encode()
        (root/'replay.json').write_bytes(raw)
        # Temporary fixtures are private test roots, not public Registry assets.
        with patch('scripts.collect_current_case_candidates.private_root', return_value=root):
            return collect(root, {'path': 'replay.json', 'sha256': digest(raw)}, output, self.registry)

    def test_actual_actions_do_not_register_or_assign_type(self):
        root, replay = self.replay_packet()
        result = self.run_collect(root, replay)
        self.assertEqual(result['reviewed_question_count'], 1)
        self.assertGreater(result['candidate_question_method_count'], 0)
        for candidate in result['candidates']:
            self.assertIsNone(candidate['case_type'])
            self.assertFalse(candidate['registration_eligible'])
            self.assertTrue(candidate['own_executions'])
        self.assertEqual(result['filled_case_slots'], 0)
        self.assertEqual(result['new_blind_sample_count'], 0)

    def test_duplicate_review_fails_before_output(self):
        root, replay = self.replay_packet()
        replay['independent_question_reviews'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.run_collect(root, replay)
        self.assertFalse((root/'candidates.json').exists())

    def test_changed_review_bytes_fail(self):
        root, replay = self.replay_packet()
        (root/'review.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            self.run_collect(root, replay)
        self.assertFalse((root/'candidates.json').exists())

    def test_old_epoch_and_overwrite_refused(self):
        root, replay = self.replay_packet()
        self.run_collect(root, replay)
        previous = (root/'candidates.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'new private'):
            self.run_collect(root, replay)
        self.assertEqual((root/'candidates.json').read_bytes(), previous)
        replay['source_commit'] = 'old'
        with self.assertRaisesRegex(ValueError, 'epoch'):
            self.run_collect(root, replay, 'old.json')
