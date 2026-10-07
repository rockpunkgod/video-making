# Student POV 画面准备 0.1

这条增量通道消费已批准的 Student POV Copy、Copy Projection、PedagogyPlan、冻结
Bundle 和当前提供的 Status。当前只支持 R02 已有的局部候选排除。它把原题、既有
关系及实际产物转成原生 AE 画面，再建立 Premiere 画面与钢琴时间线。

用户正在优化声音时，生产停在 `PICTURE_AND_MUSIC_PREPARED_VOICE_PENDING`。
这是制作组件，尚不是带配音样片；不生成临时声音，不导出或交付最终样片。

## 冻结输入与画面

`creative_os.student_sample.build_spec` 先重放当前 Copy 校验，再校验显式 Direction。
Direction 提供构图、关键帧和已经绑定的关系；没有句法分析、自由解题、教学压缩
决策或新的教学 Review。保持 ANSWER 和 Pedagogy 的职责。

- 每个显示文本绑定提供的 document、JSON pointer、完整原值 SHA，摘录另绑定
  Unicode 起止偏移。只允许布局换行和空白归并，不能改字、词或标点。
- 原题和选项来自 Plan；前台文案来自已批准 Copy；证据摘录只能使用当前 Plan
  明确指定的焦点证据。后台推理和 Tell Later 不能作为新的画面文案。
- 连线、标记与划除绑定当前动作或已有证据，不能借另一动作的凭证。
- 原题题干固定在上方，先显示原始候选，再展开方法动作；消费者画面不显示内部
  方法编号。剩余候选保持相同墨色及未选中状态，排除必须匹配当前实际动作。
- Tell Now 的必要前台表达仍然存在。已由审阅决定使用证据或候选状态覆盖的边界，
  不再被 Renderer 改写成重复提醒。

Spec 使用仓库 Canonical JSON SHA，记录资产语义 SHA、Plan/Copy SHA、最终 Copy
锁、字体文件 SHA 和全部 Direction。重复构建得到相同 Spec。结构校验和 Native
Audit 是确定性检查，不是语义认证、学生效果认证或 Human Taste 批准。

## 原生画面执行

```text
python -m ae_production.student_picture build <ae-request.json>
python -m ae_production.student_picture audit <ae-request.json>
python -m ae_production.student_picture preview <ae-request.json>
python -m ae_production.student_picture render <ae-request.json>
```

请求显式提供 `spec / copy / projection / plan / bundle / status`，以及新的工程路径、
输出目录和预览时间。文件路径留在本地配置；引用身份由 ID、版本和 SHA 维持。
执行继续使用现有 AE MCP 的 execution guide、确定性 JSX 和 TIFF 渲染通道。
H.264 编码仅压缩原生帧，不重新绘制教学画面。

Native Audit 回读文字、字体、颜色、字号、行距、层启用状态、原点、变换、关键帧、
标记尺寸、背景与绑定，拒绝额外层、文字动画替换、效果/遮罩，以及已检查的位置、
比例、透明度和文案属性上的表达式。数据检查
之后还要检查真实预览和关键转变帧，不能用属性检查代替观感。

写入超时不表示没有发生。保留原请求和错误，先回读当前工程。对于晚完成的完整
构建，可以调用 `reconcile-build`：要求唯一的 Spec 匹配、正确工程路径和完整
Native Audit，再恢复本地 identity；该命令不重试写入。
原生 checkpoint 可能保存当前工程并改变其文件字节；不能据此宣称旧 AEP 字节
完全未变。需要保留特定旧文件的原始字节时，应在 checkpoint 前独立备份。

## Premiere 画面与音乐准备

```text
python -m premiere_production.student_picture assemble <pr-request.json>
python -m premiere_production.student_picture audit <pr-request.json>
```

请求提供画面生产请求、画面 Receipt、Audio Plan、新 PR 工程、序列预设及本地
连接配置。音量属性采用已回读的本机名称。序列为 1080p24、48 kHz 双声道：
V1 为已验证的无声原生画面；A1 留空；A2 为用户提供的本地钢琴录音。
工程只导入这两个媒体源，拒绝额外声音或另一版素材；回读来源、源范围、时间线
和音乐音量包络。另登记画面段落与待配音的编辑标记。

钢琴为内部试制素材，录音权利和实际听感保持单独状态。暂定音量包络不等于
最终混音批准。AE/PR 工程、题面、Copy、声音、音乐、视频及逐帧材料均留在
忽略的 `local-data/`；公开仓库只保存工作流、脱敏报告与合成测试。

## 等待声音与后续交付

```yaml
preparation_state: PICTURE_PREPARED_VOICE_PENDING
voice_status: AWAITING_USER_AUDIO
user_voice_ready_signal_received: false
sample_delivery_allowed: false
public_render_ready: false
```

Voice Slots 和画面时长都是编辑预估，不是实际声音对齐凭证。配音不用为了贴合
占位时间而改变自然表达。收到用户明确的声音完成通知后，绑定最终声音及文字，
按实际语速调整节点、音乐和字幕；核心 Payoff 完成后保留短暂停顿，不能让占位
标记直接冒充最终时序。若实际文案改变，原 Copy/编辑审核不得继承。

这组命令没有最终样片导出操作，`require_sample_delivery` 始终拒绝这类准备物，
即使自行改写本地 ready 标记。之后的带配音内部样片有独立媒体与检查记录。
公开资格仍需教学、最终实际展示来源、最终编辑和当前上游全部通过。
