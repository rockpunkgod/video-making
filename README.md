# ANSWER Method Engine · video-making

Video Production OS v0.1 的冻结消费接口、分级门禁与本地运行说明见 [Video OS](docs/video-os.md)，基线见 [video-os-baseline](docs/video-os-baseline.md)。工程试制通过不代表独立教学认证或公开视频放行。

V8 AE 增量模块见 [AE Production Layer](ae/README.md) 与 [真实预览验收](AE_MVP_ACCEPTANCE.md)：仅消费冻结 Video Package，使用官方 JUNKDOGE MCP 操作 AE，真实素材和三个内部预览保留在忽略的本地目录。

Swiss Academic Motion v0.2 的中文入口、品牌色、方法动作节奏和平台投影见 [视觉收敛报告](AE_VISUAL_DIRECTION_REVIEW.md) 与 [视觉版本迁移](ae/design/V0.2_MIGRATION.md)。v0.1 保留；视觉工程检查不替代人工审美或公开发布审核。

ANSWER is an evidence-grounded Gaokao English method and question-analysis system.

以课程证据为根基，把高考英语方法转化为可触发、可执行、可验证、可迁移的考试决策系统。成果另存于本仓库；`rockpunkgod/ANSWER` 源仓库未修改。

支持六题型注册、学生卡点导航、方法组合、原文跨度证据图、单题/整卷结构化分析、学生/微信/机器/内容导出、真实观察数据评估。82项包含子动作、内部规则与训练框架，不是82个核心品牌。六个黄金方法有完整独立首次接触稿；所有项保持 candidate+Useful。

当前是可运行的证据与流程约束核心，不是自由文本自动解题器：无外部语义审阅时不猜答案；审阅记录会检查跨度、角色、路径与冲突，但不把结构检查冒充语义证明。完整作文语义批改/评分仍由兼容Skill宿主执行，可通过writing_review进入统一结构与原顺序输出，分数仅为外部建议。未验证提速、传播效果或Signature。

## 使用

开发其他模块或使用独立交付文件夹，先读[模块开发交接入口](docs/module-integration.md)：接口、版本、示例、数据排除范围和尚未验证能力。

完整仓库内使用 Python 3.10+：

```powershell
python -m pip install -r requirements-dev.txt
python -m answer_engine validate
python -m answer_engine case-coverage
python -m answer_engine symptom 语法填空 "有提示词但不确定空位需要什么"
python -m answer_engine method R01
python -m answer_engine analyze examples/question-course.json --renderer student
python -m answer_engine analyze examples/question-reviewed-course.json --renderer structured
python -m answer_engine analyze examples/question-action-course.json --renderer student
python -m answer_engine analyze examples/question-lesson-course.json --renderer legacy-wechat
python -m answer_engine paper examples/paper-course.json
python -m answer_engine lesson examples/passage-lesson.synthetic.json --renderer legacy-wechat
python -m answer_engine evaluate evaluation/datasets/real-observations.pending.json
python -m answer_engine release-check evaluation/release-review.example.json
python -m answer_engine release-bindings evaluation/release-review.example.json
python -m unittest discover -s tests -v
```

示例来自已有课程片段，reviewed示例是工程取证记录，不是真人测试或自动推理成果。Paper示例为两条同源记录，不冒充完整试卷；接口接受完整questions数组。JSON/JSONL评估使用 `--plan` 指定采集前冻结计划。

Python API：`from answer_engine import QuestionAnalyzer, PaperAnalyzer`；`analyze(dict)` 返回受JSON Schema约束的结果。review_provider可接宿主语义分析器；没有内置外部模型、抓取或发布服务。

外部审阅只能补标注，不能改变原题号、题型、题面、选项、提示词或学生材料；新增/删除这些字段也会拒绝。题面订正须由调用方重新提交，整卷推荐不会跟随审阅接口悄悄换题。

写作审阅输入、原稿引用及完整/局部交付边界见[写作审阅通道](docs/writing-review.md)。缺原文或首句时实际扣留剧情诊断、整篇修改稿及完整分数，不只添加免责声明。

方法组合可通过action_executions提交具体动作与类型化产物，execution_trace明确记录本步消费哪一步的定位、拆句、分组或骨架；停止/未审阅结果不能继续传递。计划不冒充已执行，核验失败撤回答案。见[可执行方法编排](docs/method-execution.md)；外部语义审阅仍不等于程序自动证明。

