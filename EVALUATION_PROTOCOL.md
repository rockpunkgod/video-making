# 方法传播与强可用性验收协议

验收执行顺序固定为：第一阶段传播效果验收，第二阶段强可用性验收。先确认学生看得懂、记得住、说得出来，再检验拿到陌生题能否独立完成动作与证据判断。

第二阶段的优先级高于第一阶段。正确性与课程证据边界贯穿两个阶段。传播通过只表示表达可以进入实战测试；最终发布等级由第二阶段决定。传播和实用发生冲突时，以第二阶段的强可用性验收为准，回改名称、口令、例子、视觉公式或短版表达；传播效果不能抵消实战误用或判断错误。

## 第一阶段：传播效果验收

逐个检查六个方法的学生首次接触版本，按 10 秒、30 秒、90 秒顺序呈现。首次呈现不给 Registry 或课程材料，也不给额外口头解释。

1. 看得懂：学生能说出内容针对什么卡点，以及第一眼看哪里。
2. 记得住：看完后遮住内容，能复述核心动作与刹车句；记录复述是否需要提示。
3. 说得出来：能用自然口语讲清方法，而不是只报品牌名或课程术语。
4. 看得见：能照视觉公式指出要拆、圈、比或分组的对象，以及方法产物。
5. 短长一致：10/30/90 秒三个版本的职责、判断标准与边界一致；记录实际口播时长，超时就压缩表达，不能删去改变结论的条件。

记录每项的通过/未通过、学生原话、需要的提示和具体误解。缺少真实受试者时只能给出文案审查意见，不能记录学生记忆或传播效果已经通过。真实视频数据可另记完播、收藏、分享与评论理解情况，不能用播放量代替上述学习指标。

传播未通过：修订症状入口、动作表述、例子或视觉公式，再重复第一阶段。传播通过：冻结该版本，进入第二阶段。

## 第二阶段：强可用性验收

按下文 Practicality Gate → First-use Test → Blind Evaluation 与 Baseline 对照推进。用冻结版本、示范题和第二道陌生题，检验触发、第一刀动作、决定性证据、Stop Rule、迁移与效率价值。

第二阶段未通过：记录具体失败动作，回改表达或方法边界；修订版本重新通过第一阶段后再测实战。两个阶段都通过，才按成熟度与实用价值门槛升级。

## Practicality Gate

`candidate` 可以保留待测项；进入 `validated` 或 `stable` 前，原有七项及新增 Method Role Correctness 必须同时有题面证据和实测结果。

1. Trigger：学生只看题面就能识别可能适用，不需要先知道答案。
2. Action：指令必须落到圈、划、拆、比、回填或分组等动作；注意逻辑、结合上下文等不能单独通过。
3. Output：必须标成 `locate`、`interpret`、`reduce`、`decide` 或 `verify`，且与实际产物一致。
4. Stop：必须有可观察的停止条件，不允许强套。
5. Transfer：更换题材、文章或选项后，核心动作仍成立。
6. Efficiency：记录减少的阅读范围、候选数、判断步骤、犹豫或认知负担；无提速时说清它改善的正确性或结构理解。
7. Misuse Cost：误触发导致错答的风险越高，Trigger 越需精确，Stop Rule 越需前置。

8. Method Role Correctness：逐一核对首次接触版、10/30/90 秒版、口令和方法卡所宣传的能力，是否与实际能完成的任务一致。locator 只找位置，interpreter 只解释关系，reducer 只缩小范围；verifier 负责核验已有候选或结论，不能宣称独立解题。不得将任何辅助产物包装成直接定案。

```yaml
role_correctness:
  declared_primary_role:
  observed_actual_role:
  role_match:
  overclaim_detected:
  notes:
```

`declared_primary_role` 与 `observed_actual_role` 使用 Method Card 的角色词汇；实际产物仍使用原有 Output 五类。framework 按其声明的唯一产物核对，例如 R09 产生全文骨架卡，不能宣传为直接选答案。`role_match = false` 或 `overclaim_detected = true` 时，该版本验收失败，不得进入 `validated` 或 `stable`；没有实际观察数据时保留 `null`，不能按未发现越界认定通过。

