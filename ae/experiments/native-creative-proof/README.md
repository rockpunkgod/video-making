# AE Native Creative Proof

一个定制合成视觉研究入口：同一句原文中的两块附属片段绕附着端转开、脱离、暂存；原始核心对象闭合实际间隙，镜头回到稳定阅读面。当前 r7-wordcue-final 为 20.25 秒：显式给定的 after / that 先短暂突出，再确认整段范围，约 0.25 秒离轴、随后约 0.83 秒归位。保持 r6-sharp 的起刀间隔、镜头、主干闭合、原录音与阅读停留。主干一行，两块分别在给定视觉锚点的上方 / 下方归位。历史 r6-sharp / r5-fast 为 20.25 秒，Astra 建议版 r4 为 22 秒，r3 为 27 秒。实际结果及限制见根目录 `AE_NATIVE_CREATIVE_PROOF_ACCEPTANCE.md`。

这不是教学分析器、生产 Rig 或 V10。输入中的跨度、视觉附着关系和保护对象全部事先给定；五个呈现参数互斥，省略时仍沿用 27 秒时序。脚本不解析英文、不消费 Registry，不改变真实 Direction 的 `execution_allowed`，也不证明英语分析或方法收益。上 / 下归位只消费原合成锚点，不能把几何归位检查当作真实语法归属认证。r7 的词级提示有原文字符范围、scene SHA 与合成权威标记，不推断引导词或先行词。`SYNTHETIC` 标识始终显示，教学与公开资格始终为 false。

## 文件职责

| 文件 | 用途 |
| --- | --- |
| `synthetic-scene.json` | 显式合成原文、完整跨度分区、保护对象、暂存与恢复约束、固定 Scratch VO |
| `rhythm-r4.json` | 单独绑定 Astra 呈现修订：时序、暂存位置与原声音出场时间；不改变冻结 scene |
| `attachment-r5.json` | 上 / 下就近归位；沿用 r4 的 22 秒时序与原旁白 |
| `attachment-r5-fast.json` | 相同归位规则，剥离约快两成；保留阅读与结果停留，原录音只重新放置 |
| `attachment-r6-sharp.json` | 保留 r5-fast 的整条呈现时钟；只将两刀的物理转开 / 运输 / 落位压到 0.6 倍，连接线提前随抽离出现 |
| `attachment-r7-wordcue.json` | 原文字符范围绑定的合成词提示；保留整条时钟与五个录音，分开词提示 / 范围确认 / 快速离轴 / 归位 |
| `build.jsx` | 本片专用布局、三维附着 Null、薄载体与侧边、不同时间曲线、导向相机、原生景深 |
| `attachment-audit.jsx` | 原生采样字形中心、随锚点移动的落位、短暂连接线与结果可读层级；不认证英语关系 |
| `word-cue-audit.jsx` | 原生读取高亮的父级、字符绑定与几何，验证词 / 范围接力及断开后的准备提示退场 |
| `variants.jsx` | 同素材平面对照 A、只固定相机变换的 C、反向恢复检查 D |
| `run.py` | 冻结执行快照、MCP 原生回读、表达式检查、原生 TIFF 渲染与封装、不可覆盖的渲染凭证 |
| `guide.py` | 逐字绑定现有 `voice-delivery/v1`，48 kHz 帧边界补静音、Premiere 单镜头装配与原生导出 |
| `review.py` | 从实际视频提取覆盖全时段的顺序帧；不冒充实时观看或人工观感认证 |

## 当前镜头与动作

| 时段 | 主要动作 | 相机与焦点 |
| --- | --- | --- |
| 0–3.5 s | 原句正常可读，外围上下文作为参照 | 稳定整体阅读 |
| 3.5–4.7 s | 明确接近当前句 | 相机和观察目标分别移动，上下文产生视差 |
| 4.7–8.2 s | 4.7–5.0 s 突出 after；5.0–5.3 s 展开范围、静止确认；5.3–5.55 s 转开离轴，6.377 s 上方归位；6.9–8.2 s 随原主语闭合真正间隙 | 镜头与焦点方向沿用 r6-sharp，释放后回到主干 |
| 8.2–12.4 s | 原镜头交接；9.1–9.4 s 突出 that；9.4–9.7 s 范围确认；9.7–9.95 s 转开离轴，10.78 s 下方归位 | 镜头沿操作区域交接；不追逐暂存片段 |
| 12.4–15.75 s | 核心保持已有结果，阅读轴出现；连接线与载体淡去 | 单次连续返回稳定结果构图，没有退远再推近的第二高潮 |
| 15.75–20.25 s | 当前阅读结构稳定，外围信息仍保留 | 镜头、核心文字、焦点停稳；附属文字仍清楚可读 |

