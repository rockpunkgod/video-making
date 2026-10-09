# Method Relay × Dual-Pass Creative Proof

## v0.1.1：Guided 方法说明增量（当前交付）

2026-10-09，基线 `main@71e05697e6cef2f011e40c9c744b42180b6deaf7`。
当前含声片为 `local-data/method-relay-dual-pass/pr-r3/METHOD_RELAY_DUAL_PASS.mp4`；
AE 为 `dual-r4/PROJECT_DUAL.aep`，Premiere 为 `pr-r3/METHOD_RELAY.prproj`。
仍是 **SYNTHETIC / VISUAL-ONLY** 内部研究，1920×1080、24 fps、46.5 秒、1116 帧。
旧 P0、r2 全片、旧 take 与上一轮验收记录均保留。

本次按用户确认的 Astra 建议，只替换前三段引导文稿：

| Clip | 新文稿 | PR start–end / 秒 | 末尾补静音 / samples |
|---|---|---|---|
| locate | 题目问谁，先用‘查地图’这件事找原句。 | 15.750–18.916667 | 320 |
| carry | 先抓主要动作，再看是谁做的，把主干读清楚。 | 20.000–24.000 | 1920 |
| basis | 拿这句作依据，选项也按同样三项一一核对。 | 26.250–30.125 | 1680 |

compare / verify 文稿与原 Producer WAV 逐字、逐字节复用，放置时刻和完整长度不变。
新增录音仍用同一 GPT-SoVITS v2ProPlus、模型、reference、speed=1、cut3 / 0.28 秒，
没有训练或换声音系统。三段新录音原长分别 3.16 / 3.96 / 3.84 秒，均适配旧时刻。
交接仍为 48 kHz PCM16 mono，仅补帧边界静音；没有截断或拉伸语音。
`voice-r2/generation.json` 明记三段新生成和两段复用的原 delivery / generation SHA，
没有把组装凭证写成一次生成五段。五段试听均为 PENDING，不继承旧认可。

Guided 比较区增加一次小栏头 **谁 / 做什么 / 对象**（27.000–33.750 秒）；
三列原生 x 为 478 / 666 / 831，Fast 不显示。预览发现栏头接近背景句，
已移至独立的列头行后重新构建。B 主体强调持续在 31.000–33.750 秒的
“换了人”整句观察窗口；这是口播段配合，不声称已有逐词强制对齐。
Fast、相机路径、镜头顺序、两遍 0.25 秒释放、合成轨迹与总时长不变。

前三段说明逐段绑定已有冻结方法的 `core_action / decision_rule / stop_rule`，
保存 artifact、版本、semantic SHA、字段 pointer / value SHA 和文稿 SHA。
当前清单失效或这些绑定改变后拒绝继续制作；旧 0.1.0 冻结请求仍能重放。
这些是**一般方法动作与边界字段的表达绑定**，不认证合成分区、语法附着或答案。
原文、候选状态、deferred、真实 R02 的 Evidence / Action / Stop / Role 及 Frozen Copy
未改动；G01 HOLD 不升级。三句短说明不能替代真实案例的必要边界审核。

实际证据：

- 原生 AE 完整输出 1116 TIFF，queue DONE；归档校验后清除本次 loose 帧。
  17 个源对象与原题身份延续、99 个回溯属性及 3 个表达式检查继续通过。
- 新旧 AE 画面前 **15.5 秒的 372 帧解码 hash 全部相同**，包括 Fast 与物理回溯。
  记录为 `guidance-r3/unchanged-content-proof.json`；两份 director 与 trajectory 也相同。
- Premiere 原生导出、全片解码通过；与本次 AE 画面对比 **1116 帧**，
  SSIM 均值 **0.999842885**、最低 **0.999663**。
  五段实际编码 waveform 相关度 **0.999984897–0.999997897**，AAC 偏移 1024 samples。
