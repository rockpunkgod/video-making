# Video Production OS v0.1

> 适用范围：V0–V7 旧 Package / Pattern 契约及历史回放，保留原 API 行为。当前多题 FREE_SHOWCASE 从[当前生产工作流](workflows/CURRENT_PRODUCTION_WORKFLOW.md)进入，不受本页 30/60/90 秒短格式规则限制；旧 AE 契约也不等于当前原生执行器。

本模块消费 ANSWER Frozen Asset Bundle，不读取 Registry、课程 Markdown 或原始试卷来补教学判断。Python 3.10+，使用仓库现有 jsonschema 依赖；源码目录运行或 editable 安装。

## 流水线与运行

```text
Frozen Asset + 当前状态清单
→ Engineering Teaching Gate + Source Internal-use Gate
→ Candidate → 显式编辑评分 → 排名 → Pattern
→ Director → Draft Package → LanguagePolisher → Diff Guard
→ Timing Resolver → Final Draft Package
→ Teaching Release → Source Display Review → Editorial Review
→ Locked Package → AE Contract
```

Engineering Pilot 到 Final Draft 即可完成。公开输出另外要求 Teaching、Source Display、Editorial 三把钥匙均 PASS，且当前上游仍有效。内部 AE 契约带 `internal_engineering_only`；它不是正式 AE 模板或发布凭证。

```powershell
python -m answer_engine export-asset export-request.json
python -m answer_engine export-status export-request.json
python -m content_os produce production-request.json --output local-data/video-os/run
python -m content_os validate local-data/video-os/run/video-package.json
python -m content_os rank local-data/video-os/run/candidate.json
python -m content_os handoff local-data/video-os/run/video-package.json --statuses status.json --internal --output local-data/video-os/ae-contract.json
python -m content_os refresh-upstream catalog.json --statuses status.json --output refreshed-catalog.json
python -m content_os review video-package.json --statuses status.json --source source-review.json --editorial editorial-review.json --output reviewed-package.json
```

`export-*` 将 JSON 写到 stdout；其输入可为内联结构，也可使用 `{ "file": "relative.json", "sha256": "…" }` 显式引用。文件 hash 是解析后的规范 JSON hash，不是文件字节 hash。路径相对请求文件，不扫描其他文件。导出器不运行 Analyzer、不创建 Review、不修改输入。

export-request 顶层字段：`question`、`analysis`、`methods[]`（冻结方法卡）、`reviews[]`、`withdrawals[]`、`source`、`evaluation_phase`，可选 `current`、`history[]`、`provenance`。`source` 包含 usage_status、redistribution_status、source_reference、attribution_text。`current` 可显式提供 question_snapshot_sha 和 method_versions；缺少它只能描述所供快照，不声称观察了远端当前状态。

Review 必须内嵌完全相同的 question/analysis，或提供匹配的 input_sha256/analysis_sha256。未知 reviewer_kind 不升级。支持已有 AI bounded/action review 的直接投影；人工凭证必须明确声明 `reviewer_kind=human`、`independent_human_review=pass`。身份是上游凭证声明，本工具不认证真实身份。

history 中也保留 evaluation_phase；较晚阶段的历史不能混入 Blind/host_review。消费端复核 Review 原凭证与摘要、各项 fingerprint 和 presentation hash 一致性。方法特定 Review 只能绑定该方法的 Claims；每条实际动作都要在最终场景出现并保留其真实产物。

production-request 引用 `bundles[]`、`statuses[]` 的 JSON 文件路径；还需 `selections[]`、content_scope、pattern_id、duration_target、content_ratings 和 feasibility_ratings。每个 selection 显式指定 asset_id、method_id、action_ids；Challenge 另标 teaching/challenge purpose。示例请求由本地 Pilot 命令生成，不需手工阅读完整 JSON 再判断门禁。

```powershell
python -m scripts.video_os_pilot
```

此命令需要已有私有真实审阅文件，仅向 `local-data/video-os/pilot/` 写入请求、包、Manifest、重放、内部 AE 契约及模拟失效结果。它不新增教学 Review。缺私有文件的公开 checkout 仍可运行合成单元测试。

## 冻结契约和规范化 hash

Canonical JSON 定义为 Python `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)` 的 UTF-8 字节，再计算 SHA-256。

- 对象键按字典序排序，无无意义空白；数组保留原有语义顺序。
- missing 与 null 不等价；字符串换行、Unicode 内容保持原样，不偷偷修正题面。
- v1 使用 Python 标准 JSON 数字序列化；跨语言生产者必须匹配这些字节规则，禁止 NaN/Infinity。不声称实现 RFC 8785。
- `semantic_binding_sha` 覆盖题面、冻结分析、方法教学字段、审阅语义凭证、撤回及依赖状态，不覆盖生成时间和诊断路径。
- Review 语义投影排除 generated_at/created_at/updated_at/provenance/diagnostic_path/debug；原凭证及完整 hash 仍保留。
- `presentation_sha` 覆盖方法展示名、错误直觉、视觉公式、短版等展示投影。
- `content_sha` 排除 envelope 的 generated_at/provenance；`envelope_sha` 包括生成时间。两者不自包含自身 hash。
- 修改教学文本时不靠模型猜测“只是错别字”。仅明确的非消费诊断 metadata 变化免教学失效；Method Version、Evidence、Stop Rule 变化必须重新绑定。

