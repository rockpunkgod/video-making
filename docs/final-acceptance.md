# Final Acceptance

## 当前来源版本检查点（2026-10-13）

当前结论仍为 **PARTIAL**，工程完成未获证明。正式来源为 ANSWER `61bc9c3e15004639cb442c20e7946ca9631f14ce`；此前版本的入口齐备、方法分类、案例覆盖和回归数字不能作为本版验收证据。下文原报告及追加记录保留为历史时点，不改写原冻结观察。

来源更新保留 82 个方法 ID，51 张卡片更新来源相关动作与边界。当前仅 29 个入口保留静态齐备标记；6 个重点入口为独立首次接触草稿，另 47 个入口扣留旧稿、等待新版复核。不能继续引用历史“82 项 student_ready、0 项草稿”的结论。R06 现为内部诊断规则，R17 为核验规则；不能沿用历史分类表。

当前自动检查入口：`python -m scripts.audit_student_entries`。可加 `--output evaluation/reports/current-student-entry-audit.json` 保存逐方法检查结果。该工具检查实际 Registry、生成学生稿、四步字段、版本及来源绑定，不判断英文语义正确、短稿实际时长或学生掌握情况。六个重点入口字段齐备也不能自动解除草稿状态。

本版来源、Registry 及生成资产校验通过。2026-10-13 对齐提交的工作区全量回归为 1379 项，0 失败、0 错误；隔离导出的交付副本另有 86 项关键回归通过。这两项属于工程控制证据，不能计成新版 Blind 样本、学生 First-use 或效率证明。原有公开课程例和 22 个私人 Case 保留原版来源与观察，不自动填入新版发布槽。

当前优先缺口：逐项复核六个重点入口与新版 full 的一致性；配齐完整真实示范和第二道陌生题；实测短稿时长；随后按传播→冻结→强可用性顺序收集真实参与者数据。其他受影响方法须逐题型完成新版学生入口，不得以本检查点代替施工。全部方法仍 candidate；真人状态为 `pending_real_participant_validation`，没有升级 Efficient 或 Signature。

本检查点修复 Schema 生成器遗漏新版复核状态的问题，并添加生成契约与当前卡片一致性测试。相关 46 项回归通过，当前 Registry/生成资产校验通过；这不是本检查点新增功能后的全量回归结果。另实际导出 F01 私有首用材料草稿，以已有湖北圆创题面示范三维标记，以另一篇既有材料作第二任务；不复制历史审阅为新版标准，不揭露第二题的预期组别，不新增 Case 或 Blind 计数。示范仍为 AI 草稿，独立英语语义复核和参与者陌生性尚未认证，采集许可为 false，观察字段全 null。

后续推进：F01 材料升级为题面指纹锁定稿；新增 R09 私有练习，以湖北圆创纳米薄膜全文展示实际题干/选项→有效首尾→中间展开→全文骨架，再用另一篇既有主旨题测迁移动作。只产出骨架，不凭框架报答案，保留潜力、耐久退化和机械破坏的限定。两份材料的来源/学生稿/教学版本一致性复核通过；相关 37 项回归通过，Registry 和生成资产仍通过。尚未独立认证这些 AI 示范的英语语义，更未取得学生测试结果。导出器现在拒绝缺失选项和同题号换题面，检测原题、学生稿以及同版本四步卡变更，不能以哈希检查代替真实研究。

再追加 R06 私有首用草稿：在已有自然活动文章的正文核心成立后，比候选的对象及完整判断，展示“更多空闲时间”与“从屏幕走向自然”的核心关系差异；第二题换成猫行为的另一篇标题题。只诊断候选覆盖，不把没原词当缺块，也不借此选择剩余项。三方法材料均留空真实观察、保持采集许可 false；新增正式案例和 Blind 计数为 0。R01、R02、G01 的同等材料尚未完成，三份 AI 草稿也不能替代六样板静态语义复核或真人验收。

最新推进：六个重点方法均已有私有首用材料草稿，当前选择由 `local-data/first-use-materials-61bc9c3/CURRENT_DRAFTS.json` 标明，历史草稿保留但不作为当前入口。G01 修复提示词字段遗漏，实际展示决策树并保留到节点停止；R01 用原广告的“额外付费”核新增“免费”限定，第二题换成另一篇租赁广告；R02 正例用学生→创作→人物的真实关系，边界任务另核地区及愿望/事实。原 R02 请求示范因跨地区不可比被撤下，不作为同主体正例；2021 年旧题稿缺句，未靠记忆补齐或纳为完整示范。

