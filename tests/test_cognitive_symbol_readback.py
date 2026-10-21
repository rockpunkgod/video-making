"""Synthetic native-readback guards, separate from AE execution and taste."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from ae_production.cognitive_symbol_review import (
    FOG_BLUE, SOFT_BRICK, _thinking_amount, symbol_native_readback, validate_symbol_readback,
)


def fixture():
    """Two relation recipes and an anonymous Hook, in two real-comp identities."""
    plan = {'symbol_recipes': {'rows': []}, 'visual_states': {
        'definition': {'reading': {'paper_rgb': [.955, .946, .92]}},
        'thinking_windows': [{'enter': 0, 'settled': .5, 'release': 100, 'end': 101}]}}
    native = {'comp_id': 101, 'master_comp_id': 202, 'audit': {'symbol_recipes': []}}
    rows = []
    for index, (recipe, words) in enumerate((
            ('semantic_isomorphism', ('cheaper than those options', 'more affordable than its competitors')),
            ('same_form_different_relation', ('take part in feedback workshops', 'Chair feedback workshops')))):
        symbol_id = 'SYNTHETIC-' + recipe
        start, end = 10.0 * index + 1, 10.0 * index + 6
        inputs = []
        glyphs = []
        measured = []
        for gi, quote in enumerate(words):
            object_id = f'SYNTHETIC-{index}-{gi}'
            source_ref = {'world': 'SYNTHETIC', 'pointer': '/passage' if gi == 0 else '/options/A',
                          'start': 0, 'end': len(quote), 'quote': quote}
            inputs.append({'object_id': object_id, 'source_ref': source_ref,
                           'source_character_start': 0, 'source_character_end': len(quote)})
            source_name = 'SYNTHETIC SOURCE ' + object_id
            glyph_name = 'SYNTHETIC GLYPH ' + object_id
            source = [10 + gi * 30, 30, 0]
            destination = [200 + gi * 300, 150, 10]
            glyphs.append({'object_id': object_id, 'id': 11 + 100 * index + gi,
                           'source_id': 21 + 100 * index + gi, 'source_name': source_name,
                           'name': glyph_name, 'destination': destination, 'width': 180})
            measured.append({'object_id': object_id, 'name': glyph_name, 'id': 11 + 100 * index + gi,
                'source_id': 21 + 100 * index + gi, 'source_name': source_name,
                'text': quote, 'source_text': quote,
                'comment': {'source_ref': deepcopy(source_ref), 'source_layer_name': source_name,
                            'range': [0, len(quote)], 'new_text_created': False},
                'threeD': True, 'enabled': True, 'guide': False, 'parent': None,
                'in': start, 'out': end, 'start': source, 'source_world_start': list(source),
                'return': list(source), 'source_world_end': list(source), 'locked': destination,
                'locked_scale': [100, 100, 100], 'font_size': 64, 'font': 'ArialMT',
                'source_font': 'ArialMT', 'source_font_size': 64, 'apply_fill': True,
                'source_handoff': [0, 100, 0],
                'opacity': 100, 'outside_masks': [100, 100],
                'outside_mask_states': [
                    {'name': 'SYMBOL_OUTSIDE_BEFORE', 'present': False},
                    {'name': 'SYMBOL_OUTSIDE_AFTER', 'present': False}],
                'travel_samples': [[a + (b-a) * k/16 for a, b in zip(source, destination)] for k in range(17)],
                'foreground': {'name': 'THINKING_FOREGROUND_INK', 'enabled': True, 'stack_index': 1,
                    'units': 2, 'smoothness': 0, 'ranges': [[0, len(quote)], [0, len(quote)]],
                    'times': [start + 1, end - .46], 'amounts': [100, 100],
                    'colors': [[.955, .946, .92], [.955, .946, .92]], 'errors': ['', '']}})
        relation = {'kind': recipe, 'verified': 'SYNTHETIC UPSTREAM CONTROL'}
        authority = {'scope': 'SYNTHETIC FROZEN EVIDENCE'}
        spec = {'symbol_id': symbol_id, 'variant': 'payoff', 'recipe_id': recipe,
            'start': start, 'end': end, 'inputs': inputs,
            'parameters': {'font': {'size': 64, 'family': 'ArialMT'}, 'layout': {'width': 800, 'min_gap': 20}},
            'phases': [{'end': start + .3}, {'end': start + .8}, {'end': start + 1}],
            'relation': relation, 'authority': authority}
        plan['symbol_recipes']['rows'].append(spec)
        native['audit']['symbol_recipes'].append({'symbol_id': symbol_id, 'glyphs': glyphs})
        paths = []
        for pi in range(2):
            path_start = [[0, 0], [40, 0], [100, 20 * pi]] if index == 0 else [[0, 0], [40, 0], [100, 0]]
            locked = [[0, 0], [50, 0], [100, 0]] if index == 0 else [[0, 0], [50, 30 * pi], [100, 30 * pi]]
            color = SOFT_BRICK if index == 1 and pi == 1 else FOG_BLUE
            paths.append({'name': f'SYNTHETIC PATH {index}-{pi}', 'id': 31 + 100 * index + pi, 'threeD': True,
                'enabled': True, 'guide': False, 'stroke_width': 1.5,
                'in_point': start, 'out_point': end, 'visibility_times': [start+1, end-.46],
                'opacity': [100, 100], 'stroke_opacity': [100, 100], 'opacity_errors': ['', ''],
                'stroke_color': list(color), 'held_stroke_color': list(color),
                'comment': {'relation': deepcopy(relation), 'authority': deepcopy(authority),
                            'source_refs': [deepcopy(i['source_ref']) for i in inputs]},
                'start': path_start, 'locked': locked, 'held': deepcopy(locked)})
        native['audit']['symbol_recipes'][-1]['paths'] = [
            {'name': item['name'], 'id': item['id'], 'from': deepcopy(item['start']), 'to': deepcopy(item['locked'])}
            for item in paths]
        for comp in (101, 202):
            actual = deepcopy(measured)
            actual_paths = deepcopy(paths)
            if comp == 202:
                for g in actual:
                    g['id'] += 1000
                    g['source_id'] += 1000
                for path in actual_paths:
                    path['id'] += 1000
            rows.append({'comp_id': comp, 'symbol_id': symbol_id, 'variant': 'payoff',
                         'recipe_id': recipe, 'range': [start, end], 'glyphs': actual, 'paths': actual_paths})
    hook_inputs = [{'object_id': 'SYNTHETIC-HOOK-A', 'quote': 'workshops'},
                   {'object_id': 'SYNTHETIC-HOOK-B', 'quote': 'workshops'}]
    hook_objects = ['SYNTHETIC ANONYMOUS A', 'SYNTHETIC ANONYMOUS B']
    hook = {'symbol_id': 'SYNTHETIC-HOOK', 'variant': 'hook',
            'recipe_id': 'same_form_different_relation', 'start': 0, 'end': 1,
            'inputs': hook_inputs}
    plan['symbol_recipes']['rows'].append(hook)
    native['audit']['symbol_recipes'].append({'symbol_id': hook['symbol_id'], 'objects': hook_objects})
    for comp in (101, 202):
        rows.append({'comp_id': comp, 'symbol_id': hook['symbol_id'], 'variant': 'hook',
            'recipe_id': hook['recipe_id'], 'range': [0, 1], 'objects': deepcopy(hook_objects),
            'object_ids': [{'name': name, 'id': 301 + i + (1000 if comp == 202 else 0)}
                           for i, name in enumerate(hook_objects)],
            'source_refs': deepcopy(hook_inputs), 'spoiler_boundary': 'NO_ACTION_LABELS_NO_VERDICT'})
    return plan, native, rows


class CognitiveSymbolReadbackTest(unittest.TestCase):
    def setUp(self):
        self.plan, self.native, self.rows = fixture()

    def reject(self, mutate):
        rows = deepcopy(self.rows)
        mutate(rows)
        with self.assertRaises(ValueError):
            validate_symbol_readback(self.plan, self.native, rows)

    def test_complete_native_parameter_readback_has_scoped_claims(self):
        result = validate_symbol_readback(self.plan, self.native, self.rows)
        self.assertEqual(result['status'], 'PASS_SCOPED_NATIVE_RECIPE_PARAMETERS')
        self.assertEqual(result['normal_speed_review'], 'UNOBSERVED')
        self.assertEqual(result['listening_review'], 'UNOBSERVED')
        self.assertEqual(result['artistic_review'], 'PENDING')
        self.assertFalse(result['public_render_ready'])

    def capture_native_reader(self, rows=None):
        class FakeReadOnlyHost:
            def __init__(self, folder, result):
                self.folder, self.result, self.code = folder, result, None

            def js(self, code):
                self.code = code
                return deepcopy(self.result)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return FakeReadOnlyHost(Path(folder.name), self.rows if rows is None else rows)

    def test_raw_actual_read_packet_persists_before_parameter_validation(self):
        bad = deepcopy(self.rows)
        bad[0]['glyphs'][0]['travel_samples'] = []
        host = self.capture_native_reader(bad)
        with self.assertRaises(ValueError):
            symbol_native_readback(host, self.plan, self.native)
        raw = json.loads((host.folder / 'SYMBOL_NATIVE_READBACK_RAW.json').read_text(encoding='utf-8'))
        self.assertEqual(raw['status'], 'RAW_NATIVE_READBACK_NOT_VALIDATED')
        self.assertEqual(raw['rows'], bad)
        self.assertEqual(raw['comp_ids'], [101, 202])
        self.assertFalse(raw['public_render_ready'])

    @unittest.skipUnless(shutil.which('node'), 'Node with the ES3 Acorn parser is required')
    def test_native_payload_parses_as_es3_and_rejects_reserved_keys_and_modern_syntax(self):
        host = self.capture_native_reader()
        symbol_native_readback(host, self.plan, self.native)
        self.assertIn("'in':l.inPoint", host.code)
        self.assertIn("'return':tx", host.code)
        sources = [host.code, host.code.replace("'in':l.inPoint", 'in:l.inPoint', 1),
                   host.code.replace("'return':tx", 'return:tx', 1),
                   host.code + '\nconst invalidForExtendScript = 1;']
        # The modern Node parser itself accepts reserved object keys. Use the
        # bundled Acorn's actual ES3 grammar and forbid unquoted reserved words.
        runner = r"""let input='';process.stdin.setEncoding('utf8');
