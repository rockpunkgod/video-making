# Method Choreography 0.1：方法认知编舞

本模块把当前冻结体验投影为一条状态链：问题 → 注意力进入 → 主动作的物理隐喻 → 信息结构后果 → 有据缩减/局部结果 → Stop → 第一动作记忆。它不生成新口播，也不指定动画实现。

```text
ANSWER：什么是真的
  → Pedagogy：现在必须学什么
  → Student POV：学生如何经历
  → Method Choreography：认知状态如何变化
  → Creative：镜头、构图与视觉处理
  → AE / Premiere：技术执行与最终时序
```

## 现有链路与版本

Motion Identity 0.1 的六种 Signature 和全部 Brand Grammar 文件不变。新层通过方法/签名 ID、版本与四个 Registry SHA 绑定它们，只输出共享的 focus / carry / transform / settle / seal 原则和 grammar ID，不复制颜色、缩放幅度、Effect 或具体时长。

当前 R02/G01 实现状态编舞；其它四个 Golden Methods 只扩充规格，不增加真实教学方法。Schema 固定为 `method-choreography/v1` / `schema_version=0.1.0`。本模块独立存在，不自动接管 Creative OS、样片或生产索引。

## 输入与门禁

`compile_choreography(experience, plan, copy_handoff, motion_handoff, bundle, status)` 必须重检 Student POV Experience、Pedagogy 0.4、两份 Handoff、当前冻结材料与当前状态清单。可显式提供已经存在的 Frozen Method Application；它必须属于相同方法版本、选定动作和 Review，不能用布局标注替代审阅。

READY Experience 可生成工程消费契约，教学/来源/编辑发布仍独立 HOLD。上游 HOLD 默认拒绝编舞生产；`diagnostic=True` 只生成明确标注的当前输入结构诊断，资格不升级。G01 没有合法 Handoff 时沿用 Student POV 的显式诊断输入，不制造 Handoff、Baseline 或收益凭证。

Binding 保存 method/version、Plan SHA、Experience SHA、final_copy_sha、Handoff 内容 SHA、可选 application SHA、父冻结语义 SHA、analysis SHA 与词汇/签名/原 Brand Registry SHA。任何相关源变化、撤回、来源权限或结构编排变化均在下一次 compile / validate / project 前重检。没有当前状态来源时只可历史 inspect，不可放行。

旧 0.3 Copy 的 `analyze_legacy` 可重新核验并保留原 READY/HOLD 状态，报告 `V04_INPUT_REQUIRED`。它不填 Work Delta、不生成新 Experience、不继承旧批准；升级必须从实际 0.4 输入重新生成。

## 状态、对象与后果

每个 state 保存原逻辑对象及 disposition、当前 active scope、foreground/background、当前候选数、关系阶段、已有 route 节点、未决对象、当前产物是否被接触、是否停止及可 settle 对象。所有这些是计划结构，不能证明学生已理解或实际构图有效。

Operation 保存 family/verb、target/preserved objects、来源引用、reversibility、当前有效范围、定性 temporal character 与实际认知变化类别。变更目标必须存在；未申明对象不能被偷偷改变。每个转换必须有 attention/work/relation/scope/candidate/structure/stop 的实际字段变化。只改 stage 标签或 re-layout 字样不算认知变化。

Object Lineage 保存相同 object_id、origin_object_id、source_content_sha 与各状态 disposition。Pedagogy 对象直接复用 ID；已有 application span 按冻结内容和结构位置稳定绑定 ID，保留其原 span_id，不自行分词或识别主谓。原题、证据、条件及未决信息有保护约束。

| 状态 | 约束 |
|---|---|
| protected | 不能退后、删除或消失 |
| defer / background | 保留原内容与可逆恢复，不包装成工作永久消失 |
| unresolved | 不定案、不淘汰、不用 resolved settle 暗示正确答案 |
| remove | 必须已经由当前来源授权，限定当前受审状态；上游变化必须重开 |
| resolved | 只表示当前已有产物，不补完整题目答案 |

候选资格与原选项文本是不同的来源对象。R02 的 D 可在当前有据资格集合中退出；原 options 对象与逐字文本持续存在。剩余 A/B/C 的资格保持 unresolved。

## Physics 与 Signature

| Family | 词汇 |
|---|---|
| Navigation | scan / jump / anchor / lock / return |
| Reduction | peel / mute / fold / tighten / reveal / restore |
| Comparison | align / overlay / split / extrude / reveal_difference |
| Relationship | connect / detach / rewire / reverse / reconnect / lock |
| Classification | float / attract / regroup / cluster / separate / settle |
| Routing | extract / branch / route / resolve / seal |

词汇是认知隐喻，不代表已实现六类教学求解或六类 AE Effect。R01 Extra Block、R02 Relation、R06 Missing Mass、R09 已给压缩结构、F01 已给分类轴、G01 已给空位/路线各有不同 core pattern；交换方法名不能通过匹配。真实辨识度仍等待人看过输出后回答。

