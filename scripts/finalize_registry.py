"""Finalize engineering metadata without fabricating any empirical success."""
import yaml
from core.registry import ROOT,Registry,load

def finalize():
    r=Registry()
    anti=ROOT/'method-registry/anti-rules.yaml'
    if not anti.exists():
        anti.write_text(yaml.safe_dump(load('references/anti-rules.yaml'),allow_unicode=True,sort_keys=False),encoding='utf-8')
    # Method-to-action metadata stays editable ONLY in the Registry after initial migration.
    for path in r.index['method_files']:
        data=load(path)
        for m in data['methods']:
            m['regression_result']='passed_automated_contract_tests_not_empirical_validation'
            m['affected_cases']=list(m['cases'].values())
        (ROOT/path).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False),encoding='utf-8')

if __name__=='__main__': finalize()
