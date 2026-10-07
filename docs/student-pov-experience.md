# Student POV v0.4：学生第一视角学习体验

本层把已经冻结的 Pedagogy 选择编排成学习者接触对象、执行动作、看到变化、停下和记住第一刀的顺序。它不是另一个解题器，也不决定教学压缩。本轮消费真实 Pedagogy 0.4 Copy/Motion Handoff；既有 Copy 0.3、声音、Creative、AE 与 Premiere 链保持兼容。

```text
ANSWER：什么是真的
  → Pedagogy：现在必须学什么
  → Student POV：怎么经历这次学习
  → Creative：怎么导演这次经历
  → Narration Performance：已批准的文字怎么演
  → AE / PR：视听执行
```

## 输入与当前门禁

`realize_experience(copy_handoff, motion_handoff, plan, bundle, status)` 先按 0.4 重新核验 Plan 和两份 Handoff。只消费已批准的第一动作、主简化、Work Delta、Payoff、边界覆盖、原题、Evidence 引用与认知对象。它不读 Registry、题库或教学 Markdown 补事实，不调用 Analyzer，不修改上游输入。

Motion 的 `reference_catalog` 在核验后还原为已有引用。对象 ID、注意力范围和未解决状态逐项来自它的认知结构；没有英语解析、新角色归因或新候选淘汰。

当前只实现 first_touch / bounded worked_example 的单一主动作体验。Schema 为 action_demo / cognitive_payoff / boundary_demo / transfer_demo / counterexample 保留类型，但后三类没有被本轮自动启用；需未来有相应 Case 交接与明确消费实现。多个竞争主动作直接拒绝，supporting 不成为另一个前台主动作。

上游 HOLD 没有合法 Handoff。本层可显式设置 `allow_held_plan=true`，只从当前有效 Plan 的已披露字段生成**诊断草稿**：输入标记 DIAGNOSTIC_UPSTREAM_HOLD，两份 Handoff SHA 为 null，消费资格始终阻断。这不是补造上游 Handoff 或批准。当前 G01 仅走此路径，Baseline/收益仍为空。

## Experience Curve 与 Beat

认知阶段为 PAIN → INTERRUPT → ORIENT → FOCUS → ACT → TENSION → COLLAPSE → PAYOFF → STOP → MEMORY。它们不是固定十幕，每个出现阶段都需精确 Pedagogy 引用；不能为了戏剧性补齐。

现有 cognitive_function pain / interrupt / focus / action / collapse / payoff / stop / stamp 保留，另支持 orient / tension。ORIENT 可以由清楚的 Focus 承担；TENSION 可与真实动作共享一拍；Collapse + Payoff 默认共用一拍。MEMORY 使用 stamp function，先回收真实第一动作和短记忆句，再显示方法名。

| 阶段 | 来源与职责 |
|---|---|
| Pain | 原题与既有 symptom；不发明学生比例或焦虑 |
| Interrupt | 已有明确负向动作指令；不能从好听的 Hook 推出新 Anti-rule |
| Orient / Focus | 已有 first_signal、focus object 和 attention transition；不新增阅读范围 |
| Act | 唯一 primary_action 的 instruction、实际动作和 Output 绑定 |
| Tension | 已有 unresolved object；不能创作“两个都对得上”的冲突 |
| Collapse | primary_simplification、真实 Work Delta 与 before/after 结构 |
| Payoff | 只绑定允许 Claim 与局部 scope；可没有 VO，让真实变化落下来 |
| Stop | 当前产物、未解决对象、deferred / required、禁止后续推断与必要覆盖 |
| Memory | 刚执行的第一刀、冻结 memory phrase、后置方法名 |

R02 的当前 Handoff 没有可直接投影成 Interrupt 的负向动作文字，默认省略该阶段，不把“少读全文”补成新指令。Focus 已能交接已有注意力范围，因此默认不拆独立 Orient。可审阅候选只能引用当前允许字段；新的措辞仍等待精确最终文案审核。

每个 Beat 保存 ID、cognitive_function、计划中的前后学习状态、VO、Screen、注意力/张力/缩减/Payoff/未解决状态、delivery_intent、silence_candidate 和来源绑定。学习状态是计划标签，不声称观众已经焦虑、理解、释放或记住。

## 原题、VO、Screen 与留白

`reality_layer` 保存逐字原题与字段引用，首先出现并被所有 Beat 持续引用。题目 ID 留后台，内部 R02/G01 等编号和 Role 不进入新增消费端口播。Evidence 由 Handoff 的有效引用读取冻结 JSON 中的已有 quote，不扫描原始材料。

VO 推进行动、判断与节奏；Screen 展示原题、Evidence、对象、结构和固定记忆表达。默认 Focus 用已有 Evidence，Act 用第一动作语言；不把方法四步卡、完整推理链和结果待办清单逐句念完。

Stop 的必要覆盖留在上游规定的 focus/action/stop encounter。R02 已审阅的原则留在真实 action 对比处；候选保持中性未定状态，结果后不补“另外三个还得看”“现在还不能选”的提醒，也不另建提醒墙。G01 没有同等风险降级凭证，其诊断草稿保留原必要字面边界，不能套用 R02 的呈现许可。