六份当前材料的数据一致性复核通过，相关 42 项自动回归通过，Registry/生成资产仍通过。六份草稿不是六个通过验收的方法，更不是六个新增 Case：独立当前来源语义复核、完整研究采集计划与真实观察仍缺。所有观察槽为 null，采集许可 false，正式案例和 Blind 新增计数均为 0；student_ready 数量及成熟度/实用等级没有变化。

后续全量回归：提交 `2c64f2a` 的 1405 项通过，0 失败、0 错误。此结果先于下一项草稿修订，不作为修订后的全量证明。F01 挑战曾错误要求每题指出一个无区分度维度，现按课程原文改为条件式任务；90 秒稿同步修改，旧完整卡保存在 `provenance/student-entry-revisions/F01-1.2.0-before-conditional-challenge.json`。核心触发、动作、判断、Stop、职责和方法版本保持不变，仅修订尚未冻结的传播草稿。相关 98 项回归通过；新旧字段对照有专门测试。首用材料现在同时绑定挑战文案；六份未采集草稿重导为挑战绑定 v2，旧稿和旧索引保留。冻结素材的当前状态检查也纳入短稿、实战卡、挑战、视觉式和入口文案，同版本学生指令变化会扣留旧素材，不改历史动作或观察。不据此认证教学效果或升级方法等级。

学生卡点入口推进：`symptom --renderer student` 直接给一个可能入口的第一刀、产物/判断及完整 Stop，泛说不会或多种卡点竞争时先澄清，不发方法菜单。补齐看不懂长句等自然词序；有限明确否定不当正向卡点，不是A就是B仍视为竞争而非否定。保留原结构化列表默认行为与题面观察的独立核对，症状命中仍为低置信度建议。长句场景不把阶段/持续分支强塞第一刀，G01 的减范围产物明确是知识节点而非选项答案。相关 135 项核心/动作/讲解回归通过；新增入口及 Registry 校验另行通过。未宣称自然语言全覆盖、真实 Trigger Precision 或学生学习效果，当前状态仍 PARTIAL。

### 当前 Gate 差异

再验收推进：湖北圆创三道既有题的 G01/R09/F01 新版动作经另一 AI 卷审阅者核原 PDF、当前来源、角色、Stop、图及重放，登记为独立的新版本记录，当前目录第 25 版，旧 22 个记录保留。新增独立题目和 Blind 样本为 0。三个动作分别仅输出路线、骨架、完整分组，不报答案。F01 boundary 仅覆盖时间轴无区分度后的局部停止筛选，不冒称整个方法停机。47 个非听力任务已完成新版结构回放并接入这三个动作，44 个仍待当前语义复核；20 道听力只有来源记录。原题不改，旧语义断言不自动继承，未标注对照不是学生 Baseline，整卷仍 PARTIAL。新增准备/回放入口及窄化分组选项证据限制的控制通过，不据此升级成熟度或效率等级。

当前案例版本检查：22 个已登记私有案例的历史完整性通过，22 个旧请求均未通过当前 Registry 的版本绑定准入。只读工具 `scripts.audit_real_case_epoch` 保留历史动作与目录，列出当前动作和重新审阅要求，不迁移版本或增加覆盖。湖北圆创 Q62 另存一份 G01 当前来源动作；原题面一致、旧动作哈希未变、分析重放一致、四输出模式通过，产物仅为路线节点且答案为空。这是揭答后 AI 重建，不构成独立语义认证或新 Case/Blind 计数。远端 ANSWER HEAD 再次核对为 `61bc9c3`，未修改原仓库。

G3 为 PARTIAL：六个结构草稿存在，当前来源下的完整学生样板复核尚未完成。G4 为 PARTIAL：来源重绑定已完成，但 53 个学生入口尚未重新就绪。G7/G8/G11 继续 PARTIAL：历史案例、合法证据路径或机械整卷回归不证明当前版本的完整真实语义覆盖。G14 的自动控制回归通过不抵消这些缺口。G16 保留真实验收未完成标记。未在此重新逐项核验的 Gate 不因旧报告 PASS 自动获得新版认证。

