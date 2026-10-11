# 工作流审计：2026-10-11

本报告保存审计证据与当时结论；长期入口是 [CURRENT_PRODUCTION_WORKFLOW](CURRENT_PRODUCTION_WORKFLOW.md)。范围为 Phase A 只读审计和 Phase B 文档收敛。没有证据要求本轮修改运行时，Phase C 不实施代码适配。

## 基线、保护与并行任务

- 本地与 `git ls-remote --heads origin main` 均为 `d9fa2da8bf893745f567e21cb631a4d43299c110`，未回退。
- 主工作区有 Research-to-Design、Cinema、知识库，以及此前授权的 B06 AI 审阅/消费/制作代码增量。全部保留，不纳入此次提交。
- 既有另一 worktree `video-making-audience-v02` 在 `c77dd216a8c125d0f2a3037f905eaa6c78220434`，核查时 clean。
- 本次独立 worktree `video-making-workflow-audit` / 分支 `docs/workflow-consolidation-20261011`，基于同一 main。
- 主代理负责本审计；用户随后明确 Astra 继续原 B06 制作。审计不取得 Adobe 占用、不调用宿主、不执行 G2。并行任务进度不能写成“此次审计渲染成功”。
- 私有 `local-data/workflow-audit/BASELINE.json` 记录审计开始时工作树及 251 个受保护文件 SHA，包括教学源码/Registry/Case、B06 r2 交接、真实冻结源、原 R06 AEP/画面。并行生产新增文件不是审计修改。

结论标签：`CONFIRMED` 有代码或收据直接支持；`INFERRED` 为明确说明的设计推断；`UNVERIFIED` 缺实际执行/观看凭证；`BLOCKED` 有已知依赖缺口。能力角色与六个成熟度维度另记，不能替代教学生命周期。

## 证据目录

