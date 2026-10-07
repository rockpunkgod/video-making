# Student POV Copy Realization v0.3

Pedagogy Compiler 决定 WHAT TO TEACH；Student POV Copy 决定 HOW IT FEELS TO USE；Motion 决定 HOW IT MOVES；Premiere 决定 HOW IT PLAYS。本层是 `student_pov/`，不是第二个 Pedagogy Compiler。

```text
Frozen ANSWER + current status
 → approved READY PedagogyPlan
 → sealed Copy-facing projection
 → Student POV realization
 → Motion Identity / Shot / VO / Subtitle
 → AE / Premiere
```

“approved”在工程 API 中指 Compiler 当前重检通过且 READY 的冻结教学选择；最终 Copy 的语义保真和自然口语仍必须有另一个精确文案绑定的外部凭证。Human Taste 必须 PENDING，不能由程序自签。

## 不跨越的职责

Copy 不改变 Tell Now/Later、Role、答案范围、Evidence、方法适用、是否跳步或 Stop 状态。`validate_handoff` 在入口先重新核验 Plan 与当前冻结资产；first_touch HOLD 不能偷换成 first_touch READY。可以明确选择 READY bounded worked_example。

候选自然表达使用模型无关 adapter.propose(small_projection)，或显式 `draft_lines`。适配器只获得轻量投影，不拿 Registry/自由求解器。每句候选绑定既有 Plan 字段，主动作/记忆句必须引用各自对应字段。新表达没有最终语义保真和自然口语凭证则 HOLD。写法判据见“自然口语”一节，判据本身不是凭证。测试仅使用模拟适配器，不调用 Astra 或外部语言模型。

## Baseline、Method Path、Removed Work

实现优先从上游已有 Review 的 `reviewed_payoff` 消费 `payoff.reviewed_support`：同题/方法版本/实际动作、自己的 Evidence、baseline_path、method_path、removed_steps、remaining_steps、cognitive_work、实际 reduction、allowed_claim、cognitive_relief_line、可转用第一动作声明以及实际 Output anchors。它不是用户要求 ANSWER 必须新增的教学 Review。后备的 `frozen_candidate_transition` 可从已有审阅局部排除机械投影真实候选变化；不造 Review，不推断学生常见路径。

`student_path_comparison.support_origin / baseline_kind / baseline_measured / learner_transfer_validated` 随 Copy 保存。机械输入的 baseline 是原候选集合，不是测得的学生路径；唯一自有局部排除可以关闭当前候选核验任务，其他候选和必要 Stop 仍需完成。它始终不声称 baseline 已测量或学生迁移已验证。显式 reviewed_path 也仅搬运源声明，不借 AI 文案凭证升级人工教学认证。

每个 path step 有源中已有 text 与 work_ids；removed 需在 baseline 出现、在当前 method path 消失，不能与 deferred/still_required 混同。reduction 需 before>after>0、ID 数量一致、after IDs 属于 before；Output anchor 必须精确指向当前实际产物及其 hash。算法核绑定和结构，不认证基线路径真实性或推理正确。

没有真实受凭证支持的 removed_work，输出 HOLD/PAYOFF_UNSUPPORTED。不能从“整篇文章很长”“方法名很简洁”“分组后很好看”倒推出学生节省了工作。永久 removed 只在明确限定的 scope 内成立；后续仍要做的词形或上下文不能称“不用做”。

## TYPE A / B / C

| 类型 | 强制事实权限 | 边界 |
|---|---|---|
| TYPE_A Direct Decision | decider + 实际 candidate_decision | 局部 retain/eliminate 不继承整题 answer permission；候选变化须和实际排除一致 |
| TYPE_B Candidate Collapse | reducer + 显式实际 remaining/retained candidate 产物 | 普通 candidate_partition 保留全部候选，只证明组织变化，不能伪称 4→2。当前 Core 没有这种显式剩余产物时诚实 HOLD |
| TYPE_C Reading / Structure Collapse | locator/interpreter/framework + 相容定位/解释/骨架/route 产物 | 保留真实 framework 类型，不伪映射 decide；有据范围/结构简化也不授予答案 |

框架路线不得将 word_form、derivation、number、possessive、gerund_check、context_check 包装成 removed。G01 到名词性节点后的具体词形 deferred，上下文与该节点内部规则 still_required；是否可用动名词不能由本层新分类。

