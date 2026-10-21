# Cognitive Symbol Library v1

本库归属现有 Motion Identity。作者在 `AV_AUTHOR.cognitive_symbols` 选择有源 Recipe；
`creative_os.motion_identity.compile_symbols` 编译入同一份 `AV_PLAN.symbol_recipes`，
当前受保护的 Native 模板调用 `ae/rigs/cognitive-symbols.jsx`。没有另一套导演或渲染器。
G01 的旧 registry、绑定与验证接口继续保持历史行为。

`semantic_isomorphism` 用已核验的同主体、同比较对象、同价格维度，对齐不同表达。
`same_form_different_relation` 保持共同名词稳定，展示真实动作和角色差异；Hook 只允许
既有已绑定决策中的两处相同名词与匿名结构，不显示实际动作、角色、判断或答案。

作者必须绑定外部用户请求、精确原文范围、实际已审方法执行、已消费的 interpretation
output、完整候选核验及实际场景终判。布局或几何重合不能证明英语语义。
库只检查这些引用和执行约束；上游语义审阅、原速观感、听感及学生效果分别记录。

每个实例有唯一 `symbol_id`，每种模板有稳定 `recipe_id`。`inputs` 的每个对象指定
`object_id`、Recipe 对应 `role` 和 `{world,pointer,start,end,quote}`。
参数为 `duration_seconds`、`space:{origin,depth}`、
`font:{family,size,advance_factor,line_height}`、`layout:{width,height,min_gap}`、
`curve:"smoothstep"`、`mask:"source_glyphs_only"`。坐标是 Rig 局部逻辑像素，
相对 `space.origin`；4K 继承当前原生合成缩放。参数预检不自动换行、缩字或降级为文字卡。
多行文本保留真实换行；超出版面、缺源、角色缺失或无效关系直接拒绝。

Lesson 使用既有 `settled + 0.3s` 至真实判断时刻，最短 3 秒；移动至多 1.35 秒，
最后 6 帧精确归位，其后保留至少 1 秒稳定辨认。Hook 使用既有 Hook 时钟。
结尾仅可用 `recall_of` 重现两条已完成 Lesson 的同一对象及关系，不增加教学断言。
时间参数改变不了完整口播，也不能挤压必读意群。

必须在实际 AE 原生两合成检查原字身份、源范围、字体度量、遮罩、深度、位置和运动。
同名词对精确重合是允许的语义结构，其余对象不得过度重叠。结构只使用既有雾蓝
`#7E96A8`、柔砖红 `#A36F64`，不覆盖本片 Reading 的已审原色。

静态和动态预览来自当前私有生产目录中的真实 Native 输出，并由输出媒体 SHA、参数 SHA、
来源 SHA 与原生审计绑定。仓库不放私有原题或媒体，也不预置不存在的预览文件。
在真实原生执行前 `actual_native_consumption=UNVERIFIED`；原速观看和试听未进行时保持
`UNOBSERVED`。工程测试不代表艺术质量、点击率、留存或学习效果通过。

当前独立制作已实际执行两个 Recipe（含匿名 Hook、两题 Lesson 和两条结尾 Recall）及
原字挑战。`SYMBOL_NATIVE_READBACK.json`、`CHALLENGE_NATIVE_READBACK.json` 和
`NATIVE_PREVIEW_RECEIPT.json` 位于私有生产修订，记录实际双合成参数及静帧。
`presets/first-person-lesson.json` 对齐该版实际32号关系文字和1080×360局部布局。
这不使编译计划中的预期状态自动成为媒体或艺术审核；最终动态预览仍须从同版真实编码
影片逐帧截取，并绑定 `MASTER_DELIVERY_QA.json`、Recipe实例及输出哈希。