| ID | 核验对象 | 可支持的结论与范围 |
|---|---|---|
| E01 | [Frozen exporter](../../answer_engine/frozen_export.py)、[CLI](../../answer_engine/__main__.py)、Frozen/Status Schema | 显式只读导出入口；export 分支在 Registry/analyze 之前返回。状态相对于提供的材料 |
| E02 | [Episode](../../creative_os/episode.py)、[产品上下文](../../creative_os/content_profiles.py) | 多题同方法、独立题身份、逐题来源/Payoff、产品区分；不自动选题或证明吸引力 |
| E03 | [Audience](../../creative_os/audience_engagement.py)、B06 r2 全 Beat 交接 | 已实现建议与计划映射；`actual_media_mapping=UNAVAILABLE`；没有向原生 executor 自动执行建议 |
| E04 | [Pedagogy](../../pedagogy/compiler.py)、[Student POV](../../student_pov/realization.py)、[Experience](../../student_pov/experience.py) | 默认兼容 0.3，新 0.4 显式选择；真实新体验文案仍需独立批准 |
| E05 | [Choreography](../../method_choreography/validation.py)、[Direction 0.2](../../creative_os/cognitive_direction/compiler.py)、[验收](../../COGNITIVE_DIRECTION_V02_ACCEPTANCE.md) | 可重放的非渲染计划；R02/G01 诊断；不是当前 R06 原生生成器 |
| E06 | 本机 `free-showcase/prepare_title_task_episode.py`、`refine_title_read_cues.py`、`refine_title_candidate_holds.py` | 实际 r1→r2→r3 作者路径、P02 旧封装、独立场景/几何/时序；代码私有，不随公共克隆提供 |
| E07 | [Adaptive executor](../../ae/experiments/adaptive-episode/run.py)、[实际 JSX](../../ae/templates/cognitive-pov-v0.1.jsx) | 当前状态/输入校验、原生对象和帧执行、画面封装；未全局接入 HostOwnership |
| E08 | 本机 R06 r3 `native-request.json`、AEP、`native-audit.json`、`native-motion-audit.json`、`NATIVE_RENDER_RECEIPT.json`、`PICTURE_RECEIPT.json` | 原生 4K24、9,051 帧 / 377.125 秒画面；native/spec/media 身份与既有完整解码记录。此次不再渲染/解码整片 |
| E09 | 本机 R06 r1 `voice-delivery/`、`editorial/AUDIO_EDITORIAL.json`、r3 `VOICE_TIMING.json` / `CAPTIONS.json` | 19 条独立逐字声音、音乐与字幕计划已存在；完整 r3 原生 PR/最终声画收据在审计快照尚未完成 |
| E10 | [Voice delivery](../../scripts/voice_delivery.py)、[PR cinema](../../premiere_production/cinema.py)、[PR voice](../../premiere_production/student_voice.py) | 稳定音频消费、实测时长及原生/编码核验；不同历史请求不能互换 |
| E11 | [Showcase](../../content_os/showcase.py)、[lifecycle](../../content_os/lifecycle.py)、[发布政策](../../FREE_SHOWCASE_POLICY.md) | 免费四项独立审核；现有 review 全绑定的保守失效行为；Paid 不受免费 gate 认证 |
| E12 | [Audience Learning](../../content_os/engagement_learning.py)、[说明](../audience-learning-loop.md) | SQLite 台账、计划与实际帧锚点分离、真实反馈/数据来源；不预测传播、不给人审代签 |
| E13 | [B06 preflight](../../ae_production/judgement_preflight.py)、[入口](../../ae/experiments/r06-b06-judgement/run.py)、[旧验收](../../R06_B06_JUDGEMENT_ACCEPTANCE.md)、本机 r2 交接 | 提出四项标注请求、完整动作前缀与场景覆盖；committed G1 HOLD，非 G2 |
| E14 | 本机 r3 `HOST_PHRASE_REVIEW.json`、当前状态与 `G2_CONSUMPTION_RECEIPT.json`，此前未提交 producer/consumer | 用户在审计前授权 AI 宿主后的新独立凭证；四项限定消费可重放。非独立人工、非 committed 主链完成 |
| E15 | [HostOwnership](../../ae_production/host_ownership.py)、[测试](../../tests/test_host_ownership.py) | 合作式占用与前后身份检查能力；存在文件/通过合成测试不证明所有制作命令已接入 |
| E16 | [词提示剥离](../../AE_NATIVE_CREATIVE_PROOF_ACCEPTANCE.md)、[Method Relay](../../METHOD_RELAY_DUAL_PASS_ACCEPTANCE.md)、[Locating Trace](../../LOCATING_TRACE_V01_ACCEPTANCE.md) | 各绑定影片的范围限定认可；合成剥离不认证真实语法，定位通过不认证 B06 判断 |
| E17 | [Reading D](../../READING_D_DUAL_PASS_ACCEPTANCE.md)、[历史 Cinema](../first-person-solving-cinema.md)、[声音实验](../../STUDENT_POV_VOICE_PERFORMANCE_ACCEPTANCE.md) | 历史生产和有限能力；R02 Performance B 未明显改善，实验停止；不默认推广到 R06 |
| E18 | 主工作区未提交 `knowledge/`、`creative_os/cognitive_direction/{research,workflow,...}.py`、相关 dirty 文档 | 本机研究到设计增量存在，未纳入此基线提交；读研究不成为教学来源或发布必经门禁 |
| E19 | [历史 Adaptive 验收](../../ADAPTIVE_DUAL_SPEED_DIRECTION_ACCEPTANCE.md) | R09 两题原生执行与逐包无损声画交接；不认证新 R06 或修复 PR 原生色彩行为 |
| E20 | [Motion Identity](../../creative/motion-identity/motion-identity.md) 与同目录规格 | V9.1 六种 Signature 词汇、G01 有界 Hero；不等于六方法均已执行或获教学许可 |

私有 E06/E08/E09/E13/E14 仅在此机核查；公共克隆缺失时必须记录不可用，不能从验收报告虚构重跑。公开报告不复制真实题、完整审阅、音视频或模型。

## 主要发现与处理顺序

