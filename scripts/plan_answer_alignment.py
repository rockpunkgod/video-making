"""Resolve source bindings explicitly before an atomic runtime migration.

No fuzzy heading matching, automatic algorithm activation, card rewriting or
private evidence mutation. A successful plan is not an applied migration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from core.registry import ROOT, Registry
from scripts.capture_answer_revision import private_relative, sections

TARGET = '61bc9c3e15004639cb442c20e7946ca9631f14ce'
READING = 'gaokao-english/references/reading-comprehension.md'
CLOZE = 'gaokao-english/references/cloze.md'
APPLICATION = 'gaokao-writing/references/application-writing-and-correction.md'
CONTINUATION = 'gaokao-writing/references/continuation-writing-and-correction.md'

# These are source relocations, NOT statements that the old and new names
# mean the same method. Split the conflated identities before activation.
RELOCATIONS = {
    READING: {
        '主旨缺失':['mainly题与主旨大意'],
        '跳读定位（学生常说定位阅读法）':['跳读定位'],
        '名词定出处与题文同序（学生常说顺藤摸瓜）':
            ['按题型任务分流，不按文体硬套','跳读定位'],
        'mainly题与主旨大意（学生常说中心思想）':['mainly题与主旨大意'],
        '定位后上下文核对（学生常说左顾右盼）':
            ['阅读方法适用边界','同源替换','代词指代'],
    },
    CLOZE: {'完形语篇逻辑破译':['语篇行文结构的已核验操作（内容说明，非新增方法名）']},
    APPLICATION: {
        '六步训练法':['应用文写作六步训练法通用梳理框架'],
        '三种句子生成法':['三种写作表达方法'],
        '三种句子生成法的细化':['三种写作表达方法的细化'],
        '富兰克林写作法':['富兰克林写作法（寒4五步）'],
    },
    CONTINUATION: {
        '五 润：升华主题，润色修改':['五 润：检查主题回应，润色修改'],
        '动作链与动作面（人物刻画核心）':['动作链与动作面'],
    },
    'gaokao-english/references/course-evidence.md': {
        '结构一致、七选五主语一致、七选五时态一致':
            ['结构一致','七选五主语一致','七选五时态一致'],
    },
    'gaokao-english/references/seven-five.md': {
        '共同行为、结构一致、主语一致、时态一致':
            ['结构一致','主语一致','时态一致'],
    },
    'gaokao-grammar-fill/references/grammar-fill.md': {
        '总路线、无提示词、有提示词、需要动词形式':
            ['总路线','无提示词','有提示词','需要动词形式：先判谓语还是非谓语'],
    },
}

# Exact source identities. Never turn these into aliases on another card.
IDENTITIES = [
    (READING,'定位阅读法（应用文阅读课程题名）','course_title',False,[]),
    (READING,'顺藤摸瓜（记叙文细节的原命名）','bounded_course_operation',True,['narrative_detail']),
    (READING,'左顾右盼（记叙文细节的原命名）','bounded_course_operation',True,['narrative_detail','word_meaning_context']),
    (READING,'中心思想（8.7讲义原名，强版本未激活）','unactivated_strong_definition',False,[]),
    (READING,'积极阅读法：重复定主旨','bounded_course_operation',True,['theme_framework']),
    (READING,'积极阅读法：褒贬定态度（受限作者评价观察）','bounded_course_operation',True,['author_evaluation']),
    (READING,'记叙文全文主旨／标题的受限操作','bounded_operation_group',True,['narrative_main_idea','narrative_title']),
    (READING,'褒贬一致（阅读已验受限比较判据）','comparison_criterion',True,
        ['title','paragraph_main_idea','object_evaluation','cognitive_cause','word_meaning_direction']),
    (READING,'分句结构法（原名；逻辑简化中的受限结构动作）','bounded_structure_operation',True,['complex_structure']),
    (READING,'画蛇添足（判项诊断用语）','candidate_diagnosis',False,[]),
    (READING,'mainly题与主旨大意','bounded_course_operation',True,['main_idea','paragraph_main_idea']),
    (CLOZE,'语篇行文结构的已核验操作（内容说明，非新增方法名）','internal_framework',True,['cloze']),
    (APPLICATION,'应用文写作六步训练法通用梳理框架','editorial_framework',False,[]),
    (APPLICATION,'三种写作表达方法','distinct_course_method_group',True,['application_expression']),
    (APPLICATION,'富兰克林写作法（寒4五步）','course_training_sequence',True,['application_after_class']),
    (CONTINUATION,'情节构思：PTSD 四步法','source_version_group',True,['continuation_planning']),
    (CONTINUATION,'动作链与动作面','mixed_activation_group',True,['action_chain_only']),
]


def build_plan(commit=TARGET, repo_root=ROOT):
    repo_root=Path(repo_root).resolve()
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Full lowercase upstream commit required')
    revision=repo_root/'provenance/upstream-revisions'/commit
    manifest=json.loads((revision/'manifest.json').read_bytes())
    if manifest.get('commit')!=commit:
        raise ValueError('Captured upstream identity differs')
    documents={}
    for row in manifest['files']:
        path=row['path']; raw=private_relative(revision/'files',path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Captured upstream asset changed: '+path)
        if Path(path).suffix=='.md': documents[path]=sections(raw.decode('utf-8'))
    current=Registry()
    if current.asset_root.resolve()!=repo_root:
        raise ValueError('Registry and planning root disagree')
    # Historical plans stay bound to their actual starting epoch even after
    # live rules advance again; never reinterpret an old migration from HEAD.
    registry=(current if current.index['source_baseline']['commit']==manifest['previous_runtime_commit']
              else Registry(snapshot_commit=manifest['previous_runtime_commit']))
    registry.validate()
    history=Registry(snapshot_commit=registry.index['source_baseline']['commit'])
    # Planning must start from a byte-preserved, replayable historical epoch.
    if history.index!=registry.index or history.methods!=registry.methods:
        raise ValueError('Current runtime differs from its preserved historical epoch')

    def resolve(path,heading):
        headings=RELOCATIONS.get(path,{}).get(heading,[heading])
        result=[]
        for target in headings:
            matches=[s for s in documents.get(path,[]) if s['heading']==target]
            if len(matches)!=1:
                raise ValueError('Missing or ambiguous exact target heading: '+path+' / '+target)
            result.append({'path':path,**matches[0],'commit':commit})
        return result

    methods=[]
    for mid,m in registry.methods.items():
        bindings=[]; changed=False
        for sid in m['section_ids']:
            old=registry.sources['sections'][sid]
            new=resolve(old['path'],old['heading'])
            same=len(new)==1 and old['heading']==new[0]['heading'] and old['content']==new[0]['content']
            changed=changed or not same
            bindings.append({'old_section_id':sid,'old_heading':old['heading'],
                             'state':'unchanged_section' if same else 'explicit_relocation_or_change',
                             'targets':[{k:s[k] for k in ('path','heading','line_start','line_end','commit')}
                                        for s in new]})
        references=[]
        for ref in m['source_references']:
            references.extend({k:s[k] for k in ('path','heading','line_start','line_end','commit')}
                              for s in resolve(ref['path'],ref['heading']))
        methods.append({'method_id':mid,'old_version':m['version'],
                        'source_content_changed':changed,'bindings':bindings,
                        'resolved_references':references,
                        'semantic_review':'required_before_apply',
                        'promotion':'not_authorized_by_source_alignment'})
    identities=[]
    for path,heading,kind,activated,tasks in IDENTITIES:
        source=resolve(path,heading)[0]
        identities.append({'source_heading':heading,'identity_kind':kind,
                           'source_activation':activated,'task_scope':tasks,
                           'equivalent_to_existing_brand':False,
                           'runtime_registration':'not_created_by_this_plan',
                           'source':{k:source[k] for k in ('path','heading','line_start','line_end','commit')}})
    return {'schema_version':'1.0.0','scope':'binding_plan_only',
            'runtime_migration_applied':False,'from_commit':registry.index['source_baseline']['commit'],
            'current_runtime_commit':current.index['source_baseline']['commit'],
            'to_commit':commit,'method_count':len(methods),
            'source_changed_method_count':sum(m['source_content_changed'] for m in methods),
            'methods':methods,'course_identities':identities,
            'retired_current_risks':['APPLICATION-TRAINING-WORDCOUNT-TENSION'],
            'retain_historical_risks':True,
            'release_requirement':'传播效果先验收，强可用性后验收；冲突服从正确性与可用性；本计划不算任一验收通过。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--commit',default=TARGET)
    args=parser.parse_args(); result=build_plan(args.commit)
    print(json.dumps(result,ensure_ascii=False,indent=2))
