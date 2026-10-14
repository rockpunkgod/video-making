# P2 排版后端

基线：`origin/main@3f30b66`。本轮使用独立分支 `redesign/p2-typeset`。
旧视觉分支含与 main 不同版本的学生入口投影，因此没有把它整体合入；
当前后端直接基于 main，已有明暗视觉分支及工程保留不动。
用户已限定本轮只管后端：不改 AE、视觉 token、镜头、字幕或前端样式。

## 接口

旧 `layout_words(...)` 的默认行为保持不变。
显式使用 `flow=True` 时：单个硬换行参与空格排版，空行保留段落边界；
在测量宽度内平衡行长，尽量让冠词、介词和连接词与下一词同行。
`strip_hard_breaks(text)` 仅用于显示文本，不可拿其索引绑定原文证据。
`balance_lines(words, width, min_fill=0.72)` 接受新接口测量过的 token，返回新列表。
`focus_windows(words, max_lines=9)` 按完整行分窗，不遗漏或重复词，也不判断证据位置。

上层入口 `creative_os.typeset.typeset(text, font_path, style)` 接收现有前端规范，
读取 `type_scale.focus_text/focus_line_height` 和
`layout.focus_width/focus_max_lines/focus_characters_per_line`；后端不另定字号。

命令行：

```text
python -m creative_os.typeset --text-file <原文.txt> --font <本地字体> --style <现有规范.json> --output <新排版.json>
```

输出是 `typeset-plan/v1`：

- `source_sha256 / font_sha256 / style_sha256`：原文、实际测量字体及排序规范 JSON 的绑定。
- `words`：原词、原文 Unicode `start/end`、AE UTF-16 `utf16_start/end`、测量宽度与行坐标。
- `lines`：显示行、原文范围、填充比例和排版复看提示。
- `focus_windows`：每窗最多九行，原文范围、逐词位置和测量包围范围。
- `geometry=PROVISIONAL_REQUIRES_AE_MEASUREMENT`：Python 决定分行，AE 原生字形测量仍是最终坐标来源。

不能将显示行拼回去覆盖原文；原文绑定保留原有 CRLF、空格、标点和字符位置。
输出文件已存在时拒绝覆盖。请求不读取 Registry、不调用 Analyzer，不改变教学状态。

## 不可满足的情况

72% 填充率、45–65 字符是排版复看目标，不是绝对保证。
短段落、长词和连接词链可能让目标不可满足：
短行、单词行、无法避免的连接词行尾都会明确标记；单词本身比窗口宽则拒绝。
不加字、不改词、不拉伸，也不隐藏这些提示。
正文的语义段落边界必须来自输入的空行；原始数据没有段落标记时，后端不猜段落。

## 当前验证

合成测试覆盖原文偏移、emoji 的 UTF-16 偏移、硬换行兼容、段落边界、连接词、
不可满足条件、窗口完整覆盖、重复生成、输入修改和样式修改绑定。
本地历史冻结 R06 原文仅用于排版回放，不授予当前教学资格：

| 原文 | 词数 | 行数 | 焦点窗 | 短行 | 连接词行尾 |
|---|---:|---:|---:|---:|---:|
| Bond | 314 | 24 | 3 | 0 | 0 |
| 猫 | 306 | 23 | 3 | 0 | 0 |

两份原文词序和源文件 hash 不变。真实原文与排版 JSON 保留本地忽略目录 `local-data/p2/`。
没有进行前端图像或 AE 测量验收；本轮交付的是后端接口与验证数据。

`python -m unittest tests.test_typeset_v1 tests.test_method_application -q`：16 项通过。
尝试 `python -m unittest discover -s tests` 后数分钟未产生任何输出，已中止；
全量回归未完成，不记为通过，也未据此修改无关测试或教学模块。
