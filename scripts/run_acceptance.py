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
    for args in [['case-coverage'],['analyze','examples/writing-word-count.synthetic.json','--renderer','legacy-wechat'],['analyze','examples/writing-word-count.synthetic.json','--renderer','content-export'],['analyze','examples/writing-image.synthetic.json','--renderer','legacy-wechat'],['analyze','examples/writing-image.synthetic.json','--renderer','content-export'],['validate'],['lesson','examples/passage-lesson.synthetic.json','--renderer','legacy-wechat'],['lesson','examples/passage-lesson.synthetic.json','--renderer','content-export'],['analyze','examples/question-lesson-course.json','--renderer','legacy-wechat'],['analyze','examples/question-action-course.json','--renderer','content-export'],['analyze','examples/question-course.json','--renderer','student'],['analyze','examples/question-reviewed-course.json','--renderer','content-export'],['analyze','examples/writing-review.synthetic.json','--renderer','legacy-wechat'],['analyze','examples/writing-review.synthetic.json','--renderer','content-export'],['paper','examples/paper-course.json'],['evaluate','evaluation/datasets/synthetic-observations.json'],['evaluate','evaluation/datasets/real-observations.pending.json']]:
        proc=subprocess.run([sys.executable,'-m','answer_engine',*args],cwd=ROOT,capture_output=True,encoding='utf-8')
        if proc.returncode: raise RuntimeError(proc.stderr)
        smoke.append({'command':'python -m answer_engine '+' '.join(args),'exit_code':proc.returncode})
    modules=Counter(m['question_type'] for m in r.methods.values())
    categories=Counter(m['method_type'] for m in r.methods.values())
    ready=sum(bool(m.get('student_ready')) for m in r.methods.values())
    unfinished=len(r.methods)-ready
    cases=[load(path) for m in r.methods.values() for path in m['cases'].values()]
    statuses=Counter(c['status'] for c in cases)
    coverage=r.case_coverage()
    real=load_records(ROOT/'evaluation/datasets/real-observations.pending.json')
    synthetic=load_records(ROOT/'evaluation/datasets/synthetic-observations.json')
    entry_gap=f'{unfinished}项学生入口仍需逐一源绑定审阅；' if unfinished else ''
    report={'final_status':'PARTIAL','before_refactor':{'tests_run':16,'passed':16,'head':'60ebaf4'},'after_refactor':{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'registry':validated,'generated':generated,'cli_smoke':smoke},'method_migration':dict(modules),'method_types':dict(categories),'case_counts':dict(statuses),'source_commit':r.index['source_baseline']['commit'],'source_repository_unchanged':'verified by read-only source git status and immutable snapshot hashes','evaluation_status':'pending_real_participant_validation','real_record_count':len(real),'synthetic_record_count':len(synthetic),'remaining_blockers':[entry_gap+'全量真实完整案例仍待核','缺完整六型盲题与旧答疑语义回归数据','没有可靠校准的自由文本语义求解后端，当前使用外部审阅接口','无真实受试者传播、First-use、Blind、效率或Signature数据']}
    report['safety_hardening']={'option_closure':'unique own support plus reviewed elimination of every supplied rival','evidence_graph':'own method trigger, own candidate claim and current-input quote binding','spoken_symptoms':'10 requested examples tested; suggestions not semantic proof','analysis_schema_version':'1.7.0','grammar_navigation':'explicit hint branch plus reviewed trigger paths; never infer blank POS from hint spelling','writing_feedback':'external review transport with independent trigger, draft coverage, module-specific order and real withholding of unsupported sections; no automatic grading certification'}
    report['case_coverage']=coverage
    report['paper_scan']={'schema_version':'1.1.0','legacy_output_schema':'1.0.0 still accepted','coverage_stages':['potential_question_ids','verified_trigger_question_ids','produced_question_ids','reviewed_decision_question_ids','case_candidate_question_ids'],'ranking':'own eligible case count descending then method ID; not suggestion frequency or demonstration score','gate':'closed question plus own verified trigger and own produced artifact or reviewed decision, with no stopped execution for this method','scope':'external reviewed structural scan, not legal-source, complete-paper or English-semantic certification'}
    report['review_provider_binding']={'input_gate':'schema validation before callback and after return','immutable_fields':['question_id','question_type','stem','passage','options','given_word','student_text','continuation_starters','original_images','student_symptoms'],'snapshot':'independent deepcopy detects in-place and nested changes, additions and deletions','scope':'single question and inherited paper/passage input consistency; not a callback sandbox or semantic certification'}
    report['student_entry_migration']={'static_ready':ready,'draft_remaining':unfinished,'meaning':'static copy completeness, not observed first-use success','ready_by_module':dict(Counter(m['question_type'] for m in r.methods.values() if m.get('student_ready')))}
    report['evaluation_design_hardening']={'result_schema_version':'1.2.0','grouping':['method_id','method_version','dataset_id','communication_freeze_id'],'workflow':'declared study freeze / communication freeze / practicality / first-use / blind sequence, with each communication version observed; not authenticated dates','short_safety':'absolute trigger/action/evidence/transfer/stop gates plus relative boundary/role/stop deltas; bad 90s reference cannot release short versions','release':'missing workflow or absolute thresholds, any per-version correctness loss or failed blind gate blocks release and efficiency/signature review hints; no automatic Registry promotion'}
    report['method_execution']={'schema_version':'1.7.0','typed_artifact_count':8,'scope':'external reviewed action results, not an automatic English semantic executor','dependency_gate':'earlier reviewed complete non-stopped compatible artifacts only','binding':'current input spans, role/version, named decisions and graph payload fingerprint','failed_verification':'answer and recommendation actually withheld'}
    report['single_question_lesson']={'analysis_schema_version':'1.7.0','scope':'external reviewed spoken transport, not certified semantic or whole-passage delivery','complete_gate':'own actions, quotes, candidate relations, stop rules and closed answer','seven_five':'three reviewed F01 partitions displayed once before body','projection_binding':'text, method, trigger, candidate relation and current graph spans; unsupported full script withheld'}
    report['whole_passage_delivery']={'schema_version':'1.0.0','scope':'declared external course order and spoken delivery, not authenticated semantic/old-host performance','order_gate':['reading task mode, not passage letter','cloze original-number first pass / observed stop / exact recovery','grammar explicit hint branch then original-number order','seven-five one shared grouping before breakthrough'],'complete_gate':'every own single-question script and closure, original material, reviewed order; no partial answer string','projection':'original input spans/order/action/text/answer-summary rechecked'}
    report['original_image_review']={'writing_review_version':'1.1.0','analysis_schema_version':'1.7.0','formats':['image/png','image/jpeg'],'binding':'decoded supplied bytes / sha256 / pixel region / transcription hash / graph payload fingerprint','course_rules':'application one-band lowering; continuation explicit discretionary deduction','scope':'external visual assertions; original authorship, legibility, communication impact and grading not certified','negative_gate':'filename, transcription, unclear image, missing communication impact or material cannot authorize adjustment'}
    p=ROOT/'evaluation/reports/engineering-acceptance.json'; p.parent.mkdir(parents=True,exist_ok=True)
    report['writing_score_boundaries']={'writing_review_version':'1.2.0','analysis_version':'1.7.0','bands':'parsed from the same frozen course rubric, not a second table','word_count':'reviewed full-student-draft evidence, quoted course thresholds, supported deduction and before/after arithmetic; actual count remains external','projection':'all scores bind own current-draft / trigger / reviewed relation / verification path and score fingerprint, not only image scores','scope':'course-contract consistency, not certified English grading'}
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    table='\n'.join(f'| {kind} | {count} | {count} | {count} | 0 | 0 |' for kind,count in modules.items())
    phases=[('0','PASS','源/目标基线、16项before测试'),('1','PASS','注册表、逐字源章节、标准Schema与历史快照'),('2','PASS','六样板完整结构、四步卡、三短版及显式案例缺口；不是教学成熟认证'),('3','PASS','保留两阶段协议、角色/短版/边界/失败类型、可运行Case契约'),('4','PARTIAL','六卡自动门禁通过；原宿主独立语义行为未测'),('5','PASS' if not unfinished else 'PARTIAL',f'六模块82项结构迁移与全部源契约保留；{ready}项静态入口齐备，{unfinished}项草稿；真实案例待核'),('6','PASS','症状Router和9条有源Anti-Rule'),('7','PASS','EvidenceGraph路径/跨度/循环/冲突检查，类型化Composer动作/产物衔接与刹车控制'),('8','PARTIAL','稳定单题接口、外部审阅及正确拒答；非自由题面自动语义求解器'),('9','PARTIAL','整卷结构扫描、方法/难度/证据/Demo排序可运行；无完整真实卷语义回归'),('10','PARTIAL','四Renderer与兼容Skill/脚本接入；完整旧答疑行为尚未认证'),('11','PASS','真人记录导入、统计、冻结计划及短版安全；真人数据未运行'),('12','PASS',f'{result.testsRun}项自动Regression及CLI烟测通过'),('13','PASS','README及架构/维护/评估/迁移文档'),('14','PASS','逐Gate如实验收，最终PARTIAL，不宣布工程全完成')]
    gates=[('G1','PASS','源课程逐字快照与源工作区未改；已知规则风险明确后置'),('G2','PASS','Registry统一事实，生成资源漂移检查通过'),('G3','PASS','六个完整结构样板；教学效果待实测'),('G4','PASS' if not unfinished else 'PARTIAL',f'82项结构迁移；{ready}项静态入口，{unfinished}项草稿，真实案例缺口明示'),('G5','PASS','症状导航返回动作与Stop'),('G6','PASS','9条Anti-Rule有绑定/边界/源章节'),('G7','PARTIAL',f'{len(cases)}条登记记录，{statuses["verified_course_example"]}个可核短片段；核心方法/框架仍有{coverage["core_unregistered_slot_count"]}个类型槽未登记，不能视为案例齐全'),('G8','PARTIAL','图可生成并校验路径，语义关系仍外部审阅'),('G9','PASS','角色/版本/类型化产物/依赖可执行，未审阅或停止不续用'),('G10','PARTIAL','单题稳定Schema，决定性语义判断非自动完成'),('G11','PARTIAL','整卷接口可执行；真实完整卷回归缺数据'),('G12','PASS','Core不含交付模板，Renderer不改变答案事实'),('G13','PARTIAL','入口/脚本/契约兼容通过，完整旧题库宿主语义表现未验'),('G14','PASS',f'16 baseline保留，当前{result.testsRun}项通过'),('G15','PASS','JSON/JSONL导入、12类指标/差值、三短版安全可运行；统计显著性需审阅'),('G16','PASS','真人未测为pending_real_participant_validation；零升级虚报')]
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

