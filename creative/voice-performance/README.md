# Narration Performance Layer v0.1

这是 Frozen Student POV Copy 之后的独立认知口播计划层。它决定交付方式，
不决定教学事实、答案、Evidence、Role、Boundary、Stop 或 TELL_NOW。
当前仅消费工程 READY 的 R02 bounded worked_example；G01 的 HOLD 和
PAYOFF_UNSUPPORTED 不受声音功能影响。没有进入 V10、换引擎或重训模型。

```text
Frozen Copy 0.3 + 已有 Cognitive Scene / Voice Slot
  → narration-performance/v1
  → 可替换 Producer（本次 GPT-SoVITS v2ProPlus）
  → voice-delivery/v1 + 独立 performance-realization
  → 实测时长 / 新 timing / Premiere
  → 人工 A/B 试听
```

## 表演意图

声音人格是 Bright-Neutral Intelligent Conversation：清晰、直接、克制、有行动感。
只使用 conversational、alert、focused、firm、curious、relieved、restrained 七种 tone。
energy 是说话驱动力，不能投影成响度；certainty 是交付意图，不能升级教学判断。
pace 是相对语速意图，不能通过后期 time-stretch 实现。

| 已有 cognitive_function | Tone | Energy | Pace | Certainty | Before / After ms |
| --- | --- | --- | --- | --- | --- |
| pain | alert | .62 | .58 | .55 | 0 / 500 |
| interrupt | firm | .72 | .64 | .82 | 0 / 250 |
| focus | focused | .50 | .42 | .65 | 150 / 250 |
| action | conversational | .66 | .62 | .72 | 100 / 200 |
| collapse | restrained | .40 | .40 | .85 | 0 / 500 |
| payoff | relieved | .62 | .46 | .94 | 375 / 500 |
| stop | firm | .40 | .35 | .96 | 0 / 600 |
| stamp | restrained | .42 | .42 | .95 | 0 / 400 |

映射是保守实验输入，不是情感认证或永久公式。只有当前 Copy 真有 VO 的场景
才生成 clip；没有 Interrupt、Stop 或 Stamp VO 就不添加。当前 R02 的 Collapse、
Stop 和 Stamp 保持无口播，继承已有 Silence Event 与边界画面。
emphasis 只能引用原 transcript 的逐字子串，保留为意图；禁止新增句子或改标点。
所有语音输入逐字匹配，认为文案限制交付时另提 copy_issue_candidate，不改稿。

Formal Schema：[narration-performance.schema.json](narration-performance.schema.json)。
Plan 绑定 method/plan/scene、script_sha、final_copy_sha、Copy/分析/生产 Spec/教学语义 SHA、
逐字 transcript、来源及性能参数。沿用共享 canonical UTF-8 JSON/SHA-256；key 排序、
数组保序、missing 与 null 区分、无 NaN；语义 Plan 不含时间戳和诊断路径。
Plan 的 transcript_sha 是字符串的 canonical JSON SHA，delivery 的 transcript_sha256
是文稿文件字节 SHA；两者分别校验，不能互换。
改 performance 只改其 SHA；改 Copy 后必须重新 Plan、生成、计时与审核。

## 本次后端真正执行什么

GPT-SoVITS 当前本地版本的 run 接口提供 speed_factor、seed 和分句/片段停顿参数，
没有可靠直接的 tone / energy / certainty / word emphasis 接口。
Adapter 不传虚构 emotion 参数。

| Intent / Control | 本轮记录 |
| --- | --- |
| inference speed_factor | APPLIED：实际调用参数；严格 0.96–1.05 |
| pace intent | APPROXIMATED：暂定 `clamp(1 + (pace-.5)*.25, .96, 1.05)`；听感和音色待人工 |
| tone / energy / certainty / emphasis | UNREALIZED：同一参考和权重，没有直接控制 |
| pause_before / pause_after | TTS 阶段 UNREALIZED；Premiere 新时间线按帧、镜头窗口与既有静默执行，记录 APPROXIMATED 及实际间隔 |
| seed diversity | 实际参数，不称为情感控制 |
| reference bank | 只预留，不启用、不换参考 |

尊重当前 Profile 根字段及 legacy settings 的既有兼容检查；冲突拒绝。
Performance 不静默覆盖 cut3 / 0.28s 或未来用户参数。
所有句子共用模型、参考、温度和 Profile。关键 pain/interrupt/action/payoff/stop
最多三个 Take，其余默认一个；v0.1 默认关键段两条。Take A 使用保守 pace 映射、
Profile seed；Take B 是 speed=1.0、seed+1 的备用试听；可显式要求 C，使用映射、seed+2。
这不是批量生成整片的随机抽卡，也不依据统计自动选“更自然”的声音。
新 Take 都有独立音频 SHA 和生成凭证，PENDING，不继承旧 accepted pack 的认可。
仅过高峰值可衰减；不 boost、不 normalize、不压嗓、不加额外压缩或后期变速。

## 使用现有生产链

