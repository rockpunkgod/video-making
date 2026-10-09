"""Freeze the unmodified text layer of locally supplied exam PDFs, one page at a time.

This is a local research extraction, not OCR, a completeness check, or an
authentication of any paper or answer key. Run questions before answers.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "local-data/organized-pdfs/source-manifest.json"
VERSION = 1
ANSWER_NAME = re.compile(r"答案|解析|参考答案|答题卡|answer|solution", re.I)
QUESTION_NAME = re.compile(r"空白卷|试题|真题|试卷", re.I)
CONTENT_RISK = re.compile(r"答案|解析|参考答案|答案解析|answer\s*key|solutions?", re.I)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def selected(row: dict, kind: str) -> bool:
    if row.get("extension", "").lower() != ".pdf":
        return False
    name = Path(row["relative_path"].replace("\\", "/")).stem
    answer = bool(ANSWER_NAME.search(name))
    question = bool(QUESTION_NAME.search(name))
    # The two short-named 2026 papers in this collection are unclassified in
    # the inventory. Treat unknown PDFs as candidates, never as verified papers.
    questions = not answer and (question or row.get("filename_claim") == "unknown")
    answers = answer
    return (questions if kind == "questions" else answers if kind == "answers"
            else questions or answers)


def source_path(source_root: Path, relative: str) -> Path:
    path = (source_root / Path(relative.replace("\\", "/"))).resolve()
    if not path.is_relative_to(source_root) or not path.is_file():
        raise ValueError(f"Missing or unsafe source path: {relative}")
    return path


def image_count(page) -> int:
    """Count image XObjects, including those inside Form XObjects.

    Inline images and drawings are not covered, so zero does not certify that
    a page's appearance is fully represented by extracted text.
    """
    seen = set()

    def walk(resources) -> int:
        resources = resources.get_object() if resources is not None else {}
        xobjects = resources.get("/XObject", {})
        xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
        count = 0
        for ref in xobjects.values():
            key = getattr(ref, "idnum", id(ref))
            if key in seen:
                continue
            seen.add(key)
            obj = ref.get_object()
            subtype = obj.get("/Subtype")
            if subtype == "/Image":
                count += 1
            elif subtype == "/Form":
                count += walk(obj.get("/Resources"))
        return count

    return walk(page.get("/Resources"))


def extract_pdf(data: bytes, fingerprint: str, relative_paths: list[str]) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data), strict=False)
    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    pages = []
    issues = []
    for number, page in enumerate(reader.pages, 1):
        raw = page.extract_text()
        text = raw if raw is not None else ""
        count = image_count(page)
        page_row = {
            "page_number": number,
            "text": text,
            "text_sha256": digest(text.encode("utf-8")),
            "text_character_count": len(text),
            "image_count": count,
            "requires_ocr": not bool(text.strip()),
        }
        pages.append(page_row)
        if page_row["requires_ocr"]:
            issues.append({"type": "requires_ocr", "page_number": number,
                           "note": "No usable text layer; visual content is unverified."})
        for match in CONTENT_RISK.finditer(text):
            context = text[max(0, match.start() - 200):match.start()]
            example = bool(re.search(r"例题|例如|例[:：]|听力.{0,30}例", context))
            issue_type = "possible_listening_example_answer" if example else "suspected_answer_annotation"
            if not any(item["type"] == issue_type and item["page_number"] == number
                       for item in issues):
                issues.append({"type": issue_type, "page_number": number,
                               "note": "Marker in text; context may be an exam example. Manual review needed."})
        if count:
            issues.append({"type": "image_content_untranscribed", "page_number": number,
                           "note": "Image resources are not represented in the text layer."})
    return {
        "version": VERSION,
        "source_sha256": fingerprint,
        "source_paths": sorted(relative_paths),
        "extractor": "pypdf text layer only; no OCR or normalization",
        "metadata": metadata,
        "pages": pages,
        "issues": issues,
    }


def freeze_json(path: Path, value: dict) -> None:
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Frozen artifact differs: {path}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def run(manifest_path: Path = DEFAULT_MANIFEST, kind: str = "questions",
        output_root: Path | None = None) -> dict:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    source_root = Path(manifest["source_root"]).resolve()
    output_root = (Path(output_root) if output_root else manifest_path.parent).resolve()
    if output_root == source_root or output_root.is_relative_to(source_root):
        raise ValueError("Output must be outside the source directory")
    grouped = defaultdict(list)
    for row in manifest["files"]:
        if selected(row, kind):
            grouped[row["sha256"].lower()].append(row)
    failed = []
    frozen = []
    for fingerprint, rows in sorted(grouped.items()):
        paths = sorted(row["relative_path"] for row in rows)
        try:
            data = None
            for row in rows:
                path = source_path(source_root, row["relative_path"])
                current = path.read_bytes()
                if digest(current) != fingerprint or len(current) != int(row["bytes"]):
                    raise ValueError(f"Source inventory mismatch before extraction: {row['relative_path']}")
                if data is None:
                    data = current
            assert data is not None
            result = extract_pdf(data, fingerprint, paths)
            for row in rows:
                path = source_path(source_root, row["relative_path"])
                if digest(path.read_bytes()) != fingerprint:
                    raise ValueError(f"Source changed during extraction: {row['relative_path']}")
            freeze_json(output_root / "pages" / f"{fingerprint}.json", result)
            frozen.append(result)
        except Exception as exc:
            failed.append({"source_sha256": fingerprint, "source_paths": paths,
                           "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "version": VERSION,
        "kind": kind,
        "selected_file_count": sum(map(len, grouped.values())),
        "unique_source_count": len(grouped),
        "frozen_source_count": len(frozen),
        "page_count": sum(len(item["pages"]) for item in frozen),
        "zero_text_page_count": sum(page["requires_ocr"] for item in frozen for page in item["pages"]),
        "failed": failed,
    }
    summary_path = output_root / f"extraction-summary.{kind}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--kind", choices=("questions", "answers", "all"), default="questions")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.kind, args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
