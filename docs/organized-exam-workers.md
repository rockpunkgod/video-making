# 一张试卷一个独立代理：真题案例与整卷回归

适用本轮用户指定的 `D:\英语资料（已整理）`，不是对原 ANSWER 的重写。

## 派发与目录

每份题面候选使用一个实际独立 subagent。最多三卷并发，完成后再派下一卷。
清单是 204 份来源候选，不是 204 套已认证、互不重复的官方真题。
`scripts.organized_paper_queue` 的 SQLite 只记录真实派发；它本身不会创建代理。
待派、正在审阅、代理已返回报告要分开。报告返回不等于完整试卷或方法 Case 通过。
报告有修订时，由协调者显式登记 `record-report PAPER_ID --outcome PARTIAL --report-file review-v2.json`。
队列核对试卷 ID、来源 SHA 和真实 reviewer_agent，保留旧文件，不自动挑选最新版。
阶段目录中的报告也须显式选版，例如 `--report-file semantic-r1/review-v1.json`；不复制成另一份报告。

用户当前指定优先 2026 年：先完成选定的Ⅰ/Ⅱ卷转写批次，再启动对应案例与整卷语义审阅；
历史卷既有报告保留，尚未派发的历史批次后置。年份和文件名只是来源声明，不认证官方身份。
同年异版本先核题面身份；重复副本只补来源，改写版保留差异，带答案版本隔离。

后来指定的新优先批次高于未派发的年份顺序。压缩包采用独立私有 intake，不改写旧清单；
核实包内路径、名称编码和原件指纹，题面、解析、音频分开绑定。真实模拟/诊断题可以研究，
但不能把学届、文件名或附件称呼当作官方高考真题认证。
Word 题面保留 DOCX 原件；dossier 显式记录 `source_extension=.docx`，回放核原件字节而非转换 PDF。
旧 PDF dossier 未写扩展名时仍默认 `.pdf`；`.pdf`、`.docx` 与 `.doc` 可进入转写批次。
旧版 `.doc` 仍核原件的 `.doc` 字节指纹；只读转换所得 PDF/DOCX 及图片是检查旁路，
另存转换链和指纹，不用转换件替换原 dossier 的来源身份，也不把格式支持当成转写正确。
Word 自动题号、表格及图片另须目视核实，精确跨度或程序运行均不等于来源内容完整。

每个代理只修改自己的 `local-data/organized-pdfs/paper-runs/<paper_id>/`。
主代理另行复核汇总，不让代理改共享 Registry、原 ANSWER、既有交付包或其他卷的冻结稿。
文件编辑使用 apply_patch；生成的结构化产物使用不可覆写的 freeze_json。
有错另存显式版本和撤回原因，不覆盖历史。

## 仓库已有内容先复用

“已有”以仓库现有题目、Case 和题源记录为准，不只比较本轮附件之间的文件名或哈希。
派发前分别核对 Case Registry、仓库追踪的题源摘录、旧题稳定 ID 和已返回的逐卷报告。
本轮私有逐卷映射位于 `progress/dedup-existing-r1/repository-existing-addendum-v2.json`；
它是带指纹的审计快照，不是替代 Registry 的新登记表，也不自动更新队列状态。

- 已有完整题目或真实 Case：复用原 ID；不同 PDF/Word 版本只补来源别名、缺失上下文或证据，不另建同题。
- 已有课程短 Case：复用 Case ID 和已占的方法槽；整卷尚缺的其他题仍可继续审阅。
- 只有题源短摘录：复用出处及源片段，只补尚缺的完整题面、逐题绑定和动作证据。
- `evidence_gap` 是未完成占位，`source_pattern_only` 是模式，不冒充已有真实题目。

同一题可关联多个方法动作，但不能复制题面或重复计为新增真题。
已审阅卷不重新派发；代码变化后的必要回放复用冻结输入，标为旧题回归，不计新 Case 或新盲测。
身份确认须有独特上下文、题干和选项等证据；不能仅凭题号、题材、方法名或文件名强行合并。
未匹配的提取差异先标待核，不自动当作新题；版本差异保留，不覆盖已有内容。
旧摘录或 Case 含已填答案时逐题登记 exposure，不把复用题包装成新留出集。

用户追加采用“低档模型先批量转写，再批量推进案例和整卷回归”。默认三卷为一批，
每卷仍绑定一个真实子代理，不把一个机械命令记作多个代理。已返回报告及仓库旧题先复用。

第一段使用低档转写代理：只读题面，修补逐页文章、题干、全选项、空标、提示词及任务边界，
所有非空文字字段绑定精确源跨度。原文不纠错，图表或模糊结构不能靠模型猜补。
产物保存在每卷 `transcription-r1/`；转写报告不命名 `review.json`，也不登记为语义报告。
`source_task_count` 数全部源题，不是缺口组数；二者单列。参考正文保持未读。

