"""Scoped mechanical source-epoch switch with backups and read admission lock.

This activates source-bound candidate cards, not validated teaching methods.
It never rewrites private questions/actions/reviews or promotes a method.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import yaml

from core.registry import ROOT, Registry
from scripts.generate_assets import build, generate
from scripts.stage_answer_alignment import stage, CORRECTIONS
from scripts.plan_answer_alignment import TARGET

LOCK='provenance/answer-migration.lock.json'


def fingerprint(raw): return hashlib.sha256(raw).hexdigest()


def target_path(root,relative):
    target=(root/relative).resolve()
    if Path(relative).is_absolute() or not target.is_relative_to(root.resolve()) or \
            target==root.resolve() or target.is_dir():
        raise ValueError('Alignment target escaped the intended repository: '+str(relative))
    return target


def apply_payload(root,payload,backup_directory):
    """All targets are explicit; failures restore prior bytes, not git state."""
    root=Path(root).resolve(); backup_directory=Path(backup_directory).resolve()
    resolved={relative:target_path(root,relative) for relative in payload}
    if len(set(resolved.values()))!=len(resolved): raise ValueError('Duplicate resolved alignment target')
    if LOCK in payload: raise ValueError('Migration lock is not a payload asset')
    before={relative:path.read_bytes() if path.exists() else None for relative,path in resolved.items()}
    backup_directory.mkdir(parents=True,exist_ok=True)
    for relative,raw in before.items():
        if raw is not None:
            backup=target_path(backup_directory,relative)
            backup.parent.mkdir(parents=True,exist_ok=True); backup.write_bytes(raw)
    journal={'scope':'scoped_source_epoch_write_only','assets':[
        {'path':p,'previous_sha256':fingerprint(before[p]) if before[p] is not None else None,
         'next_sha256':fingerprint(raw)} for p,raw in sorted(payload.items())]}
    (backup_directory/'write-journal.json').write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    lock=target_path(root,LOCK); lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('xb') as stream:
        stream.write(json.dumps({'from_backup':str(backup_directory),'scope':'source_epoch_switch'}).encode())
    changed=[]
    try:
        for relative,raw in payload.items():
            path=resolved[relative]; path.parent.mkdir(parents=True,exist_ok=True)
            changed.append(relative); path.write_bytes(raw)
        for relative,raw in payload.items():
            if resolved[relative].read_bytes()!=raw:
                raise ValueError('Alignment write verification failed: '+relative)
    except BaseException:
        for relative in reversed(changed):
            path=resolved[relative]
            if before[relative] is None:
                path.unlink(missing_ok=True)  # only a newly created, confined payload file
            else: path.write_bytes(before[relative])
        raise
    finally:
        lock.unlink(missing_ok=True)  # task-created lock only; no recursive operation
    return journal


def activate(private_dataset=None):
    current=Registry(); current.validate()
    old_commit=current.index['source_baseline']['commit']
    report_path=ROOT/'provenance/runtime-alignments'/f'{TARGET}.json'
    if old_commit==TARGET:
        if not report_path.is_file(): raise ValueError('Applied epoch has no recorded activation; explicit recovery required')
        generate(check=True)
        return {'status':'already_source_aligned','source_commit':TARGET,'promotion_applied':False}
    catalog_before=None
    if private_dataset:
        from core.real_cases import freeze_runtime_context, load_catalog
        freeze_runtime_context(private_dataset,old_commit)
        catalog_before=load_catalog(private_dataset)
    candidate_report=stage(); candidate_root=Path(candidate_report['path'])
    with patch('core.registry.ROOT',candidate_root): candidate=Registry()
    changed={mid for mid,m in candidate.methods.items() if m['source_alignment']['source_content_changed']}
    if not changed<=set(CORRECTIONS): raise ValueError('A changed source card lacks an explicit boundary review')
    if set(current.methods)!=set(candidate.methods): raise ValueError('Activation must not silently add or remove method IDs')
    for mid,m in candidate.methods.items():
        if (m['maturity_status'],m['practical_value'])!=(current.methods[mid]['maturity_status'],current.methods[mid]['practical_value']):
            raise ValueError('Source alignment is not method promotion')
        m['source_alignment']['state']='live_source_bound'
        m['source_alignment']['acceptance']='source_alignment_only; semantic/learner/release acceptance remains pending'
    for relative in candidate.index['method_files']:
        module=candidate._load(relative)
        module['methods']=[candidate.methods[m['method_id']] for m in module['methods']]
        (candidate_root/relative).write_text(yaml.safe_dump(module,allow_unicode=True,sort_keys=False),encoding='utf-8')
    with patch('core.registry.ROOT',candidate_root):
        candidate=Registry(); candidate.validate()
    projections=build(candidate)
    paths={candidate.index['source_sections'],'method-registry/registry.yaml','method-registry/source-risks.yaml',
           'method-registry/symptom-cues.yaml','method-registry/grammar-tree.yaml','method-registry/anti-rules.yaml',
           'provenance/manifest.yaml',*candidate.index['method_files'],'cases/registry.yaml',
           *candidate.case_inventory(),
           *('provenance/ANSWER/'+f['path'] for f in candidate._load('provenance/manifest.yaml')['files'])}
    payload={relative:(candidate_root/relative).read_bytes() for relative in sorted(paths)}
    payload.update({relative:content.encode('utf-8') for relative,content in projections.items()})
    backup=Path(tempfile.mkdtemp(prefix='activation-backup-',dir=ROOT/'local-data/answer-alignment-2026-10-13'))
    journal=apply_payload(ROOT,payload,backup)
    new=Registry(); validation=new.validate(); generate(check=True)
    if private_dataset:
        from core.real_cases import load_catalog
        after=load_catalog(private_dataset)
        if (after['revision'],after['sha256'],after['cases'])!=(catalog_before['revision'],catalog_before['sha256'],catalog_before['cases']):
            raise ValueError('Private catalog changed during source migration')
    report={'schema_version':'1.0.0','scope':'source_alignment_not_teaching_or_learner_certification',
            'from_commit':old_commit,'to_commit':TARGET,'status':'source_bound_candidate_epoch_active',
            'registry_validation':validation,'generated_assets':'PASS','changed_source_profiles':len(changed),
            'method_ids_added_or_removed':False,'method_promotion_applied':False,
            'student_short_form_acceptance':'pending','new_blind_samples':0,
            'private_catalog_sha256_preserved':catalog_before['sha256'] if catalog_before else None,
            'backup_directory':str(backup),'asset_write_count':len(journal['assets']),
            'asset_hashes':journal['assets'],'full_runtime_regression':'pending_after_activation'}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in report.items() if k!='asset_hashes'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--private-dataset')
    print(json.dumps(activate(parser.parse_args().private_dataset),ensure_ascii=False,indent=2))
