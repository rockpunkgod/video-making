"""Artificial parsing/control tests. No exam text or answer keys are bundled."""
import unittest
from scripts.exam_profiles_2025 import choices, parse, explanation_stop
from scripts.ingest_exam_sources import sha


class ExamProfiles2025Tests(unittest.TestCase):
    def test_printed_options_allow_missing_dot_without_prose_a(self):
        self.assertEqual(choices(['A first\tB. second','C. third\tD. fourth']),
                         {'A':'first','B':'second','C':'third','D':'fourth'})
        self.assertEqual(choices(['A. A story\tB. A visit\tC. A name\tD. A task'])['A'],'A story')

    def test_option_drift_rejected(self):
        for lines in [['A. first B. second C. third'],['A. first B. second B. duplicate D. fourth']]:
            with self.assertRaisesRegex(ValueError,'incomplete/ambiguous'): choices(lines)

    def test_unknown_or_reveal_source_rejected(self):
        for source in [{'exam_id':'gaokao-2024-I','source_kind':'blank'},
                       {'exam_id':'gaokao-2025-I','source_kind':'reveal'}]:
            with self.assertRaisesRegex(ValueError,'Unsupported'): parse(source)

    def test_automatic_numbering_requires_review(self):
        with self.assertRaisesRegex(ValueError,'Automatic numbering'):
            parse({'exam_id':'gaokao-2025-II','source_kind':'blank','automatic_numbered_paragraphs':1})

    def test_changed_extraction_or_missing_sections_rejected(self):
        source={'exam_id':'gaokao-2025-II','source_kind':'blank','automatic_numbered_paragraphs':0,
                'text':'PROGRAM-ONLY control','text_sha256':sha(b'PROGRAM-ONLY control'),'paragraphs':['PROGRAM-ONLY control']}
        with self.assertRaisesRegex(ValueError,'sections incomplete'): parse(source)
        source['paragraphs']=['changed']
        with self.assertRaisesRegex(ValueError,'extraction changed'): parse(source)

    def test_numbered_detail_is_not_mistaken_for_new_question(self):
        lines=['【56题详解】','56. PROGRAM-ONLY explanation','【57题详解】','another detail']
        self.assertEqual(explanation_stop(lines,0,56),2)
        lines=['【65题详解】','PROGRAM-ONLY detail','66. PROGRAM-ONLY writing task']
        self.assertEqual(explanation_stop(lines,0,65),2)

    def test_next_question_inside_objective_range_ends_detail(self):
        lines=['【31题详解】','PROGRAM-ONLY detail','32. PROGRAM-ONLY next question','A. one B. two']
        self.assertEqual(explanation_stop(lines,0,31),2)

    def test_independent_passage_or_section_heading_ends_detail(self):
        for heading in ['A','B','C','D','第二节(共5小题)','第三部分 语言运用']:
            lines=['【31题详解】','PROGRAM-ONLY detail',heading,'PROGRAM-ONLY next passage']
            self.assertEqual(explanation_stop(lines,0,31),2)

if __name__=='__main__': unittest.main()
