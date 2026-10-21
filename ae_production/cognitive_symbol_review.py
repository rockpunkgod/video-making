"""Native Recipe identity, layout and relation readback; no taste certification."""
import json
import math
from pathlib import Path


FOG_BLUE = [126 / 255, 150 / 255, 168 / 255]
SOFT_BRICK = [163 / 255, 111 / 255, 100 / 255]
TRAVEL_SAMPLES = 17


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _close(actual, expected, tolerance=.002):
    return _number(actual) and _number(expected) and abs(actual - expected) <= tolerance


def _vector(actual, expected, tolerance=.002):
    return (isinstance(actual, list) and isinstance(expected, list)
            and len(actual) == len(expected)
            and all(_close(a, b, tolerance) for a, b in zip(actual, expected)))


def _finite_vector(value, length):
    return isinstance(value, list) and len(value) == length and all(_number(x) for x in value)


def _amount(actual, expected):
    # AE can return a scalar or a one/three-channel Max Amount array.
    return (_close(actual, expected, .01) if _number(actual) else
            isinstance(actual, list) and len(actual) in (1, 3)
            and all(_close(channel, expected, .01) for channel in actual))


def _color(actual, expected):
    return (isinstance(actual, list) and len(actual) in (3, 4)
            and _vector(actual[:3], expected)
            and (len(actual) == 3 or _close(actual[3], 1)))


def _identity(value):
    return type(value) is int and value > 0


def _unique(items, key, label):
    if not isinstance(items, list):
        raise ValueError(label + ' inventory is missing')
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ValueError(label + ' inventory contains missing or duplicate IDs')
        result[value] = item
    return result


def _scope(plan, native):
    planned = _unique(plan['symbol_recipes']['rows'], 'symbol_id', 'Planned Recipe')
    built = _unique(native['audit']['symbol_recipes'], 'symbol_id', 'Native Recipe')
    if set(planned) != set(built):
        raise ValueError('Native Recipe inventory differs from the actual plan')
    comps = (native['comp_id'], native['master_comp_id'])
    if any(not _identity(comp) for comp in comps) or comps[0] == comps[1]:
        raise ValueError('Recipe readback requires two distinct native compositions')
    return planned, built, comps


def _thinking_amount(plan, time):
    windows = plan['visual_states']['thinking_windows']
    if not windows or not _number(time):
        raise ValueError('Recipe foreground requires the actual visual-state clock')

    def q(value):
        x = min(1, max(0, value))
        return x * x * x * (x * (6 * x - 15) + 10)

    amount = 0
    for window in windows:
        enter, settled, release, end = [window[key] for key in ('enter', 'settled', 'release', 'end')]
        if (not all(_number(v) for v in (enter, settled, release, end))
                or not enter < settled <= release < end):
            raise ValueError('Recipe foreground visual-state window is invalid')
        amount = max(amount, q((time - enter) / (settled - enter)) * (1 - q((time - release) / (end - release))))
    return amount * 100


def _foreground(plan, spec, glyph):
    foreground = glyph.get('foreground')
    locked, held = spec['phases'][2]['end'], spec['end'] - .46
    paper = plan['visual_states']['definition']['reading'].get('paper_rgb', [242 / 255, 240 / 255, 234 / 255])
    if (not isinstance(foreground, dict) or foreground.get('name') != 'THINKING_FOREGROUND_INK'
            or foreground.get('enabled') is not True or foreground.get('stack_index') != 1
            or foreground.get('units') != 2 or not _close(foreground.get('smoothness'), 0)
            or foreground.get('ranges') != [[0, len(glyph['text'])], [0, len(glyph['text'])]]
            or not _vector(foreground.get('times'), [locked, held], 1e-6)
            or not isinstance(foreground.get('amounts'), list) or len(foreground['amounts']) != 2
            or not isinstance(foreground.get('colors'), list) or len(foreground['colors']) != 2
            or foreground.get('errors') != ['', '']
            or any(not _amount(value, _thinking_amount(plan, time))
                   for value, time in zip(foreground['amounts'], (locked, held)))
            or any(not _color(value, paper) for value in foreground['colors'])):
        raise ValueError('Recipe foreground fill is absent, disabled, stale or ineffective in the held state')


