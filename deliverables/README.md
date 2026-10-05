# 独立开发交付包

## Video Production OS v0.1

[Video-Production-OS-v0.1.zip](Video-Production-OS-v0.1.zip) 包含当前 V0–V7 源码、契约、公开示例、文档和逐文件 DELIVERY_MANIFEST.json，共511个文件。解压后从 docs/video-os.md 开始接入。

- 源码全量424项回归通过；独立解压目录49项Video OS测试、Registry和契约校验通过。最终包的运行代码及参考资源字节与冷启动验收包一致。
- F01、G01、R02三条真实 Engineering Pilot 通过；真实题与生产包保留在原工作区 local-data，ZIP不携带。
- 教学认证、来源显示和最终编辑批准仍为PENDING，公开渲染资格为false。正式AE/Astra/发布属于后续阶段。
- 所有归档条目CRC和逐文件SHA256核对通过；不包含私有试卷、Git历史、缓存或旧交付包。

大小：1,608,922字节。SHA256：`d2d86ca45e8eae577a4613927e2c1b354c2582c7df94259103b9947f5871507e`。

[完整核验记录](Video-Production-OS-v0.1.verification.json) · [压缩包校验值](Video-Production-OS-v0.1.sha256.json)

## ANSWER Method Engine 历史快照

[ANSWER-Method-Engine-9f27746.zip](ANSWER-Method-Engine-9f27746.zip) 解压后得到一个完整文件夹。先读最外层的 `开发前先读.md`，再按需要接入其他模块；目录结构不要拆散。

- 源码快照：本地提交 `9f2774675111739434765d6cdd48c2da7284e45f`，对应GitHub提交 `7e3009902fb4c801ecca43f013114fc372cf4cc0`，源码树一致。
- 内容：480个源码/方法/契约/案例/示例/文档/验收文件，加2份外层交接说明，共482个文件；逐文件SHA256核对通过。
- 源仓库375项回归及19项CLI检查通过；交付目录5项运行检查通过，随附报告的运行时指纹与交付源码字节一致。
- 不包含Git历史、缓存、凭证、私有试卷原文/答案/审阅全文或新增原始讲义；未纳入暂缓的“新建文件夹”。现有公开课程来源快照随核心保留。
- 总体状态PARTIAL，82项均Useful + candidate；尚未验证的语义/案例/真人效果见包内最终验收，不把可运行接口称作自动解题或教学认证。

压缩包大小：1,516,928字节。

SHA256：`613f6e14040383d4751e5af4d1899a0283e30e216dc001c9d043be371aad8be2`。

这是冻结交付包，不自动跟随仓库后来改动。源码仍在仓库根目录维护；以后生成新版应另存包名，保留版本和核验记录。
