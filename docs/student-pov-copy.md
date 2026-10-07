# Student POV Copy Realization v0.1

Pedagogy Compiler 决定 WHAT TO TEACH；Student POV Copy 决定 HOW IT FEELS TO USE；Motion 决定 HOW IT MOVES；Premiere 决定 HOW IT PLAYS。本层是 `student_pov/`，不是第二个 Pedagogy Compiler。

```text
Frozen ANSWER + current status
 → approved READY PedagogyPlan
 → sealed Copy-facing projection
 → Student POV realization
 → Motion Identity / Shot / VO / Subtitle
 → AE / Premiere
```

“approved”在工程 API 中指 Compiler 当前重检通过且 READY 的冻结教学选择；最终 Copy 的语义保真和自然口语仍必须有另一个精确文案绑定的外部凭证。Human Taste 必须 PENDING，不能由程序自签。

## 不跨越的职责

Copy 不改变 Tell Now/Later、Role、答案范围、Evidence、方法适用、是否跳步或 Stop 状态。`validate_handoff` 在入口先重新核验 Plan 与当前冻结资产；first_touch HOLD 不能偷换成 first_touch READY。可以明确选择 READY bounded worked_example。

候选自然表达使用模型无关 adapter.propose(small_projection)，或显式 `draft_lines`。适配器只获得轻量投影，不拿 Registry/自由求解器。每句候选绑定既有 Plan 字段，主动作/记忆句必须引用各自对应字段。新表达没有最终语义保真和自然口语凭证则 HOLD。测试仅使用模拟适配器，不调用 Astra 或外部语言模型。

## Baseline、Method Path、Removed Work

Copy 正式消费 `payoff.reviewed_support`。该内容只能是上游已有 Review 的 `reviewed_payoff`：同题/方法版本/实际动作、自己的 Evidence、baseline_path、method_path、removed_steps、remaining_steps、cognitive_work、实际 reduction、allowed_claim、cognitive_relief_line、可转用第一动作声明以及实际 Output anchors。

每个 path step 有源中已有 text 与 work_ids；removed 需在 baseline 出现、在当前 method path 消失，不能与 deferred/still_required 混同。reduction 需 before>after>0、ID 数量一致、after IDs 属于 before；Output anchor 必须精确指向当前实际产物及其 hash。算法核绑定和结构，不认证基线路径真实性或推理正确。

没有真实受凭证支持的 removed_work，输出 HOLD/PAYOFF_UNSUPPORTED。不能从“整篇文章很长”“方法名很简洁”“分组后很好看”倒推出学生节省了工作。永久 removed 只在明确限定的 scope 内成立；后续仍要做的词形或上下文不能称“不用做”。

## TYPE A / B / C

| 类型 | 强制事实权限 | 边界 |
|---|---|---|
| TYPE_A Direct Decision | decider + 实际 candidate_decision | 局部 retain/eliminate 不继承整题 answer permission；候选变化须和实际排除一致 |
| TYPE_B Candidate Collapse | reducer + 显式实际 remaining/retained candidate 产物 | 普通 candidate_partition 保留全部候选，只证明组织变化，不能伪称 4→2。当前 Core 没有这种显式剩余产物时诚实 HOLD |
| TYPE_C Reading / Structure Collapse | locator/interpreter/framework + 相容定位/解释/骨架/route 产物 | 保留真实 framework 类型，不伪映射 decide；有据范围/结构简化也不授予答案 |

框架路线不得将 word_form、derivation、number、possessive、gerund_check、context_check 包装成 removed。G01 到名词性节点后的具体词形 deferred，上下文与该节点内部规则 still_required；是否可用动名词不能由本层新分类。

## 学生体验与文案契约

PAIN、INTERRUPT、FOCUS、ONE ACTION、COLLAPSE、PAYOFF、STOP/DECIDE、METHOD STAMP 是八种认知功能，不是固定八幕。可以合并功能、结束更早或留白，不填满30/60/90秒。默认先使用、出现有据效果，再在 Stop 后显示方法名和记忆句；C端不显示 R01/G01 等编号。

first_touch 只有一个 Main Simplification/主动作，并继续受 Compiler 认知预算及 Tell Now 约束。Acquisition 是一个痛点/动作/Payoff/必要边界/记忆句；复杂边界和案例进入 Depth 系列，不在 Copy 层擅自隐藏。worked_example 是边做边学，不等于完整题解。

Pain 来自既有症状或具体题面结构，不造“90%的学生”。Interrupt 只有已批准 Payoff/动作支持才能说。Focus 不把入口升级成唯一决定性证据。动作语言优先看、圈、划、拆、比、对、找、留、排、停；不播放专家的 Role/Evidence/Review 内部链。

