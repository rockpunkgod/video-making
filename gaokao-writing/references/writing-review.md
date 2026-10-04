<!-- Generated interface guide; course facts stay in Registry. -->

# 写作审阅通道

这是宿主批改进入统一核心的结构接口，不是本地自动评分模型。课程事实仍来自Registry冻结章节；15分应用文和25分续写独立。Schema：schemas/writing-review.json；作为单题输入的writing_review字段传入，四种Renderer复用同一writing_feedback结果。

## 提交什么

宿主先按原写作契约完成真实题面和原稿的语义审阅，再提供：

- kind：guidance或correction；review_status、reviewer记录外部审阅状态与来源，不认证身份。
- source_section_ids：当前题型的冻结课程章节；评分另用正确评分章节的source_section_id。
- student_text_complete：原稿是否完整；续写还须明确student_text_excludes_given_starters。题面给定开头不属于学生自写部分，不因学生不抄而扣分。
- sections：key、纯文本text、当前题面/原稿evidence跨度。应用文为overall、diagnostics、outline、revised_text、practice和有帮助时的materials；续写另有anchors和emotion，不套用应用文诊断。
- corrections：逐处original跨度、replacement、reason、kind。error为确定错误，optional为可选润色；没有数量上限，不能虚构原句或重复重叠的改法。
- reviewed_student_spans：实际完成语言审阅的原稿范围。整段标注只是一项外部声明，不能证明错误已找全；程序只检查范围覆盖，不替代语义审阅。
- proposed_score：可为null。非空须有正确15/25 scale、有界lower/upper、源评分表中的band、rationale、student_text证据及正确源评分章节。仅外部建议，不是程序认证分数；档次与附加规则仍由宿主依源课程判断。

完整版批改同时需要普通observations中独立审阅的A09（应用文）或W15（续写）触发，不从评分建议倒贴触发。引用必须逐字绑定当前题面。应用文需题目与原稿证据，续写需原文、两首句与原稿证据。

## 实际输出门禁

full_correction仅表示材料、交付功能、引用及声称的语言审阅范围齐备，不表示英语判断或评分经过独立真人验证。answer仍为null，Paper不得把分数建议当闭合答案或内容推荐资格。

缺题目、原文或首句：扣留完整分数、剧情/任务诊断和整篇修改稿，只交付逐处现有语言修改。缺原稿覆盖、功能块或独立触发：partial_feedback，扣留分数与整篇修改稿。unreviewed：数据可保留作审计，但学生Renderer不交付其诊断、改稿或分数。guidance不能虚构学生纠错和分数。

当前通道只处理文本证据。handwriting_applied=true被拒绝；一个文件名、转写稿或键入文本不能证明原手写已经影响交际。清晰原稿的书写评价仍可由宿主按原契约完成，但需另建原图独立审阅证据适配，不能冒充已通过核心检查。

## 调用与兼容

在完整仓库运行：

```powershell
python -m answer_engine analyze INPUT.json --renderer legacy-wechat
```

Python review_provider仍可提交审阅后的输入，但必须通过相同Schema、原句跨度、题型与材料门禁。不能把正确答案、预设分数或程序测试数据当作独立学生证据。

legacy-wechat按原两模块交付顺序输出自然段；逐处原句、改法、理由和可选润色均保留，不生成标题、编号或评分表。宿主提交text时也须遵循原纯文本消息契约。生成适配Skill引用本指南，原课程契约逐字保留。单独安装Skill时仍可依原契约答疑，核心命令需完整仓库。

tests/test_writing_feedback.py使用显式synthetic程序字段检查输送、顺序、拒绝和扣留分支；它不是英语试题、学生实测、评分一致性或旧宿主语义回归。真实完整旧题库与独立宿主评价仍待提供。