- Agent 查看最终编码的 93 个 2 fps 抽帧（12 张顺序拼图）、3 个完整尺寸关键帧，
  以及原生栏头 / 主体强调预览。采样中未发现新增叠字或裁边；不代替人工实时观看。
- 相关 **44 tests PASS**，`git diff --check` 通过；登记的 **655 个受保护文件** hash
  全部不变，包含教学核心、冻结输入、选定模型 / reference / Profile 与旧交付。
  没有宣称重跑 ANSWER 全量回归或审核整个磁盘。

| 指纹 | SHA-256 |
|---|---|
| 最终含声 MP4 | `a94d36dd3d262a7fd0ced57dd6619dc22adca9687bbc652fe0539804f27856d8` |
| AE 画面 MP4 | `83eb51404b9717a10cffbc02d457fc0a5ad0e3a57284c1f286cb8606cbc85cf6` |
| 可编辑 AEP | `49a763f2ba4a5ef4f8b686af96eceeab759aca25b01b0806a70eb69767c8d52c` |
| 可编辑 PR | `f13cdd1b14627bf50d506850abd5282f7d549e730cf8ea40288243438dcdd87f` |
| fixture canonical | `5e802d0d9cf9c4f36d3d7767ba480e8f0a4376b5cd5ffb9f05b31c4049d1e566` |
| 全片 spec | `b01f298cf31addbe309acd253a2e8ae4aec209d97cf2d6e9989139201af872bc` |
| native TIFF archive | `00e2c98dcb45e3b82fbe1664f1da821f2794a2be0912282b5b5605d455ad6b80` |

当前制作凭证与增量 Manifest 留在忽略目录 `guidance-r3/`；历史根 Manifest 不覆盖。
用户对 r2 的“这个可以”仅记作有限反馈，并提出补充慢速方法说明。
2026-10-09，用户对本片反馈“可以可以，效果很好”，并明确“听感先不管”。
整体视觉体验记录为 `USER_ACCEPTED_OVERALL_VISUAL_PREVIEW`，绑定上方最终含声 MP4 SHA；
画面、动作接棒与节奏保留为本片已认可方向。逐项问题未回答，不推定每项 PASS。
听感仍为 PENDING / DEFERRED_BY_USER；不改原声音生成凭证，也不推定声音自然度通过。
新增独立人工视觉凭证，原媒体与制作凭证保持原状；此认可不扩展为真实教学认证。
原 Chopin scratch、片段和 PR duck keys 相同，公开来源权限仍 UNKNOWN / HOLD。
`final_voice_accepted=false`、`sample_delivery_allowed=false`、
`production_eligible=false`、`public_render_ready=false`。GitHub 仅提交工作流、合成 fixture
和脱敏报告，不上传媒体、工程或模型。

## v0.1：上一轮原始验收记录

2026-10-09。基线：`main@a0d1695c10455f37ff5a0f4586e8ef532eddcbf8`。
结果：**原生工程制作与技术交付完成；人工观看、试听和真实教学认证未通过。**
本片始终显示 **SYNTHETIC / VISUAL-ONLY · 合成技术研究**。
这是同一空间中对象接棒与双节奏导演的实验，不是已认证的真实高考题解答。

## 当前资产与最小增量

复用 r7 已认可的标志词提示、范围预期、0.25 秒物理剥离、上下停放，
现有原生 AE JSX / 3D Camera / Classic 3D、冻结输出校验、文本度量、
`voice-delivery/v1`、可替换 GPT-SoVITS Producer 和原生 Premiere 剪辑链。
没有重新验证另一套剥离技术，没有新增求解器、视频 OS、VFX 工具或声音系统。

R02 q26 当前冻结动作仅支持排除 D，A/B/C 仍未决，且缺少本片所需的完整
定位—分段—比较 span 接力。G01 q59 仍为 navigation-only / HOLD，
2025 阅读 D 的审阅资产也未提供同题完整多方法接力的结构绑定。
这些是阻止**真实教学完整演示**的缺口，不是渲染失败。没有补造 Review 或改答案闭合。

