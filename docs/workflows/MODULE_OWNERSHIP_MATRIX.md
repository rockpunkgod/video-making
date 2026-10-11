# 模块职责与实际消费者

当前入口：[CURRENT_PRODUCTION_WORKFLOW](CURRENT_PRODUCTION_WORKFLOW.md)。本矩阵基于 `d9fa2da` 及本机可读取的独立私有产物；**标注 LOCAL_UNMERGED 的生产增量不属于已提交能力**。E01–E20 证据编号对应审计报告；逐项六维状态、证据路径与可用性见[能力索引](PRODUCTION_CAPABILITY_INDEX.json)。下面每条卡片的“有权/禁止”界定职责，不授予额外操作权限。

## 教学事实与节目

| 模块 / 目的 | Inputs → Outputs / Contract | Producer → 实际 Consumer |
|---|---|---|
| ANSWER Frozen Export：导出已有受控事实 | 宿主 Question/Analysis/Review/Source → `frozen-asset-bundle`、`artifact-status-manifest`；`frozen_export.py` | ANSWER 宿主 → `video_contracts`、candidate、Episode、native current |
| Video Contracts：验证同一输入与有效性 | Bundle/Status → seal、语义/表现指纹、ACTIVE 匹配；`verify_bundle/status_matches` | 导出者 → 所有使用这些 API 的消费者；不会替未调用者自动把关 |
| Content OS 候选/旧 Director：把选择做成封装 | Frozen/selection/status/rating → candidate、P02 draft/final package；v0.1 兼容 API | 编辑者 → R06 私有作者的每题 package；旧 `content_os produce` |
| Episode Development：验证一期组织 | 作者 `method-episode-plan` 1.0 + statuses → 工程审计；发布时再吃逐题最终 request | R06 私有作者选题/写 plan → native `current`、Audience、`publication_episode` |
| Content Profiles：区分产品质量目标 | FREE/PAID + 七阶段现有产物 → hash-bound editorial context | 作者 → 阶段交接/质量评估；不产生具体片段 |

| 模块 | Authority / Forbidden Decisions | Evidence / Role / Gap / Action |
|---|---|---|
| ANSWER/Frozen | 提供受审 Action/Evidence/Relation/Review/Role/Stop 与 lifecycle；制作层禁止自行升 Review/补答案 | E01；`CURRENT_PRODUCTION`。Status 是显式快照，缺实时刷新不能假装当前；保留唯一事实来源 |
| Video Contracts | 检验所供封印/绑定与状态；禁止由 hash 正确推断英语正确或人工认证 | E01；`CURRENT_PRODUCTION`。要求每个真实消费者显式调用；保存私有来源可追溯性 |
| 旧 Content OS | 在既有事实内封装/明确选择；禁止重做英语、借 helper 宣称完整答案、将旧 60s 变成长 Episode 限制 | E06；`LEGACY_COMPAT`（其中封装仍实际被 R06 调用）。保留 API；文档降为兼容入口 |
| Episode | 检验独立题/主方法/递进/Payoff 范围；作者选择 Establish/Variation；禁止借题、跨题 Evidence 或提前定案 | E02、E06；`CURRENT_PRODUCTION`。不是节目生成器；保留作者→验证边界 |
| Profiles | 产品语境和质量标准；禁止 FREE 替 Paid 放行或硬改教学契约 | E02；`IMPLEMENTED` 的编辑 context，R06 作者采用政策但无已证通用 context 串线，能力角色 `EXPERIMENTAL`。Paid gate 另列 FUTURE |

## 体验、导演与研究

### Audience Engagement Design

