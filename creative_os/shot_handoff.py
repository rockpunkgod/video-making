"""Build an internal P3 handoff in a fresh directory without controlling Adobe."""
import argparse
from pathlib import Path

from video_contracts import read, write
from .shot_script import compile_shot_script
from .camera_plan import camera_plan


def build(request):
    script = read(request['script'])
    bundles = {key: read(path) for key,path in request['bundles'].items()}
    layouts = {key: read(path) for key,path in request['layouts'].items()}
    style = read(request['style'])
    handoff = compile_shot_script(script, bundles, layouts, style)
    handoff['camera'] = camera_plan(script, layouts, style)
    return handoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    handoff = build(read(args.request))
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output/'SHOT_HANDOFF.json', handoff)
    lines = ['# P3 镜头后端审阅', '', '仅机械校验通过；AE 原生接入和画面审核尚未执行。', '',
             '| 动作 | 开始秒 | 结束秒 | 原词目标 |', '|---|---:|---:|---|']
    for row in handoff['actions']:
        lines.append(f"| {row['action']} | {row['at']:.3f} | {row['end']:.3f} | {', '.join(row.get('targets', []))} |")
    lines += ['', '镜头焦点：', '']
    for cue in handoff['camera']['cues']:
        lines.append(f"- {cue['at']:.3f}s：{cue['object_id']} / 窗口 {cue['window_index']} / {cue['state']} / {cue['speed_tier']}")
    lines += ['', '公开发布资格：false。源文、教学动作和答案均不由本模块生成。',
              '具体视觉参数按输入 style 原样传递，尚未验证其原生执行效果。']
    (args.output/'REVIEW.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(args.output/'REVIEW.md')


if __name__ == '__main__':
    main()
