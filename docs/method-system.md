# 方法系统与维护

Registry索引六题型方法文件。method_type区分框架、方法、子动作、内部规则、分类与复核；primary_role只有一个，secondary_roles显式登记。source_name/source_alias保留原名；W03学生主名为剧情四格，PTSD只作源别名。

82项不等于82个品牌：包括定位子动作、语法节点、训练框架与评分规则。阅读17项、七选五11项、完形9项、语法19项、应用文10项及续写16项均有独立首次接触稿。student_ready=true只证明入口静态齐备，并不证明First-use、传播或迁移效果；所有方法仍为Useful+candidate。后续修订以source_bound_editorial_review记录源绑定，真实案例和受试验证仍缺。

职责：locator→locate、interpreter/framework→interpret（G01路线为reduce）、reducer→reduce、decider→decide、verifier→verify。C01框架与decider为同一课程方法两种显式阶段，首次接触只突出主要职责；F01无decider副职责。

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
```

Case唯一事实源是cases记录，registry.yaml为索引。真实完整题、短片段、源反例模式须区分；source_pattern_only/evidence_gap不计验证通过。困难题缺题面就留空。Anti-Rule唯一源为method-registry/anti-rules.yaml，导航为生成投影。

所有项candidate+Useful，后者只指课程用途依据。自动检查不得升级validated/stable/Efficient/Signature；正式升级要有另存的课程与真人审阅释放记录，按协议人工确认。