同批转写完成后，先逐字段及 PDF/源文指纹预检，再集中跑两种 Analyzer：

```powershell
python -X utf8 -m scripts.run_organized_paper_regression all --transcriptions SOURCE1.json SOURCE2.json SOURCE3.json --output-root local-data/organized-pdfs/transcription-batch-r1
```

此入口整批预检通过后才运行；发现缺字段、改字、未记录的删除、错来源或重复题 ID 则停止。
语填逐空核括号提示词：全文里有提示词但 `given_word` 漏传也会停止，不能误走“无提示词”路线。
英文源节编码仅作显式题型映射，不覆盖转写原件。回放使用完整已转写输入，不只旧机械子集；
字段逐字绑定不证明文章或选项边界在语义上完整，仍须下一段独立核验。
输出为 source-only 工程回放，不是新盲测、自动解题、safe abstention 认证、正式 Case 或整卷验收。
听力、缺图/缺页、不支持任务、缺学生稿等保留单独缺口，不被“这批跑完”掩盖。

文本层损坏时，另存 `origin=visual_transcription_sidecar` 的逐页视觉转录，绑定原 dossier 的路径/字节 SHA，
每页绑定实际私有 PNG 与 SHA，全文必须按页序逐字连接。`source_document_ref` 显式选该旁路；
旧 dossier 和原 PDF 不覆盖。工具检查文件、指纹和跨度一致性，不自动认证视觉转录的英语正确性。
没有下划线的真实语填空（裸数字或完整 `(1)` / `（1）`）须附 `blank_marker_visual_check`，
核原件身份、题号、页码及 PNG 指纹；括号空标整段原样绑定，不能只截中间数字而丢掉右括号；
不能凭价格/正文数字制造空位，也不能为了通过校验添加原图没有的下划线或占位符。
显示投影只删已记录的印刷页码；物理页码与印刷页码不同须显式视觉确认对应关系。
题目给定首句、称呼、落款和续写段首属于题面约束，不自动构成答案污染。
真正的预填解答也不是未知学生稿，source-only 转写禁止传入引擎的 `student_text`（以及 `student_draft`）。
`reference_read=false` 不表示从未见答案：`source_answer_exposure` 独立保留，回放不认证 clean blind。

如原转写代理确已不在实时代理列表且未返回冻结转写，可实际创建接续代理后使用
`resume-transcription PAPER_ID PREVIOUS_TASK ACTUAL_TASK --model MODEL --effort EFFORT --reason REASON`。
队列保留旧身份与接续原因；接续不是新试卷、语义完成或新盲测。不能把已进入语义阶段的作业退标为转写。

第二段再从已校验题面建立方法动作与题面预测，冻结后才揭晓参考；普通结构及工程回归采用中档，
完整英语证据、主旨范围、间接支持和高误用成本的 Stop 审阅按需提升档位。
逐卷语义报告仍走现有真实派发、冻结和登记流程；协调者另作独立 Case Review。
第二段使用不同代理时，先实际创建代理，再执行 `organized_paper_queue advance-semantic`，
显式传入 `--transcription` 和该卷 `--replay` 两个冻结文件。队列保存低档代理的历史身份及两个指纹，
只更新当前负责代理，不把转写或回放记为语义报告已返回。第二段结果仍由 `record-report` 显式选版。
一卷的语义代理可以复用公共工具，但不能把工具跑完当成自己已经审过全文。

## 现有入口

- `source-manifest.json`：406 个文件的来源清单，题面、答案、混合及待分类分开。
- `originals/snapshot.json`：全部原文件的私有字节冻结；复制答案字节不等于读取答案正文。
- `pages/<source_sha256>.json`：题面逐页原文，未纠错，未 OCR 覆盖。
- `case-bank-v4/source-bank.json`：按 paper_id 找每卷案例文件、显示投影和来源指纹。
- `case-bank-v4/papers/<paper_id>.json`：原始整卷文本及精确原文引用。
- `case-bank-v4/question-inputs/<paper_id>.json`：部分可投影结构；不是全部题已可用。
- `answer-source-links.json`：文件名配对而非答案认证；不含答案正文。
- `ocr/<source_sha256>.json`：23 页中文 OCR 转录旁路；英文误识别明显，不能直接充当可信盲评题面。

公共机械入口：

```powershell
python -X utf8 -m scripts.run_organized_paper_regression PAPER_ID
```

