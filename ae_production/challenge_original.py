"""Read the actual original-layer 72-frame challenge, never certify perception.

The expected chunk inventory is derived from AV_PLAN, not a build's claimed
challenge inventory.  Adobe is read only here; the protected Host owns execution.
"""
import json
import math

INK = [.09, .13, .16]
POLICY = 'SAME_ORIGINAL_TEXTLAYERS_NO_RECREATION'
NEUTRAL_TEXT_EFFECT_VALUES = {
    'ADBE Text Anchor Point 3D': [0, 0, 0], 'ADBE Text Position 3D': [0, 0, 0],
    'ADBE Text Scale 3D': [100, 100, 100], 'ADBE Text Skew': 0, 'ADBE Text Skew Axis': 0,
    'ADBE Text Rotation X': 0, 'ADBE Text Rotation Y': 0, 'ADBE Text Rotation': 0,
    'ADBE Text Opacity': 100, 'ADBE Text Fill Opacity': 100, 'ADBE Text Stroke Opacity': 100,
    'ADBE Text Fill Color': INK, 'ADBE Text Tracking Amount': 0,
    'ADBE Text Fill Hue': 0, 'ADBE Text Fill Saturation': 0, 'ADBE Text Fill Brightness': 0,
}


def _close(a, b, tol=1e-4):
    return type(a) in (int, float) and math.isfinite(a) and abs(a-b) <= tol


def _vec(a, b, tol=1e-3):
    return isinstance(a, list) and len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))


def _id(value): return type(value) is int and value > 0


