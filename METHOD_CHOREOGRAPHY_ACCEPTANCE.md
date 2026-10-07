# Method Choreography v0.1 Acceptance

2026-10-08。中间层契约、真实结构回放和合成测试已通过。当前真实输入只获准诊断回放，生产消费 **HOLD**；没有制作新视频或声音，Human Taste **PENDING**，`public_render_ready=false`。

## 实际基线与边界

基线为 `main@15c230f51a2039f6f4efcca9ba7e5b414edfcb1e`，高于请求中的 `31a1df7`。真实 Pedagogy Compiler 0.4 和 Student POV Experience 0.4 已存在，正式消费它们，没有手填缺失事实。

新增独立 `method_choreography/` runtime、`creative/method-choreography/` 规格/Schema/合成样本、测试、文档与本报告。现有 Method Motion Identity 0.1、六种 Signature 与 Brand Grammar 文件全部保留；这不是 Motion Identity 0.2 或 Creative OS v0.2。

没有修改 ANSWER Truth Core、Registry、Pedagogy/Student POV 输入、Frozen Evidence/Action/Stop/Role、当前 Copy、Narration Performance、Voice Producer、AE、Premiere、音乐或既有生产索引。没有新增教学/Copy Review。

## 契约与输入绑定

| 层 | 本轮消费 |
|---|---|
| Pedagogy Plan / Copy / Motion Handoff | 0.4.0；R02 使用当前有效 Handoff |
| Student POV Experience | 0.4.0；精确 Experience / final_copy_sha |
| Frozen Method Application | 0.1.0；G01 使用已有同动作跨度标注 |
| Motion Identity / Brand Grammar | 0.1.0；只绑定 ID、版本与 SHA，不导入视觉参数 |
| Method Choreography | `method-choreography/v1`，0.1.0 |
| Creative Handoff | `choreography-projection/v1`，0.1.0 |

绑定包含方法版本、Plan/Experience/final Copy SHA、Handoff 内容 SHA、可选 application SHA、父资产语义/analysis SHA、Physics/Recipe/原 Motion Identity/Brand Grammar SHA。当前 Bundle / Status 每次 compile、validate、project 重新核验；撤回、来源状态或绑定变化不能沿用旧契约。

全部真实输出及读取稿保存于忽略的 `local-data/method-choreography/v01-r2/`；早期开发回放 r1 保留，未覆盖。公开报告不包含题面、逐字 Copy、音视频、模型或 Adobe 工程。

## 六类 Physics 与实际实现

Navigation、Reduction、Comparison、Relationship、Classification、Routing 均有正式有限词汇。Operation 保存 source-bound target/preserved objects、来源、reversibility、当前有效范围和 qualitative temporal character。

六个原有方法有不同 core pattern，并共享 focus / carry / transform / settle / seal。当前真实 runtime 仅实现 R02/G01 bounded replay；R01/R06/R09/F01 为上层规格，没有新增教学方法或批量生成案例。Synthetic Peel 是单独的 **SYNTHETIC CONTRACT TEST**，不能成为真实方法或生产素材。

## R02：当前真实正例

Pedagogy Plan SHA：`4b176c0d1efd5d4e3c246412452ac30cf44670f7a63db6eb66bd761a68baa947`。
Student Experience SHA：`e17037b5cf2fd2bf17bebafc263362658e49f021eed3aa7d90488a9f1a1cb71a`。
Frozen final Copy SHA：`984ac967d439aaa32d21ce1ac68d63b3020cbb14284c9983281f88a6c322c116`。

Choreography SHA：`f94a897d1871a59e3fd288d86f0e248d3abe47ae7f5621025bf012d49ad73d7d`。
Projection SHA：`d2d36bfc5ad8b803aa343c53b0b991126a3b7ea2881861a83b2bbfd4435a8191`。

9 个 state、8 个 operation、22 个来源对象、198 次逻辑对象状态记录：