真实 R02：anchor → align → overlay → detach → rewire → 已授权候选缩减 → lock current action → recall。当前已有关系记录只提供受审关系断言，没有 actor/action/object 的逐词端点图。运行时绑定它及原 Evidence/工作对象，不解析文字创建角色或连线。`endpoint_mapping=assertion_only_no_actor_span_geometry` 明确保留这一限制；以后细粒度图形仍需要合法的上游标注。

真实 G01：当前 Evidence attention → 已绑定 slot extract → 既有 route_selection → 在同一个 slot origin 上 seal → Stop。额外提供的真实 application 是已有只读冻结跨度，允许的修饰层只能可逆暂缓，不产生 Work Delta。没有 baseline/payoff 就没有 Collapse 或 Payoff Event，也不能越过当前节点给词形答案。

## Collapse、Payoff 与 Stop

Collapse 逐项保留 Pedagogy 的 reduction type、before/after 引用、removed/deferred/still_required 与局部 scope。只有上游支持且在 Experience 中可见时才创建事件。候选数下降、阅读范围下降、关系/结构简化和完成判断不是同一种权限；当前两个真实通道都没有 final answer 资格。

Resolution 只引用当前 primary_action/output_ref，并保留来源 Role、已得产物、未决对象、allowed_claim_ref 和 scope，不输出新教学文本。Payoff Event 只指向有据缩减的 from/to 状态，不生成宣传文案。

Stop 记录 reached state、当前产物引用、unresolved/deferred objects、必要边界 coverage 引用，以及局部结果不能自动推到 final_answer 的 prohibited transition。边界遵循已批准的 Student POV 呈现，不额外生成结果提醒卡片。Memory Closure 在核心动作之后回收同一第一刀和冻结 memory phrase，再交接 method stamp。

## 定性时间与 Creative 交接

temporal_character 仅允许 quick / searching / measured / sudden / settling / held。没有秒数、帧数或旧时间线批准。Choreography 不包含 Camera、Z、blur、颜色、字体、keyframe、音效、音乐、TTS speed/reference/tone/pace 等参数。

`project_choreography` 重新核验所有源后输出绑定、state / operation / object catalog / lineage / attention / collapse / resolution / payoff / stop / memory / temporal signature / risks。下游按这些来源对象导演，不重新判断候选或重解释教学压缩。HOLD 默认不能交生产；显式 diagnostic projection 的 consumption_allowed=false，不能替换已批准成片。

## Audit 与合成 Peel

Deterministic Audit 检查对象存在、保护、可逆性、未决权限、实际状态变化、Lineage/Carry、原题连续、局部 scope、Stop、后置方法名与 core pattern。

- `PRESENTATION_RESET_RISK`：状态之间没有逻辑 Carry。
- `DETACHED_INFOGRAPH_RISK`：与原题来源空间断开。
- `DECORATIVE_CHOREOGRAPHY`：没有认知字段变化，不进入正式编舞生产。
- `PPT_MOTION_RISK`：Reset、装饰变化或没有有效状态变换。
- `SIGNATURE_DISTINCTIVENESS_FAIL`：方法标签与物理组合不符。

R02 的四个关系步骤逐次改变受绑定的比较分组：原文 Evidence → 加入当前候选 → 单独呈现已有差异断言 → 断言与原文/候选关系对照。它们不只换 phase 标签。仅改变 relation_state、保持其它信息结构不变，也触发 DECORATIVE_CHOREOGRAPHY。

这些标记是结构风险，不能证明实际渲染是否 PPT、电影感或好看。`human_taste_review=PENDING`、semantic_truth_certification=false，公开资格 false。

Synthetic Peel fixture 明确供应 core/modifier/protected 标签，数据文字必须带 SYNTHETIC 标记。它只验证 peel A → peel B → supplied core tighten → optional restore → stop：同一对象恢复、deferred≠removed、保护跨度不丢。没有真实句法识别，没有真实 Work Delta、方法认证或 Payoff，永远不能交真实生产。

## 使用与输出

```python
from method_choreography import compile_choreography, project_choreography

choreography = compile_choreography(experience, plan, copy_handoff, motion_handoff,
                                  bundle, status, application=application)
projection = project_choreography(choreography, experience, plan, copy_handoff,
                                 motion_handoff, bundle, status, application=application)
```

CLI：`python -m method_choreography compile|validate|inspect|project|analyze-legacy <request.json>`。请求显式提供 input 文件、application（若使用）、diagnostic 与唯一 output；validate/inspect/project 指定 choreography 文件，legacy 指定旧 copy/plan/projection。未知字段拒绝，既有输出拒绝覆盖。

当前真实回放和逐状态读取稿保存在忽略的 `local-data/method-choreography/v01-r2/`，前次开发回放 r1 留存；公开仓库只保存代码、契约、明确合成样本和脱敏报告。本轮停在中间层契约，不生成新视频或声音，不启用 Creative OS v0.2。