| 优先级 / 标签 | 发现 | 本轮处理 / 后续正确归属 |
|---|---|---|
| P0 CONFIRMED | README 线性图把设计层串接与实际 R06 制作混为一条链 | 改为当前入口导航与实际作者/执行路径；新链单独标明 |
| P0 CONFIRMED | Audience 全 Beat handoff 已有，但 adaptive 不导入它；处理建议仍靠导演 | 记录已验证的计划交接和未接通的执行；下一步由具体镜头作者记录采用/拒绝原因，非新 Audience Engine |
| P0 CONFIRMED | B06 旧 G1 HOLD 与审计前新增 AI 凭证同存 | 保留两份事实与版本，不让目录状态或 ready 布尔值自动升级整条制作；接纳新契约和真实 HostOwnership 属于并行 B06 任务 |
| P0 CONFIRMED | HostOwnership 尚未在旧 adaptive/PR 入口全局接入 | 文档明确 live mutation 必须实际经过 guard；审计不修改宿主或假报 live 独占验证 |
| P0 CONFIRMED | `DIRECTION_REALIZED` 名称/计划范围容易被当媒体时码 | 区分 PLANNED、原生回读、实际媒体锚点；最终 Audience 映射还要外部人工帧锚点凭证 |
| P0 CONFIRMED | R06 实际作者与编辑编排部分仍是私有脚本，公开新 Agent 无法一键重建 | 指明必须取得的 request/父资产；缺失即报本地证据不可用，不编造 CLI；后续有重复真实需求再抽取小适配 |
| P1 CONFIRMED | Pedagogy 0.4、Student POV 0.4、Direction 0.2 有实现，但真实 R02/G01 多为诊断计划，未替代 R06 执行 | 标独立计划链/阻塞依赖；保留默认 0.3 和旧 schema，不强制全仓迁移 |
| P1 CONFIRMED | 旧 Video OS 30/60/90 Pattern、旧固定双遍页面容易成为免费整期默认约束 | 加历史/兼容提示；现行 FREE 无时长上限、按题选重放。旧 API 行为不改 |
| P1 CONFIRMED | `creative_os.director`、Cognitive POV、Direction 0.2 与私有 R06 作者名称相近但消费者不同 | 职责矩阵列实际消费者与版本，保留旧入口；不为统一名字合并源码 |
| P1 CONFIRMED | Showcase 各类 review 共用所有最终绑定，音频变更可能使全套 release 凭证保守失效 | 如实记录，不宣称实现了审核精细复用；不把它误写为教学事实全部失效 |
| P1 CONFIRMED | 研究模块和实验认可容易被扩大成稳定生产能力 | 索引按具体能力与人审范围分类；研究建议只是设计依据，不能充当人类观看或教学证明 |
| P1 BLOCKED | R06 完整 AV、B06 比较可理解性、来源/录音权利和最终发布凭证尚缺 | 分别回原生编辑、G3 看片和来源/编辑审阅；不是更多编译器能解除 |
| P2 INFERRED | 一个明确负责的 Creative 作者消费各交接，比再增加统一 Runtime 更容易归因镜头失败 | 仅目标收敛建议，尚未实施新执行链或通用局部渲染 |

## B06 Dry Run：两份状态各自成立

在干净审计 worktree 中，只读读取原主工作区的 r2/r3 资料，没有调用 prepare/G0 或 Adobe：

- `validate_episode` 对两份提供的 Status 返回工程 PASS；这不是外部实时监听或独立教学认证。
- `PREPARATION_RECEIPT` 登记的 **17** 个交接文件字节 SHA 全部一致。
- `candidate_prefix` 从完整冻结动作序列得到的结果与已存 `CANDIDATE_PREFIX` 完全一致；B06 前 B/C/D，后 C/D；保留 C 不提前闭合。
- `inspect_phrase_requests` 重新核验四项精确范围后，与原 `ANNOTATION_REQUEST` 完全一致；committed 结果仍是 `HOLD_MISSING_FINE_ANNOTATION`。
- 在原主工作区，另用未提交 `consume_phrase_review` 对 r3 已冻结 AI 凭证只读复验，结果与保存收据完全一致：`READY_FOR_BOUNDED_G2`，四项覆盖，`independent_human_certified=false`。
- r3 审阅 SHA `e014e3b8fb843a1823343b2ed5938a884c4117df47efa670b0c555c47ebe08d6`；消费收据 SHA `c630ed02bc9a215c61268cf73c736f155f18d84e58252034ea1456adda39e0a4`。核验时 r3 无 AEP/PRPROJ/MP4。Astra 此后按用户明确分工继续制作，其新产出需单独收据，本报告不提前认证。

