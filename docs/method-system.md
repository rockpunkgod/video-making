# 方法系统与维护

Registry索引六题型方法文件。method_type区分框架、方法、子动作、内部规则、分类与复核；primary_role只有一个，secondary_roles显式登记。source_name/source_alias保留原名；W03学生主名为剧情四格，PTSD只作源别名。

82项不等于82个品牌：包括定位子动作、语法节点、训练框架与评分规则。阅读17项、七选五11项、完形9项、语法19项、应用文10项及续写16项保留。对齐61bc9c3后的实际入口状态为29项静态齐备、6项重点草稿、47项复核中；不能沿用旧版82项全部齐备的结论。student_ready=true不证明First-use、传播或迁移效果；所有方法仍为Useful+candidate。来源更新后的语义复核、真实案例及受试验证仍缺。

职责：locator→locate、interpreter/framework→interpret（G01路线为reduce）、reducer→reduce、decider→decide、verifier→verify。C01是语篇操作的内部框架整理，其显式框架/决定阶段不能被说成课程系列名对应的一套独立算法。首次接触只突出主要职责；F01无decider副职责。R06是主旨覆盖诊断，R17是内部补证核验，不能把它们当作各自独立完成整题的算法。

## 从卡点进入第一步

```powershell
python -m answer_engine symptom 阅读理解 看不懂长句 --renderer student
```

学生模式仅展示一个可能入口的启动条件、第一刀、产物/判断和停止条件，再要求补实际题面核验。泛说不会或卡点互相竞争时先问具体卡点，不给几十个方法名，也不把默认定位入口冒充已适用。长句场景先展示句子处理动作，阶段/持续等其他已证分支留在完整卡；正式 Stop 不被删掉。G01 的产物是下一知识节点，不是答案候选或词形答案。

不加renderer仍返回原结构化列表，兼容已有调用。自然表达变体及有限的明确否定处理只影响低置信度建议，不改变课程判据，不认证实际触发或英语语义；题面观察仍由原核心独立核对。

Composer不再仅传“上一方法的输出”文本：method_chain公开角色产物类型和execution_ids，action_executions提交具体动作及类型化输出，execution_trace只将可用产物传递。未提交动作不伪造执行；副职责单列，停止产物不续用。八类结构化产物及职责/依赖/图绑定约束见method-execution.md。

Compact与full同卡。G01.full.decision_tree保留有无提示词、功能/词性、动词谓语/非谓语树，知识节点引用源章节。R09仅产对象+核心判断+全文任务骨架；首尾、段首与重复词是取证入口，不是机械三步。

grammar-tree.yaml只维护节点依赖与方法引用，不另写判据；可调用导航先核given_word是否明确标注，再以题面跨度和已审阅触发进入功能节点。提示词原词性不选叶节点；多条路径不自动裁决。G17用于先拆句，G18/G19用于整篇反查，均不代替本句证据。源快速口诀与全称清单的使用风险单独绑定原话，不擅自删改原课程。

应用文入口按任务覆盖→句子准确→表达优化调用。文体骨架仍为category，评分为internal_rule，课后对照/训练不冒充考场答案。15分评分的材料和书写边界直接绑定源章节；训练中110/120词的句式策略与评分字数限制的张力单独登记，不成为学生通用篇幅目标。

续写五步引用具体五个子章节，不只引用空标题；首句约束、人物矛盾、两段事件线、功能提纲、回填润色各留产物。十句五锚按功能映射学生自写部分，不抄首句正常，不因句数或独立升华句机械扣分。剧情四格只用一版定义，PTSD只作源别名；自然专项模板位置约束只用于对应版本和模板，不能抹去通用原文边界。评分仍是25分独立规范。

更新时先保存history/ID/VERSION.yaml，再修改Registry并增version、change_reason、affected_cases及索引，运行生成与测试，登记regression_result。初次迁移脚本默认拒绝覆盖2.0 Registry；--rebuild仅为显式重建。

```powershell
python -m scripts.generate_assets
python -m unittest discover -s tests -v
python -m answer_engine validate
python -m answer_engine case-coverage
```

Case唯一事实源是cases记录，registry.yaml为索引。真实完整题、短片段、源反例模式须区分；source_pattern_only/evidence_gap不计验证通过。困难题缺题面就留空。Anti-Rule唯一源为method-registry/anti-rules.yaml，导航为生成投影。

case-coverage逐方法审计canonical、counterexample、boundary、transfer、hard五类槽，未登记槽只输出缺口，不生成虚构Case。validate同时检查索引与方法槽完全对应、路径与case_id唯一，以及实际Case的方法、类型、题型、职责和输出与槽一致。已登记但证据不足与未登记分别统计；该审计只证明登记及记录的来源状态，不认证完整题、语义正确性或学生效果。核心方法/框架缺少类型时，最终案例齐全度维持PARTIAL。

所有项candidate+Useful，后者只指课程用途依据。自动检查不得升级validated/stable/Efficient/Signature；正式升级要有另存的课程与真人审阅释放记录，按协议人工确认。

人工释放记录现有可运行release-check/release-bindings，契约为method-release.json。release_reviews是Registry索引中的可选方法→批准文件映射，不复制教学判据；只有目标状态与卡片一致且绑定实际案例、冻结评估、当前回归和人工检查时，Registry才接受成熟/更高等级。该机制不自动改卡、认证身份或替代语义与统计审阅，详见evaluation.md；当前映射为空。
