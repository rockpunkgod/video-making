"""Deterministic glyph geometry with original Unicode offsets.

Semantic roles arrive frozen from ANSWER. This module only measures and wraps.
Whitespace stays in provenance even where it has no visible glyph.
"""
import re


def layout_words(text, font_path, size, width, x=0, y=0, leading=1.42):
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, size)
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
