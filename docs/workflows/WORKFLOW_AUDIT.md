# 工作流审计：2026-10-11

## 自主整期 v1：2026-10-18

本次实际基线为 `video-making/main@34f64736b08d01ed8d802d9d765658585db510b3`，
远端 `ANSWER/main@1c388a0596b13935ae7c6a1af00834915a8efa33`。PR #3/#4/#5 的所需增量
在独立集成 worktree 中分别接入；原 main 的 93 个并行脏文件逐项保存 SHA，不重置或覆盖。
旧冻结题保留其来源纪元，不借新课程映射取得新教学身份。远端 PR 的 open/draft 状态不等于
本地适配是否完成，也不等于已向远端发布。

`autonomous_episode` 从真实 brief 和冻结候选池建立绑定输入的创作/语言职责工作包，宿主 AI
生成实际作者响应，再进入现行 `authored_episode.dispatch`。制作消费者仍是 `AV_AUTHOR →
AV_PLAN → authored_native → AE / Premiere / package`。内部缺作者工作项由宿主继续完成，
完整文案发送后继续内部制作，用户审稿、整片验收与公开授权保持各自 PENDING。

完整初版 `autonomous-v1-r03` 已真实输出 270.333333 秒、6488 帧、原生 4K24 声画，
24 条完整声音、音乐、字幕和两个完整终判位于同一时钟。最终完整解码、原生视频包及时间戳
保持、原生 PR 音频负载保持和全 take 放置核验通过；两宿主恢复收据与封装时工程快照分别绑定。
真实帧审阅覆盖整片时间范围，271 个逐秒采样及 12 组连续帧共 427 个不同画面；这不是完整
原速视频感知，也不是试听。两处较重要问题已进入 `internal_ai_review` 台账并交给 R04 定向
作者修订：回看指代焦点被后一个同刻样式覆盖、D 候选遮挡原文阅读。未受影响分段只按严格
依赖和递归来源证明复用，受影响整场重渲。

当前最终修订及其收据由私有 `local-data/free-showcase/PRODUCTION_INDEX.json` 指向。
逐项实际消费者、历史未执行模块和剩余问题见该版 `MODULE_CONSUMPTION_AUDIT`；不能把
旧编译器、仅载入身份 hash 或一次单测概括成全部模块完成。有效 Pedagogy 0.3 投影参与作者
绑定，Student POV 的 HOLD 仍限制表述；0.4、旧 B06/R06、付费验收和正式发布契约不被补签。

两题完整版本仍比 5 分钟目标短约 29.667 秒，没有有效第三题时不填充机械等待。音乐保留
内部 scratch 身份。当前模型工具拒绝音频感知且没有直接原速视频输入，完整听感和动态观感
明确未观察；程序、帧样本及 AI 反馈都不是人类认证或学生效果证据。

回归记录：全仓 1730 项执行发现两项同一生成引用漂移，修复生成器后相关重复验证通过；
本轮自主恢复、原生分段复用、PR 部分编排和防伪绑定另有定向回归。具体数量与最终本机验证
以交付版收据为准，不把未重新运行的全仓测试写成全绿。

本报告保存审计证据与当时结论；长期入口是 [CURRENT_PRODUCTION_WORKFLOW](CURRENT_PRODUCTION_WORKFLOW.md)。范围为 Phase A 只读审计和 Phase B 文档收敛。没有证据要求本轮修改运行时，Phase C 不实施代码适配。

前次 R01 实际接入记录（2026-10-17）：新的用户任务已授权修改消费者并制作同一版连续粗剪，上述只读范围仍仅属于本报告的原始审计。当次实查主工作区为 `main@517485f`，远端 main 为 `3f30b668`；叙事分支为 `3b8c3b7`，电影节奏分支为 `0904558`。实查工作树没有未解决合并冲突，既有并行脏改动和 worktree 保留，未盲合分支。

当时断点是默认 adaptive 入口仍消费旧 native-request，而 163 秒作者脚本、长稿和 83 秒定位修正在私有目录各自存在。该次将可复用作者/时钟/原生适配接回默认入口，交付 `mainfilm-integration-r01`。两题、单次回看、新声音、字幕、AE/PR 和 293.458333 秒代理媒体已有同版产物；E22/E23 在[能力索引](PRODUCTION_CAPABILITY_INDEX.json)保留该范围的证据。Pedagogy/Student POV/Choreography/Direction 0.2/Audience 的自动编译边界没有因此被升级为已接通。

