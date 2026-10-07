# Pedagogy Compiler v0.4 Acceptance

日期：2026-10-08。实际仓库基线：`main@31fcd975a486ab270e5a4d0254fe31356452cc9e`，已包含此前声音表演层；本轮只修改 Pedagogy、对应 Schema、合成测试与文档。

契约、来源保全、真实回放与回归测试的工程验收 PASS。Human Pedagogy Taste 为 PENDING，公开发布资格为 false。没有生成视频、改声音、改 Student POV Copy 或接入 V10。

## 契约与兼容

| 契约 | 本轮状态 |
|---|---|
| Pedagogy Plan / Compiler / Handoff | 新增显式 0.4.0 |
| 0.3.0 默认生产调用 | 保持兼容；不改变已有产物 |
| 0.1 / 0.2 / 0.3 历史 | 可 inspect；不覆盖、不改版本标签 |
| Disclosure Policy | 0.2.0，不变 |
| Boundary Delivery | 0.1.1，不变 |
| Student POV Copy / voice-delivery | 0.3.0 / v1，不变 |

0.4 必须从原 Frozen Asset 与当前提供的 Status 重新 compile。旧 Plan 只作审计对比。`required_version="0.4.0"` 拒绝 0.3；原 0.3 当前消费仍须重新核验其冻结源与 Status。缺少当前源的历史 inspect 永不提供消费资格。

R02 复用了已有 Boundary Risk Review 的原 0.3 基础绑定。Compiler 重新验证该基础，再生成新的 0.4 Plan，不修改 Review、不创建新教学凭证。当前 Copy、Voice、AE、Premiere 消费链没有切换到 0.4，新 Handoff 标记必须有显式 adapter。

新增主动作与七项 first_touch、primary_simplification、Work Delta、带 scope 的 Payoff、Cognitive Reduction / Load Projection、Boundary Presentation Coverage、认知对象与可逆状态、Attention Transition、Compression Audit / First-touch Audit 和 PENDING 人工体验槽。

## R02 真实回放

同一冻结源与既有审阅分别重新编译 first_touch / worked_example，均为内部工程 READY。主动作数为 1，没有 supporting action。局部候选域由 4 变为 3，payoff_scope 为 candidate_set，decision_completion=false，answer=null，may_output_final_answer=false。

| Work Delta | 实际投影 |
|---|---|
| baseline | structural_candidate_state；未测量学生实际路径 |
| removed | 1 个当前候选核验任务，由有效局部排除关闭 |
| deferred | 0；源记录没有支持额外暂缓，未照抄 Prompt 补齐 |
| still_required | 5；剩余三个候选核验及方法/实际动作 Stop |
| unsupported_savings | 时间、阅读、词汇、心理量化、整题捷径 |

`truth_guard / answer_scope / boundaries / semantic_review / release_state` 与原 0.3 Plan 完全相同。九条原边界及审阅仍保留；当前 Tell Now 合并呈现为一个已有审阅的覆盖组，五个未触发分支仍在 Later。Tell Now 不要求逐句 VO，但当前 Stop 与候选未闭合状态必须获得有效覆盖。

原题选项文字始终 protected；remove 操作只作用于候选 eligibility 与已关闭工作义务，不授权删改原题。22 个对象分别记录原题、Evidence、实际 Output、Stop、工作单元、候选状态及未闭合状态。没有从英文文本推断新的关系图，没有相机或 AE 参数。

选中输入的 Compression Audit 有 186 个叶节点：presented_now 39、deferred 120、engine_only 23、explicit_merge_coverage 4，omitted 0。这里的 deferred 是教学披露台账，不能当作 Work Delta 的任务暂缓。此检查证明交接结构守恒，不认证画面已经展示或学生已经理解。

| Canonical UTF-8 bytes | 0.3 | 0.4 |
|---|---:|---:|
| first_touch Copy | 82,374 | 53,746 |
| worked_example Copy | 97,945 | 53,749 |
| first_touch Motion | 13,066 | 21,256 |
| worked_example Motion | 13,069 | 21,259 |

Copy 减少约 35% / 45%，保留必要教学字段与覆盖义务。Motion 不再携带教学文字、完整风险矩阵或字面覆盖正文；体积仍增加，因为新增完整的对象状态、恢复、工作 ID 与引用目录。没有把这项增加描述成字节压缩成功。完整审计留在后台 Plan，当前下游显示内容不因新增字段变多。

## G01 负例

first_touch / worked_example 均为 HOLD：`baseline_work=null`，removed/deferred/still_required 的收益记录均为空，allowed_claim 与 payoff_scope 为 null。两种模式都保留 `BASELINE_WORK_UNSUPPORTED / PAYOFF_UNSUPPORTED / COGNITIVE_RELIEF_UNAVAILABLE`；first_touch 另保留原必要边界过载。

已有实际 route 与 noun-like 产物继续绑定，Stop、原题与未闭合状态继续保留，但不产生新的认知收益或词形豁免。两个 Consumer Handoff 都被阻断；没有给 G01 创建 Review 或补造 Payoff。

## 可核验绑定

