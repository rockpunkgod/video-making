"""Capture a verified upstream revision and preserve the existing runtime baseline.

This preparation step does not replace current teaching rules, validate semantic
changes, rewrite private cases, or authorize a runtime migration.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

from core.registry import ROOT
from scripts.ingest_exam_sources import freeze, freeze_json

REPOSITORY = 'https://github.com/rockpunkgod/ANSWER.git'
SHA = re.compile(r'^[0-9a-f]{40}$')


def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest()


def private_relative(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('Expected a relative asset path')
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or escaped asset: '+relative)
    return path


def sections(text):
    # Registry sections are read with universal newlines; compare on that same
    # representation while preserving captured source bytes and their hashes.
    text = text.replace('\r\n','\n').replace('\r','\n')
    lines = text.splitlines(keepends=True)
    starts = [0] + [i for i, line in enumerate(lines) if i and re.match(r'#{2,3} ', line)] + [len(lines)]
    return [{'heading':lines[a].strip().lstrip('# ').strip() if lines[a].startswith('#') else '入口契约',
             'line_start':a+1, 'line_end':b, 'content':''.join(lines[a:b])}
            for a,b in zip(starts,starts[1:])]


def check_source_checkout(source, commit):
    if not SHA.fullmatch(commit):
        raise ValueError('Explicit full upstream commit required')
    def git(*args):
        return subprocess.check_output(['git','-C',str(source),*args], encoding='utf-8').strip()
    if git('rev-parse','HEAD') != commit:
        raise ValueError('Source checkout is not the pinned upstream revision')
    if git('status','--porcelain','--untracked-files=all'):
        raise ValueError('Source checkout has uncommitted changes')
    remote = git('remote','get-url','origin')
    if remote not in {REPOSITORY, REPOSITORY.removesuffix('.git'), 'git@github.com:rockpunkgod/ANSWER.git'}:
        raise ValueError('Source checkout is not the requested ANSWER repository')
    return git('ls-files').splitlines()


def capture(source, commit, captured_at, repo_root=ROOT):
    source, repo_root = Path(source).resolve(), Path(repo_root).resolve()
    date.fromisoformat(captured_at)
    tracked = check_source_checkout(source, commit)
    baseline_manifest = yaml.safe_load((repo_root/'provenance/manifest.yaml').read_text(encoding='utf-8'))
    index = yaml.safe_load((repo_root/'method-registry/registry.yaml').read_text(encoding='utf-8'))
    old_commit = baseline_manifest['commit']
    if old_commit != index['source_baseline']['commit'] or not SHA.fullmatch(old_commit):
        raise ValueError('Existing runtime source identities disagree')
    current_sources = yaml.safe_load((repo_root/index['source_sections']).read_text(encoding='utf-8'))
    expected = {row['path']:row['sha256'] for row in baseline_manifest['files']}
    if len(expected) != len(baseline_manifest['files']):
        raise ValueError('Duplicate baseline source path')
    old_files = {}
    for path, digest in expected.items():
        raw = private_relative(repo_root/'provenance/ANSWER', path).read_bytes()
        if fingerprint(raw) != digest:
            raise ValueError('Frozen baseline source changed: '+path)
        old_files[path] = raw
    # Do not include large raw course originals or archives in a teaching snapshot.
    included = sorted(path for path in tracked if (
        path in expected or
        (path.startswith(('agents/','gaokao-english/','gaokao-grammar-fill/','gaokao-writing/'))
         and Path(path).suffix in {'.md','.py','.json','.yaml','.yml'}) or
        path in {'README.md','kaiming-english-qa/SKILL.md'} or
        (path.startswith('course-audits/') and Path(path).suffix == '.md')))
    if not set(expected) <= set(included):
        raise ValueError('Upstream deleted a baseline source; explicit migration review required')
    new_files = {path:private_relative(source,path).read_bytes() for path in included}
    # Verify the whole batch before the first snapshot write.
    documents = []
    for path, raw in sorted(new_files.items()):
        previous = old_files.get(path)
        documents.append({'path':path,'sha256':fingerprint(raw),'byte_count':len(raw),
                          'previous_sha256':fingerprint(previous) if previous is not None else None,
                          'state':'added' if previous is None else 'unchanged' if raw==previous else 'changed'})
    impacts = []
    for module_path in index['method_files']:
        module = yaml.safe_load(private_relative(repo_root,module_path).read_text(encoding='utf-8'))
        for method in module['methods']:
            bindings = []
            for sid in method['section_ids']:
                old = current_sources['sections'][sid]
                candidates = [s for s in sections(new_files[old['path']].decode('utf-8'))
                              if s['heading'] == old['heading']]
                state = ('missing_or_renamed' if not candidates else 'ambiguous_heading' if len(candidates)>1
                         else 'unchanged_section' if candidates[0]['content']==old['content'] else 'changed_section')
                bindings.append({'old_section_id':sid,'path':old['path'],'heading':old['heading'],
                                 'state':state,'current_candidate_lines':[
                                     [s['line_start'],s['line_end']] for s in candidates]})
            impacts.append({'method_id':method['method_id'],'version':method['version'],
                            'source_name':method['source_name'],'primary_role':method['primary_role'],
                            'method_type':method['method_type'],'source_bindings':bindings,
                            'runtime_migration':'not_applied',
                            'semantic_review':'required_not_proven_by_byte_comparison'})
    old_root = repo_root/'provenance/runtime-snapshots'/old_commit
    # Preserve all assets needed by a historical Registry, not only individual cards.
    asset_paths = {index['source_sections'],'method-registry/registry.yaml','method-registry/source-risks.yaml',
                   'method-registry/symptom-cues.yaml','method-registry/grammar-tree.yaml',
                   'method-registry/anti-rules.yaml','cases/registry.yaml','provenance/manifest.yaml',
                   *index['method_files']}
    cases = yaml.safe_load((repo_root/'cases/registry.yaml').read_text(encoding='utf-8'))
    asset_paths.update(cases['case_files'])
    asset_paths.update('provenance/ANSWER/'+path for path in expected)
    assets = {path:private_relative(repo_root,path).read_bytes() for path in sorted(asset_paths)}
    saved = []
    for path, raw in assets.items():
        freeze(old_root/path, raw)
        saved.append({'path':path,'sha256':fingerprint(raw),'byte_count':len(raw)})
    freeze_json(old_root/'snapshot-manifest.json', {
        'repository':REPOSITORY,'source_commit':old_commit,'captured_at':captured_at,
        'runtime_assets':saved,'purpose':'historical review replay; not current course activation',
        'private_cases_copied_or_modified':False})
    new_root = repo_root/'provenance/upstream-revisions'/commit
    for path, raw in new_files.items():
        freeze(new_root/'files'/path,raw)
    manifest = {'repository':REPOSITORY,'commit':commit,'captured_at':captured_at,
                'previous_runtime_commit':old_commit,'files':documents,
                'current_runtime_updated':False,'skill_installation_updated':False,
                'source_repository_modified':False}
    freeze_json(new_root/'manifest.json',manifest)
    audit = {'repository':REPOSITORY,'target_commit':commit,'previous_runtime_commit':old_commit,
             'captured_at':captured_at,'phase':'upstream_captured_runtime_alignment_pending',
             'counts':{'captured_documents':len(documents),
                       'changed_baseline_documents':sum(d['state']=='changed' for d in documents),
                       'current_methods':len(impacts),
                       'methods_with_changed_or_missing_sections':sum(any(s['state']!='unchanged_section'
                                                                        for s in m['source_bindings']) for m in impacts)},
             'methods':impacts,'completion':False,
             'pending':['review all six modules and delivery policies',
                        'bind current method cards and preserve distinct course names',
                        'implement historical replay and current lifecycle gates',
                        'regenerate projections and audit student entry copies',
                        'run current rules, old case and downstream frozen-artifact regressions',
                        'refresh handoff package and record final acceptance']}
    audit['section_comparison_policy'] = 'universal newlines only; no semantic or punctuation normalization'
    freeze_json(new_root/'migration-audit-v1.json',audit)
    return audit['counts']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--captured-at',required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.source,args.commit,args.captured_at),ensure_ascii=True))


if __name__ == '__main__':
    main()
