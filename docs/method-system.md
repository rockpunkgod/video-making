# 方法系统与维护

Registry索引六题型方法文件。method_type区分框架、方法、子动作、内部规则、分类与复核；primary_role只有一个，secondary_roles显式登记。source_name/source_alias保留原名；W03学生主名为剧情四格，PTSD只作源别名。

82项不等于82个品牌：包括定位子动作、语法节点、训练框架与评分规则。阅读17项及F01/G01共19项有独立首次接触稿，其余63项仍为结构迁移、完整源章节与动作草稿，student_ready=false。student_ready=true只证明入口静态齐备，并不证明First-use、传播或迁移效果；所有方法仍为Useful+candidate。阅读13个非黄金修订以source_bound_editorial_review记录源绑定，真实案例和受试验证仍缺。

职责：locator→locate、interpreter/framework→interpret（G01路线为reduce）、reducer→reduce、decider→decide、verifier→verify。C01框架与decider为同一课程方法两种显式阶段，首次接触只突出主要职责；F01无decider副职责。

Compact与full同卡。G01.full.decision_tree保留有无提示词、功能/词性、动词谓语/非谓语树，知识节点引用源章节。R09仅产对象+核心判断+全文任务骨架；首尾、段首与重复词是取证入口，不是机械三步。

更新时先保存history/ID/VERSION.yaml，再修改Registry并增version、change_reason、affected_cases及索引，运行生成与测试，登记regression_result。初次迁移脚本默认拒绝覆盖2.0 Registry；--rebuild仅为显式重建。

```powershell
python -m scripts.generate_assets
python -m unittest discover -s tests -v
python -m answer_engine validate
```

Case唯一事实源是cases记录，registry.yaml为索引。真实完整题、短片段、源反例模式须区分；source_pattern_only/evidence_gap不计验证通过。困难题缺题面就留空。Anti-Rule唯一源为method-registry/anti-rules.yaml，导航为生成投影。

所有项candidate+Useful，后者只指课程用途依据。自动检查不得升级validated/stable/Efficient/Signature；正式升级要有另存的课程与真人审阅释放记录，按协议人工确认。
