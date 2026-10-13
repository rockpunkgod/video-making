"""Read archive entries in memory; report provenance without copying exam text."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import yaml


def audit_archive(path):
    path = Path(path)
    findings = []
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Corrupt archive member: {bad}")
        for name in archive.namelist():
            if not name.endswith("case.yaml"):
                continue
            raw = archive.read(name)
            case = yaml.safe_load(raw) or {}
            question = case.get("question")
            if not isinstance(question, str) or not question.strip():
                continue
            findings.append({
                "entry": name,
                "case_status": case.get("status"),
                "question_characters": len(question),
                "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
                "entry_sha256": hashlib.sha256(raw).hexdigest(),
                "recorded_source": case.get("source_reference", case.get("source")),
                "recorded_source_item": case.get("source_item"),
            })
        entries = len(archive.namelist())
    return {
        "archive": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "entry_count": entries,
        "nonempty_case_questions": findings,
        "review_required": bool(findings),
        "scope": "case payload and recorded provenance; not a source-rights certification",
        "history_rewritten": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"archives": [audit_archive(path) for path in args.archives]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archives": len(result["archives"]), "findings": sum(
        len(row["nonempty_case_questions"]) for row in result["archives"])}))


if __name__ == "__main__":
    main()
