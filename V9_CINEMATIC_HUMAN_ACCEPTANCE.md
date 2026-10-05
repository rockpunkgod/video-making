# V9 — Cinematic Landscape × Human Voice × Rich Motion

增量基线：`main@a69b9d0232950a0c3f16c3ff41184495a9cbac2b`。
本轮只处理 F01 q36、G01 q59、R02 q26。音纹按用户指示留到后续；当前为测试配音。
没有接入真实 Astra，没有新增教学 Review，没有改变 Registry、方法、Evidence 或 Stop。

## 分层验收

| 项目 | 结果／资格 |
| --- | --- |
| Landscape Engineering | **PASS**：三条真实横屏 MP4、AE 合成／字体／边界／表达式与完整解码核验通过 |
| Human Voice | Delivery Copy、句级 provenance、实测 scratch voice 已建立；真人听感与最终音纹 PENDING |
| Teaching Fidelity | 七维 copy-bound AI host 重述审阅与引用 lint PASS_internal；独立人工教学认证 PENDING |
| Motion Choreography | **PASS_engineering**：三种结构变换及 Hold 已通过实际 MP4 时间采样核验；人工辨识待审 |
| Human Taste | PENDING；无用户人工审美批准凭证 |
| Teaching Release | PENDING |
| Source Display Release | PENDING，最终展示采用新的绑定 |
| Editorial Release | PENDING，旧竖屏批准不沿用 |
| Public Render | **false**，所有输出仅 INTERNAL_CREATIVE_PREVIEW |

## 交付规格与位置

三条均为 1920×1080、24fps、AE 原生 H.264，AAC 测试口播；无背景音乐。

| Pilot | v8.1 时长 | V9 实测时长 | 帧数 | 结构签名 |
| --- | ---: | ---: | ---: | --- |
| F01 q36 | 73s | 61.083333s | 1466 | 同一身份行 → 单组 4+3 空间重组 → 锁定 |
| G01 q59 | 86s | 64.083333s | 1538 | 沿既有路线逐步连接 → 名词节点 → 封闭前向空间 |
| R02 q26 | 78s | 61.333333s | 1472 | 原文关系 → 候选叠加／下移对齐 → 局部连接改写 |

最终媒体位于忽略目录 `local-data/v9/delivery-r4/<pilot>/INTERNAL_CREATIVE_PREVIEW.mp4`，
总工程为 `local-data/v9/delivery-r4/CINEMATIC_LANDSCAPE_MASTER_v0.3.aep`。
每条同时收集 Frozen Package、Manifest、当前提供的状态、Delivery Copy、Shot Plan、
Narration Track、Cue Sheet、实际 WAV、Render Contract、回放请求及审核证据。
公共仓库只提交实现、Schema、此脱敏报告和明确合成的测试代码。
最终 revision 为 4；三个 render ID 前缀分别为 F01 `a0eca8d9b958`、G01 `f37ce07188de`、
R02 `0054be68ba8c`。总工程收集为 3 个合成、3 个 JSON、3 个音轨及 1 个目录，队列清空。
六条历史 v0.1/v0.2 契约回放通过；三条 v0.2 的实际旧 AE composition/text/font/bounds
绑定也通过复核。旧 MP4 未重新导出或改动。

## 冻结边界与审阅顺序

新增 `creative_os`、独立 CINEMATIC_LANDSCAPE profile 和 v0.3 JSX；原 `content_os` 与
vertical v0.1/v0.2 路径继续保留。冻结输入只被读取、深复制及投影。

每个 unit 保存 Claim 原文与自身 method/asset/action/evidence/review refs。
逐句口播和字幕引用可追溯。内部宿主分别检查 Claim、Evidence、Role、Certainty、
Quantifier、Causality、Stop；记录绑定源语义和最终 unit 文案。
确定性 Guard 检查引用、保护词和有限扩张规则，不能证明完整语义正确。
AI host 的重述审阅没有成为 ANSWER 的新教学凭证。

F01 只演示已绑定句型轴，七项同属完整陈述句，未虚构新的区分能力。
G01 保留名词性宾语不排除全部动名词、词形核对留给 G09 的边界。
R02 保留 performing、not as a musician 的限制和 D 排除的撤回条件，未定整题答案。

最终文案仍需 Teaching Release → 最终 Source Display Review → Editorial Review →
Locked Package；全部通过且上游当前有效才可公开。此轮不生成公开 Locked Package。
Source Display 指纹覆盖实际场景文字、字幕、方法标注、引文和显示结构，图片集合为空；
最终场景更换不会只依赖抽象题目来源批准。

## 测试配音与节奏

本机注册的中文 Windows 声线实际加载失败，早期英文默认回退没有用于成片。
最终测试音频来自真实 Edge 在线 TTS，经 edge-tts 7.2.8、zh-CN-YunxiNeural、-5% rate
生成，保存真实 SentenceBoundary 事件，转换为 22050Hz mono PCM16。
这不是 Astra 输出，也不是人类录音；音纹按用户指示延后。

