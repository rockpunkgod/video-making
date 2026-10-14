# 按角色核对动作产物

版本 `role-evaluation/0.2.0`，拍摄检查线为 provisional。统计只用于选题，不产生 ANSWER Review，也不授予影片答案权限。

| 原角色 | 当前自动核对 | 初始检查线 |
|---|---|---|
| locator | 实际 located_evidence 输出是否覆盖明确指定的后续已审证据跨度 | 平均覆盖率 ≥80% |
| reducer | 有已审排除产物且闭合答案可供冲突检查时，统计误排和排除数量 | 样本误排率为0，平均排除≥1 |
| decider | 当前方法所选动作独立覆盖全部选项，唯一保留项等于冻结闭合答案 | 成立率≥70% |
| verifier | 需要独立审阅的预置错误及正确对照输入；当前通用冻结协议没有此测评记录，保持缺口 | 后续检错≥70%，误报为0 |
| framework / interpreter | 后续调用与理解是否合适需人工核对，不借其他方法的答案计命中 | 不设独立拍摄线 |

**F01 的分组不等于排除。** 当前 candidate_partition 把候选分组，不能据此生成“排除了几个”。遇到此类产物，记录缺少排除口径的适配，不把成功分组判作失败，更不虚造排除。

所有输入先经过当前 FrozenSource 门禁；不接受过期冻结、跨方法动作或失效证据。少于十道独立题标记样本不足；同方法同题禁止重复计数。未知不计作失败或零命中。即使达到数字检查线，仍需原有20%人工抽检与内容审核。

命令：`python -m scripts.move_hit_rate --role-records <requests.json> --output <report.json>`。
requests 为数组，每项包含 `bundle`、`status`（相对请求文件的路径）、`selection`（method_id/action_ids）、`observation`。
定位 observation 是 `required_evidence_refs` 数组，引用后续冻结动作 evidence 的 asset_id/pointer/sha；其余当前支持角色用空对象，从冻结动作本身取产物。

角色报告单独保存，不混用旧版人工 hit 标注；不自动写回方法成熟度。真实题、请求和逐题报告留在忽略的 local-data。
