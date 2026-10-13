"""Repair nested full projections without modifying frozen case observations."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import yaml
from core.registry import ROOT,Registry
from scripts.activate_answer_alignment import apply_payload
from scripts.generate_assets import build,generate
from scripts.stage_answer_alignment import stage
from scripts.plan_answer_alignment import TARGET


def refresh():
    live=Registry()
    if live.index['source_baseline']['commit']!=TARGET: raise ValueError('Activate the reviewed source epoch first')
    report=stage()
    with patch('core.registry.ROOT',Path(report['path'])): candidate=Registry()
    payload={}; changed=[]
    for relative in live.index['method_files']:
        module=live._load(relative)
        for m in module['methods']:
            updated=candidate.methods[m['method_id']]['full']
            if m['full']!=updated: changed.append(m['method_id']); m['full']=updated
        payload[relative]=yaml.safe_dump(module,allow_unicode=True,sort_keys=False).encode('utf-8')
    backup=Path(tempfile.mkdtemp(prefix='full-projection-backup-',dir=ROOT/'local-data/answer-alignment-2026-10-13'))
    apply_payload(ROOT,payload,backup)
    new=Registry(); new.validate(); generate()
    value={'scope':'nested_source_summary_alignment_only','source_commit':TARGET,
           'changed_methods':changed,'new_blind_samples':0,'promotion_applied':False,
           'same_version_semantic_changes_invalidate_frozen_exports':True,
           'backup_directory':str(backup)}
    output=ROOT/'provenance/runtime-alignments'/f'{TARGET}-full-projection.json'
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return value


if __name__=='__main__': print(json.dumps(refresh(),ensure_ascii=False,indent=2))
