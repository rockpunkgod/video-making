"""Make review sheets from completed native P1 frames; never edit their pixels."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw


def review(folder):
    folder = Path(folder).resolve()
    receipt = json.loads((folder / 'native-receipt.json').read_text(encoding='utf-8'))
    request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
    assert [f['id'] for f in receipt['frames']] == [f['id'] for f in request['frames']]
    for path, sha in request['source_sha'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, 'Frozen source changed'
    sheet = Image.new('RGB', (1920, 590 * ((len(receipt['frames']) + 1) // 2)), '#17181A')
    draw = ImageDraw.Draw(sheet)
    rows = []
    for i, frame in enumerate(receipt['frames']):
        assert not frame['font_substitutions'], 'Font substitution'
        path = folder / (frame['id'] + '.png')
        with Image.open(path) as im:
            im.load()
            assert im.size == (3840, 2160)
            decoded = im.convert('RGB')
            assert max(decoded.getextrema()[0]) > 180, 'Unexpected blank/dark frame'
            thumb = decoded.resize((960, 540), Image.Resampling.LANCZOS)
            x, y = (i % 2) * 960, (i // 2) * 590
            sheet.paste(thumb, (x, y))
            draw.text((x + 20, y + 554), frame['id'], fill='#F2F0EA')
            decoded.resize((1280, 720), Image.Resampling.LANCZOS).save(folder / (frame['id'] + '-720.png'))
            phone = Image.new('RGB', (844, 390), '#17181A')
            decoded.thumbnail((844, 390), Image.Resampling.LANCZOS)
            phone.paste(decoded, ((844 - decoded.width) // 2, 0))
            phone.save(folder / (frame['id'] + '-phone.png'))
        rows.append(dict(id=frame['id'],audio=False,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    sheet.save(folder / 'CONTACT_SHEET.jpg', quality=95)
    cards = ''.join('<figure><a href="'+html.escape(r['id'])+'.png"><img src="'+html.escape(r['id'])+'-720.png"></a><figcaption>'+html.escape(r['id'])+'</figcaption></figure>' for r in rows)
    (folder / 'REVIEW.html').write_text('<meta charset="utf-8"><title>P1 明暗双场</title><style>body{background:#17181a;color:#f2f0ea;font:18px sans-serif;margin:40px}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}figure{margin:0}img{width:100%}</style><h1>P1 · 明暗双场</h1><p>原生 4K 静帧设计稿；历史资产参考，非当前教学放行。点击看原图。光变、阴影变化与运动节奏尚未测试。</p><main>'+cards+'</main>', encoding='utf-8')
    (folder / 'review-checks.json').write_text(json.dumps(dict(frames=rows,frozen_inputs_unchanged=True,font_substitutions=0,motion_tested=False,public_render_ready=False),indent=2),encoding='utf-8')
    return folder / 'REVIEW.html'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    print(review(parser.parse_args().folder))
