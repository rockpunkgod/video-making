# Swiss Academic Motion v0.2 — 视觉收敛验收

基线 `main@7bc98b9bf1ecacdc693d52cd9dfe92f7a0d2bca1`，2026-10-05。
Engineering Visual QA **PASS**；Brand Constraint QA **PASS（可机械检查范围）**；
Human Taste Review **PENDING**。三条真实内部 MP4 已完成，不代表人工认可品牌审美。

本轮在原 V8 上增量修改视觉投影：简洁、克制、直接，动作在时间维度分层。
未重做 V8 架构，未增加教学事实，未启动 Astra、正式发布或 Motion SDK。
ANSWER / Registry / Case / Review / Video Package / Manifest / final copy 未修改。
教学、来源展示、编辑公开放行仍待通过，三个 `public_render_ready` 均为 false。

## 版本与基线

| 项目 | v0.1 | v0.2 |
| --- | --- | --- |
| Design | `ae/design/swiss-academic-motion.json` | `ae/design/swiss-academic-motion-v0.2.json` |
| Template | `ae/templates/method-demo-master.jsx` | `ae/templates/method-demo-master-v0.2.jsx` |
| Template family | METHOD_DEMO_MASTER | METHOD_DEMO_MASTER |
| Version | 0.1.0 | 0.2.0 |
| 平台配置 | 原安全区 | 独立 `platform-profiles.json` 0.1.0，provisional 模拟 |
| Identity | 原算法保留 | 绑定 package、design、template、revision、实际 projection/profile |

v0.2 design SHA `a14ce56ab4a77a686df9b4da870cb460060620742e69bb94f9a3e8f4f07406e1`。
JSX SHA `cc2dcb9a216dda98c6e5eb17976f80b8754d353b8211d218633d602a84613d3e`。
Render Contract schema 仍为 0.1.0，只增加平台、实际内容区和 cover candidate 的展示字段。
原教学字段不变；v0.2 契约要求新增字段齐全，旧契约继续有效。

旧交付目录完整复制到忽略的 `local-data/v8.1/V8_ENGINEERING_BASELINE/`，
原 `local-data/v8/delivery/` 与备份各 62 个文件均与启动时 SHA 相同。
包括原 MP4、AEP、checkpoint、critique、截图、合同与依赖索引。
三个旧 Render Contract 用当前代码精确重放一致，没有覆盖旧输出。

## Palette / Typography / Layout / Motion delta

Warm Off-white **#F2F0EA**、Charcoal **#20211F**、Fog Blue **#7E96A8**、
Sage Green **#91A58F**、Soft Brick **#C97868**、Divider Grey **#D8D6D0**。
原亮绿 Evidence 改为 Fog Blue 12% tint 与局部 focus line。
Charcoal 为文字、Fog 为证据、Brick 为局部错误关系、Sage 为已绑定的 Stop 收束。
不随机换 accent，不用低对比 accent 写小字。
Secondary **#4F5B63** 来自 Charcoal/Fog 混合；主/次文本对 Paper 对比度
分别 **14.189 / 6.124**。

实际 AE 比较了已安装的 Noto Sans SC、微软雅黑、等线的同字号中英文样张，
选用 **Noto Sans SC Regular**。未下载/安装或提交字体。五级字号为 Hero 80/104、
Title 64/88、Body 44/68、Metadata 28/40、Subtitle 38/56；字幕降低一级强调。
AE actual font 回读匹配，变量字体测量明确使用 Regular，16px composer 余量避免
测量值在边界附近触发 AE 额外换行。中英文字、标点、短语断行不改原字符。

六栏、96px 左边距、24px gutter 保留。移除常驻长 rail、彩色路径容器、
字幕分割线及英文场景标签；中文方法名与紧凑页码作为弱 Metadata。
核心区是 Brand Grid 与平台 profile 的交集 `[96,248,792,1208]`；字幕独立。
四个平台别名共用保守模拟排除区，不分叉四份 Master，不宣称已验证平台实时 UI。
内部 trace/footer 始终保留，独立于品牌主体。

