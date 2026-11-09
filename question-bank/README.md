# 题目库

这里保存截至 2026-11-09 本地已有题库的归档：原题文件与图片、转写、案例数据、学生讲解、争议说明、复核及整卷回归记录。原文件逐字节保存，相同内容只存一份；不是新增题目或重新验收。

当前方法依据为 ANSWER `59190489abd3e0fb6543c9a04e137881ae98cd88`。ANSWER 仓库未修改。

## 使用

在 video-making 仓库根目录执行：

```powershell
python scripts/question_bank_archive.py verify
python scripts/question_bank_archive.py restore --destination E:/题库还原
```

还原后，原目录结构位于 `E:/题库还原/local-data/`。已有同名不同内容的文件会阻止还原，避免覆盖。只还原当前学生讲解：

```powershell
python scripts/question_bank_archive.py restore --destination E:/题库还原 --prefix local-data/当前可用案例讲解_20261106_5919048_r1/
```

## 当前入口与历史

- 当前学生讲解：`local-data/当前可用案例讲解_20261106_5919048_r1/`，7 组、322 条（290 条客观题讲解、13 条写前指导、19 条争议说明）。
- 当前兼容性回放：`local-data/answer-alignment-20261106/question-replay-r3/`，271 个输入记录、5,486 个执行条目；含来源变体、子集与镜像，不能视为独立试卷数或独立题数。
- 完成状态：`local-data/CURRENT_TEACHING_AND_QUESTION_ALIGNMENT.json` 及各批次 `CURRENT_PROCESSING_INDEX.json`。
- 早期题库：`local-data/restored-organized-20261024-r1/E/自媒体/video-making/local-data/organized-pdfs/`。这是历史恢复路径，原始题库、Case 版本和审核记录均保留。
- 其他批次和旧版讲解保留原路径和状态，不能覆盖当前入口。尚未完成的任务、争议、撤回、来源限制及阻塞状态不变；`all_uploaded_complete` 仍为 `false`。

## 存储与证据边界

`manifest.json` 将原仓库相对路径映射到 SHA-256。`objects/` 内是以原内容哈希命名的 gzip 文件；解压所得字节与原文件一致。这样既保留全部收录版本，又避免多次提交同一原题或图片。清单列出收录目录、对象大小与排除范围。

历史 JSON 中的原电脑绝对路径、原审核哈希和历史引用没有重写，以免改变证据。换机器后应使用本清单与还原路径定位文件；原分析程序不会因此自动支持任意新路径。归档校验只证明传输完整性，不授予新的正式 Case、Blind、真人教学、版权或发布认证。

仅收录已有题库批次。不混入付费课程、登录数据、ANSWER 副本、临时缓存和视频工程；未导入本地题库的外部下载目录不属于本次快照。
