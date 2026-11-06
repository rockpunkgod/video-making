# 读后续写术语来源索引

本轮只读原件，生成独立核对材料。术语主表见 [TERMINOLOGY_CONTINUATION.md](TERMINOLOGY_CONTINUATION.md)。源文件 SHA256 及提取路径保存在 documents.json（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/documents.json`）。OfficeCLI输出的`paraId`是原文段落定位，不是页码；不虚报Word分页。表格以`/body/tbl[n]/tr[n]/tc[n]`定位。

## 原讲义

| ID | 原文件绝对路径 | 本轮证据 |
|---|---|---|
| D01 | `E:/开明致学/读后续写课上讲义10.4日.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D01.officecli.txt`），跳定思提润、三化法、五步中文、挖空训练 |
| D02 | `E:/开明致学/【课上讲义】第16讲作文（26S暑假）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D02.officecli.txt`），五步成文中英文、首句名词、素材安排 |
| D03 | `E:/开明致学/【课上讲义】第11讲 作文（26S秋季）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D03.officecli.txt`），四类主题升华；媒体口述待核 |
| D04 | `E:/开明致学/【课上讲义】第16讲 续写（26秋季）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D04.officecli.txt`），五字原则、动作链/动作面、分档训练原名 |
| D05 | `E:/开明致学/【课上讲义】 第8讲 续写（ 26S寒）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D05.officecli.txt`），三原则、四步骤、八技巧、PTSD、十句五定；`tbl[1]`PTSD、`tbl[2]`十句表已本轮用OfficeCLI逐cell核 |
| D06 | `E:/开明致学/【课上讲义】第14讲 续写（26S寒）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D06.officecli.txt`），PTSD另一版、肌肉骨架、gap、三重匹配、精准续写、情节节点 |
| D07 | `E:/开明致学/【课上讲义】第11讲 读后续写（26S春）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D07.officecli.txt`），人与自然三型四步、句式位置、关键元素、套用操作 |
| D08 | `E:/开明致学/9.8日高三班课上讲义（含矮胖圆字体）.docx.docx` | 原段落提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D08.officecli.txt`）；OfficeCLI识别2图，正文未检出“矮胖圆”逐字定义。文末`/body/p[167]/r[1]`关系rId5的原嵌手写样张（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D08_rId5.png`）已本轮看图；图片关系及源SHA256（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/source_extracts/D08.images.json`）。手写图支持书写训练路由，具体三字标准仍不足 |
| D09 | `E:/开明致学/高三寒假第十次课程讲义.docx.docx` | 边界阶段新定位：原OfficeCLI全文提取（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/boundary/D09.officecli.txt`）、源SHA256与路径（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/boundary/D09.source.json`）。首部paraId `3FD2C04E`“五步成文法”五项与后部解析版并存；`6144E5E1`“读后续写十大仿写句式”及各类标题原文可核。游泳题和现场三条提纲与赠50音画对应；不是只靠文件名判课程年份。首部五项及十大类没有因匹配此题而自动取得完整口述实施证据 |

`E:/开明致学/_extracted/*.txt`只作为检索入口；关键术语已回原DOCX读段。本轮生成源提取脚本`collect_sources.py`仅在报告目录写抽取物，不改原件。

D08为root验收追加定向核对：先用OfficeCLI文本/outline/query image定位图像，因正文没有字体定义，再从DOCX包中只读提取已定位的原嵌图。另一张rId4为动词时态语态知识图，与字体名词无关。没有据文件名独立断定完整定义，也没有对原手写样张作图像修改。

D09边界阶段增补：首部五项paraId为`78F85145`、`2D269F3F`、`30CE517A`、`2335F6E1`、`7857E04A`；后部解析五步骤为`626AB5A0`、`4087BED1`、`06A85C7C`、`64E76C08`、`5FFB3DBD`。十大仿写类别标题paraId依次为`0E69E935`、`3C78A684`、`6FA09977`、`71C4D58E`、`19923C82`、`281E8352`、`7E15905C`、`6F75483E`、`23C46157`、`1CB6D2EA`。保留原组合标题“倒装句、强调句开头”和“独立主格/with复合结构开头”，不按标点拆造方法。

## 本轮成品媒体及音画

