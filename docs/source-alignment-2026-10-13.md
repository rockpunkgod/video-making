# ANSWER 来源对齐与模块交接

video-making 的当前教学来源已更新到 ANSWER 提交 `61bc9c3e15004639cb442c20e7946ca9631f14ce`。原 ANSWER 仓库、已安装技能及私人原题材料没有被修改。本次更新是来源与规则对齐，不是方法实效认证。

## 当前版本

82 个现有方法 ID 保留，51 张来源发生变化的卡片已逐项更新启动、动作、判断和停止条件。旧版规则及公开案例保存在 `provenance/runtime-snapshots/b04ebc26d7fa096404111a0bb12f6c77cc8525b9`，新版来源原件保存在 `provenance/upstream-revisions`。

R06 继续使用学生入口名主旨缺块，但只作所问范围中的遗漏诊断，不是独立整题算法。定位阅读法、顺藤摸瓜、左顾右盼和中心思想按各自的课程身份保留，不再互作泛化别名。完形按证据推进，不强制空号、两遍或先易后难。PTSD 来源版本分开，动作链不设通用三个动作上限；应用文的训练数字不变成整篇词数门槛。

## 调用与复核

在仓库根目录执行：

```powershell
python -m answer_engine validate
python -m answer_engine method R09
python -m answer_engine course-identity "顺藤摸瓜（记叙文细节的原命名）"
python -m answer_engine analyze examples/question-action-course.json --renderer structured
```

历史复核须明确指定旧来源版本：

```python
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
history = Registry(snapshot_commit="b04ebc26d7fa096404111a0bb12f6c77cc8525b9")
engine = QuestionAnalyzer(history)
```

历史 Registry 不能批准当前方法升级。私人案例通过只读历史上下文复核，旧观察、动作和审阅不被重写，也不计成新版独立 Blind 样本。公开旧课程例仍保留原出处和方法版本；新版覆盖与发布门槛不自动认可它们。

## 现有真实案例的新版准入检查

2026-10-13 再次核对远端 HEAD，仍为 `61bc9c3e15004639cb442c20e7946ca9631f14ce`，与当前 Registry 来源一致。可只读检查私有案例的历史合法性及当前准入：

```powershell
python -X utf8 -m scripts.audit_real_case_epoch --dataset local-data/organized-pdfs
```

当前私有目录的第 22 版目录包含 22 个案例（F01 8、R09 6、R06 2、G01 6）。历史完整性校验通过，但这 22 个旧请求均被当前版本绑定检查拒绝；不能换一下版本号就计入新版覆盖。工具逐项给出当前四步动作及待重新审阅条件，不改题目、目录、动作、审阅、观察或成熟度。结构准入通过也不代表语义或学生验收通过。

另存的一份 G01 湖北圆创 Q62 当前版动作已执行并通过四种输出检查：先标提示词，再核空位功能，产物仅为名词路线节点，不生成词形或答案。原题面与旧动作字节校验保持一致。这是揭答后的 AI 重建，不是独立审阅、正式新 Case 或新 Blind 样本；私人材料不随源码打包。

## 下游失效检查

`export-status` 只投影请求提供的冻结状态。要检查冻结素材是否仍符合当前正式教学版本，使用：

```powershell
python -m answer_engine export-current-status REQUEST.json
```

ANSWER 比较当前版本及教学字段，出具带校验值的状态。版本变化或同版本教学字段不符都会使素材失效；已有撤销不被恢复。下游仅消费状态，不自行读取课程资料改判答案。未上线的候选版本不能出具当前正式状态。

## 验收边界

所有方法仍为 candidate，没有因本次更新升级为 validated、stable、Efficient 或 Signature。六个重点方法的学生文件包含独立四步卡、短稿、视觉公式、反例与挑战，但仍标为草稿；其他受影响入口在复核完成前不会继续展示旧稿。

传播效果先验收，强可用性后验收；冲突服从正确性与可用性。工程测试、来源校验及旧案例复核不证明学生 First-use 成功，不证明提速，也不构成公开发布授权。

## 提交与打包范围

本轮工程复核：当前工作区全量回归 1379 项通过（0 失败、0 错误）；从本次暂存内容单独导出的干净副本，来源与生成资产校验通过，另有 86 项来源、历史回放、激活和下游关键回归通过。全量范围包含工作区现有其他模块测试，独立副本复核用于确认本次交付不依赖这些未提交改动。上述结果均不代替学生或实效验收。

本次交付只包含 ANSWER 来源对齐及其必要接口变化。私人原题、`local-data`、原工程附件和其他模块未提交的开发内容不得打包。打包应从核对过的 Git 提交导出，不能直接收集当前混合工作区中的全部文件。
