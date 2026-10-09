import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.link_organized_answer_sources import build_links, parts, run


def row(path, claim="unknown", fingerprint="a"):
    return {"relative_path": path, "filename_claim": claim, "sha256": fingerprint * 64}


class OrganizedAnswerLinksTests(unittest.TestCase):
    def test_terminal_labels_and_spaces_preserve_distinct_titles(self):
        self.assertEqual(parts("甲/北京高三月考 （空白卷）.pdf"), ("甲", "北京高三月考", "空白卷"))
        self.assertEqual(parts("甲/北京高三月考（解析卷）.pdf"), ("甲", "北京高三月考", "解析卷"))
        self.assertEqual(parts("甲/北京高三月考（答案卷）.pdf"), ("甲", "北京高三月考", "答案卷"))
        self.assertEqual(parts("甲/北京（期中）月考（空白卷）.pdf"), ("甲", "北京（期中）月考", "空白卷"))
        self.assertEqual(parts("甲/北京高三月考（空白卷）修订.pdf"), ("甲", "北京高三月考（空白卷）修订", None))
        links = build_links({"files": [
            row("甲/北京高三月考（空白卷）.pdf"),
            row("甲/浙江高三月考（解析卷）.pdf", fingerprint="b"),
        ]})["links"]
        self.assertEqual(links[0]["binding_status"], "unresolved")

    def test_precise_nested_pair_and_multiple_partners(self):
        result = build_links({"files": [
            row(r"2024\北京\高三月考（空白卷）.pdf", "questions_only"),
            row(r"2024\北京\高三月考 （解析卷）.pdf", "mixed", "b"),
            row(r"2024\浙江\高三月考（答案卷）.pdf", "answers_only", "c"),
        ]})
        link = result["links"][0]
        self.assertEqual(link["binding_status"], "precise_filename_pair")
        self.assertEqual(link["partner_candidate"]["sha256"], "b" * 64)
        self.assertEqual(len(link["partner_candidates"]), 2)
        self.assertIsNone(link["reference_answer"])
        ambiguous = build_links({"files": [
            row("甲/2023卷（空白卷）.pdf"),
            row("甲/2023卷（解析卷）.pdf", fingerprint="b"),
            row("甲/2023卷（答案卷）.pdf", fingerprint="c"),
        ]})["links"][0]
        self.assertEqual(ambiguous["binding_status"], "unresolved")
        self.assertIsNone(ambiguous["partner_candidate"])
        self.assertEqual(len(ambiguous["partner_candidates"]), 2)

    def test_cross_directory_is_candidate_and_2026_year_does_not_bind(self):
        result = build_links({"files": [
            row("卷一/2026英语（空白卷）.pdf"),
            row("卷二/2026英语（解析卷）.pdf", "mixed", "b"),
            row("卷一/2026英语网传第二版（答案卷）.pdf", "answers_only", "c"),
        ]})["links"][0]
        self.assertEqual(result["binding_status"], "cross_directory_candidate")
        self.assertIsNone(result["partner_candidate"])
        self.assertEqual([x["sha256"] for x in result["partner_candidates"]], ["b" * 64])

    def test_missing_partner_and_no_answer_body_read(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            manifest = base / "source-manifest.json"
            manifest.write_text(json.dumps({"files": [
                row("exam/2022卷（空白卷）.pdf"),
                row("exam/2022卷（解析卷）.pdf", "mixed", "b"),
                row("exam/2021卷（空白卷）.pdf", "questions_only", "c"),
            ]}), encoding="utf-8")
            original = Path.read_bytes
            with patch.object(Path, "read_bytes", autospec=True) as reader:
                def guarded(path):
                    if path.suffix == ".pdf":
                        raise AssertionError("answer or question PDF body opened")
                    return original(path)
                reader.side_effect = guarded
                result = run(manifest)
            self.assertEqual([x["binding_status"] for x in result["links"]],
                             ["unresolved", "precise_filename_pair"])
            self.assertTrue(all(x["reference_answer"] is None for x in result["links"]))
            output = base / "answer-source-links.json"
            first = output.read_bytes()
            self.assertEqual(run(manifest), result)
            self.assertEqual(output.read_bytes(), first)
            manifest.write_text(json.dumps({"files": [row("new/2020（空白卷）.pdf")]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Frozen artifact differs"):
                run(manifest)


if __name__ == "__main__":
    unittest.main()
