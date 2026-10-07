# Cognitive Direction v0.2：第一视角认知导演

本层把当前 Method Choreography 0.1 导演成连续的注意力、镜头、构图与信息空间计划。母方向仍为 **Swiss Cognitive POV**，现有原生 Cognitive POV 0.1、Motion Identity 0.1、Semantic Text Layout、AE 与 Premiere 消费链不变。新接口显式使用，不接管旧工程或生产索引。

```text
Frozen Truth → Pedagogy 0.4 → Student POV Experience 0.4
  → Method Choreography 0.1 → Cognitive Direction 0.2
  → 后续 Layout / AE 执行适配 → Premiere
```

**Motion may be spatial and dynamic. Settle must be Swiss.** 未解决时允许搜索、深度、抽离、重排与关系变化；当前有据结果落下时，形成共享对齐、明确层级、单一逻辑焦点和稳定阅读帧。程序只能检查计划义务，不能认证实际画面可读性、Swiss 气质或学生理解。

## 输入、门禁与兼容

`compile_direction` 先调用现有 `validate_choreography`，连同 Experience、Plan、Copy/Motion Handoff、Frozen Bundle、当前 Status 和已使用的 application 一起重新核验。它不读教学 Markdown、原始题库或 Registry 补事实，不解析英语，不重做 Selective Disclosure，也不重写 Frozen Copy。

Binding 保存原编舞全部绑定，加上 choreography SHA / contract、Student script SHA、Direction policy / schema SHA 和旧 Cognitive POV 0.1 文件 SHA。对象、场景顺序、文案、来源、权限或上游状态变化均需重新生成；重新 seal 不能使修改合法。沿用 Canonical JSON，数组保序、missing≠null，生成时间与语义 SHA 分开，文件路径不进入本层绑定。

READY 编舞可产生供后续规划消费的 READY Direction；这仍不是 AE 可执行或公开可用。上游 HOLD 默认拒绝；`diagnostic=True` 明确生成诊断计划，production_eligible / consumption_allowed 为 false，不继承旧 Copy 或旧视频的批准。`inspect_direction` 只检查历史完整性，缺当前源不能放行。

当前真实 R02 与 G01 均沿用 0.4 输入，最终体验文案缺新审核凭证，因此只做诊断回放。G01 的上游 Payoff / Baseline 缺口继续传递。旧 Copy 0.3 与 Cognitive POV 0.1 入口没有修改，不能通过换标签把旧材料变成当前 0.4 输入。

## State 与认知来源

支持词汇 REALITY / FULL_SCOPE / SEARCH / SUSPECT / ANCHOR / FOCUS / ISOLATE / STRUCTURE / COMPARE / TRANSFORM / REDUCE / UNRESOLVED / RESOLUTION / PAYOFF / STOP / MEMORY。它们是有限标签，不是需要凑齐的剧情。

每个 Direction state 一对一复用编舞 state_id，绑定原 state 的 pointer/hash；存在对应 Experience Beat 时另保存该 Beat 引用。不存在的 Search、Suspect、Interrupt 或 Payoff 不会为了画面丰富被插入。

State 保存 cognitive function、Reality scope、active/focus/background/unresolved/resolved/carry objects、抽象 camera scope、语义层、构图、能量和稳定阅读义务。RESOLUTION 只表示当前产物与局部 scope；它不是 Final Answer。真实 R02 没有完整 Jump Reading 搜索轨迹，所以没有假装“可疑位置减速、继续寻找”的经历。

## Attention Camera 与 Shot

Camera represents learner attention。只有当前范围、逻辑焦点对象或已有结构关系的可读性变化，才允许移动。wide / medium / close / focus 是认知景别，不包含缩放百分比、像素、Z 或轨迹。

策略为 hold / push / reframe / traverse / snap_to_anchor / depth_focus / spatial_carry。每个移动绑定原 operation 和 state transition 的 pointer/hash，记录原因与注意对象；固定 Camera 不能暗改景别。Stop 的相机稳定，Memory 只回到已有第一动作对象。

Shot 是一次注意力经历，可以包含多个 state 和 operation。默认连续变换；需要 Cut 时必须有 cognitive scope jump、major object ownership change、major time compression、comparison mode change 或 payoff punctuation 的来源。当前 R02 只在受支持局部 Collapse 使用 Logic Match Cut，前后保留原选项对象作为接力锚点；其余变换保持连续。G01 和合成 Peel 不靠逐页 Cut 串联。

