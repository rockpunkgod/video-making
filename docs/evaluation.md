# 真实验收运行

基线协议为根目录EVALUATION_PROTOCOL.md：传播→冻结→Practicality Gate→First-use→Blind与Baseline，第二阶段优先级更高。当前pending_real_participant_validation。

按schemas/evaluation-record.json制作JSON数组或JSONL。每条保留参与者、方法版本、题号、冻结题组、分配条件、评价者，以及实际动作/证据/刹车/学生复述/角色。phase为communication、first_use或blind；短版独立组或预先设计counterbalanced分配。不能把自动答案正确充当动作成功。

```powershell
python -m answer_engine evaluate evaluation/datasets/real-observations.pending.json
python -m answer_engine evaluate collected-observations.jsonl --plan frozen-plan.json
```

复制plan.example.json，在采集前按风险确定样本、边界、相对90s差值和效率效应并冻结。模板默认frozen_before_data_collection=false，不能发布。身份、时间、题组真实性、首次学习和分配须外部审计，工具不能靠勾选证明。

计划示例的workflow默认全部未通过、时间及人员为待替换占位、记录ID为空，不会授权释放或等级审阅。完整artifact必须记录：study_frozen_at、communication_frozen_at、practicality_reviewed_at（均带时区），communication_record_ids（当前题组的实际传播观察ID），communication_checks五项、practicality_checks八项，demonstration_item_ids、reviewer和evidence_notes。检查项名称在evaluation/harness.py的COMMUNICATION_CHECKS与PRACTICALITY_CHECKS中固定；不能用空说明或整数1代替真实布尔与证据说明。旧计划允许缺workflow或使用null作描述性统计，不能作发布依据。

observed_at对旧统计输入仍可缺省，但完整研究链必须逐条提供。系统核所声明的参数冻结→传播观察/稿件冻结→Practicality→First-use→Blind时间顺序、示范/盲题独立性、跨阶段学习效应与当前Registry版本/角色；日期、身份、审阅结论和真实采集材料仍须独立人工审计。历史版本可以描述性统计，但不能用不匹配当前Registry的版本申请当前发布。

同题组Baseline/Method记录accuracy、秒数、剩余候选、证据句数、犹豫次数、未解率，单位不得变。First-use给示范后在第二道陌生题观察，不测试猜中答案。五类题组覆盖正/负触发、反例、边界、迁移；接口一个主case_type，重复试次拒绝。统计以观察试次为单位，题组覆盖按question_id，结果保留分子分母/record_id，缺样本null而非100%。

输出触发精确/召回、Resolution、Standalone、Assist、False Trigger、Transfer、Boundary、Role Overclaim、Stop Failure及Baseline差值。Transfer测动作和证据迁移，不逼reducer独立定案；Boundary必须实际识别、停止、证据成立、无越权且边界结论正确。accuracy差值为Method−Baseline，其余为Baseline−Method。

Evaluation Result契约1.1.0按方法、版本、dataset_id与communication_freeze_id隔离组，每组design_audit返回检查、阻断原因与record_id，不从其他题组借前置记录。所有均值仍只描述输入记录。Resolution/Standalone/Assist要求动作和证据成立且无倒贴、越权或执行中断；猜中答案仍可计入原accuracy，但不充当方法成功。

短版增加action_failure_rate与evidence_failure_rate。对90秒版的max_action_failure_delta、max_evidence_failure_delta须采集前按风险冻结，缺省时安全为untested。最低参与者须为整数，效率阈值须为有限正效应，不能用负数、布尔或NaN把零改善包装成改进。任何阶段、角色、题组或材料链缺口同时阻断效率审阅与Signature建议，而非只挡发布。

Synthetic仅为程序记录，不造真实考试或受试者，永不发布升级；其100%等数值不可引用为方法效果。real.pending为空。均值改善最多产审阅候选，不能证明显著性；最终由研究者按冻结计划审核不确定性和风险。工具不自动更改Registry。
