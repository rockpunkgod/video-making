"""Durable one-agent-per-paper dispatch ledger; never fabricate agent runs.

This ledger does not spawn agents itself. The coordinator must use the actual
collaboration tool, then bind its returned task name with `assign`. Pending
papers remain pending, and a report alone does not certify English semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3

from scripts.freeze_organized_pdf_pages import selected

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'local-data/organized-pdfs/paper-agent-queue.sqlite'
REGIONS = {'北京':'beijing', '上海':'shanghai', '天津':'tianjin', '浙江':'zhejiang',
           '江苏':'jiangsu', '安徽':'anhui', '福建':'fujian', '广东':'guangdong',
           '湖北':'hubei', '湖南':'hunan', '江西':'jiangxi', '辽宁':'liaoning',
           '山东':'shandong', '陕西':'shaanxi', '四川':'sichuan', '重庆':'chongqing',
           '宁夏':'ningxia', '海南':'hainan', '山西':'shanxi'}

def now():
    return datetime.now(timezone.utc).isoformat()

def paper_label(relative):
    path = Path(relative.replace('\\', '/'))
    name = path.stem.replace('Ⅰ','I').replace('Ⅱ','II').replace('Ⅲ','III')
    years = re.findall(r'(?<!\d)(20\d{2})(?!\d)', name)
    if not years:
        for parent in reversed(path.parts[:-1]):
            years = re.findall(r'(?<!\d)(20\d{2})(?!\d)', parent)
            if years:
                break
    year = years[0] if years else 'unknown'
    region = next((v for k,v in REGIONS.items() if k in name), None)
    if region is None:
        family = 'new-gaokao' if '新高考' in name else 'new-standard' if '新课标' in name else 'national'
        volume = re.search(r'(III|II|I|[一二三])(?=卷)', name)
        region = family + ('-' + {'一':'i','二':'ii','三':'iii'}.get(volume[1], volume[1].lower()) if volume else '')
    season = re.search(r'[（(](\d{1,2})月[）)]', name)
    suffix = '-m'+season[1].zfill(2) if season else '-spring' if '春考' in name else '-autumn' if '秋考' in name else ''
    return f'gaokao-{year}-{region}{suffix}'

def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
          paper_id TEXT PRIMARY KEY, source_sha256 TEXT UNIQUE NOT NULL,
          relative_path TEXT UNIQUE NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
          agent_task TEXT UNIQUE, model TEXT, reasoning_effort TEXT,
          report_directory TEXT, report_sha256 TEXT, review_outcome TEXT);
        CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL,
          paper_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL);
    ''')
    if 'report_addenda' not in {r[1] for r in db.execute('PRAGMA table_info(papers)')}:
        db.execute('ALTER TABLE papers ADD COLUMN report_addenda TEXT')
        db.commit()
    if 'report_file' not in {r[1] for r in db.execute('PRAGMA table_info(papers)')}:
        db.execute("ALTER TABLE papers ADD COLUMN report_file TEXT NOT NULL DEFAULT 'review.json'")
        db.commit()
    return db

def verify_addenda(directory, source_sha):
    from hashlib import sha256
    directory=Path(directory).resolve(); records=[]
    for path in sorted(directory.glob('*addendum*.json')):
        raw=path.read_bytes(); value=json.loads(raw)
        if value.get('source_sha256') != source_sha:
            raise ValueError('Addendum belongs to a different paper')
        for name, expected in value.get('binds_original_bytes',{}).items():
            original=(directory/name).resolve()
            if not original.is_relative_to(directory) or sha256(original.read_bytes()).hexdigest()!=expected:
                raise ValueError('Addendum does not bind preserved original bytes')
        records.append({'file':path.name,'sha256':sha256(raw).hexdigest(),
                        'interpretation':'apply without overwriting its original frozen report'})
    return records

def initialize(db, manifest):
    variants = Counter()
    rows = sorted((r for r in manifest['files'] if selected(r, 'questions')), key=lambda r:r['relative_path'])
    for row in rows:
        base = paper_label(row['relative_path']); variants[base] += 1
        pid = f'{base}-v{variants[base]:02d}'
        current = db.execute('SELECT * FROM papers WHERE paper_id=?',(pid,)).fetchone()
        if current and (current['source_sha256'] != row['sha256'] or current['relative_path'] != row['relative_path']):
            raise ValueError('Manifest drift; use a new intake queue, not rewritten IDs: '+pid)
        db.execute('INSERT OR IGNORE INTO papers(paper_id,source_sha256,relative_path) VALUES (?,?,?)',
                   (pid,row['sha256'],row['relative_path']))
    existing = {r[0] for r in db.execute('SELECT source_sha256 FROM papers')}
    if existing != {r['sha256'] for r in rows}:
        raise ValueError('Queue differs from current source manifest')
    db.commit()
    return len(rows)

def assign(db, paper_id, task, model, effort, directory=None):
    row = db.execute('SELECT * FROM papers WHERE paper_id=?',(paper_id,)).fetchone()
    if not row or row['state'] != 'pending':
        raise ValueError('Only an existing pending paper can be assigned')
    if not task.startswith('/root/'):
        raise ValueError('Bind an actual canonical subagent task, not a fictional worker label')
    db.execute('UPDATE papers SET state=?,agent_task=?,model=?,reasoning_effort=?,report_directory=? WHERE paper_id=?',
               ('running',task,model,effort,directory or str(DEFAULT.parent/'paper-runs'/paper_id),paper_id))
    db.execute('INSERT INTO events(recorded_at,paper_id,event,detail) VALUES (?,?,?,?)',
               (now(),paper_id,'agent_assigned',json.dumps({'actual_agent_task':task,'model':model,'reasoning_effort':effort})))
    db.commit()


def advance_semantic(db, paper_id, task, model, effort, transcription, replay):
    """Bind an actually spawned second-stage agent; preserve first-stage history."""
    from hashlib import sha256
    row = db.execute('SELECT * FROM papers WHERE paper_id=?',(paper_id,)).fetchone()
    if not row or row['state'] != 'running' or not task.startswith('/root/') or task == row['agent_task']:
        raise ValueError('A distinct actually assigned semantic agent and active transcription required')
    path = Path(transcription).resolve()
    if not path.is_relative_to(Path(row['report_directory']).resolve()):
        raise ValueError('Transcription must belong to this assigned paper directory')
    raw = path.read_bytes(); value = json.loads(raw)
    replay_path = Path(replay).resolve(); replay_raw = replay_path.read_bytes(); result = json.loads(replay_raw)
    fingerprint = sha256(raw).hexdigest()
    if value.get('paper_id') != paper_id or value.get('source_sha256') != row['source_sha256'] or \
            value.get('reviewer_agent') != row['agent_task'] or value.get('reference_read') is not False or \
            value.get('phase') != 'low_model_source_transcription_no_answers':
        raise ValueError('Source-only transcription must bind the original actual agent and source')
    if result.get('paper_id') != paper_id or result.get('source_sha256') != row['source_sha256'] or \
            result.get('transcription_sha256') != fingerprint or \
            result.get('phase') != 'source_transcription_engine_replay_not_semantic_acceptance':
        raise ValueError('Explicit preflighted replay must bind the exact transcription bytes')
    old = {'agent_task':row['agent_task'], 'model':row['model'], 'reasoning_effort':row['reasoning_effort']}
    detail = {'previous_transcription_assignment':old, 'actual_agent_task':task,
              'model':model, 'reasoning_effort':effort,
              'transcription_file':str(path), 'transcription_sha256':fingerprint,
              'replay_file':str(replay_path), 'replay_sha256':sha256(replay_raw).hexdigest(),
              'semantic_review_completed':False, 'new_blind_sample':False}
    db.execute('UPDATE papers SET agent_task=?,model=?,reasoning_effort=? WHERE paper_id=?',
               (task,model,effort,paper_id))
    db.execute('INSERT INTO events(recorded_at,paper_id,event,detail) VALUES (?,?,?,?)',
               (now(),paper_id,'semantic_agent_assigned',json.dumps(detail)))
    db.commit()

def selected_report(row, filename=None):
    """Select an explicit immutable revision, never silently pick newest glob."""
    filename = filename or row['report_file']
    if not re.fullmatch(r'review(?:-v[1-9][0-9]*)?\.json', filename):
        raise ValueError('Use an explicit review.json or review-vN.json basename')
    directory = Path(row['report_directory']).resolve()
    report = (directory / filename).resolve()
    if not report.is_relative_to(directory):
        raise ValueError('Report must stay inside its assigned paper directory')
    return report

def record_report(db, paper_id, outcome, filename='review.json'):
    from hashlib import sha256
    row = db.execute('SELECT * FROM papers WHERE paper_id=?',(paper_id,)).fetchone()
    if not row or row['state'] != 'running':
        raise ValueError('No actually assigned agent for paper')
    report = selected_report(row, filename)
    data = report.read_bytes(); value = json.loads(data)
    if value.get('source_sha256') != row['source_sha256']:
        raise ValueError('Review is not bound to this source')
    if value.get('paper_id') != paper_id or value.get('reviewer_agent') != row['agent_task']:
        raise ValueError('Review paper and reviewer must match the actual assignment')
    # Completion means the scoped agent review returned, not formal Case approval.
    addenda=verify_addenda(row['report_directory'],row['source_sha256'])
    db.execute('UPDATE papers SET state=?,report_sha256=?,review_outcome=?,report_addenda=?,report_file=? WHERE paper_id=?',
               ('reviewed',sha256(data).hexdigest(),outcome,json.dumps(addenda),report.name,paper_id))
    db.execute('INSERT INTO events(recorded_at,paper_id,event,detail) VALUES (?,?,?,?)',
               (now(),paper_id,'agent_report_recorded',json.dumps({'report':str(report),'outcome':outcome})))
    db.commit()

def attach_addenda(db,paper_id):
    from hashlib import sha256
    row=db.execute('SELECT * FROM papers WHERE paper_id=?',(paper_id,)).fetchone()
    if not row or row['state']!='reviewed': raise ValueError('Review must already be recorded')
    report=selected_report(row)
    if sha256(report.read_bytes()).hexdigest()!=row['report_sha256']:
        raise ValueError('Original frozen report changed')
    records=verify_addenda(row['report_directory'],row['source_sha256'])
    db.execute('UPDATE papers SET report_addenda=? WHERE paper_id=?',(json.dumps(records),paper_id))
    db.execute('INSERT INTO events(recorded_at,paper_id,event,detail) VALUES (?,?,?,?)',
               (now(),paper_id,'integrity_addenda_bound',json.dumps(records)))
    db.commit()

def snapshot(db, limit=10):
    return {'counts':dict(db.execute('SELECT state,count(*) FROM papers GROUP BY state').fetchall()),
            'pending':[dict(r) for r in db.execute('SELECT * FROM papers WHERE state=? ORDER BY paper_id LIMIT ?',('pending',limit))],
            'active':[dict(r) for r in db.execute('SELECT * FROM papers WHERE state=? ORDER BY paper_id',('running',))]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,default=DEFAULT)
    sub = p.add_subparsers(dest='command',required=True)
    init = sub.add_parser('init'); init.add_argument('--manifest',type=Path,default=DEFAULT.parent/'source-manifest.json')
    listing = sub.add_parser('list'); listing.add_argument('--limit',type=int,default=10)
    bind = sub.add_parser('assign'); bind.add_argument('paper_id'); bind.add_argument('agent_task')
    bind.add_argument('--model',required=True); bind.add_argument('--effort',required=True); bind.add_argument('--report-directory')
    advance = sub.add_parser('advance-semantic'); advance.add_argument('paper_id'); advance.add_argument('agent_task')
    advance.add_argument('--model',required=True); advance.add_argument('--effort',required=True)
    advance.add_argument('--transcription',type=Path,required=True); advance.add_argument('--replay',type=Path,required=True)
    complete = sub.add_parser('record-report'); complete.add_argument('paper_id'); complete.add_argument('--outcome',choices=('PASS','PARTIAL','SOURCE_GAP'),required=True)
    complete.add_argument('--report-file',default='review.json',help='Explicit frozen revision; historical files are preserved')
    supplement = sub.add_parser('attach-addenda'); supplement.add_argument('paper_id')
    args=p.parse_args()
    with connect(args.queue) as db:
        if args.command=='init': initialize(db,json.loads(args.manifest.read_text(encoding='utf-8-sig')))
        elif args.command=='assign': assign(db,args.paper_id,args.agent_task,args.model,args.effort,args.report_directory)
        elif args.command=='advance-semantic': advance_semantic(db,args.paper_id,args.agent_task,args.model,args.effort,args.transcription,args.replay)
        elif args.command=='record-report': record_report(db,args.paper_id,args.outcome,args.report_file)
        elif args.command=='attach-addenda': attach_addenda(db,args.paper_id)
        print(json.dumps(snapshot(db,args.limit if args.command=='list' else 0),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
