"""Compare direct-authored and function-rebuilt native AE proof evidence."""
import argparse
from collections import Counter
from pathlib import Path
from PIL import Image
from creative_os.dark_field_proof import contrast
from video_contracts import read,write


def check(prototype,rebuilt):
    a=read(prototype/'NATIVE_READBACK.json');b=read(rebuilt/'NATIVE_READBACK.json')
    for key in ('origin','tracks','background0','background4_5'):
        if a[key]!=b[key]:raise ValueError('Native rebuild differs: '+key)
    state=read(rebuilt/'STATE_AUDIT.json')
    if state!=read(prototype/'STATE_AUDIT.json'):raise ValueError('Native field/color state differs')
    for key,value in dict(world_opacity_4_5=100,world_blur_4_5=3.2,world_depth_4_5=600,
                          eliminate_screen_dy=24,eliminate_opacity=20).items():
        if abs(state[key]-value)>1e-5:raise ValueError('Native state does not meet specification: '+key)
    expected={0:(242,240,234),4.5:(23,24,26)}
    for time,color in expected.items():
        with Image.open(rebuilt/f'FRAME_{time}.png') as im:
            actual=im.convert('RGB').getpixel((5,5))
            if actual!=color:raise ValueError(f'Rendered field at {time}s is {actual}, expected {color}')
    with Image.open(rebuilt/'FRAME_18.png') as im:
        # The opaque interior of the judgment glyph, away from antialias edges.
        colors=Counter(im.convert('RGB').crop((96,760,700,900)).getdata())
        if colors[(242,240,234)]<100:raise ValueError('No paper-white judgment glyph')
        background=im.convert('RGB').getpixel((5,5))
        ratio=contrast('#F2F0EA','#'+''.join(f'{c:02X}' for c in background))
        if ratio<15:raise ValueError('Rendered judgment contrast below 15:1')
    for t in (0,2.5,4.5,8,18):
        with Image.open(prototype/f'FRAME_{t}.png') as x,Image.open(rebuilt/f'FRAME_{t}.png') as y:
            if x.size!=y.size or x.tobytes()!=y.tobytes():raise ValueError(f'Rebuild frame differs at {t}')
    report=dict(native_trajectory_samples_equal=True,native_field_and_color_equal=True,sample_frames_pixel_identical=True,
                rendered_judgment_contrast=ratio,public_render_ready=False,
                human_visual_review='PENDING',scope='mechanical_and_pixel_checks_not_taste_approval')
    write(rebuilt/'REBUILD_CHECK.json',report);return report


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('prototype',type=Path);cli.add_argument('rebuilt',type=Path)
    a=cli.parse_args();print(check(a.prototype,a.rebuilt))
