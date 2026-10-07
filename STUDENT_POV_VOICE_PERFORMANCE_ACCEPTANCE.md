# Student POV Narration Performance v0.1 — R02 A/B

2026-10-08，基线 `main@31a1df7ee10a3a21c221cb791253bdaaa28d7043`。
已完成内部 A/B 工程与试听交付；人工偏好、口语自然度、表演方向与最终放行仍 PENDING。
这是现有 GPT-SoVITS v2ProPlus + 独立认知口播计划 + Premiere 节奏控制的增量。
没有进入 V10、重训、换引擎、启用 Reference Bank 或扩展教学方法。

## 保留的绑定与基线

Student POV Copy / Pedagogy Compiler 保持 0.3.0，Original Question binding 保留。
唯一实验对象为 R02 bounded worked_example；现有 Role、Evidence、Action、Stop、
TELL_NOW 与局部排除权限未改。G01 仍 HOLD / PAYOFF_UNSUPPORTED。

| 绑定 | SHA |
| --- | --- |
| Frozen script | `8a550b12a4a8b4086cc95348831b5071fa404aa1a38cf5c7866a1b3ba1a42771` |
| Final Copy | `97bb3acc705ca2df92d90ba4d635b81cb2a1c53a1aca67499544f9e9a8e99c80` |
| Production Spec | `4702eef6160ca6efdb90c890ee7af5a8e657cf63d6e603d5581b70f077279083` |
| Teaching semantic | `3d0aca78088cdadb57e5505d91a3e369c670a1dc7403bdc699ffb1262a1e18fa` |
| Performance Plan 0.1.0 | `fdd4b67f4ca2a2d175102a2d2dba32fe329320bf34c4f9d1bf323ad32afe4521` |
| Profile | `2515b841c0d10f7316000c6efd6d7da7978f5edcefbaeda89f2b2171370d9c7e` |
| GPT | `351fe019b05281d9b595f67a13b6a5e6834c8a0b8a9d49aa43812e87092237ac` |
| SoVITS | `77020047a47a16da638ab1303a2ad3a64e8d44ccde83f5ee79860f029672716e` |
| Reference audio | `4400ddabb2c31443789f123f3ef9bbaabc19ebf5f18187f6dccd291e69b87e32` |

A 使用本地最新 `new-material-voice-2026-10-08-tail-v1` 已有试听，保留原预览、
工程与声音，不重新生成 A。B 使用完全相同的 Profile、权重、参考与温度，
保留 cut3 / 0.28s。旧 optimized accepted pack 的文件与认可范围未改，
其用户认可不能传给这七个新 Take。

## 意图与真正执行

| Scene / Function | Tone | Energy | Pace | Certainty | Emphasis 数量 | Before / After intent ms | 实际 speed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pov-001 / pain | alert | .62 | .58 | .55 | 1 | 0 / 500 | 1.02 |
| pov-002 / focus | focused | .50 | .42 | .65 | 0 | 150 / 250 | .98 |
| pov-003 / action | conversational | .66 | .62 | .72 | 1 | 100 / 200 | 1.03 |
| pov-005 / payoff | relieved | .62 | .46 | .94 | 1 | 375 / 500 | .99 |

没有为不存在的 Interrupt、Stop 或 Stamp Voice Slot 创建口播。
Collapse、Stop、Stamp 继续保持无 VO；Stop 的本次试听重点是结果后的收束和静默。
强调词的具体逐字范围、来源引用与真实文稿留在本地绑定 JSON，不复制到公开报告。

| Control | Realization |
| --- | --- |
| 每 clip 的 inference speed_factor | APPLIED：真实 run 参数，保守范围 0.96–1.05 |
| pace 意图 | APPROXIMATED：实际听感、音色连续性仍需人工；不是后期 time-stretch |
| tone / energy / certainty / emphasis | UNREALIZED：当前后端没有直接可靠接口，没有换参考来间接伪装控制 |
| pause_before / pause_after | APPROXIMATED：原生 PR 位置已回读；按帧与既有视觉/静默窗口处理最小间隔 |
| seed | APPLIED 采样参数：主 Take 42，关键备用 Take 43；不称为情感控制 |
| gain | 沿用平直 0 dB；未用响度变化模拟 Energy，无 boost/normalize/额外压缩 |

共生成七个新 Take：三个关键节点各两条、聚焦一条。每条有独立 WAV/text SHA、
generation receipt 与 PENDING 听感状态。B 暂选各 scene 的 Take A 作为工程候选，
这不是人类已经选定的“最佳”声音；备用 Take 仍可试听，没有生产五条完整视频。

## 实测时间与制作验证

