# Locating Trace v0.1

本模块消费上游明确审阅的定位表达，不选择英语词汇，不推断词性、同义、答案或方法信用。
审阅对象与呈现调度分离：ANSWER/Host 决定哪些跨度值得注意；导演决定怎样呈现。

## 上游工作流

1. 读取当前冻结 Passage Bundle、Status 和既有 locating input request。
2. 提议工作表保持 `PROPOSED / UNREVIEWED`；注意资格、审阅引用尚缺时不可冻结。
3. 上游 Reviewer 显式提供 `reviewed-locating-trace.json` Schema 要求的材料及凭证。
   每条 assertion 绑定自身 subject SHA、同题 ID、字面证据和审阅理由。
   target、逐候选和 acquisition 分别审阅。导出器不生成这些内容。
4. 纯导出：

```text
python -m answer_engine.reviewed_locating_export REVIEW BUNDLE STATUS NEW_OUTPUT --request EXISTING_REQUEST
```

输出 `trace.json` 与初始 `status.json`，拒绝覆盖历史目录。请求引用和 SHA 必须与既有
请求、同题及资产绑定一致；没有 Reviewer 输入不能运行导出。

`ai_host` 仅映射 `ai_reviewed`。AI 不能声明人工认证；本轮所有公共资格保持 false。
SHA 证明材料一致，不证明真实审阅实际发生、独立性、眼动、学生阅读速度或教学有效性。

## 结构与验证

Source binding 保存 asset、semantic、passage、source、原篇级 review SHA、稳定 question ID。
Target 区分保留的原题信息与实际搜索表达，二者都是原 stem 精确半开区间。
Strategy 是上游配置，不是同词性万能规则。

Candidates 保留全部审阅记录，按非重叠原文偏移排序；重复字面用不同偏移及 ID 区分。
`inspected_continue` 只表示注意离开，不能排除句子或选项。
`unresolved` 不升级命中；`not_eligible` 保留记录但不高亮。
只有明确 `acquired` 可以绑定 sentence confirm / lift。

v0.1 acquired 必须位于同题既有 Segment evidence 内，evidence 又必须位于获准确认的
原文 sentence 范围内。绑定源引用、目标对应理由与独立 assertion；只授予
`locate_for_further_inspection`，不授予答案权力。

Canonical JSON 复用 `video_contracts.sha`：UTF-8、排序键、无无意义空白、数组顺序保留、
缺失不等于 null。语义 payload 不含生成时间，sealed content/envelope 沿用现有规则。

## 状态与失效

每次制作重新调用 `require_trace(trace, trace_status, bundle, source_status)`。
来源非 ACTIVE、绑定变化、Trace review 撤回/替代/失效均拒绝。制作方须取得上游最新状态，
初始 ACTIVE 不代表永久有效。静态文件不能感知外部撤回；不承诺后台监听。

## Director 与 AE

`creative_os.locating_attention.build_plan` 消费上述四个输入及实际原生字形 readback。
`native_geometry(request, audit)` 校验原 spec、完整字对象身份及 sourceRect，拒绝估算几何
冒充原生回读。精确跨度映射到原词 ID；不使用 `.index()`，不扩大到其它出现位置。

复用 recognition_timing 0.1.1，按距离配置 transfer，逐候选显式 recognition 时长。
不足时间通过 Overflow 报告所需帧数，不丢候选、不压缩辨认。
无 acquired 时最后项退色；空候选无占位命中。剩余时间分配至接近路程，不尾部填等待。

`locating_native.prepare` / `script` 是现有 fulltext rig 的薄适配。
统一候选事件时钟驱动 Focus、Camera、短暂填充高亮；Focus 保留真实逐行路线，
Camera 使用独立、单调的纵向运输曲线，不复制行内字形中心与回行的波动。
使用已有原字对象、轻微放大与透明 Lift，不新建替代句子。
适配只作用 Guided；新输出目录与工程不得覆盖 r27/r28。

当前适配保留既有 acquired endpoint 及尾部 lock/lift 时码。不同端点或 Overflow 要求
明确新版本导演与渲染绑定，不放宽旧 fulltext Request 的 20 秒验证。
无 acquired 的原生适配在扫描结束截断合成时长，防止旧默认 Lock/Lift 执行。
这不截断配音：本专项无声，声音仍暂缓；未来有声音需重新 timing。

现阶段原生 probe 只验证合成未命中路径的表达式、109 帧回读和 5 张原生 4K 图像。
不能据此宣布真实 q33、命中接 Lift、跨行观感、Fast 像素保护或人工审美通过。
完整速度/加速度边界和旧轨迹接入还需原生实测，未授权正式交付。

## 本地 q33

