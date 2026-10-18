# 自主整期制作 v1

执行入口仍是 `ae/experiments/adaptive-episode/run.py`。`autonomous` 只编排
`authored_episode.dispatch → AV_AUTHOR / AV_PLAN → authored_native → AE / Premiere / package`，
不另建渲染器，也不回到历史 B06/R06 的执行停点。

本次用户授权整期内部制作、AI 独立审阅和定向修订。完整稿继续从实际作者输入导出并全文发送；
用户暂未回复保持 PENDING，内部制作继续。最终整片验收和公开发布仍由用户决定。

用户明确提交已独立审阅的完整稿时，可使用 `copy_review=USER_REVIEWED_EXACT_COPY`
及 `copy_review_evidence`。每次当前入口重新验证外部用户的明确文字、来源 Markdown
与收据 SHA、场景顺序及逐场完整口播（只忽略排版空白）。作者的自签标签不能代替该记录；
修改任一字或标点即失效。脚本与 QA 仅更新文案状态，视觉、听感和整片验收保持独立。

## 已实现的操作

```powershell
python -X utf8 ae/experiments/adaptive-episode/run.py autonomous <local-data/revision> --brief <BRIEF.json> --through prepare
python -X utf8 ae/experiments/adaptive-episode/run.py autonomous <local-data/revision> --through render-master --batch-size 96
python -X utf8 ae/experiments/adaptive-episode/run.py autonomous <local-data/revision> --through package-master --batch-size 96
python -X utf8 -m ae_production.autonomous_episode status <local-data/revision>
python -X utf8 -m ae_production.autonomous_episode review <local-data/revision>
python -X utf8 -m ae_production.autonomous_episode revise <local-data/revision> --new-folder <local-data/new-revision> --decision <REVISION_REQUEST.json>
python -X utf8 ae/experiments/adaptive-episode/run.py autonomous <local-data/revision> --through restore
```

省略目录时，原入口读取实际生产索引。索引可指向同一 Git 仓库已登记 worktree 的
`local-data`，保留真实制作的绝对绑定；任意外部目录不享有该例外。

`BRIEF.json` 提供有效冻结候选池、风格资料和产品目标。宿主 AI 调度选材、文案、语言、
观众任务、导演及独立审阅职责，提交绑定输入的作者响应；`consume_author_response`
检查后才进入既有消费者。缺意群时产生语言作者工作包并回到同一 `chunks`。
`NEEDS_HOST_AGENT` 是宿主 AI 应继续完成的工作项，不是向用户索要作者输入或中途批准。
也可显式配置本地 agent 的 argv；裸 CLI 不伪造模型作者或观察结果。

## 实际消费者与恢复

作者的源跨度、观看任务、披露、候选前缀、编排、阅读路径、注意事件和完整声音放置只维护
一个时钟。Pedagogy 版本显式选择；旧来源不获得新方法身份。旧 Student POV/0.4 或细结构
运行时的 HOLD 必须如实保留，不能靠改状态获得执行资格。

主合成原生输出 3840×2160 / 24fps。默认受保护交互宿主按 96 帧分段；每 768 个实际新渲帧
在完整、干净、已保存的检查点正常退出并通过桌面入口恢复同一保存工程，释放原生渲染器资源。
原 PID 退出、保存字节、新 PID、工程和目标逐项回读。不强制结束现有 Adobe 进程。

所有 Adobe 写操作只有一个执行者，继续使用共享 `HostOwnership`。未知写保留占用并检查；
只读连接超时可唤醒已观察的宿主再读。Premiere 部分编排先回读原生片段、完整 take、位置、
长度及原工程，严格排除重复、裁断或外来音轨后，只完成未放置部分。

已完成分段须有 `done=true`、同版计划/原生绑定和真实媒体 SHA。无收据媒体不自动重做。
跨版本复用只接受有界、已证明的模板或注意/阅读可见性修复；真实源、完整声音、其余时钟、
相机、布局、阅读和原生层逐项相同。受影响整场重渲；递归保留实际父媒体与原始渲染身份。

新口播只复用精确文本一致且未被拒绝的完整 take，其余由既有 Producer 真正生成。
CPU-only 安装自动选择已支持的 CPU 后端，模型、声音包与速度控制不变；
实测新音频重新对齐并编译时钟，不沿用旧对齐或裁短、拉伸声音迁就旧画面。

## 实际媒体反馈

先交出完整同版声画，再把最终媒体绑定的独立观察交给 `review`。
`internal_ai_review` 进入现有 Audience Learning 追加台账，和外部人类、平台数据通道分开。
问题包含媒体、场景、时段、事实、责任模块和复查；`revise` 消费选中的实际问题并生成新作者输入。
没有实际问题不产生空修订，最多三轮有据定向修订。

本次环境明确拒绝音频感知，也未提供直接原速视频感知。编码画面和连续帧观察如实记录；
音频完整性、对齐、波形、ASR 或文件哈希均不是试听。完整听感与原速运动不能标成通过。
`REVIEW.html` 提供完整影片、可编辑工程、全文、字幕和章节入口，供用户最终验收。

内部音乐 scratch 不因混音成功获得公开权利。无实际发布则没有平台留存或学生效果数据。
`public_render_ready=false`；历史局部认可不会升级为新整片或独立人类教学认证。
