"""Local Bilibili horizontal packaging; never selects, signs or publishes a cut.

The existing showcase checker remains the publication authority. This adapter
renders reviewable covers and binds their bytes to the real authored master.
Platform performance belongs to the existing engagement-learning ledger.
"""
from copy import deepcopy
from datetime import datetime
from html import escape
import json
from pathlib import Path

from video_contracts import sha
from .showcase import feedback_template, file_sha, inspect_media


VERSION = 'bilibili-packaging/v1'
SIZE = (1920, 1080)
MOBILE_SIZE = (320, 180)
BLUE, BRICK = '#7E96A8', '#A36F64'
PAPER, INK, DARK = '#F2F0EA', '#20211F', '#17181A'
SHOW = '英语有画说 · 学霸这题怎么做？'
CANDIDATES = [
    {
        'id': 'A',
        'title': '英语阅读：原文和选项都有这个词，为什么还不能选？',
        'cover_copy': ['词一样', '就能选？'],
        'visual_conflict': '两处真实 workshops 保持相同字形；两条关系轨迹先同向、后分离。',
        'composition': '纸面底色；左侧两行大字；右侧双 workshops 与细关系轨迹；底部小栏目署名。',
        'title_cover_complement': '标题指明英语阅读的原词陷阱；封面用一个短追问和同字异轨让冲突可见。',
        'first_15_seconds': '开场两句直接提出同词仍不能选的问题，随后进入第一题中性完整题面；不承诺15秒给出答案。',
        'audience_hypothesis': '做阅读时习惯凭原词匹配选项、对品牌尚无认知的高中生。假设需要真实点击数据检验。',
        'misleading_risk': '同词不等于一律错；影片须保留四项核验，不能被理解成见到原词就排除。',
    },
    {
        'id': 'B',
        'title': '单词都对上了，答案却不对？跟着学霸原速做两题',
        'cover_copy': ['看着一样', '做的事呢？'],
        'visual_conflict': '一个稳定的 workshops 词面，对应分处两个深度层的关系端点；名词一致不等于关系一致。',
        'composition': '暗场底色；上方大追问；下方两层疏朗的关系轨道和同一真实词锚点。',
        'title_cover_complement': '标题提供原速两题的观看方式；封面把注意力从单词引向实际动作。',
        'first_15_seconds': 'Hook先提出词面冲突，第一题给自主暂停入口；两题原速解决与后续回报由实际媒体兑现。',
        'audience_hypothesis': '知道单词含义却常在细节题失分、愿意跟着高手操作一次的高中生。',
        'misleading_risk': '“学霸”是栏目叙述视角，不是人物资历认证；不承诺做完两题即可提分。',
    },
    {
        'id': 'C',
        'title': '英语阅读别只盯原词：词一样，也可能说的是两回事',
        'cover_copy': ['词对上了', '意思呢？'],
        'visual_conflict': '两组 workshops 沿不同三维平面展开；相同词面与不同结构并存。',
        'composition': '纸面背景；上方两行短句；右下两层投影关系网和真实英文词，雾蓝与柔砖红区分层次。',
        'title_cover_complement': '标题限定应核对实际表达；封面留下“意思是否对齐”的具体疑问。',
        'first_15_seconds': '以已审Hook把疑问说清，再进入有来源的第一题；不在中性挑战里泄露角色差异。',
        'audience_hypothesis': '愿意检查比较对象和动作角色、但容易被重复名词吸引的高中生。',
        'misleading_risk': '封面抽象轨道只表达需要核对关系，不宣称从图形本身已证明任何选项。',
    },
]


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def asset(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Actual packaging asset missing: ' + str(path))
    return {'path': str(path), 'sha256': file_sha(path)}


def _verify(value):
    if file_sha(value['path']) != value['sha256']:
        raise ValueError('Bound packaging input changed: ' + value['path'])


def _reference_inputs(author_path, plan_path):
    author, plan = _json(author_path), _json(plan_path)
    if author['revision'] != plan['revision']:
        raise ValueError('Author and plan must have the same revision')
    if plan.get('author_sha256') != file_sha(author_path):
        raise ValueError('AV_PLAN does not bind these exact author bytes')
    source_assets = []
    for source in author['sources'].values():
        for key in ('bundle', 'status'):
            bound = asset(source[key])
            if author.get('input_files', {}).get(source[key]) != bound['sha256']:
                raise ValueError('Author source binding changed')
            if bound not in source_assets:
                source_assets.append(bound)
    if not plan.get('source_attribution'):
        raise ValueError('Actual paper/article attribution required for packaging')
    for attribution in plan['source_attribution'].values():
        bound = asset(attribution['source_path'])
        if (bound['sha256'] != attribution['source_sha256']
            or author.get('input_files', {}).get(attribution['source_path']) != bound['sha256']):
            raise ValueError('Original paper attribution binding changed')
        if bound not in source_assets:
            source_assets.append(bound)
    question = plan['worlds']['camp']['question']
    anchors = []
    for field, text in (('/passage', question['passage']), ('/options/A', question['options']['A'])):
        start = text.find('workshops')
        if start < 0:
            raise ValueError('Both real cover anchors must exist in the bound question')
        anchors.append({'world': 'camp', 'question_id': question['question_id'], 'pointer': field,
                        'start': start, 'end': start + len('workshops'), 'quote': 'workshops'})
    return {'author': asset(author_path), 'plan': asset(plan_path),
            'source_assets': source_assets, 'source_anchors': anchors,
            'source_revision': author['revision']}


def _sources(plan):
    return [{'world': world, 'paper': source['paper_display'],
             'article': source['article_display'], 'reading_section': source['reading_section'],
             'question_number': source['question_number'], 'question_id': source['question_id'],
             'original': {'path': source['source_path'], 'sha256': source['source_sha256']},
             'paper_heading_quotes': source['paper_heading_quotes'],
             'attribution': '教学使用节选，保留原试卷身份；不宣称官方认证，素材公开展示权待审核。'}
            for world, source in plan['source_attribution'].items()]


def publication_text(teaching_sources):
    """A real review draft, not a claim of rights or an approved upload."""
    if not teaching_sources:
        raise ValueError('Publication copy requires bound paper and article attribution')
    source_lines = '\n'.join(
        f'{index}. {source["paper"]}，阅读{source["reading_section"]}篇第{source["question_number"]}题；'
        f'{source["article"]}。' for index, source in enumerate(teaching_sources, 1))
    return {
        'column': SHOW,
        'byline': '英语有画说',
        'description': '选项和原文出现了相同的词，就一定能选吗？\n\n'
            '这期跟着第一视角原速做两道阅读题：先给你完整原文和四个选项，可以暂停自己判断；'
            '再回文章，核对它实际表达的动作、角色和比较关系。\n\n'
            '第一题看不同表达怎样对上同一个价格关系；第二题看相同名词背后，做的事有没有变。'
            '两题都检查全部选项，并保留最终答案的原文依据。\n\n'
            '栏目：英语有画说 · 学霸这题怎么做？\n'
            '教学来源：\n' + source_lines,
        'post_copy': '同样是 workshops，为什么不能只看词面？先暂停自己判断，再跟着第一视角原速核对两道题。',
        'tags': ['高中英语', '英语阅读', '阅读理解', '英语有画说'],
        'status': 'DRAFT_FOR_USER_REVIEW',
    }


def publication_markdown(text):
    return ('# ' + SHOW + '\n\n状态：发布前待审，不代表公开资格。\n\n'
            + text['description'] + '\n\n动态文案：\n\n' + text['post_copy'] + '\n')


class _Canvas:
    """One measured native-vector scene, rendered to both editable SVG and PNG."""
    def __init__(self, background, font_dir):
        from PIL import Image, ImageDraw
        self.image = Image.new('RGB', SIZE, background)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">',
                    f'<rect width="1920" height="1080" fill="{background}"/>']
        self.font_dir = Path(font_dir)
        self.bounds = []

    def text(self, xy, value, size, color, bold=False, latin=False):
        from PIL import ImageFont
        filename = ('arialbd.ttf' if bold else 'arial.ttf') if latin else ('msyhbd.ttc' if bold else 'msyh.ttc')
        font = ImageFont.truetype(str(self.font_dir / filename), size)
        box = self.draw.textbbox(xy, value, font=font, anchor='lt')
        if min(box[:2]) < 64 or box[2] > SIZE[0] - 64 or box[3] > SIZE[1] - 64:
            raise ValueError('Cover text outside safe canvas: ' + value)
        self.draw.text(xy, value, font=font, fill=color, anchor='lt')
        family = 'Arial' if latin else 'Microsoft YaHei'
        self.svg.append(f'<text x="{xy[0]}" y="{xy[1]}" fill="{color}" font-size="{size}" '
                        f'font-family="{family}" font-weight="{700 if bold else 400}" dominant-baseline="text-before-edge">'
                        f'{escape(value)}</text>')
        self.bounds.append({'text': value, 'font': filename, 'size': size, 'bbox': list(box)})

    def line(self, points, color, width=4):
        self.draw.line(points, fill=color, width=width, joint='curve')
        self.svg.append('<polyline points="' + ' '.join(f'{x},{y}' for x, y in points)
                        + f'" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

    def circle(self, xy, radius, color, width=4):
        x, y = xy
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=width)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def save(self, folder, candidate_id):
        from PIL import Image
        stem = Path(folder) / ('封面候选-' + candidate_id)
        self.image.save(stem.with_suffix('.png'))
        self.image.resize(MOBILE_SIZE, Image.Resampling.LANCZOS).save(Path(str(stem) + '-手机.png'))
        stem.with_suffix('.svg').write_text('\n'.join(self.svg + ['</svg>']) + '\n', encoding='utf-8')
        return {'full': asset(stem.with_suffix('.png')), 'mobile': asset(Path(str(stem) + '-手机.png')),
                'editable_svg': asset(stem.with_suffix('.svg')), 'text_measurements': self.bounds}


