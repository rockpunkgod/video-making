# 可执行方法编排接口

Question Analysis / content-export 1.4.0增加execution_trace。旧调用仍可只交题面和relations：没有action_executions时，只有方法计划/关系审阅，不生成实际动作产物。已有候选闭合规则不变；新执行通道不会用分组、定位或框架替代定案。

## 运行课程已有片段

```powershell
python -m answer_engine analyze examples/question-action-course.json --renderer structured
python -m answer_engine analyze examples/question-action-course.json --renderer student
```

该示例沿用课程已有environmental ___ (protect)短片段，宿主显式提交空位路线和词形核验，并用blank-route → noun-form连接两个动作。它是工程课程示例，不是完整真题、自动英语语义求解或真人First-use实验。

## 输入与产物

每条action_executions遵守schemas/method-execution.json：execution_id、method_id、method_version、role、input_artifact_ids、concrete_action、当前题面evidence、decision_rule_check、stop_rule_check、stop_applied、reviewer、review_status和output。产物遵守schemas/action-artifact.json；执行顺序就是输入列表顺序，不猜测或自动重排依赖。

| 角色 | 可产生的具体类型 | 不能冒充的结果 |
|---|---|---|
| locator | located_evidence：当前题面跨度 | 定位不定案 |
| interpreter | interpretation：有引文的语义/成分拆解 | 看懂不自动排除 |
| reducer | candidate_partition / text_groups / route_selection | 分组、分路线不产生答案 |
| framework | framework_card / route_selection | 骨架不自动选项闭合 |
| decider | candidate_decision：候选、效果、对应relation_index | 不能借另一候选或未审阅关系 |
| verifier | verification_result / located_evidence（扩证） | 核验或扩证不凭空新增答案 |

角色输入/输出类型来自core/composer.py的统一契约。method_chain保留原input/output文本，并增加input_artifact_types、output_artifact_types和execution_ids。state=planned只为计划，reviewed只为候选关系审阅，executed表示已提交可用的外部动作产物，stopped表示该步骤刹车。executed不是模型自行执行英语推理，也不认证宿主的动作描述、语义、身份或审阅为真。

## 执行与刹车规则

执行必须属于当前匹配且选入链的方法，版本和主/副职责必须与Registry一致。每个已审阅动作另有独立触发。副职责另成步骤，C01的framework产物不能直接冒充decider。

下一步只能引用本次输入中更早的produced产物；不允许前向引用、自循环、重复引用、类型不兼容、未审阅产物、缺题面产物或已停止产物。每步仍可重新回原文取证；前一个定位结果不是不可扩读的范围锁。当前题面精确跨度重新核对，输出引文须由本动作证据覆盖。

stop_applied=true时output必须为null，不能把“继续产出”包装成刹车。被停止的decider不能同时提交同职责已审阅的保留/排除关系。未审阅或本动作所需题面不全时，提议输出实际扣留为null，不传给后续方法。缺选项会挡定案、候选分组及对应验证，但不挡已有文章和任务证据支持的定位、拆句或框架产物；仍不能由这些辅助产物自动补选项或猜答案。

candidate_partition按一次分组维度覆盖全部实际选项、各一次，不允许丢项或加项；多维三分应分别记录各维度的分组动作。它仅改变候选组织方式，没有“分组后剩一项即正确”的权限。text_groups保存有跨度的文本组合；route_selection只能选择显式提示词分支和独立功能触发已确认的节点。

R09只接受framework_card的object、core_judgement、text_task三个字段。重复词、首尾、段首仍是证据入口，不能作为骨架的三个字段替代对象、判断和结构任务。框架字段均有当前题面引文，但这些字段的语义覆盖仍须外部课程审阅。

C01主要职责产物须有current_blank_role、recent_clue、expansion_gate、backfill_check四字段，不能只说“语篇逻辑”；其decider副职责仍另核具体候选。F01/F02/F03/F04必须产实际候选分组。G01/G02必须产路线并暴露有无提示词分支；选具体功能时须保留全部已审阅竞争功能，不能隐藏冲突只挑一个节点。

candidate_decision必须指向相同方法、职责、候选、效果和已审阅关系，且关系证据由本动作证据覆盖。最终答案仍依赖唯一候选自身保留和全部竞争项独立排除。verification_result必须实际消费同一候选的更早decision产物；若为rejects或unresolved，撤回当前答案/闭合状态，并禁止进入整卷内容推荐，直至解决核验冲突。

## 图、导出和验证边界

execution_trace保存实际动作、输入ID、输出、状态、证据节点、动作节点和产物节点。EvidenceGraph用action_artifact绑定独立触发、具体动作和当前证据；产物指纹绑定输出结构，跨步骤引用用显式边连接。指纹只检出结构脱钩，不证明英语语义正确。

Analyzer和所有Renderer均核trace/chain/graph一致性：改输出却不更新相应产物图、换节点、漏执行绑定或伪造executed状态都会被拒绝。Structured和content-export保留完整执行链与产物；学生版区分下一步计划、实际动作和停止原因。

完整自由题面动作仍由宿主/人工或review_provider提交。核心负责真实可运行的依赖、跨度、职责、刹车与闭合控制，不把外部记录升级成经过统计校准的自动语义求解。程序控制测试不属于真实教学验证。
