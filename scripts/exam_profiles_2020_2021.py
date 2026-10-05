"""Audited local-only blank profiles; no answer-assisted source repair.

Full exam text and predictions stay in ignored local-data. 2021 II is rejected
because its extracted blank markers/options are damaged, not repaired from keys.
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

IDS = ('gaokao-2020-I', 'gaokao-2020-II', 'gaokao-2021-I', 'gaokao-2021-II')
NUMBER = re.compile(r'^\s*(\d+)[.．\x01]\s*(.*)$')
MARKER = re.compile(r'_{2,}(\d+)_{2,}')

def choices(lines, expected='ABCD'):
    text = '\n'.join(lines)
    labels = list(re.finditer(r'(?<![A-Za-z])([A-G])[.．\x01]|^\s*([A-G])(?=[ \u00a0\t])', text, re.MULTILINE))
    names = [m[1] or m[2] for m in labels]
    if ''.join(names) != expected:
        raise ValueError('Option labels incomplete or ambiguous; no source repair')
    return {names[i]: text[m.end():labels[i+1].start() if i+1 < len(labels) else len(text)].strip()
            for i, m in enumerate(labels)}

def parse(source):
    if source.get('exam_id') not in IDS or source.get('source_kind') != 'blank':
        raise ValueError('Unsupported blank profile')
    if source.get('automatic_numbered_paragraphs'):
        raise ValueError('Automatic numbering requires original-document review')
    if source.get('embedded_image_count'):
        raise ValueError('Embedded images require independent source review')
    if sha(source['text'].encode()) != source['text_sha256']:
        raise ValueError('Frozen extraction changed')
    if source['exam_id'] == 'gaokao-2021-II':
        raise ValueError('2021 II source_problem: missing G option delimiter and damaged cloze blank markers; original-document review required, no answer-assisted repair')
    lines = source['paragraphs']
    def at(predicate, start=0):
        hits = [i for i in range(start, len(lines)) if predicate(lines[i])]
        if not hits: raise ValueError('Missing source section')
        return hits[0]
    reading = at(lambda x: '阅读' in x and ('部分' in x or x.startswith('阅读（')))
    seven = at(lambda x: x.startswith('第二节'), reading+1)
    language = at(lambda x: '语言运用' in x, seven+1)
    grammar = at(lambda x: x.startswith('第二节'), language+1)
    writing = at(lambda x: '写作' in x and ('部分' in x or x.startswith('写作（')), grammar+1)
    continuation = at(lambda x: x.startswith('第二节'), writing+1)
    questions, bindings = [], {}
    def add(number, kind, stem, passage='', options=None, task_id=None, **extra):
        qid = source['exam_id'] + ('-q'+str(number) if number is not None else '-task-'+task_id)
        q = {'question_id': qid, 'question_type': kind, 'stem': stem, 'passage': passage, **extra}
        if options is not None: q['options'] = options
        validate_schema('question-input', q)
        questions.append(q)
        bindings[qid] = {'printed_question_number': number, 'source_sha256': source['source_sha256'],
            'extraction_sha256': source['text_sha256'],
            'input_sha256': sha(json.dumps(q, ensure_ascii=False, sort_keys=True).encode())}
    heads = [i for i in range(reading, seven) if lines[i].strip() in tuple('ABCD')]
    if [lines[i].strip() for i in heads] != list('ABCD'): raise ValueError('Reading A-D incomplete')
    for n, start in enumerate(heads):
        end = heads[n+1] if n+1 < 4 else seven
        starts = [i for i in range(start+1, end) if NUMBER.match(lines[i])]
        if not starts: raise ValueError('Reading questions missing')
        passage = '\n'.join(lines[start+1:starts[0]])
        for j, i in enumerate(starts):
            m = NUMBER.match(lines[i]); stop = starts[j+1] if j+1 < len(starts) else end
            add(int(m[1]), '阅读理解', m[2], passage, choices(lines[i+1:stop]))
    offset = 0 if source['exam_id'].startswith('gaokao-2020') else 20
    opt = at(lambda x: x.startswith('A.'), seven+1)
    instruction = seven+1 if lines[seven+1].startswith('阅读') else seven
    first = instruction+1
    passage = '\n'.join(lines[first:opt])
    blanks = [int(m[1]) for m in MARKER.finditer(passage)]
    if blanks != list(range(16+offset, 21+offset)): raise ValueError('Seven-five markers incomplete')
    for number in blanks:
        add(number, '七选五', lines[instruction], passage, choices(lines[opt:language], 'ABCDEFG'), task_type='original_blank_'+str(number))
    starts = [i for i in range(language+1, grammar) if NUMBER.match(lines[i])]
    if len(starts) != 15: raise ValueError('Cloze option rows incomplete')
    first = language+2
    if lines[first].startswith('阅读'): first += 1
    passage = '\n'.join(lines[first:starts[0]])
    if [int(m[1]) for m in MARKER.finditer(passage)] != list(range(21+offset, 36+offset)):
        raise ValueError('Cloze markers incomplete')
    for j, i in enumerate(starts):
        m = NUMBER.match(lines[i]); end = starts[j+1] if j+1 < len(starts) else grammar
        add(int(m[1]), '完形填空', lines[language+1], passage, choices([m[2], *lines[i+1:end]]), task_type='original_blank_'+m[1])
    passage = '\n'.join(lines[grammar+2:writing])
    blanks = list(MARKER.finditer(passage))
    if [int(m[1]) for m in blanks] != list(range(36+offset, 46+offset)):
        raise ValueError('Grammar markers incomplete')
    for m in blanks:
        hint = re.match(r'\s*[（(]([A-Za-z]+)[）)]', passage[m.end():])
        add(int(m[1]), '语法填空', lines[grammar+1], passage, task_type='original_blank_'+m[1], **({'given_word':hint[1]} if hint else {}))
    app = writing+2
    printed = NUMBER.match(lines[app])
    add(int(printed[1]) if printed else None, '应用文', '\n'.join(lines[app:continuation]), task_id='application', task_type='source_task_constraints')
    story = continuation+1; printed = NUMBER.match(lines[story])
    notes = at(lambda x: x.startswith('注意'), story+1)
    starters = [i for i in range(notes+1, len(lines)) if lines[i].lstrip().startswith(('When Mrs.', 'With everything ready,', 'As the twins looked', 'The twins carried'))]
    if len(starters) != 2: raise ValueError('Continuation starters incomplete or ambiguous')
    add(int(printed[1]) if printed else None, '读后续写', '\n'.join([lines[story], *lines[notes:starters[0]]]),
        '\n'.join(lines[story+1:notes]), task_id='continuation', continuation_starters=[lines[i] for i in starters], task_type='source_task_constraints')
    nums = [bindings[q['question_id']]['printed_question_number'] for q in questions[:45]]
    if nums != list(range(1+offset, 46+offset)): raise ValueError('Objective source numbering not continuous')
    return {'paper_id': source['exam_id'], 'questions': questions}, bindings

def blind(dataset, exam_id):
    directory = Path(dataset)
    source = json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    paper, bindings = parse(source)
    r = Registry(); r.validate(); analyzer = QuestionAnalyzer(r)
    results = [analyzer.analyze(deepcopy(q)) for q in paper['questions']]
    value = {'schema_version':'1.0.0','exam_id':exam_id,'pass':'blind','source_kind':'blank',
        'source_sha256':source['source_sha256'],'engine_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'method_versions':{k:m['version'] for k,m in r.methods.items()},'inputs':paper,'source_bindings':bindings,
        'predictions':results,'paper_analysis':PaperAnalyzer(analyzer).analyze(deepcopy(paper)),
        'question_type_counts':dict(Counter(q['question_type'] for q in paper['questions'])),
        'limitations':['No semantic provider; unresolved is not independently verified safe abstention.',
            'Legacy Word image count unknown; source formatting/control characters retained, not corrected.',
            'No legal redistribution certification; full text remains local.', 'No student drafts or learner observations.']}
    freeze_json(directory/'predictions'/exam_id/'blind.json', value)
    return {'exam_id':exam_id,'prediction_frozen':True,'new_question_count':len(results),
        'engine_answers':sum(x['answer'] is not None for x in results),'question_type_counts':value['question_type_counts']}

def reveal(dataset, exam_id):
    directory = Path(dataset)
    frozen = (directory/'predictions'/exam_id/'blind.json').read_bytes()
    prediction = json.loads(frozen)
    if prediction['exam_id'] != exam_id or prediction['pass'] != 'blind': raise ValueError('Wrong blind freeze')
    paper, bindings = parse(json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8')))
    if paper != prediction['inputs'] or bindings != prediction['source_bindings']: raise ValueError('Blank inputs differ from frozen prediction')
    source = json.loads((directory/'sources'/exam_id/'reveal.json').read_text(encoding='utf-8'))
    if sha(source['text'].encode()) != source['text_sha256']: raise ValueError('Reveal extraction changed')
    lines=source['paragraphs']; offset=0 if '2020' in exam_id else 20
    keys, explanations={},{}
    for i,line in enumerate(lines):
        # This profile embeds each written key in its explicitly numbered
        # explanation heading, not in the listening answer block.
        inline=re.search(r'(?:^|。)\s*(\d+)\.\s*([A-Za-z]+(?:[/ ][A-Za-z]+)*)。',line) if exam_id=='gaokao-2020-II' else None
        if inline and int(inline[1]) in range(1,46):
            n=int(inline[1]); keys[n]=inline[2].strip(); explanations[n]=line
        header=re.match(r'^[【\[]答案[】\]]',line)
        if header:
            end=next((j for j in range(i+1,len(lines)) if lines[j].startswith(('【','['))),len(lines))
            block='\n'.join([line[header.end():],*lines[i+1:end]])
            labels=list(re.finditer(r'(?<!\d)(\d+)[.．\s]+',block))
            for j,m in enumerate(labels):
                n=int(m[1])
                if n not in range(1+offset,46+offset): continue
                value=block[m.end():labels[j+1].start() if j+1<len(labels) else len(block)].strip()
                if n in keys and keys[n]!=value: raise ValueError('Conflicting reference keys')
                keys[n]=value
        match=re.fullmatch(r'[【\[]\s*(\d+)题详解[】\]]',line)
        if match and int(match[1]) in range(1+offset,46+offset):
            end=next((j for j in range(i+1,len(lines)) if lines[j].startswith(('【','[')) or lines[j].startswith('第二')),len(lines))
            explanations[int(match[1])]='\n'.join(lines[i+1:end])
    expected=set(range(1+offset,46+offset))
    if set(keys)!=expected or set(explanations)!=expected:
        raise ValueError('Incomplete answer/explanation mapping; no inferred completion: keys='+str(sorted(expected-set(keys)))+', explanations='+str(sorted(expected-set(explanations))))
    rows=[]
    for a in prediction['predictions']:
        n=bindings[a['question_id']]['printed_question_number']; writing=a['question_type'] in ('应用文','读后续写')
        answer=None if writing else keys[n]
        rows.append({'question_id':a['question_id'],'official_answer':None,'reference_answer':answer,
            'answer_authority':'third_party_compilation_not_official','reference_explanation':None if writing else explanations[n],
            'analysis':a,'blind_regression':{'answer_match':None if writing or a['answer'] is None else a['answer'] in answer.split('##'),
                'trigger_valid':None,'method_role_valid':None,'evidence_valid':None,'boundary_valid':None,'unresolved_correctly':None},
            'semantic_review_status':'pending_review','failure_category':None})
    summary={'schema_version':'1.0.0','exam_id':exam_id,'status':'PARTIAL','prediction_sha256':sha(frozen),
        'reveal_source_sha256':source['source_sha256'],'new_question_count':len(rows),'objective_count':45,
        'question_type_counts':prediction['question_type_counts'],'answered_count':sum(x['reference_answer'] is not None and x['analysis']['answer'] is not None for x in rows),
        'blind_answer_match':None,'unresolved_count':sum(x['reference_answer'] is not None and x['analysis']['answer'] is None for x in rows),
        'safe_abstention':None,'wrong_answer_count':0,'evidence_failure':None,'method_trigger_failure':None,'boundary_failure':None,
        'new_real_case_count':0,'filled_case_slots':0,'remaining_core_unregistered_slots':Registry().case_coverage()['core_unregistered_slot_count'],
        'method_case_contributions':[],'source_issue':[], 'semantic_review':'pending',
        'writing_exact_match':'not_applicable','student_effect_validation':'not_performed'}
    report={**summary,'questions':rows,'case_candidates':prediction['paper_analysis']['case_candidates'],
        'demo_candidates':prediction['paper_analysis']['recommendations'],
        'limitations':['Reference document is not official; original reference samples/scoring notes preserved separately.',
            'No semantic judgement or student-effect evidence; case slots remain unchanged.']}
    freeze_json(directory/'results'/exam_id/'reveal.json',report)
    summary_path=directory/'results'/exam_id/'contribution-summary.json'
    if summary_path.exists() and json.loads(summary_path.read_text(encoding='utf-8')).get('status')=='SOURCE_REVIEW_REQUIRED':
        summary['source_issue']=[{'type':'option_label_punctuation_absent','description':'Original line-start A/C labels are explicit and uniquely segmented; punctuation remains absent in original material. Earlier conservative rejection preserved, not overwritten.','status':'pending_review'}]
        summary_path=summary_path.with_name('contribution-summary-v2.json')
    freeze_json(summary_path,summary)
    return summary

def audit(dataset, exam_id):
    """Record a rejected source without opening explanations or inventing tasks."""
    directory=Path(dataset)
    source=json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    try:
        paper,_=parse(source)
    except ValueError as error:
        result={'schema_version':'1.0.0','exam_id':exam_id,'status':'SOURCE_REVIEW_REQUIRED',
            'source_sha256':source['source_sha256'],'complete_regression_run':False,
            'new_question_count':0,'objective_count':None,'question_type_counts':{},
            'source_issue':[{'type':'source_problem','description':str(error),'status':'pending_review'}],
            'blind_answer_match':None,'safe_abstention':None,'wrong_answer_count':None,
            'evidence_failure':None,'method_trigger_failure':None,'boundary_failure':None,
            'new_real_case_count':0,'filled_case_slots':0,
            'remaining_core_unregistered_slots':Registry().case_coverage()['core_unregistered_slot_count'],
            'method_case_contributions':[],'semantic_review':'not_run_source_gate_rejected',
            'answer_key_read':False,'limitations':['No inferred option labels, markers or question numbers. Original document review required.']}
        freeze_json(directory/'results'/exam_id/'source-integrity.json',result)
        freeze_json(directory/'results'/exam_id/'contribution-summary.json',result)
        return result
    return {'exam_id':exam_id,'status':'STRUCTURAL_PROFILE_ACCEPTED','question_count':len(paper['questions']),
        'embedded_image_transcription':'not_certified','semantic_review':'pending'}

def reviewed_blind(dataset, exam_id, review_path):
    """Accept explicit source-bound host annotations; cannot certify isolation."""
    directory=Path(dataset)
    if (directory/'results'/exam_id/'reveal.json').exists():
        raise ValueError('Cannot label a new review blind after saved reveal results')
    raw=(directory/'predictions'/exam_id/'blind.json').read_bytes()
    mechanical=json.loads(raw)
    blank=json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    paper,bindings=parse(blank)
    if mechanical['inputs']!=paper or mechanical['source_bindings']!=bindings:
        raise ValueError('Current blank differs from frozen mechanical input')
    review_bytes=Path(review_path).read_bytes(); review=json.loads(review_bytes)
    if review.get('review_stage')!='before_reveal': raise ValueError('Review must be declared before_reveal')
    original=next((q for q in paper['questions'] if q['question_id']==review.get('question_id')),None)
    if original is None: raise ValueError('Review question_id absent from original paper')
    if review.get('original_input_sha256')!=bindings[original['question_id']]['input_sha256']:
        raise ValueError('Review original input hash mismatch')
    allowed={'observations','relations','requested_chain','action_executions'}
    annotations=review.get('annotations')
    if not isinstance(annotations,dict) or set(annotations)-allowed:
        raise ValueError('Annotations cannot replace original question material')
    q=deepcopy(original); q.update(deepcopy(annotations)); validate_schema('question-input',q)
    registry=Registry(); registry.validate(); analysis=QuestionAnalyzer(registry).analyze(q)
    result={'schema_version':'1.0.0','exam_id':exam_id,'pass':'host_reviewed_blind',
        'mechanical_prediction_sha256':sha(raw),'review_sha256':sha(review_bytes),
        'review_kind':'external_host_assertion_not_independent_semantic_certification','question':q,'analysis':analysis,
        'limitations':['No automatic authentication of reviewers or their answer isolation; independent semantic review pending.',
            'Original questions unchanged; no method or case promotion and no learner validation.']}
    freeze_json(directory/'predictions'/exam_id/'reviewed-blind.json',result)
    return {'exam_id':exam_id,'host_reviewed_question_count':1,'host_reviewed_answered_count':int(analysis['answer'] is not None)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('exam_id',choices=IDS)
    modes=p.add_mutually_exclusive_group(); modes.add_argument('--reveal',action='store_true'); modes.add_argument('--audit',action='store_true')
    p.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025'))
    args=p.parse_args(); function=audit if args.audit else reveal if args.reveal else blind
    print(json.dumps(function(args.dataset,args.exam_id),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
