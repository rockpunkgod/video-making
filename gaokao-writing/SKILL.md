---
name: gaokao-writing
description: 高考英语应用文、读后续写答疑；经注册表、证据核验与独立输出适配。
---

# 统一引擎适配入口

先读取本目录 [generated-contract.md](generated-contract.md)，再按题型读取其中链接的 references，保留原先题型、顺序与证据边界。课程原名、学生品牌入口、内部框架、判项诊断和课程题名按实际身份分别处理。只有已明确绑定同一动作的名称才能作入口别名，不能把独立课程原名静默合并。品牌入口不增加判据，诊断不变成独立整题算法。源契约中的逆推只能用于独立核验，不得把已知答案当证据或在 First-use 先猜后贴方法。

方法查询：在项目根执行 `python -m answer_engine method METHOD_ID`；单题：`python -m answer_engine analyze INPUT.json --renderer legacy-wechat`；整卷：`python -m answer_engine paper INPUT.json`。宿主模型按完整契约作语义分析，再提交有原文跨度、判据、刹车、回填和审阅者的 relations；核心不把宿主猜测当自动验证。缺题面或语义证据必须暂留，不填答案。写作完整批改仍由宿主按15/25分独立契约完成，不由本地程序伪评分。

单独安装 Skill 文件夹时，生成资源可自包含调用，完整核心命令需整个仓库及依赖；不要假定安装 Skill 等于安装核心。不能执行程序时按题型查询 [generated-methods.yaml](generated-methods.yaml)，完成相同证据动作；明确标记宿主分析未经核心检查。不要绕开停用边界。

名称身份有疑问时读取 [generated-course-identities.yaml](generated-course-identities.yaml)，并回对应题型原章节；项目内可用 `python -m answer_engine course-identity 完整源标题` 查询。来源登记、程序检查或生成短稿不等于方法已通过传播、实用性或真人验收。

完整写作审阅进入核心时读取 [writing-review.md](references/writing-review.md)，提交writing_review而非用客观题relations假装评分。区分确定错误与可选润色，独立15/25分规范、材料与书写边界不变；程序只检查引用/交付结构，分数仅外部建议。
