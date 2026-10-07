# Student POV 新声音试听工作流

这条增量通道把用户要求试用的新声音接到既有画面。它产出内部试听预览，
不把一次模型生成请求记成最终声音验收，也不替代教学、来源、编辑或 Human Taste。

## 可替换的声音生产者

Video OS 只消费 `voice-delivery/v1` 中的 WAV、逐字文稿和文件绑定。
可选的 GPT-SoVITS 生产者独立执行；剪辑模块不导入 Torch 或声音模型。
先核实本地训练任务已完成、交付 Profile 选定的权重及参考音频 SHA，再试用。
不以最大 epoch 或文件名中的日期自行替换已经选定的权重。

```text
<声音环境 Python> voicepacks/tools/generate_gpt_sovits.py
  --pack <选定的本地声音包>
  --runtime <已有 GPT-SoVITS 工程>
  --clips-file <显式文稿列表.json>
  --output <新的本地声音输出目录>
```

文稿列表使用唯一的 `id / text`，从已校验 Copy 的实际 VO 逐字导出。
现有 `--text-file` 单篇入口保持兼容。一次加载模型，所有句子使用同一套
权重、参考音频和 Profile 参数；中文入口保留中英混读。
新训练包未提供 split/fragment 参数时，使用 `cut0 / 0.1s`，不改变其语速参数。
声明 `none;` 后期策略的 Profile 只允许降低过高峰值，不自动提升音量或变速。
所有新声音的听感状态为 PENDING，不能继承参考音频或旧声音的用户认可。

## 准备与逐字绑定

导出声音后，只做 48 kHz 单声道 PCM16 交接。若本机原生剪辑接口按视频帧
截取声音长度，`scripts.voice_delivery.pad_to_video_frame` 在新的文件末尾补
不足一帧的静音。它保留全部原 PCM 样本；不裁尾音、不变速、不覆盖已有 take。

`premiere_production.student_voice.bind_voice` 要求每个 Copy VO scene 恰好对应
一个声音，顺序与逐字文稿一致，且 WAV/hash/实际时长匹配。
显式位置必须在 24 fps 帧边界；句子不得重叠、超出画面或覆盖已有 Payoff Silence。
实际声音不适合画面窗口时，调整已绑定的画面时序，不能删句或捏造更短的教学结论。

语音识别结果只作为读法诊断，不能覆盖文稿、教学事实或人工听感记录。
英文短语、单个选项字母、自然口语和音色连续性仍需实际听感确认。

## 原生剪辑与预览

```text
python -m premiere_production.student_voice assemble <voice-preview-request.json>
python -m premiere_production.student_voice audit <voice-preview-request.json>
python -m premiere_production.student_voice export <voice-preview-request.json>
```

请求显式提供 `prepared_request / voice_plan / project / output / video_output /
export_preset / export_preset_sha`。先打开原画面准备工程，再另存到新试音工程。
A1 放入逐句声音，A2 保持已绑定的钢琴；读取真实素材、源范围、音量与时间线。
所有音轨必须与 Plan 一致，不能夹入旧声音或额外素材。

导出前后重放当前提供的上游状态和冻结 Copy 检查，并重新读取原生工程。
另解码实际 MP4，逐句检查生成 WAV 的信号是否出现在预定位置，拒绝静音、
错源或明显错位。容许并记录不超过一视频帧且逐句一致的编解码延迟；
信号匹配不是读法、自然口语、音色或人工听感认证。
现有视频不覆盖，调用超时保留请求、错误和不确定状态，不自动重试。
试听与画面预览不写入原画面准备物的声音 ready 标记。

```yaml
kind: internal_voiced_preview
voice_status: GENERATED_TRIAL
listening_review: PENDING
user_voice_ready_signal_received: false
final_voice_accepted: false
sample_delivery_allowed: false
public_render_ready: false
```

以上表示内部声音预览可交给用户试听，最终样片资格仍未获得。
字幕、整体节奏和最终听感不会因为实际 WAV 放置通过而自动 PASS。
新的模型、原始/交接声音、真实 Copy、音乐、PR 工程、视频与细化诊断全部留在
忽略的 `local-data/`；公开仓库只提交工作流、合成测试及脱敏验收记录。
