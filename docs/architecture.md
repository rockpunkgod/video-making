# Method Engine 架构

本实现另存于video-making，ANSWER源仓库只读。优先级：正确性>课程证据>触发>执行>迁移>效率>记忆>传播。验收仍先传播、冻结、再强可用性；后者有否决权。

```text
冻结课程 → Registry（方法卡 + 逐字源章节）
                     ↓
题面/卡点 → Matcher → Composer → QuestionAnalyzer → EvidenceGraph
                                     ↓
                       PaperAnalyzer / 四种Renderer
真人观察 → Evaluation → 人工审阅升级（不自动写Registry）
```

source-sections保存运行时章节逐字内容、行区间和提交号，方法卡提供动作及引用。provenance是只读审计，不作第二份人工维护事实源。学生稿、Legacy参考、症状与角色表是生成投影；generate_assets --check检查漂移。

核心为确定性的结构、跨度与流程约束引擎，不是已校准的自由文本英语解题模型。无语义审阅时给方法建议/动作/刹车，answer=null。关系由宿主/人工提交，或Python review_provider产生；跨度一致不能证明语义正确。题型/任务/难度标注也要审阅。

七选五 F01–F04 的初筛 reducer 可以只引用所有候选各自的选项跨度，产出完整 candidate_partition；不强塞无关正文引文。此窄例外不产生保留/排除关系，不缩成唯一答案，也不适用于其他角色或方法。决定候选的 relations、candidate_decision 以及正文内容动作仍须引用本题正文。原题不完整时不绕过输入完整性门禁。

review_provider只补审阅标注，不替换原题。调用前先校验输入并保存独立深拷贝；返回后再校验，并逐项锁定question_id、question_type、stem、passage、options、given_word、student_text、continuation_starters、original_images及student_symptoms，连字段的新增/删除也拒绝。接口可以补observations、relations、action_executions、writing_review、lesson_review、requested_chain，以及task_type/difficulty标注；这些仍接受各自门禁。需修正题型或题面时，调用方先核对并重新提交题目，不能在审阅过程中悄悄换题。整卷入口复用同一限制，推荐题号因此仍绑定原输入。这是数据一致性控制，不是对Python回调的安全隔离或语义认证。

Reviewed结论要求独立触发、当前题面跨度、具体判据、Stop检查、回填验证、审阅者与明确决定职责。不完整/未审阅/冲突关系不定案；排除与剩余不证明答案。提供options时，必须有唯一候选自身的保留证据，且其他候选全部具有审阅后的排除证据；单个保留项不能跳过未核验竞争项。无选项的语法生成仍需唯一词形的独立审阅关系。answer_verification列出保留、排除、未决候选及闭合状态，不是语义真实性认证。辅助角色不独立decide；C01只有显式二阶段decider可闭合当前空。

图检查节点唯一、边闭合、无环、引文标签与跨度相同，以及同一方法的独立触发、同一候选的主张→审阅关系→结论路径。validate_graph(graph, question)可将每个引文重新绑定当前题面；Analyzer自动执行此检查。仅传graph不能认证源文本真实性，两个模式都不认证审阅者身份或语义为真。未闭合题不进整卷内容推荐；展示分为启发式排序，不代表传播或提分效果。

结论与candidate_decision产物还要求同一条已审阅关系明确绑定相同method_id和candidate；候选主张及该方法的独立触发必须在这条关系自身的上游，关系另有直接引用的source_evidence。把无关候选关系、触发或主张接到结论旁边，不能充当自己的推理链；只有触发引文也不能代替决定关系的引用。写作核验关系明确标记student_draft，不能借另一原稿关系；旧的写作分析若缺该关系标记须重新分析，原writing_review输入契约不变。这些检查仍只证明图与输入/外部审阅的结构一致，不认证英语推断或评分为真。

method-registry/symptom-cues.yaml保存口语导航别名，不复制方法判据；公开症状表从它和方法卡生成。具体卡点优先于通用题型入口，口语匹配仍为low/trigger_verified=false，不能直接授权关系定案。题型和任务范围由调用方审阅；段落主旨不得调用全文覆盖排除法。未覆盖口语退回结构入口，不假称语义分类已经校准。

接口：QuestionAnalyzer.analyze(dict)、PaperAnalyzer.analyze(dict)、CLI；契约为Draft 2020-12 JSON Schema。当前部署为完整仓库+Python3.10+，源码或editable安装。单独Skill文件夹仅自包含宿主答疑，不自动安装核心。未建抓取/视频/AE/支付/发布服务。

