# 成片审阅证据输出 v1

这是当前 authored 制作链的增量产物输出，不是审阅 Agent、评分或自动改片功能。
正常入口不变：`adaptive-episode/run.py → authored_episode.dispatch →
AV_AUTHOR / AV_PLAN → authored_native → AE / Premiere → package[-master]`。
`audit` 只读采集现有 AE 属性、关键帧、缓动、表达式和运行采样；
`package` / `package-master` 在现有成片逐包、完整 take、完整解码检查通过后，
自动从最终 MP4 和同版制作数据导出证据。没有第二套渲染器，不改变声画内容。

新增真人三问门槛后的 `review-copy` 复用同一导出函数，提供完整实际渲染的审阅候选。
总索引以 `media_role=REVIEW_CANDIDATE_AWAITING_THREE_HUMAN_ANSWERS`、
`formal_delivery=false` 标明其状态，收录 REVIEW_CANDIDATE_QA，不能冒充正式交付。
独立字幕模式同时提供 SRT、AE 字幕缺席读回及 Premiere 导入/读回原始收据；不能把
成功导入当作字幕内容已核验。18 帧表面匹配的实际位置、缩放和透明度采样也随 Recipe
事件导出，保持与计划参数及最终截图各自独立的来源分类。

渲染期间由 `gpt-6-luna`、low、独立上下文的只读 agent 等待，主 agent 整理证据。
等待者只报告有用进展、完成或错误，不写 Adobe、不恢复任务、不评价作品。
Adobe 继续保持唯一写执行者。

## 审阅入口与目录

入口是现有媒体目录下的：
`review_evidence/<最终文件名>-<同版绑定哈希12位>/review_evidence_manifest.json`。
制作目录的 `REVIEW_EVIDENCE_RECEIPT.json` 记录其绝对路径、SHA 和成片 SHA；
正常 package 返回值也包含 `review_evidence_manifest`，无需人工整理。

| 文件 | 内容与依据 |
|---|---|
| `video_metadata.json` | 最终 MP4 的 FFprobe 流/容器参数、逐帧计数、流起点差、工具版本、渲染日志位置；流起点差不冒充听画同步感知 |
| `timeline_manifest.json` | 原有场景、计划帧区间、最终 MP4 逐帧 PTS 对应、元素/动作/口播/字幕/音乐关联；不将计划边界说成独立检测到的场景切点 |
| `motion_manifest.json` | AE 原生 transform 的实际数值关键帧、原生插值/ease speed/influence、空间切线、表达式、前中后采样；意群/挑战/Recipe 复用已有读回，配置与运行值分别标明 |
| `audio_manifest.json` | 完整 take/音乐源路径与 SHA、实际源 WAV 参数、Premiere 实际放置、原生音乐音量、字幕对应、重叠、最终混音实际峰值/RMS/EBU R128；工程音量与混音响度分开 |
| `frame_index.json` | 每张最终 MP4 解码截图的帧号、实际 PTS、场景/动作 ID、尺寸、图片 SHA 和成片 SHA |
| `review_frames/` | 每场起中末、已登记重要动作前中后及连续 9 帧序列；1280px 宽 PNG 与全片场景索引 JPG；未识别动作不宣称完整覆盖 |
| `review_audio/final_mix.wav` | 从最终 MP4 解码的 16-bit PCM 混音，附测量日志；已有成片仍是主要声画审阅对象 |
| `source_snapshots/` | 实际工程、主要计划/原生读回/原生源代码的字节快照，SHA 绑定；原件路径另存，避免应用之后保存导致快照失效 |
| `review_evidence_manifest.json` | 总入口、对应成片、commit、工具、文件 SHA、场景/动作/声音/图片数量、完整度、缺失原因及结构验证结果 |

审阅者只需通用 JSON、图片、WAV 和现有 MP4。按
`scene_id → event_id → element_id → ms/帧 → frame_index → 声音事件` 定位。
源工程配置可从快照读取，不依赖仓库 Python 模块。源素材本身保留绝对路径和 SHA，
不重复建立素材库；跨机器移交时应同时提供原有项目所需素材。

## 时间、坐标与证据边界

结构化时间统一 ms，帧号从零起，结束帧为 exclusive。AE 原生关键帧可落在子帧，
保留 `source_frame_position`；整数帧区间只作覆盖定位，不改原生时间。
原始 JSX/表达式与原文件快照保持真实原文及原单位，不改写代码中的秒。
运动分别记录 AE world/parent local/composition/character-range 坐标、参考合成/父对象、
px/percent/degrees 等单位，禁止把世界坐标当作投影后的 4K 屏幕坐标。

`PLAN_CONFIGURATION`、`NATIVE_ENGINE_READBACK`、
`SOURCE_DEFINED_INTERVAL_WITH_NATIVE_RUNTIME_SAMPLES` 和
`FINAL_MP4_FFPROBE_MEASUREMENT` 是不同证据来源。
计划帧号映射最终 PTS，只证明制作帧对应，不是独立的语义切点检测。
截图文件编号与 `sample_index` 是从零起的采样序号；`source_frame_number`（兼容字段
`frame_number`）才是最终视频的源帧号。场景归属严格按源帧落入的半开区间确定，
跨场事件只登记为 `event_context_scene_ids`，不能改变截图所属场景或证明事件可见。
索引同时记录视频流起点、原始 PTS 和 time base；校验检查帧、PTS 与场景边界一致。
程序不追踪最终像素的对象轨迹，不做源分离来猜独立口播起点。
没有记录的口播原生增益、声画校准偏移、可靠渲染墙钟起止时间等为 null 并附原因。
历史工程没有新的采集收据时保留旧键值，缓动缺失为 null，不强制迁移或编造。

已有不完整证据目录保留并报错，不自动覆盖。已完成证据重复调用先验证视频、JSON、
图片、工程快照、源音频哈希及交叉引用；任何绑定改变均不能沿用旧证据。
结构 PASS 不代表观感、听感、教学效果、人类批准或发布资格。

## 验证

`tests/test_review_evidence.py` 检查实际编码小样的导出机制、单位/原生数值保留、
连续序列、缺失值、旧绑定/篡改拒绝和幂等输出。它是工程回归，不代替真实制作验收。
当前真实整片必须仍由正常受保护制作入口完成，再核对 FFprobe、至少三个重要帧、
一个原生动画关键帧事件和一个 Premiere 实际声音放置。测试不产生主观审片结论。
