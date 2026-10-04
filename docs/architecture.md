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

Reviewed结论要求独立触发、当前题面跨度、具体判据、Stop检查、回填验证、审阅者与明确决定职责。不完整/未审阅/冲突关系不定案；排除与剩余不证明答案。提供options时，必须有唯一候选自身的保留证据，且其他候选全部具有审阅后的排除证据；单个保留项不能跳过未核验竞争项。无选项的语法生成仍需唯一词形的独立审阅关系。answer_verification列出保留、排除、未决候选及闭合状态，不是语义真实性认证。辅助角色不独立decide；C01只有显式二阶段decider可闭合当前空。

图检查节点唯一、边闭合、无环、引文标签与跨度相同，以及同一方法的独立触发、同一候选的主张→审阅关系→结论路径。validate_graph(graph, question)可将每个引文重新绑定当前题面；Analyzer自动执行此检查。仅传graph不能认证源文本真实性，两个模式都不认证审阅者身份或语义为真。未闭合题不进整卷内容推荐；展示分为启发式排序，不代表传播或提分效果。

method-registry/symptom-cues.yaml保存口语导航别名，不复制方法判据；公开症状表从它和方法卡生成。具体卡点优先于通用题型入口，口语匹配仍为low/trigger_verified=false，不能直接授权关系定案。题型和任务范围由调用方审阅；段落主旨不得调用全文覆盖排除法。未覆盖口语退回结构入口，不假称语义分类已经校准。

接口：QuestionAnalyzer.analyze(dict)、PaperAnalyzer.analyze(dict)、CLI；契约为Draft 2020-12 JSON Schema。当前部署为完整仓库+Python3.10+，源码或editable安装。单独Skill文件夹仅自包含宿主答疑，不自动安装核心。未建抓取/视频/AE/支付/发布服务。

Question Analysis与content-export当前版本1.4.0，grammar_navigation：非语法为null；语法包含hint_branch、status、paths、next_node、review_basis和limitations。导航只接受显式有无提示词及外部审阅触发；缺标注先确认入口，未核空位功能不进入叶节点。知识路由不产生新关系或答案，仍须按同一证据闭合机制验证。Paper内嵌单题同步采用此契约。

writing_review输入经单独文本审阅适配进入writing_feedback；两类写作各自的功能顺序、纠错与改稿保留，缺材料实际扣留不支持的诊断/完整稿/分数。审阅结果在EvidenceGraph绑定当前原稿及独立触发；图仍不认证语义、评分或身份。手写原图评价尚无核心证据适配，不能靠图片名或转写文本授权书写扣分。详见writing-review.md。

Composer计划另有类型化执行通道：action_executions → execution_trace → action_artifact图节点。明确区分计划、关系审阅与实际提交产物；只有更早的已审阅、完整、未刹车产物可被后续消费。R09骨架、F01分组、语法路线和独立候选判断各有限权；核验失败撤回答案。Renderer重检执行链与图指纹绑定，content-export保留完整产物。详见method-execution.md；该通道不认证外部语义或审阅身份。
