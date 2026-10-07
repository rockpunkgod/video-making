# Removed Cognitive Work — v0.3 audit

本轮把“爽感”限定为有来源的认知工作移除。视觉动效、配乐、字体、快剪、留白或方法名称都不是工作减少证据。

## 结构

```yaml
student_path_comparison:
  support_origin:
  baseline_kind:
  baseline_measured:
  learner_transfer_validated:
  baseline_path: []
  method_path: []
  removed_steps: []
  remaining_steps: []
cognitive_work:
  removed: []
  deferred: []
  still_required: []
```

baseline 只能来自已冻结并绑定当前题/方法/实际动作的凭证。它可能是明确声明的审阅路径，或已有审阅候选域及局部决定的机械状态投影；不得宣称是观测到的学生行为，除非确有真实观察。Compiler/Copy 不自行创造“普通学生必定从头翻译”的对照，不要求 ANSWER 为视频新增 reviewed_payoff Review。

removed：在明确 scope 内该工作确实被已有实际产物和审阅结论取代。deferred：当前动作后暂不做，后续还要做。still_required：当前或随后任务依然需要。deferred 可以同时记为后续仍需完成；removed 不能与二者混同。

TYPE A 需真正局部排除/判断产物；TYPE B 需实际剩余候选，完整候选分组没有任何候选退出；TYPE C 需具体定位/关系/结构产物及有据范围简化。算出 before>after 只核结构，不能认证真实认知负担、速度或教学效果。

## 当前唯一新增 Golden：R02 bounded action

| 项目 | 结果 |
|---|---|
| 对照来源 | 已冻结原候选集合及同一方法自己的实际局部排除 |
| baseline_kind / baseline_measured | structural_candidate_state / false；不是实测学生路径 |
| 方法前的当前任务 | 候选域包含四项，各项尚在本局部任务范围内 |
| 方法后的当前结果 | 已有有效决定排除D；剩下A/B/C，不授予整题答案 |
| removed | 当前候选D的核验任务已被这个有效局部决定关闭；上游失效时重新打开 |
| deferred | 这个有限状态台账未声明另行推迟的任务；空数组不表示整题没有后续工作 |
| still_required | A/B/C各自核验、方法Stop与本次动作Stop；没有删除这些工作 |
| 可说范围 | 当前候选4→3、局部排除；不能说唯一答案已经出来 |
| 不支持的收益 | 学生通常路径、少读全文、少认识词、时间节省、提速和真实迁移均未认证 |
| 第一动作复用 | 模板可描述；learner_transfer_validated=false，不等于学生已会陌生题复用 |
| Copy状态 | AI文本与计划分工复核通过，内部Copy工程READY；实际体验/Human Taste/PUBLIC均未放行 |

当前完整台账、动作与Evidence引用位于忽略的 `local-data/pedagogy/student-pov-r8/R02/cognitive-work.json`。一份真实局部排除支持一个有限简化，不将其他方法的分组或路线自动升级为同样的候选压缩。

## G01 q59 既有草稿同步

| 项目 | 结果 |
|---|---|
| 真实 baseline_path | 未提供已冻结的路径凭证；UNKNOWN |
| 已冻结 method output | with_hint → noun 路线；名词性功能节点，未填词 |
| 可证明永久 removed work | 无可消费凭证；空数组，不编省脑子结论 |
| deferred | 具体词形：派生/单复数/所有格/动名词相关结构核验，仍须后续处理 |
| still_required | 后续节点句法、搭配、上下文/内容核验；词形仍未闭合 |
| “排除全部动名词” | 禁止；现有实际 Stop 明确不允许 |
| “不用认识单词/不需要词汇” | 未提供当前具体词的安全捷径凭证；阻断 |
| 首次教学投影 | 十条未知/当前必要 Tell Now 未能安全分级，HOLD/PEDAGOGY_OVERLOAD；未知 Caveat 不因调用方遗漏而被隐藏 |
| bounded worked_example | 工程冻结投影 READY，公开资格保持 false |
| Student POV Payoff | HOLD/PAYOFF_UNSUPPORTED，不作为真实成功样例 |

原题正文、实际证据、真实候选脚本与路径缺口报告只在忽略的 `local-data/pedagogy/`。本公开报告不附题面、答案、音视频或未经许可的片段。

## 调整方向

下一步若上游已有可信的当前动作 work-reduction 记录，可原样冻结并消费。届时核：baseline 与 method 的同一任务、移除的 work IDs、哪些只是延后、实际产物 anchors、当前 Role、必需 Tell Now，以及短文案的语义保真/自然口语。缺任何一项继续 HOLD，传播性不能覆盖 Practical Use。

当前0.3门禁同时要求 baseline 的每个 work_id 有明确去向，remaining_steps 完整对应 deferred/still_required；第一动作明确不可迁移时不放行。当前G01稿位于 `student-pov-r8/G01`，已同步自然表达并绑定AI文本复核，完整必要边界仍在。改好表达不能补出缺失的真实工作减少凭证；r4及此前稿仅作历史。