## First-use Test

对从未学过该方法的学生，只提供方法名、症状、四步实战卡和一道示范题；然后给第二道题材不同、结构同类的盲题。

记录：

```yaml
first_use_test:
  participant_id:
  method_id:
  second_item_id:
  trigger_success:
  action_success:
  evidence_success:
  stop_rule_success:
  no_answer_backfit:
  final_result:
  observed_first_action:
  failure_type: null
  notes:
```

学生只记得品牌名，但无法完成第一刀动作，立即判为不通过。

`failure_type` 使用列表记录，可同时标记多个失败；仅通过时填 `[]`，待测时填 `null`。未通过时必须至少标记一类，并在 `notes` 写出观察到的动作或学生原话，不能只记录通过/未通过。

| failure_type | 观察到的失败 | 优先回查位置 |
|---|---|---|
| missed_trigger | 实际适用却没有启动 | Trigger Cue、记忆入口 |
| false_trigger | 实际不适用却启动 | Trigger 范围、反例 |
| wrong_first_action | 想到方法但第一刀做错 | Action、视觉公式、示范题 |
| wrong_evidence | 动作正确却使用错误证据 | 证据位置与求证指引 |
| ignored_stop_rule | 已达停止条件仍继续强套 | Stop Rule 的强度、位置与记忆 |
| answer_backfit | 先猜答案再倒贴方法 | 测试过程、动作先后记录 |
| method_overreach | 让 locate / interpret / reduce / verify 承担独立 decide | 方法角色、传播承诺 |
| execution_breakdown | 知道规则却无法完成执行链，且不属于前述类别 | 执行链、例题或方法本身 |

上述回查方向是修订线索，不自动证明失败由文案造成；需结合记录判断该改方法名、Trigger、Action、视觉公式、Stop Rule、例题还是方法本身。

## Blind Evaluation

测试集必须明确标记并覆盖 `positive_trigger`、`negative_trigger`、`counterexample`、`boundary`、`transfer`，不能只有标准正例。类别可重叠，但统计时按独立题目去重。先冻结答案、适用性与边界标注，再执行盲测；测试期间不向受试者暴露答案。

每个方法至少记录：

- Trigger Precision = 真正适用的已触发题 / 全部已触发题。
- Trigger Recall = 被正确触发的适用题 / 全部适用题。
- Resolution Rate = 触发后真正解决候选差异的比例。
- Standalone Rate = 方法单独完成定案的比例。
- Assist Rate = 方法只完成定位、解释、缩减或验证的比例。
- False Trigger Rate = 误触发题 / 全部不适用题。
- Transfer Rate = 换题材后成功完成核心动作的比例。
- Time / Complexity Gain = 与 Baseline 比较的时间、候选、证据跨度、犹豫和未解率差值。
- Boundary Accuracy = 正确识别并停止的边界题 / 全部边界题。

边界题指表面符合方法，但完整边界要求不启动或停止使用的题。正确停止必须有边界识别和 Stop Rule 的证据，不能将碰巧没用方法计为成功。例如 R01 的新增内容虽无逐字对应，却有充分间接支持：学生指出支持链并停止按 R01 排除，才计为 Boundary Success；执行没原词→加戏→排除则失败。

```yaml
boundary_result:
  is_boundary_item:
  boundary_detected:
  stop_rule_applied:
  overreach:
  final_result:
```

Boundary Success 要求前三项为 `true`、`overreach = false`，且 `final_result` 记录为成功。不应启动的题，正确拒绝启动也属于 Stop Rule 生效。没有边界题时 Boundary Accuracy 为 `null`，不能填 100% 或认定达标。Boundary Accuracy 的通过门槛需在盲测前冻结，按方法误用成本设定并记录依据，不在看到结果后调整。

## Baseline 对照

同一组题随机或交叉分配两种条件：

- Baseline：逐项阅读+完整文本理解+常规排除。
- Method：只额外提供当前方法的首次接触版。

每题记录：

