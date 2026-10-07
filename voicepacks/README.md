# 可替换配音包

当前已接受的声音：[optimized-2026-10-07](optimized-2026-10-07/README.md)。

视频只消费 `delivery.json` 中的音频、逐字文稿及指纹，不导入模型或 TTS 引擎。
配音包可以来自人工录制、任意 TTS 或另一个训练模型。选择声音由制作请求中的
音频路径决定，没有写入全局默认、剪辑代码或教学数据。

交付接口为 `voice-delivery/v1`：每个 clip 提供 `id`、`audio`、`audio_sha256`、
`transcript`、`transcript_sha256`、`duration_seconds`、`sample_rate`、`channels`、
`listening_review`。路径相对于交付清单。可选 `source_binding` 用于调用方携带冻结
文案绑定；本接口不生成或批准教学判断。

换声音时创建另一个目录与清单，运行 `python -m scripts.voice_delivery <delivery.json>`
校验，再把新音频路径及 SHA 交给现有视频请求。已有片段接口的 `text` 使用文稿内容，
`sha` 使用 `audio_sha256`。完整口播可直接选 WAV 导入 Premiere/AE。音频长度变化时
须重新计算字幕和画面时序，不能复用旧时间轴或批准记录。

`scripts.voice_delivery` 只依赖 Python 标准库。可选的 GPT-SoVITS 生成工具单独放在
`voicepacks/tools/`，不会被视频模块导入。删掉生成工具和模型后，已交付 WAV 仍可使用。
新生成文稿默认待试听；本次试听接受只绑定成品示例，不传递给未来配音或整片发布。

现有 GPT-SoVITS 生产者可选消费独立的
[Narration Performance Plan](../creative/voice-performance/README.md)，按冻结认知 Voice Slot
生成有限 Take，并记录实际 speed/seed、分句/尾音参数及未实现意图。
Performance 元数据独立保存；WAV 消费接口、旧 accepted pack 和既有生成入口保持兼容。