五类 Motion 保留：Reveal / Focus / Compare / Eliminate / Connect。
8 帧快 Reveal/Eliminate、16 帧 Focus、12 帧 Compare/Connect；soft_out、
24px 位置预算、4px 局部修正、零 overshoot。依据先定位，操作数分阶段进入，
连接随后建立，局部判断延迟出现，最后稳定 Hold。Exit 在语义分页边界硬切。
没有背景循环、glow、gradient、bounce、粒子、shake、glitch、3D 或圆角 UI 卡片。
完整 [Visual Element Audit 与迁移说明](ae/design/V0.2_MIGRATION.md) 单独保存。

## 三条真实 Pilot：before / after / critique

| Pilot | 原版问题 | 新版结构及实际时间样本 | 尚待确认 |
| --- | --- | --- | --- |
| F01 q36 | 长 rail 与密集候选偏界面；色块压过结构 | 中文短入口；A–G 中性全集 strip；同轴候选按 3+3+1 分页，ID/正文/细线分层对齐；24–31s 动态、64s Stop | 当前冻结资产只有一个有效轴，不能制造第二轴；单个截图不能容纳七条完整选项 |
| G01 q59 | 四个实色节点像流程组件库 | 原文低 tint；40–47s 路径逐节点展开、连接跟随、终点聚焦、边界横线收束，停止后无尾箭头；70.5s 完整 Stop | 路径稳态可截图；中文入口速度与整体留白的品牌感觉待人工 |
| R02 q26 | 关系不同列宽、英文标签、局部判定不直观 | 共列“谁／做什么／对谁”；29.5–36.5s 原文连接→2s 后候选→4s 后局部判定；错误连接仅微移，中文“局部排除”与原 verdict 并存；62s 完整 Stop | 缺失对象槽保持空白；不得把局部排除理解成整题答案，静音学生理解待人工 |

Hook 仅把原 primary_text 的连续前缀提到 Hero，余句作为 Body；拼接与原句逐字一致。
原文 evidence 保留完整，全文口播保持原字符，Role 和 Stop 不改变。
F01 没有灰掉未被上游排除的候选，G01 不伪造 word_answer，R02 不升级局部 verdict。

修订过程留下失败与修复记录：r1/r2 的实际 AE composer 多行溢出通过测量余量与
分页修复；r4 的“提示词”“翻页信号”拆词与 R02 Hook 孤立“谁”通过有限短语规则、
前缀边界及列宽修复。最终 r5 字体、逐字绑定、actual bounds 和表达式回读均通过。
没有把失败截图删掉后宣称第一次即成功。

## 实际媒体与交付

| Pilot | Render ID 前缀 | Comp ID | 时长 | 字节数 | 原生渲染 / 全解码 |
| --- | --- | --- | --- | --- | --- |
| F01 | e3ce907fa152 | 1273 | 73s | 9,422,463 | PASS / PASS |
| G01 | c5ca9fe20556 | 1359 | 86s | 9,922,317 | PASS / PASS |
| R02 | 72f9edbd9b80 | 1427 | 78s | 9,710,576 | PASS / PASS |

均为 AE 26.0x67 原生 H.264 15 Mbps 预设，1080×1920、30 fps。
最终仅三条 composition 与数据依赖收集到
`local-data/v8.1/delivery/METHOD_DEMO_MASTER_v0.2.aep`；JSON 重连后再次核验绑定。
每条 MP4 位于该目录对应 pilot 子目录的 `INTERNAL_ENGINEERING_PREVIEW.mp4`。
绑定、当前提供状态、表达式、实际字体/文字/边界、palette/effect 检查在渲染前执行。
状态输入仍是调用方显式提供的清单，不声称能实时感知外部撤回。

`local-data/v8.1/visual-review/<pilot>/` 保存每条 Hook / action / Stop 三组 A/B PNG、
375px 手机缩放图、模拟 UI 排除区、三个比例的封面裁切和 12 帧动态序列。
Before 从保留的真实 MP4 提取；After 静态帧来自官方 `ae_previewFrame`，动态帧来自
新版实际 MP4 解码。来源、时间、render ID 在本地 frame-provenance 中明确记录。