- **Purpose / Contract：** Episode 之上的观看问题、递进、信息回报假设与 beat 风险；0.1/0.2 `design_engagement/validate_engagement/director_handoff`。
- **Inputs / Producer：** 有效 Episode、当前 Status、宿主 authored Audience Direction；v0.2 另有七字段 viewer_state 和早于当前的 beat 引用。
- **Outputs / Consumer：** 计划、结构风险、scene handoff。实际 B06 r2 已做 beat→native scene 对照；目前消费到限定导演交接，未执行新镜头。
- **Authority / Forbidden：** 建议观众为什么继续看、看什么变化；不能产教学事实、认知测量结果、AE 坐标/关键帧或自动把建议视作完成。
- **Evidence / Role / Gap / Action：** E03、E13；`CURRENT_PRODUCTION` 仅 B06 计划/交接范围。`actual_media_mapping=UNAVAILABLE`；未来用实际 export 建映射，不用 planned timing 冒充。

### Pedagogy Compiler

- **Purpose：** 在已审选择内决定必须保留的教学信息、第一动作、Work Delta/Payoff/边界。
- **Inputs / Outputs / Contract：** Frozen+Status+selection，显式细结构/必要 review → Plan/Copy/Motion Handoff；`compile_plan` 默认 **0.3.0**，`CURRENT_VERSION=0.4.0` 不改变默认。0.4 须显式 `contract_version='0.4.0'`。
- **Producer / Consumer：** 宿主结构输入 → Student POV 相容版本/Method Choreography；无证据表明本次 R06 私有作者调用此链。
- **Authority / Forbidden：** 组织已有支持范围，保留 Stop；禁止增加省时、最终答案或未审细结构。
- **Evidence / Role / Gap / Action：** E04；0.3 `LEGACY_COMPAT`，0.4 `EXPERIMENTAL`（契约实现/实际诊断，不是 R06 native producer）。保留显式版本，缺输入返上游。

### Student POV

- **Purpose：** 让学习者跟着已有信息执行；不重新决定哪些教学事实成立。
- **Inputs / Outputs / Contract：** 相容 Pedagogy Copy/Motion、Bundle/Status、draft/copy_review → 0.3 Copy 或 0.4 Experience；`realize` 默认 **0.3.0**，0.4 用显式版本或 `realize_experience`。
- **Producer / Consumer：** Pedagogy+宿主文案 → Choreography/后续设计；0.4 R02/G01 有真实诊断，没有已证明 R06 参数接线。
- **Authority / Forbidden：** 在 Pedagogy 已定披露范围内组织体验顺序和自然跟做语言；不重新决定 TELL_NOW/TELL_LATER，不删必要边界，不让新措辞免 Copy Review，不从未决候选跳答案。
- **Evidence / Role / Gap / Action：** E04；0.4 `EXPERIMENTAL`，现有真实诊断的新 Copy Review/支持项仍 HOLD。不能用 schema 通过冒充可生产。

### Method Choreography

- **Purpose：** 保存有据动作间关系、source object 身份、结构后果与可逆性。
- **Inputs / Outputs / Contract：** Pedagogy/Experience 0.4、当前 Frozen、可选已审 application、身份规格 → `method-choreography/v1`、`choreography-projection/v1` 0.1。
- **Producer / Consumer：** 教学/体验投影 → Cognitive Direction 的设计消费；真实 R02/G01 bounded diagnostic，其他四方法是规格。
- **Authority / Forbidden：** 有据逻辑对象/动作；禁止新 actor/object 英语解析、给未审词段几何语义、维护第二套 AE 坐标。
- **Evidence / Role / Gap / Action：** E05；`EXPERIMENTAL`，真实消费 HOLD，Synthetic Peel 只合成。保留限定上层描述；先补真实依赖再接执行器。

### Cognitive Direction 0.2 与旧 Creative Director

- **Purpose：** 0.2 表达注意力、连续空间、相机意图；旧 `creative_os/director.py` 为早期 0.1 delivery 生成 shot plan。
- **Inputs / Outputs / Contract：** 0.2 消费明确 Choreography/Experience/来源 → direction/projection；`execution_allowed=false`。旧 0.1 消费 package/delivery/voice timing → shot plan/landscape contract。
- **Producer / Consumer：** 宿主设计/Choreography → 0.2 projection 消费边界与诊断；旧 director → `creative_os.__main__.prepare` / landscape。当前 R06 `DIRECTION_REALIZED.json` 来自私有作者，**不是 0.2 projection 的编译输出**。
- **Authority / Forbidden：** 导演画声兑现方式；不能更改事实或以 projection 假装原生参数/执行许可。具体坐标由一个执行作者维护。
- **Evidence / Role / Gap / Action：** E05、E06；0.2 `EXPERIMENTAL`，旧 director `LEGACY_COMPAT`。后续最小接线围绕一个具体 B06 消费者，不新建统一万能导演 runtime。

