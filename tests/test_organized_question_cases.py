import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_organized_question_cases import build_source, run


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen_for(texts, fingerprint):
    return {"source_sha256": fingerprint, "source_paths": ["2008年高考英语试卷（北京）（空白卷）.pdf"],
            "pages": [{"page_number": i + 1, "text": text,
                       "text_sha256": sha(text.encode()), "requires_ocr": not bool(text.strip()),
                       "image_count": 0} for i, text in enumerate(texts)], "issues": []}


def check_exact_pages_children_options_and_unmatched():
    texts = ["第一部分 听力\n1. What?\nA. One\nB. Two\nC. Three\n",
             "第二部分 阅读理解\nA\nArticle text\n21. Why?\nA. X\nB. Y\nC. Z\nD. W\n"
             "第三部分 语法填空\nThe boy _41_ ran.\n"
             "第四部分 书面表达\n1. 时间 2. 地点\n",
             "第五部分 阅读理解\n14. Passage\n(1) First?\nA. Yes\nB. No\nC. Maybe\nD. Other\n"]
    row = {"sha256": "a" * 64}
    bank = build_source(row, frozen_for(texts, row["sha256"]), "2008-北京-v01")
    assert bank["document_text"] == "\n".join(texts)
    cases = {c["printed_number"]: c for c in bank["cases"]}
    assert "1" in cases
    assert cases["1"]["issues"] == ["missing_audio"]
    assert [o["label"] for o in cases["21"]["options"]] == list("ABCD")
    assert cases["21"]["context_binding"] == "needs_context_binding"
    assert cases["41"]["source"]["quote"] == "_41_"
    assert "2" not in cases
    assert "14(1)" in cases
    assert bank["sections"][-1]["parent_tasks"][0]["printed_number"] == "14"
    for case in bank["cases"]:
        ref = case["source"]
        assert bank["document_text"][ref["start"]:ref["end"]] == ref["quote"]
        assert case["method_id"] is None and case["answer"] is None
        assert case["formal_method_case"] is False


def check_runner_freezes_and_refuses_changed_output(tmp_path):
    source_root = tmp_path / "input"
    source_root.mkdir()
    name = "2008年高考英语试卷（北京）（空白卷）.pdf"
    raw = b"synthetic pdf sentinel"
    (source_root / name).write_bytes(raw)
    fingerprint = sha(raw)
    manifest_dir = tmp_path / "frozen"
    (manifest_dir / "pages").mkdir(parents=True)
    frozen = frozen_for(["第一部分 听力\n1. Hi?\nA. a\nB. b\nC. c\n"], fingerprint)
    (manifest_dir / "pages" / f"{fingerprint}.json").write_text(json.dumps(frozen), encoding="utf-8")
    manifest = {"source_root": str(source_root), "files": [{"relative_path": name,
                 "extension": ".pdf", "filename_claim": "questions_only", "sha256": fingerprint,
                 "bytes": len(raw), "claimed_year": "2008", "claimed_volume": "北京"}]}
    manifest_path = manifest_dir / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "case-bank-v1"
    summary = run(manifest_path, output)
    assert summary["source_files"] == 1
    assert summary["leaf_question_cases"] == 1
    assert run(manifest_path, output) == summary
    assert (output / "source-bank.json").exists()


def check_fullwidth_and_spaced_blanks_and_bare_cloze_row():
    text = ("第一部分 七选五\n阅读下面短文，选项中有两项为多余选项。\nText  36   Next ＿37＿ More\n"
            "A. A\nB. B\nC. C\nD. D\nE. E\nF. F\nG Keep this raw delimiter\n"
            "第二部分 完形填空\nText _41_\n41 A. one B. two C. three D. four\n"
            "第三部分 语法填空\n在空白处填入1个适当的单词。\nIt is　 61 　（be） fine.\n")
    row = {"sha256": "b" * 64}
    bank = build_source(row, frozen_for([text], row["sha256"]), "synthetic-v01")
    cases = {(c["question_type"], c["printed_number"]): c for c in bank["cases"]}
    assert ("seven_five", "36") in cases and ("seven_five", "37") in cases
    assert [o["printed_delimiter"] for o in cases[("seven_five", "36")]["options"]][-1] == " "
    assert ("cloze", "41") in cases
    assert ("grammar_fill", "61") in cases


def check_real_known_paper_counts():
    root = Path(__file__).resolve().parents[1] / "local-data/organized-pdfs"
    if not (root / "source-manifest.json").exists():
        raise unittest.SkipTest('Private user-supplied PDFs are not part of the public repository')
    manifest = json.loads((root / "source-manifest.json").read_text(encoding="utf-8"))
    checks = [
        ("e0e9e3e9e77db75012dad085a537446a09c4d1d3c295189313c5966c34247641",
         {"seven_five": 5, "cloze": 15, "grammar_fill": 10,
          "application_writing": 1, "continuation_writing": 1}),
        ("9aa77c99ed3828b7e16d0b0ab74b6be9b64ba11c939ffe8421a4c475c5b881bf",
         {"seven_five": 5, "cloze": 20, "grammar_fill": 10}),
    ]
    for fingerprint, expected in checks:
        row = next(r for r in manifest["files"] if r["sha256"] == fingerprint)
        frozen = json.loads((root / "pages" / f"{fingerprint}.json").read_text(encoding="utf-8"))
        bank = build_source(row, frozen, "known-paper-v01")
        for kind, count in expected.items():
            assert sum(c["question_type"] == kind for c in bank["cases"]) == count
    fingerprint = next(r["sha256"] for r in manifest["files"] if "2008年高考英语试卷（全国Ⅰ卷）（空白卷）" in r["relative_path"])
    row = next(r for r in manifest["files"] if r["sha256"] == fingerprint)
    frozen = json.loads((root / "pages" / f"{fingerprint}.json").read_text(encoding="utf-8"))
    bank = build_source(row, frozen, "known-national-i-v01")
    assert [c["printed_number"] for c in bank["cases"] if c["question_type"] == "cloze"] == [str(n) for n in range(36, 56)]


class OrganizedQuestionCaseTests(unittest.TestCase):
    def test_exact_pages_children_options_and_unmatched(self):
        check_exact_pages_children_options_and_unmatched()

    def test_runner_freezes_and_refuses_changed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            check_runner_freezes_and_refuses_changed_output(Path(tmp))

    def test_fullwidth_and_spaced_blanks_and_bare_cloze_row(self):
        check_fullwidth_and_spaced_blanks_and_bare_cloze_row()

    def test_real_known_paper_counts(self):
        check_real_known_paper_counts()

if __name__=='__main__': unittest.main()