因此采用明确标记的合成句子、原题、分区与预先提供的 A–D 状态。
导演只消费 fixture 明示的对象、视觉停放锚点和结果，不分析英语生成新判断。
图形锚点不是已认证的语法附着关系；暂缓片段为 **deferred**，没有宣称永久删除。

三个轻量中文名为冻结输出现有名称投影：**关键词追踪 / 长句拆骨 / 谁干的陷阱**，
版本均为 1.1.0，记录 artifact、semantic binding、名称 hash 与 JSON pointer。
没有直接读取 Registry 或教学 Markdown 补事实，也没有新造“长句瘦身”品牌。
名称来源有效不能为合成动作适用性背书；真实题中方法必要性仍未建立。

最小增量位于 `ae/experiments/method-relay-dual-pass/`：单片 fixture、对象绑定、
两套显式导演时刻、原生构建/读回/渲染及现有 Premiere 交接。
共享教学模块、R02 frozen Evidence / Action / Stop / Role、原 Frozen Copy 均未改动。

## 可观看交付

全部路径相对于仓库，本地结果根目录为 `local-data/method-relay-dual-pass/`。
代码与脱敏报告入库；MP4、WAV、AEP、PR 工程、模型和原始教学资料仅留在忽略目录。

| 交付 | 本地路径 | 实际结果 |
|---|---|---|
| 完整含声技术片 | `pr-r2/METHOD_RELAY_DUAL_PASS.mp4` | 原生 Premiere H.264 / AAC，1920×1080，24 fps，46.5 秒，1116 帧 |
| 接棒单独片段 | `p0-r4/P0.mp4` | 原生 AE，20 秒、480 帧，无口播 |
| 完整可编辑 AE | `dual-r2/PROJECT_DUAL.aep` | 原生文本、3D Camera、物理层、表达式与完整时间线 |
| 接棒可编辑 AE | `p0-r4/PROJECT_P0.aep` | 独立保存，未覆盖旧片 |
| 可编辑 Premiere | `pr-r2/METHOD_RELAY.prproj` | V1 原生全片，A1 五段口播，A2 Chopin scratch |
| 解题接力记录 | `METHOD_RELAY_TRACE.json` | supplied input/output、源跨度、原生 ID、scope、Stop 与合成候选状态 |
| 双导演清单 | `DUAL_PASS_DIRECTION.json` | 同一轨迹，两套镜头/动作/读题停留与实际 VO 时刻 |
| 镜头时间码 | `KEY_SHOT_TIMECODES.md` | 定位、剥离、接棒、比较、核验与五段 VO |
| 文件与制作凭证 | `DELIVERY_MANIFEST.json` | 源码快照、输入、项目、媒体、27 项主要凭证与发布状态 |

最终完整 MP4 SHA-256：`46ca152ef552afaca99c7d83566b6f7e3c1f56b3b9a6baa3c078241073a854dd`。
接棒 MP4：`96cd420b26e3c5785f0a5a4adcb28092e64a79d5bce6b9694886b7991b5fe991`。
完整 AEP：`d1291b9050cace3706469ee59952cbb508a3d24674fb894e40b4e4a4c3f88c6b`。
接棒 AEP：`a15d9b62cc0f8d4b855c2218353cac38d321de9069d14809958ce085c3225665`。
PR 工程：`658753d2ebb179059e5d981bbf3bc5cb5fffd1efd5c98ef25f0bf828fedaf3f1`。

## 连续对象与双速

5 个原句分区、12 个原选项部分，共 **17 个唯一原生文本对象**贯穿两个 pass。
Source Text 无动画/替换；原题也保持同一原生 ID 与逐字内容。
证据句从原阅读环境提升；暂缓片段沿视觉连接停放上下；主干收紧后继续留存；
原选项进入同一比较空间，三个对应列对齐。核验时先把主干移回原槽位，
再让暂缓片段沿分阶段路径归位，避免返回途中叠字。