此入口只跑通用结构子集。历史单选仍路由未知，不能当语法填空。
当前有效子集报告目录为 `mechanical-intake-v4-2`。
`mechanical-intake-v4` 缺少提示词传递，`mechanical-intake-v4-1` 尚未拦截正文/说明数字；
两者保留为失效历史，不能用于当前覆盖和方法触发统计。
v4 案例库的叶记录本身也可能含误切数字或未细分任务，数量只是解析候选数。
例如“填入 1 个适当单词”、价格、百分比不是自动可用空位。
公共回归入口拦截说明/页码数字与无明确空标的数字，留给每卷代理核实，绝不删原文。
阅读、写作、图形题及缺损结构须代理独立绑定后，用现有 QuestionAnalyzer/PaperAnalyzer 跑。
不能用子集回归报告声称整卷全部题型通过。所有 source-level 记录仍未登记为正式方法 Case。

## 每卷必须实际做

1. 完整读该卷所有题面页，并检查页码、题号、文章、选项、空位、提示词、写作任务与续写段首。
   使用 PDF skill；若涉及解题/方法，完整读对应 Skill 及其要求的课程模块。
   原文错字保留；版式页眉仅可从显示投影剔除，记录被排除的原始 start/end/quote。
   图形选项、图画作文和广告图须渲染目视核验，不能凭文本层声称内容完整。
   听力无音频、历史改错/翻译等未支持类型单独登记，不硬塞六型。
2. 从题面独立建立逐题输入与 source-structure。字段来源用精确单段或多段源跨度绑定。
   不从答案补题。所有可忠实转换的笔试题实际运行 QuestionAnalyzer 和 PaperAnalyzer。
   先冻结输入、预测、版本和指纹。无语义 provider 的 unresolved 不是已认证 safe_abstention。
3. 从真实触发中挑最多三个优先六黄金方法的候选，不为数量强套。
   先冻结自己的 source-only AI 语义观察、动作及产物，再揭晓答案。
   允许辅助动作或有界排除未闭合；不要借整题答案给所有参与方法信用。
   尽可能将动作记录实际送入引擎，保存执行ID、own output、role、evidence spans、Stop。
4. 冻结后才读取本卷精确配对的答案/解析。配对仍需题号和全文核验。
   官方来源未经认证时 official_answer=null，third_party_reference 单列。
   解析和答案串矛盾、缺页、图形缺失都标待核，不修改盲稿或反推方法。
5. 输出 review.json，顶层 paper_id、source_sha256、reviewer_agent。
   分列工程回归、AI题面审阅、第三方参考对照、source gap、typed产物、方法候选与正式登记。
   正式 Case 注册和成熟度变更由另一个授权审阅流程执行，此处不可自动填槽。
   Report 中记录当前 v4 与独立原题绑定的差异，以便后续显式解析修订。

## 证据和刹车优先

R01 先确认同一完整断言，才可拆 A+B；不同对象不是自动“加戏”。
找不到原词不是无间接依据，B 有合理文本支持时停止此理由的排除。
R02 保留主体、完整动作和对象，不为制造主体错换而过度限定一个多义动词。
R06 比全文任务及范围，不把缺关键词当缺主旨。
R09 只产对象、核心判断、全文结构任务的骨架卡；入口不是三个万能取词步骤。
F01 只产初次三维暂定分组；每维覆盖全部 A-G，一维无区分度要明说。
句型轴比较完整句、半句、祈使、疑问等真实结构；But 等转折标志不能被包装为句型差异。
相关代词尚未回填时只能标暂定，分出组不等于实际减掉候选，更不能据分组定答案。
G01 先按空位功能走决策树，不按括号原词性强进入动词路线。
定位、解释、缩小、决定、核验职责分清；只剩一个选项也不自动正确。

## 不得混记的统计

AI 宿主不是人审。不能写 human judgement、真人 First-use 或学生速度收益。
独立代理在看参考卷之前的观察，可以记 agent_before_reference_read；不能自动称新留出集。
若父代理或旧材料已透露某题答案提示，逐题记 exposure，排除相应 clean-blind 统计。
已揭晓旧卷的重新跑题不变成新增盲测。需要修正身份或归因时另存绑定原 SHA 的附录。
真实原题入库数、解析完整题数、方法候选数、正式 Method Case 数和真人研究人数分开。
实用性优先于传播；没有独立实效证据，不升级 validated/stable/Efficient/Signature。

全部全文与答案保留私有目录。未核再发行权限，不上传公开仓库。

## 从目录到逐卷报告

依赖由 `pyproject.toml` 的 `organized-exams` 可选组声明。按以下顺序运行本地入口：

```powershell
& .\scripts\inventory_organized_sources.ps1
python -X utf8 -m scripts.freeze_organized_originals
python -X utf8 -m scripts.freeze_organized_pdf_pages --kind questions
python -X utf8 -m scripts.link_organized_answer_sources
python -X utf8 -m scripts.build_organized_question_cases
python -X utf8 -m scripts.organized_paper_queue init
python -X utf8 -m scripts.run_organized_paper_regression all
```