## 历史基线报告（2026-10-05，非当前验收）

## 1. Final Status

PARTIAL。日期2026-10-05。成果另存video-making，ANSWER源及用户已安装Skill未修改。可运行工程核心与自动校验完成，但不宣布全部G1–G16通过或“工程全完成”。

## 2. Architecture

Registry（源章节+方法）→Matcher/Composer→Question/Paper Analyzer→EvidenceGraph→四Renderer；独立Evaluation导入真人观察。原Skill由生成适配接入，完整宿主答疑仍遵守原契约。

## 3. Completed Phases

| Phase | Status | 实际结果 |
|---|---|---|
| 0 | PASS | 源/目标基线、16项before测试 |
| 1 | PASS | 注册表、逐字源章节、标准Schema与历史快照 |
| 2 | PASS | 六样板完整结构、四步卡、三短版及显式案例缺口；不是教学成熟认证 |
| 3 | PASS | 保留两阶段协议、角色/短版/边界/失败类型、可运行Case契约 |
| 4 | PARTIAL | 六卡自动门禁通过；原宿主独立语义行为未测 |
| 5 | PASS | 六模块82项结构迁移与全部源契约保留；82项静态入口齐备，0项草稿；真实案例待核 |
| 6 | PASS | 症状Router和9条有源Anti-Rule |
| 7 | PASS | EvidenceGraph路径/跨度/循环/冲突检查，类型化Composer动作/产物衔接与刹车控制 |
| 8 | PARTIAL | 稳定单题接口、外部审阅及正确拒答；非自由题面自动语义求解器 |
| 9 | PARTIAL | 整卷结构扫描、方法/难度/证据/Demo排序可运行；无完整真实卷语义回归 |
| 10 | PARTIAL | 四Renderer与兼容Skill/脚本接入；完整旧答疑行为尚未认证 |
| 11 | PASS | 真人记录导入、统计、冻结计划及短版安全；真人数据未运行 |
| 12 | PASS | 375项自动Regression及CLI烟测通过 |
| 13 | PASS | README及架构/维护/评估/迁移文档 |
| 14 | PASS | 逐Gate如实验收，最终PARTIAL，不宣布工程全完成 |

## 4. Method Migration

| 题型 | 登记总数 | 结构迁移 | candidate | validated | stable |
|---|---:|---:|---:|---:|---:|
| 阅读理解 | 17 | 17 | 17 | 0 | 0 |
| 七选五 | 11 | 11 | 11 | 0 | 0 |
| 完形填空 | 9 | 9 | 9 | 0 | 0 |
| 语法填空 | 19 | 19 | 19 | 0 | 0 |
| 应用文 | 10 | 10 | 10 | 0 | 0 |
| 读后续写 | 16 | 16 | 16 | 0 | 0 |

共82项，全部Useful，Efficient/Signature均为0。含{'method': 30, 'framework': 12, 'sub_action': 27, 'verification_rule': 3, 'internal_rule': 8, 'category': 2}，不是全部核心品牌。82项student_ready（静态入口齐备，不是First-use通过）；其他0项仍为草稿。共同课程/输出/评分/版本细则完整保留，未独立品牌化。Case共106条：{'evidence_gap': 90, 'source_pattern_only': 9, 'verified_course_example': 7}；7条为短片段而非完整真题，缺口不算验证通过。

## 5. Tests

Before：16/16；After：375/375。覆盖baseline、全量Registry/Case/标准Schema、Analyzer证据/角色/拒答、Paper推荐门禁、Renderer事实保留、Legacy资源/脚本、Evaluation公式/空数据/重复/污染/不可伪升级。四Skill通过skill-creator quick_validate（Windows使用UTF-8模式）；editable安装通过。CLI 19种烟测通过，写作示例为synthetic程序输送记录，不是实际英语题或真人评分。详细机器记录：evaluation/reports/engineering-acceptance.json。未声称旧题库正确率或宿主语义回归已通过。

## 6. Evaluation Readiness

