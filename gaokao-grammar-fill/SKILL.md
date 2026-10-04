---
name: gaokao-grammar-fill
description: 高考英语语法填空答疑；经注册表、证据核验与独立输出适配。
---

# 统一引擎适配入口

先读取本目录 [generated-contract.md](generated-contract.md)，再按题型读取其中链接的 references，保留原先题型、顺序与证据边界。课程原名和品牌名是同一方法的别名，不产生新判据。学生动作入口允许注册品牌名，方法问答同时兼容课程原名。源契约中的逆推只能用于独立核验，不得把已知答案当证据或在 First-use 先猜后贴方法。

方法查询：在项目根执行 `python -m answer_engine method METHOD_ID`；单题：`python -m answer_engine analyze INPUT.json --renderer legacy-wechat`；整卷：`python -m answer_engine paper INPUT.json`。宿主模型按完整契约作语义分析，再提交有原文跨度、判据、刹车、回填和审阅者的 relations；核心不把宿主猜测当自动验证。缺题面或语义证据必须暂留，不填答案。写作完整批改仍由宿主按15/25分独立契约完成，不由本地程序伪评分。

单独安装 Skill 文件夹时，生成资源可自包含调用，完整核心命令需整个仓库及依赖；不要假定安装 Skill 等于安装核心。不能执行程序时按题型查询 [generated-methods.yaml](generated-methods.yaml)，完成相同证据动作；明确标记宿主分析未经核心检查。不要绕开停用边界。

语法知识路由读取 [grammar-navigation.md](references/grammar-navigation.md)。先确认有无提示词，再按未填句功能进入节点；树路径只是知识调用计划，不能代替句法、搭配与词形核验。
