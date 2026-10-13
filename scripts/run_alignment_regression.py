"""Run existing controls with compact failure reports, not teaching certification."""
import json
from pathlib import Path
import sys
import time
import unittest
from core.registry import ROOT


class CompactResult(unittest.TextTestResult):
    def addError(self,test,err):
        super().addError(test,err)
        print('ERROR '+test.id()+': '+str(err[1]).splitlines()[0][:300],flush=True)
    def addFailure(self,test,err):
        super().addFailure(test,err)
        print('FAIL '+test.id()+': '+str(err[1]).splitlines()[0][:300],flush=True)
    def printErrors(self): pass


def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT/'tests'))
    started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=0,resultclass=CompactResult).run(suite)
    report={'scope':'engineering regression only; not semantic or learner acceptance',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'elapsed_seconds':round(time.monotonic()-started,3),
            'failing_tests':[{'test':test.id(),'trace_excerpt':trace.splitlines()[-1][:500]}
                             for test,trace in result.failures+result.errors]}
    output=ROOT/'local-data/answer-alignment-2026-10-13/full-regression-latest.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='failing_tests'},ensure_ascii=False),flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__': sys.exit(main())