Jump Reading 的 scan / jump / anchor / lock 映射到遍历、注意速度变化、吸附与范围锁定；本轮只消费已有操作，不自动推导命中位置或增加未命中状态。完整真实搜索轨迹仍需要上游供给。

## Continuous Reality 与 Logical Carry

原 passage / stem / options / blank / Evidence 不被新 Diagram 替换。原题 stem 保存 `upper_anchor_objects` 的持续上方锚点意图，具体位置由后续执行层计算。所有状态和 Shot 都保留同一个 Reality Layer。

visual_object_id 由原 object_id / origin_object_id / content SHA 稳定生成，在所有状态和 Shot 中复用。`visual_lineage` 将上游 `object_lineage` 转为同一对象的 plane / disposition / content SHA 遇见记录；Logic Match Cut 保存相同 continuity object 和 visual ID。不存在“每场重新做一份长得一样的文字”。

对象 catalog 使用来源引用，不复制教学文本。原题与允许的 Evidence 可以逐字显示；工作、候选资格、产物等后台对象仅提供非文本结构意图，`display_policy=structural_only_no_new_text` 不授权读出后台字段。教学文字、Memory 与方法名始终来自上游允许的 Copy/Experience 引用。

## 2.5D、可逆空间与 Focus

| Plane | 意义 |
|---|---|
| foreground | 当前必须处理的逻辑主体或同一组对象 |
| reading_plane | 当前可读的原题空间 |
| supporting_plane | 相关 Evidence、产物、未决对象及受审失效记录 |
| background_plane | 上游允许暂时不看的对象 |
| latent_plane | 可逆 deferred，保留同一对象与恢复路径 |

Protected 不能退到 background / latent 或消失。Unresolved 保持可读、中性开放，不能获得 winner spotlight。已受审的 D 资格退出活动集合，原 options 文本仍存在；这两者不是删除同一对象。

Deferred 使用 suspend / push back / fold 的可恢复意图，绝不 hard delete。`restore_paths` 保存原视觉 ID、content SHA、latent→reading 的恢复意图和已有 restore operation；尚未执行时明确 available_not_executed，不能伪造恢复事件。

Focus 通过相对对比、留白、语义深度和运动停止形成认知主导对象；不把画框、荧光笔当默认焦点机制。剩余 A/B/C 可以成为一个逻辑候选组焦点，不能挑一项暗示获胜。语义深度是信息层级，不是 3D 特效；本层没有 orbit、旋转、fly-through 或不可读透视参数。

## Physics、构图后果与 Swiss Settle

六个 family 的全部已注册 verb 都有视觉意图映射：Navigation 导演注意力路径；Reduction 导演层分离与收紧；Comparison 导演同坐标对齐与差异隔离；Relationship 导演原题中显现的关系变化；Classification 导演已有分组；Routing 导演原空位、已有路径和边界。这个映射不扩大上游真实 runtime 或新增教学方法。

构图 character 为 dense / searching / focused / split / aligned / isolated / compressed / resolved / sealed。它们不是固定版式。subject、原结构 groups、活动候选组、latent objects、reading axis、density 与 negative space 随有据动作改变；允许 controlled asymmetry，不强制所有状态居中。

Significant Action 必须产生真正的构图变化。R02 Collapse 的主体从关系比较切为三项开放候选组，reading axis 和 negative space 同时改变，并进入稳定阅读。不能仅降低其它文字透明度、换阶段标签或减少后台数字。

Peel 的外围层分离到 latent，core 依上游给定对象收紧，再 reframe；Align/Overlay 在同一来源坐标中加入候选，而不是固定双栏；Rewire 必须从原题已有关系断言或合法端点长出来；Compression 只能保留上游供给的结构对象，不能让 Director 总结正文。

当前 R02 关系只有断言级绑定，没有 actor/action/object 跨度几何。`layout_capability_gap=RELATION_ENDPOINT_SPANS_UNAVAILABLE` 明确禁止 actor endpoint graph；当前只导演受审断言与原 Evidence 的比较分组。这不妨碍本轮粗粒度计划，但不能宣称已完成逐词关系改线。

## 能量、Accent 与阅读节奏

