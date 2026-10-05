# V8 AE Production Layer — Engineering Acceptance

日期：2026-10-05。基线：`8095b948`，V0–V7 Engineering MVP。

工程结果：**PASS，三个真实内部 MP4 已完成**。教学认证、来源放行、编辑放行均
**PENDING**，所有交付 `PUBLIC_RENDER_READY=false`。录制口播同步与最终审美验收
**PARTIAL / 待人工观看**。本报告不认证方法有效性、完整答案或公开教学资格。

## 本轮增量

新增独立 `ae_production/`、`ae/schemas/render-contract.json`、自有 Swiss Academic
Motion tokens、通用 `METHOD_DEMO_MASTER` JSX、实际 AE 布局审计、CLI 与测试。
ANSWER、Registry、Case、解题逻辑、V0–V7 teaching/package schemas 没有修改。
生产模块不导入 Analyzer，也不读取原始教学文件。它只投影 Video Package 已冻结
的 scene、claim、role、action、evidence、Stop 和最终文案。

Render Contract 绑定 package ID/hash、manifest hash、final-copy hash、当前状态输入、
design/template version、实际 JSX hash、render ID、组件来源 pointer/value hash。
相同输入重放契约一致；修订保留历史工程与 checkpoint，不覆盖旧版包。

执行桥为官方 **JUNKDOGE ae-mcp v0.10.8**，实际 AE **26.0x67**；本机 native AEX
未启用。官方签名 Windows panel SHA-256：
`85616427077f433b27fed87ae4b5eaa0872a56f0331780de33d77024cb5d87f7`。
本层 HTTP client 仅调用其公开 MCP 工具，没有第二座执行桥。
Craft 使用 iart 的 composition/art-direction/AE skills，Critique 使用 Lobzy 的
motion-design-critique/visual-diagnostics；自有 tokens 保持品牌权威。
具体入口及第三方项目链接见 [AE README](ae/README.md)。

## 真实交付

完整交付在忽略目录 `local-data/v8/delivery/`，公开报告不包含原题原文、教学审阅
全文、截图或试卷。每个 pilot 子目录保留 package、manifest、status、Render Contract、
MP4、实际 AE 表达式和布局审计、checkpoint、媒体探测、Critique、动态抽帧。

| Pilot | 最终修订 | AE comp | Render ID 前缀 | MP4 秒数 / 帧数 | 文件 bytes |
| --- | --- | --- | --- | --- | --- |
| F01 q36 | r4 | 425 | a04e2b31cf6b | 73 / 2190 | 12490600 |
| G01 q59 | r3 | 499 | 86dcd860b91c | 86 / 2580 | 13297746 |
| R02 q26 | r2 | 565 | 6231ab7a463a | 78 / 2340 | 11993521 |

均为 **1080×1920、H.264、30 fps**，`ffprobe` 核验时长、帧数和尺寸；
`ffmpeg` 全片解码没有报错。视频均为静音文本计时预览。

`delivery/METHOD_DEMO_MASTER.aep` 只保留三个最终 comp、三个绑定 JSON footage 及
所属文件夹（7 items），替换数据路径后再次独立核验实际 contract、全部文字和字体，
并重新捕获画面。随工程交付三个 JSON 依赖，不能单独搬走裸 AEP。
旧工程、旧 captures 与修订 checkpoint 仍在 `local-data/v8/pilots/`。
`delivery/checkpoint.json` 保存收集后真实 checkpoint；`delivery-checksums.json` 保存
文件校验值。部署字体要求与启动步骤见 AE README。

## 视觉与迭代结果

一个 Master 根据 typed output 和组件构建全部三条内容，没有按方法 ID 分叉模板。

| 内容 | 真实视觉结构 | Critique → 修订 |
| --- | --- | --- |
| F01 | 七个候选按已有分组轴展开，固定字号分为 4+3 页 | 修正 AE paragraph 原点/shape 默认位置引起的裁切；保留中性卡片，未将 helper 升级成答案 |
| G01 | 四节点纵向路径、原有 supporting excerpt、终端 Stop 线 | 从已有动作文案投影中文节点；补展示已有原句；终点没有后续分支或 word_answer |
| R02 | 原句证据页 → 两行原有关系操作数 → 单项 verdict | 在关系页前补已有原句，完整长 Stop 的标线按实际字框高度延伸；无整题答案暗示 |