附属文字的 Source Text、原 ID、跨度和父级不变；暂存通过位置、旋转与对比变化实现。核心文字没有 Source Text 动画，没有复制一份“简化句”替换它们。摄像机 Focus Distance 是目标世界坐标到相机观察轴的投影，避免混用父级局部坐标或假定 Z 正负的远近含义。

两刀的动画因果关系均只消费合成输入中的已给定关系，不重新解析英语：

| 约束 | 第一刀 `aside-time` | 第二刀 `aside-map` |
| --- | --- | --- |
| attachment / pivot | 原跨度 8–26，挂接 `core-subject`；沿片段左端 `x=369` 转开 | 原跨度 42–68，挂接 `core-object`；沿片段左端 `x=1088` 转开 |
| motion path | 转开后连续运输至锚点上方；落点按原字形中心计算，随原锚点闭合间隙 | 转开后连续运输至锚点下方；落点按原字形中心计算 |
| constraint | 转动前附着端不平移；整段文字、保护跨度、来源与恢复位置保留；不拆散单词 | 同一约束；不移动主干来制造额外收益 |
| consequence | 片段离开阅读轴后，原主语于 6.9–8.2 s 闭合真正空出的间隙 | 句尾离开阅读轴，主干右界从外围尾段回到原宾语；不安排虚假的第二次接合 |
| rest state | 上方 96 单位、76% 尺度、72% 文字对比，回到同一阅读面；保留 deferred 与恢复路径 | 下方 96 单位，同一层级；不持续模糊或藏到远处 |

上下落位由世界坐标与原生 `sourceRectAtTime` 字形中心计算；没有修改源文案或输入锚点。连接线按两端实时 `toComp` 坐标绘制，抽离时出现，按该版绑定的阶段淡去（r5 落位后保留 0.5 秒、淡去 0.3 秒；r6 提前出现，但保留旧淡去时点；r7 第一刀等主干闭合后退场，第二刀按实际落位退场）。r7 的词底色交接给范围细线，原附着边与范围在断开时退场。最终不画箭头或树状结构。近远由本片实际相机观察关系决定，不概括成任何 Z 正负规则。

r6 的 `peel_motion_scale` 只作用于两块对象的 Position / Scale / Y Rotation / Z Rotation 及跟随表达式的释放权重，不压缩整条时间轴。两刀仍在 5.3 / 9.7 秒起动，间隔 4.4 秒；更早落位后维持停留，不提前下一刀。载体退隐、主干闭合、镜头交接与结果阶段使用原时钟；连接线随提前的释放出现，但仍按原阶段淡去。`verify_peel_timing` 读取实际 AE Position / Y Rotation 关键帧核验加速，不能只凭配置中的 0.6 宣称执行成功。本机关键帧存在不足 0.02 ms 的回读量化；校验只允许一个观测时间刻度 1/24576 s，整帧移位仍拒绝。

r7 把转开离轴与运输分开：前段由 `peel_detach_seconds=0.25` 控制，后段按 `peel_motion_scale=0.4` 的总运动预算分配。范围确认结束后，原片段转开并向上 / 下离开 56 个世界单位，再沿原归位路径停稳。词提示是独立 Shape，按字体度量定位在指定原文词后；原 Text 层没有拆字、复制或重写。词 / 范围 / 准备附着边按实际呈现秒数直接写关键帧，避免再映射一次时钟；carrier 从断开起短暂显现、落位后退去。`word-cue-audit.jsx` 要求词提示时范围与 carrier 不出现、范围确认时词底色已退去、断开后准备提示不残留，不能用配置代替原生回读。

r3 的节奏问题由实际关键帧确认：主语在约 10.9 秒接近谓语，第二片段离开后核心已连成一行；18.6–20.55 秒主语移约 131 px、谓语和宾语各约 130 px，属于整体再构图，没有新的显著阅读跨度压缩。不能把后段移动当作额外 Cognitive Payoff。用户要求优先打磨节奏与整体质感；r4 删除后置整体平移、重排原旁白，只做一次结果再构图。观看判断不因执行成功而通过。