```text
Problem
  → anchor current Evidence
  → align supplied source objects
  → overlay current candidate
  → detach existing mismatch assertion
  → reveal reviewed relation
  → apply supported candidate 4→3
  → lock current action / Stop
  → recall first action
```

关系断言来自当前动作已绑定的 Frozen relation record。原文/候选对象分组仅使用已有 Evidence 的 field metadata、已给候选资格对象及受审断言，不解析英文主体或创造连线端点。

四个 core operation 逐次改变 `structural_groups` 和当前 foreground 信息关系。只修改 `relation_state` 标签也会被判为装饰编舞；阶段名称本身不能冒充 Spatial Consequence。

局部候选数在实际 Collapse 之前保持 4，之后为 3。D 的资格改变只在当前受审状态内不可逆；原 options 文本对象持续存在。A/B/C 保持 unresolved，不能被封成答案。Work Delta 的 removed=1、deferred=0、still_required=5 原样绑定；没有新增省时、少读、词汇或迁移结论。

Resolution 绑定实际 candidate_decision 与原 decider Role，scope 仍为 `candidate_set`；`decision_completion=false`、final answer 资格 false。Stop 保存未决对象、必要 coverage 与禁止局部结果 → final_answer 的转换；没有添加免责声明卡或结果提醒文案。Memory 只回收已有第一动作/记忆句，方法名在 core action 之后。

限制：当前关系为 `assertion_only_no_actor_span_geometry`。没有独立的 actor/action/object 逐词标注，所以本层不生成主体图、端点几何或新句法标签。R02 不伪造辅助型 Frozen Method Application，application SHA 为 null；认知对象来自真实 Pedagogy Cognitive Structure。

结构编译 **PASS**，可用性 **HOLD**：`FINAL_EXPERIENCE_COPY_REVIEW_REQUIRED`，且本轮显式 `DIAGNOSTIC_ONLY_NOT_PRODUCTION_READY`。没有为解锁生产而创建新 Copy 审核。

## G01：当前负例

Pedagogy Plan SHA：`ecd5decffdf546224777e67117bb219a885bc4ded73fdde577d2461132385eaf`。
Student Experience SHA：`24b5adbe4f2f143ed34bc869f3ca81e4c93733d4666fcea1f877251ce9fed3b8`。
已有 application SHA：`264c6fba415d70ec32ab7d4e44b6c356491abb342a9eeb9b0ab39a949d343330`。

Choreography SHA：`999efd58a70886de05436bf34fc3b8f8bfe18eb0f211024d33b2e7a759c90514`。
Projection SHA：`4604b38d5280061eb9b2bd186c764ad8e8ed3d7dfc3794ce65fbc6bdf0ae2801`。

6 个 state、5 个 operation、16 个来源对象、96 次对象状态记录：attention → extract bound slot → existing route → seal same origin / Stop → memory。

额外跨度来自已存在、重新校验的同一 G01 Action/Review application。空位作为 Extract、Route 和 Seal 的同一逻辑 origin。允许暂缓的跨度保留内容与可逆状态，不创造 Work Delta，也不把路线外部工作说成永久删除。

`collapse.supported=false`，`payoff_event=null`。已有 route_selection 和当前 framework Role 不得到最终词形或答案；当前未决对象和 Stop 保留。

结构诊断 **PASS**，可用性继续 **HOLD**：`BASELINE_WORK_UNSUPPORTED`、`PAYOFF_UNSUPPORTED`、`COGNITIVE_RELIEF_UNAVAILABLE`、`UPSTREAM_PEDAGOGY_HOLD` 与新最终文案/诊断资格缺口。Copy/Motion Handoff SHA 仍为 null；消费当前 Student POV 的显式上游 HOLD 诊断，不创建虚假 Handoff。

## Synthetic Peel 与兼容

合成 fixture 明确给出两个 modifier、两个 protected core span；字符串带 SYNTHETIC 标记。成功表达 peel A → peel B → supplied core tighten → restore same objects → stop，同时验证不 restore 时仍保留可逆 deferred。原内容 SHA、ID、保护跨度与逻辑来源不变。

