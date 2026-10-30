# 读后续写独立源状态：方法实施边界

2026-10-13。本表与术语命名验收分开；不替代共享总账。报告：[CONTINUATION_BOUNDARY_REVIEW.md](CONTINUATION_BOUNDARY_REVIEW.md)。范围为已交接的续写五件成品媒体、两件下载中媒体与对应讲义，不声称重新清点所有课程目录。

## 成功音窗与实际读取量

| 本批原音 | 秒窗 | 时长 | 原ASR片段数 | 实际核查 |
|---|---|---|---|---|
| CONT_WINTER08 | 4860–6180 | 1320秒／22分钟 | 760 | 全部760段已读，结合D05与5100/5700/6000/6120帧核现场填槽及改提纲 |
| CONT_GIFT50 | 1080–1560 | 480秒／8分钟 | 322 | 全部322段已读，结合新增原讲义D09及1200.046/1500.046帧核必要过程与可省衔接 |
| 合计 | 两窗 | 1800秒／30分钟 | 1082 | 不是人耳逐字听核，不包含只有WAV的两窗 |

旧23分钟原音直接复用：暑16 600–1260，秋16 270–660与660–870，寒8 4740–4860。旧窗口不在本批新增量中重复计算。赠50与暑16游泳回忆是同一剧情，不计两个独立整题。

原WAV、`.audio.json`、`.asr.json`保留同目录；ASR使用既有本地faster-whisper-large-v3-turbo、CUDA float16，模型hash沿用来源索引。赠50第一次启动因手工传入的hash字符串漏字而被校验挡住，未生成ASR；修正为既有核验hash后成功，无覆盖或清洗raw。

## 源级状态

| 源 | 本次证据范围 | 可得结论 | 不能宣布的内容／剩余缺口 |
|---|---|---|---|
| 暑16：快速阅读原文定思路 | 复用D02、旧600–1260原音及原帧；复读750–1024 | 首句人物/动作时地→带问题读文；两首句名词限定；人物/任务异文保持；赠50补同题实际提纲 | 不算全课所有例题新验；人物一律出现是培养习惯的强建议，不能冒充普遍评分条款 |
| 秋16：人物深度刻画训练 | D04、旧270–870原音；新增800/840原帧 | “提”为中文每句大意与句型；4–5句可行的口述；动作链2个完整微例 | 动作面组成未核；Skill 2三动作现场原音未核；各分档配方不能当全已视频验收 |
| 寒8：人与自我高分策略 | D05、旧4740–4860、本批4860–6180；导航及细帧 | Daniel一例首句→回文→寒8四槽→两段功能提纲完整；现场重复修订及手势限制确认 | 修书6300–6960仅WAV+原帧，不计第二完整音画填槽例；其十句现场为空；其余三原则/八技巧原件有证但不据本例宣布所有素材逐项实施核完 |
| 赠50：读后续写 | 本批1080–1560，新增D09原件，导航帧 | 游泳第一段中文提纲完整；父亲带零食回来是本例必要补全，准备吃可省且不能重复第二段 | 后续英语扩句/升级没有全部核验；训练动作存在不认证“富兰克林”原名；D09同名五步列表差异待命名增补审议 |
| 秋11：结尾升华金句积累 | D03原件、导航及4500/4800/4980等原帧；4380–4920仅WAV | 仅定位原主题素材、stage/family/Pat/celebrate例与后续篮球例 | 未取得该媒体原音实施独证；不能宣布四类素材选择/套用已实际核完 |
| 寒14：人与社会高分策略 | 完整D06原讲义 | 名称与讲义PTSD槽位、骨架/肌肉、本材料框架已核 | 媒体仍`.downloading`，未打开；无该版PTSD原音填槽，不能用寒8代证 |
| 春11：人与自然高分策略 | 完整D07原讲义 | 原名、关键元素呼应、模板限定位置及不一定升华文字可确认 | 媒体仍`.downloading`，未打开；没有新原音，不合并为其他版本的通用操作 |

本次收尾仅枚举未完成文件的名称和长度，确认仍为：

- `D:/03.寒假班/18.第14讲 读后续写高分挑战：人与社会高分策略.mp4.baiduyun.p.downloading`
- `D:/04.春季班/12.第11讲 读后续写高分挑战：人与自然高分策略.mp4.baiduyun.p.downloading`

未打开、probe、hash这两件。P01旧高二PPT仍只复用已亲看原渲染，当前原PPT未复定位。

## 原件及新增匹配讲义

D01–D08完整路径与提取物在[SOURCE_INDEX.md](SOURCE_INDEX.md)。本批新增D09提取物放独立boundary目录；按根代理追加要求已向来源索引增量补D09及其标题段落锚点：

- 原件：`E:/开明致学/高三寒假第十次课程讲义.docx.docx`
- 原件OfficeCLI全文提取：`G:/gaokao-course-terminology-20261013/continuation/boundary/D09.officecli.txt`
- 源hash和提取路径：`G:/gaokao-course-terminology-20261013/continuation/boundary/D09.source.json`
- 对照锚点：`5AB94112`原文父亲去买零食、`64B0DC36`第一首句、`50016DFA`父亲回来提纲、`777AC0BF`准备吃零食及可省限定、`30A4832C`第二首句；用paraId定位，不冒充Word页码。

## 根代理亲核绝对路径

1. 寒8 raw：`G:/gaokao-course-terminology-20261013/continuation/boundary/audio/winter08/CONT_WINTER08_000004860000_000006180000.asr.json`。重点5963–6095秒（去重复、解释动机、手势）；入口与填槽4860–5206秒。
2. 寒8最终原帧：`G:/gaokao-course-terminology-20261013/continuation/boundary/frames/winter08-detail/CONT_WINTER08_000006120000.jpg`。填槽帧：`G:/gaokao-course-terminology-20261013/continuation/boundary/frames/winter08-navigation/CONT_WINTER08_000005100000.jpg`。
3. 赠50 raw：`G:/gaokao-course-terminology-20261013/continuation/boundary/audio/gift50/CONT_GIFT50_000001080000_000001560000.asr.json`。重点1325–1454秒（必要衔接与可省句、准备吃而非正在吃）；回原文1195–1242秒。
4. 赠50最终原帧：`G:/gaokao-course-terminology-20261013/continuation/boundary/frames/gift50-navigation/CONT_GIFT50_000001500046.jpg`。
5. 动作链旧raw：`G:/gaokao-course-terminology-20261013/continuation/audio/autumn16/CONT_AUTUMN16_000000660000_000000870000.asr.json`，764–849秒；新增对应原帧：`G:/gaokao-course-terminology-20261013/continuation/boundary/frames/autumn16-action/CONT_AUTUMN16_000000840000.jpg`。

根代理已反馈亲读寒8 5963–6090与赠50 1325–1450，实看6120/1500.046帧，接受本批有界职责；这条反馈不扩大为上表待核源已验。

## 保留待核队列（不是失败或完成）

- `G:/gaokao-course-terminology-20261013/continuation/boundary/audio/winter08/CONT_WINTER08_000006300000_000006960000.wav`：修书例11分钟，manifest已存，无ASR。
- `G:/gaokao-course-terminology-20261013/continuation/boundary/audio/autumn11/CONT_AUTUMN11_000004380000_000004920000.wav`：9分钟，manifest已存，无ASR。

本批按优先闭合两关键窗停止，不强求每源全时长转写。若需继续，直接使用已提取WAV，先核能改变结论的缺口；不重计旧证，不因音窗尚未处理而否认已核名称。
