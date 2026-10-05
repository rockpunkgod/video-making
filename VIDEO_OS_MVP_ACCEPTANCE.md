# Video Production OS v0.1 — V0–V7 验收

日期：2026-10-05。基线：`18afe8a`。本报告只确认工程流水线，不认证英语语义、正式 Case、方法有效性、Efficient 或 Signature。

## 独立验收结果

| 项目 | 结果 | 含义 |
|---|---|---|
| Engineering Pilot | **PASS** | 3 道真实 AI-reviewed 题完成冻结消费、门禁、评分、排序、导演、Final Draft Package、Manifest、重放与失效传播 |
| Semantic Certification | **PENDING** | 没有新增独立人工教学认证 |
| Source Release | **PENDING** | 原题仍为本地研究／再发行未核实；最终展示未获人工放行 |
| Editorial Release | **PENDING** | 最终 Hook、口播、字幕、画面仍待人工编辑审核 |
| PUBLIC_RENDER_READY | **false** | 未自动开放正式渲染或发布 |

## 三条真实 Engineering Pilot

| 资产 | Scope | 实际演示范围 | 估算时长 | 重放／失效传播 |
|---|---|---|---:|---|
| 2025 I q36 / F01 | method_action_demo | 现有句型分组动作；不报整题答案 | 73 秒 | PASS / PASS |
| 2025 I q59 / G01 | method_action_demo | 现有空位导航；不把词形答案归因给 G01 | 86 秒 | PASS / PASS |
| 2021 I q26 / R02 | method_action_demo | 新的 style-only 限定动作；不复用旧混合归因 | 78 秒 | PASS / PASS |

选材顺序：审阅记录干净程度 > 教学清晰度 > 可视化可行性 > 品牌优先级。未为了 R01 数量使用已撤回记录。R02 Bundle 同时保留旧 Review 的 WITHDRAWN 历史与新的 ACTIVE Review。

以上时长是程序估算，不是实测成片。真实题、审阅全文、Bundle、Package、内部 AE Contract、模拟撤回记录与完整审阅稿均留在被 Git 忽略的 `local-data/video-os/pilot/`。公开仓库不包含原题全文。

## 已落实的边界

- ANSWER 只增加只读导出接口、冻结／状态契约；未修改 Registry、Case、分析器、Renderer 或任何原始审阅事实。Pilot 前后保护文件 hash 一致。
- Video OS 仅使用冻结结构数据；不读取教学 Markdown、Registry 或题库补事实。Claims 精确绑定自己的 Method、Action、Evidence 和 Review。
- Canonical JSON 明确 UTF-8、键排序、无无意义空白、保留数组顺序、missing 不等于 null；区分语义、展示、内容和 envelope 指纹。
- 固定顺序为 Draft → LanguagePolisher → Diff Guard → Timing → Final Draft → 教学／来源展示／编辑审核 → Locked Package。
- copy_lock 绑定最终文案；Source Review 绑定实际显示文字、片段、图片 hash 和署名；审核后变化撤销旧资格。
- 分别输出 teaching_stale、source_release_stale、editorial_stale。新 Review 不自动复活旧包；已登记的渲染／待发布资产继承父依赖失效。
- AI-reviewed 可用于 Engineering Pilot，但不自动进入教学发布。human_reviewed/human_certified 只能来自显式上游凭证；人工审核按拟公开内容进行。
- unknown 时效不计零；内容评分与生产可行性分开；raw/portfolio 分开。ranking_policy 0.1.0 标为 provisional。
- Claim Guard 明确为确定性 lint，不是语义认证器。没有加入虚构热点、错误率或教学效果数据。

## 验证证据

- 全量回归：`python -m unittest discover -s tests -v`，**424 项通过**，约 265 秒。日志：`local-data/video-os-delivery-regression.log`。
- Video OS 专项与独立解压运行：**49 项通过**；覆盖规范 hash、只读导出、Blind 及历史阶段隔离、撤回依赖、AI/人工分层、helper 无答案、多方法 Claims 与各自 Review、Challenge 不泄漏、三个发布门禁、文案及来源锁、润色边界、动作及可视产物不得遗漏、重放与交付。
- Registry 与原生成资产：`python -m answer_engine validate`，82 methods / 20 source documents，PASS；generated_assets PASS。
- 新契约生成一致性：`python -m scripts.build_video_schemas --check`，PASS。
- 真实本地流水线：`python -m scripts.video_os_pilot`，3 条 PASS，受保护上游文件不变。
- CLI 已实际验证 export-asset、export-status、produce、validate、review、refresh-upstream 和内部 handoff；review 后的 Manifest 确认绑定最终包。正式公开 handoff 拒绝路径已实际执行；合成三钥匙正向路径有测试。
- 完整解题／Trap Reveal、边界演示／Method Demo、Anti-Rule 的合成正向契约检查通过；Method Duel 与独立 Challenge 的正向路径纳入专项测试。它们均不构成真实教学认证。
- 交付 ZIP 逐文件 SHA256 与 CRC 校验通过；独立解压目录通过 Registry、契约及49项测试，未携带私有题面。生成方式见 `scripts/package_video_os.py`。
- `git diff --check` 通过；真实题生产文件确认被 `.gitignore` 排除。

## 当前限制与停止点

这是 V0–V7 Engineering MVP。真实教学、来源和编辑审核仍需按公开队列完成；本轮没有自动制造任何批准凭证。

状态刷新是同步消费调用方提供的最新清单，不是远端实时监听；旧清单无法证明之后没有撤回。v0.1 LanguagePolisher 只自动允许有限的非教学衔接语调整，拒绝任意教学改写。AE Contract 仅文本模式，图片展示通道尚未开放，也未制作 AE 模板或接入实际 Astra 服务。

停止于 V7：未自动进入 V8 正式 AE、自动发布、Radar 或 cheat-on-content。使用说明见 [docs/video-os.md](docs/video-os.md)，机器可读脱敏结果见 [evaluation/reports/video-os-mvp.json](evaluation/reports/video-os-mvp.json)。

逐项完成审计见 [docs/video-os-completion-audit.md](docs/video-os-completion-audit.md)。源码交付包位于 `deliverables/Video-Production-OS-v0.1.zip`，包的校验记录另存同目录；真实内部审阅稿位于 `local-data/video-os/pilot/PILOT_REVIEW.md`。
