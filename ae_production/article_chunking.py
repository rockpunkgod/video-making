"""Article-level language decisions, compiled before layout or animation.

The production author reads the complete article and supplies contiguous sense
groups. This compiler validates literal coverage and protected phrases; it is
not an English parser and cannot certify the linguistic quality of a draft.
AE must consume these identities, never invent boundaries from line length.
"""
from copy import deepcopy
from hashlib import sha256
from html import escape
from pathlib import Path
import re

from video_contracts import read, write
from scripts.voice_delivery import sha256 as file_sha256

DRAFT = 'ARTICLE_CHUNKS.json'
COMPILED = 'READING_CHUNKS.json'
SCHEMA = 'article-chunks/v1'


def text_sha(text):
    return sha256(text.encode('utf-8')).hexdigest()


def source_packet(bundles):
    return {world: {'question_id': b['source_snapshot']['question_id'],
                    'passage_sha256': text_sha(b['source_snapshot']['passage']),
                    'passage': b['source_snapshot']['passage']}
            for world, b in bundles.items()}


def compile_chunks(draft, bundles):
    if draft.get('schema') != SCHEMA or set(draft.get('articles', {})) != set(bundles):
        raise ValueError('Article chunking must cover every frozen article exactly once')
    if not isinstance(draft.get('editor'), str) or not draft['editor'].strip():
        raise ValueError('Record who made the linguistic boundary decisions')
    result = {'schema': SCHEMA, 'editor': draft['editor'], 'articles': {},
              'linguistic_review': 'EDITOR_AUTHORED_NOT_MACHINE_CERTIFIED',
              'human_visual_review': 'PENDING'}
    for world, src in source_packet(bundles).items():
        article = draft['articles'][world]; text = src['passage']
        if article.get('passage_sha256') != src['passage_sha256']:
            raise ValueError('Article chunking belongs to another source: ' + world)
        # Existing source spans use Python character indexes; native AE uses
        # UTF-16. Do not quietly animate the wrong glyphs on unsupported input.
        if any(ord(c) > 0xffff for c in text):
            raise ValueError('Non-BMP source needs an explicit UTF-16 span adapter')
        token_starts = {m.start() for m in re.finditer(r'\S+', text)}
        token_ends = {m.end() for m in re.finditer(r'\S+', text)}
        chunks = []; cursor = 0
        for value in article.get('chunks', []):
            if not isinstance(value, str) or not value or value != value.strip() or '\n' in value or '\r' in value:
                raise ValueError('A sense group must contain exact words within one paragraph')
            while cursor < len(text) and text[cursor].isspace(): cursor += 1
            end = cursor + len(value)
            if text[cursor:end] != value:
                raise ValueError(f'Changed, missing or reordered source at {world}:{cursor}: {value!r}')
            if cursor not in token_starts or end not in token_ends:
                raise ValueError('A chunk boundary cuts inside an original word: ' + value)
            chunks.append({'id': f'{world}:{cursor}:{end}', 'start': cursor, 'end': end, 'text': value})
            cursor = end
        if not chunks or text[cursor:].strip():
            raise ValueError('Article has unread words; annotate the complete passage: ' + world)
        protected = []
        for phrase in article.get('keep_together', []):
            if not isinstance(phrase, str) or not phrase.strip():
                raise ValueError('Protected phrase must be literal source text')
            matches = list(re.finditer(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text))
            if not matches: raise ValueError('Protected phrase is absent from source: ' + phrase)
            for m in matches:
                if not any(c['start'] <= m.start() and c['end'] >= m.end() for c in chunks):
                    raise ValueError('A protected phrase was split: ' + phrase)
                protected.append({'start': m.start(), 'end': m.end(), 'text': phrase})
        result['articles'][world] = {k: v for k, v in src.items() if k != 'passage'}
        result['articles'][world].update(chunks=chunks, keep_together=protected)
    return result


def current_chunks(folder, bundles):
    folder = Path(folder)
    if not (folder / DRAFT).exists() or not (folder / COMPILED).exists():
        raise ValueError('Article sense groups are missing; author ARTICLE_CHUNKS.json and run chunks before prepare/build')
    wanted = compile_chunks(read(folder / DRAFT), bundles)
    wanted['input_sha256'] = file_sha256(folder / DRAFT)
    if read(folder / COMPILED) != wanted:
        raise ValueError('Article sense groups changed; rerun chunks and prepare in a new native revision')
    return wanted