`cognitive_relief_line` 必须绑定 source_payoff_ref 与 allowed_claim；无凭证时为空或 HOLD 候选。高风险“不用认识词”同时要求具体这一题/这一步/当前判断、具体词的已有 Evidence 和已批准 shortcut；“做阅读不用背单词”总阻断。

推荐 FinalScript 每 scene 包含 time_range、cognitive_function、visual_state、student_attention、vo、screen_copy、motion_function、evidence_ref、pedagogy_ref、removed_work、output_state、silence_after、notes。时间按版本化中文4字/秒、英文150词/分估算较长口播/屏幕阅读，不声称真实配音精确匹配。

## VO / Screen / Motion 与 Signature

VO 表达学生思考、第一动作、当前判断、节奏、短 Payoff/Stop；Screen 展示原文、Evidence、对比对象、关键词、Candidate、最终结构和实际 Output；Motion 展示有据抽离、重组、关系变化、范围/候选收缩与 Boundary Seal。结构 QA 检测相同 VO 与屏幕文本重复，完整视听重复和审美仍待人审核。

Signature 映射仅协调视觉语法：R01 Overgrowth；R02 Relation Rewire；R06 Missing Mass；R09 Semantic Compression；F01 Axis Regroup；G01 Extract→Route→Seal。映射不提供适用或结论，不能替代 Payoff 支持。本模块不调用 AE，不制作效果，不更改 Shot/Motion/PR 模块。

强视觉事件只能跟随有据的范围/候选减少、Evidence Lock、关系重组、额外块抽离、空位抽离、最终决定或 Boundary Seal。禁止装饰性 Flash/Glitch/无意义 Zoom 作为 Payoff 证明。没有实际压缩时最多是 actual_output_only_no_payoff_claim。

## Silence 与 Explanation Suppression

支持 Collapse/Answer Lock/Evidence Lock/Boundary Seal/Payoff/Transformation 后0.3–1.0秒的 Hold/Silence/Music Duck/Settle 候选。必要 Tell Now 在静默中仍可见且有阅读时间；静默不用于藏边界。

`suppression_qa(copy,coverage)` 只产生审阅候选。coverage 由编辑显式记录画面、Motion、Evidence 均已表达且下一动作不依赖这句，才标 EXPLANATION_REDUNDANT 并建议去掉 VO。Stop 和绑定 Tell Now 的 scene 永远保护；来源 Copy 不改，原最终 Copy Approval 对变化后的候选失效。

## QA、审批与重载

Schema 为 `creative/copy-system/student-pov-copy.schema.json`。CopyAudit 包含第一动作/Role/Evidence/Stop/Tell Now/Payoff、可见压缩、学生操作结构、动作语言、解释密度、专家链泄漏、屏幕口播重复、捷径、禁说、自然口语风险。PASS 仅是 deterministic binding/claim lint；不是完整语义、自然口语或学生体验认证。

`copy_audit.observation_scope=planned_scene_structure_only` 明确这些观察只针对生成的 FinalScript。兼容字段 `cognitive_reduction_visible` 要求计划屏幕确实包含有凭证的 before→after 文本，且 Collapse 绑定实际 Output、Evidence 和 removed_work；仅有 Payoff 记录不能判 true。`student_pov_present` 要求场景有来源绑定的第一动作、Evidence 焦点和完整必要 Stop，不再固定为 true。这两个 bool 均不表示实际画面清晰、学生感到轻松或学会了操作。`actual_visual_review`、`student_experience_review` 和 `human_taste_review` 始终 PENDING；外部 Copy 文案凭证也不能自动替它们签字。

`final_copy_sha` 同时覆盖 script 与逐景 FinalScript；`copy_review` 必须绑定 script_sha/final_copy_sha 并显式确认 semantic_fidelity、natural_speech、layer_division。任何相关文字或场景修改让旧批准无效。AI凭证不升级人工教学认证。Human Taste 14问见 `STUDENT_POV_HUMAN_TASTE_REVIEW.md`，始终等待真实用户/人工意见。

```python
from student_pov import realize, validate_copy
candidate = realize(copy_projection, plan, frozen_bundle, current_status)
validate_copy(candidate, copy_projection, plan, frozen_bundle, current_status)
```

独立 `python -m student_pov realize|validate <request.json>`，只读明确列出的计划/投影/资产/状态和可选 draft_lines/copy_review；不覆盖历史。教学、来源、编辑与公开渲染始终独立，本模块不自动发布。

真实 G01 当前缺已有基线路径/removed_work 与自然 Copy 凭证，学生视角层 HOLD；工程化 Contract 合成测试不补这个缺口。Hero 的 native visual proof 可以绑定 READY worked_example，但不能因此声称新 Student POV 层通过了学生验收。详见 `STUDENT_POV_COPY_ACCEPTANCE.md`。