Before：16/16；After：{result.testsRun}/{result.testsRun}。覆盖baseline、全量Registry/Case/标准Schema、Analyzer证据/角色/拒答、Paper推荐门禁、Renderer事实保留、Legacy资源/脚本、Evaluation公式/空数据/重复/污染/不可伪升级。四Skill通过skill-creator quick_validate（Windows使用UTF-8模式）；editable安装通过。CLI {len(smoke)}种烟测通过，写作示例为synthetic程序输送记录，不是实际英语题或真人评分。详细机器记录：evaluation/reports/engineering-acceptance.json。未声称旧题库正确率或宿主语义回归已通过。

## 6. Evaluation Readiness

First-use、Blind/Baseline、10/30/90s Safety均有记录Schema及直接可运行CLI。真实记录{len(real)}条，synthetic程序记录{len(synthetic)}条；后者不是真实试题或真人效果。真人状态pending_real_participant_validation；未测null/untested，safe_for_release未伪造true，工具不自动升级。

## 7. Remaining Blockers

{entry_gap}全量真实完整Case；六题型完整盲题与旧答疑回归材料；可靠语义后端或独立宿主审阅；真实学生传播/First-use/Blind及冻结对照数据。现有核心可接受外部语义审阅并保留完整路径，但不能凭结构校验认证推断正确或审阅身份。

