# 真实验收运行

基线协议为根目录EVALUATION_PROTOCOL.md：传播→冻结→Practicality Gate→First-use→Blind与Baseline，第二阶段优先级更高。当前pending_real_participant_validation。

## 新版学生入口与真实首用材料

`python -m scripts.audit_student_entries` 读取当前来源版本、逐方法四步卡及独立学生稿，输出结构缺口。它不自动批准语义一致性、短版时长或真实学生成功；历史报告中的入口数量不能覆盖本版检查。

首用材料准备入口：

```powershell
python -m scripts.prepare_first_use_materials --method F01 --demonstration DEMO.json --transfer TRANSFER.json --walkthrough WALKTHROUGH.json --output local-data/STUDY-DRAFT
```

DEMO 和 TRANSFER 是已有完整原题的结构化文件（可有顶层 question）。只提取原题字段，不复制答案、历史关系、分组结果或评分。第二题须是不同题号、不同材料和不同文章；参与者是否曾见过仍须现场确认。WALKTHROUGH 显式绑定当前 method_id、method_version、source_commit、示范 question_id 及 `demonstration_question_sha256`，提供 first_action、evidence、output、stop，并声明 `review_scope=ai_authored_draft_not_learner_validation`。题面指纹由 `scripts.prepare_first_use_materials.question_fingerprint(read_question(path)[0])` 计算，题号不变但原文或选项变化也必须重新审查示范。

若原题在已有整卷冻结文件的 `inputs.questions` 中，可加 `--demonstration-id 原题ID` 和/或 `--transfer-id 原题ID` 精确取题。工具不改原文件、不重建题号，也不从 predictions 读取答案；题号缺失或重复就停止。示范指纹用 `read_question(path, 原题ID)` 计算，复核时同时绑定整卷文件哈希、选中的原题 ID 与原题字段指纹。

输出仅写入私有 local-data，拒绝覆盖既有材料。student-material.md 只展示方法名、症状、四步卡、示范和无提示的第二题；facilitator.json 单独保留来源文件哈希、前置研究门槛和全 null 的观察槽。材料草稿不授权采集，先完成示范及评分依据的独立审查、传播验收、版本冻结和 Practicality Gate，再进入 First-use。导出不登记新 Case，不重计 Blind，不导入或编造参与者结果。

七选五须有完整 A–G，阅读须有完整 A–D；缺项、空项或非文字原文不导出，不自动补题。第二题使用 Registry 当前 Challenge，检测具体动作而非直接猜答案。原选项自带字母时不重复加字母；这些检查不证明文章未缺段或英语语义正确。

G01 保留仓库题面中的 `given_word`，兼容旧 `hint_word`，两字段冲突就停止。无提示词须有显式 null 或空值，不能将字段丢失当作无提示词。学生材料展示当前 Registry 的决策树；到知识节点即停，不将路由当答案。树的同版本变化也会使旧材料指纹失效。

```powershell
python -m scripts.prepare_first_use_materials --verify local-data/STUDY-DRAFT
```

复核学生文件哈希、原题与示范文件哈希、题面指纹及当前教学卡指纹。同版本卡片的四步动作变化也会使旧材料失效。检查只证明数据一致性，不认证来源真实性、教学效力或研究许可；材料草稿不能夹带伪造的 First-use 观察。旧材料版本保留，重新生成须用新目录。

当前材料绑定范围为 `first_use_card_and_challenge_v2`，包含 Challenge；不能仅凭同版本四步卡未变继续使用旧练习任务。旧范围缺此绑定时须重新导出。`python -m scripts.refresh_first_use_drafts --index local-data/STUDY/CURRENT_DRAFTS.json --suffix REVISION` 可批量重导未采集草稿，并输出新的索引供明确选择；不会改旧稿。已有观察值、已批准采集、来源文件变化或方法版本变化均拒绝刷新，不能把真实旧观察迁成新结果。

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

Evaluation Result契约1.2.0按方法、版本、dataset_id与communication_freeze_id隔离组，每组design_audit返回检查、阻断原因与record_id，不从其他题组借前置记录。所有均值仍只描述输入记录。Resolution/Standalone/Assist要求动作和证据成立且无倒贴、越权或执行中断；猜中答案仍可计入原accuracy，但不充当方法成功。