四项语义请求由预检提出，上游授权宿主审阅后另冻，消费者核绑定后才接入受保护的原生执行。没有返回标注的原 r2 路径必须停 G1；有新凭证的并行 r3 也不自动继承原生、人审或整期放行。G3 是用户看片，G4 须等其范围明确的确认。

## 文档漂移与增量修订

| 文件 | 漂移 / 处理 |
|---|---|
| `README.md` | 新增唯一当前入口；实际生产与计划链分离，指出 B06 状态是版本快照 |
| `docs/video-os.md` / `docs/video-os-baseline.md` | 顶部标旧 V0–V7 / 18afe8a 基线与兼容用途；30/60/90 不再约束当前 Episode |
| `docs/first-person-solving-cinema.md` | 顶部限定历史 Reading D 链，定位/提取能力按实际认可范围复用 |
| `docs/pedagogy-compiler.md` / `docs/student-pov-experience.md` / `docs/cognitive-direction-v02.md` | 增加当前路径定位，保留原版本和显式适配条件 |
| `docs/audience-engagement-design.md` | 明确 v0.2 计划交接不等于执行接通，保留 v0.1 参考正文 |
| `docs/content-profiles.md` / `FREE_SHOWCASE_POLICY.md` | 保留现行独立 Rubric 与无时长上限政策，补当前生产导航 |
| `creative/README.md` / `docs/module-integration.md` | 主工作区正有未提交研究增量，本轮不覆盖；后者属于 ANSWER 开发接口，不是制作端可运行 Analyzer 的授权 |
| 旧验收报告 | 原版本事实、日期与局部认可原样保留；能力索引引用范围，不改成“最新全都通过” |

## 验收与五项独立批判

本轮完成的是入口、事实分层与兼容性检查，没有要求另一个 Agent 盲测接手，也没有测试真实观众的理解。以下 PASS 只对应列出的检查。

### 已执行验证

- 干净审计 worktree 的既有回归 **248 项通过**（180.457 秒）：`test_method_episode`、`test_audience_engagement`、`test_content_profiles`、`test_candidate_motion`、`test_judgement_preflight`、`test_host_ownership`、`test_free_showcase`、`test_engagement_learning`、`test_pedagogy`、`test_pedagogy_v04`、`test_student_pov`、`test_student_experience`、`test_cognitive_direction`。
- 补充 `python -m unittest tests.test_video_os tests.test_voice_delivery -q`，**54 项通过**（19.903 秒）。合计 **302 项**，包括旧短格式兼容、规范化 hash、状态失效区分、不可继承的声音 take 认可。没有新增运行时测试或修改测试。
- 真实 R06 r3 的 `adaptive-episode.current()` 只读检查通过：22 个输入文件绑定、19 条声音、3840×2160 / 24 fps / 377.125 秒；`public_render_ready=false`。未调用 `build/audit/preview/render`，Adobe 调用数为 0。
- B06 的真实只读重放结果见上节：17 份原交接身份保持一致；原 r2 HOLD 与新 r3 限定 AI 凭证各自成立。
- 能力索引检查通过：33 个唯一 ID、6 种角色、逐项 6 个独立维度、20 项证据目录及完整必要字段；106 个能力/证据路径、21 个 Python 符号均存在。私有及未提交路径从主工作区核实，未冒称公共克隆可用。
- 修改文档及新入口中的 92 个本地链接均可解析；`git diff --check` 通过。
- 251 个受保护文件 SHA 均未变化。原工作区另外 91 个并行研究/Cinema 文件 SHA 均未变化；7 个已登记的 B06 制作文件由 Astra 独立推进，不纳入审计改动。此检查包括旧 R06 AEP/画面和冻结教学输入。