本片使用 Classic 3D。其本机脚本 matchName 为 `ADBE Advanced 3d`，这个历史名称不等于当前产品界面中的 Advanced 3D。没有新增插件、外部三维链或生成图像；也没有把 Gaussian Blur 当作景深。载体是原生极薄平面和侧边，不是挤出网格；本轮未做灯光或接触阴影。

## 本机重放

使用已有 AE / JUNKDOGE 桥与 Premiere 桥。Python 依赖、FFmpeg、字体和原生导出预设均沿用现有安装；不自动安装或修改系统。每次使用新目录，不覆盖历史 take 或凭证；生成产物遵守用户的最近三版保留要求，输入 / 回读 / 故障记录继续保留。

执行前在 AE 中打开空白工程或本研究目录中的工程。MCP checkpoint 会保存当前载入的工程；因此工具会拒绝对其它工程做 checkpoint。真实旧样片不应作为本实验的起始工程。

从仓库根目录运行，例如：

```powershell
python ae/experiments/native-creative-proof/run.py build local-data/ae-native-creative-proof/r-next --revision r-next --attachment-r7-wordcue
python ae/experiments/native-creative-proof/run.py preview local-data/ae-native-creative-proof/r-next
python ae/experiments/native-creative-proof/run.py render local-data/ae-native-creative-proof/r-next --single-frame
python ae/experiments/native-creative-proof/run.py variants local-data/ae-native-creative-proof/r-next
```

从该次 `variants.json` 读取实际 `comp_ids`，不要沿用旧合成 ID：

```powershell
$proofVariants = Get-Content local-data/ae-native-creative-proof/r-next/variants.json -Raw | ConvertFrom-Json
python ae/experiments/native-creative-proof/run.py render local-data/ae-native-creative-proof/r-next --comp-id $proofVariants.comp_ids.A --label A --single-frame
python ae/experiments/native-creative-proof/run.py render local-data/ae-native-creative-proof/r-next --comp-id $proofVariants.comp_ids.C_FIXED_CAMERA --label C_FIXED_CAMERA --start 3.5 --duration 7 --single-frame
python ae/experiments/native-creative-proof/run.py render local-data/ae-native-creative-proof/r-next --comp-id $proofVariants.comp_ids.D_RESTORE --label D_RESTORE --duration 8 --single-frame
python ae/experiments/native-creative-proof/review.py local-data/ae-native-creative-proof/r-next/NATIVE_B.mp4 local-data/ae-native-creative-proof/r-next/full-motion-review
```

A 是同输入的简化平面基线：固定相机、取消景深与深度、取消局部转动与薄载体，其余动作目标和结果不变。C 只固定相机 Position / Point of Interest；几何、父级、景深和焦点交接不变。D 把同一批对象的关键帧反向映射到六秒内，第七秒核对原文、原位置和附着父级。r5 / r6 / r7 的表达式驱动位置先在原锚点尚未反向前按帧采样，再反向位置与尺度，避免正向跟随表达式破坏恢复；D 的焦点同样不使用正向时间表达式。当前 r7-wordcue-final 已核验恢复合成，未渲染新的 A / C / D 电影；上面的命令是重放入口。

已完成的 B 快照也可在一个新的空白工程中制作对照，避免继续使用失败的渲染会话。源 `PROJECT_B.aep`、冻结的执行 JSX 与字体绑定必须精确匹配；同目录其它 AEP 或相同字节的另一条路径不能替代这个快照：

```powershell
python ae/experiments/native-creative-proof/run.py fork local-data/ae-native-creative-proof/controls-next --source local-data/ae-native-creative-proof/r3
python ae/experiments/native-creative-proof/run.py variants local-data/ae-native-creative-proof/controls-next
```

然后从新目录读取实际合成 ID，使用上面的渲染命令。导入 AEP 会同时复制其已完成渲染队列；工具只在这个新工程中移除已核验为同一合成研究、同一 scene SHA、DONE 的队列副本，其它状态一律阻断。源工程保持原字节。历史 r3 对照在 `r3-controls-r4`；当前 r4 对照同主片保存在 `r4`。历史导入前后原生布局、文字、父级、关键帧、相机和焦点采样一致，仅原生图层 ID 不同。

