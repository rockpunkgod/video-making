# 2025 新课标 I 卷阅读 D 篇：完整讲解内部试制

本轮在 V9.1 方向验收后增量实现完整篇目视频，覆盖四题、20 个讲解单元。
成片 336.292 秒，1920×1080、24 fps、48 kHz 双声道；由 Premiere 原生导出。
真实题面、解析、讲解稿、声纹配置、音视频及 Adobe 工程只在忽略的 `local-data/reading-d-2025/`。
本报告不转载题目、答案或录音，也不构成教学认证或公开发布批准。

## ANSWER 先补齐，再冻结消费

初始本地整卷 Blind 扫描中的四题均为 `needs_evidence`，没有闭合答案或执行动作。
用户随后明确要求在本地 ANSWER 补齐，并提供解析版 DOCX。该授权只用于本篇显式
宿主审阅；不是给 Video OS 自动生产教学 Review 的通用许可。

本篇 AI 宿主审阅材料包含冻结原文/选项、全部候选的直接文本比较、方法的实际辅助
动作与边界、篇级顺序以及逐句讲解。先作题面观察，再对照用户解析；记录解析段号
与原文位置的差异，未直接照搬解析。AI 宿主自审仍是 `ai_reviewed`，
`independent_human_certified=false`，未声称独立人工或教学效果验证。

原 QuestionAnalyzer 要求由合格的 decider 产物闭合答案。本片实际使用的定位和解释
动作不能因此获得 decider 角色。为避免伪造归因，新增显式宿主篇级审阅纯导出：

```text
python -m answer_engine.reviewed_passage_export <已有host-review.json> <新的导出目录>
```

它只校验和封装显式输入，不分析题目、不创建 Review、不读取 Registry 或 Reveal。
`schemas/reviewed-passage-export.json` 定义输入；输出类型为 `frozen_reviewed_passage`。
这是内部篇级传输契约，不是把旧 `QuestionAnalysis` 的未闭合状态改成已闭合，也不是
旧 FrozenAssetExporter 接受了新类型。Registry、旧分析器、Case 和旧发布门禁保持不变。

每个候选都需要自己的证据跨度与审阅理由；直接文本判断标为 `direct_text_review`，
不记作某个方法的成绩。方法动作仅记录冻结版本允许的辅助 Role、实际产物和 Stop；
跨题证据、缺候选、错引用、无边界、方法编号进入面向学生的文案均拒绝。汇总仅能在
最后一个单元引用全部题目的已审阅保留判断。结构检查不是语义真伪认证。

当前附加契约采用共享 Canonical JSON：UTF-8、键排序、无冗余空白、数组保序、
缺失与 null 有别。重复导出的语义绑定一致，生成时间只影响 envelope。
本篇传输保守绑定整个 payload，包括冻结方法卡及来源说明；payload 中的任何
变化都需重新导出。它尚未提供旧 V7 的细粒度 metadata/rights/presentation 失效分类，
不能用作公共发布接口或宣称达到细粒度生命周期兼容。来源另有 `source_sha` 校验，
改变来源也不能沿用旧状态。缺状态、撤回、替代、stale、blocked 均阻断后续生产。
静态清单不自动感知外部撤回，需由上游提供更新文件。

## 声音、画面与实际生产链

```text
显式 ANSWER 宿主篇级审阅 → 纯冻结导出 + 当前状态
→ 绑定讲解稿 → 本地已接受 VoiceDesign 配置 → 实际口播时长
→ 确定性版式与原文划线 → AE 原生运动帧 + 已验证静止画面
→ 冻结原文字幕 + ASR 时间锚点估算 → PR 原生整片导出
```

- 声音采用本地用户已接受的 v6_plain / 第六版“平实讲解”。20 段完整生成，保存配置
  指纹、种子、输入文本、运行环境和音频 hash。它是 VoiceDesign，不是身份锁定的
  个人训练模型；跨句音色一致性与实际听感仍需人工试听。
- 保持常速，不剪停顿、不自动变速。段落长度取实际声音与原文阅读估算的较长者，
  再对齐 24 fps。全文阅读速度估算为每秒 2.5 个英文词，不冒充测得的学生阅读速度。