请求均在忽略的本地版本目录中，引用显式冻结输入，保留旧输出。
Plan request 提供 copy / projection / plan / bundle / status / spec / output，
可选 overrides，仅允许当前有声 scene 的 intent 与 take_count。

```text
python -m narration_performance plan <plan-request.json>
python -m narration_performance validate <performance-context.json>

<现有声音环境 Python> voicepacks/tools/generate_gpt_sovits.py
  --pack <当前本地声音包> --runtime <已有 GPT-SoVITS 工程>
  --performance-request <producer-request.json> --output <新的 takes 目录>

python -m narration_performance prepare <prepare-request.json>
python -m premiere_production.student_voice assemble <新的 voice-preview-request.json>
python -m premiere_production.student_voice audit <新的 voice-preview-request.json>
python -m premiere_production.student_voice export <新的 voice-preview-request.json>
python -m narration_performance compare <compare-request.json>
```

producer-request 提供上述六个冻结输入路径及 performance_plan；相对路径按请求目录解析。
生产者一次加载模型，按认知 Voice Slot 生成 Take，独立保存 receipts/<take_id>.json、
generation.json 和 performance-realization.json。voice-delivery/v1 的字段完全不变。

prepare-request 另提供 prepared_request、raw_delivery、baseline_generation、selected_takes
（scene ID → take ID）、新的 output / project / video_output 及现有 export_preset / SHA。
本次 A/B 必须沿用 baseline Profile、全部权重与 reference SHA，选中一条只是工程候选。
转换为 48 kHz PCM16，补不足一帧尾静音；不截短原声音。交接清单 ID 恢复为原 scene ID。
另存 selection.json、performance-timing.json 和已有消费者可用的 voice-preview-request。

已有真实视觉窗口、Payoff Silence、Stop Hold 先于新增停顿。停顿按最小间隔处理，
与已有认知静默合并，不堆叠额外长等待。每条记录实际间隔、窗口内延迟及量化差异。
音频长度变化重算时间和整 clip 字幕 cue，不继承旧时间轴批准；这些 cue 是独立数据，
不是已渲染的新字幕或词级对齐。本轮隔离 voice variable，不重做画面/字幕风格/音乐/Shot 顺序。
放不下返回 RETIMING_REQUIRED，之后另做画面重排，不裁、拉伸或删 Copy。
Premiere 保留原音乐源和包络、平直 0 dB 人声，另存工程并回读所有轨道、源范围和声音。

有 performance sidecar 的请求在生成、每次编辑和导出前重放当前状态与全部绑定。
没有 sidecar 的既有配音链保持兼容；已交付 WAV 的消费不导入 Torch/TTS 模型。
原生导出检查编码后每段真实声音，匹配只证明信号存在，不证明语气、读法或教学效果。

compare-request 提供 performance_context（prepare-request）、baseline_index、
baseline_native_audit、production_request、unchanged_inputs（制作前文件 SHA 台账）及新 output。
对照工具检查真实像素、完整解码、同一音乐包络和冻结输入，输出 comparison.json、
final-performance-realization.json、performance-review.json、风险记录、本地试听页和
两版保留真实 PR 停顿的纯人声。没有自动偏好选择或自动重新生成。

## A/B、风险和停止

A 是最新 tail-v1 已有试听；B 使用同一 Copy、Picture、Music、模型和参考。
只改变口播交付与新的 PR 声音位置。实际作品和细化凭证留在 local-data。
Human Listening Review 绑定两版实际音频、视频、时间线与 Copy 指纹，回答十二个问题。

NO_MELANCHOLIC_DRIFT 与 Anti-Overacting 始终等待人工试听。组合 lint 可以提示
连续 slow / low energy / long pause / falling tail / Chopin 风险；没有尾音观察就保留 UNKNOWN。
lint 不自动改音频、不把未发现风险写成声音已自然。
广告 Hook、喊话 Payoff、故意压低 Stop、每句强重音、声音抢画面等由人工明确检查。

没有明显 B 偏好就停止堆功能，判断 Copy、后端、reference 或复杂度问题。
B 明显更好只获得后续单独冻结资格；本次实现不自动冻结，也不授予最终声音或公开放行。
当前始终 final_voice_accepted=false、sample_delivery_allowed=false、public_render_ready=false。

部分外部反馈也可触发实验停止。例如用户只说「B 没明显改善」，先核验 comparison
及两版实际输出的 SHA，另存原话、适用绑定和停止决定，再更新本地实验索引。
记录 `STOPPED_NO_DEMONSTRATED_IMPROVEMENT`，不推断用户偏好 A，不补答十二问。
原 `performance-review.json` 保留 PENDING；完整审核仍遵守 `validate_human_review`
的显式回答要求。停止实验与听感通过分别记录，部分反馈不能授予任何放行资格。
当前 R02 实验已依此停止，详见 [验收报告](../../STUDENT_POV_VOICE_PERFORMANCE_ACCEPTANCE.md)。