宿主完整单题讲解可通过[lesson_review](docs/lesson-review.md)进入原口播形态，绑定动作、短引文、候选比较和刹车，完整消息只在答案闭合后输出。缺口会实际扣留；单题通道不证明整篇做题顺序或旧题库语义表现。

整篇讲题另用[lesson接口](docs/passage-lesson.md)：保留原题号，检查阅读任务优先、完形首轮暂留/次轮回收、语法双路顺序及七选五一次分组，最后才按原题号汇总。每题必须有自身完整口播和闭合证据；缺一处就扣留整篇消息，不把结构测试宣传成真实答疑效果。

整卷扫描1.1.0将方法建议次数与已核验触发、动作产物、审阅决定和案例候选分开。典型方法候选按自身可审阅案例数排序，不把建议频次当适用率；定位或分组入选也不代表能独立定案。题目来源、难度和教学效果仍需外部核验。

## 目录与兼容

V9.1 增量视频模块：见 [G01 Hero 工作流](docs/cinematic-hero-workflow.md) 与
[Swiss Cognitive Motion](creative/motion-identity/motion-identity.md)。只消费冻结输出；
实际视频、音乐及 Adobe 工程保留在忽略的本地目录。

当前方法应用视觉试制见 [Swiss Cognitive POV 工作流](docs/swiss-cognitive-pov.md)：
纯导出已有动作与语义跨度，在持续原题中执行注意力镜头和可逆拆解；AE 输出动效，
Premiere 完成声音、字幕与最终内部样片。工程成功与教学、来源、编辑及 Human Taste 分开记录。

教学选择与学生视角文案为两个独立增量层：
[Pedagogy Compiler](docs/pedagogy-compiler.md) 提供 `python -m pedagogy compile|validate|handoff|matrix`；
[Student POV Copy](docs/student-pov-copy.md) 提供 `python -m student_pov realize|validate`。
两者只消费冻结资产和当前状态；READY 教学投影不替真实 Payoff、最终文案或学生体验认证。
本轮 G01 worked_example 投影 READY，新 Student POV 候选因既有基线路径与工作减少凭证缺失 HOLD。
自然口语规则、现有表达问题和可修改入口见 [文案 Agent 交接说明](docs/student-pov-natural-copy-handoff.md)。

完整篇目内部试制另见 [阅读 D 篇生产工作流](docs/reading-d-2025-production.md)：
显式 ANSWER 宿主审阅纯导出、已接受本地声音配置、持续题目区、原生 AE 场景与 PR 整片交付。
附加篇级契约不修改旧分析器闭合状态，也不自动取得公开发布资格。

- method-registry：方法与源章节唯一事实源，history保留旧版。
- schemas/cases：标准契约、案例及显式证据缺口。
- core/renderers：流程约束与四种独立投影。
- evaluation：真人记录契约、统计工具及明确synthetic的程序样本。
- gaokao-english/objective/grammar-fill/writing、agents：原调用名称的生成兼容资源，不修改用户技能库。
- docs：基线、架构、维护、评估、迁移和最终验收。

改Registry后运行 `python -m scripts.generate_assets` 再测试校验，不手改生成资源。单独安装Skill仍可由宿主读取自包含参考；核心需完整仓库与依赖。支持源码目录/editable部署，不承诺独立wheel携带课程数据。

验收顺序：传播效果→冻结→强可用性；第二阶段优先级更高。真实数据缺失为 pending_real_participant_validation。最终缺口见 [docs/final-acceptance.md](docs/final-acceptance.md)。课程基线为 ANSWER@b04ebc26d7fa096404111a0bb12f6c77cc8525b9。

成熟度与实用等级由人工批准，工具不自动升级。release-check核对批准凭证、五类案例、真实冻结评估和当前回归绑定；release-bindings只生成材料指纹，指纹不是批准。示例未批准且会被挡住；实际操作见[真实验收运行](docs/evaluation.md)。
## 真实试卷材料

用户提供的2020—2025原卷与第三方解析仅用于本地方法回归，全文不随公开仓库再发行；原卷先Blind、冻结预测后才Reveal。导入流程、当前卷级进度及未审项见 [docs/exam-ingestion.md](docs/exam-ingestion.md) 和 `evaluation/reports/exam-ingestion.json`。原题回归不构成真实学生效果验证。
