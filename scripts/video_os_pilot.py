"""Local-only bridge from existing frozen reviews to the public Video OS interface.

Reads existing artifacts; never invokes an analyzer or writes teaching sources.
Private source text and output stay under ignored local-data/.
"""
from copy import deepcopy
from pathlib import Path
import json

from answer_engine.frozen_export import FrozenAssetExporter
from core.registry import Registry
from video_contracts import ROOT, read, sha, write
from content_os.__main__ import run_pipeline
from content_os.director import copy_payload
from content_os.lifecycle import refresh_catalog
from content_os.release import ae_contract
from content_os.scoring import rank

PILOTS = (
    ('gaokao-2025-I/F01-gaokao-2025-I-q36.review.json', 'F01', 'F01-sentence'),
    ('gaokao-2025-I/G01-gaokao-2025-I-q59.review.json', 'G01', 'post-reveal-2025-I-q59-G01-route'),
    ('gaokao-2021-I/R02-gaokao-2021-I-q26-style-only.review.json', 'R02', 'post-reveal-2021-I-q26-R02-D-style-only'),
)


def editorial_ratings(bundle, feasibility=False):
    values = {'PA': (6, '编辑估计：已有 wrong instinct 或动作说明显示可讲的卡点；未经学生数据验证'),
              'HP': (6, '编辑估计：先演示一个动作，未使用难度或错误率统计'),
              'DP': (8, '已存在可展示的类型化动作产物'),
              'SV': (7, '编辑判断：动作与停止边界可作为复习材料，收藏效果未验证'),
              'TR': (6, '编辑估计：可说明动作结构，不声称实测迁移效果'),
              'RC': (7, '冻结方法名可稳定展示，不代表已验证品牌传播效果')}
    if feasibility:
        values = {'PF1': (7, '原题与审阅已冻结；公开来源权限仍待审'),
                  'PF2': (8, '已有动作、证据、方法版本和Stop绑定'),
                  'PF3': (7, '单个动作的顺序展示，不开发定制动画'),
                  'PF4': (5, '真实审阅文字较长，时长检查可能拒绝短格式'),
                  'PF5': (7, '适配通用动作演示契约；非AE成片适配证明'),
                  'PF6': (5, '只有AI审阅；公开需要独立人工、来源与编辑审核')}
    result = {k: {'value': value, 'status': 'known', 'rationale': rationale,
                  'evidence': [bundle['asset_id'] + '#/analysis/execution_trace']} for k, (value, rationale) in values.items()}
    if not feasibility:
        result['TS'] = {'value': None, 'status': 'unknown', 'rationale': 'Exam Radar not connected; no heat evidence'}
    return result


