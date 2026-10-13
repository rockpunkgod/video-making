"""Current-epoch structure checks must not masquerade as student success."""
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from core.registry import ROOT, Registry
from scripts.audit_student_entries import audit, PRIORITY
from scripts import build_schemas


class CurrentEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.report = audit(cls.registry)

    def test_schema_generator_preserves_current_editorial_states(self):
        captured = {}
        with patch.object(build_schemas, 'write', side_effect=lambda name, schema: captured.update({name:schema})):
            build_schemas.build()
        generated = captured['method-card']
        stored = json.loads((ROOT/'schemas/method-card.json').read_text(encoding='utf-8'))
        self.assertEqual(generated, {key: value for key, value in stored.items() if key not in ('$schema','$id')})
        validator = Draft202012Validator(generated)
        for method in self.registry.methods.values():
            validator.validate(method)

    def test_priority_structure_does_not_certify_semantics_or_participants(self):
        self.assertEqual({row['method_id'] for row in self.report['priority_entries']}, set(PRIORITY))
        for row in self.report['priority_entries']:
            self.assertEqual(row['structural_gaps'], [])
            self.assertEqual(row['learner_acceptance'], 'pending_real_participant_validation')
            self.assertEqual(row['timed_delivery'], 'unmeasured')
        self.assertFalse(self.report['engineering_complete'])

    def test_audit_counts_actual_flags_not_historical_claims(self):
        counts = self.report['entry_counts']
        self.assertEqual(sum(counts.values()), len(self.registry.methods))
        self.assertEqual(counts.get('static_entry_ready',0), sum(
            method.get('student_ready') is True for method in self.registry.methods.values()))
        self.assertEqual(self.report['source_commit'], self.registry.index['source_baseline']['commit'])

    def test_held_guide_cannot_pass_as_independent_instruction(self):
        held = [row for row in self.report['methods'] if row['entry_state']=='held_for_reacceptance']
        self.assertTrue(held)
        for row in held:
            self.assertIn('independent_guide_exposes_four_steps', row['structural_gaps'])

    def test_checked_in_current_report_is_reproducible(self):
        stored=json.loads((ROOT/'evaluation/reports/current-student-entry-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(stored,self.report)

    def test_draft_guide_displays_actual_not_ready_flag(self):
        for row in self.report['priority_entries']:
            if row['entry_state']=='draft':
                text=(ROOT/row['guide_path']).read_text(encoding='utf-8')
                self.assertIn('当前 student_ready=false',text)

    def test_missing_first_cut_is_not_hidden_by_other_complete_fields(self):
        with patch.dict(self.registry.methods['F01']['four_step_card'], {'first_cut':''}):
            with self.assertRaises(ValidationError):
                audit(self.registry)


if __name__ == '__main__':
    unittest.main()