`collapse.learner_visible` 只检查计划屏幕存在 before→after、实际受支持 removed work 和有据变化，不检查实际渲染或学生感受。只有来源支持候选缩减才出现 Collapse；普通 route 或已有产物不自动得到收益。局部 4→3 不获得最终答案资格。

Silence Candidate 只在 collapse / payoff / answer_lock / evidence_lock / boundary_seal / transformation 的有据节点提出 0.3–1.0 秒范围。本版使用 Collapse/Stop settle，没有最终起止时间、帧数或毫秒安排。必须说出的 Tell Now 不能改成无 VO；范围和最终时间由 Creative / PR 决定，不继承旧时间线批准。

## 意图接口与禁止事项

`attention_intent` 只列 focus / background / preserve / unresolved 对象 ID；范围逐项等于 Pedagogy attention transition。`delivery_intent` 只表示认知状态、speech_function 和 concise / alert / direct 等说话倾向，voice_execution=false。

本层不输出 Camera、blur、Z、Peel、颜色、关键帧、speed_factor、pitch、reference 或 Emotion API，不生成声音或 take，不调用 GPT-SoVITS，不修改 Premiere。默认没有固定总时长，不把认知内容填进 30/60/90 秒。

## 文案规则与审核

默认语言目标是 Intelligent Conversational Teaching：聪明、直接、自然、有判断。既有 Copy 自然口语三问与画面锚点判据仍有效，参见 `docs/student-pov-copy.md`。允许有来源与明确对象的碎句，不强制完整书面句，也不把字面默认投影当作自然口语认证。

新 `draft_lines` 可指定 pain / interrupt / orient / focus / action / payoff / stop / memory，每句须绑定精确、用途允许的 Plan 字段。Action 必须绑定 primary instruction，Payoff 必须绑定 allowed_claim，Memory 必须绑定冻结 memory_phrase；后台 Guard、Later、其它方法或无来源文本不可消费。候选不能替换对象、工作分类、Evidence、答案、Role 或 Stop。

外部 `copy_review` 必须是 0.4 凭证，精确绑定 source_plan_sha、script_sha、final_copy_sha，明确 reviewer / reviewer_kind，并确认 semantic_fidelity / natural_speech / layer_division。它不升级 ANSWER 教学认证或真人听感。0.3 的批准不继承；词句、对象状态、顺序、原题层或相关体验安排变化都会使旧批准失效。

`compilation_status=PASS` 表示当前体验交接结构成立。没有新最终文案审核时 availability=HOLD；真实体验与发布仍待独立审核。新的外部文案凭证在合成测试中可以解除文案缺口，不能解除 G01 的上游 HOLD。

## Audit 的能力边界

Experience Audit 检查唯一可执行第一动作、原题先出现、注意力来源、真实缩减、局部权限、工作分类、未解决对象、当前 Stop 覆盖和后置命名。`method_named_before_understood=null`：程序只能检查是否先于动作，不能观测学生“已经理解”。

AI Tone Lint 检测常见统计/热点、角色与答案夸大、词汇/阅读收益泛化、内部术语、原样 VO/Screen 重复、长句和解释模板。连续依赖“首先/其次/接下来”等才标 over_structured / too_many_signposts，单独一个词不是绝对禁词。冗余结果提醒也送审核。

这是确定性文字与结构 lint，不是完整语义或真人听感认证。“robotic_logic”等是触发已知句式的风险标记，不表示程序识别了所有 AI 感；unnatural_complete_sentence、lack_of_rhythm、真正的画面与声音语义重复仍需人工。固定原题、Evidence 和逐字边界的否定/引用不作为新营销 Claim 改写，但其绑定与覆盖仍严格重检。

Human Taste 的新 15 问全部 PENDING。没有 experience_is_good、student_will_understand 或程序自签 PASS。三类 Release 保持 HOLD，public_render_ready=false。

## API、CLI 与兼容

```python
from student_pov import realize_experience, validate_experience

experience = realize_experience(copy_handoff, motion_handoff, plan, bundle, status)
validate_experience(experience, copy_handoff, motion_handoff, plan, bundle, status)
```

既有 `realize` API 默认仍为 Copy 0.3。新调用可显式 `contract_version="0.4.0"` 并提供 `motion_projection`；`validate_copy` 可按同一精确版本分派。0.1/0.2/0.3/0.4 都能历史 inspect，缺当前源时无消费资格。迁移只能从当前真实 Pedagogy 0.4 重新 realize，不能改旧版本标签或覆盖历史输出。

CLI 保持 `python -m student_pov realize|validate|inspect <request.json>`。0.4 请求列 plan、projection、motion_projection、bundle、status、contract_version，输出仍用 output，validate/inspect 仍用 copy。可选 draft_lines/copy_review 文件与 options；当前 HOLD 诊断显式指定 allow_held_plan，不提供假 Handoff。

真实草稿和请求保存在忽略的 `local-data/pedagogy/student-experience-v04-r1/`。它们不替换 current-copy / current-voice / production 索引。验收见 `STUDENT_POV_V04_ACCEPTANCE.md`。
