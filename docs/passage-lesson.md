# 整篇讲题交付接口

PassageLessonAnalyzer与lesson命令接入原课程整篇顺序，不替代PaperAnalyzer扫描整卷。输入passage-lesson-input，输出passage-lesson-analysis 1.0.0。当前单题内嵌契约仍为Question Analysis 1.5.0。

输入包含lesson_id、question_type、共享原文passage、material_complete、questions和review。questions逐项保留原题号number和原单题question；相同原文可省略各单题passage，由入口填入，已有passage不一致会拒绝。不能混题型或复用题号。材料完整性、题型、题目任务和原题号是宿主审阅声明，不由程序或篇字母猜定。

review提供审阅者、审阅状态、冻结做题顺序章节source_section_ids、reading_mode和steps。每步含question_id、pass、outcome、transition、当前题面evidence及execution_ids。transition必须用本题真实引文说清为何现在做/暂留/回收，不能只写这题简单；程序检查引用和流程，不认证这个理由在英语语义上正确。

## 题型顺序

阅读original_order按原题号；central_task按全文主旨/目的/标题、细节/推断/段落任务、猜词三层，层内保持原题号。必须显式审阅任务类别，不凭A/B/C/D篇号推断模式；未知任务不能套中心任务优先。

语法每空先明确given_word，无提示为null，有提示为非空文字。无提示词先做、有提示词后做，每遍内部按原题号。缺标注不猜提示词状态。

完形首轮逐空号访问全部题，solved或deferred。暂留必须引用该空自己的已审阅stopped动作；不能虚构先不会、后突然会。第二轮只回收首轮暂留空，仍按原空号，不能提前交错、漏空或重复回收。回收时使用该空自己已经闭合的单题证据与口播，不靠另一空占用推答案。无暂留时不编造失败尝试或虚假回收。

七选五允许按已审阅的突破口顺序讲，逐空transition须有当前证据依据。全部空共用同一A–G选项集、相同三维F01分组。Renderer先点明实际分组动作并展示句型/主角/时间三维字母分组一次，再讲先从哪个空突破；后续不重建或重复分组，仍核各空自身决定性关系。

## 交付门槛与输出

完整交付要求material_complete=true、篇级顺序reviewed、每空自身答案闭合且single_question_lesson完整。任何一空缺动作/短引文/候选比较/刹车或闭合，整篇口播和答案串实际扣留。incomplete_question_ids指出具体未完成题；单题结构分析仍保留，便于补证，而不是删除全部可用工作。

student / legacy-wechat只称呼一次同学，按宿主实际transition和单题动作推进，不逐题套开场，不中途汇总答案串；最后按原题号汇总一次。Structured / content-export保留原题面、单题图、执行与口播、篇级步骤和最终汇总。Renderer重新绑定原题面跨度、执行/口播图、顺序和核心答案，不接受改排序、改答案串、换原文后仍伪称完整的输出。

```powershell
python -m answer_engine lesson examples/passage-lesson.synthetic.json --renderer legacy-wechat
python -m answer_engine lesson examples/passage-lesson.synthetic.json --renderer content-export
```

示例是明确标synthetic的程序输送数据，不是英语试卷或真实学生。实现和测试不证明宿主自由文字的忠实性、突破难度判断、真实整卷效果或旧题库语义表现。真实完整课程题/旧答疑记录仍须独立回归。
