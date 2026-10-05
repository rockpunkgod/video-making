# Premiere 配置验收

配置阶段完成；本报告不代表 V9.1 Hero Segment 或创意审核完成。

## 本机实测

- Premiere Pro 2026（26.0.0.72），Windows，中文界面。
- 使用上游 [premiere-pro-mcp](https://github.com/leancoderkavy/premiere-pro-mcp) **1.19.1** 的签名 CEP 连接器和原始服务器；未复制工具实现，未新建第二套主机桥接。
- Codex 已注册原始 stdio 入口，限制为 **28** 个生产工具；启动超时 30 秒，工具超时 180 秒。实际 stdio 初始化、工具目录和 `verify_premiere_connection` 均通过，CEP、工程、活动序列全部返回 ready。
- 新建并保存纯合成测试工程；创建 1920×1080、24 fps、方形像素、48 kHz 双声道序列。实际 timebase 为 10,584,000,000 ticks/frame。
- 媒体导入、覆写、视频／音频关联裁剪、分别移动视频和音频、标记、保存均在真实主机执行并读取结果。
- 中文音量属性按主机返回的“音量／级别”设置，读取值确认 -6 dB 对应的归一化幅度。上游快捷音量工具不兼容此中文属性名称，未将失败记为通过。
- UTF-8 SRT 已导入；实际节目监视器显示“中文配置测试 · 非教学内容”。CEP 的字幕读取接口不支持结构回读；创建回执的 `verified: false` 保留，不自动升级。
- Premiere 原生 H.264 本地导出通过；输出 1920×1080、24 fps、78 帧、3.25 秒、AAC 音轨，完整解码无错误。所用安装目录内 EPR 是本地导出预设，没有使用 Frame.io 上传。

## 已处理的配置问题

1. 工具直接启动时 CEP 曾报告 `PlugPlugSetup` 失败；通过 Explorer 启动保存的快捷方式后，扩展菜单及 CEP 引擎恢复。此次实测确认该启动方式可用，未声称消除所有崩溃原因。
2. 默认 TEMP 桥接目录继承其他账户写权限，上游安全检查拒绝启动。改用当前用户目录下的专用桥接目录；仅为新目录设置当前用户、SYSTEM、Administrators 权限。未放宽上游检查，未修改全局 TEMP 权限。
3. 上游预设搜索未找到非默认盘的安装目录；改为显式传入安装目录中经主机验证的 EPR。原始 Adobe 预设未修改。

## 后续交付约束

- 当前测试 EPR **没有烧录字幕**。节目监视器的字幕显示通过，不等于 MP4 的字幕交付通过；正式交付前必须另行配置并验证烧录字幕或绑定字幕文件。
- 上游 `move_clip` 只移动指定片段，不自动移动关联音频。流程必须分别执行并检查同步，不能仅凭视频回执声称音画同步。
- UXP 为上游预览能力，本机未安装／验证 UXP 插件；当前生产连接使用 CEP。不能以静态兼容信息宣称 UXP 已连接。
- 配置跨系统重启恢复尚未验收；重启后先执行只读连接检查，必要时打开连接器面板并 Start。
- Teaching、Source Display、Editorial、Human Taste 均未因此获得通过；公开发布资格保持 false。

## 可重复配置

在仓库根目录运行 `scripts/configure_premiere.ps1`，显式提供本机 Premiere 可执行文件路径；需要启动时加 `-Launch`。脚本将运行时、配置备份和快捷方式放入忽略的 `local-data/premiere/`。在 Premiere 官方连接器面板填写脚本输出的 Bridge directory，Save 后 Start。

Codex 配置方式依据 [OpenAI Docs：MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。新增工具需在重新加载的 Codex 聊天中使用；配置时已经通过独立 stdio 客户端实测相同入口。

本机测试工程、视频、音频、字幕、预设副本、截图、日志及原始回执全部保留在忽略的 `local-data/v9.1/pr-config/`，不提交媒体或本机凭证。

自动验证：6 项配置／响应边界测试和 20 项现有 Creative OS 回归。覆盖配置重放、其他连接配置保留、远程端点拒绝、明确失败处理，以及“字幕请求接受不等于已验证”。
