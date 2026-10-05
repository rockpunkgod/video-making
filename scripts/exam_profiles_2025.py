"""Audited 2025 written-paper profiles; copyrighted text stays local/ignored.

Layout validation is not OCR, source-rights clearance or semantic certification.
Printed numbering is preserved, including II's restart after listening.
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
from scripts.run_exam_regression import NUMBER, MARKER


def choices(lines, letters='ABCD'):
    """Read printed labels, also accepting a source label with a missing dot.

    Tabs/newlines are required before subsequent undotted labels. This avoids
    treating a standalone English A in option prose as another choice.
    """
    text='\n'.join(lines).strip()
    labels=list(re.finditer(r'(?:^|[\t\n]|(?<=\s))([A-G])[.．](?=\s)|(?:^|[\t\n])\s*([A-G])(?=\s)',text))
    found=''.join(x[1] or x[2] for x in labels)
    if found!=letters:
        raise ValueError('Option labels incomplete/ambiguous; no answer-assisted repair')
    return {x[1] or x[2]:text[x.end():labels[i+1].start() if i+1<len(labels) else len(text)].strip()
            for i,x in enumerate(labels)}


def parse(source):
    exam=source.get('exam_id')
    if exam not in {'gaokao-2025-I','gaokao-2025-II'} or source.get('source_kind')!='blank':
        raise ValueError('Unsupported 2025 blank source')
    if source['automatic_numbered_paragraphs']:
        raise ValueError('Automatic numbering requires source review')
    if sha(source['text'].encode())!=source['text_sha256'] or '\n'.join(source['paragraphs'])!=source['text']:
        raise ValueError('Frozen extraction changed')
    lines=source['paragraphs']; offset=20 if exam.endswith('-I') else 0
    def at(prefix,start=0):
        return next((i for i in range(start,len(lines)) if lines[i].startswith(prefix)),None)
    reading=at('第二部分'); seven=at('第二节',reading+1) if reading is not None else None
    language=at('第三部分',seven+1) if seven is not None else None
    grammar=at('第二节',language+1) if language is not None else None
    writing=at('第四部分',grammar+1) if grammar is not None else None
    continuation=at('第二节',writing+1) if writing is not None else None
    if None in [reading,seven,language,grammar,writing,continuation]:
        raise ValueError('Written sections incomplete')
    questions=[]; bindings={}
    def add(number,kind,stem,passage='',options=None,**extra):
        q={'question_id':exam+'-q'+str(number),'question_type':kind,'stem':stem,'passage':passage,**extra}
        if options is not None: q['options']=options
        validate_schema('question-input',q); questions.append(q)
        bindings[q['question_id']]={'printed_question_number':number,'section':'written',
            'source_sha256':source['source_sha256'],'extraction_sha256':source['text_sha256'],
            'input_sha256':sha(json.dumps(q,ensure_ascii=False,sort_keys=True).encode())}
    heads=[i for i in range(reading,seven) if lines[i] in list('ABCD')]
    if [lines[i] for i in heads]!=list('ABCD'): raise ValueError('Reading passages A-D incomplete')
    for index,start in enumerate(heads):
        end=heads[index+1] if index+1<len(heads) else seven
        starts=[i for i in range(start+1,end) if NUMBER.match(lines[i])]
        if not starts: raise ValueError('Missing reading questions')
        passage='\n'.join(lines[start+1:starts[0]])
        for j,i in enumerate(starts):
            match=NUMBER.match(lines[i]); stop=starts[j+1] if j+1<len(starts) else end
            add(int(match[1]),'阅读理解',match[2],passage,choices(lines[i+1:stop]))
    seven_options=at('A.',seven+1)
    if seven_options is None or seven_options>=language: raise ValueError('Missing seven-five options')
    passage='\n'.join(lines[seven+2:seven_options]); options=choices(lines[seven_options:language],'ABCDEFG')
    blanks=[int(m[1]) for m in MARKER.finditer(passage)]
    if blanks!=list(range(offset+16,offset+21)): raise ValueError('Seven-five blank numbers incomplete')
    for number in blanks: add(number,'七选五',lines[seven+1],passage,options,task_type='original_blank_'+str(number))
    starts=[i for i in range(language,grammar) if NUMBER.match(lines[i])]
    if len(starts)!=15: raise ValueError('Cloze option rows incomplete')
    passage='\n'.join(lines[language+3:starts[0]])
    if [int(m[1]) for m in MARKER.finditer(passage)]!=list(range(offset+21,offset+36)):
        raise ValueError('Cloze blank numbers incomplete')
    for j,i in enumerate(starts):
        m=NUMBER.match(lines[i]); end=starts[j+1] if j+1<len(starts) else grammar
        add(int(m[1]),'完形填空',lines[language+2],passage,choices([m[2],*lines[i+1:end]]),task_type='original_blank_'+m[1])
    passage='\n'.join(lines[grammar+2:writing]); blanks=list(MARKER.finditer(passage))
    if [int(m[1]) for m in blanks]!=list(range(offset+36,offset+46)): raise ValueError('Grammar blank numbers incomplete')
    for m in blanks:
        hint=re.match(r'\s*\(([A-Za-z]+)\)',passage[m.end():]); extra={'given_word':hint[1]} if hint else {}
        add(int(m[1]),'语法填空',lines[grammar+1],passage,task_type='original_blank_'+m[1],**extra)
    app=at(str(offset+46)+'.',writing+1); story=at(str(offset+47)+'.',continuation+1)
    if app is None or story is None: raise ValueError('Printed writing tasks incomplete')
    add(offset+46,'应用文','\n'.join(lines[app:continuation]),task_type='source_task_constraints')
    notes=at('注意',story+1)
    if notes is None: raise ValueError('Missing continuation constraints')
    starters=[i for i in range(notes+1,len(lines)-1) if lines[i] and lines[i+1].startswith('___') and not lines[i].startswith('___')]
    if len(starters)!=2: raise ValueError('Continuation starters incomplete/ambiguous')
    add(offset+47,'读后续写','\n'.join([lines[story],*lines[notes:starters[0]]]),
        '\n'.join(lines[story+1:notes]),continuation_starters=[lines[i] for i in starters],task_type='source_task_constraints')
    if [bindings[q['question_id']]['printed_question_number'] for q in questions]!=list(range(offset+1,offset+48)):
        raise ValueError('Written numbering incomplete or shifted')
    return {'paper_id':exam,'questions':questions},bindings


def blank(dataset,exam_id):
    return json.loads((Path(dataset)/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))


def blind(dataset,exam_id):
    source=blank(dataset,exam_id); paper,bindings=parse(source)
    r=Registry(); r.validate(); a=QuestionAnalyzer(r)
    result={'schema_version':'1.0.0','exam_id':exam_id,'pass':'blind','source_kind':'blank',
        'source_sha256':source['source_sha256'],'engine_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'method_versions':{mid:m['version'] for mid,m in r.methods.items()},'inputs':paper,'source_bindings':bindings,
        'predictions':[a.analyze(deepcopy(q)) for q in paper['questions']],
        'paper_analysis':PaperAnalyzer(a).analyze(deepcopy(paper)),
        'question_type_counts':dict(Counter(q['question_type'] for q in paper['questions'])),
        'limitations':['Embedded image content not certified; extracted text is not complete visual inspection.',
            'No semantic provider; answerless mechanical results are not safe-abstention or solving accuracy.',
            'Listening is outside six written-type engine scope. No student writing draft or learner results.']}
    freeze_json(Path(dataset)/'predictions'/exam_id/'blind.json',result)
    return {'exam_id':exam_id,'written_questions':47,'objective_questions':45,'engine_answers':sum(x['answer'] is not None for x in result['predictions']),
        'prediction_frozen':True,'semantic_review':'pending','question_type_counts':result['question_type_counts']}


def reviewed_blind(dataset,exam_id,annotations_path):
    """Consume separate pre-reveal host annotations without modifying blind.json."""
    root=Path(dataset); prediction=json.loads((root/'predictions'/exam_id/'blind.json').read_text(encoding='utf-8'))
    if any((root/'results'/exam_id).glob('reveal*.json')): raise ValueError('Reveal already frozen; cannot label new review blind')
    paper,bindings=parse(blank(dataset,exam_id))
    if prediction['inputs']!=paper: raise ValueError('Frozen blind inputs differ')
    raw=Path(annotations_path).read_bytes(); payload=json.loads(raw)
    if payload.get('review_timing')!='pre_reveal': raise ValueError('Explicit pre-reveal declaration required')
    original={q['question_id']:q for q in paper['questions']}; results=[]
    r=Registry(); r.validate()
    for annotation in payload['questions']:
        q=deepcopy(original[annotation['question_id']]); permitted={'task_type','observations','relations','action_executions','lesson_review'}
        if set(annotation)-permitted-{'question_id'}: raise ValueError('Annotation may not replace original question material')
        q.update({k:v for k,v in annotation.items() if k in permitted})
        results.append({'input':q,'analysis':QuestionAnalyzer(r).analyze(q),'source_binding':bindings[q['question_id']]})
    result={'schema_version':'1.0.0','exam_id':exam_id,'pass':'host_reviewed_blind','source_kind':'blank',
        'review_timing':'pre_reveal','reviewer_kind':'codex_host_not_independent_human','annotation_sha256':sha(raw),
        'mechanical_prediction_sha256':sha((root/'predictions'/exam_id/'blind.json').read_bytes()),'questions':results,
        'limitations':['Host semantic assertions are not authenticated independent human review.',
            'A correct answer alone is not validated method, real learner effect or legal Case promotion.']}
    freeze_json(root/'predictions'/exam_id/'reviewed-blind.json',result)
    return {'exam_id':exam_id,'host_reviewed_questions':len(results),'host_engine_answers':sum(x['analysis']['answer'] is not None for x in results)}


def explanation_stop(lines,start,wanted):
    """An explanation may itself begin with its printed question number."""
    return next((j for j in range(start+1,len(lines)) if re.match(r'【\d+题详解】|【答案】',lines[j])
                 or (NUMBER.match(lines[j]) and int(NUMBER.match(lines[j])[1]) not in wanted)),len(lines))


def reveal(dataset,exam_id):
    """Answer documents are opened only after an original blank prediction exists."""
    root=Path(dataset); raw=(root/'predictions'/exam_id/'blind.json').read_bytes(); prediction=json.loads(raw)
    paper,_=parse(blank(dataset,exam_id))
    if prediction['pass']!='blind' or prediction['inputs']!=paper: raise ValueError('Frozen blind input mismatch')
    source=json.loads((root/'sources'/exam_id/'reveal.json').read_text(encoding='utf-8'))
    if sha(source['text'].encode())!=source['text_sha256']: raise ValueError('Reveal extraction changed')
    # Restrict answer/explanation mapping to written section: II restarts at 1.
    lines=source['paragraphs']; start=next((i for i,t in enumerate(lines) if t.startswith('第二部分')),None)
    if start is None: raise ValueError('Missing written reveal section')
    offset=20 if exam_id.endswith('-I') else 0; wanted=set(range(offset+1,offset+46)); keys={}; details={}; conflicts=[]
    for i in range(start,len(lines)):
        t=lines[i]
        if t.startswith('【答案】'):
            end=next((j for j in range(i+1,len(lines)) if lines[j].startswith(('【解析】','【详解】'))),len(lines))
            block='\n'.join([t.removeprefix('【答案】'),*lines[i+1:end]])
            labels=list(re.finditer(r'(?<!\d)(\d+)[.．\s]+',block))
            for j,label in enumerate(labels):
                n=int(label[1]); value=block[label.end():labels[j+1].start() if j+1<len(labels) else len(block)].strip()
                if n not in wanted: continue
                if n in keys and keys[n]!=value: conflicts.append({'question_number':n,'type':'conflicting_reference_labels'})
                else: keys[n]=value
        m=re.fullmatch(r'【(\d+)题详解】',t)
        if m and int(m[1]) in wanted:
            stop=explanation_stop(lines,i,wanted)
            details[int(m[1])]='\n'.join(lines[i+1:stop]).strip()
    missing=sorted(wanted-set(keys)); missing_details=sorted(wanted-{n for n,t in details.items() if t})
    rows=[]
    for analysis in prediction['predictions']:
        n=prediction['source_bindings'][analysis['question_id']]['printed_question_number']; reference=keys.get(n)
        rows.append({'question_id':analysis['question_id'],'printed_question_number':n,'engine_answer':analysis['answer'],
            'reference_answer':reference,'official_answer':None,'reference_explanation':details.get(n),
            'answer_authority':'third_party_compilation_not_official','answer_match':None if reference is None or analysis['answer'] is None else analysis['answer'] in reference.split('##'),
            'semantic_review_status':'pending_independent_review'})
    host_path=root/'predictions'/exam_id/'reviewed-blind.json'; host=[]
    if host_path.exists():
        host_data=json.loads(host_path.read_text(encoding='utf-8'))
        for item in host_data['questions']:
            n=item['source_binding']['printed_question_number']; answer=item['analysis']['answer']; reference=keys.get(n)
            host.append({'question_id':item['analysis']['question_id'],'engine_answer':answer,'reference_answer':reference,
                'answer_match':None if answer is None or reference is None else answer in reference.split('##'),
                'reviewer_kind':'codex_host_not_independent_human','review_timing':'pre_reveal',
                'reviewed_prediction_sha256':sha(host_path.read_bytes()),'semantic_review_status':'pending_independent_review'})
    report={'schema_version':'1.1.0','exam_id':exam_id,'status':'PARTIAL','prediction_sha256':sha(raw),
        'blank_source_sha256':prediction['source_sha256'],'reveal_source_sha256':source['source_sha256'],
        'new_question_count':47,'objective_count':45,'question_type_counts':prediction['question_type_counts'],
        'answered_count':sum(x['engine_answer'] is not None for x in rows[:45]),'unresolved_count':sum(x['engine_answer'] is None for x in rows[:45]),
        'safe_abstention':None,'evidence_failure':None,'method_trigger_failure':None,'boundary_failure':None,'blind_answer_match':None,
        'missing_reference_numbers':missing,'missing_explanation_numbers':missing_details,'source_issue':conflicts,
        'new_real_case_count':0,'filled_case_slots':0,'method_case_contributions':[],
        'case_candidates':prediction['paper_analysis']['case_candidates'],'demo_candidates':prediction['paper_analysis']['recommendations'],
        'questions':rows,'host_reviewed_blind':host,
        'limitations':['Mechanical and host-reviewed blind runs are separate; no automatic/human-independent accuracy claim.',
            'Reference authority, embedded images, case semantics and actual learners remain unverified. No method upgrades.']}
    # Retain the initial frozen reveal snapshot when the extraction profile is
    # corrected. Never change the original blank predictions or source bytes.
    freeze_json(root/'results'/exam_id/'reveal-v1.1.json',report)
    summary={k:v for k,v in report.items() if k not in {'questions','case_candidates','demo_candidates','host_reviewed_blind'}}
    summary['host_reviewed_question_count']=len(host); summary['host_reviewed_answered_count']=sum(x['engine_answer'] is not None for x in host)
    summary['host_reviewed_reference_match_count']=sum(x['answer_match'] is True for x in host)
    freeze_json(root/'results'/exam_id/'contribution-summary-v1.1.json',summary)
    return summary


def main():
    p=argparse.ArgumentParser(); p.add_argument('exam_id',choices=['gaokao-2025-I','gaokao-2025-II']); p.add_argument('--phase',choices=['blind','host','reveal'],default='blind')
    p.add_argument('--annotations'); p.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025')); args=p.parse_args()
    result=blind(args.dataset,args.exam_id) if args.phase=='blind' else reviewed_blind(args.dataset,args.exam_id,args.annotations) if args.phase=='host' else reveal(args.dataset,args.exam_id)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
