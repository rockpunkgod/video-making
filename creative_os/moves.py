"""Read-only brand projections. Never route a solver or supply video teaching facts."""
from copy import deepcopy
from pathlib import Path
import re

import yaml

from core.registry import Registry
from video_contracts import ROOT, sha

CATALOG_PATH = ROOT / 'method-registry/move-catalog.yaml'
FIELDS = ('trigger', 'action_3s', 'trap_name', 'counterexample', 'mantra')
FIELDS_V2 = ('trigger', 'role', 'first_step', 'trap_name', 'counterexample', 'mantra')
ROLE_NAMES = {'locator': '定位', 'interpreter': '理解', 'reducer': '缩小范围',
              'decider': '判定', 'verifier': '核验', 'framework': '组织步骤'}
SOURCE_FIELDS = {
    'trigger': 'trigger_cues', 'action_3s': 'four_step_card',
    'trap_name': 'common_wrong_instinct', 'counterexample': 'counterexamples',
    'mantra': 'memory_line',
}


def create_catalog(specs, *, registry=None):
    registry = registry or Registry()
    entries = []
    version = '0.2.0' if specs and 'first_step' in specs[0]['move_card'] else '0.1.0'
    fields = FIELDS_V2 if version == '0.2.0' else FIELDS
    source_fields = {**SOURCE_FIELDS}
    if version == '0.2.0':
        source_fields['first_step'] = source_fields.pop('action_3s')
        source_fields['role'] = 'primary_role'
    for spec in specs:
        if set(spec['move_card']) != set(fields):
            raise ValueError('Consistent complete display fields required')
        ids = spec['method_ids']
        if not ids or len(set(ids)) != len(ids) or any(mid not in registry.methods for mid in ids):
            raise ValueError('Existing distinct methods required')
        bindings = {name: [{'method_id': mid, 'version': registry.methods[mid]['version'],
                           'field': field, 'sha': sha(registry.methods[mid][field])}
                          for mid in ids]
                    for name, field in source_fields.items()}
        entries.append({**deepcopy(spec), 'field_bindings': bindings,
            'methods': [{'method_id': mid, 'version': registry.methods[mid]['version'],
                         'source_name': registry.methods[mid]['source_name'],
                         'role': registry.methods[mid]['primary_role'],
                         'source_references': deepcopy(registry.methods[mid]['source_references'])}
                        for mid in ids],
            'evaluation': {'sampled': 0, 'annotated': 0, 'applicable': None,
                           'hits': None, 'hit_rate': None, 'human_audit_fraction': None},
            'wording_review': 'pending', 'student_test': 'not_run'})
        if version == '0.2.0':
            entries[-1]['trap_status'] = 'candidate_pending_three_reviewed_cases'
    # Tier is presentation metadata, deliberately outside runtime method cards.
    tiers = {mid: ('move' if m['method_type'] in ('method', 'framework') else
                   'knowledge' if m['method_type'] == 'category' else 'sub_action')
             for mid, m in registry.methods.items()}
    for mid in ('G03', 'G04', 'G09', 'G10', 'G11', 'A09', 'W15'):
        tiers[mid] = 'knowledge'
    tiers['R06'] = 'sub_action'
    result = {'version': version, 'source_commit': registry.index['source_baseline']['commit'],
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
        fields = FIELDS_V2 if catalog['version'] == '0.2.0' else FIELDS
        if row['name'] in names or re.search(r'[\\/:*?"<>|]', row['name']):
            raise ValueError('Unique filesystem-safe display names required')
        names.add(row['name'])
        selected += row['first_batch'] is True
        if set(row['move_card']) != set(fields) or any(
                not isinstance(text, str) or not text.strip() for text in row['move_card'].values()):
            raise ValueError('Complete display wording required')
        if not re.fullmatch(r'[\u3400-\u9fff]{2,6}', row['move_card']['trap_name']):
            raise ValueError('Trap label must contain 2–6 characters')
        if set(row['field_bindings']) != set(fields):
            raise ValueError('Every display field must retain its source bindings')
        if [m['method_id'] for m in row['methods']] != row['method_ids']:
            raise ValueError('Grouped methods remain individually bound')
        for method in row['methods']:
            current = registry.methods[method['method_id']]
            for key, source_key in (('version', 'version'), ('source_name', 'source_name'),
                                    ('role', 'primary_role'), ('source_references', 'source_references')):
                if method[key] != current[source_key]:
                    raise ValueError('Display grouping changed a source method')
        if fields == FIELDS_V2:
            if (len(re.findall(r'[\u3400-\u9fff]', row['move_card']['first_step'])) > 15
                    or len(re.findall(r'[\u3400-\u9fff]', row['move_card']['mantra'])) > 10):
                raise ValueError('First step must fit 15 Chinese characters, mantra 10')
            if row['move_card']['role'] != ' / '.join(m['role'] for m in row['methods']):
                raise ValueError('Display roles must preserve each grouped method in order')
            if row.get('trap_status') != 'candidate_pending_three_reviewed_cases':
                raise ValueError('Trap activation is not granted by catalog wording')
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
    fields = FIELDS_V2 if catalog['version'] == '0.2.0' else FIELDS
    if fields == FIELDS_V2:
        labels = ('看到什么', '这一步做什么', '先做什么', '常见陷阱', '什么时候别用', '记住一句')
    def display(row, key):
        if key == 'role':
            return '、'.join(dict.fromkeys(ROLE_NAMES[m['role']] for m in row['methods']))
        if key == 'trap_name' and row.get('trap_status') == 'candidate_pending_three_reviewed_cases':
            return '—'
        return row['move_card'][key]
    return {f'student-guides/moves/{row["name"]}.md':
            '# ' + row['name'] + '\n\n' + '\n\n'.join(
                f'**{label}**\n\n{display(row, key)}' for key, label in zip(fields, labels)) + '\n'
            for row in catalog['entries'] if row['first_batch']}