## 学生体验与文案契约

PAIN、INTERRUPT、FOCUS、ONE ACTION、COLLAPSE、PAYOFF、STOP/DECIDE、METHOD STAMP 是八种认知功能，不是固定八幕。可以合并功能、结束更早或留白，不填满30/60/90秒。默认先使用、出现有据效果，再在 Stop 后显示方法名和记忆句；C端不显示 R01/G01 等编号。

first_touch 只有一个 Main Simplification/主动作，并继续受 Compiler 认知预算及 Tell Now 约束。Acquisition 是一个痛点/动作/Payoff/必要边界/记忆句；复杂边界和案例进入 Depth 系列，不在 Copy 层擅自隐藏。worked_example 是边做边学，不等于完整题解。

Pain 来自既有症状或具体题面结构，不造“90%的学生”。Interrupt 只有已批准 Payoff/动作支持才能说。Focus 不把入口升级成唯一决定性证据。动作语言优先看、圈、划、拆、比、对、找、留、排、停；不播放专家的 Role/Evidence/Review 内部链。

`cognitive_relief_line` 必须绑定 source_payoff_ref 与 allowed_claim；无凭证时为空或 HOLD 候选。高风险“不用认识词”同时要求具体这一题/这一步/当前判断、具体词的已有 Evidence 和已批准 shortcut；“做阅读不用背单词”总阻断。

### 自然口语：写学生怎么想，不写字段怎么读

绑定保证每句有出处，不保证它像人说的话。逐字搬运 Plan 会把“由 your 限定的是哪种功能”这类内部表述带上口播；机械套短句又会变成一串“先别→只看→先停”。两种都是机器味。本节是写作判据，不是自然口语凭证。

以下是表达倾向，不是新增禁词表或句式校验。具体语境需要时可以使用普通书面词或有目的的重复；是否保留，取决于学生听一次能否理解和这句是否推进当前动作。

写每句前先答三问：为什么是现在说这句（对应哪一个当前可见的题面事实）、学生听一遍能不能懂、去掉对象后还能不能理解。答不上来就先不写。

- 一句一个落点。一句话只推进一个判断或一个动作，多出来的拆句或删掉，不靠连接词往下堆。
- 说眼睛和笔尖的动作，不说后台术语。系统自造的名词和公文化的说法（节点、总路线、功能、决策树、空位、待核、词形；产出、判据、复核、检查、核对、定案）换成学生会说的说法：节点→这一步，功能→这个空要填什么，待核→还得再看，产出→只给到，复核→再看一遍，核对→对一下，定案→定死。学生自己就在用的词（抓手、盯住、卡在这儿）照用。这条只管学生会听到的口播和会看到的屏幕字；字段名、notes、来源与审计标记不在其内。
- 文言小词也要换成口语。不等于→不代表，尚未→还没，不能凭／不凭→不能光看，仍属→还得再，仅……不……→只……不……，任一→随便哪个，本法→这套方法，所剩→剩下。这类词单看不像生造词，凑进一句就成了课文腔，也是“有的口语有的又很书面”的主因。词表是举例，不是按表替换：同一个词在不同句子里说法不一样。
- 全片语域要一样，不混。不能有的句子口语、有的句子像念课文，也不能一句里前半口语后半书面。只有你自己写的叙述和指令参与拉平；下面几类按原样保留，不参与：方法名和记忆句这类固定叫法（绑定方法身份，不改写）、屏幕上照抄的原文与题面、学生考试会遇到的语法术语（谓语、非谓语、动名词、所有格、单复数）。判法：把叙述和指令连着念一遍，凡是念着像在读材料的句子，拿最顺口的那句当基准拉平，拉不平就整句重写。
- 指代要有画面锚点。说“这个空”时画面正圈着这个空；没有锚点的“它、这个、这里”不写。
- 念一遍再定稿。一口气念得完、不用回读；“由……限定、属于、进行、该、其”若让句子显得搬字段或拗口，就换成更直接的说法。念着别扭就重写，不靠改字段让它过 lint。
- 允许变化。“先别”“只看”这类阻断/聚焦句可用，但不是每条必须；长短句可换，可有轻微反应、必要衔接或自然停顿，不硬塞反问、感叹、网络梗或“咱们”。
- 从卡点进，不从课程进。不写“今天我们学习……”，不写课程背景，不虚构学生比例、想法或普遍痛点。
- 相邻句避免机械套同一句式。保留有助于对比、节奏或记忆的重复；重复开头却没有推进新动作时才重写。一次听不完整的长句先拆短。
- 方法名放动作价值之后，最后留下下一题能直接调用的第一动作。

