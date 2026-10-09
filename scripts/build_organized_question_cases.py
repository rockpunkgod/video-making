"""Build a source-faithful, private question case bank from frozen question PDFs.

This is structural parsing only. It does not inspect answer PDFs, authenticate a
paper, infer an answer, or attach a teaching method. All offsets address the
unmodified ``'\n'.join(page['text'] for page in pages)`` document text.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts.ingest_exam_sources import freeze, freeze_json
from scripts.freeze_organized_pdf_pages import selected
from scripts.organized_paper_queue import paper_label


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "local-data/organized-pdfs/source-manifest.json"
DEFAULT_OUTPUT = ROOT / "local-data/organized-pdfs/case-bank-v4"
NUMBER = re.compile(r"(?m)^\s*(\d{1,3})[.．、)）]\s*")
CLOZE_BARE_NUMBER = re.compile(r"(?m)^\s*(\d{1,3})[ \t]+(?=A[.．、)）])")
CHILD = re.compile(r"(?m)^\s*[（(](\d{1,2})[）)]\s*(?=\S)")
OPTION = re.compile(r"(?m)^[ \t]*([A-K])([.．、)）]|[ \t]+)(?=\S)")
INLINE_OPTION = re.compile(r"(?<![A-Za-z])([A-K])([.．、)）])(?=\s*\S)")
BLANK = re.compile(r"(?<!\d)[_＿]\s*(\d{1,3})\s*[_＿]|(?<!\d)(\d{1,3})\s*[_＿]{2,}|[（(](\d{1,2})[）)]\s*[_＿]{2,}")
SPACED_BLANK = re.compile(r"[ \t\u3000]+(\d{1,3})[ \t\u3000]+")
PAGE_HEADER = re.compile(r"(?m)^第\d+页\s*\|\s*共\d+页[^\r\n]*(?:\r?\n)?")
PART = re.compile(r"^\s*第[一二三四五六七八九十\d]+部分|^\s*第[一二三四五六七八九十\d]+节|^\s*Part\s+[IVX\d]+\b", re.I)
EN_HEADING = re.compile(r"^\s*(Directions|Grammar|Reading(?:\s+Comprehension)?|Writing|Translation|Vocabulary|Listening)(?:\s*[:：]|\s*$)", re.I)
TYPE_TERMS = [
    ("continuation_writing", r"读后续写|续写"),
    ("application_writing", r"应用文|书面表达|写作|Writing"),
    ("summary_writing", r"概要写作|概要"),
    ("error_correction", r"短文改错|改错"),
    ("seven_five", r"七选五|七选[五5]|选出.{0,8}填入空白|补全短文"),
    ("cloze", r"完形填空|完形"),
    ("grammar_fill", r"语法填空|语法填词|Grammar"),
    ("vocabulary", r"词汇|Vocabulary"),
    ("reading", r"阅读理解|阅读表达|任务型阅读|任务阅读|阅读|Reading"),
    ("translation", r"翻译|Translation"),
    ("listening", r"听力|Listening"),
    ("single_choice", r"单项填空|单项选择|单选"),
]
MC_TYPES = {"listening", "single_choice", "cloze", "reading", "seven_five", "vocabulary"}
WRITING_TYPES = {"application_writing", "continuation_writing", "summary_writing", "translation", "error_correction"}


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def lines(text: str):
    offset = 0
    for line in text.splitlines(keepends=True):
        yield offset, line
        offset += len(line)


def page_index(pages: list[dict]):
    out = []
    cursor = 0
    for i, page in enumerate(pages):
        start, end = cursor, cursor + len(page["text"])
        out.append({"page_number": page["page_number"], "start": start, "end": end,
                    "text_sha256": page["text_sha256"], "requires_ocr": page["requires_ocr"],
                    "image_count": page["image_count"]})
        cursor = end + (i < len(pages) - 1)
    return out


def source_ref(text: str, start: int, end: int, page_map: list[dict]) -> dict:
    if not 0 <= start <= end <= len(text):
        raise ValueError("Invalid source span")
    nums = [p["page_number"] for p in page_map if start < p["end"] and end > p["start"]]
    return {"start": start, "end": end, "quote": text[start:end], "page_numbers": nums}


def project_layout(ref: dict) -> dict:
    raw = ref["quote"]
    excluded = [{"start": ref["start"] + m.start(), "end": ref["start"] + m.end(),
                 "quote": m.group()} for m in PAGE_HEADER.finditer(raw)]
    display = PAGE_HEADER.sub("", raw)
    return {"text": display, "source_start": ref["start"], "source_end": ref["end"],
            "excluded_layout_spans": excluded,
            "projection_rule": "remove only printed page-header lines; preserve every other character"}


def identify_type(heading: str, inherited: str = "unknown") -> str:
    if re.match(r"\s*Directions\s*[:：]", heading, re.I):
        if re.search(r"\b(?:hear|listen|recording|conversation|talk)\b", heading, re.I):
            return "listening"
        if re.search(r"\b(?:read.{0,35}passage|reading|comprehension)\b", heading, re.I):
            return "reading"
        if re.search(r"\b(?:each blank|blanks).{0,60}\b(?:choice|choices|options)\b", heading, re.I):
            return "cloze"
    for kind, pattern in TYPE_TERMS:
        if re.search(pattern, heading, re.I):
            return kind
    return inherited


def section_starts(text: str) -> list[tuple[int, str, str]]:
    found = [(0, "source_preface", "unknown")]
    current = "unknown"
    source_lines = list(lines(text))
    for index, (offset, line) in enumerate(source_lines):
        stripped = line.strip()
        window = " ".join(part.strip() for _, part in source_lines[index:index + 3])
        cue = bool(re.match(r"阅读下面|阅读以下|根据所给|在空白处|Directions", stripped, re.I))
        probe = window if cue else stripped
        instruction_kind = None
        if re.search(r"所给段落开头语.{0,25}续写|段落开头语.{0,25}续写", probe):
            instruction_kind = "continuation_writing"
        elif re.search(r"两项.{0,12}多余|多余.{0,12}两项", probe):
            instruction_kind = "seven_five"
        elif re.search(r"空白处.{0,35}(?:适当|正确形式|括号)|括号内.{0,25}正确形式", probe):
            instruction_kind = "grammar_fill"
        elif re.search(r"短文.{0,90}(?:每题|各题).{0,35}(?:四个|4个|A.{0,10}B.{0,10}C.{0,10}D).{0,40}(?:填入|空白处)|短文.{0,50}空白处.{0,50}选项", probe):
            instruction_kind = "cloze"
        if PART.match(stripped) or EN_HEADING.match(stripped) or instruction_kind:
            kind = instruction_kind or identify_type(stripped, current)
            if re.match(r"^\s*第.*部分", stripped) and kind == current:
                kind = "unknown"
            current = kind
            if offset == 0:
                found[0] = (0, stripped, kind)
            else:
                found.append((offset, stripped, kind))
    return found


def parse_options(text: str, start: int, end: int, page_map: list[dict]) -> tuple[list[dict], list[str]]:
    block = text[start:end]
    candidates = []
    for offset, line in lines(block):
        line_matches = list(INLINE_OPTION.finditer(line))
        head = OPTION.match(line)
        if head and not any(m.start() == head.start(1) for m in line_matches):
            line_matches.insert(0, head)
        for match in line_matches:
            candidates.append((offset + match.start(1), match.group(1), match.group(2)))
    # Only a complete, ordered, unique set is asserted as parsed options.
    labels = [label for _, label, _ in candidates]
    issues = []
    if not labels:
        return [], issues
    valid_sets = [list("ABCDEFGHIJK"[:n]) for n in range(3, 12)]
    if labels not in valid_sets:
        return [], ["option_labels_incomplete_or_ambiguous"]
    options = []
    for i, (offset, label, delimiter) in enumerate(candidates):
        stop = candidates[i + 1][0] if i + 1 < len(candidates) else len(block)
        if i + 1 == len(candidates):
            following = block[offset + len(label) + len(delimiter):stop]
            passage = re.search(r"(?m)^\s*[A-D]\s*$", following)
            if passage:
                stop = offset + len(label) + len(delimiter) + passage.start()
                issues.append("option_boundary_before_next_passage")
            elif following.count("\n") > 5 or len(following) > 500:
                issues.append("needs_option_boundary")
        # Do not absorb trailing unrelated section text into the last choice;
        # its exact span remains available in the case and material task.
        raw_end = offset + len(block[offset:stop].rstrip("\r\n"))
        options.append({"label": label, "printed_delimiter": delimiter,
                        "source": source_ref(text, start + offset, start + raw_end, page_map)})
    return options, issues


def blank_markers(text: str, start: int, end: int):
    matches = list(BLANK.finditer(text, start, end)) + list(SPACED_BLANK.finditer(text, start, end))
    matches.sort(key=lambda m: (m.start(), m.end()))
    result = []
    occupied = set()
    for match in matches:
        number = next((g for g in match.groups() if g is not None), None)
        if number is None or int(number) > 150 or match.start() in occupied:
            continue
        occupied.add(match.start())
        result.append((match, number))
    return result


def case_base(paper_id: str, number: str, kind: str, source: dict,
              section_id: str, page_map: list[dict], text: str) -> dict:
    return {"question_id": f"{section_id}-Q{number}", "paper_id": paper_id,
            "printed_number": number, "question_type": kind, "source": source,
            "section_id": section_id, "context_binding": "section_shared",
            "method_id": None, "trigger": None, "action": None, "answer": None,
            "formal_method_case": False, "source_authenticity": "unverified",
            "source_rights": "private", "options": [], "issues": []}


def build_source(row: dict, frozen: dict, paper_id: str,
                 extraction_file_sha256: str | None = None) -> dict:
    pages = frozen["pages"]
    text = "\n".join(p["text"] for p in pages)
    if frozen["source_sha256"] != row["sha256"]:
        raise ValueError("Frozen extraction/source manifest SHA mismatch")
    extraction_hash = extraction_file_sha256 or digest(json.dumps(frozen, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for page in pages:
        if digest(page["text"].encode("utf-8")) != page["text_sha256"]:
            raise ValueError("Frozen page text SHA mismatch")
    page_map = page_index(pages)
    starts = section_starts(text)
    sections = []
    cases = []
    pending = []
    for i, (start, heading, kind) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        section_id = f"{paper_id}-S{i + 1:02d}"
        sec_ref = source_ref(text, start, end, page_map)
        section = {"section_id": section_id, "heading": heading, "question_type": kind,
                   "source": sec_ref, "context_binding": "needs_context_binding" if kind in {"reading", "seven_five"} else "section_shared",
                   "material_task": True, "parent_tasks": [], "issues": []}
        sections.append(section)
        if not text[start:end].strip():
            continue
        if kind == "unknown":
            section["issues"].append("unknown_type_or_unmatched_material")
        if kind in WRITING_TYPES:
            section["issues"].append("writing_task_whole_source_retained")
            heading_end = text.find("\n", start, end)
            body = text[heading_end + 1:end] if heading_end >= 0 else ""
            if len(body.strip()) < 20 and i + 1 < len(starts) and starts[i + 1][2] in WRITING_TYPES:
                section["issues"].append("heading_only_or_prompt_missing")
                pending.append({"section_id": section_id, "issue": "heading_only_or_prompt_missing", "source": sec_ref})
                continue
            # The whole task, including any story and supplied opening lines,
            # is the source-level case until a paper reviewer refines it.
            case = case_base(paper_id, f"task{i + 1}", kind, sec_ref, section_id, page_map, text)
            case["case_kind"] = "task_case"
            case["printed_number"] = None
            case["source_sha256"] = row["sha256"]
            case["extraction_sha256"] = extraction_hash
            case["context_ref"] = sec_ref
            case["issues"].append("task_needs_question_segmentation")
            cases.append(case)
            pending.append({"section_id": section_id, "issue": "writing_task_needs_review", "source": sec_ref})
            continue
        markers = blank_markers(text, start, end) if kind in {"cloze", "seven_five", "grammar_fill", "vocabulary"} else []
        numbers = [m for m in NUMBER.finditer(text, start, end) if int(m.group(1)) <= 150]
        if kind == "cloze":
            numbers += [m for m in CLOZE_BARE_NUMBER.finditer(text, start, end) if int(m.group(1)) <= 150]
            numbers.sort(key=lambda m: m.start())
        if kind in {"seven_five", "grammar_fill"} and markers:
            # Numbered prose lists are material, while explicit blanks are the
            # printed answer locations for these sections.
            numbers = []
        accepted = []
        previous = None
        for m in numbers:
            n = int(m.group(1))
            if previous is not None and n <= previous:
                section["issues"].append("nonmonotonic_number_candidate")
            accepted.append(m)
            previous = n
        if not accepted and kind != "unknown":
            section["issues"].append("no_leaf_question_segmented")
        for j, m in enumerate(accepted):
            qstart = m.start()
            qend = accepted[j + 1].start() if j + 1 < len(accepted) else end
            n = m.group(1)
            occurrence = 1 + sum(p.group(1) == n for p in accepted[:j])
            child_matches = [c for c in CHILD.finditer(text, qstart, qend)]
            if child_matches:
                section["issues"].append("parent_with_subquestions")
                section["parent_tasks"].append({"printed_number": n,
                    "source": source_ref(text, qstart, qend, page_map),
                    "status": "material_package_not_leaf_question"})
                for k, child in enumerate(child_matches):
                    cstart = child.start()
                    cend = child_matches[k + 1].start() if k + 1 < len(child_matches) else qend
                    child_number = child.group(1)
                    case = case_base(paper_id, f"{n}({child_number})", kind,
                                     source_ref(text, cstart, cend, page_map), section_id, page_map, text)
                    if occurrence > 1:
                        case["question_id"] += f"-occ{occurrence:02d}"
                        case["issues"].append("repeated_printed_number")
                    case["parent_printed_number"] = n
                    case["parent_material_source"] = source_ref(text, qstart, qend, page_map)
                    case["context_ref"] = sec_ref
                    case["source_sha256"] = row["sha256"]
                    case["extraction_sha256"] = extraction_hash
                    case["options"], option_issues = parse_options(text, cstart, cend, page_map)
                    case["issues"].extend(option_issues)
                    cases.append(case)
                continue
            case = case_base(paper_id, n, kind, source_ref(text, qstart, qend, page_map), section_id, page_map, text)
            if occurrence > 1:
                case["question_id"] += f"-occ{occurrence:02d}"
                case["issues"].append("repeated_printed_number")
            case["source_sha256"] = row["sha256"]
            case["extraction_sha256"] = extraction_hash
            case["options"], option_issues = parse_options(text, qstart, qend, page_map)
            case["issues"].extend(option_issues)
            if kind in MC_TYPES and not case["options"]:
                case["issues"].append("option_missing_or_unparsed")
            if kind == "listening":
                case["issues"].append("missing_audio")
            if kind in {"reading", "seven_five"}:
                case["context_binding"] = "needs_context_binding"
            case["context_ref"] = sec_ref
            if kind == "cloze":
                locations = [b for b, num in markers if n == num]
                case["blank_location"] = source_ref(text, locations[0].start(), locations[0].end(), page_map) if len(locations) == 1 else None
                if len(locations) != 1:
                    case["issues"].append("blank_location_unverified")
            cases.append(case)
        if kind in {"seven_five", "grammar_fill", "vocabulary"}:
            existing = {c["printed_number"] for c in cases if c["section_id"] == section_id}
            shared_options, shared_option_issues = parse_options(text, start, end, page_map) if kind == "seven_five" else ([], [])
            for marker, n in markers:
                if int(n) > 150 or n in existing:
                    continue
                ref = source_ref(text, marker.start(), marker.end(), page_map)
                case = case_base(paper_id, n, kind, ref, section_id, page_map, text)
                case["source_sha256"] = row["sha256"]
                case["extraction_sha256"] = extraction_hash
                case["shared_material_source"] = sec_ref
                case["context_ref"] = sec_ref
                case["blank_location"] = ref
                if kind == "seven_five":
                    case["options"] = shared_options
                    case["issues"].extend(shared_option_issues)
                    if [o["label"] for o in shared_options] != list("ABCDEFG"):
                        case["issues"].append("shared_options_missing_or_unparsed")
                if len([num for _, num in markers if num == n]) != 1:
                    case["issues"].append("blank_marker_repeated")
                if kind == "seven_five":
                    case["context_binding"] = "needs_context_binding"
                cases.append(case)
                existing.add(n)
        if not accepted:
            pending.append({"section_id": section_id, "issue": "unsegmented_material_task",
                            "source": sec_ref})
        for issue in sorted(set(section["issues"])):
            pending.append({"section_id": section_id, "issue": issue,
                            "source": source_ref(text, start, min(end, start + 200), page_map)})
    seen = Counter()
    for case in cases:
        qid = case["question_id"]
        seen[qid] += 1
        if seen[qid] > 1:
            case["question_id"] = f"{qid}-occ{seen[qid]:02d}"
            case["issues"].append("repeated_printed_number_or_child_marker")
    return {"schema_version": "1.0.0", "paper_id": paper_id,
            "source_sha256": row["sha256"], "source_paths": frozen["source_paths"],
            "extraction_sha256": extraction_hash,
            "document_text": text, "document_text_sha256": digest(text.encode("utf-8")),
            "pages": page_map, "sections": sections, "cases": cases,
            "pending_review": pending, "source_authenticity": "unverified", "source_rights": "private"}


def title_identity(row: dict) -> str:
    title = Path(row["relative_path"].replace("\\", "/")).stem
    year = re.search(r"(?:19|20)\d{2}", title)
    yy = year.group() if year else row.get("claimed_year") or "unknown-year"
    month = re.search(r"(?<!\d)(1[0-2]|[1-9])月", title)
    mm = f"{int(month.group(1)):02d}m" if month else ""
    region = row.get("claimed_volume")
    if not region:
        bracket = re.search(r"[（(]([^（）()]+)[）)]", title)
        region = bracket.group(1) if bracket else "未标地区"
    region = re.sub(r"(?:空白卷|试题|真题|试卷|解析卷|答案|\s)", "", region)
    region = re.sub(r"[^\w\u3400-\u9fffⅠⅡⅢIVX-]", "", region) or "未标地区"
    return f"{yy}-{region}{('-' + mm) if mm else ''}"


def run(manifest_path: Path = DEFAULT_MANIFEST, output_root: Path = DEFAULT_OUTPUT) -> dict:
    manifest_path = Path(manifest_path).resolve()
    output_root = Path(output_root).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    source_root = Path(manifest["source_root"]).resolve()
    if output_root == source_root or output_root.is_relative_to(source_root):
        raise ValueError("Case bank output must be outside source directory")
    rows = [r for r in manifest["files"] if selected(r, "questions")]
    rows.sort(key=lambda r: r["relative_path"])
    variants = Counter()
    banks = []
    all_cases = []
    pending = []
    original_hashes = {}
    for row in rows:
        fingerprint = row["sha256"].lower()
        source_path = (source_root / Path(row["relative_path"].replace("\\", "/"))).resolve()
        if not source_path.is_relative_to(source_root) or not source_path.is_file():
            raise ValueError(f"Unsafe or missing source: {row['relative_path']}")
        data = source_path.read_bytes()
        if digest(data) != fingerprint or len(data) != int(row["bytes"]):
            raise ValueError(f"Source SHA/size changed before build: {row['relative_path']}")
        original_hashes[source_path] = fingerprint
        frozen_path = manifest_path.parent / "pages" / f"{fingerprint}.json"
        frozen_bytes = frozen_path.read_bytes()
        frozen = json.loads(frozen_bytes.decode("utf-8"))
        identity = paper_label(row["relative_path"])
        variants[identity] += 1
        paper_id = f"{identity}-v{variants[identity]:02d}"
        bank = build_source(row, frozen, paper_id, digest(frozen_bytes))
        filename = f"{paper_id}.json"
        freeze_json(output_root / "papers" / filename, bank)
        strict = []
        for case in bank["cases"]:
            kind = case["question_type"]
            if kind not in {"single_choice", "cloze", "seven_five", "grammar_fill"} or case["issues"]:
                continue
            if kind in {"cloze", "seven_five", "grammar_fill"} and not case.get("blank_location"):
                continue
            if kind in {"single_choice", "cloze", "seven_five"} and not case["options"]:
                continue
            if kind == "seven_five" and [o["label"] for o in case["options"]] != list("ABCDEFG"):
                continue
            context = case.get("context_ref") or case["source"]
            if any(p["requires_ocr"] for p in bank["pages"] if p["page_number"] in context["page_numbers"]):
                continue
            strict.append({"question_id": case["question_id"], "paper_id": paper_id,
                           "question_type": kind, "printed_number": case["printed_number"],
                           "question": project_layout(case["source"]),
                           "shared_context": project_layout(context),
                           "options": [{"label": opt["label"],
                                        "printed_delimiter": opt["printed_delimiter"],
                                        "projection": project_layout(opt["source"])}
                                       for opt in case["options"]],
                           "blank_location": case.get("blank_location"),
                           "source_sha256": fingerprint, "extraction_sha256": bank["extraction_sha256"],
                           "status": "structural_question_input; semantic_review_pending"})
        input_file = f"question-inputs/{filename}"
        freeze_json(output_root / input_file, {"paper_id": paper_id, "source_sha256": fingerprint,
                                               "question_inputs": strict})
        all_cases.extend(bank["cases"])
        for item in bank["pending_review"]:
            pending.append({"paper_id": paper_id, "source_sha256": fingerprint, **item})
        ocr = [p["page_number"] for p in bank["pages"] if p["requires_ocr"]]
        banks.append({"paper_id": paper_id, "source_sha256": fingerprint,
                      "extraction_sha256": bank["extraction_sha256"],
                      "source_paths": bank["source_paths"],
                      "case_file": f"papers/{filename}",
                      "question_input_file": input_file,
                      "question_input_subset": [entry["question_id"] for entry in strict],
                      "leaf_question_cases": sum(c.get("case_kind") != "task_case" for c in bank["cases"]),
                      "material_tasks": len(bank["sections"]),
                      "ocr_pending_pages": ocr,
                      "status": "structural_parse_pending_review"})
    for path, expected in original_hashes.items():
        if digest(path.read_bytes()) != expected:
            raise ValueError(f"Source SHA changed during build: {path}")
    ids = [c["question_id"] for c in all_cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Question IDs are not unique")
    exact = defaultdict(list)
    for case in all_cases:
        blank_location = case.get("blank_location")
        if blank_location and case["source"]["quote"].strip() == blank_location["quote"]:
            continue
        fingerprint_text = case["source"]["quote"] + "\n" + case.get("context_ref", {}).get("quote", "")
        exact[digest(fingerprint_text.encode("utf-8"))].append(case["question_id"])
    groups = [{"exact_question_sha256": h, "occurrences": ids}
              for h, ids in sorted(exact.items()) if len(ids) > 1]
    source_lookup = {b["paper_id"]: b for b in banks}
    paper_texts = {b["paper_id"]: json.loads((output_root / b["case_file"]).read_text(encoding="utf-8"))["document_text"]
                   for b in banks}
    for case in all_cases:
        # Replay exact spans against each immutable per-paper dossier.
        ref = case["source"]
        if paper_texts[case["paper_id"]][ref["start"]:ref["end"]] != ref["quote"]:
            raise ValueError(f"Span replay failed: {case['question_id']}")
    freeze(output_root / "question-cases.jsonl",
           ("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in all_cases)).encode("utf-8"))
    freeze_json(output_root / "source-bank.json", {"schema_version": "1.0.0", "sources": banks,
                                                   "exact_duplicate_groups": groups})
    summary = {"schema_version": "1.0.0", "source_files": len(banks),
               "material_tasks": sum(b["material_tasks"] for b in banks),
               "leaf_question_cases": sum(c.get("case_kind") != "task_case" for c in all_cases),
               "task_cases": sum(c.get("case_kind") == "task_case" for c in all_cases),
               "parse_pending_sources": len({p["paper_id"] for p in pending}),
               "ocr_pending_pages": sum(len(b["ocr_pending_pages"]) for b in banks),
               "option_missing": sum("option_missing_or_unparsed" in c["issues"] for c in all_cases),
               "unknown_types": sum(c["question_type"] == "unknown" for c in all_cases),
               "exact_duplicate_groups": len(groups),
               "status": "source_level_question_cases_pending_review"}
    freeze_json(output_root / "summary.json", summary)
    freeze_json(output_root / "pending-review.json", {"items": pending})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
