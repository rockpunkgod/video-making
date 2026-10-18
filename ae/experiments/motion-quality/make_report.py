"""Make the local review from this trial's native and encoded-media receipts."""
import html
import json
from pathlib import Path
import sys

from run import read,write,sha256


def make(folder):
    p=Path(folder);i=read(p/'TRIAL_INPUT.json');n=read(p/'NATIVE_IDENTITY.json')
    qa=read(p/'NATIVE_QA.json');media=read(p/'MEDIA_QA.json');blur=read(p/'BLUR_PIXEL_QA.json');curves=read(p/'NATIVE_CURVE_QA.json')
    assert qa['status']==curves['status']=='PASS'
    assert qa['native_identity_sha256']==blur['native_identity_sha256']==media['native_identity_sha256']==curves['native_identity_sha256']==sha256(p/'NATIVE_IDENTITY.json')
    for v in ('A','B'):assert sha256(media['variants'][v]['file'])==media['variants'][v]['sha256']
    speeds=read(p/'CAMERA_SPEEDS.json');native=read(p/'NATIVE_READBACK.json')
    def table(head,rows):
        return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
    def speed_svg(limit):
        rows=[r for r in speeds if r['t']<=limit];peak=max(max(r['A_speed'],r['B_speed']) for r in rows)*1.08
        def point(t,v):return f'{56+t/limit*1080:.2f},{270-v/peak*230:.2f}'
        lines=[]
        for k,color in [('A','#8d9499'),('B','#b44719')]:lines.append('<polyline fill="none" stroke="'+color+'" stroke-width="2" points="'+' '.join(point(r['t'],r[k+'_speed']) for r in rows)+'"/>')
        ticks=''.join(f'<text x="{56+t/limit*1080:.1f}" y="294">{t:g}s</text>' for t in range(0,int(limit)+1,max(1,int(limit)//8)))
        return '<svg viewBox="0 0 1180 310" role="img" aria-label="Native camera speed comparison"><path d="M56 35V270H1140" fill="none" stroke="#bbb"/><text x="60" y="22">A 灰 / B 橙 · 原生世界单位/秒 · 上限 '+f'{peak:.0f}'+'</text>'+''.join(lines)+ticks+'</svg>'
    phase=[
        ('搜索','0.000–7.458','原搜索点保留；中间速度接近 0','中间目标速度 85 / 90；不换向，不左右抖动'),
        ('命中 / 阅读','7.458–10.667','原命中时间和完整源句','同一命中时间；减速到 0，保留阅读停顿'),
        ('回到选项','10.917–13.917','12.917s 才出发，1s 完成','在命中阅读结束后提前准备，3s 完成；终点不变'),
        ('携带 / 接近','15.750–19.167','选项随原空间轨迹移动','同一原生 3D 选项跟随前景路径；相机中途速度连续'),
        ('辨认 / 提取','19.167–23.208','原辨认时间与提取终点','相机提前 6 帧准备；文字位移先落稳，转角晚 4 帧收束'),
        ('比较 / 判断','23.208–28.375','原参加 / 主持对照；A 排除','比较镜头稳定；强调色在原时刻出现，判断时间不变'),
        ('归位 / 交接','30.583–32.417','原位交还','位移提前 5 帧，转角提前 2 帧收束；原位交还时刻不变'),
        ('共同尾帧','32.417–33.417','完整落位后保留 1s','同样保留 1s；不是新增教学结果')]
    phase_html=table(['阶段','样片时间','A 原版','B 实验'],phase)
    metrics=table(['项目','A','B','测量范围'],[
        ('相机峰值速度',f"{qa['camera_metrics']['A']['peak_camera_speed']:.1f}",f"{qa['camera_metrics']['B']['peak_camera_speed']:.1f}",'原生世界单位/秒；包含提前出发的时长变化，不仅是曲线影响'),
        ('选项锚点出画帧数',qa['camera_metrics']['A']['option_anchor_outside_frame'],qa['camera_metrics']['B']['option_anchor_outside_frame'],'携带开始至原判断；锚点在画内不等于每个字都可读'),
        ('搜索途经点 1 速度','1.05','82.75','邻接帧最低速度；无必要时不归零'),
        ('搜索途经点 2 速度','0.87','89.89','同上'),
        ('稳定阅读段位置漂移','原版保留',qa['reading_position_drift'],'B 相机 / 注意点 / 提取组原生回读'),
        ('每版实际帧数',media['variants']['A']['frames'],media['variants']['B']['frames'],'逐帧解码及 1/24s 时间戳检查'),
        ('音频','3 条完整原 take','解码 PCM 与 A 完全相同','未裁句、未变速；听感仍待审')])
    keys=[];b=native['comps']['B']
    curves={c['name']:c['position'] for c in b['controllers']}
    curves.update(SOURCE_LIFT_position=b['liftPosition'],SOURCE_LIFT_orientation=b['liftOrientation'])
    for name,rows in curves.items():
        for k in rows:
            speed=' / '.join(str(round(e['speed'],3)) for e in (k['incoming'][0],k['outgoing'][0]))
            influence=' / '.join(str(round(e['influence'],3)) for e in (k['incoming'][0],k['outgoing'][0]))
            keys.append([html.escape(name),f"{k['t']-i['clip_start']:.3f}s",html.escape(str(k['v'])),speed,influence,html.escape(str(k.get('spatialIn','non-spatial')))])
    key_table=table(['控制器 / 属性','样片时间','原生值','入 / 出速度','入 / 出 influence %','原生入空间切线'],keys)
    blur_table=table(['样片时间','RGB 平均差 / 255','变化超过 1 色阶的像素','含义'],[[f"{r['time']:.3f}s",f"{r['mean_rgb_difference']:.6f}",f"{r['fraction_changed_more_than_one']*100:.3f}%",'静止阅读' if r['time']>26 else '交接 / 动作'] for r in blur['frames']])
    chunks=table(['原词块','峰值时间','放大范围'],[[html.escape(c['text']),f"{c['center']-i['clip_start']:.3f}s",'100% → 104% → 100%'] for c in n['rig']['chunks']])
    audio=table(['完整台词','进入时间','原 take / 解码片段相关系数'],[[html.escape(t['text']),f"{t['offset_samples']/48000:.3f}s",f"{t['correlation']:.6f}"] for t in media['audio']['complete_takes']])
    data={'total':i['clip_frames'],'fps':24,'phases':phase}
    text=(Path(__file__).parent/'review-template.html').read_text('utf-8')
    for token,value in {'PHASE_TABLE':phase_html,'METRIC_TABLE':metrics,'FULL_SPEED':speed_svg(i['clip_frames']/24),'SEARCH_SPEED':speed_svg(7.458333),'KEY_TABLE':key_table,'BLUR_TABLE':blur_table,'CHUNK_TABLE':chunks,'AUDIO_TABLE':audio,'FRAME_DATA':json.dumps(data,ensure_ascii=False),'NATIVE_SHA':sha256(p/'NATIVE_IDENTITY.json'),'AEP_SHA':sha256(n['project'])}.items():text=text.replace('{{'+token+'}}',value)
    dest=p/'REVIEW.html';dest.write_text(text,'utf-8')
    write(p/'REPORT_RECEIPT.json',{'report':str(dest),'sha256':sha256(dest),'native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'media_qa_sha256':sha256(p/'MEDIA_QA.json'),'blur_qa_sha256':sha256(p/'BLUR_PIXEL_QA.json'),'human_review':'PENDING','production_integrated':False})
    print(dest)


if __name__=='__main__':make(sys.argv[1])
