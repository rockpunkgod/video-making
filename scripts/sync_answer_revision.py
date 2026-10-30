"""Apply a captured additive ANSWER revision without reauthoring teaching rules.

Only exact, unchanged existing method sections may use this path. Changed
actions need their own semantic migration. Old Cases and private evidence stay
untouched; a new source identity does not inherit old admission or release.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import yaml

from core.registry import ROOT, Registry
from scripts.activate_answer_alignment import apply_payload
from scripts.capture_answer_revision import sections
from scripts.generate_assets import build, generate


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare_payload(commit, root=ROOT):
    root = Path(root).resolve()
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Full lowercase captured commit required')
    with patch('core.registry.ROOT', root):
        live = Registry()
        live.validate()
    previous = live.index['source_baseline']['commit']
    revision = root / 'provenance/upstream-revisions' / commit
    captured = json.loads((revision / 'manifest.json').read_bytes())
    if captured['commit'] != commit or captured['previous_runtime_commit'] != previous:
        raise ValueError('Captured revision does not extend the current source epoch')
    # A historical Registry must remain loadable before changing live metadata.
    with patch('core.registry.ROOT', root):
        history = Registry(snapshot_commit=previous)
        if history.index != live.index or history.methods != live.methods:
            raise ValueError('Preserved historical epoch differs from current rules')

    captured_files = {}
    for row in captured['files']:
        relative = row['path']
        path = (revision / 'files' / relative).resolve()
        if not path.is_relative_to((revision / 'files').resolve()):
            raise ValueError('Captured path escapes revision')
        raw = path.read_bytes()
        if digest(raw) != row['sha256']:
            raise ValueError('Captured source changed: ' + relative)
        captured_files[relative] = raw

    payload, section_index, documents, lookup = {}, {}, [], {}
    manifest = {'repository': captured['repository'], 'commit': commit, 'files': []}
    baseline = live._load('provenance/manifest.yaml')
    for row in baseline['files']:
        relative = row['path']
        if relative not in captured_files:
            raise ValueError('Existing runtime source missing from revision: ' + relative)
        raw = captured_files[relative]
        payload['provenance/ANSWER/' + relative] = raw
        manifest['files'].append({'path': relative, 'sha256': digest(raw)})
        if Path(relative).suffix != '.md':
            continue
        ids = []
        for section in sections(raw.decode('utf-8')):
            key = (relative, section['heading'])
            if key in lookup:
                raise ValueError('Ambiguous exact source heading: ' + str(key))
            sid = digest(f"{relative}:{section['line_start']-1}".encode())[:16]
            section_index[sid] = {'path': relative, **section, 'commit': commit}
            lookup[key] = sid
            ids.append(sid)
        documents.append({'path': relative, 'sha256': digest(raw), 'sections': ids})

    def rebind(sid, require_unchanged=False):
        old = live.sources['sections'][sid]
        key = (old['path'], old['heading'])
        if key not in lookup:
            raise ValueError('Existing section removed or renamed: ' + str(key))
        target = lookup[key]
        if require_unchanged and section_index[target]['content'] != old['content']:
            raise ValueError('Changed method content requires semantic migration: ' + str(key))
        return target

    def save(relative, value):
        payload[relative] = yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode('utf-8')

    index = deepcopy(live.index)
    index['source_baseline'].update(commit=commit, captured_at=captured['captured_at'])
    if index.get('cloze_order_source'):
        index['cloze_order_source']['commit'] = commit
    for identity in index.get('course_identities', []):
        source = identity['source']
        sid = lookup[(source['path'], source['heading'])]
        source.update({key: section_index[sid][key] for key in ('commit', 'line_start', 'line_end')})
    for relative in index['method_files']:
        module = live._load(relative)
        for method in module['methods']:
            method['section_ids'] = [rebind(sid, require_unchanged=True) for sid in method['section_ids']]
            for ref in method['source_references']:
                if (ref['path'], ref['heading']) not in lookup:
                    raise ValueError('Unresolved existing method citation')
                ref['commit'] = commit
            method['full']['section_ids'] = list(method['section_ids'])
            if method.get('static_design_review'):
                method['static_design_review'].update(
                    source_section_ids=list(method['section_ids']),
                    status='source_rebound_semantic_reacceptance_pending')
            # Keep method versions and actual actions; change only source scope.
            method['source_alignment'].update(commit=commit, state='live_source_bound',
                source_content_changed=False,
                acceptance='unchanged_method_sections; added_source_contracts_preserved; learner/release_pending')
            method['student_ready'] = False
            method['change_reason'] = 'ANSWER ' + commit + ' 增量来源同步；保留既有动作与版本，旧证据不自动获得新来源准入。'
        save(relative, module)

    risks = live._load('method-registry/source-risks.yaml')
    for risk in risks['risks']:
        if risk.get('section_id'):
            risk['section_id'] = rebind(risk['section_id'])
    grammar = deepcopy(live.grammar_tree)
    grammar['source_sections'] = [rebind(sid) for sid in grammar['source_sections']]
    anti = live._load('method-registry/anti-rules.yaml')
    for rule in anti['rules']:
        rule['source_evidence'] = [rebind(sid) for sid in rule['source_evidence']]
    save('method-registry/source-risks.yaml', risks)
    save('method-registry/grammar-tree.yaml', grammar)
    save('method-registry/anti-rules.yaml', anti)
    save('method-registry/symptom-cues.yaml', {'routes': live.symptom_cues})
    save('method-registry/source-sections.yaml', {'sections': section_index, 'documents': documents})
    save('method-registry/registry.yaml', index)
    save('provenance/manifest.yaml', manifest)

    with tempfile.TemporaryDirectory(prefix='answer-sync-stage-') as temporary:
        candidate_root = Path(temporary)
        for directory in ('schemas', 'cases'):
            shutil.copytree(root / directory, candidate_root / directory)
        for relative, raw in payload.items():
            path = candidate_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        with patch('core.registry.ROOT', candidate_root):
            candidate = Registry()
            validation = candidate.validate()
        payload.update({path: content.encode('utf-8') for path, content in build(candidate).items()})
    report = {'scope': 'additive_source_sync_not_method_or_student_promotion',
              'from_commit': previous, 'to_commit': commit,
              'captured_documents_verified': len(captured_files), 'validation': validation,
              'existing_method_sections_changed': 0, 'method_versions_changed': 0,
              'source_repository_modified': False, 'historical_cases_modified': False,
              'method_promotion_applied': False, 'learner_acceptance': 'pending'}
    return payload, report


def sync(commit):
    live = Registry()
    if live.index['source_baseline']['commit'] == commit:
        live.validate()
        generate(check=True)
        return {'status': 'already_source_aligned', 'source_commit': commit}
    payload, report = prepare_payload(commit)
    directory = ROOT / 'local-data/answer-sync-2026-10-24'
    directory.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='backup-', dir=directory))
    journal = apply_payload(ROOT, payload, backup)
    Registry().validate()
    generate(check=True)
    report.update(status='source_bound_candidate_epoch_active', backup_directory=str(backup),
                  asset_write_count=len(journal['assets']), full_regression='pending')
    path = ROOT / 'provenance/runtime-alignments' / (commit + '-additive.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    print(json.dumps(sync(args.commit), ensure_ascii=False, indent=2))
