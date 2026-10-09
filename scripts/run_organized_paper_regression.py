"""Run the unchanged engine on a paper's source-only structural projection.

This is an initial mechanical smoke pass, not an English solver, an independent
unseen-paper blind evaluation or proof that an entire paper was segmented.
Every paper still requires its own actual subagent source/semantic review.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re

from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry, ROOT
from scripts.ingest_exam_sources import freeze_json, sha

KINDS={'single_choice':'未知','cloze':'完形填空','seven_five':'七选五','grammar_fill':'语法填空'}

def projection(value):
    # The parser records any removed printed pagination lines separately.
    return value['text']

def admission_issue(entry, document_text):
    marker=entry.get('blank_location')
    if not marker: return None
    start=marker['start']; end=marker['end']
    a=document_text.rfind('\n',0,start)+1
    b=document_text.find('\n',end)
    line=document_text[a:b if b>=0 else len(document_text)]
    if re.search(r'阅读下面|空白处填入|每小题|满分|共\s*\d+\s*小题|第\s*\d+\s*页.*共\s*\d+\s*页',line):
        return 'number_in_instruction_or_pagination_not_a_verified_blank'
    if not re.search(r'[_＿]',marker['quote']) and not re.fullmatch(r'[（(]\s*\d+[）)]',marker['quote'].strip()):
        # Space-delimited digits can be a price, count or damaged printed gap.
        # Retain them in the original dossier for the paper agent, not in the
        # supposedly unambiguous initial analyzer subset.
        return 'space_delimited_number_requires_independent_blank_confirmation'
    return None

def convert(entry, document_text):
    kind=entry['question_type']
    if kind not in KINDS: raise ValueError('Unsupported structural projection')
    q={'question_id':entry['question_id'],'question_type':KINDS[kind],
       'stem':projection(entry['question']), 'passage':projection(entry['shared_context']),
       'task_type':'source_intake_projection_'+kind}
    if entry.get('blank_location'):
        q['stem']=entry['blank_location']['quote']
        if kind=='grammar_fill':
            # Copy an immediately printed prompt word; never infer one from
            # grammar, an answer, or the original part of speech.
            end=entry['blank_location']['end']
            hint=re.match(r'[_＿]*\s*[（(]([A-Za-z]+(?:[ -][A-Za-z]+){0,2})[）)]',document_text[end:])
            if hint: q['given_word']=hint[1]
    if entry['options']:
        q['options']={}
        for opt in entry['options']:
            raw=projection(opt['projection'])
            prefix=opt['label']+opt['printed_delimiter']
            if not raw.startswith(prefix): raise ValueError('Unbound option delimiter')
            body=raw[len(prefix):].strip()
            if not body: raise ValueError('Empty printed option')
            q['options'][opt['label']]=body
    # Single-choice legacy grammar questions remain UNKNOWN: they are not
    # grammar-fill questions simply because both can involve grammar.
    return q

def runtime_hashes():
    result={}
    for folder in ('core','schemas','method-registry'):
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and path.suffix in {'.py','.json','.yaml'}:
                result[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    return result

def run_paper(bank_root, source, output_root, analyzer=None, fingerprints=None):
    bank_root=Path(bank_root); output_root=Path(output_root)
    input_path=bank_root/source['question_input_file']
    raw=input_path.read_bytes(); record=json.loads(raw)
    if record['source_sha256'] != source['source_sha256'] or record['paper_id'] != source['paper_id']:
        raise ValueError('Wrong paper projection/source binding')
    dossier_path=bank_root/source['case_file']
    dossier=json.loads(dossier_path.read_text(encoding='utf-8'))
    if dossier['source_sha256'] != source['source_sha256']:
        raise ValueError('Wrong original-text dossier')
    admitted=[]; excluded=[]
    for entry in record['question_inputs']:
        issue=admission_issue(entry,dossier['document_text'])
        if issue: excluded.append({'question_id':entry['question_id'],'reason':issue,'source':entry['blank_location']})
        else: admitted.append(entry)
    inputs={'paper_id':source['paper_id'],'questions':[convert(e,dossier['document_text']) for e in admitted]}
    analyzer=analyzer or QuestionAnalyzer()
    predictions=[analyzer.analyze(deepcopy(q)) for q in inputs['questions']]
    paper=PaperAnalyzer(analyzer).analyze(deepcopy(inputs))
    if predictions != paper['questions']: raise ValueError('Question/Paper Analyzer disagree')
    if any(p['answer'] is not None for p in predictions):
        raise ValueError('Unreviewed structural projection unexpectedly declares an answer')
    value={'schema_version':'1.0.0','paper_id':source['paper_id'],'source_sha256':source['source_sha256'],
           'phase':'mechanical_source_only_intake','projection_sha256':sha(raw),
           'dossier_sha256':sha(dossier_path.read_bytes()),
           'intake_script_sha256':sha(Path(__file__).read_bytes()),
           'excluded_structural_candidates':excluded,
           'inputs':inputs,'predictions':predictions,'paper_analysis':paper,
           'runtime_sha256':fingerprints or runtime_hashes(),
           'limits':{'whole_paper_semantic_review':False,'novel_heldout_blind_evaluation':False,
                     'reference_answer_provided_to_engine':False,'source_authenticity':'unverified',
                     'safe_abstention':None,'formal_method_cases_registered':0,
                     'source_coverage':'structural_subset_only; independent paper agent must verify omitted tasks'}}
    dest=output_root/source['paper_id']/'mechanical-intake.json'
    freeze_json(dest,value)
    return {'paper_id':source['paper_id'],'source_sha256':source['source_sha256'],
            'structural_input_count':len(predictions),'question_type_counts':dict(Counter(q['question_type'] for q in inputs['questions'])),
            'engine_answer_count':0,'unresolved_count':len(predictions),'safe_abstention':None,
            'excluded_ambiguous_number_candidates':len(excluded),
            'formal_method_case_count':0,'report':str(dest),'report_sha256':sha(dest.read_bytes()),
            'status':'PARTIAL_STRUCTURAL_SUBSET_NOT_WHOLE_PAPER_ACCEPTANCE'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paper_id',help='Human paper ID, or all for an initial corpus smoke pass')
    parser.add_argument('--bank-root',type=Path,default=ROOT/'local-data/organized-pdfs/case-bank-v4')
    parser.add_argument('--output-root',type=Path,default=ROOT/'local-data/organized-pdfs/mechanical-intake-v4-2')
    args=parser.parse_args(); index=json.loads((args.bank_root/'source-bank.json').read_text(encoding='utf-8'))
    sources=[s for s in index['sources'] if args.paper_id=='all' or s['paper_id']==args.paper_id]
    if not sources: raise ValueError('Unknown paper ID')
    analyzer=QuestionAnalyzer(Registry()); fingerprints=runtime_hashes(); summaries=[]
    for source in sources:
        summary=run_paper(args.bank_root,source,args.output_root,analyzer,fingerprints)
        summaries.append(summary); print(json.dumps(summary,ensure_ascii=False),flush=True)
    if args.paper_id=='all': freeze_json(args.output_root/'summary.json',{'paper_count':len(summaries),'papers':summaries})

if __name__=='__main__': main()
