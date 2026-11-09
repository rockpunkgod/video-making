"""Archive/verify/restore the existing question corpus without changing its evidence."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "question-bank"
SOURCE = "59190489abd3e0fb6543c9a04e137881ae98cd88"
ROOT_NAMES = (
    "exams-2020-2025", "organized-pdfs", "restored-organized-20261024-r1",
    "intake-20261024-baidu-r1", "priority-zips-20261026-r1",
    "all-uploaded-next-20261026-r1", "all-uploaded-coverage-20261026-r1",
    "all-uploaded-coverage-20261026-r2", "all-uploaded-priority-zip-map-20261026-r1",
    "all-uploaded-continuation-queue-20261026-r3",
    "contested-questions-high-resolution-20261026-r1",
    "current-entry-reconciliation-20261026-r6", "current-entry-reconciliation-20261026-r7",
    "current-entry-reconciliation-20261026-r8", "current-entry-reconciliation-20261026-r9",
    "current-entry-reconciliation-20261026-r10",
    "question-alignment-70db6d6-20261030", "answer-alignment-20261030-latest",
    "answer-alignment-20261106",
)
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "tmp", "node_modules"}
SECRET = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{40,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def source_files():
    roots = [ROOT / "local-data" / n for n in ROOT_NAMES]
    roots += sorted((ROOT / "local-data").glob("当前可用案例讲解_*"))
    roots += [ROOT / "local-data/CURRENT_TEACHING_AND_QUESTION_ALIGNMENT.json"]
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*") if root.is_dir() else [root]):
            if not p.is_file():
                continue
            parts = p.relative_to(ROOT).parts
            if any(x in SKIP_DIRS or x.startswith(("ANSWER-", "activation-backup-")) for x in parts):
                continue
            yield p


def build():
    if (BANK / "manifest.json").exists():
        verify()
    entries, objects = [], {}
    for p in source_files():
        data = p.read_bytes()
        if SECRET.search(data):
            raise SystemExit(f"Credential-like content requires review: {p.relative_to(ROOT)}")
        digest = sha(data)
        if digest not in objects:
            name = f"objects/{digest[:2]}/{digest}.gz"
            out = BANK / name
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists():
                if sha(gzip.decompress(out.read_bytes())) != digest:
                    raise ValueError(f"Existing corrupt object: {digest}")
            else:
                out.write_bytes(gzip.compress(data, compresslevel=6, mtime=0))
            objects[digest] = {"path": name, "size": len(data), "stored_size": out.stat().st_size}
        entries.append({"path": p.relative_to(ROOT).as_posix(), "sha256": digest})
    if not entries:
        raise SystemExit("No corpus found")
    json_write(BANK / "manifest.json", {
        "format": "question-bank-content-addressed-v1", "source_commit": SOURCE,
        "snapshot_date": "2026-11-09", "all_uploaded_complete": False,
        "scope": "Existing exam sources, transcriptions, cases, reviews and regressions; historical status retained. No new Case/Blind/learner approval.",
        "active_export": "local-data/当前可用案例讲解_20261106_5919048_r1",
        "active_replay": "local-data/answer-alignment-20261106/question-replay-r3",
        "included_roots": list(ROOT_NAMES),
        "exclusions": ["paid course materials", "browser/login data", "ANSWER checkouts", "activation backups", "temporary/cache files", "unrelated video/creative work"],
        "files": entries, "objects": objects,
        "logical_file_count": len(entries), "unique_file_count": len(objects),
        "logical_bytes": sum(objects[e["sha256"]]["size"] for e in entries),
        "stored_bytes": sum(o["stored_size"] for o in objects.values()),
    })
    verify()


def load():
    value = json.loads((BANK / "manifest.json").read_text(encoding="utf-8"))
    paths = set()
    for e in value["files"]:
        p = Path(e["path"])
        if p.is_absolute() or ".." in p.parts or not e["path"].startswith("local-data/") or e["path"] in paths:
            raise ValueError("Unsafe or duplicate restore path")
        paths.add(e["path"])
        if e["sha256"] not in value["objects"]:
            raise ValueError("Missing object reference")
    for digest, obj in value["objects"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or obj["path"] != f"objects/{digest[:2]}/{digest}.gz":
            raise ValueError("Unsafe object path")
    return value


def verify():
    value = load()
    for digest, obj in value["objects"].items():
        data = gzip.decompress((BANK / obj["path"]).read_bytes())
        if sha(data) != digest or len(data) != obj["size"]:
            raise ValueError(f"Corrupt object: {digest}")
    if len(value["files"]) != value["logical_file_count"] or len(value["objects"]) != value["unique_file_count"]:
        raise ValueError("Count mismatch")
    print(json.dumps({"status": "PASS", "files": len(value["files"]), "unique_objects": len(value["objects"]), "stored_bytes": value["stored_bytes"]}))


def restore(destination: Path, prefix: str):
    value = load()
    target = destination.resolve()
    selected = [e for e in value["files"] if e["path"].startswith(prefix)]
    if not selected:
        raise SystemExit("No matching paths")
    # Preflight every existing destination before writing anything; never overwrite.
    for e in selected:
        out = target / e["path"]
        if not out.resolve().is_relative_to(target):
            raise ValueError("Restore path escapes destination")
        if out.exists() and (not out.is_file() or sha(out.read_bytes()) != e["sha256"]):
            raise SystemExit(f"Existing different file; use an empty destination: {out}")
    for e in selected:
        out = target / e["path"]
        if out.exists():
            continue
        data = gzip.decompress((BANK / value["objects"][e["sha256"]]["path"]).read_bytes())
        if sha(data) != e["sha256"]:
            raise ValueError("Corrupt object")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print(json.dumps({"status": "RESTORED", "files": len(selected), "destination": str(target)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["build", "verify", "restore"])
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--prefix", default="local-data/")
    args = parser.parse_args()
    if args.operation == "restore":
        if not args.destination:
            parser.error("restore requires --destination")
        restore(args.destination, args.prefix)
    elif args.operation == "build":
        build()
    else:
        verify()
