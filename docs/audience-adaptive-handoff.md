# Audience → Adaptive v0.1：B06 最小交接与执行规格

基线：`main@3f30b668496ce8fe6d08906daab0305cecd0d889`。
当前交付是**可执行的计划交接校验及预览取样消费**，不是新的运动生成器。
私有 B06 输入和 Adobe 宿主在本环境不可用：`LOCAL_PRODUCTION_EVIDENCE_UNAVAILABLE`。
不重跑 B06 prepare/G0，不改 r2/r3 历史项目、教学资产或已有审批。

## 接口与实际消费者

`ae_production.audience_adapter.compile_adapter(plan, episode, statuses,
audience_direction, native_direction, beat_scenes, spec, bindings,
transitions=(), voices=()) -> report`

- 先调用现有 `bind_existing_scenes()` 做独立场景投影，再调用真正的
  `director_handoff()` 重验完整 Episode、Audience 及全 Beat 交接。
- 重用 `audit_candidate_events()` 核对**全动作前缀**及已有答案闭合。
  选定场景只附加当前对象/时窗约束；未选 Beat 保留建议状态。
- `bindings` 每行只有以下字段，时间均为整个 Native Spec 的计划秒数：

| 字段 | 内容 |
|---|---|
| question_id / beat_id / scene_id | 当前题、既有 Beat、既有唯一场景，必须在全 Beat 映射中 |
| object_ids | 已存在的来源对象，具有同 Beat 来源且覆盖注意和阅读全窗口 |
| attention_range | `[start,end]`，在场景内先定向；不代表测得注意力 |
| reading_range | `[start,end]`，比较事件中必须位于 compare_start 至 decision_start 内 |
| candidate_event_id | `spec.events[].scene_id`；非候选场景可为 null，候选场景不能省略 |

`transitions` 每行只有 `from_question_id, to_question_id, payoff_beat_id,
obstacle_beat_id, gain_beat_id`。前后题必须相邻；上一题必须是既有 payoff，
下一题须声明非 none 的 novelty，gain 必须在 obstacle 之后且有 fresh_information。
对应计划镜头也必须按收益→新困难→新信息排列。文案投影来自已经校验的 Viewer State，
这里不生成题目、新承诺或英语语义。字段检查不能证明编辑声明真实或有吸引力。

输出包含逐场景任务、悬问、下轮信息收益、原生对象、注意/阅读/动作/确认窗口、
候选前后状态、事件 SHA、取样时点、未选交接行和递进记录。
`spec_sha`、完整 Status、voices、bindings、transitions 和重建的 handoff 都被绑定。
函数不修改任何输入、不移动任何关键帧、不缩放任何声音、不自动延长时长。

### 新 revision 接入

在新的私有 `native-request.json` 中显式添加 `audience_adapter` 对象，其七个键
`plan, audience_direction, native_direction, beat_scenes, bindings, transitions,
compiled` 的值均为绝对 JSON 路径；无递进时 transitions 文件写 `[]`。
所有七个路径及其当前**文件字节 SHA-256**必须进入现有 `input_files`。
其中 native_direction 是作者版本，投影由接口重建，不要传上次投影冒充作者输入。

编译阶段使用当前 Episode/Status 和已经按完整声音实测排好的 Spec：

```python
from ae_production.audience_adapter import compile_adapter
from video_contracts import read, write
r = read(request_path)
c = r['audience_adapter']
episode = read(r['episode_plan'])
statuses = {key: read(path) for key, path in r['statuses'].items()}
report = compile_adapter(read(c['plan']), episode, statuses,
    read(c['audience_direction']), read(c['native_direction']),
    read(c['beat_scenes']), r['spec'], read(c['bindings']),
    read(c['transitions']), r['voices'])
# compiled 必须是新的 revision 路径；保留既有产物。
write(c['compiled'], report)
# 作者随后更新 input_files，绑定上述七份文件的实际字节 SHA。
```

```powershell
python ae/experiments/adaptive-episode/run.py audience_preflight local-data/<new-revision>
```

该命令不访问 Adobe，写入计划校验快照 `AUDIENCE_ADAPTIVE_PREFLIGHT.json`。
`current()` 在 build/audit/preview/render/package 每次入口重新编译并与 compiled
逐字段比较；改 Status、Spec、输入文件或伪造 PASS 均不能复用旧结果。
`preview()` 对启用适配的 revision 消费报告中的阅读起点/中点、决策点和确认点；
使用既有分页预览接口。超过 32 个时点时必须收窄本次试验范围，不能抽样后声称全检。
无 `audience_adapter` 的旧请求继续走原有路径，不增加全仓迁移门槛。

**宿主执行仍按当前入口权限：**旧 adaptive 写入口尚未接入逐次 HostOwnership，
不能因为新 preflight 通过就用于真实新写操作。B06 后续原生制作继续交给已受保护的
`r06-b06-judgement` 唯一执行者。本次没有修改或接通该限定制作器的 `PRODUCTION.json`
接口；作者将报告作为受版本绑定的制作交接，若要在它上面自动消费须另做明确适配。
不要复制旧 AEP/PR 收据给新 Native Spec。既有 build/audit/帧收据与 PR 审计仍须完成。

## B06：从观看任务到具体镜头事件

依据当前工作流与 `R06_B06_JUDGEMENT_ACCEPTANCE.md`：B06 只排除 B，
B/C/D → C/D；B07 保留 C 仍是 C/D。本轮测试使用程序合成题复现该形状，
不是读取真实 B06、再次上游审阅或重新运行 r3。

