# Student POV v0.4 — Learner Experience Compiler Acceptance

2026-10-08。代码、Schema、确定性回放与兼容回归 **PASS**。当前真实 Experience 的新最终文案审核、实际视听体验和 Human Taste **PENDING / HOLD**；没有公开放行。

## 基线与实施范围

实际开始基线：`main@86655b381790b2773c2f866824c1f948a53adf91`，高于请求中的 `31a1df7`。该基线已经包含真实 Pedagogy Compiler 0.4 与之前的 R02 Narration Performance 实验，因此正式消费已有 0.4 输入，不补造 Work Delta。

新增 `student_pov/experience.py`、`experience_qa.py`、`creative/copy-system/student-pov-experience.v0.4.schema.json`、文档与合成测试。既有入口增加显式 0.4 分派；默认仍产生 Copy 0.3。0.1 / 0.2 / 0.3 的历史 inspect 不改标签，不覆盖旧输出，不继承批准。

本轮只安排学生接触既有教学内容的顺序、对象、行动、未决状态、结构变化、停止与记忆。没有修改 ANSWER、Registry、Pedagogy Truth、Frozen Evidence / Action / Stop / Role，没有新增教学 Review；没有修改 Creative、Narration Performance、Voice Producer、AE、Premiere 或现有生产索引。

## 当前输入与可重放绑定

READY 输入必须同时通过当前 Bundle / Status、Pedagogy Plan 0.4、Copy/Motion Handoff 0.4 核验。Motion 的引用目录核验后再展开，所有关注对象与注意力范围来自已有认知结构。没有读取教学 Markdown、Registry 或题库补事实。

| 回放 | 上游 Plan SHA | Experience SHA | 编译 / 消费状态 |
|---|---|---|---|
| R02 worked_example | `4b176c0d1efd5d4e3c246412452ac30cf44670f7a63db6eb66bd761a68baa947` | `e17037b5cf2fd2bf17bebafc263362658e49f021eed3aa7d90488a9f1a1cb71a` | PASS / HOLD |
| R02 first_touch，同一真实资产 | `a3503a2870dab4490bec7a6e854927267cf36d9c4aedb1e039ca720d925e7a65` | `93f679a5073bb30a61d116546d4fcb7c7d98927d704ed4698550702c91803315` | PASS / HOLD |
| G01 worked_example，显式诊断 | `ecd5decffdf546224777e67117bb219a885bc4ded73fdde577d2461132385eaf` | `24b5adbe4f2f143ed34bc869f3ca81e4c93733d4666fcea1f877251ce9fed3b8` | PASS / HOLD |

R02 worked_example 的新 `script_sha`：`bc366133635053cff2daca24a27b585843c1b4545b5b5457bbeb6fc3d08c6ad3`；新 `final_copy_sha`：`984ac967d439aaa32d21ce1ac68d63b3020cbb14284c9983281f88a6c322c116`。Copy/Motion Handoff 内容 SHA 分别为 `38f2e79fb04e8a49603710368b4037f24aaa7891037bdbd6cec1474a506de068` / `d2b26b288a43f5f9ad83c464589c253bac8db99730bcb3221a8af0ce96679256`。

三份实际回放均通过 CLI realize / validate / inspect；相同冻结输入重复生成的完整对象逐项一致，核心内容和语义 SHA 一致。语义指纹不含根生成时间；改变来源、对象、文案或体验顺序会失效。历史 inspect 保留阅读能力，但不授予当前消费资格。未覆盖旧 Take、文案或批准记录。

真实题面、引用、逐拍 VO/Screen、请求与回放凭证只保留在忽略目录 `local-data/pedagogy/student-experience-v04-r1/`。公开报告不包含真实题面、逐字文案或媒体。

## R02：局部缩减的完整体验

`experience_kind=cognitive_payoff`。六个 Beat 承载八个认知阶段：

```text
PAIN → FOCUS → ACT + TENSION → COLLAPSE + PAYOFF → STOP → MEMORY
```

| 体验职责 | 实际交接 |
|---|---|
| 原题与 Pain | 原题首先展示并持续保留；只使用已有 symptom 和受审结构基线 |
| Focus | 关注对象、范围前后与 reason_ref 来自实际 attention transition；不创造“全文不读”许可 |
| 第一动作 | 唯一冻结 primary_action 的关系比较；instruction、Evidence 与实际产物精确绑定 |
| Tension | 与行动共享一拍，只引用当前真实未决对象，不制造营销悬念 |
| Collapse / Payoff | 已有候选结构 4→3；before/after 同时有来源且在计划中出现，默认没有 Payoff VO |
| Stop | current_output、candidate_set scope、禁止下一推断、完整必要覆盖与未决对象保留；不补结果后提醒口播 |
| Memory | 回收已执行的第一动作与冻结短句，动作之后才显示方法名；消费者不显示内部方法编号 |

Work Delta 明确保留：baseline_work=4、removed_work=1、deferred_work=0、still_required_work=5。此基线是受审结构投影，**不是实测学生路径、节时或迁移实验**。局部工作减少不等于完整题目已解决；A/B/C 及其它未决对象持续进入 attention/unresolved/Stop，`may_output_final_answer=false`。

当前 Handoff 没有可直接投影的负向 Interrupt 指令，所以没有编造“先别读全文”等新 Anti-rule。Focus 已有明确对象，默认也不独立拆 Orient。Schema/API 能处理已有指令或有据候选；不是强制补齐十幕。该限制保留为当前真实输入情况。

R02 的必要边界保持原批准 encounter：原则在 action 对比中，剩余候选为中性未决对象。Stop 不被删除，不把内部待办或用户拒绝的“另外三个还得看／现在还不能选”搬成新的 VO 或提醒墙。

