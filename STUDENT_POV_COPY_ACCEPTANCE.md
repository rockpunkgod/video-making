# Student POV Copy Realization Acceptance

日期：2026-10-07。当前 Compiler/Copy 契约 **0.2.0**，审计修复基线 `main@6380ffc`。**工程契约通过；真实新层输出 HOLD。** 这份报告不把既有20秒 native Hero 的视觉证明当作 Payoff、学生体验或自然口语验收成功。

## 交付

| 项目 | 状态 |
|---|---|
| System Specification / 层间职责 | PASS：`docs/student-pov-copy.md`；不重做 Selective Disclosure |
| 正式 Schema | PASS：`creative/copy-system/student-pov-copy.schema.json` |
| Baseline vs Method Path / Work disposition | PASS（契约）：绑定已有 reviewed_payoff；未提供则空/UNKNOWN，不造事实 |
| TYPE A/B/C mapping | PASS（门禁）：真实 Role/Output、局部/最终答案权限、Output anchor；普通分组不能伪称候选退出 |
| Cognitive Relief | PASS（绑定控制）：source_payoff_ref/allowed_claim；缺真实 removed_work 则 PAYOFF_UNSUPPORTED |
| 一个 first_touch 主简化 | PASS：单一主动作；Compiler HOLD 不自动转 READY |
| 三层表达/Signature协调 | PASS（契约）：VO/Screen/Motion 分工，方法名后置；编号只留后台 |
| Silence contract | PASS：0.3–1.0秒，实际支持事件后 settle，必要边界仍可见 |
| Explanation Suppression QA | PASS：仅去冗余 VO 的候选，Stop/Tell Now 保护，原 Copy 不改、审批失效 |
| CopyAudit / 防越权 | PASS（确定性 lint）：ROLE/Stop/证据/词汇捷径/专家链/重复/自然口语风险 |
| CopyAudit 观察范围 | planned_scene_structure_only；实际画面、学生体验与 Human Taste 均 PENDING，不由 bool 自动认证 |
| Final Copy review binding | PASS：script_sha + final_copy_sha，任何相关改动令旧批准失效 |
| 0.2 场景与引用门禁 | PASS：baseline→method_path 显示、有据主动作/完整 Stop；空动作、后台字段引用、错用途 Payoff/Stop 引用拒绝 |
| 0.2 Work disposition | PASS：baseline 全量归类、remaining 完整对应 deferred/still_required；无迁移第一动作继续 HOLD |
| 0.1 历史迁移 | PASS：历史完整性可读，当前不可消费；重生成新 Copy，旧输出字节不变 |
| 自然口语写作指导 | 已加入三问、画面锚点、试念与语气变化；写作倾向不作为禁词表、审核凭证或学生体验通过证明 |
| Human Taste 14问 | PENDING：`STUDENT_POV_HUMAN_TASTE_REVIEW.md`，无自签 |
| 真实黄金候选数量 | 1：G01 bounded worked_example；未制作六条视频 |
| 真实 Student POV Release | HOLD；public_render_ready=false |

## 唯一真实候选

源是已有 G01 q59 冻结实际 route/noun-node action，Plan 使用 `compiler-r3/G01/worked_example.plan.json`，SHA 为 `647711d4672971f66282af39bee59038d66c33d185ee6541c8a02d5124c4cc8d`。它具有精确 Evidence、Role/版本和 Stop，但当前缺已有 baseline_path、removed_work 与自然文案最终凭证。具体词形仍待核，未排除全部动名词；路线 Output 不能变成填词答案。

当前输出位于忽略的 `local-data/pedagogy/student-pov-r4/G01/`（r2/r3 原候选作为历史保留）：

