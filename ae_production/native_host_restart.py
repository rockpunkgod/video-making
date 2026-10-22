"""Normal checkpoint restart of the exact saved, owned interactive AE host.

No process is force-terminated. Windows Explorer performs the normal launch in
the installed application directory. A disconnected or changed host is never
implicitly taken over or treated as permission to repeat a prior write.
"""
import ctypes
from ctypes import wintypes
import json
import os
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


def activate_observed_panel(observed, executable):
    """Open the installed panel in this new host, without opening a project.

    Adobe's dynamic extension command IDs need real menu input; sending a
    WM_COMMAND can appear successful while leaving the panel closed.
    """
    # AE may move between monitors with different Windows display scaling.
    # Make menu coordinates local to this automation thread's actual monitor.
    ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    from pywinauto import Desktop
    import win32gui,win32process
    if (not observed.get('MainWindowHandle') or Path(observed['Path']).resolve()!=executable.resolve()):
        raise RuntimeError('Panel activation requires the exact observed restarted executable/window')
    desktop=Desktop(backend='win32');window=desktop.window(handle=observed['MainWindowHandle'])
    if window.process_id()!=observed['Id']:raise RuntimeError('Restarted panel window process changed')
    if any(w.process_id()==observed['Id'] and w.class_name()=='#32770' and w.is_visible()
           for w in desktop.windows()):
        raise RuntimeError('Restarted host has a modal dialog; preserve it without accepting or cancelling')
    menu=window.menu()
    if menu is None:return {'action':'WAITING_FOR_NATIVE_MENU','project_write':False}
    menus=menu.items()
    main=next((m for m in menus if m.text().startswith('窗口') or m.text().startswith('Window')),None)
    if main is None:return {'action':'WAITING_FOR_NATIVE_MENU','project_write':False}
    extension=next((m for m in main.sub_menu().items()
                    if m.text().startswith('扩展') or m.text().startswith('Extensions')),None)
    if extension is None:return {'action':'WAITING_FOR_NATIVE_MENU','project_write':False}
    def focused():
        if win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]!=observed['Id']:
            raise RuntimeError('Observed AE lost foreground; no menu input sent to another application')
    window.set_focus();focused();main.click_input()
    focused();extension.click_input()
    panel=next((m for m in extension.sub_menu().items() if m.text().strip()=='ae-mcp'),None)
    if panel is None:raise RuntimeError('Installed ae-mcp panel is unavailable')
    opened=bool(panel.state() & 8)
    # The menu toggles the panel; never close one that is already present.
    if not opened:
        focused();panel.click_input()
    if window.process_id()!=observed['Id']:raise RuntimeError('Panel activation process changed')
    return {'process_id':observed['Id'],'window_handle':observed['MainWindowHandle'],
            'executable':str(executable),'action':'ALREADY_OPEN_NOT_TOGGLED' if opened else 'OPEN_EXISTING_INSTALLED_PANEL',
            'project_write':False,'new_application_launch':False}


def observed_panel_binding(rows, processes, observed):
    """Resolve a missing connector PID only through live OS parent identities."""
    hosts=[p for p in processes if p['Name'].lower()=='afterfx.exe']
    if (len(hosts)!=1 or hosts[0]['ProcessId']!=observed['Id']
            or Path(hosts[0]['ExecutablePath']).resolve()!=Path(observed['Path']).resolve()):
        raise RuntimeError('Panel reconciliation requires the exact single observed AE host')
    candidates=[]
    by_pid={p['ProcessId']:p for p in processes}
    for row in rows:
        if (row.get('role')!='primary' or row.get('state')!='running' or row.get('pid') is not None
                or row.get('endpoint')!='http://127.0.0.1:11488/mcp'):continue
        chain=[];pid=row.get('cepPid')
        for _ in range(8):
            p=by_pid.get(pid)
            if not p or pid in [x['ProcessId'] for x in chain]:break
            chain.append(p)
            if pid==observed['Id']:break
            if p['Name'].lower()!='cephtmlengine.exe':break
            pid=p['ParentProcessId']
        if len(chain)>=2 and chain[-1]['ProcessId']==observed['Id']:
            candidates.append({'before':row,'observed_ancestry':chain,'pid':observed['Id']})
    if len(candidates)>1:raise RuntimeError('Multiple connector panels match the same AE; preserve them')
    return candidates[0] if candidates else None


