"""Explicit frozen assets -> honest golden-method coverage, without scanning."""
from .compiler import compile_plan
from .policy import GOLDEN_METHODS


def golden_matrix(assets, modes=('first_touch', 'worked_example', 'boundary')):
    rows = []
    plans = []
    for mid in GOLDEN_METHODS:
        own = [a for a in assets if a['selection']['method_id'] == mid]
        for mode in modes:
            attempts = []
            for asset in own:
                try:
                    plan = compile_plan(asset['bundle'], asset['status'], asset['selection'], mode=mode,
                        fields=asset.get('fields'), generated_at='golden-matrix-replay')
                    attempts.append(plan)
                except ValueError as error:
                    attempts.append({'availability': {'status': 'UNAVAILABLE_EVIDENCE_GAP',
                                                       'gaps': [str(error)], 'blockers': []}})
            priority = {'READY': 0, 'HOLD': 1, 'UNAVAILABLE_EVIDENCE_GAP': 2}
            best = min(attempts, key=lambda p: priority[p['availability']['status']]) if attempts else None
            if best and 'plan_id' in best:
                plans.append(best)
            rows.append({'method_id': mid, 'mode': mode,
                'status': best['availability']['status'] if best else 'UNAVAILABLE_EVIDENCE_GAP',
                'plan_id': best.get('plan_id') if best else None,
                'gaps': best['availability']['gaps'] if best else ['no_explicit_valid_frozen_asset'],
                'blockers': best['availability']['blockers'] if best else []})
    return {'schema_version': '0.1.0', 'kind': 'pedagogy_golden_matrix',
            'rows': rows, 'plans': plans, 'public_render_ready': False,
            'synthetic_is_not_real_validation': True}