- 上方持续显示当前题干；原文在固定区域逐步划线，下方展示绑定判断与选项。
  采用暖白、墨色和低饱和绿，无内部方法编号，无新增自由 Hook。
- 每场原生渲染前 4 秒 TIFF 动效；最后一张无损帧与原生 6 秒帧逐像素相同后，
  才允许延长静止画面。共 1,920 张原生运动帧；未调用不稳定的 AE H.264 导出。
- 字幕始终使用冻结稿，ASR 只提供字符时间锚点并插值；ASR 同音、繁简、英语识别
  误差不改文案，也不自动授予试听 PASS。字幕时序标记为估算。
- 发现 DirectWrite 将可变中文字体误选为 Thin，已通过 `freeze_caption_font` 固定
  常规 400 字重，并绑定本地字体 hash。字号 50 的字幕投影已逐场抽帧检查。
- 背景音乐沿用用户提供的一首本地录音，仅降低音量并淡入淡出；曲终后保留纯人声
  回顾。不扩展音乐分析/生成系统，不上传商业录音；音乐公开权利仍未确认。
- AE 保存独立、可编辑的 20 场视觉/声音 master；字幕由独立 ASS 投影烧录进交付
  视觉素材，不声称该 AE composition 自带原生字幕。PR 保存独立工程及四个章节标记。

## 可重放接口

`creative_os.passage_video.prepare/validate_plan` 检查冻结文案、当前状态、字体、音频、
时间顺序及每场来源。`ae_production.passage_execution` 核验原生文字/字体/绑定并生成
可延长的运动头；`creative_os.passage_delivery.assemble` 生成字幕和整片视觉/人声。
`premiere_production.passage.export_internal` 在导出前后检查状态和绑定，拒绝旧输出覆盖。
长片使用独立检查，未放宽 Hero 的 10–15 秒契约。

可选字体依赖：`pip install -e ".[passage-captions]"`。本地 TTS/ASR 环境与模型由调用方
显式提供，不作为项目强制依赖，也不联网下载。配音和 ASR 的入口分别为：

```text
python -m scripts.generate_passage_voice <本地request.json>
python -m scripts.audit_passage_voice <本地request.json>
python -m scripts.freeze_caption_font <本地可变字体.ttf> <新的本地regular.ttf>
```

请求显式提供 bundle/status/profile/model/output；ASR 另提供 voice_root/asr_model。
发现未完成输出目录时停止核对，不自动覆盖或重复触发 Adobe 操作。工具超时需要
先检查宿主真实状态。现有录音复用需通过文本、配置、音频和冻结材料指纹校验。

## 本轮验收与剩余门禁

| 项目 | 结果 |
|---|---|
| 完整篇目内部工程交付 | PASS：四题、20 场、约 5 分 36 秒 |
| 既有全量回归 | 546 项通过；随后最终篇级专项 15 项通过，含 6 项新增交付测试 |
| 冻结导出只读性与重放 | 同输入语义绑定一致；原 Blind 快照保持原 hash；纯导出前后输入 hash 不变 |
| 视频技术检查 | 全片解码通过；1080p24、双声道 48 kHz；20 场最终帧检查 |
| 最终声音 | 使用 v6_plain；自动 ASR 诊断完成，独立逐句人工试听未完成 |
| 教学 Release | HOLD：AI 宿主审阅，不是独立人工认证 |
| 来源/音乐 Release | HOLD：仅内部使用，实际展示与录音权利未获公开批准 |
| 编辑 Release | HOLD：冻结稿/字幕已绑定，最终人工编辑批准未完成 |
| PUBLIC_RENDER_READY | false |

本地 Manifest 保留 `copy_lock`、实际展示片段/文本/帧指纹、原生导出回执、声音配置、
上游状态、项目/文件指纹及独立门禁。GitHub 只保存工作流、正式契约、脱敏说明和
明确合成测试；不上传真实讲解 Review、视频、录音、题目或 Adobe 工程。
