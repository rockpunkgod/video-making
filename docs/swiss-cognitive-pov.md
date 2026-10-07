# Swiss Cognitive POV 0.1

本轮交付一个真实方法应用的 20 秒原生视觉试制。原题形成连续的阅读空间，
镜头随当前关注范围移动；已有动作允许暂缓的成分短暂退到后层，然后恢复。
英文原题、空位、方法角色、实际产物和 Stop 均来自冻结 ANSWER 资产。

这条视觉证明使用既有冻结 Copy 和 `worked_example` Plan；新增的 Student POV
Copy Layer 有独立的 Payoff 门禁。不能把视觉试片的工程成功解释为该层已经 READY。
教学压缩层见 [Pedagogy Compiler](pedagogy-compiler.md)。

## 职责

| 层 | 输入与职责 | 禁止 |
| --- | --- | --- |
| ANSWER 纯导出 | 已冻结题面、实际动作、明确跨度标注、当前状态与既有 Review | 解题、创建 Review、改变 Registry |
| Pedagogy Compiler | 完整 Truth 投影为 Plan，决定 Disclosure | 改答案、Role、Stop 或成熟度 |
| Student POV Copy | 消费批准的 Plan，提供学生执行语言 | 自定边界、编造省掉的工作 |
| Motion Director | 把已绑定的跨度和关系映射为确定性运动 | 用句法解析或模型补教学关系 |
| AE | 执行层、相机、字体、位置、透明度与模糊关键帧 | 决定语义、混最终声音 |
| Premiere | 连续 VO、钢琴、字幕、音量包络、最终导出 | 重写教学事实、自动公开发布 |

`Claim Guard`、跨度断言绑定与 Native Audit 都是机械核验，不能认证英语语义、
真实学生效果或审美。公开资格继续分别依赖教学、最终展示来源、最终编辑批准和有效上游。

## 冻结方法应用接口

新增命令，保留原单题、整卷和资产导出接口：

```powershell
python -m answer_engine export-method-application <request.json>
# 或者显式保存一个新的本地冻结文件；已有文件拒绝覆盖
python -m answer_engine.method_application_export <request.json>
```

请求显式指定 `bundle`、`status`、`annotation`；保存模式另指定 `output`。
只读接口在 Registry 实例化前分流，不调用 Analyzer。

`schemas/method-application-input.json` 定义源区间的完整、有序跨度划分、保留/暂缓/保护
跨度和关系。每个标签或关系必须引用本动作的已有 `concrete_action`、
`decision_rule_check` 或 `stop_rule_check` 中的原样断言。其作用是绑定，
不是对任意标签与断言之间的语义充分性做自动证明。

`schemas/frozen-method-application.json` 保存原题、当前 Method、实际 Action、
标注、Review 指纹、父资产、来源与三个 Hash。当前只支持已有 produced 的
framework / locator / interpreter；不由提示词推导词形，不把辅助动作升级为定案。
否定、条件、决定性 scope 和 comparison 不能退离当前焦点层。

所有 Hash 复用仓库 Canonical JSON：UTF-8，键排序，无无意义空白，缺失与 null 不同，
数组保序，拒绝 NaN。语义投影排除明确的诊断字段与时间；内容 Hash 排除传输元数据，
envelope Hash 包括生成时间。文件移动不改变内容语义；实际绑定内容变化必须重新导出。

## 连续空间与认知运动

六种 Physics 家族是可扩展词汇，不是六个自动语义求解器：

| 家族 | 操作 |
| --- | --- |
| Navigation | scan / jump / anchor / lock |
| Reduction | peel / mute / tighten / reveal / restore |
| Comparison | align / overlay / split / reveal_difference |
| Relationship | connect / detach / rewire / lock |
| Classification | float / attract / regroup / settle |
| Routing | extract / branch / route / seal |

