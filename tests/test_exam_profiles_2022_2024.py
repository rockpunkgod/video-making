"""Program-only extraction fixtures, not exam cases or learner observations."""
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest

from scripts.exam_profiles_2022_2024 import EXAMS, choices, parse, reveal, reviewed_blind
from scripts.ingest_exam_sources import sha, freeze_json


def source_fixture(first=1):
    lines = ['第二部分 阅读', '第一节', 'program-only instruction']
    number = first
    for head, count in zip('ABCD', [3,4,4,4]):
        lines += [head, 'PROGRAM-ONLY paragraph, not a real exam.']
        if head == 'A':
            lines += ['1 hour', 'program price']  # not a question label
        for _ in range(count):
            lines += [str(number)+'. Program question?', 'A. A program article.\tB. beta\tC gamma\tD. delta']
            number += 1
    lines += ['第二节', 'program instruction', ' '.join('___'+str(i)+'___' for i in range(number,number+5))]
    number += 5
    lines += [letter+'. program '+letter for letter in 'ABCDEFG']
    lines += ['第三部分 语言运用','第一节','program instruction',
              ' '.join('___'+str(i)+'___' for i in range(number,number+15))]
    lines += [str(i)+'. A. alpha\tB. beta\tC. gamma\tD. delta' for i in range(number,number+15)]
    number += 15
    lines += ['第二节','program instruction',
              ' '.join('___'+str(i)+'___'+(' ( act )' if i%2 else '') for i in range(number,number+10))]
    number += 10
    lines += ['第三部分 写作','第一节',str(number)+'. 假定你是 program-only requester','注意：','program limits',
              '第二节',str(number+1)+'. 阅读下面材料 program-only prompt', 'PROGRAM-ONLY story.',
              '注意：','program limits','Program starter one.','____________','Program starter two.','____________']
    text = '\n'.join(lines)
    return dict(exam_id=EXAMS[0], source_kind='blank', automatic_numbered_paragraphs=0,
                embedded_image_count=1, paragraphs=lines, text=text,
                text_sha256=sha(text.encode()), source_sha256='a'*64)


class ExamProfileTest(unittest.TestCase):
    def test_six_types_preserve_printed_numbering_in_both_ranges(self):
        for first in (1,21):
            paper, bindings = parse(source_fixture(first))
            self.assertEqual(len(paper['questions']),47)
            self.assertEqual([b['printed_question_number'] for b in bindings.values()],list(range(first,first+47)))
            self.assertEqual(set(q['question_type'] for q in paper['questions']),
                             {'阅读理解','七选五','完形填空','语法填空','应用文','读后续写'})
            self.assertIn('1 hour', paper['questions'][0]['passage'])
            self.assertEqual(paper['questions'][-1]['continuation_starters'],['Program starter one.','Program starter two.'])
            self.assertTrue(all(b['original_layout_review']=='pending_source_review' for b in bindings.values()))

    def test_parsing_is_pure_and_does_not_add_answer_fields(self):
        source = source_fixture(); before = deepcopy(source)
        paper, _ = parse(source)
        self.assertEqual(source,before)
        self.assertFalse(any('answer' in q for q in paper['questions']))

    def test_visible_missing_period_is_not_fabricated_option_text(self):
        result = choices(['A. A program article.\tB. beta\tC gamma\tD. delta'])
        self.assertEqual(result,dict(A='A program article.',B='beta',C='gamma',D='delta'))

    def test_missing_duplicate_or_empty_options_rejected(self):
        for value in ['A. alpha\tB. beta\tD. delta', 'A. alpha\tB. beta\tC. gamma\tD. delta\tD. duplicate',
                      'A. alpha\tB. beta\tC. gamma\tD.']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                choices([value])

    def test_changed_text_or_paragraphs_rejected(self):
        for field in ('text','paragraphs'):
            source = source_fixture()
            if field=='text': source[field]+='tamper'
            else: source[field][0]+='tamper'
            with self.subTest(field=field),self.assertRaises(ValueError): parse(source)

    def test_reveal_and_unreviewed_automatic_numbering_rejected(self):
        for change in [dict(source_kind='reveal'), dict(exam_id='unsupported'), dict(automatic_numbered_paragraphs=1)]:
            with self.subTest(change=change),self.assertRaises(ValueError): parse({**source_fixture(),**change})

    def test_missing_blank_not_filled_from_answer(self):
        source = source_fixture(); source['paragraphs'] = [s.replace('___16___','unmarked') for s in source['paragraphs']]
        source['text']='\n'.join(source['paragraphs']); source['text_sha256']=sha(source['text'].encode())
        with self.assertRaisesRegex(ValueError,'incomplete'): parse(source)

    def test_given_word_whitespace_and_hintless_branches_preserved(self):
        paper,_ = parse(source_fixture())
        grammar=[q for q in paper['questions'] if q['question_type']=='语法填空']
        self.assertEqual(sum('given_word' in q for q in grammar),5)
        self.assertTrue(all(q.get('given_word','act')=='act' for q in grammar))

    def test_reveal_requires_existing_blind_before_source_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError): reveal(Path(tmp),EXAMS[0])
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_host_review_adapter_does_not_transfer_specific_question_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            for exam in EXAMS:
                if exam == 'gaokao-2023-I': continue
                with self.subTest(exam=exam),self.assertRaisesRegex(ValueError,'only supports'):
                    reviewed_blind(tmp, exam, 'missing-review.json')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_writing_prose_numbering_does_not_overwrite_objective_keys(self):
        source = source_fixture(); paper, _ = parse(source)
        lines = ['第二部分 阅读', '【答案】'+ '    '.join(str(i)+'. alpha' for i in range(1,46)), '【解析】']
        for i in range(1,46): lines += ['【'+str(i)+'题详解】','PROGRAM-ONLY explanation.']
        lines += ['第四部分 写作', '【答案】Dear program recipient,', '1. This is prose, not another answer.', '【解析】']
        text = '\n'.join(lines)
        reference = dict(paragraphs=lines, text=text, text_sha256=sha(text.encode()), source_sha256='b'*64)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); exam=EXAMS[0]
            freeze_json(root/'sources'/exam/'blank.json',source)
            freeze_json(root/'sources'/exam/'reveal.json',reference)
            freeze_json(root/'predictions'/exam/'blind.json',dict(pass_='unused', **{'pass':'blind'},
                inputs=paper, predictions=[dict(question_id=q['question_id'],answer=None) for q in paper['questions']],
                question_type_counts={'program-only-count':47}))
            summary=reveal(root,exam)
            self.assertEqual(summary['objective_count'],45)
            self.assertEqual(summary['mechanical_unresolved_count'],45)
            self.assertEqual(summary['host_reviewed_answered_count'],0)
            self.assertNotIn('questions',summary)
            self.assertNotIn('reference_answer',summary)


if __name__=='__main__': unittest.main()
