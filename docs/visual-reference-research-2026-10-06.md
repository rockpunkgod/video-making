# 教学视频视觉复审与参考吸收

2026-10-06。基于 main@3fb2b67 与本地消费者试片 r11。用户反馈：离目标效果仍很远。
本轮完成文献、GitHub 场景源码和现有输出复审；没有把研究建议冒充已完成的新成片。

## 结论与纠偏

当前最大问题是**教学动作没有成为画面主体**。之前把“简洁、克制”执行成小字、
大面积空白、统一淡入和结果卡片。版面有所区分，但从证据到判断的过程仍然薄弱。
工程检查证明文件、绑定和输出可靠，不证明好看、好懂或适合目标观众。

撤回“单焦点版可以作为整体方向优胜者”的强解释。它的主次清楚，但证据过早退出。
当前三版均保留为探索样本，创意方向仍未获用户认可。

### 实际输出证据

- 单焦点版有 16 条动画轨道，全部为 opacity；另两版各 17 条，也全部为 opacity。
  这不是要求增加轨道数，而是确认当前没有把选择、分组或关系建立做成可见动作。
- 单焦点版原文在 5.25 秒退出。后面的判断和停止说明需要观众记住刚才的原文。
- 11.5 秒时，单焦点版有 45 个非空白屏幕字符，尚未计字幕；边界、检查清单、
  补充说明同时出现。字符数只是负荷线索，不能代替阅读测试。
- 证据对照版末段最小字号为 27px。若 1920px 宽视频显示为 390px 宽，名义字号
  约 5.5px；42px 字幕约 8.5px。实际观看设备未知，390px 是风险模拟而非用户设备事实。
- 已抽取三版 4s / 7.8s / 12s 成片帧做 390px 宽对照。真实题面与截图仅在忽略目录。

## GitHub：看具体场景，不把框架名称当审美

以下均已核验仓库并读取所列源码。没有运行第三方完整项目，也没有声称观看其全部样片。
源码快照固定到下列提交；第三方源码只存本地参考目录，公开仓库保存链接和原创分析。

