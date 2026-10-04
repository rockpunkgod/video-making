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

Reviewed结论要求独立触发、当前题面跨度、具体判据、Stop检查、回填验证、审阅者与明确决定职责。不完整/未审阅/冲突关系不定案；排除与剩余不证明答案。辅助角色不独立decide；C01只有显式二阶段decider可闭合当前空。

图检查节点唯一、边闭合、无环和原文→审阅关系→结论路径。它不认证审阅者身份或语义为真。未闭合题不进整卷内容推荐；展示分为启发式排序，不代表传播或提分效果。

接口：QuestionAnalyzer.analyze(dict)、PaperAnalyzer.analyze(dict)、CLI；契约为Draft 2020-12 JSON Schema。当前部署为完整仓库+Python3.10+，源码或editable安装。单独Skill文件夹仅自包含宿主答疑，不自动安装核心。未建抓取/视频/AE/支付/发布服务。