复用原 `locating-input-request-r1/upstream-locating-request.json`。
新资料在忽略的 `local-data/method-relay-dual-pass/locating-trace-v01/`：
`review/` 保存提议工作表；`native/` 保存合成执行凭证；`receipts/` 保存保护指纹。
四条原始候选工作表保持提议历史，不自动变成审阅。随后本轮获授权的 ANSWER/Host AI
逐项完成显式审阅：一项背景表达未获准注意，三项成为内部工程辨认序列。
审阅、原工作表及纯冻结分别保存于不同文件。保留原题记忆信息，另明确审阅有限定位词，
不由 Renderer 偷换搜索任务。AI 自审记录不代表独立人审、真实眼动或方法实效。
当前 q33 Trace 已冻结并已执行真实原生补丁；r2 已生成诊断成片，
Astra 只读审阅指出相机碎波动与填色遮字，新修正版正在核验。
不添加 R12 Action 或答案信用，不继承旧 Human Review。

纯导出入口兼容既有请求尚未包含新增 source_sha 的情况：核验原请求已有的 asset、
semantic、passage、review 指纹，完整 source_sha 由冻结 Bundle 与当前 Status 另行验证。
不会为了本模块改写既有请求。

原生读取 Fast 全部原对象的 168 帧表达式结果触发 120 秒超时，桥接进入 degraded/
sentinelInFlight 状态。该步骤是只读，补丁尚未执行。必须等待桥接恢复并读回实际状态，
不能盲目重发。后续将拆分属性核验，保留原生保护与媒体复用证据。

```text
python -m unittest tests.test_locating_trace tests.test_locating_recognition_timing tests.test_source_evidence_acquisition tests.test_method_relay_dual_pass tests.test_ae_native_creative_proof
```

以上包含两种不同合成结构：单项命中、跨行重复词仍未命中。它们不认证英语方法实效。

## Guided 高亮颜色与原字保护

新呈现计划记录版本化 palette：题干线索橙色 `[0.95,0.74,0.43]`；
比较中蓝色 `[0.64,0.79,0.90]`；只有上游明确 acquired 的候选，
在其 recognition 窗口结束后转橙色。仍为低饱和短暂填充，不画下划线。
“蓝→橙”只表达定位已取得依据，不授予定案或排除权限。

填色放入原文词对象所在的 3D 层组，层序在全部原词之后，Z 在字后；
避免新顶层被 2D overlay 隔离而遮淡原字。AE 颜色表达式显式输出 RGBA。
原生验证逐帧检查 palette、层序、深度与 opacity，不能只看 JSON。
规则默认作用新 Guided；已认可 Fast 的旧色与原表达式保留。

相机与焦点分别回读验证，不再强制 Camera Y = Focus Y + offset。
逐帧运输不反向，识别事件共用时钟；边界速度连续性只证明技术衔接，
不能代替实际连续影片的流畅度审核。

`locating_render.py <render-config.json>` 消费当前 source/trace 状态、补丁与
原生运动回读，分批渲染 4K TIFF 并生成 SHA 清单、归档及无声 B。
每批开始和编码前重查状态，禁止旧工程覆盖或未绑定工程渲染。
`locating_comparison.py <render-config.json> <old-guided.mp4> <old-sha> <new-output>`
复用相同 request 的 A，输出完整 B、扫描、识别循环、命中到透明提取片段及 A/B。
独立视频全部原生 4K；对照画布为 4K，两侧内容明确缩至 1080p，不冒充全幅原生。
循环是原片段三次剪辑重复，不是额外阅读事件。Human Review 绑定 B movie SHA。

## 内存故障边界

真实 r5 渲染出现 AE 导出错误与内存耗尽反馈。`purge_between_chunks` 不能保证
3D renderer 分配完全释放；不能因此盲目循环重试或自动沿用失败回执。
`locating_render` 在 Windows 每批开始前要求至少 1 GiB 可用物理内存。
`ae_production.memory_guard` 用 Windows Job 限制新启动的原生进程树，并监测
系统可用内存和超时；只回收自己启动的进程，不处理已存在的 Adobe 会话。
原生 aerender 的短区间独立实例实验结果另行记录，未经帧核验不视为 render PASS。

当前保护规则按用户明确配置：系统可用物理内存至少 1 GiB；新启动进程树
内存预算最多 10 GiB。低于余量线禁止启动下一批，受保护进程运行期间
低于线则终止其自己启动的进程树。显式配置低于 1 GiB 或超过 10 GiB
进程预算会被拒绝。阈值不是已证明的稳定性修复。

最新用户指令覆盖此前 12 GiB 方案：当前系统可用物理内存停止线为 1 GiB，
启动前与运行中使用同一阈值。新进程树上限仍为 10 GiB，未解除超时、
工程保护或当前上游状态核验。12/8 GiB 记录保留为历史，不是当前默认值。
