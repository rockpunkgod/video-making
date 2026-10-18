"""Apply the two requested reading fixes to a protected copy of the existing B."""
import json,sys
from pathlib import Path
from run import Trial,read,write,sha256,HERE

def main(folder):
    t=Trial(folder);p=t.folder;i=t.i
    assert i.get('reading_focus_revision')==2
    assert not (p/'NATIVE_IDENTITY.json').exists(), 'Inspect completed/unknown patch; no replay'
    n=read(p/'BASELINE_NATIVE_IDENTITY.json')
    for rel,expected in n['code_binding'].items():
        assert sha256(HERE.parent/rel)==expected, 'Baseline generator changed'
    n['project']=str(t.project);n['code_binding']=t.binding();n['input_sha256']=sha256(p/'TRIAL_INPUT.json')
    n['human_review']='PENDING';n['revision_basis']='Existing B retained; two explicit user corrections only'
    code=(HERE/'reading-focus.jsx').read_text('utf-8')
    code+='\nvar I='+json.dumps(i,ensure_ascii=False)+',rig='+json.dumps(n['rig'],ensure_ascii=False)+';'
    code+='var c=app.project.itemByID('+str(n['B_source'])+');rig=mqReviseReading(c,I,rig);app.project.save();return rig;'
    write(p/'READING_PATCH_PENDING.json',{'code_sha256':sha256(HERE/'reading-focus.jsx'),'input_sha256':n['input_sha256'],'source_identity_sha256':sha256(p/'BASELINE_NATIVE_IDENTITY.json')})
    n['rig']=t.mutate('Revise sequential reading blocks and query color return',lambda:t.h.js(code))
    write(p/'NATIVE_IDENTITY.json',n)
    write(p/'READING_PATCH_COMPLETE.json',{'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'project_sha256':sha256(t.project),'changed':['search chunk order / corresponding blue focus','query return color'],'preserved':['camera motion','3D objects and source geometry','extraction and return','evidence and judgment','copy and complete audio']})
    print(json.dumps({'project':str(t.project),'chunks':len(n['rig']['chunks'])},ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1])