def original_challenge_scope(plan, native):
    contract = plan.get('audience_challenges')
    if contract is None: return []
    manifest = native['audit'].get('audience_challenges', [])
    if (len(manifest) != len(contract['rows'])
            or [m['scene_id'] for m in manifest] != [c['scene'] for c in contract['rows']]):
        raise ValueError('Original challenge native build inventory is incomplete')
    result = []
    for challenge, built in zip(contract['rows'], manifest):
        world = challenge['world']; data = plan['worlds'][world]; q = data['question']
        base = plan['world_order'].index(world) * 10000
        if (built.get('source_identity') != POLICY or built.get('world') != world
                or built.get('question_id') != q['question_id'] or q['question_id'] != challenge['question_id']
                or built.get('frames') != 72 or challenge['end_frame']-challenge['start_frame'] != 72
                or any(not _close(built.get(k), challenge[k], 1e-6) for k in ('start', 'end', 'handoff_end'))
                or not _close(challenge['end']-challenge['start'], 3, 1e-6)
                or not _close(challenge['handoff_end']-challenge['end'], .8, 1e-6)
                or not _close(challenge['start_frame']/24, challenge['start'], 1e-6)
                or not _close(challenge['end_frame']/24, challenge['end'], 1e-6)):
            raise ValueError('Original challenge native identity or exact clock changed')
        blocks = [b for b in data['blocks'] if b['visible']]
        cursor = 0
        for block in data['blocks']:
            if (block['start'] != cursor or block['text'] != q['passage'][block['start']:block['end']]
                    or block['visible'] != bool(block['text'].strip())):
                raise ValueError('Original challenge must bind every complete original article block')
            cursor = block['end']
        if cursor != len(q['passage']):
            raise ValueError('Original challenge cannot omit the tail of the full article')
        source_rows = []
        for block in blocks:
            sources = [s for s in native['audit']['sources'] if s['id'] == block['id']]
            if (len(sources) != 1 or sources[0]['text'] != block['text']
                    or block['text'] != q['passage'][block['start']:block['end']]
                    or not _id(sources[0]['layer_id']) or not _vec(sources[0]['position'], sources[0]['position'])
                    or len(sources[0]['position']) != 3
                    or not _close(sources[0]['position'][0], base+2250)
                    or not _close(sources[0]['position'][2], 100)):
                raise ValueError('Original challenge source inventory is not the complete real article')
            source_rows.append({'name': block['id'], 'proxy_id': sources[0]['layer_id'],
                'text': block['text'], 'start': block['start'], 'end': block['end'],
                'position': sources[0]['position'], 'source': data['source']})
        expected = []
        for block in blocks:
            cursor = block['start']
            for chunk in block['reading_chunks']:
                if (chunk['text'] != q['passage'][chunk['start']:chunk['end']]
                        or not cursor <= chunk['start'] < chunk['end'] <= block['end']
                        or q['passage'][cursor:chunk['start']].strip()):
                    raise ValueError('Original challenge chunk is not source-exact')
                cursor = chunk['end']
                expected.append({'chunk_id': chunk['id'], 'text': chunk['text'], 'start': chunk['start'],
                    'end': chunk['end'], 'source_layer': block['id'],
                    'range': [chunk['start']-block['start'], chunk['end']-block['start']],
                    'animator': 'CHALLENGE_FOLD_'+challenge['scene']+'_'+str(len(expected))})
            if q['passage'][cursor:block['end']].strip():
                raise ValueError('Original challenge cannot omit words between its authored sense groups')
        if not expected or len({c['chunk_id'] for c in expected}) != len(expected):
            raise ValueError('Original challenge cannot omit or duplicate the complete article sense groups')
        actual = built.get('article_chunks', [])
        if built.get('article_layers') != [b['id'] for b in blocks] or len(actual) != len(expected):
            raise ValueError('Original challenge did not use every original layer and sense group')
        for claimed, wanted in zip(actual, expected):
            original = next(s for s in source_rows if s['name'] == wanted['source_layer'])
            if (any(claimed.get(k) != v for k, v in wanted.items())
                    or claimed.get('source_layer_id') != original['proxy_id']
                    or not _vec(claimed.get('source_position'), original['position'])
                    or not _vec(claimed.get('challenge_position'), [base+40, 132, 0])
                    or not _vec(claimed.get('delta'), claimed.get('delta', []))
                    or len(claimed.get('delta', [])) != 3
                    or not _close(claimed['delta'][2], 0)
                    or not _close(claimed.get('scale'), claimed.get('scale', -1))
                    or not 0 < claimed['scale'] <= 400
                    or type(claimed.get('width')) not in (int, float)
                    or not math.isfinite(claimed['width']) or not 0 < claimed['width'] <= 760
                    or not isinstance(claimed.get('baseline'), list) or len(claimed['baseline']) != 3
                    or not base+40 <= claimed['baseline'][0] <= base+800
                    or not 132 <= claimed['baseline'][1] <= 604 or claimed['baseline'][2] != 0
                    or claimed['baseline'][0]+claimed['width'] > base+800+.01):
                raise ValueError('Original challenge folded source identity, glyph range or layout changed')
        for previous, current in zip(actual, actual[1:]):
            source_gap = q['passage'][previous['end']:current['start']]
            if abs(current['baseline'][1]-previous['baseline'][1]) < .01:
                space = current['baseline'][0]-previous['baseline'][0]-previous['width']
                if source_gap and source_gap.isspace() and space < 2:
                    raise ValueError('Original challenge must preserve visible whitespace between source sense groups')
            elif current['baseline'][1]-previous['baseline'][1] < 17:
                raise ValueError('Original challenge reading rows overlap or reverse their real source order')
        measured_width = max(c['baseline'][0]+c['width']-(base+40) for c in actual)
        measured_height = max(c['baseline'][1]-132+4 for c in actual)
        if (not _close(built.get('article_height'), built.get('article_height', -1))
                or not 0 < built['article_height'] <= 476
                or not _close(built.get('article_width'), built.get('article_width', -1))
                or not 0 < built['article_width'] <= 760
                or not _close(built['article_width'], measured_width, .01)
                or not _close(built['article_height'], measured_height, .01)):
            raise ValueError('Complete original challenge article overflows its reading column')
        result.append({'scene': challenge['scene'], 'world': world, 'question_id': q['question_id'],
            'start': challenge['start'], 'end': challenge['end'], 'handoff_end': challenge['handoff_end'],
            'start_frame': challenge['start_frame'], 'end_frame': challenge['end_frame'],
            'base': base, 'sources': source_rows, 'chunks': actual,
            'glyph_names': [world+'_QUESTION']+[world+'_OPTION_'+c for c in 'ABCD'],
            'proxy_glyphs': built.get('original_glyphs', []),
            'glyph_texts': [q['stem']]+[c+'   '+q['options'][c] for c in 'ABCD']})
    return result


