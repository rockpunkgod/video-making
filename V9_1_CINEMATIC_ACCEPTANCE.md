# V9.1 Swiss Cognitive Motion · Engineering Pilot

基线：`main@a7e628628770735bf00396f7db82961baca362cd`。
本轮为增量模块；只实际制作 G01 10–15 秒 Hero，不进入 V10。

最新提示词的 40 项对应证据与待人工事项见
[逐项验收表](docs/v9.1-requirements-audit.md)。

## 交付与工程结果

- 建立六种品牌动作和六种方法视觉规格。R01/R02/R06/R09/F01 只写规范。
- G01 使用同一个原句空位进行 Extract → Route → Seal：Fog Blue 证据显影、
  100→103% 聚焦、空位及细线接力、无弹性归位、微锁定、细线封口。
  方法名在动作理解之后出现；不展示未经绑定的路径分支或最终词形。
- 保留完整 Human Voice Script；Hero 为独立绑定的动作摘录，未伪装成完整解题。
  AI host 文案保真凭证未升级为人工教学认证。音纹按用户要求留待后续。
- 三种原生 AE 视觉方向，每种 Hook/Core/Stop 三张静帧；实际推荐方向为
  Paper / Evidence。静帧和过程帧由 AE/导出影片取得，不是设计稿替代渲染。
- 最终 AE 原生视觉段：1920×1080、24fps、14.75 秒、354 帧，无音轨。
  AEP/模板/冻结文案/视觉契约/渲染文件以 SHA 绑定，保留旧修订。
- 原生 AE 检查实际文字、字体、字号、画布、效果、表达式、23 个节点的
  关键帧、可见区间及未动画的坐标/透明度。接受 AE 的有限子帧时间量化，
  保持数值严格比对；不能把可执行表达式检查宣传为完整语义认证。
- Premiere 使用官方上游 MCP 的当前 CEP 连接，接收冻结渲染文件。
  三段 source/timeline bounds 回读核验；VO、稀疏结构 SFX 和一首夜曲分别成轨。
  最终 H.264/AAC 文件全量解码通过，规格与 AE 视觉段一致。
- 字幕实际烧录，Noto Sans SC Regular 42px，无描边/阴影，向上移入底部安全区。
  Native SRT 将前两个重叠输入 cue 合并，最终三条 cue 的文字与口播逐字一致。
  这以实际 sidecar 和输出帧核验，不将 CEP 的 accepted 回执当作 renderVerified。
- 两个 Hold 的上方 900px 运动区域，8.25→9.0 秒及 11.5→13.0 秒抽帧逐像素相同；
  字幕区单独核验。9.05→9.50 秒的实际音轨为数字静音。

真实题面、音视频、AEP、PRPROJ、字幕、全部运行回执、SHA 与 Creative Review
均保存于忽略的 `local-data/v9.1/`。公开报告不重发真实题目或商业录音。

## 音乐

使用用户提供的 Arthur Rubinstein 演奏 Op.15 No.3，连续片段、无 loop、无 Beat Sync。
录音来源、标题、作曲者、演奏者、原文件及裁剪文件 SHA、授权和授权证据已入
本地 Manifest。无录音授权证明，状态固定 `SCRATCH_MUSIC / Music License HOLD`。
作曲者身份不构成录音授权。

基础避让由 Premiere 原生音量关键帧完成并回读。工程起点参照实际录音与
口播电平；英语证据进一步压低，Stop 平滑降至近乎静音，不随短暂停顿反复抽动。
电平或静音检查不等于人工试听通过。五个音乐试听问题保留为 PENDING。
没有扩展选曲、BPM、配器、音乐生成、复杂分析或推荐系统。

## 独立验收

| 项目 | 当前状态 | 含义 |
|---|---|---|
| Engineering Pilot | PASS | 真实冻结资产完成原生 AE → PR → 最终内部试片 |
| AI host fidelity | 内部可用 | 有文案绑定；不是独立语义认证 |
| Human Taste / Direction | PENDING | 等实际观看确认方向 |
| Brand Recognition / Memory | PENDING | 仅预留测试协议，无真实学习者结果 |
| Human Listening | PENDING | 五项音乐问题未代用户回答 |
| Teaching Release | HOLD | 未取得本 scope 的独立人工教学放行 |
| Source Display Release | HOLD | 实际展示片段/文字/画面 hash 已冻结，未放行 |
| Editorial Release | HOLD | 最终口播/字幕/视觉/音频绑定，未签署人工批准 |
| Music License | HOLD | 用户提供录音不代表公开视频授权 |
| PUBLIC_RENDER_READY | false | 任一未放行都不能公开使用 |

最终 Copy Lock 包含实际字幕及文案指纹，`editorial_review_sha: null`。
Source Display 保存展示片段 ID/ref、实际文字/画面 hash、来源标注和空批准 ID。
所有生产操作重新读取当前提供的上游清单；静态文件不承诺后台实时撤回感知。

## Creative Review 与 Stop Rule

Agent 的逐帧检查支持进入人工方向审阅：文字与边界可读、空位持续接力、
路径止于名词节点、细线封口形成可复用动作、静止画面保留阅读价值。
抽离过渡的 Motion Blur 是运动阶段处理，不是要求阅读的 Hold；视觉节奏、
记忆强度和音乐气质仍需人的实际观看/试听。

新增六项品牌检查：Signature recognizability、Method-motion fidelity、Brand grammar
consistency、Mnemonic clarity、Motion distinctiveness、Motion-to-teaching alignment。
八个 G01 人工问题和五个音乐问题随最终媒体 SHA 存入本地 CreativeReview。
不宣称“已经能被学习者认出方法”，不把一次工程试制变成方法有效性结论。

尚无 copy/visual-bound human `APPROVED_DIRECTION`，因此停止在 Hero：
不制作完整 G01/F01/R02，不进入 V10，也不接自动发布。

## 验证

全量回归 510 项通过；随后增加字幕实际文字绑定和原生 AE 回读控制，
针对 Hero / Creative OS / Premiere 的最终 67 项回归另行通过。
覆盖：重复冻结生成、不可丢否定词/Stop、撤回阻断、状态元数据刷新、
伪 Hold、渲染文件篡改、AI 不得批准全片、方法不能改名冒用、Registry 禁教学字段、
UXP 静态兼容不冒充在线、错误序列阻断、操作不确定后禁止盲重试、
录音身份不升级授权、字幕改字拒绝、实际运动/可见性漂移拒绝。

后续审计补齐声音门禁：每个摘录单元必须有且只有一条口播绑定；SFX 变更拒绝；
带音乐的声音计划不得保留“无音乐、不适用 ducking”的旧声明。最终导出前实际
回读音轨位置、片段覆盖以及所有配乐关键帧，拒绝多余、缺少或改动的关键帧。
校正声音计划描述后重新原生导出，解码后全部视频帧与音频样本 SHA 均与上一版
试片一致。该证据证明记录修正，没有代替人工试听或方向批准。

本轮只提交代码、视觉规范、工作流、测试与脱敏报告。未提交媒体、真实题面、
商用录音、Adobe 工程或本机认证令牌。