用户明确不要结果后的检查清单式提醒。类似“另外几个还得再看”“现在还不能选”“这里只负责……”的自我审查口播全部省去，也不搬到字幕或单独的片尾提醒墙。已经成立的结果用短句、真实产物和停顿表达。必要边界的教学功能仍须有依据：由Pedagogy的实质Boundary Risk Review决定哪些当前需要、哪些属于未走到的后续分支；当前功能可以由正确Evidence对比和中性未定候选状态覆盖。Copy不能自行把边界移后，也不能以“安全”为由把重复提醒默认加回。`stop_vo`可以不提供，任何改稿都重新绑定文案审核。

词表用于选择新表达，不对受保护文本执行批量替换。必要的“词形”等教学对象应保留其含义；“定死”等候选说法也不能增加确定性。冻结题面、Evidence、方法名继续按契约原样投影。默认Stop逐字保留；只有显式、同题同动作的Pedagogy风险审阅才允许合并呈现或用已绑定的Evidence/Output覆盖。原Stop全文、条件及依赖仍留在Guard，不能靠删文案消除约束。

这些判据只约束表达。它们不改 Tell Now/Tell Later、Role、答案范围、Evidence、Stop，也不许因“写得顺”补出未认证的认知收益，或把 deferred 说成 removed。判据通过不等于自然口语通过。工程入口接受明确标明 AI 或人工身份、绑定最终文案的外部 Copy 凭证及 natural_speech 检查；它不代签真人听感或 Human Taste，后两项仍需人工反馈。

推荐 FinalScript 每 scene 包含 time_range、cognitive_function、visual_state、student_attention、vo、screen_copy、motion_function、evidence_ref、pedagogy_ref、removed_work、output_state、silence_after、notes。时间按版本化中文4字/秒、英文150词/分估算较长口播/屏幕阅读，不声称真实配音精确匹配。

## VO / Screen / Motion 与 Signature

VO 表达学生思考、第一动作、当前判断、节奏、短 Payoff/Stop；Screen 展示原文、Evidence、对比对象、关键词、Candidate、最终结构和实际 Output；Motion 展示有据抽离、重组、关系变化、范围/候选收缩与 Boundary Seal。结构 QA 检测相同 VO 与屏幕文本重复，完整视听重复和审美仍待人审核。

Signature 映射仅协调视觉语法：R01 Overgrowth；R02 Relation Rewire；R06 Missing Mass；R09 Semantic Compression；F01 Axis Regroup；G01 Extract→Route→Seal。映射不提供适用或结论，不能替代 Payoff 支持。本模块不调用 AE，不制作效果，不更改 Shot/Motion/PR 模块。

强视觉事件只能跟随有据的范围/候选减少、Evidence Lock、关系重组、额外块抽离、空位抽离、最终决定或 Boundary Seal。禁止装饰性 Flash/Glitch/无意义 Zoom 作为 Payoff 证明。没有实际压缩时最多是 actual_output_only_no_payoff_claim。

## Silence 与 Explanation Suppression

支持 Collapse/Answer Lock/Evidence Lock/Boundary Seal/Payoff/Transformation 后0.3–1.0秒的 Hold/Silence/Music Duck/Settle 候选。必要Tell Now可放在实际focus/action比较处；经已绑定风险审阅批准的局部范围可由候选状态覆盖。静默不用于隐藏尚未覆盖的边界。

`suppression_qa(copy,coverage)` 只产生审阅候选。coverage 由编辑显式记录画面、Motion、Evidence 均已表达且下一动作不依赖这句，才标 EXPLANATION_REDUNDANT 并建议去掉 VO。Stop 和绑定 Tell Now 的 scene 永远保护；来源 Copy 不改，原最终 Copy Approval 对变化后的候选失效。

## QA、审批与重载

