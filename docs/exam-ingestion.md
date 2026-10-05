# 用户提供的真实试卷：导入与隔离回归

2026-10-05接收2020—2025年Ⅰ/Ⅱ卷共12套、25个Word源文件。清单哈希全部核对通过；材料是第三方整理及解析，不是官方扫描或官方解析，不把来源身份改写为官方。现有ANSWER和Method Registry未改。

原文件、原卷/解析独立提取、稳定题号输入、Blind Prediction、Reveal Result留在被Git忽略的`local-data/exams-2020-2025/`。未核公开再发行权限，不把全文或参考范文上传到公开仓库。冻结写入可重复执行，但不同内容不得覆盖；文件系统本身并非防篡改存储，采集身份和素材权利仍须外部审阅。

```powershell
python -X utf8 -m scripts.ingest_exam_sources "用户提供的下载包目录"
python -X utf8 -m scripts.run_exam_regression gaokao-2024-I
python -X utf8 -m scripts.run_exam_regression gaokao-2024-I --reveal
```

officecli因本机组件缺失无法读取，按技能兜底使用OOXML只读提取；`.doc`使用Word只读、禁宏、隐藏窗口、不加入最近文件、不保存更改，并核提取前后源哈希。保留表格段落、制表符、换行。自动编号和嵌入图片登记为提取风险，未做OCR不声称图片内容完整。

并行完成11卷布局核验及回归：共517项，阅读165、七选五55、完形165、语法110、两类写作各11。2021Ⅱ因原卷空号和选项结构缺损拒绝加入完整回归，不能靠解析推补正文、选项或题号。缺句点但标签清楚的选项保留实际标签，不添标点；歧义或缺内容则拒绝推补。新增2025Ⅱ目录的两个Word与原冻结源哈希一致，仅登记私有来源别名，不替换原材料；听力文件不混入六型笔试评估。

11卷全部运行Question Analyzer与Paper Analyzer；495道客观题机械运行全部未解。预测先冻结，Reveal才读取第三方答案与逐题解析，22项写作不做Exact Match。机械回答0、匹配0、错答0、未解495，正确率为null而非0%或100%；结构未猜测不等于语义审阅已确认的safe_abstention，后者仍为null。语义、Trigger、Boundary失败统计均待审，不伪造为0。正式Case新增0、填槽0，144个核心未登记槽仍未补齐，82项仍Useful+candidate。

另有3道揭晓前AI宿主动作审阅：2021ⅠQ26（R01/R02）、2023ⅠQ21（R12定位/R01判断）、2025ⅠQ31（R09骨架/R06覆盖）。冻结触发、动作、证据和刹车后再对照，3道与第三方参考答案一致。自选3题不代表整卷自动正确率、独立人工语义认证或真人First-use效果；辅助方法不借整题答案冒充定案。这类审阅与机械未解分开统计。

统一入口支持`--phase blind/host/reveal`及`--review`，但不是通用英语自动求解器，宿主适配支持范围不同：2023的示范适配仅限2023ⅠQ21，2024Ⅰ已经揭晓不得补标盲审。命令不会自动运行下一阶段。修改解析提取时保留旧冻结结果，显式版本文件记录修订；汇总选择最新版本。2025ⅠQ56/Q64同题号详解正文保留，v1.2另修新题号/下一篇被吞入详解的问题；两卷均保留初版、v1.1、v1.2，未更换盲预测。

## Case Candidate与揭晓后AI审阅

```powershell
python -X utf8 -m scripts.collect_exam_cases gaokao-2021-I
python -X utf8 -m scripts.collect_exam_cases gaokao-2023-I
python -X utf8 -m scripts.collect_exam_cases gaokao-2025-I
python -X utf8 -m scripts.summarize_exam_ingestion
```

