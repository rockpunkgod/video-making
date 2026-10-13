"""Synthetic review binding controls; not independent English certification."""
import json
from pathlib import Path
import tempfile
import unittest

from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.real_cases import digest, json_digest, material
from scripts.replay_current_paper import read_reviewed_question
from tests import test_option_only_partition as fixtures


class CurrentQuestionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def packet(self, change=None, question=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        question = question or fixtures.OptionOnlyPartitionTests().question()
        analysis = QuestionAnalyzer(self.registry).analyze(question)
        def write(name, value):
            raw = json.dumps(value).encode('utf-8')
            (root/name).write_bytes(raw)
            return {'path': name, 'sha256': digest(raw)}
        qref = write('question.json', question)
        aref = write('analysis.json', analysis)
        sref = write('source.json', {'questions': [material(question)]})
        sref['question_pointer'] = '/questions/0'
        review = {
            'stage': 'post_reveal_current_source_independent_question_review',
            'review_scope': 'private_current_question_review_only', 'reviewer_kind': 'AI',
            'source_commit': self.registry.index['source_baseline']['commit'],
            'author': question['action_executions'][0]['reviewer'],
            'reviewer': 'synthetic-review-binding-fixture-not-a-learner',
            'independent_from_author': True,
            'checks': {k: True for k in ['source_material', 'question_scope', 'trigger',
                                       'action', 'evidence', 'role', 'stop']},
            'review_notes': 'Synthetic metadata binding only, not actual semantic certification.',
            'question_id': question['question_id'], 'question_ref': qref, 'analysis_ref': aref,
            'source_question_ref': sref, 'analysis_sha256': json_digest(analysis),
            'evidence_graph_sha256': json_digest(analysis['evidence_graph']),
            'method_versions': analysis['method_versions'], 'answer_closed': analysis['answer_verification']['closed'],
        }
        if change:
            change(review)
        write('review.json', review)
        return root, question

    def test_current_review_can_admit_real_action_without_fabricating_blind_or_case(self):
        root, question = self.packet()
        accepted, binding = read_reviewed_question(root, 'review.json', self.registry)
        self.assertEqual(accepted, question)
        self.assertEqual(binding['review_scope'], 'private_current_question_review_only')
        self.assertNotIn('blind', binding)
        self.assertNotIn('case_id', binding)
        self.assertEqual(len(list(root.glob('*.json'))), 4)

    def test_self_review_is_not_independent(self):
        root, _ = self.packet(lambda r: r.update(reviewer=r['author']))
        with self.assertRaisesRegex(ValueError, 'distinct'):
            read_reviewed_question(root, 'review.json', self.registry)

    def test_old_source_review_cannot_be_admitted(self):
        root, _ = self.packet(lambda r: r.update(source_commit='old-source'))
        with self.assertRaisesRegex(ValueError, 'current-source'):
            read_reviewed_question(root, 'review.json', self.registry)

    def test_replay_and_graph_hashes_are_bound(self):
        for key in ['analysis_sha256', 'evidence_graph_sha256']:
            with self.subTest(key=key):
                root, _ = self.packet(lambda r: r.update({key: 'f'*64}))
                with self.assertRaisesRegex(ValueError, 'actual replay'):
                    read_reviewed_question(root, 'review.json', self.registry)

    def test_review_cannot_upgrade_partition_to_closed_answer(self):
        root, _ = self.packet(lambda r: r.update(answer_closed=True))
        with self.assertRaisesRegex(ValueError, 'actual replay'):
            read_reviewed_question(root, 'review.json', self.registry)

    def test_source_pointer_cannot_substitute_another_question(self):
        root, _ = self.packet(lambda r: r['source_question_ref'].update(question_pointer='/questions/1'))
        with self.assertRaisesRegex(ValueError, 'does not resolve'):
            read_reviewed_question(root, 'review.json', self.registry)

    def test_author_and_explicit_true_checks_cannot_be_faked_with_alias_or_integer(self):
        for change, expected in [
            (lambda r: r.update(author='not-the-annotation-author'), 'actual annotations'),
            (lambda r: r['checks'].update(evidence=1), 'checks must be explicit')]:
            root, _ = self.packet(change)
            with self.assertRaisesRegex(ValueError, expected):
                read_reviewed_question(root, 'review.json', self.registry)

    def test_terminal_author_cannot_hide_behind_a_different_action_author(self):
        from tests import test_question_verification as terminal_fixture
        factory=terminal_fixture.QuestionVerificationTests(); factory.registry=self.registry
        question=factory.question()
        question['question_verification_review']['reviewer']='synthetic-review-binding-fixture-not-a-learner'
        root,_=self.packet(question=question)
        with self.assertRaisesRegex(ValueError,'actual annotations'):
            read_reviewed_question(root,'review.json',self.registry)

    def test_lesson_author_cannot_hide_behind_a_different_action_author(self):
        from tests import test_terminal_lesson as lesson_fixture
        factory=lesson_fixture.TerminalLessonTests(); factory.registry=self.registry
        question=factory.question()
        author=question['action_executions'][0]['reviewer']
        question['question_verification_review']['reviewer']=author
        question['lesson_review']['reviewer']='synthetic-review-binding-fixture-not-a-learner'
        root,_=self.packet(question=question)
        with self.assertRaisesRegex(ValueError,'actual annotations'):
            read_reviewed_question(root,'review.json',self.registry)


if __name__ == '__main__':
    unittest.main()
