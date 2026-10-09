import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfWriter

from scripts.freeze_organized_pdf_pages import digest, run, selected


class OrganizedPdfFreezerTests(unittest.TestCase):
    def test_filename_stage_selection(self):
        def row(name, claim):
            return {"relative_path": name, "extension": ".pdf", "filename_claim": claim}

        self.assertTrue(selected(row("2008试卷（空白卷）.pdf", "questions_only"), "questions"))
        self.assertFalse(selected(row("2008试卷（解析卷）.pdf", "mixed"), "questions"))
        self.assertTrue(selected(row("2026/英语.pdf", "unknown"), "questions"))
        self.assertTrue(selected(row("2008试卷（解析卷）.pdf", "mixed"), "answers"))

    def test_freezes_pages_and_never_opens_answer_in_question_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            question = source / "2008试题.pdf"
            writer.write(question)
            data = question.read_bytes()
            # A deliberately nonexistent answer entry proves stage isolation.
            rows = [
                {"relative_path": question.name, "extension": ".pdf", "bytes": len(data),
                 "sha256": digest(data), "filename_claim": "questions_only"},
                {"relative_path": "2008答案.pdf", "extension": ".pdf", "bytes": 0,
                 "sha256": "f" * 64, "filename_claim": "answers_only"},
            ]
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"source_root": str(source), "files": rows}), encoding="utf-8")
            out = root / "out"
            summary = run(manifest, "questions", out)
            self.assertEqual(summary["selected_file_count"], 1)
            self.assertEqual(summary["page_count"], 1)
            self.assertEqual(summary["zero_text_page_count"], 1)
            self.assertEqual(summary["failed"], [])
            frozen_path = out / "pages" / f"{digest(data)}.json"
            frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
            self.assertEqual(frozen["pages"][0]["text"], "")
            self.assertEqual(frozen["pages"][0]["text_sha256"], digest(b""))
            self.assertTrue(frozen["pages"][0]["requires_ocr"])
            before = frozen_path.read_bytes()
            self.assertEqual(run(manifest, "questions", out), summary)
            self.assertEqual(frozen_path.read_bytes(), before)

    def test_inventory_mismatch_fails_without_freezing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            question = source / "2014试题.pdf"
            question.write_bytes(b"changed")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"source_root": str(source), "files": [{
                "relative_path": question.name, "extension": ".pdf", "bytes": 7,
                "sha256": "a" * 64, "filename_claim": "questions_only",
            }]}), encoding="utf-8")
            out = root / "out"
            summary = run(manifest, "questions", out)
            self.assertEqual(summary["frozen_source_count"], 0)
            self.assertEqual(len(summary["failed"]), 1)
            self.assertFalse((out / "pages" / ("a" * 64 + ".json")).exists())


if __name__ == "__main__":
    unittest.main()
