"""Explicit editorial ratings: no guessed teaching facts or popularity."""
from copy import deepcopy
from video_contracts import validate
from .candidates import engineering_gate

DIMENSIONS = ('PA', 'HP', 'DP', 'SV', 'TR', 'RC', 'TS')
FEASIBILITY = ('PF1', 'PF2', 'PF3', 'PF4', 'PF5', 'PF6')
RANKING_POLICY = {'version': '0.1.0', 'status': 'provisional', 'p0_content': 8, 'p0_feasibility': 7, 'p1_content': 6}


def score(ratings, dimensions=DIMENSIONS):
    if set(ratings) != set(dimensions):
        raise ValueError('Every dimension must be explicit, including unknown')
    for name, item in ratings.items():
        value = item.get('value')
        if value is None:
            if item.get('status') != 'unknown' or not item.get('rationale'):
                raise ValueError('Unknown needs explicit status/rationale')
        elif (type(value) not in (int, float) or not 0 <= value <= 10 or item.get('status') != 'known'
              or not item.get('rationale', '').strip() or not item.get('evidence')):
            raise ValueError('Known score needs 0–10 value, rationale and evidence')
    known = [v['value'] for v in ratings.values() if v['value'] is not None]
    return {'rubric_version': 'gaokao_education_v1' if dimensions == DIMENSIONS else 'production_feasibility_v1',
            'dimensions': deepcopy(ratings), 'raw_score': round(sum(known) / len(known), 4) if known else None,
            'known_dimension_count': len(known), 'score_coverage': len(known) / len(dimensions)}


def rate(candidate, content, feasibility):
    if not candidate['engineering_pilot_eligible']:
        raise ValueError('Teaching Engineering Gate must PASS before scoring')
    return {**deepcopy(candidate), 'content_score': score(content), 'production_feasibility': score(feasibility, FEASIBILITY)}


def rank(candidates):
    rows = []
    for c in candidates:
        validate('content-candidate', c)
        for field, dimensions in (('content_score', DIMENSIONS), ('production_feasibility', FEASIBILITY)):
            if field in c and score(c[field]['dimensions'], dimensions) != c[field]:
                raise ValueError('Stored score does not match its evidence-backed dimensions')
        by_id = {b['asset_id']: b for b in c['source_items']}
        engineering_valid = all(all(k == 'current_upstream_valid' or v['status'] == 'PASS' for k, v in
            engineering_gate(by_id[s['asset_id']], s, c['content_scope'], None)['checks'].items()) for s in c['selections'])
        cv = c.get('content_score', {}).get('raw_score')
        pf = c.get('production_feasibility', {}).get('raw_score')
        dims = c.get('content_score', {}).get('dimensions', {})
        complete = all(dims.get(k, {}).get('value') is not None for k in DIMENSIONS[:-1]) and c.get('production_feasibility', {}).get('known_dimension_count') == 6
        if c['teaching_engineering_gate']['status'] == 'BLOCKED' or c.get('invalidation', {}).get('teaching_stale'):
            priority, reason = 'BLOCKED', 'Upstream invalid or teaching dependencies stale'
        elif not c['engineering_pilot_eligible'] or not engineering_valid or c['source_use']['internal_use'] != 'PASS' or cv is None or pf is None or not complete:
            priority, reason = 'HOLD', 'Engineering gate or required editorial ratings incomplete'
        elif cv >= 8 and pf >= 7:
            priority, reason = 'P0', 'Provisional thresholds: content >= 8 and feasibility >= 7'
        elif cv >= 6:
            priority, reason = 'P1', 'Content >= 6; P0 requirements not met'
        else:
            priority, reason = 'P2', 'Eligible reserve content under provisional thresholds'
        rows.append({'content_id': c['content_id'], 'engineering_priority': priority, 'public_priority': 'HOLD',
                     'reason': reason, 'content_value': cv, 'feasibility': pf, 'risk_flags': c['risk_flags'],
                     'methods': sorted({s['method_id'] for s in c['selections']}),
                     'question_types': sorted({b['source_snapshot']['question_type'] for b in c['source_items']}),
                     'pattern': c.get('pattern_id', 'unselected'), 'duration': c.get('duration_target', 'unknown')})
    rows.sort(key=lambda r: (('P0', 'P1', 'P2', 'HOLD', 'BLOCKED').index(r['engineering_priority']),
                             -(r['content_value'] or 0), -(r['feasibility'] or 0), r['content_id']))
    seen = {k: {} for k in ('methods', 'question_types', 'pattern', 'duration')}
    for i, row in enumerate(rows, 1):
        row.update(raw_rank=i, portfolio_rank=i)
        row['repetition'] = {}
        for k in seen:
            values = row[k] if isinstance(row[k], list) else [str(row[k])]
            row['repetition'][k] = sum(seen[k].get(v, 0) for v in values)
            for v in values:
                seen[k][v] = seen[k].get(v, 0) + 1
    return {'ranking_policy': deepcopy(RANKING_POLICY), 'rows': rows, 'distributions': seen,
            'note': 'Public queue requires package-level release checks; portfolio order preserves raw rank in v0.1'}
