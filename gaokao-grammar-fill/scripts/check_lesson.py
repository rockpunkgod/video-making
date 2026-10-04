"""Read-only checks for a gaokao lesson draft; no solver and no answer key."""
import argparse
import json
from pathlib import Path
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def norm(text):
    text = re.sub(r"_{2,}\s*\d+\s*_{2,}", " ___ ", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"""(?<!\w)['"]|['"](?!\w)""", "", text)
    return re.sub(r"\s+", " ", text).strip().lower().rstrip(".,;:?!")

def quoted(text):
    for match in re.finditer(r'“([^”\n]+)”|"([^"\n]+)"', text):
        value = match.group(1) or match.group(2)
        if not re.search(r"[\u3400-\u9fff]", value) and len(re.findall(r"[A-Za-z]+", value)) >= 2:
            yield match.start(), value

def contains_quote(haystack, quote):
    parts = [p for p in re.split(r"\.{3,}|…+", quote) if norm(p)]
    return bool(parts) and all(norm(part) in norm(haystack) for part in parts)

def options_in(text):
    markers = list(re.finditer(r"(?<![A-Za-z])([A-G])[.)]\s+", text))
    return {m.group(1): text[m.end():markers[i + 1].start() if i + 1 < len(markers) else len(text)].strip()
            for i, m in enumerate(markers)}

def parse_source(source, kind):
    blank_ids = list(dict.fromkeys(int(x) for x in re.findall(r"_{2,}\s*(\d+)\s*_{2,}", source)))
    numbered = list(re.finditer(r"(?m)^\s*(\d{1,3})[.)]\s+", source))
    questions = {}
    for i, match in enumerate(numbered):
        chunk = source[match.end():numbered[i + 1].start() if i + 1 < len(numbered) else len(source)]
        opts = options_in(chunk)
        if opts:
            first_option = re.search(r"(?<![A-Za-z])[A-G][.)]\s+", chunk)
            questions[int(match.group(1))] = {"stem": chunk[:first_option.start()].strip(), "options": opts}
    if kind == "seven-five":
        marker = re.search(r"(?m)^\s*A[.)]\s+", source)
        opts = options_in(source[marker.start():]) if marker else {}
        body = source[:marker.start()] if marker else source
        questions = {number: {"stem": "", "options": opts} for number in blank_ids}
    else:
        body = source[:numbered[0].start()] if numbered else source
    body_paras = [p.strip() for p in re.split(r"\n\s*\n", body)
                  if re.match(r'["“]?[A-Za-z_]', p.strip())]
    body_text = "\n\n".join(body_paras)
    first = re.split(r"(?<=[.!?])\s+", body_paras[0], maxsplit=1)[0] if body_paras else ""
    expected = blank_ids or list(questions)
    return body_text, body_paras, first, questions, expected

def draft_sections(draft):
    found = []
    offset = 0
    for block in re.split(r"\n\s*\n", draft):
        start = draft.find(block, offset)
        offset = start + len(block)
        if re.match(r"\s*(?:答案|最终|按原|最后按|完整答案)", block):
            continue
        match = re.match(r"\s*[^。！？\n\d]{0,16}?第?(\d{1,3})(?:题|空|[.、])", block)
        if match:
            found.append((int(match.group(1)), start, block))
    return found

def source_facts(source, kind):
    body, paras, first, questions, expected = parse_source(source, kind)
    blanks = {}
    for index, para in enumerate(paras):
        for marker in re.finditer(r"_{2,}\s*(\d+)\s*_{2,}", para):
            blanks[int(marker.group(1))] = {
                "paragraph": index + 1,
                "before_in_paragraph": para[:marker.start()].strip(),
                "after_in_paragraph": para[marker.end():].strip(),
                "previous_paragraph": paras[index - 1] if index else None,
                "next_paragraph": paras[index + 1] if index + 1 < len(paras) else None,
            }
    return {"source_first_sentence": first,
            "source_paragraphs": [{"paragraph": i + 1, "text": p} for i, p in enumerate(paras)],
            "blank_contexts": blanks,
            "source_questions": {n: {"stem": q["stem"]} for n, q in questions.items()} if kind == "seven-five" else questions,
            "shared_options": next(iter(questions.values()))["options"] if kind == "seven-five" and questions else None,
            "expected_numbers": expected}

def clear_subject_finite(text):
    # High-precision cue only: a stated subject followed by a finite auxiliary
    # cannot be a subject-less base-verb imperative. Not a full English parser.
    return re.match(r"^(?:(?:A|An|The)\s+.+?|It|They|We|You|He|She|This|That|These|Those)\s+(?:is|are|was|were|will|would|can|could|may|might|must|should|has|have|had|does)\b", text.strip(), re.I)

