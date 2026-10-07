# Pedagogy Compiler v0.4

0.4 是独立、显式选择的新 Plan / Handoff 契约。它从原 Frozen Asset 和当前提供的 Status 重新编译，记录唯一主动作、真实 Work Delta 和认知对象状态。它不修改 ANSWER、Registry、原题、Action、Evidence、Role、Stop 或已有 Review，也不自动接入当前 Student POV 0.3、画面和声音生产链。

## 版本与迁移

`CURRENT_VERSION = "0.4.0"`；现有调用的默认 `contract_version` 保持 `0.3.0`，保护既有消费者。新调用必须显式指定 `contract_version="0.4.0"`。`schemas/pedagogy-plan.json` 同时校验历史与新契约，独立的 `pedagogy-plan-v03.json` 原样保存旧 Schema，`pedagogy-plan-v04.json` 和 `pedagogy-handoff-v04.json` 定义新结构。

- 0.1 / 0.2 / 0.3 可以只读 inspect，不覆盖历史产物，不改变旧版本标签。
- 0.1 / 0.2 不能当前消费；0.3 在兼容链仍需原冻结输入、当前 Status 和原版本披露审阅重放。
- `required_version="0.4.0"` 拒绝 0.3；迁移只能重新 compile。旧 Plan 仅用于审计对比，不是教学输入。
- 现有 Boundary Risk Review 仍绑定其原 0.3 基础 Plan。0.4 先从同一冻结输入重新编译并验证这个绑定，再产生新 Plan SHA，不创建新 Review。
- 所有 CLI 输出拒绝覆盖。当前下游尚未切换，消费新 Handoff 必须实现显式的 0.4 adapter。

```python
from pedagogy import compile_plan, validate_plan, copy_projection, motion_projection

plan = compile_plan(
    frozen_bundle, current_manifest, selection,
    mode="first_touch", channel="video",
    boundary_review=existing_boundary_review,
    contract_version="0.4.0",
)
validate_plan(plan, frozen_bundle, current_manifest, required_version="0.4.0")
copy = copy_projection(plan, frozen_bundle, current_manifest)
motion = motion_projection(plan, frozen_bundle, current_manifest)
```

`selection`、Review 和展示字段必须已有精确绑定；上例不授权创造教学输入。

## 一次最小学习动作

`first_touch` 明确包含 pain、first_signal、first_action、judgment_point、immediate_output、stop、memory_phrase。教学文字仍是已有字段的受限投影；不是新写的 Student POV 文案。`primary_simplification.before / operation / after` 只使用有效支持的结构与实际产物。

首次 video 默认一个 primary action。只有选中实际动作的冻结依赖构成单一终点，其他动作又都是它的依赖，才标为 supporting；独立动作不能藏入 supporting。多个独立主动作使 first_touch HOLD。`deferred_actions` 记录已有 Reviewed Work 中待执行的任务，不声称这些任务已产生新的 Action Artifact；`work_delta.deferred_work` 保留完整依据。缺少支持时为空，不猜后续解题动作。

0.4 的 first-touch `core_actions` 预算统一为 1；原 0.3 的预算与哈希不变。Supporting 只交接来源引用，不能与主动作争夺前台中心。预算是工程限制，不证明学生已经理解。

## Work Delta 与局部 Payoff

`work_delta` 保存 baseline_work、method_work、removed_work、deferred_work、still_required_work、unsupported_savings。支持只来自既有 `reviewed_payoff` 或精确的冻结候选状态变化；每个工作单元绑定源、实际动作、自己的 Evidence 和 Review。

- baseline 缺支持时为 null，加入 `BASELINE_WORK_UNSUPPORTED / PAYOFF_UNSUPPORTED / COGNITIVE_RELIEF_UNAVAILABLE`，保持 HOLD。
- removed 是当前已审阅范围内确实关闭的任务；deferred 仍要回来；still_required 继续保留。分类必须互斥、覆盖已有 baseline，且匹配实际 Output 锚点。
- 方法路径、实际产物与结构缩减必须一致。Reducer 的 partition 不自动成为淘汰，Locator 不获得最终答案，route 不免除词形或语境核验。
- `unsupported_savings` 单列时间、阅读、词汇、心理量化和整题捷径收益，不能进入 allowed_claim。确定性 Claim lint 不能代替语义认证。

`payoff` 增加 structural_before / structural_after / work_delta / allowed_claim / forbidden_claims / payoff_scope。Scope 枚举为 local / candidate_set / evidence_scope / whole_question；当前 bounded method_action_demo 不开放 whole_question 或 decision_completion。局部 decider 的排除仍不能输出整题答案。

`cognitive_reduction.types` 是有限结构分类。本版只报告来源实际支持的 candidate_reduction / scope_reduction / attention_reduction，其他类别保留契约但不凭英语文本自动推断。`cognitive_load_projection` 记录对象 ID、候选数和 Evidence 范围；没有关系数量支持时为 null，不把结构投影写成认知负荷下降百分比。

