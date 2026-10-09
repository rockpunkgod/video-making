"""Preserve every user-supplied source byte in a private immutable snapshot.

Copying an answer document is not its Reveal: this command does not decode any
source body, select an answer, or provide it to an analyzer.
"""
import argparse
import json
from pathlib import Path

from scripts.ingest_exam_sources import freeze, freeze_json, sha

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'local-data/organized-pdfs/source-manifest.json'

def run(manifest_path=DEFAULT, output_root=None):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    source_root = Path(manifest['source_root']).resolve()
    output_root = Path(output_root or manifest_path.parent/'originals').resolve()
    if output_root == source_root or output_root.is_relative_to(source_root):
        raise ValueError('Never write into the supplied source directory')
    records = []
    for row in sorted(manifest['files'], key=lambda r:r['relative_path']):
        path = (source_root / row['relative_path'].replace('\\','/')).resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            raise ValueError('Missing/unsafe source: '+row['relative_path'])
        data = path.read_bytes()
        if sha(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('Source changed since inventory: '+row['relative_path'])
        target = output_root/'files'/(row['sha256']+row['extension'])
        freeze(target,data)
        if sha(target.read_bytes()) != row['sha256'] or sha(path.read_bytes()) != row['sha256']:
            raise ValueError('Source/snapshot hash differs: '+row['relative_path'])
        records.append({**row,'frozen_file':target.relative_to(output_root).as_posix(),
                        'body_exposure':'binary_snapshot_only_not_decoded'})
    result = {'schema_version':'1.0.0','source_root':str(source_root),
              'source_manifest_sha256':sha(manifest_path.read_bytes()),
              'file_count':len(records),'total_bytes':sum(r['bytes'] for r in records),
              'source_rights':'private_user_research_redistribution_not_verified',
              'source_authenticity':'unverified','records':records}
    freeze_json(output_root/'snapshot.json',result)
    return {k:result[k] for k in ('file_count','total_bytes','source_manifest_sha256')}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=DEFAULT)
    p.add_argument('--output-root',type=Path)
    a=p.parse_args(); print(json.dumps(run(a.manifest,a.output_root),ensure_ascii=False))

if __name__=='__main__': main()