First-use、Blind/Baseline、10/30/90s Safety均有记录Schema及直接可运行CLI。真实记录0条，synthetic程序记录15条；后者不是真实试题或真人效果。真人状态pending_real_participant_validation；未测null/untested，safe_for_release未伪造true，工具不自动升级。

## 7. Remaining Blockers

全量真实完整Case；六题型完整盲题与旧答疑回归材料；可靠语义后端或独立宿主审阅；真实学生传播/First-use/Blind及冻结对照数据。现有核心可接受外部语义审阅并保留完整路径，但不能凭结构校验认证推断正确或审阅身份。

## 8. Final Acceptance

| Gate | Status | Evidence / limitation |
|---|---|---|
| G1 | PASS | 源课程逐字快照与源工作区未改；已知规则风险明确后置 |
| G2 | PASS | Registry统一事实，生成资源漂移检查通过 |
| G3 | PASS | 六个完整结构样板；教学效果待实测 |
| G4 | PASS | 82项结构迁移；82项静态入口，0项草稿，真实案例缺口明示 |
| G5 | PASS | 症状导航返回动作与Stop |
| G6 | PASS | 9条Anti-Rule有绑定/边界/源章节 |
| G7 | PARTIAL | 106条登记记录，7个可核短片段；核心方法/框架仍有144个类型槽未登记，不能视为案例齐全 |
| G8 | PARTIAL | 图可生成并校验路径，语义关系仍外部审阅 |
| G9 | PASS | 角色/版本/类型化产物/依赖可执行，未审阅或停止不续用 |
| G10 | PARTIAL | 单题稳定Schema，决定性语义判断非自动完成 |
| G11 | PARTIAL | 整卷接口可执行；真实完整卷回归缺数据 |
| G12 | PASS | Core不含交付模板，Renderer不改变答案事实 |
| G13 | PARTIAL | 入口/脚本/契约兼容通过，完整旧题库宿主语义表现未验 |
| G14 | PASS | 16 baseline保留，当前375项通过 |
| G15 | PASS | JSON/JSONL导入、12类指标/差值、三短版安全可运行；统计显著性需审阅 |
| G16 | PASS | 真人未测为pending_real_participant_validation；零升级虚报 |

传播先验收，实用性优先否决。名字、动作、证据、边界不能互相替代。没有真人数据，不升级成熟度或实用价值。

本轮安全增强：单项保留不能跳过未核验竞争项；answer_verification显式报告候选闭合；证据图绑定同一方法触发、同一候选主张与当前题面；附件10种口语卡点均有导航回归，导航不构成语义证明。Question Analysis Schema当前1.7.0。

阅读模块17项学生入口静态齐备：13个非黄金方法从1.0.0修订为1.1.0，旧稿保存在history；判据、Stop、误用、反例示意及三短版逐项区分，未修改冻结源章节。示意反例不算真实Case，所有成熟度仍为candidate。

七选五11项静态入口齐备：F02–F11保留旧稿后逐项完善，区分reduce/interpret/verify/decide；正文闭环不由形式、同词、时态、占用或剩余定案，示意反例不算真实Case。

完形9项静态入口齐备：保留两个核心入口与七个子动作；线索、框架与核验不自动定案，C01二阶段decider必须显式声明。C01/C02的原空号两遍规则补充直接源引用，示意反例与真人结果仍未验证。

语法19项静态入口齐备：18个非黄金节点保留旧稿后逐项源核，机器导航只确认有无提示词及已审阅功能；提示词原词性不决定空位词性，树不独立定案。三个语法源风险绑定原话与章节并自动校验，保留原资料、不机械执行简化口诀或全称清单。

应用文10项静态入口齐备：先任务、后准确句、再升级；文体/评分/课后训练保持原类型。评分材料、书写及仿写循环直接源绑定，训练字数策略不覆盖题面与评分限制。示意反例不是真实Case，不据文案升级实用等级。

续写16项静态入口齐备：五步法引用具体子章节，首句约束、功能支架、细节/转折与回扣逐项区分；给定首句不计学生句数、不抄正常，十句和独立升华句不作机械扣分项。PTSD只作源别名，类别与评分/训练不升格；原课程版本张力继续保留。

