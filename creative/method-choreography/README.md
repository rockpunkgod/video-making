# Method Choreography v0.1

本层消费当前 Pedagogy 0.4 和 Student POV Experience 0.4，描述认知动作怎样由一个受绑定状态走向下一个状态。它独立于仍然保留的 Method Motion Identity 0.1。

`physics.json` 是六类认知操作词汇；`method-choreographies.json` 是六种现有 Signature 的上层规格。它们不提供教学事实、句法识别、候选判断或使用资格。当前真实 runtime 仅实现 R02/G01 的 bounded replay；R01/R06/R09/F01 仍为规格，不自动生产。

| 契约 | 作用 |
|---|---|
| `method-choreography.schema.json` | 完整状态、操作、对象传承、局部结果、Stop 与来源绑定 |
| `choreography-projection.schema.json` | 给 Creative 的交接，保留当前消费门禁 |
| `synthetic-peel-input.schema.json` | 明确提供的合成跨度与状态；无真实英语规则 |
| `synthetic-peel.fixture.json` | **SYNTHETIC CONTRACT TEST**，defer → tighten → restore |

实现位于 `method_choreography/`。新命令不调用 Adobe、声音或 Renderer。完整接口、真实输入限制和兼容分析见 [使用文档](../../docs/method-choreography.md)，工程证据见 [验收报告](../../METHOD_CHOREOGRAPHY_ACCEPTANCE.md)。

所有状态保留逻辑对象 ID、来源内容指纹与原题关系。原句和候选原文不被资格变化改写；deferred 不变成 removed，未决对象保持开放，已支持的当前产物才可 settle。视觉像素、字体、色彩、镜头、帧数及音频参数归下游决定。

机械 Audit 不代签教学或电影感。真实方法辨识度、对象连续性是否看得见、Stop 是否自然、动作是否增加理解与记忆，均等待绑定实际输出的 Human Taste Review。当前没有新视频，全部 PENDING；公开资格始终 false。
