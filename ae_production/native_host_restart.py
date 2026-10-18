"""Normal checkpoint restart of the exact saved, owned interactive AE host.

No process is force-terminated. Windows Explorer performs the normal launch in
the installed application directory. A disconnected or changed host is never
implicitly taken over or treated as permission to repeat a prior write.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import time

from ae_production.host_ownership import HostOwnership
from scripts.voice_delivery import sha256
from video_contracts import write


def process_absent(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x100000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return True
        raise ctypes.WinError(ctypes.get_last_error())
    try:return kernel.WaitForSingleObject(handle,0)==0
    finally:kernel.CloseHandle(handle)


def restart_saved_host(h,cursor):
    from ae_production.authored_native import Host,process,current_native
    before=h.identity()
    _,_,native=current_native(h.folder)
    if (Path(before['project_path']).resolve()!=h.project.resolve()
            or before.get('process_id')!=h.pid or before.get('target_id')!='comp:'+str(native['comp_id'])
            or before.get('dirty') is not False or before.get('rendering') is not False):
        raise RuntimeError('Only this clean saved native project may restart')
    observed=process('AfterFX')
    if observed['Id']!=h.pid:raise RuntimeError('Native process changed before restart')
    executable=Path(observed['Path']);project_sha=sha256(h.project)
    name=f'HOST_RESTART_{cursor:05d}_{time.time_ns()}'
    path=h.folder/(name+'.json')
    target={k:before[k] for k in ('process_id','project_path','target_id')}
    lease=HostOwnership('after_effects','/root',h.folder.name,target,Path(h.h['ownership_directory']))
    lease.acquire()
    record={'schema':'saved-native-host-restart/v1','cursor':cursor,'before':before,
            'saved_project':str(h.project),'saved_project_sha256':project_sha,
            'token':lease.record['token'],'forced_termination':False,'state':'NORMAL_SHUTDOWN_REQUESTED'}
    write(path,record)
    receipt=lease.close_saved_host(h.identity,lambda:h.js('app.quit();return {quit_requested:true};',timeout=10),
                                  lambda:process_absent(h.pid),{str(h.project):project_sha})
    record.update(shutdown=receipt,state='EXACT_OWNED_HOST_EXITED');write(path,record)
    # Explorer launches through its normal desktop context.
    # This avoids inheriting a tool runtime's DLL/CEP environment. Show=0 keeps
    # a background restart from stealing the user's foreground window.
    def ps_quote(value):return "'"+str(value).replace("'","''")+"'"
    script="Start-Process -FilePath 'C:\\Windows\\explorer.exe' -ArgumentList "+ps_quote('"'+str(executable)+'"')+" -WindowStyle Hidden"
    subprocess.run(['powershell','-NoProfile','-Command',script],check=True,
                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    record.update(state='NORMAL_DESKTOP_LAUNCH_REQUESTED',launch='Windows Explorer executable open',
                  executable=str(executable),working_directory=str(executable.parent));write(path,record)
    last=None
    for _ in range(150):
        try:
            fresh=Host(h.folder,'after_effects');actual=fresh.identity()
            if actual.get('process_id')!=fresh.pid:raise ValueError('New host process identity changed before opening')
            if fresh.pid==h.pid:raise RuntimeError('The closed host PID was reused; inspect restart')
            if actual.get('dirty') is not False or actual.get('rendering') is not False:
                raise RuntimeError('New host is not clean and idle')
            if actual['project_path'] not in ('',str(h.project.resolve())):
                raise RuntimeError('New host opened another project; preserve it')
            if sha256(h.project)!=project_sha:raise ValueError('Saved checkpoint changed before opening')
            if actual['project_path']=='':
                code='if(app.project.numItems||app.project.dirty)throw Error("New host is not empty");app.open(new File('+json.dumps(h.project.as_posix())+'));var c=app.project.itemByID('+before['target_id'].split(':')[1]+');for(var i=1;i<=app.project.numItems;i++)app.project.item(i).selected=false;c.selected=true;c.openInViewer();return {project:app.project.file.fsName,comp_id:c.id};'
                fresh.mutation_js(code,'Open exact saved native restart checkpoint',
                    {'process_id':fresh.pid,'project_path':str(h.project.resolve()),'target_id':before['target_id']})
            elif actual['target_id']!=before['target_id']:
                raise RuntimeError('Restarted native target differs; inspect without replay')
            if sha256(h.project)!=project_sha:raise ValueError('Saved checkpoint changed during normal restart')
            after=fresh.identity()
            expected={'process_id':fresh.pid,'project_path':str(h.project.resolve()),
                      'target_id':before['target_id'],'dirty':False,'rendering':False}
            if any(after.get(k)!=v for k,v in expected.items()):
                raise ValueError('Restarted saved target identity changed before completion')
            record.update(state='RESTARTED_SAVED_TARGET_VERIFIED',after=after);write(path,record)
            return fresh
        except Exception as error:
            last=error
            # Opening the saved project is a mutation: an existing lock means
            # its result needs explicit inspection, never another loop attempt.
            if (Path(h.h['ownership_directory'])/'after_effects.json').exists():raise
            if isinstance(error,(ValueError,FileExistsError)) or 'another project' in str(error) or 'target differs' in str(error):raise
        time.sleep(1)
    record.update(state='STARTUP_UNAVAILABLE',last_error=str(last));write(path,record)
    raise RuntimeError('Saved native restart retained; startup did not become available: '+str(last))
