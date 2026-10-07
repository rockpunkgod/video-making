# Pedagogy Compiler v0.3

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

0.3 的 `original_question` 额外保留已有 passage、question_type、given_word 与完整 stem/options，不投影答案或执行元数据。`original_question_refs` 为每个展示字段保存独立冻结引用，Copy 的第一景先展示原题，并让后续动作引用持续题面层。原题、Evidence 中出现的词或统计照录，不作为新增口播 Claim 改写。详见 `docs/original-question-copy-contract.md`。

## Tell Now / Later / Engine Only

- 当前实际动作 Stop 永远 Tell Now；频率、严重程度、当前相关性都是有限等级 low/medium/high/unknown。
- 默认逐项枚举已冻结的 anti_rule、failure_cases、cannot_replace、four_step_card.stop，以及已存在的 typed false_triggers/caveats/boundaries 与当前 Review 的 boundary Claim；不依赖 extra_boundary_refs。每条保留自己的源 pointer/hash 风险台账，没有已有、精确绑定的 `pedagogy_risk_annotations` 就保守 unknown → Tell Now。非支持形状或空文本 fail closed，不能整团藏入 BACKEND_GUARD。
- 当前相关性 high、任一 unknown、严重程度 high、相关性 medium 或频率 high 均保留 Tell Now。高危但罕见也先保留，不能靠编辑猜测降级。
- 只有既有 Review 记录明确将当前相关性降为 low，且其它风险不触发保守条件，才允许 Tell Later。记录需 source_pointer、item_sha、risk 三项等级及 rationale；Compiler 不创建这种记录。
- Engine Only 是固定的实现字段白名单：method ID/version、Role ID、审阅/Evidence ID、源分析指纹、release state。语义 Stop、教学限制和反例不能伪装成工程元数据。

以上是没有独立披露审阅时的默认保守政策。另可显式提供`boundary_review`，契约为`schemas/boundary-risk-review.json`（0.1.0），由Pedagogy层消费已有冻结事实完成的外部边界风险审阅；它不是ANSWER教学Review，也不生成英语规则。审阅精确绑定基础Plan、题目、方法、动作、分析、完整Guard及原边界台账。每条记录省略风险、严重度、当前分支、依据和后置触发点。当前没有学生实测，frequency必须unknown；低当前相关性不能写成低频或低严重度。

显式审阅可将已判断本次未触发的分支移到Later，也可把多个当前边界合到一份字面呈现；当前实际Stop仍是Now，必须逐字符记录所有子句的覆盖。允许的覆盖是字面显示、经审阅的等价关系、已有Evidence聚焦、未闭合候选状态与上游重检。当前Stop不能仅靠后台标签覆盖；教学条件不能整条改称ENGINE_ONLY。程序检查绑定和结构覆盖，不认证风险判断或英语真值。AI审阅只允许内部工程投影，三类公开Release不变。

Tell Later 的断言、风险依据、原因及 `still_exists=true` 均保留在 Plan 和 compression_audit。完整方法与实际动作作为 BACKEND_GUARD 绑定；这个标记不授权删除某条 Tell Now。频率 unknown 不等于罕见，数字风险分数不接受。

默认情况下，当前动作Stop和方法Stop文字完全相同且属于同一分层时保留全部来源并合为一条；语义近似不自动合并。显式风险审阅可以批准多个来源共用当前呈现，但只能选已有原文字面片段，保存每项及每句的覆盖和审阅引用；不能自由改写判据。重放会重新核验审阅、来源、现行状态、遗漏和预算，不直接清空HOLD。Compiler不自动生成这种评审来解除过载。

## 模式、Case 与认知负载

支持 first_touch、worked_example、counterexample、boundary、transfer、hard_case、review。canonical→first_touch/worked_example；counterexample→反例；boundary→刹车；transfer→迁移；hard→高阶。对应Case内容只能来自当前选中题目、方法和实际动作自己的有效冻结Review中的 `reviewed_claims`。只有 `case_type / case_kind` 标签不能开启Case模式或后续可用槽；Registry中的示意或evidence_gap不能充当真实Case。

支持的内容键为 `canonical / counterexample / boundary / transfer / hard`，`hard_case`也可绑定到hard槽。每份非空内容必须是已有文本断言；空值或非文本形状拒绝消费，同一槽的冲突断言也拒绝，不按最后一份Review覆盖。计划的case步骤和followup引用指向实际内容及其hash，保留该题已有动作、Evidence和Stop。内容变化会使旧投影源重放失败。Compiler不把标签扩写成反例，也不加载另一道未提交的题目。

transfer/hard_case现在可投影这份已有、已审阅的具体内容；步骤仍围绕明确提交的同一道冻结应用，不代表已完成独立练习产品、整个教学系列或真实学生迁移验证。simultaneous_concepts统计当前不同step-kind数，是工程近似值，不表示已验证学生实际同时处理的概念数。

