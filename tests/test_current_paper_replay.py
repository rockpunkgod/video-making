"""Synthetic source-preserving paper binding controls, not teaching results."""
from copy import deepcopy
import unittest

from scripts.replay_current_paper import bind_questions


class CurrentPaperBindingTests(unittest.TestCase):
    def paper(self):
        return {'paper_id': 'synthetic-paper', 'questions': [
            {'question_id': 'synthetic-1', 'question_type': '语法填空',
             'task_type': 'grammar_form_completion', 'stem': 'synthetic blank',
             'passage': 'program-only source', 'given_word': 'program',
             'relations': [{'old': 'unsafe history'}],
             'observations': [{'old': 'unsafe history'}],
             'action_executions': [{'method_version': 'old'}], 'requested_chain': ['OLD']},
            {'question_id': 'synthetic-2', 'question_type': '语法填空',
             'task_type': 'grammar_form_completion', 'stem': 'synthetic second blank',
             'passage': 'another program-only source', 'given_word': None}]}

    def test_control_discards_old_claims_but_preserves_hint_and_task(self):
        original = self.paper()
        before = deepcopy(original)
        control, current = bind_questions(original, [])
        self.assertEqual(original, before)
        self.assertEqual(control, current)
        for key in ['relations', 'observations', 'action_executions', 'requested_chain']:
            self.assertNotIn(key, current['questions'][0])
        self.assertEqual(current['questions'][0]['given_word'], 'program')
        self.assertIsNone(current['questions'][1]['given_word'])
        self.assertEqual(current['questions'][0]['task_type'], 'grammar_form_completion')

    def test_only_explicit_reviewed_question_is_inserted(self):
        paper = self.paper()
        _, raw = bind_questions(paper, [])
        reviewed = deepcopy(raw['questions'][0])
        reviewed['action_executions'] = [{'new': 'current reviewed action'}]
        control, current = bind_questions(paper, [reviewed])
        self.assertNotIn('action_executions', control['questions'][0])
        self.assertEqual(current['questions'][0], reviewed)
        self.assertNotIn('action_executions', current['questions'][1])
        reviewed['passage'] = 'subsequent external mutation'
        self.assertEqual(current['questions'][0]['passage'], 'program-only source')

    def test_changed_material_or_hint_cannot_be_inserted(self):
        for field in ['passage', 'given_word', 'stem']:
            paper = self.paper()
            _, current = bind_questions(paper, [])
            reviewed = current['questions'][0]
            reviewed[field] = 'replaced'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'original paper'):
                bind_questions(paper, [reviewed])

    def test_changed_task_scope_is_not_silently_inherited(self):
        paper = self.paper()
        _, current = bind_questions(paper, [])
        reviewed = current['questions'][0]
        reviewed['task_type'] = 'title'
        with self.assertRaisesRegex(ValueError, 'task scope'):
            bind_questions(paper, [reviewed])

    def test_duplicate_or_foreign_review_does_not_expand_paper(self):
        paper = self.paper()
        _, current = bind_questions(paper, [])
        reviewed = current['questions'][0]
        with self.assertRaisesRegex(ValueError, 'duplicate or outside'):
            bind_questions(paper, [reviewed, reviewed])
        reviewed['question_id'] = 'not-in-paper'
        with self.assertRaisesRegex(ValueError, 'duplicate or outside'):
            bind_questions(paper, [reviewed])

    def test_duplicate_source_ids_are_rejected(self):
        paper = self.paper()
        paper['questions'].append(deepcopy(paper['questions'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate source'):
            bind_questions(paper, [])


if __name__ == '__main__':
    unittest.main()
