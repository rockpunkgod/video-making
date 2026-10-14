"""WCAG sRGB contrast for the actual composited style colors."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def rgb(hex_color):
    if len(hex_color)!=7 or hex_color[0]!='#':raise ValueError('Expected #RRGGBB')
    return [int(hex_color[i:i+2],16)/255 for i in (1,3,5)]


def luminance(color):
    return sum(w*(v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4)
               for w,v in zip((0.2126,0.7152,0.0722),color))


def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+0.05)/(x+0.05)


def evaluate(style):
    palette=style['palette'];rows=[]
    for pair in style['contrast']['combinations']:
        fg=rgb(palette[pair['foreground']]);bg=rgb(palette[pair['background']])
        alpha=pair.get('background_opacity',1)
        if not 0<=alpha<=1:raise ValueError('Invalid fill opacity')
        base=rgb(palette[pair.get('base','paper')]);bg=[x*alpha+y*(1-alpha) for x,y in zip(bg,base)]
        value=contrast(fg,bg)
        rows.append(dict(pair,ratio=round(value,4),passed=value>=pair['minimum']))
    return rows


def report(style):
    rows=evaluate(style)
    lines=['# style-v1 对比度', '', '| 用途 | 实际比值 | 下限 | 结果 |','| --- | ---: | ---: | --- |']
    for row in rows:lines.append(f"| {row['role']} | {row['ratio']:.2f}:1 | {row['minimum']}:1 | {'PASS' if row['passed'] else 'FAIL'} |")
    raw=contrast(rgb(style['palette']['ink']),rgb(style['palette']['attention_orange']))
    lines+=['',f'原指定炭黑与满橙底为 {raw:.2f}:1。保留橙色，满色高亮使用较深墨色；常规正文不变。',
             '比值包含背景合成；景深背景是导航层，不能作为焦点正文的可读性证明。',
             '字幕标准不代表已完成 P3 音频/字幕制作，动态表现不在本次静帧验证范围。']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--style',type=Path,default=ROOT/'ae/design/style-v1.json');p.add_argument('--report',type=Path)
    args=p.parse_args();style=json.loads(args.style.read_text(encoding='utf-8'));text=report(style)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(text,encoding='utf-8')
    print(text)
    raise SystemExit(0 if all(r['passed'] for r in evaluate(style)) else 1)