Visual energy 为 low / medium / high，每项有驱动与来源引用。当前规则保守：题面、注意力和一般动作 medium；有据关系揭示或局部 Collapse high；Stop/Memory low。G01 没有 Payoff，不产生 high 或 Collapse accent；合成收紧也不被包装成认知收益高潮。

Accent 只绑定已有 relation reveal 或受支持 Collapse，最多一个同时出现；semantic depth intent 最多两个，结构动作需来源而不受装饰配额限制。保留原 Brand Grammar 六个 ID 和 SHA，不复制原文件中的 AE 参数或音乐规则。

节奏为 MOVE / SETTLE / READ / TRANSFORM / HOLD。Evidence lock、关系结果、候选缩减、当前产物、Stop、Memory 都留稳定帧义务：共享对齐、唯一逻辑焦点、停止运动与可读结构。`pause_frame_required=true` 是需要执行验证的计划，不是已经测过学生阅读时间。

真实计划只保存语义顺序，duration 为 null，不修改声音或复用旧时间线。Synthetic Peel 单独使用 20–40 秒的测试窗口（默认 30 秒），验证曲线不平、也不强加 high；它没有绝对时间、帧或已渲染时长，不成为真实英语样片。

## Stop、Memory 与风险检查

Stop 同步稳定 Camera、背景和当前路径，增加留白，保留 unresolved / deferred 与原必要边界 coverage。它不输出新的提醒墙、结果警告或 Final Answer glow。具体口播、音乐 Duck 和声音表演不在本层。

Memory Closure 只回收上游 remembered objects / action pattern / first action / memory phrase。没有上游的 WHO→ACTION→OBJECT 文字或细粒度端点时不自行补。Method Stamp 在核心动作之后以小型 editorial metadata 出现，内部方法编号不展示，不做 Logo Reveal。

Audit 能检测 whole-screen reset、detached infographic、未授权镜头运动、破坏 lineage/可逆性、假 Payoff、未决答案式处理、无构图后果和能量漂移。PPT_RISK_01–10 覆盖逐页标题、reset、panel、扁平空间、只有 entrance、Step 编号、字面 VO/Screen 重复、断接力、恒定景别与密度。

DEMO_RISK_01–05/07 可标记无认知原因的 3D/Camera、orbit、旋转、具体 blur/displacement、过早 accent、无据 Cut。DEMO_RISK_06（特效抢注意）、真正语义重复、第一视角、Swiss 气质、Pause-frame Value 和认知释放必须真人看画面后判断，全部 PENDING。结构 lint 不冒充审美或教学效果认证。

## API、CLI 与停止点

```python
from creative_os.cognitive_direction import compile_direction, project_direction

direction = compile_direction(choreography, experience, plan, copy_handoff,
                              motion_handoff, bundle, status, application=application)
projection = project_direction(direction, choreography, experience, plan,
                               copy_handoff, motion_handoff, bundle, status,
                               application=application)
```

`python -m creative_os.cognitive_direction compile|validate|inspect|project <request.json>`。请求显式列 choreography、experience、plan、两份 handoff、bundle、status，可选 application / diagnostic。Validate/Project/Inspect 列 direction；写入命令列唯一 output。路径相对 request 文件，未知字段和覆盖历史输出均拒绝。

合成通道为 compile-synthetic / validate-synthetic / project-synthetic，请求列 choreography / fixture，可选 restore / test_window_seconds；它先重新校验上一层合成编舞，不接受真实材料冒充 fixture。

正式 Schema 位于 `creative/schemas/cognitive-direction.v0.2.json`，包含 Direction 与 Projection 两个封闭契约。Projection 内含已绑定 Direction Plan，所有实时核验继续执行。它始终 `execution_allowed=false`，不是旧 AE Rig 可直接执行的合同；后续适配要处理 glyph geometry 与执行参数。本轮没有改 Text Layout，没有 AE / TTS 调用、AEP、视频、声音、音乐或批量生产。

真实回放位于忽略的 `local-data/cognitive-direction/v02-r2/`，旧编舞、Copy、声音和索引均保留。工程结果与限制见 [验收报告](../COGNITIVE_DIRECTION_V02_ACCEPTANCE.md)。本轮到 Direction / Shot / Camera / Spatial / Visual Intent 停止。
