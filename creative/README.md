# V9 Creative OS — frozen delivery and cinematic landscape

`creative_os` 是冻结 Video Package 之上的增量模块。运行时只消费 Package、Manifest、
当前显式提供的状态清单、Delivery Copy 和配音文件；不读 Registry、教学 Markdown 或原始题库。
没有 Analyzer 调用，没有新的 ANSWER Review。发现教学疑点交回上游。

流水线：Frozen Package → Delivery Copy → 七维内部 fidelity review → 实际配音计时 →
Shot Plan → Landscape Render Contract → AE 检查／预览／内部 MP4。
最终公开教学、来源展示、编辑及 Human Taste 审核仍独立，当前全部 PENDING。

## 文案与语义

HumanVoiceWriter 是模型无关协议。`FixtureHumanVoiceWriter` 用于模拟适配测试；
`AstraHumanVoiceAdapter` 只接受显式注入的 transport，没有 transport 会失败。
本轮文案 provider 为 `agent_authored_internal`，未调用 Astra。

每个 delivery unit 保存原 Claim 全文、自身 method/asset、action/evidence/review refs、
protected terms、prohibited implications、intent、tone、pause、breath、emphasis。
每句口播和每个字幕 cue 保留来源引用。引用不能跨方法借用；画面引文必须是已绑定来源的逐字子串。

内部 fidelity review 必须明确覆盖 claim、evidence、role、certainty、quantifier、causality、Stop
七个维度，并绑定当前 meaning/copy hash。AI host 的重述检查不升级为独立人工教学认证。
Semantic Guard / Claim Guard 是确定性引用和扩张 lint 加显式宿主审阅，**不是语义真值认证器**。
未列举的新语义错误可能通过有限规则，必须继续人工审阅。

口播与屏幕文字分开：口播负责动作和刹车，画面只放当前任务、证据或结构。
不使用密集“首先／其次／由此可见”等连接词，也不以网感口头禅代替教学。
Human Voice Critic 返回有限 cliché lint、十维检查列表和 LOW/MEDIUM/HIGH 指标；
真人听感与 Human Taste 保留 PENDING。

## 使用

从仓库根目录运行：

```text
python -m creative_os prepare <request.json>
python -m creative_os validate <replay-request.json>
python -m creative_os build <build-request.json>
python -m creative_os render <render-request.json>
python -m scripts.build_creative_schemas --check
```

prepare request 显式指定 `package`、`manifest`、`delivery`、`statuses`（asset ID → 文件路径）、
`recordings`（unit ID → mono PCM16 WAV）、`output_dir`、可选 `revision`、`voice_provider` 和
`sentence_boundaries`（unit ID → TTS SentenceBoundary JSON 路径）。目录必须是新版本目录。
文件路径是绝对路径；示例和真实题均留在忽略的 local-data。

validate/build/render request 指定上述冻结输入及 `contract`。build 另需 `output_dir` 和
`project_path`；render 另需真实 `comp_id` 和 `output_dir`。build 在官方 checkpoint 之前先将
AE 当前工程另存到指定 V9 工作路径；若该路径已有别的未打开工程则拒绝覆盖。
这避免 checkpoint 的保存动作改变旧工程。所有 AE 写操作使用原有
JUNKDOGE 官方 bridge，不建立第二套桥接。

提供外部 WAV 不需要在线 TTS。可选测试声线：

```text
pip install -e ".[scratch-voice]"
python -m scripts.generate_scratch_voice <voice-request.json>
```

voice request 指定 `delivery`、`output_dir`、`voice`、可选 `rate` 和 `proxy`。
该命令显式调用 Edge 在线语音，需要 ffmpeg；保存真实音频和句子时间戳，
失败不会假装已有配音。它不是 Astra，也不是人类录音。服务行为见
[edge-tts 上游](https://github.com/rany2/edge-tts)。音纹后续调整，当前只用 scratch voice。

## 计时、来源展示和失效

WAV 逐单元测量时长，停顿向 24fps 边界取整，静音真实混入音轨。提供真实句子时间戳时
字幕按该边界展示；跨页仍标注估算拆分。没有时间戳时只做明确标注的句内权重估算。
实际 render 必须有音频；无音频的显式 read-through 仅能用于规划。
音效仅在结构动作加入一次低电平程序点击，没有背景音乐或虚构音乐许可。

Copy Lock 分开保存 `teaching_semantic_sha`、`delivery_copy_sha`、`screen_copy_sha`、
`audio_timing_sha` 和 `editorial_review_sha`。改变文案清除原文案审阅；只改变声线、停顿或
音频时，已有教学／文案结论不自动改写，渲染必须重做。正式文案修改仍需重新编辑审核。
`refresh_creative` 消费新的上游状态清单，复用 V7 的 teaching/source/editorial 失效原因链，
增加 timing/render 失效。缺当前状态时禁止 AE build/render，历史数据可读。
没有后台监听，旧状态快照不能自行感知外部撤回。

Source Display 绑定最终全部场景文字、字幕、方法标注、逐字引文、完整显示结构和图片 hash；
当前没有外部截图，图片集合为空。最终来源审核不会复用旧竖屏或仅题目级批准。
`landscape_delivery.collect` 复制所有冻结输入、实际配音与回放请求；诊断路径改变不改变 render ID。

## 版本和门禁

设计／AE template 0.3.0，Creative schemas/director/timing 0.1.0。
Canonical JSON 使用共享 UTF-8、排序 key、紧凑编码、禁止 NaN 的 SHA-256。
missing 与 null 不合并，数组保序。语义与文案投影不加入路径或生成时间；
Schema 指纹也按解析后的 canonical JSON 计算，生成文件固定 LF；
模板代码记录实际文件内容 SHA，当前版本源码固定 LF。
完整运输契约可以包含诊断路径，其完整 hash 与稳定 render ID 分开。

旧 `content_os`、vertical v0.1/v0.2 design/schema/template/builder 全部保留。
新 profile 为 CINEMATIC_LANDSCAPE，不改变旧默认 API 的输出。
所有 V9 输出为 `INTERNAL_CREATIVE_PREVIEW`，`public_render_ready=false`；
工程合格不意味着教学认证、版权、最终编辑或人工审美通过。
