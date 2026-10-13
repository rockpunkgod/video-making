"""Recompute published pending/synthetic statistics; never modify observations."""
import hashlib
import json
from core.registry import ROOT
from evaluation.harness import evaluate,load_records


def refresh():
    values=[]
    for source,name in [('synthetic-observations.json','synthetic-contract-result.json'),
                        ('real-observations.pending.json','real-validation.pending.json')]:
        path=ROOT/'evaluation/datasets'/source; before=path.read_bytes()
        result=evaluate(load_records(path))
        dest=ROOT/'evaluation/results'/name
        dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if path.read_bytes()!=before: raise ValueError('Observation data changed during projection refresh')
        values.append({'observations':source,'sha256_preserved':hashlib.sha256(before).hexdigest(),
                       'result':name,'origin':result['origin']})
    return values


if __name__=='__main__': print(json.dumps(refresh(),ensure_ascii=False,indent=2))