def reconcile_observed_panel(folder, observed):
    """Repair startup PID discovery metadata, not ownership or project state."""
    registry=Path.home()/'.ae-mcp/instances/registry.json'
    module=Path(os.environ.get('APPDATA',''))/'Adobe/CEP/extensions/com.aemcp.panel/host/instance-registry.js'
    if not registry.exists() or not module.exists():return None
    rows=json.loads(registry.read_text('utf-8'))['instances']
    if not any(r.get('state')=='running' and r.get('pid') is None for r in rows):return None
    script='[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);ConvertTo-Json -InputObject @(Get-CimInstance Win32_Process -Filter "Name=\'AfterFX.exe\' OR Name=\'CEPHtmlEngine.exe\'" | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath) -Compress'
    result=subprocess.check_output(['powershell','-NoProfile','-Command',script],
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    binding=observed_panel_binding(rows,
                                  json.loads(result.decode('utf-8-sig')),observed)
    if not binding:return None
    if process_absent(binding['pid']) or any(process_absent(p['ProcessId']) for p in binding['observed_ancestry']):
        raise RuntimeError('Observed panel ancestry exited before reconciliation')
    # Use the installed registry's locked update. Preserve workspace, state,
    # resource limits and all uncertain dispatches; Host.identity still follows.
    code="""const fs=require('fs');const b=JSON.parse(fs.readFileSync(0,'utf8'));
const {InstanceRegistry}=require(b.module);(async()=>{const r=new InstanceRegistry();
const before=await r.get(b.before.instanceId);
for(const k of ['pid','cepPid','state','projectPath','workspaceId','endpoint'])
 if(before[k]!==b.before[k])throw Error('Observed registry changed before PID repair');
for(const p of b.observed_ancestry)process.kill(p.ProcessId,0);
const after=await r.update(before.instanceId,{pid:b.pid});
console.log(JSON.stringify(after));})().catch(e=>{console.error(e);process.exitCode=1});"""
    result=subprocess.run(['node','-e',code],input=json.dumps({**binding,'module':str(module)}),
                          capture_output=True,text=True,encoding='utf-8',check=True,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    receipt={**binding,'after':json.loads(result.stdout),'project_mutation':False,
             'ownership_state_changed':False,'budget_changed':False}
    write(folder/('OBSERVED_PANEL_PID_'+str(time.time_ns())+'.json'),receipt)
    return receipt


def open_verified_checkpoint(fresh, record):
    """Admit only the empty replacement host proved by this normal restart."""
    from ae_production.authored_native import current_native
    _,_,native=current_native(fresh.folder)
    actual=fresh.identity();before=record['before'];project_sha=record['saved_project_sha256']
    if (record['state'] not in ('NORMAL_DESKTOP_LAUNCH_REQUESTED','STARTUP_UNAVAILABLE')
            or record.get('forced_termination') is not False
            or not process_absent(before['process_id']) or fresh.pid==before['process_id']
            or actual!={'process_id':fresh.pid,'project_path':'','target_id':'none','dirty':False,'rendering':False}
            or Path(record['saved_project']).resolve()!=fresh.project.resolve()
            or sha256(fresh.project)!=project_sha
            or before['target_id']!='comp:'+str(native['comp_id'])):
        raise ValueError('Saved restart does not prove this empty replacement host and exact checkpoint')
    target={k:actual[k] for k in ('process_id','project_path','target_id')}
    after={**target,'project_path':str(fresh.project.resolve()),'target_id':before['target_id']}
    lease=HostOwnership('after_effects','/root',fresh.folder.name,target,Path(fresh.h['ownership_directory']))
    lease.acquire();receipt=fresh.folder/'dispatch'/str(time.time_ns());receipt.parent.mkdir(exist_ok=True)
    write(receipt.with_suffix('.pending.json'),{'label':'Open verified empty restart checkpoint','before':actual,'token':lease.record['token'],'saved_project_sha256':project_sha})
    code='if(app.project.numItems||app.project.dirty)throw Error("New host is not empty");app.open(new File('+json.dumps(fresh.project.as_posix())+'));var c=app.project.itemByID('+str(native['comp_id'])+');for(var i=1;i<=app.project.numItems;i++)app.project.item(i).selected=false;c.selected=true;c.openInViewer();return {project:app.project.file.fsName,comp_id:c.id};'
    def operation():
        try:r=fresh.js(code)
        except BaseException as error:write(receipt.with_suffix('.error.json'),{'error':str(error)});raise
        write(receipt.with_suffix('.transport.json'),r);return r
    result=lease.mutate(fresh.identity,operation,target_after=after)
    if sha256(fresh.project)!=project_sha:raise ValueError('Saved checkpoint changed during open; retain ownership for inspection')
    observed=fresh.identity();lease.release(fresh.identity)
    write(receipt.with_suffix('.complete.json'),{'result':result,'identity':observed,'token':lease.record['token']})
    return result


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
    last=None;panel_attempted=False
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
                open_verified_checkpoint(fresh,record)
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
            try:started=process('AfterFX')
            except RuntimeError:started=None
            if started and started['Id']!=h.pid and started.get('MainWindowHandle'):
                if Path(started['Path']).resolve()!=executable.resolve():
                    raise RuntimeError('Restarted executable changed; preserve the observed host')
                # The panel may register after its first visible menu state.
                # PID observation remains independent of the one UI activation.
                if reconcile_observed_panel(h.folder,started):
                    continue # Repeat only fresh identity reads, not an AE write.
                if not panel_attempted:
                    record.update(panel_activation_requested={'process_id':started['Id'],
                        'window_handle':started['MainWindowHandle']});write(path,record)
                    activation=activate_observed_panel(started,executable)
                    if activation.get('action')!='WAITING_FOR_NATIVE_MENU':
                        panel_attempted=True;record['panel_activation']=activation;write(path,record)
        time.sleep(1)
    record.update(state='STARTUP_UNAVAILABLE',last_error=str(last));write(path,record)
    raise RuntimeError('Saved native restart retained; startup did not become available: '+str(last))
