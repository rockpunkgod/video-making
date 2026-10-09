"""Replay every source binding independently of the corpus parser.

A passing audit proves byte/span accounting only, not authenticity, English
semantics, complete question segmentation or formal method-Case approval.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from scripts.freeze_organized_pdf_pages import selected
from scripts.ingest_exam_sources import freeze_json, sha

def references(value):
    if isinstance(value,dict):
        if {'start','end','quote'} <= value.keys():
            yield value
        for child in value.values(): yield from references(child)
    elif isinstance(value,list):
        for child in value: yield from references(child)

def audit(bank_root, manifest_path):
    bank_root=Path(bank_root).resolve(); manifest_path=Path(manifest_path).resolve()
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    expected={r['sha256']:r for r in manifest['files'] if selected(r,'questions')}
    index=json.loads((bank_root/'source-bank.json').read_text(encoding='utf-8'))
    if {s['source_sha256'] for s in index['sources']} != set(expected):
        raise ValueError('Not all supplied question sources accounted for')
    ids=set(); types=Counter(); spans=0; papers=[]; issues=Counter()
    raw_root=Path(manifest['source_root']).resolve()
    for item in index['sources']:
        location=(bank_root/item['case_file']).resolve()
        if not location.is_relative_to(bank_root): raise ValueError('Unsafe case file path')
        bank=json.loads(location.read_text(encoding='utf-8'))
        source_sha=item['source_sha256']; row=expected[source_sha]
        original=(raw_root/row['relative_path'].replace('\\','/')).resolve()
        if not original.is_relative_to(raw_root) or sha(original.read_bytes()) != source_sha:
            raise ValueError('Original source changed: '+row['relative_path'])
        extraction=json.loads((manifest_path.parent/'pages'/(source_sha+'.json')).read_text(encoding='utf-8'))
        text='\n'.join(p['text'] for p in extraction['pages'])
        if text != bank['document_text'] or sha(text.encode('utf-8')) != bank['document_text_sha256']:
            raise ValueError('Case document differs from untouched page extraction')
        for ref in references(bank):
            if not 0 <= ref['start'] <= ref['end'] <= len(text) or text[ref['start']:ref['end']] != ref['quote']:
                raise ValueError('Source span does not replay: '+bank['paper_id'])
            spans+=1
        for case in bank['cases']:
            qid=case['question_id']
            if qid in ids: raise ValueError('Duplicate question ID: '+qid)
            ids.add(qid); types[case['question_type']]+=1; issues.update(case.get('issues',[]))
            if case['source_sha256'] != source_sha:
                raise ValueError('Cross-source question binding')
            if case.get('formal_method_case') is not False or any(case.get(k) is not None for k in ('method_id','answer','trigger','action')):
                raise ValueError('Structural corpus must not manufacture method/answer credit')
        papers.append({'paper_id':bank['paper_id'],'source_sha256':source_sha,
                       'material_case_count':len(bank['cases']),
                       'no_question_cases':not bool(bank['cases']),
                       'ocr_pending_pages':sum(p['requires_ocr'] for p in extraction['pages']),
                       'case_issue_count':sum(bool(c.get('issues')) for c in bank['cases']),
                       'source_authenticity':'unverified','semantic_review':'pending'})
    lines=(bank_root/'question-cases.jsonl').read_text(encoding='utf-8').splitlines()
    aggregate=[json.loads(line) for line in lines if line]
    if len(aggregate) != len(ids) or {c['question_id'] for c in aggregate} != ids:
        raise ValueError('JSONL differs from per-paper records')
    return {'status':'PASS_SOURCE_SPANS_ONLY','source_files_accounted_for':len(papers),
            'material_case_records':len(ids),'source_spans_replayed':spans,
            'case_type_counts':dict(types),'case_issue_counts':dict(issues),
            'no_question_sources':sum(p['no_question_cases'] for p in papers),
            'ocr_pending_pages':sum(p['ocr_pending_pages'] for p in papers),
            'formal_method_case_count':0,'semantic_correctness':None,
            'all_questions_segmented':None,'authenticity_verified':False,
            'learner_effect_validated':False,'papers':papers}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bank_root',type=Path)
    p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[1]/'local-data/organized-pdfs/source-manifest.json')
    p.add_argument('--output',type=Path)
    args=p.parse_args(); result=audit(args.bank_root,args.manifest)
    if args.output: freeze_json(args.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('papers','case_issue_counts')},ensure_ascii=False))

if __name__=='__main__': main()
