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
统一轨迹表驱动 Focus、Camera、短暂填充高亮；同行主要转移 Focus，跨行运输 Camera。
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
四条候选只是提议，不是要求凑四个，也不已获准高亮。Reviewer 可以逐项拒绝或修订。
当前 `UPSTREAM_REVIEW_PENDING`；不伪造 q33 B、R12 Action 或真实轨迹闭环。

```text
python -m unittest tests.test_locating_trace tests.test_locating_recognition_timing tests.test_source_evidence_acquisition tests.test_method_relay_dual_pass tests.test_ae_native_creative_proof
```

以上包含两种不同合成结构：单项命中、跨行重复词仍未命中。它们不认证英语方法实效。