## G01：没有收益凭证就不产生 Payoff

上游仍 HOLD，未生成合法 0.4 Handoff。本轮明确使用 `allow_held_plan=true` 的已披露 Plan 诊断投影：`upstream.status=DIAGNOSTIC_UPSTREAM_HOLD`，Copy/Motion Handoff SHA 均为 null。这不是伪造 Handoff 或批准。

`experience_kind=action_demo`，五个 Beat：PAIN → FOCUS → ACT + TENSION → STOP → MEMORY。现有 first action / route / 产物 / 原必要 Stop 可见；未决词形对象保留。没有 Collapse、Payoff Scene 或 Cognitive Relief，`learner_visible=false`。Baseline 仍为 null，未新增 removed/deferred/required work。

HOLD 原因包括 `BASELINE_WORK_UNSUPPORTED`、`PAYOFF_UNSUPPORTED`、`COGNITIVE_RELIEF_UNAVAILABLE`、`UPSTREAM_PEDAGOGY_HOLD` 及新最终文案审核缺口。即使未来外部 Copy 审核通过，也不能借此解除上游教学 HOLD。

## VO / Screen / Silence 与审核

每拍独立保存 VO、Screen、认知状态、attention/delivery intent、来源引用和 Silence Candidate。Screen 用原题、Evidence、对象及结构；VO 用已有行动文字；Silence 让真实变化与停止落定。留白只给 0.3–1.0 秒范围建议，没有最终起止时间、帧数、Camera、颜色、AE 参数、TTS 参数或音频生成。

需要口述的 Tell Now 不能被 silence 或另一句 copy 覆盖。必须呈现的其它边界保留原 scene、表达和 coverage。以后任何文案、对象、原题层或安排变更都必须重新绑定当前最终审核，不继承旧时间线批准。

| 机械审计 | R02 | G01 诊断 |
|---|---|---|
| 第一动作可执行且唯一 | PASS | PASS |
| 原题首先出现且保留 | PASS | PASS |
| 关注范围与工作分类精确保留 | PASS | PASS |
| 未决对象与 Stop 保留 | PASS | PASS |
| Payoff 来源 / scope | PASS，局部 | 无 Payoff；权限保留 |
| 计划中可见结构缩减 | PASS，4→3 | 不适用；禁止补造 |
| VO/Screen 原样文字重复 | 未触发 | 未触发 |
| 内部编号、角色、新营销/答案夸大 | 未触发 | 未触发 |
| AI Tone Lint flags | 空 | 空 |

Lint 是确定性文字和结构检查，不是语义认证或审美认证。连续依赖逻辑路标才标记 over_structured；单词不是绝对禁词。已冻结原文、Evidence 和逐字否定边界不被误认成新增肯定 Claim，但绑定与覆盖照常核验。AI 感、口语自然、视听语义重复和节奏仍须人工检查。`method_named_before_understood=null`，程序只知道方法名在动作之后，不知道学生是否理解。

所有真实新稿 `copy_review_state=PENDING`，R02 缺口为 `FINAL_EXPERIENCE_COPY_REVIEW_REQUIRED`；没有创建新的真实 Copy Review 来凑 READY。旧 0.3 外部批准不继承到 0.4。Human Taste 15 问、实际画面与听感均 **PENDING**。

## 验证与输入保护

| 检查 | 结果 |
|---|---|
| 新增合成体验测试 | **32 PASS** |
| 既有 Copy / Pedagogy 兼容回归 | **56 PASS** |
| 仓库全量回归 `python -m unittest discover -s tests -v` | **778 PASS**，487.403 秒 |
| ANSWER 校验 | **PASS**，82 methods / 20 source_documents / generated_assets PASS |
| R02/G01 当前真实 0.3 文案重新核验 | **PASS**；原 R02 READY、G01 HOLD 不变 |
| 受保护文件逐字 SHA 前后对比 | **457 / 457 未变** |
| Git whitespace check | PASS |

保护清单覆盖 ANSWER/Registry/Case、Pedagogy 实现与 Schema、实际冻结材料、旧 Copy 与 current 索引、Creative/AE/PR/Narration/Voice 代码、声包及既有媒体。回归、真实 replay 没有修改这些输入或现行生产资格。

合成测试覆盖当前源变化/撤回失效、重复生成、0.3 兼容与拒绝改标签、旧凭证不得继承、唯一主动作、真实 Attention/Tension/Collapse、allowed_claim 与局部答案权限、工作分类与未决候选、后台术语、重复文案、后置命名、必要口述与 Silence、没有 Payoff 的 action_demo、禁止 AE/TTS 控制、历史不可覆盖和公开门禁。

## 状态与本轮停止点

| 门禁 | 当前状态 |
|---|---|
| 体验契约工程验收 | PASS |
| R02 体验结构编译 | PASS；新最终文案缺凭证，消费 HOLD |
| G01 体验结构诊断 | PASS；上游与收益缺口，消费 HOLD |
| 真人自然口语 / 学习体验 | PENDING |
| Teaching Release | HOLD |
| Source Display Release | HOLD |
| Editorial Release | HOLD |
| public_render_ready | **false** |

当前只能证明：同一个有效 Pedagogy 0.4 输入能稳定编译出有来源的学习接触顺序、唯一动作、真实变化和 Stop。不能据此宣称已经更自然、学生已理解、会收藏或会迁移。

本轮停在 Student POV 0.4。只实现 first_touch / bounded worked_example 的动作与收益体验；其它 experience_kind 保留契约位置，没有自动启用。没有接入声音、渲染或 Creative 生产，没有替换 current-copy / current-voice 或现有 A/B。公开仓库只提交代码、工作流、Schema、合成测试与本脱敏报告。
