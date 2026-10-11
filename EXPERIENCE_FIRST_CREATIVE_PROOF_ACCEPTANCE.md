# Experience-First Creative Proof · 首批交付

日期：2026-10-11。生产基线：`main@258d9e89649ffb0d40c127e7fe81cc7a8949d156`。工程核验通过；收到首轮人工反馈，**形式差异需要修订，停止扩大制作**。

## 首轮实际反馈

用户观看后反馈：“都很好，但是和老师放ppt没区别”。保留这项总体正向评价及关键异议，形式差异状态为`NEEDS_REVISION`。逐题理解、爽点、回看价值与目标学生冷看未分别获审，不能将总体评价写成这些项目全部通过。下文`PENDING`为交付时的历史状态；当前反馈与媒体SHA另存本地`HUMAN_FEEDBACK_01.json`。

根代理核对了实际时段：第一条预先给定选中证据后逐项解释；第二条将选项放入预设分栏；第三条先完成关系表，再等待候选退出。这些均能展示已有依据，当前仍以观看整理结果为主。导演修订记录为`CREATIVE_DIAGNOSIS_01.md`，下一次验证收窄到一个归属比较，先检验注意力和比较如何让原因可见。修订稿尚未制作，不能声称已改善；工程验收不被这项创意异议抹掉。

本批从已有真实冻结资产中选出三个不同的观看价值，完成实际动态小样。选题、导演取舍和最终核验由根代理负责；低档子代理只进行独立检索与只读编码监测。没有重新建设 Video OS。

## 实际交付

| 方向 | 已消费的输出范围 | 动态小样 | 观看状态 |
|---|---|---|---|
| 抓住关键 | 已审阅辅助定位，加四项各自的上游直接文本判断；全部必要比较后才闭合 | 34s / 816帧 | PENDING |
| 复杂变清楚 | 已审阅选项分组；原有七项全部保留，不生成空位答案 | 32s / 768帧 | PENDING |
| 看似一样 | 已审阅归属对照，仅排除一个候选；局部回看不恢复或再次排除该候选 | 36s / 864帧 | PENDING |

三个小样都是横版 **1920×1080、24 fps、Rec.709、无声 `EDITORIAL_PROXY`**。本轮任务显式允许低成本1080p预演；`native_glyph_certified=false`。没有制作正式4K、完整Episode或发布包，也没有调用Adobe宿主、重训声音或生成新配音。

实际选题、精确题目身份、原文范围、Action / Evidence / Relation / Review、版本指纹及MP4只保存在忽略的本地目录：

```text
local-data/creative-proofs/experience-first-r04/
  CANDIDATE_SELECTION.md
  CREATIVE_REVIEW.md
  SOURCE_BINDINGS.json
  EXECUTION_RECEIPT.json
  FINAL_EXECUTION_RECEIPT.json
  ACTUAL_FRAME_MAP.json
  INPUT_PROTECTION_BEFORE.json
  INPUT_PROTECTION_AFTER.json
  DELIVERY_REGRESSION_RECEIPT.json
  DELIVERY_PROTECTION_CHECK.json
  01_DECISIVE_CLUE.mp4
  02_COMPLEXITY_COLLAPSE.mp4
  03_FALSE_MATCH.mp4
  <clip>/PLAN.json
  <clip>/DIRECTOR.md
  <clip>/MEDIA_RECEIPT.json
  <clip>/DELIVERY_MEDIA_CHECK.json
  <clip>/FRAME_STATES.json
  <clip>/ENCODED_QA/
```

前期三个revision保留。r04只修正实际帧抽查发现的文字碰撞，源文本、动作和时码不变。真实案例未拼成一期多方法节目。现有R06 B06原生工程与六份G2媒体保留；其观看反馈与技术验收分别记录，具体被观看的旧／新媒体版本尚未核实。

## 工程核验及其限度

复用现有冻结封印、所供状态清单、Engineering / Source Internal Gate和`audit_candidate_events()`。新增`ae_production.experience_proof`是只读校验器：核对精确文本范围、逐题直接判断、完整闭合前置动作、原始完整分组、回看状态及媒体绑定。它不生成教学事实、语义标注或导演动作，也不能因字符范围匹配就授予精细语义操作权限。

- 三个实际MP4均核验媒体SHA、绑定Plan、分辨率、帧率、实际解码帧数并完成全片解码。
- 保存逐帧渲染状态及实际媒体帧映射；抽取编码后的关键帧检查比较、候选退出、保留集合、回看与文字可辨认性。状态日志不是逐帧像素语义认证，抽查不是原生字形验收。
- 回看单独绑定帧范围，不能重复计入动作或复活候选。分组不伪造候选减少。辅助定位不借用直接判断的解题归因。
- **137份**已登记输入及历史文件的前后SHA一致，包括六份选用冻结Bundle/Status、旧B06工程与媒体、91份既有未提交文件，以及前期预演输入。没有修改ANSWER、Registry或原Frozen Teaching输入。
- Experience Proof、Candidate Motion、Method Episode、Audience Engagement四组去重回归共**34项通过**，其中14项新增合成测试。测试数据无真实试题。相关模块回归通过不代表执行了仓库全量回归。
- 所供状态清单有效只说明这次显式状态消费通过；本轮没有后台监听外部新撤回。

当前来源只用于内部验证；AI审阅保持其明确上游级别，不升级为独立人工认证。G01已有HOLD及Payoff缺口保持原状。冻结输入和历史批准均不因预演而改变。

## 明确的人工停止点

**实际交付三条后停在观看审核。** `HUMAN_EXPERIENCE_REVIEW=PENDING`，`public_render_ready=false`。编辑上建议优先看“看似一样”，这只是根代理的创作判断。

人工分别记录：第一次是否知道任务、是否先察觉线索、判断是否自然、有无拖沓或重复、是否想看下一题、局部回看是否带来新理解。程序和Agent都不能签署这些答案。

未获得范围明确的真实观看反馈，不进入高保真4K、R06整期、通用局部渲染或正式发布。如果全部不成立，下一步回到选题、实际认知收益和观看顺序。公开仓库仅提交必要校验代码、合成测试、入口说明和本脱敏报告；题材、媒体及制作记录保留本地。

## 重放核验

在仓库根目录使用已存在的私有计划及媒体收据，输出一个新的核验记录：

```powershell
python -m ae_production.experience_proof <PLAN.json> --media-receipt <MEDIA_RECEIPT.json> --output <new-check.json>
python -m unittest tests.test_experience_proof tests.test_candidate_motion tests.test_method_episode tests.test_audience_engagement -q
```

命令行不覆盖已有核验记录。媒体核验需要本机FFmpeg/FFprobe；不包含通用渲染Runtime。