写作审阅通道：宿主完整语义意见经writing_review进入统一结构、证据图与两模块原交付顺序；逐处纠错/可选润色不设数量上限，缺原文或首句实际扣留剧情诊断、完整稿与分数。分数只为外部建议，身份、语义与改写保真未认证；原图字节/区域/转写稿指纹进入独立审阅适配，应用文降档和续写酌扣不能混用；清晰度和交际影响仍外部声明，未完成真人评分验证。程序输送测试不能替代旧题库宿主语义回归。

真实验收链增强：结果Schema 1.2.0按方法/版本/题组/传播冻结稿隔离，workflow核阶段顺序、传播逐版观察绑定、陌生题与跨阶段学习控制。绝对盲测门槛、独立Baseline正确性和适用试次动作/证据均逐时长检查；90s失败不作合格参照，均值不掩盖某版损害。缺链条或采集前绝对门槛不授予释放或效率审阅建议；猜中不充当方法成功。时间、身份与审阅结论仍为外部声明，程序不能认证真人数据；新增测试均为程序控制测试。

方法编排执行通道：action_executions传入具体动作与八类产物，execution_trace按ID消费更早已审阅、完整、未刹车的兼容产物。R09三字段骨架、候选全覆盖分组、角色/版本/独立触发、对应候选关系和语法节点路径均有运行门禁；核验不支持时实际撤回答案与整卷推荐。产物指纹与执行链/图联合校验，Renderer显示实际动作和停止原因。此为外部动作结果的运行控制，不认证自由题面语义求解、真实动作或宿主审阅身份。

单题口播通道：lesson_review经源合同、独立触发、实际动作、短引文、候选关系和刹车覆盖进入lesson_feedback；完整消息恢复原纯文本开场，最后由核心闭合答案汇总。七选五实际三维分组在开头展示一次，缺分组或闭合就扣留完整稿。投影重检文字/图/触发/候选/答案一致性；未认证宿主自由文字语义与整篇课程顺序，旧题库语义回归仍缺。生成技能只增加接口链接，不复制教学判据或改用户技能库。

整篇交付接口：lesson复用单题核心，显式保留原题号、共享原文和审阅顺序。阅读中心任务先于细节/猜词、完形暂留后原空号回收、语法无提示词优先及七选五一次分组先于突破说明均有工程检查；最后按原题号汇总，缺某题口播时指出该题并扣留整篇消息。接口可运行不等于真实材料完整、自由文字语义或旧宿主表现已认证；相应真实回归仍缺。

评分边界：定档区间直接解析冻结源评分表，无调整依据的档/分冲突不接受；词数调整需1.2.0外部审阅、完整学生稿证据、原附加规则和准确前后记账。词数与原图调整独立，纯文本评分也绑定自身图路径及载荷，四Renderer拒绝事后换分或断证。程序测试不认证计词、定档、英语评分或真人效果。

## 案例类型逐方法审计

登记记录仍为106条，没有为补数新建题目或占位案例。全部82项五类槽中304槽未登记；30个正式method中26项共有104个未登记槽。保守纳入method和framework共42项核心节点，其中144个槽未登记。registered + evidence_gap与unregistered + evidence_gap是两种不同缺口；已登记例子也不认证完整真题或教学效果。可运行python -m answer_engine case-coverage读取完整矩阵。

| 方法 | 类型 | canonical | counterexample | boundary | transfer | hard |
|---|---|---|---|---|---|---|
| R01 | method | 已登记/evidence_gap | 已登记/source_pattern_only | 已登记/evidence_gap | 已登记/evidence_gap | 已登记/evidence_gap |
| R02 | method | 已登记/source_pattern_only | 已登记/source_pattern_only | 已登记/evidence_gap | 已登记/evidence_gap | 已登记/evidence_gap |
| R06 | method | 已登记/source_pattern_only | 已登记/evidence_gap | 已登记/source_pattern_only | 已登记/evidence_gap | 已登记/evidence_gap |
| R09 | framework | 已登记/source_pattern_only | 已登记/source_pattern_only | 已登记/source_pattern_only | 已登记/evidence_gap | 已登记/evidence_gap |
| R03 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R04 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R05 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R07 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R08 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R10 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R11 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R12 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R16 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| R17 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| F01 | method | 已登记/verified_course_example | 已登记/source_pattern_only | 已登记/verified_course_example | 已登记/verified_course_example | 已登记/evidence_gap |
| F05 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| F06 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| F07 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| C01 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| C02 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G01 | framework | 已登记/verified_course_example | 已登记/verified_course_example | 已登记/verified_course_example | 已登记/verified_course_example | 已登记/evidence_gap |
| G05 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G06 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G07 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G08 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G12 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| G15 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A01 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A02 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A03 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A04 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A05 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A06 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A07 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| A10 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W01 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W02 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W03 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W04 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W05 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W13 | method | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |
| W16 | framework | 已登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap | 未登记/evidence_gap |