Fast 为 **02.5–12.5 秒，共 10 秒**，无 VO，每个方法只出现一次小中文名。
12.5–15.25 秒物理回溯；99 个原对象/平面/相机属性与初始状态读回一致。
Guided 从 **15.5–46.5 秒，共 31 秒（含结尾停留）**，独立设计镜头、
识别预期、阅读停顿与五段引导。两遍共享 trajectory，未以视频倍速代替导演。
两遍剥离的执行段均为 0.25 秒，展开的是观看与认知停留。

| 关键镜头 | Fast / 秒 | Guided / 秒 |
|---|---|---|
| 从任务锁定原句 | 2.65–3.2 | 16–19.7 |
| 原句提升、定位接给分区处理 | 3.2–3.65 | 19.7–21.3 |
| 第一片段释放 | 4.03–4.28 | 21.9–22.15 |
| 第二片段释放 | 5.23–5.48 | 24.7–24.95 |
| 主干留存、原选项进入比较列 | 6.1–7.2 | 27–29.3 |
| 主体差异检查 | 7.3–8.6 | 30.1–34.8 |
| 其他动作差异 | 8.65–9.65 | 35–38.1 |
| 回原句核验、合成状态落定 | 10.1–11.6 | 40–43.5 |

以上落定仅对应合成 fixture 提供的 A；不改变真实 R02 的 bounded 状态。

## 实际技术证据

- AE 使用 Classic 3D（原生标识 `ADBE Advanced 3d`），实际渲染完整 TIFF：
  P0 480 帧、全片 1116 帧，queue 为 DONE。每帧 hash 与压缩档案校验后，
  才清除本次 loose TIFF。FFmpeg 仅封装原生帧、解码与检查，没有替代 AE 动画。
- 两遍原对象 ID 一致；主干在接棒采样点 opacity 为 100；每遍 12 个比较列读回
  `dx=0`，原 A–D 顺序保持，行位置 645/715/790/850，未使用 A/B 换位制造比较。
  3 个表达式无错误，验证结果未截断；无可见内部方法编号。
- 顺序检查全片 2 fps 的 93 个抽帧位置、剥离 24 fps 的 48 个位置、
  归位 8 fps 的 40 个位置：23 张顺序拼图全部由 Agent 查看。
  修正后采样中未发现叠字、裁边或归位替身；运动段允许短暂侧面/运动模糊。
  这不是人工实时播放、审美或教学效果批准。
- Premiere 原生整片导出、全片解码成功。两路画面统一 timebase/PTS 后对比
  **1116 帧**，平均 SSIM **0.999843904**、最低 **0.999663**；另查看最终编码
  的 16 个关键抽帧位置。此项证明画面通过剪辑编码保留，不认证审美或语义。
- `python -m unittest tests.test_method_relay_dual_pass tests.test_ae_native_creative_proof`：
  **41 tests PASS**。覆盖受保护源跨度、暂缓状态、前驱产物、原生替换/身份丢失、
  列对齐/回溯、独立双速、完整逐字 VO、PENDING 与官方恢复 ID。
  没有宣称本轮重跑 ANSWER 全量回归；共享教学代码未修改。
- `protected-final.json`：先前登记的 **565 个文件全部原 hash 不变**，包括
  教学核心/导出/Compiler/Copy、选定冻结材料与旧 r7 视频及 Adobe 工程。
  这是登记范围核验，不声称审计整个磁盘。声音模型、参考与 Profile 也再次核对相同。

fixture canonical SHA：`0863be34d63c9fdba0c6b616c4b6c9765a83c0f6564f6f75b25e064e64c0b0a4`。
共享 trajectory SHA：`d59b2e2d4b531a4eab9c1319fd329ff0d8b165a59d522a720a3adaeb59be2f62`。
最终双速 spec SHA：`7d242871f109205936a3b3ba0d414c430835f5b542b39fb9f3e3e1f898f7a97a`。
完整 native TIFF 档案 SHA：`00959d38a78088dceffef678df60e65d0178c5661c2acfe015121975ba9f114b`。