真实 R02 的 baseline_kind 为 structural_candidate_state，baseline_measured=false：它是已有选项域，不是观察得到的学生思考路径。4→3 支持当前一个候选任务关闭；其它候选核验和 Stop 仍 required。本次源记录的 deferred_work 为空，不能把 Prompt 中的示例补成教学事实。G01 的 route/noun-like 结构没有 Reviewed Baseline，因此继续 HOLD。

## Tell Now 的呈现职责与覆盖

原 Tell Now / Tell Later / Engine Only 政策和风险审阅不变。`boundary_presentations` 额外记录 action_stop / misuse_prevention / scope_limit / candidate_status / condition / counterexample_guard，以及 spoken / screen / motion_state / persistent_context / combined 的 delivery form。

Tell Now 表示当前学生必须获得，不要求每条 VO 朗读。已有外部 Boundary Review 可决定多个边界共用字面呈现、Evidence 聚焦和未闭合候选状态；每项 coverage 保存源 item、原文范围、展示表达和精确 review_ref。没有这种凭证时保留完整字面 screen 呈现。当前 Stop 不能通过后台标签消失，语义近似不能自动合并。

Coverage 是计划交接义务。Renderer 是否真正展示、学生是否获得该边界仍需后续检查和人工记录；本模块不代签这些结果。

## 认知对象交接

`cognitive_structure` 只包含已有对象、来源关系、对象集合和 attention_transition。状态为 focus / preserve / background / defer / remove / unresolved / resolved / protected。

- 原题文字、Evidence、实际 Output、当前 Stop 和 required 工作义务保留保护；原题选项文字不会因淘汰而被删除。
- 候选 eligibility 是独立状态对象，已支持淘汰才可 remove，且只在当前 reviewed state 有效；上游变化后必须重检。
- background / defer 必须 reversible，有明确 restore_state；不得变成 remove。protected 不能背景化、暂缓或删除。
- 未闭合答案与剩余任务仍以 unresolved 对象保留。
- attention_transition 只交接 from_scope / to_scope 的对象 ID 与来源；没有 zoom、相机、坐标、blur、keyframe 或 AE 参数。

可选 `structure_input` 只接受已有 `frozen_method_application`，重新核验当前源、实际动作与自有 Review。Span 角色及关系逐项来自该冻结标注，不解析英语，不发明 WHO/ACTION/OBJECT。本轮 modifier/subject/predicate/object 的 Peel 场景仅为 SYNTHETIC 契约、暂缓及恢复测试。

## 后台丰富，消费者精简

Copy Handoff 交接七项学习单元、唯一主动作、原题、可用局部 Payoff、工作分类、必要边界覆盖、Evidence 引用和禁止 Claim。它不携带完整 Guard、内部风险矩阵、Review 正文或完整审核台账。

Motion Handoff 交接对象状态、已有关系、结构缩减、工作 ID/来源和覆盖义务；去掉边界表达全文、字面覆盖范围和工作文字，不生成新教学文字，也不指定特效。重复引用收进 `reference_catalog`，每项仍保存完整 asset_id / pointer / sha；`catalog_ref` 由规范化引用 hash 生成，碰撞、悬空引用、未使用引用和无对象绑定的工作 ID 均拒绝。字面呈现细节由 Copy 与 Plan 保留。两种 Handoff 都保留 required / unresolved，不能为精简删掉未完成任务。

## 守恒与审核

`compression_audit` 将选中方法、实际动作和原题字段的冻结叶节点逐项绑定，并检验：

```text
source_truth_items = presented_now + deferred + engine_only + explicit_merge_coverage
omitted = []
```

这是选中输入范围的交接守恒，不是整套 ANSWER 库的语义认证。Presented 表示计划中有字段、对象或已审阅的覆盖义务，不表示画面已经渲染。语义 Stop 优先按原披露分类；Engine Only 只能接工程身份、状态及成熟度元数据。

`first_touch_audit` 检查字段、主动作数量、受支持 Payoff 和剩余工作保留。`human_pedagogy_taste` 始终 PENDING：第一刀是否清楚、是否过载、Stop 是否易懂、下次是否可用，都不能由程序自签。三类 Release 保持 HOLD，`public_render_ready=false`。

CLI 继续使用 `python -m pedagogy compile|validate|handoff <request.json>`，0.4 请求增加 `contract_version`，可选提供 `structure_input` 路径。Validate / handoff 请求的同名字段可要求精确版本。历史 `inspect` 请求只含 plan 路径，`inspect-handoff` 只含 handoff 路径，两者永不授予当前消费资格。真实回放、请求与结果只保存在忽略的 `local-data/pedagogy/compiler-v04-r2/`；工程验收见 `PEDAGOGY_COMPILER_V04_ACCEPTANCE.md`。

## 0.3 兼容链与既有披露规则

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

