# Pedagogy Compiler v0.2

Truth Completeness ≠ Teaching Completeness。ANSWER 保留完整 Trigger、Role、实际动作、Output、Evidence、Stop、Review、来源及生命周期；独立 `pedagogy/` 只选择已冻结的表达并记录省略。Renderer 继续投影，Copy/Motion 不再自行决定边界。

## 输入与职责

只接受既有 `FrozenAssetBundle + ArtifactStatusManifest` 或 `frozen_reviewed_passage + reviewed_passage_status`。原始 `QuestionAnalysis`、未绑定 Review、规划动作、停用产物和未确认内部使用的来源不能消费。运行时不导入 Analyzer、Registry、Renderer，不扫描 Case/原始题库/教学 Markdown，不生成 Review，不改变原 ANSWER 源仓库。

```text
ANSWER frozen structured truth + current supplied status
  → Pedagogy Compiler
  → sealed PedagogyPlan + Student Mental Model
  → sealed Copy/Motion handoff
  → Student POV Copy / Lesson / Card / WeChat
```

API 的 `analysis` 参数是冻结运输对象，不是自由分析结果：

```python
from pedagogy import PedagogyCompiler, validate_plan, copy_projection

plan = PedagogyCompiler().compile(
    analysis=frozen_bundle, status=current_manifest,
    selection={"method_id": "SYNTHETIC_METHOD", "action_ids": ["synthetic-action"]},
    mode="first_touch", channel="video", duration_target=30,
)
validate_plan(plan, frozen_bundle, current_manifest)
copy = copy_projection(plan, frozen_bundle, current_manifest)
```

以上只展示调用形状。实际方法/版本/动作必须已有；不能将这个合成 ID 当成资产。

## 学生四件套与来源

`symptom / first_signal / first_action / judgment_point / memory_phrase` 投影已有方法的症状、四步卡、核心动作、判据或短表达。可以显式选同一方法/实际动作中的 JSON pointer；不接受新文案、另一个方法的断言、答案值或任意 Evidence。缺少可用记忆句时首次教学为 `UNAVAILABLE_EVIDENCE_GAP`。其它模式允许该辅助字段为 null。

每个教学 Item 同时保存 text、原字段 pointer/hash、实际动作、Evidence 和 Review 引用。方法定义的第一动作与实际题中的具体动作分别保存，Working Rule 不替换完整 Action。`student_model` 是 see/think/do/check/stop；不是“方法已经适用/题已经闭合”的新增结论。0.2 的 `student_model.stop` 是有序数组，必须完整等于 `boundaries.tell_now`，包括实际 Action Stop 和所有当前必要 Caveat；不能只取第一条方法 Stop。

投影只允许两种操作：原题和 Evidence 逐字保留；教学字段移除内部方法编号并将内部 `word_answer` 标签显示为“填词答案”。不自由改写、不删除否定/范围/条件、不归并措辞不同的 Stop。自然文案由后续 Copy 候选及独立保真审核处理。

## Tell Now / Later / Engine Only

- 当前实际动作 Stop 永远 Tell Now；频率、严重程度、当前相关性都是有限等级 low/medium/high/unknown。
- 默认逐项枚举已冻结的 anti_rule、failure_cases、cannot_replace、four_step_card.stop，以及已存在的 typed false_triggers/caveats/boundaries 与当前 Review 的 boundary Claim；不依赖 extra_boundary_refs。每条保留自己的源 pointer/hash 风险台账，没有已有、精确绑定的 `pedagogy_risk_annotations` 就保守 unknown → Tell Now。非支持形状或空文本 fail closed，不能整团藏入 BACKEND_GUARD。
- 当前相关性 high、任一 unknown、严重程度 high、相关性 medium 或频率 high 均保留 Tell Now。高危但罕见也先保留，不能靠编辑猜测降级。
- 只有既有 Review 记录明确将当前相关性降为 low，且其它风险不触发保守条件，才允许 Tell Later。记录需 source_pointer、item_sha、risk 三项等级及 rationale；Compiler 不创建这种记录。
- Engine Only 是固定的实现字段白名单：method ID/version、Role ID、审阅/Evidence ID、源分析指纹、release state。语义 Stop、教学限制和反例不能伪装成工程元数据。

Tell Later 的断言、风险依据、原因及 `still_exists=true` 均保留在 Plan 和 compression_audit。完整方法与实际动作作为 BACKEND_GUARD 绑定；这个标记不授权删除某条 Tell Now。频率 unknown 不等于罕见，数字风险分数不接受。

当前动作 Stop 和方法 Stop 文本完全相同且属于同一分层时，保留全部来源引用并作为一条学生边界；每个来源仍有独立风险台账记录，条目指向合并后仍存在的边界 ID。语义近似的句子不会自动合并。严谨性超过首次教学预算时输出 HOLD/PEDAGOGY_OVERLOAD，要求分系列或消费已有的分级凭证，不由本模块创建评审来解除过载。

