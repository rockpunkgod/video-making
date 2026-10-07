# Student POV Copy Realization Acceptance

日期：2026-10-07。**工程契约通过；真实新层输出 HOLD。** 这份报告不把既有20秒 native Hero 的视觉证明当作 Payoff、学生体验或自然口语验收成功。

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
| Human Taste 14问 | PENDING：`STUDENT_POV_HUMAN_TASTE_REVIEW.md`，无自签 |
| 真实黄金候选数量 | 1：G01 bounded worked_example；未制作六条视频 |
| 真实 Student POV Release | HOLD；public_render_ready=false |

## 唯一真实候选

源是已有 G01 q59 冻结实际 route/noun-node action，Plan 使用 `compiler-r2/G01/worked_example.plan.json`。它具有精确 Evidence、Role/版本和 Stop，但当前缺已有 baseline_path、removed_work 与自然文案最终凭证。具体词形仍待核，未排除全部动名词；路线 Output 不能变成填词答案。

忽略的 `local-data/pedagogy/student-pov-r3/G01/` 保留（r2 原候选作为历史保留）：

- `literal-realization.json`：严格字面默认投影，HOLD。
- `hook-variants.json`：3条有 Plan 来源的可审阅候选，均 HOLD_FIDELITY_REVIEW_REQUIRED。
- `payoff-variants.json`：2条有边界的 Output settle 候选，均 HOLD_PAYOFF_UNSUPPORTED；不声称省下真实工作。
- `draft-lines.json`：自然操作语言候选，无新教学 Review。
- `recommended-copy.candidate.json` / `final-script.candidate.json`：唯一推荐候选，逐 scene 含时间估算、认知功能、VO/Screen/Motion、Evidence/Plan引用、removed_work/output/silence/notes。
- `stop-boundary-audit.json`：两条 Tell Now 完整保留；未擅自降级或解除 Stop。

推荐 Copy SHA：`bb4e51b3620ec97f58a39f3c8840c27cc7a9a256ce8dbd26f14933add55bb820`。状态为 HOLD，issues 空；缺口为 `PAYOFF_UNSUPPORTED:missing_reviewed_baseline_and_removed_work`、`COGNITIVE_RELIEF_UNAVAILABLE`、`FINAL_COPY_SEMANTIC_AND_NATURAL_SPEECH_REVIEW_REQUIRED`。r3 仅加固审计范围，Compiler r2 Plan SHA、实际文案与 FinalScript SHA 均未变。

真实候选 `cognitive_reduction_visible=false`，因为没有已核 baseline/removed_work，也没有计划 before→after 对照；`student_pov_present=true` 只表示已生成有来源的第一动作、Evidence 焦点和完整 Stop 场景。后者不是学生实际感到轻松或理解了方法的证明。两项观察明确标记 `planned_scene_structure_only`；actual_visual_review、student_experience_review 与 Human Taste 均 PENDING。

真实题面、答案、片段与候选全文不进入 Git。公开报告不复制高考试题。静态结构/版本/绑定通过不代表候选口播语义、自然感、学生理解或陌生题复用已验证。

## 测试与限制

本层16项合成测试全部通过；与 Compiler/整篇适配合计36项新增测试通过，不将多轮累计。审计范围加固后重新运行这16项，全部通过，包含“有 Payoff 但未显示 before 不算可见压缩”、第一动作缺失不算学生操作结构、不能伪签 actual_visual_review 及重封装审计也不能绕过重载验证。合成 TYPE_A/TYPE_C 正例只验证通道；TYPE_B 普通 partition 明确 HOLD，因为当前 Core 不提供已核剩余候选的产物，不修改 Core 来凑正例。

负例包括：reducer“答案出来”、locator“找到能选”、framework填具体词、缺路径或无下降、改 Output anchors、词形由 deferred 伪装 removed、删 Tell Now、无依据词汇捷径/泛化、直播后台链、原文/Evidence改义、先讲内部方法编号、Copy改后沿用批准、上游撤回后重载。

自然候选允许改表达，必须绑定已有 Plan 字段并送独立最终保真/自然口语审核；程序不能替代完整语义认证。VO/屏幕重复检查和动作词出现是结构信号，学生的认知体验和审美仍由真实 Human Taste 回答。只要实际压缩、必要边界或文案凭证未满足，继续 HOLD，不以传播性或包装覆盖 Practical Use。