采集前另冻结blind_acceptance.minimums的trigger_precision、trigger_recall、action_success、evidence_success、transfer_rate，以及.maximums的false_trigger_rate、stop_rule_failure_rate。五项最低成功值为(0,1]、两项最大失败容忍为[0,1)，示例阈值按风险修订而不是通用标准。不能补填在已采集计划上；缺此项的旧计划仍可做描述性统计，但不授权发布或效率/Signature审阅。

blind_acceptance_audit逐时长检查绝对可用性、Boundary、角色、参与者/题组覆盖及独立Baseline正确性不下降。动作/证据分母覆盖所有适用试次（漏触发也算失败），保留分子、分母、record_id和逐版效率对照。参照90s不达标，即使短版相对差值不坏也不能释放；某版正确率降低，不由其他时长的提高抵消。传播10/30/90的记忆与复述也逐版检查，不能借均值补证明。

短版增加action_failure_rate与evidence_failure_rate。对90秒版的max_action_failure_delta、max_evidence_failure_delta须采集前按风险冻结，缺省时安全为untested。最低参与者须为整数，效率阈值须为有限正效应，不能用负数、布尔或NaN把零改善包装成改进。任何阶段、角色、题组或材料链缺口同时阻断效率审阅与Signature建议，而非只挡发布。

Synthetic仅为程序记录，不造真实考试或受试者，永不发布升级；其100%等数值不可引用为方法效果。real.pending为空。均值改善最多产审阅候选，不能证明显著性；最终由研究者按冻结计划审核不确定性和风险。工具不自动更改Registry。

## 人工释放凭证

成熟度与实用等级仍是两个字段，当前均为candidate+Useful。`schemas/method-release.json`定义单独的外部人工批准记录；`evaluation/release-review.example.json`默认approved=false、检查全false、绑定null，没有真实批准。

先完成真实案例/版本修订、数据、冻结计划与课程审阅，在candidate状态运行完整验收。工程报告绑定代码、测试、Schema、协议、语义Registry与案例快照，并核对测试前后材料未变。然后复制未批准模板，填写实际输入文件、目标状态与等级，用release-bindings取当前材料指纹；方法指纹只排除四个状态/等级别名，不能借此改Trigger、Action、Stop、版本或其他教学事实。实际批准须由具名审阅者填写时间、材料引用与检查结论，再运行release-check。两命令只读；生成指纹或均值审阅建议均不构成批准。

```powershell
python -m answer_engine release-bindings evaluation/ACTUAL-REVIEW.json
python -m answer_engine release-check evaluation/ACTUAL-REVIEW.json
```

凭证的inputs分别指向原始JSON/JSONL观察、冻结计划和完整工程回归报告，须是仓库内相对文件路径。检查器重新计算原始评估，不信任粘贴的safe_for_release=true；案例五槽必须有verified_course_example与题面，人工另核合法来源和语义。主职责与产物类型由机器另行核对，人工勾选不能覆盖类型错配。批准时间须晚于相同方法/版本/题组/冻结稿的观察。缺链、旧指纹、synthetic、未批准、少案例、旧回归或错目标均阻断。当前没有真实批准，不能沿用程序测试中的临时元数据标记。

stable还需同版本、较早的validated批准记录（validated_review），本题组至少两道不同迁移题号及人工多题材审阅；不同题号不自动证明不同题材。Efficient另需评估的效率审阅候选与人工统计显著性核查。Signature再核品牌类型、视觉公式、记忆/口语和短版安全。身份、采集真实性、来源合法性、英语语义、题材差异与统计显著性始终由外部审阅者负责，程序不认证这些事实。

只有真实批准后，维护者才手动更改Method Card及其别名/索引、重新生成投影，在registry.yaml的可选release_reviews中登记`method_id: 实际批准文件路径`。Registry.validate要求批准对象、目标状态和等级与当前卡一致，并重新核材料；数据、规则或代码改变后旧批准失效，需先回到待审状态并重新回归/审批。没有任何自动写卡或自动升级命令。实际版本/案例改动还须维护相应真实回归夹具，不能删失败测试来放行。
