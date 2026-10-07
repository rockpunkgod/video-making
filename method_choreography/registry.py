"""Read existing motion identity and a separate cognitive-operation vocabulary."""
from video_contracts import ROOT, read, sha

DIRECTORY = ROOT / 'creative/method-choreography'
VERSION = '0.1.0'


def registry():
    physics = read(DIRECTORY / 'physics.json')
    recipes = read(DIRECTORY / 'method-choreographies.json')
    identity = read(ROOT / 'creative/motion-identity/method-signatures.json')
    grammar = read(ROOT / 'creative/motion-identity/brand-motion-grammar.json')
    if any(r['version'] != VERSION or r['authority'] != 'cognitive_choreography_only_not_teaching_truth'
           for r in (physics, recipes)):
        raise ValueError('Choreography registry has no teaching authority')
    if identity['version'] != VERSION or grammar['version'] != VERSION:
        raise ValueError('Explicit Motion Identity compatibility required')
    signatures = {s['method_id']: s['signature_id'] for s in identity['signatures']}
    rows = recipes['recipes']
    if len(rows) != len({r['method_id'] for r in rows}) or set(signatures) != {r['method_id'] for r in rows}:
        raise ValueError('Existing six motion identities must remain distinct')
    if not set(recipes['brand_grammar_refs']) <= {r['id'] for r in grammar['grammar']}:
        raise ValueError('Unknown shared Brand Grammar')
    patterns = []
    for row in rows:
        if row['signature_id'] != signatures[row['method_id']]:
            raise ValueError('Method label/signature mismatch')
        if not row['core_pattern'] or any(v not in physics['families'].get(f, []) for f,v in row['core_pattern']):
            raise ValueError('Signature needs valid cognitive operations')
        patterns.append(sha(row['core_pattern']))
    if len(set(patterns)) != len(patterns):
        raise ValueError('SIGNATURE_DISTINCTIVENESS_FAIL: interchangeable physics patterns')
    return physics, recipes, {'physics_sha': sha(physics), 'recipes_sha': sha(recipes),
        'motion_identity_sha': sha(identity), 'brand_grammar_sha': sha(grammar)}


def signature_matches(method_id, operations):
    _, recipes, _ = registry()
    row = next((r for r in recipes['recipes'] if r['method_id'] == method_id), None)
    if row is None: return False
    actual = [(o['family'],o['verb']) for o in operations]
    cursor = iter(actual)
    return all(any(item == tuple(required) for item in cursor) for required in row['core_pattern'])
