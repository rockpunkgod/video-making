"""Package and verify the current source worktree, excluding all private assets.

Git-indexed files plus unignored new files are included; no staging/commit/network
operations. Source bytes, individual hashes and the archive are verified locally.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'Video-Production-OS-v0.1'


def included_paths():
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, check=True, capture_output=True)
    paths = sorted(set(p.decode('utf-8') for p in result.stdout.split(b'\0') if p))
    excluded = {'local-data', '.git', 'deliverables', 'build', 'dist', '__pycache__', '.pytest_cache'}
    return [p for p in paths if not set(PurePosixPath(p).parts) & excluded and (ROOT / p).is_file()]


def package(output):
    paths = included_paths()
    records = [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest(),
                'bytes': (ROOT / p).stat().st_size} for p in paths]
    manifest = {'version': '0.1.0', 'source': 'current reviewed worktree', 'files': records,
                'private_assets_included': False, 'git_history_included': False}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for r in records:
            archive.writestr(PREFIX + '/' + r['path'], (ROOT / r['path']).read_bytes())
        archive.writestr(PREFIX + '/DELIVERY_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC verification failed')
        for r in records:
            if hashlib.sha256(archive.read(PREFIX + '/' + r['path'])).hexdigest() != r['sha256']:
                raise ValueError('Delivery byte mismatch: ' + r['path'])
    result = {'archive': output.name, 'file_count': len(records) + 1, 'bytes': output.stat().st_size,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'per_file_verification': 'PASS'}
    output.with_suffix('.sha256.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(ROOT / 'deliverables/Video-Production-OS-v0.1.zip'))
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))
