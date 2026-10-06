"""Expression-led layouts of frozen copy. No new teaching claims are authored.

This presentation is separate from the copy lock. Re-derivation binds every
visible excerpt, role, geometry and native event to the exact input plan.
"""
import re
from video_contracts import sha
from .passage_video import wrap

VERSION = '0.3.0'
PAPER = '#FAF8F2'
INK = '#243530'
BLUE = '#526E87'
OCHRE = '#967548'
SAGE = '#527B65'
BRICK = '#985D4D'


def direct(plan, bundle, modes):
    from PIL import ImageFont
    if set(modes) != {s['segment_id'] for s in plan['scenes']}:
        raise ValueError('Every scene needs one explicit presentation mode')
    scenes = {}
    for scene in plan['scenes']:
        sid = scene['segment_id']; mode = modes[sid]; nodes = []
        if mode not in ('overview', 'instances', 'paired', 'focus', 'decompose',
                        'comparison', 'verdict', 'boundary', 'recap'):
            raise ValueError('Unknown composition mode')
        if mode == 'verdict' and scene['kind'] != 'closure':
            raise ValueError('Only a frozen closure can use the verdict composition')
        if mode == 'boundary' and scene['kind'] != 'boundary':
            raise ValueError('Boundary composition requires an upstream boundary')
        if mode == 'recap' and not next(s for s in bundle['payload']['review']['segments']
                                       if s['segment_id'] == sid).get('summary_refs'):
            raise ValueError('Recap requires frozen cross-question decision bindings')

        def panel(name, x, y, w, h, color, event=None, travel=0):
            nodes.append(dict(type='panel', name=name, x=x, y=y, w=w, h=h,
                              color=color, event=event, travel=travel))

        def text(name, value, x, y, width, size, origin, color=INK,
                 english=False, event=None, travel=0, zoom=1):
            font = ImageFont.truetype(plan['fonts']['english' if english else 'chinese'], size)
            if not english and hasattr(font, 'get_variation_names'):
                try:
                    if b'Regular' in font.get_variation_names(): font.set_variation_by_name(b'Regular')
                except OSError:
                    pass  # A static regular font has no variation table.
            copy = wrap(value, font, width)
            # A lone Chinese glyph is not an acceptable last line in a teaching
            # heading. Prefer a small, bounded size reduction to splitting a word.
            if not english and name == 'JUDGMENT':
                original_size = size
                while any(re.fullmatch(r'[\u4e00-\u9fff]', line) for line in copy.splitlines()):
                    size -= 1
                    if size < original_size*.85: raise ValueError('Chinese heading needs editorial re-layout')
                    font = ImageFont.truetype(plan['fonts']['chinese'], size)
                    try:
                        if b'Regular' in font.get_variation_names(): font.set_variation_by_name(b'Regular')
                    except (OSError, AttributeError): pass
                    copy = wrap(value, font, width)
            height = len(copy.splitlines()) * size * 1.24
            if y + height > 934 or x < 80 or x + width > 1840:
                raise ValueError('Readable body overflow: ' + sid + '/' + name)
            nodes.append(dict(type='text', name=name, text=copy, x=x, y=y,
                              w=width, h=height, size=size,
                              font='Georgia' if english else 'NotoSansSC-Regular',
                              color=color, origin=origin, event=event, travel=travel, zoom=zoom))

        # The question is outside all moving body groups. The caption band stays light.
        panel('BACKGROUND', 0, 0, 1920, 1080, PAPER)
        panel('HEADER_RULE', 110, 211, 1700, 1, '#D7DCD5')
        text('HEADER', scene['heading'], 110, 48, 1700, 26, 'heading', '#68716A')
        text('QUESTION', scene['stem'], 110, 104, 1700, 38, 'stem')
        segment = next(s for s in bundle['payload']['review']['segments'] if s['segment_id'] == sid)
        # Keep excerpt boundaries. A new line is not a continuation of another quote.
        source = '\n'.join(e['quote'] for e in segment['evidence'] if e['field'] == 'passage')
        screen = scene['screen']
        annotations = scene['annotations']

        def source_text(x, y, width, size, color=INK):
            text('SOURCE', source, x, y, width, size, 'source', color, english=True)

        def judgment(x, y, width, size, color=INK, event=None):
            text('JUDGMENT', screen, x, y, width, size, 'screen', color,
                 event=event, travel=90 if event else 0, zoom=1.18 if event else 1)

        def options(x, y, width, size, gap, dark=False):
            for index, opt in enumerate(scene['options']):
                color = '#D9DFD5' if dark else INK
                if opt['state'] == 'eliminate': color = '#D7AB9B' if dark else BRICK
                if opt['state'] != 'neutral':
                    panel('STATE_' + opt['letter'], x-16, y+index*gap-6,
                          width+32, gap-12, '#34473E' if dark else '#E7DACE',
                          'verdict' if mode == 'verdict' else None, 110)
                text('OPTION_' + opt['letter'], re.sub(r'\s+', ' ', opt['text']),
                     x, y+index*gap, width, size, 'options/'+opt['letter'], color)

        def pullouts(x, y, width, size, color=BLUE):
            # Successive focus windows replace each other; the full source remains.
            for index, annotation in enumerate(annotations):
                text('FOCUS_'+str(index), annotation['quote'], x, y, width, size,
                     'annotations/'+str(index), color, True, 'source_'+str(index), 150, 1.16)
                nodes[-1]['exclusive'] = True

        if mode == 'overview':
            panel('OPTION_AREA', 1240, 232, 680, 704, '#EEEDE3', travel=180)
            source_text(110, 280, 1040, 37)
            judgment(110, 705, 1040, 49)
            options(1310, 320, 500, 29, 125)
            pullouts(110, 605, 1080, 43)
        elif mode == 'instances':
            panel('INSTANCE_AREA', 715, 450, 1205, 486, '#E3EAF0', 'source_0', 320)
            source_text(110, 257, 1690, 34)
            judgment(110, 540, 510, 65)
            for index, annotation in enumerate(annotations):
                y = 475 + index*106
                panel('INSTANCE_RULE_'+str(index), 770, y+66, 1000, 2, BLUE,
                      'source_'+str(index), 220)
                text('INSTANCE_'+str(index), annotation['quote'],
                     785+(index % 2)*70, y, 920, 53, 'annotations/'+str(index),
                     BLUE, True, 'source_'+str(index), 180, 1.22)
        elif mode == 'paired':
            if len(annotations) != 4 or len(screen.splitlines()) != 2:
                raise ValueError('Paired layout requires two explicit bound pairs')
            # Context and approximations stay visible; no inferred chart or percentages.
            panel('LEFT_CONDITION', 0, 232, 956, 704, '#E0E9EE', 'source_0', -260)
            panel('RIGHT_CONDITION', 964, 232, 956, 704, '#EEE3D0', 'source_2', 260)
            parts = scene['source'].split('\nBut ')
            if len(parts) != 2: raise ValueError('Paired evidence needs an explicit contrast boundary')
            for index, part in enumerate((parts[0], 'But '+parts[1])):
                x = 110+index*960
                text('SOURCE_'+str(index), re.sub(r'\s+', ' ', part), x, 285, 740, 34,
                     'source', english=True)
                text('CONDITION_'+str(index), annotations[index*2]['quote'], x, 560,
                     740, 50, 'annotations/'+str(index*2), BLUE if index == 0 else OCHRE,
                     True, 'source_'+str(index*2), 120, 1.22)
                text('RESULT_'+str(index), screen.splitlines()[index], x, 730, 740, 50,
                     'screen', event='source_'+str(index*2+1), travel=110, zoom=1.3)
        elif mode == 'focus':
            panel('FOCUS_AREA', 0, 440, 1920, 252, '#E2E9ED', 'source_0', 310)
            source_text(110, 264, 1690, 40)
            for index, annotation in enumerate(annotations):
                text('FOCUS_'+str(index), annotation['quote'], 150, 476+index*255,
                     1620 if index == 0 else 850, 76 if index == 0 else 50, 'annotations/'+str(index),
                     BLUE if index == 0 else OCHRE, True, 'source_'+str(index), 200, 1.25)
            # Same copy, complementary Chinese line stays beside the focal English.
            text('JUDGMENT', screen, 1110, 748, 690, 44, 'screen')
        elif mode == 'decompose':
            if len(annotations) != 3: raise ValueError('Decomposition needs three bound spans')
            source_text(110, 273, 1690, 44)
            widths = [370, 630, 450]; xs = [110, 570, 1350]
            for index, annotation in enumerate(annotations):
                tone = [BLUE, SAGE, OCHRE][index]
                panel('TRACK_'+str(index), xs[index], 493, widths[index], 5,
                      tone, 'source_'+str(index), 230)
                text('PART_'+str(index), annotation['quote'], xs[index], 540,
                     widths[index], 48, 'annotations/'+str(index), tone, True,
                     'source_'+str(index), 200, 1.2)
            judgment(110, 786, 1690, 52)
        elif mode == 'comparison':
            panel('OPTION_AREA', 1060, 232, 860, 704, '#EEE4D8', travel=260)
            source_text(110, 275, 860, 32)
            options(1150, 300, 660, 32, 132)
            judgment(110, 745, 860, 44)
            pullouts(110, 630, 860, 40)
        elif mode == 'verdict':
            panel('DARK_FIELD', 0, 232, 1920, 704, INK)
            panel('DECISION_FIELD', 1130, 232, 790, 704, '#48664F', 'verdict', 400)
            source_text(110, 280, 920, 33, PAPER)
            judgment(1210, 360, 595, 68, PAPER, 'verdict')
            options(135, 625, 820, 27, 65, True)
            pullouts(110, 510, 930, 39, '#CDD9E3')
        elif mode == 'boundary':
            panel('BOUNDARY_AREA', 0, 232, 840, 704, '#EADFCA', travel=-280)
            judgment(110, 380, 630, 65)
            source_text(930, 285, 870, 34)
            pullouts(930, 732, 870, 42, OCHRE)
        elif mode == 'recap':
            # Cross-question content can only originate in explicit summary refs.
            segment = next(s for s in bundle['payload']['review']['segments'] if s['segment_id'] == sid)
            decisions = bundle['payload']['review']['decisions']
            refs = segment['summary_refs']
            retained = [decisions[i] for i in refs if decisions[i]['effect'] == 'retain']
            questions = bundle['payload']['questions']
            if len(retained) != 4: raise ValueError('Recap needs four retained decisions')
            for index, decision in enumerate(retained):
                question = next(q for q in questions if q['question_id'] == decision['question_id'])
                y = 255+index*141
                panel('RECAP_FIELD_'+str(index), 0, y-12, 1920, 135,
                      '#E4EBE3' if index % 2 == 0 else '#EEE7DA', travel=180*(-1 if index%2 else 1))
                text('ANSWER_'+str(index), str(question['number'])+'  '+decision['candidate'],
                     110, y, 340, 70, 'summary_refs/'+str(decisions.index(decision)), SAGE)
                text('STEM_'+str(index), question['stem'], 485, y+7, 1315, 30,
                     'summary_question/'+question['question_id'])
            text('JUDGMENT', screen.splitlines()[-1], 110, 861, 1690, 42, 'screen')
        panel('CAPTION_PAPER', 0, 941, 1920, 139, PAPER)
        # Extract a bound phrase from its actual reading position. The full source
        # stays visible, so a close-up never silently removes the qualifying context.
        sources = [n for n in nodes if n['type'] == 'text' and n['name'].startswith('SOURCE')]
        for node in nodes:
            if node['type'] != 'text' or not node['origin'].startswith('annotations/'):
                continue
            quote = annotations[int(node['origin'].split('/')[1])]['quote']
            hits = []
            for src in sources:
                lines = src['text'].splitlines(); flat = ' '.join(lines)
                if flat.count(quote) != 1: continue
                at = flat.index(quote); offset = 0
                for line_index, line in enumerate(lines):
                    if offset <= at < offset+len(line):
                        font = ImageFont.truetype(plan['fonts']['english'], src['size'])
                        hits.append(([src['x']+font.getlength(line[:at-offset]),
                                      src['y']+line_index*src['size']*1.24], src['size']/node['size'], src['name']))
                        break
                    offset += len(line)+1
            if len(hits) != 1: raise ValueError('Extraction needs one visible source origin: '+sid+'/'+node['name'])
            node['from_position'], node['from_scale'], node['from_source'] = hits[0]
        scenes[sid] = dict(mode=mode, nodes=nodes, segment_sha=scene['segment_sha'])
    result = dict(version=VERSION, plan_sha=plan['plan_sha'], modes=modes, scenes=scenes,
                  public_render_ready=False, semantic_certification=False)
    result['direction_sha'] = sha(result)
    return result


def validate_direction(direction, plan, bundle):
    if direction != direct(plan, bundle, direction['modes']):
        raise ValueError('Presentation no longer matches frozen copy and geometry')
