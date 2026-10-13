"""Read-only brand projections. Never route a solver or supply video teaching facts."""
from copy import deepcopy
from pathlib import Path
import re

import yaml

from core.registry import Registry
from video_contracts import ROOT, sha

CATALOG_PATH = ROOT / 'method-registry/move-catalog.yaml'
FIELDS = ('trigger', 'action_3s', 'trap_name', 'counterexample', 'mantra')
SOURCE_FIELDS = {
    'trigger': 'trigger_cues', 'action_3s': 'four_step_card',
    'trap_name': 'common_wrong_instinct', 'counterexample': 'counterexamples',
    'mantra': 'memory_line',
}


def create_catalog(specs, *, registry=None):
    registry = registry or Registry()
    entries = []
    for spec in specs:
        if set(spec['move_card']) != set(FIELDS):
            raise ValueError('Five display fields required')
        ids = spec['method_ids']
        if not ids or len(set(ids)) != len(ids) or any(mid not in registry.methods for mid in ids):
            raise ValueError('Existing distinct methods required')
        bindings = {name: [{'method_id': mid, 'version': registry.methods[mid]['version'],
                           'field': field, 'sha': sha(registry.methods[mid][field])}
                          for mid in ids]
                    for name, field in SOURCE_FIELDS.items()}
        entries.append({**deepcopy(spec), 'field_bindings': bindings,
            'methods': [{'method_id': mid, 'version': registry.methods[mid]['version'],
                         'source_name': registry.methods[mid]['source_name'],
                         'role': registry.methods[mid]['primary_role'],
                         'source_references': deepcopy(registry.methods[mid]['source_references'])}
                        for mid in ids],
            'evaluation': {'sampled': 0, 'annotated': 0, 'applicable': None,
                           'hits': None, 'hit_rate': None, 'human_audit_fraction': None},
            'wording_review': 'pending', 'student_test': 'not_run'})
    # Tier is presentation metadata, deliberately outside runtime method cards.
    tiers = {mid: ('move' if m['method_type'] in ('method', 'framework') else
                   'knowledge' if m['method_type'] == 'category' else 'sub_action')
             for mid, m in registry.methods.items()}
    for mid in ('G03', 'G04', 'G09', 'G10', 'G11', 'A09', 'W15'):
        tiers[mid] = 'knowledge'
    tiers['R06'] = 'sub_action'
    result = {'version': '0.1.0', 'source_commit': registry.index['source_baseline']['commit'],
              'scope': 'brand_projection_only', 'runtime_aliases_changed': False,
              'tiers': tiers, 'entries': entries}
    validate_catalog(result, registry=registry)
    return result


def validate_catalog(catalog, *, registry=None):
    registry = registry or Registry()
    if (catalog['scope'] != 'brand_projection_only' or catalog['runtime_aliases_changed'] is not False
            or catalog['source_commit'] != registry.index['source_baseline']['commit']):
        raise ValueError('Display catalog source epoch differs')
    if set(catalog['tiers']) != set(registry.methods) or any(
            value not in ('move', 'sub_action', 'knowledge') for value in catalog['tiers'].values()):
        raise ValueError('Every existing method needs a presentation tier')
    names = set()
    selected = 0
    for row in catalog['entries']:
        if row['name'] in names or re.search(r'[\\/:*?"<>|]', row['name']):
            raise ValueError('Unique filesystem-safe display names required')
        names.add(row['name'])
        selected += row['first_batch'] is True
        if set(row['move_card']) != set(FIELDS) or any(
                not isinstance(text, str) or not text.strip() for text in row['move_card'].values()):
            raise ValueError('Complete display wording required')
        if not 2 <= len(row['move_card']['trap_name']) <= 6:
            raise ValueError('Trap label must contain 2–6 characters')
        if set(row['field_bindings']) != set(FIELDS):
            raise ValueError('Every display field must retain its source bindings')
        if [m['method_id'] for m in row['methods']] != row['method_ids']:
            raise ValueError('Grouped methods remain individually bound')
        for method in row['methods']:
            current = registry.methods[method['method_id']]
            for key, source_key in (('version', 'version'), ('source_name', 'source_name'),
                                    ('role', 'primary_role'), ('source_references', 'source_references')):
                if method[key] != current[source_key]:
                    raise ValueError('Display grouping changed a source method')
        for bindings in row['field_bindings'].values():
            if not bindings:
                raise ValueError('Unbound display field')
            for binding in bindings:
                current = registry.methods[binding['method_id']]
                if (binding['method_id'] not in row['method_ids']
                        or binding['version'] != current['version']
                        or binding['sha'] != sha(current[binding['field']])):
                    raise ValueError('Stale display wording source')
    if not 15 <= selected <= 20:
        raise ValueError('First batch must contain 15–20 display moves')
    return catalog


def load_catalog(path=CATALOG_PATH, *, registry=None):
    catalog = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    return validate_catalog(catalog, registry=registry)


def student_cards(catalog):
    """Five consumer fields. The internal source/role/review records stay separate."""
    labels = ('看到什么', '先做什么', '常见陷阱', '什么时候别用', '记住一句')
    return {f'student-guides/moves/{row["name"]}.md':
            '# ' + row['name'] + '\n\n' + '\n\n'.join(
                f'**{label}**\n\n{row["move_card"][key]}' for key, label in zip(FIELDS, labels)) + '\n'
            for row in catalog['entries'] if row['first_batch']}
