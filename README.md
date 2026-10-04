# 高考英语方法体系样板

本仓库是从 `rockpunkgod/ANSWER` 的课程证据中另行构建的方法资产库，不修改、不复制、不替代 ANSWER 的答疑 Skill。它把已核验的课程方法转成学生可识别、可执行、可验证、可刹车的 Method Card，同时保留课程名与固定版本的来源引用。

## 本轮交付

- `method-registry/schema.yaml`：统一 Method Card Schema。
- `method-registry/registry.yaml`：六个示范方法的唯一索引。
- `method-registry/reading.yaml`：R01、R02、R06、R09。
- `method-registry/seven-five.yaml`：F01。
- `method-registry/grammar.yaml`：G01 及决策树节点。
- `references/student-symptoms.md`：学生症状到方法入口。
- `references/anti-rules.md`：第一版反口诀清单。
- `student-guides/`：六个方法各自独立的学生首次接触版，含 10/30/90 秒同标准表达。
- `cases/`：六个方法的 canonical、counterexample、boundary、transfer 案例框架。
- `EVALUATION_PROTOCOL.md`：Practicality Gate、First-use Test、Blind Evaluation 与 Baseline 对照协议。
- `tests/`：结构、来源、组合、状态与关键边界的自动回归。
- `REGRESSION_REPORT.md`：原有测试、新增测试、有意变化与证据缺口。

## 设计决定

1. 课程证据仍是方法事实来源。`brand_name` 只降低学生的执行成本，`source_name` 和 `source_references` 始终保留。
2. `locator` 和 `reducer` 只负责找位置或缩范围，不得宣称直接定案。
3. 每张卡同时提供 `compact` 和 `full`；传播版不能脱离完整版单独作为答案依据。
4. 案例原文未被 ANSWER 运行层可重用发布时，案例文件显式标记 `evidence_gap`，不补造题面。
5. 六个方法本轮统一为 `candidate`。只有四类案例和原回归全部闭环后，才能升为 `validated` 或 `stable`。
6. 传播性服从可用性。方法优先级固定为：正确性→可触发性→可执行性→迁移性→效率价值→易记性→传播性。
   验收执行顺序为：先传播效果验收，再强可用性验收。先验证看懂、记忆、复述与视觉动作，再用陌生题验证实战。第二阶段优先级更高；传播和实用冲突时，以强可用性验收为准，回改传播表达，最终升级仍须通过可用性门槛。
7. 六个样板暂只标为 `Useful`，不标 `Signature`。未运行的真实学生 First-use Test 和 Blind Evaluation 一律留空，不用内部结构检查代替学习效果。

## 保留与重组

- 原逻辑完整保留：直接/间接支持、主体与施受关系、主旨覆盖与错误关系、三一致只初筛、语法填空先判结构后变形。
- 升为主方法：过度推测→R01，主客一致→R02，主旨缺失→R06，三化法→R09，三一致→F01，语法填空总路线→G01。
- 降为子动作：首尾段、段首句、重复词变成 R09 的取证入口；结构、主体、时间变成 F01 的三个初筛维度；各语法知识点挂到 G01 决策树节点。

## 验证

在仓库根目录运行：

```powershell
python -m unittest discover -s tests -v
```

校验依赖 Python 3 和 PyYAML。

## 来源基线

- 只读来源：`https://github.com/rockpunkgod/ANSWER.git`
- 基线提交：`b04ebc26d7fa096404111a0bb12f6c77cc8525b9`
- 取证日期：2026-10-05

详细路径和章节见每张 Method Card 的 `source_references`。