| 来源与已读场景 | 观察 | 吸收方式 | 不直接照搬 |
|---|---|---|---|
| [3b1b/videos · attention.py](https://github.com/3b1b/videos/blob/306a1346a356c7a7b097875ceb51c5cd67d0a56c/_2024/transformers/attention.py)，`AttentionPatterns` 开头 | 整句中的词有持续身份；分别框选词组，随后建立连接并停顿 | 原句作为主舞台；逐步标出已绑定的词和关系，判断紧贴对应结构出现 | 黑底、多色体系、数学内容与现成画面；不能把模型注意力的解释变成我们的语法事实 |
| [motion-canvas/examples · state-machine.tsx](https://github.com/motion-canvas/examples/blob/8ffefed144368d33de4b0e451894c718eb95d574/examples/asset-code/src/scenes/state-machine.tsx)；同项目 `intro.tsx` | `waitUntil` 连接讲解节点；文字选择按词/行变化；后续图形与连线分步出现 | 按口播语义节点安排高亮、分组、关系线和停顿；内容到动作逐项对应 | 示例中的背景效果、旋转和弹性；也不为参考而更换 AE/PR 主流程 |
| [ibelick/motion-primitives · text-effect.tsx](https://github.com/ibelick/motion-primitives/blob/120f64f6ca60348e251f929e9c81f11ccbe45eda/components/core/text-effect.tsx)、[text-morph.tsx](https://github.com/ibelick/motion-primitives/blob/120f64f6ca60348e251f929e9c81f11ccbe45eda/components/core/text-morph.tsx) | 区分字/词/行的节奏；字符通过持续 layout ID 连接前后状态 | 短中文提示按意义成组出现；场景变化时保留同一证据对象的视觉身份 | 逐字弹跳、默认 spring、模糊字；尤其不把提示词变形成“答案”，以免暗示定案 |
| [juliangarnier/anime · split-effects](https://github.com/juliangarnier/anime/blob/01b81be1df6843ccfe0a71c0699a746bf740dd77/examples/text/split-effects/index.js) | 将行和词分开编排；支持时间线和恢复原位 | 参考排版对象的组织方式，少量用于非证据性短标题 | 循环缩放、随机位移、字母扰动；不适合需要精读的原题 |

3b1b 的视频源码仓库声明 CC BY-NC-SA 4.0，不能因 Manim 库采用 MIT 就假定视频源码
同样可直接商用。本轮只吸收组织方法，没有移植其代码或素材。[仓库说明](https://github.com/3b1b/videos#readme)

上述取舍属于项目的设计判断，不是 GitHub 作者对我们内容的背书。网页 UI 动效库可
帮助观察节奏和连续性，但不能替代教学分镜。

## 文献：哪些支持调整，哪些不能外推

| 文献与阅读范围 | 相关发现 | 本项目采用的推论与边界 |
|---|---|---|
| Mayer & Moreno (2003), *Nine Ways to Reduce Cognitive Load in Multimedia Learning*；原文理论和干预章节 | 讨论对齐、信号提示、同步和分段如何减轻处理负担 | 标签靠近原文，高亮与讲解同步。不能简单推成“删掉字幕”；我们的语言学习、静音观看和可访问性需求仍需考虑。[原文](https://carpentries.github.io/instructor-training/files/papers/mayer-reduce-cognitive-load-2003.pdf) |
| Tversky, Morrison & Bétrancourt (2002), *Animation: Can It Facilitate?*；原文结论与比较设计 | 动画并不天然优于等信息静态图；过快或复杂会妨碍理解 | 动画应揭示关系/变化，让中间步骤可观察。也不能反推“全部静态最好”。[原文](https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/_Morrison_Betrancourt_AnimationCanitfacilitate.pdf) |
| Alpizar, Adesope & Wong (2020), *A meta-analysis of signaling principle in multimedia learning environments*；出版社/作者机构摘要 | 29 项实验、2726 人，信号提示总体呈正向效果，受条件影响 | 值得优先试“指向当前证据”的高亮，不能以高亮数量或效应量保证本片效果。[出版社](https://link.springer.com/article/10.1007/s11423-020-09748-7) |
| Fiorella & Mayer (2016), *Effects of observing the instructor draw diagrams…*；ERIC 的作者摘要，未获取完整论文 | 四项实验的结果依条件而异；无手部的渐进绘制没有显著优于对照 | 支持研究过程演示，但不能宣称“画线一定改善学习”，也不据此添加假手动画。[作者摘要](https://eric.ed.gov/?id=EJ1099178) |
| Guo, Kim & Rubin (2014), *How Video Production Affects Student Engagement*；作者机构摘要及作者稿首页 | MOOC 观看数据提示制作方式与参与度相关 | 借鉴讲解过程感；不能把参与度当理解，也不能从长课数据推出“15秒最优”。[作者机构记录](https://pure.kaist.ac.kr/en/publications/how-video-production-affects-student-engagement-an-empirical-stud/) |
| Cheng et al. (2022), *Investigating the Role and Interplay of Narrations and Animations in Data Videos*；原文摘要、讨论和局限 | 对 60 条数据视频、426 片段进行定性分析，归纳口播与动画的关系 | 为每句口播写对应视觉动作；这是设计类比，研究没有证明这种改法能提升高考英语学习。[作者机构原文](https://www.microsoft.com/en-us/research/uploads/prod/2022/05/NarrationsAnimationsInDataVideos-EuroVis2022.pdf) |

## 下一版只解决一个主问题：让判断在原文上发生

建议方向：**原文主导的动态讲解**。把现有的纸色与克制排印作为底层，把对象持续性、
局部标注、关系建立和有目的的停顿作为主要表现力。每次显著运动都对应一个已经冻结的
教学动作。美术参考不能补充教学结论。

以下为导演草案，不是已生成或已批准的新教学文案。时间是暂定分配，不是研究结论。

| 阶段 | 观众需要看见的变化 | 制作取舍 |
|---|---|---|
| 建立题面 | 原句和空位直接成为主体，知道正在看哪里 | 去掉独立标题页；原文首帧可读，不把“看这里”做成大面积空场 |
| 指向证据 | 已绑定的支配词、限定词按口播顺序被标出；其他部分退到次要层级 | 每次一个主动作；颜色编码稳定。不能删除尚需阅读的结构 |
| 形成判断 | 在相应词组旁建立分组/短连接，出现当前语法功能 | 同一空位持续可认；不用跨屏飞行，也不把词语换成答案 |
| 明确停止 | 保留原文与当前判断，强调仍未确定的部分 | 停止表现为推理到此为止，不是装饰性封口印章 |
| 交代边界 | 否定条件和后续检查按语义分组，留足阅读时间 | 不把所有限定挤成小字页脚。需要更长时长时先修订时间契约，不加速或藏掉边界 |

优先做一段有起因、有动作、有结果的粗动画来验证此方向，再制作完整 Hero。暂时停止
扩充配色方向与增加通用动效组件。AE/PR 继续承担制作，外部仓库承担参考。

### 应当质疑的旧要求

- **固定 10–15 秒**：可以验证一个局部动作，不一定容得下所有解释和限制。研究不能
  给本片指定最优时长。若阅读不足，应申请/记录范围内的时长方案调整；本轮不偷改运行契约。
- **绝对的大留白**：留白应服务主次。先保证目标观看尺寸下原文、关键标注和字幕可读。
- **每个方法固定一套品牌动作**：只有在动作确实表达教学步骤时保留，不能为了签名制造运动。
- **一套数值即“高级感”**：字号、速度、缓动都是可检验的制作选择，不是永久审美公式。

## 下轮验收方式

1. 先审分镜：遮掉标签后，是否仍看得出“选中了什么、关系怎样建立、为什么停下”。
2. 对比同一教学输入、同一口播与声音，先隔离视觉变化；不得改事实来制造惊喜。
3. 同时检查 1920px 输出与假设的 390px 宽观看，后者不合格时不能用桌面截图通过审美验收。
4. 看动作中点和真实播放，不只选静止的漂亮帧；关键原文在对应判断期间可回看。
5. 分开记录：绑定/渲染是否正确、编辑是否看清、用户是否喜欢、学生是否理解。
   现有测试只覆盖第一类的一部分，后面三类目前没有通过证据。
6. 学习效果试验以后再做：用独立获准的测试材料验证依据识别和边界理解，不新造教学 Review。

本轮只提交研究与制作规则更新。实际题面、媒体、第三方源码快照和诊断截图仍留在本地。
