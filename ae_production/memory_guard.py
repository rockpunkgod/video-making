"""Windows-only memory guard for a new, owned native render process tree.

Never assigns or terminates existing Adobe processes. A closed Job releases
only descendants of the process launched here; it does not clean disk assets.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import time


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


def guarded_run(command,log_path,limit_gib=10,minimum_free_gib=12,timeout=240):
    if (os.name!='nt' or not 4<=limit_gib<=10 or not 12<=minimum_free_gib<=20
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
        limits.job_memory=int(limit_gib*2**30)
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
