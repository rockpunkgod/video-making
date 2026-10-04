# 真实验收运行

基线协议为根目录EVALUATION_PROTOCOL.md：传播→冻结→Practicality Gate→First-use→Blind与Baseline，第二阶段优先级更高。当前pending_real_participant_validation。

按schemas/evaluation-record.json制作JSON数组或JSONL。每条保留参与者、方法版本、题号、冻结题组、分配条件、评价者，以及实际动作/证据/刹车/学生复述/角色。phase为communication、first_use或blind；短版独立组或预先设计counterbalanced分配。不能把自动答案正确充当动作成功。

```powershell
python -m answer_engine evaluate evaluation/datasets/real-observations.pending.json
python -m answer_engine evaluate collected-observations.jsonl --plan frozen-plan.json
```

复制plan.example.json，在采集前按风险确定样本、边界、相对90s差值和效率效应并冻结。模板默认frozen_before_data_collection=false，不能发布。身份、时间、题组真实性、首次学习和分配须外部审计，工具不能靠勾选证明。

同题组Baseline/Method记录accuracy、秒数、剩余候选、证据句数、犹豫次数、未解率，单位不得变。First-use给示范后在第二道陌生题观察，不测试猜中答案。五类题组覆盖正/负触发、反例、边界、迁移；接口一个主case_type，重复试次拒绝。统计以观察试次为单位，题组覆盖按question_id，结果保留分子分母/record_id，缺样本null而非100%。

输出触发精确/召回、Resolution、Standalone、Assist、False Trigger、Transfer、Boundary、Role Overclaim、Stop Failure及Baseline差值。Transfer测动作和证据迁移，不逼reducer独立定案；Boundary必须实际识别、停止、证据成立、无越权且边界结论正确。accuracy差值为Method−Baseline，其余为Baseline−Method。

Synthetic仅为程序记录，不造真实考试或受试者，永不发布升级；其100%等数值不可引用为方法效果。real.pending为空。均值改善最多产审阅候选，不能证明显著性；最终由研究者按冻结计划审核不确定性和风险。工具不自动更改Registry。