Schema 为 `creative/copy-system/student-pov-copy.schema.json`。CopyAudit 包含第一动作/Role/Evidence/Stop/Tell Now/Payoff、可见压缩、学生操作结构、动作语言、解释密度、专家链泄漏、屏幕口播重复、捷径、禁说、自然口语风险。PASS 仅是 deterministic binding/claim lint；不是完整语义、自然口语或学生体验认证。

当前 Copy 契约为 0.3.0。候选不得引用未披露或后台字段；Payoff 句必须引用 Payoff/allowed_claim，Stop 句必须引用当前边界或有限输出状态，空第一动作直接拒绝。Baseline 中每个 work_id 必须明确归入 removed/deferred/still_required，后两类完整列入 remaining_steps；声明第一动作不可迁移时继续 HOLD。默认在开始场景显示原题及已绑定的 baseline，在 Collapse 显示 method_path 与实际产物。显式 payoff_line 成为唯一口播结果句，并绑定 final_copy_claim；更改它会使旧文案批准失效。无依据百分比、热点表达仍 FAIL；照录原题中的数字、英文词或来源标签不等于新造口播 Claim。

`reality_layer` 保存来自 Plan 的未填答原题、逐字段冻结引用及完整展示文本。第一景先显示原题，所有后续场景引用同一持续题面层，再用已绑定的 Evidence 聚焦。Plan 保留已有 passage/stem/options/given_word，不把 Review 答案、执行记录或方法编号投到题面；题目 ID 留作追溯。结构检查要求原题先出现且不可变，但不代签实际画面的持续可见性或阅读清晰度。详见 `docs/original-question-copy-contract.md`。

`copy_audit.observation_scope=planned_scene_structure_only` 明确这些观察只针对生成的 FinalScript。兼容字段 `cognitive_reduction_visible` 要求计划屏幕确实包含有凭证的 before→after 文本，且 Collapse 绑定实际 Output、Evidence 和 removed_work；仅有 Payoff 记录不能判 true。`student_pov_present` 要求场景有来源绑定的第一动作、Evidence 焦点和完整必要 Stop，不再固定为 true。这两个 bool 均不表示实际画面清晰、学生感到轻松或学会了操作。`actual_visual_review`、`student_experience_review` 和 `human_taste_review` 始终 PENDING；外部 Copy 文案凭证也不能自动替它们签字。

READY 要求第一动作保留、原题先展示、计划中可见压缩和完整学生操作结构均成立，且 Payoff/外部文案凭证满足要求。`inspect_historical` 和 `python -m student_pov inspect <request.json>` 仅检查保存件完整性，不核当前上游、不允许消费。历史 0.1/0.2 Copy Schema 独立保留；当前 validate/生成消费明确拒绝旧契约，须从新 Plan 与当前冻结源重建，不能修改版本标签或覆盖旧 Copy。

`final_copy_sha` 同时覆盖 script、逐景 FinalScript 与 reality_layer；`copy_review` 必须绑定 script_sha/final_copy_sha 并显式确认 semantic_fidelity、natural_speech、layer_division。任何相关文字、题面层或场景修改让旧批准无效。AI凭证不升级人工教学认证。Human Taste 14问见 `STUDENT_POV_HUMAN_TASTE_REVIEW.md`，始终等待真实用户/人工意见。

```python
from student_pov import realize, validate_copy
candidate = realize(copy_projection, plan, frozen_bundle, current_status)
validate_copy(candidate, copy_projection, plan, frozen_bundle, current_status)
```

独立 `python -m student_pov realize|validate|inspect <request.json>`，只读明确列出的计划/投影/资产/状态和可选 draft_lines/copy_review；inspect 只需指定 copy。命令不覆盖历史。教学、来源、编辑与公开渲染始终独立，本模块不自动发布。

当前真实Copy以本地`local-data/pedagogy/current-copy.json`为入口。R02已完成九项Boundary Risk Review，实质结论和绑定规则见`R02_BOUNDARY_RISK_REVIEW.md`；当前稿省去结果提醒，保留关系对比和真实候选状态。G01同步稿删除冗余Stop VO，缺受支持的工作减少，继续HOLD；本轮没有替G01做风险降级。旧20秒Hero只保留为历史视觉证明，不能继承新文案或新Plan的审核。详见`STUDENT_POV_COPY_ACCEPTANCE.md`。
