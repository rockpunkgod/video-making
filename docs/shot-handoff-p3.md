# P3：镜头后端与原生动态预览

基线：main `3f30b66`，接续 P2 `13dec4e`。不修改 ANSWER、Registry 或已有视觉规范。
此处 P3 指 P2 排版之后的镜头接入阶段，不是早期计划中同名的音乐包装阶段。

## 已实现

- `creative_os.shot_script`：统一原文对象、精确字符切片、动作及帧时序。
  原文和布局必须一致，重复或悬空引用、遗漏原词、篡改原词均拒绝。
- 排除与答案复用 `audit_candidate_events`。画面不能给另一个选项套用排除凭证，
  不能把只剩一个候选当作答案闭合。整个选项撤离必须有对应的已绑定动作。
- 明暗状态检查：不能重复 dim/brighten；原词必须先 lift 才能 compare/return；
  归位未结束不能恢复亮场。同一目标的动作不能重叠。
- `camera_plan`：读取作者指定的焦点窗与认知状态，返回窗口中心、边界与原有速度档位。
  不搜索答案、不选择证据，也不声称已验证 AE 的实际速度曲线。
- 内部稿无需 `spec_sha` 自校验、A/B 强制或人工 PENDING 字段；精确原文引用继续保留。
  这不是发布接口，`public_render_ready=false` 固定返回，现有发布门未改。
- `shot-handoff-preview.jsx`：独立原生 AE 验证消费者，执行一个原词片段的
  locate → dim/lift → return → brighten。不是完整通用镜头模板。

## 输入与运行

`shot-script/v1` 最少字段：`fps / duration / objects / targets / actions`。
对象包含 `id / text / source_ref / layout_id`；source_ref 使用现有
`asset_id / pointer / sha`。target 包含 `id / object_id / range / text`，
range 始终指向未归一化原文 Unicode 字符位置。
动作包含唯一 `id / action / at / targets`；dim/brighten 不带 targets。
时长来自现有 style；排除另带 `candidate_event_index`。
`candidate_events / answers` 原样遵循已有机械动作审计契约。
`focus_cues` 包含 `at / object_id / window_index / state`，state 为
read/search/recognize/hit/end。

本地 request：

```json
{
  "script": "<local script.json>",
  "bundles": {"<asset id>": "<local frozen bundle.json>"},
  "layouts": {"passage": "<typeset-plan.json>"},
  "style": "<existing style-v1.json>",
  "preview": {"layout_id": "passage", "window_index": 0}
}
```

```text
python -m creative_os.shot_handoff request.json local-data/p3/handoff-new
python scripts/prepare_shot_preview.py request.json local-data/p3/native-new
```

所有输出目录必须新建；原生 preview 限于忽略的 local-data。
在 AE 运行生成的 build.jsx：先保存当前会话副本，再建立独立工程。
脚本回读实际字形宽度，保留 P2 行序，并按最大行宽居中整个正文块。
片段提取透明无底板；原世界 opacity 始终不变，通过灯光降低亮度与原生景深分离。
新工程中的 `P3_PREVIEW_4K` 用于原生导出，旧工程不覆盖。
再运行同目录 `render.jsx`，它核对工程路径和生成时记录的合成 ID，
禁用其他未完成的队列项，通过现有 H.264 模板导出；已有 MP4 拒绝覆盖。

## 本次可见交付

本地 `local-data/p3/native-r3/`：15 秒、3840×2160、24 fps，无声动态小样。
使用既有 Bond 历史冻结原文第一页及 P1 已使用的原词片段；只验证阅读、识别、提起、归位。
不输出答案、不新增教学判断，也不把历史素材升级为可发布资产。

时序：0–3s 阅读；3s 短暂高亮；4.5s 明暗转换与提取；11s 归位；12s 恢复阅读。
原生首轮发现折叠变换导致嵌套灯光失效，r2 关闭折叠变换并修正归位深度。
r2 导出又发现队列第一项仍指向旧合成；r3 显式关闭保存后的旧会话并重建工程，
按新合成 ID 导出。最终 MP4 完整解码 360 帧通过，编码后 3.5/7/11.5/13 秒抽帧核验。
这是 1080p 作者合成嵌套放大到 4K 的现有工程约定；不是新建原生 4K 排版坐标系。

## 明确未完成

- Native preview 仅执行上述五步，没有悄悄忽略动作并假装支持 compare/eliminate。
- 相机焦点数据已生成；动态 preview 暂用固定相机加真实景深，尚未执行通用相机轨迹。
- 灯光强度降为原来的 25%，不等于经过标定的 Rec.709 亮度 25%。
  原生景深替代离线模糊，尚未宣称达到精确的 3.2px。
- 尚未迁移整期生成器，也未接入本轮 Premiere、配音、音效或音乐。
- 38 项相关单测通过；全仓回归未在此轮运行。视觉体验仍待用户审阅。

已完成的是可运行后端和一条原生动态技术样片，不能将它记为完整 P3 生产系统验收通过。