本轮只实现 `object_slot_routing` Profile：完整原题 → 已绑定区域 → 空位结构 →
当前关系 → 既有名词节点 → 原区域和停止边界。暂缓成分保留原文、偏移和可逆轨迹。
不制造候选词形或答案。固定为一个光轴、零旋转、无景深的注意力相机；
z 轴表示阅读范围与注意力层次。相机行程与当前范围变化对应，不加入 Flash、Glitch 或 HUD。
消费者画面使用方法名，不显示 G01 等内部编号。

`creative_os.semantic_text_layout` 只测量字体与 Unicode 源偏移。
`creative_os.cognitive_pov` 可重复生成同一 Spec，并在执行前重新推导比较。
自己重新计算 Hash 不能使角色、文案、目标或运动篡改合法。

## 原生生产

```powershell
python -m ae_production.cognitive_execution build <ae-request.json>
python -m ae_production.cognitive_execution audit <ae-request.json>
python -m ae_production.cognitive_execution preview <ae-request.json>
python -m ae_production.cognitive_execution render <ae-request.json>
python -m scripts.generate_cognitive_voice <voice-request.json>
python -m premiere_production.cognitive <editorial-request.json>
```

AE 请求提供所有冻结输入、当前状态文件、Spec、唯一输出目录和新 AEP 路径。
使用官方 AE MCP 执行指南与确定性 JSX；实际字体、文字、层集合、变换、
透明度、模糊、画幅和相机关键帧都需原生回读。输出 480 张原生 TIFF 后仅压缩为
不含声音的 Motion Clip，保留 AEP/模板/帧/媒体指纹。

VO 使用已接受的本地参考，整段一次生成，记录文字与参考绑定。
这是声音连续性的工程处理；不宣称已获得人类声音一致性认证。

Premiere 使用安装的官方 MCP 工具导入并核验媒体路径、建立新序列、独立声音轨道
与字幕，再使用已回读的本机音量属性加入包络。口播恢复精确采样尾部，
不能让自动按视频帧取整悄悄截掉声音。最终导出前校验 Spec、Copy、当前状态、
READY worked_example Plan（若请求绑定）、AE 文件、声音、音乐、字幕、序列和包络。
任何不确定的修改先读实际状态；不盲重试。

可选 Plan 必须绑定同一冻结父资产、语义指纹、方法版本与实际动作，且全部 Tell Now 逐字存在于冻结 Screen 文本；这是本视觉通道当前支持的结构要求，不认证实际阅读效果或自然措辞。旧0.1 Plan 不能继续当前消费，旧20秒样片也未显示新0.2 Plan 的十条 Tell Now；保留为历史视觉证明，不通过换 Plan SHA 继承新 READY。改写后的边界或新 Copy 需重新审核与生成对应展示包，不能挪用旧渲染。

字幕样式在原生界面设置 Noto Sans SC Regular、深墨绿、48 px、无描边/背景/阴影。
CEP 没有字幕内容读取 API：`create_caption_track` accepted 不等于实际创建已证实。
因此另导出原生字幕 sidecar 对照冻结文本和时序，并检查实际带字幕视频帧。
原生 SRT 写出会按帧取整并截断毫秒，时序允许最多一帧加 1 ms 的写出误差。
编辑批准必须绑定最终字幕与展示画面，不能沿用改变之前的批准。

本机连接使用 loopback 服务和专用私有权限目录；不修改整棵用户 Temp/AppData ACL，
不绕过上游私有目录检查。token、安装路径、屏幕坐标和真实材料仅保存在忽略的本地配置。
Adobe 与预览放在用户指定的屏幕 2。

## 当前验收与下一步

见 [SWISS_COGNITIVE_POV_ACCEPTANCE.md](../SWISS_COGNITIVE_POV_ACCEPTANCE.md)。
Engineering / Payoff / Human Taste / Teaching / Source / Editorial / Music 分开记录。
这轮完成一个视觉试制后停止；不自动生产六方法系列，不扩展 AE 模板或发布系统。

Human Taste Review 必须评估学生是否知道下次第一刀、实际少做或暂缓了什么、
复杂度在哪一秒下降、去掉特效是否仍有方法价值，以及 Stop 是否清楚。
只要还没有真人看过，结论保留 PENDING。
