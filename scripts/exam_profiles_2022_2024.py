"""Local answer-isolated profiles for five supplied exams; no semantic certification.

Source and output text stays in ignored local-data. Printed numbers are retained.
No reveal material is consulted by parse() or blind().
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess

from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry, validate_schema
from scripts.ingest_exam_sources import ROOT, freeze_json, sha

EXAMS = ('gaokao-2022-I', 'gaokao-2022-II', 'gaokao-2023-I',
         'gaokao-2023-II', 'gaokao-2024-II')
NUMBER = re.compile(r'^\s*(\d+)(?:[.．]\s*|\s+)(.*)$')
MARKER = re.compile(r'_{2,}(\d+)_{2,}')


def choices(lines, letters='ABCD'):
    text = '\n'.join(lines)
    labels = list(re.finditer(r'(?m)(?<!\S)([A-G])[.．]\s*|(?:^|\t| {2,})([A-G])\s+', text))
    names = [m[1] or m[2] for m in labels]
    if ''.join(names) != letters:
        raise ValueError('Option labels incomplete or ambiguous; no answer-assisted repair')
    result = {names[i]: text[m.end():labels[i+1].start() if i+1 < len(labels) else len(text)].strip()
              for i, m in enumerate(labels)}
    if not all(result.values()):
        raise ValueError('Empty printed option')
    return result


def parse(source):
    if source.get('exam_id') not in EXAMS or source.get('source_kind') != 'blank':
        raise ValueError('Unsupported blank source')
    if source['automatic_numbered_paragraphs']:
        raise ValueError('Automatic numbering requires source review')
    if sha(source['text'].encode('utf-8')) != source['text_sha256']:
        raise ValueError('Frozen extraction changed')
    if '\n'.join(source['paragraphs']) != source['text']:
        raise ValueError('Paragraph extraction differs from frozen text')
    lines = source['paragraphs']
    def find(test, start=0):
        found = [i for i in range(start, len(lines)) if test(lines[i].strip())]
        if not found:
            raise ValueError('Required printed section missing')
        return found[0]
    reading = find(lambda s: s.startswith('第二') and '阅读' in s)
    seven = find(lambda s: s.startswith('第二节'), reading+1)
    language = find(lambda s: s.startswith('第三部分'), seven+1)
    grammar = find(lambda s: s.startswith('第二节'), language+1)
    writing = find(lambda s: s.startswith('第') and '写作' in s, grammar+1)
    continuation = find(lambda s: s.startswith('第二节'), writing+1)
    questions, bindings = [], {}
    def add(number, kind, stem, passage='', options=None, paragraph_range=None, **extra):
        suffix = 'q'+str(number) if number is not None else 'task-'+kind
        q = dict(question_id=source['exam_id']+'-'+suffix, question_type=kind,
                 stem=stem, passage=passage, **extra)
        if options is not None:
            q['options'] = options
        validate_schema('question-input', q)
        questions.append(q)
        bindings[q['question_id']] = dict(printed_question_number=number,
            source_sha256=source['source_sha256'], extraction_sha256=source['text_sha256'],
            input_sha256=sha(json.dumps(q, ensure_ascii=False, sort_keys=True).encode()),
            source_paragraph_range=paragraph_range,
            embedded_image_transcription='pending_source_review',
            original_layout_review='pending_source_review')
    heads = [i for i in range(reading, seven) if lines[i].strip() in list('ABCD')]
    if [lines[i].strip() for i in heads] != list('ABCD'):
        raise ValueError('Reading passages A-D incomplete')
    for k, start in enumerate(heads):
        end = heads[k+1] if k+1 < len(heads) else seven
        starts = [i for i in range(start+1, end-1) if NUMBER.match(lines[i])
                  and re.match(r'^\s*A(?:[.．]|\s)', lines[i+1])]
        if not starts:
            raise ValueError('Reading questions absent')
        passage = '\n'.join(lines[start+1:starts[0]])
        for j, i in enumerate(starts):
            m = NUMBER.match(lines[i]); stop = starts[j+1] if j+1 < len(starts) else end
            add(int(m[1]), '阅读理解', m[2], passage, choices(lines[i+1:stop]), [start+1, stop])
    option_start = find(lambda s: bool(re.match(r'^A(?:[.．]|\s)', s)), seven+1)
    seven_passage = '\n'.join(lines[seven+2:option_start])
    opts = choices(lines[option_start:language], 'ABCDEFG')
    for m in MARKER.finditer(seven_passage):
        add(int(m[1]), '七选五', lines[seven+1], seven_passage, opts,
            [seven+1, language], task_type='original_blank_'+m[1])
    rows = [i for i in range(language+3, grammar) if NUMBER.match(lines[i])]
    if len(rows) != 15:
        raise ValueError('Cloze option rows incomplete')
    cloze_passage = '\n'.join(lines[language+3:rows[0]])
    blank_numbers = [int(m[1]) for m in MARKER.finditer(cloze_passage)]
    row_numbers = [int(NUMBER.match(lines[i])[1]) for i in rows]
    if blank_numbers != row_numbers:
        raise ValueError('Cloze blank/option numbering differs')
    for j, i in enumerate(rows):
        m = NUMBER.match(lines[i]); end = rows[j+1] if j+1 < len(rows) else grammar
        add(int(m[1]), '完形填空', lines[language+2], cloze_passage,
            choices([m[2], *lines[i+1:end]]), [language+2, end], task_type='original_blank_'+m[1])
    grammar_passage = '\n'.join(lines[grammar+2:writing])
    for m in MARKER.finditer(grammar_passage):
        hint = re.match(r'\s*\(\s*([A-Za-z]+)\s*\)', grammar_passage[m.end():])
        add(int(m[1]), '语法填空', lines[grammar+1], grammar_passage,
            paragraph_range=[grammar+1, writing], task_type='original_blank_'+m[1],
            **({'given_word': hint[1]} if hint else {}))
    app_start = find(lambda s: '假定你是' in s, writing+1)
    m = NUMBER.match(lines[app_start]); app_number = int(m[1]) if m else None
    add(app_number, '应用文', '\n'.join(lines[app_start:continuation]),
        paragraph_range=[app_start, continuation], task_type='source_task_constraints')
    story_start = find(lambda s: '阅读下面材料' in s, continuation+1)
    notes = find(lambda s: s.startswith('注意'), story_start+1)
    starters = [i for i in range(notes+1, len(lines)-1)
                if lines[i].strip() and not lines[i].strip().startswith('_')
                and lines[i+1].strip().startswith('___')]
    if len(starters) != 2:
        raise ValueError('Continuation starters incomplete or ambiguous')
    m = NUMBER.match(lines[story_start]); story_number = int(m[1]) if m else None
    add(story_number, '读后续写', '\n'.join([lines[story_start], *lines[notes:starters[0]]]),
        '\n'.join(lines[story_start+1:notes]), paragraph_range=[story_start, len(lines)],
        continuation_starters=[lines[i] for i in starters], task_type='source_task_constraints')
    counts = Counter(q['question_type'] for q in questions)
    if counts != Counter({'阅读理解':15, '七选五':5, '完形填空':15, '语法填空':10, '应用文':1, '读后续写':1}):
        raise ValueError('Six-type written paper incomplete')
    numbers = [b['printed_question_number'] for b in bindings.values()]
    first = numbers[0]
    if first not in (1, 21) or numbers != list(range(first, first+47)):
        raise ValueError('Printed numbering incomplete; no renumbering permitted')
    return {'paper_id':source['exam_id'], 'questions':questions}, bindings


def blind(dataset, exam_id):
    directory = Path(dataset)
    source = json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    paper, bindings = parse(source)
    registry = Registry(); registry.validate(); analyzer = QuestionAnalyzer(registry)
    results = [analyzer.analyze(deepcopy(q)) for q in paper['questions']]
    result = dict(schema_version='1.0.0', exam_id=exam_id, pass_='blind', source_kind='blank',
        source_sha256=source['source_sha256'], inputs=paper, source_bindings=bindings,
        engine_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        method_versions={mid:m['version'] for mid,m in registry.methods.items()},
        predictions=results, paper_analysis=PaperAnalyzer(analyzer).analyze(deepcopy(paper)),
        question_type_counts=dict(Counter(q['question_type'] for q in paper['questions'])),
        limitations=['Embedded images and table layout require source review; no OCR or layout certification.',
            'No semantic review provider. Abstention is not independently solving English questions.',
            'No student drafts; writing cannot be exact-match evaluated.'])
    result['pass'] = result.pop('pass_')
    freeze_json(directory/'predictions'/exam_id/'blind.json', result)
    return dict(exam_id=exam_id, written_questions=len(results), objective_questions=45,
                engine_answers=sum(x['answer'] is not None for x in results),
                prediction_frozen=True, semantic_review='pending', question_type_counts=result['question_type_counts'])


def reviewed_blind(dataset, exam_id, review_path):
    """Freeze host-reviewed outputs separately; never modify mechanical predictions.

    Local review annotations are external assertions, not semantic certification.
    The review must be prepared without revealing this exam's reference answers.
    """
    if exam_id != 'gaokao-2023-I':
        raise ValueError('This local host-review adapter only supports the reviewed 2023 I q21')
    directory = Path(dataset)
    mechanical_path = directory/'predictions'/exam_id/'blind.json'
    mechanical_bytes = mechanical_path.read_bytes()
    mechanical = json.loads(mechanical_bytes)
    blank = json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    paper, bindings = parse(blank)
    if mechanical['inputs'] != paper:
        raise ValueError('Mechanical prediction differs from current blank input')
    if (directory/'results'/exam_id/'reveal.json').exists():
        raise ValueError('Cannot label a new review blind after saved reveal results')
    review_bytes = Path(review_path).read_bytes(); review = json.loads(review_bytes)
    if review.get('question_id') != 'gaokao-2023-I-q21' or review.get('method_ids') != ['R12','R01']:
        raise ValueError('This adapter is bound to one reviewed question and method sequence')
    if review['review_stage'] != 'before_reveal':
        raise ValueError('Review is not declared answer-isolated')
    original = next(q for q in paper['questions'] if q['question_id'] == review['question_id'])
    q = deepcopy(original)
    def span(quote):
        start = q['passage'].index(quote)
        return dict(field='passage', start=start, end=start+len(quote), quote=quote)
    locator = span(review['locator_quote'])
    evidence = [span(s) for s in review['evidence_quotes']]
    # Full passage supports the explicit negative-evidence search; bounded quotes
    # additionally expose decisive positive and contradiction evidence.
    evidence.append(span(q['passage']))
    q['requested_chain'] = review['method_ids']
    q['observations'] = [dict(method_id='R12', evidence=[locator], reviewed=True),
                         dict(method_id='R01', evidence=evidence, reviewed=True)]
    q['relations'] = [dict(method_id='R01', candidate=c['candidate'], effect=c['effect'],
        claim=c['claim'], evidence=evidence, decision_rule_check=c['decision'],
        stop_rule_check=c['stop'], verification=c['decision']+' '+c['stop'],
        reviewer=review['reviewer'], review_status='reviewed') for c in review['candidate_checks']]
    registry = Registry(); registry.validate()
    q['action_executions'] = [dict(execution_id='locate', method_id='R12',
        method_version=registry.methods['R12']['version'], role='locator', input_artifact_ids=[],
        concrete_action='圈题干所问对象和范围，标原文入口 '+review['locator_quote']+'，读取所引完整断言。',
        evidence=evidence, decision_rule_check='所标区域对应题干对象；定位只产出待核证据，不独立定案。',
        stop_rule_check='定位只产出待核证据位置，不把同词和同数字当答案。', stop_applied=False,
        reviewer=review['reviewer'], review_status='reviewed',
        output=dict(kind='located_evidence', spans=evidence))]
    for index, c in enumerate(review['candidate_checks']):
        q['action_executions'].append(dict(execution_id='check-'+c['candidate'], method_id='R01',
            method_version=registry.methods['R01']['version'], role='decider', input_artifact_ids=['locate'],
            concrete_action=c['claim']+' 拆A+B，只对新增断言逐项回文求证。',
            evidence=evidence, decision_rule_check=c['decision'], stop_rule_check=c['stop'],
            stop_applied=False, reviewer=review['reviewer'], review_status='reviewed',
            output=dict(kind='candidate_decision', candidate=c['candidate'], effect=c['effect'], relation_index=index)))
    analyzed = QuestionAnalyzer(registry).analyze(q)
    result = dict(schema_version='1.0.0', exam_id=exam_id, pass_='host_reviewed_blind',
        mechanical_prediction_sha256=sha(mechanical_bytes), review_sha256=sha(review_bytes),
        source_sha256=blank['source_sha256'], source_bindings={q['question_id']:bindings[q['question_id']]},
        original_input=original, reviewed_input=q, prediction=analyzed,
        engine_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        semantic_review_status='pending_independent_review', limitations=review['limitations'])
    result['pass'] = result.pop('pass_')
    freeze_json(directory/'predictions'/exam_id/'reviewed-blind.json', result)
    return dict(exam_id=exam_id, question_id=q['question_id'], prediction_frozen=True,
        answer=analyzed['answer'], content_eligible=analyzed['content_eligible'],
        execution_states=[s['state'] for s in analyzed['execution_trace']], independent_review='pending')


def reveal(dataset, exam_id):
    directory = Path(dataset)
    prediction_bytes = (directory/'predictions'/exam_id/'blind.json').read_bytes()
    prediction = json.loads(prediction_bytes)
    blank = json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    paper, bindings = parse(blank)
    if prediction['pass'] != 'blind' or prediction['inputs'] != paper:
        raise ValueError('Blind freeze missing or mismatched; do not read reference answers')
    reviewed_path = directory/'predictions'/exam_id/'reviewed-blind.json'
    reviewed_bytes = reviewed_path.read_bytes() if reviewed_path.exists() else None
    reviewed = json.loads(reviewed_bytes) if reviewed_bytes else None
    if reviewed and (reviewed['pass'] != 'host_reviewed_blind'
                    or reviewed['mechanical_prediction_sha256'] != sha(prediction_bytes)):
        raise ValueError('Host review does not bind current pre-reveal freeze')
    source = json.loads((directory/'sources'/exam_id/'reveal.json').read_text(encoding='utf-8'))
    if sha(source['text'].encode('utf-8')) != source['text_sha256']:
        raise ValueError('Reveal extraction changed')
    lines = source['paragraphs']
    start = next(i for i,s in enumerate(lines) if s.startswith('第二') and '阅读' in s)
    objective_numbers = {bindings[q['question_id']]['printed_question_number']
                         for q in paper['questions'] if q['question_type'] not in {'应用文','读后续写'}}
    keys, explanations, issues = {}, {}, []
    for i in range(start, len(lines)):
        line = lines[i]
        if line.startswith('【答案】'):
            end = next((j for j in range(i+1,len(lines)) if lines[j].startswith('【解析】')),len(lines))
            block = '\n'.join([line.removeprefix('【答案】'), *lines[i+1:end]])
            if not re.match(r'^\s*\d+(?:[.．]|\s)', block):
                continue  # prose writing samples are not numbered answer keys
            labels = list(re.finditer(r'(?<!\d)(\d+)(?:[.．]\s*|\s+)', block))
            for j,label in enumerate(labels):
                number = int(label[1])
                if number not in objective_numbers:
                    continue
                answer = block[label.end():labels[j+1].start() if j+1<len(labels) else len(block)].strip()
                if number in keys and keys[number] != answer:
                    raise ValueError('Conflicting printed answer labels')
                keys[number] = answer
        detail = re.fullmatch(r'【?(\d+)题详解】', line)
        if detail and int(detail[1]) in objective_numbers:
            number = int(detail[1])
            if i+1 >= len(lines) or not lines[i+1].strip():
                raise ValueError('Empty printed explanation')
            explanations[number] = dict(text=lines[i+1], source_paragraph_index=i+1, printed_marker=line)
            if not line.startswith('【'):
                issues.append(dict(type='malformed_reference_explanation_marker', printed_question_number=number,
                                   status='preserved_not_corrected'))
    if set(keys) != objective_numbers or set(explanations) != objective_numbers:
        raise ValueError('Answer/explanation mapping incomplete; no inferred completion')
    rows = []
    for analysis in prediction['predictions']:
        qid = analysis['question_id']; number = bindings[qid]['printed_question_number']
        writing = number not in objective_numbers
        answer = None if writing else keys[number]
        host = reviewed['prediction'] if reviewed and reviewed['prediction']['question_id'] == qid else None
        host_match = None if host is None or host['answer'] is None or writing else host['answer'] in answer.split('##')
        rows.append(dict(question_id=qid, printed_question_number=number, official_answer=None,
            reference_answer=answer, reference_explanation=None if writing else explanations[number],
            answer_authority='third_party_compilation_not_official', mechanical_analysis=analysis,
            host_reviewed_analysis=host, mechanical_answer_match=None if writing or analysis['answer'] is None else analysis['answer'] in answer.split('##'),
            host_reviewed_answer_match=host_match, trigger_valid=None, evidence_valid=None,
            role_valid=None, boundary_valid=None, unresolved_correctly=None,
            semantic_review_status='pending_independent_review', failure_category=None,
            writing_evaluation='constraint_review_pending_no_exact_match' if writing else None))
    host_answered = [row for row in rows if row['host_reviewed_answer_match'] is not None]
    report = dict(schema_version='1.0.0', exam_id=exam_id, status='PARTIAL',
        prediction_sha256=sha(prediction_bytes), reviewed_prediction_sha256=sha(reviewed_bytes) if reviewed_bytes else None,
        blank_source_sha256=blank['source_sha256'], reveal_source_sha256=source['source_sha256'],
        written_questions=len(rows), objective_count=len(objective_numbers),
        mechanical_answered_count=sum(x['answer'] is not None for x in prediction['predictions']),
        mechanical_unresolved_count=sum(x['answer'] is None for x in prediction['predictions'][:45]),
        host_reviewed_answered_count=len(host_answered),
        host_reviewed_match_count=sum(row['host_reviewed_answer_match'] is True for row in host_answered),
        independent_semantic_accuracy=None, safe_abstention=None, evidence_failure=None,
        trigger_failure=None, boundary_failure=None, new_real_case_count=0, filled_case_slots=0,
        question_type_counts=prediction['question_type_counts'], method_case_contributions=[],
        source_issue=issues+[dict(type='embedded_images_and_table_layout', status='pending_source_review')],
        limitations=['No learner records or independent human semantic certification.',
            'Host-reviewed agreement is separate from mechanical output, not solver-wide accuracy.',
            'Writing sample remains in source reveal; no unique-answer matching or score invention.',
            'No methods upgraded and no automatic Case registration.'], questions=rows)
    freeze_json(directory/'results'/exam_id/'reveal.json', report)
    summary = {k:v for k,v in report.items() if k not in {'questions','limitations'}}
    summary['copyright_scope'] = 'No source text, option text, answer or explanation in this summary'
    freeze_json(directory/'results'/exam_id/'contribution-summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exam_id', choices=EXAMS)
    parser.add_argument('--dataset', default=str(ROOT/'local-data/exams-2020-2025'))
    parser.add_argument('--review', help='Local answer-isolated host review JSON; separate freeze')
    parser.add_argument('--reveal', action='store_true')
    args = parser.parse_args()
    if args.review and args.reveal:
        parser.error('Review freeze and reveal are separate passes')
    result = reveal(args.dataset, args.exam_id) if args.reveal else reviewed_blind(args.dataset, args.exam_id, args.review) if args.review else blind(args.dataset, args.exam_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
