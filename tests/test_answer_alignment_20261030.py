"""Source, compatibility and consumer checks; no student outcome assertions."""
from copy import deepcopy
import hashlib
import json
import unittest

from core.registry import ROOT, Registry
from scripts.align_answer_20261030 import PREVIOUS, TARGET, prepare
from scripts.generate_assets import build, apply_reference_supplements


class October30AlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = Registry(snapshot_commit=PREVIOUS)
        cls.current = Registry()
        cls.assets = build(cls.current)

    def test_current_and_historical_registries_validate(self):
        self.assertEqual(self.current.validate()['status'], 'PASS')
        self.assertEqual(self.old.validate()['status'], 'PASS')
        self.assertEqual(self.current.index['source_baseline']['commit'], TARGET)

    def test_all_ids_roles_support_and_empirical_states_survive(self):
        self.assertEqual(set(self.old.methods), set(self.current.methods))
        self.assertEqual(len(self.current.methods), 82)
        for mid, old in self.old.methods.items():
            new = self.current.methods[mid]
            for key in ('brand_name', 'source_name', 'aliases', 'core_action', 'decision_rule',
                        'primary_role', 'secondary_roles', 'output_type', 'maturity_status',
                        'practical_value', 'first_use_test', 'evaluation', 'entry_copy'):
                self.assertEqual(old[key], new[key], (mid, key))
            self.assertEqual(old['full']['beginner_support'], new['full']['beginner_support'])
            self.assertFalse(new['student_ready'])

    def test_only_three_projection_versions_change(self):
        changed = {mid for mid in self.current.methods
                   if self.current.methods[mid]['version'] != self.old.methods[mid]['version']}
        self.assertEqual(changed, {'A06', 'A07', 'W05'})
        for mid in set(self.current.methods) - changed:
            self.assertEqual(self.old.methods[mid]['compact'], self.current.methods[mid]['compact'])

    def test_r09_original_entry_and_full_contract_unchanged(self):
        old, new = self.old.methods['R09'], self.current.methods['R09']
        for key in ('four_step_card', 'compact', 'stop_rule', 'challenge_prompt', 'visual_formula'):
            self.assertEqual(old[key], new[key])
        old_sections = [self.old.sources['sections'][sid]['content'] for sid in old['section_ids']]
        new_sections = [self.current.sources['sections'][sid]['content'] for sid in new['section_ids']]
        self.assertEqual(old_sections, new_sections)

    def test_source_files_and_sections_have_current_exact_hashes(self):
        manifest = self.current._load('provenance/manifest.yaml')
        self.assertEqual(len(manifest['files']), 22)
        for row in manifest['files']:
            raw = (ROOT/'provenance/ANSWER'/row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
        self.assertTrue(all(s['commit'] == TARGET for s in self.current.sources['sections'].values()))

    def test_cloze_relocation_is_explicit_and_old_snapshot_stays_readable(self):
        for mid in ('C01', 'C03'):
            old = self.old.methods[mid]
            new = self.current.methods[mid]
            self.assertIn('语篇行文结构的已核验操作', self.old.sources['sections'][old['section_ids'][0]]['heading'])
            self.assertEqual(self.current.sources['sections'][new['section_ids'][0]]['heading'],
                             '行文结构（结构认识与已核操作）')

    def test_w05_has_concept_not_obsolete_gap_or_three_action_cap(self):
        card = self.current.methods['W05']
        text = json.dumps(card, ensure_ascii=False)
        self.assertNotIn('动作面独立定义未核', text)
        self.assertNotIn('最多三个', text)
        self.assertNotIn('至多三个', text)
        self.assertIn('描写概念', text)
        self.assertIn('人物能力', card['stop_rule'])
        self.assertIn('描写概念', self.assets['student-guides/W05-动作拆链.md'])

    def test_current_source_risks_use_corrected_quotes(self):
        fixed = [r for r in self.current.risks if r['status'] == 'upstream_corrected_boundary_retained']
        self.assertEqual(len(fixed), 3)
        for risk in fixed:
            self.assertIn(risk['source_quote'], self.current.sources['sections'][risk['section_id']]['content'])

    def test_old_cases_preserved_and_not_credited_to_new_source(self):
        old, new = self.old.case_inventory(), self.current.case_inventory()
        self.assertEqual(old, new)
        self.assertTrue(all(not self.current.case_is_current(case) for case in new.values()))

    def test_new_names_are_independent_inspection_identities(self):
        for name in ('主语一致', '时态一致', '动静一致', '单复一致', '逻辑判断内容关联', '句子升华三部曲'):
            identity = self.current.course_identity(name)['identity']
            self.assertFalse(identity['equivalent_to_existing_brand'])
            self.assertEqual(identity['source']['commit'], TARGET)

    def test_no_superseded_supplement_appended_and_tampering_rejected(self):
        path = 'gaokao-english/references/cloze.md'
        self.assertEqual(self.assets[path], self.current.document(path))
        catalog = json.loads((ROOT/'creative/method-choreography/course-method-mapping.json').read_bytes())
        broken = deepcopy(catalog)
        broken['methods'][0]['definition'] += '\nSYNTHETIC change'
        with self.assertRaisesRegex(ValueError, 'supersession content mismatch'):
            apply_reference_supplements(self.current, dict(self.assets), broken)

    def test_migration_cannot_reinterpret_current_source_as_previous(self):
        with self.assertRaisesRegex(ValueError, 'explicit previous epoch'):
            prepare()


if __name__ == '__main__':
    unittest.main()
