# Experience First / Rigour First — 当前差异审计

基线：`main@3a606b26d127f4896d99cb14a78a03eb42128428`。本审计对应最高优先级产品修订。既有教学事实、冻结资产、审阅历史和 Adobe 工程保留。程序检查不构成人类观看体验的证明。

## 产品口径

`FREE_SHOWCASE` 是精彩的高手做题体验，由 Creative Director 主导内容组织。`PAID_MASTERY` 是严谨的高手训练体系，由 Pedagogy / Teaching Review 主导。两者共享 Truth、实际展示的 Source Rights、No Fabricated Claims 和 No Unsupported Final Answer 硬门槛；通过硬门槛后分别评价质量，不合并成一个总分。

免费质量顺序：Hook → Engagement → Narrative → Cognitive Payoff → Visual Impact → Voice Performance → Memorability → Shareability。

付费质量顺序：Teaching Accuracy → Evidence → Applicability → Boundary → Action Executability → Method Integration → Practice → Transfer。

质量评价需要实际内容或人工反馈。没有观看、听感或传播数据时记为 PENDING / UNKNOWN，不凭计划预测高分。免费内容不以研究级 First-use / Transfer 为普通发布前置；付费教学收益主张需要与实际核验相匹配。

## 仓库差异

| 已有实现或习惯 | 对免费体验的影响 | 本轮采用的调整 | 保留的底线 |
|---|---|---|---|
| `content_os/director.py::build_draft` 以 `core_action` 开场，逐项显示实际动作、方法名及全部 Stop 类 Claim | 题目让位给方法说明；内部字段易被逐字读成口播 | 原冻结 Package 保留为来源凭证；单独组织最终作品文案，从题目的当前困难进入，方法名后置 | 最终文案逐题审核事实、Role、结论范围及必要限定；不修改冻结 Claim |
| 同一模板依次铺陈 Evidence、动作、结构卡和方法回收 | 画面像连续更新的课件；动效没有改变学生当前任务 | 题目、注意力目标与动作驱动镜头；结构只在实际需要比较或压缩时出现 | 只能消费已有动作产物；不能为视觉高潮制造候选淘汰或答案 |
| 旧短片 Pattern 的 30 / 60 / 90 秒计时与升级规则 | 易将多题主片硬裁成短动作片，或为了档位补总结 | 多题主片由真实阅读、口播和动作决定时长；90–180 秒仅为导演试制参考；短版另行审阅 | 裁剪后重新核验展示片段、Evidence 与结论范围 |
| 每题完整 Fast Pass + Guided Replay | 第二题把第一题的规则再教一遍，重复消耗观看动机 | 第一题建立动作；第二题用新的困难改变观察路径，只慢放确有理解价值的节点 | 原速仍按实际动作顺序，不用跳步制造高手感 |
| `student_pov/realization.py` 的来源绑定、Tell Now 与审阅要求 | 被误读为每条安全字段都要进 VO；重复“还不能选”打断现场感 | 后台完整保存；前台用正常任务引导和真实结果状态收束，必要限定嵌入当前证据 | Copy 不能自行删决定性边界、升级 Role 或把 deferred 包装成 removed |
| `core.release.check_release` 的方法研究门禁与视频传播混写 | 普通免费作品容易被要求先证明完整方法迁移 | 明确区分方法研究、当前片段教学审核和作品审核 | 旧 Registry / 方法推广门禁不改；付费教学主张不借审美结果升级 |
| 同一声音状态与持续钢琴铺底 | 不同认知阶段区别小，可能形成慢、沉的旁白感 | 先在导演稿上标明搜索、辨认、判断、释放与停顿，再安排声音和剪辑；听感单独审核 | 不重训、换引擎或改 Frozen Copy；未听审不能宣称自然 |
| 前一版 R09 174 秒与 19 条 VO 草稿 | 分段归纳和框架说明过多；“骨架有了”未必是观众感到的突破 | 暂停生成；重审题序、悬念、实际反差和两题递进，再定完整分镜及口播 | 两份现有输出都是 framework_card，无答案许可；不能伪造最终选项 |

## 当前真实案例的限制

现有 R09 两题有各自有效的 AI 审阅、动作和来源绑定，适合内部创作核验。BMF 需要保留员工可持续实践，并限定“零排放”为原文描述的食材运输环节；Sea Level 必须区分摘录实际完成的任务与书中宣布的三个历史阶段。两题均未获得完整答案闭合凭证。它们能够支撑框架形成与文本任务辨认，不能支撑“已经锁定正确选项”的高潮。

因此，双题资产齐备不等于双题作品已经精彩。选题方案须进一步回答：观众为何想继续看、每题真正看清了什么、第二题为何值得继续、这个 Payoff 是否来自真实动作。若答案不充分，应报告选题缺口，而不是靠镜头或文案放大方法信用。

## 下一步交付顺序

1. Episode Selection Brief：选择能形成体验递进的真实题，标明支持范围与缺口。
2. Question-by-Question Storyboard：完整口播、视觉状态、实际动作、逐题 Evidence、节奏曲线、Payoff 和正常收束。
3. 再依据已定导演方案列出最小技术缺口，复用现有 AE → Premiere 链路完成内部样片。

在选题、Copy、Director、Motion、Voice、Premiere 和 Human Review 的交接记录中显式传递 `content_profile`。它决定组织主导方和质量 Rubric，不改变 ANSWER 方法事实，也不能替代公开审核。人工审美、听感、传播结果分别记录，当前均未自签通过。
