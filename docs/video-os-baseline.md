# Video OS 基线与职责边界

> 历史基线文档：描述 18afe8a 时的初始缺口，不代表当前能力。当前入口、实际生产证据与阻塞见[当前生产工作流](workflows/CURRENT_PRODUCTION_WORKFLOW.md)；本页正文保留作历史对照。

基线：video-making `18afe8a`；检查日期：2026-10-05。

Teaching Engine != Video Production OS。ANSWER 是唯一教学事实源，Video OS 只消费被冻结、可追溯的结构化资产。

## 已有能力与缺口

ANSWER 已有单题/整卷分析、Method Registry、Evidence Graph、执行轨迹、审阅撤回和内容投影。旧 `content-export` 1.7.0 包含答案状态、方法链、方法版本、实际动作、证据图、短版稿和 Stop Rule，但缺少完整题面、精确审阅凭证、来源使用信息及跨生产资产失效绑定。`eligible_for_review` 不表示可以发布，`safe_for_release=untested` 不升级为 true。

基线没有 Video OS 的 Candidate、评分、排序、导演、Package、时间解析、编辑审核或 AE 渲染服务。此次增加冻结导出和下游生产域；原有 Registry、教学规则与分析器保持原样。

## 可用的真实工程试制资产

| 资产 | 已有动作 | 允许的首轮 scope | 审阅限制 |
|---|---|---|---|
| 2025 I q36 / F01 | 三分动作中的句型分组 | method_action_demo | AI post-reveal；不提供整题定案 |
| 2025 I q59 / G01 | 空位功能导航 | method_action_demo | AI post-reveal；不把具体词形归因给 G01 |
| 2021 I q26 / R02 | 新的 style-only 限定动作 | method_action_demo | 旧混合归因已撤回；仅用新的精确绑定记录 |

选择顺序为 Review cleanliness > Teaching clarity > Visual demonstrability > Brand priority。R01 不是首轮硬目标；撤回或语义存疑的 R01 不作正向 Pilot。

全部原题与审阅全文位于忽略的 `local-data/`，来源仍为本地研究/再发行未核实。内部工程试制不代表来源可以公开使用。已有 Demo Score、审阅结构通过和答案一致均不证明方法正确、学生学会、提速或 Signature。

独立人工审核采用 just-in-time：只审核真正进入公开队列的 2–3 条，不启动全题库人工认证项目。