Schema 由 `python -m scripts.build_video_schemas` 生成，`--check` 只校验。冻结包中嵌入现有 ANSWER 契约，消费端不依赖教学模块的实现。

## Claims、文案与来源锁

每条教学 claim 都包含 text、method_id、source_ref、action_artifact_refs、evidence_refs、review_refs；验证原文精确相等与方法归属，拒绝用 A 方法的证据为 B 方法背书。所有画面教学文字与口播均来自这些引用；实际动作产物保留于 method_visual。

`copy_lock` 保存 final_copy_sha、polished_from_sha、editorial_review_sha。最终文案 hash 包括口播、字幕、语义场景、内容字段和展示来源；审批 ID 本身不进入文案 hash。任何相关改动使旧 Editorial Approval 失效。

Source Review 绑定 `display_sha=sha(display_payload(package))`，包含实际场景文字与类型化可视内容的 displayed_text_sha、图片 hash、片段 ID、原文片段及署名。还绑定每个当前 source_sha。更换截图、显示内容或署名不能沿用旧批准。v0.1 只允许文本展示；图片数组非空会阻断交付，避免未实现的图片校验通道绕过来源锁。

人工 source-review 最少需 reviewer_kind=human、reviewer、review_id、status=pass、display_sha、source_bindings。editorial-review 还需 final_copy_sha、display_sha、teaching_bindings，以及 teaching_consistency、role、evidence、stop_rule、hook、subtitle、source_display、challenge_no_leak 八项 checks=pass。

Teaching Release 只消费 ANSWER 人工 Review 中的 release_review：status、content_scope、method_id、action_ids 和该 scope 的 checks。规则集中在 `content_os.candidates.RELEASE_CHECKS`；Video OS 不创建该凭证。接口接受凭证不等于此次真实 Pilot 已获任何人工批准。

LanguagePolisher 是模型无关接口。v0.1 默认 IdentityPolisher；测试适配器只可修改允许列表内的非教学衔接语。教学改写保守拒绝，不假装能自动认证任意润色后的语义等价。真实 Astra 未连接。

Claim Guard = deterministic claim lint, not semantic truth certification。它检查特定夸张表达、无 citation 统计与结构越权；PASS 不代表 Hook 的英语语义正确。

## 排名、失效与局限

七维均为 0–10 或 unknown；有分数必须有 rationale/evidence。总分为已知维度等权平均，同时返回 coverage；全未知为 null。可行性六维另算，越高越易生产。

ranking_policy version=0.1.0、status=provisional：内容 ≥8 且可行性 ≥7 为 P0，内容 ≥6 为 P1，其余合格内容为 P2。必要维度缺失为 HOLD，硬失效为 BLOCKED。TS 未知不作零分。raw/portfolio 分开，v0.1 portfolio 只提示重复、不改分或强制均衡。Candidate 排名的 public_priority 保守为 HOLD，正式公开资格由最终 Package 决定。真实发布 20–30 条之后才考虑用实际复盘校准阈值。

刷新输出 teaching_stale、source_release_stale、editorial_stale 和 reasons。撤回沿父依赖传播到已登记 Render/待发布记录；失效标记不自动清除，新 Review 需要新导出/生成。catalog 为 `{entries:[{id,parent_ids,artifact}]}`，验证依赖缺失与环。

这是同步消费状态清单，不是后台监听器。调用方负责取得当前上游清单；历史清单无法证明远端没有新撤回。缺状态时阻断放行；`validate` 只做历史结构检查。更换题面/分析得到新的 asset ID 时，调用方应同时导出旧请求相对 current 的状态，使旧包显式 stale，而非丢弃旧记录。

发现教学异常可运行 `python -m content_os teaching-issue <artifact_id> --reason "…" --refs <bound_ref> --output issue.json`。输出只供 ANSWER Review 接收，不改变事实或发送消息。

时长是中文每秒4字、英文每分钟150词、逐场景取口播和画面阅读较长值并加停顿的估算；目标按30/60/90秒升级，超限拒绝短格式。不替代真人口播、字幕排版或 AE Layout QA。

## 源码交付

`python -m scripts.package_video_os` 生成 deliverables 下的源码ZIP及校验记录。包含当前Git工作树的源码、契约、公开示例和文档，不需要先提交；排除私有数据、Git历史、旧交付包及缓存。包内 DELIVERY_MANIFEST.json 记录逐文件字节hash。独立目录运行需现有 requirements-dev.txt 中的依赖；源码目录支持Python 3.10+。真实Pilot材料只在原工作区，本包不携带。