外部审阅原题绑定：回调前后均校验输入，独立快照锁定题号、题型、原文、选项、提示词、学生稿、续写首句、原图和卡点；改值、嵌套原位修改或字段新增/删除均拒绝。审阅仍可补关系、动作、讲解及任务/难度标注，但不能清洗非法原输入或悄悄换题；整卷推荐复用该门禁。此为程序数据一致性测试，不认证英语语义或隔离Python回调。

整卷方法覆盖1.1.0：保留建议次数，另逐方法列出核验触发、产物、决定及案例候选题号。典型方法候选只按自身可审阅案例数排序；不能借其他方法的闭合答案或高展示分，把仅计划、仅触发或已停止的方法包装成典型用法。辅助方法产物仍无定案权；Schema兼容旧1.0.0投影。程序测试不认证完整真题卷、来源合法性、英语语义或学生效果，G11保持PARTIAL。

证据关系候选绑定：完成审计发现原图门禁可接受不同候选的审阅关系，现已修复。结论及candidate_decision产物要求同方法、同候选的同一条审阅关系，自身上游具备主张与独立触发，并有直接源引文；旁接主张/触发或只有触发引文不作决定关系证据。写作关系显式绑定student_draft，旧的缺标记写作结果须重新分析，原输入不变。回归覆盖四Renderer和无结论节点的产物图；这是结构修复，不把G8语义认证或其他未核要求改成PASS。

人工释放凭证入口：release-check与release-bindings只读检查方法/案例/原始观察/冻结计划/回归报告绑定，Registry的可选release_reviews索引指向显式人工批准记录。成熟度或实用等级不再永久无条件拒绝，但五类已核验案例、真实评估阶段链、当前代码/测试/语义Registry回归快照、人工审核及目标状态均必须通过；stable另需同版validated批准和多道迁移题，Efficient/Signature另需统计及相应人工审阅。工具不修改卡片，空模板不能批准；当前批准记录为0，82项仍Useful+candidate，不认证人、语义或显著性。

真实试卷导入：12套25个Word源哈希冻结，仅公开元数据。11套517项（495道客观题、22项写作）完成结构回归、冻结机械Prediction后Reveal；2021Ⅱ原题结构缺损拒绝推补。机械客观题全部未解，不能将未猜测统计当成语义正确的safe_abstention。3道另有揭晓前AI宿主动作审阅并与第三方答案一致，不是整卷自动正确率、独立人工语义认证或真人学习效果。写作按约束审阅、不以范文Exact Match。新Case及填槽均为0，方法状态不变；G8/G11及学生研究链仍PARTIAL。详情见exam-ingestion.md及evaluation/reports/exam-ingestion.json。

冻结审阅重放与Case Review：3卷各47项重放原题+冻结注释，逐方法6个候选（4个有产物、2个缺typed动作）；另有3道揭晓后AI语义审阅，不冒充新盲测或人工认证。两份R01出现同词强补共同断言归因问题，R09骨架有安全改善限定措辞风险。R01/R06 boundary和R02 canonical只作建议，已批准类型/登记/填槽仍0。2025两卷解析提取v1.2修复新题号/篇章内容吞入详解，旧源/预测/解析版本全部保留。源绑定或结构闭合不认证英语语义；不修改方法以贴答案。

负向语义审阅执行：withdraw_review只接受绑定原输入及冻结分析的显式撤回，不能添加答案、改题或补方法。撤回关系同步扣留其决定产物；撤回框架/定位时传递停用全部依赖消费者及其决定，重新生成图/单题/整卷结果。3道实际审阅均在新揭晓后记录扣留答案与Demo/Case推荐，原盲稿仍保留3道参考匹配事实，不算新盲预测或safe_abstention认证。所有Renderer可消费扣留后的合法Schema。

