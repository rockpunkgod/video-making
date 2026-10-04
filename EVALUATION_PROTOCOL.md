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

`candidate` 可以保留待测项；进入 `validated` 或 `stable` 前，下列七项必须同时有题面证据和实测结果。

1. Trigger：学生只看题面就能识别可能适用，不需要先知道答案。
2. Action：指令必须落到圈、划、拆、比、回填或分组等动作；注意逻辑、结合上下文等不能单独通过。
3. Output：必须标成 `locate`、`interpret`、`reduce`、`decide` 或 `verify`，且与实际产物一致。
4. Stop：必须有可观察的停止条件，不允许强套。
5. Transfer：更换题材、文章或选项后，核心动作仍成立。
6. Efficiency：记录减少的阅读范围、候选数、判断步骤、犹豫或认知负担；无提速时说清它改善的正确性或结构理解。
7. Misuse Cost：误触发导致错答的风险越高，Trigger 越需精确，Stop Rule 越需前置。

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
  notes:
```

学生只记得品牌名，但无法完成第一刀动作，立即判为不通过。

## Blind Evaluation

测试集必须同时包含正触发、近似但不适用的反例、边界和换题材迁移。在冻结答案与标注前不向受试者暴露答案。

每个方法至少记录：

- Trigger Precision = 真正适用的已触发题 / 全部已触发题。
- Trigger Recall = 被正确触发的适用题 / 全部适用题。
- Resolution Rate = 触发后真正解决候选差异的比例。
- Standalone Rate = 方法单独完成定案的比例。
- Assist Rate = 方法只完成定位、解释、缩减或验证的比例。
- False Trigger Rate = 误触发题 / 全部不适用题。
- Transfer Rate = 换题材后成功完成核心动作的比例。
- Time / Complexity Gain = 与 Baseline 比较的时间、候选、证据跨度、犹豫和未解率差值。

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
- `Signature`：在 Efficient 基础上，Trigger、Action、Transfer、Stop、视觉式、记忆和学生口语化全部通过。

本轮六个方法暂为 `Useful + candidate`。这不是对方法价值的贬低，而是对尚未运行真实学生盲测的诚实记录。
