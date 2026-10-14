"""P2 backend: source-preserving layout proposals, not final AE glyph geometry."""
import argparse
import hashlib
import json
from pathlib import Path

from .semantic_text_layout import layout_words, focus_windows


def digest(data):
    return hashlib.sha256(data).hexdigest()


def typeset(text, font_path, style, *, role='focus_text', width=None, fallback_font_path=None):
    size = style['type_scale'][role]
    layout = style['layout']
    width = layout['focus_width'] if width is None else width
    line_height = style['type_scale']['focus_line_height']
    if line_height < size:
        raise ValueError('Line height cannot be smaller than font size')
    font_path = Path(font_path)
    limits = layout.get('focus_characters_per_line')
    words = layout_words(text, str(font_path), size, width,
                         leading=line_height/size, flow=True,
                         max_characters=limits[1] if limits else None,
                         fallback_font_path=fallback_font_path)
    windows = focus_windows(words, layout['focus_max_lines'])
    lines = []
    for word in words:
        if not lines or lines[-1]['line'] != word['line']:
            lines.append(dict(line=word['line'], text=word['text'], start=word['start'],
                              end=word['end'], fill=word['line_fill'], warnings=word['layout_warnings']))
        else:
            lines[-1]['text'] += ' ' + word['text']
            lines[-1]['end'] = word['end']
    for line in lines:
        if limits and not limits[0] <= len(line['text']) <= limits[1]:
            line['warnings'] = [*line['warnings'], 'CHARACTER_COUNT_REVIEW']
    return dict(schema='typeset-plan/v1', geometry='PROVISIONAL_REQUIRES_AE_MEASUREMENT',
        source_sha256=digest(text.encode('utf-8')), font_sha256=digest(font_path.read_bytes()),
        fallback_font_sha256=digest(Path(fallback_font_path).read_bytes()) if fallback_font_path else None,
        style_sha256=digest(json.dumps(style, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False).encode('utf-8')),
        role=role, size=size, width=width, line_height=line_height,
        words=words, lines=lines, focus_windows=windows,
        source_offsets='original_unicode_codepoints', teaching_facts_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text-file', type=Path, required=True)
    parser.add_argument('--font', type=Path, required=True)
    parser.add_argument('--style', type=Path, required=True)
    parser.add_argument('--fallback-font', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Preserve CRLF offsets; Path.read_text would normalize them.
    text = args.text_file.read_bytes().decode('utf-8')
    plan = typeset(text, args.font, json.loads(args.style.read_text(encoding='utf-8')),
                   fallback_font_path=args.fallback_font)
    if args.output.exists():
        raise ValueError('Choose a fresh output path')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    main()
