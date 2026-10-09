# Locating Trace v0.1 — 增量实施记录

基线：main@3618e4b1d91849c25dc727d8d81d39c1bc7bd77e。
Astra 已完成只读设计评审，root 二审后修正同题 evidence 绑定、精确偏移和无命中路径。
本记录不是完整验收通过声明。

| 项目 | 当前证据与状态 |
|---|---|
| Trace 契约、Schema、纯导出 | 已实现；不选择候选、不生成 Review，不改变旧教学材料 |
| 来源/题目/逐项 review/状态校验 | 合成正反例通过；AI 无人工认证升级 |
| Timing 适配 | 复用 0.1.1；无命中、空候选、末项退色、Overflow 有测试 |
| Locating Attention Director | 确定性 span→原词→几何→事件表，呈现与语义分离 |
| AE 薄适配 | 草案已执行合成未命中路径；不是真实题验收 |
| 原生执行证据 | 合成 3840×2160/24，3 原词身份保留；6 表达式检查无错误；109 帧回读；5 张原生 4K preview |
| 合成实测的限制 | 稀疏测试场景；未验证真实长文 DOF、基线放大、速度边界、完整命中接 Lift或成片质感 |
| q33 标注审阅 | UPSTREAM_REVIEW_PENDING；四项 PROPOSED/UNREVIEWED 工作表，零获准候选 |
| q33 B / A-B / 扫描与局部循环 | NOT_RENDERED；无 Reviewed Trace，不生成伪造闭环 |
| Fast 保护 | r27 影片及工程 SHA 已登记，原件不变；新渲染解码像素比较未执行 |
| q33 Human Visual Review | PENDING，旧 r27 认可不转移 |
| 教学人工认证 / 公开来源 / 编辑放行 | 均未获得，public_render_ready=false |

109 项相关 portable 回归通过。它们不是 AE 视觉证据；原生验证限上表实际范围。
真实原文、提议、AEP 和 preview 全部保留忽略目录，公开只提交代码、合成测试和脱敏记录。

合成原生探针首次因测试脚本占位符替换误改图层名称失败；依据服务器 recovery ID
恢复 checkpoint 并修正测试脚本，第三次成功。未盲目重建、覆盖已有认可工程或真实输入。

后续仍须：上游明确审阅与冻结→真实 Guided 接线及边界连续性回读→4K B/A-B
及局部片段→Fast 保护验证→绑定影片 SHA 的人工反馈。全任务保持未完成。