### Research-to-Design / 并行知识库

- **Purpose：** 提供注明来源、适用条件、证据强弱的设计依据与待试假设。
- **Inputs / Outputs / Producer / Consumer：** 研究材料 → 研究记录/呈现建议 → 宿主改稿和导演。已提交 `COGNITIVE_DESIGN_CREATIVE_REVISION.md` 记录实际 R06 改稿；自动知识接入增量在原工作区未提交。
- **Authority / Forbidden：** 推荐可验证的呈现方式；禁止成为第二个教学源、把文献结论当本片学生效果、自动升为制作硬门槛。
- **Contract / Evidence / Role / Gap / Action：** 无已合并通用 Research→R06 runtime 契约；E18；`EXPERIMENTAL`。保留正在开发的文件，本轮不收编或重写。

## 生产与保护

| 模块 / Purpose | Inputs → Outputs / Producer → Consumer / Contract | Authority 与禁止 | Evidence / Role / Gap / Action |
|---|---|---|---|
| R06 private authors | 两题+冻结改稿+完整VO → Episode/native request/spec/caption；r1→r2→r3作者 → adaptive | 手写合法呈现与实际时间；不增事实/假人工许可 | E06；`CURRENT_PRODUCTION`，LOCAL_PRIVATE。实际链可追踪，作者不在公开 repo；未来提取有限入口，不能宣称通用 CLI 已有 |
| Adaptive Episode | request/current+原 JSX → 原生工程/audit/framepack/picture；私有作者 → AE/PR | 执行已绑定原文字形/轨迹、核验 source/候选/完整依赖；禁止 solver/通用语义审阅 | E07、E08；`CURRENT_PRODUCTION`，HostOwnership 未接入，不能无保护恢复生产 |
| Host Ownership | 明确 project/target、owner、宿主快照 → 占用/操作与前后读回收据；未来限定 executor 调用 | 防止并发/错误目标；timeout 保留 UNCERTAIN；禁止盲目重试、自动清锁或抢占 | E15；`BLOCKED_DEPENDENCY` 指接线缺口，模块本身已实现/合成测试。旧 executor 没调用，未证明 native integration |
| B06 judgement preflight | r3既有画面与r2专用请求 → preparation/candidateprefix/annotations/handoff | 请求精细审阅、检查完整前缀；禁止词法PASS冒充语义通过 | E13；`CURRENT_PRODUCTION` 仅准备范围。run.py prepare-only；不重复G0 |
| B06 independent review + consumer | request/Action/Relation/source/当前Status/逐项review/plan → 独立review与限定READY收据 | 明确被授权的 AI 宿主可冻结本次新review；消费者只比对绑定/范围，部分不支持HOLD | E14；`EXPERIMENTAL`、LOCAL_UNMERGED。实际审阅完成，human false；未进G2，不随审计合并代码 |
| Voice Delivery | 已冻结逐字稿/完整声音/测得时长 → `voice-delivery/v1` | 验文件/文本/SHA；补帧静音；不得截断/拉伸或继承旧take认可 | E09；`CURRENT_PRODUCTION`，R06十九条真实素材；完整听感PENDING |
| Narration Performance | Copy+plan+现有producer → 表演意图、真实执行与A/B | 不改事实/引擎/训练；意图不等于实际声学兑现 | E17；`EXPERIMENTAL`，R02 STOPPED_NO_DEMONSTRATED_IMPROVEMENT，不推荐默认套入R06 |
| Premiere Production | 当前picture+完整VO/music/captions → native sequence/encoded media/核验 | 排布/避让/完整take与实际时间核验；禁止用accepted API响应冒充渲染验证 | E10；R06新版 `BLOCKED_DEPENDENCY`。历史原生实现可参考；桥不能新增音轨的限制、导出色彩问题须按具体项目验证 |
| Lossless editorial handoff | 已验证Rec.709 picture+真实PR audio export → packet-identical mux | 保留父媒体封装/时间/流；不能宣称修好PR色彩或任意输入安全 | E10、E19；`PROVEN_REUSABLE`仅已有逐包检验的交接技术；人审/新片适用性另审 |

