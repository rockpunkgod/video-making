"""Rebind explicitly identified editable examples, never frozen observations.

Section IDs encode line offsets and can collide across epochs. Only an explicit
per-file hash/epoch manifest identifies the starting rules. Changed definitions
require semantic reauthoring, not this mechanical operation.
"""
import hashlib
import json
from pathlib import Path

from core.registry import ROOT, Registry

FILES=('question-action-course.json','question-lesson-course.json','passage-lesson.synthetic.json',
       'writing-image.synthetic.json','writing-review.synthetic.json','writing-word-count.synthetic.json')
MANIFEST='provenance/example-source-epochs.json'


def rebind_example(value, previous, current):
    def section_id(sid):
        source=previous.sources['sections'].get(sid)
        if source is None:
            raise ValueError('Example source ID is missing from its explicit source epoch')
        if source.get('commit')!=previous.index['source_baseline']['commit']:
            raise ValueError('Example source section differs from its explicit source epoch')
        matches=[(key,row) for key,row in current.sources['sections'].items()
                 if (row['path'],row['heading'],row.get('commit'))==
                    (source['path'],source['heading'],current.index['source_baseline']['commit'])]
        if len(matches)!=1:
            raise ValueError('Example source binding is missing or ambiguous')
        key,target=matches[0]
        if target['content']!=source['content']:
            raise ValueError('Changed example source content requires semantic reauthoring')
        return key

    def visit(item):
        if isinstance(item,list): return [visit(child) for child in item]
        if not isinstance(item,dict): return item
        result={key:visit(child) for key,child in item.items()}
        if 'method_version' in result and 'method_id' in result:
            mid=result['method_id']
            if (mid not in previous.methods or mid not in current.methods or
                    result['method_version']!=previous.methods[mid]['version'] or
                    result['method_version']!=current.methods[mid]['version']):
                raise ValueError('Example method version requires explicit reauthoring; no automatic upgrade')
        if 'source_section_ids' in result:
            ids=result['source_section_ids']
            if len(ids)!=len(set(ids)):
                raise ValueError('Example source IDs must not be duplicated')
            result['source_section_ids']=[section_id(sid) for sid in ids]
        return result
    return visit(value)


def prepare_refresh(root=ROOT, current=None):
    root=Path(root); current=current or Registry()
    manifest=json.loads((root/MANIFEST).read_bytes())
    updates={}; changes=[]; histories={}
    for name,identity in manifest['examples'].items():
        if name not in FILES:
            raise ValueError('Only explicitly allowed editable examples can be refreshed')
        path=root/'examples'/name; raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=identity['sha256']:
            raise ValueError('Editable example differs from its explicit epoch manifest: '+name)
        commit=identity['source_commit']
        if commit not in histories:
            histories[commit]=(current if commit==current.index['source_baseline']['commit']
                               else Registry(snapshot_commit=commit))
        previous=histories[commit]
        value=rebind_example(json.loads(raw),previous,current)
        output=(raw if value==json.loads(raw) else
                (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        if output!=raw:
            updates['examples/'+name]=output; changes.append(name)
        identity.update(source_commit=current.index['source_baseline']['commit'],
                        sha256=hashlib.sha256(output).hexdigest())
    manifest_raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if manifest_raw!=(root/MANIFEST).read_bytes(): updates[MANIFEST]=manifest_raw
    return updates,{'scope':'explicitly epoch-bound editable examples only; not new case/learner evidence',
                    'updated':changes,'registered_examples':len(manifest['examples'])}


def refresh(root=ROOT, current=None):
    # Preflight the entire registered batch before the first mechanical write.
    root=Path(root)
    updates,report=prepare_refresh(root,current)
    for relative,raw in updates.items(): (root/relative).write_bytes(raw)
    return report


if __name__=='__main__': print(json.dumps(refresh(),ensure_ascii=False))