def _vertices(actual, expected):
    return (isinstance(actual, list) and isinstance(expected, list)
            and len(actual) == len(expected) == 3
            and all(_finite_vector(a, 2) and _finite_vector(b, 2) and _vector(a, b)
                    for a, b in zip(actual, expected)))


def _outside_masks(glyph, lo, hi, locked, held):
    """Amount alone does not prove that the original outside glyphs are hidden."""
    states = glyph.get('outside_mask_states')
    names = ('SYMBOL_OUTSIDE_BEFORE', 'SYMBOL_OUTSIDE_AFTER')
    ranges = ((0, lo), (hi, len(glyph['text'])))
    if not isinstance(states, list) or len(states) != 2:
        raise ValueError('Recipe outside glyph masks need their actual native selector/effect states')
    for state, name, (start, end) in zip(states, names, ranges):
        if end <= start:
            if state != {'name': name, 'present': False}:
                raise ValueError('Recipe gained an unbound outside glyph mask')
            continue
        if (not isinstance(state, dict) or state.get('name') != name or state.get('present') is not True
                or state.get('enabled') is not True or state.get('selector_count') != 1
                or state.get('property_names') != ['ADBE Text Opacity']
                or state.get('units') != 2 or not _close(state.get('smoothness'), 0)
                or state.get('ranges') != [[start, end], [start, end]]
                or not _vector(state.get('times'), [locked, held], 1e-6)
                or not isinstance(state.get('amounts'), list) or len(state['amounts']) != 2
                or any(not _amount(value, 100) for value in state['amounts'])
                or not _vector(state.get('opacity'), [0, 0], .01)
                or state.get('errors') != ['', '']):
            raise ValueError('Recipe outside glyph mask is disabled, misranged or ineffective')


