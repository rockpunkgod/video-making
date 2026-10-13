# 发布准备记录

本记录对应 2026-10-13 的发布准备。根代理已完成行为验收并授权发布；本次变更仍须以 Git 提交和远端状态核验为准，不表示部署或同步中央 Skill。

基线为 `5dfb258881adb9f90e00289b86357dd3d360480c`。更新前正式包保存在 [旧版 ZIP](../../../archives/gaokao-skills-before-20261013-5dfb258.zip)，校验与恢复说明见[备份说明](../../../archives/gaokao-skills-before-20261013-5dfb258.md)。

## 本次修订范围

- 客观题阅读：修改 `gaokao-english/SKILL.md`、`references/router.md`、`references/reading-comprehension.md`、`references/course-evidence.md`、`references/evidence-gaps.md`，对齐课程原名、证据身份、受限入口及运行边界。
- 写作：修改 `gaokao-writing/references/application-writing-and-correction.md` 与 `references/continuation-writing-and-correction.md`，保留应用文与读后续写的来源版本、方法职责和未验缺口。
- 文档入口：根 README 仅新增旧版备份与核查资料链接。
- 归档：保存旧包 ZIP 与说明；保存 2026-10-13 课程核查资料；保留本批客观题与写作发布说明快照。归档内的材料状态不约束后续正式模块状态。

发布说明快照：[客观题阅读增量](objective-release.md)、[写作有界增量](writing-release.md)。其中“未提交/待验”等表述保留为快照形成时的状态，不应解释为当前验收或发布结果。

## 独立行为验收

根代理对六个学生请求完成有界行为验收，六例通过：应用文“两简一复从”与反向劫匪插葱；续写名称版本/PTSD边界与段间衔接；阅读课程原名与范围；褒贬一致单题比较；分句结构法单题条件核查。验收展示的是六例中的有限动作与缺口处理，不代表全部课程或全部方法完成验证。

未测范围仍包括七选五、完形、评分实战、其他阅读文体整篇题序；也未完成长句重构全流程、动作面定义、续写富兰克林、中心思想强推理、所有褒贬题或复杂作者态度的全面验收。课程证据范围没有因本次行为验收扩大。

旧版 ZIP SHA-256 复核仍为 `F5C1A26A7B67A21F5EE8630419D3F24371F140EEE08F609BE284A4E127F77A11`，对应基线提交 `5dfb258881adb9f90e00289b86357dd3d360480c`；旧包完好。
