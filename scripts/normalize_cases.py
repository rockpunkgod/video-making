"""Envelope migration; preserve every pre-existing gap/status."""
from core.registry import ROOT, Registry, load
import yaml

def normalize():
    r = Registry()
    for mid, m in r.methods.items():
        for kind, path in m['cases'].items():
            c = load(path)
            c.update(case_id=mid+'-'+kind,question_type=m['question_type'],source=c.get('source',c.get('source_reference',m['source_references'][0])),question=c.get('question',c.get('prompt_excerpt')),answer=c.get('answer',c.get('expected_result')),trigger=c.get('trigger',m['trigger_cues'][0]),evidence=c.get('evidence',[]),method_role=m['primary_role'],expected_output=m['output_type'],stop_rule=m['stop_rule'],notes=c.get('notes',c.get('gap','尚未真人验收')))
            (ROOT/path).write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False),encoding='utf-8')
    cases = [path for m in r.methods.values() for path in m['cases'].values()]
    (ROOT/'cases/registry.yaml').write_text(yaml.safe_dump({'case_files':cases},allow_unicode=True,sort_keys=False),encoding='utf-8')

if __name__ == '__main__': normalize()