Paper Analysis 1.1.0保留原输出字段，并增加method_coverage和typical_method_candidates；Schema仍接受旧1.0.0投影。method_counts只表示匹配/建议次数，包括未核验的结构入口，不是适用率。method_coverage按方法列出潜在匹配、独立已核验触发、已提交产物、已审阅决定及案例候选题号；每一层都能回到questions核证据和角色。案例候选需该题结论闭合、该方法独立触发通过且有自身产物或决定，本方法已停止则不计。定位、拆句和分组产物仍是辅助角色，不因入选候选而获得定案权。典型方法候选只按自身案例候选数降序、同数按ID排序；缺产物的已核验建议不能借别的方法答案升级。此排序不证明提速、迁移或真实教学效果，边界/困难案例仍须另行人工审阅选取。逐题难度仍是输入标签，展示分仍是启发式指标；不由建议数量认证完整真题卷或案例来源合法性。

Question Analysis与content-export当前版本1.7.0，grammar_navigation：非语法为null；语法包含hint_branch、status、paths、next_node、review_basis和limitations。导航只接受显式有无提示词及外部审阅触发；缺标注先确认入口，未核空位功能不进入叶节点。知识路由不产生新关系或答案，仍须按同一证据闭合机制验证。Paper内嵌单题同步采用此契约。

writing_review输入经独立审阅适配进入writing_feedback；两类写作各自的功能顺序、纠错与改稿保留，缺材料实际扣留不支持的诊断/完整稿/分数。1.1.0审阅另可提交original_images字节、区域和转写稿指纹；image_evidence绑定分数审阅图路径，四Renderer重检图与载荷，输出不重复图片字节。图片名或转写文本仍不能授权书写扣分；看不清不扣分，应用文降档/续写酌扣独立。图和图片解码均不认证原稿身份、清晰度、交际影响、语义或评分，详见writing-review.md。

Composer计划另有类型化执行通道：action_executions → execution_trace → action_artifact图节点。明确区分计划、关系审阅与实际提交产物；只有更早的已审阅、完整、未刹车产物可被后续消费。R09骨架、F01分组、语法路线和独立候选判断各有限权；核验失败撤回答案。Renderer重检执行链与图指纹绑定，content-export保留完整产物。详见method-execution.md；该通道不认证外部语义或审阅身份。

整题终判单列为 `question_verification_review`，不创建新方法名，也不更改支持方法的职责。输入须绑定题号、审过的任务、原题材料指纹及当前来源提交，消费实际 produced 的解释、骨架或逐候选关系核查；定位、分组或剩余项不能独立定案。每个原选项完整文本必须恰好核一次，分别提交本题原文跨度、整项关系检查、回填说明和 `backfill_verdict`，并写具体停止条件。这里的 supports 是回填支持该项保留/排除判断，不是一律说候选正确；rejects/unresolved 均使该项待定。上游停止或旧式决定后验证失败不能被终判绕过。

verifier 可产出 `verification_result` 的显式 `scope: candidate_relation_check` 分支，不需要先假造一个 decider。必须提供 candidate、原选项完整 claim、空的 target_execution_ids、自己的准确 evidence、具体 relation_check、backfill_check 及 verdict。这些字段描述候选呼应或逻辑关系核查，不直接生成 retain/eliminate 或答案。局部 supports 不保证完整选项正确；rejects 仅否定本项所核关系，不是全题失败；unresolved 使该项终判待定，不能靠别项已排而选。缺显式 scope 的旧验证仍要求真实同候选先前决定，旧冻结输入与角色产物列表不变。

没有解释/骨架支持时，终判必须消费每个原候选自己的关系核查。已有 produced 核查全部必须消费，不能省掉不利或未决记录后借另一个解释绕过。候选图只接自己的核查及共同支持产物，输出端核候选、scope、完整主张、自己的证据覆盖、载荷哈希和精确依赖边集合。保留与自己的 rejects 冲突即拒绝；自己的 unresolved 暂留。程序核字段和依赖，无法仅凭存在两个引文就证明实际两侧关系或段落任务正确，仍须独立英语审阅。

新图路径为完整题干/候选主张/本项正文/实际解释产物 → question_review → question_decision → question_verification；各项自行绑定 review_id、candidate 和 effect，不借另一项关系作证。整题输出单列 question_verification，不塞入带 method_id 的 candidate_analysis；Paper 的方法判项覆盖因此不增加辅助方法信用。只有唯一正向保留、所有竞争项完成、终判已审且未停止，才闭合答案。未提供此接口的输入继续产生原 1.7.0 输出；显式提供时为 1.8.0。四 Renderer 及内嵌整卷、篇级、冻结素材、视频契约同步接纳并复核新证明，公开发布状态仍不自动变成通过。