### 八项场景检查

| 场景 | 实际检查与结论 | 适用范围 |
|---|---|---|
| 1. 当前 B06 | PASS：从现有交接读入并重放 r2 请求，仍停 G1；词法范围不升级关系审阅。另版 r3 只在独立 AI 凭证消费核验后获得限定 READY | 已提交路径不引导直接渲染；READY 不代替 G2/G3。两份状态不互相覆盖 |
| 2. 有效完整 Episode | PASS：真实 Episode 与 native `current()` 只读检查；追到私有作者、旧 Package 封装、实际 JSX。计划链与参数来源分别列出 | 有效 request 可交给符合宿主占用条件的制作执行者；没有此次新原生执行或完整 AV 验收 |
| 3. 历史 Reading D | PASS：历史文档顶部和能力索引将其路由为限定技术/历史回放，当前入口转 R06；旧文件及 API 保留 | 文档路由与文件检查，未重开历史工程、未转移人工认可 |
| 4. Paid Mastery | PASS：`test_paid_cannot_use_free_publication_review`、独立 Rubric/绑定检查；入口明确转 Paid 训练设计 | 免费 gate 不认证课程；完整 Paid 验收仍 FUTURE |
| 5. 上游撤回 | PASS：Episode/Audience/Showcase 的撤回阻断及 Video OS 传递失效测试通过 | 相对于实际收到的状态清单；没有后台实时监听承诺 |
| 6. 修改配音或镜头 | PASS：声音/稿件字节变化被拒、新 take 不继承认可；Copy/画面/署名使最终审核过期。metadata、rights、presentation 与教学失效分别测试 | 时钟/字幕/媒体须重验；现有 Showcase 保守重签行为保留，不误称无关教学事实改变 |
| 7. 旧时长规则 | PASS：现行入口与产品政策明确无时长上限，实际 R06 为 377.125 秒；旧短格式拒绝测试仍通过 | 不修改历史 Pattern 行为，也不将其限制投射到多题 Episode |
| 8. 研究与人类反馈 | PASS：Audience 仅建议、AI 不可签人审、合成/真实反馈分离、计划帧不可冒充实际媒体等测试通过 | 不以研究、结构评分或程序 PASS 证明好看、理解或传播；新片人审仍 PENDING |

### 修改范围与兼容影响

新增上述四份工作流资料；修改 README 及“文档漂移”表中九份既有文档，共 **14 个文件**。生产能力索引是文档数据，明确 `not_runtime_contract=true`、`not_release_authority=true`，没有运行时消费者或新增门禁。源码、Schema、默认版本、测试、历史验收及真实媒体均未因本轮审计改变。Phase C 未实施；B06 并行任务的代码与媒体不混入本次提交。

### 五项批判复核

| 复核问题 | 结论 |
|---|---|
| 是否过度设计 | 只建立四份导航/职责/索引/审计文件；不新增 Runtime、审批系统或生产必填表 |
| 是否破坏兼容 | 不改 API、Schema、默认契约、旧 Pattern、历史文档正文或冻结媒体 |
| 是否增加开发阻力 | 索引只是发现工具，不成为运行时门禁；复用现有收据，不要求补不存在的设计层 |
| 是否缩短交接 | 从一个入口直接定位 revision、下一步、停止点与负责人；明确哪些只是计划 |
| 是否帮助创意归因 | 比较原因不清回导演/标注，文字不清回原生布局，听感回声音/剪辑；不会一律改 ANSWER 或堆架构 |

剩余工作按 P0→P1 顺序由真实制作缺口驱动。本审计本身不证明观看改善，不替任何未发生的人工审片、听感、来源许可或平台数据签字。
