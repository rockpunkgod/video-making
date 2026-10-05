"""Fixed type scale; measured reflow and pagination instead of shrink-to-fit."""
import re
from functools import lru_cache
from PIL import ImageFont


class LayoutOverflow(ValueError):
    pass


@lru_cache(maxsize=16)
def font(path, size):
    # No silent substitute: AE and the measuring host must share this font.
    return ImageFont.truetype(path, size)


def wrap(text, width, size, font_path, max_units=None):
    """Returns character-exact runs; joining runs reproduces the original string."""
    face = font(font_path, size)
    tokens = re.findall(r'[A-Za-z0-9]+(?:[’\'-][A-Za-z0-9]+)*|[^A-Za-z0-9]', text)
    lines, line = [], ''
    for token in tokens:
        if token == '\n':
            lines.append(line + token); line = ''; continue
        def fits(value):
            units = sum(1 if ord(c) > 255 else 0.5 for c in value)
            return face.getlength(value) <= width and (max_units is None or units <= max_units)
        if line and not fits(line + token):
            lines.append(line); line = ''
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
    if len(lines)>1 and len(lines[-1].strip())<4 and not lines[-2].endswith('\n'):
        move=min(4-len(lines[-1].strip()),len(lines[-2])-1)
        if move>0:
            lines[-1]=lines[-2][-move:]+lines[-1]; lines[-2]=lines[-2][:-move]
    return lines or ['']


def pages(text, width, height, token, design):
    style = design['typography'][token]
    lines = wrap(text, width, style['size'], design['font']['measurement_file'])
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
    lines = wrap(text, 1080 - 2 * grid['side_margin'], style['size'], design['font']['measurement_file'], cfg['max_line_units'])
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