| ID | 成品文件 | 本轮范围与状态 |
|---|---|---|
| V02 CONT_SUMMER16 | `D:/暑假班/16.读后续写高分挑战：快速阅读原文定思路.mp4` | 原音机器转写600–1260秒（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/audio/summer16/CONT_SUMMER16_000000600000_000001260000.asr.json`），同名`.wav`与`.audio.json`保留；抽帧索引（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/frames/summer16/CONT_SUMMER16_frames.json`）；首句规则细帧索引（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/frames/summer16-detail/CONT_SUMMER16_frames.json`） |
| V03 CONT_AUTUMN16 | `D:/秋季班/16.读后续写高分挑战：人物深度刻画训练.mp4` | 原音270–660秒（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/audio/autumn16/CONT_AUTUMN16_000000270000_000000660000.asr.json`）、原音660–870秒（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/audio/autumn16/CONT_AUTUMN16_000000660000_000000870000.asr.json`），同名wav/manifest保留；抽帧索引（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/frames/autumn16/CONT_AUTUMN16_frames.json`） |
| V04 CONT_AUTUMN11 | `D:/秋季班/11.读后续写高分挑战：结尾升华金句积累.mp4` | 完整文件名可见；本轮先核D03，尚未做该媒体内容独证 |
| V05 CONT_WINTER08 | `D:/03.寒假班/10.第8讲 读后续写高分挑战：人与自我高分策略.mp4` | 原音4740–4860秒（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/audio/winter08/CONT_WINTER08_000004740000_000004860000.asr.json`），wav/manifest保留；旧原帧`VIDEO_CDF1BF78D39C_000004800000.jpg`本轮已看 |
| V07 CONT_GIFT50 | `D:/秋季班/定海神针50题【赠课】/50.龙坚定海神针：读后续写.mp4` | 抽帧索引（本地证据未随归档提供，原路径：`G:/gaokao-course-terminology-20261013/continuation/frames/gift50/CONT_GIFT50_frames.json`），0/180/360/600秒题面路由为读后续写。只证明课程题型，不从文件名推断方法 |

最便于验收的段落：V02 938.8–1022.7秒（两首句名词+人物/任务语义异文）；V03 388.8–496.6秒（五句建议、四句也可、四处固定衔接、隐形升华也要有）；V05 4756.6–4801.1秒（目的、方式、苦难、结局，回原文填未知槽）。

音频由既有 `G:/gaokao-english-rebuild-及工具/gaokao-english-rebuild/scripts/transcribe_review_window.py`按连续短窗抽取；本地 faster-whisper-large-v3-turbo，CUDA float16。模型`model.bin`SHA256 `E76620F83D5F5B69EFD3D87E3DC180C1BD21DF9FBEBACFD4335E5E1EFCC018DA`，脚本每次验证哈希。原ASR保存source_start/source_end、音频SHA256、word timestamps及参数。机器转写不等于人工逐字听核。

## 复用旧原证

| ID | 证据绝对路径 | 核验状态 |
|---|---|---|
| P01 | `G:/gaokao-english-rebuild-及工具/gaokao-english-rebuild/distillation/02_extraction/documents/PRESENTATION_24D04DDE487B/rendered/幻灯片3.PNG` 与同目录`幻灯片4.PNG` | 本轮亲看：Purpose/Twist/Struggle/Denouement四点串剧情；十句行全文句位表。旧登记原PPT相对路径`02. 2026龙坚高二英语/03. 龙坚高二英语寒假班（完结）/电子资料/用十句行文法打开26年浙江首考.pptx`，当前原文件未重新定位；不声称从新下载源重新抽取 |
| V05-old | `G:/gaokao-english-rebuild-及工具/gaokao-english-rebuild/distillation/02_extraction/video/VIDEO_CDF1BF78D39C/sparse_visual/VIDEO_CDF1BF78D39C_000004800000.jpg` | 本轮亲看：高三寒8，80分钟P目的/T方式/S苦难/D结局 |
| V06 | `G:/gaokao-english-rebuild-及工具/gaokao-english-rebuild/distillation/02_extraction/video/VIDEO_14D33E6B1204/reviewed_windows/ptsd-detail/`及`writing-methods/` | 旧高二人与自我课程的60分钟PTSD、120–130分钟十句五定原帧留存；本轮只用作交叉检索定位，未新增亲看全部帧结论 |

旧`evidence-ledger.yaml`与`course-evidence.md`仅作定位线索，不代替原图/文档/原音。P01与高三寒8来自不同课，不静默合并。

## 未完成下载与路由缺口

以下仅枚举文件名状态，没有打开、probe或hash未完成件：

- `D:/03.寒假班/18.第14讲 读后续写高分挑战：人与社会高分策略.mp4.baiduyun.p.downloading`。
- `D:/04.春季班/12.第11讲 读后续写高分挑战：人与自然高分策略.mp4.baiduyun.p.downloading`。
- 寒8课上讲义、寒8空白PDF、春11空白PDF及寒假读后续写五大素材在D盘部分仍有`.downloading`。本报告改用E盘已完整原DOCX，但不声称两份字节相同。
- `D:/秋季班/定海神针50题【赠课】/36–42`文件名为“语法填空-1…-7”，不能由名字确认题型或排除实际写作词汇素材；本轮尚未逐题面路由，未纳入术语独证。

旧正式模块 `E:/新建文件夹/answer-method-audit-20261011/gaokao-writing/references/continuation-writing-and-correction.md`仅是待核清单来源；未修改。源索引将未核媒体与已核讲义分列，避免“有讲义即整课视频已蒸馏”的混算。
