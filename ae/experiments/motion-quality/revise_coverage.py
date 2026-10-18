"""Extend the protected B to the complete question using the production rig."""
import json,sys
from pathlib import Path
from run import Trial,read,write,sha256,HERE

RIG=HERE.parents[1]/'rigs/reading-focus.jsx'

def main(folder):
    t=Trial(folder);p=t.folder;i=t.i
    if (p/'NATIVE_IDENTITY.json').exists():raise FileExistsError('Inspect existing patch; never replay')
    n=read(p/'BASELINE_NATIVE_IDENTITY.json');plan=read(Path(i['parent_folder'])/'AV_PLAN.json')
    scenes=[s for s in plan['scenes'] if s.get('world')=='camp' and s['kind']!='recap']
    start=scenes[0]['start'];end=scenes[-1]['end']
    i['full_question']={'start':start,'end':end,'frames':round((end-start+1)*24),'scenes':scenes,'voices':[v for v in plan['segments'] if start<=v['voice_start']<end]}
    write(p/'TRIAL_INPUT.json',i);t.i=i
    code=RIG.read_text('utf-8')+'\n'+(HERE/'coverage-patch.jsx').read_text('utf-8')
    code=code.replace('TRIAL_INPUT',json.dumps(i,ensure_ascii=False)).replace('BASELINE_NATIVE',json.dumps(n,ensure_ascii=False))
    code=code.replace('PATCH_RECEIPT',json.dumps((p/'COVERAGE_BEFORE_SAVE.json').as_posix()))
    r=t.mutate('Extend sequential phrase focus and continuous question return',lambda:t.h.js(code,'Revise question reading coverage'))
    r.update(code_binding=t.binding(),input_sha256=sha256(p/'TRIAL_INPUT.json'),reading_rig_sha256=sha256(RIG))
    write(p/'NATIVE_IDENTITY.json',r)
    write(p/'COVERAGE_PATCH_COMPLETE.json',{'project_sha256':sha256(t.project),'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'human_review':'PENDING'})
    print(json.dumps({k:r[k] for k in ('B','full_question_comp','full_question_frames')},ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1])
