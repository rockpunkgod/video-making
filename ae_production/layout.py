"""Fixed type scale; measured reflow and pagination instead of shrink-to-fit."""
import re
from functools import lru_cache
from PIL import ImageFont


class LayoutOverflow(ValueError):
    pass


# Conservative, literal typography rules; no model or paraphrasing.
CJK_PHRASES=('支持这个判断','自己的风格','翻页信号','点头风格','练习配合','三维标记','提示词',
             '这个判断','不代表','不等于','到此停止','方法边界','原文依据',
             '做什么','对谁','有限谓语','空位成分','名词节点','不能','没有','支持','动名词')
LINE_START_FORBIDDEN='，。？！：；、）》】」』”’…%,.!?;:)]}'
LINE_END_FORBIDDEN='（【《「『“‘('


@lru_cache(maxsize=16)
def font(path, size, variation=None):
    # No silent substitute: AE and the measuring host must share this font.
    face=ImageFont.truetype(path, size)
    if variation: face.set_variation_by_name(variation)
    return face


def wrap(text, width, size, font_path, max_units=None, variation=None, tracking=0, cjk=False):
    """Returns character-exact runs; joining runs reproduces the original string."""
    face = font(font_path, size, variation)
    pattern=r'[A-Za-z0-9]+(?:[’\'-][A-Za-z0-9]+)*|[^A-Za-z0-9]'
    if cjk:pattern=r'[A-Za-z0-9]+(?:[’\'_-][A-Za-z0-9]+)*|[^A-Za-z0-9]'
    if cjk:pattern='|'.join(re.escape(s) for s in CJK_PHRASES)+'|'+pattern
    tokens = re.findall(pattern, text)
    lines, line = [], ''
    for token in tokens:
        if token == '\n':
            lines.append(line + token); line = ''; continue
        def fits(value):
            units = sum(1 if ord(c) > 255 else 0.5 for c in value)
            measured=face.getlength(value)+max(0,len(value)-1)*size*tracking/1000
            return measured <= width and (max_units is None or units <= max_units)
        if line and not fits(line + token):
            carry=''
            if cjk:
                # Prefer a recent punctuation pause; don't leave an opening mark behind.
                pauses=[m.end() for m in re.finditer('[，；：。！？]',line)]
                if pauses and pauses[-1]>=len(line)*0.55 and pauses[-1]<len(line):
                    line,carry=line[:pauses[-1]],line[pauses[-1]:]
                if line and line[-1] in LINE_END_FORBIDDEN:
                    carry=line[-1]+carry;line=line[:-1]
                if token[0] in LINE_START_FORBIDDEN and not carry:
                    previous=re.search(r'[A-Za-z0-9]+(?:[’\'_-][A-Za-z0-9]+)*$|.$',line)
                    if previous:
                        carry=previous.group();line=line[:previous.start()]
                if carry and not fits(carry+token):
                    raise LayoutOverflow('layout_overflow: punctuation / phrase cannot safely wrap')
            if line:lines.append(line)
            line = carry
        if not fits(token):
            # Long English words can break at glyph boundaries, without inserting a hyphen.
            for ch in token:
                if line and not fits(line + ch): lines.append(line); line = ''
                if not fits(ch): raise LayoutOverflow('layout_overflow: single glyph')
                line += ch
        else:
            line += token
    if line: lines.append(line)
    # Avoid a lone closing mark / tiny tail while preserving all original characters.
    if not cjk and len(lines)>1 and len(lines[-1].strip())<4 and not lines[-2].endswith('\n'):
        move=min(4-len(lines[-1].strip()),len(lines[-2])-1)
        if move>0:
            lines[-1]=lines[-2][-move:]+lines[-1]; lines[-2]=lines[-2][:-move]
    return lines or ['']


def pages(text, width, height, token, design):
    style = design['typography'][token]
    lines = wrap(text, width-design['font'].get('measurement_margin_px',0), style['size'], design['font']['measurement_file'],
                 variation=design['font'].get('variation'),tracking=style.get('tracking',0),cjk=design.get('cjk_typography',False))
    capacity = int(height // style['leading'])
    if capacity < 1: raise LayoutOverflow('layout_overflow: no readable line')
    return [lines[i:i + capacity] for i in range(0, len(lines), capacity)]


def slots(text, bounds, token, design):
    x, y, w, h = bounds
    runs = pages(text, w, h, token, design)
    if len(runs) != 1: raise LayoutOverflow('layout_overflow: paginate before placing')
    return {'x': x, 'y': y, 'width': w, 'height': h, 'lines': runs[0], 'style_token': token}


def subtitle_cues(text, start, end, scene_id, design):
    if not text: return []
    cfg = design['subtitles']; grid = design['grid']; style = design['typography']['Subtitle']
    lines = wrap(text, cfg.get('width',1080 - 2 * grid['side_margin'])-design['font'].get('measurement_margin_px',0), style['size'], design['font']['measurement_file'], cfg['max_line_units'],
                 variation=design['font'].get('variation'),tracking=style.get('tracking',0),cjk=design.get('cjk_typography',False))
    groups = [lines[i:i + cfg['max_lines']] for i in range(0, len(lines), cfg['max_lines'])]
    total = sum(len(''.join(g)) for g in groups)
    minimum=cfg['min_duration_frames']/design['canvas']['fps']
    if end-start < len(groups)*minimum:
        raise LayoutOverflow('layout_overflow: insufficient subtitle time')
    remaining=end-start-len(groups)*minimum
    elapsed = start; cues = []
    for i, group in enumerate(groups):
        finish = end if i == len(groups)-1 else elapsed + minimum + remaining * len(''.join(group)) / total
        if (finish-elapsed)*design['canvas']['fps'] < cfg['min_duration_frames']-1e-6:
            raise LayoutOverflow('layout_overflow: subtitle too short')
        cues.append({'cue_id': scene_id + ':subtitle:' + str(i), 'scene_id': scene_id,
                     'start': elapsed, 'end': finish, 'text': ''.join(group), 'lines': group})
        elapsed = finish
    return cues
