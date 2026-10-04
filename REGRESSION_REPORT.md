# Regression Report

日期：2026-10-05  
来源基线：`rockpunkgod/ANSWER@b04ebc26d7fa096404111a0bb12f6c77cc8525b9`  
目标仓库：`rockpunkgod/video-making`

## 结论

六张 Method Card、六份学生首次接触版、症状导航、Anti-Rule Registry、24 个案例位和 Practicality/Blind Evaluation 协议已建立。自动结构与边界回归 16 项全部通过。

这不等于已通过真实学生教学验收。First-use Test、Blind Evaluation 与 Baseline 对照尚未运行，所有结果值保持 `null`；六个方法均为 `candidate + Useful`，未升级为 `validated`、`stable`、`Efficient` 或 `Signature`。

## 原有测试

ANSWER 当前可见文本对这六个方法没有提供可直接运行的统一回归套件。本轮将原模块中的关键行为边界固化为回归断言：

- R01：直接支持与间接支持都是文本依据；绝对词不机械判错；排除一项不证明剩余项。
- R02：愿望不等于事实，能力不等于意愿，三槽位一致只通过本项检查。
- R06：只用于全文主旨、写作目的或最佳标题；明确局部细节题不进全文拼图。
- R09：首尾段、段首句和重复词是取证入口，不是机械固定三步；主要段落缺失时停止。
- F01：结构、主体、时间只缩小候选；最终必须内容闭环；只剩一项不自动正确。
- G01：有/无提示词先分路；有提示词先定空位成分；只有确认需要动词形式才分谓语/非谓语。

## 新增自动测试

命令：

```powershell
python -m unittest discover -s tests -v
```

结果：16/16 通过。

覆盖：

1. 六个且仅六个样板方法存在。
2. 全部 Method Card 满足 Schema 必填字段。
3. Registry 索引与卡片的名称、状态和版本一致。
4. `primary_role` 和 `output_type` 清晰，F01 是 `reduce`，R09 是 `framework`。
5. 所有来源引用固定到同一 ANSWER commit，并含路径和章节。
6. 六张四步实战卡完整。
7. Practicality Gate 七项回答完整，状态如实标为实测待进行。
8. First-use Test 结果未伪造，全部保持待测。
9. Blind Evaluation 已定义 Baseline 和八项指标，未运行值保持空。
10. 所有方法均为 `candidate + Useful`，不过度声称成熟度或品牌等级。
11. 每个方法四类案例路径均存在且类型对应。
12. 存在案例缺口时，`validated/stable` 门禁不允许通过。
13. 六份学生首次接触版均含四步卡、10/30/90 秒版、挑战、视觉式和 Anti-Rule，且不以抽象定义开场。
14. Anti-Rule 首批八条齐全。
15. 原课程六类关键边界保持。
16. G01 的完整版是真实分支 Decision Tree，而非平铺知识清单。

## 新增手工检查

验收流程已追加为两阶段：先传播效果验收，再强可用性验收。以下文案检查属于第一阶段的内部审查，真实学生传播效果与第二阶段实战效果均仍待测，未据此升级方法状态。

- 学生页的首段全部从症状和第一动作开始，未用抽象定义开场。
- 学生页不存在把注意、理解、结合上下文、看逻辑、分析全文作为唯一动作的说明。
- 六个品牌名均可自然动词化：选项在加戏、先看谁干的、主旨缺块、把全文压一下、七选五先三分、这个空先判位置。
- 六张视觉式均可在一屏内表达方法核心动作和产物。

## 行为变化

### 有意改造

- 过度推测重组为 R01 选项加戏，第一动作固定为 A+B→只查 B；直接/间接支持边界不变。
- 主客一致重组为 R02 谁干的陷阱，学生入口从抽象主客改为三槽位对齐；愿望/事实、能力/意愿、施事/受事逻辑不变。
- 主旨缺失重组为 R06 主旨缺块，将不全面落成 2–4 个核心块与块间关系。
- 三化法的学生产物重组为 R09 全文骨架卡。对象、核心判断、结构任务是产出格式；课程原有首尾段、段首句、重复词全部降为取证入口并保留。
- 结构一致、主语一致、时态一致合并为 F01 一次性 reducer，最终内容闭环责任不变。
- 语法填空总路线重组为 G01 Decision Tree，所有具体知识点作为叶节点依旧保留。

### 无意行为变化

未发现。由于目标仓库为独立方法资产库，本轮未改动 ANSWER 的路由、答疑顺序、输出合同或任何源文件。

## 证据不足与待办

- R01、R02、R06、R09 的多数课程例题在 ANSWER 运行层被有意抽象化，未发布可重用完整题面与答案链。相应案例位标为 `source_pattern_only` 或 `evidence_gap`。
- F01 和 G01 已放入来自课程语料或讲义登记的真实例题，但仍需在冻结盲测集上运行 First-use Test。
- 方法的 Trigger Precision、Trigger Recall、Resolution Rate、Standalone/Assist Rate、False Trigger Rate、Transfer Rate 和 Time/Complexity Gain 尚无真实测量值。
- 在这些缺口闭合前，不得将任一方法标记为 `validated`、`stable`、`Efficient` 或 `Signature`。
