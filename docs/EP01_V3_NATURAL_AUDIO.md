# EP01 V3 自然拟物声重混：执行说明

## 当前状态与范围

- 本分支只处理现有 3840×2160 / 24fps MP4 音轨；原始画面码流用 FFmpeg copy，不重编码。
- 只使用原始 4K MP4 的声音作为底层。绝不混入 V2 电子音效混合 stem；这一原则不能自动保证原片本身没有电子杂声。
- 新增自然声只来自 Kenney RPG Audio 官方授权的 CC0 素材，保存声源链接、样本名和压缩包 SHA256。
- 不修改已有 Adobe/生产入口及受保护媒体指针，不改文案、教学和镜头。
- 自动镜头变化的时间位置只是音效草稿，未看实片，不能假装与提取、排除和结算精准同步。
- 目前代码已提交；真实编码/听审和发布批准均未完成。

## Windows 本机一条命令

将 ChatGPT 文件库中的原始视频「英语有画说_EP01_首发候选_4K24.mp4」放在 Windows Downloads。不要用 V2 MP4 替代。需要 Python 3.10+、FFmpeg 和 ffprobe 在 PATH。

在对应工作分支仓库根目录运行：

    powershell -ExecutionPolicy Bypass -File scripts\ep01_v3_run_windows.ps1 -Preview720

如原片存放在其他路径：

    powershell -ExecutionPolicy Bypass -File scripts\ep01_v3_run_windows.ps1 -Original "D:\影片\英语有画说_EP01_首发候选_4K24.mp4" -Preview720

脚本自动下载 Kenney RPG Audio 音效 ZIP。网络下载失败时，可手动从 https://opengameart.org/content/50-rpg-sound-effects 下载 RPGsounds_Kenney.zip 后传入 -FoleyZip 参数。

输出目录为 用户 Videos/EP01_V3：

- 英语有画说_EP01_V3_自然拟物_4K24.mp4 — 4K 全片，原画面 copy 与 320 kbps AAC 新音轨
- 英语有画说_EP01_V3_试听_720p.mp4 — 可选小体积手机试听
- 英语有画说_EP01_V3_自然拟物_4K24.v3_receipt.json — 编码和音效来源收据

## 真实镜头时间对齐

素材含 paper（翻书）、swish（柔和布料摩擦）、tap（轻放书本）、settle（合书）。

自动 cue 只根据低分辨率画面变化生成稀疏草稿；正式使用应通过实际视频的真实时间戳编写 cues.json，示例结构如下（**例子里的时间是假设值，禁止直接当成影片真实时间点发布**）：

    {
      "cues": [
        {"at": 12.5, "material": "paper", "gain_db": -30},
        {"at": 35.0, "material": "swish", "gain_db": -31},
        {"at": 55.0, "material": "tap", "gain_db": -27},
        {"at": 77.0, "material": "settle", "gain_db": -30}
      ]
    }

使用准确时间表：

    powershell -ExecutionPolicy Bypass -File scripts\ep01_v3_run_windows.ps1 -CueSheet "D:\制作\V3_cues.json" -Preview720

## 交付检查与权限

- 先完整听 4K/720p，包括耳机与手机；关键画面对应的音效时间要逐个检查，整片口播清晰，无突兀或电子滋滋声。
- 程序自动检查 4K 分辨率、24fps、时长、音频存在和输出编码；这些不构成听感/视觉验收。
- 本次确认的 CC0 许可只覆盖新加的 Kenney Foley，不代表原片配乐及其他来源已具备公开上传权利。仓库原有肖邦录音属内部 scratch，公开发布前仍须确认录音版权或替换。
- 未完成真实输出、全片审阅和用户验收前，公开发布状态始终为否。

## 修改文件

- scripts/ep01_v3_soft_audio.py — 完整音频重混与授权声源核验
- scripts/ep01_v3_run_windows.ps1 — 一条命令生成4K和可选手机试听
- tests/test_ep01_v3_natural_audio.py — 离线代码回归，不是主观试听
