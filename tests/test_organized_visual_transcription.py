"""Synthetic visual-source checks for the private transcription replay."""
import base64
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.ingest_exam_sources import freeze_json, sha
from scripts.run_organized_paper_regression import (
    run_transcription_batch,
    validate_transcription,
)


PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlqWQAAAABJRU5ErkJggg=='
)
PDF_SHA = sha(b'PDF')


def source_span(content, quote, start=0):
    at = content.index(quote, start)
    return {'start': at, 'end': at + len(quote), 'quote': quote}


def transcription(content, question, fields, exclusions=None):
    return {
        'phase': 'low_model_source_transcription_no_answers',
        'paper_id': 'test-paper', 'source_sha256': PDF_SHA,
        'reviewer_agent': '/root/synthetic_transcriber', 'reference_read': False,
        'inputs': {'paper_id': 'test-paper', 'questions': [question]},
        'source_bindings': [{
            'question_id': question['question_id'], 'fields': fields,
            'display_exclusions': exclusions or [],
        }],
    }, {'paper_id': 'test-paper', 'source_sha256': PDF_SHA, 'document_text': content}


class VisualTranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.render = self.root / 'renders' / 'page-1.png'
        self.render.parent.mkdir(parents=True)
        self.render.write_bytes(PNG)

    def visual(self, number=1, path=None):
        return {
            'page_number': number,
            'rendered_path': (path or self.render).relative_to(self.root).as_posix(),
            'rendered_sha256': sha(PNG),
        }

    def grammar(self):
        content = 'The 56 arrived.'
        q = {'question_id': 'test-Q56', 'question_type': 'grammar_fill',
             'stem': '56', 'passage': content}
        value, dossier = transcription(content, q, {
            '/stem': [source_span(content, '56')],
            '/passage': [source_span(content, content)],
        })
        return value, dossier

    def test_space_delimited_grammar_digit_requires_source_bound_private_png(self):
        value, dossier = self.grammar()
        with self.assertRaisesRegex(ValueError, 'blank confirmation'):
            validate_transcription(value, dossier, self.root)
        value['source_bindings'][0]['blank_marker_visual_check'] = {
            **self.visual(), 'confirmed': True, 'printed_number': 56,
            'source_sha256': PDF_SHA,
        }
        result = validate_transcription(value, dossier, self.root)
        self.assertEqual(result['questions'][0]['question_type'], '语法填空')
        self.assertEqual(result['questions'][0]['stem'], '56')

    def test_grammar_visual_binding_rejects_wrong_render_source_or_escaped_path(self):
        value, dossier = self.grammar()
        visual = {**self.visual(), 'confirmed': True, 'printed_number': 56,
                  'source_sha256': PDF_SHA}
        for changed, expected in [
            ({'rendered_sha256': '0' * 64}, 'fingerprint'),
            ({'source_sha256': '0' * 64}, 'blank confirmation'),
            ({'printed_number': 57}, 'blank confirmation'),
        ]:
            with self.subTest(changed=changed):
                variant = deepcopy(value)
                variant['source_bindings'][0]['blank_marker_visual_check'] = {**visual, **changed}
                with self.assertRaisesRegex(ValueError, expected):
                    validate_transcription(variant, dossier, self.root)
        outside = self.root.parent / ('outside-' + self.root.name + '.png')
        outside.write_bytes(PNG)
        self.addCleanup(outside.unlink)
        value['source_bindings'][0]['blank_marker_visual_check'] = {
            **visual, 'rendered_path': str(outside),
        }
        with self.assertRaisesRegex(ValueError, 'outside private dataset'):
            validate_transcription(value, dossier, self.root)

    def test_bare_page_number_needs_visual_reference_and_correct_number(self):
        content = 'Question? A 3 B'
        q = {'question_id': 'test-Q1', 'question_type': 'unknown',
             'stem': 'Question?', 'passage': 'A B'}
        digit = source_span(content, '3 ')
        digit.update(kind='printed_pagination', printed_page_number=3)
        value, dossier = transcription(content, q, {
            '/stem': [source_span(content, 'Question?')],
            '/passage': [source_span(content, 'A '), source_span(content, 'B')],
        }, [digit])
        with self.assertRaisesRegex(ValueError, 'visual confirmation|actual page number'):
            validate_transcription(value, dossier, self.root)
        for bad_number in (2, 4):
            variant = deepcopy(value)
            variant['source_bindings'][0]['display_exclusions'][0].update(self.visual(bad_number))
            with self.subTest(number=bad_number), self.assertRaisesRegex(ValueError, 'pagination'):
                validate_transcription(variant, dossier, self.root)
            variant['source_bindings'][0]['display_exclusions'][0]['confirmed'] = True
            # A physical PDF page can differ from its printed page number.
            self.assertEqual(validate_transcription(variant, dossier, self.root)['questions'][0]['passage'], 'A B')
        value['source_bindings'][0]['display_exclusions'][0].update(self.visual(3))
        self.assertEqual(validate_transcription(value, dossier, self.root)['questions'][0]['passage'], 'A B')

    def test_ordinary_english_article_cannot_be_removed_as_page_number(self):
        content = 'Question? A ordinary B'
        q = {'question_id': 'test-Q1', 'question_type': 'unknown',
             'stem': 'Question?', 'passage': 'A B'}
        removal = source_span(content, 'ordinary ')
        removal.update(self.visual(3), kind='printed_pagination', printed_page_number=3)
        value, dossier = transcription(content, q, {
            '/stem': [source_span(content, 'Question?')],
            '/passage': [source_span(content, 'A '), source_span(content, 'B')],
        }, [removal])
        with self.assertRaisesRegex(ValueError, 'pagination'):
            validate_transcription(value, dossier, self.root)

    def test_parenthesized_printed_footer_can_be_removed_exactly(self):
        content = 'Question? A 第3页（共12页） B'
        q = {'question_id': 'test-Q1', 'question_type': 'unknown',
             'stem': 'Question?', 'passage': 'A B'}
        value, dossier = transcription(content, q, {
            '/stem': [source_span(content, 'Question?')],
            '/passage': [source_span(content, 'A '), source_span(content, 'B')],
        }, [source_span(content, '第3页（共12页） ')])
        self.assertEqual(validate_transcription(value, dossier, self.root)['questions'][0]['passage'], 'A B')

    def sidecar_batch(self):
        bank = self.root / 'case-bank-v4'
        original = {'paper_id': 'test-paper', 'source_sha256': PDF_SHA,
                    'document_text': 'Original text layer.'}
        original_path = bank / 'papers' / 'test-paper.json'
        freeze_json(original_path, original)
        pages = [
            {**self.visual(1), 'text': 'Which?'},
            {**self.visual(2), 'text': 'Alpha.'},
        ]
        content = '\n'.join(p['text'] for p in pages)
        q = {'question_id': 'test-Q1', 'question_type': 'unknown',
             'stem': 'Which?', 'passage': 'Alpha.'}
        value, _ = transcription(content, q, {
            '/stem': [source_span(content, 'Which?')],
            '/passage': [source_span(content, 'Alpha.')],
        })
        sidecar = {'origin': 'visual_transcription_sidecar',
                   'paper_id': 'test-paper', 'source_sha256': PDF_SHA,
                   'original_dossier_ref': {
                       'path': original_path.relative_to(self.root).as_posix(),
                       'sha256': sha(original_path.read_bytes()),
                   }, 'pages': pages, 'document_text': content}
        pdf = self.root / 'originals' / 'files' / (PDF_SHA + '.pdf')
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b'PDF')
        return bank, value, sidecar, pdf

    def run_sidecar(self, bank, value, sidecar):
        sidecar_path = self.root / 'visual-source.json'
        freeze_json(sidecar_path, sidecar)
        value['source_document_ref'] = {
            'path': sidecar_path.relative_to(self.root).as_posix(),
            'sha256': sha(sidecar_path.read_bytes()),
        }
        value['source_document_sha256'] = sha(sidecar_path.read_bytes())
        value_path = self.root / 'transcription.json'
        freeze_json(value_path, value)
        return run_transcription_batch([value_path], self.root / 'replay', bank)

    def test_valid_sidecar_replays_actual_engine_without_blind_claim(self):
        bank, value, sidecar, _ = self.sidecar_batch()
        value['source_answer_exposure'] = {
            'present': True, 'description': 'Synthetic answer printed in source box',
        }
        summary = self.run_sidecar(bank, value, sidecar)
        self.assertEqual(summary['papers'][0]['input_count'], 1)
        self.assertEqual(summary['papers'][0]['engine_answer_count'], 0)
        self.assertEqual(summary['new_blind_samples'], 0)
        report = json.loads((self.root / summary['papers'][0]['report']).read_text(encoding='utf-8'))
        self.assertFalse(report['visual_fidelity_certified'])
        self.assertEqual(report['source_document_ref'], value['source_document_ref'])
        self.assertEqual(report['source_answer_exposure'], value['source_answer_exposure'])
        self.assertFalse(report['limits']['clean_blind_certified'])

    def test_sidecar_rejects_origin_dossier_binding_page_order_and_join(self):
        for name in ('origin', 'dossier_sha', 'page_order', 'page_join', 'pdf_identity'):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                # Each mutation gets its own private dataset and no replay outputs.
                previous_root, previous_render = self.root, self.render
                self.root = Path(temporary)
                self.render = self.root / 'renders' / 'page-1.png'
                self.render.parent.mkdir(parents=True)
                self.render.write_bytes(PNG)
                try:
                    bank, value, sidecar, _ = self.sidecar_batch()
                    if name == 'origin':
                        sidecar['origin'] = 'unknown'
                    elif name == 'dossier_sha':
                        sidecar['original_dossier_ref']['sha256'] = '0' * 64
                    elif name == 'page_order':
                        sidecar['pages'].reverse()
                    elif name == 'page_join':
                        sidecar['document_text'] += ' changed'
                    elif name == 'pdf_identity':
                        sidecar['source_sha256'] = '0' * 64
                    with patch('scripts.run_organized_paper_regression.QuestionAnalyzer') as analyzer:
                        with self.assertRaises(ValueError):
                            self.run_sidecar(bank, value, sidecar)
                        analyzer.assert_not_called()
                    self.assertFalse((self.root / 'replay').exists())
                finally:
                    self.root, self.render = previous_root, previous_render

    def test_sidecar_rejects_changed_original_pdf_bytes(self):
        bank, value, sidecar, pdf = self.sidecar_batch()
        pdf.write_bytes(b'OTHER')
        with patch('scripts.run_organized_paper_regression.QuestionAnalyzer') as analyzer:
            with self.assertRaisesRegex(ValueError, 'source fingerprint'):
                self.run_sidecar(bank, value, sidecar)
            analyzer.assert_not_called()
        self.assertFalse((self.root / 'replay').exists())

    def test_prefilled_answer_cannot_be_transcribed_as_a_blind_question(self):
        value, dossier = self.grammar()
        value['inputs']['questions'][0]['answer'] = 'arrived'
        with self.assertRaisesRegex(ValueError, 'cannot contain answers'):
            validate_transcription(value, dossier, self.root)
        value, dossier = self.grammar()
        value['inputs']['questions'][0]['student_draft'] = 'arrived'
        with self.assertRaisesRegex(ValueError, 'cannot contain answers'):
            validate_transcription(value, dossier, self.root)
        # student_text is the actual Engine material field, not student_draft.
        value, dossier = self.grammar()
        value['inputs']['questions'][0]['student_text'] = 'arrived'
        value['source_bindings'][0]['fields']['/student_text'] = [source_span(dossier['document_text'], 'arrived')]
        with self.assertRaisesRegex(ValueError, 'cannot contain answers'):
            validate_transcription(value, dossier, self.root)


if __name__ == '__main__':
    unittest.main()