def chunk_stage(folder, bundles):
    """One existing-entry operation, with a source packet for the language author."""
    folder = Path(folder)
    write(folder / 'ARTICLE_CHUNKING_INPUT.json', {
        'schema': 'article-chunking-input/v1', 'articles': source_packet(bundles),
        'draft_template': {'schema': SCHEMA, 'editor': '', 'articles': {
            world: {'passage_sha256': src['passage_sha256'], 'chunks': [], 'keep_together': []}
            for world, src in source_packet(bundles).items()}},
        'instructions': [
            'Read each complete article before marking natural English sense groups.',
            'Keep fixed expressions, verb-particle/preposition units, noun phrases and names together.',
            'Use clause and coordination boundaries; do not aim for equal word counts.',
            'Copy exact contiguous text into chunks and cover every non-whitespace character once.',
            'Record fragile compounds/collocations as keep_together; do not add teaching evidence.',
            'AE wraps whole groups. If a group cannot fit, revise layout or have the language author reconsider; never auto-split it.',
            'Boundary validity and native validation do not certify linguistic or visual quality.'
        ]})
    if not (folder / DRAFT).exists():
        return {'status': 'NEEDS_LINGUISTIC_AUTHOR', 'source_packet': str(folder / 'ARTICLE_CHUNKING_INPUT.json'),
                'required': str(folder / DRAFT), 'production_ready': False}
    result = compile_chunks(read(folder / DRAFT), bundles)
    result['input_sha256'] = file_sha256(folder / DRAFT)
    dest = folder / COMPILED
    if (folder / 'native-identity.json').exists() and (not dest.exists() or read(dest) != result):
        raise ValueError('Chunk changes require a new revision; preserve the existing AEP and reading receipt')
    write(dest, result)
    sections = []
    for world, article in result['articles'].items():
        text = bundles[world]['source_snapshot']['passage']; cursor = 0; body = []
        for c in article['chunks']:
            body.append(escape(text[cursor:c['start']]))
            body.append('<span class="chunk" title="' + escape(c['id']) + '">' + escape(c['text']) + '</span>')
            cursor = c['end']
        body.append(escape(text[cursor:]))
        sections.append('<h2>' + escape(world) + '</h2><div class="article">' + ''.join(body) + '</div>')
    (folder / 'ARTICLE_CHUNKS_REVIEW.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>文章词块审阅</title><style>'
        'body{max-width:1100px;margin:48px auto;background:#f4f1e8;color:#18232a;font:20px/2.2 Arial;}'
        '.article{white-space:pre-wrap}.chunk{display:inline-block;border-bottom:2px solid #839dac;'
        'margin:0 3px 5px;padding:0 3px}.chunk:hover{background:#dbe4e7}h1,h2{line-height:1.3}</style>'
        '<h1>文章词块 · 独立审阅</h1><p>每个下划线是一块。原文逐字保留；划分由编辑作出，观看效果待审。</p>'
        + ''.join(sections), encoding='utf-8')
    return {'status': 'COMPILED', 'articles': len(result['articles']),
            'chunks': sum(len(a['chunks']) for a in result['articles'].values()),
            'output': str(dest), 'review': str(folder / 'ARTICLE_CHUNKS_REVIEW.html'),
            'human_visual_review': 'PENDING'}


def bind_worlds(worlds, compiled):
    """Extraction blocks may not silently become a second linguistic segmenter."""
    for world, data in worlds.items():
        chunks = compiled['articles'][world]['chunks']; assigned = []
        for block in data['blocks']:
            selected = [c for c in chunks if c['start'] < block['end'] and c['end'] > block['start']]
            if any(c['start'] < block['start'] or c['end'] > block['end'] for c in selected):
                raise ValueError('An excerpt boundary cuts a sense group; reconcile the authored spans: ' + block['id'])
            block['reading_chunks'] = deepcopy(selected)
            assigned.extend(c['id'] for c in selected)
        if assigned != [c['id'] for c in chunks]:
            raise ValueError('Source blocks do not preserve every article chunk exactly once')