def _state(actual, expected_position, expected_scale, label):
    # [position x/y/z, scale x/y/z, opacity, base-neutral, non-fold-active]
    if (not isinstance(actual, list) or len(actual) != 9
            or not _vec(actual[:3], expected_position) or not _vec(actual[3:6], expected_scale)
            or not _close(actual[6], 100) or actual[7] != 1 or not _close(actual[8], 0)):
        raise ValueError('Original challenge '+label+' is hidden, moved or judgement-emphasized')


def _base_text(actual, exact, font_size, scope):
    events = actual.get('source_text_events', [])
    if (actual.get('text_expression') or not events or not _close(events[0]['time'], scope['start'], 1e-6)
            or any(event['text'] != exact or event['neutral'] != 1 or not _close(event['font_size'], font_size)
                   or not scope['start']-1e-6 <= event['time'] <= scope['handoff_end']+1e-6 for event in events)
            or any(a['time'] >= b['time'] for a, b in zip(events, events[1:]))):
        raise ValueError('Original challenge base text or color changes inside its window/handoff')


def _continuous(previous, current, initial, target, step_limits=None):
    limits = [.55]*6 if step_limits is None else step_limits
    for axis, (old, value, start, end) in enumerate(zip(previous[:6], current[:6], initial[:6], target[:6])):
        distance = end-start
        if abs(distance) < 1e-6:
            if not _close(value, start, .01): return False
        else:
            progress = (value-start)/distance; prior = (old-start)/distance
            if not -.001 <= progress <= 1.001 or progress < prior-.001 or progress-prior > limits[axis]+1e-6:
                return False
    return True


