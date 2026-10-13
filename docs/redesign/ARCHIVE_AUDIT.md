# 被跟踪 ZIP 核查

2026-10-13 在 `main@c32714f` 基线上读取两个 ZIP，全程内存解码，没有把题面解压到公开目录。

| 文件 | 条目 | Case 文件 | 有题面文本的 Case |
|---|---:|---:|---:|
| ANSWER-Method-Engine-9f27746.zip | 482 | 106 | 7 |
| Video-Production-OS-v0.1.zip | 511 | 106 | 7 |

两份均包含 F01 的三条课程例片段与 G01 的四条课程例片段。G01 的来源登记明确包含
2021/2022 高考试题；F01 包含模考课程例和英文候选句。它们不是空的 Case 模板。
这里不复述原句；逐条路径、字符数、源登记和 SHA 保存在本地 `ARCHIVE_AUDIT.json`。

本分支停止跟踪这两个 ZIP，并忽略 `deliverables/`。本地原文件保留。
没有把带题面的 ZIP 改上传为 Release 附件。做附件前仍需去除私有/真实题面或确认
所展示内容的来源资格，移动到 Release 本身不能解决这一点。

旧提交仍含这些文件。本轮没有改写 Git 历史、强推或删除本地备份。
如需清除历史，需要单独确认具体范围；该步骤不属于当前 P0 内容制作。

复核入口：

```powershell
python -m scripts.audit_archives PATH_TO_ARCHIVE --output local-data/redesign-v1/ARCHIVE_AUDIT.json
```

此报告只说明归档内容及其记录的出处，不是来源权利或公开发布认证。
