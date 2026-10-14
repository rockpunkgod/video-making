# P4：两题内部完整代理片

接续 `ca9bb05`，仓库主线基线 `3f30b66`。代码继续在 `redesign/p2-typeset`。
交付是内部粗片，不认证视觉方向、自然口语或公开发布；教学事实及 Registry 未修改。

## 单一路径

```text
显式冻结 Bundle + 当前提供的 Status
→ 现有 AUTHORED_SCENES + voice-delivery/v1
→ episode_build（证据、候选与闭合检查；完整声音决定时长）
→ AE 原生画面与逐字字幕
→ Premiere：V1 画面，A1 独立配音，A2 短提示音，A3 记忆卡两音提示
→ 原生导出 → 两遍响度处理（视频流复制）→ 1080p 内部审阅
```

命令行：

```text
python -m creative_os.episode_build <本地 request.json> <新 local-data 输出目录>
python -m premiere_production.episode_audio <EPISODE_HANDOFF.json> <新 audio 目录> --picture <AE picture.mp4>
python scripts/loudnorm.py <Premiere raw.mp4> <新 review.mp4>
```

request 明确提供 `style / font / fallback_font / sources{bundle,status}`、
`authored_copy / voice_delivery / edit[]`。
每镜头包含 `id / source / kind / display_refs / voice_ids`，可以声明阅读和停顿时长。
evidence 镜头还包含原文 `range` 和 producing `action_ref`；只能提取该实际动作已有的证据。
comparison 镜头声明 `action_index`，候选及效果直接投影原动作。
result 镜头只有上游已闭合答案并完成全部动作覆盖后才能声明 answer。
两个帧时间域均使用 24 fps；源 WAV 必须是已有 48 kHz mono PCM16 和帧边界静音补齐版本。

生成的 `build.jsx` 与 `render.jsx` 在 AE 执行。原生最终测量字体宽度，保留 P2 行序；
纸与原词均采用现有 style 的参数，原词投影保留源字符范围和原图层身份。
不另建配色、动效规范或 TTS 引擎。
新工程与输出拒绝覆盖，当前 AE 会话先保存副本再关闭。
Premiere 接入由现有 MCP 完成，本地 `PREMIERE_RECEIPT.json` 保存回读、素材清单、声音属性和导出结果。
同时输出 `P4_PREMIERE.xml` 作为可编辑交换文件；本次实际成片未用它代替原生 Premiere 验证。

## 当前真实素材与范围

- 2024 全国猫标题题：只排除 D；结尾回到 A/B/C，没有填入答案。
- 2021 浙江 Bond 标题题：已有 A/B/D 排除、C 核验及冻结答案 C。
- 使用原有 19 条逐字配音，全部为待试听状态；未训练、重生成或变速。
- 使用既有冻结方法 memory_line 作为两秒记忆卡；不显示方法编号。
- 本轮音效是原创短干声，记忆卡用原创两音提示；没有第三方录音样本。
  原肖邦录音许可未确定，未作为本片音乐；两音提示不能记成完整钢琴音乐制作已完成。

实际生成：24 镜头，149.541667 秒，1920×1080 / 24 fps。
五次候选判断均有两秒快走与配音回看，明确显示“原速／慢放”。
回看使用 `replay_of` 绑定之前同一个冻结动作，不重复计入候选变化。
先完整审阅代理片，再进入 4K 母版与正式发布审核。
真实题、工程、声音及视频只存在本地忽略目录，公开仓库只提交代码与合成测试。

## 验证与实际限制

50 项相关测试通过：包括绑定变化、撤回/替代阻断、闭合不足阻断、另一选项不能借用当前动作、声音复用、回看不重复决策、
不合法时长、字幕词文一致、原 PCM 保留及 Premiere 交换文件独立声音结构。
全仓回归未在此轮运行，不宣称通过。

在真实 Premiere 回读了 19 条声音的时间、完整源范围及非反向属性。
最终编码后逐条比对源音频，不以单纯“有波形”冒充正确配音；实测约 1024 samples 偏移，
小于一帧，仅作为编码信号核验，不等于自然听感通过。
字幕切分逐字一致，分句时间为估算，未声称完成强制对齐。
响度目标为 −14 ±1 LUFS、真峰值 ≤−1 dBTP；实际数值见本地 loudness 报告。

当前仍是完整流程粗片：镜头连接采用统一空间与剪辑接续，尚未实现全期无切口连续镜头。
本轮是逐次判断的快走加局部回看，并非整道题完整原速之后再重放整道题；
双速电影体验是否成立仍由用户审阅，不能从程序通过自动推出。
冷开场复用旧 VO，记忆卡复用冻结文本；口语、判断爽点、局部慢放与片头包装仍需人工审阅。
本次只核验当前请求明确提供的状态清单，不能自行感知尚未提供的外部撤回。
`final_voice_accepted=false`、`public_render_ready=false`，不写入教学或发布批准。
