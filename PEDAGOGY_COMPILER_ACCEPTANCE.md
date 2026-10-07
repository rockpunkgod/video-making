# Pedagogy Compiler Acceptance

## 当前 v0.3 增量

2026-10-07：Compiler/Plan/Handoff 0.3.0，披露 Policy 0.2.0。工程冻结投影、原题快照和局部候选状态适配通过；完整首用/迁移/高阶内容与真人教学效果仍为 PARTIAL/PENDING。以下 v0.2 记录保留为历史，不授予当前消费资格。

未提供单独风险审阅的基础输出保存在忽略的`local-data/pedagogy/compiler-r5/`：三份真实输入、九个Plan、六个Copy/Motion Handoff完成源重放，历史字节不变。F01/G01/R02的worked_example继续READY；默认first_touch仍因9/10/9项HOLD。用户要求的R02九项实质风险审阅另存`boundary-risk-r2/R02/`，新first_touch/worked_example投影READY：四项当前功能合到一个关系比较与输出状态，五项未触发分支Later。frequency全unknown，severity全high，没有借低风险假设解除过载。

原题 whitelist、逐字段引用和 Copy 持续题面层已接通；不输出正确答案或执行元数据到题面。历史0.1/0.2完整性可读、当前消费拒绝，旧批准不能继承新的题面或文案。

R02 的现有审阅动作支持唯一局部排除的4→3结构对照；机械适配检查自己的方法版本、动作、Review、Decision/Evidence生命周期、当前范围及未闭合状态。专门 reviewed_payoff 仍兼容，但不再把它当作必须新增的上游 Review。G01 路由与 F01 分组仍不证明候选淘汰或永久省去后续工作。

`baseline_kind=structural_candidate_state`、`baseline_measured=false`，仅关闭本 scope 的一个候选核验任务；其他候选与 Stop 仍需要，源变化可重开。不证明学习、速度、少读全文、独立人工认证或最终答案。公开资格持续为 false。

Case门禁已补齐：只有自己的有效冻结Review中非空`reviewed_claims`内容才能开放Case/followup；case_type标签、空内容、非文本或冲突内容不能放行。标签本身不再算独立迁移/高阶内容。

风险Review契约0.1.0、投影交付0.1.1是0.3主契约的显式增量。基础Plan未改；新投影精确绑定原九项、每个复合Stop子句、旧Guard及当前状态。Reviewer是AI，不升级Teaching/Source/Editorial。旧0.1.0风险交付保持历史完整性可读、当前消费阻断；重新生成0.1.1，内嵌Review时间/envelope不改变语义SHA。没有覆盖旧包或旧Review。

本轮12项风险/呈现测试与6项native绑定测试通过；最终全仓664项回归通过（410.222秒），日志`local-data/pedagogy/verification-r7/full-regression.log`。ANSWER82 methods / 20 source documents / generated assets PASS。全部真实题、文案、声音、视频和工程保持本地，不把step-kind近似、结构预算READY或风险分层当成真人首用/迁移验收。

## v0.2 历史记录

日期：2026-10-07。初始基线 `main@adff3939f769d631a7ac6e8fc6d5f939045b3601`；完成审计修复基线 `main@6380ffc`。当前 Compiler/Policy 契约 **0.2.0**。**工程冻结投影通过；真实 first_touch 与完整黄金案例覆盖 PARTIAL。** 当前冻结资产和状态核验不等于独立教学语义、真人首用、效率或公开发布通过。

| 项目 | 结果与证据 |
|---|---|
| Core unchanged | PASS：独立 `pedagogy/`；生产代码不导入 Analyzer/Registry；只读前后内容一致测试 |
| Registry/Case/Renderer unchanged | PASS：本模块无写入；真实核验前后 Git diff 无这些目录修改 |
| 原 ANSWER 源仓库 unchanged | PASS：未访问或修改源仓库，本轮位于 video-making |
| Schema | PASS：`schemas/pedagogy-plan.json`，规范化 hash/Envelope/引用与冻结绑定 |
| First Action/Memory/Student Mental Model | PASS：已有字段投影，缺字段不造；see/think/do/check/stop，stop 完整覆盖全部 Tell Now 数组 |
| Tell Now/Later/Engine Only | PASS：默认逐项枚举冻结 anti_rule/failure_cases/cannot_replace/四步 Stop 等 Caveat，不需调用方 opt-in；unknown/high 保守；当前实际 Stop 必须 Now；Later 只来自已有绑定风险记录 |
| First-touch overload | PASS：必要边界、动作、Evidence cluster/概念与长度限额；过载 HOLD，不能为短片删边界 |
| Role/Stop/Evidence/answer preservation | PASS：重新 seal 的越权修改仍被源重放拒绝；局部动作 answer=null |
| Compression audit | PASS：included、omitted、risk refs、still_exists、backend guard、禁止修改与 hash |
| Copy/Motion handoff | PASS：sealed 轻量接口，依赖 Plan/源/当前状态重新核验；无 AE 特效选择 |
| 生命周期/历史 | PASS：缺状态只可查看历史，不能消费；撤回、版本/权限/动作/Review 依赖变化阻断重载 |
| 0.1→0.2 迁移 | PASS：旧 Schema 历史可读，当前消费明确阻断；重新消费原冻结输入保存新 Plan，旧 r1/r2 及 Copy r2/r3 保留 |
| Payoff carry-through | PASS：只搬运上游已有 reviewed_payoff，缺记录为 null，不自行造 baseline |
| Teaching/Source/Editorial Release | HOLD，public_render_ready 始终 false |

