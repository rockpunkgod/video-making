<!-- Generated interface guide; course facts stay in Registry. -->

# 单题口播兼容通道

Question Analysis及content-export从1.5.0增加lesson_feedback；输入可交lesson_review。它保存宿主已经完成的单题现场讲解，不用核心通用字段模板冒充原口播。范围为阅读理解、七选五、完形填空、语法填空；写作仍走独立writing_review。

## 宿主提供什么

遵守schemas/lesson-review.json，提交question_type、reviewer、review_status、source_section_ids和segments。每段有segment_id、function、method_id、text、当前题面evidence及relation_indices。

function为action、evidence、comparison或stop。方法首次实际出现必须嵌在action文本中点名，允许品牌名或已登记课程别名，不先列方法目录。证据可以独立成段，也可以自然嵌在comparison中，不要求机械五段或小标题；每次引证必须显示当前题面真实短引文。comparison引用该候选自己的已审阅relations，不能用另一项、未审阅判断或无关方法关系替代。中文自然纯文本；英文原文自身标点保持原样。

source_section_ids必须含冻结学生交付合同章节，并含实际使用的方法自身课程章节；写作或另一题型章节不能替代。引用来源只在结构数据里保存，不在学生消息中展示台账。这个接口不改变Registry判据，也不把新讲稿当课程事实源。

## 什么条件才交付完整单题讲解

必须有该方法独立触发、实际动作、可复核题面引文、候选核验、刹车说明，并由核心闭合最终答案。每个实际使用方法都须有对应动作、证据和刹车；所有已保留/排除候选均有自身比较依据。没有独立的evidence段时，comparison内的短引文仍可完成证据功能。

只在reviewed且满足上述条件时scope=single_question_lesson。其余为partial_delivery或unreviewed，完整segments实际扣留为空，不给学生展示未经支持的完整口播。原核心仍能返回下一步计划，或已独立审阅的局部候选事实；不会用自信讲稿填补未闭合答案。

七选五单题也须先展示三一致，不能因只问一空省掉初筛。宿主先提交三个F01的produced candidate_partition，axis分别为sentence、actor、time，全部实际选项各分一次；某维没有区别时用单组如实标注，不编造组。口播首次F01动作之后由Renderer展示三维字母分组一次，再继续正文。缺某维、同维多份或无独立审阅分组时扣留完整口播。宿主F01 action只点明动作，不另重复自动分组表。

Graph绑定每段真实文本、独立方法触发、精确跨度和所引用候选关系。Analyzer及Renderer重检段落/图/答案闭合一致性，防止改文字、丢证据绑定或改scope之后仍输出完整稿。结构和引文一致不是英语语义、文字忠实性、审阅者身份或旧宿主答疑表现的认证。

## 学生输出

student与legacy-wechat在完整口播存在时输出一条自然消息。开头只称呼一次同学并说我们来分析一下，随后按宿主动作顺序展示段落，最后从核心闭合结果汇总这一题答案一次。开场不先报题型或方法，正文不展示职责、置信度、路由、审阅、证据编号等内部术语。答案汇总不是从宿主另交答案键读取。

Structured与content-export保留完整lesson_feedback及图绑定供后续复用。无完整口播时仍走原有受限结构投影，不把它宣称为完整现场口播。

## 明确未完成的范围

这是单题兼容通道，学生只问一处时适用。整篇七选五的一次三维字母分组、突破空顺序、阅读中心任务优先、完形按原空号两遍和语法无提示词优先的整篇流程，仍需完整篇级执行/交付适配；不得因单题结构测试通过声称这些顺序已验证。

可运行课程片段示例：python -m answer_engine analyze examples/question-lesson-course.json --renderer legacy-wechat。沿用已冻结语法课程短片段，口播为工程输送样例，不是完整真题或真实学生讲解实验。

宿主自由文字的语义忠实性与旧题库表现仍须独立真实回归。程序样本全部为synthetic输送测试，不作为考试题、真人口播或传播效果证据。
