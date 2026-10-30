"""Pinned source migration with reviewed boundaries and historical snapshots."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import yaml

from core.registry import ROOT, Registry
from scripts.capture_answer_revision import sections, fingerprint as sha
from scripts.activate_answer_alignment import apply_payload
from scripts.align_answer_20261030 import replace_text
from scripts.generate_assets import build, generate

PREVIOUS = '70db6d6f0423bc8da95c591ca1feda883c2865b1'
TARGET = '9a872ba0397910bd9350cff860c3b94fd061a3a8'
READING = 'gaokao-english/references/reading-comprehension.md'
LISTENING = 'gaokao-english/references/listening.md'
APPLICATION = 'gaokao-writing/references/application-writing-and-correction.md'
RENAMES = {
    (READING, '中心思想（8.7讲义原名，强版本未激活）'):
        '中心思想（8.7讲义原名，受限记叙文本推断入口）',
    (LISTENING, '解题三步（寒13练习／精听来源）'):
        '解题三步（寒假第10讲练习／精听来源，本地文件序号13）',
}
NOTES = {
    'R': '按题干保积极阅读分支；比数绝重大只定位，中心思想受限于文本推断；记叙框架来源各保，不改三化产物和篇级依赖。',
    'F': '总起以真实统领触发，不加非典型位置人为门槛；比较关联句只初筛，褒贬核完整断言与安抚功能，不靠另一空占用定案。',
    'C': '同根可作暂选后的独立回证，不能以初选反证词义；配平只提醒回题核证，不按字母配额改答案。',
    'G': '特指不等于唯一；介词核中心词义项与补语，as/though核构式，cattle为复数；非谓语先后不机械对应形式，搭配清单不排他。',
    'A': '27写作口诀、大小三圈与六类信件分源；综合运用小结不改名五审。三思辨模型按职责用，单句重构已补核，简单句和相关两点可保留。',
    'W': 'PTSD先核已知再在约束内构思未给解决过程，不把留空误作禁止创造；十类、32素材按功能选，不强制前置、数量或负面结果。',
}


def correct(method):
    mid = method['method_id']
    if mid == 'G03':
        method = replace_text(method, '所指是否唯一不清', '特指泛指及所指关系不清')
    elif mid == 'A05':
        method = replace_text(method, '不宣称缺连续口述或新完整例的分支已全面验收。',
            '已补核两独立单句重构；不把例题完成分词固定到新题，准确简单句可以保留。')
    elif mid == 'W03':
        method = replace_text(method, '未知槽留空，不凭口诀补事故或救场者',
            '核清原文与两首句前未知槽留空；核清后可在人物、矛盾与结果约束内构思未给的解决过程，不凭口诀补事故或救场者')
        method['compact']['30s'] = ('剧情整理不清？先用教师为本次固定的四格，圈原文和两首句已知的信息，未知先留空。'
            '例如，目标已给、解决过程未给，先记目标，核清人物与结果约束后再构思解决过程。'
            '教师先定版本；无依据先空着，不凭口诀编事故。方案撞上原文或首句限制就停。')
        method['compact']['90s'] = ('剧情整理不清？先注明本次四格版本，圈原文与两首句的已知信息，未知先标问号。'
            '这一步得到的是情节约束卡。核清人物关系、矛盾及两段必须接到的结果后，未给的解决过程可以合理构思；'
            '同一题可有多个方案，每个都要逐条接住约束。未定版本或方案冲突就停。'
            '反例：为了填满困难格硬编事故，或用无铺垫的新人物解决问题，格子齐了也不成立。'
            '换题重圈新文约束，不搬旧剧情。挑战：先不写全文，标出已知、待核和核清后可构思的解决过程，并给一条原文约束。')
        method['levels'].update(
            L1='教师先固定本次版本；圈原文与两首句已知，每格填已知或标待核，不混字母定义。',
            L2='先核人物、矛盾和结果约束，再为未给的解决过程提出相容方案；未知不冒充原文事实。',
            L4='换题沿本次明确版本重核约束，不搬上一题的目标、障碍或解决过程。')
    if mid in {'G03', 'A05', 'W03'}:
        parts = method['version'].split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        method['version'] = '.'.join(parts)
        method['full']['presentation_revision'] = '2026-10-30.2'
    return method


def prepare(root=ROOT):
    root = Path(root).resolve()
    with patch('core.registry.ROOT', root):
        live = Registry(); live.validate()
        history = Registry(snapshot_commit=PREVIOUS)
    if live.index['source_baseline']['commit'] != PREVIOUS:
        raise ValueError('Migration requires the explicit previous epoch')
    if history.index != live.index or history.methods != live.methods:
        raise ValueError('Historical snapshot must preserve prior editorial state exactly')
    captured = root/'provenance/upstream-revisions'/TARGET
    manifest = json.loads((captured/'manifest.json').read_bytes())
    if (manifest['commit'], manifest['previous_runtime_commit']) != (TARGET, PREVIOUS):
        raise ValueError('Wrong captured source epoch')
    files = {}
    for row in manifest['files']:
        path = (captured/'files'/row['path']).resolve()
        if not path.is_relative_to((captured/'files').resolve()): raise ValueError('Source escaped capture')
        raw = path.read_bytes()
        if sha(raw) != row['sha256']: raise ValueError('Captured source digest mismatch')
        files[row['path']] = raw
    payload, source_sections, documents, lookup = {}, {}, [], {}
    baseline = live._load('provenance/manifest.yaml')
    next_manifest = dict(repository=manifest['repository'], commit=TARGET, files=[])
    for row in baseline['files']:
        path = row['path']; raw = files[path]
        payload['provenance/ANSWER/'+path] = raw
        next_manifest['files'].append({'path':path, 'sha256':sha(raw)})
        if not path.endswith('.md'): continue
        ids=[]
        for section in sections(raw.decode('utf-8')):
            key=(path,section['heading'])
            if key in lookup: raise ValueError('Ambiguous source heading')
            sid=sha(f"{path}:{section['line_start']-1}".encode())[:16]
            lookup[key]=sid;source_sections[sid]=dict(path=path,**section,commit=TARGET);ids.append(sid)
        documents.append({'path':path,'sha256':sha(raw),'sections':ids})
    def target_key(path, heading):return path,RENAMES.get((path,heading),heading)
    def rebind(sid):
        old=live.sources['sections'][sid]
        return lookup[target_key(old['path'],old['heading'])]
    def save(path,value):payload[path]=yaml.safe_dump(value,allow_unicode=True,sort_keys=False).encode()
    index=deepcopy(live.index)
    index['source_baseline'].update(commit=TARGET,captured_at='2026-10-30')
    index['cloze_order_source']['commit']=TARGET
    # Preserve the earliest bound production-map content; update only the
    # reviewed current endpoint, so an older supplement cannot reappear.
    supersession=deepcopy(index['reference_supersession'])
    supersession['to_commit']=TARGET
    for item in supersession['sections']:
        key=target_key(item['path'],item['heading'])
        item['after_sha256']=sha(source_sections[lookup[key]]['content'].rstrip().encode())
    index['reference_supersession']=supersession
    for row in index['course_identities']:
        source=row['source'];key=target_key(source['path'],source['heading']);s=source_sections[lookup[key]]
        row['source_heading']=key[1]
        source.update({k:s[k] for k in ('heading','commit','line_start','line_end')})
        if key==(READING,RENAMES[(READING,'中心思想（8.7讲义原名，强版本未激活）')]):
            row.update(identity_kind='bounded_course_operation',source_activation=True,
                task_scope=['text_supported_narrative_inference_not_common_sense_algorithm'])
    names=[('十二字真言','source_specific_framework'),('大小三圈','bounded_operation_group'),
        ('六类书信的本课职责','source_version_group'),('综合运用小结','source_specific_framework'),
        ('训练栏目与阶段','course_training_sequence')]
    for heading,kind in names:
        if any(row['source_heading']==heading for row in index['course_identities']):continue
        s=source_sections[lookup[(APPLICATION,heading)]]
        index['course_identities'].append(dict(source_heading=heading,identity_kind=kind,
            source_activation=True,task_scope=[],equivalent_to_existing_brand=False,
            runtime_registration='not_created_by_this_plan',
            source={k:s[k] for k in ('path','heading','commit','line_start','line_end')}))
    reviews=[]
    for path in index['method_files']:
        module=live._load(path)
        for original in module['methods']:
            method=deepcopy(original);mid=method['method_id'];changes=[]
            for sid in method['section_ids']:
                before,after=live.sources['sections'][sid],source_sections[rebind(sid)]
                if before['content']!=after['content']:
                    changes.append(dict(old_heading=before['heading'],new_heading=after['heading'],
                        before_sha256=sha(before['content'].encode()),after_sha256=sha(after['content'].encode())))
            method['section_ids']=[rebind(sid) for sid in method['section_ids']]
            for ref in method['source_references']:
                ref['heading']=target_key(ref['path'],ref['heading'])[1];ref['commit']=TARGET
            method=correct(method);index['methods'][mid]['version']=method['version']
            method['full'].update(section_ids=method['section_ids'],source_update_note=NOTES[mid[0]])
            method['static_design_review'].update(source_section_ids=method['section_ids'],status='source_bound_editorial_review')
            method['source_alignment'].update(commit=TARGET,state='live_source_bound',source_content_changed=bool(changes),
                acceptance='explicit source delta review; learner/blind/release pending')
            method['change_reason']='ANSWER 9a872ba 显式来源差异复核；旧来源归档，保基础入口与实用优先，不自动授予Case或真人准入。'
            method['student_ready']=False
            reviews.append(dict(method_id=mid,source_deltas=changes,review=NOTES[mid[0]],
                version_before=original['version'],version_after=method['version']))
            original.clear();original.update(method)
        save(path,module)
    risks=deepcopy(live._load('method-registry/source-risks.yaml'))
    for risk in risks['risks']:
        if 'section_id' in risk:risk['section_id']=rebind(risk['section_id'])
    grammar=deepcopy(live.grammar_tree);grammar['source_sections']=[rebind(sid) for sid in grammar['source_sections']]
    anti=deepcopy(live._load('method-registry/anti-rules.yaml'))
    for rule in anti['rules']:rule['source_evidence']=[rebind(sid) for sid in rule['source_evidence']]
    for path,value in [('method-registry/registry.yaml',index),('method-registry/source-risks.yaml',risks),
        ('method-registry/source-sections.yaml',dict(sections=source_sections,documents=documents)),
        ('method-registry/grammar-tree.yaml',grammar),('method-registry/anti-rules.yaml',anti),
        ('method-registry/symptom-cues.yaml',dict(routes=live.symptom_cues)),('provenance/manifest.yaml',next_manifest)]:save(path,value)
    scratch=root/'local-data/answer-alignment-20261030-latest'
    scratch.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='stage-',dir=scratch) as tmp:
        candidate_root=Path(tmp)
        for directory in ('schemas','cases'):shutil.copytree(root/directory,candidate_root/directory)
        for relative,raw in payload.items():
            dest=candidate_root/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        with patch('core.registry.ROOT',candidate_root):candidate=Registry();validation=candidate.validate()
        payload.update({path:content.encode() for path,content in build(candidate).items()})
    return payload,dict(from_commit=PREVIOUS,to_commit=TARGET,validation=validation,methods_reviewed=reviews,
        changed_source_methods=sum(bool(r['source_deltas']) for r in reviews),
        corrected_projection_methods=['G03','A05','W03'],learner_acceptance='pending',source_repository_modified=False,
        private_cases_modified=False,method_promotion_applied=False,scope='source_alignment_and_bounded_editorial_corrections')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if Registry().index['source_baseline']['commit']==TARGET:
        Registry().validate();generate(check=True);print(json.dumps(dict(status='already_source_aligned',commit=TARGET)));return
    payload,report=prepare()
    if args.apply:
        backup=Path(tempfile.mkdtemp(prefix='activation-backup-',dir=ROOT/'local-data/answer-alignment-20261030-latest'))
        journal=apply_payload(ROOT,payload,backup);Registry().validate();generate(check=True)
        report.update(status='applied',backup_directory=str(backup),asset_hashes=journal['assets'])
        path=ROOT/'provenance/runtime-alignments'/f'{TARGET}-reviewed.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'methods_reviewed','asset_hashes'}},ensure_ascii=False))


if __name__=='__main__':main()
