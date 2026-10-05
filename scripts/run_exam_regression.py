"""Answer-isolated local exam regression. No method edits or case promotions.

The initial audited extraction profile is 2024 I. Unsupported layouts are
reported, never repaired from the answer document. Full text stays ignored.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.registry import Registry,validate_schema
from scripts.ingest_exam_sources import freeze_json,sha,ROOT

NUMBER=re.compile(r'^\s*(\d+)[.．\s]+(.*)$')
MARKER=re.compile(r'_{2,}(\d+)_{2,}')

def choices(lines,letters='ABCD'):
    text='\n'.join(lines)
    labels=list(re.finditer(r'([A-G])[.．]',text))
    if ''.join(x[1] for x in labels)!=letters:
        raise ValueError('Option labels incomplete/ambiguous; no answer-assisted repair')
    return {x[1]:text[x.end():labels[i+1].start() if i+1<len(labels) else len(text)].strip()
            for i,x in enumerate(labels)}

def parse_2024_i(source):
    if source['exam_id']!='gaokao-2024-I' or source['source_kind']!='blank':
        raise ValueError('No audited extraction profile for this source yet')
    if source['automatic_numbered_paragraphs']:
        raise ValueError('Automatic numbering requires source review')
    if '\n'.join(source['paragraphs'])!=source['text']:
        raise ValueError('Paragraph extraction differs from frozen text')
    lines=source['paragraphs']
    def at(prefix,start=0):
        found=[i for i in range(start,len(lines)) if lines[i].startswith(prefix)]
        if not found: raise ValueError('Missing section: '+prefix)
        return found[0]
    reading=at('第二部分'); seven=at('第二节',reading+1)
    language=at('第三部分',seven+1); grammar=at('第二节',language+1)
    writing=at('第四部分',grammar+1); continuation=at('第二节',writing+1)
    questions=[]; source_bindings={}
    def add(number,kind,stem,passage='',options=None,**extra):
        q={'question_id':source['exam_id']+'-q'+str(number),'question_type':kind,
           'stem':stem,'passage':passage,**extra}
        if options is not None: q['options']=options
        validate_schema('question-input',q); questions.append(q)
        source_bindings[q['question_id']]={'printed_question_number':number,'source_sha256':source['source_sha256'],
            'extraction_sha256':source['text_sha256'],'input_sha256':sha(json.dumps(q,ensure_ascii=False,sort_keys=True).encode())}
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
    seven_passage='\n'.join(lines[seven+2:seven_options])
    seven_choices=choices(lines[seven_options:language],'ABCDEFG')
    blanks=[int(m[1]) for m in MARKER.finditer(seven_passage)]
    if blanks!=list(range(36,41)): raise ValueError('Seven-five blank numbers incomplete')
    for number in blanks:
        add(number,'七选五',lines[seven+1],seven_passage,seven_choices,task_type='original_blank_'+str(number))
    cloze_starts=[i for i in range(language,grammar) if NUMBER.match(lines[i])]
    if len(cloze_starts)!=15: raise ValueError('Cloze option rows incomplete')
    cloze_passage='\n'.join(lines[language+3:cloze_starts[0]])
    if [int(m[1]) for m in MARKER.finditer(cloze_passage)]!=list(range(41,56)):
        raise ValueError('Cloze blank numbers incomplete')
    for j,i in enumerate(cloze_starts):
        m=NUMBER.match(lines[i]); end=cloze_starts[j+1] if j+1<len(cloze_starts) else grammar
        add(int(m[1]),'完形填空',lines[language+2],cloze_passage,choices([m[2],*lines[i+1:end]]),task_type='original_blank_'+m[1])
    grammar_passage='\n'.join(lines[grammar+2:writing])
    grammar_blanks=list(MARKER.finditer(grammar_passage))
    if [int(m[1]) for m in grammar_blanks]!=list(range(56,66)): raise ValueError('Grammar blank numbers incomplete')
    for m in grammar_blanks:
        hint=re.match(r'\s*\(([A-Za-z]+)\)',grammar_passage[m.end():])
        extra={'given_word':hint[1]} if hint else {}
        add(int(m[1]),'语法填空',lines[grammar+1],grammar_passage,task_type='original_blank_'+m[1],**extra)
    app_start=at('66.',writing+1)
    add(66,'应用文','\n'.join(lines[app_start:continuation]),task_type='source_task_constraints')
    story_start=at('67.',continuation+1); notes=at('注意',story_start+1)
    starter_indices=[i for i in range(notes+1,len(lines)-1) if lines[i] and lines[i+1].startswith('___') and not lines[i].startswith('___')]
    if len(starter_indices)!=2: raise ValueError('Continuation starters incomplete/ambiguous')
    add(67,'读后续写','\n'.join([lines[story_start],*lines[notes:starter_indices[0]]]),
        '\n'.join(lines[story_start+1:notes]),continuation_starters=[lines[i] for i in starter_indices],task_type='source_task_constraints')
    numbers=[source_bindings[q['question_id']]['printed_question_number'] for q in questions]
    if numbers!=list(range(21,68)): raise ValueError('Written question numbering is not continuous')
    return {'paper_id':source['exam_id'],'questions':questions},source_bindings

def blind(dataset,exam_id):
    directory=Path(dataset); path=directory/'sources'/exam_id/'blank.json'
    source=json.loads(path.read_text(encoding='utf-8'))
    if sha(source['text'].encode())!=source['text_sha256']: raise ValueError('Frozen extraction changed')
    paper,bindings=parse_2024_i(source)
    r=Registry(); r.validate(); analyzer=QuestionAnalyzer(r)
    # Only blank inputs reach the Analyzer. No reveal file is opened here.
    results=[analyzer.analyze(deepcopy(q)) for q in paper['questions']]
    result={'schema_version':'1.0.0','exam_id':exam_id,'pass':'blind',
        'source_kind':'blank','source_sha256':source['source_sha256'],
        'engine_commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'method_versions':{mid:m['version'] for mid,m in r.methods.items()},
        'inputs':paper,'source_bindings':bindings,'predictions':results,
        'paper_analysis':PaperAnalyzer(analyzer).analyze(deepcopy(paper)),
        'question_type_counts':dict(Counter(q['question_type'] for q in paper['questions'])),
        'limitations':['Text extraction has not certified embedded image transcription or rights.',
            'No review provider; semantic decisions are unavailable, abstention is not solving accuracy.',
            'Writing reference text is not an exact-match answer; no student draft was supplied.']}
    freeze_json(directory/'predictions'/exam_id/'blind.json',result)
    return {'exam_id':exam_id,'written_questions':len(results),'objective_questions':45,
        'engine_answers':sum(x['answer'] is not None for x in results),
        'prediction_frozen':True,'semantic_review':'pending','question_type_counts':result['question_type_counts']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('exam_id'); p.add_argument('--reveal',action='store_true'); p.add_argument('--phase',choices=['blind','host','reveal'],default='blind'); p.add_argument('--review'); p.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025'))
    args=p.parse_args()
    if args.reveal and args.phase=='host': raise ValueError('Host review and reveal cannot be combined')
    result=run_phase(args.dataset,args.exam_id,'reveal' if args.reveal else args.phase,args.review)
    print(json.dumps(result,ensure_ascii=False,indent=2))

def run_phase(dataset,exam_id,phase,review=None):
    if exam_id=='gaokao-2024-I':
        if phase=='host': raise ValueError('2024 I explanation already revealed; cannot back-label a blind host review')
        return (reveal if phase=='reveal' else blind)(dataset,exam_id)
    import importlib
    year=exam_id.split('-')[1] if exam_id.startswith('gaokao-') else None
    module='exam_profiles_2020_2021' if year in {'2020','2021'} else 'exam_profiles_2022_2024' if year in {'2022','2023','2024'} else 'exam_profiles_2025' if year=='2025' else None
    if module is None: raise ValueError('No audited extraction profile for '+exam_id)
    profile=importlib.import_module('scripts.'+module)
    if phase=='host':
        if not review: raise ValueError('Host phase requires actual source-bound review input')
        return profile.reviewed_blind(dataset,exam_id,review)
    if phase not in {'blind','reveal'}: raise ValueError('Unknown regression phase')
    return getattr(profile,phase)(dataset,exam_id)

def reveal(dataset,exam_id):
    directory=Path(dataset); prediction_path=directory/'predictions'/exam_id/'blind.json'
    # The frozen file must already exist before explanation text is read.
    prediction_bytes=prediction_path.read_bytes(); prediction=json.loads(prediction_bytes)
    if prediction['pass']!='blind' or prediction['exam_id']!=exam_id: raise ValueError('Wrong frozen prediction')
    blank=json.loads((directory/'sources'/exam_id/'blank.json').read_text(encoding='utf-8'))
    inputs,_=parse_2024_i(blank)
    if inputs!=prediction['inputs']: raise ValueError('Frozen blind inputs differ from original blank source')
    source=json.loads((directory/'sources'/exam_id/'reveal.json').read_text(encoding='utf-8'))
    if sha(source['text'].encode())!=source['text_sha256']: raise ValueError('Reveal extraction changed')
    lines=source['paragraphs']; answer_blocks=[]; explanations={}
    for i,line in enumerate(lines):
        if line.startswith('【答案】'):
            end=next((j for j in range(i+1,len(lines)) if lines[j].startswith('【解析】')),len(lines))
            answer_blocks.append('\n'.join([line.removeprefix('【答案】'),*lines[i+1:end]]))
        detail=re.fullmatch(r'【(\d+)题详解】',line)
        if detail and int(detail[1]) in range(21,66):
            explanations[int(detail[1])]=lines[i+1]
    keys={}
    for block in answer_blocks:
        labels=list(re.finditer(r'(?<!\d)(\d+)[.．\s]+',block))
        for j,label in enumerate(labels):
            number=int(label[1])
            if number not in range(21,66): continue
            answer=block[label.end():labels[j+1].start() if j+1<len(labels) else len(block)].strip()
            if number in keys and keys[number]!=answer: raise ValueError('Conflicting third-party answer labels')
            keys[number]=answer
    if set(keys)!=set(range(21,66)) or set(explanations)!=set(range(21,66)):
        raise ValueError('Answer/explanation mapping incomplete; no inferred completion')
    rows=[]
    for analysis in prediction['predictions']:
        number=prediction['source_bindings'][analysis['question_id']]['printed_question_number']
        writing=number>=66; raw_answer=None if writing else keys[number]
        alternatives=[] if writing else raw_answer.split('##')
        actual=analysis['answer']; matched=None if writing or actual is None else actual in alternatives
        rows.append({'question_id':analysis['question_id'],'official_answer':None,
            'reference_answer':raw_answer,'answer_authority':'third_party_compilation_not_official',
            'reference_explanation':None if writing else explanations[number],
            'analysis':{'matched_methods':analysis['method_matches'],'method_chain':analysis['method_chain'],
                'trigger_evidence':analysis['trigger_evidence'],'evidence_graph':analysis['evidence_graph'],
                'candidate_analysis':analysis['candidate_analysis'],'engine_answer':actual,
                'answer_status':'writing_constraint_review_pending' if writing else 'unresolved' if actual is None else 'match' if matched else 'mismatch'},
            'blind_regression':{'answer_match':matched,'trigger_valid':None,'method_role_valid':None,
                'evidence_valid':None,'boundary_valid':None,'unresolved_correctly':None},
            'semantic_review_status':'pending_review','failure_category':None})
    objective=[x for x in rows if x['reference_answer'] is not None]
    answered=[x for x in objective if x['analysis']['engine_answer'] is not None]
    counts=prediction['question_type_counts']
    coverage=Registry().case_coverage()
    report={'schema_version':'1.0.0','exam_id':exam_id,'status':'PARTIAL',
        'prediction_sha256':sha(prediction_bytes),'blank_source_sha256':blank['source_sha256'],
        'reveal_source_sha256':source['source_sha256'],'new_question_count':len(rows),
        'question_type_counts':counts,'objective_count':len(objective),'answered_count':len(answered),
        'blind_answer_match':None if not answered else sum(x['blind_regression']['answer_match'] for x in answered)/len(answered),
        'matched_count':sum(x['blind_regression']['answer_match'] is True for x in answered),
        'wrong_answer_count':sum(x['blind_regression']['answer_match'] is False for x in answered),
        'unresolved_count':sum(x['analysis']['engine_answer'] is None for x in objective),
        'structurally_safe_abstention_count':sum(x['analysis']['engine_answer'] is None for x in objective),
        'safe_abstention':None,'evidence_failure':None,'method_trigger_failure':None,'boundary_failure':None,
        'new_real_case_count':0,'filled_case_slots':0,'remaining_core_unregistered_slots':coverage['core_unregistered_slot_count'],
        'method_case_contributions':[],'case_candidates':prediction['paper_analysis']['case_candidates'],
        'demo_candidates':prediction['paper_analysis']['recommendations'],
        'source_issue':[{'type':'source_explanation_mismatch','description':'Q58 explanation mentions use sth. to do sth., but the supplied blank sentence has open on warm days; raw explanation preserved, semantic justification pending independent review','status':'pending_review'},
            {'type':'reference_sample_duplicate','description':'Continuation reference extraction visibly repeats paragraphs; original source and raw text preserved, no automatic deduplication','status':'pending_review'}],
        'limitations':['Reference answers are not official answers.',
            'Safe abstention correctness and semantic failure counts remain null until independent review.',
            'Writing samples/scoring remarks remain in the separate frozen reveal document, not unique answers.',
            'No cases registered automatically. Suggestions are not verified triggers/actions.',
            'No learner observations; no maturity or usefulness promotion.'],
        'questions':rows}
    freeze_json(directory/'results'/exam_id/'reveal.json',report)
    return {k:v for k,v in report.items() if k not in {'questions','limitations'}}

if __name__=='__main__': main()