此测试没有识别真实英语长难句，没有 reviewed Baseline、Work Delta 或 Payoff，removed 始终为空，生产消费 false。聚焦和可逆编排不能被包装成教学效果认证。

当前真实 0.3 Copy 的 compatibility analysis 也重新校验：R02 原 READY、G01 原 HOLD 保持原样，报告 `V04_INPUT_REQUIRED`。没有改版本标签、覆盖旧稿、从 0.3 手填 0.4 Experience 或继承批准。

## 审计与交接

| 审计 | R02 | G01 |
|---|---|---|
| Object Lineage / 原内容 SHA | PASS，22×9 | PASS，16×6 |
| 可逆性与受审排除范围 | PASS | PASS |
| 未决对象、scope、Stop | PASS | PASS |
| Reality Layer / Carry | PASS，所有状态保留 | PASS，所有状态保留 |
| 有据认知状态转换 | 8 | 5 |
| Collapse / Payoff | 局部 4→3 | 不创建 |
| Anti-PPT / Reset / Detached / Decorative 风险 | 未触发 | 未触发 |
| Signature physics pattern | 机械匹配 PASS | 机械匹配 PASS |

负控可检测 `PRESENTATION_RESET_RISK`、`DETACHED_INFOGRAPH_RISK`、`DECORATIVE_CHOREOGRAPHY`、`PPT_MOTION_RISK` 和方法换标签后的 `SIGNATURE_DISTINCTIVENESS_FAIL`。这些是结构 lint，不是实际渲染审美或学生效果认证。

真实 Creative Projection 保存 binding、states、operations、object catalog/lineage、attention、collapse/resolution/payoff/stop/memory、qualitative tempo 与风险。CLI compile / validate / inspect / project 均实际完成，相同输入重复生成完整对象一致。时间戳不改变语义 SHA，改变 envelope；源、Copy 或体验安排变化使旧契约失效。

真实 Projection 均 `diagnostic_only=true`、`consumption_allowed=false`。默认门禁拒绝把 HOLD 交给正式 Creative 生产。契约无相机/布局像素、AE Effect、帧数、音乐、TTS 参数或新增教学文本。

## 验证

| 检查 | 结果 |
|---|---|
| 新增 Method Choreography 合成测试 | **38 PASS** |
| 最终代码全量回归 `python -m unittest discover -s tests -v` | **816 PASS**，503.379 秒 |
| ANSWER validate | **PASS**，82 methods / 20 source_documents / generated_assets PASS |
| 保护清单内容 SHA | **779 / 779 未变**，最终全量回归结束后再核对通过 |
| 实际回放输入逐字 hash | PASS |
| 真实旧 0.3 Copy 核验 | PASS；原资格保持 |
| `git diff --check` / staged check | **PASS** |

覆盖当前源/Plan/Experience 改变、撤回/权限变化、无效对象、保护跨度、deferred≠removed、未决资格、reducer/locator 答案权限、4→3、无收益 G01、真实关系依赖、假的 Collapse、同对象传承、Synthetic restore、方法换名、Reset/Detached/Decorative、状态标签无效变化、无 AE/TTS/新事实、定性时间、必要 Stop、历史不可覆盖、READY/HOLD 投影门禁、旧版兼容与输入不变。

## 发布状态与停止点

Engineering Contract / Replay：PASS。Human Taste、真实方法辨识度、画面可读性、实际心理释放与记忆效果：**PENDING**。Teaching / Source Display / Editorial Release：**HOLD**。`public_render_ready=false`。

本轮完成有据状态链、反例门禁、合成可逆动作与 Creative 数据交接即停止。没有调用 GPT-SoVITS、AE MCP 或 Premiere，没有新 AEP、视频、配音或 A/B，没有更改 Chopin，没有进入 V10 或 Creative OS v0.2。公开仓库仅提交工作流代码、契约、合成样本、文档和本脱敏报告。
