# Pedagogy Compiler Acceptance

日期：2026-10-07。基线 `main@adff3939f769d631a7ac6e8fc6d5f939045b3601`。**工程契约完成；真实 first_touch 与完整黄金案例覆盖 PARTIAL。** 当前冻结资产和状态核验不等于独立教学语义、真人首用、效率或公开发布通过。

| 项目 | 结果与证据 |
|---|---|
| Core unchanged | PASS：独立 `pedagogy/`；生产代码不导入 Analyzer/Registry；只读前后内容一致测试 |
| Registry/Case/Renderer unchanged | PASS：本模块无写入；真实核验前后 Git diff 无这些目录修改 |
| 原 ANSWER 源仓库 unchanged | PASS：未访问或修改源仓库，本轮位于 video-making |
| Schema | PASS：`schemas/pedagogy-plan.json`，规范化 hash/Envelope/引用与冻结绑定 |
| First Action/Memory/Student Mental Model | PASS：已有字段投影，缺字段不造；see/think/do/check/stop |
| Tell Now/Later/Engine Only | PASS：unknown/high 风险保守；当前实际 Stop 必须 Now；Later 只来自已有绑定风险记录，工程白名单不可当教学规则 |
| First-touch overload | PASS：必要边界、动作、Evidence cluster/概念与长度限额；过载 HOLD，不能为短片删边界 |
| Role/Stop/Evidence/answer preservation | PASS：重新 seal 的越权修改仍被源重放拒绝；局部动作 answer=null |
| Compression audit | PASS：included、omitted、risk refs、still_exists、backend guard、禁止修改与 hash |
| Copy/Motion handoff | PASS：sealed 轻量接口，依赖 Plan/源/当前状态重新核验；无 AE 特效选择 |
| 生命周期/历史 | PASS：缺状态只可查看历史，不能消费；撤回、版本/权限/动作/Review 依赖变化阻断重载 |
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

这里只消费已有、明确提交的三份真实冻结资产。R01/R06/R09 没有提交可消费冻结包；不会扫描 Registry/Case 补答案或凑样例。三份实际动作的独立 boundary Case 凭证缺失。first_touch 的完整方法 Stop 与实际 action Stop 不同，且没有已有风险分级，所以两条都 Tell Now，超过一条主边界预算。

统计：18 槽，3 READY、3 HOLD、12 UNAVAILABLE。没有一条黄金真实 first_touch 被伪报 READY。合成首用正例只证明运行控制。

## 真实本地交接

真实题面与实际输出全部在忽略的 `local-data/pedagogy/compiler-r2/`；公开仓库只提交代码、合成测试和本脱敏报告。

G01 `worked_example.plan.json` 的 plan_sha：`dac639c7fa31fa2645793e7c27bd21e6f3edf0871918e411dadb5e017ecf1bd9`。同目录 `worked_example.copy.json / worked_example.motion.json` 通过 `validate_handoff`；`validate_plan(...)[consumption_allowed]=true`。先前 r1 是保留的历史，不能与新契约混用。

实际 ACTION/Review、Role、output node、当前 Stop、原分析不闭合状态及 AI-only 凭证均保留。没有变成人工认证、正式方法成功 Case、Efficient 或 Signature。

## 验证

新增模块测试：`python -m unittest tests.test_pedagogy tests.test_pedagogy_workflow tests.test_student_pov -v`，共36项。覆盖 Compiler 的15项、冻结整篇/CLI/四动作过载/状态依赖5项、后续 Student POV16项；不把重复运行相加。

真实三份资产9个 Plan 均完成源重放，三份 worked_example 的 Copy/Motion handoff 当前核验通过。冻结输入前后不变；同输入重复生成 plan/content hash 一致，时间只改 Envelope。完整仓库回归由主集成任务统一记录。

## 保留的限制

风险等级、Case 类型、语义和外部审阅身份仍是上游断言；确定性 lint 不能认证教学真理、压缩安全或真人学习。当前状态仅来自调用方提供的 manifest，不承诺后台实时监听。正式首次教学仍需现有风险依据/合格 Case 或更长合法模式；公开使用另核最终实际展示片段和编辑锁定文案。