此步骤不读答案：核冻结宿主稿与机械预测哈希、原题不可变字段、图及执行链，逐项重放并检查当前引擎结果等于冻结结果，再用原卷47题加原有审阅注释重跑Paper Analyzer。必须标记为揭晓后的冻结注释聚合，而不是新增盲测。题文、图、实际产物及候选存放私有`case-review/<exam_id>/candidates.json`。只计方法自身已核触发及实际产物/决定，不给默认建议、已停方法或借用其他方法闭合的节点成功信用。

实际得到6个方法候选：2021ⅠR01/R02、2023ⅠR12/R01、2025ⅠR09/R06。2021Ⅰ只有relation-level决定、没有typed动作，标记needs_action_recording；其余4个有产物也只标pending_case_review。三个独立执行的揭晓后AI审阅文件以宿主稿哈希、题号和版本绑定，仍不是独立人工认证。类型建议不等于批准类型，review-index及公开元数据不改变Registry或填槽。

审阅发现：两道R01的A项用相关名词强补共同断言，排除方向正确也不能视作方法成功；必须先确认同一完整断言才能拆增量。R02只负责D项风格/动作主体，不独立证明整题。R12引全文不能据此宣称少读文本。R09骨架不能将儿童步行和安全活动受挤压，写成历史安全指标绝对下降。R06可用Why the Rush?表达全文价值冲突，缺streets等原词不等于主旨缺块。R01/R06的boundary与R02 canonical仅为审阅建议，其余不强分类型；不因为题材不同或方法联用就机械填写transfer/hard。

闭环当前已到Case Candidate→AI Case Review，登记仍待完整来源/语义/动作及授权审阅；新增正式Case和填槽仍为0。题目答案匹配、工程重放、方法归因与真人效果是四项不同证据，均不互相代替。

## 负向审阅必须实际执行

`from answer_engine import withdraw_review`接收原输入、冻结分析与显式负向审阅。finding必须绑定两份内容指纹、题号、揭晓后阶段、审阅者、失败分类及精确关系索引/执行ID。仅能撤回，不能添加答案或改原题；现有引擎重放不等于冻结结果时拒绝事后贴合。

撤回关系后，将它标为unreviewed并停用对应决定产物；撤回框架、定位或决定产物时沿依赖链停用消费者，并撤回消费者所声称的决定关系。关系索引保持不变，不改候选原主张；旧讲解/评分注释不能复用。重新运行Question/Paper Analyzer及四Renderer，不以原高Demo分越过失效证据。

```powershell
python -X utf8 -m scripts.apply_exam_withdrawals gaokao-2023-I local-data/exams-2020-2025/semantic-reviews/gaokao-2023-I.withdrawal-request.json
```

实际三道负向处理另存私有withdrawal.json：2021ⅠQ26及2023ⅠQ21撤回R01对A的归因，候选A待核，答案与展示推荐实际扣留；2025ⅠQ31暂撤精度待核的R09骨架及依赖的四项决定。此为保守停用，不宣称参考答案错误。公开报告分开保留原3道盲匹配与当前3道扣留，不回写原预测，也不将扣留计作新的盲测或语义已认证的safe_abstention。审阅身份及英语结论仍待独立审阅，程序仅执行负向决定。

已发现的2024Ⅰ卷解析风险单独登记为pending_review：Q58援引`use sth. to do sth.`但原句是`open on warm days`；续写范文提取文本可见段落重复。保留原稿，不自动改答案、去重或把该解析判成正确。2021Ⅱ卷包内已知第65题the/from冲突及卷首分值问题仍单独保存，未用说明覆盖原题。

下一阶段须逐题独立语义审阅、错误分类、Case Candidate→Case Review→登记；不能为补数把同一题包装成五类案例，不能反推方法以贴参考答案。当前无可靠自由题面语义后端，机械Analyzer运行不冒充独立英语解答。嵌图、表格版式、第三方答案权威性与公开权利仍待核。真实学生传播/First-use/Blind/Baseline/Short-version Safety是另一条研究链，目前观察0，未被原题数据补齐。先传播效果验收，再强可用性验收；冲突以可用性为准，总验收仍PARTIAL。
