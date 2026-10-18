"""Bounded native shutter check on this trial; never replay an unknown capture."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from run import Trial, read, write, sha256


def main(folder):
    trial=Trial(folder);p=trial.folder;n=trial.native()
    receipt=p/'BLUR_PIXEL_QA.json'
    if receipt.exists():
        raise FileExistsError('Inspect existing blur check; no replay')
    state=trial.h.js('var c=app.project.itemByID('+str(n['B_source'])+');return {enabled:c.motionBlur,angle:c.shutterAngle,phase:c.shutterPhase};')
    assert state=={'enabled':True,'angle':120,'phase':-60},state
    after={'process_id':trial.h.pid,'project_path':str(trial.project),'target_id':'comp:'+str(n['B'])}
    captures={}
    for label in ('on','off'):
        dest=p/('BLUR_'+label.upper()+'.json')
        if dest.exists():raise FileExistsError('Inspect incomplete blur experiment')
        if label=='off':
            trial.mutate('Temporarily disable B blur for paired pixel comparison',lambda:trial.h.js('var c=app.project.itemByID('+str(n['B_source'])+');c.motionBlur=false;app.purge(PurgeTarget.ALL_CACHES);app.project.save();return {blur:c.motionBlur};'))
        r=trial.mutate('Capture B blur '+label,lambda:trial.h.c.call('ae_previewFrame',{'comp_id':str(n['B']),'times':[17.5,18.7,21.5,26.5],'layout':'grid','grid_max_side':2048,'out_dir':str(p/'blur-previews'),'include_base64':False,'scale':.5},timeout=240),after=after)
        write(dest,r);captures[label]=r
    # Restore only after both captures have a terminal success receipt.
    restored=trial.mutate('Restore B authored shutter setting',lambda:trial.h.js('var c=app.project.itemByID('+str(n['B_source'])+');c.motionBlur=true;app.purge(PurgeTarget.ALL_CACHES);app.project.save();return {enabled:c.motionBlur,angle:c.shutterAngle,phase:c.shutterPhase};'))
    assert restored==state
    rows=[]
    for a,b in zip(captures['on']['frames'],captures['off']['frames']):
        aa=np.asarray(Image.open(a['path']).convert('RGB'),dtype=float);bb=np.asarray(Image.open(b['path']).convert('RGB'),dtype=float)
        d=np.abs(aa-bb)
        rows.append({'time':a['time'],'mean_rgb_difference':float(d.mean()),'fraction_changed_more_than_one':float(np.mean(d.max(axis=2)>1)),'on':a['path'],'off':b['path'],'on_sha256':sha256(a['path']),'off_sha256':sha256(b['path'])})
    assert any(x['fraction_changed_more_than_one']>0 for x in rows[:-1]),'No moving-frame blur effect measured'
    result={'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'restored':restored,'frames':rows,'scope':'Paired native frames isolate shutter effect; not proof of reading comprehension or human visual approval','human_review':'PENDING'}
    write(receipt,result)
    print(result)


if __name__=='__main__':main(sys.argv[1])