def validate_original_challenges(plan, native, rows):
    scope = original_challenge_scope(plan, native)
    comps = [native['comp_id'], native['master_comp_id']]
    if any(not _id(i) for i in comps) or len(set(comps)) != 2:
        raise ValueError('Original challenge requires two distinct real native compositions')
    expected = {(cid, s['scene']): s for cid in comps for s in scope}
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or {(r['comp_id'], r['scene']) for r in rows} != set(expected)):
        raise ValueError('Original challenge must inspect both native compositions and every question')
    identities = {}; owners = {}
    for row in rows:
        s = expected[(row['comp_id'], row['scene'])]; base = s['base']
        if row.get('extra_challenge_passage_layers') != []:
            raise ValueError('Original challenge cannot recreate the article as a duplicate passage layer')
        article = row['article_layers']; chunks = row['chunks']; glyphs = row['glyphs']
        if ([a['name'] for a in article] != [a['name'] for a in s['sources']]
                or len(chunks) != len(s['chunks']) or [g['name'] for g in glyphs] != s['glyph_names']):
            raise ValueError('Native original challenge layer/chunk inventory changed')
        all_ids = [a['id'] for a in article]+[g['id'] for g in glyphs]
        if any(not _id(i) for i in all_ids) or len(set(all_ids)) != len(all_ids):
            raise ValueError('Native original challenge layer identities must be distinct and persistent')
        for ident in all_ids:
            if ident in owners and owners[ident] != row['comp_id']:
                raise ValueError('Master original challenge must read its own real native layer IDs')
            owners[ident] = row['comp_id']
        for actual, source in zip(article, s['sources']):
            comment = actual['comment']
            if (actual['text'] != source['text'] or comment.get('kind') != 'original_passage'
                    or comment.get('exact_text') != source['text'] or comment.get('source') != source['source']
                    or comment.get('start') != source['start'] or comment.get('end') != source['end']
                    or comment.get('field') != 'passage'
                    or not _close(actual.get('font_size'), actual.get('original_font_size', -1))
                    or not 1 <= actual['font_size'] <= 200
                    or actual['enabled'] is not True or actual['guide'] is not False or actual['three_d'] is not True
                    or actual['in_point'] > s['start'] or actual['out_point'] < s['handoff_end']
                    or actual['neutral'] != 1
                    or actual['fold_names'] != [chunk['animator'] for chunk in s['chunks'] if chunk['source_layer'] == source['name']]):
                raise ValueError('Actual original article text, source comment, font or lifetime changed')
            if row['comp_id'] == comps[0] and actual['id'] != source['proxy_id']:
                raise ValueError('Native proxy original challenge text layer identity changed')
            _base_text(actual, source['text'], actual['original_font_size'], s)
            if any(not _close(c['scale'], 1700/actual['original_font_size'], .01)
                   for c in s['chunks'] if c['source_layer'] == source['name']):
                raise ValueError('Original challenge compact scale must follow its preserved native source font size')
            key = (row['comp_id'], actual['name'])
            if key in identities and identities[key] != actual['id']:
                raise ValueError('One original source acquired inconsistent native identities')
            identities[key] = actual['id']
        for actual, wanted in zip(chunks, s['chunks']):
            source = next(a for a in article if a['name'] == wanted['source_layer'])
            if (actual['name'] != wanted['animator'] or actual['source_id'] != source['id']
                    or actual['range'] != wanted['range'] or actual['units'] != 2 or actual['smoothness'] != 0
                    or not _vec(actual['delta'], wanted['delta']) or actual['expression_error']
                    or actual['selector_count'] != 1 or actual['property_names'] != ['ADBE Text Position 3D']):
                detail = {'comp_id': row['comp_id'], 'scene': row['scene'], 'chunk': wanted['chunk_id'],
                    'name': [actual['name'], wanted['animator']], 'source_id': [actual['source_id'], source['id']],
                    'range': [actual['range'], wanted['range']], 'units': actual['units'],
                    'smoothness': actual['smoothness'], 'delta': [actual['delta'], wanted['delta']],
                    'selector_count': actual['selector_count'], 'property_names': actual['property_names'],
                    'expression_error': actual['expression_error']}
                raise ValueError('Original challenge sense-group selector, glyph range or fold delta changed: '+json.dumps(detail))
        for index, (glyph, text) in enumerate(zip(glyphs, s['glyph_texts'])):
            if (glyph['text'] != text or glyph['enabled'] is not True or glyph['guide'] is not False
                    or glyph['three_d'] is not True or glyph['neutral'] != 1
                    or glyph['in_point'] > s['start'] or glyph['out_point'] < s['handoff_end']):
                raise ValueError('Challenge must carry the complete same original stem and all four options')
            if (len(s['proxy_glyphs']) != 5 or s['proxy_glyphs'][index].get('name') != glyph['name']
                    or s['proxy_glyphs'][index].get('exact_text') != text
                    or not _id(s['proxy_glyphs'][index].get('source_layer_id'))
                    or row['comp_id'] == comps[0] and s['proxy_glyphs'][index]['source_layer_id'] != glyph['id']):
                raise ValueError('Original challenge question proxy identity differs from its real built source glyphs')
            _base_text(glyph, text, 50 if index == 0 else 46, s)
            key = (row['comp_id'], glyph['name'])
            if key in identities and identities[key] != glyph['id']:
                raise ValueError('One original question acquired inconsistent native identities')
            identities[key] = glyph['id']
        badge = row['badge']
        if (badge['text'] != '想先自己做？可暂停' or badge['spoken'] is not False
                or badge['enabled'] is not True or badge['guide'] is not False
                or not _close(badge['in_point'], s['start'], 1e-6) or not _close(badge['out_point'], s['end'], 1e-6)):
            raise ValueError('Challenge pause entry must retain its exact screen-only 72-frame lifetime')
        samples = row['samples']
        if [sample['frame'] for sample in samples] != list(range(s['start_frame'], s['end_frame'])):
            raise ValueError('Original challenge must inspect all and only its 72 frame times')
        for sample in samples:
            if (len(sample['article']) != len(article) or len(sample['chunks']) != len(chunks)
                    or len(sample['glyphs']) != 5 or not _close(sample['badge_opacity'], 100)
                    or not _vec(sample['camera'], [base+640, 320, -1550, base+640, 320, 0, 0])):
                raise ValueError('Original challenge source, badge or neutral fixed camera is incomplete')
            for actual, source in zip(sample['article'], article):
                _state(actual, [base+40, 132, 0], [1700/source['original_font_size']]*3, 'article')
            if any(not _close(a, 100) for a in sample['chunks']):
                raise ValueError('Original challenge must continuously fold every sense group through all 72 frames')
            for index, actual in enumerate(sample['glyphs']):
                pos = [base+(830 if index else 820), 300+(index-1)*58 if index else 192, 0]
                _state(actual, pos, [38]*3, 'stem/options')
        handoff = row['handoff']
        times = [s['end']+i/24 for i in range(math.ceil((s['handoff_end']-s['end'])*24))]+[s['handoff_end']]
        if len(handoff) != len(times) or any(not _close(a['time'], b, 1e-6) for a, b in zip(handoff, times)):
            raise ValueError('Original challenge same-glyph handoff must be observed continuously to its final exact pose')
        prior = [100]*len(chunks)
        prior_article = samples[-1]['article']; prior_glyphs = samples[-1]['glyphs']
        prior_time = (s['end_frame']-1)/24
        for sample in handoff:
            if (len(sample['article']) != len(article) or len(sample['glyphs']) != 5 or len(sample['chunks']) != len(chunks)
                    or any(not _close(a, a) or not -1e-4 <= a <= old+1e-4 for a, old in zip(sample['chunks'], prior))):
                raise ValueError('Original challenge fold must return continuously without glyph reset or overshoot')
            prior = sample['chunks']
            for state in sample['article']+sample['glyphs']:
                if (len(state) != 9 or not _close(state[6], 100) or state[7] != 1 or not _close(state[8], 0)
                        or any(not _close(v, v) for v in state[:6])):
                    raise ValueError('Original challenge glyphs cannot disappear during their continuous handoff')
            for index, (old, now, source) in enumerate(zip(prior_article, sample['article'], s['sources'])):
                initial = [base+40, 132, 0]+[1700/article[index]['original_font_size']]*3
                limits = [.55]*6
                # The inherited handoff sends originals behind the paper in
                # 0.12s, then continues their slower lateral/scale return. Zero
                # velocity Bezier keys with 55% influence have a normalized
                # maximum slope 1/(1-.55); apply that only to this depth leg.
                if prior_time < s['end']+.12 and sample['time'] > s['end']:
                    limits[2] = max(.55, min(.99, (sample['time']-prior_time)/.12/(1-.55)))
                if not _continuous(old, now, initial, source['position']+[100]*3, limits):
                    raise ValueError('Original article handoff jumps, reverses or overshoots instead of carrying the same glyphs')
            for index, (old, now) in enumerate(zip(prior_glyphs, sample['glyphs'])):
                initial = [base+(830 if index else 820), 300+(index-1)*58 if index else 192, 0]+[38]*3
                target = [base+(90 if index else 80), 230+(index-1)*80 if index else 95, 0]+[100]*3
                if not _continuous(old, now, initial, target):
                    raise ValueError('Original question handoff jumps, reverses or overshoots instead of carrying the same glyphs')
            prior_article = sample['article']; prior_glyphs = sample['glyphs']
            prior_time = sample['time']
        if any(not _close(v, 0) for v in handoff[-1]['chunks']):
            raise ValueError('Original challenge fold must fully return every sense group')
        for actual, source in zip(handoff[-1]['article'], s['sources']): _state(actual, source['position'], [100]*3, 'returned article')
        for index, actual in enumerate(handoff[-1]['glyphs']):
            origin = [base+(90 if index else 80), 230+(index-1)*80 if index else 95, 0]
            _state(actual, origin, [100]*3, 'returned stem/options')
    return {'status': 'PASS_NATIVE_ORIGINAL_LAYERS_72_FRAME_PARAMETERS', 'source_identity': POLICY,
            'rows': rows, 'normal_speed_review': 'UNOBSERVED', 'mobile_legibility': 'UNOBSERVED',
            'listening_review': 'UNOBSERVED'}


