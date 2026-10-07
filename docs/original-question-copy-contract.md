# Original Question / Persistent Reality Layer — v0.3

先展示原题，再在同一道题上展示方法动作。当前增量补齐 Compiler→Copy 的题面消费契约；不读取原始题库、教学 Markdown 或 Registry，也不重新解题。

## 冻结输入与投影

`PedagogyPlan.original_question` 只投影已有的 `question_id`、`question_type`、`passage`、`stem`、`options`、`given_word`。缺失保持缺失，显式 null 保持 null；题目 ID 用于追溯，不显示在 C 端题面。`correct_answer`、Review 答案、analysis、action_executions 等不进入展示快照。

`original_question_refs` 对每个实际投影字段保存 asset_id、JSON pointer 和规范化内容 SHA；整篇冻结传输的文章引用 `/payload/passage`，题目字段引用其自己的 `/payload/questions/<index>/...`。普通冻结传输引用 `/source_snapshot/...`。所有引用纳入 Plan 来源台账，源重放拒绝字段修改、遗漏引用及借用其他题目的内容。

## 先展示与持续题面

Copy 的 `reality_layer` 保存原题、逐字段引用、字面屏幕文本、`persistent=true`、`fact_mutation_allowed=false` 和 Plan 引用。第一景先展示完整可用题面；后续每景保留 `reality_layer_ref=/reality_layer`，Evidence 聚焦与动作发生在同一题面上。选项字母保留，不显示内部方法或题目 ID。

照录的题面与 Evidence 是 source text，不按新增口播 Claim 的禁词或统计 lint 改写。新写的口播和教学提示继续受 Claim lint、角色、范围与引用约束。真实画面的原题可见性、字号、范围缩小和停留时间仍待实际视效审核；计划字段通过不等于渲染验收。

## 文案锁与历史

0.3 的 `final_copy_sha = SHA-256(canonical JSON({script, final_script, reality_layer}))`。题面文字、题面绑定、场景或口播变化使旧 Copy 凭证失效。历史 0.1/0.2 使用各自原有的最终文案指纹定义，只允许完整性检查；新消费必须重新从原冻结输入与提供的当前状态生成，不覆盖旧文件。

屏幕阅读与口播仍按中文4字/秒、英文150词/分估算较长者，加显式停顿。完整题面快照可能让默认保守估计更长；本增量不为达到15/30/60秒而隐藏题面、压掉 Stop 或宣称全文已经读完。后续导演可提出有据的阅读焦点方案，再核验最终实际展示与节奏。

## 完成范围与未完成项

- 完成：冻结题面逐字段引用、先题面后聚焦的 Copy 计划、持续题面引用、最终指纹与历史迁移门禁。
- 保持：真实 G01 bounded action 缺少受支持 Payoff，继续 HOLD；当前 G01/R02 最终文字已绑定 AI Copy 文本复核，真人听感与实际画面仍待审。旧 native 样片不继承新版本资格，公开资格为 false。
- 完成：已有冻结候选变化到 Payoff 的机械适配。专门 `reviewed_payoff` 继续兼容；原候选域与有效的唯一自有局部排除也可形成结构状态对照，不要求 ANSWER 新增 Review，不推出学生行为、提速或最终答案。
- 未认证：真人听感、Human Taste、学习效果、实际画面持续可见性、陌生题迁移和公开来源权限。

transfer/hard_case 的完整内容投影以及 simultaneous_concepts 的 step-kind 近似仍是已有能力限制，不纳入完整教学系列或实际认知负担验收。当前验证与真实 Copy 状态见两份 Acceptance 报告。
