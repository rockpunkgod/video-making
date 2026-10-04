# ANSWER Method Engine · video-making

ANSWER is an evidence-grounded Gaokao English method and question-analysis system.

以课程证据为根基，把高考英语方法转化为可触发、可执行、可验证、可迁移的考试决策系统。成果另存于本仓库；`rockpunkgod/ANSWER` 源仓库未修改。

支持六题型注册、学生卡点导航、方法组合、原文跨度证据图、单题/整卷结构化分析、学生/微信/机器/内容导出、真实观察数据评估。82项包含子动作、内部规则与训练框架，不是82个核心品牌。六个黄金方法有完整独立首次接触稿；所有项保持 candidate+Useful。

当前是可运行的证据与流程约束核心，不是自由文本自动解题器：无外部语义审阅时不猜答案；审阅记录会检查跨度、角色、路径与冲突，但不把结构检查冒充语义证明。完整作文语义批改/评分仍由兼容Skill宿主执行，可通过writing_review进入统一结构与原顺序输出，分数仅为外部建议。未验证提速、传播效果或Signature。

## 使用

完整仓库内使用 Python 3.10+：

```powershell
python -m pip install -r requirements-dev.txt
python -m answer_engine validate
python -m answer_engine symptom 语法填空 "有提示词但不确定空位需要什么"
python -m answer_engine method R01
python -m answer_engine analyze examples/question-course.json --renderer student
python -m answer_engine analyze examples/question-reviewed-course.json --renderer structured
python -m answer_engine analyze examples/question-action-course.json --renderer student
python -m answer_engine analyze examples/question-lesson-course.json --renderer legacy-wechat
python -m answer_engine paper examples/paper-course.json
python -m answer_engine evaluate evaluation/datasets/real-observations.pending.json
python -m unittest discover -s tests -v
```

示例来自已有课程片段，reviewed示例是工程取证记录，不是真人测试或自动推理成果。Paper示例为两条同源记录，不冒充完整试卷；接口接受完整questions数组。JSON/JSONL评估使用 `--plan` 指定采集前冻结计划。

Python API：`from answer_engine import QuestionAnalyzer, PaperAnalyzer`；`analyze(dict)` 返回受JSON Schema约束的结果。review_provider可接宿主语义分析器；没有内置外部模型、抓取或发布服务。

写作审阅输入、原稿引用及完整/局部交付边界见[写作审阅通道](docs/writing-review.md)。缺原文或首句时实际扣留剧情诊断、整篇修改稿及完整分数，不只添加免责声明。

方法组合可通过action_executions提交具体动作与类型化产物，execution_trace明确记录本步消费哪一步的定位、拆句、分组或骨架；停止/未审阅结果不能继续传递。计划不冒充已执行，核验失败撤回答案。见[可执行方法编排](docs/method-execution.md)；外部语义审阅仍不等于程序自动证明。

宿主完整单题讲解可通过[lesson_review](docs/lesson-review.md)进入原口播形态，绑定动作、短引文、候选比较和刹车，完整消息只在答案闭合后输出。缺口会实际扣留；单题通道不证明整篇做题顺序或旧题库语义表现。

## 目录与兼容

- method-registry：方法与源章节唯一事实源，history保留旧版。
- schemas/cases：标准契约、案例及显式证据缺口。
- core/renderers：流程约束与四种独立投影。
- evaluation：真人记录契约、统计工具及明确synthetic的程序样本。
- gaokao-english/objective/grammar-fill/writing、agents：原调用名称的生成兼容资源，不修改用户技能库。
- docs：基线、架构、维护、评估、迁移和最终验收。

改Registry后运行 `python -m scripts.generate_assets` 再测试校验，不手改生成资源。单独安装Skill仍可由宿主读取自包含参考；核心需完整仓库与依赖。支持源码目录/editable部署，不承诺独立wheel携带课程数据。

验收顺序：传播效果→冻结→强可用性；第二阶段优先级更高。真实数据缺失为 pending_real_participant_validation。最终缺口见 [docs/final-acceptance.md](docs/final-acceptance.md)。课程基线为 ANSWER@b04ebc26d7fa096404111a0bb12f6c77cc8525b9。