## 声音与剪辑

使用现有 `new-material-voice-2026-10-08-tail-v1`、GPT-SoVITS v2ProPlus，
同一模型和 reference；未训练、换权重或开发新声音层。
五段合成引导文稿先冻结，再逐字生成；speed=1、cut3、fragment_interval=0.28 秒。
新录音均为 `listening_review=PENDING`，不继承旧声音认可，也没有宣称情绪控制已实现。

Producer WAV 原为 32 kHz mono；交接重采样为 **48 kHz PCM16 mono**，
末尾仅补静音到 24 fps 帧边界，没有截短语音或 time stretch。

| Clip | PR start–end / 秒 | 末尾补静音 / samples |
|---|---|---|
| locate | 15.750–18.958333 | 400 |
| carry | 20.000–24.541667 | 1040 |
| basis | 26.250–30.833333 | 1120 |
| compare | 31.000–35.375 | 720 |
| verify | 40.000–44.083333 | 160 |

实际编码检出五段 bound waveform，相关度范围 **0.999985632–0.999997897**，
相同 AAC 偏移 1024 samples（21.33 ms），相对增益约 0.7067。
此项只是声音存在与位置核验，不能证明自然度、字母发音、尾音或音色连贯性通过。

现有 Rubinstein / Chopin Nocturne No. 6 录音从 8 秒开始作为低存在感 scratch；
Premiere 实际写入并读回 Duck/fade key，核验段降至 -42 dB、末尾淡出。
录音公开权利 **UNKNOWN / HOLD**。没有新增选曲、作曲或复杂音乐系统。

## 发现与修复，仍未通过的部分

早期 P0 预览发现取景裁边、选项挤行；随后发现 A/B 换位的路径穿过，
已改为足够间隔且原顺序进入。dual-r1 全片检查发现约 42 秒归位叠字，
已修正为主干先清空槽位、片段随后横移并归位；最终为 p0-r4 / dual-r2 / pr-r2。

制作期间 C 盘耗尽，造成两个临时文件测试错误及 AE 写设置模态警告。
测试临时目录改到本次 E 盘忽略目录。dual-r1 原生帧已经完整输出时超时，
保留失败凭证，以服务器正式 recovery ID 执行 `ae_execRecover / continue`，
匹配 DONE queue 后封装既有帧，没有盲目重发渲染。最终 dual-r2 正常渲染，无恢复重试。

查到运行中 AE 旧 C 盘 disk cache 约 24.7 GB；通过原生 purge 清理，
已备份设置并保存 G 盘缓存路径，清理后 C 盘空闲约 26 GB。
**当前进程仍写旧 C 盘缓存；下一次正常启动后 G 盘是否生效尚未核验。**
少量旧安装/诊断临时文件采用 hash 核验后的可逆搬移；没有删除冻结输入或旧认可工程。

| 审核层 | 当前状态 |
|---|---|
| 原生制作、对象延续、编码交付 | 技术 PASS，以上述实际凭证为限 |
| 真实同题多方法必要性与教学闭合 | NOT_ESTABLISHED；本片是合成研究 |
| 人工审美、接棒理解、双速观看 | PENDING |
| 人工试听、悲伤旁白/拖尾/连贯性 | PENDING |
| 来源公开权限 | UNKNOWN / HOLD |
| 编辑放行、最终声音认可 | 未通过 |

人工检查见 `METHOD_RELAY_DUAL_PASS_HUMAN_REVIEW.md`，需绑定本片实际 SHA。
旧 r7 的“效果很好”只保留给旧片；真实 R02/G01 和旧 B 无改善结果不升级。
`final_voice_accepted=false`、`sample_delivery_allowed=false`、
`production_eligible=false`、`public_render_ready=false`。
当前可播放文件仅用于内部技术观看，不自动进入真实题教学、商业成片或公开发布。