question_scope 独立绑定完整候选集合、原题指纹和整个审阅载荷；所有候选关系须直接接入同一范围节点。输出端不能删除竞争项或终判记录、改写来源/回填说明后沿用旧图，也重检未被终判消费的上游停止和失败核验。它提供数据一致性约束，不是数字签名；同步伪造所有输入、图和审阅记录不构成认证。

输入审阅是外部语义声明，程序只核数据、跨度、依赖、职责、图和聚合。绑定哈希不认证审阅者身份、原卷完整性、英语语义或学生效果；不能把这条接口包装成自动英语求解器。原单题口播契约仍要求自身逐段比较绑定，不因整题闭合自动变成完整口播。

序列化产物内的引文必须是本动作已绑定原文引文在相应坐标上的精确子串。只校坐标包含或重新计算产物哈希不足：不能在不改动作原文的情况下输出伪造引文。该检查覆盖解释、骨架、定位、文本分组和候选关系核查等实际带引文的产物；合法子跨度仍允许。它检查现有载荷内部一致性，不认证所有载荷一起被重写后的真实性。

学生fallback只展示一个待核入口，首次动作、判断和刹车直接读取Registry四步实战卡，不将低置信建议当成已核验触发。保留全部已提交产物与候选证据；任一真实停止记录或未通过核验产物存在时，不再邀请执行后续计划，也不催学生继续套方法。混合produced/stopped的聚合步骤仍按实际停止记录刹车；独立后续产物不被隐藏。完整机器链、已闭合口播和写作交付分支保持不变。四Renderer另检查计划的Registry版本、题型、职责、产物、Stop及主要动作绑定，空执行链也不能注入未经Registry支持的教学字段；副职责具体动作仍由原有执行图门禁约束。这些是投影及结构安全检查，不证明真实学生First-use成功。

评分的分档区间及词数附加规则直接解析源评分章节；writing_review 1.2.0独立记录词数调整前后区间和完整学生稿证据。所有分数建议在图中绑定自身载荷指纹、原稿、触发、审阅关系与验证，不仅是原图评分。Renderer重检并区分档内建议与扣分后建议；计词、定档和酌扣裁量仍由宿主独立核验。

单题口播另经lesson_review → lesson_feedback输送，绑定实际动作/短引文/候选比较/刹车与独立触发，缺完整覆盖或答案未闭合时实际扣留。完整交付从同学、我们来分析一下进入正文，最后由核心答案汇总，不展示内部字段；宿主自由文字忠实性和整篇课程顺序仍未认证，详见lesson-review.md。

lesson-review 1.1.0 可把整题比较绑定到独立终判的本项验证节点，不在这一段附上 method_id。支持方法先点名并展示真实动作，整题比较随后接入；主旨骨架、词义解释等因此不冒领决定职责。候选引用、覆盖、证据、版本、Stop 和相同交付来源检查在输入/四输出端重检，七选五篇级也接纳无方法名的终判段而不重复分组。完整消息的自然表达仍须独立语义审阅，不能用结构通过代替学生学会。

显式当前整题审阅的平面作者门禁同时检查动作、关系及提示状态/终判/口播/写作注释作者。不能只报另一动作作者，掩盖整题审阅者自己写的终判或口播。混合作者材料在逐阶段独立证据未获整题准入前，不能包装为一个作者的全面独立审阅。

PassageLessonAnalyzer复用单题核心与口播检查，另核冻结课程顺序、原题号、共享原文和实际暂留/回收步骤。篇级Renderer先分组三维，再说突破空，整篇只称呼及汇总一次；原题面和步骤保留供投影重检。顺序理由、完整性与自由文字仍是外部声明，不认证真实语义或宿主效果，见passage-lesson.md。

语法提示状态的原题数字空位通过显式注释适配，不自动规范化原题。`grammar_hint_review.numeric_marker_binding` 必须绑定当前 `question_id`、与数字题干完全相同的 `question_number`（1–999）、原 `passage` 中唯一数字token的精确 `target_span`、外部确认 `printed_blank_confirmed:true` 及具体 `source_review_note`。原审阅仍须实名标记、reviewed及实际引文；引文覆盖本空和完整后续token，括号提示或裁切拒绝。普通数字、年份、另题的空位及缺少该注释的输入不会被启用为无提示路线。不能给原材料偷偷补 `given_word:null`、下划线或改题号。

该接口只确认调用分支，不判词性、从句、答案或G01已执行。叶节点仍需单独触发审阅和动作，来源的印刷空位性质与审阅身份仍需外部语义/来源核验，字符和注释一致性不认证这些事实。旧下划线标空接口不改，旧未知记录可在原输入下继续重放。
