"""Reviewed, pinned source migration; no learner promotion or private case edits.

The additive sync deliberately rejects this revision. This separate migration
records changed sections and the one explicit heading relocation, retains the
complete prior Registry snapshot, and repairs conflicting editorial projections.
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
from scripts.capture_answer_revision import sections
from scripts.activate_answer_alignment import apply_payload
from scripts.generate_assets import build, generate

PREVIOUS = '1c388a0596b13935ae7c6a1af00834915a8efa33'
TARGET = '70db6d6f0423bc8da95c591ca1feda883c2865b1'
READING = 'gaokao-english/references/reading-comprehension.md'
CLOZE = 'gaokao-english/references/cloze.md'
WRITING = 'gaokao-writing/references/continuation-writing-and-correction.md'
RENAMES = {(CLOZE, '语篇行文结构的已核验操作（内容说明，非新增方法名）'):
           '行文结构（结构认识与已核操作）'}
NOTES = {
 'R': '主客一致补观察/假设与语义施受边界；主语、时态、动静独立保名，不借七选五分组。期末两首一尾来源不覆盖三化入口。',
 'F': '单复一致为指代/概括检查，不增加第四分组维度；逻辑判断内容关联保独立原名，不新增整题顺序。',
 'C': '行文结构是结构认识与取证入口；首句给假设，组合口诀和无信靠主题不替代单空证据，不强制遍数。',
 'G': '一看二思保原名；反身回查不靠人称重复；why/how不按是否发生定词；非谓语按成分定主人，完成不定式不一律禁作后置修饰，逗号不独自定doing。',
 'A': '寒4五步不吞并赠课挖空版本；春5格式与结尾服从实际任务；国庆表达技巧、修改流程和构思模型分别保名，简单句可保留。',
 'W': 'PTSD各来源槽位不混；动作面已证为描写概念而非自造公式；两简一复从与反向扩写分开；七句方案不取代十句五定，环境/升华须由当前故事支持。',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_text(value, old, new):
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [replace_text(v, old, new) for v in value]
    if isinstance(value, dict):
        return {k: replace_text(v, old, new) for k, v in value.items()}
    return value


def prepare(root=ROOT):
    root = Path(root).resolve()
    with patch('core.registry.ROOT', root):
        live = Registry()
        live.validate()
        history = Registry(snapshot_commit=PREVIOUS)
    if live.index['source_baseline']['commit'] != PREVIOUS:
        raise ValueError('Migration requires the explicit previous epoch')
    if history.index != live.index or history.methods != live.methods:
        raise ValueError('Prior snapshot must preserve current editorial work exactly')
    captured = root / 'provenance/upstream-revisions' / TARGET
    manifest = json.loads((captured / 'manifest.json').read_bytes())
    if manifest['commit'] != TARGET or manifest['previous_runtime_commit'] != PREVIOUS:
        raise ValueError('Wrong captured source epoch')
    files = {}
    for row in manifest['files']:
        path = (captured / 'files' / row['path']).resolve()
        if not path.is_relative_to((captured / 'files').resolve()):
            raise ValueError('Captured path escapes revision')
        raw = path.read_bytes()
        if sha(raw) != row['sha256']:
            raise ValueError('Captured source digest mismatch')
        files[row['path']] = raw
    payload, lookup, source_sections, documents = {}, {}, {}, []
    baseline = live._load('provenance/manifest.yaml')
    paths = [row['path'] for row in baseline['files']]
    paths.append('gaokao-writing/references/course-evidence.md')
    next_manifest = {'repository': manifest['repository'], 'commit': TARGET, 'files': []}
    for path in paths:
        raw = files[path]
        payload['provenance/ANSWER/' + path] = raw
        next_manifest['files'].append({'path': path, 'sha256': sha(raw)})
        if not path.endswith('.md'):
            continue
        ids = []
        for section in sections(raw.decode('utf-8')):
            key = (path, section['heading'])
            if key in lookup:
                raise ValueError('Ambiguous source heading')
            sid = sha(f"{path}:{section['line_start']-1}".encode())[:16]
            lookup[key] = sid
            source_sections[sid] = {'path': path, **section, 'commit': TARGET}
            ids.append(sid)
        documents.append({'path': path, 'sha256': sha(raw), 'sections': ids})

    def target_key(path, heading):
        return (path, RENAMES.get((path, heading), heading))

    def rebind(sid):
        old = live.sources['sections'][sid]
        return lookup[target_key(old['path'], old['heading'])]

    def save(path, value):
        payload[path] = yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode('utf-8')

    index = deepcopy(live.index)
    index['source_baseline'].update(commit=TARGET, captured_at='2026-10-30')
    index['cloze_order_source']['commit'] = TARGET
    index['reference_supersession'] = {'from_commit': PREVIOUS, 'to_commit': TARGET,
        'sections': [{'path': old['path'], 'heading': old['heading'],
            'before_sha256': sha(old['content'].rstrip().encode()),
            'after_sha256': sha(source_sections[rebind(sid)]['content'].rstrip().encode())}
            for sid, old in live.sources['sections'].items()
            if (old['path'], old['heading']) in lookup]}
    for row in index['course_identities']:
        source = row['source']
        key = target_key(source['path'], source['heading'])
        section = source_sections[lookup[key]]
        row['source_heading'] = key[1]
        source.update({k: section[k] for k in ('heading', 'commit', 'line_start', 'line_end')})
        if key == (WRITING, '动作链与动作面'):
            row['task_scope'] = ['action_chain', 'action_surface_concept_not_formula']
    identities = [
        (READING, name, 'bounded_course_operation', True) for name in ['主语一致', '时态一致', '动静一致']]
    identities += [(READING, '语言冰山理论（解释框架）', 'explanatory_framework', False),
        (READING, '阅读理解基本流程／两首一尾定主题（期末规划来源）', 'source_specific_framework', True),
        ('gaokao-english/references/seven-five.md', '单复一致', 'consistency_check', True),
        ('gaokao-english/references/seven-five.md', '逻辑判断内容关联', 'bounded_course_operation', True),
        (WRITING, '句子升华三部曲', 'sentence_training', True),
        (WRITING, '国庆续写的独立入口与提纲方案', 'source_version_group', True),
        ('gaokao-writing/references/application-writing-and-correction.md', '国庆应用文：修改流程与表达训练', 'source_version_group', True)]
    for path, heading, kind, active in identities:
        s = source_sections[lookup[(path, heading)]]
        index['course_identities'].append({'source_heading': heading, 'identity_kind': kind,
            'source_activation': active, 'task_scope': [], 'equivalent_to_existing_brand': False,
            'runtime_registration': 'not_created_by_this_plan',
            'source': {k: s[k] for k in ('path', 'heading', 'commit', 'line_start', 'line_end')}})
    reviews = []
    corrected = []
    for path in index['method_files']:
        module = live._load(path)
        for original in module['methods']:
            mid = original['method_id']
            method = deepcopy(original)
            changes = []
            for sid in original['section_ids']:
                before, after = live.sources['sections'][sid], source_sections[rebind(sid)]
                if before['content'] != after['content']:
                    changes.append({'old_heading': before['heading'], 'new_heading': after['heading'],
                        'before_sha256': sha(before['content'].encode()), 'after_sha256': sha(after['content'].encode())})
            method['section_ids'] = [rebind(sid) for sid in original['section_ids']]
            for ref in method['source_references']:
                ref['heading'] = target_key(ref['path'], ref['heading'])[1]
                if (ref['path'], ref['heading']) not in lookup:
                    raise ValueError('Unresolved explicit citation')
                ref['commit'] = TARGET
            if mid == 'W05':
                method = replace_text(method, '动作面独立定义未核，不补成动作加心理加环境。',
                    '动作面是使动作饱满生动的描写概念，不另造动作加心理加环境公式。')
                method = replace_text(method, '动作面：独立定义待核', '动作面：描写概念，非独立公式')
                method['levels']['L1'] = '把已有行动拆成必要的相关小动作，核人物能力；不凑数量。'
                method['levels']['L2'] = '核同一主体、动作关系、人物能力和语境；两或三动作是局部训练，不是所有句子的数量上限。'
            if mid == 'A06':
                method['levels']['L2'] = method['core_action'] + '准确异写可保留；赠课挖空循环另按来源说明，不塞入寒4五步。'
            if mid == 'A07':
                method['levels']['L1'] = method['core_action']
                method['levels']['L2'] = method['core_action'] + '这是应用文来源；续写已有一句再加修饰的同名版本另列。'
                method['levels']['L4'] = '新题仍核相关简单句的真实关系；无法合法合并时保留独立句，不借续写定义补固定步骤。'
            if mid in {'W05', 'A06', 'A07'}:
                parts = method['version'].split('.')
                parts[-1] = str(int(parts[-1]) + 1)
                method['version'] = '.'.join(parts)
                index['methods'][mid]['version'] = method['version']
                method['full']['presentation_revision'] = '2026-10-30.1'
                corrected.append(mid)
            method['full']['section_ids'] = method['section_ids']
            method['full']['source_update_note'] = NOTES[mid[0]]
            method['static_design_review'].update(source_section_ids=method['section_ids'],
                status='source_bound_editorial_review')
            method['source_alignment'].update(commit=TARGET, state='live_source_bound',
                source_content_changed=bool(changes),
                acceptance='2026-10-30 explicit source delta review; learner/blind/release pending')
            method['change_reason'] = 'ANSWER 70db6d6 显式来源差异复核；保留品牌动作和基础入口，异文分源，旧Case不自动获新纪元准入。'
            method['student_ready'] = False
            reviews.append({'method_id': mid, 'source_deltas': changes,
                'review': NOTES[mid[0]], 'version_before': original['version'], 'version_after': method['version']})
            original.clear()
            original.update(method)
        save(path, module)
    risks = deepcopy(live._load('method-registry/source-risks.yaml'))
    replacements = {
        'GRAMMAR-PARTICIPLE-QUICK-SPLIT': '不能用有无 `be` 机械二分',
        'GRAMMAR-WHY-HOW-TEMPORAL-SHORTCUT': '不能以事件已经发生或尚未达成独立定词',
        'GRAMMAR-NONFINITE-UNIVERSAL-LISTS': '完成不定式则可在适当结构中作后置修饰',
    }
    for risk in risks['risks']:
        if 'section_id' in risk:
            risk['section_id'] = rebind(risk['section_id'])
        if risk['risk_id'] in replacements:
            risk['source_quote'] = replacements[risk['risk_id']]
            risk['status'] = 'upstream_corrected_boundary_retained'
            risk['reason'] = '新版已明确收紧旧简化口径；旧全称说法仅留历史快照，当前按本句结构、语义与时间关系核验。'
            risk['action'] = '执行新版完整边界；不再把已纠正原话呈为当前来源，不按有无be、发生/未发生或完成形式名称独立选排。'
    grammar = deepcopy(live.grammar_tree)
    grammar['source_sections'] = [rebind(sid) for sid in grammar['source_sections']]
    anti = deepcopy(live._load('method-registry/anti-rules.yaml'))
    for rule in anti['rules']:
        rule['source_evidence'] = [rebind(sid) for sid in rule['source_evidence']]
    for path, value in [('method-registry/registry.yaml', index), ('method-registry/source-risks.yaml', risks),
            ('method-registry/source-sections.yaml', {'sections': source_sections, 'documents': documents}),
            ('method-registry/grammar-tree.yaml', grammar), ('method-registry/anti-rules.yaml', anti),
            ('method-registry/symptom-cues.yaml', {'routes': live.symptom_cues}), ('provenance/manifest.yaml', next_manifest)]:
        save(path, value)
    with tempfile.TemporaryDirectory(prefix='answer-70db6d6-stage-') as tmp:
        candidate_root = Path(tmp)
        for directory in ('schemas', 'cases'):
            shutil.copytree(root / directory, candidate_root / directory)
        for path, raw in payload.items():
            dest = candidate_root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        with patch('core.registry.ROOT', candidate_root):
            candidate = Registry()
            validation = candidate.validate()
        payload.update({path: content.encode('utf-8') for path, content in build(candidate).items()})
    return payload, {'from_commit': PREVIOUS, 'to_commit': TARGET, 'validation': validation,
        'methods_reviewed': reviews, 'changed_source_methods': sum(bool(x['source_deltas']) for x in reviews),
        'corrected_projection_methods': corrected, 'learner_acceptance': 'pending',
        'source_repository_modified': False, 'private_cases_modified': False, 'method_promotion_applied': False,
        'full_regression': 'not_run', 'scope': 'source_alignment_and_bounded_editorial_corrections'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    report_path = ROOT / 'provenance/runtime-alignments' / (TARGET + '-reviewed.json')
    if Registry().index['source_baseline']['commit'] == TARGET:
        Registry().validate()
        generate(check=True)
        print(json.dumps({'status': 'already_source_aligned', 'commit': TARGET}))
        return
    payload, report = prepare()
    if args.apply:
        backup = Path(tempfile.mkdtemp(prefix='activation-backup-', dir=ROOT / 'local-data/answer-alignment-20261030'))
        journal = apply_payload(ROOT, payload, backup)
        Registry().validate()
        generate(check=True)
        report.update(status='applied', backup_directory=str(backup), asset_hashes=journal['assets'])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in {'methods_reviewed', 'asset_hashes'}}, ensure_ascii=True))


if __name__ == '__main__':
    main()