| Scene | PR Start–End s | Before actual ms | After actual ms |
| --- | --- | --- | --- |
| pov-001 | 2.500–4.875 | 2500.000 | 5291.667 |
| pov-002 | 10.167–12.125 | 5291.667 | 4000.000 |
| pov-003 | 16.125–21.125 | 4000.000 | 9250.000 |
| pov-005 | 30.375–31.292 | 9250.000 | 6708.333 |

实际间隔包括已有读题和 Motion 时间，不表示 TTS 执行了同等时长的表演停顿。
新增 focus/action 窗口延迟分别约 167/125 ms，按 24 fps 量化。
Payoff 的 29.6–30.35s protected silence 优先于新增停顿；不再叠加长等待。
末句完整保留，方法名出现前还有约 1.708s 的 Stop Hold。

48 kHz 单声道 PCM16 交接沿用既有补帧工具，完整 PCM 只做重采样与末尾静音补帧。
按实际声音重新生成 whole-clip 字幕 cue 与窗口检查，不复用旧时间轴批准。
所有音频都能放进既有画面窗口，未重做 AE、字幕风格、Motion、镜头顺序或音乐。
本次独立 cue 未渲染为新字幕，不宣称词级对齐或最终字幕验收通过。

A/B 都是 38 秒、1080p24 H.264 / 48 kHz AAC 内部预览。完整解码无错误，
912 帧解码像素逐帧一致，原音乐源及所有音量包络一致。
B 混音峰值约 -7.5 dBFS；编码后四段实际声音相关系数为 0.9979–0.9996，
统一 1024 样本（约 21 ms）AAC 延迟已记录。信号验证不认证语气、英文/字母读法或自然度。

| 输出 / 凭证 | SHA |
| --- | --- |
| A 预览 | `8e077867ebce8030a1c4dbac14c593b0b346b116f082b668b615fd8aa2822147` |
| B 预览 | `e512038e0288b7219b79a47b036ccd99004be5904c400f9002839fd569a7bd63` |
| A 纯人声（保留实际 PR 停顿） | `50352f14ee062a56b4a8c72f6df833fdb91df83b207afb5918598b672bc2d8d2` |
| B 纯人声（保留实际 PR 停顿） | `78ad03808beccb021404dd8f08d1f33bf6f1e32dceb397fc2e2dccfb8a31c392` |
| B 原生时间线/导出 receipt 文件 | `86699b4a12748894ae836c2503d844496b92097f63c21122d72e8134fa63bac5` |
| A/B comparison | `94f8d74d39565866ec27a4d30667d7f1bd7e86a6a0b5128e95cb17747c1ad419` |

本地 `narration-performance-r1/comparison/` 保存对照页、两版纯人声、comparison.json、
最终意图执行记录、十二问 Human Listening Review、Anti-Overacting 与 Melancholic Drift 记录。
逐 clip 原始/交接音频 SHA、真实参数、实际间隔及 source refs 保存在这些本地 sidecar。
当前工程核验未替任何备用 Take 选择或自然度审核签字。

## 检查与停止状态

全仓 715 项回归快照通过；最终增量专项 60 项通过，含额外四项 A/B 对照控制。
覆盖用户要求的绑定、改稿失效、不支持语气记录、速度/停顿范围、ID 对齐、
Take/旧认可隔离、reference 新凭证、尾音配置冲突、Payoff Silence、Stop 完整性、
新时长重算、公开 false、G01 HOLD 及禁止读 Truth Core/Registry/模型运行时。
额外检查原 PCM 与实际静默、A/B 文件保护、画面变动/解码错误拦截及不完整 sidecar。
已有 ANSWER 校验继续为 82 methods / 20 source documents / generated assets PASS。
258 个教学输入与旧制作资产制作前后文件 SHA 全部一致。

| Review / Release | 本轮状态 |
| --- | --- |
| 工程 A/B | READY_FOR_HUMAN_COMPARISON |
| 人工十二问、英文/字母、尾音、音色连续性 | PENDING |
| NO_MELANCHOLIC_DRIFT | PENDING：有限意图/间隔 lint 无组合提示，尾音观察未知，不代表已通过 |
| Anti-Overacting | PENDING：不由 Agent 宣称更像真人 |
| Narration Performance 0.1 冻结 | EXPERIMENT_NOT_FROZEN |
| Final voice accepted | false |
| Sample delivery allowed | false |
| Public render ready | false |

等待真实 A/B 反馈；没有明显 B 偏好就停止继续堆功能，再判断 Copy、后端、reference
或是否需要复杂 Voice Layer。即使 B 被偏好，也只具备后续单独冻结资格，不自动发布。
公开提交只有工作流、Schema、合成测试和本脱敏报告，视频、声音、真实 Copy、模型、
Adobe 工程及细化凭证都留在忽略的本地目录。

使用见 [Narration Performance v0.1](creative/voice-performance/README.md)。