```yaml
item_result:
  condition: baseline | method
  accuracy:
  elapsed_seconds:
  candidates_before:
  candidates_after:
  evidence_span_sentences:
  hesitation_count:
  unresolved:
  trigger_decision:
  first_action:
  stop_rule_used:
```

结论只能说方法在哪些触发场景改善了正确率、速度、候选数、证据范围、犹豫或结构理解，不宣称永远更好。

## 实用价值升级

- `Useful`：课程证据支持它可解决真实问题；允许真实盲测待完成。
- `Efficient`：已通过 Blind Evaluation，且至少一个效率或认知负担指标显著改善，正确性不下降。
- `Signature`：Efficient + Trigger 通过 + Action 通过 + Transfer 通过 + Stop 通过 + Boundary Accuracy 达标 + Method Role Correctness 通过 + Visual Formula 通过 + 学生记忆与口语化通过 + Short-version Safety 通过。

### Short-version Safety Gate

10 秒版、30 秒版必须分别进入 Blind Evaluation，或至少接受专门的压缩安全测试，并与 90 秒完整版对照。三个版本使用同一方法版本和可比的冻结题组，覆盖负触发、反例与边界；采用独立受试组或平衡分配，控制先看其他版本、重复做题产生的学习效应。第一阶段的短到长展示是表达检查，不能直接当作这项安全对照结果。

逐版记录：

```yaml
short_version_safety:
  version: 10s | 30s | 90s
  false_trigger_rate:
  boundary_accuracy:
  role_overclaim_rate:
  stop_rule_failure_rate:
  safe_for_release:
```

同时按 First-use Test 的 `failure_type` 比较 `wrong_first_action`、`ignored_stop_rule`、`method_overreach` 的发生情况。`role_overclaim_rate` 记录受试者把辅助职责误当独立定案的比例，传播文案自身的越权承诺另由 Method Role Correctness 直接否决。`stop_rule_failure_rate` 以应刹车的题为分母。各比例须保留分子、分母与题目记录；没有样本或尚未测试时填 `null`。

测试前冻结短版相对完整版的可接受差值、Boundary Accuracy 门槛和样本方案，按误用成本说明依据。误触发明显上升、边界识别明显下降，或出现未解决的角色越权时，短版 `safe_for_release = false`，不得上线；证据不足或未测则保持 `null`，不视为通过。必须回改口令、Trigger Cue、Stop Rule、视觉公式、示例或视频文案，再按两阶段流程复测。

完整版正确不能替代短版安全证据。Signature 要求实际对外使用的 10/30 秒压缩版本均通过安全门槛；好记不能抵消 False Trigger、Method Overreach 或 Boundary Failure。

本轮六个方法暂为 `Useful + candidate`。这不是对方法价值的贬低，而是对尚未运行真实学生盲测的诚实记录。

## 可运行数据与工具入口

本协议仍是验收依据；实现入口为 `python -m answer_engine evaluate 观察记录.json --plan 冻结计划.json`。记录支持 JSON 数组或 JSONL，契约见 `schemas/evaluation-record.json`，结果见 `schemas/evaluation-result.json`。导入包含第一阶段 communication、第二阶段 first_use 与 blind 的实际观察，记录动作、证据、刹车与学生复述原话；不能把自动答案正确冒充这些过程成功。

统计按 method_id + method_version 分组，不混用版本，也不混用 real/synthetic。指标保留分子分母与 record_id。没有样本为 null；未形成可比冻结题组时短版 safe_for_release 为 untested。独立受试组或 counterbalanced 分配用于控制重复学习；同一受试者重复题面的未平衡记录不能进入短版发布推荐。

计划示例 `evaluation/plan.example.json` 默认未冻结，不能直接授予发布通过。采集前由研究者按风险设定样本量、边界门槛、短版允许差值与效率效应量，保存计划版本；工具不能认证提交者、采集时间或真人身份，这些必须由研究者外部审计。

均值改善只产生 review_for_Efficient / review_for_Signature 的人工审阅候选，不能证明统计显著性，不能自动升级 Registry。发布推荐还需真实数据、传播记忆与复述、First-use 无动作/证据/刹车/越权/倒贴失败，以及三个短版安全条件。工程回归不等于教学效果通过。