固定引导版要求五条匹配合成文本的既有 `voice-delivery/v1`，文件目录含 `generation.json`。最初使用同一最新 Producer 生成一次 Scratch；r4 复用五条与 guide-r3 字节相同的录音，只把“接起来”移至实际接合。没有重启 R02 Performance 实验。下面的 `delivery.json` 是本地匹配的交付文件：

```powershell
python ae/experiments/native-creative-proof/guide.py prepare local-data/ae-native-creative-proof/r-next local-data/ae-native-creative-proof/guide-next --delivery local-data/ae-native-creative-proof/scratch-voice-r1/delivery.json
python ae/experiments/native-creative-proof/guide.py assemble local-data/ae-native-creative-proof/r-next local-data/ae-native-creative-proof/guide-next
python ae/experiments/native-creative-proof/guide.py export local-data/ae-native-creative-proof/r-next local-data/ae-native-creative-proof/guide-next
```

Premiere V1 只有一段完整、按该次绑定时长的画面（r7-wordcue-final 为 20.25 秒），A1 放置五个完整声音；没有音乐、音效、切镜或 time-stretch。r7 的五条 WAV 与 guide-r6-sharp 字节相同，出场时间也相同。切换实验前先将旧 PR 工程复制到新目录并打开副本，避免创建新工程时保存历史固定工程；AE 同样先 Save As 到独立研究会话，再创建新编排，避免 checkpoint 改写先前工作工程。导出后重新回读时间线、核对源路径、编码规格及五条实际声音的波形相关性。波形存在不等于听感通过。

## 凭证与故障

每次冻结保存原文、布局、字体 SHA、执行 JSX 快照与 `spec_sha`；后来脚本修改不会使旧快照失去可核查性。`PROJECT_<variant>.aep` 是对应影片的不可覆盖原生工程快照；`NATIVE_CREATIVE_PROOF.aep` 是可继续操作的工作工程。

渲染调用 AE Render Queue 的已有 TIFF 模板，FFmpeg 只封装原生帧。每个 TIFF 被按原始字节归档，ZIP 内每个成员 SHA 验证成功后才删除本次生成的散帧；保留归档、逐帧 SHA 和视频 SHA。全片解码失败或帧数不齐均拒绝出凭证。

发生 native timeout / 失败时保留请求与返回的确切 recovery ID，先回读实际状态；`--recovery-id` 仅用于已核对的官方恢复，不自动猜 ID、不盲目重试。未知旧队列会阻断渲染。渲染区间必须在该次绑定的合成时长内且对齐 24 fps 帧边界。

本机一次对照渲染停在 414/648 帧且桥接超时；下一次另名输出遇到原生“导出合成时发生意外错误”。先原生回读，再通过各次确切的官方 recovery ID 处理失败状态，没有用观察超时推断任务已停。失败请求和原因保留；415 张残留 TIFF 后按用户磁盘清理要求删除，记录在本地清理凭证中。

最终通过不可变 B 快照导入空白研究工程，在 `r3-controls-r4` 完成 A、C、D 三个实际对照。C 渲染结束后出现“撤消组不匹配”提示，桥调用耗时含等待提示的时间；不能当作纯渲染性能。`--single-frame` 调用本机已核验存在的 `app.setMultiFrameRenderingConfig(false,100)`，只用于本次渲染脚本；不重置用户首选项，也不证明已查明早期导出错误根因或长期修复 AE。`render-request-*.json` 保存实际调用；使用的渲染代码没有外层 Undo group。

本机缓存已核对迁移至 G 盘；Common 缓存经 Junction 路由，Analyzer 目录实际名为 `Analyzer Cache Files`。缓存迁移与后来导出成功之间不能直接推断因果关系。

r4 已在屏幕 2 实际启动原生缓存预览；Info 面板在两个不同片中时点均显示 528/528 帧、24 fps（实时）。合成 1920×1080、Full 分辨率，查看器缩放 53.3%；原工程未保存、对应固定 AEP / 电影 SHA 不变。这个结果只证明该次热缓存预览的面板观测，不是冷缓存性能基准或全程丢帧计数，也不代替用户对运动和节奏的判断。本地 `r4/realtime-preview-receipt.json` 绑定截图、片中时间及原生回读。

只有代码、这份合成 fixture、测试和脱敏报告进入 Git。真实教学资产、AEP、PR 工程、媒体、声音模型、reference、token 和本地凭证均留在被忽略的 `local-data/`。