process.stdin.on('data', x => input+=x);
process.stdin.on('end',()=>{
 let parser;try{parser=require('acorn')}catch(e){parser=require('internal/deps/acorn/acorn/dist/acorn')}
 const results=JSON.parse(input).map(source=>{
  try{parser.parse('function nativeReadback(){\n'+source+'\n}',{ecmaVersion:3,allowReserved:'never'});return true}
  catch(e){return false}
 });process.stdout.write(JSON.stringify(results));
});"""
        actual = subprocess.run(['node', '--expose-internals', '-e', runner],
            input=json.dumps(sources), capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertEqual(json.loads(actual.stdout), [True, False, False, False])

    @unittest.skipUnless(shutil.which('node'), 'Node is required for the pure property-lookup model')
    def test_long_animator_names_use_exact_numeric_lookup_without_native_name_translation(self):
        host = self.capture_native_reader()
        symbol_native_readback(host, self.plan, self.native)
        helper = host.code[host.code.index('function namedAnimator('):host.code.index('function amount(')]
        target = 'SYMBOL_SOURCE_HANDOFF_recall-workshop-role-displacement_candidate_action'
        runner = r"""let input='';process.stdin.setEncoding('utf8');
process.stdin.on('data', x=>input+=x);process.stdin.on('end',()=>{
 const spec=JSON.parse(input),find=eval('('+spec.helper+')');
 const items=[{name:spec.target.slice(0,39)},{name:spec.target},{name:spec.target+' trailing'}];
 let numericCalls=0;
 const group={numProperties:items.length,property(index){
  if(typeof index!=='number')throw Error('Native property(name) translation limit must not be called');
  numericCalls++;return items[index-1];
 }};
 const layer={property(name){if(name!=='ADBE Text Properties')throw Error('Unexpected native group');
  return {property(name){if(name!=='ADBE Text Animators')throw Error('Unexpected animator group');return group}};
 }};
 const found=find(layer,spec.target),missing=find(layer,spec.target+' missing');
 process.stdout.write(JSON.stringify({exact:found===items[1],missing:missing===null,numericCalls}));
});"""
        actual = subprocess.run(['node', '-e', runner],
            input=json.dumps({'helper': helper.strip(), 'target': target}),
            capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertEqual(json.loads(actual.stdout), {'exact': True, 'missing': True, 'numericCalls': 5})

    def test_missing_instance_wrong_comp_or_duplicate_row_is_rejected(self):
        for mutate in (lambda r: r.pop(), lambda r: r[0].update(comp_id=999),
                       lambda r: r.__setitem__(0, deepcopy(r[1]))):
            with self.subTest(mutate=mutate):
                self.reject(mutate)

    def test_recipe_variant_range_and_identity_cannot_drift(self):
        for key, value in (('variant', 'unbound'), ('recipe_id', 'wrong-recipe'), ('range', [1, 7])):
            with self.subTest(key=key):
                self.reject(lambda r: r[0].update({key: value}))

    def test_hook_remains_same_source_anonymous_without_verdict(self):
        for key, value in (('objects', []), ('source_refs', []), ('spoiler_boundary', 'ANSWER_A')):
            with self.subTest(key=key):
                self.reject(lambda r: r[-1].update({key: value}))

    def test_no_source_object_or_relation_path_can_be_omitted(self):
        for mutate in (lambda r: r[0]['glyphs'].pop(), lambda r: r[0]['paths'].pop(),
                       lambda r: r[0]['glyphs'].__setitem__(0, deepcopy(r[0]['glyphs'][1]))):
            with self.subTest(mutate=mutate):
                self.reject(mutate)

    def test_original_text_quote_identity_and_no_regeneration(self):
        mutations = (lambda g: g.update(text='SYNTHETIC replacement'),
                     lambda g: g.update(source_text='SYNTHETIC changed source'),
                     lambda g: g['comment'].update(range=[1, 2]),
                     lambda g: g['comment'].update(new_text_created=True),
                     lambda g: g['comment']['source_ref'].update(quote='SYNTHETIC forged quote'),
                     lambda g: g['comment'].update(source_layer_name='SYNTHETIC wrong layer'))
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.reject(lambda r: mutate(r[0]['glyphs'][0]))

    def test_recipe_is_a_visible_native_three_dimensional_object(self):
        for key, value in (('threeD', False), ('enabled', False), ('guide', True), ('parent', 99),
                           ('in', 0), ('out', 99), ('opacity', 0)):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['glyphs'][0].update({key: value}))

    def test_proxy_native_build_ids_and_source_name_are_checked(self):
        for key, value in (('id', 0), ('source_id', 0), ('source_name', 'SYNTHETIC wrong original')):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['glyphs'][0].update({key: value}))

    def test_duplicate_cannot_be_the_original_object(self):
        self.reject(lambda r: r[0]['glyphs'][0].update(id=r[0]['glyphs'][0]['source_id']))

    def test_source_and_return_positions_and_exact_landing_are_checked(self):
        for key in ('start', 'return', 'locked'):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['glyphs'][0].update({key: [999, 999, 999]}))

    def test_font_scale_masks_and_handoff_keep_visible_original_glyphs(self):
        for key, value in (('font_size', 32), ('locked_scale', [50, 100, 100]),
                           ('outside_masks', [0, 100]), ('source_handoff', [100, 0, 0])):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['glyphs'][0].update({key: value}))

    def test_nonfinite_and_overshooting_motion_are_rejected(self):
        for sample in ([math.nan, 30, 0], [math.inf, 30, 0], [999, 30, 0], [-99, 30, 0]):
            with self.subTest(sample=sample):
                self.reject(lambda r: r[0]['glyphs'][0]['travel_samples'].__setitem__(8, sample))

    def test_requires_all_seventeen_complete_finite_three_dimensional_samples(self):
        bad = ([], [[]], [[0, 0, 0]] * 16, [[0, 0, 0]] * 18,
               [[0, 0]] * 17, [[0, 0, 0, 0]] * 17,
               [[True, 0, 0]] * 17, [[None, 0, 0]] * 17)
        for samples in bad:
            with self.subTest(samples=samples):
                self.reject(lambda r: r[0]['glyphs'][0].update(travel_samples=samples))
        self.reject(lambda r: r[0]['glyphs'][0]['travel_samples'].__setitem__(0, [11, 30, 0]))
        self.reject(lambda r: r[0]['glyphs'][0]['travel_samples'].__setitem__(-1, [199, 150, 10]))

    def test_planned_and_build_symbol_ids_cannot_be_duplicate_or_missing(self):
        for container in ('planned', 'built'):
            for mode in ('duplicate', 'missing', 'extra'):
                with self.subTest(container=container, mode=mode):
                    plan, native = deepcopy(self.plan), deepcopy(self.native)
                    items = plan['symbol_recipes']['rows'] if container == 'planned' else native['audit']['symbol_recipes']
                    if mode == 'duplicate':
                        items.append(deepcopy(items[0]))
                    elif mode == 'missing':
                        items.pop()
                    else:
                        extra = deepcopy(items[0]); extra['symbol_id'] = 'SYNTHETIC unbound extra'
                        items.append(extra)
                    with self.assertRaises(ValueError):
                        validate_symbol_readback(plan, native, self.rows)

    def test_native_compositions_must_be_distinct_positive_ids(self):
        for value in (101, 0, -1, True, 202.0):
            with self.subTest(value=value):
                native = deepcopy(self.native); native['master_comp_id'] = value
                with self.assertRaises(ValueError):
                    validate_symbol_readback(self.plan, native, self.rows)

    def test_proxy_layer_ids_cannot_masquerade_as_master_layers(self):
        for field in ('id', 'source_id'):
            with self.subTest(field=field):
                self.reject(lambda r: r[1]['glyphs'][0].update({field: r[0]['glyphs'][0][field]}))
        self.reject(lambda r: r[1]['paths'][0].update(id=r[0]['paths'][0]['id']))
        self.reject(lambda r: r[-1]['object_ids'][0].update(id=r[-2]['object_ids'][0]['id']))

    def test_multiple_ranges_can_share_one_native_source_in_the_same_composition(self):
        plan, native, rows = deepcopy(self.plan), deepcopy(self.native), deepcopy(self.rows)
        spec = plan['symbol_recipes']['rows'][0]
        first, second = [item['source_ref']['quote'] for item in spec['inputs']]
        full = first + ' / ' + second
        ranges = [(0, len(first)), (len(first) + 3, len(full))]
        build = native['audit']['symbol_recipes'][0]['glyphs']
        for index, (lo, hi) in enumerate(ranges):
            item = spec['inputs'][index]
            item.update(source_character_start=lo, source_character_end=hi)
            item['source_ref'].update(pointer='/passage', start=lo, end=hi)
            build[index].update(source_id=build[0]['source_id'], source_name=build[0]['source_name'])
        for row in rows[:2]:
            for index, (lo, hi) in enumerate(ranges):
                glyph = row['glyphs'][index]
                glyph.update(text=full, source_text=full,
                    source_id=build[0]['source_id'] + (1000 if row['comp_id'] == 202 else 0),
                    source_name=build[0]['source_name'])
                glyph['comment'].update(range=[lo, hi], source_ref=deepcopy(spec['inputs'][index]['source_ref']),
                                        source_layer_name=build[0]['source_name'])
                glyph['foreground']['ranges'] = [[0, len(full)], [0, len(full)]]
                glyph['outside_mask_states'] = []
                for name, start, end in [('SYMBOL_OUTSIDE_BEFORE', 0, lo),
                                         ('SYMBOL_OUTSIDE_AFTER', hi, len(full))]:
                    state = {'name': name, 'present': end > start}
                    if end > start:
                        state.update(enabled=True, selector_count=1,
                            property_names=['ADBE Text Opacity'], units=2, smoothness=0,
                            ranges=[[start, end], [start, end]],
                            times=[spec['phases'][2]['end'], spec['end']-.46],
                            amounts=[100, 100], opacity=[0, 0], errors=['', ''])
                    glyph['outside_mask_states'].append(state)
            for path in row['paths']:
                path['comment']['source_refs'] = [deepcopy(item['source_ref']) for item in spec['inputs']]
        validate_symbol_readback(plan, native, rows)
        # Repeated references may not claim two different source documents.
        rows[0]['glyphs'][1].update(source_font_size=65)
        with self.assertRaises(ValueError):
            validate_symbol_readback(plan, native, rows)

    def test_build_and_actual_object_inventories_refuse_duplicate_ids(self):
        plan = deepcopy(self.plan)
        plan['symbol_recipes']['rows'][0]['inputs'].append(deepcopy(plan['symbol_recipes']['rows'][0]['inputs'][0]))
        with self.assertRaises(ValueError):
            validate_symbol_readback(plan, self.native, self.rows)
        native = deepcopy(self.native)
        native['audit']['symbol_recipes'][0]['glyphs'].append(deepcopy(native['audit']['symbol_recipes'][0]['glyphs'][0]))
        with self.assertRaises(ValueError):
            validate_symbol_readback(self.plan, native, self.rows)
        self.reject(lambda r: r[1]['glyphs'][1].update(id=r[1]['glyphs'][0]['id']))

    def test_actual_font_identity_and_uniform_scale_are_preserved(self):
        for key, value in (('font', 'DifferentFace'), ('source_font', 'DifferentFace'),
                           ('source_font_size', 128), ('font_size', math.nan), ('apply_fill', False),
                           ('locked_scale', [100, 80, 100]), ('locked_scale', [100, 100, 0]),
                           ('locked_scale', [100, 100]), ('locked_scale', [100, math.nan, 100])):
            with self.subTest(key=key, value=value):
                self.reject(lambda r: r[0]['glyphs'][0].update({key: value}))
        self.reject(lambda r: r[0]['glyphs'][0].update(font='OtherFace', source_font='OtherFace'))

    def test_requested_font_family_cannot_be_ignored_while_preserving_original_glyphs(self):
        plan = deepcopy(self.plan)
        original_rows = deepcopy(self.rows)
        # The actual source and carried glyph still agree with one another.
        # A different authored family must reject, rather than silently retype
        # the original or leave the family parameter unconsumed.
        plan['symbol_recipes']['rows'][0]['parameters']['font']['family'] = 'DifferentFace'
        with self.assertRaisesRegex(ValueError, 'font identity'):
            validate_symbol_readback(plan, self.native, self.rows)
        self.assertEqual(self.rows, original_rows)
        self.assertEqual(self.rows[0]['glyphs'][0]['font'], 'ArialMT')
        self.assertEqual(self.rows[0]['glyphs'][0]['source_font'], 'ArialMT')

    def test_native_amount_arrays_are_supported_without_ignoring_broken_channels(self):
        rows = deepcopy(self.rows)
        for row in rows:
            for g in row.get('glyphs', []):
                g['source_handoff'] = [[0, 0, 0], [100, 100, 100], [0, 0, 0]]
                g['outside_masks'] = [[100], [100, 100, 100]]
                g['foreground']['amounts'] = [[100, 100, 100], [100]]
        self.assertEqual(validate_symbol_readback(self.plan, self.native, rows)['status'],
                         'PASS_SCOPED_NATIVE_RECIPE_PARAMETERS')
        rows[0]['glyphs'][0]['foreground']['amounts'][0] = [100, 0, 100]
        with self.assertRaises(ValueError):
            validate_symbol_readback(self.plan, self.native, rows)

    def test_foreground_fill_is_effective_across_the_entire_source_glyph_object(self):
        for key, value in (('name', 'wrong'), ('enabled', False), ('stack_index', 2), ('units', 1),
                           ('smoothness', 100), ('ranges', [[0, 2], [0, 2]]), ('times', [0, 0]),
                           ('amounts', [0, 100]), ('colors', [[0, 0, 0], [0, 0, 0]]),
                           ('errors', ['expression failed', ''])):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['glyphs'][0]['foreground'].update({key: value}))
        self.reject(lambda r: r[0]['glyphs'][0].update(foreground=None))

    def test_held_foreground_follows_real_return_to_reading_state_instead_of_forcing_100(self):
        plan, rows = deepcopy(self.plan), deepcopy(self.rows)
        # Deliberately place the held point inside the reading return ramp.
        plan['visual_states']['thinking_windows'][0].update(release=5, end=6)
        for row in rows:
            if row['variant'] == 'hook':
                continue
            spec = next(s for s in plan['symbol_recipes']['rows'] if s['symbol_id'] == row['symbol_id'])
            for glyph in row['glyphs']:
                glyph['foreground']['amounts'] = [_thinking_amount(plan, t) for t in (spec['phases'][2]['end'], spec['end'] - .46)]
        self.assertGreater(rows[0]['glyphs'][0]['foreground']['amounts'][1], 0)
        self.assertLess(rows[0]['glyphs'][0]['foreground']['amounts'][1], 100)
        validate_symbol_readback(plan, self.native, rows)
        rows[0]['glyphs'][0]['foreground']['amounts'][1] = 100
        with self.assertRaises(ValueError):
            validate_symbol_readback(plan, self.native, rows)

    def test_relation_strokes_keep_actual_motion_identity_colors(self):
        self.reject(lambda r: r[0]['paths'][0].update(stroke_color=[1, 0, 0]))
        self.reject(lambda r: r[2]['paths'][1].update(stroke_color=list(FOG_BLUE)))
        self.reject(lambda r: r[2]['paths'][1].update(held_stroke_color=[0, 1, 0]))
        rows = deepcopy(self.rows)
        for row in rows:
            for path in row.get('paths', []):
                path['stroke_color'].append(1)
                path['held_stroke_color'].append(1)
        validate_symbol_readback(self.plan, self.native, rows)

    def test_relation_visibility_reads_both_actual_layer_and_stroke_opacity(self):
        for key, value in (
                ('opacity', [0, 0]), ('opacity', [100, 0]),
                ('stroke_opacity', [0, 0]), ('stroke_opacity', [100, float('nan')]),
                ('in_point', 2), ('out_point', 3), ('visibility_times', [2, 4]),
                ('opacity_errors', ['', 'Invalid opacity expression'])):
            with self.subTest(key=key, value=value):
                self.reject(lambda r: r[0]['paths'][0].update({key: value}))

    def partial_mask_fixture(self):
        plan, native, rows = fixture()
        spec = plan['symbol_recipes']['rows'][0]; item = spec['inputs'][0]
        quote = item['source_ref']['quote']; text = 'pre '+quote+' suffix'
        lo, hi = 4, 4+len(quote)
        item.update(source_character_start=lo, source_character_end=hi)
        for row in rows:
            if row['symbol_id'] != spec['symbol_id']: continue
            glyph = row['glyphs'][0]
            glyph.update(text=text, source_text=text)
            glyph['comment']['range'] = [lo, hi]
            glyph['foreground']['ranges'] = [[0, len(text)], [0, len(text)]]
            glyph['outside_mask_states'] = [
                {'name': name, 'present': True, 'enabled': True, 'selector_count': 1,
                 'property_names': ['ADBE Text Opacity'], 'units': 2, 'smoothness': 0,
                 'ranges': [[start, end], [start, end]],
                 'times': [spec['phases'][2]['end'], spec['end']-.46],
                 'amounts': [100, 100], 'opacity': [0, 0], 'errors': ['', '']}
                for name, start, end in [('SYMBOL_OUTSIDE_BEFORE', 0, lo),
                                         ('SYMBOL_OUTSIDE_AFTER', hi, len(text))]]
        return plan, native, rows

    def test_partial_original_glyph_masks_have_actual_ranges_effect_and_held_visibility(self):
        plan, native, rows = self.partial_mask_fixture()
        self.assertEqual(validate_symbol_readback(plan, native, rows)['status'],
                         'PASS_SCOPED_NATIVE_RECIPE_PARAMETERS')
        for row in rows:
            for glyph in row.get('glyphs', []):
                for state in glyph['outside_mask_states']:
                    if state['present']: state['amounts'] = [[100], [100, 100, 100]]
        validate_symbol_readback(plan, native, rows)

    def test_amount_100_cannot_conceal_a_disabled_wrong_range_or_ineffective_glyph_mask(self):
        for key, value in (
                ('enabled', False), ('selector_count', 2), ('units', 1),
                ('ranges', [[0, 3], [0, 4]]), ('ranges', [[0, 4], [0, 3]]),
                ('opacity', [100, 100]), ('opacity', [0, 100]), ('amounts', [100, 0]),
                ('property_names', ['ADBE Text Opacity', 'ADBE Text Position 3D']),
                ('errors', ['Invalid selector', ''])):
            with self.subTest(key=key, value=value):
                plan, native, rows = self.partial_mask_fixture()
                rows[1]['glyphs'][0]['outside_mask_states'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'outside glyph mask'):
                    validate_symbol_readback(plan, native, rows)

    def test_unnecessary_or_missing_mask_state_cannot_inherit_a_pass(self):
        self.reject(lambda r: r[0]['glyphs'][0].pop('outside_mask_states'))
        self.reject(lambda r: r[0]['glyphs'][0]['outside_mask_states'][0].update(present=True))
        plan, native, rows = self.partial_mask_fixture()
        rows[0]['glyphs'][0]['outside_mask_states'][0] = {
            'name': 'SYMBOL_OUTSIDE_BEFORE', 'present': False}
        with self.assertRaisesRegex(ValueError, 'outside glyph mask'):
            validate_symbol_readback(plan, native, rows)

    def test_path_geometry_cannot_be_replaced_with_arbitrary_matching_shapes(self):
        rows = deepcopy(self.rows)
        for path in rows[0]['paths']:
            path['locked'] = [[0, 0], [1, 1], [2, 2]]
            path['held'] = deepcopy(path['locked'])
        with self.assertRaises(ValueError):
            validate_symbol_readback(self.plan, self.native, rows)

    def test_actual_native_font_must_fit_the_slot(self):
        for width in (0, -1, 9999, math.nan, 'not-numeric'):
            with self.subTest(width=width):
                native = deepcopy(self.native)
                native['audit']['symbol_recipes'][0]['glyphs'][0]['width'] = width
                with self.assertRaises(ValueError):
                    validate_symbol_readback(self.plan, native, self.rows)

    def test_relation_paths_are_bound_visible_and_still_after_settle(self):
        for key, value in (('threeD', False), ('enabled', False), ('guide', True),
                           ('stroke_width', 10), ('held', [[999, 999]])):
            with self.subTest(key=key):
                self.reject(lambda r: r[0]['paths'][0].update({key: value}))
        for key, value in (('relation', {}), ('authority', {}), ('source_refs', [])):
            with self.subTest(comment=key):
                self.reject(lambda r: r[0]['paths'][0]['comment'].update({key: value}))

    def test_isomorphism_starts_different_and_ends_at_same_verified_structure(self):
        self.reject(lambda r: r[0]['paths'][0].update(start=deepcopy(r[0]['paths'][1]['start'])))
        self.reject(lambda r: r[0]['paths'][0].update(locked=[[0, 1]], held=[[0, 1]]))

    def test_shared_form_starts_same_and_exposes_different_relations(self):
        self.reject(lambda r: r[2]['paths'][0].update(start=[[999, 999]]))
        self.reject(lambda r: r[2]['paths'][0].update(locked=deepcopy(r[2]['paths'][1]['locked']),
                                                     held=deepcopy(r[2]['paths'][1]['held'])))


if __name__ == '__main__':
    unittest.main()
