"""Read-only checks for the 2026-10-28 presentation-only revision.

These checks certify preservation/structure, never student success or duration.
"""
from pathlib import Path
import hashlib
import json
import yaml

from core.registry import ROOT, Registry

PROTECTED=('method_id','brand_name','source_name','aliases','version','question_type',
           'method_type','role','primary_role','secondary_roles','output_type',
           'core_action','decision_rule','verification','stop_rule','section_ids',
           'source_references','cases','status','maturity_status','practical_value',
           'first_use_test','evaluation','role_correctness','short_version_safety')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    registry=Registry()
    registry.validate()
    rows=[]
    for mid,method in registry.methods.items():
        history=ROOT/f'method-registry/history/{mid}/editorial-before-20261028.yaml'
        original=yaml.safe_load(history.read_text(encoding='utf-8'))
        for key in PROTECTED:
            if method.get(key)!=original.get(key):
                raise ValueError(f'Copy-only revision changed {mid}.{key}')
        base_full={key:value for key,value in method['full'].items()
                   if key not in ('beginner_support','presentation_revision')}
        if base_full!=original['full']:
            raise ValueError('Original full contract changed: '+mid)
        if method['full']['presentation_revision']!='2026-10-28.2':
            raise ValueError('Unexpected presentation identity: '+mid)
        guide=ROOT/f'student-guides/{mid}-{method["brand_name"]}.md'
        text=guide.read_text(encoding='utf-8')
        if '新版入口复核中' in text or '## 先做这一小步' not in text:
            raise ValueError('Guide still held or lacks first action: '+mid)
        if method['student_ready'] or method['maturity_status']!='candidate':
            raise ValueError('Copy rewrite cannot grant learner readiness: '+mid)
        rows.append({'method_id':mid,'version':method['version'],
                     'presentation_revision':method['full']['presentation_revision'],
                     'history_path':history.relative_to(ROOT).as_posix(),
                     'history_sha256':sha(history),
                     'guide_path':guide.relative_to(ROOT).as_posix(),
                     'guide_sha256':sha(guide),
                     'protected_fields_unchanged':True,
                     'full_source_contract_unchanged':True,
                     'student_ready':False,
                     '10s_copy_characters':len(method['compact']['10s']),
                     '30s_copy_characters':len(method['compact']['30s']),
                     'duration_measured':None})
    if len(rows)!=82:
        raise ValueError('Expected82 reviewed entries')
    # Reconstruct the first delivered presentation from its immutable cards.
    # Compare the exact serialized guide bytes (including line-ending variant)
    # with that delivery's receipt, not merely its method IDs.
    from scripts.generate_assets import build
    old_receipt=json.loads((ROOT/'evaluation/reports/student-entry-editorial-20261028.json').read_text(encoding='utf-8'))
    previous=Registry()
    for mid in previous.methods:
        previous.methods[mid]=yaml.safe_load((ROOT/f'method-registry/history/{mid}/editorial-20261028.1.yaml').read_text(encoding='utf-8'))
    previous_assets=build(previous)
    for row in old_receipt['methods']:
        text=previous_assets[row['guide_path']]
        candidates=[text.encode('utf-8'),text.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')]
        if row['guide_sha256'] not in {hashlib.sha256(raw).hexdigest() for raw in candidates}:
            raise ValueError('Prior guide cannot be reconstructed exactly: '+row['method_id'])
    return {'method_count':82,'source_commit':registry.index['source_baseline']['commit'],
            'protected_fields':list(PROTECTED),'methods':rows,
            'current_entry_counts':json.loads((ROOT/'evaluation/reports/current-student-entry-audit.json').read_text(encoding='utf-8'))['entry_counts'],
            'generator_sha256':sha(ROOT/'scripts/generate_assets.py'),
            'prior_presentation_guides_reconstructed_against_receipt':82,
            'scope':'Preservation and authored-entry structure only; not actual duration, English case revalidation or learner success.'}


if __name__=='__main__':
    print(json.dumps(check(),ensure_ascii=False,indent=2))
