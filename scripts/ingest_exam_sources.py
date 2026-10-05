"""Freeze supplied exam sources locally; never upload copyrighted source text.

Blank and explanation documents remain separate. This is ingestion, not semantic
validation, student-effect evidence or a declaration of redistribution rights.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def sha(data): return hashlib.sha256(data).hexdigest()

def freeze(path,data):
    """Idempotent write; refuse to overwrite frozen material with changed bytes."""
    path=Path(path)
    if path.exists():
        if path.read_bytes()!=data: raise ValueError('Frozen artifact differs: '+str(path))
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream: stream.write(data)

def freeze_json(path,value):
    freeze(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

def extract_docx(path):
    with ZipFile(path) as archive:
        body=ET.fromstring(archive.read('word/document.xml')).find(W+'body')
        paragraphs=[]
        for p in body.iter(W+'p'):
            chunks=[]
            for n in p.iter():
                if n.tag==W+'t': chunks.append(n.text or '')
                elif n.tag==W+'tab': chunks.append('\t')
                elif n.tag in {W+'br',W+'cr'}: chunks.append('\n')
            paragraphs.append(''.join(chunks))
        return {'paragraphs':paragraphs,'text':'\n'.join(paragraphs),
                'automatic_numbered_paragraphs':len(list(body.iter(W+'numPr'))),
                'embedded_image_count':len([n for n in archive.namelist() if n.startswith('word/media/')]),
                'extractor':'OOXML paragraph/run/tab/break extraction; no OCR'}

def extract(path):
    if path.suffix.lower()=='.docx': return extract_docx(path)
    if path.suffix.lower()!='.doc': raise ValueError('Unsupported source format')
    command=['powershell','-NoProfile','-File',str(ROOT/'scripts/read_legacy_doc.ps1'),'-InputPath',str(path)]
    proc=subprocess.run(command,capture_output=True,encoding='utf-8-sig',timeout=120)
    if proc.returncode: raise ValueError(proc.stderr)
    result=json.loads(proc.stdout)
    result['paragraphs']=result['text'].split('\r')
    result['embedded_image_count']=None
    return result

def freeze_package_metadata(source_root,output_root):
    for metadata in Path(source_root).iterdir():
        if metadata.is_file() and metadata.suffix.lower() in {'.txt','.csv','.json'}:
            freeze(Path(output_root)/'package-metadata'/metadata.name,metadata.read_bytes())

def ingest(source_root,output_root):
    source_root=Path(source_root).resolve(); output_root=Path(output_root).resolve()
    if source_root==output_root or source_root in output_root.parents:
        raise ValueError('Output must not be inside supplied source directory')
    freeze_package_metadata(source_root,output_root)
    with (source_root/'文件与来源清单.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    records=[]; papers={}
    for row in rows:
        relative=Path(row['包内路径']); path=(source_root/relative).resolve()
        if not path.is_relative_to(source_root) or not path.is_file(): raise ValueError('Invalid source path')
        data=path.read_bytes(); fingerprint=sha(data)
        if fingerprint!=row['SHA256'].lower() or len(data)!=int(row['字节数']):
            raise ValueError('Source inventory mismatch: '+str(relative))
        exam_id='gaokao-'+row['年份']+'-'+row['卷别']
        kind='blank' if row['文件类型']=='原卷' else 'listening' if row['文件类型']=='听力试题及答案' else 'reveal'
        frozen=output_root/'raw'/relative
        freeze(frozen,data)
        extracted=extract(frozen)
        if sha(path.read_bytes())!=fingerprint: raise ValueError('Supplied source changed')
        extracted.update(exam_id=exam_id,source_kind=kind,source_sha256=fingerprint)
        extracted['text_sha256']=sha(extracted['text'].encode('utf-8'))
        extract_path=output_root/'sources'/exam_id/(kind+'.json')
        freeze_json(extract_path,extracted)
        record={'source_id':exam_id+'-'+kind,'exam_id':exam_id,'kind':kind,
                'source_reference':row['来源页面'],'download_reference':row['下载直链'],
                'filename':relative.as_posix(),'bytes':len(data),'sha256':fingerprint,
                'extraction_sha256':extracted['text_sha256'],
                'automatic_numbered_paragraphs':extracted['automatic_numbered_paragraphs'],
                'embedded_image_count':extracted['embedded_image_count'],
                'usage_status':'user_supplied_local_research; redistribution_not_verified',
                'answer_authority':'third_party_compilation_not_official'}
        records.append(record)
        paper=papers.setdefault(exam_id,{'exam_id':exam_id,'year':int(row['年份']),
            'exam_name':row['年份']+' 高考英语 '+row['卷别']+'卷（第三方整理版）',
            'region_or_source':row['卷别'],'source_reference':row['来源页面'],
            'usage_status':record['usage_status'],'source_ids':[],
            'paper_complete':None,'answer_key_available':kind=='reveal',
            'explanation_available':kind=='reveal',
            'question_types':{k:None for k in ['reading','seven_five','cloze','grammar_fill','application_writing','continuation_writing']},
            'ingestion_status':'source_frozen_structure_pending',
            'source_issue':[]})
        paper['source_ids'].append(record['source_id'])
        paper['answer_key_available']|=kind=='reveal'
        paper['explanation_available']|=kind=='reveal'
        if extracted['automatic_numbered_paragraphs']:
            paper['source_issue'].append({'type':'extraction_numbering','description':kind+' has automatic numbering; plain-text numbers require review','status':'pending_review'})
        if extracted['embedded_image_count']:
            paper['source_issue'].append({'type':'embedded_media','description':kind+' contains images; raw source preserved, text extraction is not complete image transcription','status':'pending_review'})
        print(record['source_id']+' frozen',flush=True)
    for paper in papers.values():
        if paper['exam_id']=='gaokao-2021-II':
            paper['source_issue'] += [{'type':'source_answer_conflict','description':'Supplied errata reports Q65 per-item explanation the vs final key from; preserve both and require semantic review','status':'pending_review'},
                {'type':'source_header_conflict','description':'Supplied errata reports 100-point/90-minute header inconsistent with section marks','status':'pending_review'}]
    manifest={'schema_version':'1.0.0','origin':'user_supplied_exam_material',
              'scope':'source hashes and read-only extraction only; not question completeness, semantic truth, rights or learner validation',
              'papers':sorted(papers.values(),key=lambda x:x['exam_id']),'sources':records}
    freeze_json(output_root/'source-manifest.json',manifest)
    return manifest

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('source_root'); parser.add_argument('--output',default=str(ROOT/'local-data/exams-2020-2025'))
    args=parser.parse_args(); out=ingest(args.source_root,args.output)
    print(json.dumps({'papers':len(out['papers']),'sources':len(out['sources']),'status':'source_frozen_structure_pending'}))

if __name__=='__main__': main()
