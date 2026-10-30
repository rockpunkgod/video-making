"""Compatibility controls; synthetic inputs carry no teaching evidence."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from scripts.rebind_question_corpus import rebind_question, digest_text


class RebindTests(unittest.TestCase):
    def setUp(self):
        self.old = SimpleNamespace(index={'source_baseline': {'commit': 'old'}},
            methods={'R01': {'version': '1', 'core_action': 'check B'}},
            sources={'sections': {'s1': {'path': 'reading', 'heading': 'one',
                'commit': 'old', 'content': 'before'}}})
        self.new = deepcopy(self.old)
        self.new.index['source_baseline']['commit'] = 'new'
        self.new.sources['sections'] = {
            's1': {'path': 'reading', 'heading': 'different', 'commit': 'new', 'content': 'wrong'},
            's2': {'path': 'reading', 'heading': 'one', 'commit': 'new', 'content': 'after'}}
        self.changes = {('reading', 'one'): {'new_heading': 'one',
            'before_sha256': digest_text('before'), 'after_sha256': digest_text('after')}}
        self.q = {'question_id': 'synthetic', 'question_type': '阅读理解',
            'stem': 'Synthetic', 'passage': 'Original', 'requested_chain': ['R01'],
            'review': {'author': 'historical author', 'method_id': 'R01',
                'method_version': '1', 'source_commit': 'old', 'source_section_ids': ['s1']}}

    def test_reused_offset_maps_by_historical_identity_and_preserves_copy(self):
        original = deepcopy(self.q)
        rebound, audit = rebind_question(self.q, self.old, self.new, self.changes)
        self.assertEqual(rebound['review']['source_section_ids'], ['s2'])
        self.assertEqual(rebound['review']['author'], 'historical author')
        self.assertEqual(self.q, original)
        self.assertFalse(audit['new_independent_English_review'])
        self.assertFalse(audit['new_case_admission'])

    def test_unapproved_or_tampered_delta_rejected(self):
        for changes in ({}, {('reading', 'one'): dict(self.changes[('reading', 'one')], after_sha256='wrong')}):
            with self.assertRaises(ValueError):
                rebind_question(self.q, self.old, self.new, changes)

    def test_foreign_epoch_rejected(self):
        self.q['review']['source_commit'] = 'foreign'
        with self.assertRaises(ValueError):
            rebind_question(self.q, self.old, self.new, self.changes)

    def test_version_and_contract_changes_require_reauthoring(self):
        for field, value in [('version', '2'), ('core_action', 'different action')]:
            registry = deepcopy(self.new)
            registry.methods['R01'][field] = value
            with self.assertRaises(ValueError):
                rebind_question(self.q, self.old, registry, self.changes)


if __name__ == '__main__':
    unittest.main()