目录清单和原文件快照可重复验证，但不得原地重写成另一批来源。
题面提取与文件名配对都不读取解析正文。OCR 是旁路转录，不能覆盖原始文本层。
题面候选全部跑过通用机械入口后，仍须实际逐卷派发，不能把这一步算作 204 个代理报告。
每卷报告必须分别记录全部源任务、忠实引擎输入、方法候选、正式 Case 四项计数。
源任务含听力和未支持的历史题型；方法候选至多三个的限制绝不限制全卷源题入库。

协调者的第二次动作审阅另存 `coordinator-reviews/`，并用 SHA 绑定附录关联原卷，
不覆盖盲稿、参考对照或初审意见。揭晓后的显示投影修复或动作修订必须明确标时，
不能重新计算为题面初次盲测。附录指出的限权、撤回或修订须随初审一起读取。

## 独立 Case Review 后的私有登记

逐卷代理的候选不是正式 Case。协调者可在六项动作审阅通过后登记完整原题绑定的私有研究 Case；
没有真人数据不妨碍保存已核的题面动作，但不能因此升级方法成熟度、效率等级或 Signature。
传播阶段先验收，实用性阶段拥有否决权；本登记不替代任一真人阶段。

```powershell
python -m answer_engine register-real-case coordinator-reviews/REGISTRATION/REQUEST.json --dataset local-data/organized-pdfs
python -m answer_engine case-coverage --private-catalog local-data/organized-pdfs
```

REQUEST 是相对私有 dataset 的路径，不是公开 Case 文件。请求必须指向保留原字节的盲稿/原题指针、
原 PDF/Word、完整文本字段逐段源跨度、揭晓原件、独立动作重放与第二审阅者的 Case Review。
揭晓后的修订只加动作注释，不能改冻结的题干、全文、选项、提示词或首句；不重算新盲测。
旧 PDF 请求继续沿用 `pdf_path`、`pdf_sha256` 和 `question_binding.pdf_sha256_pointer`，不改历史字节。
新格式请求使用 `original_path`、`original_sha256`、`source_format=pdf|docx|doc`，
以及 `question_binding.original_sha256_pointer`；独立审阅对应绑定 `source_original_sha256`。
两套字段不能混用。入口核路径扩展名、原件字节指纹及格式标记，DOCX 还核 Word 文档 XML、包内容类型与主文档关系，
DOC 使用 `organized-exams` 可选依赖解析 OLE 容器并核 WordDocument / Table 流和 Word FIB 标记；
这些检查不认证题源官方身份、逐字语义或源题完整性，转换件仍只作另存视觉旁路。
存在揭晓适配器时，它的原对照 JSON 和参考原件也须同时绑定字节指纹：旧版 `reference_pdf_ref`，
新版 `reference_original_ref={path,sha256,format}`。不能同时给两套参考原件字段。
新版原对照 JSON 也须包含相同 `reference_original_ref`，防止分别绑定两个无关文件。
独立审阅逐项核触发、动作、证据、主要职责、Stop 和案例类型，并绑定该方法自己的执行 ID。
辅助分组/骨架不领取其他方法或整题答案信用。工具核一致性与可重放，不认证审阅者身份或英语语义。

登记键是 `canonical_question_id + method_id + case_type + method_version`。
已有题沿用仓库稳定 ID，已有短 Case 的完整补证须明确复用 Case ID、原 Case 指纹和独立匹配记录。
同键重登拒绝；另一个 PDF/Word 版本只能显式核对来源别名，不增加 Case 数。题号/文件名相似不作同题证据。
新格式来源别名使用 `old_original_sha256` / `new_original_sha256`，显式复用原 `case_id`，
独立审阅确认 `source_alias_reconciled=true`；旧 PDF 别名链保持兼容，不迁移或重写历史。
新版别名还核全部核心题面字段，仅允许 Unicode/空白显示差异，不能凭 canonical ID 声明合并内容不同的题；
实质版本差异另存待复核，不靠改 ID、哈希或审阅标志绕过同题约束。
同一冻结题面核心指纹只能对应一个 canonical ID，重新封装盲稿元数据也不能换名绕过登记去重。
该指纹包含原题 ID、题型及全部核心题面字段；不是只凭某段文字相同合并不同题。
原题全文复用已有冻结输入，Catalog 只存引用与方法动作证据；所有内容仍在私有目录。

`real-case-catalog/catalog-NNNNNN.json` 为仅追加的版本链，重新读取时检查历史前缀、上游字节、
完整字段绑定、当前 Analyzer/图/执行链重放及遗失/孤立文件。失败时停下并另存修订，不覆盖历史。
`case-coverage` 默认仍只返回公开 Registry；显式私有参数才叠加 `private_registered_case_count`，
不会把公开占位或模式记录改成完整案例，也不会授予释放资格。
状态 `reviewed_real_exam_case` 限于私有 AI 动作复核，真人状态始终单列。
