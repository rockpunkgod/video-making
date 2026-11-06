"""Pinned, bounded criteria clarification; no automatic teaching promotion."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import yaml

from core.registry import ROOT, Registry
from scripts import align_answer_9a872ba as compiler
from scripts.align_answer_20261030 import replace_text
from scripts.activate_answer_alignment import apply_payload
from scripts.generate_assets import generate
from scripts.capture_answer_revision import fingerprint

PREVIOUS='9a872ba0397910bd9350cff860c3b94fd061a3a8'
TARGET='59190489abd3e0fb6543c9a04e137881ae98cd88'
RULES={
 'C07':'先产出同一人物、状态或事件的词汇呼应及所在内容；完整核清身份、行为、候选词义与回填关系后，可据该内容选排。只有字面重复时仍只是定位线索，不能从词形直接定案。',
 'F05':'产出统领范围及段落任务解释；候选覆盖全部管辖内容、引出实际展开且承接成立时，据完整覆盖选排，不再为辅助标签额外复证。',
 'F06':'产出具体呼应的核验：候选提供所指对象、概括前述内容或承接同一动作，并与两侧及段落任务相接时，据此选排；只有同词命中不能定案，多项成立再比真实差异。',
 'F07':'把两侧完整内容与当前段落任务一起核清；说明候选怎样接出所需关系、竞争项哪处不成立，据此选排。证据已足够不另排一轮无疑点回文，冲突或仍有竞争才继续。',
 'F08':'完整命题、否定范围、评价对象及安抚或改善功能共同支持时，据具体评价差异选排；只有同维同向仍仅初筛，不能凭好坏词或另一空占用定案。',
 'R16':'产出对象—完整判断框架；选项倒推或妖项助攻提供核查入口，所问范围真实展开支持完整判断与覆盖时据此选排。已核正文可直接使用，不强制助攻先于回文或事后再读一次。',
}
NOTE='点明方法、当前决定性证据与选排结论；定位或形式初筛不定案，完整对应/指代/覆盖/逻辑满足判据后可用显式副职责选排；缺证、竞争或冲突才继续，不造暂定或重复回文。'


def correct(method):
    mid=method['method_id']
    if mid not in RULES:return method
    method=replace_text(method,method['decision_rule'],RULES[mid])
    method['secondary_roles']=list(dict.fromkeys([*method['secondary_roles'],'decider']))
    method['compact']['30s']+='完整内容已核清并区分竞争项，就说明选排证据；只有形式线索则继续。'
    # Keep one primary role in the first-use entry. Explicit secondary decisions
    # require their own reviewed evidence/action, never a role-label shortcut.
    method['full']['decision_boundary']='主要职责和首个产物保持；副职责须显式声明decider并提供已审阅的具体候选差异、题面证据、停止与回填检查。不是分组、词面、好坏方向或排剩一项自动升级。'
    method['secondary_role_gate']=method['full']['decision_boundary']
    parts=method['version'].split('.');parts[-1]=str(int(parts[-1])+1);method['version']='.'.join(parts)
    method['full']['presentation_revision']='2026-11-06.1'
    return method


def prepare(root=ROOT):
    renames=dict(compiler.RENAMES)
    renames[('gaokao-english/references/cloze.md','名词复现只是线索')]='名词复现：找呼应并核当前空'
    notes=dict(compiler.NOTES)
    for prefix in ('R','F','C'):notes[prefix]=NOTE
    # Reuse the audited compiler with explicit inputs; historical pinned entry
    # points and all other card corrections retain their original behavior.
    with patch.multiple(compiler,PREVIOUS=PREVIOUS,TARGET=TARGET,RENAMES=renames,NOTES=notes,correct=correct):
        payload,report=compiler.prepare(root)
    index=yaml.safe_load(payload['method-registry/registry.yaml'])
    index['source_baseline']['captured_at']='2026-11-06'
    payload['method-registry/registry.yaml']=yaml.safe_dump(index,allow_unicode=True,sort_keys=False).encode()
    for path in index['method_files']:
        module=yaml.safe_load(payload[path])
        for method in module['methods']:
            method['change_reason']='ANSWER 5919048 明确已核内容判据与有界副职责；不新增算法，不虚构暂定，不重复无疑点回文，旧审阅不自动升级。'
        payload[path]=yaml.safe_dump(module,allow_unicode=True,sort_keys=False).encode()
    with patch('core.registry.ROOT',Path(root).resolve()):old=Registry()
    sections=yaml.safe_load(payload[index['source_sections']])['sections']
    reviewed=[]
    for source in old.sources['sections'].values():
        heading=renames.get((source['path'],source['heading']),source['heading'])
        matches=[s for s in sections.values() if (s['path'],s['heading'])==(source['path'],heading)]
        if len(matches)!=1:raise ValueError('Common source section must have one exact reviewed target')
        after=matches[0]
        if source['content']!=after['content']:
            reviewed.append({'path':source['path'],'old_heading':source['heading'],'new_heading':heading,
                'before_sha256':fingerprint(source['content'].encode()),'after_sha256':fingerprint(after['content'].encode())})
    report['source_sections_reviewed']=reviewed
    report.update(corrected_projection_methods=list(RULES),
        scope='explicit decision criteria, bounded secondary roles, no redundant rechecks',
        method_promotion_applied=False)
    return payload,report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if Registry().index['source_baseline']['commit']==TARGET:
        Registry().validate();generate(check=True);print('already source aligned');return
    payload,report=prepare()
    if args.apply:
        base=ROOT/'local-data/answer-alignment-20261106';base.mkdir(parents=True,exist_ok=True)
        backup=Path(tempfile.mkdtemp(prefix='activation-backup-',dir=base))
        journal=apply_payload(ROOT,payload,backup);Registry().validate();generate(check=True)
        report.update(status='applied',backup_directory=str(backup),asset_hashes=journal['assets'])
        path=ROOT/'provenance/runtime-alignments'/f'{TARGET}-reviewed.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'methods_reviewed','asset_hashes'}},ensure_ascii=False))


if __name__=='__main__':main()