def compact_facts(facts):
    result = dict(facts)
    contexts = {}
    for number, item in facts["blank_contexts"].items():
        before = re.split(r"(?<=[.!?])\s+", item["before_in_paragraph"])
        after = re.split(r"(?<=[.!?])\s+", item["after_in_paragraph"])
        contexts[number] = {
            "paragraph": item["paragraph"],
            "nearest_before": " ".join(before[-2:]),
            "nearest_after": " ".join(after[:2]),
            "previous_paragraph_number": item["paragraph"] - 1 if item["previous_paragraph"] is not None else None,
            "next_paragraph_number": item["paragraph"] + 1 if item["next_paragraph"] is not None else None,
        }
    result["blank_contexts"] = contexts
    result["context_note"] = "邻句只取同段最近两句；全文段落上面只列一次，需要更远证据按段号回查。空前为空时不能把后句称空前。"
    if facts["shared_options"]:
        result["option_structure_cues"] = {
            letter: {"visible_subject_and_finite": match.group(),
                     "meaning": "已出现主语与限定助动词/情态动词，不能只因表达建议就称无主语祈使句；再读完整句确认"}
            for letter, option in facts["shared_options"].items()
            if (match := clear_subject_finite(option))
        }
    return result

METHODS = {
    "cloze": r"相同词性定答案|瞻前顾后|上下呼应",
    "seven-five": r"三一致|结构一致|主语一致|时态一致|褒贬|内容一致|核心内容|逻辑|包含|因果|转折|对比|并列|递进|指代|照应",
    "reading": r"三化|定位|顺藤摸瓜|左顾右盼|中心思想|首尾|合并|上下文|构词|同义|重复.{0,4}逻辑",
    "grammar": r"代词|物主|词性|派生|名词|动词|形容|副词|冠词|介词|连词|时态|语态|主谓|非谓语|分词|不定式|句间|逻辑|从句"
}