每段实际 WAV 测时，停顿向 24fps 边界取整，约 0.51–1.51s 的段后静音实际写入音轨。
字幕依服务返回的句子时间戳排列；长句跨页分配仍明确标为估算，不冒充逐字强制对齐。
结构动作只加入一次 -36dBFS 程序点击；音乐许可未确认，没有使用背景音乐。
实际音轨和 breath/emphasis 标注都被保存；情感、发音和真人 cadence 仍需人工听审。

## A/B 与内部 Critique

每条保存 Hook、核心动作、Stop 三组真实解码帧和核心动作的连续时间采样；
对照保留竖屏与横屏完整画幅，没有裁切旧版制造对比优势。整体节奏另记录时长、
八个 delivery units 的说话时间、停顿和稳定 Hold。

| 维度 | 内部观察／尚需核验 |
| --- | --- |
| Humanity | 短指令、具体动作和刹车代替机械模板；真人听感 PENDING |
| Cinematic Quality | 横向留白、层级和硬切；主观“电影感” PENDING |
| Motion Richness | F01 空间重组、G01 导航闭合、R02 关系重连；不是统计 fade 数量 |
| Clarity | 一段一个任务，独立字幕；真实学习者理解 PENDING |
| Brand Quality | 保留 Paper/Charcoal/Fog/Sage/Brick，中文入口；人工审美 PENDING |
| AI Feel | 三条 cliché lint 均 LOW，未接假 Astra；不据此认证“像真人” |
| Lecture Feel | 屏幕短于口播，减少条目说明；R02 条件多，仍需真人判断解释负担 |
| Readability | AE 原生字体、正文范围、段落与稳定状态碰撞审核；横屏小手机显示仍需人工 |
| Memorability | 三种结构签名已分开；没有学习者记忆数据 |

Artificial Polish Index 为 **LOW（内部文本检查）**：没有密集转折连接词、低俗网感口头禅或
虚构营销判断。Naturalness、Brevity、Rhythm、Specificity、Human cadence、AI cliché density、
Lecture tone、Sales tone、Pretentiousness、Teaching fidelity 十维逐项留存。
“LOW”不代表所有句子已由真人批准；避免把确定性检查写成人工审美认证。

Motion 评价按 structural transformations、focus changes、spatial reorganization、temporal
layering、motion-to-hold contrast、signature clarity 六项进行。实际 AE 的空间位置改变与
后续静止状态均有采样；Motion Blur 仅用于移动结构，180° shutter，稳定阅读文本关闭模糊。
Depth 使用前景关系线和内容层次，Texture 关闭，没有强行增加 3D、粒子或滤镜。

最高影响的初版问题是手动换行在 AE 多加一行导致标题溢出；已修正 JSX，重新生成并通过
原生审计。最终来源显示指纹另补齐完整文案与字幕绑定，采用新的 revision。

## 复现、失效与验证

Copy Lock 独立保存 teaching/delivery/screen/audio timing 指纹。文案修改清除 copy-bound
host review 和 editorial approval；声线、音频或停顿变化使 render stale。新的状态清单
通过 V7 机制传播撤回、替代、来源权限及展示变化，不宣称后台实时监听。
本地 dependency index 登记 Frozen Package → Delivery Copy → Render。

全量回归 **472 项通过**；最终 49 项生产层针对性回归通过（含 V9 的 20 项），Schema 生成检查通过。
Schema 指纹采用 canonical JSON，换行、JSON key 顺序及缩进差异不改变 render ID；
新增跨格式／CRLF 回放测试。生成 Schema 固定 LF，防止 Git checkout 造成运输字节差异。
重复生成核心契约一致；诊断路径迁移仍保持 render ID。
反例覆盖引用串借、Role 升级、绝对化、Stop／句级引用丢失、fake Astra、缺状态、撤回、
音频篡改、计时漂移、文案审阅失效和私自编辑显示投影。

历史资产扫描 119 个文件：118 个保持原字节 hash；旧 v0.2 AEP 在首次官方 checkpoint
保存时发生序列化变化，随后已另存到 V9 工作工程。冻结输入、旧 JSON/MP4、v0.1/v0.2
源码没有改变；旧版契约与 AE composition 绑定已单独回放核验，不把 AEP 字节变化隐瞒为
“所有文件 hash 不变”。没有再对旧竖屏进行视觉迭代。
后续 build 已在官方 checkpoint 前自动另存指定 V9 工作路径，避免再次保存旧工程。
最终收集前曾出现系统盘剩余空间为零，官方恢复请求报 ENOSPC，随后恢复记录为空而无法读取。
仅将本轮 18 个较早的 V9 checkpoint 工程归档到本地数据目录，保留路径及 hash 清单；
没有删除其他用户文件。F01 的超时操作已实际完成，通过原生绑定与边界核验确认后接纳，
没有重复执行 build，也不把失败的官方恢复请求记为成功。AE 会话退出后由用户恢复，
重新打开已保存的 V9 工程，核对合成再继续缺失的 G01 构建与最终导出。
这些记录属于本次恢复证据，不代表已经消除所有 AE 崩溃原因。
这里的 Signature Motion 仅指视觉结构，不授予 ANSWER 的正式 Signature 或方法成熟度资格。

V9 到此停止；不进入正式 Astra、最终音纹、自动发布、新方法或公开发布阶段。
