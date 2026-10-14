"""Render a local backend proof sheet; does not modify production frontend files."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creative_os.typeset import typeset
from creative_os.semantic_text_layout import layout_words, focus_windows


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(request_path, output):
    request = json.loads(Path(request_path).read_text(encoding='utf-8'))
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / 'local-data') or output.exists():
        raise ValueError('Choose a fresh local-data directory')
    style_path, font_path = Path(request['style']), Path(request['font'])
    style = json.loads(style_path.read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    palette = style['palette']; size = style['type_scale']['focus_text']
    leading = style['type_scale']['focus_line_height'] / size
    width = style['layout']['focus_width']; limit = style['layout']['focus_max_lines']
    font = ImageFont.truetype(str(font_path), size*2)
    fallback_path=Path(request['fallback_font']) if request.get('fallback_font') else None
    fallback=ImageFont.truetype(str(fallback_path),size*2) if fallback_path else None
    # Reviewer labels are outside the production reading surface.
    label_font = ImageFont.truetype(str(font_path), 28*2)
    records = []; sections = []; overview = []
    for index, item in enumerate(request['cases']):
        source = Path(item['bundle']); before_sha = digest(source)
        bundle = json.loads(source.read_text(encoding='utf-8'))
        text = bundle['source_snapshot']['passage']
        plan = typeset(text, font_path, style, fallback_font_path=fallback_path)
        legacy = layout_words(text, str(font_path), size, width, leading=leading,fallback_font_path=fallback_path)
        variants = [('before', legacy, focus_windows(legacy, limit)),
                    ('after', plan['words'], plan['focus_windows'])]
        (output / f'case-{index+1}-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        pairs = {}
        for name, words, windows in variants:
            images = []
            for n, window in enumerate(windows):
                im = Image.new('RGB', (3840,2160), palette['environment'])
                draw = ImageDraw.Draw(im)
                draw.rectangle((192,128,3648,1848), fill=palette['paper'])
                selected = [w for w in words if window['start'] <= w['start'] < window['end']]
                first_y = selected[0]['y']
                for word in selected:
                    draw.text((int((180+word['x'])*2),int((230+word['y']-first_y)*2)),
                              word['text'],font=fallback if fallback and re.search(r'[\u3400-\u9fff]',word['text']) else font,fill=palette['ink'],anchor='ls')
                label=f'{name.upper()}   /   {n+1:02d} of {len(windows):02d}   /   {size}px @1080p'
                draw.text((192,1970),label,font=label_font,fill=palette['paper'])
                filename=f'case-{index+1}-{name}-{n+1:02d}.png'
                im.save(output/filename)
                im.resize((1280,720),Image.Resampling.LANCZOS).save(output/filename.replace('.png','-720.png'))
                phone=Image.new('RGB',(844,390),palette['environment']); small=im.copy();small.thumbnail((844,390),Image.Resampling.LANCZOS);phone.paste(small,((844-small.width)//2,0));phone.save(output/filename.replace('.png','-phone.png'))
                images.append(filename)
                if n==0: overview.append(im.resize((960,540),Image.Resampling.LANCZOS))
            pairs[name]=images
        assert digest(source)==before_sha
        assert [text[w['start']:w['end']] for w in plan['words']]==[w['text'] for w in legacy]
        record=dict(label=item['label'],source_sha256=before_sha,source_unchanged=True,
            tokens=len(plan['words']),before_lines=legacy[-1]['line']+1 if legacy else 0,
            after_lines=len(plan['lines']),before_windows=len(pairs['before']),after_windows=len(pairs['after']),
            warnings=[dict(line=l['line']+1,reasons=l['warnings']) for l in plan['lines'] if l['warnings']],images=pairs)
        records.append(record)
        rows=[]
        for n in range(max(map(len,pairs.values()))):
            cells=[]
            for name in ('before','after'):
                if n>=len(pairs[name]):cells.append('<div>已读完，没有省略原词。</div>');continue
                filename=pairs[name][n]
                cells.append(f'<a href="{filename}"><img src="{filename.replace(".png","-720.png")}"></a>')
            rows.append('<div class="pair">'+''.join(cells)+'</div>')
        warnings=html.escape(json.dumps(record['warnings'],ensure_ascii=False))
        sections.append('<h2>'+html.escape(item['label'])+'</h2><p>'+f'原有 {record["before_lines"]} 行 / {record["before_windows"]} 窗 → P2 {record["after_lines"]} 行 / {record["after_windows"]} 窗。'+ '</p><details><summary>排版复看提示（不隐藏无法满足的约束）</summary><pre>'+warnings+'</pre></details><div class="pair"><b>左：原有断行</b><b>右：P2 平衡断行</b></div>'+''.join(rows))
    sheet=Image.new('RGB',(1920,540*len(records)),palette['environment'])
    for i,im in enumerate(overview):sheet.paste(im,((i%2)*960,(i//2)*540))
    sheet.save(output/'COMPARE.jpg',quality=95)
    page='''<meta charset="utf-8"><title>P2 排版审阅</title><style>body{background:#17181a;color:#f2f0ea;font:18px system-ui;margin:32px}p{line-height:1.8}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:16px 0}img{width:100%}a{color:inherit}</style><h1>P2 排版审阅</h1><p>同一原文、字体、字号和窗口宽度，只比较断行。点击图片查看 4K。左右按窗口序号排列，文字进度不一定相同。</p><p>这是后端测量预览，不是 AE 成片。两份历史教学资产只用于排版核对；此页面不授予教学或发布资格。实际前端设计未修改。</p>'''+''.join(sections)
    (output/'REVIEW.html').write_text(page,encoding='utf-8')
    (output/'report.json').write_text(json.dumps(dict(cases=records,style_sha256=digest(style_path),font_sha256=digest(font_path),geometry='PROVISIONAL_REQUIRES_AE_MEASUREMENT',production_frontend_modified=False),ensure_ascii=False,indent=2),encoding='utf-8')
    return records


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request');p.add_argument('output')
    a=p.parse_args();print(json.dumps(build(a.request,a.output),ensure_ascii=True))