| 观看阶段 | 当前任务、悬问与下一步回报 | 对应既有 Native Spec / 检查点 |
|---|---|---|
| B05→B06 定向 | 只比较 B 的主张与已经找到的正文；“它们在讨论同一件事吗？” | 既有全 Beat→Scene 映射找到 B06 所属题/Beat；attention_range 绑定原位来源对象；不直接显示排除结果 |
| B06 比较 | 看清数量主张与问题/回应关系；回报是把判断缩到这组对象 | reading_range 在 compare_start 后、decision_start 前；对象必须先在场且留到阅读结束。细粒度词组操作仅用 r3 已有四项凭证，不由适配层切词 |
| B06 决策 | 已见依据后只排除 B | candidate_event_id=B06，动作时钟精确取 decision_start→decision_end；冻结 action/output 必须匹配 |
| B06 确认 | 当前只剩 C/D；“接下来还要分辨什么？” | confirmation_start 后落稳；报告保留 before/after，禁止升级为选 C 或全题闭合；镜头不可先于判断宣布收益 |
| B06→B07 接缝 | 带着 C/D 进入下一次不同的比较 | 保留 B07 原入口和完整声音；它是同题动作接力，不伪装成两道独立题间递进 |

不要把旧验收文件中的 [6905,7739) 等实际帧号直接填成新 spec 的秒数。
新 revision 从实际场景及事件读取时窗；如使用局部时间轴，必须先显式换算来源帧与零点。
实际导出后再以新原生回读、媒体 SHA、帧/样本映射核对；Audience Learning 的外部
人工锚点要求另行满足。报告中的计划秒数绝不转写为 actual_media。

### B06 下一轮原生操作规格（尚未执行）

1. 在已有有效交接上读取 PREPARATION_RECEIPT、PRODUCTION_INDEX、完整候选前缀、
   四项词组凭证/当前状态和既有 G2 收据，保留历史。缺失就记录缺失，不以样例补齐。
2. 为新 revision 编写 B06 binding：用实际对象 ID 和当前事件时刻；完整 Episode
   仍保留全 Beat 映射。重新实测完整 voice 放置后编译，不截断、拉伸或重复讲解凑时长。
3. 如果使用 read_hold/payoff_hold，阅读窗必须无 VO 重叠且相机/对象位置、缩放、
   不透明度关键段保持稳定。guided_inline 允许引导；不把它冒充静默观察。
   此检查不证明遮挡、焦点、景深、缓动或可读性，原生和实片仍需核验。
4. 唯一执行者在受保护 B06 入口新建派生工程；保留原题/认知空间的真实深度、
   连续镜头、透明原词提取、识别减速和命中落稳，不退回平面卡片讲解。
5. 取样阅读前/中、决策、确认帧，并连续看 B05→B06→B07；实际回读对象/相机/字形/
   关键帧，完整 4K24 帧序列与源指纹核验后交 PR；完整 PCM、字幕、音乐/SFX 在同一
   实测时钟上复核。保留当前声音模型与肖邦方向，试听、音乐权利仍分别待审。
6. 独立人工分别评价“看清比较对象了吗、为何排 B、还剩谁、接缝、声音是否自然”。
   G3 未通过只修 B06 和必要接缝；不把本次任务当作 G4 整期制作授权。

## 5–8 分钟主片的可复用递进

5–8 分钟是节目目标区间，不是程序时长门槛。2–3 道真实题组织同一方法；
每题必须兑现自己的实际收益，下一题把已掌握动作带到新困难中。
使用 `transitions` 投影以下结构，不增加固定过场、整题双遍或解释字数：

| 来源 | 编辑选择 | 接收者 |
|---|---|---|
| 上一题 supported payoff | 先让已兑现的结果可见，必要时停一拍 | 下一题既有 original_task / obstacle Beat |
| 下一题 novelty 与悬问 | 只引出本题新障碍：证据变了、条件增加或应用变化 | 该题后续有 fresh_information 的 Beat |
| 后续可验证的信息收益 | 用真实动作兑现承诺，再接下一个难点 | 自己的 payoff / 下一次相邻 transition |

容易识别的不一致选项快速带过；讲解和镜头资源优先给本方法真正起作用、学生易混淆
的比较。方法名简短承接已经可见的价值，避免再展开一串完整理论。
程序只保证来源、相邻顺序和兑现时序，编辑判断“新困难是否值得看”仍由作者和观众确认。

## 继承要求核对与证明范围

| 维度 | 本次如何继承 | 尚需的真实证据 |
|---|---|---|
| 视觉 | 不修改 spec；保留 3D、Reality/Cognitive Space、连续镜头、透明提取、橙/蓝注意色及轻微放大；quiet hold 只校验已有稳定关键段 | AE 深度、相机、焦点、运动模糊、无弹跳/划线、字形及实际帧 |
| 声音 | 不生成或修改 take；绑定声音清单及当前文件指纹；静默窗检查重叠 | 完整 voice-delivery、48kHz 位置、字幕、ducking、原生 PR 和最终试听 |
| 叙事 | 题目驱动、收益→新困难→新信息；方法名代替重复推理；只选有价值的局部慢看 | 连续观看确认参与感和观看动机，不能从代码 PASS 推断 |
| 教学 | 完整 Episode/Status/Review/Action/Stop/Role 由现有验证器重核；candidate_motion 保留候选状态，不补事实、不自主切词、无答案升级 | 真实现有凭证和当前状态；有缺口回 teaching_issue_candidate/上游 |
| 发布 | FREE_SHOWCASE，human PENDING，public false；不改 Paid/方法成熟度/来源权利 | 既有最终媒体与独立发布审核 |

计划镜头：PLANNED。代码交接：只有相同输入上实际通过测试/预检才 PASS。
本次 Adobe 原生执行：NOT_ASSESSED；实际媒体锚点 UNAVAILABLE；观感与听感 PENDING。
历史 r3 六份局部 A/B 的完成事实保持其原范围，不传递给本次适配 revision。