def render_cover(candidate_id, folder, font_dir='C:/Windows/Fonts'):
    """Build real 16:9 abstract-relation covers; no stock or answer annotations."""
    if candidate_id not in ('A', 'B', 'C'):
        raise ValueError('Unknown candidate')
    Path(folder).mkdir(parents=True, exist_ok=True)
    c = _Canvas(DARK if candidate_id == 'B' else PAPER, font_dir)
    foreground = PAPER if candidate_id == 'B' else INK
    c.text((108, 84), '英语阅读', 42, BLUE, bold=True)
    if candidate_id == 'A':
        c.text((108, 244), '词一样', 160, foreground, bold=True)
        c.text((108, 444), '就能选？', 160, foreground, bold=True)
        c.text((1000, 296), 'workshops', 108, BLUE, latin=True)
        c.text((1000, 578), 'workshops', 108, BRICK, latin=True)
        c.line([(998, 449), (1400, 449), (1688, 360), (1780, 360)], BLUE, 5)
        c.line([(998, 731), (1400, 731), (1688, 832), (1780, 832)], BRICK, 5)
        for point, color in (((998, 449), BLUE), ((1780, 360), BLUE), ((998, 731), BRICK), ((1780, 832), BRICK)):
            c.circle(point, 13, color, 4)
    elif candidate_id == 'B':
        c.text((108, 218), '看着一样', 140, foreground, bold=True)
        c.text((108, 392), '做的事呢？', 140, foreground, bold=True)
        c.line([(1130, 250), (1660, 250), (1780, 356), (1400, 356)], BLUE, 5)
        c.line([(1130, 706), (1660, 706), (1780, 600), (1400, 600)], BRICK, 5)
        c.circle((1130, 250), 22, BLUE, 5)
        c.circle((1130, 706), 22, BRICK, 5)
        c.text((1115, 440), 'workshops', 110, foreground, latin=True)
        c.line([(1390, 356), (1390, 412)], BLUE, 4)
        c.line([(1390, 565), (1390, 600)], BRICK, 4)
    else:
        c.text((108, 224), '词对上了', 148, foreground, bold=True)
        c.text((108, 408), '意思呢？', 148, foreground, bold=True)
        c.line([(952, 704), (1306, 600), (1784, 600), (1430, 704), (952, 704)], BLUE, 5)
        c.line([(1050, 920), (1306, 848), (1784, 848), (1528, 920), (1050, 920)], BRICK, 5)
        c.line([(1050, 704), (1050, 920)], '#CBC7BD', 3)
        c.line([(1700, 600), (1700, 848)], '#CBC7BD', 3)
        c.text((1086, 516), 'workshops', 100, BLUE, latin=True)
        c.text((1195, 724), 'workshops', 100, BRICK, latin=True)
        c.circle((952, 704), 12, BLUE, 4)
        c.circle((1784, 848), 12, BRICK, 4)
    c.text((108, 944), '英语有画说 · 学霸这题怎么做？', 36, foreground)
    return c.save(folder, candidate_id)


