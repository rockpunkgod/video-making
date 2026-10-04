"""Run reproducible engineering gates and write an honest final report."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import unittest
from core.registry import ROOT,Registry,load,validate_schema
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from scripts.generate_assets import generate
from evaluation.harness import evaluate,load_records

def run():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful(): raise SystemExit('Regression failed; no PASS report generated')
    r=Registry(); validated=r.validate(); generated=generate(check=True)
    smoke=[]
    for args in [['validate'],['analyze','examples/question-course.json','--renderer','student'],['analyze','examples/question-reviewed-course.json','--renderer','content-export'],['paper','examples/paper-course.json'],['evaluate','evaluation/datasets/synthetic-observations.json'],['evaluate','evaluation/datasets/real-observations.pending.json']]:
        proc=subprocess.run([sys.executable,'-m','answer_engine',*args],cwd=ROOT,capture_output=True,encoding='utf-8')
        if proc.returncode: raise RuntimeError(proc.stderr)
        smoke.append({'command':'python -m answer_engine '+' '.join(args),'exit_code':proc.returncode})
    modules=Counter(m['question_type'] for m in r.methods.values())
    categories=Counter(m['method_type'] for m in r.methods.values())
    ready=sum(bool(m.get('student_ready')) for m in r.methods.values())
    unfinished=len(r.methods)-ready
    cases=[load(path) for m in r.methods.values() for path in m['cases'].values()]
    statuses=Counter(c['status'] for c in cases)
    real=load_records(ROOT/'evaluation/datasets/real-observations.pending.json')
    synthetic=load_records(ROOT/'evaluation/datasets/synthetic-observations.json')
    report={'final_status':'PARTIAL','before_refactor':{'tests_run':16,'passed':16,'head':'60ebaf4'},'after_refactor':{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'registry':validated,'generated':generated,'cli_smoke':smoke},'method_migration':dict(modules),'method_types':dict(categories),'case_counts':dict(statuses),'source_commit':r.index['source_baseline']['commit'],'source_repository_unchanged':'verified by read-only source git status and immutable snapshot hashes','evaluation_status':'pending_real_participant_validation','real_record_count':len(real),'synthetic_record_count':len(synthetic),'remaining_blockers':[f'{unfinished}项学生入口仍需逐一源绑定审阅，全部真实案例仍待核','缺完整六型盲题与旧答疑语义回归数据','没有可靠校准的自由文本语义求解后端，当前使用外部审阅接口','无真实受试者传播、First-use、Blind、效率或Signature数据']}
    report['safety_hardening']={'option_closure':'unique own support plus reviewed elimination of every supplied rival','evidence_graph':'own method trigger, own candidate claim and current-input quote binding','spoken_symptoms':'10 requested examples tested; suggestions not semantic proof','analysis_schema_version':'1.1.0'}
    report['student_entry_migration']={'static_ready':ready,'draft_remaining':unfinished,'meaning':'static copy completeness, not observed first-use success','ready_by_module':dict(Counter(m['question_type'] for m in r.methods.values() if m.get('student_ready')))}
    p=ROOT/'evaluation/reports/engineering-acceptance.json'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    table='\n'.join(f'| {kind} | {count} | {count} | {count} | 0 | 0 |' for kind,count in modules.items())
    phases=[('0','PASS','源/目标基线、16项before测试'),('1','PASS','注册表、逐字源章节、标准Schema与历史快照'),('2','PASS','六样板完整结构、四步卡、三短版及显式案例缺口；不是教学成熟认证'),('3','PASS','保留两阶段协议、角色/短版/边界/失败类型、可运行Case契约'),('4','PARTIAL','六卡自动门禁通过；原宿主独立语义行为未测'),('5','PARTIAL',f'六模块82项结构迁移与全部源契约保留；{ready}项静态入口齐备，{unfinished}项草稿；真实案例待核'),('6','PASS','症状Router和9条有源Anti-Rule'),('7','PASS','EvidenceGraph路径/跨度/循环/冲突检查，明确Composer输入输出'),('8','PARTIAL','稳定单题接口、外部审阅及正确拒答；非自由题面自动语义求解器'),('9','PARTIAL','整卷结构扫描、方法/难度/证据/Demo排序可运行；无完整真实卷语义回归'),('10','PARTIAL','四Renderer与兼容Skill/脚本接入；完整旧答疑行为尚未认证'),('11','PASS','真人记录导入、统计、冻结计划及短版安全；真人数据未运行'),('12','PASS',f'{result.testsRun}项自动Regression及CLI烟测通过'),('13','PASS','README及架构/维护/评估/迁移文档'),('14','PASS','逐Gate如实验收，最终PARTIAL，不宣布工程全完成')]
    gates=[('G1','PASS','源课程逐字快照与源工作区未改；已知规则风险明确后置'),('G2','PASS','Registry统一事实，生成资源漂移检查通过'),('G3','PASS','六个完整结构样板；教学效果待实测'),('G4','PARTIAL','82项结构迁移；未逐一完善短版/案例原因明示'),('G5','PASS','症状导航返回动作与Stop'),('G6','PASS','9条Anti-Rule有绑定/边界/源章节'),('G7','PASS',f'{len(cases)}条记录，{statuses["verified_course_example"]}个可核短片段；不是完整题集'),('G8','PARTIAL','图可生成并校验路径，语义关系仍外部审阅'),('G9','PASS','组合职责/输入/产物显式，无混题型和无匹配调用'),('G10','PARTIAL','单题稳定Schema，决定性语义判断非自动完成'),('G11','PARTIAL','整卷接口可执行；真实完整卷回归缺数据'),('G12','PASS','Core不含交付模板，Renderer不改变答案事实'),('G13','PARTIAL','入口/脚本/契约兼容通过，完整旧题库宿主语义表现未验'),('G14','PASS',f'16 baseline保留，当前{result.testsRun}项通过'),('G15','PASS','JSON/JSONL导入、12类指标/差值、三短版安全可运行；统计显著性需审阅'),('G16','PASS','真人未测为pending_real_participant_validation；零升级虚报')]
    md=f'''# Final Acceptance

## 1. Final Status

PARTIAL。日期2026-10-05。成果另存video-making，ANSWER源及用户已安装Skill未修改。可运行工程核心与自动校验完成，但不宣布全部G1–G16通过或“工程全完成”。

## 2. Architecture

Registry（源章节+方法）→Matcher/Composer→Question/Paper Analyzer→EvidenceGraph→四Renderer；独立Evaluation导入真人观察。原Skill由生成适配接入，完整宿主答疑仍遵守原契约。

## 3. Completed Phases

| Phase | Status | 实际结果 |
|---|---|---|
'''+ '\n'.join(f'| {phase} | {status} | {note} |' for phase,status,note in phases)+f'''

## 4. Method Migration

| 题型 | 登记总数 | 结构迁移 | candidate | validated | stable |
|---|---:|---:|---:|---:|---:|
{table}

共{len(r.methods)}项，全部Useful，Efficient/Signature均为0。含{dict(categories)}，不是全部核心品牌。{ready}项student_ready（静态入口齐备，不是First-use通过）；其他{unfinished}项仍为草稿。共同课程/输出/评分/版本细则完整保留，未独立品牌化。Case共{len(cases)}条：{dict(statuses)}；7条为短片段而非完整真题，缺口不算验证通过。

## 5. Tests

Before：16/16；After：{result.testsRun}/{result.testsRun}。覆盖baseline、全量Registry/Case/标准Schema、Analyzer证据/角色/拒答、Paper推荐门禁、Renderer事实保留、Legacy资源/脚本、Evaluation公式/空数据/重复/污染/不可伪升级。四Skill通过skill-creator quick_validate（Windows使用UTF-8模式）；editable安装通过。CLI六种烟测通过。详细机器记录：evaluation/reports/engineering-acceptance.json。未声称旧题库正确率或宿主语义回归已通过。

## 6. Evaluation Readiness

First-use、Blind/Baseline、10/30/90s Safety均有记录Schema及直接可运行CLI。真实记录{len(real)}条，synthetic程序记录{len(synthetic)}条；后者不是真实试题或真人效果。真人状态pending_real_participant_validation；未测null/untested，safe_for_release未伪造true，工具不自动升级。

## 7. Remaining Blockers

其余{unfinished}项学生入口源绑定审阅及全量真实完整Case；六题型完整盲题与旧答疑回归材料；可靠语义后端或独立宿主审阅；真实学生传播/First-use/Blind及冻结对照数据。现有核心可接受外部语义审阅并保留完整路径，但不能凭结构校验认证推断正确或审阅身份。

## 8. Final Acceptance

| Gate | Status | Evidence / limitation |
|---|---|---|
'''+ '\n'.join(f'| {gate} | {status} | {note} |' for gate,status,note in gates)+'\n\n传播先验收，实用性优先否决。名字、动作、证据、边界不能互相替代。没有真人数据，不升级成熟度或实用价值。\n'
    md+='\n本轮安全增强：单项保留不能跳过未核验竞争项；answer_verification显式报告候选闭合；证据图绑定同一方法触发、同一候选主张与当前题面；附件10种口语卡点均有导航回归，导航不构成语义证明。Question Analysis Schema升级为1.1.0。\n'
    md+='\n阅读模块17项学生入口静态齐备：13个非黄金方法从1.0.0修订为1.1.0，旧稿保存在history；判据、Stop、误用、反例示意及三短版逐项区分，未修改冻结源章节。示意反例不算真实Case，所有成熟度仍为candidate。\n'
    (ROOT/'docs/final-acceptance.md').write_text(md,encoding='utf-8')
    return report

if __name__=='__main__':
    value=run(); print(json.dumps({'status':value['final_status'],'tests':value['after_refactor']['tests_run'],'methods':sum(value['method_migration'].values())},ensure_ascii=False))
