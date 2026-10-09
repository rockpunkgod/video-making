"""Link organized question and answer *filenames* without reading answer files.

The inventory's titles and paths are claims, not authentication of a paper or
answer key. This stage never opens a source document or extracts an answer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "local-data/organized-pdfs/source-manifest.json"
TRAILING_ROLE = re.compile(r"\s*[（(]\s*(空白卷|解析卷|答案卷)\s*[）)]\s*$")
ANSWER_WORD = re.compile(r"答案|解析|参考答案|答题卡|answer|solution", re.I)


def parts(relative_path: str) -> tuple[str, str, str | None]:
    """Return directory, exact base title, and a terminal role label."""
    path = Path(relative_path.replace("\\", "/"))
    title = path.stem
    match = TRAILING_ROLE.search(title)
    base = title[:match.start()].rstrip() if match else title.rstrip()
    return path.parent.as_posix(), base, match.group(1) if match else None


def role(row: dict) -> str:
    _, title, suffix = parts(row["relative_path"])
    if suffix in {"解析卷", "答案卷"}:
        return "answer"
    if suffix == "空白卷":
        return "question"
    if ANSWER_WORD.search(title) or row.get("filename_claim") in {"answers_only", "mixed"}:
        return "answer"
    if row.get("filename_claim") in {"questions_only", "unknown"}:
        return "question"
    return "unclassified"


def source_ref(row: dict) -> dict:
    return {"relative_path": row["relative_path"], "sha256": row["sha256"].lower()}


def build_links(manifest: dict) -> dict:
    rows = manifest["files"]
    paths = [row["relative_path"].replace("\\", "/") for row in rows]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate relative_path in source manifest")
    answers = [(row, *parts(row["relative_path"])) for row in rows if role(row) == "answer"]
    links = []
    for question in rows:
        if role(question) != "question":
            continue
        directory, base, _ = parts(question["relative_path"])
        same_directory = []
        cross_directory = []
        for answer, answer_directory, answer_base, _ in answers:
            if base != answer_base:
                continue
            partner = source_ref(answer)
            if answer_directory == directory:
                same_directory.append(partner)
            else:
                cross_directory.append(partner)
        same_directory.sort(key=lambda item: item["relative_path"])
        cross_directory.sort(key=lambda item: item["relative_path"])
        if len(same_directory) == 1:
            status = "precise_filename_pair"
            partner = same_directory[0]
        elif not same_directory and cross_directory:
            status = "cross_directory_candidate"
            partner = None
        else:
            status = "unresolved"
            partner = None
        links.append({
            "question": source_ref(question),
            "title_claim": {"normalized_filename_stem": base, "source_authenticity": "unverified"},
            "partner_candidate": partner,
            "partner_candidates": same_directory + cross_directory,
            "binding_status": status,
            "answer_authority": "unverified",
            "reference_answer": None,
        })
    links.sort(key=lambda item: item["question"]["relative_path"])
    return {
        "schema_version": 1,
        "scope_note": "Filename and inventory metadata only; source bodies and answers not read.",
        "question_candidate_count": len(links),
        "links": links,
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


def run(manifest_path: Path = DEFAULT_MANIFEST, output_path: Path | None = None) -> dict:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    result = build_links(manifest)
    output_path = Path(output_path) if output_path else manifest_path.parent / "answer-source-links.json"
    freeze_json(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.manifest, args.output)
    print(json.dumps({"question_candidate_count": result["question_candidate_count"],
                      "binding_counts": {status: sum(x["binding_status"] == status for x in result["links"])
                                         for status in ("precise_filename_pair", "cross_directory_candidate", "unresolved")}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
