# B站横版发布包装

`content_os.bilibili_packaging` 只负责本地候选及真实产物绑定，不登录、不上传、不发布，也不替代 `content_os.showcase.decide` 的教学、来源、编辑及最终媒体审核。

`generate_candidates(folder, revision, author_path, plan_path)` 生成三套真实1920×1080封面PNG、可编辑SVG、320×180手机缩图、标题和简介草稿，以及本地HTML审阅入口。候选中的真实英文锚点须存在于同一已绑定题目的原文及选项中；源码不含真实试卷全文。没有新媒体时，媒体字段为空并明确待制作，不用旧片补位。候选不自选。

`finalize(package, author_path, plan_path, media_path, qa_path)` 验证实际作者、计划、新媒体和同版QA后绑定4K24成片，执行既有 `showcase.inspect_media` 的实际探测及完整解码。QA必须绑定相同媒体SHA、计划SHA、修订及帧数。返回新对象，不覆盖原包或旧媒体；调用 `save_package(folder, package)` 显式保存。

`choice_template` 只生成外部创意选择的待审工作单。`selection_status` 校验外部用户与ChatGPT选择的精确输入绑定、带时区日期、真实声明人及证据文件。封面字节、标题、简介、来源、计划、QA或媒体发生变化后，旧选择失效。外部身份仍需操作者核实，程序不能认证用户身份。创意选中不自动通过任何公开审核，包装模块始终保留 `public_render_ready=false`。

横版尺寸来自本次用户要求，不能冒充已测的B站实时UI安全区。现有旧平台配置只有竖版模拟；本模块不强行套用竖版矩形，也不建立新的平台发布器。实际手机缩图可读性和封面艺术判断分别记录；测试不代表点击率或学习效果。

发布后数据入口将操作者导向既有 `content_os.engagement_learning.AudienceLearning`：先冻结实际最终cut和title/cover/description版本；用户真实手动发布后登记真实帖子ID、URL和时间；再录入带来源、统计窗口的实际观察。未发布时没有平台数据，不填造结果。
