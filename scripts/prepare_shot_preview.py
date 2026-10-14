"""Prepare a fresh native AE preview from a validated local handoff request."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creative_os.shot_handoff import build
from video_contracts import read, write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('request', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    request = read(args.request)
    handoff = build(request)
    preview = request['preview']
    script = handoff['script']
    if (len(script['objects']) != 1 or len(script['targets']) != 1 or script.get('candidate_events')
            or script.get('answers') or [a['action'] for a in script['actions']] !=
            ['locate','dim_world','lift','return','brighten_world']):
        raise ValueError('Native v0.1 preview supports one source locate/lift/return only')
    plan = handoff['layouts'][preview['layout_id']]
    target = script['targets'][0]
    win = plan['focus_windows'][preview['window_index']]
    selected = [w for w in plan['words'] if target['range'][0] <= w['start'] and w['end'] <= target['range'][1]]
    if (not selected or selected[0]['start'] != target['range'][0] or selected[-1]['end'] != target['range'][1]
            or len({w['line'] for w in selected}) != 1 or not win['start'] <= target['range'][0] < target['range'][1] <= win['end']):
        raise ValueError('Preview needs a complete, single-line original word slice in its window')
    out = args.output.resolve()
    if not out.is_relative_to(ROOT/'local-data'):
        raise ValueError('Real media and text must remain in ignored local-data')
    out.mkdir(parents=True, exist_ok=False)
    data = dict(output=out.as_posix(), handoff=handoff, **preview)
    write(out/'SHOT_HANDOFF.json', handoff)
    code = 'var SHOT_PREVIEW='+json.dumps(data, ensure_ascii=True)+';\n'
    code += (ROOT/'ae/templates/shot-handoff-preview.jsx').read_text(encoding='utf-8')
    (out/'build.jsx').write_text(code, encoding='utf-8')
    render = 'var SHOT_PREVIEW_OUTPUT='+json.dumps(out.as_posix(), ensure_ascii=True)+';\n'
    render += (ROOT/'ae/templates/shot-handoff-render.jsx').read_text(encoding='utf-8')
    (out/'render.jsx').write_text(render, encoding='utf-8')
    print(out/'build.jsx')


if __name__ == '__main__':
    main()