## 专项实验：只承认逐功能、逐范围

| 能力 / Entry | 已有范围 / 实际证据 | Role / 不可继承 |
|---|---|---|
| native-creative-proof r7 词提示、范围确认、0.25s剥离、上下停放 | 合成明确跨度；原生3D/字形持续；用户“效果很好”绑定r7媒体。E16 | `PROVEN_REUSABLE` 的视觉参考。不是英语跨度识别、整目录生产批准、声音或教学认可 |
| 同实验 Camera/Focus/DOF | 本机AE26 Classic3D、真实Camera、FocusDistance、原生景深已执行；父级/世界坐标处理有具体记录。E16 | `EXPERIMENTAL`技术实现；早期partial认可不覆盖全rig/任意源/当前R06；无通用SDK |
| method-relay 局部动作接棒/阅读停留 | 一部指定影片的画面/动作/节奏被认可；逐项问卷/声音另待。E16 | `PROVEN_REUSABLE`仅同类型明确输入的视觉参考。独立两法教学接力资格不随视觉认可通过 |
| locating trace / Reading D 连续源字形、定帧复用 | 原生/帧来源有记录；Reading D整片仍有自己的限定。E16、E17 | 局部技术 `PROVEN_REUSABLE`；Reading D整体 `LEGACY_COMPAT`，不当R06默认入口 |
| adaptive R09 快速连续执行/局部guided replay | 5648帧native+PR及完整take检查；没有机械2×/0.5×或时长上限。E19 | `EXPERIMENTAL`导演策略，工程NATIVE_VERIFIED，完整观看理解仍PENDING；不宣称已验证学生能跟上 |
| Motion Identity G01 | 六方法signature规格，实际只G01 Hero；1080p历史pilot有native/PR。E20 | G01历史技术 `LEGACY_COMPAT`；其余规格 `EXPERIMENTAL`，不能一并叫native-ready |

## 谁验收与反馈

| 模块 | 输入/输出/实际消费者 | Authority / 禁止 / 缺口 |
|---|---|---|
| Engineering QA | current dependencies、实际host readback、frames、媒体decode、音轨对齐 → 精确工程收据 → 编辑/人审 | 验证已实现内容/规格/时间；不能证明好看、跟得上、学会或发布资格。E08、E10 |
| FREE Showcase gate | 当前 package/status、scope、finalcopy/display、实际最终media、四类外部human review → `decide` → `publication_episode` | 现行免费审核政策，代码已实现；在当前 R06 完整媒体消费范围标 `EXPERIMENTAL`，尚无最终 R06 审核收据。每类共同绑定全部最终输入。AI不充当human、未知权利HOLD。E11 |
| Paid release | 训练产品独立质量标准 → 专用审核（未实现） | `FUTURE`；FREE decide显式拒绝Paid。E02、E11 |
| Audience Learning | 实际cut inspection、human media-beat mapping、真实publication/observations → retrospective/rule review → 下期编辑 | `EXPERIMENTAL`实现与合成测试，当前R06无真实平台结果；不能把计划时间、研究、AI或synthetic称观众认可。E12 |

教学事实由 ANSWER 提供；Episode/Audience 组织观看；Student POV 组织跟做语言；导演兑现动作和注意力；AE/PR 执行并回读；工程、真实人类、来源权利与发布分别验收。未接通的边不会因为此矩阵列齐而自动成立。
