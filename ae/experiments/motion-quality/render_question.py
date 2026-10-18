"""Render the actual complete native question in bounded, receipted batches."""
import json,subprocess,sys
from pathlib import Path
from run import Trial,read,write,sha256,base

def release_inactive_pages(pid):
    """Bounded Windows working-set trim; never closes or restarts the AE host."""
    import ctypes
    k=ctypes.WinDLL('kernel32',use_last_error=True);p=ctypes.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.restype=ctypes.c_void_p;k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    p.EmptyWorkingSet.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    h=k.OpenProcess(0x0500,False,pid)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not p.EmptyWorkingSet(h):raise ctypes.WinError(ctypes.get_last_error())
    finally:k.CloseHandle(h)

def main(folder):
    t=Trial(folder);n=t.native();p=t.folder;full=t.i['full_question'];qa=read(p/'NATIVE_QA.json');binding=sha256(p/'NATIVE_IDENTITY.json')
    if qa['status']!='PASS' or qa['native_identity_sha256']!=binding:raise ValueError('Current native reading audit required')
    directory=p/'question-parts';directory.mkdir(exist_ok=True);total=full['frames'];parts=[]
    for start in range(0,total,48):
        end=min(start+48,total);dest=directory/f'B-{start:04}.mp4';receipt=dest.with_suffix('.json')
        if receipt.exists():
            r=read(receipt)
            if r['native_sha256']!=binding or sha256(dest)!=r['sha256']:raise ValueError('Stale native part')
            parts.append(r);continue
        if dest.exists():raise FileExistsError('Inspect unreceipted render; do not replay')
        release_inactive_pages(t.h.pid)
        if base.available_memory()<2*2**30:raise RuntimeError('Insufficient memory reserve')
        code="var c=app.project.itemByID(CID);if(app.project.renderQueue.numItems||c.width!==3840||c.height!==2160||c.frameRate!==24||Math.round(c.duration*24)!==TOTAL)throw Error('Unexpected target');var q=app.project.renderQueue.items.add(c),o=q.outputModule(1),preset=null;for(var i=0;i<o.templates.length;i++)if(o.templates[i].indexOf('H.264')>=0&&o.templates[i].indexOf('15 Mbps')>=0){preset=o.templates[i];break;}if(!preset)throw Error('Missing native preset');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanDuration=(END-START)/24;q.timeSpanStart=START/24;q.skipFrames=0;app.setMultiFrameRenderingConfig(false,25);app.beginSuppressDialogs();try{app.project.renderQueue.render();}finally{app.endSuppressDialogs(false);}var r={done:q.status===RQItemStatus.DONE,status:q.status,start:START,end:END,preset:preset};if(r.done)q.remove();app.purge(PurgeTarget.ALL_CACHES);app.project.save();return r;"
        for k,v in {'CID':str(n['full_question_comp']),'TOTAL':str(total),'DEST':json.dumps(dest.as_posix()),'START':str(start),'END':str(end)}.items():code=code.replace(k,v)
        with base.monitor_existing_render(t.h.pid,t.h.hwnd,minimum_free_gib=1) as memory:
            r=t.mutate('Render complete question '+str(start)+'-'+str(end),lambda:t.h.js(code),after={'process_id':t.h.pid,'project_path':str(t.project),'target_id':'comp:'+str(n['full_question_comp'])})
        r.update(memory=memory,native_sha256=binding,path=str(dest))
        if not r['done']:write(dest.with_suffix('.stopped.json'),r);raise RuntimeError('Render stopped; inspect first')
        stream=next(s for s in base.probe(dest)['streams'] if s['codec_type']=='video')
        if [stream['width'],stream['height'],stream['r_frame_rate'],int(stream['nb_read_frames'])]!=[3840,2160,'24/1',end-start]:raise ValueError('Native frame coverage mismatch')
        r['sha256']=sha256(dest);write(receipt,r);parts.append(r)
        print(json.dumps({'frames':end,'total':total,'percent':round(end/total*100,1),'free_gib':round(memory['minimum_free_bytes']/2**30,2)}),flush=True)
    listing=directory/'concat.txt';listing.write_text(''.join("file '"+Path(r['path']).as_posix()+"'\n" for r in parts),'utf-8')
    picture=p/'media/B_COMPLETE_QUESTION_PICTURE_4K24.mp4'
    if not picture.exists():subprocess.run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-c','copy','-movflags','+faststart',str(picture)],check=True)
    final=p/'media/B_COMPLETE_QUESTION_4K24.mp4'
    if not final.exists():
        args=['ffmpeg','-v','error','-n','-i',str(picture)];filters=[]
        for j,v in enumerate(full['voices']):
            args+=['-i',v['voice']['path']];filters.append(f'[{j+1}:a]adelay={round((v["voice_start"]-full["start"])*48000)}S:all=1[a{j}]')
        filters.append(''.join(f'[a{j}]' for j in range(len(full['voices'])))+f'amix=inputs={len(full["voices"])}:normalize=0,apad,atrim=duration={total/24}[voice]')
        subprocess.run(args+['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[voice]','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(final)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(final),'-f','null','-'],check=True)
    write(p/'RENDER_COMPLETE_QUESTION.json',{'output':str(final),'sha256':sha256(final),'parts':parts,'probe':base.probe(final),'full_decode':'PASS','voices':full['voices'],'native_identity_sha256':binding,'human_review':'PENDING'})
    print(json.dumps({'output':str(final),'frames':total},ensure_ascii=False),flush=True)

if __name__=='__main__':main(sys.argv[1])
