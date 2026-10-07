# Swiss Cognitive POV 0.1 验收

基线 `main@adff3939f769d631a7ac6e8fc6d5f939045b3601`。
本报告只包含流程、状态和可核验的工程结果。真实原题、口播、音乐、视频、
Adobe 工程与最终画面绑定保留在忽略的 `local-data/cognitive-pov-r1/`。

| 验收项 | 结果 | 证据与限制 |
| --- | --- | --- |
| 冻结消费 | PASS engineering | 已有 ACTIVE 资产、精确 Action/Method/Review、源跨度和当前状态 |
| ANSWER 修改范围 | 纯导出增量 | 增加命令、只读 exporter、Schema；Core/Registry/教学事实未改 |
| 工程试片 | PASS engineering | 一个 G01 bounded worked_example，20 s / 1920×1080 / 24 fps / 480 帧 |
| 原生 AE | PASS engineering | 字体/文字/层集合/关键帧/相机/边界原生回读；480 原生 TIFF |
| 原生 Premiere | PASS engineering | Motion、单段 VO、独立钢琴、原生字幕；软件未代替 PR 混最终片 |
| 最终媒体 | PASS engineering | 全片解码、48 kHz 双声道、精确采样口播尾部、最终停留原生像素一致 |
| 字幕 | PASS engineering | 六条实际原生 sidecar 文字与冻结 Copy 一致；最终烧录画面已检查 |
| Pedagogy Plan | HISTORICAL_ONLY | 原 r2 为0.1历史，当前消费被0.2门禁阻断；新 r3 worked_example READY，但旧画面没有覆盖新完整 Tell Now |
| 新 Student POV Copy | HOLD | 缺已有审阅支持的 baseline / removed_work，不能宣称 Payoff 成功 |
| 声音一致性 | PENDING human listening | 使用最终接受参考，一次连续生成；ASR 仅辅助对齐 |
| Human Taste | PENDING | 工程检查不能替用户或真实学生作审美、认知体验判断 |
| 教学发布 | HOLD | AI reviewed，未独立人工认证，不给框架动作补最终词形 |
| 来源展示发布 | HOLD | 实际题面/文字/最终帧另绑定；公开使用权限未获批准 |
| 音乐发布 | HOLD | 用户本地录音仅内部 scratch，未取得录音公开许可 |
| 编辑发布 | HOLD | 最终 Copy/字幕/声音/画面需审核，本轮未签批准 |
| `public_render_ready` | false | 工程试制成功不放行公开渲染 |

样片首先展示完整未填原题，随后聚焦已有动作对应的区域。已有上下文暂时退后，
目标结构收紧，呈现当前名词节点；原区域恢复后保留原 Stop。消费者看不到方法编号。
没有解出答案，没有创建 Review，没有因镜头缩小而声称整题或词汇工作已经消失。

这是 Swiss Cognitive POV 的原生视觉证明。它不是新 Student POV Copy System 已经
通过真实 Payoff 验收的完整样片；新层的候选脚本、必要证据缺口和人工口语审阅单独交付。
未来文案变化必须重新绑定 Plan、Copy、VO、字幕、画面和编辑审核，不能复活旧批准。

2026-10-07 完成审计后，Compiler/Copy 契约升级为0.2。G01 新 Plan 完整保留十条 Tell Now；旧20秒 Spec 只覆盖先前的部分边界。可选 Plan 绑定检查新增同一父资产/语义/方法版本/实际动作及逐字 Screen 边界覆盖；旧渲染不能通过换新 Plan SHA 冒充当前完整样片。真实学生视角文案仍 HOLD，旧视频保留为历史视觉证明。

本轮测量的两组原生停留在 18 s 和 19 s 的无损帧相同；这证明静止，
不证明学生已经读完全部边界。现有 20 秒长度是视觉原型，不拿它覆盖 first_touch 的
PEDAGOGY_OVERLOAD。强可用性与真实审阅优先于传播和画面冲击。

2026-10-07 定版验证：本轮新增 50 项合成测试全部通过，包含 Compiler / Student POV 的
36 项与冻结方法应用、动效、声音尾部、原题先展示的 14 项。完整共享工作区回归运行
611 项通过（数量为执行时快照，包含独立声纹工作流的测试）；详细日志仅保留本地。
`python -m answer_engine validate` 返回 82 methods / 20 source documents，Registry 和
generated assets 均 PASS。`git diff --check` 通过；本次提交未改 Core、Registry 或既有 Case。

自然口语写作原则与可修改位置另见 [文案 Agent 交接说明](docs/student-pov-natural-copy-handoff.md)。
它供后续提出表达改进，当前不会覆盖旧最终 Copy 或将 HOLD 候选自动批准。
收到新的上游撤回/来源状态后，下一次执行必须重新校验；本地快照不会自行实时感知撤回。

0.2审计修复后完整回归628项通过；ANSWER 校验仍为82 methods / 20 source documents / generated assets PASS。当前合同与历史状态分开记录，原音视频和工程文件未改，也未上传；最新真实材料缺口见 [黄金方法交付状态](docs/golden-method-delivery-status.md)。
