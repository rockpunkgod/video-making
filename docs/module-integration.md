# 其他模块开发交接入口

本文件夹是 `video-making` 中 ANSWER Method Engine 的完整源码交付快照，不是原 ANSWER 仓库，也不是已完成真实教学验证的自动解题服务。先看本文件，再看 `docs/final-acceptance.md`。总体状态为 **PARTIAL**；82项方法均为 Useful + candidate，没有已认证的 Efficient / Signature。

## 1. 保留整个文件夹

运行时会从源码根目录读取 `method-registry`、`schemas`、`cases` 和课程来源章节。不要只复制 `core`，也不要把单独 Skill 当成已经部署的引擎。支持 Python 3.10+、源码目录运行及 editable 安装；不承诺独立 wheel 包含课程数据。

在此文件夹打开终端：

```powershell
python -m pip install -r requirements-dev.txt
python -m answer_engine validate
python -m answer_engine analyze examples/question-course.json --renderer student
python -m answer_engine analyze examples/question-action-course.json --renderer structured
python -m answer_engine paper examples/paper-course.json
```

这里的示例是课程片段或明确标记的 synthetic 程序样本，不是完整真题正确率或学生效果证明。依赖安装会连接包索引；交付时的运行验证使用已有本地依赖，不代表另一台机器已经安装依赖。

## 2. 外部模块只调用接口，不另建方法事实源

| 下游需要什么 | 接入入口 | 必须保留的边界 |
|---|---|---|
| 单题分析、学生卡点下一步 | `QuestionAnalyzer.analyze(dict)` | 未闭合时 `answer=null`；方法建议不等于触发已核验 |
| 整卷扫描、方法覆盖、候选内容排序 | `PaperAnalyzer.analyze(dict)` | `method_counts` 是建议次数，不是适用率或正确率 |
| 整篇讲题、原题号与顺序 | `core.passage_lesson.PassageLessonAnalyzer` | 逐题自身闭合、口播齐备后才完整交付 |
| 方法卡、品牌、四步卡、短版、视觉公式 | `Registry.methods[method_id]` | 使用同一版本，不手改生成 Skill 或复制出第二套判据 |
| 学生版、旧微信版、机器版、内容资产 | `renderers.render(analysis, kind, registry)` | Renderer只投影，不能补英语推断或改答案 |
| 真实测试数据与 Baseline 比较 | `python -m answer_engine evaluate ... --plan ...` | 传播→冻结→实用性；synthetic不能支持真人升级 |

CLI 的 `analyze` / `paper` / `lesson` / `method` / `symptom` / `evaluate` / `release-check` / `release-bindings` / `case-coverage` 可供其他语言通过子进程调用；输入和输出都是标准 JSON（学生/微信投影为文本）。当前没有 HTTP 服务、外部模型、抓取、视频、AE、支付或发布服务。

```python
from answer_engine import Registry, QuestionAnalyzer, PaperAnalyzer
from renderers import render

registry = Registry()
analyzer = QuestionAnalyzer(registry)
question = {
    'question_id': 'your-original-id',
    'question_type': '阅读理解',
    'task_type': 'detail',
    'stem': '原题题干',
    'passage': '原题完整原文',
    'options': {'A': '原选项A', 'B': '原选项B'},
    'student_symptoms': ['两个选项都像原文'],
}
analysis = analyzer.analyze(question)
student_text = render(analysis, 'student', registry)
machine_json = render(analysis, 'structured', registry)
paper = PaperAnalyzer(analyzer).analyze({'paper_id': 'your-paper-id',
                                       'questions': [question]})
```

这段仅演示调用形状，不是英语题或答案案例。有效题面、候选覆盖及语义审阅须由调用方提供。

## 3. 契约和审阅通道

- 单题输入：`schemas/question-input.json`；单题结果：`schemas/question-analysis.json`，当前版本 **1.7.0**。
- 整卷结果：`schemas/paper-analysis.json`，当前版本 **1.1.0**；还接受旧1.0.0投影。
- 方法卡与证据图：`schemas/method-card.json`、`schemas/evidence-graph.json`。
- 实际动作：`schemas/method-execution.json`、`schemas/action-artifact.json`；完整说明见 `docs/method-execution.md`。
- 写作、单题口播、整篇交付：`docs/writing-review.md`、`docs/lesson-review.md`、`docs/passage-lesson.md`。
- 真实验收和人工释放：`EVALUATION_PROTOCOL.md`、`docs/evaluation.md`。

`observations` / `relations` / `action_executions` 是宿主或人工提交的外部审阅记录，不是引擎自己证明的英语事实。Python `review_provider` 可补这些记录，但不能修改原题号、题型、题面、选项、提示词、学生原稿或原图；不是安全沙箱。跨度、指纹和图一致也不能认证审阅者身份、语义正确或评分正确。

`locate` 找证据位置，`interpret` 形成语义/框架，`reduce` 缩候选，`decide` 判断当前候选，`verify` 回填核验。不要把定位、骨架或分组包装成答案。完整机器输出保留方法全链；学生fallback只给一个待核入口及四步卡，已有真实停止或失败核验时不继续邀请执行后续计划。没有显式解除缺口的契约，后来的独立产物不会自动解除此前刹车。

## 4. 内容模块的使用限制

`content-export` 提供视觉公式、10/30/90秒稿、Anti-Rule、动作、Stop及证据全链，不提供AE工程。`eligible_for_review` 只表示可送审，不是可以发布；`safe_for_release='untested'` 不能转换成 true。Case中 `evidence_gap`、缺槽、短片段和未审候选不能包装成完整成功真题案例。任何实际发布另需核版权、语义、短版安全和真人验证。

## 5. 文件夹包括与不包括

包括：核心、Renderer、全部Registry及历史版本、公开案例/缺口、契约、评估框架、兼容Skill/Agent、测试、示例、文档、现有公开源快照与验收元数据。

不包括：`.git`、虚拟环境、缓存、凭证、`local-data` 私有原题/答案/审阅全文、新提供的 `E:\开明致学` 原始讲义，以及用户暂缓的 `E:\新建文件夹`。公开验收元数据可能引用私有源指纹；缺私有材料时不能声称已重跑真实试卷链。

文件夹不带Git历史，个别源码审计测试使用Git索引，须在 `video-making` 源仓库运行；不要在交付文件夹运行全量验收后据此覆盖随附报告。普通接口、Registry校验和示例无需Git历史。复制文件夹后若独立开发，建议初始化自己的仓库并保持来源与版本记录。

## 6. 开发前先看当前限制

`docs/final-acceptance.md` 和 `evaluation/reports/engineering-acceptance.json` 是交付快照的工程验收证据，不是英语/真人效果证明。仍缺全量完整真实案例、独立语义审阅及旧宿主语义回归、可靠自由文本语义后端、真实受试者传播/首用/迁移/Baseline数据。外部模块可以接这些可运行接口，但不能宣传尚未证明的提速或提分。

修改Registry后运行 `python -m scripts.generate_assets`，不要手改生成投影。其他模块建设不应改变 ANSWER 原仓库；本轮成果来源为 `rockpunkgod/video-making`。