使用六栏、五级固定字体与语义颜色；动画限定 reveal/focus/compare/eliminate/connect。
12-frame soft-out、24px rise、2-frame stagger，不使用 spring/overshoot/wiggle。
动态抽帧观察到有序入场和稳定阅读段。字体不随字数缩小；过载分页或 BLOCK。

每条本地 `motion-critique.json` 含 issue、severity、scene_id、component_id、
recommendation、修订结果及以下十项判断：

| Critique 项 | 结果 | 依据及限制 |
| --- | --- | --- |
| Hierarchy | PASS | 角色 rail、主信息、字幕、来源层次明确 |
| Composition | PASS | 单一教学焦点，正文与字幕安全区分离 |
| Typography | PASS | 固定五级；实际 AE MicrosoftYaHei；无字体替换 |
| Readability | PARTIAL | 字框无溢出；部分中英技术文案较密，需人工观看 |
| Timing | PARTIAL | 沿用冻结时序、字幕文本逐字完整；尚无录制口播同步 |
| Easing | PASS | 实际 MP4 入场抽帧、稳定段及 AE 表达式评估 |
| Motion Purpose | PASS | 分组、路径、关系与局部排除各自承担信息作用 |
| Information Density | PASS | 分页保留证据/Stop，未 shrink-to-fit |
| Visual Balance | PASS | 左对齐和一致留白，无装饰竞争焦点 |
| Brand Consistency | PASS | 三条同 tokens、同 JSX 和五类 motion |

这些 PASS 是工程/视觉检查，不是语义真实性认证，也不代替用户审美批准。

## 十项验收

| Integrity | 结果 | 可核验证据 |
| --- | --- | --- |
| Data | PASS | package/manifest/copy 精确绑定；实际 AE JSON 与 contract 再比较 |
| Evidence | PASS（结构） | 每个场景保留原 evidence refs/full payload；实际展示文字核验 |
| Role | PASS（结构） | 上游 role 直接投影；tamper 测试拒绝 |
| Stop | PASS（结构） | 原 Stop 全文保留，截图可见；删除测试阻断 |
| Layout | PASS | Pillow 预检 + AE sourceRect、font、文字内容/时段碰撞独立检查 |
| Motion | PASS | 最终 comp 表达式全量检查、真实像素与 MP4 动态抽样 |
| Timing | PARTIAL | 字幕不漏字、最多两行、最低 hold；真实配音尚未接入 |
| Reusability | PASS（本轮 scope） | 三条由同 METHOD_DEMO_MASTER；framework 契约投影有实现，尚无真实 framework pilot |
| Traceability | PASS | 全部身份/hash、build/preview/collect/checkpoint/媒体 probe 保存在本地 |
| Staleness | PASS | 复用 V7 index；三个真实包的隔离撤回模拟都使 preview stale，派发前拒绝、AE 调用次数 0 |

失效模拟在独立 `withdrawal-simulation.json`，未修改真实 ANSWER 状态或创建新 Review。
静态视频不能感知未来撤回；收到新 status 后下一次操作校验并传播，旧 MP4 只可作为
历史重放。`dependency-index.json` 注册了三个 package → render 关系，无新数据库。

## 测试与已知缺口

`python -m unittest discover -s tests -q`：**440 tests PASS（288.756 秒）**。
V8 新增 16 个测试，覆盖重复契约、只读输入、manifest/role/Stop/组件篡改、缺少/撤回
状态、真实 AE 绑定漂移、字幕完整性、短时长阻断和 preview 失效传播。
布局压力样本包括短文、长句、长词、中英混排、2/3/4 行、七候选、长证据、长字幕；
固定字号保留逐字文本，不安全槽位拒绝。它们是明确的合成测试，并非新真实 Review。
AE/video schema 生成检查、`git diff --check` 通过。上游目录和 schemas diff 为空。

实际 AE 测试发现并修复 JSON `sourceData=null` fallback、paragraph anchor、shape
默认中心、Stop marker 高度以及 native render 外层 Undo 组问题。H.264 曾报原生
unexpected error；保存工程后由用户正常启动 AE，最终两条成功导出，保留失败记录。
没有把失败的调用/空文件计为完成。恢复时依据返回 recovery ID 和当前队列状态。

本轮不做正式人工教学认证、版权放行、最终编辑放行、真实 Astra、完整 expression SDK、
第二桥、自动发布或 V9–V13。三个内部真实预览交付后停止 V8，下一步设计判断基于
用户观看这些画面后的反馈。
