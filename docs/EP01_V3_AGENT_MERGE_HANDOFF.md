# EP01 V3 — Agent 接手、验证与合并指令

目标仓库：https://github.com/rockpunkgod/video-making
代码 PR：https://github.com/rockpunkgod/video-making/pull/7
工作分支：ep01-v3-soft-sound-20261103
目标基线：main
日期：2026-11-04

## 用户已确定的创作决定

- 仅替换声音：V2 完整 4K/24fps 画面原封不动，使用 FFmpeg 视频流 copy，不重新渲染。
- 删除 OPUS 此前加入的**所有旧音效**，不是压小或对旧混音做滤波；电子滋滋声、电子转场/点击提示声全部排除。
- 人声清晰，配乐温柔、克制、具有电影感，拟物音效尽量真实（翻纸、布料、木质轻放），避免尖锐廉价电子音。
- 对齐实际定位、原文提取、选项排除、答案揭晓的动作。只改声音，不动口播文字、镜头、教学内容。
- 真正输出 4K 完整 MP4 + 720p 试听；不把测试、脚本、合并当作成片或发布。

## 必须坚持的技术和音源边界

V2 位于用户 Windows Downloads：EP01_拟物音效重混_V2_4K24.mp4。

V2 只作为**视频输入**。原始 MP4 的声音不一定干净：其中可能已包含 OPUS 音效，直接用它替换 V2 音频不能实现用户要求。因此：

1. 从原始配音源（分 take 的已审口播、对齐收据、Premiere/AE 项目等）找到或重建 **完整时长、带正确静音与时间位置的干净 VO**。自行搜索本机项目路径，但不要改动生产指针、冻结作者稿及宿主单写者协议。干净 VO 不能是 V2/源 MP4 混合音轨重命名。
2. 若需要音乐，独立选择已授权的、可以发布的实际录音音乐；旧混音音乐含 OPUS 效果风险，不复用。记录真实素材链接和许可证据。
3. 新拟物音效采用 Kenney RPG Audio CC0，按真实画面精确补充 cue JSON；自动选帧只可用作初步草稿。
4. 如果找不到独立干净人声，就只可生成标为 DRAFT 的技术试听，不能宣称全部旧 OPUS 音效消除，也不能发布。

## 代码测试

先确认 PR #7 仅改独立 V3 相关脚本、PowerShell 导出入口、测试、文档和专用 GitHub Actions。禁止覆盖主生产链。

分支现有隔离 CI 工作流：.github/workflows/ep01-v3-audio.yml
- Python 脚本编译
- 独立结构测试
- Linux FFmpeg 使用合成 4K 视频/音频（包含独立配乐）的集成测试
- PowerShell 语法检查

可以在本机重复：
    python -m unittest discover -s tests -p "test_ep01_v3_natural_audio.py" -v
    python -m unittest discover -s tests -p "test_ep01_v3_ffmpeg_integration.py" -v

第二条仅当环境变量 EP01_V3_INTEGRATION=1 且 FFmpeg/ffprobe 可用时才会执行测试；没有本片实际 MP4 的自动化测试不能代表真人试听。

注意仓库整体 CI 在 V3 前已有与 FFmpeg 缺失、历史快照散列相关的失败。应对照 main 基线区分，不要为了本次声音修改随意改动其他生产模块。

## Windows 真实导出（严格）

切换到 PR 分支，拿到独立对齐纯 VO 后：

    powershell -ExecutionPolicy Bypass -File .\scripts\ep01_v3_run_windows.ps1 -CleanVoice "D:\EP01\clean_voice_full_length.flac" -Music "D:\EP01\approved_new_music.flac" -CueSheet "D:\EP01\V3_reviewed_cues.json" -Preview720

- -Music 可以省略，但要保证片子没有无意义长时间静默。
- V2 画面文件会在 Downloads 中自动查找，必要时用 -Picture 指定确切路径。
- 输出到 用户 Videos/EP01_V3，含完整 4K、720p、收据。
- 禁止用 -DraftUseOriginalAudio 生成的非干净声音文件冒充正式 V3。

## 合并判断：代码与成片分开

**代码合并允许先于影片导出。** 先检查 PR #7 的真实 diff 与目标 main，确认只触碰本次隔离 V3 文件，专用 V3 CI 通过并没有由本 PR 导致的新失败；若发现基线已有的整体 CI 失败，记录证据而非随意更改别的生产模块。

代码审查合格后：将 PR #7 从 Draft 变为 Ready，按用户授权合并到 main；只合并脚本、测试、文档和专用工作流，不更改用户现有已登记的媒体指针，不触碰 Adobe 生产锁。

**媒体交付仍是单独未完成任务。** 合并后继续寻找真实独立 VO、已授权音乐与真实音效 cue，导出完整 4K/720p 并做人工全片听审。若素材缺失，就明确报告媒体交付受阻，但不必为了缺少本机原始媒体而一直卡住已通过代码审查的 PR。不得把代码合并、合成素材 CI 或 DRAFT 预览当作用户真实 V3 完片或发布资格。

## 交付答复

报告：PR 地址、最终提交与合并 SHA（若合并）、隔离 CI 实测、V2 源文件路径、干净 VO 来源与时长、音乐和 Foley 授权、4K/720p 文件绝对路径、输出收据、听审未完成部分。
