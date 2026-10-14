# style-v1：P1 视觉选择

2026-10-14 新增[明暗双场候选](light-dual-space-v1.json)及
[镜头实施说明](../../docs/design/light-dual-space.md)：灯下暖纸进入暗场思考，
以照明或曝光替代透明度退场。该候选尚未接入静帧模板，保留旧输出供比较。

[style-v1.json](style-v1.json) 是新制作方向的候选规范。B站 16:9 横屏为主，
竖屏从已完成横屏片中派生。所有字号使用 1920×1080 作者坐标，交付母版按 2 倍输出；
字号指相机投影后的屏幕尺寸。全景只建立原文空间，46px 焦点窗承担阅读。

P1 只交付真实题静帧、字体比较和[对比度报告](../../docs/design/style-v1-contrast.md)。
静帧不会证明电影感、运动节奏、声音、方法迁移或发布资格。字体、配色、字号确认后
才进入 P2；不自动开展模板化、声音包装或整期重建。

英文候选 Source Serif 4 的上游是 [Adobe 官方仓库](https://github.com/adobe-fonts/source-serif)，
按 [OFL 1.1](https://github.com/adobe-fonts/source-serif/blob/release/LICENSE.md) 提供。
与本机 Georgia 使用同一焦点句、屏幕字号和构图比较。字体只安装在本机，不提交字体文件。
本机 Noto Sans SC / Noto Serif SC 的 Medium / Bold 实例用于中文；原始字体保留。

满橙色底与指定炭黑只有 4.04:1；候选规范增加 `highlight_ink`，满橙色高亮上的
字达到 4.73:1。常规纸色、墨色和橙色不变。比较蓝作为低透明度高亮底，保留黑字。

静帧制作复用 JUNKDOGE 的 `JunkdogeClient` 与原生 Render Queue 单帧 TIFF 输出：

```powershell
python scripts/render_style_stills.py build PATH_TO_EXISTING_R02_PLAN local-data/style-v1/NEW_P1
python scripts/render_style_stills.py render local-data/style-v1/NEW_P1
python scripts/contrast_check.py
```

输入只消费已冻结的原题、原文、动作和明确的 D 排除；不解新题、不改教学事实、
不把一项排除展示为整题答案。真实题面、PNG、AEP、字体和本地原生诊断均留在 `local-data/`。
内部草稿没有新增自签 `spec_sha`、强制 A/B 视频或人工通过门；原冻结接口和公开发布门保留。

旧 Swiss v0.1–v0.5 已移到 [legacy](legacy/README.md)。旧生产接口明确读取历史文件，
不是把未确认的 style-v1 偷换进既有生产链。平台目录标记主横屏和派生竖屏；
历史消费者的默认竖屏坐标保持兼容，P3 新镜头模板才正式接入主横屏。