以下仅列 hash 与结果，不提交真实题面或文案。完整请求、Plan、Handoff、回放及保全台账位于忽略的 `local-data/pedagogy/compiler-v04-r2/`；开发中的 r1 产物也保留，不覆盖历史。

| 输入 | R02 | G01 |
|---|---|---|
| Frozen semantic binding | `3d0aca78088cdadb57e5505d91a3e369c670a1dc7403bdc699ffb1262a1e18fa` | `101f9ac68420c2e54ca422bf4f61c91b20ec53e651c397cf8e8c95ecf1102e9b` |
| Frozen source hash | `ed073ba568782bb39ee964bad9a0c9c616a6b6e7885141793717d0c91066a2e5` | `21ab21b67b920e617b4e667e708efe289ead61bb7886e37b245b1c8cd50c5ea1` |
| Selected method hash | `ee1ec99443db4281aab59ee97652b01b0017dc6041fb8e39887864cca23da766` | `514992d6241e0df19e8a20ea621f79f88014484e578d1b731938b2ae96e89ed2` |
| Actual action set hash | `a1e9e1fb61f00ce6887965f6d990c3a85eb7d14827df86ddc72b2e096a92bbcf` | `45f6e13bb07565f9ed5d087de01a64adb0ac9d06765691228f4a233f3f07c200` |
| Supplied Status file SHA-256 | `d9fee881e9f8660ee417e2ec665c871ac09f38d2b9c86ce30df69087d8ca376f` | `19999addc04bb2e51266fa92d52ee4b11cb2b381dab72793ae417d5a20a54b19` |
| Existing Boundary Review file SHA-256 | `57e77d74e12d30b2e3e9ee2dff5c6d2392dc7909b188497b7e961f680eb53cf1` | 未提供；未创建 |

R02 source_analysis_sha 保持 `da5bc550b80b2c7285e4b9e51e2408eb81900deb0fad47235e35a046e45a58d0`。

| 输出 | Semantic Plan SHA / Handoff Content SHA |
|---|---|
| R02 first_touch Plan | `a3503a2870dab4490bec7a6e854927267cf36d9c4aedb1e039ca720d925e7a65` |
| R02 worked_example Plan | `4b176c0d1efd5d4e3c246412452ac30cf44670f7a63db6eb66bd761a68baa947` |
| R02 worked_example Copy | `38f2e79fb04e8a49603710368b4037f24aaa7891037bdbd6cec1474a506de068` |
| R02 worked_example Motion | `d2b26b288a43f5f9ad83c464589c253bac8db99730bcb3221a8af0ce96679256` |
| G01 first_touch Plan | `bb685946d577b4511801468b492adeef544e19546f1dcf04dea720cc203b1287` |
| G01 worked_example Plan | `ecd5decffdf546224777e67117bb219a885bc4ded73fdde577d2461132385eaf` |

四条真实编译均验证同输入重复生成完全一致；只改生成时间时 plan_sha 不变、envelope_sha 改变。旧 Plan/Handoff 仍通过原 0.3 冻结源重放。

## 测试与保全

- 新增 27 个合成测试已通过，覆盖版本伪迁移、源变化、依赖撤回、一个主动作、supporting 依赖、空 baseline HOLD、分类守恒、局部范围、Reducer/Locator 边界、4→3 无答案、Tell Now 覆盖、语义 Stop、审阅绑定、保护/暂缓/恢复、无 AE/新文字、Compression Audit、收益禁言、人工 PENDING 与发布状态。
- SYNTHETIC modifier / subject / predicate / object 测试只检查冻结标注的契约、状态、恢复与投影，不证明真实英语句法识别。
- 83 项既有 Pedagogy / Boundary / Mechanical Payoff / Student POV 定向回归通过。
- 全量回归：746 项通过，453.773 秒；包含新增 27 项，不把定向重跑重复计入总数。日志保存在忽略的 `local-data/pedagogy/compiler-v04-r2/full-regression.log`。
- ANSWER 校验通过：82 方法、20 来源文档、生成资产 PASS。
- 388 文件的原始保全台账中，387 个受保护源、旧 Plan/Review/Copy、Voice、AE/PR 与媒体文件内容 hash 不变；剩余一个是本轮有意升级的 Schema dispatcher。原 Schema 在 `pedagogy-plan-v03.json` 中逐字节归档，未丢失旧定义。

## 未闭合项与 Release

程序通过不代表第一刀已被学生看懂。R02 的 baseline 是结构候选域，尚无学生实测路径、耗时、心理负荷或陌生题迁移凭证；不能输出对应效率收益。当前没有 R02 主体/谓词/宾语的冻结 span 图，因此没有新增 relation_simplification。G01 缺少 Baseline/Payoff，继续 HOLD。

0.4 下游 adapter 未激活；既有 Frozen Copy、声音模型、声音验收、图像和 Premiere 时间线均未改。没有新增播放体验、人声或审美 PASS，没有自动制作或发布。

```yaml
human_pedagogy_taste: PENDING
semantic_truth_certification_by_compiler: false
teaching_release: HOLD
source_display_release: HOLD
editorial_release: HOLD
public_render_ready: false
current_downstream_activated: false
```