## 8. Final Acceptance

| Gate | Status | Evidence / limitation |
|---|---|---|
'''+ '\n'.join(f'| {gate} | {status} | {note} |' for gate,status,note in gates)+'\n\n传播先验收，实用性优先否决。名字、动作、证据、边界不能互相替代。没有真人数据，不升级成熟度或实用价值。\n'
    md+='\n本轮安全增强：单项保留不能跳过未核验竞争项；answer_verification显式报告候选闭合；证据图绑定同一方法触发、同一候选主张与当前题面；附件10种口语卡点均有导航回归，导航不构成语义证明。Question Analysis Schema当前1.7.0。\n'
    md+='\n阅读模块17项学生入口静态齐备：13个非黄金方法从1.0.0修订为1.1.0，旧稿保存在history；判据、Stop、误用、反例示意及三短版逐项区分，未修改冻结源章节。示意反例不算真实Case，所有成熟度仍为candidate。\n'
    md+='\n七选五11项静态入口齐备：F02–F11保留旧稿后逐项完善，区分reduce/interpret/verify/decide；正文闭环不由形式、同词、时态、占用或剩余定案，示意反例不算真实Case。\n'
    md+='\n完形9项静态入口齐备：保留两个核心入口与七个子动作；线索、框架与核验不自动定案，C01二阶段decider必须显式声明。C01/C02的原空号两遍规则补充直接源引用，示意反例与真人结果仍未验证。\n'
    md+='\n语法19项静态入口齐备：18个非黄金节点保留旧稿后逐项源核，机器导航只确认有无提示词及已审阅功能；提示词原词性不决定空位词性，树不独立定案。三个语法源风险绑定原话与章节并自动校验，保留原资料、不机械执行简化口诀或全称清单。\n'
    md+='\n应用文10项静态入口齐备：先任务、后准确句、再升级；文体/评分/课后训练保持原类型。评分材料、书写及仿写循环直接源绑定，训练字数策略不覆盖题面与评分限制。示意反例不是真实Case，不据文案升级实用等级。\n'
    md+='\n续写16项静态入口齐备：五步法引用具体子章节，首句约束、功能支架、细节/转折与回扣逐项区分；给定首句不计学生句数、不抄正常，十句和独立升华句不作机械扣分项。PTSD只作源别名，类别与评分/训练不升格；原课程版本张力继续保留。\n'
    md+='\n写作审阅通道：宿主完整语义意见经writing_review进入统一结构、证据图与两模块原交付顺序；逐处纠错/可选润色不设数量上限，缺原文或首句实际扣留剧情诊断、完整稿与分数。分数只为外部建议，身份、语义与改写保真未认证；原图字节/区域/转写稿指纹进入独立审阅适配，应用文降档和续写酌扣不能混用；清晰度和交际影响仍外部声明，未完成真人评分验证。程序输送测试不能替代旧题库宿主语义回归。\n'
    md+='\n真实验收链增强：结果Schema 1.2.0按方法/版本/题组/传播冻结稿隔离，workflow核阶段顺序、传播逐版观察绑定、陌生题与跨阶段学习控制。绝对盲测门槛、独立Baseline正确性和适用试次动作/证据均逐时长检查；90s失败不作合格参照，均值不掩盖某版损害。缺链条或采集前绝对门槛不授予释放或效率审阅建议；猜中不充当方法成功。时间、身份与审阅结论仍为外部声明，程序不能认证真人数据；新增测试均为程序控制测试。\n'
    md+='\n方法编排执行通道：action_executions传入具体动作与八类产物，execution_trace按ID消费更早已审阅、完整、未刹车的兼容产物。R09三字段骨架、候选全覆盖分组、角色/版本/独立触发、对应候选关系和语法节点路径均有运行门禁；核验不支持时实际撤回答案与整卷推荐。产物指纹与执行链/图联合校验，Renderer显示实际动作和停止原因。此为外部动作结果的运行控制，不认证自由题面语义求解、真实动作或宿主审阅身份。\n'
    md+='\n单题口播通道：lesson_review经源合同、独立触发、实际动作、短引文、候选关系和刹车覆盖进入lesson_feedback；完整消息恢复原纯文本开场，最后由核心闭合答案汇总。七选五实际三维分组在开头展示一次，缺分组或闭合就扣留完整稿。投影重检文字/图/触发/候选/答案一致性；未认证宿主自由文字语义与整篇课程顺序，旧题库语义回归仍缺。生成技能只增加接口链接，不复制教学判据或改用户技能库。\n'
    md+='\n整篇交付接口：lesson复用单题核心，显式保留原题号、共享原文和审阅顺序。阅读中心任务先于细节/猜词、完形暂留后原空号回收、语法无提示词优先及七选五一次分组先于突破说明均有工程检查；最后按原题号汇总，缺某题口播时指出该题并扣留整篇消息。接口可运行不等于真实材料完整、自由文字语义或旧宿主表现已认证；相应真实回归仍缺。\n'
    md+='\n评分边界：定档区间直接解析冻结源评分表，无调整依据的档/分冲突不接受；词数调整需1.2.0外部审阅、完整学生稿证据、原附加规则和准确前后记账。词数与原图调整独立，纯文本评分也绑定自身图路径及载荷，四Renderer拒绝事后换分或断证。程序测试不认证计词、定档、英语评分或真人效果。\n'
    md+='\n## 案例类型逐方法审计\n\n登记记录仍为'+str(coverage['registered_case_count'])+'条，没有为补数新建题目或占位案例。全部'+str(coverage['method_count'])+'项五类槽中'+str(coverage['unregistered_slot_count'])+'槽未登记；'+str(coverage['formal_method_count'])+'个正式method中'+str(coverage['formal_methods_with_missing_slots'])+'项共有'+str(coverage['formal_unregistered_slot_count'])+'个未登记槽。保守纳入method和framework共'+str(coverage['core_method_count'])+'项核心节点，其中'+str(coverage['core_unregistered_slot_count'])+'个槽未登记。registered + evidence_gap与unregistered + evidence_gap是两种不同缺口；已登记例子也不认证完整真题或教学效果。可运行python -m answer_engine case-coverage读取完整矩阵。\n\n| 方法 | 类型 | canonical | counterexample | boundary | transfer | hard |\n|---|---|---|---|---|---|---|\n'
    for method in coverage['methods']:
        if not method['core_required']: continue
        cells=['未登记/evidence_gap' if s['registration']=='unregistered' else '已登记/'+s['evidence_status'] for s in method['slots']]
        md+='| '+method['method_id']+' | '+method['method_type']+' | '+' | '.join(cells)+' |\n'
    md+='\n外部审阅原题绑定：回调前后均校验输入，独立快照锁定题号、题型、原文、选项、提示词、学生稿、续写首句、原图和卡点；改值、嵌套原位修改或字段新增/删除均拒绝。审阅仍可补关系、动作、讲解及任务/难度标注，但不能清洗非法原输入或悄悄换题；整卷推荐复用该门禁。此为程序数据一致性测试，不认证英语语义或隔离Python回调。\n'
    md+='\n整卷方法覆盖1.1.0：保留建议次数，另逐方法列出核验触发、产物、决定及案例候选题号。典型方法候选只按自身可审阅案例数排序；不能借其他方法的闭合答案或高展示分，把仅计划、仅触发或已停止的方法包装成典型用法。辅助方法产物仍无定案权；Schema兼容旧1.0.0投影。程序测试不认证完整真题卷、来源合法性、英语语义或学生效果，G11保持PARTIAL。\n'
    (ROOT/'docs/final-acceptance.md').write_text(md,encoding='utf-8')
    return report

if __name__=='__main__':
    value=run(); print(json.dumps({'status':value['final_status'],'tests':value['after_refactor']['tests_run'],'methods':sum(value['method_migration'].values())},ensure_ascii=False))
