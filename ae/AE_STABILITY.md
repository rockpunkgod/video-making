# AE 26.0 本机稳定性配置与验证

2026-10-05，实际环境 AE `26.0x67`、官方 JUNKDOGE `0.10.8`。
这次配置针对本机已观察到的故障，不是所有机器的通用优化模板。

此前原生 H.264 导出返回“意外错误，错误代码 `\1`，请重新启动”；AE 进程仍在、
官方桥仍响应。这是导出失败记录，不能直接等同进程崩溃。Windows 近一天记录中有
`RADAR_PRE_LEAK_64 / AfterFX.exe` 内存泄漏预警，未找到对应的 Application Error
进程崩溃记录；更早或未被系统记录的故障不能据此排除。工具启动导致的 CEP 加载
异常是另一条启动路径问题，目前使用用户正常快捷方式恢复，不宣称已修好启动环境。

## 已应用的配置

| 偏好设置 | 原值 | 新值 | 原因 |
| --- | --- | --- | --- |
| Disk Cache Controls / Compressed | true | false | 避开 Adobe 列出的 AE 26.0/26.2 压缩缓存兼容问题 |
| Speculative Preview Preference Section / Cache Frames When Idle | true | false | 减少此自动化生产会话的后台预缓存负载；不是已证明的根因 |

Adobe 的[已知问题说明](https://helpx.adobe.com/after-effects/desktop/troubleshooting/fixed-and-known-issues/known-issues-after-effects.html)
建议对受影响配置关闭 Preferences → Disk → Disk Cache → Enable Compressed Frames
(Lossless)。本机回读确认该功能原先开启。

修改使用同一官方 MCP 的 `ae_exec` 调用 AE 自身 `app.preferences` API，作用域
`PREF_Type_MACHINE_INDEPENDENT`，保存到磁盘、reload 后按 **Bool** 回读。
不能用 `getPrefAsLong` 判定 Bool：本机该读法曾返回 0，而 Bool 读法正确返回 true。
工程先保存，并清理 RAM cache；没有删除用户素材或整个磁盘缓存目录。
GPU 驱动、其他插件、MFR、已有输出预设和项目教学数据没有被重置。

本机完整偏好设置备份在忽略目录
`local-data/v8.1/ae-stability/preferences-before/`。前后回读、checkpoint、实际请求与
两条短片重复导出结果保留在同目录。撤销本次配置只需在 AE 设置中重新启用上述
两个选项；如需完整恢复备份，应先关闭 AE，并核对同版本备份，避免覆盖运行中设置。

## 实际验证与限制

配置后，同一 AE 进程原生 H.264 15 Mbps 预设连续输出三条完整内部视频
（73/86/78 秒），再通过两个独立 `ae_exec` 调用分别导出 2 秒短片。
五次均成功，没有中途重启；两次短片的全解码也通过。最后 Bool 回读仍为 false。
完整视频通过 1080×1920、30 fps、时长和全解码核验，未改教学包。

这是本次会话的稳定性复测，不能证明任何工程都永不崩溃，也不能仅凭该结果把
此前 H.264 错误归因于压缩缓存。若再次发生，保留该次 checkpoint、官方 recoveryId、
AE/Windows 日志，先区分编码失败、桥超时和进程崩溃，再做单因素配置调整。
不循环盲重试、不自动覆盖 MP4、不为排错引入第二套 AE bridge。
