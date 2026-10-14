# 写作审阅通道

完整写前讲解可直接使用现有 `writing_review.kind=guidance`，不用伪造学生全文或批改。已审自然段可作为section text（如overall内完整消息），配当前题面/原文/两首句的自身跨度、正确模块source_section_ids；corrections、reviewed_student_spans为空，proposed_score=null。学生与微信输出保留正文，结构化与内容输出同时保留同一feedback及图。自然文字正确性、来源与新输出层仍需分阶段独立审阅，不能因旧框架批准而自动批准新文字，也不能把mixed-author输入冒充一次全面不同作者的整题审阅。

输入和四输出共用模块来源、固定功能顺序、栏目唯一/题型匹配、guidance禁止修改/评分及修改原句必须student_text等准入。投影另核完整payload、原交付状态与每段自己的claim/关系/原文跨度/触发路径，不能改已审文字或把未审/局部稿升级后沿用旧图。返回的section_order是独立列表，不会改变模块全局顺序。旧已序列化的写作分析须从原已审输入重新分析，不能只改指纹或补一个节点当成新审阅；原合法输入、正文、15/25分及无独立方法触发的guidance例外不变。此为一致性检查，不是签名或审阅者身份、英语、评分正确性的自动认证。

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

从Question Analysis/content-export 1.7.0起，未声明调整的建议区间必须位于该band的冻结评分表区间内，区间直接解析Registry源表，不维护第二份分档表。所有分数建议（含纯文本）绑定自己的审阅、原稿、触发和验证图路径及载荷指纹；四Renderer拒绝事后换分、换档或断开评分证据。旧writing_review 1.0.0/1.1.0正确输入继续支持；旧结构结果须重新分析后再按新契约输出。

词数调整使用writing_review 1.2.0，并在proposed_score提供word_count_adjustment：reviewer、review_status=reviewed、source_section_id、source_quote（该模块具体词数附加规则的原句）、word_count、deduction_points、score_before（lower/upper）、evidence（覆盖完整student_text的跨度）、rationale。band表示词数调整之前的定档；score_before必须在该档内，proposed_score.lower/upper是扣分后区间，最低为0。没有词数调整则省略此字段。

门槛和固定扣分值从同一冻结评分章节解析：应用文仅实际少于60或多于100时减2，恰好60/100不触发；续写仅少于120时接受宿主明确的酌情扣分值，不因超过150机械扣分。程序不认证英语计词结果，word_count与计数理由仍需宿主独立核对。不得数题目给定首句或以部分稿件估全稿词数。

如同时存在原图书写处理，应用文先保持“降低一档”的源规则，续写先核视觉酌扣的前后区间，再输送词数调整；两项均要独立证据。学生输出明确分开档内建议与词数扣分后的建议，不把跨档的扣后数字错误称为档内分数。此为外部建议的记账顺序，不认证宿主定档或裁量正确。

完整版批改同时需要普通observations中独立审阅的A09（应用文）或W15（续写）触发，不从评分建议倒贴触发。引用必须逐字绑定当前题面。应用文需题目与原稿证据，续写需原文、两首句与原稿证据。

## 实际输出门禁

full_correction仅表示材料、交付功能、引用及声称的语言审阅范围齐备，不表示英语判断或评分经过独立真人验证。answer仍为null，Paper不得把分数建议当闭合答案或内容推荐资格。

缺题目、原文或首句：扣留完整分数、剧情/任务诊断和整篇修改稿，只交付逐处现有语言修改。缺原稿覆盖、功能块或独立触发：partial_feedback，扣留分数与整篇修改稿。unreviewed：数据可保留作审计，但学生Renderer不交付其诊断、改稿或分数。guidance不能虚构学生纠错和分数。

## 原手写图片的独立证据入口

Question Analysis和content-export从1.6.0支持原图证据。原有writing_review 1.0.0文字批改仍可运行。图片审阅使用writing_review 1.1.0或1.2.0，不能只提供一个文件名或转写稿：

- 单题输入original_images：image_id、sha256（原始字节的SHA-256）、mime_type、data_base64。仅PNG/JPEG单帧，单图最多10 MiB、2000万像素；核心不读取路径、不下载URL、不做OCR。原图字节解码和尺寸可核不代表原稿身份可核。
- writing_review.handwriting_review：reviewer、review_status、original_handwriting、clear_image、affects_communication（不确定为null）、rationale、该模块评分章节source_section_id，以及student_text_sha256（当前转写稿UTF-8的SHA-256）。转写与原图对应仍须宿主实际核对，哈希只防换稿。
- regions：image_id、sha256、box（原图未旋转的像素坐标[x1,y1,x2,y2]，右/下界不含）、observed（具体看不清什么）、communication_impact（为什么影响读者辨认）。宿主在原图查看区域后填写，不凭字迹美观断言交际影响。
- proposed_score.handwriting_applied只有在完整批改、独立评分触发、清晰原手写、已审阅且affects_communication=true时才允许。original_handwriting_reference必须为已引用image_id。
- 应用文adjustment_kind=lower_one_band，band_before到建议band必须恰好下降一档；deduction_points、score_before为null。不把它改写成固定扣几分。
- 续写adjustment_kind=discretionary_deduction，deduction_points是外部明确的正整数，score_before含lower/upper且减后对应建议区间，band_before为null。程序不替宿主选扣分值。
- 不处理书写时adjustment_kind=none，band_before、deduction_points、score_before均为null。看不清可以记录clear_image=false、affects_communication=null，但不能应用书写降档或扣分。

结果保留image_manifest（ID、字节哈希、格式和真实尺寸）、原稿指纹、区域节点和分数的图路径，不复制base64图片到输出。图与审阅载荷指纹在四Renderer再次核对，材料缺失时仍扣留分数和书写处罚文字。structured只是审计数据，学生端不交付未审阅视觉断言。图片字节和引用完整不是自动视觉评分或真人评分认证。

## 调用与兼容

在完整仓库运行：

```powershell
python -m answer_engine analyze INPUT.json --renderer legacy-wechat
```

Python review_provider仍可提交审阅后的输入，但必须通过相同Schema、原句跨度、题型与材料门禁。不能把正确答案、预设分数或程序测试数据当作独立学生证据。

原图输送烟测可运行 `python -m answer_engine analyze examples/writing-image.synthetic.json --renderer legacy-wechat`。该文件用白色程序图片和明确标记的synthetic视觉断言测试通道；没有实际书写，不是评分、案例或真人结果。实际接入必须用真实原稿字节和宿主独立审阅替换，不可沿用示例断言。

词数记账烟测可运行 `python -m answer_engine analyze examples/writing-word-count.synthetic.json --renderer legacy-wechat`。仍是明确synthetic程序输送记录，不是真人文章或真实评分；完整的定档、词数和扣分值均须以实际审阅替换。

legacy-wechat按原两模块交付顺序输出自然段；逐处原句、改法、理由和可选润色均保留，不生成标题、编号或评分表。宿主提交text时也须遵循原纯文本消息契约。生成适配Skill引用本指南，原课程契约逐字保留。单独安装Skill时仍可依原契约答疑，核心命令需完整仓库。

tests/test_writing_feedback.py使用显式synthetic程序字段检查输送、顺序、拒绝和扣留分支；它不是英语试题、学生实测、评分一致性或旧宿主语义回归。真实完整旧题库与独立宿主评价仍待提供。
