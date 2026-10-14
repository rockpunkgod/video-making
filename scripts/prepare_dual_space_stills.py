"""Prepare a standalone AE script from a local, source-bound P1 design request."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    output = Path(request['output']).resolve()
    if not output.is_relative_to(ROOT / 'local-data'):
        raise ValueError('Real design frames must remain in local-data')
    if request.get('public_render_ready') is not False:
        raise ValueError('P1 design does not grant release')
    if not request.get('source_sha'):
        raise ValueError('Frozen source file bindings required')
    for name, digest in request['source_sha'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen source changed')
    ids = [f['id'] for f in request['frames']]
    if len(ids) != len(set(ids)) or any(not x.replace('_', '').isalnum() for x in ids):
        raise ValueError('Unique filename-safe frame IDs required')
    if any((output / (x + '.png')).exists() for x in ids):
        raise ValueError('Preserve old renders: choose a fresh output directory')
    checkpoint = Path(request['preserve_session_path']).resolve()
    if not checkpoint.is_relative_to(output) or checkpoint.exists():
        raise ValueError('Fresh session checkpoint inside output required')
    output.mkdir(parents=True, exist_ok=True)
    code = 'var DUAL_SPACE_DATA=' + json.dumps(request, ensure_ascii=True) + ';\n'
    code += (ROOT / 'ae/templates/stills/dual-space-stills.jsx').read_text(encoding='utf-8')
    path = output / 'render.jsx'
    path.write_text(code, encoding='utf-8')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    print(prepare(parser.parse_args().request))