每条实际动作片段同时检查进入和 Hold。5.5s 与 7s 后的教学主体 crop 平均 RGB
差异 F01/R02 为 0.00008、G01 为 0；动作开始与展开后主体确有变化。
这是抽样稳定性检查，字幕仍随时间推进，不声称全帧或全视频逐像素恒定。
口播为冻结文字估时的静音内部预览，没有录音、音画同步或真人理解验证。

## QA、Critique 与中文适配

Engineering Visual QA：453 项全量回归通过；最终短语/列宽修订后 29 项 AE 相关
回归再次通过；schema 同步检查、三条 v0.1 精确重放、真实 font/text/bounds、
表达式、前后冻结数据 hash、native 渲染和全解码均通过。
各内部 render 已登记到原 V7 本地依赖索引，不增加服务或新数据库。

| 中文适配检查 | F01 | G01 | R02 |
| --- | --- | --- | --- |
| Chinese entry | PASS：原句短前缀 | PASS：中文直接动作 | PASS：中文三槽位动作 |
| CJK typography | PASS：规则及代表帧 | PASS：“提示词”完整 | PASS：“翻页信号”完整 |
| Mobile legibility | PARTIAL：375px 模拟，真机待审 | 同左 | 同左 |
| Silent comprehension | PENDING：真人理解 | PENDING：真人理解 | PENDING：真人理解局部判定 |
| Safe area | PASS：版本化模拟区 | 同左 | 同左 |
| Pause-frame value | PARTIAL：候选三页＋Stop | 结构稳态 PASS，收藏价值待审 | 结构稳态 PASS，收藏价值待审 |
| Cover candidate | PARTIAL：中心 1:1 裁切丢失方法 Metadata | 同左 | 同左 |

375px 模拟下 Body 约 15.3px、Subtitle 13.2px；Metadata 约 9.7px，只有辅助信息。
有限断行规则不是完整中文语义分词；自动布局通过不替代手持设备阅读验证。
cover_candidate 只预留既有 Hook、方法名、主焦点，尚不是完整封面制作/放行系统。

每条本地 `motion-critique.json` 保留十项检查：Hierarchy、Composition、Typography、
Readability、Timing、Easing、Motion Purpose、Information Density、Visual Balance、
Brand Consistency，以及 issue/severity/scene_id/component_id/recommendation/resolution。

Brand Constraint QA **PASS** 覆盖：grid、色彩、字级、无圆角节点容器、无不批准
effects/3D/gradient、背景静止、位移和 overshoot 约束、实际关键文字安全区。
新增十一项严格品牌检查均保留：Swiss grid、Editorial hierarchy、Whitespace、
Semantic colors、Restrained motion、UI-like、PPT-like、Social-template-like、Decorative、
Too many cards、Too many persistent labels。后六项及留白质量有 agent 的像素观察与
解释，但主观审美不由自动 PASS 自证。Human Taste Review 始终 **PENDING**。

需要人工观看确认中文入口、手机字号、静音理解、动作节奏、截图价值与品牌记忆。
没有为降低机械错误率把五类 Motion 全部做成统一淡入淡出。

## AE 稳定性修复

用户追加要求配置 AE、解决经常性失败。本机确实启用了 Adobe 列为 AE 26.0/26.2
已知崩溃风险的压缩磁盘缓存；已备份设置，关闭压缩缓存与空闲预缓存并保存/回读。
同一进程连续导出三条完整视频及两次独立 2s 短片均成功，无中途重启。
这不证明所有工程永久稳定，也不把导出错误、CEP 启动异常与进程崩溃混为一谈。
依据、前后值、恢复方式和验证限制见 [AE 稳定性记录](ae/AE_STABILITY.md)。

## 发布与后续边界

本轮没有新增任何教学 Review、独立人工认证、来源许可或 Editorial Approval。
Teaching Release / Source Display Release / Editorial Release 尚未获得公开 PASS。
任何视觉工程成功或人工审美认可都不能单独提升公开资格。
所有真实题文、帧、MP4、AEP、备份与日志只在忽略目录；公开仓库提交代码、
脱敏报告及明确标记的合成测试。停止在 v0.2 视觉收敛，不扩展方法或自动发布。