def check(source, draft, kind, route="other", only=None):
    body, paras, first, questions, expected = parse_source(source, kind)
    facts = source_facts(source, kind)
    detected = list(expected)
    if only:
        expected = only
    sections = draft_sections(draft)
    if only and len(only) == 1 and not sections:
        sections = [(only[0], 0, draft)]
    ids = [n for n, _, _ in sections]
    issues = []
    def issue(code, message, excerpt=""):
        issues.append({"code": code, "message": message, "excerpt": excerpt})
    if only and detected and any(n not in detected for n in only):
        issue("source_scope_mismatch", "指定的单题题号不在已识别的源题中，须检查范围和题面解析。", str(only))
    if not draft.lstrip().startswith("同学"):
        issue("opening", "学生稿须以同学开头。")
    verdict = re.search(r"(?:你的|你给的|你填的|学生的)答案[^。！？\n]*(?:正确|全对|都对|不对|错|成立|应改|应该改)", draft)
    if verdict:
        issue("answer_verdict_mode", "交付只有讲解；删除对学生答案串的评对错，保留本题证据、逐题结论与回填。", verdict.group())
    for number in expected:
        if number not in ids:
            issue("question_coverage", f"未找到第{number}题/空的独立逐题段落；不能只在汇总给答案。")
    for number, _, block in sections:
        if expected and number not in expected:
            issue("scope", f"当前请求范围外的第{number}题/空。", block[:90])
        opening = block if only else re.split(r"[。！？\n]", block, maxsplit=1)[0]
        if not re.search(METHODS[kind], opening):
            issue("method_visibility", f"第{number}题/空的首句未看到实际课程方法或语法知识点。", opening[:160])
    first_section = min((start for _, start, _ in sections), default=len(draft))
    prelude = draft[:first_section].strip()
    if kind == "seven-five":
        grouping = re.split(r"带着|回到正文|看正文|浏览正文", prelude, maxsplit=1)[0]
        if re.search(r"与全文|和全文|明显干扰|是干扰项", grouping):
            issue("premature_option_verdict", "分组阶段已经用全文下判断；先描述选项，回文取证后再排除。", grouping[-240:])
        opts = facts["shared_options"] or {}
        for claim in re.finditer(r"((?:[A-G][、，,和及与\s]*){1,7})(?:都|均|是|属于|为|的)*祈使句", prelude):
            for letter in re.findall(r"[A-G]", claim.group(1)):
                marker = clear_subject_finite(opts.get(letter, ""))
                if marker:
                    issue("imperative_group_conflict", f"{letter}被分为祈使句，但原项已有主语和限定动词：{marker.group()}。应按真实句法分组，不按建议内容分。", claim.group())
    if kind == "reading" and route == "expository":
        if not re.match(r"\s*同学[，,、\s]*先看题目", draft):
            issue("reading_entry", "说明/议论稿尚未从实际读题进入，检查是否先总结全文。", prelude[:200])
        title_ids = [n for n, q in questions.items() if re.search(r"best title|main (?:idea|message)|mainly about", q["stem"], re.I)]
        guess_ids = [n for n, q in questions.items() if re.search(r"(?:word|phrase).*(?:mean|refer)|underlined.*mean", q["stem"], re.I)]
        order = list(dict.fromkeys(n for n in ids if n in expected))
        for number, start, block in sections:
            end = min((p for _, p, _ in sections if p > start), default=len(draft))
            teaching = draft[start:end]
            if number in title_ids and "三化" not in teaching:
                issue("course_title_method", f"第{number}题应用三化法，不能用泛称主旨定位法替代；实际展示首尾、段首与重复词求证。")
            if number in title_ids and len(paras) >= 3:
                cn = {2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
                last = re.search(r"尾段|末段|结尾|最后一段|第(?:" + str(len(paras)) + "|" + cn.get(len(paras), "不存在") + r")段", teaching)
                middle = re.search(r"中间段|第(?:" + "|".join(str(i) + "|" + cn.get(i, "不存在") for i in range(2, len(paras))) + r")段", teaching)
                if middle and last and middle.start() < last.start():
                    issue("threehua_reading_sequence", f"第{number}题先展开中间段才到尾段；对照实际正文求证应先首尾再中间。特殊背景段例外需由本题支持。")
            if number in guess_ids and not re.search(r"代回|放回|替换回|换回|换成.*(?:句|原文)", teaching):
                issue("guess_refill", f"第{number}题推得本句义后，要实际代回原句验证。")
        if title_ids and order and order[0] not in title_ids:
            issue("reading_order", "检测到标题/主旨题，但实际逐题开头不是主旨题；请对照课程相对顺序。", str(order))
        if guess_ids and any(n in order for n in guess_ids):
            ordinary = [n for n in order if n not in title_ids + guess_ids]
            if ordinary and min(order.index(n) for n in guess_ids if n in order) < max(order.index(n) for n in ordinary):
                issue("reading_order_review", "猜词题出现在其他题之前；按实际题型人工复核，不机械重排特殊设问。", str(order))
    for pos, value in quoted(draft):
        prefix = draft[max(0, pos - 45):pos]
        # Refilled/condensed examples can legitimately differ from the printed text.
        rewritten = re.search(r"回填|填入|填为|还原为|化简|相当于|完整句|句意是", prefix)
        grammar_example = re.search(r"\b(?:to do|sth|sb|doing)\b", value, re.I)
        rewritten = rewritten or grammar_example
        if not rewritten and not contains_quote(source, value):
            issue("literal_quote", "英文引文不能在原始题面逐字找到；若是回填/化简请说明，若称原文则修正。", value)
        opt_claim = re.search(r"([A-G])\s*(?:项)?\s*(?:中(?:的)?|里(?:的)?|说|是|：|:)\s*$", prefix)
        if opt_claim:
            before = [(n, start) for n, start, _ in sections if start <= pos]
            number = before[-1][0] if before else (expected[0] if expected else None)
            opts = questions.get(number, {}).get("options", {})
            letter = opt_claim.group(1)
            if letter in opts and not contains_quote(opts[letter], value):
                issue("option_quote_origin", f"声称来自{letter}项的引文不在该项。实际选项：{opts[letter]}", value)
        if re.search(r"空前(?:正文|原文|句子|句)?\s*(?:是|说|有|提到|：|:)?\s*$", prefix):
            before = [(n, start) for n, start, _ in sections if start <= pos]
            if before:
                number = before[-1][0]
                marker = re.search(r"_{2,}\s*" + str(number) + r"\s*_{2,}", body)
                if marker and not contains_quote(body[:marker.start()], value):
                    issue("before_blank_origin", f"引文不在未填正文第{number}空之前。", value)
    # Position labels are factual claims, including Chinese paraphrases. Require a
    # nearby English cue so the claimed region can be compared to the source.
    for claim in re.finditer(r"(?:空前|空后|上一段|下一段|首句)(?:[^。！？\n]*)(?:[。！？]|$)", draft):
        label = re.match(r"空前|空后|上一段|下一段|首句", claim.group()).group()
        segment = claim.group()
        cues = list(quoted(segment))
        before = [(n, start) for n, start, _ in sections if start <= claim.start()]
        number = before[-1][0] if before else None
        context = facts["blank_contexts"].get(number)
        if label == "首句" and kind == "cloze" and claim.start() < first_section:
            if not cues:
                issue("source_position_cue", "解读首句须带实际首句短引文；只解读这句，后文放到大意。", segment[:200])
            elif any(not contains_quote(first, value) for _, value in cues):
                issue("first_sentence_origin", "称首句的英文线索不在实际首句中。", segment[:200])
        elif context and label in ("空前", "空后", "上一段", "下一段"):
            region = {"空前": "before_in_paragraph", "空后": "after_in_paragraph", "上一段": "previous_paragraph", "下一段": "next_paragraph"}[label]
            actual = context[region]
            if not actual:
                issue("empty_source_region", f"第{number}空所称{label}在源文中为空；不能把空后或别段内容放到这里。", segment[:200])
            elif not cues:
                issue("source_position_cue", f"第{number}空称{label}但无实际英文定位词；请按定位卡取短引文核实中文位置复述。", segment[:200])
            elif not any(contains_quote(actual, value) for _, value in cues):
                issue("source_position_origin", f"第{number}空{label}的引文不在所称区域。", segment[:200])
    if kind == "cloze":
        # This verifies a selected word/letter pair, never whether the choice is correct.
        for number, _, block in sections:
            opts = questions.get(number, {}).get("options", {})
            for match in re.finditer(r"(?:选|填)\s*([A-D])\s+([A-Za-z]+)\b", block):
                letter, word = match.groups()
                if letter in opts and not re.match(re.escape(word) + r"\b", re.sub(r"^[^A-Za-z]+", "", norm(opts[letter])), re.I):
                    issue("letter_word_binding", f"第{number}空{letter}项实际是 {opts[letter]}，不是 {word}。", match.group())
        for match in re.finditer(r"(\d{1,3})[.、：:]?\s*(?:题|空)?\s*(?:选|填)?\s*([A-D])\s+([A-Za-z]+)\b", draft):
            number, letter, word = int(match.group(1)), match.group(2), match.group(3)
            opts = questions.get(number, {}).get("options", {})
            if letter in opts and not re.match(re.escape(word) + r"\b", re.sub(r"^[^A-Za-z]+", "", norm(opts[letter])), re.I):
                issue("summary_binding", f"汇总第{number}空{letter}项实际是 {opts[letter]}，不是 {word}。", match.group())
    return {
        **facts,
        "automatic_flags": issues,
        "source_first_sentence": first,
        "source_paragraphs": [{"paragraph": i + 1, "text": p} for i, p in enumerate(paras)],
        "source_questions": {n: {"stem": q["stem"]} for n, q in questions.items()} if kind == "seven-five" else questions,
        "shared_options": next(iter(questions.values()))["options"] if kind == "seven-five" and questions else None,
        "expected_numbers": expected,
        "detected_source_numbers": detected,
        "actual_numbered_sections": ids,
        "draft_opening_for_manual_review": prelude,
        "manual_review_still_required": [
            "逐项以真实主谓结构确认分组，不能照搬范例字母。",
            "首句解读只来自首句；开场不能逐一提前讲出待填核心动作。",
            "引文的空前/空后/段落标签准确；名词语义不符不能说成语法不能作主语。",
            "每题有方法、决定性证据、关系、证据后结论和具体回填/原文验证。",
            "必要生词以真实构词或上下文推义，临场口语自然，不输出检查过程。"
        ],
        "limitations": "这是定位疑点的辅助检查，不会解题，不证明语法语义正确；版式特殊时解析可能不全，需对照源文。"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--draft", help="Omit to obtain source facts before drafting")
    parser.add_argument("--kind", required=True, choices=list(METHODS))
    parser.add_argument("--route", default="other", choices=["other", "expository", "narrative", "informational"])
    parser.add_argument("--only", help="Comma-separated question numbers explicitly requested by the student")
    args = parser.parse_args()
    only = [int(n) for n in args.only.split(",")] if args.only else None
    source = Path(args.source).read_text(encoding="utf-8-sig")
    if args.draft:
        checked = check(source, Path(args.draft).read_text(encoding="utf-8-sig"), args.kind, args.route, only)
        result = {key: checked[key] for key in ("automatic_flags", "expected_numbers", "actual_numbered_sections", "limitations")}
        result["review_note"] = "源文定位卡在写稿前已读，本次不重复全文。仍须人工复核中文复述、选项方向与课程操作。"
    else:
        result = compact_facts(source_facts(source, args.kind))
    result["next_step"] = (
        "这是初稿检查，不是学生交付稿。逐项处理实际问题并修稿后复查；最终只交付自然讲解，不输出本检查。"
        if args.draft and result.get("automatic_flags") else
        "自动未标出疑点仍须回读中文释义和课程实际操作；若是修订后复查才可交付，仅交付学生稿。"
        if args.draft else
        "现在按课程写公开讲解初稿，保存后必须用同一解释器再次运行本脚本并增加--draft 初稿路径。源文定位已完成但修稿尚未执行，不能直接结束任务。"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("automatic_flags") else 0

if __name__ == "__main__":
    raise SystemExit(main())
