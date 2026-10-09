"""Windows-only memory guard for a new, owned native render process tree.

Never assigns or terminates existing Adobe processes. A closed Job releases
only descendants of the process launched here; it does not clean disk assets.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import time
import threading
from contextlib import contextmanager


class MemoryStatus(ctypes.Structure):
    _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[
        (name,ctypes.c_ulonglong) for name in ('total_physical','free_physical','total_page',
            'free_page','total_virtual','free_virtual','extended')]


class BasicLimits(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),
        ('flags',wintypes.DWORD),('minimum_working',ctypes.c_size_t),('maximum_working',ctypes.c_size_t),
        ('active_processes',wintypes.DWORD),('affinity',ctypes.c_size_t),
        ('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_=[('basic',BasicLimits),('io',ctypes.c_ulonglong*6),
        ('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
        ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]


def available_memory():
    if os.name!='nt':raise RuntimeError('Windows native guard required')
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return status.free_physical


class ProcessCounters(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('page_faults',wintypes.DWORD)]+[
        (name,ctypes.c_size_t) for name in ('peak_working','working','peak_paged','paged',
            'peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]


def process_memory(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000|0x10,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        counter=ProcessCounters();counter.size=ctypes.sizeof(counter)
        api=ctypes.WinDLL('psapi',use_last_error=True)
        api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
        if not api.GetProcessMemoryInfo(handle,ctypes.byref(counter),counter.size):raise ctypes.WinError(ctypes.get_last_error())
        return counter.private,counter.working
    finally:kernel.CloseHandle(handle)


def stop_reason(free,private,minimum_free_gib=1,limit_gib=None):
    if free<minimum_free_gib*2**30:return 'LOW_SYSTEM_MEMORY'
    if limit_gib is not None and private>limit_gib*2**30:return 'RENDER_PROCESS_BUDGET'
    return None


@contextmanager
def monitor_existing_render(pid,hwnd,minimum_free_gib=1,limit_gib=None):
    """Request Escape for this render; never terminate an existing AE process."""
    if (os.name!='nt' or type(pid) is not int or pid<=0 or type(hwnd) is not int or hwnd<=0
            or not 1<=minimum_free_gib<=20 or (limit_gib is not None and not 1<=limit_gib<=256)):
        raise ValueError('Explicit Windows memory reserve and process budget required')
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    owner=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
    if owner.value!=pid:raise ValueError('Live render window and PID must match')
    user.GetLastActivePopup.argtypes=[wintypes.HWND];user.GetLastActivePopup.restype=wintypes.HWND
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    record={'minimum_free_bytes':available_memory(),'peak_private_bytes':0,'peak_working_bytes':0,
        'stop_reason':None,'abort_requested':False,'existing_process_terminated':False}
    ended=threading.Event()
    def watch():
        while not ended.is_set():
            try:
                free=available_memory();private,working=process_memory(pid)
                record['minimum_free_bytes']=min(record['minimum_free_bytes'],free)
                record['peak_private_bytes']=max(record['peak_private_bytes'],private)
                record['peak_working_bytes']=max(record['peak_working_bytes'],working)
                reason=stop_reason(free,private,minimum_free_gib,limit_gib)
                if reason:
                    record['stop_reason']=reason
                    popup=user.GetLastActivePopup(hwnd)
                    for window in set([hwnd,popup]):
                        if window:
                            user.PostMessageW(window,0x100,27,1)
                            user.PostMessageW(window,0x101,27,0xC0000001)
                    record['abort_requested']=True;return
            except Exception as error:
                record['monitor_error']=str(error);return
            ended.wait(.25)
    thread=threading.Thread(target=watch,daemon=True);thread.start()
    try:yield record
    finally:ended.set();thread.join(timeout=2)


def guarded_run(command,log_path,limit_gib=None,minimum_free_gib=1,timeout=240):
    if (os.name!='nt' or (limit_gib is not None and not 1<=limit_gib<=256) or not 1<=minimum_free_gib<=20
            or not 1<=timeout<=600):raise ValueError('Conservative explicit memory/time limits required')
    threshold=int(minimum_free_gib*2**30)
    initial=available_memory()
    if initial<threshold:raise RuntimeError('Insufficient free memory; render not launched')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];kernel.CreateJobObjectW.restype=wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    job=kernel.CreateJobObjectW(None,None)
    if not job:raise ctypes.WinError(ctypes.get_last_error())
    process=None;start=time.monotonic();minimum=initial
    try:
        limits=ExtendedLimits()
        # KILL_ON_JOB_CLOSE | JOB_MEMORY. A renderer allocation failure is safer
        # than allowing this experimental child tree to exhaust the workstation.
        limits.basic.flags=0x2000|0x200
        # New workers receive current available RAM minus the explicit system
        # reserve; no fixed 10 GiB ceiling. Never budget memory already in use.
        limits.job_memory=initial-threshold if limit_gib is None else min(int(limit_gib*2**30),initial-threshold)
        if not kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        with open(log_path,'xb') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if not kernel.AssignProcessToJobObject(job,int(process._handle)):
                process.terminate();process.wait(timeout=10)
                raise ctypes.WinError(ctypes.get_last_error())
            while process.poll() is None:
                free=available_memory();minimum=min(minimum,free)
                if free<threshold:raise RuntimeError('Memory guard stopped owned render: low system memory')
                if time.monotonic()-start>timeout:raise TimeoutError('Owned render exceeded bounded runtime')
                time.sleep(.25)
            return {'exit_code':process.returncode,'elapsed_seconds':time.monotonic()-start,
                'minimum_free_bytes':minimum,'job_limit_bytes':limits.job_memory,
                'minimum_free_limit_bytes':threshold,'existing_processes_untouched':True}
    finally:
        kernel.CloseHandle(job)
        if process is not None and process.poll() is None:process.wait(timeout=15)