def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    base = ROOT / 'local-data/exams-2020-2025/action-reviews'
    output = ROOT / 'local-data/video-os/pilot'
    exporter = FrozenAssetExporter(); registry = Registry()
    protected = [p for folder in ('method-registry', 'cases', 'local-data/exams-2020-2025')
                 for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    import hashlib
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report = {'selection_policy': 'review_cleanliness > teaching_clarity > visual_demonstrability > brand_priority',
              'engineering_pilot': {'status': 'PENDING'}, 'semantic_certification': {'status': 'PENDING'},
              'source_release': {'status': 'PENDING'}, 'editorial_release': {'status': 'PENDING'}, 'pilots': []}
    candidates = []
    for relative, mid, action_id in PILOTS:
        review = read(base / relative)
        a = review['analysis']; q = review['question']
        req = {'question': q, 'analysis': a, 'methods': [registry.methods[m] for m in a['method_versions']],
               'reviews': [review], 'withdrawals': [], 'evaluation_phase': 'post_reveal',
               'source': {'usage_status': 'internal_only', 'redistribution_status': review['source_rights'],
                          'source_reference': review['exam_id'], 'attribution_text': review['exam_id']},
               'current': {'question_snapshot_sha': sha(q), 'method_versions': {m: registry.methods[m]['version'] for m in a['method_versions']}}}
        # Inspect existing withdrawal records, by exact snapshot, not just question ID.
        withdrawal_audit = []
        for path in sorted((base / Path(relative).parent).glob('*withdrawal*.json')):
            record = read(path)
            finding = record.get('withdrawal', record.get('finding', {}))
            matches = finding.get('input_sha256') == sha(q) and finding.get('analysis_sha256') == sha(a)
            withdrawal_audit.append({'artifact_sha': sha(record), 'targets_selected_snapshot': matches})
            if matches:
                req['withdrawals'].append(finding)
        if mid == 'R02':
            old_review = read(base / 'gaokao-2021-I/R02-gaokao-2021-I-q26.review.json')
            old_withdrawal = read(base / 'gaokao-2021-I/R02-gaokao-2021-I-q26.review-withdrawal.json')
            old_req = {**req, 'question': old_review['question'], 'analysis': old_review['analysis'],
                       'reviews': [old_review], 'withdrawals': [old_withdrawal], 'current': {}}
            req['history'] = [exporter.export(old_req)]
        folder = output / (q['question_id'] + '-' + mid)
        write(folder / 'export-request.json', req)
        bundle = exporter.export(req); status = exporter.status(req)
        write(folder / 'bundle.json', bundle); write(folder / 'status.json', status)
        production = {'bundles': [bundle], 'statuses': [status], 'content_scope': 'method_action_demo',
                      'selections': [{'asset_id': bundle['asset_id'], 'method_id': mid, 'action_ids': [action_id]}],
                      'pattern_id': 'P02', 'duration_target': 60,
                      'content_ratings': editorial_ratings(bundle), 'feasibility_ratings': editorial_ratings(bundle, True)}
        request_file = {**production, 'bundles': ['bundle.json'], 'statuses': ['status.json']}
        write(folder / 'production-request.json', request_file)
        result = run_pipeline(production, folder)
        entry = {'question_id': q['question_id'], 'method_id': mid, 'scope': 'method_action_demo',
                 'upstream_review_level': bundle['semantic_review']['level'], 'withdrawal_audit': withdrawal_audit,
                 'engineering': result['engineering'], 'semantic_certification': 'PENDING', 'source_release': 'PENDING', 'editorial_release': 'PENDING'}
        if (folder / 'video-package.json').exists():
            package = read(folder / 'video-package.json')
            candidates.append(read(folder / 'candidate.json'))
            entry['estimated_seconds'] = package['production']['actual_estimated_duration']
            entry['semantic_binding_sha'] = bundle['semantic_binding_sha']
            entry['final_copy_sha'] = package['copy_lock']['final_copy_sha']
            # Same explicit frozen inputs, independent replay output.
            replay = folder / 'replay'
            run_pipeline(production, replay)
            entry['replay_identical'] = copy_payload(package) == copy_payload(read(replay / 'video-package.json'))
            if result['engineering'] == 'PASS':
                write(folder / 'ae-internal-contract.json', ae_contract(package, {bundle['asset_id']: status}, internal=True))
                # Negative fixture is local simulation only, never a new ANSWER review.
                from video_contracts import seal
                simulated = deepcopy(status)
                simulated['effective_status'] = 'WITHDRAWN'
                simulated['invalidation_reasons'] = ['SIMULATED transport event for engineering test; no upstream mutation']
                simulated = seal(simulated)
                catalog = {'entries': [{'id': package['package_id'], 'parent_ids': [], 'artifact': package},
                    {'id': 'simulated-render', 'parent_ids': [package['package_id']], 'artifact': {'status': 'internal_test'}}]}
                stale = refresh_catalog(catalog, {bundle['asset_id']: simulated})
                write(folder / 'simulated-staleness.json', stale)
                entry['staleness_propagated'] = all(e['artifact']['invalidation']['teaching_stale'] for e in stale['entries'])
        report['pilots'].append(entry)
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report['upstream_files_unchanged'] = before == after
    if not report['upstream_files_unchanged']:
        raise ValueError('Protected upstream files changed')
    count = sum(p['engineering'] == 'PASS' for p in report['pilots'])
    report['engineering_pilot'] = {'status': 'PASS' if count >= 2 else 'PARTIAL', 'completed_real_assets': count,
                                   'meaning': 'Engineering preservation only; no independent teaching certification'}
    write(output / 'rank.json', rank(candidates))
    write(output / 'acceptance.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