0.3 first_touch 的结构预算：core_actions≤2、primary_boundary≤1、memory_phrase=1、primary_evidence_cluster≤1、simultaneous_concepts≤3；另有学生字段 180 字/记忆句 80 字的保守长度检查。它们是 provisional 工程限制，不是认知科学精确指标。Student POV 的首次教学进一步要求只有一个主动作，不能借 Compiler 的上限偷塞两个主简化。0.4 已统一 primary action 上限为 1。

worked_example 明确记录原题→观察→实际动作→Evidence→当前判断→Stop；默认 scope 是 method_action_demo。原分析的答案/闭合保留为后台 Guard，前台 answer=null、may_output_final_answer=false。某个 decider 的局部排除也不能自动包装成整题答案。

counterexample / boundary / transfer / hard_case 缺对应已绑定 Case 时为 `UNAVAILABLE_EVIDENCE_GAP`。不创造反例、迁移题或新的 Review。案例覆盖和方法成熟度分开，仍不自动升级 candidate/Useful。

## 指纹、重载与放行

沿用 UTF-8、键排序、无无意义空格的 Canonical JSON；数组顺序保留，missing≠null。`plan_sha` 排除生成时间/运输校验值；`content_sha` 与 envelope_sha 分开。来源、方法、实际动作、当前必要边界、表达选择、政策/Compiler 版本都进入计划绑定。

`validate_plan(plan,bundle,status)` 重新生成全部投影；单纯重新 seal 不能掩盖答案、Role、Evidence、Stop、成熟度、确定性或披露分层的修改。当前状态缺失/撤回/替代/语义变化/权限变化/动作或审阅依赖失效时消费阻断。`inspect_historical` 只核历史完整性，永不授予当前消费资格。

兼容链的 Compiler、Plan 与 Handoff 契约版本为 0.3.0，披露 Policy 保持 0.2.0；新的显式契约为 0.4.0。Schema 支持完整性检查 0.1/0.2 历史结构，`inspect_historical` 对它们返回 LEGACY_CONTRACT/consumption_allowed=false；`validate_plan` 与 `validate_handoff` 阻断它们的当前消费。迁移必须用原冻结资产及当前状态重新 compile，重新生成投影和下游绑定，不能修改旧 Plan 的版本标签或覆盖原文件。旧包既有 Review、源事实、答案、成熟度与历史结果均不被覆盖，旧 Copy/渲染不能继承新 Plan 的 READY。

`copy_projection / motion_projection / validate_handoff` 都要求当前提供的上游状态；静态文件不会自行感知外部撤回。收到新状态后，下次消费前重检。Copy 只获得轻量教学字段、已有 Evidence、Do Not Say 和绑定；Motion 只获得认知关系，不指定 AE 特效。

三类公开 Release 和 `public_render_ready` 在本模块始终 HOLD/false。READY 表示当前内部冻结投影可以消费，不是独立教学认证、来源许可、编辑释放或学生教学效果证明。

## CLI 与本轮真实状态

独立 `python -m pedagogy compile|validate|handoff|matrix <request.json>`；请求显式列 bundle/status/selection，输出不可覆盖历史。同类操作没有自动解题或目录扫描。editable 安装同时提供 `pedagogy-compiler`。

没有显式风险审阅的真实投影仍在忽略的`local-data/pedagogy/compiler-r5/`，F01/G01/R02的默认首用分别因9/10/9项边界HOLD。本轮R02经用户要求的实质风险审阅，另存`local-data/pedagogy/boundary-risk-r1/R02/`：基础九项原文及台账未改，1/2/3/8功能合到一个关系比较和候选状态，4/5/6/7/9后置；新first_touch/worked_example工程投影READY。这是当前D-only动作的呈现判断，不是解除其它模式的Case缺口。F01/G01首用限制和R01/R06/R09的缺资产状态不变。详见`R02_BOUNDARY_RISK_REVIEW.md`与`PEDAGOGY_COMPILER_ACCEPTANCE.md`。

Payoff 优先携带已有 Review 中的 `reviewed_payoff`，要求同题、同方法版本、同组实际动作及自身 Evidence。后备的 `frozen_candidate_transition` 只投影已有有效局部排除：原候选域、唯一自有 decider 产物、精确审阅范围、未核集合与当前生命周期必须一致。多个决定的先后不明、借用其他方法、已闭合或失效依赖均不可投影；分组、路由不伪造候选淘汰。

每个非空 wrapper 保留 origin、baseline_kind、baseline_measured。机械投影是 `structural_candidate_state / false`，不是观察学生的实际路径；只有本 scope 下一个候选核验任务被有效排除关闭，其他候选与 Stop 仍需要，源变化后可重开。它不证明节省阅读、词汇或时间，不证明学生陌生题迁移，更不授权最终答案。两条通道都无支持时仍为 null；不要求 ANSWER 为适配器另造新 Review。后续说明见 `docs/student-pov-copy.md`。