辅助动作审阅：另有2025Ⅰ两项真实题面动作，F01 Q36三维A–G完整分组、G01 Q59有提示词到名词性功能节点，均产生实际产物但不填写答案。单独post_reveal_action_review通道核源指纹、不可变题面、角色、执行图和四种Renderer，不以整题未闭合否定辅助动作，也不以辅助产物认证整题成功。2项AI审阅、4个产物，与原盲预测/3道匹配分开统计；独立Case/学生/Baseline仍待核，正式登记及填槽0。

七选五组合修正：默认F01一次分组先于解释，解释可消费已审阅分组，不从分组得答案；实际2025ⅠQ36链12个产物但六项未决，仍扣留答案。F05恢复原冻结课程首段尾分支为1.2.0，完整1.1.0历史及私有旧结果保留，当前唯一版本单独重放；角色和成熟度不升级。链的英语语义、独立Case、学生迁移与Baseline收益仍待核。用户暂停纳入新建文件夹材料，本轮不使用该补充源或模拟卷。

有界动作审阅：2021ⅠQ26补录R02自己的单项决定，不借未执行legacy关系或剩余项定案。原performing词义过强的混合理由实际撤回；风格/配合归属的重新审阅另存并绑定前驱SHA，仅当前快照计1，A/B/C未解且整题null。原Case Candidate与盲稿不改，新动作是独立揭晓后修订，类型建议未批准，正式Case/填槽仍0；不声称真人或独立英语认证。

学生首次动作投影：fallback只显示一个待核入口及Registry四步实战卡，不把计划当成已验证触发。实际停止或核验不支持时扣留后续计划提示，保留已提交证据及独立后续产物；混合produced/stopped步骤也不漏掉刹车。机器全链与完整口播/写作分支不改。四Renderer新增空计划的Registry版本、题型、职责、产物、Stop及主要动作绑定检查；程序测试不证明真实学生首用、传播或迁移成功，方法状态仍不升级。

## 整理目录与私有真实案例检查点（2026-10-09）

以上历史回归与零登记结论保留为各自时点记录。本检查点不重写原冻结报告。
406 个文件对应 204 份题面来源候选，不等于 204 套互不重复或已认证的官方真题。
本时点实际派发 26 个逐卷代理，24 份报告返回、2 卷在审；其余仍待派。
报告合计 1,677 个源任务、1,138 个忠实引擎输入及 62 个候选只是来源内计数，包含仓库旧题，
不能作为新增真题数、整卷语义正确率或已完成案例数。听力、历史改错、缺页和参考冲突均保留缺口。
2021 全国乙卷题面 PDF 附答案已曝光，不能算干净盲测；揭晓后的字段修复与动作修订也不重计盲测。

仓库去重核对现有 Case、课程出处、旧题稳定 ID 及已返回报告，不只比较附件文件名。
公开 Registry 仍为 106 条（含 90 条缺口、9 条模式及 7 条短课程片段），原有 ID 与文件不改。
私有 Catalog 另登记 2 个独立 AI 复核研究 Case，均复用既有真题 ID、仅补方法动作，不新增题目：
F01 boundary 检查三轴无区分度和代词未回填时不能据分组定案；
R09 canonical 保存完整五段的三字段骨架，并限制局部运输排放断言。两者均没有整题答案信用。
全文题面、参考及逐卷报告不因登记而上传公开仓库。

登记链实际校验原 PDF/字段跨度、冻结题面不可变、揭晓绑定、第二审阅者的六项检查、
独立方法执行 ID、当前 Analyzer/证据图/产物重放及只追加 Catalog。
公开覆盖矩阵和私有已核数分列；AI 动作复核可推进 Case 库，但不认证官方答案、审阅身份、
真人 First-use、Baseline 收益或传播效果。82 项方法仍为 candidate，真人参与 0，升级 0。
G7/G8/G10/G11 仍 PARTIAL，不以这两例宣称全题型、全槽或整卷完成。
私有精确快照为 `progress/contribution-24-reports-v1.json`，只代表该检查点，不代替实时派发账本。