## 模式、Case 与认知负载

支持 first_touch、worked_example、counterexample、boundary、transfer、hard_case、review。canonical→first_touch/worked_example；counterexample→反例；boundary→刹车；transfer→迁移；hard→高阶。Case 类型只能来自当前冻结且有效的 Review 标签或已审阅 boundary/counterexample Claim。Registry 中的示意或 evidence_gap 不能充当真实 Case。

当前 transfer/hard_case 的 Case 可用性由冻结 Review case_type 标签判断，步骤仍是已选动作的通用投影；followup ref 仅指向类型标签，没有加载另一道独立 Case 的题面与内容。它是结构入口，不是完整迁移或高阶教学系列的验收证明。simultaneous_concepts 统计当前不同 step-kind 数，是工程近似值，不表示已验证学生实际同时处理的概念数。

first_touch 的结构预算：core_actions≤2、primary_boundary≤1、memory_phrase=1、primary_evidence_cluster≤1、simultaneous_concepts≤3；另有学生字段 180 字/记忆句 80 字的保守长度检查。它们是 provisional 工程限制，不是认知科学精确指标。Student POV 的首次教学进一步要求只有一个主动作，不能借 Compiler 的上限偷塞两个主简化。

worked_example 明确记录原题→观察→实际动作→Evidence→当前判断→Stop；默认 scope 是 method_action_demo。原分析的答案/闭合保留为后台 Guard，前台 answer=null、may_output_final_answer=false。某个 decider 的局部排除也不能自动包装成整题答案。

counterexample / boundary / transfer / hard_case 缺对应已绑定 Case 时为 `UNAVAILABLE_EVIDENCE_GAP`。不创造反例、迁移题或新的 Review。案例覆盖和方法成熟度分开，仍不自动升级 candidate/Useful。

## 指纹、重载与放行

沿用 UTF-8、键排序、无无意义空格的 Canonical JSON；数组顺序保留，missing≠null。`plan_sha` 排除生成时间/运输校验值；`content_sha` 与 envelope_sha 分开。来源、方法、实际动作、当前必要边界、表达选择、政策/Compiler 版本都进入计划绑定。

`validate_plan(plan,bundle,status)` 重新生成全部投影；单纯重新 seal 不能掩盖答案、Role、Evidence、Stop、成熟度、确定性或披露分层的修改。当前状态缺失/撤回/替代/语义变化/权限变化/动作或审阅依赖失效时消费阻断。`inspect_historical` 只核历史完整性，永不授予当前消费资格。

当前 Compiler、Policy、Plan 与 Handoff 契约版本为 0.2.0。Schema 仍支持完整性检查 0.1.0 历史结构，`inspect_historical` 对它返回 LEGACY_CONTRACT/consumption_allowed=false；`validate_plan` 与 `validate_handoff` 显式阻断旧契约。迁移必须用原冻结资产及当前状态重新 compile，重新生成投影和下游绑定，不能修改旧 Plan 的版本标签或覆盖原文件。旧包既有 Review、源事实、答案、成熟度与历史结果均不被覆盖，旧 Copy/渲染不能继承新 Plan 的 READY。

`copy_projection / motion_projection / validate_handoff` 都要求当前提供的上游状态；静态文件不会自行感知外部撤回。收到新状态后，下次消费前重检。Copy 只获得轻量教学字段、已有 Evidence、Do Not Say 和绑定；Motion 只获得认知关系，不指定 AE 特效。

三类公开 Release 和 `public_render_ready` 在本模块始终 HOLD/false。READY 表示当前内部冻结投影可以消费，不是独立教学认证、来源许可、编辑释放或学生教学效果证明。

## CLI 与本轮真实状态

独立 `python -m pedagogy compile|validate|handoff|matrix <request.json>`；请求显式列 bundle/status/selection，输出不可覆盖历史。同类操作没有自动解题或目录扫描。editable 安装同时提供 `pedagogy-compiler`。

当前真实投影保存在忽略的 `local-data/pedagogy/compiler-r3/`，r1/r2 原文件保留为历史。F01、G01、R02 的 bounded worked_example READY；未补风险凭证，所有已冻结 Caveat 都保守纳入 Tell Now，分别为 9/10/9 条。first_touch 因必要边界过载而 HOLD；独立 boundary Case 缺口为 UNAVAILABLE。R01/R06/R09 未提供可消费的冻结资产，保持缺口。九条 Plan、六个 READY Copy/Motion Handoff 当前源重放通过，原 bundle/status 字节指纹不变；迁移记录位于本地 migration.json。详见 `PEDAGOGY_COMPILER_ACCEPTANCE.md`。

新增 Payoff 只携带已有 Review 中的 `reviewed_payoff`，要求同题、同方法版本、同组实际动作及自身 Evidence。缺该记录时 `payoff.reviewed_support=null`；长题面和短 Output 不能自行证明 Removed Cognitive Work。后续系统说明见 `docs/student-pov-copy.md`。