def validate_symbol_readback(p, n, rows):
    planned, build, comps = _scope(p, n)
    expected_rows = {(comp, symbol) for comp in comps for symbol in planned}
    if (not isinstance(rows, list) or len(rows) != len(expected_rows)
            or {(row['comp_id'], row['symbol_id']) for row in rows} != expected_rows):
        raise ValueError('Recipe readback requires every instance in both real compositions')
    layer_owners, carried_ids, source_snapshots = {}, set(), {}

    def own(layer_id, comp_id, name, unique=False):
        if not _identity(layer_id) or not isinstance(name, str) or not name:
            raise ValueError('Recipe lost an actual native layer identity')
        owner = layer_owners.get(layer_id)
        if owner is not None and owner != (comp_id, name):
            raise ValueError('Recipe reused a native layer ID across compositions or unrelated objects')
        if unique and layer_id in carried_ids:
            raise ValueError('Recipe reused a carried glyph or relationship layer')
        layer_owners[layer_id] = (comp_id, name)
        if unique:
            carried_ids.add(layer_id)

    for row in rows:
        s, spec, comp = planned[row['symbol_id']], build[row['symbol_id']], row['comp_id']
        if (row['variant'] != s['variant'] or row['recipe_id'] != s['recipe_id']
                or not _vector(row['range'], [s['start'], s['end']], 1e-6)):
            raise ValueError('Recipe native range or identity changed')
        if s['variant'] == 'hook':
            if (row['objects'] != spec['objects'] or row['source_refs'] != s['inputs']
                    or row['spoiler_boundary'] != 'NO_ACTION_LABELS_NO_VERDICT'):
                raise ValueError('Hook Recipe must reuse its anonymous real-source objects without a verdict')
            actual = row.get('object_ids', [])
            if len(actual) != len(spec['objects']) or [item['name'] for item in actual] != spec['objects']:
                raise ValueError('Hook Recipe omitted actual native object identities')
            for item in actual:
                own(item['id'], comp, item['name'], unique=True)
            continue  # The separate Hook readback inspects actual anonymous objects and spoiler phases.
        inputs = _unique(s['inputs'], 'object_id', 'Recipe input')
        expected = _unique(spec['glyphs'], 'object_id', 'Recipe build glyph')
        actual_glyphs = _unique(row['glyphs'], 'object_id', 'Recipe actual glyph')
        if set(expected) != set(inputs) or set(actual_glyphs) != set(inputs) or len(row['paths']) != 2:
            raise ValueError('Recipe omitted source glyphs or its semantic relation structure')
        for g in row['glyphs']:
            item, declared = inputs[g['object_id']], expected[g['object_id']]
            comment, lo, hi = g['comment'], item['source_character_start'], item['source_character_end']
            if (g['source_text'] != g['text'] or g['text'][lo:hi] != item['source_ref']['quote']
                    or comment['source_ref'] != item['source_ref'] or comment['source_layer_name'] != g['source_name']
                    or comment['range'] != [lo, hi] or comment['new_text_created'] is not False
                    or g['threeD'] is not True or g['enabled'] is not True or g['guide'] is not False
                    or g['parent'] is not None or not _close(g['in'], s['start'], 1e-6)
                    or not _close(g['out'], s['end'], 1e-6) or g['id'] == g['source_id']
                    or g['source_name'] != declared['source_name'] or g.get('name') != declared['name']):
                raise ValueError('Recipe no longer carries the original native glyph range')
            own(g['id'], comp, g['name'], unique=True)
            own(g['source_id'], comp, g['source_name'])
            source_key = (comp, g['source_id'])
            snapshot = (g['source_name'], g['source_text'], g.get('source_font'), g.get('source_font_size'))
            if source_key in source_snapshots and source_snapshots[source_key] != snapshot:
                raise ValueError('One native source layer returned inconsistent original glyph identities')
            source_snapshots[source_key] = snapshot
            if comp == comps[0] and (g['id'] != declared['id'] or g['source_id'] != declared['source_id']):
                raise ValueError('Recipe build layer IDs changed')
            font_size, source_size = g['font_size'], g.get('source_font_size')
            if (not _number(font_size) or not _number(source_size) or font_size <= 0
                    or not _close(font_size, source_size) or g.get('font') != g.get('source_font')
                    or g.get('font') != s['parameters']['font']['family']
                    or g.get('apply_fill') is not True or not _finite_vector(g['locked_scale'], 3)
                    or any(not _close(scale, g['locked_scale'][0]) for scale in g['locked_scale'])
                    or g['locked_scale'][0] <= 0
                    or not _close(font_size * g['locked_scale'][0] / 100, s['parameters']['font']['size'], .001)):
                raise ValueError('Recipe changed native font identity, glyph dimensions or uniform scale')
            if (any(not _finite_vector(g[key], 3) for key in ('start', 'source_world_start', 'return', 'source_world_end', 'locked'))
                    or not _vector(g['start'], g['source_world_start'])
                    or not _vector(g['return'], g['source_world_end'])
                    or not _vector(g['locked'], declared['destination'])
                    or not isinstance(g['source_handoff'], list) or len(g['source_handoff']) != 3
                    or any(not _amount(value, target) for value, target in zip(g['source_handoff'], (0, 100, 0)))
                    or not _close(g['opacity'], 100)
                    or not isinstance(g['outside_masks'], list) or len(g['outside_masks']) != 2
                    or any(not _amount(value, 100) for value in g['outside_masks'])):
                raise ValueError('Recipe glyph handoff, mask or precise landing failed')
            samples = g.get('travel_samples')
            if (not isinstance(samples, list) or len(samples) != TRAVEL_SAMPLES
                    or any(not _finite_vector(value, 3) for value in samples)
                    or not _vector(samples[0], g['start']) or not _vector(samples[-1], g['locked'])):
                raise ValueError('Recipe requires all 17 finite three-dimensional movement samples')
            for value in samples:
                if any(v < min(a, b) - .002 or v > max(a, b) + .002
                       for v, a, b in zip(value, g['start'], g['locked'])):
                    raise ValueError('Recipe original object overshoots its semantic destination')
            width = declared['width']
            slot = (s['parameters']['layout']['width'] - s['parameters']['layout']['min_gap']) / 2 - 2 * s['parameters']['layout']['min_gap']
            if not _number(width) or not 0 < width <= slot:
                raise ValueError('Actual native Recipe font is not readable in its slot')
            _foreground(p, s, g)
            _outside_masks(g, lo, hi, s['phases'][2]['end'], s['end'] - .46)
        expected_paths = _unique(spec['paths'], 'name', 'Recipe build path')
        actual_paths = _unique(row['paths'], 'name', 'Recipe actual path')
        if set(expected_paths) != set(actual_paths) or len(expected_paths) != 2:
            raise ValueError('Recipe relationship layer identity changed')
        a, b = row['paths']
        for pi, path in enumerate((a, b)):
            declared_path = expected_paths[path['name']]
            own(path.get('id'), comp, path['name'], unique=True)
            color = SOFT_BRICK if s['recipe_id'] == 'same_form_different_relation' and pi == 1 else FOG_BLUE
            if (path['threeD'] is not True or path['enabled'] is not True or path['guide'] is not False
                    or not _close(path.get('in_point'), s['start'], 1e-6)
                    or not _close(path.get('out_point'), s['end'], 1e-6)
                    or not _vector(path.get('visibility_times'), [s['phases'][2]['end'], s['end'] - .46], 1e-6)
                    or not _vector(path.get('opacity'), [100, 100], .01)
                    or not _vector(path.get('stroke_opacity'), [100, 100], .01)
                    or path.get('opacity_errors') != ['', '']
                    or not _close(path['stroke_width'], 1.5, 1e-6)
                    or not _color(path.get('stroke_color'), color) or not _color(path.get('held_stroke_color'), color)
                    or path['comment']['relation'] != s['relation'] or path['comment']['authority'] != s['authority']
                    or path['comment']['source_refs'] != [i['source_ref'] for i in s['inputs']]
                    or not _vertices(path['start'], declared_path['from'])
                    or not _vertices(path['locked'], declared_path['to'])
                    or not _vertices(path['locked'], path['held'])):
                raise ValueError('Recipe structure is decorative, unbound, invisible, recolored or unsettled')
            if comp == comps[0] and path['id'] != declared_path['id']:
                raise ValueError('Recipe native path build identity changed')
        if s['recipe_id'] == 'semantic_isomorphism' and (a['locked'] != b['locked'] or a['start'] == b['start']):
            raise ValueError('Different source relations did not align into the same verified structure')
        if s['recipe_id'] == 'same_form_different_relation' and (a['start'] != b['start'] or a['locked'] == b['locked']):
            raise ValueError('Shared noun structure did not expose the actual different actions')
    return {'status': 'PASS_SCOPED_NATIVE_RECIPE_PARAMETERS', 'rows': rows,
            'normal_speed_review': 'UNOBSERVED', 'listening_review': 'UNOBSERVED',
            'artistic_review': 'PENDING', 'public_render_ready': False}


