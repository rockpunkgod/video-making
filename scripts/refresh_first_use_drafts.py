"""Re-export explicitly selected uncollected drafts without touching old materials.

Only source-bound draft materials can be refreshed. This is not study approval,
observation conversion, case registration or new blind-test sampling.
"""
import argparse
import hashlib
import json
from pathlib import Path

from core.registry import ROOT, Registry
from scripts.prepare_first_use_materials import (prepare,read_question,validate_materials,
                                                validate_draft_metadata,render_student_material)


def refresh(index, suffix, registry=None):
    registry=registry or Registry()
    registry.validate()
    index=Path(index).resolve(); base=index.parent
    if not base.is_relative_to((ROOT/'local-data').resolve()):
        raise ValueError('Study draft index must be private')
    if not suffix or any(char not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for char in suffix):
        raise ValueError('Use an explicit lowercase revision suffix')
    manifest=json.loads(index.read_text(encoding='utf-8'))
    output_index=base/('CURRENT_DRAFTS-'+suffix+'.json')
    if output_index.exists():
        raise ValueError('Revision index already exists; refuse overwrite')
    if manifest.get('source_commit')!=registry.index['source_baseline']['commit']:
        raise ValueError('Source epoch changed; semantic review required, not draft refresh')
    batch=[]
    for mid,relative in manifest['current_kits'].items():
        old=(base/relative).resolve()
        if not old.is_relative_to(base):
            raise ValueError('Draft path escapes private study directory')
        meta=json.loads((old/'facilitator.json').read_text(encoding='utf-8'))
        if (meta.get('method_id')!=mid or meta.get('method_version')!=registry.methods[mid]['version'] or
                meta.get('source_commit')!=manifest['source_commit']):
            raise ValueError('Method identity or version changed; do not migrate an old demonstration')
        try:
            validate_draft_metadata(meta)
        except ValueError as exc:
            raise ValueError('Refuse to refresh collected, approved or non-draft material') from exc
        if hashlib.sha256((old/'student-material.md').read_bytes()).hexdigest()!=meta.get('student_material_sha256'):
            raise ValueError('Old student copy changed; inspect it instead of silently refreshing')
        refs=meta['source_refs']
        if len(refs)!=3 or any(hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()!=ref['sha256'] for ref in refs):
            raise ValueError('Original source or demonstration changed; semantic review required')
        demo,_=read_question(refs[0]['path'],refs[0].get('question_selector'))
        transfer,_=read_question(refs[1]['path'],refs[1].get('question_selector'))
        walkthrough=json.loads(Path(refs[2]['path']).read_bytes())
        validate_materials(registry.methods[mid],manifest['source_commit'],demo,transfer,walkthrough)
        render_student_material(registry.methods[mid],demo,transfer,walkthrough)
        target=old.with_name(old.name+'-'+suffix)
        if target.exists():
            raise ValueError('Revision output already exists; refuse overwrite')
        batch.append((mid,relative,refs,target))
    results=[]
    for mid,relative,refs,target in batch:
        result=prepare(mid,refs[0]['path'],refs[1]['path'],refs[2]['path'],target,registry,
                       demonstration_id=refs[0].get('question_selector'),
                       transfer_id=refs[1].get('question_selector'))
        results.append(result)
        manifest['current_kits'][mid]=target.name
        manifest.setdefault('superseded_before_acceptance',[]).append({
            'kit':relative,'reason':'Uncollected draft re-exported with current challenge-bound teaching projection.'})
    # A new index is proposed; the caller explicitly selects it as current.
    output_index.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'index':str(output_index),'methods':[row['method_id'] for row in results],
            'status':'uncollected_drafts_reexported_not_accepted',
            'collection_allowed':False,'new_case_count':0,'new_blind_sample_count':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',required=True,type=Path)
    parser.add_argument('--suffix',required=True)
    args=parser.parse_args()
    print(json.dumps(refresh(args.index,args.suffix),ensure_ascii=False))
