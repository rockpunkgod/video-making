# 单题口播兼容通道

Question Analysis及content-export从1.5.0增加lesson_feedback；输入可交lesson_review。它保存宿主已经完成的单题现场讲解，不用核心通用字段模板冒充原口播。范围为阅读理解、七选五、完形填空、语法填空；写作仍走独立writing_review。

## 宿主提供什么

遵守schemas/lesson-review.json，提交question_type、reviewer、review_status、source_section_ids和segments。每段有segment_id、function、method_id、text、当前题面evidence及relation_indices。

function为action、evidence、comparison或stop。方法首次实际出现必须嵌在action文本中点名，允许品牌名或已登记课程别名，不先列方法目录。证据可以独立成段，也可以自然嵌在comparison中，不要求机械五段或小标题；每次引证必须显示当前题面真实短引文。comparison引用该候选自己的已审阅relations，不能用另一项、未审阅判断或无关方法关系替代。中文自然纯文本；英文原文自身标点保持原样。

source_section_ids必须含冻结学生交付合同章节，并含实际使用的方法自身课程章节；写作或另一题型章节不能替代。引用来源只在结构数据里保存，不在学生消息中展示台账。这个接口不改变Registry判据，也不把新讲稿当课程事实源。

1.1.0 另允许不挂方法名的整题比较段：`segment_scope=whole_question`、`function=comparison`，提交 `terminal_review_id`、`candidate_ids`、text、evidence 和 segment_id，不提交 method_id 或 relation_indices。它引用 `question_verification` 中已闭合的本项验证节点，而非让解释方法领判项信用。段落必须在实际支持方法动作之后，显示当前正文短引，并覆盖所引用候选自己的决定性证据。未知项、未审终判、Stop、未完成回填或错审阅 ID 均拒绝。1.0.0 保持原方法段语义，不能装入新整题段。

输入与输出共用交付来源检查：必须含 delivery-contract 路径锚及所用方法来源，未知、重复、跨题型来源均拒绝，不能删合同后继续输出完整稿。路径锚不冒充完整交付细则文本；自然讲解的语义、文风与实际短引仍须独立读题复核。

## 什么条件才交付完整单题讲解

必须有该方法独立触发、实际动作、可复核题面引文、候选核验、刹车说明，并由核心闭合最终答案。每个实际使用方法都须有对应动作、证据和刹车；所有已保留/排除候选均有自身比较依据。没有独立的evidence段时，comparison内的短引文仍可完成证据功能。

只在reviewed且满足上述条件时scope=single_question_lesson。其余为partial_delivery或unreviewed，完整segments实际扣留为空，不给学生展示未经支持的完整口播。原核心仍能返回下一步计划，或已独立审阅的局部候选事实；不会用自信讲稿填补未闭合答案。

七选五单题也须先展示三一致，不能因只问一空省掉初筛。宿主先提交三个F01的produced candidate_partition，axis分别为sentence、actor、time，全部实际选项各分一次；某维没有区别时用单组如实标注，不编造组。口播首次F01动作之后由Renderer展示三维字母分组一次，再继续正文。缺某维、同维多份或无独立审阅分组时扣留完整口播。宿主F01 action只点明动作，不另重复自动分组表。

Graph绑定每段真实文本、独立方法触发、精确跨度和所引用候选关系。Analyzer及Renderer重检段落/图/答案闭合一致性，防止改文字、丢证据绑定或改scope之后仍输出完整稿。结构和引文一致不是英语语义、文字忠实性、审阅者身份或旧宿主答疑表现的认证。

整题段不增加方法判项次数。四 Renderer 和篇级输出保留这些无 method_id 的段落，七选五仍只在开头展示一次合法三维分组。漏候选或漏停止说明时，核心可保留已经独立成立的整题答案，但完整口播实际扣留；两种验收信用分开。

## 决定性图像的显式运输版本

原题可选 `required_image_evidence` 非空数组，每项为 `{candidate,image_id,sha256,box}`，box 是原图像素的 `[x1,y1,x2,y2]`。它属于原始材料而非可删审阅注释，进入 material fingerprint、graph root 和 review_provider 原材料不变检查。必须由独立来源审阅先确定候选及完整必要区域；没有该声明时，程序不声称自己知道语义上是否必须看图。旧输入不生成这个字段。

整题审阅 1.1.0 允许 candidate_checks 各项携非空 `image_evidence: [{image_id,sha256,box,observed}]`；至少一项有图证。每个来源义务必须由同候选的精确区域满足，不能用大框包含、空白角、另一候选或别的图替换。原 PNG/JPEG 严格解码，校验原字节 hash、实际 MIME、单帧、有界像素及区域；仍须保留完整候选、正文和题干证据及实际已产生的语义产物，不给定位、分组或缩范围动作定案权限。旧 1.0.0 不接受新图证字段。新分析和 content-export 版本为 1.9.0，旧无图证路径的输出不加空字段。

讲解 1.2.0 的 whole_question 比较段可携 `image_evidence: [{candidate,region_index}]`，引用同一 terminal 中该候选图证的零起始位置，不另抄一份无归属观察。段内必须逐字包含被引用的 observed，并引用该段所有 candidate_ids 的全部图证；方法段没有这个字段，不扩大任何方法职责。数字或观察句的语义正确性仍须独立读图审阅，逐字出现不是语义认证。

图节点分别绑定候选、terminal review、完整审阅/manifest/来源义务 fingerprint 及原区域，直接 supports 自己的候选审阅节点；完整口播另由绑定列表和直接边承接同一候选的验证节点与所有图节点。删 region、改 observed、挪候选、重算仅 graph 的 hash、漏口播区域或降级接口均不能交付完整稿。未审/不完整讲解仍实际扣留，学生输出不拼接自由终判文字，也不孤立报答案。

便携冻结消费者使用无 core/Registry/solver 依赖的共享检查，重新解码 source_snapshot 原图，重核来源义务、terminal、完整 lesson 原输入和双向图绑定；export/status 及生命周期同时保留图证。单独 renderer 没有原 question，只能检查绑定 manifest 和图的内部一致性，不能重新认证原图字节。`content_os` 的视频 full_solution 门禁不在本次扩展，terminal-only 图证不自动取得视频全解、真实题语义、学生实效或发布资格。

## 学生输出

student与legacy-wechat在完整口播存在时输出一条自然消息。开头只称呼一次同学并说我们来分析一下，随后按宿主动作顺序展示段落，最后从核心闭合结果汇总这一题答案一次。开场不先报题型或方法，正文不展示职责、置信度、路由、审阅、证据编号等内部术语。答案汇总不是从宿主另交答案键读取。

Structured与content-export保留完整lesson_feedback及图绑定供后续复用。无完整口播时仍走原有受限结构投影，不把它宣称为完整现场口播。

## 明确未完成的范围

这是单题兼容通道，学生只问一处时适用。整篇分组、突破空顺序、阅读中心任务优先、完形按当前证据推进及实际暂留返回、语法无提示词优先，由独立passage-lesson.md接口检查并交付；不由单题通道证明。当前完形不强制固定空号、两遍作答或先易后难。历史版本的两遍记录仅在显式历史Registry中复核，不能作为当前调用要求。篇级工程顺序测试也不等于真实整卷或旧宿主语义验证。

可运行课程片段示例：python -m answer_engine analyze examples/question-lesson-course.json --renderer legacy-wechat。沿用已冻结语法课程短片段，口播为工程输送样例，不是完整真题或真实学生讲解实验。

宿主自由文字的语义忠实性与旧题库表现仍须独立真实回归。程序样本全部为synthetic输送测试，不作为考试题、真人口播或传播效果证据。