R01 当次 53 项相关回归通过，未跑全仓测试；37 份受保护父资产前后 SHA 一致。历史测试失败、漏读 take、原生失败与修复前媒体均保留。当前版本及未兑现项见[当前入口](CURRENT_PRODUCTION_WORKFLOW.md#当前版本与接手)。

## 后续 R02 整片接入：2026-10-17

本次从 `main@05afc5e2e46fd4317c5fd46baa3bb290de4e6464` 的实际脏工作区继续，保持同一个 `mainfilm-integration-r02`。已核对叙事、电影节奏分支的原记录；不合并整分支、不删除并行 Research/Cinema 增量。用户的新反馈是三维扫读未兑现、动作过快、文案仍像助手，并要求每次全文独立审稿。

实际修复进入原默认入口：`script` 从生产台词导出完整稿，旧稿会阻止新声音/时钟继续；明确的 `reading_path / choreography / voice_placements` 经 `compile_clock` 进入实际排版行、相机、焦点、完整候选及字幕。定位携带题干线索，按完整原文中已绑定的路线搜索，到时才高亮；不提前知道命中位置。原位辨认、飞行、源句静读、透明提取、比较、判断和返回分别计时，完整配音随对应阶段开始。两题各核四项，一次回看只展开价格比较对象；作者承担观看动机与导演判断，不伪称所有旧编译器自动串线。

已制作真实 448.333333 秒、10760 帧、1080p24 连续声画代理，37 段完整 take、143 条字幕和 14.75 秒开场肖邦乐句进入同一 AE→PR 链。最终媒体 SHA 为 `541e160785e22cb38b62a46a4792ad30e13922c03cd88fc98019b9b91e8ecf30`。原生 PR 的逐段位置、音乐十个音量键均回读；最终完整解码通过，原生画面包及时间不变、音频负载不变，仅校正实测统一的 1024 样本 AAC 延迟。37 段完整声音与导出的最低相关系数为 0.999994。交付和最后保存工程的具体路径/字节分别在私有 `DELIVERY_QA.json / RESTORED_HOSTS.json`；Premiere 恢复前 Save 可改工程元数据，封装时快照与最终保存版本分开绑定。

作品回归使用真实编码帧：旧已认可 B 片与本片 D 项对照原位辨认、字母与整项连续入场及落稳，属于表现能力对照，不转授不同题材的认可。另查两题搜索路线、B/C/D 比较、重点回看和结尾。检查发现 C 项跨段证据过小、结尾跨世界飞行出现空白，已修为只提取本场确切来源的两段并各自归位，以及按实际口播句界切题。保留修前整片和工程；50 个未受影响分段原字节复用，仅重新渲染末尾 8 段共 56.166667 秒，台词、声音与 AV_PLAN 均未变。证据在 E24 的各帧来源、尾段补丁和复用收据。

原生失败未隐藏：空间不足导致的未保存工程已用同一失败凭据核验部分状态后保存并恢复父工程；20 秒渲染触发内存保护后实际检查并清理所属停止队列，改用较小分段；PR 第 24 段放置超时后用三次一致回读确认只存在前 23 段、无待执行桥命令，再明确续放缺失部分。保留错误、检查和恢复凭据，不盲重跑。当前 AE/PR 已恢复父工程、共享占用释放；43 份旧资产 SHA 不变。

相关 61 项回归通过，未运行全仓测试。程序与原生检查只证明本次执行；完整文案 V1、完整观看和听感仍待用户独立审阅，学生观察为 0。4K 主合成未渲染正式影片，音乐是内部 scratch，公开资格未获放行。已删除被明确替代的当前默认表现和过时接手步骤；历史可重放链、旧媒体、失败记录及未确认废弃的模块保留。下方仍为原始 2026-10-11 审计，不以本次工程结果改写旧结论。

## 后续 R03 方法表达修订：2026-10-17

用户确认上一版整体方向基本成立，并明确免费版采用“点名—执行—结果”。本轮从 `main@aa7157bf2056bff51bb06577b8bc42ce465f1b64` 继续修改同一主片；保留两题递进、三维原题世界、完整候选移动、声音模型与唯一重点回看，不新增展示模块或教学方法。现行政策和入口撤下“动作价值之后才出现方法名”的旧顺序，后台分析不再默认逐字段成为口播、字幕或微型课程。

生产实际消费的 V2 完整稿已全文发送聊天，1314 字改为 510 字；仍待独立审稿。有效冻结材料中的“跳读定位”和“换词不换义”在即将使用时点名，后续调用不复述定义。删除定位报行程和“参加/主持”的生活类比，完整原文、选项、来源区间及所有终判引用保持不变。选中的 29 段完整声音包括 28 段新生成和 1 段精确复用，模型、声音资产和速度系数不变；对齐与 ASR 不代替人工听审。

同一作者输入已进入实际声音、72 条字幕和原生时钟，278.625 秒、6687 帧的 AE 主片包含 42 个来源块、13 个阅读事件、两条携带题干线索的路线及一次重点回看。原生来源、候选身份、字幕、相机和焦点回读通过。其后完整 AE→PR 的 1080p24 声画代理已输出，最终 SHA 为 `604f417ff5e3b346a70bd7b475e0567fb359c728b97d94d4d2660753ac8305d8`，完整解码和 29 段完整声音核验在 R03 `DELIVERY_QA.json`，宿主恢复在 `RESTORED_HOSTS.json`。有实际完整媒体不等于获得整片审美或听感认可。

保留首轮声音模型初始化退出、零 take 的失败记录。检查宿主空闲状态后释放 AE 缓存，在新目录用同一 CPU 模型完成生成；资源处置不冒称已证明崩溃根因。发现接手时 AE 没有活动合成，原恢复代码却强制解析合成 ID，本轮只补上恢复工程窗口的 `none` 分支；仍须原生回读身份，不放松共享宿主占用。相关 41 项回归通过，未跑全仓测试。旧媒体、工程和冻结输入共 53 项受保护，未删除历史失败或并行脏工作。

## 后续 R04 与独立 Motion A/B：2026-10-17

用户指出跳读应一次小幅俯仰后向下移动，随后明确焦点放大按词块接续。R04 沿用 V2 文案，原生向下路径已有预览但未完成整片渲染。最新任务将范围收敛为先分析 Read Frog 原宣传片，再完成独立 8–12 秒原生 A/B；因此未将新 Rig 提前接入主片，也未扩写制作架构。

已取得原始 `read-frog-feature-tour.mp4`：80.600 秒视频轨、1920×1080、30fps、2418 帧；主要运动区间密集逐帧提取，约覆盖 38.5 秒。参考片包含可见的连续对象交接，也包含 38.433→38.467 秒的实际剪切，未将后者伪拟合成相机推镜。原始工程未取得，软件、焦距、缓动控制点等不虚构；声音只保留测量，独立试听判断仍待完成。

独立本机目录 `G:/VideoMaking/read-frog-motion-ab-r02` 已产出 A/B 各 12 秒、3840×2160、24fps 的实际 MP4、24 秒顺序对照、原生可编辑 AEP、接触表和 `REVIEW.html`。样片取自当前合法 SC03 比较镜头，原词、完整声音、方法与 A 暂留时机一致；不将局部暂留冒充整题终答，也不代签完整跳读段。B 用原生相机、连续曲线、前景携带与词块同相位 100–104% 焦点；源码仅在 [独立实验](../../ae/experiments/read-frog-motion/README.md) 内消费。

`NATIVE_QA.json` 核验实际轨道、文本与来源、5 个词块、原生关键帧、空间及落位；`MEDIA_QA.json` 核验每版 288 帧、连续时戳、完整解码、音频样本一致；同帧开关像素对照证明运动模糊产生差异并恢复原值。程序通过与图像观察分别记录，审美、正常速度可读性、听感及学生效果仍未获人工认可。相关 41 项回归通过，未跑全仓测试。

试验中一次预览参数被工具输入校验拒绝，未进入原生执行。已检查项目、队列和占用后记录并解除不确定占用，再用有效参数执行，保留失败与恢复凭据。最终 AE 已恢复试验前 R04 工程和 `comp:1`，PR 未被本次实验改动；65 份旧保护资产及父工程、AV_PLAN 共 67 项 SHA 一致。参考片、媒体与私有来源不随源码发布。

## 限定 Motion Quality 实验：2026-10-18

用户指定 Mhd Labs、Jake In Motion、Ben Marriott 与 School of Motion 的四个原始 YouTube 教程，要求实际原生 A/B，不扩大生产架构。已取得并核对原页面、作者与完整时间戳英文字幕；没有下载解码这四部教程或取得其工程，所用参数是本实验的设计与原生测量，不冒充作者曲线。之前 Read Frog 原视频的逐帧研究仍保持其独立范围。

新本机目录 `G:/VideoMaking/motion-quality-r01` 保留原 R04 AEP、原 AV_PLAN 与既有试片，选择 SC09L 搜索后段至 SC10 原位交还。两版均实际渲染为 **3840×2160、24fps、802 帧 / 33.416667 秒**，含相同的一秒尾帧；另有 1604 帧顺序对比片、可编辑 `MOTION_QUALITY_AB.aep`、编码帧接触表与本地交互报告。保留三条完整原 take、原词与字形、证据、方法和 A 排除时机，未冒充整题终答。片段完整文案单独交付，未修改主片稿。

实际 B 消费分阶段原生速度、空间切线、Camera + Null、可见前景选项、12 个词块焦点与提取/归位错峰。41 个实际关键帧的有效速度及 influence 核验通过；原生时间刻度量化、首键无入段速度独立记录。生成稿原先包含未在原生回读中出现的 Y 转角，最终明确收敛为实测的 1° / 0.8° 单轴 pitch。仅同步生成参数与工程注释，前后全部原生回读字节一致、媒体字节不变，凭据为 `GENERATOR_ALIGNMENT.json`；不声称修复了未知 AE 属性行为。

原生每版 802 帧回读显示搜索单调向下、两处途经速度不再近零，比较段相机/提取组位置稳定，来源原位交还保持。最终媒体完整解码、时戳、画面包与完整声音核验通过；A/B 解码音频一致，三条 take 的最低相关系数约 0.9999956。120° / −60° 快门的实际开关对照在运动帧产生差异，所测静读帧无超过 1 色阶的显著差异。相关既有回归 41 项通过，70 个受保护文件保持原字节。程序检查、模型图像抽查、人工原速审美/试听分别记录，后两项人审仍 PENDING，不接入主片默认值。

宿主启动、局部 Time Remap 构建错误及原生预览/渲染自动切换活动合成的记录均保留。每次先检查真实结果；已完成首段没有重渲染，失败构建以原服务器 recovery 凭据继续。本次续作从已经完成的 A/B 媒体继续，没有重复制作。未改 ANSWER、冻结依据、主片消费者或并行 Research/Cinema 脏工作。

## B 词块阅读修订与 AE MCP 更新：2026-10-18

用户认可 B 的总体方向，同时指出放大必须像阅读一样逐行从左到右按词块接续，以及约 12 秒的携带词骤然回黑。本次另存 `G:/VideoMaking/motion-quality-r02`，原 B 媒体、AEP 和报告均保留。读取 AE 实际排版的 7 行后绑定 14 个明确词块；同块原词共用三帧升起、两帧停留、三帧回落的 100–104% 五次平滑函数，蓝色焦点使用同一包络。原 B 的相机与对象路径逐帧一致，未重新编排已认可的提取、比较和返回。

携带词在样片 12.125–12.875 秒渐变为原文墨色。仅在原交接时刻恢复原位颜色，虽然数值回读为正确值，实际预览仍暴露一帧缺字；将原位颜色接回扩展至快门采样边界后，再次原生预览及最终编码的 309/310/311 帧均有原词。这个结果只由实际画面验证，不以参数检查代签。初版颜色表达式维数错误、预览参数拒绝与修前画面均保留，未把失败记录删除或当作成功。

最终 A/B 均为 802 帧、33.416667 秒、3840×2160 / 24fps。A 保持原媒体字节，B 的四段共 192 帧重新原生渲染，另 13 段按不相交依赖及 SHA 复用；不是整条重渲染。最终 B SHA 为 `7b5da5fba6836cee54904a6fc511571c752ddd152671b8eba5642996e3c1c933`；可编辑 AEP SHA 为 `16aab4ee8e6d0094fc4b0033f7529ce729891a900f36a9bac6bc1f39ad832e9e`。原生顺序、曲线、802 帧状态、完整解码、时戳和三条完整声音通过核验，A/B 解码音频一致。19 个本轮保护文件不变。审片页含旧 B / 新 B 同帧对照、14 个峰值与归位连续帧；程序检查、模型图像观察与用户原速审阅分别记录。文案未改，仍须全文在聊天交付；新修订不继承旧 B 的人工认可，不接入主片默认 Rig。

按用户提供的原生插件更新本机 AE MCP 0.10.8→0.11.0。安装文件与官方包逐项核对：720 个面板文件一致，原生插件 SHA 与发布校验一致，204 个稳定用户配置文件安装前后不变，旧面板完整备份。实际初始化、16 个工具、ExtendScript 读回与 native-aegp 读回通过；上述新渲染也实际使用新版宿主。最小客户端适配只处理独立执行来源元数据和显式工程绑定，保留独立宿主身份及共享占用；相关 `test_ae_bridge_envelope / test_host_ownership / test_authored_episode` 共 50 项通过，未运行全仓测试。

自动启动仍遇到既有 CEP 错误，用户手动打开空白 AE 后工作恢复。工程切换的即时回读曾被旧绑定拒绝；分别独立读取实际工程或空白状态、核对已完成操作凭据，再以原占用 token 明确 reconcile，未重复打开/关闭操作。最终用户打开的 AE 保持运行且回到干净空白工程，共享占用已释放。安装、备份、真实验证及限制详见本机 `G:/VideoMaking/tooling/ae-mcp-update-v0.11.0-20261018/INSTALL_RECEIPT.json`。

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

## 2026-10-18 · 关键分歧点资源分配增量

### 基线与冲突

已 fetch 最新 main：远端 `3f30b668` 已包含在本地 `aa7157bf`，本地领先 4 个提交。未重置工作区、提交或覆盖既有工程。审查实际 `AV_AUTHOR → compile_clock → authored_native → authored-episode.jsx` 调用，而非以旧 Package 文档推断当前生产。

| 冲突 | 实际证据 | 本轮修改 |
|---|---|---|
| 普通项也获得完整复杂动作 | 原生模板的所有 compare 都执行 candidate flight、source lift 和空间退出；SC04/05 与关键 SC03 使用相同主要阶段参数 | 普通项消费 `in_place_check`，原文和完整选项保留，去掉提取/飞行；关键项保持原生比较 |
| 选题没有可消费的分歧分析单元 | 旧 PA/HP/DP 等评分和短格式 Pattern 不包含绑定具体候选、困难与方法收益的单元 | `rank_teaching_focus` 作为当前 Selection 补充，使用同一暂定价值函数驱动导演比较停留 |
| 前台完整展示与后台完整核验混同 | 8 个选项均为完整 compare 场景；camp C 29.292 秒，A 19.5 秒 | 全部完整 candidate checks 保留，前台按 quick/brief/focus 分级；必要阅读停留不缩短 |
| Audience 意图泛化 | 各 compare 的 audience_intent 原为同一句“方法表达修订” | 当前 handoff 绑定真实困难、原文、方法与前一场景的候选状态 |
| 只改文案容易留下等长无声动作 | 编译时钟固定累加全部阶段 | 同一消费者改变镜头、声音起点、字幕及裁决时间；24 条完整声音保持原字节 |

### 数据与调用链

新增 `creative_os/teaching_focus.py` 的严格输入校验和资源消费者；作者输入只增 `teaching_focus`，不改 ANSWER、冻结 Bundle、终审或发布契约。`units` 支持单项、两项、多项；仅恰好两项时报告可选 Critical Option Pair，不推断“只剩两个”。`difficulty_basis=EDITORIAL_HYPOTHESIS` 与 `student_difficulty=UNMEASURED` 分开保留。

现有 `adaptive-episode/run.py check` 调用 Selection 评分；`script / voice / align / prepare / build` 对新制作要求此输入；`checked_author` 复核全部 source/action/terminal，`direct_scene` 和共享 `teaching_value_points` 分配真实阶段，`prepare` 产出资源报告与真实候选状态的 Audience handoff；原生模板消费轻量/关键分级，`audit` 检查真实层和状态。历史输入仍可读取；旧短片运行器不变，且不作为当前主片入口。

### 真实冻结资产对照

私有 `critical-focus-r01` 基于既有 Fitbit / 写作营两道冻结题，使用当前原句、同一 R03 实际执行和完整整题审阅。生成器为 `scripts/critical_focus_demo.py`，对比操作 `--compare-only` 会验证所有保留内容的来源和音频字节。完整新口播已发送，语义/文案/画面/听感审核均不借用旧版认可。

| 资源指标 | 修改前 | 修改后 |
|---|---:|---:|
| 实际完整声音编译的整片时钟 | 278.458333 秒 | 251.125 秒 |
| 完整 take 数 | 29 | 24（全部原字节复用） |
| 原选项完整核验 | 8/8 | 8/8，同一引用与结果 |
| 原文、方法引用、必要 reading_path | 全部保留 | 范围与路径一致；24 词块总览从 2.2 秒延长到 8 秒 |
| 原文阅读停留 | 原参数 | 原参数，不为密度加速 |
| 复杂比较/回放场景 | 9 | 5；其余 4 个改为原地轻量核对 |
| Fitbit 关键比较/回放时长占比 | 43.45% | 59.13% |
| 写作营关键比较时长占比 | 71.15% | 77.24% |

写作营没有强行制造二选一：C 保留嘉宾分享/往届文集两处核验；B 仍是跨段作品归属难点；A/D 随后连续对照。最后一句保持“**四项检查完，选D。**”。上表是编译资源对比，不是新媒体观看结果或学生学习数据。

### 验证及剩余事项

最终相关 152 项单元/集成检查通过（包含本轮关键分歧、防止均摊、引用失效、原有 Episode、Audience、发布、声音、阅读和宿主占用检查），私有 `REGRESSION_RECEIPT.json` 保存命令及实际结果。新增负例覆盖未核选项、隐藏决定性证据、关键项被改为快速略过、方法失效、伪造实测难度、候选数量固定化、读速被缩短，以及分级未进入实际时钟。宿主已退出时报告明确的缺失状态，不再误报 JSON 解析失败；此检查不重启宿主。12 项旧资产及本轮交付绑定核验通过，原稿导出与审阅页所用文案副本一致。保留对新原生层和原文交接的现场检查，程序通过不签审美。

新分级镜头已完成完整原生合成构建、160 层读回、13 阅读时段/117 词块，以及两套合成中的 10 个限时证据颜色实例检查。SC05 实际输出 205 帧、8.541667 秒、3840×2160@24fps；全部解码、PTS 连续、原生画面包与完整声音对齐通过。画面帧检查另发现并修复标签重叠和残留颜色，不能用原先的程序 PASS 掩盖这些问题。人工原速观看与完整听审仍待完成。2 题验证版仍短于约 5–8 分钟整期目标；下一轮应补有方法收益且已冻结的内容，保持一次有价值的局部慢放，不拉长普通项。跨段 B/C 仍有可压缩的重复访问，可在原速观看后进一步合并视觉阅读接力，不能直接删除支持其判断的原文。

实际工程：`G:/VideoMaking/critical-focus-r01/media/MAIN_FILM.aep`；局部视频：同目录 `SC05_LIGHT_CHECK_4K24.mp4`；原速审阅和最终编码接触表：`G:/VideoMaking/critical-focus-r01/REVIEW.html`。此前词块整题修订另存于 `motion-quality-r03`，已有 1104/3269 帧，等待恢复已退出的 AE 后续渲；本轮局部样片不冒充该整题片。

## 2026-10-18 · 用户恢复 AE 后完成整题续渲

上节停止点现已完成。用户手动打开空白 AE 后，先核对宿主身份、已保存 AEP、原生实现与前 23 个完整分段的绑定，再接续 `motion-quality-r03`。没有重新构建工程或重渲已完成的 1104 帧。最终得到 **136.208333 秒、3269 帧、3840×2160@24fps** 整题，以及同版可编辑 AEP；原 R04 工程 hash 保持不变。

| 核验层次 | 实际结果与范围 |
|---|---|
| 原生实现 | 当前完整行检查重新读回 8 个阅读时段、68 个词块和 1 次题干交接，PASS；不是仅检查作者声明 |
| 编码视频 | 3269 帧完整解码、连续时间戳、无整帧黑场；整题视频包与 AE 原生拼接画面一致 |
| 声音 | 13 条完整 take 按实际位置核对，最低相关系数 0.9999936；无裁切或变速，不代签读音与听感 |
| 对照片 | 802 帧短 B 来自同一原生整题的精确切帧及末尾停留；复核其前段来源与整题分段相同。旧 A/B 原字节另保留为对照 |
| 最终画面检查 | 实际编码交接逐帧图、全题接触表及搜索/出版段/复看词块峰值接触表已检查；题干随镜头连续进入，仍需人工原速判断速度、模糊与周边文字遮挡 |
| 工程依赖 | 实际 14 个 FootageItem 文件存在，只引用 R04 和 copy-v3 的保留声音目录 |
| 宿主恢复 | 已保存本版，恢复为用户本次打开的空白工程；AE 保持运行、无未保存改动、无渲染任务 |

交付入口为 `G:/VideoMaking/motion-quality-r03/REVIEW.html`，视频为同目录 `media/B_COMPLETE_QUESTION_4K24.mp4`，工程为 `media/MOTION_QUALITY_AB.aep`。`COMPLETE_QUESTION_MEDIA_QA.json`、`NATIVE_QA.json`、`NATIVE_FOOTAGE_DEPENDENCIES.json`、`ENCODED_STILL_INSPECTION.json` 和 `RESTORED.json` 分别记录各类证据。完整 13 句口播已在聊天独立发送，本轮续渲没有改稿，结尾仍为“四项检查完，选D。”。

`critical-focus-r01` 仍是当前主片；上述整题保留较早讲解顺序，只补完先前词块和题干交接修订。没有将其媒体、人审或完成状态转授给新主片。原速审美、完整听审与新文案认可仍分别 PENDING，未发布。

## 2026-10-18 · 历史产出归档

按用户明确要求交由 `gpt-6-luna` 子代理执行。本项目旧视频、工程、预览、分段、收据及未跟踪交付副本已收拢为 **96 个 ZIP、96 份清单、71 组独立历史产出**，索引为 `G:/VideoMaking/_archive/2026-10-18/ARCHIVE_INDEX.json`。27 个旧展开交付目录中，2 个与原 ZIP 完全一致；另外 25 个包含原 ZIP 没有的本地文件，因此分别补充完整包，原 ZIP 亦保留。源码中已跟踪的 2 个 ZIP 和其校验资料原位保留。

各包逐成员读取、字节数和 SHA-256 校验由子代理完成，之后才迁移原件。父代理又检查了 96 个包的存在、记录大小、全部声明成员及恢复路径映射，待处理成员为 0。有些包使用 `local-` 前缀，恢复说明明确先进入暂存区、改回原目录名；混合包按成员到原路径的明确映射恢复，不能直接解压覆盖。

自动审批曾拒绝对旧 `motion-quality-r02` 目录递归删除，仅返回“策略阻止”。没有换工具重试删除；旧原件改为可恢复迁移到 `retained-originals`。E 盘迁入归档的源字节为 5,201,629,291，记录时可用空间为 5,254,746,112 字节；G 盘内搬迁及新增压缩包体积不计作释放空间。

三份真实计划 `critical-focus-r01 / mainfilm-integration-r04 / motion-quality-r03-copy-v3` 在全部迁移后重新验证通过；14 个当前 AE 素材存在且 hash 不变，11 项受保护绑定不变。当前 R03 AEP 因授权续渲逐批保存而发生的 hash 更新单独记账，没有伪称工程字节未变；源 R04 AEP 和新主片 AEP 字节保持一致。当前主片指针保留，旧媒体入口指向归档中的原字节，能力索引 39 个历史路径可解析至对应 ZIP 成员。详细证据见当前 R03 目录的 `FINAL_POST_ARCHIVE_QA.json` 和 `ARCHIVE_INDEX_QA.json`。PR 只读连接未响应，未对 PR 作任何改动；不据此声称检查过 PR 的活动项目。

## 2026-10-18 · 文章语义词块进入当前主片

用户明确反馈“把本应连在一起的短语拆开了”。实查默认 Rig 在每条 AE 排版行内按词数均分，导致 `high school writers`、`take part in` 和 `GrubStreet’s previous summer programs` 等被拆。新增文章词块编辑职责：作者先阅读完整冻结文章并标注连续意群，同一入口 `chunks` 编译精确原词、源文 hash、保护短语及稳定区间；`prepare → AV_PLAN.worlds.blocks.reading_chunks → cmKeepChunks / cmMappedChunks → audit` 是实际调用链。没有部署自动语言模型，也不以格式校验冒充自然语言判断。

新修订 `critical-focus-r02` 继承 R01 的 24 条逐字文案、完整 take、字幕、场景顺序、全部证据/终判引用、教学资源分配和 **251.125 秒 / 6027 帧**时钟。两篇完整文章共 145 个意群，AE 原生 noBreak 保证整块换行；13 个阅读时段、113 次焦点在代理与 4K 主合成中均已实际读回。原来被拆的受保护短语出现次数由 25 降为 0，含复读窗口；这一数字只衡量显式保护短语，不声称所有英语划分已经人工认可。全部 24 句文案已在聊天独立发送，未改稿。

相关 92 项测试通过，覆盖原词缺漏/重排、短语误拆、陈旧划分、摘录边界重切、原生逐行覆盖、颜色/题干交接及共享宿主恢复记录；未运行全仓测试。实际预览已检查完整短语及布局；可播放验证选择本版主片连续 SC09L → SC13 → SC12，覆盖写作营全部 8 个阅读时段和 5 条完整声音，最终编码与人审状态分别记录在本版私有收据。

渲染期间保留两次原生错误、部分状态检查及内存耗尽凭据。已完成的 1296 帧逐段 hash 复用。用户手动重开空白 AE 后，确认旧宿主/控制进程已退出、新宿主确为空白，并保留旧占用记录后取得新占用；仅移除精确匹配的失败队列项，从缺失范围续渲。没有把原失败调用宣称完成或盲重放已完成画面。恢复收据的 Path 序列化错误已修复并有回归；此前原生恢复成功但记账失败的调用没有重执行。

原 `critical-focus-r01` 与用户查看的 `motion-quality-r03` 共 6 项相关受保护输入/输出 hash 保持不变；本轮不扩张为整个历史归档审计。现有 Swiss Cognitive POV、3D 相机、下移扫读、104% 平滑焦点、提取/归位和声音决定继续继承。词块自然程度、原速观感和听感保持 PENDING；整期 251.125 秒的完整 4K24 输出仍未完成，不借局部片宣称整片通过。

最终交付：`G:/VideoMaking/critical-focus-r02/REVIEW.html`、`media/READING_CHUNKS_4K24.mp4` 与 `media/MAIN_FILM.aep`。实际 1833 帧 / 76.375 秒 / 4K24、8 个阅读时段、5 条完整声音（最低相关系数 0.9999946375），完整解码、时间戳及原生画面包保持均通过。8 张编码接触表、5 处易拆短语峰值及归位采样帧已由模型检查，50 张连续归位帧可在审阅页逐帧查看；这不是人工播放通过。渲染后两合成的全部 145 处原生 noBreak 和原词再读回通过，队列为空。AE 已恢复本次用户打开的干净空白工程，占用释放；当前工程 SHA 为 `11d116dd3e95c7f9ca7890261a14c59eb2dcf2b37f41413f7803a4fa1bc389e6`。`READING_MEDIA_QA / POST_RENDER_NATIVE_QA / ENCODED_FRAME_INSPECTION / RESTORED_HOSTS` 分别记录，不互相替代人审。

## 2026-10-18 · 用户确认后对齐仓库

用户确认“可以，把这些对齐到仓库”。本次整理同一制作链的 55 个文件：默认入口、文章词块编译/原生排版/审阅、共享阅读与题干归位、关键分歧点资源分配、AE MCP 0.11 兼容、既有动效实验来源以及对应回归和文档。`creative/README.md` 仅纳入导演原则一段；独立 Research/Cinema 的工作区改动继续保留。原题、声音、MP4、AEP、预览及本机指针仍在私有目录。

从 Git 暂存区逐文件导出干净副本验证，排除本机未提交依赖：92 项本链回归及 38 项 Audience / Free Showcase / Voice Delivery 相邻回归均通过，共 **130 项**。32 个待提交 Python 文件语法检查及 AE Schema 生成检查通过；未运行全仓回归。缺少 Windows 子进程创建标志的平台按 0 处理，使新增宿主缺失回归可在 CI 的非 Windows 环境执行；原生 AE 的平台要求不变。

额外检查发现 `build_video_schemas --check` 的既有基线差异：`schemas/frozen-asset-bundle.json`、`video/schemas/content-candidate.json`、`video/schemas/video-package.json`。生成器、三个输入及五个输出共 9 个文件已与提交前 HEAD 逐字核对一致，该失败并非本次制作改动引入。保留原始 Schema 和独立待办，不能把专项通过记作全仓 CI 通过。此次入库及本机指针的实际提交绑定另记于私有 `local-data/repository-alignment/2026-10-18`。