def original_challenge_readback_code(plan, native):
    """Return read-only Adobe code so a sole host owner can capture raw evidence."""
    scope = original_challenge_scope(plan, native)
    if not scope: return None
    code = r'''var scope=__SCOPE__,ids=__IDS__,neutralEffects=__NEUTRAL__,out=[];
function unique(c,name){var found=null;for(var i=1;i<=c.numLayers;i++){var l=c.layer(i);if(l.name!==name)continue;if(found)throw Error('Duplicate original challenge layer '+name);found=l;}if(!found)throw Error('Missing original challenge layer '+name);return found;}
function tr(l,n){return l.property('ADBE Transform Group').property(n);}
function amount(an,t){var v=an.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount').valueAtTime(t,false);return v instanceof Array?v[0]:v;}
function neutral(l,t){var d=l.property('Source Text').valueAtTime(t,false),ink=[.09,.13,.16];for(var k=0;k<d.text.length;k++){var col=d.characterRange(k,k+1).fillColor;for(var v=0;v<3;v++)if(Math.abs(col[v]-ink[v])>.00001)return 0;}return 1;}
var currentFoldPrefix='',preparedAnimators={};
function prepareAnimators(l){var aa=l.property('ADBE Text Properties').property('ADBE Text Animators'),list=[];for(var k=1;k<=aa.numProperties;k++){var an=aa.property(k);if(an.name.indexOf(currentFoldPrefix)===0)continue;var props=an.property('ADBE Text Animator Properties'),effects=[];for(var pi=1;pi<=props.numProperties;pi++){var prop=props.property(pi);if(prop.isModified)effects.push(prop);}list.push({animator:an,effects:effects});}preparedAnimators[l.id]=list;}
function neutralEffect(prop,t){var expected=neutralEffects[prop.matchName];if(expected===undefined||prop.expressionError)return false;var value=prop.valueAtTime(t,false);if(expected instanceof Array){if(!(value instanceof Array)||value.length<expected.length)return false;for(var i=0;i<expected.length;i++)if(Math.abs(value[i]-expected[i])>.001)return false;if(prop.matchName==='ADBE Text Fill Color'&&value.length>3&&Math.abs(value[3]-1)>.001)return false;return true;}return typeof value==='number'&&Math.abs(value-expected)<.001;}
function active(l,t){var list=preparedAnimators[l.id],peak=0;for(var k=0;k<list.length;k++){var entry=list[k],v=Math.abs(amount(entry.animator,t));if(v<.001)continue;for(var j=0;j<entry.effects.length;j++)if(!neutralEffect(entry.effects[j],t)&&v>peak)peak=v;}return peak;}
var baseNeutral={};
function state(l,t){var p=tr(l,'ADBE Position').valueAtTime(t,false),s=tr(l,'ADBE Scale').valueAtTime(t,false);return [p[0],p[1],p[2],s[0],s[1],s[2],tr(l,'ADBE Opacity').valueAtTime(t,false),baseNeutral[l.id],active(l,t)];}
function staticLayer(l,t,end){prepareAnimators(l);var prop=l.property('Source Text'),d=prop.valueAtTime(t,false),events=[],times=[t];for(var k=1;k<=prop.numKeys;k++)if(prop.keyTime(k)>t&&prop.keyTime(k)<=end)times.push(prop.keyTime(k));for(var k=0;k<times.length;k++){var doc=prop.valueAtTime(times[k],false);events.push({time:times[k],text:doc.text.replace(/\r/g,'\n'),neutral:neutral(l,times[k]),font_size:doc.fontSize});}baseNeutral[l.id]=events[0].neutral;return {name:l.name,id:l.id,text:d.text.replace(/\r/g,'\n'),enabled:l.enabled,guide:l.guideLayer,three_d:l.threeDLayer,in_point:l.inPoint,out_point:l.outPoint,neutral:events[0].neutral,source_text_events:events,text_expression:prop.expressionEnabled?prop.expression:''};}
for(var ci=0;ci<ids.length;ci++){var c=app.project.itemByID(ids[ci]);
 for(var si=0;si<scope.length;si++){var s=scope[si],layers=[],chunkProps=[],article=[],chunks=[],glyphLayers=[],glyphs=[],samples=[],handoff=[],extras=[];currentFoldPrefix='CHALLENGE_FOLD_'+s.scene+'_';
  for(var li=1;li<=c.numLayers;li++)if(c.layer(li).name.indexOf('CHALLENGE_PASSAGE_')===0)extras.push(c.layer(li).name);
  for(var li=0;li<s.sources.length;li++){var l=unique(c,s.sources[li].name),st=staticLayer(l,s.start,s.handoff_end);st.comment=JSON.parse(l.comment);st.font_size=l.property('Source Text').valueAtTime(s.start,false).fontSize;st.original_font_size=l.property('Source Text').valueAtTime(0,false).fontSize;st.fold_names=[];var aa=l.property('ADBE Text Properties').property('ADBE Text Animators');for(var ai=1;ai<=aa.numProperties;ai++)if(aa.property(ai).name.indexOf(currentFoldPrefix)===0)st.fold_names.push(aa.property(ai).name);layers.push(l);article.push(st);}
  for(var ki=0;ki<s.chunks.length;ki++){var wanted=s.chunks[ki],l=unique(c,wanted.source_layer),an=l.property('ADBE Text Properties').property('ADBE Text Animators').property(wanted.animator);if(!an)throw Error('Missing fold animator '+wanted.animator);var sels=an.property('ADBE Text Selectors'),sel=sels.property(1),ad=sel.property('ADBE Text Range Advanced'),props=an.property('ADBE Text Animator Properties'),names=[];for(var pi=1;pi<=props.numProperties;pi++){var property=props.property(pi);if(property.isModified||property.matchName==='ADBE Text Position 3D')names.push(property.matchName);}chunkProps.push(an);chunks.push({name:an.name,source_id:l.id,range:[sel.property('ADBE Text Index Start').valueAtTime(s.start,false),sel.property('ADBE Text Index End').valueAtTime(s.start,false)],units:ad.property('ADBE Text Range Units').value,smoothness:ad.property('ADBE Text Selector Smoothness').value,delta:props.property('ADBE Text Position 3D').valueAtTime(s.start,false),selector_count:sels.numProperties,property_names:names,expression_error:ad.property('ADBE Text Selector Max Amount').expressionError});}
  for(var gi=0;gi<s.glyph_names.length;gi++){var l=unique(c,s.glyph_names[gi]);glyphLayers.push(l);glyphs.push(staticLayer(l,s.start,s.handoff_end));}
  var badge=unique(c,'CHALLENGE_PAUSE_'+s.scene),bs=staticLayer(badge,s.start,s.end);bs.spoken=JSON.parse(badge.comment).spoken;
  var cam=unique(c,'READING_CAMERA');
  function sampleAt(t){var a=[],g=[],v=[];for(var j=0;j<layers.length;j++)a.push(state(layers[j],t));for(var j=0;j<glyphLayers.length;j++)g.push(state(glyphLayers[j],t));for(var j=0;j<chunkProps.length;j++)v.push(amount(chunkProps[j],t));return {time:t,article:a,glyphs:g,chunks:v};}
  for(var frame=s.start_frame;frame<s.end_frame;frame++){var t=frame/24,z=sampleAt(t),p=tr(cam,'ADBE Position').valueAtTime(t,false),target=tr(cam,'ADBE Anchor Point').valueAtTime(t,false);z.frame=frame;z.badge_opacity=tr(badge,'ADBE Opacity').valueAtTime(t,false);z.camera=[p[0],p[1],p[2],target[0],target[1],target[2],cam.property('ADBE Camera Options Group').property('ADBE Camera Aperture').valueAtTime(t,false)];samples.push(z);}
  for(var f=0;f<Math.ceil((s.handoff_end-s.end)*24);f++)handoff.push(sampleAt(s.end+f/24));handoff.push(sampleAt(s.handoff_end));
  out.push({comp_id:c.id,scene:s.scene,article_layers:article,chunks:chunks,glyphs:glyphs,badge:bs,samples:samples,handoff:handoff,extra_challenge_passage_layers:extras});
 }
}return out;'''
    return code.replace('__SCOPE__', json.dumps(scope, ensure_ascii=False)).replace(
        '__IDS__', json.dumps([native['comp_id'], native['master_comp_id']])).replace(
        '__NEUTRAL__', json.dumps(NEUTRAL_TEXT_EFFECT_VALUES))


def original_challenge_readback(host, plan, native, raw_only=False, evidence_path=None):
    code = original_challenge_readback_code(plan, native)
    if code is None: return None
    observed = host.js(code)
    from pathlib import Path
    from video_contracts import sha, write
    packet = {'kind': 'RAW_NATIVE_ORIGINAL_CHALLENGE_NOT_YET_VALIDATED',
              'plan_content_sha': sha(plan), 'native_build_content_sha': sha(native),
              'rows': observed, 'normal_speed_review': 'UNOBSERVED', 'listening_review': 'UNOBSERVED'}
    if evidence_path is None and getattr(host, 'folder', None) is not None:
        evidence_path = Path(host.folder)/'ORIGINAL_CHALLENGE_NATIVE_RAW.json'
    if evidence_path is not None: write(Path(evidence_path), packet)
    if raw_only: return packet
    return validate_original_challenges(plan, native, observed)
