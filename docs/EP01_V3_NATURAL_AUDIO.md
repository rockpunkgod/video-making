# EP01 V3：OPUS 旧音效全替换，4K 画面不重渲

## 核心约束

1. **画面仅取自** V2 的 EP01_拟物音效重混_V2_4K24.mp4，3840×2160/24fps，FFmpeg 使用 -map 0:v:0 -c:v copy，**完全不取 V2 音频**。
2. **人声必须来自独立、未经 OPUS 音效混合的整片 VO 音轨**。例如从原始配音 takes 按真实时间戳重建的全长 WAV/FLAC。必须与 V2 画面完整对齐。
3. **所有旧 OPUS 音效必须被排除**：不复用 V2 音轨、旧效果 stem 或任何可能含旧效果的原始整轨。只混入新获得的 Kenney CC0 实录拟物音效，音乐为独立的、经过授权的单独音轨。
4. 具体文字定位、提取、选项排除和结算音效，须按真实画面逐个核对；自动镜头变化时间只可用于草稿。
5. GitHub 代码合并、媒体编码、主观听审与发行权利属于独立阶段，不得混为一谈。

### 原始 MP4 不等于干净 VO

原始 MP4 的混合声轨可能已经含 OPUS 曾添加的音效。直接用它替换 V2 的声音仍会保留这些效果，FFmpeg 无法从普通混合音轨无损提取绝对纯净的人声。严格模式因此要求独立声源；**没有独立干净 VO，就不能声称 OPUS 音效已全部消除**。

## Windows 一条命令

已知 V2 MP4 在 Downloads。请先从源工程的原始配音文件里重建**带正确时间轴、完整时长**的纯人声音轨。安装 Python 3.10+、FFmpeg 和 ffprobe，并切到分支 ep01-v3-soft-sound-20261103：

    powershell -ExecutionPolicy Bypass -File .\scripts\ep01_v3_run_windows.ps1 -CleanVoice "D:\EP01\clean_voice_full_length.flac" -Music "D:\EP01\approved_new_music.flac" -CueSheet "D:\EP01\V3_reviewed_cues.json" -Preview720

- -CleanVoice：必需；来源必须是真正独立、无旧 OPUS 效果的人声，时长误差不超过 0.5 秒。
- -Picture：可选指定 V2 画面完整路径；否则自动搜索 Downloads 中唯一的 EP01...V2...4K24.mp4。
- -Music：可选独立有授权的新配乐；**绝不把旧混合音轨改名当作配乐**。
- -CueSheet：可选已核对真实时间戳；省略时仅为镜头变化自动猜位的待审草稿。
- -FoleyZip：网络无法下载 Kenney 官方 CC0 素材时指定预先取得的音效包。

默认导出到 用户 Videos/EP01_V3：
- EP01_V3_clean_source_4K24.mp4 — 原 V2 4K 视频比特流 copy，新 AAC 320k 声轨
- EP01_V3_clean_source_preview_720p.mp4 — 可选小体积试听文件
- EP01_V3_clean_source_4K24.v3_receipt.json — 声源、许可证、时间点和编码验证收据

### 仅用于排查问题的旧混音草稿，不能发布

如尚未取得干净 VO，允许通过下述显式开关预览技术流程：

    powershell -ExecutionPolicy Bypass -File .\scripts\ep01_v3_run_windows.ps1 -DraftUseOriginalAudio -Original "D:\EP01\EP01_original_4K24.mp4" -Preview720

此时生成带 DRAFT_unverified_audio 的文件；收据注明 DRAFT_OLD_OPUS_EFFECTS_MAY_REMAIN。**不得用它验证“OPUS 全部删除”，不得作为发布版。**

## 真实音效对齐

Foley 音源：Kenney RPG Audio CC0；paper（翻书）、swish（布料摩擦）、tap（书本轻放）、settle（合书）。仅示例 JSON 结构如下：

    {
      "cues": [
        {"at": 12.5, "material": "paper", "gain_db": -30},
        {"at": 35.0, "material": "swish", "gain_db": -31}
      ]
    }

**上述时间是格式示例，不是本片的已验证镜头时间，禁止直接作为发布版本。**

## 验收 / 合并的边界

- 实际比对 V2 视频流、帧数和时长，核对原始 4K 画面未改变。
- 在耳机和手机上从头到尾试听：确认没有任何旧 OPUS 音效、滋滋电子音、卡顿、爆音、过度静音、人声被音乐覆盖。
- 逐帧或逐镜头检查新音效与提取、排除、答案揭晓的同步；重新修正误放的 cue。
- 检查原始配音、独立新音乐、Kenney Foley 的真实授权。肖邦演奏录音的权利需要独立确认。
- 未实际完成编码和人类感官检查，不得声称可发布。编码收据只是程序检查，不是创意验收。

### 仓库交接

PR #7：ep01-v3-soft-sound-20261103 → main。隔离脚本不得改动原有 Adobe/PR/AE 当前生产入口和媒体指针。

- scripts/ep01_v3_soft_audio.py：音频重新混合、干净人声强制验证
- scripts/ep01_v3_run_windows.ps1：Windows 一条命令和 720p 预览
- tests/test_ep01_v3_natural_audio.py：结构与声源安全测试
- tests/test_ep01_v3_ffmpeg_integration.py：合成素材真实 FFmpeg 测试（不等于本片导出）
- .github/workflows/ep01-v3-audio.yml：隔离 CI

另一个 Agent 在合并前须复核当前 PR 的最新提交和专用 CI，执行本机真实媒体 QA；代码合并不授权公开发布。