def symbol_native_readback(h, p, n):
    planned, built, comps = _scope(p, n)
    packet = [{'plan': spec, 'build': built[symbol_id]} for symbol_id, spec in planned.items()]
    code = r"""var ids=__IDS__,packet=__PACKET__,rows=[];
function tx(l,n){return l.property('ADBE Transform Group').property(n);}
function namedAnimator(l,name){var group=l.property('ADBE Text Properties').property('ADBE Text Animators');for(var i=1;i<=group.numProperties;i++){var an=group.property(i);if(an.name===name)return an;}return null;}
function amount(l,name){var an=namedAnimator(l,name);if(!an)throw Error('Required original glyph animator missing: '+name);return an.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount');}
function mask(l,name,empty,t){var a=namedAnimator(l,name);if(!a){if(empty)return 100;throw Error('Required original glyph mask missing');}return amount(l,name).valueAtTime(t,false);}
function maskState(l,name,locked,held){
 var an=namedAnimator(l,name);if(!an)return {name:name,present:false};
 var selectors=an.property('ADBE Text Selectors'),sel=selectors.property(1),adv=sel.property('ADBE Text Range Advanced'),amt=amount(l,name),props=an.property('ADBE Text Animator Properties'),opacity=props.property('ADBE Text Opacity'),names=[];
 for(var i=1;i<=props.numProperties;i++)if(props.property(i).isModified)names.push(props.property(i).matchName);
 if(!opacity)throw Error('Outside glyph mask has no actual opacity effect');
 return {name:an.name,present:true,enabled:an.enabled,selector_count:selectors.numProperties,property_names:names,units:adv.property('ADBE Text Range Units').value,smoothness:adv.property('ADBE Text Selector Smoothness').value,
  ranges:[[sel.property('ADBE Text Index Start').valueAtTime(locked,false),sel.property('ADBE Text Index End').valueAtTime(locked,false)],[sel.property('ADBE Text Index Start').valueAtTime(held,false),sel.property('ADBE Text Index End').valueAtTime(held,false)]],times:[locked,held],
  amounts:[amt.valueAtTime(locked,false),amt.valueAtTime(held,false)],opacity:[opacity.valueAtTime(locked,false),opacity.valueAtTime(held,false)],errors:[amt.expressionError,opacity.expressionError]};
}
function world(source,t,ap){var p=tx(source,'ADBE Position').valueAtTime(t,false),a=tx(source,'ADBE Anchor Point').valueAtTime(t,false),sc=tx(source,'ADBE Scale').valueAtTime(t,false),v=[p[0]+(ap[0]-a[0])*sc[0]/100,p[1]+(ap[1]-a[1])*sc[1]/100,p[2]];if(source.parent){var par=source.parent,pp=tx(par,'ADBE Position').valueAtTime(t,false),ps=tx(par,'ADBE Scale').valueAtTime(t,false);v=[pp[0]+v[0]*ps[0]/100,pp[1]+v[1]*ps[1]/100,pp[2]+v[2]*ps[2]/100];}return v;}
for(var ci=0;ci<ids.length;ci++){
 var c=app.project.itemByID(ids[ci]);
 for(var si=0;si<packet.length;si++){
  var S=packet[si].plan,B=packet[si].build,row={comp_id:c.id,symbol_id:S.symbol_id,variant:S.variant,recipe_id:S.recipe_id,range:[S.start,S.end]};
  if(S.variant==='hook'){
   row.objects=B.objects;row.source_refs=B.source_refs;row.spoiler_boundary=B.spoiler_boundary;row.object_ids=[];
   for(var oi=0;oi<B.objects.length;oi++){var ob=c.layer(B.objects[oi]);row.object_ids.push({name:ob.name,id:ob.id});}
   rows.push(row);continue;
  }
  row.glyphs=[];row.paths=[];
  for(var gi=0;gi<B.glyphs.length;gi++){
   var G=B.glyphs[gi],l=c.layer(G.name),source=c.layer(G.source_name),comment=JSON.parse(l.comment),ap=tx(l,'ADBE Anchor Point').value,locked=S.phases[2].end,held=S.end-.46,samples=[];
   for(var k=0;k<17;k++)samples.push(tx(l,'ADBE Position').valueAtTime(S.start+(S.phases[1].end-S.start)*k/16,false));
   var hidden=amount(source,'SYMBOL_SOURCE_HANDOFF_'+S.symbol_id+'_'+G.object_id);
   var doc=l.property('Source Text').valueAtTime(locked,false),original=source.property('Source Text').valueAtTime(S.start,false);
   var foreground=namedAnimator(l,'THINKING_FOREGROUND_INK');
   if(!foreground)throw Error('Recipe foreground animator is missing');
   var fgAmount=amount(l,'THINKING_FOREGROUND_INK'),fgColor=foreground.property('ADBE Text Animator Properties').property('ADBE Text Fill Color'),fgSelector=foreground.property('ADBE Text Selectors').property(1),fgAdvanced=fgSelector.property('ADBE Text Range Advanced');
   row.glyphs.push({object_id:G.object_id,name:l.name,id:l.id,source_id:source.id,source_name:source.name,
    text:doc.text,source_text:original.text,comment:comment,threeD:l.threeDLayer,enabled:l.enabled,guide:l.guideLayer,parent:l.parent?l.parent.id:null,
    'in':l.inPoint,'out':l.outPoint,start:tx(l,'ADBE Position').valueAtTime(S.start,false),locked:tx(l,'ADBE Position').valueAtTime(locked,false),
    'return':tx(l,'ADBE Position').valueAtTime(S.end-1/240,false),source_world_start:world(source,S.start,ap),source_world_end:world(source,S.end,ap),
    locked_scale:tx(l,'ADBE Scale').valueAtTime(locked,false),font:doc.font,source_font:original.font,font_size:doc.fontSize,source_font_size:original.fontSize,apply_fill:doc.applyFill,
    opacity:tx(l,'ADBE Opacity').valueAtTime(locked,false),outside_masks:[mask(l,'SYMBOL_OUTSIDE_BEFORE',comment.range[0]===0,locked),mask(l,'SYMBOL_OUTSIDE_AFTER',comment.range[1]===doc.text.length,locked)],
     outside_mask_states:[maskState(l,'SYMBOL_OUTSIDE_BEFORE',locked,held),maskState(l,'SYMBOL_OUTSIDE_AFTER',locked,held)],
    source_handoff:[hidden.valueAtTime(Math.max(0,S.start-1/24),false),hidden.valueAtTime(S.start,false),hidden.valueAtTime(S.end,false)],travel_samples:samples,
    foreground:{name:foreground.name,enabled:foreground.enabled,stack_index:foreground.propertyIndex,times:[locked,held],units:fgAdvanced.property('ADBE Text Range Units').value,smoothness:fgAdvanced.property('ADBE Text Selector Smoothness').value,
     ranges:[[fgSelector.property('ADBE Text Index Start').valueAtTime(locked,false),fgSelector.property('ADBE Text Index End').valueAtTime(locked,false)],[fgSelector.property('ADBE Text Index Start').valueAtTime(held,false),fgSelector.property('ADBE Text Index End').valueAtTime(held,false)]],
     amounts:[fgAmount.valueAtTime(locked,false),fgAmount.valueAtTime(held,false)],colors:[fgColor.valueAtTime(locked,false),fgColor.valueAtTime(held,false)],errors:[fgAmount.expressionError,fgColor.expressionError]}});
  }
  for(var pi=0;pi<B.paths.length;pi++){
    var l=c.layer(B.paths[pi].name),root=l.property('ADBE Root Vectors Group'),path=root.property('ADBE Vector Shape - Group').property('ADBE Vector Shape'),stroke=root.property('ADBE Vector Graphic - Stroke'),color=stroke.property('ADBE Vector Stroke Color'),op=tx(l,'ADBE Opacity'),strokeOpacity=stroke.property('ADBE Vector Stroke Opacity'),locked=S.phases[2].end,held=S.end-.46;
   row.paths.push({name:l.name,id:l.id,threeD:l.threeDLayer,enabled:l.enabled,guide:l.guideLayer,comment:JSON.parse(l.comment),
     in_point:l.inPoint,out_point:l.outPoint,visibility_times:[locked,held],opacity:[op.valueAtTime(locked,false),op.valueAtTime(held,false)],stroke_opacity:[strokeOpacity.valueAtTime(locked,false),strokeOpacity.valueAtTime(held,false)],opacity_errors:[op.expressionError,strokeOpacity.expressionError],
    stroke_width:stroke.property('ADBE Vector Stroke Width').value,stroke_color:color.valueAtTime(S.phases[2].end,false),held_stroke_color:color.valueAtTime(S.end-.46,false),
    start:path.valueAtTime(S.start,false).vertices,locked:path.valueAtTime(S.phases[2].end,false).vertices,held:path.valueAtTime(S.end-.46,false).vertices});
  }
  rows.push(row);
 }
}
return rows;"""
    rows = h.js(code.replace('__IDS__', json.dumps(comps)).replace('__PACKET__', json.dumps(packet, ensure_ascii=False)))
    raw = {'status': 'RAW_NATIVE_READBACK_NOT_VALIDATED', 'revision': p.get('revision'),
           'plan_sha256': n.get('plan_sha256'), 'native_project': n.get('project_path'),
           'comp_ids': list(comps), 'rows': rows, 'public_render_ready': False}
    (Path(h.folder) / 'SYMBOL_NATIVE_READBACK_RAW.json').write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return validate_symbol_readback(p, n, rows)
