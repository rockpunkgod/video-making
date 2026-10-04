"""Case metadata coverage is not question correctness or teaching validation."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from core.registry import Registry,load,CASE_TYPES


class CaseCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry()

    def test_all_methods_have_five_reported_slots_without_inventing_cases(self):
        coverage=self.r.case_coverage()
        self.assertEqual(coverage['method_count'],82)
        self.assertEqual(coverage['registered_case_count'],106)
        self.assertEqual(coverage['unregistered_slot_count'],304)
        self.assertEqual(coverage['formal_method_count'],30)
        self.assertEqual(coverage['formal_unregistered_slot_count'],104)
        self.assertEqual(coverage['formal_methods_with_missing_slots'],26)
        self.assertEqual(coverage['core_method_count'],42)
        self.assertEqual(coverage['core_unregistered_slot_count'],144)
        self.assertFalse(coverage['registration_complete'])
        for m in coverage['methods']:
            self.assertEqual([s['case_type'] for s in m['slots']],list(CASE_TYPES))
            for s in m['slots']:
                if s['registration']=='unregistered':
                    self.assertIsNone(s['path']); self.assertIsNone(s['case_id'])
                    self.assertEqual(s['evidence_status'],'evidence_gap'); self.assertTrue(s['reason'])

    def test_registered_gap_is_not_unregistered_or_a_verified_success(self):
        coverage=self.r.case_coverage(); m=next(m for m in coverage['methods'] if m['method_id']=='R03')
        self.assertEqual(m['slots'][0]['registration'],'registered')
        self.assertEqual(m['slots'][0]['evidence_status'],'evidence_gap')
        self.assertFalse(m['registration_complete']); self.assertFalse(m['registered_examples_complete'])
        for mid in self.r.index['golden_methods']:
            golden=next(m for m in coverage['methods'] if m['method_id']==mid)
            self.assertTrue(golden['registration_complete'])
            self.assertFalse(golden['registered_examples_complete'])
        self.assertIn('no full-question',coverage['scope'])

    def test_duplicate_or_stale_case_index_is_rejected(self):
        original=load('cases/registry.yaml')
        for mutation in ['duplicate','missing','foreign','invalid']:
            index=deepcopy(original)
            if mutation=='duplicate': index['case_files'].append(index['case_files'][0])
            elif mutation=='missing': index['case_files'].pop()
            elif mutation=='foreign': index['case_files'].append('cases/not-a-registered-case.yaml')
            else: index['case_files'].append(None)
            with patch('core.registry.load',side_effect=lambda path:index if path=='cases/registry.yaml' else load(path)):
                with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.r.case_coverage()

    def test_wrong_type_question_role_or_output_cannot_fill_a_slot(self):
        path=self.r.methods['R03']['cases']['canonical']; original=load(path)
        for field,value in [('case_type','transfer'),('question_type','语法填空'),('method_role','decider'),('expected_output','decide'),('method_id','R04')]:
            case={**original,field:value}
            with patch('core.registry.load',side_effect=lambda p:case if p==path else load(p)):
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,'mismatch'): self.r.case_coverage()

    def test_duplicate_case_ids_and_reused_paths_are_rejected(self):
        path=self.r.methods['R03']['cases']['canonical']; case=load(path)
        case['case_id']=load(self.r.methods['R01']['cases']['canonical'])['case_id']
        with patch('core.registry.load',side_effect=lambda p:case if p==path else load(p)):
            with self.assertRaisesRegex(ValueError,'Duplicate case ID'): self.r.case_coverage()
        r=Registry(); r.methods['R03']['cases']['transfer']=path
        with self.assertRaisesRegex(ValueError,'reused'): r.case_coverage()

    def test_missing_file_and_unknown_slot_are_errors_not_silent_gaps(self):
        r=Registry(); r.methods['R03']['cases']['canonical']='cases/no-such-case.yaml'
        with self.assertRaisesRegex(ValueError,'Missing or unreadable'): r.case_coverage()
        r=Registry(); r.methods['R03']['cases']['made_up']='cases/no-such-case.yaml'
        with self.assertRaisesRegex(ValueError,'Unknown case type'): r.case_coverage()


if __name__=='__main__': unittest.main()
