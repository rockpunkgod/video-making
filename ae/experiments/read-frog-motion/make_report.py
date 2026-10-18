"""Assemble the local review document after actual media QA exists."""
from html import escape
from pathlib import Path
import sys
from run import read, write

def speed_svg(rows):
    w,h=1120,300;x0,y0=65,30;pw,ph=1030,220;maximum=2200
    def path(v):return ' '.join(('M' if k==0 else 'L')+f'{x0+r["t"]/12*pw:.2f},{y0+ph-r[v]/maximum*ph:.2f}' for k,r in enumerate(rows))
    lines=''.join(f'<line x1="{x0}" x2="{x0+pw}" y1="{y0+ph-y/maximum*ph}" y2="{y0+ph-y/maximum*ph}" stroke="#e7eae7"/><text x="4" y="{y0+ph-y/maximum*ph+5}" font-size="13">{y}</text>' for y in (0,500,1000,1500,2000))
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="原生相机逐帧速度对照"><g font-family="Segoe UI,Microsoft YaHei" fill="#43515a">{lines}<path d="{path("A_speed")}" fill="none" stroke="#9c9b94" stroke-width="2"/><path d="{path("B_speed")}" fill="none" stroke="#245b7b" stroke-width="3"/><text x="700" y="22" font-size="14">灰：A　蓝：B　单位：场景单位／秒</text><text x="65" y="282" font-size="13">0 s</text><text x="570" y="282" font-size="13">6 s</text><text x="1060" y="282" font-size="13">12 s</text></g></svg>'

def main(folder,reference):
    p=Path(folder);ref=Path(reference);i=read(p/'TRIAL_INPUT.json');n=read(p/'NATIVE_IDENTITY.json');q=read(p/'MEDIA_QA.json');source=read(ref/'SOURCE.json')
    rows=read(p/'CAMERA_SPEEDS.json');template=Path(__file__).with_name('review-template.html').read_text('utf-8')
    chunks='<table><tr><th>词块</th><th>峰值时刻（样片）</th><th>动画范围</th></tr>'
    for c in n['rig']['chunks']:
        center=c['center']-i['clip_start'];chunks+=f'<tr><td>{escape(c["text"])}</td><td>{center:.3f} s</td><td>{center-c["attack"]:.3f}–{center+c["release"]:.3f} s</td></tr>'
    chunks+='</table>'
    blur='参数已原生回读；单独开关对实际像素的验证记录另存，若未提供记录则不宣称已隔离证明效果。'
    if (p/'MOTION_BLUR_PIXEL_CHECK.json').exists():
        data=read(p/'MOTION_BLUR_PIXEL_CHECK.json')
        blur='已做同帧原生运动模糊开／关像素对照。'
        blur+='差异可测。' if data.get('different_pixels') else '尚未测得差异，不宣称效果已被隔离验证。'
        blur+='开关恢复原值。' if data.get('restored_exactly') else '恢复状态仍待核查。'
        blur+=escape(data.get('interpretation',''))
    values={'COPY':escape(i['voice']['text']),'SPEED_SVG':speed_svg(rows),'CHUNKS_TABLE':chunks,'BLUR_STATUS':blur,'AUDIO_CORRELATION':f'{q["audio"]["whole_take_correlation"]:.6f}','REVISION':escape(i['revision']),'REFERENCE_SHA':source['sha256'],'A_SHA':q['variants']['A']['sha256'],'B_SHA':q['variants']['B']['sha256']}
    for k,v in values.items():template=template.replace('{{'+k+'}}',v)
    if '{{' in template:raise ValueError('Unfilled report field')
    (p/'REVIEW.html').write_text(template,encoding='utf-8')
    print(str(p/'REVIEW.html'))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