## 六黄金方法 × 三模式（真实显式资产）

| 方法 | first_touch | worked_example | boundary |
|---|---|---|---|
| R01 | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP |
| R02 | HOLD/PEDAGOGY_OVERLOAD | READY bounded local action | UNAVAILABLE_EVIDENCE_GAP |
| R06 | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP |
| R09 | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP | UNAVAILABLE_EVIDENCE_GAP |
| F01 | HOLD/PEDAGOGY_OVERLOAD | READY actor-axis action | UNAVAILABLE_EVIDENCE_GAP |
| G01 | HOLD/PEDAGOGY_OVERLOAD | READY route/noun node | UNAVAILABLE_EVIDENCE_GAP |

这里只消费已有、明确提交的三份真实冻结资产。R01/R06/R09 没有提交可消费冻结包；不会扫描 Registry/Case 补答案或凑样例。三份实际动作的独立 boundary Case 凭证缺失。0.2 默认枚举所有已冻结 Caveat，未提供已有风险分级，所以 F01/G01/R02 的 Tell Now 分别为 9/10/9 条，超过一条主边界预算；不会只保留两个 Stop 来缩小报告中的负载。

统计：18 槽，3 READY、3 HOLD、12 UNAVAILABLE。没有一条黄金真实 first_touch 被伪报 READY。合成首用正例只证明运行控制。

## 真实本地交接

当前真实题面与实际输出全部在忽略的 `local-data/pedagogy/compiler-r3/`；公开仓库只提交代码、合成测试和本脱敏报告。旧目录保持原样。

当前 G01 `worked_example.plan.json` 的 plan_sha：`647711d4672971f66282af39bee59038d66c33d185ee6541c8a02d5124c4cc8d`。同目录 `worked_example.copy.json / worked_example.motion.json` 通过 `validate_handoff`；`validate_plan(...)[consumption_allowed]=true`。原 r2 的 `dac639c7fa31fa2645793e7c27bd21e6f3edf0871918e411dadb5e017ecf1bd9` 仅作历史，按 0.2 当前消费被明确阻断；先前视频或 Copy 不能自动继承新的边界覆盖和 READY。

实际 ACTION/Review、Role、output node、当前 Stop、原分析不闭合状态及 AI-only 凭证均保留。没有变成人工认证、正式方法成功 Case、Efficient 或 Signature。

## 验证

0.2 受影响专项：`python -m unittest tests.test_pedagogy tests.test_pedagogy_workflow -v`，共24项全部通过（19 Compiler + 5 冻结整篇/CLI/过载/状态依赖）。新增默认 Caveat 风险覆盖、完整 student_model.stop、逐来源合并台账及旧契约历史可读/当前不可消费的正反例。合成首用正例通过明确标记的 SYNTHETIC 低风险输入才能合法分级，不向任何真实资产添加风险或 Review。Student POV 和完整仓库回归由主集成任务单独记录，不重复累计测试数量。

真实三份资产9个新 Plan 均完成源重放，三份 worked_example 的六个 Copy/Motion Handoff 当前核验通过。冻结 bundle/status 文件前后字节 hash 不变，truth_guard、答案范围、成熟度与 Review 等级不变；同输入重复生成 plan/content hash 一致，时间只改 Envelope。旧九个 Plan 只允许历史完整性检查，当前消费被版本门禁阻断。完整仓库回归由主集成任务统一记录。

主集成定版回归628项通过，ANSWER 校验82 methods / 20 source documents / generated assets PASS；Student POV23项与 native Cognitive绑定6项另见相应验收，不将回归与专项累计成新增数量。

## 保留的限制

风险等级、Case 类型、语义和外部审阅身份仍是上游断言；确定性 lint 不能认证教学真理、压缩安全或真人学习。当前状态仅来自调用方提供的 manifest，不承诺后台实时监听。正式首次教学仍需现有风险依据/合格 Case 或更长合法模式；公开使用另核最终实际展示片段和编辑锁定文案。

transfer/hard_case 当前按冻结 Review case_type 标签判断可用性，尚不生成独立迁移题/高阶题教学链；followup 引用是类型标签，不是独立 Case 内容。simultaneous_concepts 是 step-kind 数的工程近似，不宣称已经测量学生实际同时处理的概念数。这些结构入口不计入完整系列教学或真实认知负担验收。
