"""Deterministic glyph geometry with original Unicode offsets.

Semantic roles arrive frozen from ANSWER. This module only measures and wraps.
Whitespace stays in provenance even where it has no visible glyph.
"""
import re
import math

KEEP_WITH_NEXT = ('a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'for', 'and', 'but', 'or')


def strip_hard_breaks(text):
    """Display-only normalization. Never use these offsets for source binding."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return '\n\n'.join(re.sub(r'\s+', ' ', p).strip()
                       for p in re.split(r'\n[ \t]*\n+', text))


def balance_lines(words, width, min_fill=0.72, keep_with_next=KEEP_WITH_NEXT):
    """Balance measured tokens per paragraph; keep source offsets immutable.

    Short paragraphs and impossible connector chains are reported, not stretched.
    Input tokens need w, space_width, size, paragraph, start/end, x/y and line.
    """
    if not math.isfinite(width) or width <= 0 or not 0 < min_fill <= 1:
        raise ValueError('Positive width and min_fill in (0, 1] required')
    if not words:
        return []
    if any(not math.isfinite(w['w']) or w['w'] < 0 or w['w'] > width for w in words):
        raise ValueError('A source token exceeds the readable width')
    from itertools import groupby
    output = []; line_number = 0
    origin_x, origin_y = words[0]['x'], words[0]['y']
    forbidden = set(keep_with_next)
    for _, group in groupby(words, key=lambda w: w.get('paragraph', 0)):
        tokens = list(group); n = len(tokens)
        # Cost puts source fidelity/width first, then avoids connector endings,
        # then balances lines. Finite penalties allow an honest impossible case.
        costs = [float('inf')] * (n + 1); costs[n] = 0; choices = {}
        for i in range(n - 1, -1, -1):
            used = 0
            for j in range(i, n):
                used += tokens[j]['w'] + (tokens[j]['space_width'] if j > i else 0)
                if used > width + 1e-8:
                    break
                fill = used / width
                connector = j < n - 1 and tokens[j]['text'].casefold() in forbidden
                singleton = i == j and n > 1
                cost = (1-fill)**2 + max(0, min_fill-fill)*4
                cost += 1000*connector + 10*singleton + costs[j+1]
                if cost < costs[i]:
                    costs[i] = cost; choices[i] = (j+1, used, connector, singleton)
        i = 0
        while i < n:
            end, used, connector, singleton = choices[i]
            warnings = []
            if used / width < min_fill: warnings.append('SHORT_LINE')
            if connector: warnings.append('KEEP_WITH_NEXT_UNSATISFIED')
            if singleton: warnings.append('SINGLE_TOKEN_LINE')
            cursor = origin_x
            for k in range(i, end):
                word = tokens[k]
                if k > i: cursor += word['space_width']
                output.append(dict(word, x=cursor,
                    y=origin_y + line_number * word['line_height'], line=line_number,
                    line_fill=used / width, layout_warnings=list(warnings)))
                cursor += word['w']
            line_number += 1; i = end
    return output


def focus_windows(words, max_lines=9):
    """Partition lines for a camera consumer; no evidence or teaching decisions."""
    if isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines < 1:
        raise ValueError('Positive integer max_lines required')
    from itertools import groupby
    lines = [list(g) for _, g in groupby(words, key=lambda w: w['line'])]
    windows = []
    for i in range(0, len(lines), max_lines):
        chunk = [w for row in lines[i:i+max_lines] for w in row]
        windows.append(dict(index=len(windows), start=chunk[0]['start'], end=chunk[-1]['end'],
            line_start=chunk[0]['line'], line_count=len(lines[i:i+max_lines]),
            word_spans=[[w['start'], w['end']] for w in chunk],
            bounds=dict(left=min(w['x'] for w in chunk), top=min(w['y']-w['size'] for w in chunk),
                        right=max(w['x']+w['w'] for w in chunk), bottom=max(w['y'] for w in chunk))))
    return windows


def layout_words(text, font_path, size, width, x=0, y=0, leading=1.42,
                 *, flow=False, keep_with_next=KEEP_WITH_NEXT, min_fill=0.72):
    # Legacy calls retain their byte-for-byte geometry; P2 explicitly opts in.
    if not all(math.isfinite(v) for v in (size, width, x, y, leading)) or min(size, width, leading) <= 0:
        raise ValueError('Finite positive size, width and leading required')
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, size)
    if flow:
        tokens = []; previous_end = 0; paragraph = 0; utf16_cursor = 0
        for match in re.finditer(r'\S+', text):
            utf16_cursor += len(text[previous_end:match.start()].encode('utf-16-le')) // 2
            utf16_start = utf16_cursor
            utf16_cursor += len(match.group().encode('utf-16-le')) // 2
            gap = text[previous_end:match.start()].replace('\r\n', '\n').replace('\r', '\n')
            if tokens and re.search(r'\n[ \t]*\n', gap): paragraph += 1
            tokens.append(dict(text=match.group(), start=match.start(), end=match.end(),
                x=x, y=y, w=font.getlength(match.group()), space_width=font.getlength(' '),
                size=size, line=0, paragraph=paragraph, line_height=size*leading,
                utf16_start=utf16_start, utf16_end=utf16_cursor))
            previous_end = match.end()
        return balance_lines(tokens, width, min_fill, keep_with_next)
    words = []; cursor_x = x; baseline = y; line = 0; previous_end = 0
    for match in re.finditer(r'\S+', text):
        gap = text[previous_end:match.start()]
        if '\n' in gap and words:
            baseline += size * leading; cursor_x = x; line += 1
        space = font.getlength(' ') if cursor_x != x else 0
        measured = font.getlength(match.group())
        if measured > width:
            raise ValueError('A source token exceeds the readable width')
        if cursor_x + space + measured > x + width:
            baseline += size * leading; cursor_x = x; space = 0; line += 1
        cursor_x += space
        words.append(dict(text=match.group(), start=match.start(), end=match.end(),
                          x=cursor_x, y=baseline, w=measured, line=line, size=size))
        cursor_x += measured; previous_end = match.end()
    return words


def bind_words(words, spans, font_path=None):
    """Split at explicit semantic boundaries without interpreting English."""
    result = []
    for word in words:
        hits = [s for s in spans if s['start'] < word['end'] and s['end'] > word['start']]
        if len(hits) > 1:
            raise ValueError('Semantic boundaries must lie between visible tokens')
        if hits and not (hits[0]['start'] <= word['start'] and word['end'] <= hits[0]['end']):
            if font_path is None: raise ValueError('Partially bound token needs exact glyph measurement')
            from PIL import ImageFont
            font=ImageFont.truetype(font_path,word['size'])
            cuts=sorted({word['start'],word['end']} | {
                p for s in hits for p in (s['start'],s['end']) if word['start']<p<word['end']})
            for start,end in zip(cuts,cuts[1:]):
                literal=word['text'][start-word['start']:end-word['start']]
                own=[s for s in hits if s['start']<=start and end<=s['end']]
                result.append(dict(word,text=literal,start=start,end=end,
                    x=word['x']+font.getlength(word['text'][:start-word['start']]),
                    w=font.getlength(literal),span_id=own[0]['span_id'] if own else None))
            continue
        result.append(dict(word, span_id=hits[0]['span_id'] if hits else None))
    return result