def generate_candidates(folder, revision, author_path, plan_path, font_dir='C:/Windows/Fonts'):
    """Create the real candidate package while final media and choice stay empty."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'BILIBILI_PACKAGE.json'
    if manifest_path.exists():
        raise ValueError('Do not overwrite a candidate package; create a revision')
    refs = _reference_inputs(author_path, plan_path)
    candidates = []
    for definition in CANDIDATES:
        candidate = deepcopy(definition)
        candidate['cover'] = render_cover(candidate['id'], folder, font_dir)
        candidate.update(creative_status='PENDING_USER_AND_CHATGPT_SELECTION', selected=False)
        candidates.append(candidate)
    teaching_sources = _sources(_json(plan_path))
    text = publication_text(teaching_sources)
    text_path = folder / '简介与发布文案.md'
    text_path.write_text(publication_markdown(text), encoding='utf-8')
    feedback = feedback_template(revision)
    feedback.update(platform='BILIBILI', published_version=None)
    feedback_path = folder / '发布后数据登记入口.json'
    _write(feedback_path, {'state': 'NOT_PUBLISHED', 'actual_observations': [], 'template': feedback,
        'consumer': 'content_os.engagement_learning.AudienceLearning',
        'workflow': ['freeze the actual final cut and title/cover/description versions',
                     'after actual manual publication, AudienceLearning.publish with real URL and post ID',
                     'AudienceLearning.performance or CSV import with real source and observation window'],
        'note': 'This is a handoff to the existing ledger, not invented platform results or a second observation system.'})
    package = {'schema': VERSION, 'revision': revision, 'platform': 'BILIBILI',
        'delivery_geometry': {'video': [3840, 2160], 'fps': 24, 'cover': list(SIZE),
            'mobile_review': list(MOBILE_SIZE), 'scope': 'user_requested_horizontal_delivery_not_live_platform_UI_policy'},
        'reference_inputs': refs, 'candidates': candidates, 'publication_text': text,
        'publication_text_asset': asset(text_path), 'teaching_sources': teaching_sources,
        'rights': {key: 'HOLD' for key in ('teaching_source_display', 'music_recording', 'voice_recording', 'public_release')},
        'media': None, 'final_media_qa': None, 'selection': None,
        'selection_status': 'PENDING_USER_AND_CHATGPT_SELECTION',
        'perception': {'covers_actual_png': 'PENDING', 'mobile_cover_readability': 'PENDING',
                       'film_full_speed_watch': 'UNOBSERVED', 'film_listening': 'UNOBSERVED'},
        'feedback_entry': asset(feedback_path), 'published': False, 'public_render_ready': False,
        'publication_authority': 'content_os.showcase.decide / existing independent release reviews',
        'state': 'CANDIDATES_READY_NEW_MEDIA_PENDING'}
    _write(manifest_path, package)
    _write(folder / '标题与封面候选.json', candidates)
    write_review_page(folder, package)
    return package


def packaging_bindings(package):
    """Content bytes, title, description, sources and media all expire old choices."""
    return sha({key: package[key] for key in ('schema', 'revision', 'platform', 'delivery_geometry',
        'reference_inputs', 'candidates', 'publication_text', 'publication_text_asset',
        'teaching_sources', 'rights', 'media', 'final_media_qa')})


def choice_template(package, candidate_id):
    if candidate_id not in {candidate['id'] for candidate in package['candidates']}:
        raise ValueError('Unknown cover candidate')
    return {'candidate_id': candidate_id, 'status': 'PENDING', 'reviewer_kind': 'human',
        'origin': 'external_user_and_chatgpt', 'reviewer': '', 'reviewed_at': '',
        'bindings_sha': packaging_bindings(package), 'evidence': None,
        'note': 'External creative selection only; never approves rights or publication.'}


def selection_status(package):
    review = package.get('selection')
    if not review:
        return 'PENDING_USER_AND_CHATGPT_SELECTION'
    if review.get('bindings_sha') != packaging_bindings(package):
        return 'INVALIDATED_BY_CHANGED_INPUTS'
    if review.get('status') != 'APPROVED' or review.get('reviewer_kind') != 'human' or review.get('origin') != 'external_user_and_chatgpt':
        return 'PENDING_USER_AND_CHATGPT_SELECTION'
    try:
        if not review.get('reviewer', '').strip() or datetime.fromisoformat(review['reviewed_at']).tzinfo is None:
            return 'PENDING_USER_AND_CHATGPT_SELECTION'
        if review['candidate_id'] not in {candidate['id'] for candidate in package['candidates']}:
            return 'INVALID_SELECTION'
        _verify(review['evidence'])
        validate_assets(package)
    except (KeyError, OSError, TypeError, ValueError):
        return 'INVALID_EXTERNAL_CREDENTIAL_OR_ASSET'
    return 'EXTERNAL_CREATIVE_SELECTION_RECORDED'


def validate_assets(package):
    if package.get('schema') != VERSION or package.get('platform') != 'BILIBILI':
        raise ValueError('Only Bilibili packaging v1 is supported')
    if package.get('public_render_ready') is not False or package.get('published') is not False:
        raise ValueError('Packaging cannot authorize or claim publication; use the existing external review/registration path')
    for item in (package['reference_inputs']['author'], package['reference_inputs']['plan'],
                 package['publication_text_asset'], package['feedback_entry']):
        _verify(item)
    if (Path(package['publication_text_asset']['path']).read_text(encoding='utf-8')
            != publication_markdown(package['publication_text'])):
        raise ValueError('Publication text differs from the actual review document')
    for item in package['reference_inputs']['source_assets']:
        _verify(item)
    for candidate in package['candidates']:
        for key in ('full', 'mobile', 'editable_svg'):
            _verify(candidate['cover'][key])
    for key in ('media', 'final_media_qa'):
        if package.get(key):
            _verify(package[key])
    return True


def finalize(package, author_path, plan_path, media_path, qa_path):
    """Bind a real same-revision 4K24 export; keep every human decision separate."""
    validate_assets(package)
    result = deepcopy(package)
    refs = _reference_inputs(author_path, plan_path)
    if refs['source_revision'] != result['revision']:
        raise ValueError('Final film must belong to this packaging revision')
    if refs['source_anchors'] != result['reference_inputs']['source_anchors']:
        raise ValueError('Real cover anchors changed; create new candidates')
    plan, qa = _json(plan_path), _json(qa_path)
    media = asset(media_path)
    if (qa.get('sha256') != media['sha256'] or qa.get('same_revision') != result['revision']
        or qa.get('plan_sha256') != file_sha(plan_path) or qa.get('frames') != plan['frames']
        or Path(qa.get('media', '')).resolve() != Path(media_path).resolve()
        or qa.get('full_decode') != 'PASS' or not qa.get('formal_4k_rendered')):
        raise ValueError('Final media QA is missing, stale or from a different cut')
    actual = inspect_media(media_path)
    if abs(actual['duration'] - plan['frames'] / 24) > 1 / 24:
        raise ValueError('Actual media does not match the authored clock')
    result.update(reference_inputs=refs, teaching_sources=_sources(plan), media={**media, 'inspection': actual},
                  final_media_qa=asset(qa_path), state='MEDIA_BOUND_FOR_USER_CREATIVE_AND_RELEASE_REVIEW',
                  published=False, public_render_ready=False)
    result['selection_status'] = selection_status(result)
    return result


def write_review_page(folder, package):
    """A real local preview, deliberately without publication controls."""
    folder = Path(folder)
    cards = []
    for c in package['candidates']:
        full = Path(c['cover']['full']['path']).name
        mobile = Path(c['cover']['mobile']['path']).name
        rows = ''.join('<dt>' + escape(label) + '</dt><dd>' + escape(c[key]) + '</dd>' for label, key in (
            ('视觉冲突', 'visual_conflict'), ('构图', 'composition'), ('标题与封面互补', 'title_cover_complement'),
            ('前15秒兑现', 'first_15_seconds'), ('受众假设', 'audience_hypothesis'), ('误导风险', 'misleading_risk')))
        cards.append(f'<article><h2>候选 {c["id"]}</h2><h3>{escape(c["title"])}</h3>'
                     f'<a href="{escape(full)}"><img class="full" src="{escape(full)}" alt="封面候选 {c["id"]}"></a>'
                     f'<p>手机缩图（320×180）</p><img width="320" height="180" src="{escape(mobile)}" alt="手机缩图">'
                     f'<dl>{rows}</dl></article>')
    html = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    html += '<title>B站标题与封面候选</title><style>body{margin:32px auto;max-width:1120px;padding:0 24px;background:#f2f0ea;color:#20211f;font:17px/1.7 system-ui}h1,h2,h3{line-height:1.4}article{margin:48px 0 72px}img.full{width:100%;height:auto}dt{font-weight:600;margin-top:16px}dd{margin:4px 0}p.status{color:#6c514b}</style>'
    html += '<h1>B站标题与封面候选</h1><p class="status">三套均待用户与ChatGPT选择。未定稿，未发布，不代表音乐、教学来源或整片感知审核通过。</p>'
    html += '<p>封面为1920×1080横版；可点击查看完整尺寸。封面中的 workshops 均绑定本期真实写作营原文与选项。抽象轨迹提出关系是否一致的疑问，不代替教学证据。</p>'
    html += ''.join(cards) + '<p><a href="简介与发布文案.md">简介与发布文案</a> · <a href="BILIBILI_PACKAGE.json">同版绑定与审核状态</a></p></html>'
    (folder / '封面审阅入口.html').write_text(html, encoding='utf-8')


def save_package(folder, package):
    validate_assets(package)
    _write(Path(folder) / 'BILIBILI_PACKAGE.json', package)
    write_review_page(folder, package)