first_touch 的结构预算：core_actions≤2、primary_boundary≤1、memory_phrase=1、primary_evidence_cluster≤1、simultaneous_concepts≤3；另有学生字段 180 字/记忆句 80 字的保守长度检查。它们是 provisional 工程限制，不是认知科学精确指标。Student POV 的首次教学进一步要求只有一个主动作，不能借 Compiler 的上限偷塞两个主简化。

worked_example 明确记录原题→观察→实际动作→Evidence→当前判断→Stop；默认 scope 是 method_action_demo。原分析的答案/闭合保留为后台 Guard，前台 answer=null、may_output_final_answer=false。某个 decider 的局部排除也不能自动包装成整题答案。

counterexample / boundary / transfer / hard_case 缺对应已绑定 Case 时为 `UNAVAILABLE_EVIDENCE_GAP`。不创造反例、迁移题或新的 Review。案例覆盖和方法成熟度分开，仍不自动升级 candidate/Useful。

## 指纹、重载与放行

沿用 UTF-8、键排序、无无意义空格的 Canonical JSON；数组顺序保留，missing≠null。`plan_sha` 排除生成时间/运输校验值；`content_sha` 与 envelope_sha 分开。来源、方法、实际动作、当前必要边界、表达选择、政策/Compiler 版本都进入计划绑定。

`validate_plan(plan,bundle,status)` 重新生成全部投影；单纯重新 seal 不能掩盖答案、Role、Evidence、Stop、成熟度、确定性或披露分层的修改。当前状态缺失/撤回/替代/语义变化/权限变化/动作或审阅依赖失效时消费阻断。`inspect_historical` 只核历史完整性，永不授予当前消费资格。

当前 Compiler、Plan 与 Handoff 契约版本为 0.3.0，披露 Policy 保持 0.2.0。Schema 支持完整性检查 0.1/0.2 历史结构，`inspect_historical` 对它们返回 LEGACY_CONTRACT/consumption_allowed=false；`validate_plan` 与 `validate_handoff` 显式阻断旧契约。迁移必须用原冻结资产及当前状态重新 compile，重新生成投影和下游绑定，不能修改旧 Plan 的版本标签或覆盖原文件。旧包既有 Review、源事实、答案、成熟度与历史结果均不被覆盖，旧 Copy/渲染不能继承新 Plan 的 READY。

`copy_projection / motion_projection / validate_handoff` 都要求当前提供的上游状态；静态文件不会自行感知外部撤回。收到新状态后，下次消费前重检。Copy 只获得轻量教学字段、已有 Evidence、Do Not Say 和绑定；Motion 只获得认知关系，不指定 AE 特效。

三类公开 Release 和 `public_render_ready` 在本模块始终 HOLD/false。READY 表示当前内部冻结投影可以消费，不是独立教学认证、来源许可、编辑释放或学生教学效果证明。

## CLI 与本轮真实状态

独立 `python -m pedagogy compile|validate|handoff|matrix <request.json>`；请求显式列 bundle/status/selection，输出不可覆盖历史。同类操作没有自动解题或目录扫描。editable 安装同时提供 `pedagogy-compiler`。

没有显式风险审阅的真实投影仍在忽略的`local-data/pedagogy/compiler-r5/`，F01/G01/R02的默认首用分别因9/10/9项边界HOLD。本轮R02经用户要求的实质风险审阅，另存`local-data/pedagogy/boundary-risk-r1/R02/`：基础九项原文及台账未改，1/2/3/8功能合到一个关系比较和候选状态，4/5/6/7/9后置；新first_touch/worked_example工程投影READY。这是当前D-only动作的呈现判断，不是解除其它模式的Case缺口。F01/G01首用限制和R01/R06/R09的缺资产状态不变。详见`R02_BOUNDARY_RISK_REVIEW.md`与`PEDAGOGY_COMPILER_ACCEPTANCE.md`。

Payoff 优先携带已有 Review 中的 `reviewed_payoff`，要求同题、同方法版本、同组实际动作及自身 Evidence。后备的 `frozen_candidate_transition` 只投影已有有效局部排除：原候选域、唯一自有 decider 产物、精确审阅范围、未核集合与当前生命周期必须一致。多个决定的先后不明、借用其他方法、已闭合或失效依赖均不可投影；分组、路由不伪造候选淘汰。

每个非空 wrapper 保留 origin、baseline_kind、baseline_measured。机械投影是 `structural_candidate_state / false`，不是观察学生的实际路径；只有本 scope 下一个候选核验任务被有效排除关闭，其他候选与 Stop 仍需要，源变化后可重开。它不证明节省阅读、词汇或时间，不证明学生陌生题迁移，更不授权最终答案。两条通道都无支持时仍为 null；不要求 ANSWER 为适配器另造新 Review。后续说明见 `docs/student-pov-copy.md`。
