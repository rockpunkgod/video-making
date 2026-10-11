# Reality Layer + Cognitive Space · 创意预演验收

日期：2026-10-11。生产基线：`main@0af0ff5f9a341ae8823573ec1bdb488a8721240c`。

用户对前组三条预演反馈“与老师PPT没区别”，本轮尝试真实题面与临时认知空间结合的影像。仅复用其中一个真实案例及其已有单候选排除动作，不扩展整期或视频系统。

## 实际交付

一条 **40 秒、960 帧、1920×1080、24 fps、Rec.709、无声 EDITORIAL_PROXY**。完整原文和原题构成固定父世界；已发现原词进入透明工作空间；已有关系通过分组和靠近呈现；实际判断后投影退出，镜头回到原题。

旧预演和本轮第一遍导出保留。本轮独立 r02 修正回归时字形叠加，不改变题目、来源、证据、动作、结论或文案。没有生成新教学 Claim、最终答案、新配音或正式 Adobe 工程。

完整操作说明见 [导演流程](docs/reality-cognitive-space-proof.md)。真实题目身份、来源全文、上游关系与审阅引用、工程重放输入、实际MP4及所有指纹仅保存在忽略的目录：

```text
local-data/creative-proofs/reality-cognitive-r02/
  PLAN.json
  INPUT_CHECK.json
  SOURCE_DISPLAY.json
  DIRECTOR.md
  CREATIVE_REVIEW.md
  render.py
  verify.py
  REALITY_COGNITIVE_R02.mp4
  MEDIA_RECEIPT.json
  MEDIA_CHECK.json
  FRAME_STATES.json
  ACTUAL_FRAME_MAP.json
  DELIVERY_AUDIT.json
  INPUT_PROTECTION_BEFORE.json
  INPUT_PROTECTION_AFTER.json
  ENCODED_QA/
```

## 工程证据与边界

- 所供状态清单和冻结引用通过现有消费门禁；本轮没有后台检测新撤回。
- 单候选动作与上游一致。实际候选状态首次更新在第 **651 帧（27.125 秒，零基帧号）**；其余候选保持未决，不宣布最终答案。
- **960帧**状态核验父世界持续存在、来源全文指纹稳定、投影原词和范围一致、退出后工作空间清空、返回原题及候选集合一致。
- 实际媒体SHA与计划绑定，分辨率、帧率、解码帧数及全片解码通过。保存 **16张编码后关键帧**供字形、比较和回归抽查。
- **148份**已登记输入与历史文件前后SHA一致，包括冻结Bundle/Status、旧原生工程与媒体、既有未提交文件、旧预演和作者程序。没有改ANSWER、Registry或Frozen Teaching输入。
- Experience Proof 与 Candidate Motion 相关 **21项合成回归通过**；未宣称仓库全量回归。

状态日志和关键帧抽查只证明相应工程检查，不证明每帧像素语义、完整英文理解、自然口播或认知爽感。`native_glyph_certified=false`，声音尚未加入。

## 人工停止点

交付本条后等待实际观看：**`human_experience_review=PENDING`**。本轮Agent没有签署“参与感更强”或“已经摆脱PPT感”。不进入正式4K、完整Episode、通用Renderer或发布阶段。

AI教学审阅保留上游级别，来源仅限内部试制。**`public_render_ready=false`**。公开仓库不包含试题、媒体、声音或原生工程。
