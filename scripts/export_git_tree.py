"""Read a bounded slice of a committed Git tree for connector-based delivery.

Does not write files, refs, credentials, or remote state. Content comes from Git
objects (not Windows working-tree newline conversions).
"""
import argparse
import json
import subprocess
import sys
from core.registry import ROOT

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout

def export(ref,start,count):
    entries=[]
    for line in git('ls-tree','-r','-z',ref).split(b'\0'):
        if not line: continue
        meta,path=line.split(b'\t',1)
        mode,kind,sha=meta.decode('ascii').split()
        if kind!='blob': raise ValueError('Submodules require explicit handling')
        entries.append({'path':path.decode('utf-8'),'mode':mode,'type':'blob','sha':sha})
    selected=entries[start:start+count]
    elements=[]
    for item in selected:
        content=git('cat-file','blob',item['sha']).decode('utf-8')
        elements.append({key:item[key] for key in ['path','mode','type']}|{'content':content})
    return {'ref':ref,'tree_sha':git('rev-parse',ref+'^{tree}').decode().strip(),'total':len(entries),'start':start,'elements':elements}

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(); parser.add_argument('--ref',default='HEAD'); parser.add_argument('--start',type=int,default=0); parser.add_argument('--count',type=int,default=10)
    args=parser.parse_args(); print(json.dumps(export(args.ref,args.start,args.count),ensure_ascii=False))
