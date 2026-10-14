"""Sample local questions and summarize explicit annotations, never solve or certify them.

Run as `python -m scripts.move_hit_rate`. Sampling is not method applicability.
Unknown applicability/hits stay null. Human audits bind the exact annotation bytes.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import json
import math
import hashlib
from pathlib import Path

import yaml

from creative_os.moves import CATALOG_PATH, load_catalog
from video_contracts import sha


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def question_inventory(exam_root):
    rows = []
    seen = set()
    for path in sorted(Path(exam_root).glob('predictions/*/blind.json')):
        payload = json.loads(path.read_bytes())
        for index, question in enumerate(payload['inputs']['questions']):
            qid = question['question_id']
            if qid in seen:
                raise ValueError('Duplicate question ID in sampling pool')
            seen.add(qid)
            rows.append({'question_id': qid, 'question_type': question['question_type'],
                'exam_id': payload['exam_id'], 'question_sha': sha(question),
                'question': deepcopy(question), 'input_file': str(path.resolve()),
                'input_file_sha': file_sha(path), 'input_index': index,
                'source_sha': payload['source_sha256']})
    return rows


def prepare_samples(catalog, inventory, *, per_move=10):
    if type(per_move) is not int or per_move < 10:
        raise ValueError('At least ten sampled questions per initial move')
    samples = []
    for move in catalog['entries']:
        if not move['first_batch']:
            continue
        by_exam = defaultdict(list)
        for row in inventory:
            if row['question_type'] == move['question_type']:
                by_exam[row['exam_id']].append(row)
        for rows in by_exam.values():
            rows.sort(key=lambda row: sha([move['name'], row['question_id']]))
        pool = []
        exam_order = sorted(by_exam, key=lambda exam: sha([move['name'], exam]))
        while any(by_exam.values()) and len(pool) < per_move:
            for exam in exam_order:
                if by_exam[exam] and len(pool) < per_move:
                    pool.append(by_exam[exam].pop(0))
        for row in pool:
            binding = {'move_name': move['name'], 'question_id': row['question_id'],
                'question_sha': row['question_sha'], 'source_commit': catalog['source_commit'],
                'move_card_sha': sha(move['move_card']),
                'method_versions': {m['method_id']: m['version'] for m in move['methods']}}
            samples.append({'sample_id': sha(binding), 'binding': binding,
                'source': deepcopy(row), 'annotation': None, 'human_audit': None})
    return {'version': 'move-hit-rate/v1', 'catalog_source_commit': catalog['source_commit'],
            'sampling_scope': 'question-type-stratified; applicability not inferred',
            'samples': samples, 'public_render_ready': False}


def _validated_annotation(sample):
    annotation = sample['annotation']
    if annotation is None:
        return None
    if set(annotation) != {'applicable', 'hit', 'annotator', 'kind', 'evidence_refs', 'notes'}:
        raise ValueError('Complete explicit annotation fields required')
    if (type(annotation['applicable']) is not bool or type(annotation['hit']) is not bool
            or annotation['kind'] not in ('ai', 'human') or not annotation['annotator'].strip()
            or not annotation['notes'].strip() or not annotation['evidence_refs']):
        raise ValueError('Annotation requires a decision, provenance and evidence')
    if annotation['hit'] and not annotation['applicable']:
        raise ValueError('A non-applicable method cannot claim a hit')
    audit = sample['human_audit']
    if audit is not None and (set(audit) != {'reviewer', 'annotation_sha', 'agrees', 'notes'}
            or not audit['reviewer'].strip() or not audit['notes'].strip()
            or type(audit['agrees']) is not bool or audit['annotation_sha'] != sha(annotation)):
        raise ValueError('Human audit must bind the current annotation')
    return annotation


def summarize(catalog, samples, *, min_hit_rate=None, verify_sources=True):
    if min_hit_rate is not None and (isinstance(min_hit_rate, bool)
            or not math.isfinite(min_hit_rate) or not 0 <= min_hit_rate <= 1):
        raise ValueError('An explicit hit-rate threshold must be in 0–1')
    moves = {row['name']: row for row in catalog['entries'] if row['first_batch']}
    grouped = defaultdict(list)
    ids = set()
    for sample in samples['samples']:
        binding = sample['binding']
        move = moves.get(binding['move_name'])
        if not move or sample['sample_id'] != sha(binding) or sample['sample_id'] in ids:
            raise ValueError('Duplicate or invalid sample binding')
        ids.add(sample['sample_id'])
        if (binding['source_commit'] != catalog['source_commit']
                or binding['move_card_sha'] != sha(move['move_card'])
                or binding['method_versions'] != {m['method_id']: m['version'] for m in move['methods']}
                or binding['question_id'] != sample['source']['question_id']
                or binding['question_sha'] != sha(sample['source']['question'])):
            raise ValueError('Sampling or method binding changed')
        if verify_sources:
            path = Path(sample['source']['input_file'])
            if file_sha(path) != sample['source']['input_file_sha']:
                raise ValueError('Sampled source file changed')
            original = json.loads(path.read_bytes())['inputs']['questions'][sample['source']['input_index']]
            if sha(original) != binding['question_sha']:
                raise ValueError('Question no longer matches its original source')
        _validated_annotation(sample)
        grouped[move['name']].append(sample)
    result = []
    for name in moves:
        rows = grouped[name]
        annotated = [row for row in rows if row['annotation'] is not None]
        # Stable audit sample prevents choosing only favorable cases for the 20% check.
        audit_count = math.ceil(len(annotated) * 0.2)
        selected = sorted(annotated, key=lambda row: sha(['human-audit', row['sample_id']]))[:audit_count]
        audited = [row for row in selected if row['human_audit'] is not None]
        disagreements = [row for row in audited if not row['human_audit']['agrees']]
        applicable = sum(row['annotation']['applicable'] for row in annotated) if annotated else None
        hits = sum(row['annotation']['hit'] for row in annotated) if annotated else None
        rate = hits / applicable if applicable else None
        complete = len(rows) >= 10 and len(annotated) == len(rows)
        audit_complete = bool(annotated) and len(audited) == audit_count and not disagreements
        state = ('HOLD_MISSING_ANNOTATIONS' if not complete else
                 'HOLD_HUMAN_AUDIT' if not audit_complete else
                 'HOLD_NO_APPLICABLE_CASES' if rate is None else
                 'HOLD_THRESHOLD_UNSPECIFIED' if min_hit_rate is None else
                 'LOW_HIT_RATE_DO_NOT_FILM' if rate < min_hit_rate else 'READY_FOR_CONTENT_REVIEW')
        result.append({'move_name': name, 'evaluation': {'sampled': len(rows),
            'annotated': len(annotated), 'applicable': applicable, 'hits': hits, 'hit_rate': rate,
            'annotation_coverage': len(annotated) / len(rows) if rows else None,
            'human_audit_fraction': len(audited) / len(annotated) if annotated else None},
            'required_human_audit_sample_ids': [row['sample_id'] for row in selected],
            'disagreements': len(disagreements), 'filming_state': state})
    return {'version': 'move-hit-rate/v1', 'source_commit': catalog['source_commit'],
            'min_hit_rate': min_hit_rate, 'moves': result,
            'semantic_certification': False, 'registry_maturity_changed': False,
            'public_render_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=CATALOG_PATH)
    parser.add_argument('--exam-root', type=Path)
    parser.add_argument('--samples', type=Path)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--min-hit-rate', type=float)
    parser.add_argument('--write-evaluation', action='store_true')
    parser.add_argument('--role-records', type=Path,
        help='JSON requests with bundle/status paths, selection and role observation; no solving')
    args = parser.parse_args()
    if args.role_records:
        from creative_os.role_evaluation import evaluate, summarize as role_summary
        root = args.role_records.parent
        requests = json.loads(args.role_records.read_bytes())
        records = [evaluate(json.loads((root / row['bundle']).read_bytes()),
                    json.loads((root / row['status']).read_bytes()), row['selection'], row['observation'])
                   for row in requests]
        report = {**role_summary(records), 'records': records}
        if args.prepare or args.write_evaluation:
            parser.error('Role observations do not rewrite catalog evaluation or sampling')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'role_observations': len(records), 'public_render_ready': False}))
        return
    if args.samples is None:
        parser.error('--samples is required unless --role-records is supplied')
    catalog = load_catalog(args.catalog)
    if args.prepare:
        if args.samples.exists():
            raise FileExistsError('Preserve existing annotations; use a new sampling file')
        if args.exam_root is None:
            parser.error('--prepare requires --exam-root')
        samples = prepare_samples(catalog, question_inventory(args.exam_root))
        args.samples.parent.mkdir(parents=True, exist_ok=True)
        args.samples.write_text(json.dumps(samples, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    else:
        samples = json.loads(args.samples.read_bytes())
    report = summarize(catalog, samples, min_hit_rate=args.min_hit_rate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.write_evaluation:
        evaluations = {row['move_name']: row['evaluation'] for row in report['moves']}
        for row in catalog['entries']:
            if row['name'] in evaluations:
                row['evaluation'] = evaluations[row['name']]
        # Presentation evaluation only; no Registry fact, maturity or Review writes.
        args.catalog.write_text(yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding='utf-8')
    print(json.dumps({'moves': len(report['moves']), 'sampled': sum(
        row['evaluation']['sampled'] for row in report['moves']), 'annotated': sum(
        row['evaluation']['annotated'] for row in report['moves']), 'public_render_ready': False}))


if __name__ == '__main__':
    main()
