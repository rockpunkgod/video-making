# Reality × Cognitive Space — Native Fast-Pass Proof

日期：2026-10-11。生产基线：`main@2acfabda3a54c083f339b7ad36ec4ab1e0d1fbeb`。

本轮把已认可的 r02 混合空间方向转为原生 AE 相机实验。沿用同一真实 R02 归属比较题、原文、审阅关系和单候选排除动作；只制作一遍原速，不重做 B06，不加入慢放或完整影片。

## 实际交付

两条全屏 **18 秒、3840×2160、24 fps、432 帧、Rec.709、无声**影片：

| 版本 | 唯一控制变量 | 实际媒体 SHA-256 |
| --- | --- | --- |
| A | Camera Position / Point of Interest 固定在初值 | `a512eb9607a9c619056569b3f0c7fbe21bfa7254ae41d59cc6e9ca2430a16baf` |
| B | 同一世界中的连续寻找、捕获、比较和返回 | `6316929570c46f26b840c849c2535fdcdecfe05e06b1bbc1fa9e5db6bbc10c12` |

两版信息、字形对象、投影、颜色、动作、候选判断及时间相同。A 从完整 B 原生合成复制；只修改两条相机属性。焦点目标和光圈轨道相同，焦距表达式按各自相机位置实际求值。固定镜头版保留相同物理对象运动，不另造一套课件方案。

已认可的 r02 **40秒1080p方向预演**和历史工程保持原样，作为风格基线；它不参与此次同导演时序的单变量 A/B。

## 本次镜头

0–1.6秒进入原题；1.6–4.7秒穿过已有原文；4.7–5.5秒确认原句；5.4–8.2秒捕获原词并形成前景工作空间；8.2–12.2秒比较归属；12.2–12.55秒执行原有候选排除；随后收束并返回原题，16.2–18秒保留后续候选。

候选集合首次更新在零基 **第302帧，12.583333秒**，由冻结动作审计结果派生。原 r02 的相应更新在第651帧、27.125秒。这里记录制作时序，不把时间提前本身当作高手感的证明。未决候选留存，不新增最终答案。

## 原生制作与验证

- AE Classic 3D：**344个原文/题面原词对象、34个来源投影**。实际字形范围与原文词序核对；投影复制实际源字形，记录原生层ID，并从回读的真实原位置出发。
- 原题世界持续存在。透明前景文字在同一世界中捕获、比较及退出，不插入新概念卡、箭头、划线或答案展示。
- 原生相机位置、观察方向、焦点目标和景深实际存在。捕获/比较时轻微景深，进入与返回时光圈归零；没有花哨旋转或弹跳。
- 逐层回读 A/B，移除唯一允许变化的 Camera Position / Point of Interest 后，其余原生轨道一致。逐帧读取 **2×432** 个候选状态与相机焦距。
- 补充检查实际源字体、静态原文字形、原位置、来源范围与投影的位置/缩放/透明度轨道。AE原生关键帧时间量化按明确容差核对。
- 原生 AE 渲染 **864张4K TIFF**，两版各9批。逐帧SHA校验后由FFmpeg封装；不是用图片或替代渲染器生成动画。本轮无声音编辑，不写入Premiere工程。
- 两份实际MP4均通过尺寸、帧率、432帧计数及全片解码核验；抽取 **34张编码后4K关键帧**检查题面、捕获、比较、候选退出和返回。
- **152份**已登记输入与历史文件前后SHA一致，包含原Bundle/Status、旧工程/媒体、r02、旧预演和既有未提交知识库/Cinema工作。未修改ANSWER、Registry、Frozen Teaching或文案。
- Native Fast Pass、Host Ownership、Experience Proof与Candidate Motion相关 **46项合成回归通过**；不是仓库全量回归。

所有Adobe写入使用`HostOwnership`，实际读回process/project/comp。首次构建发生明确脚本错误；保留独占记录和失败证据，核查部分工程后，用服务器指定recovery ID执行一次显式恢复。没有把超时当作可重试成功。导出时一条AE撤消组提示被核验、记录并关闭，已落盘的帧继续进入同一渲染回执。渲染结束后占用记录正常释放。

## 本地重放与停止点

代码和操作说明：[`ae/experiments/reality-cognitive-fast/README.md`](ae/experiments/reality-cognitive-fast/README.md)。真实资料只保存在忽略的本地 revision：

```text
local-data/creative-proofs/reality-cognitive-r03-native-fast/
  NATIVE_SPEC.json
  NATIVE_IDENTITY.json
  REALITY_COGNITIVE_NATIVE_FAST_PASS_4K.aep
  HOST_PRIOR_SNAPSHOT.aep
  NATIVE_AUDIT_BEFORE_RENDER.json
  NATIVE_AUDIT.json
  NATIVE_AUDIT_SUMMARY.json
  NATIVE_RENDER_A.json / NATIVE_RENDER_B.json
  FRAME_TRANSFER_*.json
  HOST_RECEIPTS.json
  A_NATIVE_FAST_PASS_4K.mp4 / B_NATIVE_FAST_PASS_4K.mp4
  MEDIA_INDEX.json
  DIRECTOR.md / AV_CUE_SHEET.csv
  ACTUAL_MEDIA_FRAME_MAP.json
  INPUT_PROTECTION_BEFORE.json / INPUT_PROTECTION_AFTER.json
  ENCODED_QA_RECEIPT.json / encoded-qa/
  FINAL_EXECUTION_RECEIPT.json
  HUMAN_REVIEW.json / HUMAN_REVIEW.md
```

Spec SHA：`8220c4b763b0330026fae9294308e2a62afbdfd7a70dbeb1c086799b43c8099f`。
最终原生工程SHA：`a437d143c425f29fb2ce17824a22a02a927f80a3c7eb1cf595defb6f1ba4ce5e`。
每版render receipt另存该版完成时的工程SHA；最终工程是在两版渲染后保存的版本。

实际媒体帧范围绑定媒体SHA和原生轨道时序；人工语义锚点仍待反馈，不宣称Audience Learning Loop已获得真实观看证据。

只等待三项独立人工判断：**高手感、电影感、因果感**。捕获中原位文字与来源投影的短暂共存，也应结合动态观看检查是否争夺注意力。工程检查不代签观感，`human_review=PENDING`。本批停止，不自动加入慢放或扩展整期。原AI教学审阅级别保持不变，`public_render_ready=false`。公开仓库仅提交工作流、代码、脱敏报告和合成测试。