- `literal-realization.json`：严格字面默认投影，HOLD。
- `hook-variants.json`：3条有 Plan 来源的可审阅候选，均 HOLD_FIDELITY_REVIEW_REQUIRED。
- `payoff-variants.json`：2条有边界的 Output settle 候选，均 HOLD_PAYOFF_UNSUPPORTED；不声称省下真实工作。
- `draft-lines.json`：自然操作语言候选，无新教学 Review。
- `recommended-copy.candidate.json` / `final-script.candidate.json`：唯一推荐候选，逐 scene 含时间估算、认知功能、VO/Screen/Motion、Evidence/Plan引用、removed_work/output/silence/notes。
- `stop-boundary-audit.json`：十条 Tell Now 完整保留；未擅自降级或解除 Stop。
- `migration.json`：原源包/状态与全部 r3 候选文件前后字节 hash 一致；仅迁移绑定和新增完整边界，逐句候选措辞未改。

推荐 Copy SHA：`9f8c612b0b789127f00aebb8fbc0f3f3b41c7058d3d1c175f5cc3cb50ee828d7`；Final Copy SHA：`ea7ea54e86e19fe9a0b99a0f259b0dc1052639868ac9f549e5f86dd2bf4d7bba`。状态为 HOLD，issues 空；缺口为 `PAYOFF_UNSUPPORTED:missing_reviewed_baseline_and_removed_work`、`COGNITIVE_RELIEF_UNAVAILABLE`、`FINAL_COPY_SEMANTIC_AND_NATURAL_SPEECH_REVIEW_REQUIRED`。旧 r3 Copy SHA `bb4e51…` 只作历史完整性检查；新 Stop 屏幕及来源绑定改变了最终 Copy，不能沿用旧批准。

真实候选 `cognitive_reduction_visible=false`，因为没有已核 baseline/removed_work，也没有计划 before→after 对照；`student_pov_present=true` 只表示已生成有来源的第一动作、Evidence 焦点和完整 Stop 场景。后者不是学生实际感到轻松或理解了方法的证明。两项观察明确标记 `planned_scene_structure_only`；actual_visual_review、student_experience_review 与 Human Taste 均 PENDING。

真实题面、答案、片段与候选全文不进入 Git。公开报告不复制高考试题。静态结构/版本/绑定通过不代表候选口播语义、自然感、学生理解或陌生题复用已验证。

## 测试与限制

0.2 专项运行：Compiler/整篇适配24项、Student POV23项，共47项通过；native Cognitive binding6项另行通过，合计53项。包含 baseline 进入屏幕、明确 payoff_line 实际交付及旧批准失效、空主动作/错引用拒绝、baseline 遗漏 Work/不可迁移动作 HOLD、重复和畸形标识 HOLD、统计/热度越权 FAIL、READY 场景结构约束、旧 Copy 历史可读但当前不可消费。合成 TYPE_A/TYPE_C 正例只验证通道；TYPE_B 普通 partition 明确 HOLD，因为当前 Core 不提供已核剩余候选的产物，不修改 Core 来凑正例。

当前新 Plan 与旧20秒 native Spec 绑定检查按预期拒绝：旧展示缺少新完整 Tell Now。旧视频保留为历史视觉证明，未重新渲染或换 SHA 继承新 READY；新文案候选不自动获得生产或学生验收资格。

完整共享工作区回归：`python -m unittest discover -s tests -v`，628项通过（执行快照，含其他独立模块）；本地日志 verification-r4/full-regression.log。ANSWER 校验继续为82 methods / 20 source documents / generated assets PASS。源包/状态及原候选 JSON 字节 hash 不变，当前自然措辞也未改；新合同仅新建本地输出，未提交真实题面、文案、媒体或 Adobe 工程。

负例包括：reducer“答案出来”、locator“找到能选”、framework填具体词、缺路径或无下降、改 Output anchors、词形由 deferred 伪装 removed、删 Tell Now、无依据词汇捷径/泛化、直播后台链、原文/Evidence改义、先讲内部方法编号、Copy改后沿用批准、上游撤回后重载。

自然候选允许改表达，必须绑定已有 Plan 字段并送独立最终保真/自然口语审核；程序不能替代完整语义认证。VO/屏幕重复检查和动作词出现是结构信号，学生的认知体验和审美仍由真实 Human Taste 回答。只要实际压缩、必要边界或文案凭证未满足，继续 HOLD，不以传播性或包装覆盖 Practical Use。
